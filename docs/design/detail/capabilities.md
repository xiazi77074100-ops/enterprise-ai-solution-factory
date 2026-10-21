# 詳細設計：業務の Capability（解析・抽出・検証）

| 版 | 日付 | 変更内容 | 作成者 |
|---|---|---|---|
| 0.1 | 2026-10-19 | 初版（P3-01b） | Claude Code |
| 0.2 | 2026-10-19 | 根拠の照合（MCP）・結果の出力（P3-01c） | Claude Code |
| 0.3 | 2026-10-19 | OCR（Tesseract）、OCR 由来の根拠は未確認（P3-04） | Claude Code |
| 0.4 | 2026-10-21 | 規則ベースの抽出 1.1.0（文言の設定・真偽）、根拠は最初の出現だけ、検証の真偽の比較、万・億の金額（P4-03） | Claude Code |

Capability の契約（入出力・設定のスキーマ）は `contracts/examples/capabilities/` が正。ここは実装の動きを書く。どの部品も業務名を持たず、業務の違いはノードの設定（`field_spec`・Rule pack）で表す（`easf-capability-contract` §1-4）。

## 1. 一覧

| 実装キー | Capability | 種類 | 実装 | 実行のされ方 |
|---|---|---|---|---|
| `document_parser.v1` | `document.parser@1.0.0` | local | `backend/app/capabilities/document_parser.py` | ワーカーが文書を読み（`StoredDocumentHandler`）、子プロセスで解析 |
| `rule_based_extractor.v1` | `document.rule_extractor@1.0.0` | local | `backend/app/capabilities/rule_extractor.py` | 子プロセス |
| `structured_extractor.v1` | `document.extractor@1.0.0` | llm | `backend/app/capabilities/mock_extractor.py`（mock の応答） | LlmPort の mock（`execution_mode: mock`、D-004） |
| `rule_validator.v1` | `document.rule_validator@1.0.0` | local | `backend/app/capabilities/rule_validator.py` | ワーカーが Rule pack を読み（`RulePackHandler`）、子プロセスで評価 |
| `easf_local_mcp:locate_evidence` | `document.evidence_locator@1.0.0` | mcp_tool | `backend/app/capabilities/evidence.py`（`backend/app/mcp_server.py` のツール） | MCP アダプタ（`backend/app/adapters/mcp.py`）が自作のローカル MCP サーバを stdio で起動して呼ぶ |
| `result_exporter.v1` | `result.exporter@1.0.0` | local | `backend/app/capabilities/result_exporter.py` | 子プロセス |

結び付けは `backend/app/executor/handlers.py`、許可リストの `available` は `backend/app/catalog/registry.py`（一致をテストで確かめる）。ワーカー側の読み出しは `backend/app/adapters/resources.py`。参照が解決できない（文書・Rule pack が無い、保存したファイルのハッシュが違う）ときはノードを失敗にし、再試行しない（`document_not_found`・`document_unreadable`・`rule_pack_not_found`）。

## 2. 解析（document_parser.v1）

- PDF：テキスト層（pypdfium2、`backend/app/capabilities/pdf_text.py`）のページごとのテキスト。根拠の文字の番号はこの文字列を指す。
- 設定 `ocr`（ノードの設定）：
  - `tesseract`：画像（PNG・JPEG）と、テキスト層の無い（空白だけの）PDF のページを Tesseract（日本語、`--psm 6`）で読み、`extraction_method: ocr_tesseract`。PDF のページは 300 dpi で画像にしてから読む。Tesseract は PATH の実行ファイル（コンテナに同梱、Alpine の `tesseract-ocr` 5.5.2・`tesseract-ocr-data-jpn`）を絶対パスで、引数のリスト・`shell=False`・自分で作った一時ファイルだけで呼ぶ（`backend/app/capabilities/ocr.py`）。OCR の出力は NFKC にし（丸数字・全角の数字も数字に）、日本語の文字どうしの間の空白を除く（Tesseract 5.5 は「請 求 書」のように空白を入れる）。根拠の文字の番号はこの正規化後のテキストを指す。1 ページ 40 秒まで。Tesseract が無ければノードを失敗にする（`exception_ocrunavailableerror`。空のテキストでごまかさない）。
  - `none`：画像は空のテキストの 1 ページ、テキスト層の無い PDF のページも空。抽出は missing → 人の確認。
  - `llm`：未対応（D-004）。ノードを失敗にする。
