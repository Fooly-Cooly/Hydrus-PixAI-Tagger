@echo off
title Hydrus PixAI Tagger Launcher

:: If venv doesn't exist, trigger first-time setup
if not exist "venv\Scripts\python.exe" (
    echo [INFO] Virtual environment not found. Starting setup installer...
    echo.
    call setup.bat
    if not exist "venv\Scripts\python.exe" (
        echo.
        echo [ERROR] Setup was cancelled or failed. Cannot start application.
        pause
        exit /b 1
    )
    echo.
)

:: Launch the tagger without keeping the terminal window open
echo Starting Hydrus PixAI Tagger...
if exist "venv\Scripts\pythonw.exe" (
    start "" "venv\Scripts\pythonw.exe" hydrus_pixai_tagger.pyw %*
    exit /b 0
) else (
    python hydrus_pixai_tagger.py %*
    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] Script exited with error code %errorlevel%.
        pause
    )
)
