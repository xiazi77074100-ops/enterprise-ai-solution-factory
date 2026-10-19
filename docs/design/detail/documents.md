# 詳細設計：文書（アップロード・一覧・ダウンロード）

| 版 | 日付 | 変更内容 | 作成者 |
|---|---|---|---|
| 0.1 | 2026-10-19 | 初版（P3-01a） | Claude Code |

API の形は `contracts/openapi.yaml`（`uploadDocument`・`listDocuments`・`downloadDocument`、契約 1.0.2 のまま）が正。ここは内部の動きを書く。規則の出所は `jp-secure-coding` の upload-and-files.md、ADR-003・ADR-004。

## 1. 操作

| 操作 | 誰が | 入力 | チェック | 副作用 | API |
|---|---|---|---|---|---|
| 登録 | 案件の solution_lead・solution_architect・qa_evaluator | `multipart/form-data`：`file`（1 つ）・`data_origin`（`synthetic` だけ） | §2 の順 | 保存先にファイル、`document` に 1 行 | `uploadDocument`（201） |
| 一覧 | 案件のメンバー | `limit`（1〜200、既定 50）・`cursor` | メンバーでなければ 404 | なし。新しい順 | `listDocuments` |
| ダウンロード | 案件のメンバー | 文書 ID | 文書が無い・メンバーでない → 404（区別しない）。保存したファイルの SHA-256 が記録と違えば 500（壊れたファイルを返さない） | なし | `downloadDocument` |

実行の入力（`startRun`）の `document_ref` には、**同じ案件の文書の ID** だけを渡せる。無い ID・他の案件の ID・UUID でない値は同じ 422（`invalid_run_inputs`、「入力 {name} の文書が見つかりません。」）で、他の案件の文書があるかどうかは分からない（`backend/app/executor/engine.py`）。

## 2. 登録のチェック（順に。最初に当たったもので止まる）

| # | チェック | 結果 | code・メッセージ |
|---|---|---|---|
| 1 | 要求全体の大きさ（10 MB ＋ 64 KiB。ほかの API は 1 MiB のまま） | 413 | `payload_too_large`「送信データが大きすぎます。」 |
| 2 | ログイン・CSRF トークン・Origin | 401・403 | 共通 |
| 3 | 項目が `file` と `data_origin` のちょうど 2 つ、`file` は 1 つ、`data_origin` が `synthetic` | 422 | `validation_error`「入力内容に誤りがあります。」 |
| 4 | 案件のメンバーで、登録できるロール | 404・403 | 共通 |
| 5 | ファイルが 10 MB（10,485,760 バイト）以下 | 413 | `document_too_large`「ファイルの大きさが上限（10 MB）を超えています。」 |
| 6 | 空でない | 422 | `document_empty`「ファイルが空です。」 |
| 7 | ファイル名（§3）が空でない | 422 | `invalid_file_name`「ファイル名が正しくありません。」 |
| 8 | 拡張子・宣言の型・先頭のバイトが同じ許可された形式（§4） | 415 | `unsupported_media_type`「PDF・PNG・JPEG のファイルだけを登録できます。」 |
| 9 | 子プロセスで構造を確かめる（§5） | 422 | §5 の表 |

## 3. ファイル名

- 表示用の文字列としてだけ持つ（`display_name`）。保存先のパスにもヘッダにもそのまま使わない。
- NFC に正規化 → `/` と `\` で区切った最後の部分だけ → 制御文字（Unicode の Cc）と書式文字（Cf。右から左への上書き U+202E など）を除く → 前後の空白を除く。`.`・`..`・空は 422。
- 255 文字を超えたら、拡張子を残して前を切る。
- ダウンロードの `Content-Disposition` は `attachment; filename="<ASCII の代替>"; filename*=UTF-8''<RFC 5987 で符号化した名前>`。代替は ASCII の印字できる文字以外と `"`・`\` を `_` にしたもの。

## 4. 形式