- テキスト層のある PDF のページは、`tesseract` でも OCR しない。
- 1 ページが 50,000 文字を超えたら失敗（切り詰めると根拠の位置がずれるため）。
- 出力：`document_id`・`document_sha256`（登録時のハッシュ）・`pages`。

## 3. 規則ベースの抽出（rule_based_extractor.v1、D-015）

設定 `field_spec[]` の各項目に `labels`（見出しの文字列、1〜10 個）を書く。

1. ページのテキストを NFKC に正規化する。
2. 各見出しについて「見出し＋（任意の括弧書き、例「（10%）」「（普通）」）＋ `：` または `:`」の後ろの、行末までを候補にする。
3. 型ごとに読む：`date`（西暦・和暦〔令和・平成、R・H〕→ ISO 8601）、`decimal`（`¥`・`￥`・`円`・桁区切りを除いた数字の文字列）、`integer`、`string`（前後の空白を除き 200 文字まで）。
4. 結果：異なる値が 1 つ → `found`、2 つ以上 → `uncertain`（値は null）、見出しはあるが読めない → `uncertain`、見出しが無い → `missing`。
5. `array`・`boolean` はこの方式では読まないので `uncertain`（人が確認）。
6. OCR で読んだページ（`extraction_method` が `text_layer` でない）から拾った値は、1 つに決まっても `found` にせず `uncertain`（値は下書きとして残す）。OCR は `¥` や区切りを読み違える（例：`¥104,060` → `\104,.060` → `104`）ため、誤った値を確定に見せない（D-034）。値の読み取りの前に、OCR のページの値だけ後処理する：数字に挟まれた「.」＋3 桁は桁区切りの「,」とみなす、2 つ以上の空白（列の間隔）より後ろを捨て、前後の「-」「_」「|」（罫線）を除く（D-036）。

文書の中の文は、どれもデータとして扱う（指示として解釈しない。LLM を使わない）。

### 3.1 版 1.1.0 の設定（P4-03、契約書）

`document.rule_extractor@1.1.0`（同じ実装キー `rule_based_extractor.v1`）。`field_spec[]` の各項目に、次の設定を任意で書ける。`labels` だけの設定（1.0.0）は前と同じに動く。どれも**文字列そのまま**で、正規表現を設定から受けない。

| 設定 | 意味 |
|---|---|
| `between: [{before, after}]` | `before` と `after` に挟まれた文字列（改行をまたいで探す。60 文字以内で「。」を含まない）。`before` が空なら行の先頭から |
| `heading` | その文言を含む **30 文字以内の行**を、印字どおりの行で値にする（条の見出し。長い文の中で触れただけのもの〔不審な指示など〕は数えない） |
| `true_if` / `false_if` | 真偽の項目：その文言があれば true / false。両方あれば uncertain |
| `uncertain_if` | その文言があれば、値が 1 つに決まっても uncertain（「別途協議」「相当の期間」） |

金額は「3,000万円」「1億円」も読む（`backend/app/capabilities/values.py`。請求書の読み方は変わらない）。

## 4. LLM の抽出（structured_extractor.v1、mock）

実 API は D-004 で保留。mock は文書を読まず、`field_spec` の全項目を null・`uncertain` で返す（決定的。正解ラベルを使わない）。実行は `mixed` / `mock` として記録され、実接続には数えない。流れの確認のためだけに使う。

## 5. ルールの検証（rule_validator.v1）

Rule pack（`contracts/rule_pack.schema.json`）の式を、決まった演算子だけで評価する（`eval` しない）。

| 状況 | 結果 |
|---|---|
| 式が真 | `pass` |
| 式が偽 | `fail` |
| 参照した値が null・空・無い | ルールの `on_missing`（`uncertain` または `fail`） |
| 値はあるが比べられない（数値でない、未知の演算子、`unique_in_project` で案件の文脈が無い） | `uncertain` |
| `and`・`or`・`not` の中で値が無い | 3 値の論理（Kleene）。決まらなければ `uncertain` |
| 入れ子が 8 段を超える | `uncertain` |

