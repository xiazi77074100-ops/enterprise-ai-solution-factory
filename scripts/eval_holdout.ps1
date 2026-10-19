# Holdout evaluation (a person runs this; fixtures/HOLDOUT.md "評価のとき", easf-eval-integrity §2).
# Runs app.evaluation.offline in Linux (Docker, with Tesseract) against the decrypted holdout folder, mounted
# read-only. Every file is checked against the frozen manifest; only aggregates are written to
# reports/eval/holdout/result.json, which is what the AI may read. Delete the decrypted folder afterwards.
#
#   pwsh scripts/eval_holdout.ps1                                   # default folder below
#   pwsh scripts/eval_holdout.ps1 -HoldoutDir D:\somewhere\invoice
param(
    [string]$HoldoutDir = (Join-Path $env:USERPROFILE "easf-holdout\invoice"),
    [string]$Manifest = "",
    [string]$OutDir = ""
)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
if (-not $Manifest) { $Manifest = Join-Path $repo "fixtures\manifest.holdout.json" }
if (-not $OutDir) { $OutDir = Join-Path $repo "reports\eval\holdout" }
$HoldoutDir = (Resolve-Path $HoldoutDir).Path
if ($HoldoutDir.StartsWith($repo, [StringComparison]::OrdinalIgnoreCase)) { throw "The holdout must stay outside the repository." }
if (-not (Test-Path (Join-Path $HoldoutDir "labels")) -or -not (Test-Path (Join-Path $HoldoutDir "documents"))) {
    throw "Expected labels\ and documents\ under $HoldoutDir (the decrypted holdout folder)."
}
New-Item -ItemType Directory -Force $OutDir | Out-Null

$script = @'
set -e
apt-get update -qq >/dev/null && apt-get install -y -qq tesseract-ocr tesseract-ocr-jpn >/dev/null 2>&1
mkdir -p /work && cd /repo && tar --exclude=backend/.venv --exclude='*/__pycache__' -cf - backend fixtures contracts | tar -xf - -C /work
cd /work/backend && uv sync --locked -q
PYTHONPATH=. uv run python -m app.evaluation.offline --workflow ../fixtures/workflows/invoice-v3.json --rule-pack ../fixtures/rule_packs/invoice-1.1.0.json --manifest /manifest.json --split holdout --data-dir /holdout --out /out/result.json
'@ -replace "`r", ""

docker run --rm `
    -v "${repo}:/repo:ro" -v "${HoldoutDir}:/holdout:ro" -v "${Manifest}:/manifest.json:ro" -v "${OutDir}:/out" `
    ghcr.io/astral-sh/uv:python3.12-bookworm-slim sh -c $script
if ($LASTEXITCODE -ne 0) { throw "evaluation failed (exit $LASTEXITCODE)" }
Write-Host "Aggregates written to $(Join-Path $OutDir 'result.json'). Delete the decrypted holdout folder now."
