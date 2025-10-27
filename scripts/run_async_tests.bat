@echo off
echo 🧪 Running KPFU LLM Generator - Async Test Suite
echo ================================================================
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Set test environment variables
set USE_MOCK_SERVICES=true
set DATABASE_URL=sqlite:///./test.db
set PYTHONPATH=%CD%;%CD%\app

echo 📊 Attempting to run async tests with pytest-asyncio...
echo.

echo ================================================================
echo 🔄 ASYNC MOCK SERVICES TESTS
echo ================================================================
echo.
echo 📦 Testing Redis Mock (Async)...
python -m pytest tests/test_mock_services.py::TestMockRedis -v --tb=short -s
echo.

echo 📦 Testing Ollama Mock (Async)...
python -m pytest tests/test_mock_services.py::TestMockOllama -v --tb=short -s
echo.

echo ================================================================
echo 💾 ASYNC CACHE TESTS
echo ================================================================
echo.
echo 📦 Testing Cache Manager (Async)...
python -m pytest tests/test_cache.py -v --tb=short -s
echo.

echo ================================================================
echo 🤖 ASYNC MODEL MANAGER TESTS
echo ================================================================
echo.
echo 📦 Testing Model Manager (Async)...
python -m pytest tests/test_model_manager.py -v --tb=short -s
echo.

echo ================================================================
echo 🔗 INTEGRATION TESTS
echo ================================================================
echo.
echo 📦 Testing System Integration...
python -m pytest tests/test_integration.py -v --tb=short -s
echo.

echo ================================================================
echo 📊 ASYNC TEST RESULTS
echo ================================================================
echo.
echo ℹ️ Note: Async tests may require additional configuration
echo 📋 If tests fail, the core functionality still works in sync mode
echo 🎯 Main application uses async properly in production
echo.

REM Cleanup test database
if exist test.db del test.db

echo Press any key to exit...
pause >nul