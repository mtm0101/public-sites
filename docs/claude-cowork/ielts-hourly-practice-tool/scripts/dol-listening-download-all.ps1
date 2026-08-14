param(
  [int]$MaxTests = 0,
  [switch]$Reset,
  [switch]$Force,
  [switch]$InitOnly,
  [switch]$ContinueOnError,
  [switch]$StopOnError,
  [switch]$PauseOnExit
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppRoot = Split-Path -Parent $ScriptDir
$PyScript = Join-Path $ScriptDir "fetch_dol_listening_assets.py"
$LogDir = Join-Path $AppRoot "data\chatgpt\dol\listening"
$LogFile = Join-Path $LogDir ".dol-listening-download-log.txt"

if (-not (Test-Path $LogDir)) {
  New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

function Log($msg) {
  $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  $text = "$msg"
  $line = if ($text.Trim() -eq "") { "[$ts]" } else { "[$ts] $text" }
  Write-Host $line
  for ($attempt = 1; $attempt -le 5; $attempt++) {
    try {
      Add-Content -Path $LogFile -Value $line -Encoding UTF8 -ErrorAction Stop
      return
    } catch [System.IO.IOException] {
      if ($attempt -eq 5) {
        Write-Warning "Could not append to the DOL log after five attempts."
        return
      }
      Start-Sleep -Milliseconds 200
    }
  }
}

$pyArgs = @("-u", $PyScript, "--download-audio", "--download-vtt")
if ($MaxTests -gt 0) { $pyArgs += @("--max-tests", [string]$MaxTests) }
if ($Reset) { $pyArgs += "--reset" }
if ($Force) { $pyArgs += "--force" }
if ($InitOnly) { $pyArgs += "--init-only" }
if ($ContinueOnError -or -not $StopOnError) { $pyArgs += "--continue-on-error" }

try {
  Log ""
  Log "=== DOL listening downloader starting ==="
  Log "App root: $AppRoot"
  Log "Log file: $LogFile"
  Log "Safe to stop with Ctrl+C or by closing this window; rerun to resume."
  Log "Command: python $($pyArgs -join ' ')"

  $proxyVars = @("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")
  $clearedProxyVars = @()
  foreach ($name in $proxyVars) {
    if ([Environment]::GetEnvironmentVariable($name, "Process")) {
      [Environment]::SetEnvironmentVariable($name, $null, "Process")
      $clearedProxyVars += $name
    }
  }
  if ($clearedProxyVars.Count -gt 0) {
    Log "Cleared proxy env for this run: $($clearedProxyVars -join ', ')"
  }

  $oldPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    & python @pyArgs 2>&1 | ForEach-Object { Log "$_" }
    $exitCode = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $oldPreference
  }

  Log "=== DOL listening downloader finished with exit code $exitCode ==="
} catch {
  $exitCode = 1
  Log "ERROR: $($_.Exception.Message)"
  Log "=== DOL listening downloader failed ==="
} finally {
  if ($PauseOnExit) {
    Read-Host "Press Enter to close"
  }
}

exit $exitCode
