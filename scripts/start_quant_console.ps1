param(
    [string]$OwnerId = $env:QUANT_STATUS_OWNER_ID,
    [string]$DataDir = 'data/completion-enhancement',
    [string]$EvidenceDir = 'quant/artifacts/parallel-evidence-completion',
    [string]$RefreshReport,
    [ValidateRange(1, 65535)][int]$Port = 3000,
    [switch]$SnapshotOnly
)

$ErrorActionPreference = 'Stop'
$repoPath = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $repoPath
try {
    if ([string]::IsNullOrWhiteSpace($OwnerId) -or $OwnerId -match '[\s@]') {
        throw 'Use your authenticated Better Auth user.id as -OwnerId.'
    }
    if ($env:QUANT_STATUS_OWNER_ID -and $env:QUANT_STATUS_OWNER_ID -cne $OwnerId) {
        throw 'The supplied owner differs from QUANT_STATUS_OWNER_ID. Review the configured owner before rebinding.'
    }
    $env:QUANT_STATUS_OWNER_ID = $OwnerId
    if (-not $env:QUANT_STATUS_SIGNING_KEY) {
        if ($SnapshotOnly) { throw 'Set the server signing key in the scheduler environment before refreshing its snapshot.' }
        $random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try {
            $keyBytes = New-Object byte[] 32
            $random.GetBytes($keyBytes)
            $env:QUANT_STATUS_SIGNING_KEY = [BitConverter]::ToString($keyBytes).Replace('-', '').ToLowerInvariant()
        } finally {
            $random.Dispose()
        }
    }
    if ($env:QUANT_STATUS_SIGNING_KEY -cnotmatch '^[a-f0-9]{64}$') {
        throw 'QUANT_STATUS_SIGNING_KEY must be 64 lowercase hexadecimal characters.'
    }
    if (-not $env:QUANT_STATUS_FILE) {
        $env:QUANT_STATUS_FILE = Join-Path $repoPath 'data/quant-activation/private/status-envelope.json'
    }
    if (-not [IO.Path]::IsPathRooted($env:QUANT_STATUS_FILE)) {
        throw 'QUANT_STATUS_FILE must be an absolute private path.'
    }
    $env:QUANT_STATUS_SYNC = 'false'
    $env:QUANT_MONGO_PUBLISH = 'false'
    $python = @('quant/.venv/Scripts/python.exe', '.venv/Scripts/python.exe') |
        ForEach-Object { Join-Path $repoPath $_ } | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $python) { throw 'Create a Quant virtualenv and install quant/requirements.txt.' }

    $current = Join-Path $DataDir 'reports/current-status.json'
    $statusArgs = @('-m', 'quant.pipeline.write_current_status', '--data-dir', $DataDir, '--evidence-dir', $EvidenceDir)
    if ($RefreshReport) { $statusArgs += @('--refresh-report', $RefreshReport) }
    & $python @statusArgs | Out-Null
    if ($LASTEXITCODE) { throw 'Quant current-status generation failed.' }
    & $python -m quant.pipeline.export_quant_status --current-status $current --output $env:QUANT_STATUS_FILE
    if ($LASTEXITCODE) { throw 'Quant status projection failed.' }
    if (-not $SnapshotOnly) {
        $env:BETTER_AUTH_URL = "http://localhost:$Port"
        $env:NEXT_PUBLIC_BETTER_AUTH_URL = $env:BETTER_AUTH_URL
        Write-Host "Sign in to Market Pulse, then open http://localhost:$Port/quant."
        & npm.cmd run dev -- --hostname localhost --port $Port
        if ($LASTEXITCODE) { throw 'The Next.js server exited with an error.' }
    }
} finally {
    Pop-Location
}
