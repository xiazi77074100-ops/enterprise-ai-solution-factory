# dev での評価（契約書、要件変更 CR-1、Factory、参考値）

| 項目 | 内容 |
|---|---|
| 日付 | 2026-10-21（ベースラインの CR-1 の完了〔`449e51e`、11:22〕の後） |
| 実施 | Claude Code（P4-04、Factory 側） |
| データ | `fixtures/contract/manifest.json` の dev 28 件 ＋ CR-1 の正解（`labels_cr1`） |
| 解決策 | `fixtures/workflows/contract-v3.json`（v2 に項目 `antisocial_exclusion` を 1 つ足しただけ） |
| Rule pack | `contract@1.1.0`（`fixtures/rule_packs/contract-1.1.0.json`。1.0.0 に CON-006 を足しただけ） |
| コマンド | `python -m app.evaluation.offline --workflow ../fixtures/workflows/contract-v3.json --rule-pack ../fixtures/rule_packs/contract-1.1.0.json --manifest ../fixtures/contract/manifest.json --split dev --extra-labels labels_cr1`（Linux・Tesseract） |

## 1. 変更の大きさ（AC-10）

**製品のコードの変更はなし。** 設定だけ：Workflow に 1 項目（既存の `heading` の設定）、Rule pack に 1 ルール（既存の `present` 演算子）。差分は 10 行ほど。Capability の版は v2 と全く同じ（結合テスト `test_requirement_change_cr1_is_configuration_only` が確かめる）。評価の道具に別ファイルの正解を合わせる `--extra-labels` を足した（評価の側の変更で、製品ではない）。

## 2. 結果

| 指標 | CR-1 前（v2） | CR-1 後（v3） |
|---|---|---|
| 項目抽出（マクロ平均） | 0.924（9 項目） | 0.918（10 項目） |
| 重大ルールの再現率 | 1.0（4 件） | **1.0（10 件）** |
| 根拠の位置の正しさ | 1.0 | **1.0** |
| 重大項目が誤っているのに found | 0 | **0** |

CON-006：fail→fail 6（条項の無い 6 件をすべて検出）、pass→pass 19、pass→fail 3（スキャン 3 件で見出しを OCR で読めず、確認へ回る誤検出）。新しい項目の一致 0.864（誤りはスキャン 3 件だけ）。ほかのルール・項目の結果は CR-1 前と同じ。

## 3. 人の作業時間（M2）

| arm | 分 | 測り方 |
|---|---|---|
| ベースライン | 30 | **測っていない**。CR-1 のパッケージがフォルダに入った 10:54 からコミットの 11:22 までの時計の時間（上限） |
| Factory | 15 | **CC の推定**（人は測っていない）：人の発言 2 回 × 5 分 ＋ 報告を読む 5 分 |

どちらも測った値ではないため、M2 の比較には使えない程度の精度しかない（事前登録 §5・§9）。
