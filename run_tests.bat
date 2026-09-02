@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo               Living World - Test Runner
echo ========================================================
echo.

set "PYTHON="
py -3 --version >nul 2>&1
if not errorlevel 1 set "PYTHON=py -3"
if "%PYTHON%"=="" python --version >nul 2>&1 && set "PYTHON=python"

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

echo [*] Running tests...
echo.
"venv\Scripts\python.exe" test_social_progression_and_dating.py
"venv\Scripts\python.exe" run_all_tests.py
echo.
pause
