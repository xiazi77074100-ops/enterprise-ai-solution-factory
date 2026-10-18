---
name: easf-phase-gate
description: EASF のフェーズとゲート（G0〜G5）の運用。フェーズ・タスクの着手前の確認、作業中の止まる条件、ゲート報告書、Claude Code から Codex への引き渡し書、台帳（DECISIONS.md・TASK_STATUS.md・CHANGELOG.md・COST_LEDGER.csv・HUMAN_TIME_LOG.csv）の書き方、正直な報告の規則。フェーズやタスクを始める・終える、ゲート報告を書く、Codex に作業を渡す、費用・工数・決定を記録する、「次のフェーズ」「承認」「進捗報告」と言われたときに使う。
---

# easf-phase-gate — フェーズとゲートの運用

正本は `easf_package/tasks/PHASE_PLAN.md`・`TASK_BOARD.csv`・`docs/03_ACCEPTANCE_AND_EXPERIMENT.md`。ここはその運用手順。

## 1. 着手前（毎回）

次を確かめ、1 つでも欠けたら作業を始めずに人間へ確認する。

1. 直前のゲートが人間に承認されている（承認の記録：`DECISIONS.md` の行、または人間の明示の指示）。
2. 今回のフェーズ ID と、承認されたタスク ID（`TASK_BOARD.csv`）。
3. 自分が変えてよいパス（`AGENTS.md` の所有表・引き渡し書）。共通契約（`contracts/`）・マイグレーションを変える必要があれば止まる。
4. 関係する受入条件（AC-xx）と、それを示すテスト・証跡のパス。
5. 時間・費用の見込みと、追加現金支出の累計（10,000 円の上限に対して）。

着手時に、上の 5 点を日本語で短く宣言してから始める。

## 2. 作業中に止まる条件

- 契約（OpenAPI・Capability / Workflow スキーマ・イベント）を変える必要が出た。
- 承認されていない範囲に広がる（変更要求を書いて止まる）。
- 有料の API・サービスを新しく使う、または費用の累計が上限に近づいた。
- ホールドアウトのラベルが見える状態になった・見てしまった（`easf-eval-integrity`）。
- 会社・顧客の資産を使う必要が出た。
- セキュリティの高・中の指摘を直せない。

## 3. 台帳（G0 承認後にリポジトリ直下に作り、事実だけを書く）

| ファイル | 列・中身 |
|---|---|
| `DECISIONS.md` | `D-NNN`・日付・決定・理由・決めた人・関連 ADR。承認・却下・受容したリスクもここ |
| `TASK_STATUS.md` | タスク ID・担当・状態（未着手／作業中／レビュー待ち／完了／中止）・ブランチ・証跡・更新日 |
| `CHANGELOG.md` | ゲートごとの変更点（利用者に見える変化と契約の変化） |
| `COST_LEDGER.csv` | `date,category,item,amount_jpy,currency_original,amount_original,source,arm,phase,note`。category は `model_api` / `infrastructure` / `tool` / `other`。arm は `factory` / `baseline` / `shared`。**推定値は note に「推定」と書く** |
| `HUMAN_TIME_LOG.csv` | `date,person,arm,phase,task_id,activity,minutes,note`。activity は `analysis` / `prompting` / `code_review` / `debugging` / `test_design` / `integration` / `qa` / `reporting` / `waiting`。人間の時間だけ（AI の実行時間は別） |

## 4. ゲート報告

`reports/gate_G<id>.md` に `references/gate-report-template.md` の形で書き、**止まって人間の判断を待つ**。次のフェーズへ自分で進まない。

報告の規則：
- 実行したコマンド・終了コード・結果の要点・ログのパス・コミット SHA を付ける。
- 実行していないものは「未実行」と理由。失敗は失敗と書く。「おそらく通る」「概ね成功」と書かない。
- 数値（精度・時間・費用・削減率）は測った値だけ。測っていない数値・目標値を実績のように書かない。
- 模擬（MOCK）で動かしたものは模擬と明記し、実接続として数えない。

## 5. Codex への引き渡し

G0 で契約が凍結されるまで並行実装を渡さない（レビュー・テスト設計は渡してよい）。渡すときは `references/handoff-template.md` の形で、入力・出力・変えてよいパス・テスト・受入条件を書く。Codex の成果は契約テスト・独立レビューを通してから CC がマージする。

## 6. 進捗報告（人間へ）

日本語で、次の順に短く：やったこと → 変更したファイル → 実行したテストと結果 → 失敗・未解決 → 時間と費用（実績） → 次の提案 → 人間に決めてほしいこと。

## references

- [gate-report-template.md](references/gate-report-template.md)
- [handoff-template.md](references/handoff-template.md)
