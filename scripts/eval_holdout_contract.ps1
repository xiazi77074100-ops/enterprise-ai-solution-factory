# Contract holdout evaluation of both arms (a person runs this once; preregistration §7・§8, D-047).
#   1. baseline (A): its own CLI in its own environment, on the decrypted holdout documents
#   2. Factory (B): the frozen workflow (contract-v3) in Linux with Tesseract
#   3. both outputs scored by the same scorer (app.evaluation.score_outputs), hashes checked against the manifest
# Only aggregates are written to reports/eval/contract-holdout/ (what the AI may read). Per-document outputs stay in
# a temporary folder outside the repository and are deleted at the end. Delete the decrypted holdout folder afterwards.
#
#   powershell -ExecutionPolicy Bypass -File scripts\eval_holdout_contract.ps1
param(
    [string]$HoldoutDir = (Join-Path $env:USERPROFILE "easf-holdout\contract"),
    [string]$BaselineDir = "C:\work\aidd\easf-baseline-contract",
    [string]$Manifest = "",  # tests only: a different hash manifest
    [string]$OutDir = ""     # tests only: a different place for the aggregates
)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
if (-not $Manifest) { $Manifest = Join-Path $repo "fixtures\contract\manifest.holdout.json" }
$HoldoutDir = (Resolve-Path $HoldoutDir).Path
if ($HoldoutDir.StartsWith($repo, [StringComparison]::OrdinalIgnoreCase)) { throw "The holdout must stay outside the repository." }
foreach ($sub in "documents", "labels", "labels_cr1") {
    if (-not (Test-Path (Join-Path $HoldoutDir $sub))) { throw "Expected $sub\ under $HoldoutDir (the decrypted contract holdout)." }
}
$work = Join-Path $env:TEMP "easf-contract-holdout-outputs"
if (Test-Path $work) { Remove-Item -Recurse -Force $work }
New-Item -ItemType Directory -Force (Join-Path $work "baseline") | Out-Null
$out = if ($OutDir) { $OutDir } else { Join-Path $repo "reports\eval\contract-holdout" }
New-Item -ItemType Directory -Force $out | Out-Null

try {
    Write-Host "1/3 baseline (A) on the holdout"
    Push-Location $BaselineDir
    try {
        & (Join-Path $BaselineDir ".venv\Scripts\python.exe") -m cli.run_batch (Join-Path $HoldoutDir "documents") (Join-Path $work "baseline")
        if ($LASTEXITCODE -ne 0) { throw "baseline run failed (exit $LASTEXITCODE)" }
    } finally { Pop-Location }

    Write-Host "2/3 Factory (B) on the holdout, 3/3 scoring both arms"
    $script = @'
set -e
apt-get update -qq >/dev/null && apt-get install -y -qq tesseract-ocr tesseract-ocr-jpn >/dev/null 2>&1
mkdir -p /app && cd /repo && tar --exclude=backend/.venv --exclude='*/__pycache__' -cf - backend fixtures contracts experiment | tar -xf - -C /app
cd /app/backend && uv sync --locked -q
M=/manifest.json
PYTHONPATH=. uv run python -m app.evaluation.offline --workflow ../fixtures/workflows/contract-v3.json --rule-pack ../fixtures/rule_packs/contract-1.1.0.json --manifest $M --split holdout --data-dir /holdout --extra-labels labels_cr1 --write-outputs /work/factory --out /work/factory-self.json > /dev/null
for arm in baseline factory; do
  echo == $arm
  PYTHONPATH=. uv run python -m app.evaluation.score_outputs --outputs /work/$arm --scoring ../experiment/contract_scoring.json --manifest $M --split holdout --data-dir /holdout --extra-labels labels_cr1 --out /out/$arm.json
done
'@ -replace "`r", ""
    docker run --rm `
        -v "${repo}:/repo:ro" -v "${HoldoutDir}:/holdout:ro" -v "${Manifest}:/manifest.json:ro" -v "${work}:/work" -v "${out}:/out" `
        ghcr.io/astral-sh/uv:python3.12-bookworm-slim sh -c $script
    if ($LASTEXITCODE -ne 0) { throw "Factory run or scoring failed (exit $LASTEXITCODE)" }
} finally {
    Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue  # per-document holdout outputs never stay
}
Write-Host "Aggregates written to $out (baseline.json, factory.json). Delete the decrypted holdout folder now."
