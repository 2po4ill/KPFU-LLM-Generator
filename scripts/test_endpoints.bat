@echo off
echo 🌐 Testing KPFU LLM Generator API Endpoints...
echo.

echo 📊 Health Check:
curl -s http://localhost:8080/health
echo.
echo.

echo 📈 System Status:
curl -s http://localhost:8080/api/v1/status
echo.
echo.

echo 🔍 Detailed Health:
curl -s http://localhost:8080/api/v1/health/detailed
echo.
echo.

echo ✅ All endpoints tested!
pause