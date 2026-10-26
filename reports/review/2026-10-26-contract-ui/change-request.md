# RV-G4-UI-001の限定変更要求

2026-10-26、Codex。状態：提案、製品未適用。根拠は同じフォルダーの `worker.log`、`model-repro.json`、`partial-db-*.json`。

独立workerは認証モデルをimportせず、`run.created_by`など12の外部キーが`app_user.id`を解決できない。最小候補は `backend/app/executor/worker.py` で認証モデルを明示的に読み込むこと。DB・migration・契約の変更ではない。

レビュー用の候補差分（未適用）：

```diff
 import time

+# 独立プロセスでもapp_userへの外部キーを解決するため、認証モデルを登録する。
+from app.auth import models as auth_models  # noqa: F401
 from app.core.config import get_settings
```

API全体のimportやモデル探索の基盤は追加しない。`worker.py`は現行manifestの固定対象外で、旧行のSHAやD-047の設定・実装を書き換える必要はない。manifestの保証範囲を拡大したとも扱わない。

必要な範囲：CC所有の `backend/app/executor/worker.py`、新しい独立プロセス回帰試験 `backend/tests/test_worker_bootstrap.py`、次タスクのhandoff・診断報告・台帳。既存UIシナリオは試験補助の必要最小限の修正だけ。D-053はこの入口修正を含まないため、CCまたはこの範囲のCodex限定代行を指定する。

回帰の手順：

1. 新規Python子プロセスで `app.executor.worker` だけをimportし、全FKの`.column`を解決する。API/TestClient/テストのconftestを子プロセスへimportしない。修正前失敗→修正後成功を記録する。
2. 既存の実装manifest照合、ruff/型検査、契約・既存統合試験を実施する。
3. 別の専用_test DB・Uvicorn・独立worker・Vite・新規ChromeでP5-03lの同一フローを再実行し、修正承認・根拠・export/traceまで実績を採取する。

診断importでFK解決が0件になったことだけでは、この回帰や実フローの成功に代えられない。修正・回帰・成功時UI証拠は**未実行**。G4の承認は別に必要。
