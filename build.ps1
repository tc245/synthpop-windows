# build.ps1 — build the Windows .exe with PyInstaller
# Run from the project root:  .\build.ps1
#
# Output: dist\SynthPop Desktop\SynthPop Desktop.exe
# Distribute the entire dist\SynthPop Desktop\ folder.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Activate venv if not already active
if (-not $env:VIRTUAL_ENV) {
    if (Test-Path ".\.venv\Scripts\Activate.ps1") {
        Write-Host "Activating virtual environment..." -ForegroundColor Cyan
        & .\.venv\Scripts\Activate.ps1
    } else {
        Write-Error "No .venv found. Run .\setup.ps1 first."
        exit 1
    }
}

Write-Host "Cleaning previous build artefacts..." -ForegroundColor Cyan
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist")  { Remove-Item -Recurse -Force "dist" }

Write-Host "Running PyInstaller..." -ForegroundColor Cyan
pyinstaller packaging\synthpop_desktop.spec

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller failed (exit code $LASTEXITCODE)."
    exit 1
}

$out = Resolve-Path "dist\SynthPop Desktop"
Write-Host ""
Write-Host "Build complete!" -ForegroundColor Green
Write-Host "Output: $out" -ForegroundColor Green
Write-Host "Distribute the entire folder (not just the .exe)." -ForegroundColor Yellow
