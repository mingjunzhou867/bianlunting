$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$configPath = Join-Path $repoRoot "config\.env"
$backendActivate = Join-Path $repoRoot ".venv\Scripts\Activate.ps1"
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$requirementsPath = Join-Path $repoRoot "requirements.txt"

if (-not (Test-Path $backendActivate) -or -not (Test-Path $venvPython)) {
    Write-Host "Backend virtual environment was not found at $backendActivate" -ForegroundColor Yellow
    Write-Host "Create the backend environment before starting the service." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $configPath)) {
    Write-Host "Missing config file: $configPath" -ForegroundColor Yellow
    Write-Host "Create it from config\.env.example before starting the backend." -ForegroundColor Yellow
    exit 1
}

Write-Host "Starting backend from $repoRoot" -ForegroundColor Cyan
Set-Location $repoRoot
. $backendActivate

Write-Host "Installing backend dependencies..." -ForegroundColor Yellow
& $venvPython -m pip install -r $requirementsPath

& $venvPython ".\api\main.py"
