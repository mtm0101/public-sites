# ============================ DEPRECATED (2026-07-09) ============================
# The S3 bucket is NO LONGER a content channel — it stores ONLY user-data.json, which
# the web app reads/writes itself. Content is served from the repo (GitHub Pages/local).
# Do NOT run this script as part of any pipeline. Kept only for reference/emergency.
# ==================================================================================
# Upload the contents of the local data/ folder to the bucket (DEPRECATED — content no longer uses S3).
# Historical note: data/claude-cowork/lessons/... used to map to bucket key claude-cowork/lessons/...
#
# STATUS (2026-07-09, all working): anonymous LIST/GET/PUT all work — PUTs MUST carry an
# `x-amz-checksum-sha256` header (Content-MD5 alone is rejected with a SigV4 demand by the
# bucket's Object Lock). CORS is enabled (Allow-Origin *, GET/PUT/HEAD, content-type +
# x-amz-checksum-sha256), so browsers can scan/read/save directly. DELETE stays denied.
# This script also publishes index.html to the bucket root, so the app itself runs from
#   https://t-do-not-delete-ihp-7xf29m4kq9vnb1zt8we5yu3hj6kf0fd4jh1sa9vr2mn.s3.amazonaws.com/index.html
# Run:  powershell -File scripts/upload-to-s3.ps1  (from tool root; DEPRECATED)

$base = 'https://t-do-not-delete-ihp-7xf29m4kq9vnb1zt8we5yu3hj6kf0fd4jh1sa9vr2mn.s3.amazonaws.com'
$root = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) '..\data'
if (-not (Test-Path $root)) { Write-Host "data/ folder not found next to this script."; exit 1 }
$ok = 0; $fail = 0

function Put-S3([string]$key, [byte[]]$bytes, [string]$ctype = 'application/json') {
    $sha = [Convert]::ToBase64String(([Security.Cryptography.SHA256]::Create()).ComputeHash($bytes))
    try {
        Invoke-WebRequest -Uri "$base/$key" -Method Put -Body $bytes `
            -ContentType $ctype -Headers @{ 'x-amz-checksum-sha256' = $sha } `
            -UseBasicParsing -TimeoutSec 60 | Out-Null
        Write-Host "OK    $key"; $script:ok++
    } catch {
        Write-Host "FAIL  $key  $($_.Exception.Message)"; $script:fail++
    }
}

# the app itself, served same-origin from the bucket
$appHtml = Join-Path (Split-Path -Parent $root) 'index.html'
if (Test-Path $appHtml) { Put-S3 'index.html' ([IO.File]::ReadAllBytes($appHtml)) 'text/html; charset=utf-8' }

# folder markers for every directory under data/ (so the prefixes exist even while empty)
Get-ChildItem $root -Recurse -Directory | ForEach-Object {
    $key = ($_.FullName.Substring($root.Length + 1) -replace '\\', '/') + '/'
    Put-S3 $key ([byte[]]@())
}

# every .json under data/, keys relative to data/ (user-data.json is never uploaded by this script
# so a cloud save from the app is not overwritten)
Get-ChildItem $root -Filter '*.json' -Recurse | Where-Object { $_.Name -ne 'user-data.json' } | ForEach-Object {
    $key = $_.FullName.Substring($root.Length + 1) -replace '\\', '/'
    Put-S3 $key ([IO.File]::ReadAllBytes($_.FullName))
}
Write-Host "`nUploaded $ok object(s), $fail failed."
if ($fail -gt 0) { Write-Host 'If everything failed with 400: the Object Lock / policy / CORS fixes above are still pending.' }
