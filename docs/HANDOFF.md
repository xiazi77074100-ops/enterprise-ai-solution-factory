# 引き継ぎ（次のセッションへ）

| 項目 | 内容 |
|---|---|
| 更新日 | 2026-10-19 |
| 書いた人 | Claude Code（統合責任者） |
| main の最新 | P3-02a まで（`e80e8be` の次の台帳更新。CI 成功） |

新しいセッションは、まずこの文書、`AGENTS.md`、`TASK_STATUS.md`、`DECISIONS.md` の最後の数行を読む。

## 1. 現在地

- **Phase 3（G2、請求書の POC）の途中。** 計画は `docs/phase3/PHASE3_PLAN.md`（タスクは §4）。G1b は承認済み（D-027）。
- 完了：P3-00（計画、D-027・D-028）、P3-02a（請求書の合成データの生成器・dev 28 件・manifest・Rule pack `invoice@1.1.0`、D-029）。
- **次にやること：P3-01a 文書の API**（アップロード・一覧・ダウンロード。`contracts/openapi.yaml` の `uploadDocument`・`listDocuments`・`downloadDocument`、`jp-secure-coding` の upload-and-files.md）。そのあと P3-01b〜d、P3-03（§5）。
- **人の作業待ち**：ホールドアウト 12 件の生成と凍結（`fixtures/HOLDOUT.md`。AI は実行しない・見ない）。**凍結は抽出・ルールの調整（P3-01b 以降で dev の結果を見て直すこと）より前**に行う（fixture_plan §7-5）。P3-01a は調整を含まないので、凍結の前に進めてよい。P3-01b で dev の結果を見て抽出を直す前に、凍結が済んでいるか人に確かめる。
- 人に返事をもらっていない事項：`HUMAN_TIME_LOG.csv`（人の作業時間）の記入（任意）。

| ゲート | 状態 | 報告 |
|---|---|---|
| G0 | 承認（D-014） | `reports/gate_G0.md` |
| G1a | 承認（D-024） | `reports/gate_G1a.md` |
| G1b | 承認（D-027） | `reports/gate_G1b.md` |
| G2 | Phase 3 の途中 | — |

## 2. できているもの

| 部分 | 中身 | 主なパス |
|---|---|---|
| 認証・案件 | ログイン（Cookie・CSRF・ロック）、案件・メンバー・要件の版と承認、利用者は CLI で作る | `backend/app/{auth,project}`、`backend/app/admin.py` |
| Catalog | Capability・Rule pack の不変の版（RFC 8785 のハッシュ、DB トリガー）、実装の許可リスト | `backend/app/catalog/` |
| Composer | Workflow の静的検証 13 種、Solution の API（ETag・承認・凍結） | `backend/app/composer/`、`backend/app/api/solutions.py` |
| Executor | Run の状態機械、DB をキューにしたワーカー（`python -m app.executor.worker`）、再試行・予算・異常終了からの回復、local は子プロセス、LLM は mock だけ、人の確認、ハッシュ連鎖のトレース | `backend/app/executor/`、`backend/app/adapters/` |
| 画面 | ログイン・案件・要件・解決策・実行モニター・確認タスク・確認・能力カタログ。見た目は sales-assistant の UI に合わせ、配色は EASF の青緑系（D-026） | `frontend/src/` |
| 契約 | v1 を凍結、現在 1.0.2（D-022・D-025）。変えるときは版を上げ、DECISIONS に書く | `contracts/` |
| 診断 | G1a 前・G1b 前の自己診断（指摘はすべて対応済み） | `reports/security/` |
| 合成データ（請求書） | 生成器（計画 → レコード → PDF・スキャン PNG・正解ラベル）、dev 28 件、manifest、Rule pack `invoice@1.1.0`。根拠の位置は `backend/app/capabilities/pdf_text.py`（解析と同じ関数）の文字の番号。ホールドアウトは人が生成（`fixtures/HOLDOUT.md`） | `fixtures/`、`backend/tests/fixtures/` |

