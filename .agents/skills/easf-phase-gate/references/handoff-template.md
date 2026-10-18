# Codex への引き渡し書の書式

`handoffs/<task-id>.md` に置き、Codex にはこのファイルのパスと `easf_package/prompts/01_CODEX_PARALLEL.md` を渡す。

```markdown
# 引き渡し <task-id>：<題名>

| 項目 | 内容 |
|---|---|
| フェーズ / ゲート | Phase n / G… |
| ブランチ | codex/<task-id>-<slug>（main の <SHA> から） |
| 前提の契約 | contracts/openapi.yaml @ <SHA>、contracts/capability.schema.json v1 … |

## 目的
## 入力（読むもの）
## 出力（作るもの）
## 変えてよいパス
- …
## 変えてはいけないパス
- contracts/、backend/migrations/、AGENTS.md、.claude/skills/（必要なら変更要求として報告）
## 受入条件
| AC / 条件 | 確かめるテスト | 期待結果 |
## 守る skill
jp-secure-coding、jp-dev-standards、（UI なら）japan-enterprise-frontend、（データなら）easf-eval-integrity
## 記録
HUMAN_TIME_LOG.csv（arm・task_id を付ける）、COST_LEDGER.csv
## 提出
PR の説明：範囲・変更ファイル・実行したテストと結果・制約・リスク・破壊的変更・費用。マージはしない。
```
