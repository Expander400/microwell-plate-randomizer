@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 plate_randomizer_gui.py %*
    goto finished
)
where python >nul 2>nul
if not errorlevel 1 (
    python plate_randomizer_gui.py %*
    goto finished
)
echo Python was not found. Install Python 3.10 or newer from https://www.python.org/downloads/
echo Then reopen this launcher. See README.md for help.
pause
exit /b 1
:finished
if errorlevel 1 (
    echo.
    echo The app could not start. See the message above and README.md.
    pause
    exit /b 1
)
