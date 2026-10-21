# 契約書のホールドアウトの作り方（人だけが行う）

手順・守ることは請求書と同じ（`fixtures/HOLDOUT.md`）。違うところだけを書く。

- 件数：12 件。層は normal 3、missing_confidentiality 2、excessive_liability・auto_renewal・missing_notice・missing_governing_law・ambiguous・contradictory・injected_instruction 各 1（`fixtures/generator/contract.py` の `STRATA`）。
- 種は**請求書と別の新しい種**にする（会話・ファイルに書かない）。
- 生成（PowerShell、リポジトリの直下）：

  ```powershell
  $env:EASF_HOLDOUT_SEED = Read-Host -Prompt "秘密の種" -MaskInput
  $env:PYTHONPATH = "backend"
  uv run --project backend python -m fixtures.generator contract-holdout --out "$env:USERPROFILE\easf-holdout\contract"
  Remove-Item Env:EASF_HOLDOUT_SEED; Remove-Item Env:PYTHONPATH
  ```

  `fixtures/contract/manifest.holdout.json`（ハッシュだけ）がリポジトリに書かれる。出力先には `documents\`・`labels\`・`labels_cr1\`（要件変更 CR-1 の正解。CR-1 の評価まで使わない）ができる。
- 目で確かめる重大ラベル：層 `missing_confidentiality`・`injected_instruction`（CON-001、critical）と、`ambiguous`・`contradictory`。**ラベルは編集しない**。
- 凍結：`fixtures/contract/manifest.json` と `fixtures/contract/manifest.holdout.json` の SHA-256 を DECISIONS に記録する。

## 評価のとき（人が 1 回だけ実行する、P4-05）

1. 暗号化 ZIP（`%USERPROFILE%\easf-holdout-contract.zip`）を `%USERPROFILE%\easf-holdout\contract` に展開する（`documents\`・`labels\`・`labels_cr1\` ができる）。
2. Docker Desktop を起動し、リポジトリの直下で：

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\eval_holdout_contract.ps1
   ```

   - ベースライン（A）は自分の環境（`C:\work\aidd\easf-baseline-contract\.venv`）で、Factory（B）は Linux（Docker・Tesseract）で、凍結した版を実行する。
   - 両方の出力を同じ採点の道具（`app.evaluation.score_outputs`）で採点し、ファイルのハッシュを `fixtures/contract/manifest.holdout.json` と照合する。
   - 出力は `reports/eval/contract-holdout/baseline.json`・`factory.json` の集計値だけ。文書ごとの出力は一時フォルダに作り、最後に消す。
3. 展開したフォルダを消す（ZIP は残す）。
4. CC に「評価が終わった」と伝える。

