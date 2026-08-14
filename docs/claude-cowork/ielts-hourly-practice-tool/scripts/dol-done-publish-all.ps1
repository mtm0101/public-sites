# dol-done-publish-all.ps1
# DONE - tuhoc DOL vocab pipeline. 197 sets published; upcoming.json queue empty.
# Re-run only when upcoming.json has new entries or with -ForceFetch to refresh from DOL.
#
# Usage (from repo root):
#   powershell -File dol-done-publish-all.ps1
#
# Options:
#   -DryRun          Show what would run; no file changes
#   -SkipFetch         Only sync state for dol-gpt-*.json already on disk
#   -ForceFetch        Re-fetch from DOL even when lesson file exists
#   -NoConvert       Skip manifest rebuild (convert_lessons.py)
#   -NoTranslate     Skip Vietnamese example translation (fastest)
#   -Translator      Primary translator: gtx (default, faster) or mymemory
#   -Push            After success, run update-index-and-push.ps1 (git pull, commit, push)
#   -ForcePush       Pass -Force to update-index-and-push.ps1

param(
    [switch]$DryRun,
    [switch]$SkipFetch,
    [switch]$ForceFetch,
    [switch]$NoConvert,
    [switch]$NoTranslate,
    [ValidateSet("gtx", "mymemory")]
    [string]$Translator = "gtx",
    [switch]$Push,
    [switch]$ForcePush
)

$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $toolRoot "..\..\..")).Path
$pyScript = Join-Path $PSScriptRoot "publish_dol_all.py"
$pushScript = Join-Path $repoRoot "update-index-and-push.ps1"

if (-not (Test-Path $pyScript)) {
    Write-Error "Missing $pyScript"
}

Write-Host "DOL vocab - local publish all" -ForegroundColor Cyan
Write-Host "  Tool:  $toolRoot"
Write-Host "  Repo:  $repoRoot"
Write-Host ""

$pyArgs = @($pyScript)
if ($DryRun) { $pyArgs += "--dry-run" }
if ($SkipFetch) { $pyArgs += "--skip-fetch" }
if ($ForceFetch) { $pyArgs += "--force-fetch" }
if ($NoConvert) { $pyArgs += "--no-convert" }
if ($NoTranslate) { $pyArgs += "--no-translate" }
$pyArgs += @("--translator", $Translator)

Push-Location $toolRoot
try {
    python @pyArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "WARN: publish_dol_all.py exited $LASTEXITCODE" -ForegroundColor Yellow
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
    Write-Host "OK - local publish finished. Commit/push when ready:" -ForegroundColor Green
    Write-Host "  cd $repoRoot"
    Write-Host "  git add docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/dol/"
    Write-Host "  git add docs/claude-cowork/ielts-hourly-practice-tool/manifest.json"
    Write-Host '  git commit -m "dol vocab: local publish all"'
    Write-Host "  git push"
    Write-Host ""
    Write-Host "Or re-run with -Push to use update-index-and-push.ps1"
}
finally {
    Pop-Location
}
