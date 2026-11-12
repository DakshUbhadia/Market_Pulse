param(
    [string]$From = '2018-01-01',
    [switch]$CorporateOnly
)
$ErrorActionPreference = 'Stop'
$repoPath = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoPath
$pythonPath = Join-Path $repoPath 'quant\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create quant/.venv and install quant/requirements.txt first.'
}
$moduleName = if ($CorporateOnly) { 'quant.pipeline.update_corporate' } else { 'quant.pipeline.update_all' }
& $pythonPath -m $moduleName --from $From
exit $LASTEXITCODE
