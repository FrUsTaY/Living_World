@echo off
setlocal

echo [Living World] Checking virtual environment...

:: Check if venv folder exists
if not exist "venv\Scripts\activate.bat" (
    echo [Living World] Virtual environment not found. Creating venv...
    python -m venv venv
    if errorlevel 1 (
        echo [Error] Failed to create virtual environment. Check if Python is installed.
        pause
        exit /b 1
    )
)

:: Activate virtual environment
echo [Living World] Activating virtual environment...
call venv\Scripts\activate.bat

:: Install or check dependencies
echo [Living World] Checking dependencies...
python -m pip install --upgrade pip > nul
pip install -r requirements.txt

:: Launch the application
echo [Living World] Launching simulation...
python main.py

echo.
echo [Living World] Application exited.
pause
