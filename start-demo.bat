@echo off
REM One-click demo start (Windows). Run from the TripPilotAI folder.
cd /d "%~dp0"

echo Starting backend and frontend in their own windows...
start "TripPilot Backend" cmd /k "cd /d backend && .venv\Scripts\activate && uvicorn app.main:app --port 8000"
start "TripPilot Frontend" cmd /k "cd /d frontend && npm run dev"

echo Waiting 20 seconds for the servers to start...
timeout /t 20 /nobreak >nul

echo.
echo Pre-warming demo destinations (this makes the live demo fast). Takes 1-2 minutes.
backend\.venv\Scripts\python.exe backend\scripts\prewarm.py

echo.
echo Opening the app...
start http://localhost:3000
echo Done. Keep the two server windows open during the demo.
pause
