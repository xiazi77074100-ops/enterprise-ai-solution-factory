param(
    [ValidateSet('python', 'owasp-top-ten', 'react', 'typescript', 'secrets', 'combined')]
    [string]$Pack = 'python',
    [ValidateSet('copy', 'direct')]
    [string]$Placement = 'copy',
    [ValidateSet('smoke', 'product')]
    [string]$Scope = 'product'
)

# 規則・製品は読み取り専用。選択肢以外のシェル文字列を受け取らない。
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$label = "$Scope-$Pack-$Placement"
$seconds = if ($Scope -eq 'smoke') { 40 } else { 180 }
$packs = if ($Pack -eq 'combined') { @('python', 'owasp-top-ten', 'react', 'typescript', 'secrets') } else { @($Pack) }
$configs = ($packs | ForEach-Object { "--config /tmp/rules/$_.yml" }) -join ' '
$setup = 'cp -R /out/rules /tmp/rules; '
if ($Scope -eq 'smoke') {
    $target = '/smoke/input.py'
    if ($Placement -eq 'copy') {
        $setup += 'cp -R /smoke /tmp/smoke; '
        $target = '/tmp/smoke/input.py'
    }
} else {
    $setup += 'mkdir -p /tmp/src; '
    $target = '/input/backend/app /input/frontend/src'
    if ($Placement -eq 'copy') {
        $setup += 'cp -R /input/backend /tmp/src/backend; cp -R /input/frontend /tmp/src/frontend; '
        $target = '/tmp/src/backend/app /tmp/src/frontend/src'
    }
}
$scan = "timeout -k 5 $seconds semgrep scan --oss-only --disable-version-check --no-trace --metrics off --jobs 1 --debug --exclude '**/__pycache__/**' --json --output /out/$label.json $configs $target"
$shellCode = $setup + $scan + '; code=$?; echo "$code" > /out/' + $label + '.exit; exit "$code"'
$dockerArgs = @(
    'run', '--rm', '--name', "easf-p503a2-$label", '--network', 'none', '--cpus', '1',
    '-v', "${PSScriptRoot}:/out", '-v', "${repoRoot}/reports/security/2026-10-23-g4/semgrep/smoke:/smoke:ro",
    '-v', "${repoRoot}/backend/app:/input/backend/app:ro", '-v', "${repoRoot}/frontend/src:/input/frontend/src:ro",
    '--entrypoint', 'sh', 'semgrep/semgrep:1.180.0', '-c', $shellCode
)
$timer = [Diagnostics.Stopwatch]::StartNew()
& docker @dockerArgs *> (Join-Path $PSScriptRoot "$label.log")
$code = $LASTEXITCODE
$timer.Stop()
[pscustomobject]@{ label = $label; exit = $code; wall_seconds = $timer.Elapsed.TotalSeconds; scan_limit_seconds = $seconds } |
    ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $PSScriptRoot "$label-run.json")
exit $code
