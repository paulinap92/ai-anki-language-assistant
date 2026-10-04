$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$appDir = Join-Path $repoRoot "dist\AI Anki Language Assistant"
$exe = Join-Path $appDir "AI Anki Language Assistant.exe"

if (-not (Test-Path $exe)) {
    throw "Packaged EXE not found: $exe"
}

Write-Host "==> Starting packaged EXE for smoke test"
$process = Start-Process -FilePath $exe -WorkingDirectory $appDir -PassThru

Start-Sleep -Seconds 12

if ($process.HasExited) {
    $startupLog = Join-Path $appDir "logs\startup.log"
    if (Test-Path $startupLog) {
        Write-Host "---- startup.log ----"
        Get-Content $startupLog
        Write-Host "---------------------"
    }
    throw "Packaged application exited during the startup smoke-test window. Exit code: $($process.ExitCode)"
}

Write-Host "Packaged application stayed alive for 12 seconds: startup smoke test passed."
Stop-Process -Id $process.Id -Force
