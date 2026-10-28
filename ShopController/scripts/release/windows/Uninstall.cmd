@echo off
cd /d "%~dp0"
"%~dp0host\ShopController.Host.exe" --uninstall-user %*
echo.
pause
