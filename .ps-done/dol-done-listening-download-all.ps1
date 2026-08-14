# DOL Listening downloader.
# Double-click/run this to download listening tests one by one until complete.
# Safe to stop anytime; rerun to resume from state/upcoming.
& "$PSScriptRoot\docs\claude-cowork\ielts-hourly-practice-tool\scripts\dol-listening-download-all.ps1" @args
if ($LASTEXITCODE -ne $null) { exit $LASTEXITCODE }
