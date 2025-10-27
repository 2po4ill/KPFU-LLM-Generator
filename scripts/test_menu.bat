@echo off
cls
echo ================================================================
echo 🧪 KPFU LLM Generator - Test Suite Menu
echo ================================================================
echo.
echo Choose a test option:
echo.
echo 1. Run All Tests (Comprehensive)
echo 2. Run Basic Tests (Core functionality only)
echo 3. Run Async Tests (Advanced async functionality)
echo 4. Run API Tests (Endpoint testing)
echo 5. Run Configuration Tests
echo 6. Test API Endpoints (Live server)
echo 7. Setup Development Environment
echo 8. Start Development Server
echo 9. Exit
echo.
set /p choice="Enter your choice (1-9): "

if "%choice%"=="1" goto run_all
if "%choice%"=="2" goto run_basic
if "%choice%"=="3" goto run_async
if "%choice%"=="4" goto run_api
if "%choice%"=="5" goto run_config
if "%choice%"=="6" goto test_endpoints
if "%choice%"=="7" goto setup
if "%choice%"=="8" goto run_dev
if "%choice%"=="9" goto exit

echo Invalid choice. Please try again.
pause
goto menu

:run_all
echo.
echo 🚀 Running comprehensive test suite...
call scripts\run_all_tests.bat
goto menu

:run_basic
echo.
echo 🎯 Running basic functionality tests...
call scripts\run_basic_tests.bat
goto menu

:run_async
echo.
echo ⚡ Running async functionality tests...
call scripts\run_async_tests.bat
goto menu

:run_api
echo.
echo 🌐 Running API tests...
call venv\Scripts\activate.bat
set USE_MOCK_SERVICES=true
set PYTHONPATH=%CD%;%CD%\app
python -m pytest tests/test_api.py -v
pause
goto menu

:run_config
echo.
echo ⚙️ Running configuration tests...
call venv\Scripts\activate.bat
set USE_MOCK_SERVICES=true
set PYTHONPATH=%CD%;%CD%\app
python -m pytest tests/test_config.py -v
pause
goto menu

:test_endpoints
echo.
echo 🔍 Testing live API endpoints...
echo Make sure the development server is running first!
call scripts\test_endpoints.bat
goto menu

:setup
echo.
echo 🛠️ Setting up development environment...
call scripts\setup_local.bat
goto menu

:run_dev
echo.
echo 🚀 Starting development server...
call scripts\run_dev.bat
goto menu

:exit
echo.
echo 👋 Goodbye!
exit /b 0

:menu
echo.
echo ================================================================
echo.
echo Choose a test option:
echo.
echo 1. Run All Tests (Comprehensive)
echo 2. Run Basic Tests (Core functionality only)
echo 3. Run Async Tests (Advanced async functionality)
echo 4. Run API Tests (Endpoint testing)
echo 5. Run Configuration Tests
echo 6. Test API Endpoints (Live server)
echo 7. Setup Development Environment
echo 8. Start Development Server
echo 9. Exit
echo.
set /p choice="Enter your choice (1-9): "

if "%choice%"=="1" goto run_all
if "%choice%"=="2" goto run_basic
if "%choice%"=="3" goto run_async
if "%choice%"=="4" goto run_api
if "%choice%"=="5" goto run_config
if "%choice%"=="6" goto test_endpoints
if "%choice%"=="7" goto setup
if "%choice%"=="8" goto run_dev
if "%choice%"=="9" goto exit

echo Invalid choice. Please try again.
pause
goto menu