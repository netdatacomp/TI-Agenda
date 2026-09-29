@echo off
cd /d "%~dp0"
cd backend
python -m pip install -r requirements.txt
if errorlevel 1 pause & exit /b 1
cd ..\frontend
call npm install
if errorlevel 1 pause & exit /b 1
cd ..
echo Instalacao concluida. Execute INICIAR.bat.
pause
