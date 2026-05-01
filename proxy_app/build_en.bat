@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ==========================================
echo   SecureProxy Build Script
echo ==========================================
echo.

REM Check Python
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.8+ from python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [OK] Python found
echo.

REM Install dependencies
echo Installing build tools...
pip install --upgrade pip
pip install pyinstaller packaging requests charset-normalizer

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies. Try running as Administrator.
    pause
    exit /b 1
)

echo [OK] Dependencies installed
echo.

REM Clean old builds
echo Cleaning old builds...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "*.spec" del /q "*.spec"

echo [OK] Cleaned
echo.

REM Build EXE
echo Building SecureProxy.exe...
echo This may take a few minutes...
pyinstaller --onefile --windowed --name "SecureProxy" --icon=NONE --add-data "core;core" --add-data "gui;gui" main.py

if errorlevel 1 (
    echo [ERROR] Build failed! Check the messages above.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   BUILD SUCCESSFUL!
echo ==========================================
echo.
echo Your file is ready: dist\SecureProxy.exe
echo.
echo Opening folder...
start dist

REM Create usage instruction
(
echo ==========================================
echo   HOW TO USE SecureProxy
echo ==========================================
echo.
echo 1. Run SecureProxy.exe
echo 2. The app will automatically download Tor and X-Ray on first start.
echo 3. If download fails due to blocking, follow the instructions in the app.
echo 4. Add your proxy configuration or select Tor.
echo 5. Click "Connect".
echo.
echo That's it! No Python or other tools needed for end users.
) > "dist\HOW_TO_USE.txt"

echo Usage instruction created in dist folder.
echo.
pause
