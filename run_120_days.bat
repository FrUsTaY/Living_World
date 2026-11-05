@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ========================================================
echo         Living World - 120 Days Diagnostics Run
echo ========================================================
echo.

set "VENV_DIR=.venv"
if not exist ".venv\Scripts\activate.bat" if exist "venv\Scripts\activate.bat" set "VENV_DIR=venv"

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    set "PYTHON="
    py -3 --version >nul 2>&1 && set "PYTHON=py -3"
    if "%PYTHON%"=="" python --version >nul 2>&1 && set "PYTHON=python"
    if "%PYTHON%"=="" (
        echo [ERROR] Python not found in PATH!
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

echo [*] Launching 120-day headless diagnostic run...
echo.
python run_120_days_diagnostics.py --npc 25 --days 120 --seed 42

echo.
echo ========================================================
echo Diagnostics complete. Press any key to exit...
pause > nul
