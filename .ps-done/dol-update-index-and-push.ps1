# dol-update-index-and-push.ps1
# BACKUP copy of update-index-and-push.ps1 (DOL is no longer inline here).
# Use dol-done-publish-all.ps1 for DOL fetch/publish; use update-index-and-push.ps1 for index/manifest/push only.
# Scan docs/claude-cowork, rebuild HTML index from current folder structure, then push to GitHub.
# See: docs/SCRIPTS.md for full documentation.
# Skips convert/index pipeline when nothing changed (use -Force to run anyway).
# DOL fetch/publish: use dol-done-publish-all.ps1 (backup with DOL inline: dol-update-index-and-push.ps1)

param(
    [switch]$Force
)

$rootDir  = $PSScriptRoot
$scanDir  = Join-Path $rootDir "docs\claude-cowork"
$htmlFile = Join-Path $rootDir "docs\index-claude-cowork-13571357.html"
$today    = Get-Date -Format "yyyy-MM-dd"

$iconMap = @{
    "aws"      = "&#9729;"
    "bbc"      = "&#127897;"
    "finance"  = "&#128185;"
    "morning"  = "&#127749;"
    "news"     = "&#128240;"
    "weekly"   = "&#128202;"
    "worldcup" = "&#9917;"
    "world"    = "&#9917;"
    "brief"    = "&#128203;"
    "report"   = "&#128200;"
    "log"      = "&#128221;"
}

function Get-Icon($name) {
    $lower = $name.ToLower()
    foreach ($key in $iconMap.Keys) {
        if ($lower -like "*$key*") { return $iconMap[$key] }
    }
    return "&#128196;"
}

function Get-ExtClass($ext) {
    switch ($ext) {
        "html" { return "ext-html" }
        "pdf"  { return "ext-pdf" }
        "md"   { return "ext-md" }
        default { return "ext-html" }
    }
}

function Test-HasPendingBbcSync {
    param([string]$RepoRoot, [string]$BbcLessonsDir)

    $claudeSessionsRoot = Join-Path $env:APPDATA "Claude\local-agent-mode-sessions"
    if (-not (Test-Path $claudeSessionsRoot)) { return $false }

    $bbcFiles = Get-ChildItem -Path $claudeSessionsRoot -Recurse -Filter "bbc-6min-*.html" -ErrorAction SilentlyContinue |
        Where-Object { $_.DirectoryName -like "*\outputs*" }

    foreach ($f in $bbcFiles) {
        $dest = Join-Path $BbcLessonsDir $f.Name
        if (-not (Test-Path $dest)) { return $true }
    }
    return $false
}

# ---- -1. Pull first: other agents (ChatGPT via GitHub connector) commit to this repo ----

Set-Location $rootDir

$headBefore = (git rev-parse HEAD 2>$null)
if (-not $headBefore) {
    Write-Host "FAILED: not a git repository" -ForegroundColor Red
    exit 1
}

git pull --rebase --autostash
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARN: git pull failed - continuing with local state (push may be rejected)" -ForegroundColor Yellow
} else {
    Write-Host "OK: pulled latest from GitHub" -ForegroundColor Green
}

$headAfter = (git rev-parse HEAD 2>$null)
$pulledNew = ($headBefore -ne $headAfter)
$hasLocalChanges = [bool](git status --porcelain 2>$null)
$bbcLessonsDir = Join-Path $rootDir "docs\claude-cowork\bbc-lessons"
$hasPendingBbc = Test-HasPendingBbcSync -RepoRoot $rootDir -BbcLessonsDir $bbcLessonsDir

if (-not $Force -and -not $pulledNew -and -not $hasLocalChanges -and -not $hasPendingBbc) {
    Write-Host "INFO: No new commits, local changes, or BBC sync - skipping convert/index. Pass -Force to run anyway." -ForegroundColor Green
    exit 0
}

if ($Force) {
    Write-Host "OK: -Force specified, running full pipeline" -ForegroundColor Cyan
} elseif ($pulledNew) {
    Write-Host "OK: New commits pulled - running pipeline" -ForegroundColor Green
} elseif ($hasLocalChanges) {
    Write-Host "OK: Local changes detected - running pipeline" -ForegroundColor Green
} else {
    Write-Host "OK: Pending BBC sync - running pipeline" -ForegroundColor Green
}

