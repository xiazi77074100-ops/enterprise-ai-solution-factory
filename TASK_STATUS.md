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
| P1-02 Capability Catalog（不変の版・検証） | CC | 未着手 | `cc/P1-02-catalog` | — | 2026-10-18 |
| P1-03 日本語 UI の枠と共通部品 | CC | 未着手 | `cc/P1-03-ui-shell` | — | 2026-10-18 |
| P1-04 契約テスト・否定テスト | CC | 未着手 | `cc/P1-04-contract-tests` | — | 2026-10-18 |
