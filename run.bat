@echo off
setlocal enabledelayedexpansion

title Ledger Educational Platform

:: Change directory to script location
cd /d "%~dp0"

echo ============================================================
echo   Ledger Educational Platform -- Startup
echo ============================================================

:: 1. Detect Python
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "PY_CMD=python"
) else (
    where py >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set "PY_CMD=py -3"
    ) else (
        echo [ERROR] Python was not found in your system PATH.
        echo Please install Python 3.10+ from https://python.org and ensure
        echo "Add Python to PATH" is checked during installation.
        echo.
        pause
        exit /b 1
    )
)

:: 2. Set up Virtual Environment
set "VENV_DIR=%~dp0.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "VENV_PIP=%VENV_DIR%\Scripts\pip.exe"
set "STAMP_FILE=%VENV_DIR%\.installed"

if not exist "%VENV_PY%" (
    echo [1/3] Creating Python virtual environment in .venv...
    %PY_CMD% -m venv "%VENV_DIR%"
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
)

:: 3. Install Dependencies
if not exist "%STAMP_FILE%" (
    echo [2/3] Installing dependencies from requirements.txt...
    "%VENV_PY%" -m pip install --upgrade pip
    "%VENV_PIP%" install -r "%~dp0requirements.txt"
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install required packages.
        pause
        exit /b 1
    )
    echo. > "%STAMP_FILE%"
    echo Dependencies installed successfully.
) else (
    echo [2/3] Dependencies verified.
)

:: 4. Initialize Database and Idempotent Seed Data
echo [3/3] Initializing databases and verifying seed data...
"%VENV_PY%" "%~dp0data.py"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Database initialization failed.
    pause
    exit /b 1
)

"%VENV_PY%" "%~dp0seed_data.py"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Sample data seeding failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Ledger is ready!
echo   Open your browser to: http://127.0.0.1:5000
echo.
echo   Demo Accounts:
echo     Admin:     admin@ledger.local     / admin123
echo     Professor: professor@ledger.local / prof123
echo     Student:   student@ledger.local   / student123
echo.
echo   Press Ctrl+C to stop the server at any time.
echo ============================================================
echo.

:: 5. Launch Application
"%VENV_PY%" "%~dp0app.py"

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] The application stopped unexpectedly with code %ERRORLEVEL%.
    pause
)
