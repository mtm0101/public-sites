$ErrorActionPreference = 'Stop'

$docsPath = $PSScriptRoot
$manifestPath = Join-Path $docsPath 'sites.json'
$mainIndexPath = Join-Path $docsPath 'index.html'
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

function Get-RelativePath {
  param(
    [Parameter(Mandatory = $true)]
    [string]$BasePath,
    [Parameter(Mandatory = $true)]
    [string]$TargetPath
  )

  $baseRoot = [System.IO.Path]::GetFullPath($BasePath).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
  $targetFullPath = [System.IO.Path]::GetFullPath($TargetPath)

  if (-not $targetFullPath.StartsWith($baseRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "$TargetPath is not under $BasePath"
  }

  return $targetFullPath.Substring($baseRoot.Length)
}

function Test-PrivateRelativePath {
  param(
    [Parameter(Mandatory = $true)]
    [string]$RelativePath
  )

  return @($RelativePath -split '[\\/]' | Where-Object { $_ -match '(?i)private$' }).Count -gt 0
}

function Test-NoListingIndex {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Path
  )

  $content = [System.IO.File]::ReadAllText($Path, $encoding)
  return $content -match '<title>\s*Not Listed\s*</title>' -and $content -match 'Open a known file URL directly\.'
}

function Get-IndexTitle {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Path,
    [Parameter(Mandatory = $true)]
    [string]$Fallback
  )

  $content = [System.IO.File]::ReadAllText($Path, $encoding)
  $match = [regex]::Match($content, '(?is)<title[^>]*>(.*?)</title>')

  if (-not $match.Success) {
    return $Fallback
  }

  $title = [System.Net.WebUtility]::HtmlDecode($match.Groups[1].Value)
  $title = [regex]::Replace($title, '\s+', ' ').Trim()

  if ([string]::IsNullOrWhiteSpace($title)) {
    return $Fallback
  }

  return $title
}

$sites = Get-ChildItem -LiteralPath $docsPath -Filter 'index.html' -File -Recurse |
  ForEach-Object {
    $indexFile = $_
    $relativeIndex = Get-RelativePath -BasePath $docsPath -TargetPath $indexFile.FullName
    $relativeFolder = Split-Path -Parent $relativeIndex

    if ($indexFile.FullName -ne $mainIndexPath -and
        -not [string]::IsNullOrWhiteSpace($relativeFolder) -and
        -not (Test-PrivateRelativePath -RelativePath $relativeFolder) -and
        -not (Test-NoListingIndex -Path $indexFile.FullName)) {
      $folder = $relativeFolder -replace '\\', '/'
      $href = $relativeIndex -replace '\\', '/'

      [pscustomobject]@{
        folder = $folder
        title = Get-IndexTitle -Path $indexFile.FullName -Fallback $indexFile.Directory.Name
        href = $href
        createdAt = $indexFile.Directory.CreationTimeUtc.ToString('yyyy-MM-ddTHH:mm:ssZ')
      }
    }
  }

$sites = @($sites | Sort-Object -Property @{ Expression = { $_.createdAt }; Descending = $true }, folder)

$payload = [pscustomobject]@{
  generatedAt = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
  sites = @($sites)
}

$json = $payload | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText($manifestPath, "$json`n", $encoding)

if (Test-Path -LiteralPath $mainIndexPath -PathType Leaf) {
  $indexHtml = [System.IO.File]::ReadAllText($mainIndexPath, $encoding)
  $embeddedJson = ($json -replace '<', '\u003c')
  $pattern = '(?s)(<script type="application/json" id="siteManifest">\s*)(.*?)(\s*</script>)'

  if ($indexHtml -notmatch $pattern) {
    throw "Could not find siteManifest block in $mainIndexPath"
  }

  $indexHtml = [regex]::Replace(
    $indexHtml,
    $pattern,
    { param($match) $match.Groups[1].Value + $embeddedJson + $match.Groups[3].Value },
    1
  )
  [System.IO.File]::WriteAllText($mainIndexPath, $indexHtml, $encoding)
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
