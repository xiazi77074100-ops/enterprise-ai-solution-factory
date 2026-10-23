# 製品を変えず、この証跡ディレクトリ内の一時コピーだけを検証する。
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$copy = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ('candidate-' + [guid]::NewGuid().ToString('N'))))
$allowedRoot = [IO.Path]::GetFullPath($PSScriptRoot) + [IO.Path]::DirectorySeparatorChar
if (-not $copy.StartsWith($allowedRoot, [StringComparison]::OrdinalIgnoreCase)) { throw '一時コピーの範囲不一致' }
$beforePath = $env:PYTHONPATH
$beforeUtf8 = $env:PYTHONUTF8
$beforeBytecode = $env:PYTHONDONTWRITEBYTECODE
$diagnosisExit = 1
try {
    New-Item -ItemType Directory -Path (Join-Path $copy 'backend') | Out-Null
    Copy-Item -LiteralPath (Join-Path $repoRoot 'backend/app') -Destination (Join-Path $copy 'backend/app') -Recurse
    $relative = [IO.Path]::GetRelativePath($repoRoot, $copy).Replace('\', '/')
    & git -C $repoRoot apply --directory $relative (Join-Path $PSScriptRoot 'proposed-fix.patch')
    if ($LASTEXITCODE -ne 0) { throw '隔離コピーへの差分適用に失敗' }
    $env:PYTHONPATH = Join-Path $copy 'backend'
    $env:PYTHONUTF8 = '1'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    & (Join-Path $repoRoot 'backend/.venv/Scripts/python.exe') (Join-Path $PSScriptRoot 'check_logs.py') --label candidate *> (Join-Path $PSScriptRoot 'candidate-run.log')
    $diagnosisExit = $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $beforePath
    $env:PYTHONUTF8 = $beforeUtf8
    $env:PYTHONDONTWRITEBYTECODE = $beforeBytecode
    # 再帰削除の直前にも絶対パスを照合する。製品側へは差分を適用しない。
    $resolvedCopy = [IO.Path]::GetFullPath($copy)
    if (-not $resolvedCopy.StartsWith($allowedRoot, [StringComparison]::OrdinalIgnoreCase)) { throw '削除範囲不一致' }
    if (Test-Path -LiteralPath $resolvedCopy) { Remove-Item -LiteralPath $resolvedCopy -Recurse -Force }
}
exit $diagnosisExit
