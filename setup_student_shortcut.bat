@echo off
REM ============================================================
REM  ECAA CBT Platform - Student Launcher Setup
REM
REM  Run this ONCE on each student PC (or once, then copy the
REM  resulting shortcut to each PC's Desktop over the network).
REM
REM  It asks for the server's address, then creates a working
REM  desktop shortcut that opens straight to the login page.
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
echo IMPORTANT: ask your IT support to set a DHCP RESERVATION (a
echo fixed IP) for the server machine. Otherwise its IP can change
echo after a reboot, which would silently break this shortcut on
echo every student PC it's been copied to.
echo.

set /p SERVER_IP="Enter the server's IP address or hostname: "

if "%SERVER_IP%"=="" (
    echo.
    echo No address entered -- nothing was created. Run this again.
    pause
    exit /b 1
)

set SHORTCUT_PATH=%USERPROFILE%\Desktop\ECAA CBT Platform.url

(
    echo [InternetShortcut]
    echo URL=http://%SERVER_IP%:8080/
    echo IconIndex=0
) > "%SHORTCUT_PATH%"

echo.
echo ============================================================
echo  Done. A shortcut named "ECAA CBT Platform" was placed on
echo  this PC's Desktop, pointing to:
echo    http://%SERVER_IP%:8080/
echo.
echo  Copy that same .url file to other student PCs' Desktops to
echo  give them the same one-click access -- you don't need to
echo  run this script again on each machine unless the server's
echo  address changes.
echo ============================================================
echo.
pause