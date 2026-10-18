# ゲート報告 G0（Phase 0）

| 項目 | 内容 |
|---|---|
| コミット | 011446f（main。本報告のコミットはこの次） |
| 作成日 | 2026-10-18 |
| 作成 | Claude Code（統合責任者） |
| 判定（自己） | **PASS（人の承認待ち）**。ただし §9 の 3 点を決めていただく必要がある |
| 人の承認 | [ ] 承認  [ ] 差し戻し　承認者：＿＿＿　日付：＿＿＿ |

## 1. 成果物

| タスク | 内容 | 証跡 | コミット | 状態 |
|---|---|---|---|---|
| P0-00 | 共通規則と skill 14 個（Claude Code / Codex 共通） | `AGENTS.md`、`.claude/skills/`、`scripts/sync_skills.py` | ebba6d0 | 完了 |
| P0-01 | 計画書、ADR-001〜009、決定記録 | `docs/phase0/PHASE0_PLAN.md`、`docs/adr/`、`DECISIONS.md` | 02556e0 | 完了（ADR は全件承認済み） |
| P0-03 | 契約 v1 と検査スクリプト | `contracts/`、`scripts/validate_contracts.py` | 8414530、011446f | 完了（凍結は本ゲートの承認時） |
| P0-05 | 基本設計・脅威モデル・見積・台帳 | `docs/design/`、`docs/phase0/estimates.md`、台帳 5 種 | 090ff68 | 完了 |
| P0-04 | 合成データ計画・事前登録 | `docs/design/fixture_plan.md`、`docs/experiment/preregistration.md` | 1db1b4e | 完了（事前登録は承認待ち） |
| P0-02 | G0 レビュー（自己レビュー） | `reviews/G0_REVIEW.md` | cfd4fa1 | 完了 |
| P0-06 | レビュー指摘 15 件の反映 | `reviews/G0_REVIEW.md` の対応欄 | 011446f | 完了 |

## 2. G0 の受入条件（PHASE0_PLAN §D-1）

| # | 条件 | 結果 | 証跡 |
|---|---|---|---|
| 1 | ADR-001〜009 が承認 | 満たす | `DECISIONS.md` D-001・D-004・D-010 |
| 2 | 契約 v1、S1〜S11 の対応 | 満たす（凍結は承認時） | `contracts/`、`validate_contracts.py` exit 0 |
| 3 | 脅威モデル・セキュリティ条件 | 満たす（承認待ち） | `docs/design/security.md`、`jp-vuln-assessment` §2 |
| 4 | 合成データ計画・保管方法・閾値の事前登録 | 満たす（承認待ち） | `fixture_plan.md`、ADR-007 |
| 5 | ベースライン実験の事前登録 | **承認待ち** | `preregistration.md` §10 |
| 6 | G0 レビューの BLOCKER・MAJOR が閉じている | 満たす（BLOCKER 0、MAJOR 7 件すべて対応済み） | `reviews/G0_REVIEW.md` |
| 7 | 見積・台帳 | 満たす | `estimates.md`、`COST_LEDGER.csv` |
| 8 | 権利関係の確認 | 満たす | D-002（個人 POC）、D-003、D-009（個人の名前・アドレスでコミット） |
| 9 | G0 までにアプリケーションコードなし | 満たす | `backend/`・`frontend/` が存在しない |

## 3. 実行したコマンドと結果（2026-10-18）

| コマンド | 終了コード | 結果 |
|---|---|---|
| `python scripts/sync_skills.py --check` | 0 | 写しが一致 |
| 写しをわざとずらして同上 | 1 | 検出 |
| `python scripts/validate_contracts.py`（jsonschema 4.26.0、openapi-spec-validator 0.9.0、一時的な venv） | 0 | `OK: schemas=5 capabilities=6 rule_packs=2 workflows=2 openapi=valid` |
| 陰性試験 1（循環・未登録の版・入力の不足・外部 `$ref`・冪等でないリトライ・汎用エンジン内の業務名） | 1 | 6 種すべて検出 |
| 陰性試験 2（`x-easf-roles` の欠落、公開してはいけない操作の `public`） | 1 | 2 種とも検出 |
| `git push`（各タスクのブランチと main） | 0 | `main...origin/main` 一致 |

未実行：Codex による独立レビュー（D-011）。各 ADR の「採用時に確認」とした外部の資料（ライブラリの版・ライセンス・LLM の料金と規約）。

## 4. 試験成績

Phase 0 は文書と契約だけのため、単体・結合・画面の試験はなし。契約の検査は §3 のとおり。

## 5. セキュリティ

- 脅威 21 種を整理し、対策と確かめ方（診断チェックリストの ID）を対応付けた（`docs/design/security.md`）。
- 契約の段階で入れた対策：外部 `$ref` の禁止、実装参照は許可リストのキー、全操作の権限宣言、副作用のある Capability を実行しない、LLM の接続先・キーの環境変数の制限、ログイン CSRF の `Origin` 照合。
- 自己診断（`jp-vuln-assessment`）は G1a から。

## 6. データ

未作成（Phase 3）。manifest の SHA-256 は凍結時に `DECISIONS.md` と `preregistration.md` §8 に記録する。

## 7. 時間と費用（実績）

| 区分 | 今回 | 累計 | 上限 |
|---|---|---|---|
| 人の時間（分） | **未記録**（`HUMAN_TIME_LOG.csv` に記入をお願いします） | 未記録 | — |
| 追加現金支出（円） | 0 | 0 | 10,000 |

## 8. 既知の問題・未解決のリスク

- 自己レビューのため独立性が低い（D-011・D-012）。G4・最終監査は別セッションで行う。
- mock の LLM では holdout を評価できない（Q1）。
- 事前登録を Factory 側が作った（Q3、§9 脅威に記載）。

## 9. 決めていただきたいこと

1. **G0 の承認**（契約 v1 の凍結を含む）。
2. **Q1：抽出の方法**。提案は (c)：LLM を使わないローカルの規則ベースの抽出を別の Capability 版として作り、実 API（1 社、上限 5,000 円）は Phase 3 の前に別途判断。
3. **事前登録の承認**（`preregistration.md` §10）と **Q2**：CR-2（請求書の要件変更）は参考値とし、比較は CR-1 だけにする提案。

## 10. 次のフェーズの提案（承認を求めるタスク）

Phase 1（G1a）：P1-01 FastAPI と PostgreSQL の雛形（健康確認・マイグレーション・CI）、P1-02 Capability Catalog（不変の版・検証）、P1-03 日本語 UI の枠と共通部品（`ui-design`）、P1-04 契約テストと否定テスト（権限表からの全件テスト）。Codex がいない場合は CC が順に実施し、タスクごとにプッシュする（D-013）。
