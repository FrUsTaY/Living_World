@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo         Living World - 120 Days Diagnostics Run
echo ========================================================
echo.

set "PYTHON="
py -3 --version >nul 2>&1
if not errorlevel 1 set "PYTHON=py -3"
if "%PYTHON%"=="" python --version >nul 2>&1 && set "PYTHON=python"

if not exist "venv\Scripts\python.exe" (
    if "%PYTHON%"=="" (
        echo [ERROR] Python not found in PATH!
        pause
        exit /b 1
    )
    echo [*] Creating virtual environment...
    %PYTHON% -m venv venv
    "venv\Scripts\python.exe" -m pip install -r requirements.txt
)

echo [*] Launching 120-day headless diagnostic run...
echo.
"venv\Scripts\python.exe" run_120_days_diagnostics.py --npc 25 --days 120 --seed 42

echo.
echo ========================================================
echo Diagnostics complete. Press any key to exit...
pause > nul
