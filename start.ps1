# Start SPORTS AI (backend :8000 and frontend :5173) in two windows and open the browser.   .\start.ps1
# NOTE: not run on Windows by the author; see README "Windows" section for the equivalent manual commands.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path "backend\.venv\Scripts\python.exe") -or -not (Test-Path "frontend\node_modules") -or -not (Test-Path "backend\artifacts\metrics.json")) {
  Write-Host "First run detected - running setup.ps1 ..." -ForegroundColor Yellow
  & "$PSScriptRoot\setup.ps1"
}

$root = $PSScriptRoot
Start-Process powershell -ArgumentList "-NoExit","-Command","Set-Location '$root\backend'; & .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000"
Start-Process powershell -ArgumentList "-NoExit","-Command","Set-Location '$root\frontend'; npm run dev -- --port 5173"

Write-Host "Waiting for the API ..." -ForegroundColor Cyan
$ok = $false
for ($i = 0; $i -lt 40; $i++) {
  try { $h = Invoke-RestMethod http://127.0.0.1:8000/api/health -TimeoutSec 2; if ($h.status -eq "ok") { $ok = $true; break } } catch { }
  Start-Sleep -Seconds 1
}
if (-not $ok) { Write-Host "The API did not become healthy within 40 s. Check the backend window for errors (try http://127.0.0.1:8000/api/health)." -ForegroundColor Red }
Start-Process "http://localhost:5173"
Write-Host "Frontend http://localhost:5173   API http://127.0.0.1:8000   Docs http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "Close the two server windows to stop."
