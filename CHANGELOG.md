# 変更履歴（CHANGELOG）

ゲートごとに、利用者に見える変化と契約の変化をまとめる。

## Phase 0（G0 前）

- 追加：Claude Code / Codex 共通の規則（`AGENTS.md`・`CLAUDE.md`）と skill 14 個（`.claude/skills/` → `.agents/skills/`）、同期スクリプト `scripts/sync_skills.py`。
- 追加：Phase 0 計画書、ADR-001〜009（提案）、契約 v1 の案（`contracts/`）、基本設計（構成・LLM ポート）、セキュリティ設計（脅威モデル）、見積、台帳。
- 追加：合成データ計画・事前登録（P0-04）、G0 レビュー（P0-02）と指摘の反映（P0-06）：権限表と `x-easf-roles`、再利用の記録・メンバー・各種一覧の API、`rejected` 状態、`project_context`、RFC 8785 の内容ハッシュ。
- アプリケーションコード：なし。
