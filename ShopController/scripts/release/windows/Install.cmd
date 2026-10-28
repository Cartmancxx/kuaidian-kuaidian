@echo off
cd /d "%~dp0"
"%~dp0host\ShopController.Host.exe" --install-user %*
echo.
pause
