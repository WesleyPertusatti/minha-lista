@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo =========================================
echo   GERANDO E PUBLICANDO A SUA LISTA
echo =========================================
echo.

python "codigo\gerar_lista.py"
if errorlevel 1 (
  echo.
  echo Deu erro ao gerar a lista. Publicacao cancelada.
  pause
  exit /b 1
)

echo.
echo Enviando para o GitHub...
git add -A
git commit -m "Atualiza lista de canais"
git push

echo.
echo Se nao houve erro acima, a lista ja esta atualizada na TV.
pause
