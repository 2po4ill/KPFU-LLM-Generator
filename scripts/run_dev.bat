@echo off
echo 🚀 Starting KPFU LLM Generator in Development Mode...
echo.

REM Set environment variables for mock services
set USE_MOCK_SERVICES=true
set DATABASE_URL=sqlite:///./test.db
set REDIS_URL=redis://localhost:6379
set CHROMADB_URL=http://localhost:8000
set OLLAMA_URL=http://localhost:11434

REM Check if virtual environment exists
if not exist "venv" (
    echo ❌ Virtual environment not found. Run setup_local.bat first.
    pause
    exit /b 1
)

REM Activate virtual environment
call ..\venv\Scripts\activate.bat

REM Start the application
echo 🌟 Starting application with mock services...
echo 📊 Application will be available at: http://localhost:8080
echo 🔍 Health check: http://localhost:8080/health
echo 📈 Status API: http://localhost:8080/api/v1/status
echo.
echo Press Ctrl+C to stop the application
echo.

REM Check Python command
py --version >nul 2>&1
if errorlevel 1 (
    set PYTHON_CMD=python
) else (
    set PYTHON_CMD=py
)

cd ..\app
%PYTHON_CMD% main.py