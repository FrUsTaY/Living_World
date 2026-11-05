@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ========================================================
echo            Living World - Diagnostics Runner
echo ========================================================
echo.

set "VENV_DIR=.venv"
if not exist ".venv\Scripts\activate.bat" if exist "venv\Scripts\activate.bat" set "VENV_DIR=venv"

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    set "PYTHON="
    py -3 --version >nul 2>&1 && set "PYTHON=py -3"
    if "%PYTHON%"=="" python --version >nul 2>&1 && set "PYTHON=python"
    if "%PYTHON%"=="" (
        echo [ERROR] Python not found.
        pause
        exit /b 1
    )
    echo [*] Creating virtual environment %VENV_DIR%...
    %PYTHON% -m venv %VENV_DIR%
    call "%VENV_DIR%\Scripts\activate.bat"
    python -m pip install -r requirements.txt
) else (
    call "%VENV_DIR%\Scripts\activate.bat"
)

echo Select diagnostic mode:
echo [1] Quick Diagnostic (30 days, 15 NPCs)
echo [2] Seasonal Diagnostic (90 days, 15 NPCs)
echo [3] Long Run Simulation (180 days, 25 NPCs)
echo [4] Interactive Social Flow Monitor
echo.
set "choice=1"
set /p choice="Enter choice (1-4, default 1): "

if "%choice%"=="2" (
    python diag_suite.py --npc 15 --days 90 --seed 42
) else if "%choice%"=="3" (
    python run_180_days_diagnostics.py --npc 25 --days 180 --seed 42
) else if "%choice%"=="4" (
    python diag_social_flow.py
) else (
    python diag_suite.py --npc 15 --days 30 --seed 42
)

echo.
echo ========================================================
echo Diagnostics complete. Press any key to exit...
pause > nul
