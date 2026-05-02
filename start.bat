@echo off
chcp 65001 >nul 2>&1
echo ============================================================
echo   Fortune Fusion Engine v2.0 - Startup
echo ============================================================
echo.

REM Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found in PATH
    echo Please install Python 3.12+ and add to PATH
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check dependencies
python -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
)

echo [INFO] Starting Fortune Fusion Engine v2.0...
echo [INFO] API: http://localhost:8000
echo [INFO] Docs: http://localhost:8000/docs
echo [INFO] Metrics: http://localhost:8000/metrics
echo.
echo Press Ctrl+C to stop
echo.

set PYTHONIOENCODING=utf-8
python -m uvicorn src.api.main:app --port 8000 --host 0.0.0.0
