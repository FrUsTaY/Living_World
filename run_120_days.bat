@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ========================================================
echo        Living World - Диагностический прогон (120 дней)
echo ========================================================
echo.

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else (
    echo [*] Активация окружения...
    py -3 -m venv .venv 2>nul || python -m venv .venv
    call ".venv\Scripts\activate.bat"
    python -m pip install -r requirements.txt
)

echo [*] Запуск фоновой диагностики на 120 дней...
echo.
python run_120_days_diagnostics.py --npc 25 --days 120 --seed 42

echo.
echo ========================================================
echo Диагностика завершена.
pause
