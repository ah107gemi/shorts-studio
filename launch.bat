@echo off
title Shorts Studio Launcher
echo ===================================================
echo             🎬 SHORTS STUDIO LAUNCHER
echo ===================================================
echo.

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at .\venv.
    echo Please run: python -m venv venv
    pause
    exit /b 1
)

echo [*] Starting Shorts Studio local production server...
echo [*] Open your browser at: http://127.0.0.1:8000
echo [*] Press Ctrl+C to stop the studio.
echo.

"venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
