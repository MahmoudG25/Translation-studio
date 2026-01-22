@echo off
title Translation srt files with ShamsAI Pipeline
echo Starting Translation AI Pipeline...

:: Check for virtual environment
if exist venv\Scripts\activate (
    call venv\Scripts\activate
)

:: Run the application
python main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Application failed to start.
    echo Please ensure Python and dependencies are installed.
    pause
)
