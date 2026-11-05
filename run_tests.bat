@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ========================================================
echo               Living World - Запуск тестов
echo ========================================================
echo.

set "VENV_DIR=.venv"
if not exist ".venv\Scripts\activate.bat" if exist "venv\Scripts\activate.bat" set "VENV_DIR=venv"

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    set "PYTHON="
    py -3 --version >nul 2>&1 && set "PYTHON=py -3"
    if "%PYTHON%"=="" python --version >nul 2>&1 && set "PYTHON=python"
    if "%PYTHON%"=="" (
        echo [ОШИБКА] Python не найден.
        pause
        exit /b 1
    )
    echo [*] Создание виртуального окружения %VENV_DIR%...
    %PYTHON% -m venv %VENV_DIR%
)

call "%VENV_DIR%\Scripts\activate.bat"
python -m pip install -r requirements.txt >nul 2>&1

echo [*] Запуск набора тестов pytest...
echo.
pytest
echo.
pause
