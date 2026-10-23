@echo off
REM Double-click launcher for Windows. If PowerShell scripts are blocked, this bypasses the policy for this one run only.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
if errorlevel 1 pause
