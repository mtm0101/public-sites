# DONE - tuhoc DOL vocab fully published (197 sets, queue empty).
# Re-run only if upcoming.json gets new entries or you need -ForceFetch refresh.
#
#   powershell -File dol-done-publish-all.ps1 [-Push] [-DryRun] ...
& "$PSScriptRoot\docs\claude-cowork\ielts-hourly-practice-tool\scripts\dol-done-publish-all.ps1" @args
if ($LASTEXITCODE -ne $null) { exit $LASTEXITCODE }
