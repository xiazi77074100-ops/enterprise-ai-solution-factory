# ホールドアウトの作り方（人だけが行う）

ホールドアウト（請求書 12 件）は評価の公正さのため、**人だけが知る秘密の種**で生成し、**リポジトリの外**に置く（`docs/design/fixture_plan.md` §6、skill `easf-eval-integrity` §2）。AI（Claude Code・Codex）にはホールドアウトの文書・ラベルを見せない。リポジトリに残るのはハッシュだけ。

## 手順

1. 秘密の種を決める（推測されにくい長い文字列。どこにも書かない。紛失すると同じ文書は作り直せないが、文書そのものは手順 3 の ZIP に残る）。
2. リポジトリの直下で、自分の端末から実行する（AI のセッションでは実行しない）：

   ```sh
   # Git Bash の例。出力先はリポジトリの外
   export EASF_HOLDOUT_SEED='（秘密の種）'
   PYTHONPATH=backend uv run --project backend python -m fixtures.generator holdout --out "$USERPROFILE/easf-holdout/invoice"
   unset EASF_HOLDOUT_SEED
   ```

   - 出力先がリポジトリの中なら止まる。種が無ければ止まる。
   - `fixtures/manifest.holdout.json`（各文書・ラベルの SHA-256 だけ）がリポジトリに書かれる。
3. 出力したフォルダを AES-256 の暗号化 ZIP にし（パスワードは人だけ）、元のフォルダを消す。
4. 重大ラベル（層 `total_mismatch`・`payee_changed`・`ambiguous`・`injected_instruction`）を 1 件ずつ目で確かめる（ZIP を作る前に）。**ラベルのファイルは編集しない**（手順 2 で `label_sha256` を記録済みのため、編集するとハッシュが合わなくなる）。確かめた人・日付・`sample_id` は手順 5 の `DECISIONS.md` の行に書く。誤りを見つけたら、フォルダを消して手順 2 からやり直し、CC に生成器の不具合として（文書の中身は伝えずに）知らせる。
5. `fixtures/manifest.json` と `fixtures/manifest.holdout.json` の SHA-256 を計算し、`DECISIONS.md` に記録する（**凍結**）。以後、閾値・ホールドアウト・成功の定義を変えない。

   ```sh
   sha256sum fixtures/manifest.json fixtures/manifest.holdout.json
   ```

6. `fixtures/manifest.holdout.json` をコミットする（ハッシュだけなので AI が見てよい）。

## 評価のとき（人が実行する）

1. 暗号化 ZIP をリポジトリの外に展開する（例：`%USERPROFILE%\easf-holdout\invoice` に `documents\`・`labels\`）。
2. Docker Desktop を起動し、リポジトリの直下で（PowerShell）：

   ```powershell
   pwsh scripts/eval_holdout.ps1          # 別の場所なら -HoldoutDir <フォルダ>
   ```

   - Linux（Docker）で Tesseract を入れて、最終の版（`fixtures/workflows/invoice-v3.json`、Rule pack `invoice@1.1.0`）を実行する。フォルダは読み取り専用でつなぐ。
   - すべての文書とラベルの SHA-256 を `fixtures/manifest.holdout.json` と照合し、1 つでも違えば止まる。
   - 出力は `reports/eval/holdout/result.json` の**集計値だけ**（件数・割合・ルールごとの件数。sample_id・値・誤りの例は書かない）。AI が読んでよいのはこのファイルだけ。
3. 展開したフォルダを消す。
4. CC に「終わった」と伝える。誤りの具体例は人が見て、必要なら dev に似た例を足す（ホールドアウトの文書そのものは渡さない）。ホールドアウトの評価は 1 回だけ（何度も回して版を選ばない）。
