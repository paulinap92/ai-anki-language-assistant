$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "==> Python"
python --version

Write-Host "==> Installing application dependencies"
python -m pip install --upgrade pip
python -m pip install -r requirements-hybrid.txt
python -m pip install -r requirements-build.txt

Write-Host "==> Dependency preflight"
python -c "import customtkinter, faster_whisper, ctranslate2, sounddevice, soundfile, piper; print('Core packaged dependencies import OK')"

Write-Host "==> Building one-folder Windows release"
python -m PyInstaller --noconfirm --clean packaging/ai_anki.spec

$appDir = Join-Path $repoRoot "dist\AI Anki Language Assistant"
if (-not (Test-Path $appDir)) {
    throw "PyInstaller output folder was not created: $appDir"
}

Write-Host "==> Adding first-run readme and writable voice folder"
Copy-Item "packaging\README_FIRST.txt" (Join-Path $appDir "README_FIRST.txt") -Force
New-Item -ItemType Directory -Force -Path (Join-Path $appDir "voices\piper") | Out-Null

$zipPath = Join-Path $repoRoot "dist\AI-Anki-Language-Assistant-Windows.zip"
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

Write-Host "==> Creating ZIP"
Compress-Archive -Path $appDir -DestinationPath $zipPath -CompressionLevel Optimal

Write-Host "Build ready:"
Write-Host $zipPath
