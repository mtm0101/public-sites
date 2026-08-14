# dol-done-publish-superlms-all.ps1
# DONE - SuperLMS vocab pipeline. 30 sets published (403ca28a16/17/18); superlms-state.json complete.
# Re-run only when DOL adds new sets or with -ForceFetch to refresh from API.
#
# Auth (one of):
#   scripts/.dol-jwt          (gitignored - paste dol-jwt cookie value)
#   env:DOL_JWT
#   -Jwt "eyJ..."
#
# Usage (from repo root):
#   powershell -File dol-done-publish-superlms-all.ps1
#   powershell -File dol-done-publish-superlms-all.ps1 -Push
#   powershell -File dol-done-publish-superlms-all.ps1 -Course 403ca28a16

param(
    [switch]$DryRun,
    [switch]$ForceFetch,
    [switch]$NoConvert,
    [switch]$Push,
    [switch]$ForcePush,
    [string]$Jwt = "",
    [string]$Course = ""
)

$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $toolRoot "..\..\..")).Path
$pyScript = Join-Path $PSScriptRoot "publish_superlms_all.py"
$pushScript = Join-Path $repoRoot "update-index-and-push.ps1"
$jwtFile = Join-Path $PSScriptRoot ".dol-jwt"

if (-not (Test-Path $pyScript)) {
    Write-Error "Missing $pyScript"
}

if (-not $Jwt -and -not $env:DOL_JWT -and -not (Test-Path $jwtFile)) {
    Write-Host ""
    Write-Host "DOL JWT required for SuperLMS API." -ForegroundColor Yellow
    Write-Host "  1. Log in at https://superlms.dolenglish.vn"
    Write-Host "  2. DevTools > Application > Cookies > dol-jwt"
    Write-Host "  3. Save the value to: $jwtFile"
    Write-Host "     or: `$env:DOL_JWT = '...'"
    Write-Host ""
    exit 1
}

Write-Host "DOL SuperLMS vocab - publish all courses" -ForegroundColor Cyan
Write-Host "  Tool:  $toolRoot"
Write-Host "  Repo:  $repoRoot"
Write-Host ""

$pyArgs = @($pyScript)
if ($DryRun) { $pyArgs += "--dry-run" }
if ($ForceFetch) { $pyArgs += "--force-fetch" }
if ($NoConvert) { $pyArgs += "--no-convert" }
if ($Jwt) { $pyArgs += @("--jwt", $Jwt) }
if ($Course) { $pyArgs += @("--course", $Course) }

Push-Location $toolRoot
try {
    python @pyArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "WARN: publish_superlms_all.py exited $LASTEXITCODE" -ForegroundColor Yellow
        if (-not $Push) { exit $LASTEXITCODE }
    }

    if ($DryRun) {
        Write-Host ""
        Write-Host "Dry-run complete - no files changed." -ForegroundColor Yellow
        exit 0
    }

    if ($Push) {
        if (-not (Test-Path $pushScript)) {
            Write-Error "Missing $pushScript"
        }
        Write-Host ""
        Write-Host "Pushing via update-index-and-push.ps1 ..." -ForegroundColor Cyan
        $pushArgs = @()
        if ($ForcePush) { $pushArgs += "-Force" }
        & $pushScript @pushArgs
        exit $LASTEXITCODE
    }

    Write-Host ""
    Write-Host "OK - SuperLMS publish finished. Commit when ready:" -ForegroundColor Green
    Write-Host "  cd $repoRoot"
    Write-Host "  git add docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/dol/"
    Write-Host "  git add docs/claude-cowork/ielts-hourly-practice-tool/manifest.json"
    Write-Host '  git commit -m "dol superlms: publish course vocab"'
    Write-Host "  git push"
    Write-Host ""
    Write-Host "Or re-run with -Push"
}
finally {
    Pop-Location
}
