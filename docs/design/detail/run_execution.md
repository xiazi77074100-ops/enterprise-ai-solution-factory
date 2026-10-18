# 詳細設計：Solution・実行（Run）・確認（Review）

| 版 | 日付 | 変更内容 | 作成者 |
|---|---|---|---|
| 0.1 | 2026-10-18 | 初版（P2-00） | Claude Code |

前提：ADR-001（自前の型付き DAG、DB をキュー、1 プロセスのワーカー）、ADR-002（LlmPort、mock のみ）、ADR-005（MCP）、契約 v1.0.1。API の形は `contracts/openapi.yaml` が正で、ここは内部の動きを書く。

## 1. Solution の状態

```
draft ──validate(ok)──▶ validated ──approve──▶ approved
  ▲                         │
  └────── update ───────────┘   （validated を更新すると draft に戻る）
```

| 操作 | 条件 | 結果 |
|---|---|---|
| 作成（createSolution） | solution_architect。要件の版は同じ案件のもの | `draft`。`workflow_hash` は作成時から計算する |
| 更新（updateSolutionDraft） | `draft` か `validated`。`If-Match` が現在の ETag と一致（違えば 412） | `draft`、ハッシュを再計算。`approved`・`archived` は 409 |
| 検証（validateSolution） | 任意の状態で実行できる（副作用は `draft` → `validated` だけ） | Composer の結果。エラーなしで `draft` なら `validated` |
| 承認（approveSolution） | solution_lead、作成者以外、`validated` で、承認の直前にもう一度検証してエラーなし | `approved`。`workflow` と `workflow_hash` は以後変更不可（アプリと DB トリガー） |

- `workflow_hash` は RFC 8785（JCS）の正規形の SHA-256（Catalog と同じ関数）。
- ETag は `"<workflow_hash>:<更新回数>"`。
- `archived` は契約にあるが、v1 では操作がない（予約）。

## 2. Composer の検証

順に検査し、見つけた問題をすべて `ValidationIssue`（`code`・`path`・`message`）で返す。スキーマ違反があれば以降の検査はしない。

| # | 検査 | code |
|---|---|---|
| 1 | `workflow.schema.json` に合う | `schema` |
| 2 | `node_id` が一意、`edges`・`inputs[].to`・`outputs[].from_node` の参照先が存在 | `duplicate_node`・`unknown_node` |
| 3 | 各ノードの `capability_id@capability_version` が Catalog に登録済み | `unknown_capability_version` |
| 4 | 実装キーが許可リストにあり、`available=True`（コードがある） | `implementation_unavailable`（**警告**。検証は通るが、承認と実行は不可） |
| 5 | `config` が版の `configuration_schema` に合う | `config_schema` |
| 6 | `timeout_ms` ≤ 版の `timeout_ms` | `timeout_exceeds_capability` |
| 7 | 循環がない（標準ライブラリ `graphlib`） | `cycle` |
| 8 | 辺の `from_path` が出所のノードの `output_schema` で解決でき、その型が行き先の入力欄の型と合う | `unknown_output_path`・`unknown_input_field`・`type_mismatch` |
| 9 | 各ノードの入力の必須欄が、辺かワークフローの入力のどちらかからちょうど 1 回与えられる | `missing_input`・`duplicate_input` |
| 10 | ワークフローの入力の型と、渡し先の入力欄の型が合う（`document_ref` は `string`・`format: uuid`） | `type_mismatch` |
| 11 | `outputs[].from_path` が解決できる | `unknown_output_path` |
| 12 | どのノードも入力か辺につながっている（孤立なし） | `unreachable_node` |
| 13 | `review.human` を含まず `requires_human_approval: false` の場合 | 警告 `no_human_review` |

型の整合（#8・#10）：JSON Schema の `type` を比べる。出所が行き先と同じか、より狭い（`integer` → `number` は可）なら可。`type` がない・`object` 同士はキーの検査をしない（実行時の入力スキーマ検証で必ず確かめる）。

## 3. Run の状態と NodeRun の状態

```
Run:     pending ─▶ running ─▶ waiting_review ─▶ running ─▶ succeeded
                       │              │                    └▶ failed
                       └▶ failed      └▶ rejected
NodeRun: pending ─▶ running ─▶ succeeded
                       │   └─▶ waiting_review ─▶ succeeded（承認・修正付き承認）／failed（却下は Run を rejected）
                       └▶ failed
         pending ─▶ skipped（Run が rejected・failed になったとき、未実行のノード）
```

| Run の状態 | 意味 | 出力・再利用の証跡 |
|---|---|---|
| `succeeded` | 全ノードが成功、確認はすべて承認 | 可 |
| `rejected` | 確認で却下 | 不可（出力しない） |
| `failed` | 失敗（`failure_code` に理由） | 不可 |
| `cancelled` | 予約（v1 に操作なし） | 不可 |

`failure_code`：`node_failed`・`timeout`・`budget_exceeded`・`invalid_input`・`invalid_output`・`no_reviewer`・`implementation_unavailable`・`interrupted`（再試行の上限を超えた異常終了）。

## 4. 実行の流れ

