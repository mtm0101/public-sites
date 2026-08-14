# run-morning-brief.ps1
# Non-interactive entry point for the morning brief, run by Claude Code CLI (not Cowork).
# Called by Windows Task Scheduler weekdays at 08:00, or manually for testing:
#   powershell -File run-morning-brief.ps1
# See: docs/claude-cowork/claude-config/morning-brief-claude-code.md for the task instructions.

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$logDir   = Join-Path $repoRoot "docs\claude-cowork\morning-brief"
$logFile  = Join-Path $logDir ".morning-brief-run-log.txt"

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

function Log($msg) {
    $ts   = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

Set-Location $repoRoot
Log "=== Morning brief run starting ==="

$prompt = "Run the morning brief task per docs/claude-cowork/claude-config/morning-brief-claude-code.md"

# Native-exe stderr must not go through 2>&1 under $ErrorActionPreference = "Stop" (PS 5.1
# wraps each stderr line as a terminating NativeCommandError). Relax it for this call only,
# and feed empty stdin so claude doesn't wait on an ambiguous console stream.
$prevEAP = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$output = $null | & claude --print $prompt --dangerously-skip-permissions 2>&1
$exitCode = $LASTEXITCODE
$ErrorActionPreference = $prevEAP

$output | ForEach-Object { Log $_ }
Log "Claude run finished (exit $exitCode)"
if ($exitCode -ne 0) {
    Log "ERROR: claude exited non-zero"
    exit $exitCode
}

Log "=== Morning brief run complete ==="
