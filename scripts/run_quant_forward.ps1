param(
    [Parameter(Mandatory=$true)][string]$Cohort,
    [Parameter(Mandatory=$true)][string]$PriceBaseline,
    [Parameter(Mandatory=$true)][string]$TotalReturnBaseline,
    [Parameter(Mandatory=$true)][string]$AsOf
)
$ErrorActionPreference = 'Stop'
$repoPath = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoPath
$pythonPath = Join-Path $repoPath 'quant\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    $pythonPath = Join-Path $repoPath '.venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Install the quant Python environment before running the paper workflow.'
}
# run_forward_signal validates sealed baselines before refresh, freezes the
# signal before next open, replays shadow accounting and appends outcomes.
& $pythonPath -m quant.pipeline.run_forward_signal --as-of $AsOf --cohort $Cohort --price-baseline $PriceBaseline --total-return-baseline $TotalReturnBaseline
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $pythonPath -m quant.pipeline.report_forward_cohort --cohort $Cohort --to $AsOf
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $pythonPath -m quant.pipeline.write_current_status
exit $LASTEXITCODE
