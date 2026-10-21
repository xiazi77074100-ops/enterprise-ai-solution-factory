# ゲート報告 G3（Phase 4、契約書の POC と再利用の証明）

| 項目 | 内容 |
|---|---|
| コミット | main（P4-05 のホールドアウトの評価まで） |
| 作成日 | 2026-10-21 |
| 作成 | Claude Code（統合責任者） |
| 判定（自己） | **草稿（未完了）**。品質（M3）は事前登録の非劣性の条件をすべて満たした。主要指標 M1（人の時間）は推定だけで、測った値が無い。G3 前の診断と独立レビューは未実行（Codex に引き渡し、`handoffs/P4-06.md`） |
| 人の承認 | [ ] 承認　承認者：　日付： |

G3 の条件（`docs/phase4/PHASE4_PLAN.md`）：コピーした業務専用の流れを作らない、同じ不変の Capability 版の再利用と回帰の証拠。AC-06・AC-07・AC-09・AC-12（契約書）、事前登録の M1〜M5。

## 1. 成果物

| タスク | 内容 | 証跡 | コミット | 状態 |
|---|---|---|---|---|
| P4-01 | 契約書の合成データ（dev 28 件、CR-1 の正解は別ファイル）、ホールドアウト 12 件（人が生成・凍結、D-041） | `fixtures/contract/` | — | 完了 |
| P4-02 | ベースラインの要件パッケージ（D-039） | `experiment/baseline_bundle/` | — | 完了 |
| A-01 | ベースライン（別リポジトリ・別セッション、人が実施、D-042） | `easf-baseline-contract`（非公開） | — | 完了 |
| P4-03 | Factory で契約書（D-043） | `fixtures/workflows/contract-v2.json`、`reports/eval/2026-10-21-contract-dev/` | d80e481 | 完了 |
| P4-04 | 要件変更 CR-1（両 arm、D-044・D-046） | `fixtures/workflows/contract-v3.json`、`fixtures/rule_packs/contract-1.1.0.json` | 71abf10 | 完了 |
| P4-05 | 最終の版の凍結（D-047）、両 arm 共通の採点（D-048）、ホールドアウトの評価（D-049） | `reports/eval/contract-holdout/` | 7ba596a ほか | 完了 |
| P4-06 | G3 前の診断・独立レビュー | `handoffs/P4-06.md` | — | **未実行**（Codex） |

## 2. 再利用の証拠（D-043・D-046）

| Capability | 請求書 → 契約書 | 分類 |
|---|---|---|
| `document.parser@1.0.0` | 同じ版 | unchanged |
| `review.human@1.0.0` | 同じ版 | unchanged |
| `result.exporter@1.0.0` | 同じ版、題名の設定だけ | config_only |
| `document.rule_extractor` | 新しい版 1.1.0（文言の設定・真偽・万の金額） | new_code |
| `document.rule_validator@1.0.0` | 同じ版、実装を修正（真偽の比較） | new_code |
| `document.evidence_locator@1.0.0` | 同じ版、実装を修正（最初の出現だけ・4 桁未満の数字を探さない） | new_code |

- 請求書と契約書で同じ `capability_version_id` を使うことを結合テストで確認（`backend/tests/integration/test_contract_workflow.py`）。
- 業務ごとの分岐なし（`scripts/validate_contracts.py` が CI で検査）。
- 回帰：実装を直した後、請求書の dev（v3）の数値がすべて前と同じことを確認（D-043）。
- **CR-1 は設定だけ**：Workflow v3 に 1 項目、Rule pack に CON-006。製品のコードの変更なし、Capability の版は v2 と同じ（D-046、AC-10）。
- 限界：実装キーが版ではなく実装に結び付くため、同じ版のまま実装を直すと古い版にも効く（請求書のホールドアウトの結果は変更前の実装のもの）。

## 3. 比較実験（事前登録 §7）

### M3 品質（ホールドアウト 12 件、`reports/eval/contract-holdout/report.md`）

| 条件 | A | B | 判定 |
|---|---|---|---|
| 重大な誤りの黙認 0 | 0 | 0 | 満たす |
| 重大ルールの再現率（B が 1.0） | 1.0 | 1.0 | 満たす |
| 項目抽出（B ≥ A − 0.05） | 0.992 | 0.946 | 満たす（余裕 0.004） |
| 根拠の位置（B ≥ 0.9） | 1.0 | 1.0 | 満たす |

参考：根拠の網羅 A 1.0・B 0.784、状態の一致 A 1.0・B 0.925、B の誤った警告 3 件（CON-004〜006 に各 1 件）。

### M1・M2 人の時間（`HUMAN_TIME_LOG.csv`）

| 指標 | A | B | 条件（B ≤ 0.7 × A） | 種類 |
|---|---|---|---|---|
| M1 契約書の POC | 75 分 | 15 分 | 15 ≤ 52.5 | **両方とも推定**（A は人の事後の推定、B は CC の推定） |
| M2 CR-1 | 30 分 | 15 分 | 参考 | A は時計の時間の上限、B は CC の推定 |

- **M1 は測った値が無いため、事前登録 §7 の成功・不成功を判定できない。** 推定のとおりなら条件を満たすが、それを結果として主張しない。
- B は 2 回目（A が先、学習効果は B に有利、ADR-008）。
- M6 の損益分岐の案件数：Factory を作った時間（Phase 1〜3 の人の時間）が記録されていないため**計算しない**。
- M4 AI の費用：両 arm とも有料の API を使っていない（0 円）。AI Coding の道具の利用料は arm ごとに分けていない。

## 4. 実行したコマンドと結果

| コマンド | 終了コード | 結果の要点 |
|---|---|---|
| `scripts/eval_holdout_contract.ps1`（人が実行） | 0 | §3 の値。集計値だけ |
| `uv run ruff check app tests`・`ruff format --check`・`mypy app`（backend） | 0 | 問題なし（2026-10-21、7ba596a） |
| `uv run pytest -q tests/unit`（Windows） | 0 | 104 passed、4 skipped（Tesseract が無い） |
| GitHub Actions（ci） | 成功 | 7ba596a |

未実行：
- G3 前の診断（ruff S・bandit・semgrep・pip-audit・npm audit・gitleaks・trivy・ZAP、手動の診断項目）→ P4-06。
- 独立レビュー → P4-06（Codex）。
- 契約書の画面（AC-12）の確認・E2E → P4-06 で確認範囲を決める。
- Linux でのバックエンドの全テスト（G3 用の記録）。

## 5. 既知の問題・未解決のリスク

1. 人の時間がすべて推定か未測定。主要指標の判定ができない。
2. 項目抽出の非劣性の余裕が 0.004。B は根拠の網羅が低く（0.784）、誤った警告がある。
3. 合成データは 1 つの生成器から作った。実在の契約書の多様さを表していない。
4. OCR の環境が arm で違う。
5. 実装キーが版に結び付かない（§2 の限界）。
6. 独立レビューなし（P4-06 まで）。
7. 実 LLM は未評価（D-004）。

## 6. 人に決めていただきたいこと

1. M1 が推定だけであることを受け入れて G3 を判定するか、別の業務で時間を測り直すか。
2. P4-06（診断・独立レビュー）の結果を待って G3 を判定すること（CC の提案）。
