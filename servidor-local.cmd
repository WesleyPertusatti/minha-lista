@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Servidor Local - Minha Lista

echo.
echo ============================================================
echo    SERVIDOR LOCAL DA SUA LISTA
echo ============================================================
echo.
echo   Deixe ESTA JANELA ABERTA enquanto assiste na TV.
echo   Nao precisa de internet: so o PC ligado e na mesma
echo   rede (Wi-Fi/roteador) da TV.
echo.
echo   Cole UM destes enderecos no app de IPTV da TV:
echo.

set "CZERO=0"
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
  for /f "tokens=* delims= " %%b in ("%%a") do (
    echo         http://%%b:8000/minha-lista.m3u
  )
)

echo.
echo   Para PARAR o servidor: aperte Ctrl+C nesta janela.
echo ============================================================
echo.

python -m http.server 8000
pause
