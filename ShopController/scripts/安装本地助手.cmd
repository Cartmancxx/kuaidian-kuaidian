@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-Host.ps1"
if errorlevel 1 (
  echo.
  echo Installation did not complete. See the message above.
  pause
  exit /b 1
)
echo.
pause
