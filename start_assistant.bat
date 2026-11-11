@echo off
title Local AI Voice Assistant (Ollama + Qwen2.5)
cd /d "%~dp0"

echo ========================================================
echo       Starting Local Voice Assistant
echo ========================================================
echo.

:: Configure Ollama to keep both LLM and Embedder in GPU VRAM (no model swapping)
set OLLAMA_MAX_LOADED_MODELS=2
set OLLAMA_KEEP_ALIVE=-1
set OLLAMA_NUM_PARALLEL=1

:: Check if Ollama is running
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Starting local Ollama service...
    start "" ollama serve
    timeout /t 3 /nobreak >nul
) else (
    echo [+] Ollama service is running.
)

:: Activate virtual environment
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo [X] Error: .venv virtual environment not found.
    pause
    exit /b 1
)

:: Launch web interface in default browser
start http://127.0.0.1:5000

:: Start the Flask app
echo [+] Starting Assistant Server on http://127.0.0.1:5000...
python app.py

pause
