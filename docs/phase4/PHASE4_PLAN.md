# Phase 4 計画（契約書の POC と再利用の証明、ゲート G3）

| 版 | 日付 | 変更内容 | 作成者 |
|---|---|---|---|
| 0.1 | 2026-10-19 | 初版（P4-00、承認待ち） | Claude Code |
| 0.2 | 2026-10-20 | 承認（D-038）、P4-01 で見つけた論点を §5 に追記 | Claude Code |

## 1. 着手前の確認（easf-phase-gate §1）

| # | 項目 | 内容 |
|---|---|---|
| 1 | 直前のゲート | G2 承認済み（D-037） |
| 2 | フェーズとタスク | Phase 4（`easf_package/tasks/PHASE_PLAN.md`）：P4-01 契約書の Rule pack と Workflow の設定、P4-02 再利用の証拠と要件変更の実験。本計画で §4 に分ける |
| 3 | 変えてよいパス | `fixtures/`（契約書の生成器・dev）、`experiment/`、`docs/`、台帳。エンジン（catalog・composer・executor・adapters・evaluation）は**原則変えない**（変えたら再利用の分類 `new_code` として記録）。`contracts/` は変えない |
| 4 | 受入条件 | G3：コピーした業務専用の流れを作らない（no copied hardcoded pipeline）、同じ不変の Capability 版の再利用と回帰の証拠。AC-06・AC-07・AC-09・AC-12（契約書）、事前登録（`docs/experiment/preregistration.md`）の M1〜M5 |
| 5 | 時間・費用 | 追加現金支出 0 円の見込み（LLM は mock、D-004）。**人の作業時間の記録が主要指標（M1）になる**（§3） |

## 2. 事前登録で決まっている順序（ADR-008、preregistration §4。変えない）

1. Phase 3：Factory で請求書（済み）。
2. **ベースライン（A）で契約書を作る**：別リポジトリ（`easf-baseline-contract`、非公開）・別セッション。EASF のコード・契約・Capability・Rule pack・評価コード・`easf-*` の skill を使わない。
3. **Phase 4：Factory（B）で契約書を作る**（このリポジトリ）。
4. 両 arm で同じ要件変更 CR-1（反社会的勢力の排除条項の抽出と critical のルール）。
5. 人が holdout で両 arm を評価する。

したがって、Factory で契約書の業務の設定・コードを作る（§4 の P4-03 以降）のは、**ベースラインが終わってから**。その前に、両 arm に共通の準備（合成データ・要件パッケージ）を作る。

## 3. 人の作業時間の記録（M1）

- M1 は「2 件目の業務（契約書）の POC を作る**人の**作業時間」。A と B の両方で、`HUMAN_TIME_LOG.csv`（`date,person,arm,phase,task_id,activity,minutes,note`）に 5 分単位で記録する。AI の実行時間は数えない。
- B（Factory）では CC が実装の大半を行うため、人の時間は「指示・確認・判断・レビュー・評価の実行」が中心になる。A でも同じ道具（Claude Code / Codex）を使うので、条件はそろう。
- 記録は**準備（P4-01・P4-02）の後、A の着手から**始める。準備は両 arm 共通なので M1 に入れない（`arm=shared` で記録してよい）。
- G2 報告の回答では「後で決める」（D-033）だったが、Phase 4 では記録が無いと実験の主要指標が出せない。

## 4. タスク（順に。タスクごとに CI の成功を確かめてから main へ）

| タスク | 担当 | 内容 | 主な証跡 | 前提 |
|---|---|---|---|---|
| P4-00 | CC | 本計画 | — | G2 承認 |
| P4-01 | CC | 契約書の合成データ：生成器（`docs/design/fixture_plan.md` §2.2 の層、条項番号の 3 種、2〜6 ページ、スキャン、不審な指示）、dev 28 件・正解ラベル・manifest、生成器のテスト、ホールドアウトの手順（請求書と同じ） | 層の件数、根拠の範囲の一致、架空の名前、Windows・Linux で同じバイト列 | 本計画の承認 |
| （人） | 人 | 契約書のホールドアウト 12 件の生成と凍結（`fixtures/HOLDOUT.md` と同じ手順） | DECISIONS の行 | P4-01 |
| P4-02 | CC | ベースラインに渡す要件パッケージ `experiment/baseline_bundle/`（preregistration §3：業務の説明、抽出項目の表〔文章〕、確認ポリシー〔文章〕、受入条件、dev データ）。SHA-256 を DECISIONS に記録 | バンドルの SHA-256 | P4-01 |
| （A） | 人（＋別セッションの AI） | ベースラインで契約書の POC（別リポジトリ・別セッション）、CR-1、人の作業時間の記録（`arm=baseline`） | ベースラインのリポジトリ、時間の記録 | P4-02、凍結 |
| P4-03 | CC（人の時間を記録） | Factory で契約書：Workflow の設定（`field_spec`・見出し）と Rule pack（`contract@1.x`）だけで足りるか確かめ、足りなければ新しい Capability 版（例：条項の見出しで区切る抽出、真偽の項目）を作り、再利用の分類（`unchanged`・`config_only`・`new_code`）を記録 | 端から端までのテスト、再利用の記録 | （A）の完了 |
| P4-04 | CC（人の時間を記録） | 要件変更 CR-1、再利用の証拠（同じ `capability_version_id` が請求書と契約書の実行で動いた記録）、請求書の回帰（変わらないこと） | トレースに結び付いた証拠、回帰テスト | P4-03 |
| P4-05 | CC・人 | dev の評価、人が holdout で両 arm を評価（arm の名前を伏せる）、G3 前の診断、`reports/gate_G3.md` | G3 報告 | P4-04 |

## 5. 見込まれる技術的な論点（P4-03 で確かめる。いまは決めない）

- 契約書は「見出し：値」ではなく条項（「第 N 条（秘密保持）」）の文章。今の `rule_based_extractor.v1` は真偽（`auto_renewal`、critical）を `uncertain` にする。設定だけで足りなければ新しい版が要り、その場合は `new_code` として正直に記録する（`easf-capability-contract` §5）。
- `rule_validator.v1` は `eq`・`ne` で真偽を比べられず、CON-003（`auto_renewal` が false か）は常に uncertain になる（P4-01 で確認）。直すのは Factory 側の作業なので P4-03 で行い、実装の修正として記録する（ベースラインの前には直さない）。
- 業務名をエンジンに書かない（`scripts/validate_contracts.py`）。違いは設定・Rule pack・抽出の項目の指定で表す。

## 6. 人に決めていただきたいこと

1. 本計画（特に §2 の順序：ベースラインを先に行う）の承認。
2. ベースライン（A）を誰がいつ行うか（人が別リポジトリ・新しいセッションで Claude Code / Codex を使う。EASF の会話・メモリを持ち込まない）。
3. 人の作業時間の記録の開始（§3。A の着手から両 arm で記録）。
