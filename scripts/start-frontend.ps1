param(
    [string]$FrontendEnvPath = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$frontendDir = Join-Path $repoRoot "frontend"
$packageLock = Join-Path $frontendDir "package-lock.json"
$nodeModules = Join-Path $frontendDir "node_modules"
$viteCmd = Join-Path $nodeModules ".bin\vite.cmd"
$frontendActivateCandidates = @()

if ($FrontendEnvPath) {
    $frontendActivateCandidates += $FrontendEnvPath
}

$frontendActivateCandidates += @(
    (Join-Path $frontendDir ".venv\Scripts\Activate.ps1"),
    (Join-Path $frontendDir "venv\Scripts\Activate.ps1"),
    (Join-Path $repoRoot ".frontend-venv\Scripts\Activate.ps1")
)

$frontendActivate = $frontendActivateCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

$npm = Get-Command "npm.cmd" -ErrorAction SilentlyContinue
if (-not $npm) {
    Write-Host "npm.cmd was not found. Install Node.js and ensure npm is in PATH." -ForegroundColor Yellow
    exit 1
}

if (-not $frontendActivate) {
    Write-Host "Frontend virtual environment activation script was not found." -ForegroundColor Yellow
    Write-Host "Pass -FrontendEnvPath or place an activation script at one of these locations:" -ForegroundColor Yellow
    foreach ($candidate in $frontendActivateCandidates | Select-Object -Unique) {
        Write-Host "  $candidate" -ForegroundColor Yellow
    }
    exit 1
}

Write-Host "Starting frontend from $frontendDir" -ForegroundColor Cyan
Set-Location $frontendDir
. $frontendActivate

if (-not (Test-Path $viteCmd)) {
    Write-Host "Frontend dependencies are missing. Running npm install..." -ForegroundColor Yellow
    if (Test-Path $packageLock) {
        & "npm.cmd" "install"
    } else {
        & "npm.cmd" "install"
    }
}

& "npm.cmd" "run" "dev"
