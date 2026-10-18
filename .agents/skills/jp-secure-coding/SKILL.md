---
name: jp-secure-coding
description: EASF でコードを書く・直す・レビューするときは常に使う、日本の第三者脆弱性診断（IPA「安全なウェブサイトの作り方」・ウェブ健康診断仕様・OWASP ASVS L2・OWASP Top 10 for LLM）で指摘されない実装規則。FastAPI / SQLAlchemy / Pydantic のバックエンド、React / TypeScript のフロントエンド、ファイルアップロード、認証・セッション・CSRF・認可、セキュリティヘッダ、エラーとログ、外部接続（REST / MCP / LLM）とプロンプトインジェクション、依存関係と秘密情報を扱う。API・画面・アダプタ・アップロード・ログイン・LLM 呼び出しを追加・変更するとき、「セキュリティ」「脆弱性」「診断」「XSS」「SQL」「CSRF」「認可」「SSRF」と言われたときに使う。
---

# jp-secure-coding — 診断で指摘されない実装規則

日本の案件では、受け入れ前に第三者が脆弱性診断（Web アプリ診断・プラットフォーム診断）を行うことが多い。
診断員は **IPA「安全なウェブサイトの作り方」の 11 項目**、**ウェブ健康診断仕様の 13 項目**、**OWASP Top 10 / ASVS**、加えて「情報漏えい」「セキュリティヘッダ」「クッキー属性」などの定番項目を手と道具（Burp Suite・OWASP ZAP など）で確かめる。
この skill は **その観点を、書く時点で潰す** ためのもの。診断の実施方法は `jp-vuln-assessment`。

## 0. 原則（全部に効く）

1. **根本的解決を先に、保険的対策を重ねる**（IPA の考え方）。例：SQL はバインド変数（根本）＋ DB ユーザーの最小権限（保険）。
2. **既定は拒否**。ルータ・エンドポイント・アダプタ・MCP ツール・ファイル形式・接続先は許可リスト。足し忘れは「動かない」側に倒れる。
3. **外から来るものはすべて信用しない**：リクエスト、アップロード文書の中身、LLM の出力、MCP / REST の応答、JSON Schema 内の `$ref`、ファイル名。
4. **境界で型を固める**：入力は Pydantic（`extra="forbid"`、`strict`）で受け、出力は response_model で絞る。DB モデルをそのまま返さない・受けない。
5. **失敗は閉じる**（fail closed）：検証できない・判定できない・時間切れは「成功」にしない。人の確認へ回すか、エラーにする。
6. **情報を出しすぎない**：スタックトレース、ライブラリ名と版、内部パス、SQL、存在確認できてしまう差分を利用者に見せない。

## 1. 項目ごとの規則（要約）

詳しい対策・コード例・テストは `references/` を読む。診断で必ず見られる順に並べた。

