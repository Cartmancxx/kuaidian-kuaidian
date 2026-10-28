@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Uninstall-Host.ps1"
if errorlevel 1 (
  echo.
  echo Uninstall did not complete. See the message above.
  pause
  exit /b 1
)
echo.
pause
