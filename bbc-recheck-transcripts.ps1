# bbc-recheck-transcripts.ps1
# Re-scan all completed bbc-gpt-*.json lessons. For each file that is NOT dialogueMode
# "original" (or fails transcript quality), run Codex to fetch the BBC transcript and
# upgrade ONLY the dialogue section in place.
#
# Double-click or:
#   powershell -File bbc-recheck-transcripts.ps1
#   powershell -File bbc-recheck-transcripts.ps1 -Publish   # rebuild manifest at end
#   powershell -File bbc-recheck-transcripts.ps1 -Single     # one file only
#   powershell -File bbc-recheck-transcripts.ps1 -Force    # recheck even if already original
#
# No git commit/push. Log: docs/claude-cowork/bbc-lessons/.bbc-recheck-transcripts-log.txt

param(
    [switch]$Publish,
    [switch]$Single,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$repoRoot = $PSScriptRoot
$lessonsDir = Join-Path $repoRoot "docs\claude-cowork\bbc-lessons"
if (-not (Test-Path $lessonsDir)) {
    New-Item -ItemType Directory -Path $lessonsDir -Force | Out-Null
}

$script:BbcRecheckLog = Join-Path $lessonsDir ".bbc-recheck-transcripts-log.txt"
. "$repoRoot\bbc-generate-lesson.ps1"

Set-Location $repoRoot

trap {
    Log ""
    Log "STOPPED: recheck batch interrupted."
    exit 130
}

Log "=== BBC transcript recheck starting ==="
Log "Mode: upgrade paraphrase/incomplete JSON to original BBC transcript (dialogue only)"
Log "Repo: $repoRoot"
Log "Log file: $logFile"
Log ""

$codex = Get-Command codex -ErrorAction SilentlyContinue
if (-not $codex) {
    Log "ERROR: codex CLI not found on PATH."
    Log "Install: npm install -g @openai/codex  then run: codex login"
    exit 1
}

Ensure-BbcTranscriptDeps
Log ""

$allFiles = @(Get-ChildItem -Path $gptBbcDir -Filter 'bbc-gpt-*.json' -ErrorAction SilentlyContinue |
    Sort-Object { $_.Name })

if (-not $allFiles.Count) {
    Log "No bbc-gpt-*.json files found in $gptBbcDir"
    exit 0
}

$targets = @($allFiles | Where-Object { Test-BbcGptNeedsRecheck $_ -Force:$Force })
$skipCount = $allFiles.Count - $targets.Count

Log "Total BBC JSON files: $($allFiles.Count)"
Log "Need recheck: $($targets.Count) | Already original OK: $skipCount"
if ($Force) { Log "Force mode: rechecking all valid files" }
Log ""

if (-not $targets.Count) {
    Log "Nothing to recheck - all files are original with adequate dialogue length."
    exit 0
}

$stats = @{ Index = 0; Upgraded = 0; Failed = 0; Blocked = $false }

foreach ($file in $targets) {
    $stats.Index++
    $parsed = Parse-BbcGptJsonFile $file
    Set-LogEpisodeContext $parsed
    Log "--- Recheck $($stats.Index)/$($targets.Count): $($file.Name) ---"

    $result = Invoke-RecheckBbcJsonFile $file

    if ($result.Blocked) {
        $stats.Blocked = $true
        Log "BLOCKED: $($result.Reason) - stopping batch"
        break
    }
    if ($result.Upgraded) {
        $stats.Upgraded++
    } else {
        $stats.Failed++
    }

    if ($Single) {
        Log "Single-file mode (-Single) - stopping after one item."
        break
    }
    Log ""
}

Log ""
Log "=== BBC transcript recheck complete ==="
Log "Upgraded: $($stats.Upgraded) | Failed: $($stats.Failed) | Processed: $($stats.Index) | Skipped (already OK): $skipCount"

if ($Publish -and $stats.Upgraded -gt 0) {
    Log ""
    Log "Rebuilding manifest..."
    $manifestExit = Invoke-ManifestStep
    if ($manifestExit -ne 0) {
        Log "WARN: convert_lessons.py exited $manifestExit"
    } else {
        Log "Manifest rebuilt OK"
    }
    Log "GitHub: run update-index-and-push.ps1 when ready"
} elseif ($stats.Upgraded -gt 0) {
    Log ""
    Log "Next: re-run with -Publish for manifest, then update-index-and-push.ps1"
}

if ($stats.Blocked) { exit 1 }
exit 0
