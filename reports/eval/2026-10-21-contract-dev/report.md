# dev での評価（契約書、Factory、参考値）

| 項目 | 内容 |
|---|---|
| 日付 | 2026-10-21（契約書のホールドアウトの凍結〔D-041〕・ベースラインの完了〔D-042〕の後） |
| 実施 | Claude Code（P4-03、Factory 側） |
| データ | `fixtures/contract/manifest.json`（SHA-256 `fea2d463…887bd209`）の dev 28 件（PDF 24・スキャン 4） |
| 解決策 | `fixtures/workflows/contract-v2.json`（`contract-poc` v2。抽出は `document.rule_extractor@1.1.0`、ほかは請求書と同じ版） |
| Rule pack | `contract@1.0.0`（`contracts/examples/rule_packs/contract-1.0.0.json`） |
| 環境 | Linux（Docker、Tesseract 5.3.0・日本語） |
| 結果 | `result.json` |

**合否の判定には使わない**（判定は人がホールドアウトで両 arm を評価する。事前登録 §7・§8）。

## 1. 結果

| 指標 | dev | ADR-007 の閾値 |
|---|---|---|
| 項目抽出（正規化一致のマクロ平均、9 項目） | **0.924** | 0.85 以上（目安） |
| 項目の状態の一致 | 0.865 | — |
| 重大項目が誤っているのに found | **0** | — |
| 重大ルールの再現率 | **1.0**（4 件） | 1.0 |
| 根拠の位置の正しさ（verified） | **1.0**（161 範囲） | 0.9 以上 |
| OCR の根拠はすべて unverified | 満たす（10 件） | 必須 |

項目ごと：auto_renewal・liability_cap_jpy 1.0、end_date 0.964、governing_law 0.962、effective_date 0.929、party_b 0.893、confidentiality 0.875、party_a 0.857、termination_notice_days 0.833。

## 2. 調整の経過（すべて凍結の後、dev だけで）

1. 最初の評価：項目 0.924、**根拠の位置 0.71**（必須の 0.9 を下回る）。原因は根拠の照合の部品：当事者の名前を前文と署名欄の両方で引用していた、「30」（解約の日数）が日付の日にも一致していた。
2. 根拠の照合を、読む順の最初の出現だけを引用し、4 桁未満の数字だけの形を探さないように直した → 根拠の位置 1.0。
3. その変更と抽出の部品の変更で請求書が変わらないことを確かめた：請求書の dev（v3）を同じ条件で評価し直し、項目・ルール・誤り・根拠の件数（278）がすべて前と同じ。途中で一度、抽出の部品の書き換えで請求書の支払期日が 0.96 → 0.0 に落ちたのをこの確認で見つけて直した（同じ値を 2 つの見出しで拾うと食い違いと数えていた）。

## 3. 誤りの具体例

項目の誤り 18 件は**すべてスキャン画像 4 件**（con-0004・con-0021・con-0030・con-0031）。OCR で読めない値は missing・uncertain になり、found で誤った値はない。

| ルール | 一致 | ずれ |
|---|---|---|
| CON-001（critical） | pass→pass 23、fail→fail 4 | pass→fail 1（スキャンで秘密保持の見出しが読めない。確認へ回る誤検出） |
| CON-002 | pass→pass 21、fail→fail 4、uncertain→uncertain 3 | — |
| CON-003 | pass→pass 24、fail→fail 4 | — |
| CON-004 | pass→pass 20、fail→fail 3 | pass→fail 4（スキャンで通知期間が読めない）、uncertain→fail 1（「相当の期間」は値なしとして fail。確認へ回る） |
| CON-005 | pass→pass 25、fail→fail 2 | pass→fail 1（スキャン） |
