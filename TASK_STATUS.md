# タスクの状態（TASK_STATUS）

| タスク | 担当 | 状態 | ブランチ | 証跡 | 更新日 |
|---|---|---|---|---|---|
| P0-00 skill 一式と共通規則 | CC | 完了 | `cc/P0-00-skills` | `AGENTS.md`、`.claude/skills/`、`python scripts/sync_skills.py --check` exit 0 | 2026-10-18 |
| P0-01 ADR とエンジン比較 | CC | 完了（ADR-001〜009 承認済み。D-010） | `cc/P0-01-adr` | `docs/adr/` | 2026-10-18 |
| P0-02 G0 レビュー（自己レビュー、D-011・D-012） | CC | 完了（BLOCKER 0・MAJOR 7・MINOR 8・質問 3） | `cc/P0-02-g0-review` | `reviews/G0_REVIEW.md` | 2026-10-18 |
| P0-03 契約 v1 | CC | レビュー待ち（凍結は G0） | `cc/P0-03-contracts` | `contracts/`、`python scripts/validate_contracts.py` exit 0（陰性試験 6 種も検出） | 2026-10-18 |
| P0-04 合成データ計画・事前登録 | CC（D-011） | 完了（事前登録は G0 で承認待ち） | `cc/P0-04-fixture-and-prereg` | `docs/design/fixture_plan.md`、`docs/experiment/preregistration.md` | 2026-10-18 |
| P0-05 脅威モデル・基本設計・見積・台帳 | CC | レビュー待ち | `cc/P0-05-design` | `docs/design/`、`docs/phase0/estimates.md`、台帳 5 種 | 2026-10-18 |
| P0-06 レビュー指摘の反映 | CC | 完了（15 件すべて反映） | `cc/P0-06-review-fixes` | `reviews/G0_REVIEW.md` §5 | 2026-10-18 |
| G0 ゲート報告 | CC | 完了・**承認済み**（D-014） | — | `reports/gate_G0.md` | 2026-10-18 |
| P1-01 FastAPI・PostgreSQL の雛形（健康確認・マイグレーション・CI） | CC | 完了 | `cc/P1-01-scaffold` | pytest 15 passed（実 PostgreSQL）、ruff・mypy strict・bandit・pip-audit 問題なし | 2026-10-18 |
| P1-02 Capability Catalog（不変の版・検証） | CC | 完了 | `cc/P1-02-catalog` | pytest 44 passed（見本 6 件の登録・冪等・409・外部 $ref・実装の許可リスト・DB トリガー・Rule pack）、静的検査問題なし | 2026-10-18 |
| P1-03 日本語 UI の枠と共通部品 | CC | 完了 | `cc/P1-03-ui-shell` | lint・typecheck・vitest 6 passed・build（ソースマップなし）・npm audit 0 件・Playwright 2 passed（1440px・390px、横スクロールなし、想定外のコンソールエラーなし） | 2026-10-18 |
| P1-04 契約テスト・否定テスト | CC | 完了 | `cc/P1-04-contract-tests` | 実装と契約の一致、x-easf-roles からの認可の全件表（実装済み 20 操作）、全応答の応答スキーマ検証。pytest 65 passed。契約の欠落 1 件を検出し 1.0.1 で修正（D-022） | 2026-10-18 |
| P1-05 認証・セッション・案件・メンバー・要件の版 | CC | 完了 | `cc/P1-05-auth-projects` | pytest 30 passed（ログイン・固定化・列挙・ロック・CSRF/Origin・IDOR・一括代入・自己承認を含む）、ruff・mypy・bandit・pip-audit 問題なし | 2026-10-18 |
| G1a 前の脆弱性自己診断 | CC | 完了 | `cc/G1a-vuln-assessment` | 高 0・中 1・低 4（すべて対応・再診断済み）。SAST・SCA・gitleaks・trivy 0 件、ZAP（未ログイン・認証付き）失敗 0。pytest 71 passed。報告書 `reports/security/2026-10-18/report.md` | 2026-10-18 |
| G1a ゲート報告 | CC | 完了・**承認済み**（D-024） | `cc/G1a-gate-report` | `reports/gate_G1a.md` | 2026-10-18 |
| P2-00 Phase 2 計画・詳細設計・テスト専用 DB | CC | 完了 | `cc/P2-00-plan` | `docs/phase2/PHASE2_PLAN.md`、`docs/design/detail/run_execution.md`。テストは `easf_test` だけを使い、`_test` 以外の DB 名では停止。pytest 71 passed、開発用 DB の利用者数は実行前後で同じ | 2026-10-18 |
| P2-01 Composer と Solution の API | CC | 完了 | `cc/P2-01-composer` | Composer の検査 13 種（見本の Workflow 2 件は合格、誤り 14 種を検出）、Solution の API 6 操作（ETag・If-Match・承認の規則・DB トリガーで凍結）、認可の全件表に追加。契約 1.0.2（D-025）。pytest 102 passed | 2026-10-18 |
| P2-02 Executor・アダプタ・Run と確認の API・トレース | CC | 完了 | `cc/P2-02-executor` | 状態機械・DB をキューにしたワーカー・子プロセスでのローカル実行・LLM は mock のみ・人の確認（割り当て・決定・再開・却下）・ハッシュ連鎖のトレース、API 8 操作。試験用 Capability（testkit）で端から端まで、再現性（同じ入力で同じハッシュとイベントの並び）、mock の `mixed`、予算超過。pytest 124 passed | 2026-10-18 |
| P2-04 Executor の敵対的テスト | CC | 完了 | `cc/P2-04-adversarial` | 13 件：無限ループの強制終了、例外は型名だけ（入力値が漏れない）、不正な出力は再試行しない、出力の上限、子プロセスの異常終了とワーカーの継続、冪等なら再試行・そうでなければしない、予算による時間切れは budget_exceeded、ノードの入力スキーマ違反、ワーカーの異常終了からの回復、2 つのワーカーの取り合い、別の実行の確認タスク。pytest 137 passed | 2026-10-18 |
| P2-03 実行・確認の画面 | CC | 完了 | `cc/P2-03-run-ui` | 解決策（検証・承認・実行）、実行の一覧、実行モニター（自動更新・処理の流れ・トレース）、確認タスク、確認（AI 下書き・根拠・3 値の判定・修正前後）。lint・typecheck・vitest 6・build・npm audit 0 件・Playwright 4 passed（模擬 API の流れ＋実バックエンドの既存の流れ、1440px・390px） | 2026-10-18 |
