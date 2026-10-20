# ベースライン（A）の進め方

EASF の比較実験（`docs/experiment/preregistration.md`）の **ベースライン（A）**：Factory（EASF）を使わずに、Claude Code / Codex と一般的な OSS だけで、契約書レビューの POC を作る。要件は `requirements.md`（凍結済み。Factory 側も同じものを使う）。

## 1. 準備

1. `python experiment/build_bundle.py --out <リポジトリの外のフォルダ>` で、この文書・要件・dev データをまとめたフォルダを作る（EASF のリポジトリの直下で実行。表示される SHA-256 が `DECISIONS.md` の記録と同じことを確かめる）。
2. 新しいフォルダ（例 `C:\work\aidd\easf-baseline-contract`）で `git init` し、上のフォルダの中身をコピーする。非公開のままにする。
3. そのフォルダで **新しい** Claude Code（または Codex）のセッションを始める。EASF の会話・メモリを持ち込まない。

## 2. 使ってはいけないもの

- EASF のリポジトリのコード・契約（`contracts/`）・Capability・Rule pack の JSON・評価のコード・skill（`easf-*` を含む `.claude/skills/`）。EASF のファイルを開かない。
- ホールドアウトの文書・正解。
- 一般的な OSS・ライブラリ（PDF の解析、OCR、Web の枠組みなど）とふつうの部品は使ってよい。LLM の実 API は使わない（EASF と同じく mock だけ。D-004）。

## 3. 作業時間の記録（主要指標 M1）

人の作業時間を `HUMAN_TIME_LOG.csv`（EASF のリポジトリの直下）に 5 分単位で記録する。AI が動いているだけの時間は数えない。

```
date,person,arm,phase,task_id,activity,minutes,note
2026-10-21,<名前>,baseline,P4,A-01,prompting,25,要件を読ませて設計を相談
```

- `arm` は `baseline`。`activity` は analysis・prompting・code_review・debugging・test_design・integration・qa・reporting のどれか。待っている時間は `waiting`（合計に入れない）。
- 作業の開始・終了ごとに書く。中断したら止める。迷う作業は note に内容を書き、分類は後で変えない。

## 4. 終わりの条件

- `requirements.md` §4 の受入条件（AC-06・AC-07・AC-09・AC-12）を自分で確かめた。
- dev 28 件について `requirements.md` §6 の形の出力を作れる。
- 終わったら、使った道具・モデルの版と、その時点の作業時間の合計を `HUMAN_TIME_LOG.csv` の note に書き、EASF の CC に「ベースライン完了」と伝える。そのあと Factory（B）が同じ要件で契約書を作る。
- 要件変更 CR-1 は、両 arm が終わってから同じ内容を渡す（まだ渡さない）。
