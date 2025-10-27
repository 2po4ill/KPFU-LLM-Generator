@echo off
echo 🧪 Running KPFU LLM Generator Test Suite...
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Set test environment variables
set USE_MOCK_SERVICES=true
set DATABASE_URL=sqlite:///./test.db
set PYTHONPATH=%CD%;%CD%\app

echo 📊 Running all tests...
pytest tests/ -v

echo.
echo 📈 Running tests with coverage...
pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

echo.
echo 🔍 Test results summary:
echo - HTML coverage report: htmlcov/index.html
echo - Test database: test.db (will be cleaned up)

REM Cleanup test database
if exist test.db del test.db

echo.
echo ✅ Test suite complete!
pause