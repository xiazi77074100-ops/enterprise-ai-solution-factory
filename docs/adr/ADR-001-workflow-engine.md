# ADR-001 Workflow エンジン

| 項目 | 内容 |
|---|---|
| 状態 | 承認（D-001） |
| 日付 | 2026-10-18 |
| 作成 | Claude Code |
| 承認 | プロジェクト責任者 2026-10-18 |

## 状況
6〜8 ノードの小さな DAG を、版を固定した Capability で組み、検証・実行・一時停止（人の確認）・再開・トレースする。中核の価値（不変の版、3 か所のスキーマ検証、証跡、業務分岐の禁止）は、どのエンジンを選んでも EASF 側で作る必要がある。

## 選択肢
| 観点 | A 自前の型付き DAG | B LangGraph | C Temporal / Prefect |
|---|---|---|---|
| 構成 | 標準ライブラリ `graphlib` で順序付け、PostgreSQL の状態機械 | ライブラリ（LangChain 系の依存） | 別サーバ＋ワーカー |
| ライセンス | — | MIT | MIT / Apache-2.0 |
| Workflow をデータ（JSON）として持ち版を固定 | そのまま | 別に作る | 別に作る |
| 一時停止と再開 | DB の状態 | 組み込み | 組み込み |
| 攻撃面・依存 | 最小 | 中 | 大 |
| 1〜2 か月の POC | 適する | 可 | 過剰 |

## 決定
A。ループは持たない（`graphlib` が循環を検出したら構成エラー）。実行は 1 プロセスのワーカー（DB をキューに使う。行ロック `FOR UPDATE SKIP LOCKED`）。

## 理由
外部エンジンの利点（耐障害の再実行、分散）は POC の規模では効かず、Workflow をデータとして検証・凍結する部分は自作が必要なため。全部が見えるので「汎用エンジンに業務分岐がない」ことも示しやすい。

## 影響・やらないこと
- 状態機械（Run：`pending → running → waiting_review → running → succeeded / rejected / failed / cancelled`、NodeRun：`pending → running → succeeded / failed / skipped / waiting_review`）は詳細設計で定義する。確認で却下されたら Run は `rejected`、以降のノードは `skipped` で、出力しない（2026-10-18 追記、RV-G0-001）。
- 分散実行・並列ノードの同時実行は行わない（ready なノードを順に実行）。
- LangGraph などは将来の「外部 Agent ランタイム」のアダプタとして扱う。

## 確かめた資料
ライブラリの版・保守状況は Phase 1 の依存固定時に確認し、ここに追記する。
