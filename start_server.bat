@echo off
REM ============================================================
REM  ECAA CBT Platform - Server Launcher (Conda version)
REM
REM  Double-click this file to start the exam server. Leave this
REM  window open while the server should be running -- closing it
REM  stops the server. Minimizing it is fine.
REM ============================================================

title ECAA CBT Platform - Server (do not close while exams are running)

REM ------------------------------------------------------------
REM EDIT THIS: the name of your conda environment for this project
REM (the one you normally run "conda activate <name>" into).
REM ------------------------------------------------------------
set CONDA_ENV_NAME=cbt

cd /d "%~dp0"

echo ============================================================
echo  Activating conda environment: %CONDA_ENV_NAME%
echo ============================================================

call conda activate %CONDA_ENV_NAME%

if errorlevel 1 (
    echo.
    echo ============================================================
    echo  Could not activate the conda environment "%CONDA_ENV_NAME%".
    echo.
    echo  Most likely cause: this Command Prompt doesn't have conda
    echo  set up yet. Try one of these:
    echo.
    echo   1^) Open "Anaconda Prompt" from the Start Menu instead of
    echo      double-clicking this file directly, then run:
    echo         cd /d "%~dp0"
    echo         start_server.bat
    echo.
    echo   2^) Or, one-time setup: open Anaconda Prompt and run
    echo         conda init cmd.exe
    echo      then close and reopen a normal Command Prompt and try
    echo      double-clicking this file again.
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Starting ECAA CBT Platform...
echo  Once you see "Serving on http://0.0.0.0:8080" below, the
echo  server is live and ready for students to connect.
echo ============================================================
echo.

REM Change "server.py" below if your Waitress launcher script has a
REM different filename.
python server.py

echo.
echo ============================================================
echo  The server has stopped. If this was unexpected, scroll up to
echo  read the error above.
echo ============================================================
pause