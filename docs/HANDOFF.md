# 引き継ぎ（次のセッションへ）

| 項目 | 内容 |
|---|---|
| 更新日 | 2026-10-19 |
| 書いた人 | Claude Code（統合責任者） |
| main の最新 | P3-04（OCR・凍結・dev v3・ホールドアウトの評価の道具）まで。各タスクは CI の成功を確かめてから main に入れた |

新しいセッションは、まずこの文書、`AGENTS.md`、`TASK_STATUS.md`、`DECISIONS.md` の最後の数行を読む。

## 1. 現在地

- **Phase 3（G2、請求書の POC）は完了し、G2 の人の承認待ち。** 報告は `reports/gate_G2.md`（自己判定 **PASS**。ホールドアウト 12 件で ADR-007 の必須の閾値をすべて満たした、`reports/eval/holdout/report.md`）。
- 完了：P3-00、P3-02a、P3-01a（文書の API）、P3-01b（解析・抽出・検証、D-030）、P3-01c（ローカル MCP の根拠・出力、D-031）、P3-01d（請求書の端から端まで・画面）、P3-03 の一部（dev の評価・G2 前の診断・報告、D-032）。
- **人の作業待ち**：G2 の承認（`reports/gate_G2.md`）。ホールドアウトは凍結・評価済み（D-035・D-036、評価は 1 回）。人の作業時間の記録は後で決める（D-033）。
- **止まる地点**：G2 の承認前に Phase 4（契約書）のコードを書かない。dev の結果を見た抽出の調整は、ホールドアウトの凍結を人に確かめてから。

| ゲート | 状態 | 報告 |
|---|---|---|
| G0 | 承認（D-014） | `reports/gate_G0.md` |
| G1a | 承認（D-024） | `reports/gate_G1a.md` |
| G1b | 承認（D-027） | `reports/gate_G1b.md` |
| G2 | 人の承認待ち（自己判定 PASS） | `reports/gate_G2.md` |

## 2. できているもの

| 部分 | 中身 | 主なパス |
|---|---|---|
| 認証・案件 | ログイン（Cookie・CSRF・ロック）、案件・メンバー・要件の版と承認、利用者は CLI で作る | `backend/app/{auth,project}`、`backend/app/admin.py` |
| Catalog | Capability・Rule pack の不変の版（RFC 8785 のハッシュ、DB トリガー）、実装の許可リスト | `backend/app/catalog/` |
| Composer | Workflow の静的検証 13 種、Solution の API（ETag・承認・凍結） | `backend/app/composer/`、`backend/app/api/solutions.py` |
| Executor | Run の状態機械、DB をキューにしたワーカー（`python -m app.executor.worker`）、再試行・予算・異常終了からの回復、local は子プロセス、LLM は mock だけ、人の確認、ハッシュ連鎖のトレース | `backend/app/executor/`、`backend/app/adapters/` |
| 文書 | 登録・一覧・ダウンロード。形式（拡張子・宣言の型・先頭のバイト）・10 MB・30 ページ・暗号化・JavaScript・添付・画素数を子プロセスで確認。保存は `EASF_STORAGE_DIR`（UUID の名前） | `backend/app/{api/documents.py,documents/}`、`docs/design/detail/documents.md` |
| 業務の Capability | `document_parser.v1`・`rule_based_extractor.v1`（見出しは設定）・`structured_extractor.v1`（mock）・`rule_validator.v1`（3 値）・`easf_local_mcp:locate_evidence`（自作のローカル MCP サーバ、stdio）・`result_exporter.v1`。ワーカー側で文書・Rule pack を読んで子プロセスへ。`project_context` | `backend/app/capabilities/`、`backend/app/adapters/{resources,mcp}.py`、`backend/app/mcp_server.py`、`docs/design/detail/capabilities.md` |
| 出力 | `exportRunResult`（JSON・CSV。CSV インジェクション対策、保存した出力から再生成して export_id を照合） | `backend/app/api/runs.py`、`docs/design/detail/exports_and_events.md` |
| 請求書の Workflow | 設定だけ（`fixtures/workflows/invoice-v2.json`）。本番の部品で端から端まで動く | `backend/tests/integration/test_invoice_workflow.py` |
| 評価 | `python -m app.evaluation.offline`（dev だけ。ホールドアウトのラベルは無いので止まる）。dev の結果は `reports/eval/2026-10-19-dev/` | `backend/app/evaluation/`、`docs/design/detail/rules_and_metrics.md` |
| 画面 | ログイン・案件（文書・要件・解決策・実行）・実行モニター（CSV／JSON の出力）・確認タスク・確認・能力カタログ。見た目は sales-assistant の UI に合わせ、配色は EASF の青緑系（D-026） | `frontend/src/` |
| 契約 | v1 を凍結、現在 1.0.2（D-022・D-025）。変えるときは版を上げ、DECISIONS に書く | `contracts/` |
| 診断 | G1a 前・G1b 前・G2 前の自己診断（指摘はすべて対応済み。G2 前は VA-G2-001 中を修正） | `reports/security/` |
| 合成データ（請求書） | 生成器（計画 → レコード → PDF・スキャン PNG・正解ラベル）、dev 28 件、manifest、Rule pack `invoice@1.1.0`。根拠の位置は `backend/app/capabilities/pdf_text.py`（解析と同じ関数）の文字の番号。ホールドアウトは人が生成（`fixtures/HOLDOUT.md`） | `fixtures/`、`backend/tests/fixtures/` |

