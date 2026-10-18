# ===================================================
#             🎬 SHORTS STUDIO LAUNCHER (PowerShell)
# ===================================================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "            🎬 SHORTS STUDIO LAUNCHER" -ForegroundColor Yellow
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

$PythonExe = Join-Path $ScriptDir "venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Python virtual environment not found at $PythonExe" -ForegroundColor Red
    Write-Host "Please create it using: python -m venv venv" -ForegroundColor Gray
    Exit 1
}

Write-Host "[*] Checking local portable FFmpeg..." -ForegroundColor Green
$FFmpegExe = Join-Path $ScriptDir "bin\ffmpeg.exe"
if (Test-Path $FFmpegExe) {
    Write-Host "    Found FFmpeg in bin/ ($FFmpegExe)" -ForegroundColor Gray
} else {
    Write-Host "    [Notice] bin\ffmpeg.exe not found. Studio will attempt system PATH detection." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[*] Starting Shorts Studio server on http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "[*] Press Ctrl+C in this terminal window to stop." -ForegroundColor DarkGray
Write-Host ""

# Optional: Auto-launch default web browser
Start-Process "http://127.0.0.1:8000"

& $PythonExe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
