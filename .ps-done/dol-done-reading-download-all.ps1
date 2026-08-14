# Double-click this file to download all DOL Reading L3 passages.
& "$PSScriptRoot\docs\claude-cowork\ielts-hourly-practice-tool\scripts\dol-reading-download-all.ps1" @args
if ($LASTEXITCODE -ne $null) { exit $LASTEXITCODE }