| 形式 | 拡張子（大文字小文字を問わない） | 宣言の型（multipart の Content-Type） | 先頭のバイト |
|---|---|---|---|
| PDF | `.pdf` | `application/pdf` | `%PDF-` |
| PNG | `.png` | `image/png` | `89 50 4E 47 0D 0A 1A 0A` |
| JPEG | `.jpg`・`.jpeg` | `image/jpeg` | `FF D8 FF` |

宣言の型は照合に使うだけで、保存する `media_type` はサーバが拡張子から決めた値。ダウンロードの `Content-Type` もこの値。

## 5. 子プロセスでの構造の確認

解析ライブラリ（pdfium・Pillow）にアップロードされたバイト列を渡すのは、`LocalHandler` が起動する子プロセスの中だけ（20 秒で強制終了）。子プロセスから戻るのは状態とページ数だけ（`backend/app/documents/inspect.py`）。時間切れ・異常終了・想定外の結果は「読み取れない」として拒否する（成功にしない）。

| 状態 | 条件 | code・メッセージ |
|---|---|---|
| `encrypted` | パスワード付き、または暗号化された PDF | `document_encrypted`「暗号化された PDF は利用できません。」 |
| `active_content` | 文書レベルの JavaScript、または添付ファイルを含む PDF | `document_active_content`「JavaScript・添付ファイルを含む PDF は利用できません。」 |
| `too_many_pages` | 31 ページ以上 | `too_many_pages`「ページ数が上限（30 ページ）を超えています。」 |
| `too_many_pixels` | 画像の幅 × 高さが 40,000,000 画素を超える（展開爆弾） | `image_too_large`「画像の画素数が上限を超えています。」 |
| `unreadable` | 開けない・0 ページ・壊れた画像・時間切れ・異常終了 | `document_unreadable`「ファイルを読み取れません。」 |

## 6. 保存

| 項目 | 内容 |
|---|---|
| 場所 | 設定 `EASF_STORAGE_DIR`（既定 `var/documents`、`backend/` からの相対。Docker では名前付きボリューム `easf_documents` を `/data/documents` に）。Web から配信しない |
| 名前 | サーバが作る `uuid4().hex`（32 桁の 16 進）。拡張子なし。読むときは名前の形を確かめ、`resolve()` 後に保存先の配下か確かめる |
| 書き方 | `O_CREAT | O_EXCL`（上書きしない）、権限 `0600`、ディレクトリ `0700` |
| DB との順序 | ファイルを書いてから行を登録。登録に失敗したらファイルを消す |
| 変更・削除 | 行の更新は DB のトリガーで拒否（ファイルは変わらない。根拠は SHA-256 を指す）。削除の API はない（保持期限と削除の手順は ADR-004、未決） |

## 7. 項目（`document` 表、`backend/migrations/versions/0006_documents.py`）

| 列 | 型 | 制約・意味 |
|---|---|---|
| `id` | UUID | 主キー |
| `project_id` | UUID | 案件 |
| `display_name` | 文字列 255 | §3 |
| `media_type` | 文字列 32 | `application/pdf`・`image/png`・`image/jpeg` |
| `size_bytes` | 整数 | 1〜10,485,760 |
| `page_count` | 整数 | 1〜30（画像は 1） |
| `sha256` | 文字列 64 | ファイルの SHA-256（16 進の小文字） |
| `data_origin` | 文字列 16 | `synthetic` だけ |
| `storage_name` | 文字列 32 | 保存名（一意、API で返さない） |
| `uploaded_by` | UUID | 登録した利用者（API で返さない） |
| `created_at` | 日時 | 登録日時 |

## 8. 未決事項・制限

- 注釈・フォームの操作に付いた JavaScript は見ていない（文書レベルの JavaScript と添付だけ）。pdfium には JavaScript の実行環境がないため、解析で実行されることはない。
- 子プロセスのメモリの上限は未設定（時間の上限だけ）。解析の Capability（P3-01b）と合わせて決める。
- 同じ内容の文書の重複は許す（ハッシュで分かる）。
