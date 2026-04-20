@echo off
REM Argos Build Script (Windows)
REM Usage: scripts\build.bat

echo ======================================
echo   Argos Build Script
echo ======================================

REM Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: python not found. Please install Python 3.11+.
    exit /b 1
)

python --version

REM Move to project root
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
cd /d %PROJECT_ROOT%
echo Project root: %PROJECT_ROOT%

REM Install dependencies
echo.
echo Installing dependencies...
python -m pip install -r requirements.txt pyinstaller --quiet

REM Generate assets if missing
if not exist "assets\icon.png" (
    echo Generating placeholder assets...
    python scripts\generate_assets.py
)

REM Run PyInstaller
echo.
echo Building with PyInstaller...
python -m PyInstaller argos.spec --noconfirm --clean

REM Check output
echo.
if exist "dist\Argos.exe" (
    echo ======================================
    echo   BUILD SUCCESS
    echo ======================================
    echo Output: dist\
    dir dist\
) else (
    echo ======================================
    echo   BUILD FAILED
    echo ======================================
    exit /b 1
)
