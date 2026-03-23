@echo off
REM Run Telegram Bot for KPFU Course Generator

echo ========================================
echo KPFU Course Generator - Telegram Bot
echo ========================================
echo.

REM Check if .env exists
if not exist .env (
    echo ERROR: .env file not found!
    echo Please create .env file with TELEGRAM_BOT_TOKEN
    echo.
    echo Example:
    echo TELEGRAM_BOT_TOKEN=your_bot_token_here
    pause
    exit /b 1
)

REM Check if Ollama is running
echo Checking Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo WARNING: Ollama is not running!
    echo Please start Ollama first: ollama serve
    echo.
    pause
)

REM Add current directory to PYTHONPATH
set PYTHONPATH=%CD%

echo Starting Telegram Bot...
echo Current directory: %CD%
echo PYTHONPATH: %PYTHONPATH%
echo.
python -m app.bot.telegram_bot

pause
