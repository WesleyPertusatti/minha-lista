@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo =========================================
echo   GERANDO A SUA LISTA DE CANAIS
echo =========================================
echo.
python "codigo\gerar_lista.py" %*
echo.
pause
