@echo off
setlocal

echo [Living World] Проверка виртуального окружения...

:: Проверяем, существует ли папка venv
if not exist "venv\Scripts\activate.bat" (
    echo [Living World] Виртуальное окружение не найдено. Создаем venv...
    python -m venv venv
    if errorlevel 1 (
        echo [Ошибка] Не удалось создать виртуальное окружение. Проверьте, установлен ли Python.
        pause
        exit /b 1
    )
)

:: Активируем виртуальное окружение
echo [Living World] Активация виртуального окружения...
call venv\Scripts\activate.bat

:: Устанавливаем или проверяем зависимости
echo [Living World] Проверка зависимостей...
python -m pip install --upgrade pip > nul
pip install -r requirements.txt

:: Запуск приложения
echo [Living World] Запуск симуляции...
python main.py

echo.
echo [Living World] Приложение завершило работу.
pause
