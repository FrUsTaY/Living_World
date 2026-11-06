@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ========================================================
echo               Living World - Запуск симуляции
echo ========================================================
echo.

REM 1. Проверяем готовое виртуальное окружение .venv
if exist ".venv\Scripts\python.exe" (
    goto :activate_venv
)

REM 2. Поиск системного Python для создания .venv
set "SYS_PYTHON="

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "SYS_PYTHON=py -3"
    goto :create_venv
)

python --version >nul 2>&1
if not errorlevel 1 (
    set "SYS_PYTHON=python"
    goto :create_venv
)

python3 --version >nul 2>&1
if not errorlevel 1 (
    set "SYS_PYTHON=python3"
    goto :create_venv
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "SYS_PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :create_venv
)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "SYS_PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :create_venv
)
if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set "SYS_PYTHON=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    goto :create_venv
)

if "%SYS_PYTHON%"=="" (
    echo [ОШИБКА] Python не найден в системе!
    echo Установите Python 3.10+ с сайта https://www.python.org/
    echo Обязательно отметьте: "Add python.exe to PATH" при установке.
    echo.
    pause
    exit /b 1
)

:create_venv
echo [*] Создание виртуального окружения .venv ...
%SYS_PYTHON% -m venv .venv
if not exist ".venv\Scripts\activate.bat" (
    echo [ОШИБКА] Не удалось создать .venv!
    pause
    exit /b 1
)
echo [+] Окружение .venv создано.
echo.

:activate_venv
echo [*] Активация виртуального окружения .venv ...
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ОШИБКА] Не удалось активировать .venv!
    pause
    exit /b 1
)

echo [*] Проверка зависимостей из requirements.txt ...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ПРЕДУПРЕЖДЕНИЕ] Возникли замечания при проверке пакетов.
) else (
    echo [+] Зависимости готовы.
)
echo.

echo [*] Запуск приложения Living World...
echo ========================================================
echo.

python main.py
set "EXIT_CODE=%errorlevel%"

echo.
echo ========================================================
if %EXIT_CODE% equ 0 (
    echo Приложение завершило работу штатно.
) else (
    echo Код завершения: %EXIT_CODE%
)
echo ========================================================
echo.
pause
