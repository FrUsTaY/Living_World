@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo               Living World - Launcher
echo ========================================================
echo.

set "PYTHON="

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=py -3"
    goto :found_python
)

python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=python"
    goto :found_python
)

python3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=python3"
    goto :found_python
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :found_python
)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :found_python
)
if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    goto :found_python
)
if exist "C:\Python312\python.exe" (
    set "PYTHON=C:\Python312\python.exe"
    goto :found_python
)
if exist "C:\Python311\python.exe" (
    set "PYTHON=C:\Python311\python.exe"
    goto :found_python
)
if exist "C:\Python310\python.exe" (
    set "PYTHON=C:\Python310\python.exe"
    goto :found_python
)

echo [ERROR] Python was not found on this computer!
echo Please install Python 3.10+ from https://www.python.org/
echo Make sure to check the box: "Add python.exe to PATH" during installation.
echo.
pause
exit /b 1

:found_python
echo [*] Python detected: %PYTHON%
echo.

if not exist "venv\Scripts\python.exe" (
    echo [*] Virtual environment not found. Creating venv in %CD%\venv ...
    %PYTHON% -m venv venv
    if not exist "venv\Scripts\python.exe" (
        echo [ERROR] Failed to create virtual environment.
        echo.
        pause
        exit /b 1
    )
    echo [+] Virtual environment created.
    echo.
    echo [*] Installing dependencies from requirements.txt...
    "venv\Scripts\python.exe" -m pip install --upgrade pip
    "venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [WARNING] Notice: some dependencies had warnings during installation.
    ) else (
        echo [+] Dependencies installed successfully.
    )
    echo.
)

echo [*] Starting Living World GUI...
echo ========================================================
echo.

"venv\Scripts\python.exe" main.py
set "EXIT_CODE=%errorlevel%"

echo.
echo ========================================================
if %EXIT_CODE% equ 0 (
    echo Application finished normally.
) else (
    echo Application exited with code: %EXIT_CODE%
)
echo ========================================================
echo.
pause
