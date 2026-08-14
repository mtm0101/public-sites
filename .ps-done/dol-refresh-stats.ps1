# Convenience wrapper — run from repo root:
#   powershell -File dol-refresh-stats.ps1 [-DryRun]
& "$PSScriptRoot\docs\claude-cowork\ielts-hourly-practice-tool\scripts\dol-refresh-stats.ps1" @args
if ($LASTEXITCODE -ne $null) { exit $LASTEXITCODE }
