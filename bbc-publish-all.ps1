# Convenience wrapper - run from repo root:
#   powershell -File bbc-publish-all.ps1 [-Push] [-DryRun] ...
& "$PSScriptRoot\docs\claude-cowork\ielts-hourly-practice-tool\scripts\publish-bbc-all.ps1" @args
if ($LASTEXITCODE -ne $null) { exit $LASTEXITCODE }
