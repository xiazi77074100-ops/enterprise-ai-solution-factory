# 実行手順・確認結果

2026-10-23、PowerShell、リポジトリルート。すべてローカルEASFの自己診断。`git fetch origin main`、`git merge --ff-only origin/main`、`git switch -c codex/P5-03a2-semgrep-copy` は各exit 0。

## 規則の取得

`semgrep-followup/` を作成してから実行し、出力を `rules-download.log` に保存。exit 0。公開規則の内容は可変のため、再実行時はログ中のSHA-256と照合する。今回はOWASPだけ前回と不一致であり、新しい規則として記録した。

```powershell
$root = (Get-Location).Path
docker run --rm --name easf-p503a2-rules --cpus 1 -v "${root}/reports/security/2026-10-23-g4/semgrep-followup:/out" --entrypoint sh semgrep/semgrep:1.180.0 -c 'mkdir -p /out/rules; for pack in python owasp-top-ten react typescript secrets; do wget -T 20 -O /out/rules/$pack.yml https://semgrep.dev/c/p/$pack || exit 1; done; sha256sum /out/rules/*.yml'
```

## 検査

実際の引数・マウント・timeoutは [run.ps1](run.ps1)。次の順で実行した。最初のdirect呼出時は外側の `exit $LASTEXITCODE` を省略しており、ツール呼出の終了コードは1だった。内部とDockerの記録は143。以降は終了コードを明示して伝播する。

```powershell
& reports/security/2026-10-23-g4/semgrep-followup/run.ps1 -Scope smoke -Pack python -Placement direct
& reports/security/2026-10-23-g4/semgrep-followup/run.ps1 -Scope smoke -Pack python -Placement copy
& reports/security/2026-10-23-g4/semgrep-followup/run.ps1 -Scope product -Pack python -Placement copy; exit $LASTEXITCODE
```

最後の4組は別のPowerShell呼出で順番に実施。各Docker終了コード0、ループの終了コード0。

```powershell
$scanFailures = 0
foreach ($pack in @('owasp-top-ten', 'react', 'typescript', 'secrets')) {
    & reports/security/2026-10-23-g4/semgrep-followup/run.ps1 -Scope product -Pack $pack -Placement copy
    if ($LASTEXITCODE -ne 0) { $scanFailures++ }
}
if ($scanFailures -gt 0) { exit 1 }
```

## 対象と結果の照合

各JSONのresults・errors・paths、各 `-run.json` の終了コード・実時間、各ログの `Ran N rules on M files` と `[WARNING]` を読み、summary.jsonに集約した。`/tmp/src/` を除いた解析対象の集合と `git ls-files backend/app frontend/src` を `Compare-Object` で照合：追跡98・解析98・差分0、exit 0。5結果はすべてerrors 0、終了コード0。警告はJSONのerrorsとは別に記録した。

`git diff --exit-code -- backend/app frontend/src` はexit 0。診断後、取得した規則5ファイルだけを絶対パス確認後に削除した。ログは本文・結果を変えず、LFへの統一と行末空白の除去を行う。CIと統合コミットはGit・Actionsの履歴から追跡する。

## 提出前の限定検査

PowerShellの `System.Management.Automation.Language.Parser.ParseFile` でrun.ps1を構文検査しエラー0、`backend/.venv/Scripts/python.exe scripts/sync_skills.py --check` と `git diff --check` は各exit 0。gitleaksは今回のディレクトリのみ、exit 0・検出0。`submission-secrets.json`・`.log` に保存した。製品全体・履歴の再診断ではない。

```powershell
$root = (Get-Location).Path
docker run --rm --name easf-p503a2-submission --network none -v "${root}/reports/security/2026-10-23-g4/semgrep-followup:/report:ro" -v "${root}/reports/security/2026-10-23-g4/semgrep-followup:/out" zricethezav/gitleaks:v8.30.1 dir /report --redact --report-format json --report-path /out/submission-secrets.json
```
