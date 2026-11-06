@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ========================================================
echo               Living World - Запуск тестов
echo ========================================================
echo.

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else (
    py -3 -m venv .venv 2>nul || python -m venv .venv
    call ".venv\Scripts\activate.bat"
    python -m pip install -r requirements.txt
)

echo [*] Запуск набора тестов pytest...
echo.
pytest
echo.
pause
