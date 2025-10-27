@echo off
echo 🚀 Setting up KPFU LLM Generator (Local Development Mode)...
echo.

REM Check if Python is available
py --version >nul 2>&1
if errorlevel 1 (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo ❌ Python is not installed. Please install Python 3.11+ first.
        echo 📥 Download from: https://www.python.org/downloads/
        pause
        exit /b 1
    )
    set PYTHON_CMD=python
) else (
    set PYTHON_CMD=py
)

echo ✅ Python found

REM Create virtual environment
echo 📦 Creating virtual environment...
if not exist "..\venv" (
    %PYTHON_CMD% -m venv ..\venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call ..\venv\Scripts\activate.bat

REM Install dependencies
echo 📥 Installing Python dependencies (development mode)...
%PYTHON_CMD% -m pip install --upgrade pip
%PYTHON_CMD% -m pip install -r ..\requirements-dev.txt

REM Create local directories
echo 📁 Creating local directories...
if not exist "..\data" mkdir ..\data
if not exist "..\data\postgres" mkdir ..\data\postgres
if not exist "..\data\redis" mkdir ..\data\redis
if not exist "..\data\chromadb" mkdir ..\data\chromadb
if not exist "..\app\models" mkdir ..\app\models
if not exist "..\app\cache" mkdir ..\app\cache

REM Create local environment file
echo 🔧 Creating local environment configuration...
if not exist "..\.env" (
    copy ..\.env.example ..\.env
)

echo.
echo 🎉 Local development setup complete!
echo.
echo 📋 Next steps for local development:
echo   1. Install and start PostgreSQL locally (port 5432)
echo   2. Install and start Redis locally (port 6379)  
echo   3. Install Ollama: https://ollama.ai/download
echo   4. Pull model: ollama pull llama3.1:8b
echo   5. Run app: cd app && python main.py
echo.
echo 🐳 Or use Docker Desktop:
echo   1. Install Docker Desktop
echo   2. Start Docker Desktop
echo   3. Run: docker-compose up -d
echo.
echo 💡 For quick testing without external dependencies:
echo   Run: python app\main.py (will use mock services)

pause