# 要件変更 CR-1（契約書、両 arm 共通、凍結）

前回の要件（`requirements.md`）に、次の 1 項目と 1 ルールを足す。ほかは変えない。事前登録 §6。

## 1. 追加する項目

| 名前 | 内容 | 型 | 重大 | 値の決め方 |
|---|---|---|---|---|
| antisocial_exclusion | 反社会的勢力の排除条項 | 文字列 | **重大** | 反社会的勢力の排除の条の見出しを印字どおり（例「第6条（反社会的勢力の排除）」「6.（反社会的勢力の排除）」「六、反社会的勢力の排除」）。無ければ null（missing） |

## 2. 追加するルール

| ID | 重大度 | 内容 | 結果 |
|---|---|---|---|
| CON-006 | critical | 反社会的勢力の排除条項がある | 無ければ fail（必ず人の確認へ）。判定できなければ uncertain |

## 3. 出力の形

`requirements.md` §6 の JSON に、`fields.antisocial_exclusion`・`field_status.antisocial_exclusion` と、`findings` の CON-006 を足す。根拠（`evidence.antisocial_exclusion`）も同じ形で出す。

## 4. データ

`data/dev/labels_cr1/<sample_id>.json`：dev 28 件の CR-1 の正解（`value`・`status`・`finding`〔CON-006〕・`gold_evidence`）。主の正解（`data/dev/labels/`）は変えない。

## 5. 作業時間

CR-1 の作業時間（M2）は、P4 の作業と分けて記録する（`task_id` を `CR-1` にする）。
