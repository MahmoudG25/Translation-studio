@echo off
setlocal enabledelayedexpansion
title Translation Studio - Installation Pipeline
echo ===================================================
echo   Translation Studio Installation ^| استوديو الترجمة
echo ===================================================
echo.

:: Step 1: Check Python
echo [1/5] Checking for Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10 or higher from python.org
    pause
    exit /b 1
)
echo ✓ Python found.

:: Step 2: Check Requirements File
if not exist requirements.txt (
    echo [ERROR] requirements.txt not found in current directory.
    echo Please make sure you are running this from the project root.
    pause
    exit /b 1
)

:: Step 3: Virtual Environment
echo [2/5] Setting up virtual environment (venv)...
if not exist venv (
    python -m venv venv
    if !ERRORLEVEL! NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo ✓ Virtual environment created.
) else (
    echo ✓ Virtual environment already exists.
)

:: Step 4: Activate and Upgrade Pip
echo [3/5] Activating venv and upgrading pip...
call venv\Scripts\activate
python -m pip install --upgrade pip
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Failed to upgrade pip. Continuing...
) else (
    echo ✓ Pip upgraded.
)

:: Step 5: Install Requirements
echo [4/5] Installing dependencies (this may take a while)...
echo This will install PySide6, faster-whisper, argostranslate, and openai.
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Installation failed. Please check your internet connection and try again.
    pause
    exit /b 1
)
echo ✓ Dependencies installed successfully.

:: Step 6: Diagnostics (FFmpeg)
echo [5/5] Running diagnostics...
ffmpeg -version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] FFmpeg was not found on your system.
    echo FFmpeg is REQUIRED for video/audio processing.
    echo Please install it via: choco install ffmpeg (Windows)
    echo or download from https://ffmpeg.org/download.html
) else (
    echo ✓ FFmpeg found and ready.
)

echo.
echo ===================================================
echo   Installation Complete! ^| اكتمل التثبيت بنجاح
echo ===================================================
echo You can now run the application using: start.bat
echo.
pause
