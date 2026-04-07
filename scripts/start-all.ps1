param(
    [string]$FrontendEnvPath = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendScript = Join-Path $scriptDir "start-backend.ps1"
$frontendScript = Join-Path $scriptDir "start-frontend.ps1"

if (-not (Test-Path $backendScript)) {
    Write-Host "Missing backend script: $backendScript" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $frontendScript)) {
    Write-Host "Missing frontend script: $frontendScript" -ForegroundColor Red
    exit 1
}

Write-Host "Launching backend and frontend in separate PowerShell windows..." -ForegroundColor Cyan

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", $backendScript
)

Start-Sleep -Seconds 1

if ($FrontendEnvPath) {
    $frontendArgs = @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-File", $frontendScript,
        "-FrontendEnvPath", $FrontendEnvPath
    )
} else {
    $frontendArgs = @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-File", $frontendScript
    )
}

Start-Process powershell -ArgumentList $frontendArgs

Write-Host "Backend and frontend launch commands were sent." -ForegroundColor Green
