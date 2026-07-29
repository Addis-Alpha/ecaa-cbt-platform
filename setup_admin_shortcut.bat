@echo off
REM ============================================================
REM  ECAA CBT Platform - Admin Shortcut Setup
REM
REM  Run this on the admin's PC to get a one-click browser shortcut
REM  to the platform's login page, using the "ECAA CBT Admin" icon.
REM
REM  This script and "ECAA_CBT_Admin.ico" must sit in the SAME
REM  folder when you run this.
REM
REM  Note: this points to the SAME login page students use --
REM  there's no separate admin URL. Signing in with an admin
REM  account is what puts you on the Administrator Dashboard.
REM ============================================================

setlocal

echo ============================================================
echo  ECAA CBT Platform - Admin Shortcut Setup
echo ============================================================
echo.
echo You need the SERVER machine's LAN IP address (or hostname).
echo If this IS the server machine: open Command Prompt and run
echo "ipconfig", then look for "IPv4 Address" under the active
echo network adapter (e.g. 192.168.1.50). You can also just use
echo "localhost" if you'll always access it from the server itself.
echo.

set /p SERVER_IP="Enter the server's IP address or hostname: "

if "%SERVER_IP%"=="" (
    echo.
    echo No address entered -- nothing was created. Run this again.
    pause
    exit /b 1
)

if not exist "%~dp0ECAA_CBT_Admin.ico" (
    echo.
    echo ============================================================
    echo  ECAA_CBT_Admin.ico was not found in this folder.
    echo  Make sure it's copied alongside this .bat file, then
    echo  run this script again.
    echo ============================================================
    pause
    exit /b 1
)

set ICON_DIR=%USERPROFILE%\ECAA_CBT_Icons
if not exist "%ICON_DIR%" mkdir "%ICON_DIR%"
copy /Y "%~dp0ECAA_CBT_Admin.ico" "%ICON_DIR%\ECAA_CBT_Admin.ico" >nul

set SHORTCUT_PATH=%USERPROFILE%\Desktop\ECAA CBT Platform - Admin.url

(
    echo [InternetShortcut]
    echo URL=http://%SERVER_IP%:8080/
    echo IconFile=%ICON_DIR%\ECAA_CBT_Admin.ico
    echo IconIndex=0
) > "%SHORTCUT_PATH%"

echo.
echo ============================================================
echo  Done. A shortcut named "ECAA CBT Platform - Admin" was
echo  placed on this PC's Desktop, pointing to:
echo    http://%SERVER_IP%:8080/
echo  using the ECAA CBT Admin icon.
echo ============================================================
echo.
pause