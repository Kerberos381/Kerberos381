@echo off
REM ============================================================
REM FakturaCZ — Build standalone Windows .exe
REM ============================================================
REM Prerequisites:
REM   1. Python 3.11+ installed and in PATH
REM   2. Run: pip install -r requirements.txt
REM ============================================================

echo.
echo ========================================
echo  FakturaCZ — Building Windows .exe
echo ========================================
echo.

REM Install dependencies
echo [1/3] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

REM Build with PyInstaller
echo.
echo [2/3] Building executable with PyInstaller...
pyinstaller ^
    --name "FakturaCZ" ^
    --onedir ^
    --windowed ^
    --noconfirm ^
    --clean ^
    --add-data "app;app" ^
    main.py

if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

REM Create data directory in output
echo.
echo [3/3] Creating data directory...
if not exist "dist\FakturaCZ\data" mkdir "dist\FakturaCZ\data"

echo.
echo ========================================
echo  BUILD COMPLETE
echo ========================================
echo.
echo  The application is in: dist\FakturaCZ\
echo  Run: dist\FakturaCZ\FakturaCZ.exe
echo.
echo  All invoice data will be stored in:
echo    dist\FakturaCZ\data\
echo.
pause
