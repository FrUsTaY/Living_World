@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ===================================================
echo     Living World - Social System Diagnostics
echo ===================================================
echo.

:: Reset variables
set "NPC_COUNT=30"
set "SIM_DAYS=30"
set "SIM_SEED="
set "NO_LOG="

:: Interactive input
set /p "INPUT_NPC=Enter the number of NPCs (default 30): "
if not "!INPUT_NPC!"=="" set "NPC_COUNT=!INPUT_NPC!"

set /p "INPUT_DAYS=Enter the number of simulation days (default 30): "
if not "!INPUT_DAYS!"=="" set "SIM_DAYS=!INPUT_DAYS!"

set /p "INPUT_SEED=Enter Seed for random (leave blank for random): "
if not "!INPUT_SEED!"=="" set "SIM_SEED=--seed !INPUT_SEED!"

set /p "INPUT_LOG=Disable detailed event logs in console? (y/n, default y): "
if /i not "!INPUT_LOG!"=="n" set "NO_LOG=--no-log"

echo.
echo Starting simulation with parameters: NPC=!NPC_COUNT!, Days=!SIM_DAYS! !SIM_SEED! !NO_LOG!
echo.

if not exist venv (
    echo [INFO] Creating virtual environment...
    py -m venv venv
)

echo [INFO] Activating virtual environment...
call venv\Scripts\activate

echo [INFO] Checking dependencies...
pip install -r requirements.txt -q

echo [INFO] Running...
echo.

python social_simulation.py --npc !NPC_COUNT! --days !SIM_DAYS! !SIM_SEED! !NO_LOG!

echo.
pause
