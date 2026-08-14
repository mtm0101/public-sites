# cleanup-s3.ps1 — delete EVERY object in the bucket EXCEPT user-data.json.
# The app now uses S3 only for user-data.json; all other objects are orphans from the
# retired content-sync architecture.
#
# STATUS (2026-07-10): anonymous DELETE is still DENIED (403) — the bucket policy does not
# grant s3:DeleteObject to the public. Two ways to run this cleanup:
#
#   OPTION A (recommended, with AWS credentials — no bucket changes needed):
#     aws s3 rm s3://t-do-not-delete-ihp-7xf29m4kq9vnb1zt8we5yu3hj6kf0fd4jh1sa9vr2mn/ `
#       --recursive --exclude "user-data.json"
#     (With Object Lock, this adds delete markers: old versions remain stored but every
#      object disappears from listings and GETs, which is all that matters here.)
#
#   OPTION B (anonymous, via this script): add s3:DeleteObject for Principal "*" to the
#     bucket policy (can be removed again right after), then run:
#       powershell -File cleanup-s3.ps1
#
$base = 'https://t-do-not-delete-ihp-7xf29m4kq9vnb1zt8we5yu3hj6kf0fd4jh1sa9vr2mn.s3.amazonaws.com'
$keep = 'user-data.json'

# quick permission probe before sweeping
try {
    Invoke-WebRequest -Uri "$base/cleanup-probe-does-not-exist.json" -Method Delete -UseBasicParsing -TimeoutSec 30 | Out-Null
} catch {
    if ($_.Exception.Response -and [int]$_.Exception.Response.StatusCode -eq 403) {
        Write-Host "ABORT: DELETE is still denied by the bucket policy (403). See OPTION A/B in this script's header." -ForegroundColor Red
        exit 1
    }
    # 404/204 etc. = deletes are permitted; continue
}

# list every key (paged), then delete all except user-data.json
$keys = @(); $token = ''
do {
    $url = "$base/?list-type=2&max-keys=1000"
    if ($token) { $url += "&continuation-token=" + [Uri]::EscapeDataString($token) }
    [xml]$xml = (Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 30).Content
    foreach ($c in $xml.ListBucketResult.Contents) { $keys += $c.Key }
    $token = if ($xml.ListBucketResult.IsTruncated -eq 'true') { $xml.ListBucketResult.NextContinuationToken } else { '' }
} while ($token)

$ok = 0; $fail = 0; $kept = 0
foreach ($k in $keys) {
    if ($k -eq $keep) { $kept++; Write-Host "KEEP  $k" -ForegroundColor Green; continue }
    try {
        Invoke-WebRequest -Uri "$base/$([Uri]::EscapeDataString($k) -replace '%2F','/')" -Method Delete -UseBasicParsing -TimeoutSec 30 | Out-Null
        Write-Host "DEL   $k"
        $ok++
    } catch {
        Write-Host "FAIL  $k  $($_.Exception.Message)" -ForegroundColor Red
        $fail++
    }
}
Write-Host "`nDeleted $ok, kept $kept, failed $fail (of $($keys.Count) objects)."
