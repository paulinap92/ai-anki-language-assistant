$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$appDir = Join-Path $repoRoot "dist\AI Anki Language Assistant"
$exe = Join-Path $appDir "AI Anki Language Assistant.exe"
$result = Join-Path $appDir "packaging_self_test.json"

if (-not (Test-Path $exe)) {
    throw "Packaged EXE not found: $exe"
}

if (Test-Path $result) {
    Remove-Item $result -Force
}

Write-Host "==> Running packaged Whisper + Piper functional self-test"
$process = Start-Process -FilePath $exe -ArgumentList "--packaging-self-test" -WorkingDirectory $appDir -PassThru -Wait

if (Test-Path $result) {
    Write-Host "---- packaging_self_test.json ----"
    Get-Content $result
    Write-Host "----------------------------------"
}

if ($process.ExitCode -ne 0) {
    throw "Packaged Whisper/Piper self-test failed with exit code $($process.ExitCode)"
}

if (-not (Test-Path $result)) {
    throw "Packaged self-test did not create its result file."
}

$report = Get-Content $result -Raw | ConvertFrom-Json
if (-not $report.ok) {
    throw "Packaged self-test report says ok=false"
}

Write-Host "Packaged Whisper and Piper functional self-test passed."
