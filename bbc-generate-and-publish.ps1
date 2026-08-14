# One-click: batch-generate ALL pending BBC episodes (JSON), rebuild manifest each success.
# Runs until queue empty. Close window anytime to stop safely.
# No git commit/push (use update-index-and-push.ps1 later).
#
# DEFAULT: JSON-only, Codex gpt-5.4-mini + low reasoning (cost-efficient).
# Override: BBC_CODEX_MODEL / BBC_CODEX_REASONING env vars.
#
# One episode only: powershell -File bbc-generate-and-publish.ps1 -Single
# Log lines prefixed: [2022-05-19 ep-220519] ...
#
# Legacy HTML: powershell -File bbc-generate-and-publish.ps1 -Html
# Manifest only: powershell -File bbc-generate-and-publish.ps1 -PublishOnly
param(
    [switch]$Html,
    [switch]$PublishOnly,
    [switch]$Push,
    [switch]$ForcePush,
    [switch]$Single
)

$splat = @{ Publish = $true }
if ($Html) { $splat.Html = $true }
if ($PublishOnly) { $splat.PublishOnly = $true }
if ($Push) { $splat.Push = $true }
if ($ForcePush) { $splat.ForcePush = $true }
if ($Single) { $splat.Single = $true }
& "$PSScriptRoot\bbc-generate-lesson.ps1" @splat
if ($LASTEXITCODE -ne $null) { exit $LASTEXITCODE }
