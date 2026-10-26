# 引き継ぎ（次のセッションへ）

| 項目 | 内容 |
|---|---|
| 更新日 | 2026-10-26 |
| 書いた人 | Claude Code（初稿）、Codex（人の指示でG3承認・現在地を更新） |
| main の最新 | P5-03eのイメージ診断まで統合済み（a0fe780）、全件CI成功。P5-03fの専用HTTP診断は本変更 |

新しいセッションは、まずこの文書、`AGENTS.md`、`TASK_STATUS.md`、`DECISIONS.md` の最後の数行を読む。

## 1. 現在地

- **G3承認済み（D-051）、Phase 5の準備。** P4-06の成果物まで統合済み。ベースラインAは別リポジトリ・別セッションで先に実施（D-042・D-046）。主要指標M1は推定のため判定に使わない（D-050）。
- 完了：P3-00、P3-02a、P3-01a（文書の API）、P3-01b（解析・抽出・検証、D-030）、P3-01c（ローカル MCP の根拠・出力、D-031）、P3-01d（請求書の端から端まで・画面）、P3-03 の一部（dev の評価・G2 前の診断・報告、D-032）。
- **現在**：人の明示的なマージ指示でCodexがP4-06をmainへ統合し、CI成功を確認。その後、本会話で人がG3を承認し継続を指示（記録日2026-10-23）。`reports/gate_G3.md` に診断・レビューと残事項を反映。元の集計ではM3の非劣性を満たすが、採点修正後の再評価は未実行。
- **P5-03a**：semgrepの最小1規則・1入力は完了（意図した1件、errors 0）。公式5規則集の製品検査は180秒で終了コード143、結果JSONなし。規則読込・解析への進行は確認したが、根本原因は不明、製品診断は未完了。`reports/security/2026-10-23-g4/report.md`、許可範囲は `handoffs/P5-03a.md`。
- **P5-03a2（補完）**：入力をコンテナ内へコピーし5規則集を個別実行、すべてexit 0・指摘0・errors 0。追跡する製品ソース98ファイルと対象集合が一致。Python・OWASPに同一箇所のテイント解析timeout警告が各1件残る。OWASP規則だけ前回から更新あり。根本原因・解析制約は未解消。`reports/security/2026-10-23-g4/semgrep-followup/report.md` を最新結果とし、前回の失敗は保持。
- **P5-03b**：依存一覧（Python94・Node486ロック項目）と既存イメージのapk78項目、第三者資産・安全境界を点検。`reports/security_review.md` に5観点の結論。配布表示・内包依存・一部来歴・ログ秘匿化・保持と削除は要確認。製品修正やG4合格の証拠ではない。
- **P5-03c / SR-01**：実ミドルウェアの通常・連鎖・SQLAlchemy例外で、合成値のログ混入3/3を確認（診断exit 1）。HTTP混入0/3。修正案を隔離コピーに適用した同じ3ケースはexit 0、型・応答trace_id・復元も保持。暫定中のVA-G4-001として、共有処理への明示承認待ちで製品は未修正。`reports/security/2026-10-23-g4/error-log/report.md` と `proposed-fix.patch`。別タスク・G4判定へは進めない。
- **P5-03d（上記の対応）**：適用確認への継続指示を受領（D-052）し、提示済み差分を共通ミドルウェアへ反映。本体の3ケースは修正前3失敗→修正後3成功。例外値をログへ渡さず、型・trace_idで追跡。VA-G4-001は確認範囲で対応済み。過去の「適用承認待ち」は解消したが、全ログ・保持・来歴・他のG4残事項を解消したことにはしない。`reports/security/2026-10-23-g4/error-log-fix/report.md`。
- **P5-02a**：既存評価7集計の索引と契約書比較表16セルの照合を実施。旧集計上の4条件は成立するが、採点修正後の再評価ではない。M1未判定・M6未算出を維持。`reports/evaluation_index.md`、`reports/review/2026-10-23-g4-readiness.md` に証拠と不足・担当を整理。G4の正式報告・承認は代行しない。
- **次**：Phase 5計画に沿い、診断の不足とレビューの残事項を個別範囲で進める。承認を指摘解消として数えない。ホールドアウトの文書・ラベルとベースラインのコードを開かない。D-047の評価済みの構成をそのまま変更せず、必要な修正は新しい版・変更要求として扱う。次のゲートの人間承認、実LLM利用、外部公開は別に扱う。

| ゲート | 状態 | 報告 |
|---|---|---|
| G0 | 承認（D-014） | `reports/gate_G0.md` |
| G1a | 承認（D-024） | `reports/gate_G1a.md` |
| G1b | 承認（D-027） | `reports/gate_G1b.md` |
| G2 | 承認（D-037） | `reports/gate_G2.md` |
| G3 | 承認（D-051、残事項を継続管理） | `reports/gate_G3.md` |

