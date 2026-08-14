# bbc-generate-lesson.ps1
# Generate BBC 6 Minute English lessons via Codex CLI (~3-10 min per episode).
#
# DEFAULT (token-efficient): JSON only -> data/chatgpt/bbc/ (no HTML).
# Codex default: gpt-5.4-mini + low reasoning (cheap). Override: BBC_CODEX_MODEL / BBC_CODEX_REASONING.
# Legacy HTML mode: pass -Html.
#
# DEFAULT batch mode: processes ALL pending queue episodes until empty (auto-advance).
# Pass -Single for one episode only. Close window anytime to stop safely.
# Queue advances after valid JSON; failed episodes are skipped after retries so the batch continues.
# No git commit/push; use update-index-and-push.ps1 later.
#
#   powershell -File bbc-generate-and-publish.ps1     # batch generate + manifest (recommended)
#   powershell -File bbc-generate-lesson.ps1 -Publish
#   powershell -File bbc-generate-lesson.ps1 -Single  # one episode only
#   powershell -File bbc-generate-lesson.ps1 -PublishOnly
#   powershell -File bbc-generate-lesson.ps1 -Html -Publish

param(
    [switch]$Html,
    [switch]$Publish,
    [switch]$PublishOnly,
    [switch]$Push,
    [switch]$ForcePush,
    [switch]$Single
)

$ErrorActionPreference = "Stop"

