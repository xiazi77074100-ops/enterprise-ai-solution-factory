# 引き継ぎ（次のセッションへ）

| 項目 | 内容 |
|---|---|
| 更新日 | 2026-10-19 |
| 書いた人 | Claude Code（統合責任者） |
| main の最新 | `3053b88`（G1b の報告まで。CI 成功） |

新しいセッションは、まずこの文書、`AGENTS.md`、`TASK_STATUS.md`、`DECISIONS.md` の最後の数行を読む。

## 1. 現在地

- **Phase 2 は完了し、G1b の承認を待っている。** 報告は `reports/gate_G1b.md`（自己判定 PASS）。人の go / no-go の前に Phase 3 のコードを書かない（`easf-phase-gate`）。
- 承認されたら Phase 3（P3-01 請求書の業務の Capability、P3-02 合成データと正解ラベル）。どちらも CC が行う（D-024。Codex には渡さない）。
- 人に返事をもらっていない事項：G1b の承認、Phase 3 の承認、`HUMAN_TIME_LOG.csv`（人の作業時間）の記入（G1a §10-3・G1b §10-3。任意）。

| ゲート | 状態 | 報告 |
|---|---|---|
| G0 | 承認（D-014） | `reports/gate_G0.md` |
| G1a | 承認（D-024） | `reports/gate_G1a.md` |
| G1b | **承認待ち** | `reports/gate_G1b.md` |

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

**まだないもの（Phase 3 以降）**：文書のアップロード・解析・抽出・ルール・根拠・出力（`exportRunResult`）、評価、再利用、実 LLM（D-004 で保留）。本番の許可リストで実行できる業務の Capability はまだない（`backend/app/executor/handlers.py` は空。人の確認だけ Executor が扱う）。

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

## 4. 進め方（このプロジェクトの約束）

- タスクごとに `cc/<task>-<slug>` ブランチ → コミット → プッシュ → **CI の成功を確かめてから** `main` へ fast-forward → プッシュ（D-013、G1a §8-2）。CI の待ち合わせは `sh scripts/wait_ci.sh $(git rev-parse HEAD)`（`gh` はこの端末にない。公開リポジトリなので API で見られる）。
- 画面・API・権限・入力チェックを変えたら、同じコミットで設計書を直す（`spec-sync`）。画面は `ui-design`、コードは `jp-secure-coding`、Capability・Workflow は `easf-capability-contract` を先に読む。
- 報告・設計書・コミットは日本語。**人とのやり取りは中国語**（利用者の希望）。中国語の文言をリポジトリに入れない。
- 実行していないものは「未実行」と書く。測っていない数値を書かない。模擬は模擬と書く。
- 契約（`contracts/`）を変える必要が出たら止まるのが原則。エラー応答の追記のような後方互換の修正は、版を上げて DECISIONS に書き、報告で知らせた前例がある（D-022・D-025）。

## 5. 次にやること（G1b 承認後）

1. P3-01 の前に計画を書く（`docs/phase3/PHASE3_PLAN.md`）：文書のアップロード（サイズ・形式・保存・ダウンロードの安全、`jp-secure-coding` upload-and-files.md）、`document_parser.v1`・`rule_based_extractor.v1`（D-015）・`structured_extractor.v1`（mock）・`rule_validator.v1`・`easf_local_mcp:locate_evidence`（ADR-005）・`result_exporter.v1` と `exportRunResult`。
2. 実装を `backend/app/executor/handlers.py` に結び付け、`backend/app/catalog/registry.py` の `available` を合わせる（`tests/unit/test_handlers.py` が一致を確かめる）。業務名をエンジン（composer・executor・adapters）に書かない（`scripts/validate_contracts.py` が検出する）。
3. 合成データ・正解ラベルは `easf-eval-integrity`・`fixture-data` に従う（ホールドアウトのラベルを見ない）。
4. G2 前の診断ではアップロードの項目（checklist E-01〜E-04）を必須にする。

## 6. 既知の問題

- 独立レビューなし（D-024）。
- バックエンドのテストが遅い（Windows の spawn）。
- 画面：Workflow の作成・編集の画面なし、確認の決定後に修正の内容を表示できない（契約 v1）、実行・確認の E2E は模擬 API。
- 人の作業時間が未記録。
