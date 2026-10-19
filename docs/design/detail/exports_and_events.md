# 詳細設計：出力（エクスポート）

| 版 | 日付 | 変更内容 | 作成者 |
|---|---|---|---|
| 0.1 | 2026-10-19 | 初版：実行の結果の出力（P3-01c） | Claude Code |

API は `contracts/openapi.yaml` の `exportRunResult`（`GET /api/v1/runs/{run_id}/export?format=json|csv`）。実装は `backend/app/api/runs.py`・`backend/app/capabilities/result_exporter.py`。イベントの項目は `contracts/events.schema.json`（変更なし）。

## 1. 操作

| 誰が | 入力 | チェック | 応答 |
|---|---|---|---|
| 案件の solution_lead・qa_evaluator・business_reviewer | `format`（`json`・`csv`） | 案件のメンバーでなければ 404、ロールが違えば 403、`format` が違えば 422。実行が `succeeded` でない・出力のノードが無い → 409 `run_not_exportable`（「出力できる結果がありません（成功した実行で、出力のノードがあるものだけ）。」）。保存した出力から内容を再現できない → 409 `export_mismatch`（「出力の内容を再現できませんでした。」） | 200。`Content-Disposition: attachment; filename="run-<実行 ID>.<format>"`、`X-Content-Type-Options: nosniff`、`Cache-Control: no-store` |

## 2. CSV

- 文字コードは UTF-8（BOM 付き。Excel で開く前提）、改行は CRLF。
- 1 行目：ノードの設定 `title_ja`（あれば）。
- 見出し行：`区分,名前,値,重要度,結果`。
- 行：`判定,decision,<承認／修正して承認／却下>,,` → 項目ごとに `項目,<項目名>,<確認後の値>,,`（値が無ければ空、配列・数値は JSON）→ ルールごとに `ルール,<rule_id>,<message>,<severity>,<result>`。
- **CSV インジェクション対策**：どのセルも、先頭が `=`・`+`・`-`・`@`・タブ・CR なら先頭に `'` を付ける（負の金額も `'-500` になる）。

## 3. JSON

`{"export_id", "run_id", "decision", "fields", "findings"}`。値はデータのまま（無害化しない）。
