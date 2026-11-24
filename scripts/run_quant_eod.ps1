param(
    [string]$From = '2018-01-01',
    [string]$DataDir,
    [switch]$CorporateOnly,
    [switch]$FullAudit,
    [string]$ConsoleStatusDataDir,
    [string]$ConsoleRefreshReport
)
$ErrorActionPreference = 'Stop'
$repoPath = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoPath
$pythonPath = Join-Path $repoPath 'quant\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    $pythonPath = Join-Path $repoPath '.venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create a Quant virtualenv and install quant/requirements.txt first.'
}
$moduleName = if ($FullAudit) { 'quant.pipeline.weekly_audit' } elseif ($CorporateOnly) { 'quant.pipeline.update_corporate' } else { 'quant.pipeline.scheduled_update' }
$arguments = @('-m', $moduleName, '--from', $From)
if ($DataDir) { $arguments += @('--data-dir', $DataDir) }
& $pythonPath @arguments
$jobExit = $LASTEXITCODE
if ($ConsoleStatusDataDir) {
    try {
        $consoleArgs = @{ DataDir = $ConsoleStatusDataDir; SnapshotOnly = $true }
        if (-not $ConsoleRefreshReport -and -not $CorporateOnly) {
            $reports = Join-Path $ConsoleStatusDataDir 'reports'
            New-Item -ItemType Directory -Path $reports -Force | Out-Null
            $ConsoleRefreshReport = Join-Path $reports ("eod-attempt-{0}.json" -f [Guid]::NewGuid().ToString('N'))
            @{
                status = if ($jobExit -eq 0) { 'COMPLETED' } else { 'FAILED' }
                checked_at = [DateTimeOffset]::UtcNow.ToString('o')
                exit_code = $jobExit
                job = $moduleName
            } | ConvertTo-Json | Set-Content -LiteralPath $ConsoleRefreshReport -Encoding ascii
        }
        if ($ConsoleRefreshReport) { $consoleArgs.RefreshReport = $ConsoleRefreshReport }
        & (Join-Path $PSScriptRoot 'start_quant_console.ps1') @consoleArgs
    } catch {
        if ($jobExit -eq 0) { $jobExit = 1 }
        Write-Warning $_.Exception.Message
    }
}
exit $jobExit
