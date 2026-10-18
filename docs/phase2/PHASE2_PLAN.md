# Phase 2 計画（Workflow と観測、ゲート G1b）

| 版 | 日付 | 変更内容 | 作成者 |
|---|---|---|---|
| 0.1 | 2026-10-18 | 初版 | Claude Code |

## 1. 着手前の確認（easf-phase-gate §1）

| # | 項目 | 内容 |
|---|---|---|
| 1 | 直前のゲート | G1a 承認済み（D-024） |
| 2 | フェーズとタスク | Phase 2。P2-01〜P2-04（`easf_package/tasks/TASK_BOARD.csv`）と、本計画で足す P2-00（計画・詳細設計・テスト専用 DB）。すべて CC（D-024） |
| 3 | 変えてよいパス | `backend/`（`app/{composer,executor,adapters}` を新設）、`backend/migrations/`、`frontend/`、`docs/`、台帳。**`contracts/` は変えない**（凍結。必要になったら止まって変更要求） |
| 4 | 受入条件 | G1b：再現できる端から端までのトレース、否定テスト、Executor に業務ごとの分岐がないこと。AC-03（Workflow の構成・検証・実行）、AC-07（確認の修正の保存とトレース）、AC-09（重大な誤りを黙って通さない）、AC-13（実行と模擬の区別）の基盤部分 |
| 5 | 時間・費用 | 追加現金支出 0 円の見込み（LLM は D-004 により mock だけ）。累計 0 円 / 上限 10,000 円 |

## 2. 範囲

**やること**

- Composer：Workflow（`contracts/workflow.schema.json`）の検証。版の固定・設定のスキーマ・辺の型の整合・循環・予算・入出力の網羅。
- Solution の API（作成・取得・下書きの更新・検証・承認・一覧）。承認で `workflow_hash` を凍結。
- Executor：Run・NodeRun の状態機械、DB をキューにしたワーカー、時間切れ・再試行・予算・異常終了からの回復。
- アダプタ：`local`（許可リストのキーに結び付けた関数を子プロセスで実行）、`llm`（ADR-002 の `LlmPort`。**mock だけ**）、`mcp_tool`・`rest`（インタフェースのみ。実装は Phase 3 以降）。
- 人の確認（`review.human` / `human_review.v1`）：確認タスクの作成・割り当て・決定・再開・却下。
- トレース：追記専用のイベント（`contracts/events.schema.json`、ハッシュ連鎖）と、Run・NodeRun・トレースの取得 API。
- 実行・確認の画面（P2-03）、Executor の敵対的テスト（P2-04）。

**やらないこと（Phase 3 以降）**

- 文書のアップロード・解析・抽出・ルール判定・出力（`document_parser.v1`・`rule_based_extractor.v1`・`rule_validator.v1`・`result_exporter.v1`・`easf_local_mcp:locate_evidence`）。`exportRunResult` と文書の API も Phase 3。
- 実 LLM API の呼び出し（D-004）。
- 実行の取り消し（`cancelled`）の API は契約 v1 にない。状態としては予約し、使わない。

## 3. G1b で何を示すか

業務の Capability は Phase 3 で作るため、G1b の「端から端まで」は次で示す。**業務の Capability を実行したようには書かない。**

- 汎用の試験用 Capability（`testkit.*`。テストの中でだけ Catalog に登録し、実装もテストの中で Executor に渡す。本番の許可リストには入れない）と、本物の `review.human` を組んだ Workflow を、検証 → 承認 → 実行 → 確認で一時停止 → 決定 → 再開 → 成功／却下まで、実 PostgreSQL・実ワーカーで流す。
- 同じ入力で 2 回実行し、入力・各ノードの入出力のハッシュとイベントの並びが一致すること（再現性）。
- LLM の経路は mock アダプタで通し、Run の `execution_mode` が `mock`／`mixed` になること（AC-13）。
- `backend/app/{composer,executor,adapters}` に業務名（請求書・契約書など）がないことは、既存の `scripts/validate_contracts.py` の検査で確かめる。

## 4. タスク

順に行い、タスクごとにコミット → プッシュ → CI の成功を確認 → `main` に fast-forward（D-013、G1a §8-2）。

| タスク | 内容 | 主な証跡 |
|---|---|---|
| P2-00 | 本計画、詳細設計（`docs/design/detail/run_execution.md`）、テスト専用 DB（G1a §8-3） | テストが開発用 DB のデータを消さない |
| P2-01 | Composer と Solution の API、`solutions` のマイグレーション | 検証の否定テスト（循環・型の不整合・未登録の版・設定違反・予算・孤立したノード）、承認の規則、契約テストの PENDING から外す |
| P2-02 | Executor・アダプタ・Run と確認の API・トレース | 端から端までのテスト、状態遷移のテスト、再現性のテスト |
| P2-04 | Executor の敵対的テスト | 時間切れ・無限ループ・不正な出力・巨大な出力・例外・予算超過・ワーカーの異常終了・二重起動・確認の横取り |
| P2-03 | 実行・確認の画面 | Playwright（1440px・390px）、`ui-design` §9 |
| G1b | 脆弱性の再診断（追加した API）とゲート報告 | `reports/gate_G1b.md` |

## 5. リスク

| リスク | 対策 |
|---|---|
| 子プロセスでの実行が Windows で遅い（spawn） | ローカルの実行は 1 ノード 1 子プロセス。遅さは測って報告する。Phase 3 で問題になれば ADR を追加 |
| 契約 v1 で足りない点が見つかる | 止まって変更要求（DECISIONS）。勝手に契約を変えない |
| 自己レビューだけになる（D-024） | `easf_package/prompts/02_REVIEW_GATE.md` の観点で G1b 前に自己レビューし、報告に明記（D-012） |
