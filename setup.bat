@echo off
setlocal enabledelayedexpansion
title Hydrus PixAI Tagger - Interactive Setup

echo ========================================================
echo        Hydrus PixAI Tagger - Setup Installer
echo ========================================================
echo.

:: 1. Check Python installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your system PATH.
    echo Please install 64-bit Python 3.10+ and check "Add Python to PATH".
    pause
    exit /b
)

:: Display Python version and architecture
for /f "delims=" %%i in ('python -c "import struct, sys; print(f'Python {sys.version.split()[0]} ({struct.calcsize(\"P\") * 8}-bit)')"') do set PYTHON_VER=%%i
echo Found: %PYTHON_VER%
echo.

:: 2. Create Virtual Environment if it doesn't exist
if not exist "venv" (
    echo [1/3] Creating virtual environment (venv)...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b
    )
) else (
    echo [1/3] Existing venv folder detected. Using existing virtual environment.
)

:: Upgrade pip
echo Upgrading pip inside venv...
venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>&1

echo.
echo ========================================================
echo               Choose PyTorch Hardware Engine
echo ========================================================
echo.
echo  [1] GPU (NVIDIA CUDA 12.x) - Recommended for most users with NVIDIA GPUs.
echo  [2] GPU (NVIDIA CUDA 13.x) - Recommended for Python 3.13/3.14 or RTX 50-series.
echo  [3] CPU Only                  - Slow, but works on any PC without NVIDIA GPU.
echo.
echo  Requirements for GPU acceleration:
echo   - 64-bit Python
echo   - NVIDIA GPU (RTX / GTX 10-series or newer)
echo   - Up-to-date NVIDIA Graphics Driver
echo ========================================================
echo.

set /p ENGINE_CHOICE="Select an option (1, 2, or 3) and press Enter: "

echo.
echo [2/3] Installing PyTorch framework...

if "%ENGINE_CHOICE%"=="1" (
    echo Installing PyTorch with CUDA 12.x support...
    venv\Scripts\python.exe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
) else if "%ENGINE_CHOICE%"=="2" (
    echo Installing PyTorch with CUDA 13.x support...
    venv\Scripts\python.exe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130
) else (
    echo Installing CPU-only PyTorch...
    venv\Scripts\python.exe -m pip install torch torchvision torchaudio
)

if %errorlevel% neq 0 (
    echo.
    echo [WARNING] Primary PyTorch install failed. Attempting standard index fallback...
    venv\Scripts\python.exe -m pip install torch torchvision torchaudio
)

echo.
echo [3/3] Installing GUI and API dependencies (PyQt6, Transformers, Pillow, Hydrus API)...
venv\Scripts\python.exe -m pip install PyQt6 transformers pillow hydrus-api accelerate

echo.
echo ========================================================
echo               Verifying GPU Acceleration
echo ========================================================
venv\Scripts\python.exe -c "import torch; print('CUDA Available:', torch.cuda.is_available()); print('Device Name:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU Only')"

echo.
echo ========================================================
echo Setup complete! Double-click 'run.bat' to start the tagger.
echo ========================================================
pause