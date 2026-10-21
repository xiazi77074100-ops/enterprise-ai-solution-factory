# G3 前の脆弱性診断報告書（自己診断・P4-06）

| 項目 | 内容 |
|---|---|
| 版・日付 | 1.0・2026-10-21（JST） |
| 対象 | main `2b87f6f` からの `codex/P4-06-g3-review`。最終差分は本 PR |
| 実施者 | Codex。CC の実装から独立したレビューとプロジェクト内の自己診断。**第三者診断ではない** |
| 環境 | Windows、Docker Desktop 4.41.2 / Engine 28.1.1。ローカル EASF Compose のみ。DB は55433、API は127.0.0.1:8001、`EASF_ENV=assessment`。Linux 回帰は `easf_test` 専用 |
| 範囲 | Phase 4 の抽出・真偽／金額の検証・根拠照合、`score_outputs`、`offline --write-outputs`、`eval_holdout_contract.ps1`。既存の認証・認可・文書・出力境界も回帰対象 |
| 基準 | リポジトリの診断チェックリスト（IPA「安全なウェブサイトの作り方」・ウェブ健康診断仕様・ASVS L2・OWASP Top 10 for LLM の対応規則）。今回の外部基準の最新版照合は未実行（既存プロジェクト規則に基づく診断） |
| 評価方法 | CVSS v3.1。高7以上／中4〜6.9／低0.1〜3.9／情報 |
| 対象外 | 第三者サーバ、会社・顧客環境、実LLM（保留）、外部REST/MCP、メール、公開TLS。ホールドアウトとベースラインのコードを開かない・生成しない |
| 承認 | 未承認。G3 は CC の統合確認後に人が判定する |

## 1. 総評

採点時の負の根拠位置を受理する低リスクの不備1件を合成文字列で再現し、許可された評価コード内で修正した。実行系の Capability・設定と契約は変更していない。報告書は診断の結果と未実行・未完了を区別し、未確認を「0件」と数えない。

G3 の判定には [独立レビュー](../../review/2026-10-21-g3.md) の残事項も必要。同じ Capability 版の実装が変更された既知の制約と、修正前の採点器による既存集計への影響は、人の判断を要する。今回の自己診断だけで第三者診断の保証や G3 承認を主張しない。

## 2. 指摘

| ID | 重大度・CVSS v3.1 | 場所・内容 | 対応 |
|---|---|---|---|
| VA-G3-001 | 低・2.8（AV:L/AC:L/PR:L/UI:R/S:U/C:N/I:L/A:N） | `score_outputs._position` が負の `start` を Python の添字として受理。人がローカルで採点する出力の位置を過大に正解と評価し得る。API の認可迂回や文書の変更ではない | 本PRで修正。指定位置は `0 <= start < end <= len(text)` を必要とし、不正なら引用文を検索して実際の位置を返す |
| I-G3-001 | 情報 | ZAP 2.16.1 は古い版との警告。D-023 により動作が確認された固定版を使用 | 新版の評価は別タスク。診断成功と最新版利用を同一視しない |
| I-G3-002 | 情報 | ローカルHTTPのためSecure Cookie/TLSを公開環境相当には検証していない | 公開は本作業の対象外。`assessment` のヘッダ・開発用入口は実HTTPで確認 |
| I-G3-003 | 情報 | ZAPのJSONに4xx応答、キャッシュ可否、未ログイン側の認証要求検出の情報アラートあり。CLIのWARN/FAIL件数とは別 | キャッシュ可能とされたのは `/health`・`/ready` のみ。注入入力による4xxは拒否応答として記録。JSONの情報アラートを省略して「全アラート0」としない |
| I-G3-004 | 情報・誤検知 | 最終ログのgitleaks初回は34検出。絶対パスでの走査では既存 `.gitleaks.toml` の先頭固定の相対パス除外が一致しなかった | 値を表示せず該当行を分類：ローカルAPI URL30件・基底イメージの公開GPG鍵のID4件。既存の除外設定を変更せず `/repo` を作業ディレクトリにして相対パスで再検査、終了0・検出0。初回結果は保持 |

VA-G3-001 の再現：`_position(["abcdef"], {"page":1,"start":-3,"end":6,"quote":"def"})` が修正前 `(1,-3,6)`、修正後 `(1,3,6)`。前者は無関係な正解の0〜3とも重なり得る。