# Re-index study content after the pull so lessons committed by other agents enter manifest.json
$ieltsConverter = Join-Path $rootDir "docs\claude-cowork\ielts-hourly-practice-tool\scripts\convert_lessons.py"
if (Test-Path $ieltsConverter) {
    try { python $ieltsConverter } catch { Write-Host "WARN: convert_lessons.py failed: $($_.Exception.Message)" -ForegroundColor Yellow }
}

# ---- BBC SYNC: copy any bbc-6min-*.html from Claude outputs into bbc-lessons ----

if (-not (Test-Path $bbcLessonsDir)) {
    New-Item -ItemType Directory -Path $bbcLessonsDir -Force | Out-Null
    Write-Host "OK: Created bbc-lessons folder" -ForegroundColor Green
}

$claudeSessionsRoot = Join-Path $env:APPDATA "Claude\local-agent-mode-sessions"

if (Test-Path $claudeSessionsRoot) {
    $bbcFiles = Get-ChildItem -Path $claudeSessionsRoot -Recurse -Filter "bbc-6min-*.html" -ErrorAction SilentlyContinue |
        Where-Object { $_.DirectoryName -like "*\outputs*" }

    foreach ($f in $bbcFiles) {
        $dest = Join-Path $bbcLessonsDir $f.Name
        if (-not (Test-Path $dest)) {
            Copy-Item -Path $f.FullName -Destination $dest -Force
            Write-Host ('SYNC: Copied {0} to bbc-lessons\' -f $f.Name) -ForegroundColor Cyan
        }
    }

    if (-not $bbcFiles) {
        Write-Host "INFO: No new BBC lesson files found in Claude outputs." -ForegroundColor Gray
    }
} else {
    Write-Host "WARN: Claude sessions folder not found, skipping BBC sync." -ForegroundColor Yellow
}

# ---- 0. Sync docs/index.html manifest: drop entries for deleted folders ----

$docsDir      = Join-Path $rootDir "docs"
$mainIndex    = Join-Path $docsDir "index.html"
$existingDirs = (Get-ChildItem -Path $docsDir -Directory).Name
$mainHtml     = Get-Content $mainIndex -Raw -Encoding UTF8
$openTag      = '<script type="application/json" id="siteManifest">'
$closeTag     = '</script>'
$openIdx      = $mainHtml.IndexOf($openTag)
$closeIdx     = $mainHtml.IndexOf($closeTag, $openIdx + $openTag.Length)

if ($openIdx -ge 0 -and $closeIdx -gt $openIdx) {
    $jsonStart    = $openIdx + $openTag.Length
    $manifestJson = $mainHtml.Substring($jsonStart, $closeIdx - $jsonStart).Trim()
    $manifest     = $manifestJson | ConvertFrom-Json
    $before       = $manifest.sites.Count

    $keptSites = New-Object System.Collections.Generic.List[object]
    foreach ($site in $manifest.sites) {
        $topFolder = ($site.folder -split '[/\\]')[0]
        if ($existingDirs -contains $topFolder) {
            $keptSites.Add($site)
        }
    }

    $after = $keptSites.Count
    if ($before -ne $after) {
        $manifest.sites = $keptSites.ToArray()
        $newJson  = $manifest | ConvertTo-Json -Depth 10
        $mainHtml = $mainHtml.Substring(0, $jsonStart) + "`n" + $newJson + "`n" + $mainHtml.Substring($closeIdx)
        Set-Content -Path $mainIndex -Value $mainHtml -Encoding UTF8 -NoNewline
        Write-Host ('OK: index.html manifest trimmed ({0} -> {1} entries)' -f $before, $after) -ForegroundColor Green
    } else {
        Write-Host ('OK: index.html manifest unchanged ({0} entries)' -f $after) -ForegroundColor Gray
    }
}

# ---- 1. Clean up tracked .html/.json for removed claude-cowork subfolders ----

Set-Location $rootDir

$trackedSubDirs = git ls-files "docs/claude-cowork/" 2>$null |
    ForEach-Object { ($_ -replace '^docs/claude-cowork/', '') -split '/' | Select-Object -First 1 } |
    Where-Object { $_ -and $_ -ne '' } |
    Select-Object -Unique

$currentDirs = Get-ChildItem -Path $scanDir -Directory | Select-Object -ExpandProperty Name

foreach ($td in $trackedSubDirs) {
    if ($currentDirs -notcontains $td) {
        $orphans = git ls-files "docs/claude-cowork/$td/" 2>$null |
            Where-Object { $_ -like "*.html" -or $_ -like "*.json" }
        foreach ($f in $orphans) {
            git rm -f --cached $f 2>$null | Out-Null
            Write-Host "CLEANUP: untracked '$f' (folder removed)" -ForegroundColor Magenta
        }
    }
}

# ---- 2. Rebuild index-claude-cowork HTML from current folder structure ----

$sections = ""

Get-ChildItem -Path $scanDir -Directory | Sort-Object Name | ForEach-Object {
    $dir      = $_
    $dirName  = $dir.Name
    $icon     = Get-Icon($dirName)
    $dirHref  = "claude-cowork/$dirName/"

    $files = Get-ChildItem -Path $dir.FullName -File |
             Where-Object { $_.Extension -in ".html", ".pdf", ".md" -and $_.Name -notlike ".*" } |
             Sort-Object Name

    $fileCount  = $files.Count
    $countLabel = if ($fileCount -eq 1) { "1 file" } else { "$fileCount files" }

    $fileRows = ""
    foreach ($f in $files) {
        $ext      = $f.Extension.TrimStart(".")
        $extClass = Get-ExtClass($ext)
        $baseName = $f.BaseName
        $fileHref = "claude-cowork/$dirName/$($f.Name)"
        $fileRows += @"

        <a class="file-item" href="$fileHref" target="_blank" rel="noopener">
          <span class="file-ext $extClass">$ext</span>
          <span class="file-name">$baseName</span>
          <span class="file-arrow">&#8250;</span>
        </a>
"@
    }

    if ($fileRows -eq "") {
        $fileRows = "`n        <span class=`"empty`">No files yet</span>"
    }

    $sections += @"

    <div class="section">
      <div class="section-header">
        <span class="section-icon">$icon</span>
        <span class="section-name">$dirName</span>
        <span class="section-count">$countLabel</span>
      </div>
      <div class="file-list">$fileRows
        <a class="dir-link" href="$dirHref" target="_blank" rel="noopener">&#128193; View folder &#8250;</a>
      </div>
    </div>
"@
}

$html = Get-Content $htmlFile -Raw -Encoding UTF8
$html = $html -replace 'last updated \d{4}-\d{2}-\d{2}', "last updated $today"
$html = $html -replace '(?s)<!-- BEGIN_SECTIONS -->.*?<!-- END_SECTIONS -->', "<!-- BEGIN_SECTIONS -->$sections`n<!-- END_SECTIONS -->"
Set-Content -Path $htmlFile -Value $html -Encoding UTF8 -NoNewline

Write-Host "OK: Index updated ($($currentDirs.Count) folders)" -ForegroundColor Green

# ---- (S3 content sync removed 2026-07-09: the bucket now stores ONLY user-data.json, which the
#       web app reads/writes itself. This script pushes to GitHub only.) ----

# ---- 3. Git commit + push ----

$status = git status --porcelain
if (-not $status) {
    Write-Host "INFO: Khong co thay doi nao de push." -ForegroundColor Yellow
    exit
}

Write-Host ""
Write-Host "Files thay doi:" -ForegroundColor Yellow
git status --short

git add .
git commit -m "update: $today $(Get-Date -Format 'HH:mm')"

Write-Host ""
Write-Host "Dang push len GitHub..." -ForegroundColor Cyan
git push

if ($LASTEXITCODE -eq 0) {
    Write-Host "OK: Push thanh cong!" -ForegroundColor Green
} else {
    Write-Host "FAILED: Push that bai. Kiem tra ket noi hoac credentials." -ForegroundColor Red
}
