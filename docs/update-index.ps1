$ErrorActionPreference = 'Stop'

$docsPath = $PSScriptRoot
$manifestPath = Join-Path $docsPath 'sites.json'
$encoding = [System.Text.UTF8Encoding]::new($false)
$noListingHtml = @'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow">
  <title>Not Listed</title>
  <style>
    body { margin: 0; min-height: 100vh; display: grid; place-items: center; font-family: "Segoe UI", Arial, sans-serif; color: #172033; background: #f7f9fc; }
    main { width: min(520px, calc(100% - 32px)); border: 1px solid #d9e2ef; border-radius: 8px; background: #fff; padding: 24px; }
    h1 { margin: 0 0 8px; font-size: 28px; line-height: 1.15; }
    p { margin: 0; color: #607086; }
  </style>
</head>
<body>
  <main>
    <h1>Not listed</h1>
    <p>Open a known file URL directly.</p>
  </main>
</body>
</html>
'@

$sites = Get-ChildItem -LiteralPath $docsPath -Directory |
  Where-Object { $_.Name -notmatch 'private$' } |
  ForEach-Object {
    $indexPath = Join-Path $_.FullName 'index.html'
    if (-not (Test-Path -LiteralPath $indexPath -PathType Leaf)) {
      return
    }

    [pscustomobject]@{
      folder = $_.Name
      title = $_.Name
      href = "$($_.Name)/index.html"
    }
  } |
  Sort-Object folder

$payload = [pscustomobject]@{
  generatedAt = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
  sites = @($sites)
}

$json = $payload | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText($manifestPath, "$json`n", $encoding)

$indexPath = Join-Path $docsPath 'index.html'
if (Test-Path -LiteralPath $indexPath -PathType Leaf) {
  $indexHtml = [System.IO.File]::ReadAllText($indexPath, $encoding)
  $embeddedJson = ($json -replace '<', '\u003c')
  $pattern = '(?s)(<script type="application/json" id="siteManifest">\s*)(.*?)(\s*</script>)'

  if ($indexHtml -notmatch $pattern) {
    throw "Could not find siteManifest block in $indexPath"
  }

  $indexHtml = [regex]::Replace(
    $indexHtml,
    $pattern,
    { param($match) $match.Groups[1].Value + $embeddedJson + $match.Groups[3].Value },
    1
  )
  [System.IO.File]::WriteAllText($indexPath, $indexHtml, $encoding)
}

$createdIndexes = 0
Get-ChildItem -LiteralPath $docsPath -Directory -Recurse |
  ForEach-Object {
    $indexPath = Join-Path $_.FullName 'index.html'
    if (-not (Test-Path -LiteralPath $indexPath -PathType Leaf)) {
      [System.IO.File]::WriteAllText($indexPath, $noListingHtml, $encoding)
      $createdIndexes++
    }
  }

Write-Host "Updated $manifestPath with $($sites.Count) public site(s)."
if ($createdIndexes -gt 0) {
  Write-Host "Added $createdIndexes no-listing index file(s)."
}
