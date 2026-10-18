# 開発環境の手順

| 版 | 日付 | 変更内容 | 作成者 |
|---|---|---|---|
| 0.1 | 2026-10-18 | 初版（P1-01） | Claude Code |

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

## 3. テストと検査（CI と同じ）

```sh
export EASF_TEST_DATABASE_URL="$EASF_DATABASE_URL"   # 未設定だと DB のテストは skipped になる（成功ではない）
uv run ruff check . && uv run ruff format --check . && uv run mypy app tests
uv run bandit -q -r app && uv run pip-audit
uv run pytest -q
```

## 4. LLM の API キー（D-015）

`.env` の `EASF_LLM_GEMINI_API_KEY` に入れる。値をコミット・ログに出さない。Gemini のプロファイルを有効にするのは、ADR-002 の確認（無料枠のデータの扱い・制限）を済ませてから（Phase 2 以降）。
