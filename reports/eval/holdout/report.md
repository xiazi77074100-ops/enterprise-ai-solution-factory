# ホールドアウトでの評価（請求書、G2 の判定）

| 項目 | 内容 |
|---|---|
| 日付 | 2026-10-19 |
| 実施 | プロジェクト責任者（`scripts/eval_holdout.ps1`、Linux の Docker・Tesseract）。CC は集計値（`result.json`）だけを読んだ |
| データ | ホールドアウト 12 件。`fixtures/manifest.holdout.json` SHA-256 `9439de443027be16f9d2e5dc54a24a3f1ab65506a3ca29a64bab8314ac622ac6`（D-035 で凍結。全ファイルのハッシュを照合して実行） |
| 解決策 | `fixtures/workflows/invoice-v3.json`（最終の版、D-036） |
| Rule pack | `invoice@1.1.0` |
| 回数 | 1 回（結果を見て版を変えていない） |

## 1. ADR-007 の閾値での判定

| 指標 | 閾値 | ホールドアウト | 判定 |
|---|---|---|---|
| 重大な誤りの黙認 | 0 件（必須） | 0（重大項目が誤っているのに found：0。Workflow は全件を人の確認へ） | **合格** |
| 重大ルールの再現率 | 1.0（必須） | 1.0（正例 5 件） | **合格** |
| 根拠の位置の正しさ | 0.9 以上（必須） | 1.0（verified 98 範囲） | **合格** |
| 照合できない根拠の扱い | 全件「未確認」（必須） | OCR の根拠 15 件はすべて unverified | **合格** |
| 確認の記録の完全さ | 100%（必須） | 本評価では測れない（人の確認を模擬しない）。確認者・時刻・修正前後の記録は結合テストで確認（test_run_pauses_for_review_and_succeeds_with_corrections ほか） | 結合テストで確認 |
| 項目抽出（正規化一致のマクロ平均） | 0.85 以上（目安） | 0.908 | **合格** |

## 2. 集計値

項目ごとの一致：due_date・issue_date・registration_no・tax 1.0、invoice_no・payee_account・subtotal 0.917、total 0.909、payee_branch 0.833、vendor_name・payee_bank 0.75。項目の状態の一致 0.701（dev は 0.851）。

ルール（正解 → 予測、件数）：

| ルール | 重大度 | 一致 | ずれ |
|---|---|---|---|
| INV-001 | critical | pass→pass 7、fail→fail 2、uncertain→uncertain 1 | pass→fail 1（誤検出。確認へ回る）、fail→uncertain 1（確認へ回るので見逃しではない） |
| INV-002 | major | pass→pass 11、fail→fail 1 | — |
| INV-003 | major | pass→pass 10、uncertain→uncertain 1、fail→fail 1 | — |
| INV-004 | critical | pass→pass 7、fail→fail 2 | pass→uncertain 3 |
| INV-005 | major | pass→pass 11、fail→fail 1 | — |
| INV-006 | major | pass→pass 10、fail→fail 1 | pass→uncertain 1 |

## 3. 解釈と制約

- 必須の閾値はすべて満たす。dev（0.961）よりホールドアウト（0.908）の項目抽出が低い。誤りの中身は AI には見せていない（人だけが確認できる）。
- 件数は 12 件で、統計的に強い主張はしない（ADR-007）。合成データは 1 つの生成器から作られ、実在の請求書の多様さは表していない。
- 実 LLM の抽出は評価していない（D-004）。
