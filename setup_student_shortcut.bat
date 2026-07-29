@echo off
REM ============================================================
REM  ECAA CBT Platform - Student Shortcut Setup
REM
REM  Run this ONCE on each student PC (or once, then copy the
REM  resulting shortcut AND the icon file to each PC's Desktop
REM  over the network -- both files travel together).
REM
REM  This script and "ECAA_CBT_Student.ico" must sit in the SAME
REM  folder when you run this.
REM ============================================================

setlocal

echo ============================================================
echo  ECAA CBT Platform - Student Shortcut Setup
echo ============================================================
echo.
echo You need the SERVER machine's LAN IP address (or hostname) to
echo continue. To find it: on the SERVER machine, open Command
echo Prompt and run "ipconfig", then look for "IPv4 Address" under
echo the active network adapter (e.g. 192.168.1.50).
echo.

set /p SERVER_IP="Enter the server's IP address or hostname: "

if "%SERVER_IP%"=="" (
    echo.
    echo No address entered -- nothing was created. Run this again.
    pause
    exit /b 1
)

if not exist "%~dp0ECAA_CBT_Student.ico" (
    echo.
    echo ============================================================
    echo  ECAA_CBT_Student.ico was not found in this folder.
    echo  Make sure it's copied alongside this .bat file, then
    echo  run this script again.
    echo ============================================================
    pause
    exit /b 1
)

REM Icon needs a permanent home on THIS pc -- a .url file only
REM stores a path to the icon, not the icon itself, so it can't
REM just point back at wherever this script happened to run from.
set ICON_DIR=%USERPROFILE%\ECAA_CBT_Icons
if not exist "%ICON_DIR%" mkdir "%ICON_DIR%"
copy /Y "%~dp0ECAA_CBT_Student.ico" "%ICON_DIR%\ECAA_CBT_Student.ico" >nul

set SHORTCUT_PATH=%USERPROFILE%\Desktop\ECAA CBT Platform.url

(
    echo [InternetShortcut]
    echo URL=http://%SERVER_IP%:8080/
    echo IconFile=%ICON_DIR%\ECAA_CBT_Student.ico
    echo IconIndex=0
) > "%SHORTCUT_PATH%"

echo.
echo ============================================================
echo  Done. A shortcut named "ECAA CBT Platform" was placed on
echo  this PC's Desktop, pointing to:
echo    http://%SERVER_IP%:8080/
echo  using the ECAA CBT icon.
echo.
echo  To copy this to other student PCs: copy BOTH the .url file
echo  from this Desktop AND the icon folder
echo  ("%ICON_DIR%") to the same two locations on the other PC.
echo ============================================================
echo.
pause