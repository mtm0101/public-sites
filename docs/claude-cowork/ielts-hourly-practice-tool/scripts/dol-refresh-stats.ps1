# dol-refresh-stats.ps1
# Fetch DOL book-level luot lam (testTakers) from live DOL pages.
#
# Usage (from repo root):
#   powershell -File dol-refresh-stats.ps1

param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $PSScriptRoot
$pyScript = Join-Path $PSScriptRoot "fetch_dol_book_stats.py"

if (-not (Test-Path $pyScript)) {
    Write-Error "Missing $pyScript"
}

Write-Host "DOL book stats (lượt làm)" -ForegroundColor Cyan
Write-Host "  Tool: $toolRoot"
Write-Host ""

$pyArgs = @($pyScript)
if ($DryRun) { $pyArgs += "--dry-run" }

Push-Location $toolRoot
try {
    python @pyArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
