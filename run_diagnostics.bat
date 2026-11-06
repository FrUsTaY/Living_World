@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ========================================================
echo            Living World - Меню диагностики
echo ========================================================
echo.

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else (
    py -3 -m venv .venv 2>nul || python -m venv .venv
    call ".venv\Scripts\activate.bat"
    python -m pip install -r requirements.txt
)

echo Выберите режим диагностики:
echo [1] Быстрая диагностика (30 дней, 15 жителей)
echo [2] Сезонная диагностика (90 дней, 15 жителей)
echo [3] Глубокая диагностика механик (120 дней, 25 жителей)
echo [4] Длительный стресс-тест (180 дней, 25 жителей)
echo [5] Тест дивергенции и ветвления мира (365 дней)
echo.
set "choice=1"
set /p choice="Введите номер (1-5, по умолчанию 1): "

if "%choice%"=="2" (
    python diag_suite.py --npc 15 --days 90 --seed 42
) else if "%choice%"=="3" (
    python run_120_days_diagnostics.py --npc 25 --days 120 --seed 42
) else if "%choice%"=="4" (
    python diag_suite.py --npc 25 --days 180 --seed 42
) else if "%choice%"=="5" (
    python run_divergence_test_365.py
) else (
    python diag_suite.py --npc 15 --days 30 --seed 42
)

echo.
echo ========================================================
echo Диагностика завершена.
pause