**まだないもの**：文書のアップロード・解析・抽出・ルール・根拠・出力（`exportRunResult`）、評価、再利用、実 LLM（D-004 で保留）、契約書の業務（Phase 4）。本番の許可リストで実行できる業務の Capability はまだない（`backend/app/executor/handlers.py` は空。人の確認だけ Executor が扱う）。

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
- Bash の命令で、標準入力を待つもの（例：引数なしの `cat >`）を書くと、終わらずに何時間も止まる。後ろで動かす命令は最初に `timeout` を付ける。

## 4. 進め方（このプロジェクトの約束）

- タスクごとに `cc/<task>-<slug>` ブランチ → コミット → プッシュ → **CI の成功を確かめてから** `main` へ fast-forward → プッシュ（D-013、G1a §8-2）。CI の待ち合わせは `sh scripts/wait_ci.sh $(git rev-parse HEAD)`（`gh` はこの端末にない。公開リポジトリなので API で見られる）。
- 画面・API・権限・入力チェックを変えたら、同じコミットで設計書を直す（`spec-sync`）。画面は `ui-design`、コードは `jp-secure-coding`、Capability・Workflow は `easf-capability-contract` を先に読む。
- 報告・設計書・コミットは日本語。**人とのやり取りは中国語**（利用者の希望）。中国語の文言をリポジトリに入れない。
- 実行していないものは「未実行」と書く。測っていない数値を書かない。模擬は模擬と書く。
- 契約（`contracts/`）を変える必要が出たら止まるのが原則。エラー応答の追記のような後方互換の修正は、版を上げて DECISIONS に書き、報告で知らせた前例がある（D-022・D-025）。

## 5. 次にやること（Phase 3 の残り。順に）

1. **P3-01a 文書の API**：PDF・PNG・JPEG だけ（拡張子・宣言の型・先頭のバイトが一致）、10 MB・30 ページまで、サーバが作る UUID の名前で保存（公開しない場所、`EASF_STORAGE_DIR` などを設定に追加）、ダウンロードは `Content-Disposition: attachment`（RFC 5987）・`nosniff`・`no-store`。`documents` の表のマイグレーション（0006）、契約テストの PENDING から外し認可の全件表に追加、否定テスト（形式の偽装・サイズ・ページ数・ファイル名・他案件）。`startRun` の `document_ref` の入力を受け付けるようにする（同じ案件の文書だけ。今は 422 で拒否している）。
2. **P3-01b** `document_parser.v1`（`app/capabilities/pdf_text.py` を使う。子プロセスで時間とメモリに上限、ADR-003）・`rule_based_extractor.v1`（D-015）・`structured_extractor.v1`（mock、D-004）・`rule_validator.v1`（Rule pack の式。`eval` しない、3 値）。実装は `backend/app/capabilities/` に置き、`backend/app/executor/handlers.py` に結び付け、`backend/app/catalog/registry.py` の `available` を合わせる（`tests/unit/test_handlers.py` が一致を確かめる）。**dev の結果を見て抽出を直す前に、ホールドアウトの凍結が済んでいるか人に確かめる。**
3. **P3-01c** 根拠の照合（`easf_local_mcp:locate_evidence`、ADR-005 の自作ローカル MCP サーバ）・`result_exporter.v1`・`exportRunResult`（CSV の先頭文字の無害化）。
4. **P3-01d** 請求書の Workflow を端から端まで（`contracts/examples/workflows/invoice.json` の Rule pack を `1.1.0` にした版）、画面（文書のアップロード・出力）。
5. **P3-03** dev での評価、G2 前の診断（アップロードの E-01〜E-04 は必須）、`reports/gate_G2.md`。

業務名（請求書・契約書など）をエンジン（composer・executor・adapters）に書かない（`scripts/validate_contracts.py` が検出する）。業務の違いは設定・Rule pack・抽出の項目の指定（`field_spec`）で表す。

## 6. 既知の問題

- 独立レビューなし（D-024）。
- バックエンドのテストが遅い（Windows の spawn）。
- 画面：Workflow の作成・編集の画面なし、確認の決定後に修正の内容を表示できない（契約 v1）、実行・確認の E2E は模擬 API。
- 人の作業時間が未記録。
