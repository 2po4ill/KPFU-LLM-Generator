@echo off
REM KPFU LLM Generator Setup Script for Windows
REM Sets up the complete hybrid infrastructure

echo 🚀 Setting up KPFU LLM Generator...

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not installed. Please install Docker Desktop first.
    pause
    exit /b 1
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose is not installed. Please install Docker Compose first.
    pause
    exit /b 1
)

REM Create necessary directories
echo 📁 Creating directories...
if not exist "app\models" mkdir app\models
if not exist "app\cache" mkdir app\cache
if not exist "data\postgres" mkdir data\postgres
if not exist "data\redis" mkdir data\redis
if not exist "data\chromadb" mkdir data\chromadb
if not exist "data\ollama" mkdir data\ollama

REM Start infrastructure services first
echo 🐳 Starting infrastructure services...
docker-compose up -d postgres redis chromadb

REM Wait for services to be ready
echo ⏳ Waiting for services to be ready...
timeout /t 10 /nobreak >nul

REM Check PostgreSQL
echo 🔍 Checking PostgreSQL connection...
:wait_postgres
docker-compose exec -T postgres pg_isready -U kpfu_user -d kpfu_generator >nul 2>&1
if errorlevel 1 (
    echo Waiting for PostgreSQL...
    timeout /t 2 /nobreak >nul
    goto wait_postgres
)
echo ✅ PostgreSQL is ready

REM Check Redis
echo 🔍 Checking Redis connection...
:wait_redis
docker-compose exec -T redis redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo Waiting for Redis...
    timeout /t 2 /nobreak >nul
    goto wait_redis
)
echo ✅ Redis is ready

REM Start Ollama and pull model
echo 🤖 Starting Ollama and pulling Llama 3.1 8B model...
docker-compose up -d ollama

REM Wait for Ollama to be ready
timeout /t 15 /nobreak >nul

REM Pull the required model
echo 📥 Pulling Llama 3.1 8B model (this may take a while)...
docker-compose exec ollama ollama pull llama3.1:8b

echo ✅ Llama 3.1 8B model ready

REM Build and start the main application
echo 🏗️ Building and starting the main application...
docker-compose up -d app

REM Wait for application to be ready
echo ⏳ Waiting for application to start...
timeout /t 20 /nobreak >nul

REM Check application health
echo 🔍 Checking application health...
curl -f http://localhost:8080/health >nul 2>&1
if errorlevel 1 (
    echo ⚠️ Application may still be starting up...
) else (
    echo ✅ Application is healthy
)

echo.
echo 🎉 KPFU LLM Generator setup complete!
echo.
echo 📊 System Status:
echo   - Application: http://localhost:8080
echo   - Health Check: http://localhost:8080/health
echo   - API Status: http://localhost:8080/api/v1/status
echo   - PostgreSQL: localhost:5432
echo   - Redis: localhost:6379
echo   - ChromaDB: localhost:8000
echo   - Ollama: localhost:11434
echo.
echo 🔧 To view logs: docker-compose logs -f
echo 🛑 To stop: docker-compose down
echo 🔄 To restart: docker-compose restart
echo.
echo 📚 Next steps:
echo   1. Check system status: curl http://localhost:8080/api/v1/status
echo   2. Load models manually: curl -X POST http://localhost:8080/api/v1/models/load
echo   3. Start implementing RPD processing (Task 2)

pause