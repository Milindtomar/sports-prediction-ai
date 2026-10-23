# One-time setup for Windows (PowerShell):  .\setup.ps1
# Creates backend\.venv, installs Python + Node dependencies, trains the models if artifacts are missing.
# NOTE: written for Windows 10/11 + Python 3.11+ + Node 20+. It was NOT run on Windows by the author (only the
# equivalent steps were run on Linux); report any problem so it can be fixed.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Need($cmd, $hint) {
  if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { Write-Host "Missing '$cmd'. $hint" -ForegroundColor Red; exit 1 }
}
Need "python" "Install Python 3.11+ from https://www.python.org/downloads/ and tick 'Add python.exe to PATH'."
Need "node"   "Install Node.js 20+ from https://nodejs.org/."
Need "npm"    "Install Node.js 20+ (npm is included)."

$pyver = python -c "import sys; print('%d.%d' % sys.version_info[:2])"
if ([version]$pyver -lt [version]"3.11") { Write-Host "Python $pyver found; 3.11 or newer is required." -ForegroundColor Red; exit 1 }

Write-Host "[1/4] Python environment" -ForegroundColor Cyan
if (-not (Test-Path "backend\.venv")) { python -m venv backend\.venv }
& backend\.venv\Scripts\python.exe -m pip install --upgrade pip | Out-Null
& backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

Write-Host "[2/4] Frontend dependencies" -ForegroundColor Cyan
Push-Location frontend
npm install
Pop-Location

Write-Host "[3/4] Models" -ForegroundColor Cyan
if (-not (Test-Path "backend\artifacts\metrics.json")) {
  Push-Location backend
  & .venv\Scripts\python.exe -m app.ml.train_all
  Pop-Location
} else { Write-Host "Artifacts already present (delete backend\artifacts to retrain)." }

if (-not (Test-Path "backend\.env") -and (Test-Path "backend\.env.example")) { Copy-Item backend\.env.example backend\.env }

Write-Host "[4/4] Done. Start the app with:  .\start.ps1   (or double-click start.bat)" -ForegroundColor Green
