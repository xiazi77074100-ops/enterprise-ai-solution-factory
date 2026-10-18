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
4. 重大ラベル（層 `total_mismatch`・`payee_changed`・`ambiguous`・`injected_instruction`）を 1 件ずつ目で確かめ、ラベルの `reviewed_by` に名前を書く（ZIP を作る前に）。
5. `fixtures/manifest.json` と `fixtures/manifest.holdout.json` の SHA-256 を計算し、`DECISIONS.md` に記録する（**凍結**）。以後、閾値・ホールドアウト・成功の定義を変えない。

   ```sh
   sha256sum fixtures/manifest.json fixtures/manifest.holdout.json
   ```

6. `fixtures/manifest.holdout.json` をコミットする（ハッシュだけなので AI が見てよい）。

## 評価のとき

ホールドアウトでの評価は人が実行し、AI には集計値（項目ごとの正解率・ルールの適合率と再現率など）だけを渡す。誤りの具体例は人が見て、必要なら dev に似た例を足す（ホールドアウトの文書そのものは渡さない）。