**まだないもの**：ホールドアウトとその評価、OCR（スキャン画像は missing → 人の確認、D-030）、評価・再利用の API、実 LLM（D-004 で保留）、契約書の業務（Phase 4）、Workflow の作成・編集の画面、ワーカーのコンテナ。

## 3. 環境（Windows 11・Git Bash・Docker Desktop）

手順の正本は `docs/design/dev_setup.md`。ここは引っかかりやすい点だけ。

- `.env`（リポジトリ直下、コミットしない）に DB・秘密鍵・テスト用 DB の URL がある。シェルでは `set -a && . ./.env && set +a`。相対パスで読めないことがあるので、`backend/` からは `. ../.env`。
- **テストは `easf_test` だけを使う**（`EASF_TEST_DATABASE_URL`・`EASF_TEST_MIGRATION_DATABASE_URL`。DB 名が `_test` で終わらないと止まる）。開発用の `easf` のデータは消えない。
- バックエンドの全テストは 7〜8 分（Windows の子プロセスの起動が遅い）。`timeout` を長めに。
- 開発用 DB には管理者が 2 人いる（`admin`、`e2e_admin_184037`）。**パスワードはリポジトリにない**。E2E や画面の確認には、自分で利用者を作る：`cd backend && EASF_NEW_USER_PASSWORD=… uv run python -m app.admin create-user --login-id … --display-name … --admin`。作った ID とパスワードは一時フォルダに置き、コミットしない。
- E2E：バックエンド（`uv run uvicorn app.main:create_app --factory --port 8000 --no-server-header`）と `npm run dev` を起動し、`E2E_LOGIN_ID`・`E2E_PASSWORD` を渡して `npx playwright test`。`e2e/runs.spec.ts` は API を模擬するのでバックエンド不要。
- 診断の道具は Docker で動かす。**ZAP は `ghcr.io/zaproxy/zaproxy:2.16.1` に固定**（この端末の `stable` イメージは壊れている、D-023）。診断用のコンテナは `docker compose --profile app up -d api`（127.0.0.1:8001、`EASF_ENV=assessment`）。
- Docker Desktop が応答しなくなることがある（`docker info` が返らない）。ほかのプロジェクトのコンテナもあるので、勝手に再起動せず人に頼む。
- **Bash からヒアドキュメントで Python を書くと、`\\` が `\` 1 つになる**。`D:\aidd` が BEL 文字に、`\u0000` が NUL バイトになった実例がある。反斜線を含む編集は Write / Edit ツールで行い、編集後に制御文字（`\x00-\x08\x0b\x0c\x0e-\x1f`）がないか確かめる。
- Bash 上の curl で日本語の JSON を送ると Shift-JIS になり 400 になる。手動の確認では ASCII を使う。
- **合成データは Windows と Linux（CI）で同じバイト列になる必要がある**（manifest のハッシュ）。生成器を変えたら `PYTHONPATH=backend uv run --project backend python -m fixtures.generator dev` で作り直し、生成器のテストを両方で通す。Linux での確認は Docker で行える（`ghcr.io/astral-sh/uv:python3.12-bookworm-slim` に `backend`・`fixtures`・`contracts` だけを tar でコピーし、`uv sync --locked` → `uv run pytest tests/fixtures`。`node_modules` を含めると遅い）。字体を埋め込まない・PNG を zlib で圧縮すると環境でずれる（D-029）。
- ホールドアウトの文書・ラベルを開かない・生成しない（`easf-eval-integrity`）。リポジトリには `fixtures/manifest.holdout.json`（ハッシュだけ）が人の手で入る。
- **2026-10-19 の作業開始時、EASF の DB コンテナ・ボリューム、診断用のイメージ、`frontend/node_modules`、`backend/.venv` が見当たらなかった**（原因は不明）。DB は作り直し、**55432 番はほかのプロジェクト（ocr-saas）が使っているので `EASF_DB_PORT=55433`**。`.env` は 55432 のまま（変えていない）。シェルでは `.env` の CR を除き、URL の 55432 を 55433 に置き換えて読む（例：`tr -d '\r' < .env | sed 's/:55432\//:55433\//' > <一時フォルダ>/env.sh` に `export EASF_DB_PORT=55433` を足して `set -a; . env.sh; set +a`）。`.env` は CRLF。
- 開発用 DB は空から作り直した。管理者は診断用の `assess_admin` だけ（パスワードはリポジトリ外。忘れたら CLI で別の利用者を作る）。
- **5173 番は sales-assistant の Vite が使っていることがある**。EASF は `npx vite --port 5174 --strictPort`、Playwright は `E2E_BASE_URL=http://localhost:5174`。
- **この端末は CPU の負荷が高いことがある**（90% 前後、ほかのプロジェクト）。Windows で全テストを流すと、試験用の Capability の子プロセスの起動が間に合わず `timeout` で落ちる（コードの問題ではない）。全件の確認は Linux（Docker）か CI で：`backend`・`fixtures`・`contracts`・`docker-compose.yml` を `tar --force-local` で固め、`ghcr.io/astral-sh/uv:python3.12-bookworm-slim` を `--network enterprise-ai-solution-factory_default` で起動し、`EASF_TEST_DATABASE_URL` を `db:5432/easf_test` にして `uv sync --locked && uv run pytest`（25 分）。
- **後ろで動かした pytest を TaskStop で止めても、Windows では子の python が残る**。残ると同じ `easf_test` を取り合ってエラーになる。PowerShell で `Get-CimInstance Win32_Process` から EASF の python を探して止める。
- CI のログは GitHub の認証が必要で読めない（`wait_ci.sh` は失敗した段の名前だけ出す）。失敗の中身は Linux の Docker で再現して調べる。
- 依存を足すときは `uvx --from uv==0.6.17 uv lock`（この端末の uv 0.10 はロックファイルの書式を全部書き換える）。`mcp` が `httpx2` を連れてくるため、テストの HTTP クライアントは `httpx2`（D-031）。
- 診断の道具（Docker）：semgrep 1.180.0 は負荷が高いと結果を書いた後に終わらないことがある（50 分で止めた）。gitleaks は `--config /repo/.gitleaks.toml --gitleaks-ignore-path /repo/.gitleaksignore` を必ず付ける（コンテナの作業ディレクトリが違うと読まれない）。ZAP のイメージは取得の途中で切れることがある（`docker pull` をやり直し、`/zap/lib` に 0 バイトのファイルが無いか確かめる、D-023）。
- 診断用の API コンテナ（`docker compose --profile app up -d api`）は読み取り専用。`/tmp` は tmpfs（VA-G2-001）。
- Bash の命令で、標準入力を待つもの（例：引数なしの `cat >`）を書くと、終わらずに何時間も止まる。後ろで動かす命令は最初に `timeout` を付ける。

