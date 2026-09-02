@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo            Living World - Diagnostics Runner
echo ========================================================
echo.

set "PYTHON="

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=py -3"
    goto :found_python
)
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=python"
    goto :found_python
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"

:found_python
if not exist "venv\Scripts\python.exe" (
    if "%PYTHON%"=="" (
        echo [ERROR] Python not found.
        pause
        exit /b 1
    )
    echo [*] Creating virtual environment...
    %PYTHON% -m venv venv
    "venv\Scripts\python.exe" -m pip install -r requirements.txt
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
    "venv\Scripts\python.exe" diag_suite.py --npc 15 --days 90 --seed 42
) else if "%choice%"=="3" (
    "venv\Scripts\python.exe" diag_suite.py --npc 25 --days 180 --seed 42
) else if "%choice%"=="4" (
    "venv\Scripts\python.exe" social_simulation.py --npc 25 --days 30
) else (
    "venv\Scripts\python.exe" diag_suite.py --npc 15 --days 30 --seed 42
)

echo.
pause
