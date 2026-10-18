# 変更履歴（CHANGELOG）

ゲートごとに、利用者に見える変化と契約の変化をまとめる。

## Phase 0（G0 前）

- 追加：Claude Code / Codex 共通の規則（`AGENTS.md`・`CLAUDE.md`）と skill 14 個（`.claude/skills/` → `.agents/skills/`）、同期スクリプト `scripts/sync_skills.py`。
- 追加：Phase 0 計画書、ADR-001〜009（提案）、契約 v1 の案（`contracts/`）、基本設計（構成・LLM ポート）、セキュリティ設計（脅威モデル）、見積、台帳。
- 追加：合成データ計画・事前登録（P0-04）、G0 レビュー（P0-02）と指摘の反映（P0-06）：権限表と `x-easf-roles`、再利用の記録・メンバー・各種一覧の API、`rejected` 状態、`project_context`、RFC 8785 の内容ハッシュ。
- アプリケーションコード：なし。

## Phase 1（G1a 前）

- 追加：FastAPI・PostgreSQL の雛形、セキュリティヘッダ・共通エラー・要求サイズの上限、CI（P1-01）
- 追加：ログイン・セッション・CSRF・案件・メンバー・要件の版、管理用 CLI（P1-05）
- 追加：Capability Catalog と Rule pack（不変の版・RFC 8785 の内容ハッシュ・DB トリガー）（P1-02）
- 追加：日本語 UI の枠と共通部品、ログイン・プロジェクト・能力カタログの画面（P1-03）
- 追加：契約テスト（実装と契約の一致・認可の全件表・応答スキーマ）（P1-04）
- 契約：1.0.0 → 1.0.1（login に 403 を追加、D-022）
- 追加：バックエンドのコンテナ（Alpine・非 root・読み取り専用）と G1a 前の脆弱性自己診断。修正：VA-001（本番の Secure Cookie 必須）、VA-002（イメージの依存）、VA-003（CORP ヘッダ）、VA-004（NUL 文字で 500）、VA-005（Host ヘッダ・インジェクション）

## Phase 2（G1b 前）

- 追加：テスト専用 DB（easf_test）（P2-00）
- 追加：Composer（Workflow の静的検証）と Solution の API（作成・更新・検証・承認・一覧）（P2-01）
- 追加：Executor（実行の状態機械・ワーカー・再試行・予算・異常終了からの回復）、アダプタ（ローカルは子プロセス、LLM は mock のみ）、人の確認、トレース（ハッシュ連鎖・追記のみ）、実行と確認の API（P2-02）
- 追加：Executor の敵対的テスト。予算の残りで短くした時間切れを budget_exceeded と記録するよう修正（P2-04）
- 追加：解決策・実行・確認の画面（実行モニター、確認タスク、修正して承認）（P2-03）
- 変更：画面の見た目を sales-assistant の UI に合わせた（配色は EASF の青緑系、D-026）。字体 Noto Sans JP を自前で配信
- 契約：1.0.1 → 1.0.2（ロールで制限する 4 操作に 403 を追加、D-025）

