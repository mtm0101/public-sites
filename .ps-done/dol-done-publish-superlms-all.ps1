# DONE - SuperLMS vocab fully published (30 sets across 3 Giai doan courses).
# Re-run only if DOL adds new course vocab sets or you need -ForceFetch refresh.
#
#   powershell -File dol-done-publish-superlms-all.ps1 [-Push] [-ForceFetch] ...
& "$PSScriptRoot\docs\claude-cowork\ielts-hourly-practice-tool\scripts\dol-done-publish-superlms-all.ps1" @args
if ($LASTEXITCODE -ne $null) { exit $LASTEXITCODE }