再発防止：`backend/tests/security/test_g3_scoring.py::test_negative_offsets_cannot_expand_evidence_into_unrelated_gold`。修正前の失敗を `regression/negative-offset-before.txt`、修正後を `regression/scoring-fixed.txt` に保存。過去のホールドアウト出力は人の実行スクリプトで削除する仕様であり、今回元出力を見ていないため既存集計への影響は不明（要確認）。集計の改変・再採点は行っていない。

## 3. コマンドと結果

コマンドはリポジトリ直下（backend / frontend と記載したものは各ディレクトリ）から実行。`.venv/Scripts/python.exe` 等は既存の仮想環境を使用。コンテナの `/repo` はこのリポジトリだけの読み取り専用マウント、`/out` は本報告配下のログ保存先である。ホールドアウト・他リポジトリのマウントなし。

| 検査 | 実行したコマンド | 終了・結果 | ログ |
|---|---|---|---|
| ruff S（0.17.1） | `backend/.venv/Scripts/ruff.exe check backend/app --select S --output-format json` | 0、検出0 | `sast/ruff-s.json` |
| bandit（1.9.4） | `backend/.venv/Scripts/python.exe -m bandit -r backend/app -f json -o .../sast/bandit.json` | 0、検出0。既存の除外設定は維持 | `sast/bandit.json` |
| semgrep（1.180.0） | `semgrep scan --config p/python --config p/owasp-top-ten --config p/react --config p/typescript --config p/secrets --json --output /out/semgrep.json --metrics off /repo/backend/app /repo/frontend/src` | **未完了**。通常・OSS・実験エンジン・同じ規則の一時ダウンロード後のローカル読み込みで再実行したが結果を得られず、各コンテナを停止（終了137）。検出0とはしない | `sast/semgrep-run.txt`、`sast/semgrep-oss-run.txt`、`sast/semgrep-native-run.txt`、`sast/semgrep-local-rules-run.txt` |
| pip-audit（2.10.1） | backend：`.venv/Scripts/python.exe -m pip_audit -f json -o ../reports/security/2026-10-21-g3/sca/pip-audit.json` | 0、既知の脆弱性0 | `sca/pip-audit.json`、`sca/pip-audit-run.txt` |
| npm audit | frontend：`npm audit --omit=dev --json` | 0、脆弱性0。dev依存は対象外 | `sca/npm-audit.json` |
| gitleaks（8.30.1）履歴 | `gitleaks git /repo --redact --config /repo/.gitleaks.toml --gitleaks-ignore-path /repo/.gitleaksignore --report-path /out/gitleaks-history.json` | 0、62コミット、秘密情報0（既存除外込み） | `secrets/gitleaks-history.json`、`secrets/history-run.txt` |
| gitleaks 作業ツリー | 同じ設定で `gitleaks dir /repo/<対象> --redact ...` | 7対象すべて0。`backend/app`・`frontend/src`・`scripts`・`experiment`・`fixtures/generator`・`contracts`・`docs`。`.env`・仮想環境・既存診断の応答を走査しない | `secrets/worktree-*.json`、`secrets/worktree-*.txt` |
| trivy（0.76.0）設定 | `trivy config --format json -o /out/trivy-config.json /repo/backend/Dockerfile` | 0、27項目成功、指摘0 | `container/trivy-config.json` |
| trivy イメージ | `trivy image --format json -o /out/trivy-image.json easf-backend:local`。API再構築後にも別ファイルへ再実行 | 初回0。再構築後の結果を併記 | `container/trivy-image*.json`、`container/image-identity.txt` |
| assessment 起動 | `EASF_DB_PORT=55433 docker compose --profile app up -d --build api`（PowerShellで環境変数設定） | 0、assessment API の構築・起動成功 | `dast/api-start.txt` |
| ZAP（2.16.1）未ログイン | `docker run --rm --network enterprise-ai-solution-factory_default -v <dast>:/zap/wrk:rw ghcr.io/zaproxy/zaproxy:2.16.1 zap-api-scan.py -t /zap/wrk/openapi.yaml -f openapi -J zap-api.json -I` | 再実行0、FAIL0・PASS114・WARN1（版の警告）。`-I` は警告による非ゼロ終了だけを抑制し、FAILを無視しない | `dast/zap-api-retest.txt`、`dast/zap-api.json` |
| ZAP 認証付き | 同じ固定イメージ、`-t /zap/wrk/openapi-auth.json -f openapi -J zap-api-auth.json -I -z '-configfile /zap/wrk/zap-auth.properties'` | Cookie・CSRF・Originを一時設定から付与、ログアウトを対象外にする。結果は下記の最終集計 | `dast/zap-api-auth-run.txt`、`dast/zap-api-auth.json` |
| 手動HTTP | `backend/.venv/Scripts/python.exe reports/security/2026-10-21-g3/manual_checks.py`（診断利用者・秘密は環境変数） | 再実行0。入口閉鎖・401・ヘッダ・CSRF・型偽装415・パス名・download一致・CORS・TRACEを確認 | `manual-retest.txt` |
| 契約 | `uv run --no-project --python 3.12 --with jsonschema --with pyyaml --with openapi-spec-validator python scripts/validate_contracts.py` | 0、schemas5・capabilities8・rule_packs2・workflows2・OpenAPI妥当、エンジンの業務名検査も成功 | `regression/contracts.txt` |
| skill 同期 | `backend/.venv/Scripts/python.exe scripts/sync_skills.py --check` | 0、ずれなし | `regression/skills.txt` |
| フロントエンド回帰 | frontend：`npm run lint`、`npm run typecheck`、`npm run build`、`npx vitest run` | 各0、vitest3ファイル10件成功 | `regression/frontend-*.txt`、`regression/vitest.txt` |
| 採点・評価回帰 | backend：`.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/security/test_g3_scoring.py tests/unit/test_score_outputs.py tests/unit/test_offline_evaluation.py` | 0、9 passed・1 skipped（WindowsにTesseractなし） | `regression/scoring-fixed.txt` |
| Linux全件回帰 | 次節のDocker手順で `uv sync --locked && uv run pytest -q` | **終了1：282 passed・1 error（1551.16秒）**。下記のセットアップエラー | `regression/pytest-linux-retest.txt` |
| 失敗した認可試験だけの再実行 | 同じLinux環境とテスト専用DBで `uv run pytest -q 'tests/contract/test_openapi_contract.py::test_authorization_matrix[listCapabilities]'` | 0、1 passed（17.50秒）。再現せず。全件実行の失敗は取り消さない | `regression/contract-isolated.txt` |
| 型・規約・整形 | backend：`.venv/Scripts/python.exe -m mypy app/evaluation tests/security/test_g3_scoring.py`、ruff check / format --check | 最終はいずれも0。mypyは4ファイル問題なし | `regression/mypy.txt`、`sast/ruff-final.txt` |
| 集計の独立照合 | `backend/.venv/Scripts/python.exe reports/security/2026-10-21-g3/review_checks.py` | 0、丸め値・混同行列の件数・非劣性の余裕を確認 | `review-checks.txt` |

