@echo off
title Fluentemente

cd /d "%~dp0"

echo ==========================================
echo           FLUENTEMENTE
echo ==========================================
echo.

echo Verificando Python...

where python >nul 2>&1

if errorlevel 1 (
    echo.
    echo Python nao foi encontrado.
    echo Instale Python em:
    echo https://www.python.org/downloads/windows/
    echo.
    pause
    exit
)

echo Python encontrado.
echo.

if not exist "backend\.venv\Scripts\python.exe" (
    echo Criando ambiente Python...
    python -m venv backend\.venv
)

echo.
echo Instalando dependencias...
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

echo.
echo Iniciando backend...

start "Fluentemente Backend" /min cmd /c "cd /d ""%~dp0backend"" && .venv\Scripts\python.exe -m uvicorn main:app --port 8000"

echo Backend iniciado.

echo.
echo Iniciando frontend...

start "Fluentemente Frontend" /min cmd /c "cd /d ""%~dp0frontend"" && ..\backend\.venv\Scripts\python.exe -m http.server 5500"

echo Frontend iniciado.

echo.
echo Aguardando servidores...
timeout /t 3 /nobreak >nul

echo Abrindo Fluentemente...

start "" "http://localhost:5500"

echo.
echo ==========================================
echo Fluentemente esta funcionando!
echo ==========================================
echo.
echo Site:
echo http://localhost:5500
echo.
echo Backend:
echo http://127.0.0.1:8000
echo.

pause