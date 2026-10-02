@echo off
cd /d "%~dp0"
start "TI Agenda API" cmd /k "cd /d ""%~dp0backend"" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
timeout /t 3 /nobreak >nul
start "TI Agenda Vue" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"
timeout /t 3 /nobreak >nul
start http://127.0.0.1:5173
