@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ========================================================
echo               Living World - Запуск симуляции
echo ========================================================
echo.

:: 1. Поиск системного Python для создания .venv
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

:found_python
if "%PYTHON%"=="" (
    if not exist ".venv\Scripts\python.exe" (
        echo [ОШИБКА] Python не найден в системе!
        echo Пожалуйста, установите Python 3.10+ с сайта https://www.python.org/
        echo Обязательно отметьте галочку: "Add python.exe to PATH" при установке.
        echo.
        pause
        exit /b 1
    )
)

:: 2. Создание виртуального окружения .venv (если ещё не создано)
if not exist ".venv\Scripts\activate.bat" (
    echo [*] Виртуальное окружение не найдено. Создание .venv ...
    %PYTHON% -m venv .venv
    if not exist ".venv\Scripts\activate.bat" (
        echo [ОШИБКА] Не удалось создать виртуальное окружение .venv.
        echo.
        pause
        exit /b 1
    )
    echo [+] Виртуальное окружение .venv успешно создано.
    echo.
)

:: 3. Активация .venv
echo [*] Активация виртуального окружения .venv ...
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ОШИБКА] Не удалось активировать .venv.
    pause
    exit /b 1
)

:: 4. Установка / обновление зависимостей в .venv
echo [*] Проверка и установка зависимостей из requirements.txt в .venv ...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ПРЕДУПРЕЖДЕНИЕ] Возникли замечания при установке некоторых пакетов.
) else (
    echo [+] Зависимости актуальны и готовы к работе.
)
echo.

:: 5. Запуск приложения Living World
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
    echo Приложение завершилось с кодом ошибки: %EXIT_CODE%
)
echo ========================================================
echo.
pause