| # | 診断項目（IPA / ウェブ健康診断） | 規則（要約） | 詳細 |
|---|---|---|---|
| 1 | SQL インジェクション | ORM / Core のバインド変数だけ。`text()` は `bindparams` 必須、f-string・`%`・`+` で SQL を組まない。**並び替え・列名は許可リストで対応付け**（`sort=` は定番の穴）。LIKE は `\`・`%`・`_` をエスケープ | backend-fastapi.md §2 |
| 2 | OS コマンド・インジェクション | `subprocess` は引数リスト・`shell=False`・絶対パスの固定バイナリ。利用者入力を引数に入れない（入れてよいのはサーバが作った一時ファイルのパスだけ）。`os.system`・`eval`・`exec`・`pickle.loads`・`yaml.load` 禁止 | backend-fastapi.md §3 |
| 3 | パス名パラメータ／ディレクトリ・トラバーサル | 保存名はサーバが発行する UUID。利用者のファイル名をパスに使わない。読むときは ID → DB → 保存先で解決し、`resolve()` 後に保存ルート配下か確かめる | upload-and-files.md |
| 4 | セッション管理の不備 | サーバ側セッション（DB）。ID は `secrets.token_urlsafe(32)`。**ログイン成功で ID を振り直す**（固定化対策）、ログアウトでサーバ側を消す、無操作 30 分・絶対 8 時間で失効（値は設定） | backend-fastapi.md §4 |
| 5 | クロスサイト・スクリプティング | React の自動エスケープに任せる。`dangerouslySetInnerHTML`・`innerHTML`・`eval`・`new Function` 禁止。`href`/`src` は `http:`/`https:`/相対だけ。根拠のハイライトは文字列を分割して React ノードで描く。CSP を厳しく | frontend-react.md |
| 6 | CSRF | Cookie セッション＋ `SameSite=Lax` ＋ **CSRF トークン（ヘッダ `X-CSRF-Token`）** ＋ 状態を変えるメソッドで `Origin` 照合。GET で状態を変えない | backend-fastapi.md §5 |
| 7 | HTTP ヘッダ・インジェクション | 利用者入力をヘッダに入れない。ダウンロード名は `Content-Disposition: attachment; filename*=UTF-8''…`（RFC 5987 で符号化、改行除去） | upload-and-files.md |
| 8 | メールヘッダ・インジェクション | メール送信機能を作らない（POC 対象外）。作るなら変更要求を出す。診断報告では「機能なし」と明記 | — |
| 9 | クリックジャッキング | `Content-Security-Policy: frame-ancestors 'none'` と `X-Frame-Options: DENY` | backend-fastapi.md §6 |
| 10 | バッファオーバーフロー | Python 自体は安全。危ないのはネイティブの解析ライブラリ（PDF・画像）→ 最新版、別プロセス・時間とメモリの上限・ページ数上限で隔離 | upload-and-files.md |
| 11 | アクセス制御・認可制御の欠落 | 全ルータに認証の依存性を既定で付け、健康確認だけ明示的に外す。**オブジェクト単位の認可**（その案件のメンバーか）をリポジトリ層の取得関数で必ず行う。UUID は認可の代わりにならない | backend-fastapi.md §7 |
| 12 | ディレクトリ・リスティング | 静的配信は Vite のビルド成果物だけ、一覧表示なし。アップロード領域は配信しない | backend-fastapi.md §6 |
| 13 | 意図しないリダイレクト | `next=`・`redirect=` を受けない。必要なら固定のパス一覧から選ぶ | backend-fastapi.md §6 |
| 14 | 認証 | パスワードは argon2id。ログイン失敗の文言は 1 種類（「ユーザー ID またはパスワードが正しくありません」）。連続失敗で一時ロック、応答時間を揃える。パスワード欄は `autocomplete="current-password"` | backend-fastapi.md §4 |
| 15 | クッキーの不適切な利用 | `__Host-` 接頭辞、`Secure`、`HttpOnly`、`SameSite=Lax`、`Path=/`、`Domain` なし。セッション以外の情報を Cookie に入れない。**トークンを localStorage に置かない** | backend-fastapi.md §4 |
| 16 | 情報漏えい | 共通の例外ハンドラで `{code,message,trace_id,details}` だけ返す。`Server`・`X-Powered-By` を出さない。本番相当では `/docs`・`/redoc`・`/openapi.json` を閉じる。ソースマップを配信しない。HTML コメントに内部情報を書かない | backend-fastapi.md §8 |
| 17 | SSRF・外部接続 | 接続先はアダプタ設定の許可リスト（完全一致のホスト）。名前解決後の IP がプライベート・ループバック・リンクローカル・メタデータなら拒否。リダイレクトを追わない。JSON Schema の外部 `$ref` を解決しない | ai-llm-mcp.md §3 |
| 18 | プロンプトインジェクション・LLM | 文書はデータとして区切って渡し、文書中の指示に従わない。LLM にはツールを持たせない（持たせるなら読み取り専用の許可リスト）。出力は JSON Schema で検証し、未検証の根拠は「未確認」 | ai-llm-mcp.md |
| 19 | 一括代入（mass assignment） | 入力モデルと DB モデルを分ける。`role`・`owner_id`・`status`・`approved_by` を入力から受けない | backend-fastapi.md §1 |
| 20 | 資源の枯渇 | すべての一覧にページング上限、アップロードサイズ・ページ数・処理時間・トークン・リトライ回数・同時実行数に上限 | backend-fastapi.md §9 |
| 21 | 依存関係・秘密情報 | ロックファイル必須、既知の脆弱性・ライセンス（AGPL / GPL）を CI で検査。秘密は環境変数と `.env`（コミットしない）、ログに出さない | dependencies-and-secrets.md |

## 2. 書く前・書いた後の手順

1. 作る機能が上の表のどの行に当たるか確かめ、該当する `references/` を読む。
2. **否定テストを先に書く**（`anthropic-skills:tdd` の流れで）：未ログイン 401、他案件 403/404、`extra` フィールド 422、上限超え 413/422、不正な並び替え列 422、CSRF なし 403。
3. 実装する。共通部品（認証依存性・`get_owned_or_404`・アップロード検証・ヘッダミドルウェア・安全な HTTP クライアント）を使い、画面・API ごとに自作しない。
4. `ruff check`（`S` 規則を含む）・`bandit`・型検査・テストを実行し、結果を報告に貼る。
5. ゲート前は `jp-vuln-assessment` でまとめて診断する。

## 3. 例外を作るとき

規則から外れる必要があれば、コードに `# security-exception: <理由> (DECISIONS.md D-xxx)` を書き、`DECISIONS.md` に理由・代替策・期限を記録して人間の承認を得る。`# nosec` / `noqa: S` だけで黙らせない。

## references

- [backend-fastapi.md](references/backend-fastapi.md) — 入力・SQL・コマンド・認証とセッション・CSRF・ヘッダ・認可・エラー・上限
- [frontend-react.md](references/frontend-react.md) — XSS・CSP・URL・保存・ビルド
- [upload-and-files.md](references/upload-and-files.md) — アップロード・保存・ダウンロード・PDF / 画像の解析
- [ai-llm-mcp.md](references/ai-llm-mcp.md) — LLM・MCP・REST アダプタ・SSRF・プロンプトインジェクション
- [dependencies-and-secrets.md](references/dependencies-and-secrets.md) — 依存関係・ライセンス・秘密情報・コンテナ
- [standards-map.md](references/standards-map.md) — IPA / ウェブ健康診断 / ASVS / LLM Top 10 との対応表
