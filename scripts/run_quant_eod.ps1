param(
    [string]$From = '2018-01-01',
    [switch]$CorporateOnly,
    [switch]$FullAudit
)
$ErrorActionPreference = 'Stop'
$repoPath = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoPath
$pythonPath = Join-Path $repoPath 'quant\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create quant/.venv and install quant/requirements.txt first.'
}
$moduleName = if ($FullAudit) { 'quant.pipeline.weekly_audit' } elseif ($CorporateOnly) { 'quant.pipeline.update_corporate' } else { 'quant.pipeline.scheduled_update' }
& $pythonPath -m $moduleName --from $From
exit $LASTEXITCODE
