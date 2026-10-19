# dev での評価（請求書、参考値）

| 項目 | 内容 |
|---|---|
| 日付 | 2026-10-19 |
| 実施 | Claude Code（P3-03） |
| データ | `fixtures/manifest.json`（SHA-256 `bbbae8e47c7c497ec0bc453645b57b1cff17143a8ce2ce10a9b37c24332d41a3`）の dev 28 件。合成データ |
| 解決策 | `fixtures/workflows/invoice-v2.json`（`invoice-poc` v2、SHA-256 `d53a469b…352ea3`） |
| Rule pack | `invoice@1.1.0`（`fixtures/rule_packs/invoice-1.1.0.json`、SHA-256 `9b4d5f9d…87124da`） |
| LLM | 使っていない（規則ベースの抽出。D-004） |
| コマンド | `cd backend && PYTHONPATH=. uv run python -m app.evaluation.offline --workflow ../fixtures/workflows/invoice-v2.json --rule-pack ../fixtures/rule_packs/invoice-1.1.0.json --manifest ../fixtures/manifest.json --split dev --out ../reports/eval/2026-10-19-dev/result.json`（終了コード 0） |
| 結果 | `result.json`（全件の誤り・ルールの混同表を含む） |

**これは dev（開発用）の結果で、合否の判定には使わない。** ADR-007 の合否はホールドアウトで判定する。ホールドアウト 12 件はまだ生成・凍結されていない（人の作業待ち、`fixtures/HOLDOUT.md`）。dev の結果を見て抽出・ルールを直すことはしていない（凍結前の調整を避けるため。直すときは人の確認のあと）。

## 1. 方法

`backend/app/evaluation/offline.py`：Workflow の設定で、解析 → 抽出 → 検証 → 根拠の照合を、本番と同じ Capability の関数で順に実行し、正解ラベルと比べる。人の確認と出力は模擬しない。案件の文脈（INV-006 の重複）は manifest の順に、前の文書の抽出値を使う（本番は確認後の値。ここが本番と違う）。子プロセス・MCP を通さず関数を直接呼ぶ（同じ関数。経路の確認は結合テスト `test_invoice_workflow.py`）。

## 2. 結果（ADR-007 の指標）

| 指標 | dev の値 | ADR-007 の閾値（ホールドアウトで判定） |
|---|---|---|
| 項目抽出（正規化一致のマクロ平均、11 項目。明細は対象外） | **0.927** | 0.85 以上（目安） |
| 項目の状態（found／missing／uncertain）の一致 | 0.851 | — |
| 重大項目が誤っているのに found（確認者に正しく見える）件数 | **0** | — |
| 重大ルールの再現率（fail か uncertain で確認へ） | **1.0**（正例 8 件） | 1.0（必須） |
| 根拠の位置の正しさ（照合済みの根拠のうち正解と重なる割合） | **1.0**（278 範囲） | 0.9 以上（必須） |
| 照合できない根拠を位置付きで出さない | 満たす（照合できない値は根拠なし） | 全件「未確認」（必須） |
| 重大な誤りの黙認 | 0（Workflow は全件を人の確認に回す。`route_when: always`） | 0 件（必須） |
| 確認の記録の完全さ | 本評価では測っていない（人の確認を模擬しないため）。確認者・時刻・修正前後は結合テストで確認 | 100%（必須） |

項目ごとの一致：vendor_name・invoice_no・issue_date・subtotal・tax・payee_bank・payee_branch・payee_account 0.929（26/28）、due_date・registration_no 0.92（23/25）、total 0.923（24/26）。

## 3. 誤りの具体例

項目の誤り 22 件は**すべてスキャン画像の 2 件**（`inv-0008`〔通常〕・`inv-0038`〔不審な指示〕、PNG）。OCR が未対応（D-030）で、全項目が `missing` になった。値を誤って `found` にした例はない。

| 文書 | 層 | 項目 | 予測 | 正解 |
|---|---|---|---|---|
| inv-0008 | normal | invoice_no | null（missing） | 2025-7102 |
| inv-0008 | normal | total | null（missing） | 9240 |
| inv-0038 | injected_instruction | vendor_name | null（missing） | （架空の会社名） |

ルールの混同（正解 → 予測）：

| ルール | 重大度 | 一致 | ずれ |
|---|---|---|---|
| INV-001 合計＝小計＋税 | critical | pass→pass 20、fail→fail 4、uncertain→uncertain 2 | pass→uncertain 1、fail→uncertain 1（スキャン。確認へ回るので見逃しではない） |
| INV-002 登録番号あり | major | pass→pass 23、fail→fail 3 | pass→fail 2（スキャンで値が読めず on_missing＝fail。誤検出） |
| INV-003 登録番号の形式 | major | pass→pass 21、uncertain→uncertain 3、fail→fail 2 | pass→uncertain 2（スキャン） |
| INV-004 振込先 | critical | pass→pass 23、fail→fail 3 | pass→uncertain 2（スキャン） |
| INV-005 支払期日あり | major | pass→pass 23、fail→fail 3 | pass→fail 2（スキャン。誤検出） |
| INV-006 重複 | major | pass→pass 24、fail→fail 2 | pass→uncertain 2（スキャン） |

重大ルールの見逃し（正解 fail を pass と予測）は 0 件。

## 4. 解釈と制約

- スキャン画像は OCR がないため抽出できない。誤った値を通すのではなく `missing`／`uncertain` で人の確認に回る。OCR（Tesseract）の導入は未決（D-030）。
- 合成データは 1 つの生成器から作られ、見出しの文字列を Workflow の設定に書いている。実在の請求書の多様さは表していない。件数が少なく、統計的な主張はしない（ADR-007）。
- 実 LLM の抽出は評価していない（D-004。mock は全項目 uncertain を返すだけ）。
