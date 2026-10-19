# 開発環境の手順

| 版 | 日付 | 変更内容 | 作成者 |
|---|---|---|---|
| 0.1 | 2026-10-18 | 初版（P1-01） | Claude Code |
| 0.2 | 2026-10-19 | 文書の保存先、ロックファイルの更新の仕方（P3-01a） | Claude Code |
| 0.3 | 2026-10-19 | E2E の接続先の上書き（P3-01d） | Claude Code |

前提：Docker Desktop、Python 3.12、uv、Node.js 22（画面は P1-03 から）。

## 1. 初回

```sh
cp .env.example .env            # パスワードを長い乱数に置き換える（.env はコミットしない）
docker compose up -d db         # PostgreSQL（127.0.0.1:55432）。初回にアプリ用ロール easf_app を作る
cd backend
uv sync --python 3.12
```

## 2. マイグレーションと起動

```sh
# リポジトリ直下の .env を読み込んでから（Git Bash の例）
set -a; . ../.env; set +a
uv run alembic upgrade head                       # 所有者ロール（EASF_MIGRATION_DATABASE_URL）
uv run uvicorn app.main:create_app --factory --no-server-header --port 8000
```

最初の利用者（管理者）は CLI で作る（API はない。ADR-006）：

```sh
uv run python -m app.admin create-user --login-id admin --display-name "管理者" --admin   # パスワードは入力を求められる
```

`--no-server-header` を必ず付ける（`Server: uvicorn` を出さない。`jp-secure-coding`）。

アップロードした文書は `EASF_STORAGE_DIR`（既定 `var/documents`、`backend/` からの相対。`.gitignore` 済み）に保存される。テストは一時フォルダを使う（`backend/tests/conftest.py`）。

依存を足したら、ロックファイルの書式を変えないよう Dockerfile と同じ版の uv で固定する：`uvx --from uv==0.6.17 uv lock`（新しい uv の `uv add` はロックファイル全体を書き換える）。

## 3. テストと検査（CI と同じ）

```sh
# .env の EASF_TEST_DATABASE_URL・EASF_TEST_MIGRATION_DATABASE_URL（easf_test）を使う。未設定だと DB のテストは skipped（成功ではない）
set -a && . ../.env && set +a
uv run ruff check . && uv run ruff format --check . && uv run mypy app tests
uv run bandit -q -r app && uv run pip-audit
uv run pytest -q
```

テストは表を空にし、マイグレーションを戻すため、**開発用の DB（`easf`）ではなく `easf_test` だけを使う**（P2-00）。DB 名が `_test` で終わらない URL を渡すとテストは止まる。`easf_test` は `docker/postgres/01-app-role.sh` が初回起動時に作る。既存のボリュームでは一度だけ次を実行する：

```sh
docker compose exec -T db psql -U easf_owner -d easf -c "CREATE DATABASE easf_test OWNER easf_owner" -c "REVOKE CONNECT ON DATABASE easf_test FROM PUBLIC"
docker compose exec -T db psql -U easf_owner -d easf_test -c "GRANT CONNECT ON DATABASE easf_test TO easf_app" -c "GRANT USAGE ON SCHEMA public TO easf_app"   -c "ALTER DEFAULT PRIVILEGES FOR ROLE easf_owner IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO easf_app"   -c "ALTER DEFAULT PRIVILEGES FOR ROLE easf_owner IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO easf_app" -c "REVOKE CREATE ON SCHEMA public FROM PUBLIC"
```

## 4. 画面（frontend）

```sh
cd frontend
npm ci
npm run dev                      # http://localhost:5173（/api はバックエンド :8000 へ中継。Cookie は同一オリジン）
npm run lint && npm run typecheck && npm test && npm run build
npm run gen:api                  # contracts/openapi.yaml から src/api/schema.d.ts を作り直す（契約を変えたとき）
```

画面の確認（`ui-design` §9。1440px と 390px、横スクロールなし、コンソールエラーなし）：

```sh
npx playwright install chromium              # 初回だけ
# バックエンドと npm run dev を起動しておく。E2E 用の利用者は CLI で作る
E2E_LOGIN_ID=... E2E_PASSWORD=... npx playwright test
# 5173 番がほかのプロジェクトで使われているときは別の番号で起動し、接続先を上書きする
# npx vite --port 5174 --strictPort ; E2E_BASE_URL=http://localhost:5174 npx playwright test e2e/documents.spec.ts e2e/runs.spec.ts
```

Node.js は 22 系（jsdom 29 は 22.13 以上）。

## 5. LLM の API キー（D-015）

`.env` の `EASF_LLM_GEMINI_API_KEY` に入れる。値をコミット・ログに出さない。Gemini のプロファイルを有効にするのは、ADR-002 の確認（無料枠のデータの扱い・制限）を済ませてから（Phase 2 以降）。
