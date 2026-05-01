@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo  SecureProxy Builder - Создание автономного .exe файла
echo ============================================================
echo.

REM Проверка наличия Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ОШИБКА] Python не найден!
    echo Пожалуйста, установите Python 3.8+ с сайта https://www.python.org/
    echo ВАЖНО: При установке отметьте галочку "Add Python to PATH"
    pause
    exit /b 1
)

echo [OK] Python найден.
echo.

REM Установка необходимых инструментов для сборки
echo [ШАГ 1/3] Установка инструментов сборки...
pip install --upgrade pip
pip install pyinstaller packaging requests urllib3 chardet idna certifi
if %errorlevel% neq 0 (
    echo [ОШИБКА] Не удалось установить зависимости. Проверьте подключение к интернету.
    pause
    exit /b 1
)
echo [OK] Инструменты установлены.
echo.

REM Очистка предыдущих сборок
echo [ШАГ 2/3] Очистка временных файлов...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "SecureProxy.spec" del /q "SecureProxy.spec"
echo [OK] Очистка завершена.
echo.

REM Сборка приложения
echo [ШАГ 3/3] Компиляция SecureProxy.exe...
echo Это может занять несколько минут...
echo.

pyinstaller --onefile ^
            --windowed ^
            --name "SecureProxy" ^
            --clean ^
            --hidden-import=requests ^
            --hidden-import=urllib3 ^
            --hidden-import=socks ^
            --hidden-import=packaging ^
            main.py

if %errorlevel% neq 0 (
    echo.
    echo [ОШИБКА] Сборка не удалась. Проверьте логи выше.
    pause
    exit /b 1
)

REM Проверка результата
if exist "dist\SecureProxy.exe" (
    echo.
    echo ============================================================
    echo  УСПЕШНО! Файл создан:
    echo  %CD%\dist\SecureProxy.exe
    echo ============================================================
    echo.
    echo Этот файл полностью автономен.
    echo Пользователю НЕ НУЖНО устанавливать Python.
    echo При первом запуске программа сама скачает Tor и X-Ray.
    echo.
    echo Откройте папку 'dist', чтобы забрать готовый файл.
    echo.
    
    REM Создание инструкции для пользователя
    (
        echo ИНСТРУКЦИЯ ПОЛЬЗОВАТЕЛЯ
        echo =======================
        echo.
        echo 1. Запустите SecureProxy.exe.
        echo 2. При первом запуске программа предложит скачать необходимые компоненты (Tor и X-Ray).
        echo 3. Нажмите "Скачать автоматически" и дождитесь завершения.
        echo    - Если загрузка не удается из-за блокировок, программа покажет инструкцию по ручной установке.
        echo 4. После установки компонентов вы можете:
        echo    - Подключиться через сеть Tor
        echo    - Добавить конфигурацию X-Ray (VMess/VLESS/Trojan и др.)
        echo    - Включить локальный SOCKS5 прокси
        echo.
        echo Папки с данными будут созданы автоматически в той же директории.
        echo.
        echo Техническая поддержка: проверьте актуальность версий на официальных сайтах проектов.
    ) > "dist\HOW_TO_USE.txt"
    
    echo Файл инструкции 'HOW_TO_USE.txt' также создан в папке 'dist'.
    pause
    start "dist" explorer "%CD%\dist"
) else (
    echo.
    echo [ОШИБКА] Файл SecureProxy.exe не был создан в папке dist.
    echo Проверьте логи сборки выше.
    pause
    exit /b 1
)

endlocal
