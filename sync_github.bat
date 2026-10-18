@echo off
setlocal
echo ====================================================
echo   Shorts Studio - GitHub Sync & Deployment Runner
echo ====================================================
cd /d "%~dp0"

REM Check if Python virtual environment exists
if exist "venv\Scripts\python.exe" (
    echo Using project virtual environment...
    venv\Scripts\python.exe deploy_github.py
) else (
    echo Using system Python...
    python deploy_github.py
)

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ====================================================
    echo   Sync complete! Successfully deployed to GitHub.
    echo ====================================================
) else (
    echo.
    echo ====================================================
    echo   Sync encountered an error (Code: %ERRORLEVEL%).
    echo ====================================================
)

echo.
pause
