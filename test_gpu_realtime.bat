@echo off
echo Starting GPU monitoring and generation test...
echo.
echo GPU Status BEFORE generation:
nvidia-smi --query-gpu=utilization.gpu,utilization.memory,memory.used --format=csv,noheader
echo.
echo Starting generation (this will take ~15 seconds)...
start /B python test_gpu_speed.py > gpu_test_output.txt 2>&1
timeout /t 5 /nobreak > nul
echo.
echo GPU Status DURING generation:
nvidia-smi --query-gpu=utilization.gpu,utilization.memory,memory.used --format=csv,noheader
timeout /t 15 /nobreak > nul
echo.
echo GPU Status AFTER generation:
nvidia-smi --query-gpu=utilization.gpu,utilization.memory,memory.used --format=csv,noheader
echo.
echo Generation output:
type gpu_test_output.txt
