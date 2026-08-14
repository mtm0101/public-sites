# publish-bbc-all.ps1
# Local BBC 6 Minute English pipeline - sync HTML, convert, publish, manifest.
# No ChatGPT required. Vocab IPA is NOT stored in JSON (index.html lazy-loads from ipa/).
#
# Usage (from repo root):
#   powershell -File publish-bbc-all.ps1
#
# Options:
#   -DryRun              Show plan only; no file changes
#   -SkipSync            Do not copy HTML from Claude outputs folder
#   -SkipConvert         Skip convert_bbc_html.py
#   -ForceConvert        Overwrite existing bbc-claude JSON files
#   -PromoteAll          Promote all claude JSON missing a gpt twin (not only queue)
#   -NoConvertManifest   Skip manifest rebuild
#   -Push                Run update-index-and-push.ps1 after success
#   -ForcePush           Pass -Force to update-index-and-push.ps1

param(
    [switch]$DryRun,
    [switch]$SkipSync,
    [switch]$SkipConvert,
    [switch]$ForceConvert,
    [switch]$PromoteAll,
    [switch]$NoConvertManifest,
    [switch]$Push,
    [switch]$ForcePush
)

$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $toolRoot "..\..\..")).Path
$pyScript = Join-Path $PSScriptRoot "publish_bbc_all.py"
$pushScript = Join-Path $repoRoot "update-index-and-push.ps1"

if (-not (Test-Path $pyScript)) {
    Write-Error "Missing $pyScript"
}

Write-Host "BBC 6 Minute English - local publish all" -ForegroundColor Cyan
Write-Host "  Tool:  $toolRoot"
Write-Host "  Repo:  $repoRoot"
Write-Host ""

$pyArgs = @($pyScript)
if ($DryRun) { $pyArgs += "--dry-run" }
if ($SkipSync) { $pyArgs += "--skip-sync" }
if ($SkipConvert) { $pyArgs += "--skip-convert" }
if ($ForceConvert) { $pyArgs += "--force-convert" }
if ($PromoteAll) { $pyArgs += "--promote-all" }
if ($NoConvertManifest) { $pyArgs += "--no-convert-manifest" }

Push-Location $toolRoot
try {
    python @pyArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "WARN: publish_bbc_all.py exited $LASTEXITCODE" -ForegroundColor Yellow
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
    Write-Host "OK - local BBC publish finished. Commit/push when ready:" -ForegroundColor Green
    Write-Host "  cd $repoRoot"
    Write-Host "  git add docs/claude-cowork/bbc-lessons/"
    Write-Host "  git add docs/claude-cowork/ielts-hourly-practice-tool/data/claude-cowork/bbc/"
    Write-Host "  git add docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/bbc/"
    Write-Host "  git add docs/claude-cowork/ielts-hourly-practice-tool/manifest.json"
    Write-Host '  git commit -m "bbc 6min: local publish all"'
    Write-Host "  git push"
    Write-Host ""
    Write-Host "Or re-run with -Push"
    exit 0
}
finally {
    Pop-Location
}
