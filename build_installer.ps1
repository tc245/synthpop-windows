# build_installer.ps1
# Full pipeline: PyInstaller → Inno Setup → .exe installer
#
# Prerequisites:
#   - Python venv set up:  .\setup.ps1
#   - Inno Setup 6 installed: https://jrsoftware.org/isdl.php
#
# Run from the project root:  .\build_installer.ps1
# Output: dist\installer\SynthPop_Desktop_Setup_1.0.0.exe

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Step 1: activate venv ──────────────────────────────────────────────────────
if (-not $env:VIRTUAL_ENV) {
    if (Test-Path ".\.venv\Scripts\Activate.ps1") {
        Write-Host "Activating virtual environment..." -ForegroundColor Cyan
        & .\.venv\Scripts\Activate.ps1
    } else {
        Write-Error "No .venv found. Run .\setup.ps1 first."
        exit 1
    }
}

# ── Step 2: clean ─────────────────────────────────────────────────────────────
Write-Host "Cleaning previous build artefacts..." -ForegroundColor Cyan
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist")  { Remove-Item -Recurse -Force "dist" }

# ── Step 3: PyInstaller ───────────────────────────────────────────────────────
Write-Host ""
Write-Host "Step 1/2 — Building app with PyInstaller..." -ForegroundColor Cyan
pyinstaller packaging\synthpop_desktop.spec
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller failed."
    exit 1
}
Write-Host "PyInstaller done." -ForegroundColor Green

# ── Step 4: locate Inno Setup ────────────────────────────────────────────────
$iscc = $null
$candidates = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
    "C:\Program Files\Inno Setup 5\ISCC.exe"
)
foreach ($c in $candidates) {
    if (Test-Path $c) { $iscc = $c; break }
}

if (-not $iscc) {
    Write-Host ""
    Write-Host "Inno Setup not found. Install it from:" -ForegroundColor Yellow
    Write-Host "  https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Then compile the installer manually:" -ForegroundColor Yellow
    Write-Host '  & "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\installer.iss' -ForegroundColor Yellow
    Write-Host ""
    Write-Host "PyInstaller output is ready at: dist\SynthPop Desktop\" -ForegroundColor Green
    exit 0
}

# ── Step 5: Inno Setup ───────────────────────────────────────────────────────
Write-Host ""
Write-Host "Step 2/2 — Building installer with Inno Setup..." -ForegroundColor Cyan
& $iscc "packaging\installer.iss"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Inno Setup failed."
    exit 1
}

$out = Resolve-Path "dist\installer"
Write-Host ""
Write-Host "Done! Installer is at:" -ForegroundColor Green
Get-ChildItem -Path "$out" -Filter "*.exe" | ForEach-Object {
    Write-Host ('  ' + $_.FullName) -ForegroundColor Green
}
