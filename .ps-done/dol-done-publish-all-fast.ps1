# DONE - fast tuhoc DOL publish (skips example translation). Queue empty; data on disk.
# Re-run only for new upcoming.json entries or -ForceFetch refresh.
#
#   powershell -File dol-done-publish-all-fast.ps1 [-Push]
param(
    [switch]$Push,
    [switch]$ForcePush
)

$splat = @{ NoTranslate = $true }
if ($Push) { $splat.Push = $true }
if ($ForcePush) { $splat.ForcePush = $true }

& "$PSScriptRoot\docs\claude-cowork\ielts-hourly-practice-tool\scripts\dol-done-publish-all.ps1" @splat
if ($LASTEXITCODE -ne $null) { exit $LASTEXITCODE }
