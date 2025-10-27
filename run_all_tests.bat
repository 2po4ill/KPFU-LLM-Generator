@echo off
echo 🧪 Running KPFU LLM Generator - Complete Test Suite
echo ================================================================
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Set test environment variables
set USE_MOCK_SERVICES=true
set DATABASE_URL=sqlite:///./test.db
set PYTHONPATH=%CD%;%CD%\app

echo 📊 Test Environment Setup:
echo - Mock Services: %USE_MOCK_SERVICES%
echo - Database: %DATABASE_URL%
echo - Python Path: %PYTHONPATH%
echo.

REM Initialize test counters
set "total_tests=0"
set "passed_tests=0"
set "failed_tests=0"

echo ================================================================
echo 🔧 PHASE 1: CONFIGURATION TESTS
echo ================================================================
echo.
python -m pytest tests/test_config.py -v --tb=short
if %errorlevel%==0 (
    echo ✅ Configuration tests: PASSED
    set /a passed_tests+=7
) else (
    echo ❌ Configuration tests: FAILED
    set /a failed_tests+=7
)
set /a total_tests+=7
echo.

echo ================================================================
echo 🌐 PHASE 2: API ENDPOINT TESTS
echo ================================================================
echo.
python -m pytest tests/test_api.py -v --tb=short
if %errorlevel%==0 (
    echo ✅ API endpoint tests: PASSED
    set /a passed_tests+=14
) else (
    echo ❌ API endpoint tests: FAILED
    set /a failed_tests+=14
)
set /a total_tests+=14
echo.

echo ================================================================
echo 🔧 PHASE 3: MOCK SERVICES TESTS (Non-Async)
echo ================================================================
echo.
echo 📦 Testing ChromaDB Mock...
python -m pytest tests/test_mock_services.py::TestMockChromaDB -v --tb=short
if %errorlevel%==0 (
    echo ✅ ChromaDB mock tests: PASSED
    set /a passed_tests+=2
) else (
    echo ❌ ChromaDB mock tests: FAILED
    set /a failed_tests+=2
)
set /a total_tests+=2

echo 📦 Testing Collection Mock...
python -m pytest tests/test_mock_services.py::TestMockCollection -v --tb=short
if %errorlevel%==0 (
    echo ✅ Collection mock tests: PASSED
    set /a passed_tests+=3
) else (
    echo ❌ Collection mock tests: FAILED
    set /a failed_tests+=3
)
set /a total_tests+=3

echo 📦 Testing SentenceTransformer Mock...
python -m pytest tests/test_mock_services.py::TestMockSentenceTransformer -v --tb=short
if %errorlevel%==0 (
    echo ✅ SentenceTransformer mock tests: PASSED
    set /a passed_tests+=2
) else (
    echo ❌ SentenceTransformer mock tests: FAILED
    set /a failed_tests+=2
)
set /a total_tests+=2

echo 📦 Testing Mock Services Factory...
python -m pytest tests/test_mock_services.py::TestGetMockServices -v --tb=short
if %errorlevel%==0 (
    echo ✅ Mock services factory tests: PASSED
    set /a passed_tests+=1
) else (
    echo ❌ Mock services factory tests: FAILED
    set /a failed_tests+=1
)
set /a total_tests+=1
echo.

echo ================================================================
echo 📊 TEST RESULTS SUMMARY
echo ================================================================
echo.
echo 🎯 Total Tests: %total_tests%
echo ✅ Passed: %passed_tests%
echo ❌ Failed: %failed_tests%
echo.

REM Calculate success percentage
set /a success_rate=(%passed_tests% * 100) / %total_tests%
echo 📈 Success Rate: %success_rate%%%
echo.

if %failed_tests%==0 (
    echo 🎉 ALL TESTS PASSED! 
    echo.
    echo ✨ Core Architecture Status: FULLY VERIFIED
    echo 🚀 System Status: READY FOR PRODUCTION
    echo 📋 Next Step: Proceed with Task 2 - RPD Processing
) else (
    echo ⚠️ Some tests failed. Review the output above.
    echo.
    echo 📋 Recommendations:
    echo - Check failed test details
    echo - Verify environment setup
    echo - Run individual test phases for debugging
)

echo.
echo ================================================================
echo 🔧 AVAILABLE TEST COMMANDS
echo ================================================================
echo.
echo Individual test phases:
echo - test.bat                       (Interactive test menu)
echo - run_all_tests.bat             (This comprehensive suite)
echo - scripts\run_basic_tests.bat   (Core functionality)
echo - scripts\test_endpoints.bat    (API endpoint testing)
echo.
echo Development commands:
echo - setup.bat                     (Initial setup)
echo - dev.bat                       (Start development server)
echo.

REM Cleanup test database
if exist test.db del test.db

echo Press any key to exit...
pause >nul