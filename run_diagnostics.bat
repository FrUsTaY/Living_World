@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

cd /d "%~dp0"

echo ===================================================
echo     Живой Мир - Диагностика социальной системы
echo ===================================================
echo.

:: Сброс переменных
set "NPC_COUNT=30"
set "SIM_DAYS=30"
set "SIM_SEED="
set "NO_LOG="

:: Интерактивный ввод
set /p "INPUT_NPC=Введите количество NPC (по умолчанию 30): "
if not "!INPUT_NPC!"=="" set "NPC_COUNT=!INPUT_NPC!"

set /p "INPUT_DAYS=Введите количество дней симуляции (по умолчанию 30): "
if not "!INPUT_DAYS!"=="" set "SIM_DAYS=!INPUT_DAYS!"

set /p "INPUT_SEED=Введите Seed для рандома (оставьте пустым для случайного): "
if not "!INPUT_SEED!"=="" set "SIM_SEED=--seed !INPUT_SEED!"

set /p "INPUT_LOG=Отключить подробные логи событий в консоли? (y/n, по умолчанию y): "
if /i not "!INPUT_LOG!"=="n" set "NO_LOG=--no-log"

echo.
echo Запуск симуляции с параметрами: NPC=!NPC_COUNT!, Дней=!SIM_DAYS! !SIM_SEED! !NO_LOG!
echo.

if not exist venv (
    echo [INFO] Создание виртуального окружения...
    py -m venv venv
)

echo [INFO] Активация виртуального окружения...
call venv\Scripts\activate

echo [INFO] Проверка зависимостей...
pip install -r requirements.txt -q

echo [INFO] Запуск...
echo.

python social_simulation.py --npc !NPC_COUNT! --days !SIM_DAYS! !SIM_SEED! !NO_LOG!

echo.
pause
