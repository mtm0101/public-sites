param(
  [int]$MaxTests = 0,
  [switch]$Reset,
  [switch]$Force,
  [switch]$ContinueOnError,
  [switch]$PauseOnExit
)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptDir 'fetch_dol_reading.py'
$argsForPython = @('-u', $pythonScript, '--continue-on-error')
if ($MaxTests -gt 0) { $argsForPython += @('--max-tests', $MaxTests) }
if ($Reset) { $argsForPython += '--reset' }
if ($Force) { $argsForPython += '--force' }
if (-not $ContinueOnError) { } # Continue is the safe default for a full archive.

Write-Host '=== DOL Reading passage downloader ===' -ForegroundColor Cyan
Write-Host 'Downloads only Reading passage content from each L3 page; questions are excluded.'
Write-Host 'Safe to stop at any time. Run again to resume.'
& python @argsForPython
$exitCode = $LASTEXITCODE
if ($PauseOnExit) { Read-Host 'Press Enter to close' }
exit $exitCode
