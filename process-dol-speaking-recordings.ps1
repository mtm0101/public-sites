[CmdletBinding()]
param(
    [string]$SourcePath = 'C:\Users\thiendd3\Downloads\gpt-codex\_temp\DOL Speaking Recordings',
    [string]$WhisperModel = 'small',
    [string]$OllamaModel = 'qwen2.5:3b',
    [ValidateSet('auto', 'cuda', 'cpu')]
    [string]$Device = 'auto',
    [bool]$InstallDependencies = $true,
    [switch]$Force,
    [int]$HtmlOnlyFrom = 0,
    [switch]$SkipManifest,
    [switch]$Publish
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = $PSScriptRoot
$AppRoot = Join-Path $RepoRoot 'docs\claude-cowork\ielts-hourly-practice-tool'
$PythonHelper = Join-Path $AppRoot 'scripts\dol_recordings_pipeline.py'
$RuntimeRoot = Join-Path $SourcePath '._dol_pipeline'
$VenvRoot = Join-Path $RuntimeRoot '.venv'
$VenvPython = Join-Path $VenvRoot 'Scripts\python.exe'

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Test-OllamaApi {
    try {
        Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 3 | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

if (-not (Test-Path -LiteralPath $SourcePath -PathType Container)) {
    throw "Recording folder not found: $SourcePath"
}
if (-not (Test-Path -LiteralPath $PythonHelper -PathType Leaf)) {
    throw "Pipeline helper not found: $PythonHelper"
}

$Videos = @(Get-ChildItem -LiteralPath $SourcePath -File | Where-Object Extension -In '.mp4', '.mkv', '.mov', '.webm')
if ($Videos.Count -eq 0) {
    throw "No supported video files found in: $SourcePath"
}

New-Item -ItemType Directory -Path $RuntimeRoot -Force | Out-Null

if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Step 'Creating an isolated Python 3.11 environment'
    & py -3.11 -m venv $VenvRoot
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
}

if ($InstallDependencies) {
    Write-Step 'Installing free local transcription dependencies'
    & $VenvPython -m pip install --disable-pip-version-check --upgrade pip
    & $VenvPython -m pip install --disable-pip-version-check 'faster-whisper>=1.1,<2' 'imageio-ffmpeg>=0.6,<1' 'nvidia-cudnn-cu12>=9,<10' 'argostranslate>=1.9,<2'
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
}

$OllamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
$OllamaExe = if ($OllamaCommand) { $OllamaCommand.Source } else { $null }
$PortableOllama = Join-Path $RuntimeRoot 'ollama'
if (-not $OllamaExe -and (Test-Path -LiteralPath $PortableOllama)) {
    $existingPortable = Get-ChildItem -LiteralPath $PortableOllama -Filter 'ollama.exe' -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($existingPortable) { $OllamaExe = $existingPortable.FullName }
}
if (-not $OllamaExe -and $InstallDependencies) {
    Write-Step 'Downloading portable Ollama for free local translation and summarization'
    $OllamaZip = Join-Path $RuntimeRoot 'ollama-windows-amd64.zip'
    & curl.exe -L --fail --retry 3 -C - -o $OllamaZip 'https://github.com/ollama/ollama/releases/latest/download/ollama-windows-amd64.zip'
    if ($LASTEXITCODE -ne 0) { throw 'Portable Ollama download failed.' }
    New-Item -ItemType Directory -Path $PortableOllama -Force | Out-Null
    Expand-Archive -LiteralPath $OllamaZip -DestinationPath $PortableOllama -Force
    $portableCommand = Get-ChildItem -LiteralPath $PortableOllama -Filter 'ollama.exe' -File -Recurse | Select-Object -First 1
    if ($portableCommand) { $OllamaExe = $portableCommand.FullName }
}
if (-not $OllamaExe) {
    throw 'Ollama is required. Re-run without -InstallDependencies:$false or install Ollama first.'
}

# CTranslate2 discovers CUDA/cuDNN DLLs through PATH on Windows. The wheels are
# isolated inside this pipeline's venv and do not modify the system CUDA setup.
$SitePackages = (& $VenvPython -c "import site; print([p for p in site.getsitepackages() if p.lower().endswith('site-packages')][-1])").Trim()
$CudaDllPaths = @(
    (Join-Path $SitePackages 'nvidia\cublas\bin'),
    (Join-Path $SitePackages 'nvidia\cudnn\bin'),
    (Join-Path $SitePackages 'nvidia\cuda_nvrtc\bin'),
    (Join-Path (Split-Path -Parent $OllamaExe) 'lib\ollama\cuda_v12')
) | Where-Object { Test-Path -LiteralPath $_ }
if ($CudaDllPaths.Count -gt 0) {
    $env:PATH = (($CudaDllPaths -join [IO.Path]::PathSeparator) + [IO.Path]::PathSeparator + $env:PATH)
}

if (-not (Test-OllamaApi)) {
    Write-Step 'Starting the local Ollama service'
    Start-Process -FilePath $OllamaExe -ArgumentList 'serve' -WindowStyle Hidden
    $ready = $false
    foreach ($attempt in 1..30) {
        Start-Sleep -Seconds 1
        if (Test-OllamaApi) { $ready = $true; break }
    }
    if (-not $ready) { throw 'Ollama did not start within 30 seconds.' }
}

Write-Step "Downloading/checking local language model: $OllamaModel"
& $OllamaExe pull $OllamaModel
if ($LASTEXITCODE -ne 0) { throw "Could not prepare Ollama model: $OllamaModel" }

Write-Step "Processing $($Videos.Count) recording(s)"
$arguments = @(
    $PythonHelper,
    '--source', $SourcePath,
    '--app-root', $AppRoot,
    '--whisper-model', $WhisperModel,
    '--ollama-model', $OllamaModel,
    '--device', $Device
)
if ($Force) { $arguments += '--force' }
if ($HtmlOnlyFrom -gt 0) { $arguments += @('--html-only-from', $HtmlOnlyFrom) }
& $VenvPython @arguments
if ($LASTEXITCODE -ne 0) { throw 'One or more recordings could not be processed.' }

if (-not $SkipManifest) {
    Write-Step 'Rebuilding the lesson manifest'
    & py -3.11 (Join-Path $AppRoot 'scripts\convert_lessons.py')
    if ($LASTEXITCODE -ne 0) { throw 'Manifest rebuild failed.' }
}

if ($Publish) {
    Write-Step 'Publishing through the repository update script'
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot 'update-index-and-push.ps1')
    if ($LASTEXITCODE -ne 0) { throw 'Publishing failed. Local output is still available.' }
}

Write-Host "`nCompleted DOL Speaking Recordings." -ForegroundColor Green
Write-Host "Local artifacts: $SourcePath"
Write-Host "App data:       $(Join-Path $AppRoot 'data\chatgpt\recordings')"
Write-Host "App page:       $(Join-Path $AppRoot 'index.html')"