- `present` は値の有無そのものを見る（無ければ偽）。
- `matches_reference`：参照表で `match_field` が `key_field` の値と一致する行のうち、`value_field` が項目の値と一致する行があれば真。該当する行が無い（未登録の取引先）も偽。
- `unique_in_project`：Executor が渡す `project_context.values[<項目名>]`（同じ案件の、この実行より前に成功した実行の確認後の値）に含まれていれば偽。
- `format`：`jp_invoice_registration_no` は `T` ＋ 13 桁の形だけを見る（合成データの登録番号は検査用数字をわざと誤っているため、検査用数字は確かめない）。
- `message` は「ルールの題名：適合／不適合／判定できません（要確認）」。入力の値を含めない。
- `requires_review`：`fail` が 1 つでもある、または `critical` が `pass` でない。

- 比較（`eq`・`ne`）は真偽どうしでもできる（P4-03。それまで CON-003 は常に uncertain だった）。真偽と数・文字列の比較、真偽の大小は uncertain。

## 6. 案件の文脈（project_context）

入力スキーマに `project_context` を持つ Capability には、Executor が入力を組み立てるときに付ける（辺からは渡さない）。中身は、同じ案件で、この実行より前に作られ成功した実行の、人の確認ノードの出力 `reviewed_fields` の値（文字列・数値だけ、項目ごとに 10,000 件・50 項目まで）。`snapshot_at` はこの実行の作成日時。Capability は DB を読まない（`easf-capability-contract` §1.1）。実装は `backend/app/executor/engine.py`。

## 7. 根拠の照合（easf_local_mcp:locate_evidence、ADR-005）

- 実際の MCP プロトコル（公式 SDK `mcp` 2.3.0、stdio）で呼ぶが、サーバは EASF 内の自作のローカルサーバ（`python -m app.mcp_server`、固定のコマンド）。**外部の実連携ではない**。
- ツールの引数は「Capability の入力 ＋ ノードの設定」。ツールのスキーマは `backend/app/mcp_tools/locate_evidence.json`（入力 ＝ 契約の `input_schema` に `configuration_schema` の項目を合わせたもの、出力 ＝ 契約の `output_schema`）。`mcp_tool` の版の登録時に Catalog が一致を確かめ、違えば `tool_schema_mismatch` で拒否する（`backend/app/catalog/validation.py`）。
- アダプタは許可リストのツール名だけを呼び、サーバが広告していなければ呼ばない（`mcp_tool_not_advertised`、再試行しない）。時間切れは `timeout`、サーバの起動失敗・プロトコルの異常は例外の型名だけを `mcp_<型名>` で記録する。
- 照合：項目の値の「印字の形」（`match: exact` は値そのまま、`normalized` は値・NFKC・日付の書き方〔西暦・和暦・スラッシュ〕・金額の書き方〔`¥`・`￥`・`円`・桁区切り〕）をページのテキストで探す。見つかった範囲を返し、その範囲の SHA-256 を付ける。状態は、テキスト層のページなら `verified`、OCR で読んだページなら `unverified`（OCR の文字は文書そのものの文字ではないため、ADR-003）。数の途中で切れる範囲（「¥104,060」の中の「¥1」など）・重なる範囲は使わない。1 項目につき**読む順の最初の出現だけ**を引用する（署名欄で繰り返す名前などを根拠にしない、P4-03）。1 文字の値・**4 桁未満の数字だけの形**（「30」は日付の日にも一致する）は探さない（「¥840」のような記号付きの形は探す）。見つからない値は根拠なし（空の配列。画面では「未確認」）。根拠を作らない（`easf-capability-contract` §1-6）。

## 8. 結果の出力（result_exporter.v1 と exportRunResult）

- Capability は出力の内容（判定・確認後の項目・ルールの結果）を決め、その内容の SHA-256 から作った UUID（`export_id`）を返す。ファイルは保存しない。
- `exportRunResult` は、成功した実行で出力のノードが成功しているものだけ（それ以外は 409 `run_not_exportable`）。保存したノードの出力から出力のノードの入力を組み立て直し、同じ関数で内容を作り、`export_id` が一致するときだけ返す（一致しなければ 409 `export_mismatch`）。
- 列と書式は `exports_and_events.md`。

