# P5-03c 実行記録

2026-10-23、PowerShell、リポジトリルート。対象 `fe581a5d84f0581712fe71afa8f68d9126c9bd54`。

| コマンド・確認 | 結果 |
|---|---|
| `git fetch origin main`、`git merge --ff-only origin/main`、`git switch -c codex/P5-03c-error-log-review` | 各0 |
| 初回 `PYTHONPATH=backend` でcheck_logs.py実行 | **1**、3ケースで合成値のログ混入。result.json・synthetic-logs.txt・run.log |
| ruff check / format | 作成途中はimport順・合成の固定鍵・行長等で1。鍵を未使用の一時生成へ変更し、整形・import順を修正。最終は各0 |
| `git apply --check .../proposed-fix.patch` | 初回1（Windows改行を含む差分）。差分だけLFで保存し直し、再確認0。製品は変更していない |
| 下記baseline診断 | **1**、baseline-result.json・baseline-synthetic-logs.txt。追加の型・構造化trace確認でも未修正を確認 |
| 下記candidate診断 | **0**、candidate-result.json・candidate-synthetic-logs.txt。隔離コピーの3ケースのみ |
| `git diff --exit-code -- backend/app contracts frontend/src` | 0 |

```powershell
$env:PYTHONPATH = 'backend'
$env:PYTHONUTF8 = '1'
backend/.venv/Scripts/python.exe reports/security/2026-10-23-g4/error-log/check_logs.py --label baseline
```

上記は安全条件を満たす場合だけ0を返す診断で、現状は1が再現結果。baselineの失敗をラッパーで成功へ読み替えない。

```powershell
& reports/security/2026-10-23-g4/error-log/verify_candidate.ps1
exit $LASTEXITCODE
```

このスクリプトは証跡ディレクトリ内の一時コピーにだけ差分を適用する。製品・実DB・外部ネットワークには書き込まない。候補の検証は作成中のPython補助でも0を確認し、最終的な再現手順はWindows標準のPowerShellに揃えて再実行した。修正案適用後に例外型の保持も追加確認し、baseline 1 / candidate 0を再確認した。

標準フォーマッタでの型・trace_idの表示を追加確認した際は、extraだけの旧候補でexit 1。`candidate-extra-only-*` にその結果を保存した。書式にも安全な型・trace_idを出す最終候補へ変更し、同じPowerShell手順でbaseline 1 / candidate 0、最終ruff・整形0を確認した。

```powershell
backend/.venv/Scripts/ruff.exe check --select E,F,I,B,UP,S,SIM,N reports/security/2026-10-23-g4/error-log/check_logs.py
backend/.venv/Scripts/ruff.exe format --check reports/security/2026-10-23-g4/error-log/check_logs.py
git apply --check reports/security/2026-10-23-g4/error-log/proposed-fix.patch
```

CVSSの暫定5.5はFIRSTの公式v3.1の定義と式を2026-10-23に確認し算出。実データ流出や実運用の権限を測定したものではない。

提出前：`python scripts/sync_skills.py --check` と `git diff --check` は各0、PowerShellのParserによるverify_candidate.ps1の構文検査もエラー0。今回の証跡のみを下記gitleaksで検査してexit 0・検出0、submission-secrets.json・.logに保存した。CI・統合コミットはGitとActionsの履歴で追跡する。

```powershell
$root = (Get-Location).Path
docker run --rm --name easf-p503c-submission --network none -v "${root}/reports/security/2026-10-23-g4/error-log:/report:ro" -v "${root}/reports/security/2026-10-23-g4/error-log:/out" zricethezav/gitleaks:v8.30.1 dir /report --redact --report-format json --report-path /out/submission-secrets.json
```