### Linux 全件回帰の手順

`ghcr.io/astral-sh/uv:python3.12-bookworm-slim` を Compose のネットワークで起動し、環境変数名 `EASF_TEST_DATABASE_URL` と `EASF_TEST_MIGRATION_DATABASE_URL` で既存のテスト用接続を渡した（値は報告しない）。接続先を `db:5432/easf_test` に変更。開発用DBの初期化は行っていない。

```sh
set -e
mkdir /app
cd /repo
tar --exclude=backend/.venv --exclude=backend/.pytest_cache --exclude='*/__pycache__' \
  -cf - backend fixtures contracts experiment docker-compose.yml | tar -xf - -C /app
apt-get update -qq
apt-get install -y -qq tesseract-ocr tesseract-ocr-jpn >/dev/null
cd /app/backend
uv sync --locked && uv run pytest -q
```

### 初回失敗・環境による制約

- Git fetchとDockerは初回サンドボックスの権限で失敗し、必要な権限で成功した。Docker Desktopの再起動、他プロジェクトのコンテナの停止は行っていない。
- 採点の独立テスト初回は一時ディレクトリの権限で1 passed・2 errors（終了1）。再実行3 passed（終了0）。その後、実装不備の再現テストを足し、修正前1 failed（終了1）→修正後の対象回帰成功。ログを削除せず保持。
- Linux初回は `experiment/` をコピー対象に含めなかったため `contract_scoring.json` が無く、収集失敗（終了2）。上記の手順へ直して再実行した。製品の不具合として数えない。
- ZAP初回は契約の相対サーバURLでOpenAPIインポート失敗。契約の写しの `servers` だけを `http://api:8000` にして再実行。凍結された `contracts/` は変更なし。
- 診断アカウントの初回準備は実行イメージに `uv` が無く失敗（終了1）、手動チェックは401で停止。ランタイムのPython CLIを使用する手順へ変更した。
- 自動承認レビューは「検査失敗時に管理者が残る」「作成失敗時に同名の既存利用者を無効化し得る」という2点で中間の実行案を拒否した。UUIDの新規IDを用い、作成成功時だけ `finally` で無効化する手順へ修正して実行した。秘密は一時ディレクトリにのみ置き、終了時にその絶対パスがTEMP配下かを確認して削除する。
- 修正後の整形検査で一度差分を検出（終了1）。許可された評価ファイルだけをruffで整形し、最終検査を記録する。
- Linux全件回帰のエラーは `test_authorization_matrix[listCapabilities]` の `world` fixture（`tests/contract/test_openapi_contract.py:348`）。実行後の確認タスクに対象runが無く `next(...)` が `StopIteration`。認可試験本体は未実行。単独再実行は成功したが、負荷・時間切れなどの原因は不明（要確認）であり、環境原因と断定しない。許可パス外のテスト・Executorは変更していない。
- 失敗時のpytestのローカル変数にDB接続URIが出たため、`redact_logs.py` でパスワードを `[REDACTED]` に置換した。秘匿化したログだけを提出する。再現手順で接続値・秘密値を標準出力へ出さない。
- semgrepは元の通常実行、`--oss-only --jobs 2 --timeout 30`、さらに `--experimental --x-parmap` でも結果ファイルが生成されなかった。公式の5規則のURLへの疎通は確認できたため、wgetでコンテナ内の `/tmp/rules` に同じ規則を取得し `--config /tmp/rules` でも試したが、`Loading rules from local config...` から進まず停止した。原因は不明（要確認）。規則ファイルはコミットせず、コンテナ削除で破棄。EASF・Docker Desktop・他案件のコードや環境の変更で回避していない。
- 提出するログの加工は、接続URIと一時認証値の秘匿化、および行末空白・改行の正規化だけ。検査結果・初回失敗・誤検知を削除して成功に見せていない。

