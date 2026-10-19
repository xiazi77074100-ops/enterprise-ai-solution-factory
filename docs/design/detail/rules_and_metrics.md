# 詳細設計：ルールの判定と評価の指標

| 版 | 日付 | 変更内容 | 作成者 |
|---|---|---|---|
| 0.1 | 2026-10-19 | 初版：評価の指標の計算式（P3-03） | Claude Code |
| 0.2 | 2026-10-19 | OCR の根拠の指標、解析の設定は Workflow から（P3-04） | Claude Code |

ルールの判定（3 値・on_missing・演算子）は `capabilities.md` §5。閾値は ADR-007（事前登録。ホールドアウトの評価後に変えない）。ここは `backend/app/evaluation/offline.py` の計算式を書く。

## 1. 評価の実行

- 対象：正解ラベルがリポジトリにある分割（dev）だけ。ラベルの無い分割（holdout）は止まる。ホールドアウトは人が実行し、AI には集計値だけを渡す（easf-eval-integrity）。
- 手順：Workflow の設定（解析の `ocr` を含む）で、解析（`document.parser`）→ 抽出（`document.rule_extractor`）→ 検証（`document.rule_validator`）→ 根拠（`document.evidence_locator`）を、本番と同じ関数で順に実行する。人の確認・出力は模擬しない。
- 案件の文脈（`unique_in_project`）：manifest の順に、前の文書の抽出値（本番は確認後の値）。
- 記録：manifest の SHA-256、Workflow の ID と版、Rule pack の ID と版。

## 2. 指標

| 指標（`metrics` のキー） | 計算 |
|---|---|
| `field_macro_normalized_match` | 正解の状態が `found` で値が配列でない項目について、項目ごとに「予測＝正解」（NFKC・前後の空白を除いた文字列、数として読めれば数で比較）の割合を出し、項目の平均 |
| `field_status_agreement` | 全項目（正解ラベルにあり抽出の設定にもある）で、予測の状態（found／missing／uncertain）が正解と同じ割合 |
| `critical_fields_wrong_but_found` | 重大項目（`field_spec[].critical`）で、予測が `found` なのに値が正解と違う件数（確認者に正しく見える誤り） |
| `critical_rule_recall` | 正解が `fail` の重大ルールのうち、予測が `fail` か `uncertain`（確認へ回る）の割合。`critical_rule_positives` はその母数 |
| `evidence_position_accuracy` | 予測の根拠（`verified`）のうち、同じページで正解の範囲と 1 文字以上重なる割合。`evidence_spans` は母数 |
| `ocr_evidence_all_unverified` | OCR で読んだページ（`extraction_method` が `text_layer` でない）の根拠がすべて `unverified` であること（ADR-003）。`ocr_evidence_spans` はその件数。`evidence_position_accuracy` は `verified` の根拠だけで計算する |

`rule_confusion` はルールごとの「正解→予測」の件数、`field_errors` は項目の誤りの全件（文書・層・予測・正解）、`missed_critical_rules` は重大ルールの見逃しの全件。
