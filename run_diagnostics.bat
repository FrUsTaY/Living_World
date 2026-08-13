@echo off
cd /d %~dp0

if not exist venv (
    echo Creating virtual environment...
    py -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate

echo Installing dependencies...
pip install -r requirements.txt

echo Running diagnostic tool...
python social_simulation.py %*

pause