## 4. 手動の診断項目と未実行

全チェックリストIDの扱いは [manual.md](manual.md) を参照。実HTTP・ソース確認・自動回帰を分ける。自動回帰を人の手動診断として数えない。

未実行：実画面での契約書の一連の確認・修正と画面DAST、実LLM／外部接続（保留）、ホールドアウトの再実行（禁止）、ベースライン実装のレビュー（禁止）、公開環境のTLS（対象外）。追加のライセンス全件調査・osv-scannerは今回未実行（引き渡しのG2同等ツール群を優先し、既存依存のSCAを実行）。

## 5. 費用と受け渡し

追加現金支出0円、有料APIなし。人の時間は未測定。AIの処理時間を人の時間に換算しない。`HUMAN_TIME_LOG.csv`・`COST_LEDGER.csv` は許可された変更パス外なので更新していない。PRを提出し、マージとG3判定は行わない。

## 6. 最終集計

| 区分 | 結果 |
|---|---|
| 製品の新規セキュリティ指摘 | 高0・中0・低1（VA-G3-001、修正済み）。情報4（うち既知の誤検知・道具の版警告を含む） |
| SCA・コンテナ | pip-audit / npm auditの既知脆弱性0、再構築したAPIのtrivyは脆弱性・秘密情報0、Dockerfile指摘0 |
| 秘密情報 | 履歴0、ソース0。追加ログの初回34件は誤検知を分類し、相対パス再検査0。pytestのURIは提出前に秘匿化 |
| DAST | 未ログイン・認証付きとも終了0、FAIL0・PASS114、WARN1（ZAPの版）。JSONの情報アラートも§2に記録。認証後projectsの200を18応答確認、HTTP5xx0。診断用利用者を無効化し一時秘密を削除、今回起動したAPIを停止 |
| フロントエンド | lint・typecheck・build・vitestすべて終了0、10テスト成功 |
| バックエンド | 全件282成功・1セットアップエラー（終了1）、当該1件の単独再実行成功。修正後の採点・評価は9成功・1スキップ。全件成功とはしない |
| 契約・凍結 | 契約検査・skill同期とも終了0。`git diff --exit-code 71abf10 -- contracts backend/migrations backend/app/{catalog,composer,executor,adapters,capabilities} fixtures/workflows/contract-v3.json fixtures/rule_packs/contract-1.1.0.json` の差分なし（`freeze-check.txt`） |
| semgrep | 未完了。4つの起動方法で結果ファイルを得られず停止（各137）。SASTを全ツールで完了したとはしない |

**ゲート条件の無条件充足は宣言しない。** semgrepが未完了、回帰全件実行に1エラーが残り、独立レビューには不変の版と実装の結び付き・再利用証跡の範囲・過去の採点値への影響の残事項がある。CCが本PRとG3草稿を統合し、人がG3を判定する。最終コミットのCIは本報告執筆時は未実行（push前）であり、ローカル実行と取り違えない。
