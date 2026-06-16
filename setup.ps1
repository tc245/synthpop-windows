# setup.ps1 — create venv, install deps, launch the app
# Run from the project root:  .\setup.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Creating virtual environment..." -ForegroundColor Cyan
python -m venv .venv

Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& .\.venv\Scripts\Activate.ps1

Write-Host "Installing dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt

Write-Host ""
Write-Host "Setup complete. Launching SynthPop Desktop..." -ForegroundColor Green
python main.py
