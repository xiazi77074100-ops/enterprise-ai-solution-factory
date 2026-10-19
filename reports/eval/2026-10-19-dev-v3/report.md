# dev での評価（請求書 v3、OCR あり、参考値）

| 項目 | 内容 |
|---|---|
| 日付 | 2026-10-19（ホールドアウトの凍結〔D-035〕の後） |
| 実施 | Claude Code（P3-04） |
| データ | `fixtures/manifest.json`（SHA-256 `bbbae8e4…332d41a3`）の dev 28 件 |
| 解決策 | `fixtures/workflows/invoice-v3.json`（`invoice-poc` v3、`ocr: tesseract`） |
| Rule pack | `invoice@1.1.0` |
| 環境 | Linux（Docker `uv:python3.12-bookworm-slim`、Tesseract 5.3.0・日本語）。Windows には Tesseract が無いため |
| 結果 | `result.json`（全件の誤り・ルールの混同表） |

**合否の判定には使わない**（ADR-007 の判定はホールドアウト）。この版（OCR の後処理 D-036 を含む）を最終の版とし、以後ホールドアウトの評価まで抽出を変えない。

## 1. 結果

| 指標 | v2（OCR なし、P3-03） | **v3（OCR あり）** | ADR-007 の閾値（ホールドアウトで判定） |
|---|---|---|---|
| 項目抽出（正規化一致のマクロ平均） | 0.927 | **0.961** | 0.85 以上（目安） |
| 項目の状態の一致 | 0.851 | 0.851 | — |
| 重大項目が誤っているのに found | 0 | **0** | — |
| 重大ルールの再現率 | 1.0（8 件） | **1.0**（8 件） | 1.0（必須） |
| 根拠の位置の正しさ（verified） | 1.0（278） | **1.0**（278） | 0.9 以上（必須） |
| OCR の根拠はすべて unverified | — | **満たす**（9 件） | 全件「未確認」（必須） |

調整の経過（すべて凍結の後）：OCR を入れただけで 0.944。誤りに、桁区切りの「,」を「.」と読む（`8,400` → `8.400` → 8.4）・表の罫線や列の間隔が値に混ざる、の 2 種類が見えたため、OCR のページの値だけに一般的な後処理を足した（D-036）→ 0.961。INV-001 の誤った fail（スキャン 1 件）も消えた。残りは文字の読み違い・読み落としで、2 件のスキャンに合わせ込むことになるため、ここで止めた。

## 2. 残った誤り（すべてスキャン画像 2 件）

OCR のページの値は `found` にならない（`uncertain` か `missing`）ので、確認者には確定に見えない。

| 文書 | 項目 | 予測（状態） | 正解 |
|---|---|---|---|
| inv-0008 | vendor_name | 「…株式全社」（uncertain） | 「…株式会社」 |
| inv-0008 | due_date | 2025-01-29（uncertain） | 2025-11-29 |
| inv-0008 | invoice_no・payee_account | null（missing） | 値あり |
| inv-0038 | payee_bank | 「…銀生」（uncertain） | 「…銀行」 |
| inv-0038 | vendor_name・subtotal・payee_branch・payee_account | null（missing） | 値あり |

ほか issue_date・payee_branch が uncertain で null（読めない）。ルールの混同は `result.json` の `rule_confusion`（重大ルールの見逃し 0）。