## 4. 進め方（このプロジェクトの約束）

- タスクごとに `cc/<task>-<slug>` ブランチ → コミット → プッシュ → **CI の成功を確かめてから** `main` へ fast-forward → プッシュ（D-013、G1a §8-2）。CI の待ち合わせは `sh scripts/wait_ci.sh $(git rev-parse HEAD)`（`gh` はこの端末にない。公開リポジトリなので API で見られる）。
- 画面・API・権限・入力チェックを変えたら、同じコミットで設計書を直す（`spec-sync`）。画面は `ui-design`、コードは `jp-secure-coding`、Capability・Workflow は `easf-capability-contract` を先に読む。
- 報告・設計書・コミットは日本語。**人とのやり取りは中国語**（利用者の希望）。中国語の文言をリポジトリに入れない。
- 実行していないものは「未実行」と書く。測っていない数値を書かない。模擬は模擬と書く。
- 契約（`contracts/`）を変える必要が出たら止まるのが原則。エラー応答の追記のような後方互換の修正は、版を上げて DECISIONS に書き、報告で知らせた前例がある（D-022・D-025）。

## 5. 次にやること

1. G2 の承認を待つ。承認されたら DECISIONS に記録する。
2. ホールドアウトはもう評価に使った。版を変えて再び評価するなら新しいホールドアウトが要る（easf-eval-integrity §2）。
3. G2 の承認後に Phase 4（契約書）の計画（P4-00）。エンジンのコードは変えず、Workflow の設定・Rule pack・field_spec で表すのが原則（`easf-capability-contract`）。
4. 気になっている小さなこと：Windows で全テストが遅い・時間切れになる（子プロセスの再利用を ADR で検討）、実行の文書の選択が 200 件まで、ワーカーのコンテナ化。

業務名（請求書・契約書など）をエンジン（catalog・composer・executor・adapters・evaluation）に書かない（`scripts/validate_contracts.py` が検出する）。

## 6. 既知の問題

- 独立レビューなし（D-024）。
- ホールドアウトが未生成・未凍結（G2 の AC-08 が未完了）。
- OCR は Tesseract（コンテナ・CI）。この Windows には無く、OCR のテストは飛ばされる。コンテナ（Alpine 5.5.2）と CI（Ubuntu 5.3.0）で Tesseract の版と出力が違う。子プロセスのメモリ上限は POSIX だけ。
- バックエンドのテストが遅い（Windows の spawn、全件で Linux 25 分）。
- 画面：Workflow の作成・編集の画面なし、確認の決定後に修正の内容を表示できない（契約 v1）、実行・確認・文書の E2E は模擬 API。
- 人の作業時間が未記録。