- **P5-03e**：別タグで修正後イメージをビルドし、UID 10001・実装SHA一致・合成例外3ケース成功を確認。初回Trivyはmusl系2パッケージの同一CVEでexit 1、キャッシュなし再ビルドでr3へ更新後はOS・Pythonとも0件、exit 0。認証前ASGI7経路成功。HTTP/認証後DAST・DBは未実行。旧タグと既存DBは変更なし。`reports/security/2026-10-23-g4/runtime/report.md`。G4の証拠不足・他の残事項は維持。

- **P5-03f**：専用の使い捨て `_test` DBと修正後APIで、認証・CSRF・他利用者の案件/文書拒否・dev PDF登録/取得等のHTTP24項目成功、exit 0。初回3失敗も保持。2ユーザーの無効化・専用資源の削除・既存コンテナID維持を確認。全面ZAP・実画面・業務実行・保持削除は未実行。`reports/security/2026-10-26-g4/http/report.md`。自己診断であり第三者診断ではない。G4の証拠不足と他の残事項は維持。

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

**できているものの補足**：請求書・契約書のホールドアウトの評価（人が実行、AIは集計値だけ）、Tesseract OCR（由来の根拠は未確認）、契約書のWorkflow v3・Rule pack contract@1.1.0、両arm共通の採点、G3前の自己診断・独立レビュー。

**まだないもの**：評価・再利用のAPI、実LLM（D-004で保留）、Workflowの作成・編集の画面、ワーカーのコンテナ。G3の承認はこれらの実装・公開の承認を兼ねない。

## 3. 環境（Windows 11・Git Bash・Docker Desktop）

手順の正本は `docs/design/dev_setup.md`。ここは引っかかりやすい点だけ。

- `.env`（リポジトリ直下、コミットしない）に DB・秘密鍵・テスト用 DB の URL がある。シェルでは `set -a && . ./.env && set +a`。相対パスで読めないことがあるので、`backend/` からは `. ../.env`。
- 契約の検査（CI の contracts-and-skills と同じ）は、backend の依存に `openapi-spec-validator` がないため `uv run --no-project --python 3.12 --with jsonschema --with pyyaml --with openapi-spec-validator python scripts/validate_contracts.py` で動かす。skill のずれは `python scripts/sync_skills.py --check`。
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

1. **Phase 5の移行準備**は `docs/phase5/PHASE5_PLAN.md`。次はP5-03aの診断対象・停止条件・許可パスの引き渡しを具体化する。追加診断・製品変更はまだ行っていない。ベースライン・Factoryのホールドアウト評価を初めから繰り返さず、M1はD-050のまま判定不能として扱う。
2. **G3の残事項**：semgrep未完了、ローカル全件回帰1セットアップエラー（単独再実行・CIは成功）、契約書の実画面確認未実行、RV-G3-001〜003。詳細は `reports/gate_G3.md` §5 と独立レビュー。担当・対応方針は次の計画で具体化する。
3. 契約書・請求書のホールドアウトは評価済み。版を変えて再評価するなら新しいホールドアウトと人の別途判断が要る。AIは元データ・ラベルを開かず、評価済みの集計値を変更しない。
4. エンジンのコードは変えず、Workflow の設定・Rule pack・field_spec で表すのが原則（`easf-capability-contract`）。変えたら再利用の分類 `new_code` として記録する。
5. 気になっている小さなこと：Windows で全テストが遅い・時間切れになる、実装キーが版に結び付かない（D-043）、ワーカーのコンテナ化。

業務名（請求書・契約書など）をエンジン（catalog・composer・executor・adapters・evaluation）に書かない（`scripts/validate_contracts.py` が検出する）。

## 6. 既知の問題

- G3の独立レビューはCodexが実施済み。指摘の全件解消とCCによる追加確認の記録はない（`reports/review/2026-10-21-g3.md`）。
- semgrep未完了。ローカルLinux全件は282成功・1セットアップエラー、当該1件の再実行とd97a556のCIは成功。原因は不明（要確認）。
- OCR は Tesseract（コンテナ・CI）。この Windows には無く、OCR のテストは飛ばされる。コンテナ（Alpine 5.5.2）と CI（Ubuntu 5.3.0）で Tesseract の版と出力が違う。子プロセスのメモリ上限は POSIX だけ。
- バックエンドのテストが遅い（Windows の spawn、全件で Linux 25 分）。
- 画面：Workflow の作成・編集の画面なし、確認の決定後に修正の内容を表示できない（契約 v1）、実行・確認・文書の E2E は模擬 API。
- 人の作業時間はすべて推定か未測定（D-042・D-045・D-046）。M1 は G3 の成否に使わず、後で別の業務で測り直す（D-050）。
