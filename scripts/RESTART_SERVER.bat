@echo off
echo ===================================================
echo   Force Restarting CattleAI Dashboard Server...
echo ===================================================
echo.

echo [1] Finding Python processes running on Port 5000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5000') do (
    echo [2] Killing process ID: %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo [3] Server stopped successfully!
echo [4] Starting the new GovTech Dashboard...
echo.

start "" cmd /c "timeout /t 2 >nul && start http://127.0.0.1:5000"
python expert-dashboard\app.py

pause
