# Rebuild manifest for existing BBC JSON (no Codex — fast).
# DEFAULT: manifest only from data/chatgpt/bbc/*.json
# Legacy HTML pipeline: powershell -File bbc-publish-only.ps1 -Html
param(
    [switch]$Html,
    [switch]$Push,
    [switch]$ForcePush
)

$splat = @{ PublishOnly = $true; Publish = $true }
if ($Html) { $splat.Html = $true }
if ($Push) { $splat.Push = $true }
if ($ForcePush) { $splat.ForcePush = $true }

& "$PSScriptRoot\bbc-generate-lesson.ps1" @splat
if ($LASTEXITCODE -ne $null) { exit $LASTEXITCODE }