try {
    if ($PSVersionTable.PSVersion.Major -ge 6) {
        [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
    }
} catch { }

$repoRoot   = $PSScriptRoot
$toolRoot   = Join-Path $repoRoot "docs\claude-cowork\ielts-hourly-practice-tool"
$gptBbcDir  = Join-Path $toolRoot "data\chatgpt\bbc"
$gptStatePath     = Join-Path $gptBbcDir "state.json"
$gptUpcomingPath  = Join-Path $gptBbcDir "upcoming.json"
$lessonsDir = Join-Path $repoRoot "docs\claude-cowork\bbc-lessons"
$logFile    = Join-Path $lessonsDir ".bbc-generate-run-log.txt"
if ($script:BbcRecheckLog) { $logFile = $script:BbcRecheckLog }
$manualFile = Join-Path $lessonsDir "RUN-IN-CURSOR.md"

if (-not (Test-Path $lessonsDir)) {
    New-Item -ItemType Directory -Path $lessonsDir -Force | Out-Null
}
if (-not (Test-Path $gptBbcDir)) {
    New-Item -ItemType Directory -Path $gptBbcDir -Force | Out-Null
}

$script:LogEpisodePrefix = ''

function Set-LogEpisodeContext($ep) {
    if (-not $ep) {
        $script:LogEpisodePrefix = ''
        return
    }
    $date = "$($ep.Date)".Trim()
    $code = "$($ep.Ep)".Trim()
    if ($date -and $code) {
        $script:LogEpisodePrefix = "[$date $code]"
    } elseif ($date) {
        $script:LogEpisodePrefix = "[$date]"
    } elseif ($code) {
        $script:LogEpisodePrefix = "[$code]"
    } else {
        $script:LogEpisodePrefix = ''
    }
}

function Log($msg) {
    $ts   = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $pfx  = if ($script:LogEpisodePrefix) { "$($script:LogEpisodePrefix) " } else { '' }
    $text = "$msg"
    if ($text.Trim() -eq '') {
        $line = "[$ts] $($pfx.TrimEnd())".TrimEnd()
    } else {
        $line = "[$ts] $pfx$text"
    }
    Write-Host $line
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

function Write-ManualFallback($reason) {
    $body = @'
# BBC lesson - manual fallback

Codex CLI could not run. See the log for the reason.

Option A - retry from terminal:

    powershell -File bbc-generate-and-publish.ps1

Option B - open this repo in Cursor Agent and paste:

    Generate one BBC 6 Minute English lesson as JSON only (no HTML).
    Read docs/claude-cowork/ielts-hourly-practice-tool/specs/02-bbc-6min.md and data/templates/bbc-lesson-template.json.
    Write docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/bbc/bbc-gpt-<YYMMDD>-<slug>.json
    Advance data/chatgpt/bbc/state.json and upcoming.json. Run convert_lessons.py for manifest.

Option C - legacy HTML mode:

    powershell -File bbc-generate-lesson.ps1 -Html -Publish
'@
    $body = $body.Replace('Codex CLI could not run. See the log for the reason.', "Codex CLI could not run: $reason")
    Set-Content -Path $manualFile -Value $body -Encoding UTF8
    Log "Wrote manual fallback: $manualFile"
}

function Get-AgentFailureReason($output) {
    $text = ($output | ForEach-Object { "$_" }) -join "`n"
    if ($text -match 'not supported when using Codex with a ChatGPT account|invalid_request_error.*model') { return 'ModelUnsupported' }
    if ($text -match 'spend limit|usage-credits|usage credits|quota|billing') { return 'SpendLimit' }
    if ($text -match 'not logged in|authentication|login required|invalid api key|run codex login') { return 'Auth' }
    if ($text -match 'rate limit|too many requests') { return 'RateLimit' }
    return 'Unknown'
}

function Resolve-CodexModel {
    if ($env:BBC_CODEX_MODEL) { return $env:BBC_CODEX_MODEL }
    # Cost-efficient default for BBC JSON generation (override with BBC_CODEX_MODEL).
    return 'gpt-5.4-mini'
}

function Resolve-CodexReasoningEffort {
    if ($env:BBC_CODEX_REASONING) { return $env:BBC_CODEX_REASONING }
    return 'low'
}

function Convert-YymmddToIsoDate($yymmdd) {
    if ("$yymmdd" -notmatch '^\d{6}$') { return $null }
    $yy = [int]$yymmdd.Substring(0, 2)
    $yyyy = if ($yy -ge 90) { 1900 + $yy } else { 2000 + $yy }
    return ('{0}-{1}-{2}' -f $yyyy, $yymmdd.Substring(2, 2), $yymmdd.Substring(4, 2))
}

function Get-YyyyFromYymmdd($yymmdd) {
    if ("$yymmdd" -notmatch '^\d{6}$') { return $null }
    $yy = [int]$yymmdd.Substring(0, 2)
    $yyyy = if ($yy -ge 90) { 1900 + $yy } else { 2000 + $yy }
    return [string]$yyyy
}

function Get-BbcUrlFromYymmdd($yymmdd) {
    $yyyy = Get-YyyyFromYymmdd $yymmdd
    if (-not $yyyy) { return $null }
    return "https://www.bbc.co.uk/learningenglish/english/features/6-minute-english_$yyyy/ep-$yymmdd"
}

function Get-ChatgptSentYymmdds {
    $done = New-Object 'System.Collections.Generic.HashSet[string]'
    $statePath = Join-Path $repoRoot 'docs\claude-cowork\ielts-hourly-practice-tool\data\chatgpt\bbc\state.json'
    if (-not (Test-Path $statePath)) { return $done }
    try {
        $state = Get-Content $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($row in @($state.sent)) {
            $yymmdd = ''
            if ("$($row.url)" -match 'ep-(\d{6})') { $yymmdd = $Matches[1] }
            if (-not $yymmdd -and "$($row.episodeDate)" -match '^\d{4}-\d{2}-\d{2}$') {
                $d = "$($row.episodeDate)"
                $yymmdd = $d.Substring(2, 2) + $d.Substring(5, 2) + $d.Substring(8, 2)
            }
            if ($yymmdd) { [void]$done.Add($yymmdd) }
        }
    } catch { }
    return $done
}

function Build-SentRowFromHtml($file) {
    $parsed = Parse-BbcHtmlFile $file
    if (-not $parsed) { return $null }
    return @{
        url = Get-BbcUrlFromYymmdd $parsed.Yymmdd
        title = $parsed.Title
        episodeDate = $parsed.Date
        processedAt = $file.LastWriteTimeUtc.ToString('o')
        htmlFile = $file.Name
    }
}

function Ensure-BbcSentState {
    $sentPath = Join-Path $lessonsDir 'bbc-6min-sent.json'
    $needsWrite = -not (Test-Path $sentPath)
    $existing = $null

    if (-not $needsWrite) {
        try {
            $existing = Get-Content $sentPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if (-not $existing.upcoming -or @($existing.upcoming).Count -eq 0) {
                $needsWrite = $true
            }
        } catch {
            $needsWrite = $true
        }
    }

    if (-not $needsWrite) {
        $head = $existing.upcoming[0]
        Log "State file OK: $($head.episodeDate) (upcoming=$(@($existing.upcoming).Count))"
        return $existing
    }

    $done = Get-ChatgptSentYymmdds
    $sentByEp = @{}

    if ($existing -and $existing.sent) {
        foreach ($row in @($existing.sent)) {
            $yymmdd = ''
            if ("$($row.url)" -match 'ep-(\d{6})') { $yymmdd = $Matches[1] }
            if ($yymmdd) {
                $sentByEp[$yymmdd] = @{
                    url = "$($row.url)"
                    title = if ($row.title) { "$($row.title)" } else { $null }
                    episodeDate = "$($row.episodeDate)"
                    processedAt = if ($row.processedAt) { "$($row.processedAt)" } else { (Get-Date).ToUniversalTime().ToString('o') }
                    htmlFile = if ($row.htmlFile) { "$($row.htmlFile)" } else { $null }
                }
                [void]$done.Add($yymmdd)
            }
        }
    }

    foreach ($file in (Get-ChildItem -Path $lessonsDir -Filter 'bbc-6min-*.html' -ErrorAction SilentlyContinue)) {
        $row = Build-SentRowFromHtml $file
        if ($row -and $row.episodeDate -match '^\d{4}-\d{2}-\d{2}$') {
            $yymmdd = $row.episodeDate.Substring(2, 2) + $row.episodeDate.Substring(5, 2) + $row.episodeDate.Substring(8, 2)
            $sentByEp[$yymmdd] = $row
            [void]$done.Add($yymmdd)
        }
    }

    $upcoming = New-Object System.Collections.ArrayList
    $gptUpcoming = Join-Path $repoRoot 'docs\claude-cowork\ielts-hourly-practice-tool\data\chatgpt\bbc\upcoming.json'
    if (Test-Path $gptUpcoming) {
        try {
            $up = Get-Content $gptUpcoming -Raw -Encoding UTF8 | ConvertFrom-Json
            foreach ($yymmdd in @($up.queue)) {
                $yymmdd = "$yymmdd".Trim()
                if (-not $yymmdd) { continue }
                if ($done.Contains($yymmdd)) { continue }
                [void]$upcoming.Add(@{
                    url = Get-BbcUrlFromYymmdd $yymmdd
                    episodeDate = Convert-YymmddToIsoDate $yymmdd
                    title = $null
                })
                if ($upcoming.Count -ge 20) { break }
            }
        } catch {
            Log "WARN: upcoming bootstrap error: $($_.Exception.Message)"
        }
    }

    if ($upcoming.Count -eq 0) {
        Log "WARN: could not build upcoming queue from chatgpt/bbc/upcoming.json"
        return $existing
    }

    $sent = @($sentByEp.GetEnumerator() | Sort-Object { $_.Key } | ForEach-Object { $_.Value })
    $stateObj = @{
        sent = $sent
        upcoming = @($upcoming.ToArray())
    }
    $json = $stateObj | ConvertTo-Json -Depth 6
    Set-Content -Path $sentPath -Value $json -Encoding UTF8
    Log "Bootstrapped state file: $sentPath (sent=$($sent.Count), upcoming=$($upcoming.Count), next=$($upcoming[0].episodeDate))"
    return $stateObj
}

function Update-BbcSentAfterHtml($htmlFile) {
    $sentPath = Join-Path $lessonsDir 'bbc-6min-sent.json'
    if (-not (Test-Path $sentPath)) { return }
    try {
        $state = Get-Content $sentPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $parsed = Parse-BbcHtmlFile $htmlFile
        if (-not $parsed) { return }

        $already = $false
        foreach ($row in @($state.sent)) {
            if ("$($row.htmlFile)" -eq $htmlFile.Name) { $already = $true; break }
            if ("$($row.episodeDate)" -eq $parsed.Date) { $already = $true; break }
        }
        if ($already) { return }

        $newSent = @{
            url = Get-BbcUrlFromYymmdd $parsed.Yymmdd
            title = $parsed.Title
            episodeDate = $parsed.Date
            processedAt = (Get-Date).ToUniversalTime().ToString('o')
            htmlFile = $htmlFile.Name
        }
        $sentList = New-Object System.Collections.ArrayList
        if ($state.sent) { foreach ($s in @($state.sent)) { [void]$sentList.Add($s) } }
        [void]$sentList.Add($newSent)

        $upcomingList = New-Object System.Collections.ArrayList
        if ($state.upcoming) {
            foreach ($u in @($state.upcoming)) {
                $skip = $false
                if ("$($u.episodeDate)" -eq $parsed.Date) { $skip = $true }
                if ("$($u.url)" -match 'ep-(\d{6})' -and $Matches[1] -eq $parsed.Yymmdd) { $skip = $true }
                if (-not $skip) { [void]$upcomingList.Add($u) }
            }
        }

        $stateObj = @{
            sent = @($sentList.ToArray())
            upcoming = @($upcomingList.ToArray())
        }
        Set-Content -Path $sentPath -Value ($stateObj | ConvertTo-Json -Depth 6) -Encoding UTF8
        Log "Updated state file after HTML: $($parsed.Date) -> $($htmlFile.Name)"
    } catch {
        Log "WARN: could not update state file after HTML: $($_.Exception.Message)"
    }
}

function Get-NextBbcEpisode {
    $result = @{ Date = ''; Yymmdd = ''; Ep = ''; Title = ''; Source = '' }

    $sentPath = Join-Path $lessonsDir 'bbc-6min-sent.json'
    if (Test-Path $sentPath) {
        try {
            $state = Get-Content $sentPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($state.upcoming -and @($state.upcoming).Count -gt 0) {
                $u = $state.upcoming[0]
                $date = "$($u.episodeDate)".Trim()
                $yymmdd = ''
                if ("$($u.url)" -match 'ep-(\d{6})') { $yymmdd = $Matches[1] }
                if (-not $date -and $yymmdd) { $date = Convert-YymmddToIsoDate $yymmdd }
                if ($date -and -not $yymmdd) {
                    $yymmdd = $date.Substring(2, 2) + $date.Substring(5, 2) + $date.Substring(8, 2)
                }
                $result.Date = $date
                $result.Yymmdd = $yymmdd
                $result.Ep = if ($yymmdd) { "ep-$yymmdd" } else { '' }
                $result.Title = "$($u.title)".Trim()
                $result.Source = 'bbc-6min-sent.json'
                return $result
            }
        } catch { }
    }

    $gptUpcoming = Join-Path $repoRoot 'docs\claude-cowork\ielts-hourly-practice-tool\data\chatgpt\bbc\upcoming.json'
    if (Test-Path $gptUpcoming) {
        try {
            $up = Get-Content $gptUpcoming -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($up.queue -and @($up.queue).Count -gt 0) {
                $yymmdd = "$($up.queue[0])".Trim()
                $date = Convert-YymmddToIsoDate $yymmdd
                $result.Date = $date
                $result.Yymmdd = $yymmdd
                $result.Ep = "ep-$yymmdd"
                $result.Source = 'chatgpt/bbc/upcoming.json'
                return $result
            }
        } catch { }
    }

    return $result
}

function Format-EpisodeLabel($ep) {
    if (-not $ep) { return '(episode unknown)' }
    if (-not $ep.Date -and $ep.Ep) { return $ep.Ep }
    if (-not $ep.Date) { return '(episode unknown)' }
    $title = if ($ep.Title) { " - $($ep.Title)" } else { '' }
    $code = if ($ep.Ep) { " ($($ep.Ep))" } else { '' }
    return "$($ep.Date)$code$title"
}

function Get-BbcHtmlSnapshot {
    return @((Get-ChildItem -Path $lessonsDir -Filter 'bbc-6min-*.html' -ErrorAction SilentlyContinue | ForEach-Object { $_.Name }))
}

function Find-NewBbcHtml($beforeNames) {
    $files = Get-ChildItem -Path $lessonsDir -Filter 'bbc-6min-*.html' -ErrorAction SilentlyContinue
    foreach ($f in ($files | Sort-Object LastWriteTime -Descending)) {
        if ($beforeNames -notcontains $f.Name) { return $f }
    }
    return $null
}

function Parse-BbcHtmlFile($file) {
    $name = if ($file.Name) { $file.Name } else { "$file" }
    if ($name -match '^bbc-6min-(\d{4}-\d{2}-\d{2})-(.+)\.html$') {
        $date = $Matches[1]
        $yymmdd = $date.Substring(2, 2) + $date.Substring(5, 2) + $date.Substring(8, 2)
        return @{
            Date = $date
            Yymmdd = $yymmdd
            Ep = "ep-$yymmdd"
            Title = ($Matches[2] -replace '-', ' ')
            File = $name
        }
    }
    return $null
}

function Get-LatestBbcHtml {
    return Get-ChildItem -Path $lessonsDir -Filter 'bbc-6min-*.html' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Test-GptBbcJsonExists($yymmdd) {
    return [bool](Get-ChildItem -Path $gptBbcDir -Filter "bbc-gpt-$yymmdd-*.json" -ErrorAction SilentlyContinue | Select-Object -First 1)
}

function Get-NextChatgptBbcEpisode {
    $result = @{ Date = ''; Yymmdd = ''; Ep = ''; Title = ''; Source = ''; JsonFile = '' }
    if (-not (Test-Path $gptUpcomingPath)) { return $result }
    try {
        $up = Get-Content $gptUpcomingPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $done = Get-ChatgptSentYymmdds
        foreach ($yymmdd in @($up.queue)) {
            $yymmdd = "$yymmdd".Trim()
            if (-not $yymmdd) { continue }
            if ($done.Contains($yymmdd)) { continue }
            if (Test-GptBbcJsonExists $yymmdd) {
                $existing = Get-ChildItem -Path $gptBbcDir -Filter "bbc-gpt-$yymmdd-*.json" -ErrorAction SilentlyContinue |
                    Sort-Object LastWriteTime -Descending | Select-Object -First 1
                if ($existing -and (Test-BbcGptJsonValid $existing)) {
                    $parsed = Parse-BbcGptJsonFile $existing
                    if ($parsed) {
                        Register-BbcJsonIfValid $existing $parsed | Out-Null
                        $done = Get-ChatgptSentYymmdds
                    }
                }
                continue
            }
            $date = Convert-YymmddToIsoDate $yymmdd
            $result.Date = $date
            $result.Yymmdd = $yymmdd
            $result.Ep = "ep-$yymmdd"
            $result.Source = 'chatgpt/bbc/upcoming.json'
            return $result
        }
    } catch { }
    return $result
}

function Get-BbcGptJsonSnapshot {
    return @((Get-ChildItem -Path $gptBbcDir -Filter 'bbc-gpt-*.json' -ErrorAction SilentlyContinue | ForEach-Object { $_.Name }))
}

function Find-NewBbcGptJson($beforeNames, $yymmdd) {
    $pattern = if ($yymmdd) { "bbc-gpt-$yymmdd-*.json" } else { 'bbc-gpt-*.json' }
    $files = Get-ChildItem -Path $gptBbcDir -Filter $pattern -ErrorAction SilentlyContinue
    foreach ($f in ($files | Sort-Object LastWriteTime -Descending)) {
        if ($beforeNames -notcontains $f.Name) { return $f }
    }
    return $null
}

function Parse-BbcGptJsonFile($file) {
    $name = if ($file.Name) { $file.Name } else { "$file" }
    $path = if ($file.FullName) { $file.FullName } else { Join-Path $gptBbcDir $name }
    try {
        $j = Get-Content $path -Raw -Encoding UTF8 | ConvertFrom-Json
        $yymmdd = ''
        if ("$($j.id)" -match 'bbc-gpt-(\d{6})') { $yymmdd = $Matches[1] }
        elseif ($j.episode -and "$($j.episode.id)" -match 'ep-(\d{6})') { $yymmdd = $Matches[1] }
        $date = ''
        if ($j.episode -and "$($j.episode.date)" -match '^\d{4}-\d{2}-\d{2}$') {
            $date = "$($j.episode.date)"
        } elseif ($yymmdd) {
            $date = Convert-YymmddToIsoDate $yymmdd
        }
        return @{
            Date = $date
            Yymmdd = $yymmdd
            Ep = if ($yymmdd) { "ep-$yymmdd" } else { '' }
            Title = if ($j.title) { "$($j.title)" } else { '' }
            File = $name
            JsonFile = $name
        }
    } catch { }
    return $null
}

function Get-LatestBbcGptJson {
    return Get-ChildItem -Path $gptBbcDir -Filter 'bbc-gpt-*.json' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Test-BbcGptJsonValid($file) {
    $path = if ($file.FullName) { $file.FullName } else { Join-Path $gptBbcDir "$file" }
    if (-not (Test-Path $path)) { return $false }
    try {
        $j = Get-Content $path -Raw -Encoding UTF8 | ConvertFrom-Json
        if ("$($j.format)" -ne 'bbc-6min') { return $false }
        if ("$($j.source)" -ne 'chatgpt') { return $false }
        if (-not $j.sections -or @($j.sections).Count -lt 5) { return $false }
        if ("$($j.id)" -notmatch '^bbc-gpt-\d{6}-') { return $false }
        return $true
    } catch {
        return $false
    }
}

function Get-BbcJsonDialogueEnCount($j) {
    $dialogue = @($j.sections) | Where-Object { "$($_.id)" -eq 'dialogue' } | Select-Object -First 1
    if (-not $dialogue -or -not $dialogue.html) { return 0 }
    return [regex]::Matches([string]$dialogue.html, '<p class="en">').Count
}

function Test-BbcGptTranscriptQuality($file) {
    $path = if ($file.FullName) { $file.FullName } else { Join-Path $gptBbcDir "$file" }
    if (-not (Test-Path $path)) { return $false }
    try {
        $j = Get-Content $path -Raw -Encoding UTF8 | ConvertFrom-Json
        $mode = "$($j.dialogueMode)".ToLower().Trim()
        $enCount = Get-BbcJsonDialogueEnCount $j
        $transcript = "$($j.links.transcript)"
        $hasBbcPdf = $transcript -match 'downloads\.bbc\.co\.uk' -and $transcript -match '\.pdf'
        if ($mode -eq 'original') {
            if ($enCount -lt 40) {
                Log "WARN: dialogueMode=original but only $enCount EN lines (need ~50+) - will retry"
                return $false
            }
            return $true
        }
        if ($hasBbcPdf) {
            Log "WARN: dialogueMode=paraphrase but links.transcript is a BBC PDF - must retry for original transcript"
            return $false
        }
        if ($enCount -lt 40) {
            Log "WARN: dialogue has only $enCount EN lines - likely incomplete - will retry"
            return $false
        }
        Log "NOTE: accepting paraphrase (no BBC PDF transcript URL; $enCount dialogue lines)"
        return $true
    } catch {
        return $false
    }
}

function Ensure-BbcTranscriptDeps {
    Log "Checking BBC PDF tools (pymupdf)..."
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) {
        Log "WARN: python not on PATH - Codex may struggle with BBC PDF transcripts"
        return
    }
    & python -c "import fitz" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Log "Installing pymupdf for BBC PDF transcript extraction..."
        & python -m pip install pymupdf --quiet 2>&1 | ForEach-Object { Log $_ }
        & python -c "import fitz; print('pymupdf OK')" 2>&1 | ForEach-Object { Log $_ }
    } else {
        Log "pymupdf available for PDF transcripts"
    }
}

function Register-BbcJsonIfValid($jsonFile, $parsed) {
    if (-not (Test-BbcGptJsonValid $jsonFile)) {
        Log "WARN: JSON not complete yet - queue not advanced ($($jsonFile.Name))"
        return $false
    }
    if (-not (Test-BbcGptTranscriptQuality $jsonFile)) {
        Log "WARN: transcript quality gate failed - queue not advanced ($($jsonFile.Name))"
        return $false
    }
    Update-ChatgptBbcStateAfterJson $jsonFile $parsed
    return $true
}

function Update-ChatgptBbcStateAfterJson($jsonFile, $parsed) {
    if (-not (Test-Path $gptStatePath) -or -not (Test-Path $gptUpcomingPath)) { return }
    try {
        $state = Get-Content $gptStatePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $up = Get-Content $gptUpcomingPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $yymmdd = $parsed.Yymmdd
        if (-not $yymmdd) { return }

        $already = $false
        foreach ($row in @($state.sent)) {
            if ("$($row.jsonFile)" -eq $jsonFile.Name) { $already = $true; break }
            if ("$($row.episodeDate)" -eq $parsed.Date) { $already = $true; break }
        }

        if (-not $already) {
            $now = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffZ')
            $row = @{
                url = Get-BbcUrlFromYymmdd $yymmdd
                title = $parsed.Title
                episodeDate = $parsed.Date
                processedAt = $now
                jsonFile = $jsonFile.Name
            }
            $sentList = New-Object System.Collections.ArrayList
            if ($state.sent) { foreach ($s in @($state.sent)) { [void]$sentList.Add($s) } }
            [void]$sentList.Add($row)
            $state.sent = @($sentList.ToArray())
        }

        $newQueue = New-Object System.Collections.ArrayList
        $removed = $false
        foreach ($q in @($up.queue)) {
            if (-not $removed -and "$q".Trim() -eq $yymmdd) { $removed = $true; continue }
            [void]$newQueue.Add($q)
        }
        $up.queue = @($newQueue.ToArray())

        Set-Content -Path $gptStatePath -Value ($state | ConvertTo-Json -Depth 8) -Encoding UTF8
        Set-Content -Path $gptUpcomingPath -Value ($up | ConvertTo-Json -Depth 6) -Encoding UTF8
        Log "Updated chatgpt/bbc state after JSON: $($parsed.Date) -> $($jsonFile.Name)"
    } catch {
        Log "WARN: could not update chatgpt/bbc state: $($_.Exception.Message)"
    }
}

function Skip-ChatgptBbcEpisode($parsed, $reason) {
    if (-not (Test-Path $gptStatePath) -or -not (Test-Path $gptUpcomingPath)) { return }
    try {
        $state = Get-Content $gptStatePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $up = Get-Content $gptUpcomingPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $yymmdd = $parsed.Yymmdd
        if (-not $yymmdd) { return }

        $already = $false
        foreach ($row in @($state.sent)) {
            if ("$($row.episodeDate)" -eq $parsed.Date) { $already = $true; break }
            if ("$($row.url)" -match 'ep-(\d{6})' -and $Matches[1] -eq $yymmdd) { $already = $true; break }
        }

        if (-not $already) {
            $now = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffZ')
            $row = @{
                url = Get-BbcUrlFromYymmdd $yymmdd
                title = $parsed.Title
                episodeDate = $parsed.Date
                processedAt = $now
                skippedAt = $now
                skipReason = "$reason"
            }
            $sentList = New-Object System.Collections.ArrayList
            if ($state.sent) { foreach ($s in @($state.sent)) { [void]$sentList.Add($s) } }
            [void]$sentList.Add($row)
            $state.sent = @($sentList.ToArray())
        }

        $newQueue = New-Object System.Collections.ArrayList
        $removed = $false
        foreach ($q in @($up.queue)) {
            if (-not $removed -and "$q".Trim() -eq $yymmdd) { $removed = $true; continue }
            [void]$newQueue.Add($q)
        }
        $up.queue = @($newQueue.ToArray())

        Set-Content -Path $gptStatePath -Value ($state | ConvertTo-Json -Depth 8) -Encoding UTF8
        Set-Content -Path $gptUpcomingPath -Value ($up | ConvertTo-Json -Depth 6) -Encoding UTF8
        Log "Skipped chatgpt/bbc episode (batch continues): $($parsed.Date) -  $reason"
    } catch {
        Log "WARN: could not skip chatgpt/bbc episode: $($_.Exception.Message)"
    }
}

function Skip-BbcHtmlEpisode($parsed, $reason) {
    $sentPath = Join-Path $lessonsDir 'bbc-6min-sent.json'
    if (-not (Test-Path $sentPath)) { return }
    try {
        $state = Get-Content $sentPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $yymmdd = $parsed.Yymmdd
        if (-not $yymmdd) { return }

        $already = $false
        foreach ($row in @($state.sent)) {
            if ("$($row.episodeDate)" -eq $parsed.Date) { $already = $true; break }
            if ("$($row.url)" -match 'ep-(\d{6})' -and $Matches[1] -eq $yymmdd) { $already = $true; break }
        }

        if (-not $already) {
            $now = (Get-Date).ToUniversalTime().ToString('o')
            $row = @{
                url = Get-BbcUrlFromYymmdd $yymmdd
                title = $parsed.Title
                episodeDate = $parsed.Date
                processedAt = $now
                skippedAt = $now
                skipReason = "$reason"
            }
            $sentList = New-Object System.Collections.ArrayList
            if ($state.sent) { foreach ($s in @($state.sent)) { [void]$sentList.Add($s) } }
            [void]$sentList.Add($row)
            $state.sent = @($sentList.ToArray())
        }

        $upcomingList = New-Object System.Collections.ArrayList
        $removed = $false
        if ($state.upcoming) {
            foreach ($u in @($state.upcoming)) {
                $isTarget = $false
                if ("$($u.episodeDate)" -eq $parsed.Date) { $isTarget = $true }
                if ("$($u.url)" -match 'ep-(\d{6})' -and $Matches[1] -eq $yymmdd) { $isTarget = $true }
                if (-not $removed -and $isTarget) { $removed = $true; continue }
                [void]$upcomingList.Add($u)
            }
        }
        $state.upcoming = @($upcomingList.ToArray())

        Set-Content -Path $sentPath -Value ($state | ConvertTo-Json -Depth 8) -Encoding UTF8
        Log "Skipped HTML episode (batch continues): $($parsed.Date) -  $reason"
    } catch {
        Log "WARN: could not skip HTML episode: $($_.Exception.Message)"
    }
}

function Get-PendingBbcEpisodeCount {
    if ($Html) {
        $sentPath = Join-Path $lessonsDir 'bbc-6min-sent.json'
        if (-not (Test-Path $sentPath)) { return 0 }
        try {
            $state = Get-Content $sentPath -Raw -Encoding UTF8 | ConvertFrom-Json
            return @($state.upcoming).Count
        } catch { return 0 }
    }
    if (-not (Test-Path $gptUpcomingPath)) { return 0 }
    try {
        $up = Get-Content $gptUpcomingPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $done = Get-ChatgptSentYymmdds
        $n = 0
        foreach ($yymmdd in @($up.queue)) {
            $yymmdd = "$yymmdd".Trim()
            if (-not $yymmdd) { continue }
            if ($done.Contains($yymmdd)) { continue }
            if (Test-GptBbcJsonExists $yymmdd) { continue }
            $n++
        }
        return $n
    } catch { return 0 }
}

function Build-JsonCodexPrompt($ep, $retryAttempt) {
    $epLabel = Format-EpisodeLabel $ep
    $yymmdd = if ($ep.Yymmdd) { $ep.Yymmdd } else { 'YYMMDD' }
    $yyyy = Get-YyyyFromYymmdd $yymmdd
    $bbcUrl = Get-BbcUrlFromYymmdd $yymmdd
    $pdfPattern = "http://downloads.bbc.co.uk/learningenglish/features/6min/${yymmdd}_6min_english_*.pdf"
    $outDir = 'docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/bbc'
    $fname = if ($ep.Yymmdd) { "bbc-gpt-$($ep.Yymmdd)-slug.json" } else { 'bbc-gpt-YYMMDD-slug.json' }
    $outFile = "$outDir/$fname"
    $retryBlock = ''
    if ($retryAttempt -gt 1) {
        $retryBlock = @"

RETRY #$retryAttempt - previous JSON used paraphrase or incomplete dialogue. MANDATORY FIX:
- Extract the FULL BBC transcript (PDF or episode page) BEFORE writing dialogue.
- Set dialogueMode to "original" and sections[dialogue].title to "Bilingual Dialogue".
- Use the transcript English sentences VERBATIM (one <p class="en"> per spoken sentence).
- Do NOT paraphrase if any full transcript source works.
"@
    }
    return @'
Generate exactly ONE BBC 6 Minute English lesson as JSON only. Stop after this single episode.

Read first (spec wins):
docs/claude-cowork/ielts-hourly-practice-tool/specs/02-bbc-6min.md
docs/claude-cowork/ielts-hourly-practice-tool/data/templates/bbc-lesson-template.json

Target episode: EPISODE_LABEL
BBC lesson URL: BBC_URL
BBC PDF pattern (search first): PDF_PATTERN
Output file: OUT_FILE (short kebab-case slug in filename)

=== ORIGINAL TRANSCRIPT FIRST (CRITICAL) ===
Default dialogueMode MUST be "original" unless every source below fails.

Fetch order (try ALL before paraphrase):
1. BBC PDF transcript - web search: site:downloads.bbc.co.uk YYMMDD 6min english
   URL pattern: PDF_PATTERN
   Extract text with pymupdf (pip install pymupdf): python -c "import fitz; d=fitz.open('URL'); print(''.join(p.get_text() for p in d))"
   Do NOT give up on PDF because fitz was missing - install pymupdf first.
2. BBC episode page: BBC_URL (full transcript often in page HTML even when sparse)
3. Web search: BBC 6 Minute English ep-YYMMDD transcript
4. Mirrors: studocu.com, docplayer.net, afarinesh.org (complete script only)

dialogueMode rules:
- "original" + section title "Bilingual Dialogue" when you have >=90% of spoken sentences from PDF/page/mirror.
- EN dialogue lines = transcript sentences AS WRITTEN (minor punctuation only). ~60-120 <p class="en"> pairs typical.
- "paraphrase" + "Bilingual Study Dialogue" ONLY after steps 1-4 all fail (no full transcript). Never set links.transcript to a BBC PDF URL if you used paraphrase.

links.transcript: exact URL where you read the dialogue (BBC PDF preferred). Include same URL in dialogue disclaimer ext-link.

Required JSON: schema 2, format bbc-6min, source chatgpt, category bbc-6-minute-english, topicNumber 0.
Sections: vocab, dialogue, speaking-1, speaking-2, speaking-3, patterns, writing, grammar, sources.

=== NO IPA IN JSON (index.html streams pronunciation at render time) ===
- Do NOT put IPA, phonetic notation, or /slash transcriptions/ in vocab, dialogue, or anywhere.
- Forbidden: vocab-ipa class, .ipa, .ipa-line, <span class="ipa">, or /.../ after words.
- The app fetches UK/US IPA from shard files and Oxford when the user taps words or uses speaker buttons.

Never create HTML. Never edit state.json, upcoming.json, or manifest.json.
Never run git commit, git push, or update-index-and-push.ps1.
RETRY_BLOCK
'@.Replace('EPISODE_LABEL', $epLabel).Replace('BBC_URL', $bbcUrl).Replace('PDF_PATTERN', $pdfPattern).Replace('YYMMDD', $yymmdd).Replace('OUT_FILE', $outFile).Replace('RETRY_BLOCK', $retryBlock)
}

function Test-BbcGptNeedsRecheck($file, [switch]$Force) {
    if (-not (Test-BbcGptJsonValid $file)) { return $false }
    if ($Force) { return $true }
    try {
        $path = if ($file.FullName) { $file.FullName } else { Join-Path $gptBbcDir "$file" }
        $j = Get-Content $path -Raw -Encoding UTF8 | ConvertFrom-Json
        $mode = "$($j.dialogueMode)".ToLower().Trim()
        if ($mode -ne 'original') { return $true }
        return -not (Test-BbcGptTranscriptQuality $file)
    } catch {
        return $true
    }
}

function Build-RecheckTranscriptPrompt($relPath, $ep, $retryAttempt) {
    $epLabel = Format-EpisodeLabel $ep
    $yymmdd = if ($ep.Yymmdd) { $ep.Yymmdd } else { 'YYMMDD' }
    $bbcUrl = Get-BbcUrlFromYymmdd $yymmdd
    $pdfPattern = "http://downloads.bbc.co.uk/learningenglish/features/6min/${yymmdd}_6min_english_*.pdf"
    $retryBlock = ''
    if ($retryAttempt -gt 1) {
        $retryBlock = @"

RETRY #$retryAttempt - previous attempt did not produce dialogueMode original with full transcript. Try PDF extraction again with pymupdf.
"@
    }
    return @'
Recheck ONE existing BBC lesson JSON and upgrade its dialogue to the ORIGINAL BBC transcript.

Read: docs/claude-cowork/ielts-hourly-practice-tool/specs/02-bbc-6min.md (section 4.3 dialogue)

Target: EPISODE_LABEL
File (read and overwrite in place): REL_PATH
BBC lesson URL: BBC_URL
BBC PDF pattern: PDF_PATTERN

Task:
1. Open REL_PATH and read the current JSON.
2. Fetch the FULL BBC episode transcript (try ALL before giving up):
   - PDF via pymupdf: pip install pymupdf; python -c "import fitz; ..."
   - BBC episode page: BBC_URL
   - Web search + studocu/docplayer mirrors
3. If you obtain >=90% of spoken sentences from an official/mirror transcript:
   - Set top-level dialogueMode to "original"
   - Set sections[id=dialogue].title to "Bilingual Dialogue"
   - Replace sections[id=dialogue].html only: disclaimer + full verbatim EN/VI dialogue (~60-120 <p class="en"> pairs)
   - Set links.transcript to the URL you used (BBC PDF preferred)
   - Write the updated JSON back to REL_PATH (same id, same filename)
4. If NO full transcript after all sources: do NOT change the file; stop and say transcript unavailable.

MUST NOT change: title, titleVi, summary, words, vocab section, speaking sections, patterns, writing, grammar, sources, episode metadata (except links.transcript).

=== NO IPA IN JSON ===
- Do not add or edit IPA anywhere. Forbidden: vocab-ipa, .ipa, /phonetic slashes/. index.html handles pronunciation.

Never create HTML. Never edit state.json, upcoming.json, manifest.json. No git.
RETRY_BLOCK
'@.Replace('EPISODE_LABEL', $epLabel).Replace('REL_PATH', $relPath).Replace('BBC_URL', $bbcUrl).Replace('PDF_PATTERN', $pdfPattern).Replace('YYMMDD', $yymmdd).Replace('RETRY_BLOCK', $retryBlock)
}

function Invoke-RecheckBbcJsonFile($jsonFile) {
    $path = if ($jsonFile.FullName) { $jsonFile.FullName } else { Join-Path $gptBbcDir "$jsonFile" }
    $parsed = Parse-BbcGptJsonFile $jsonFile
    if (-not $parsed) {
        Log "WARN: could not parse $($jsonFile.Name) - skip"
        return @{ Success = $false; Upgraded = $false; Reason = 'ParseFailed' }
    }
    Set-LogEpisodeContext $parsed
    $relPath = $path.Substring($repoRoot.Length).TrimStart('\', '/').Replace('\', '/')
    $backup = "$path.bak"
    Copy-Item -Path $path -Destination $backup -Force
    $beforeHash = (Get-FileHash $path -Algorithm SHA256).Hash
    $maxAttempts = 3
    $lastReason = 'Unknown'

    for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
        if ($attempt -gt 1) {
            Log "Retry $attempt/$maxAttempts for $($jsonFile.Name)"
            Copy-Item -Path $backup -Destination $path -Force
            Start-Sleep -Seconds 30
        }
        Log-EpisodePhase 'RECHECK START' $parsed $jsonFile.Name
        $prompt = Build-RecheckTranscriptPrompt $relPath $parsed $attempt
        try {
            $result = Invoke-CodexGenerate $prompt $repoRoot $null
        } catch {
            Log "ERROR: $($_.Exception.Message)"
            $lastReason = $_.Exception.Message
            continue
        }
        if ($result.ExitCode -ne 0) {
            $lastReason = Get-AgentFailureReason $result.Output
            Log "Codex exited $($result.ExitCode) ($lastReason)"
            if ($lastReason -in @('ModelUnsupported', 'SpendLimit', 'Auth')) {
                Copy-Item -Path $backup -Destination $path -Force
                Remove-Item $backup -Force -ErrorAction SilentlyContinue
                return @{ Success = $false; Upgraded = $false; Reason = $lastReason; Blocked = $true }
            }
            continue
        }
        $afterHash = (Get-FileHash $path -Algorithm SHA256).Hash
        if ($afterHash -eq $beforeHash) {
            Log "WARN: file unchanged after Codex - transcript may be unavailable"
            $lastReason = 'Unchanged'
            continue
        }
        if (-not (Test-BbcGptJsonValid $jsonFile)) {
            Log "WARN: JSON invalid after recheck - restoring backup"
            $lastReason = 'InvalidJson'
            continue
        }
        try {
            $j = Get-Content $path -Raw -Encoding UTF8 | ConvertFrom-Json
            if ("$($j.dialogueMode)".ToLower().Trim() -ne 'original') {
                Log "WARN: still not dialogueMode original after recheck"
                $lastReason = 'StillParaphrase'
                continue
            }
        } catch {
            $lastReason = 'InvalidJson'
            continue
        }
        if (-not (Test-BbcGptTranscriptQuality $jsonFile)) {
            Log "WARN: transcript quality gate failed after recheck"
            $lastReason = 'QualityFailed'
            continue
        }
        Remove-Item $backup -Force -ErrorAction SilentlyContinue
        Log-EpisodePhase 'RECHECK UPGRADED' $parsed $jsonFile.Name
        return @{ Success = $true; Upgraded = $true; Reason = ''; Blocked = $false }
    }
    Copy-Item -Path $backup -Destination $path -Force
    Remove-Item $backup -Force -ErrorAction SilentlyContinue
    Log "WARN: recheck failed for $($jsonFile.Name) ($lastReason) - restored backup"
    return @{ Success = $false; Upgraded = $false; Reason = $lastReason; Blocked = $false }
}

function Exit-BbcRun($code) {
    if ($code -ne 0) {
        Log "Run ended with errors (exit $code). Safe to re-run; only complete JSON advances the queue."
    }
    exit $code
}

function Invoke-ManifestStep {
    Log ""
    Log "=== Rebuild manifest (convert_lessons.py) ==="
    Push-Location $toolRoot
    try {
        & python (Join-Path $toolRoot 'scripts\convert_lessons.py') | Out-Null
        $code = $LASTEXITCODE
        if ($null -eq $code -or "$code" -eq '') { $code = 0 }
        return [int]$code
    } finally {
        Pop-Location
    }
}

function Invoke-PushStep {
    $pushScript = Join-Path $repoRoot 'update-index-and-push.ps1'
    if (-not (Test-Path $pushScript)) {
        Log "ERROR: missing $pushScript"
        return 1
    }
    Log ""
    Log "=== Push (update-index-and-push.ps1) ==="
    $pushArgs = @()
    if ($ForcePush) { $pushArgs += '-Force' }
    & $pushScript @pushArgs
    $code = $LASTEXITCODE
    if ($null -eq $code -or "$code" -eq '') { $code = 0 }
    return [int]$code
}

function Log-EpisodePhase($phase, $ep, $extra) {
    $label = Format-EpisodeLabel $ep
    if ($extra) { $label = "$label [$extra]" }
    Log ""
    Log ">>> EPISODE $phase : $label"
    Log ""
}

function Invoke-PublishStep {
    Log ""
    Log "=== Publish (convert HTML -> JSON + manifest) ==="
    $pubSplat = @{ ForceConvert = $true }
    if ($Push) { $pubSplat.Push = $true }
    if ($ForcePush) { $pubSplat.ForcePush = $true }
    & "$repoRoot\bbc-publish-all.ps1" @pubSplat
    $code = $LASTEXITCODE
    if ($null -eq $code) { $code = 0 }
    return $code
}

function Format-CodexLine($raw) {
    $line = "$raw".Trim()
    if (-not $line) { return $null }
    if ($line.StartsWith('{')) {
        try {
            $ev = $line | ConvertFrom-Json
            $type = "$($ev.type)"
            if ($ev.item) {
                $item = $ev.item
                $itemType = "$($item.type)"
                if ($itemType -eq 'command' -and $item.command) { return "codex> $($item.command)" }
                if ($itemType -eq 'text' -and $item.text) {
                    $t = "$($item.text)".Trim()
                    if ($t.Length -gt 240) { $t = $t.Substring(0, 240) + '...' }
                    return $t
                }
            }
            if ($ev.message) { return "$($ev.message)" }
            if ($ev.text) { return "$($ev.text)" }
            if ($type) { return "codex [$type]" }
        } catch { }
    }
    if ($line.Length -gt 400) { return $line.Substring(0, 400) + '...' }
    return $line
}

function Resolve-CodexRuntime {
    $cmd = Get-Command codex -ErrorAction SilentlyContinue
    if (-not $cmd) { return $null }
    $npmDir = Split-Path $cmd.Source -Parent
    $js = Join-Path $npmDir "node_modules\@openai\codex\bin\codex.js"
    if (-not (Test-Path $js)) { return $null }
    $node = Join-Path $npmDir "node.exe"
    if (-not (Test-Path $node)) { $node = "node" }
    return @{ Node = $node; Script = $js }
}

function Invoke-CodexGenerate($prompt, $cwd, $Watch) {
    $outputLines = New-Object System.Collections.ArrayList
    $runtime = Resolve-CodexRuntime
    if (-not $runtime) {
        throw "Could not resolve codex.js from npm install."
    }

    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"

    $codexModel = Resolve-CodexModel
    $codexReasoning = Resolve-CodexReasoningEffort
    $codexArgs = @(
        $runtime.Script,
        'exec', '--json',
        '--ignore-user-config',
        '-m', $codexModel,
        '-c', "model_reasoning_effort=`"$codexReasoning`"",
        '-C', $cwd,
        '-s', 'danger-full-access',
        '--dangerously-bypass-approvals-and-sandbox',
        '-'
    )

    $knownFiles = @()
    if ($Watch -and $Watch.Before) { $knownFiles = @($Watch.Before) }
    $script:liveGeneratedEpisode = $null

    Log "Codex runtime: $($runtime.Node) $($runtime.Script) (model=$codexModel, reasoning=$codexReasoning)"
    $prompt | & $runtime.Node @codexArgs 2>&1 | ForEach-Object {
        $raw = "$_"
        [void]$outputLines.Add($raw)
        $msg = Format-CodexLine $raw
        if ($msg) { Log $msg }
        elseif ($raw.Trim()) { Log $raw }

        if ($Watch -and $Watch.FindNew) {
            $newFile = & $Watch.FindNew $knownFiles
            if ($newFile) {
                $parsed = $null
                if ($Watch.Parse) { $parsed = & $Watch.Parse $newFile }
                if ($parsed) {
                    Set-LogEpisodeContext $parsed
                    Log-EpisodePhase 'GENERATED (live)' $parsed $newFile.Name
                    $knownFiles += $newFile.Name
                    $script:liveGeneratedEpisode = $parsed
                    if ($Watch.OnNew) { & $Watch.OnNew $newFile $parsed }
                }
            }
        }
    }

    $exitCode = $LASTEXITCODE
    if ($null -eq $exitCode) { $exitCode = 0 }
    $ErrorActionPreference = $prevEAP
    return @{ Output = $outputLines; ExitCode = $exitCode; LiveEpisode = $script:liveGeneratedEpisode }
}

function Invoke-OneBbcEpisode($targetEpisode, [switch]$UseHtml) {
    $script:episodeRegistered = $false
    $maxAttempts = if ($UseHtml) { 3 } else { 4 }
    $lastReason = 'Unknown'

    for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
        if ($attempt -gt 1) {
            Log ""
            Log "Retry $attempt/$maxAttempts for $(Format-EpisodeLabel $targetEpisode)"
            Start-Sleep -Seconds 45
        }

        if ($UseHtml) {
            Log "Legacy HTML mode: full bilingual HTML lesson (~5-15 min)."
            $fileBefore = Get-BbcHtmlSnapshot
            $prompt = @'
Run the BBC 6 Minute English lesson generator per CLAUDE.md in the repo root.
The state file docs/claude-cowork/bbc-lessons/bbc-6min-sent.json is already on disk.
Target episode: EPISODE_LABEL
Generate exactly that one episode: fetch transcript, write full bilingual HTML to docs/claude-cowork/bbc-lessons/, update bbc-6min-sent.json.
Never run git commit, git push, or update-index-and-push.ps1.
Run non-interactively. If one shell command fails, retry with an alternate source.
'@.Replace('EPISODE_LABEL', (Format-EpisodeLabel $targetEpisode))
            $watch = @{
                Before = $fileBefore
                FindNew = { param($known) Find-NewBbcHtml $known }
                Parse = { param($f) Parse-BbcHtmlFile $f }
                OnNew = { param($f, $p) Update-BbcSentAfterHtml $f }
            }
        } else {
            Log "JSON-only mode: writes bbc-gpt-*.json directly (no HTML, fewer tokens)."
            Log "Expect several minutes for transcript fetch + JSON authoring."
            $fileBefore = Get-BbcGptJsonSnapshot
            $prompt = Build-JsonCodexPrompt $targetEpisode $attempt
            $yymmdd = $targetEpisode.Yymmdd
            $watch = @{
                Before = $fileBefore
                FindNew = { param($known) Find-NewBbcGptJson $known $yymmdd }
                Parse = { param($f) Parse-BbcGptJsonFile $f }
                OnNew = { param($f, $p) if (Register-BbcJsonIfValid $f $p) { $script:episodeRegistered = $true } }
            }
        }
        Log ""

        try {
            $result = Invoke-CodexGenerate $prompt $repoRoot $watch
        } catch {
            Log "ERROR: $($_.Exception.Message)"
            $lastReason = $_.Exception.Message
            continue
        }

        $exitCode = $result.ExitCode
        Log "Codex run finished (exit $exitCode)"

        if ($UseHtml) {
            if ($exitCode -ne 0) {
                $recovered = Find-NewBbcHtml $fileBefore
                if ($recovered) {
                    Log "WARN: Codex exited $exitCode but HTML exists - treating as success"
                    $exitCode = 0
                    if (-not $result.LiveEpisode) {
                        $parsed = Parse-BbcHtmlFile $recovered
                        if ($parsed) {
                            Log-EpisodePhase 'GENERATED' $parsed $recovered.Name
                            Update-BbcSentAfterHtml $recovered
                        }
                    }
                }
            }
        } else {
            if ($exitCode -ne 0) {
                if ($script:episodeRegistered) {
                    Log "WARN: Codex exited $exitCode but valid JSON was saved - treating as success"
                    $exitCode = 0
                } else {
                    $recovered = Find-NewBbcGptJson $fileBefore $targetEpisode.Yymmdd
                    if ($recovered -and (Test-BbcGptJsonValid $recovered)) {
                        Log "WARN: Codex exited $exitCode but valid JSON exists - treating as success"
                        $exitCode = 0
                        if (-not $result.LiveEpisode) {
                            $parsed = Parse-BbcGptJsonFile $recovered
                            if ($parsed) {
                                Log-EpisodePhase 'GENERATED' $parsed $recovered.Name
                                if (Register-BbcJsonIfValid $recovered $parsed) { $script:episodeRegistered = $true }
                            }
                        }
                    }
                }
            }
        }

        if ($exitCode -eq 0) {
            $completedEpisode = $result.LiveEpisode
            if ($UseHtml) {
                $newFile = Find-NewBbcHtml $fileBefore
                if ($newFile -and -not $completedEpisode) {
                    $completedEpisode = Parse-BbcHtmlFile $newFile
                    Log-EpisodePhase 'GENERATED' $completedEpisode $newFile.Name
                    Update-BbcSentAfterHtml $newFile
                } elseif (-not $completedEpisode -and ($targetEpisode.Date -or $targetEpisode.Ep)) {
                    Log "WARN: no new HTML detected; expected $(Format-EpisodeLabel $targetEpisode)"
                    $completedEpisode = $targetEpisode
                }
            } else {
                $newFile = Find-NewBbcGptJson $fileBefore $targetEpisode.Yymmdd
                if ($newFile -and -not $completedEpisode) {
                    $completedEpisode = Parse-BbcGptJsonFile $newFile
                    Log-EpisodePhase 'GENERATED' $completedEpisode $newFile.Name
                    if (Register-BbcJsonIfValid $newFile $completedEpisode) { $script:episodeRegistered = $true }
                } elseif ($script:episodeRegistered) {
                    $completedEpisode = $result.LiveEpisode
                } elseif (-not $completedEpisode -and ($targetEpisode.Date -or $targetEpisode.Ep)) {
                    Log "WARN: no new JSON detected; expected $(Format-EpisodeLabel $targetEpisode)"
                    $completedEpisode = $targetEpisode
                }
            }

            if ($UseHtml -or $script:episodeRegistered) {
                return @{ Success = $true; Blocked = $false; Reason = ''; CompletedEpisode = $completedEpisode }
            }
            $newFile = if ($UseHtml) { Find-NewBbcHtml $fileBefore } else { Find-NewBbcGptJson $fileBefore $targetEpisode.Yymmdd }
            if (-not $UseHtml -and $newFile -and (Test-BbcGptJsonValid $newFile) -and -not (Test-BbcGptTranscriptQuality $newFile)) {
                $lastReason = 'ParaphraseWhenOriginalExpected'
                Log "WARN: JSON saved but transcript quality gate failed - will retry for original dialogue"
                continue
            }
            $lastReason = 'NoValidOutput'
            Log "WARN: Codex exited 0 but no valid output file -  will retry"
            continue
        }

        $lastReason = Get-AgentFailureReason $result.Output
        switch ($lastReason) {
            'ModelUnsupported' {
                return @{ Success = $false; Blocked = $true; Reason = $lastReason; CompletedEpisode = $null }
            }
            'SpendLimit' {
                return @{ Success = $false; Blocked = $true; Reason = $lastReason; CompletedEpisode = $null }
            }
            'Auth' {
                return @{ Success = $false; Blocked = $true; Reason = $lastReason; CompletedEpisode = $null }
            }
            'RateLimit' {
                Log "Rate limit hit -  waiting 90s before retry"
                Start-Sleep -Seconds 90
            }
            default {
                Log "ERROR: lesson generation failed (see log above)."
            }
        }
    }

    return @{ Success = $false; Blocked = $false; Reason = $lastReason; CompletedEpisode = $null }
}

# Dot-sourced by bbc-recheck-transcripts.ps1 — skip batch entry when loaded as a library.
if ($MyInvocation.InvocationName -eq '.') { return }

Set-Location $repoRoot
$script:episodeRegistered = $false
$script:LogEpisodePrefix = ''

trap {
    Log ""
    Log "STOPPED: batch interrupted. Queue advances only after valid JSON (or explicit skip after retries)."
    Exit-BbcRun 130
}

$modeLabel = if ($Html) { 'HTML (legacy)' } else { 'JSON-only (chatgpt/bbc)' }
$batchLabel = if ($Single) { 'single episode' } else { 'batch until queue empty' }
Log "=== BBC lesson generate starting ==="
Log "Mode: $modeLabel | Run: $batchLabel"
Log "Close the window anytime to stop safely. No git commit/push here."
Log "Repo: $repoRoot"
if ($Html) {
    Log "Output folder: $lessonsDir"
} else {
    Log "Output folder: $gptBbcDir"
}
Log ""

if ($Html) {
    Ensure-BbcSentState | Out-Null
}

$pendingStart = Get-PendingBbcEpisodeCount
if ($pendingStart -eq 0 -and -not $PublishOnly) {
    Log "Queue empty -  nothing to generate."
    Exit-BbcRun 0
}
if (-not $PublishOnly) {
    Log "Pending episodes in queue: $pendingStart"
    Log ""
}

if ($PublishOnly) {
    if (-not $Publish) { $Publish = $true }
    $targetEpisode = if ($Html) { Get-NextBbcEpisode } else { Get-NextChatgptBbcEpisode }
    Set-LogEpisodeContext $targetEpisode
    if ($Html) {
        $latestFile = Get-LatestBbcHtml
        if ($latestFile) {
            $parsed = Parse-BbcHtmlFile $latestFile
            if ($parsed) { Set-LogEpisodeContext $parsed }
        }
    } else {
        $latestJson = Get-LatestBbcGptJson
        if ($latestJson) {
            $parsed = Parse-BbcGptJsonFile $latestJson
            if ($parsed) { Set-LogEpisodeContext $parsed }
        }
    }
    if ($Html) {
        $latestFile = Get-LatestBbcHtml
        if ($latestFile) {
            $parsed = Parse-BbcHtmlFile $latestFile
            if ($parsed) { Log-EpisodePhase 'START (publish only)' $parsed $latestFile.Name }
        } elseif ($targetEpisode.Date -or $targetEpisode.Ep) {
            Log-EpisodePhase 'START (publish only)' $targetEpisode
        }
        Log "PublishOnly: HTML pipeline (convert HTML -> JSON + manifest)."
        $pubExit = Invoke-PublishStep
        if ($pubExit -ne 0) {
            Log "ERROR: bbc-publish-all.ps1 exited $pubExit"
            Exit-BbcRun $pubExit
        }
        if ($latestFile) {
            $parsed = Parse-BbcHtmlFile $latestFile
            if ($parsed) { Log-EpisodePhase 'COMPLETE' $parsed }
        } elseif ($targetEpisode.Date -or $targetEpisode.Ep) {
            Log-EpisodePhase 'COMPLETE' $targetEpisode
        }
        Log "=== BBC publish complete ==="
        Exit-BbcRun 0
    } else {
        Log "PublishOnly: manifest rebuild for existing JSON (no HTML)."
        $manifestExit = Invoke-ManifestStep
        if ($manifestExit -ne 0) {
            Log "ERROR: convert_lessons.py exited $manifestExit"
            Exit-BbcRun $manifestExit
        }
        if ($Push) {
            $pushExit = Invoke-PushStep
            if ($pushExit -ne 0) { Exit-BbcRun $pushExit }
        }
        $latestJson = Get-LatestBbcGptJson
        if ($latestJson) {
            $parsed = Parse-BbcGptJsonFile $latestJson
            if ($parsed) { Log-EpisodePhase 'COMPLETE' $parsed $latestJson.Name }
        }
        Log "=== BBC manifest publish complete ==="
        Exit-BbcRun 0
    }
}

$codex = Get-Command codex -ErrorAction SilentlyContinue
if (-not $codex) {
    Log "ERROR: codex CLI not found on PATH."
    Log "Install: npm install -g @openai/codex  then run: codex login"
    Write-ManualFallback "codex CLI not found"
    Exit-BbcRun 1
}

Log "Running: codex exec --json --ignore-user-config (streaming live to console + log)"
Log "Log file: $logFile"
Log ""

if (-not $Html) {
    Ensure-BbcTranscriptDeps
    Log ""
}

$batchStats = @{ Ok = 0; Skipped = 0; Index = 0 }

while ($true) {
    if ($Html) {
        $targetEpisode = Get-NextBbcEpisode
    } else {
        $targetEpisode = Get-NextChatgptBbcEpisode
    }

    if (-not ($targetEpisode.Date -or $targetEpisode.Ep)) {
        Log "Queue empty -  batch finished."
        break
    }

    Set-LogEpisodeContext $targetEpisode
    $batchStats.Index++
    $pending = Get-PendingBbcEpisodeCount

    Log "--- Batch $($batchStats.Index) | ~$pending episode(s) left in queue ---"
    if ($targetEpisode.Source) {
        Log "Queue source: $($targetEpisode.Source)"
    }
    Log-EpisodePhase 'START' $targetEpisode

    $epResult = Invoke-OneBbcEpisode $targetEpisode -UseHtml:$Html

    if ($epResult.Blocked) {
        $reason = $epResult.Reason
        switch ($reason) {
            'ModelUnsupported' {
                Log "BLOCKED: Codex model is not supported with your ChatGPT account."
                Log "Fix: set BBC_CODEX_MODEL=gpt-5.4-mini (or gpt-5.4) and retry."
            }
            'SpendLimit' {
                Log "BLOCKED: Codex/ChatGPT usage limit reached."
                Log "Fix: check ChatGPT/Codex billing or wait for quota reset."
            }
            'Auth' {
                Log "BLOCKED: Codex is not authenticated."
                Log "Fix: run 'codex login' in a terminal, then retry."
            }
            default {
                Log "BLOCKED: $reason"
            }
        }
        Write-ManualFallback $reason
        Log "Batch stopped after $($batchStats.Ok) ok, $($batchStats.Skipped) skipped."
        Exit-BbcRun 1
    }

    if ($epResult.Success) {
        $batchStats.Ok++
        if ($Html) {
            Log "HTML lessons on disk: $((Get-ChildItem -Path $lessonsDir -Filter 'bbc-6min-*.html' -ErrorAction SilentlyContinue).Count)"
        } else {
            Log "GPT BBC JSON on disk: $((Get-ChildItem -Path $gptBbcDir -Filter 'bbc-gpt-*.json' -ErrorAction SilentlyContinue).Count)"
        }

        if ($Publish) {
            if ($Html) {
                $pubExit = Invoke-PublishStep
                if ($pubExit -ne 0) {
                    Log "WARN: bbc-publish-all.ps1 exited $pubExit -  continuing batch"
                }
            } else {
                if (-not $script:episodeRegistered) {
                    Log "WARN: manifest skipped -  no valid JSON registered"
                } else {
                    $manifestExit = Invoke-ManifestStep
                    if ($manifestExit -ne 0) {
                        Log "WARN: convert_lessons.py exited $manifestExit -  continuing batch"
                    }
                }
            }
            if ($epResult.CompletedEpisode) {
                Log-EpisodePhase 'COMPLETE' $epResult.CompletedEpisode
            }
        }
    } else {
        $batchStats.Skipped++
        Log "WARN: episode failed after retries ($($epResult.Reason)) -  skipping, continuing batch"
        if ($Html) {
            Skip-BbcHtmlEpisode $targetEpisode $epResult.Reason
        } else {
            Skip-ChatgptBbcEpisode $targetEpisode $epResult.Reason
        }
    }

    if ($Single) {
        Log "Single-episode mode (-Single) -  stopping after one item."
        break
    }

    Log ""
}

Log ""
Log "=== BBC batch complete ==="
Log "Generated: $($batchStats.Ok) | Skipped: $($batchStats.Skipped) | Processed: $($batchStats.Index)"
if (-not $Publish) {
    Log ""
    if ($Html) {
        Log "Next: bbc-publish-all.ps1, or re-run with -Publish"
    } else {
        Log "Next: re-run with -Publish for manifest, then update-index-and-push.ps1 for GitHub"
    }
} else {
    if ($batchStats.Ok -gt 0 -and -not $Html) {
        Log "Final manifest rebuild..."
        $manifestExit = Invoke-ManifestStep
        if ($manifestExit -ne 0) {
            Log "WARN: final convert_lessons.py exited $manifestExit"
        }
    }
    Log "GitHub: run update-index-and-push.ps1 when you want to commit and push"
}
Exit-BbcRun 0
