@echo off

echo ==========================================
echo      ENCERRANDO FLUENTEMENTE
echo ==========================================
echo.

taskkill /FI "WINDOWTITLE eq Fluentemente Backend*" /T /F >nul 2>&1

taskkill /FI "WINDOWTITLE eq Fluentemente Frontend*" /T /F >nul 2>&1

echo.
echo Servidores encerrados.
echo.

pause