1. **開始（startRun）**：Solution が実行できる状態（`requires_human_approval` なら `approved`、そうでなければ `validated` 以上）か確かめる。入力を `workflow.inputs` の型で検証（名前の過不足・型。`document_ref` は Phase 2 では文書が無いので 422）。`Idempotency-Key` が同じ利用者・同じ Solution で既にあれば元の Run を返す（本文が違えば 409）。Run（`pending`）と全ノードの NodeRun（`pending`）を作り、`run.started` を記録して 202。
2. **ワーカー**：`SELECT … FOR UPDATE SKIP LOCKED` で、`pending`・`running` かつリース切れの Run を 1 件取り、リース（`lease_until`）を延ばしながら進める。
3. **次のノード**：`graphlib.TopologicalSorter` の順で、依存がすべて `succeeded` のノードを 1 つずつ実行する（並列にしない）。
4. **入力の組み立て**：ワークフローの入力と、依存ノードの出力から JSON Pointer で取り出した値。**入力スキーマで検証**（1 か所目）。違えば NodeRun `failed`（`invalid_input`）。
5. **アダプタの呼び出し**：`timeout = min(ノードの timeout_ms, 版の timeout_ms, 予算の残り時間)`。
6. **出力の検証**：**出力スキーマで検証**（2 か所目。3 か所目は Composer での設定の検証）。違えば `invalid_output`。出力の大きさの上限は 1 MiB。
7. **記録**：NodeRun に入力・出力の SHA-256（JCS）、所要時間、`execution_mode`、使用量。出力そのものは DB の NodeRun にだけ保存し、トレースにはハッシュと件数だけ。
8. **再試行**：時間切れ・アダプタの一時的な失敗で、版の `retry.idempotent` が真なら `retry.max_attempts` まで（NodeRun の `attempt` を増やす）。不正な出力は再試行しない。
9. **予算**：ノードの前後で、経過時間・LLM のトークン・円を Workflow の `budget` と比べ、超えたら Run を `failed`（`budget_exceeded`）。
10. **終了**：全ノード成功で `succeeded`。失敗したら残りを `skipped` にして `failed`。`outputs` は `succeeded` のときだけ組み立てる。

### 異常終了からの回復

- ワーカーが落ちると Run のリースが切れ、次のワーカー（再起動後の同じワーカーを含む）が拾い直す。
- `running` のまま残った NodeRun は「中断」とみなし、版が冪等で再試行が残っていれば `attempt` を増やして再実行、そうでなければ `failed`（`interrupted`）。

## 5. 実行の方式（アダプタ）

| kind | Phase 2 | 方式 |
|---|---|---|
| `local` | 実装 | 許可リストのキー（`app/catalog/registry.py`）に結び付けた関数だけを呼ぶ。**動的 import はしない**。関数は子プロセス（`multiprocessing` の spawn）で実行し、時間切れで強制終了する |
| `llm` | mock のみ | `LlmPort`。mock は入力のハッシュから決まる固定の出力を返し、`execution_mode: mock` |
| `mcp_tool`・`rest` | インタフェースのみ | 呼ぶと `implementation_unavailable` |

`review.human`（`human_review.v1`）はアダプタを通さず Executor が扱う：確認タスクを作り、NodeRun と Run を `waiting_review` にしてワーカーを離れる。

## 6. 人の確認

- **割り当て**：その案件で `business_reviewer` のロールを持つメンバーのうち、未完了の確認タスクが最も少ない人（同数なら利用者 ID の順）。いなければ Run を `failed`（`no_reviewer`）。
- **確認の項目**：入力の `fields`・`findings`・`evidence` から作る（`ReviewItem`）。
- **決定（decideReviewTask）**：割り当てられた本人だけ（他は 403、案件外は 404）。`pending` のときだけ（完了済みは 409）。`Idempotency-Key` が同じなら元の結果を返す。
  - `approved`：出力は `reviewed_fields = fields`、`corrections = []`。
  - `approved_with_corrections`：修正の `path` は `/fields/<名前>` の形だけ受け付け、`reviewed_fields` に反映する。修正前後の値のハッシュ・修正者・時刻をトレースに残す（AC-07）。
  - `rejected`：Run を `rejected`、残りのノードを `skipped`。
- 決定の後、Run を `running`（承認）にしてワーカーに戻す。

## 7. トレース（イベント）

- `contracts/events.schema.json` の形で、`run_events` 表に追記するだけ（更新・削除は DB トリガーで拒否）。
- `prev_event_hash`：同じ Run の直前のイベントの SHA-256（JCS）。最初は `null`。
- `redacted_metadata` に入れてよいのは、ハッシュ・件数・所要時間・コード・版。文書の本文・抽出値・修正の値・秘密は入れない。
- 取得（getRunTrace）は時刻順のページ送り。連鎖が壊れていないかを検査する関数を用意し、テストで確かめる。

## 8. 表（マイグレーション）

| 表 | 主な列 |
|---|---|
| `solutions` | id、project_id、requirement_revision_id、state、workflow（jsonb）、workflow_hash、revision（更新回数）、created_by、approved_by、approved_at、created_at、updated_at |
| `runs` | id、solution_id、project_id、workflow_hash、status、execution_mode、trace_id、inputs（jsonb）、input_sha256、failure_code、usage（jsonb）、created_by、idempotency_key、request_sha256、lease_until、started_at、finished_at |
| `node_runs` | id、run_id、node_id、capability_version_id、status、execution_mode、attempt、duration_ms、input_sha256、output_sha256、output（jsonb）、error_code、usage（jsonb） |
| `review_tasks` | id、run_id、node_run_id、node_id、status、assigned_to、items（jsonb）、decision、corrections（jsonb）、comment、decided_by、decided_at、idempotency_key |
| `run_events` | id、run_id、seq、event（jsonb）、event_hash |

承認済みの `solutions` の `workflow`・`workflow_hash` の変更と、`run_events` の更新・削除は DB トリガーで拒否する（Catalog と同じ方式）。
