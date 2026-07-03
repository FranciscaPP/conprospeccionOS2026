@echo off
title Conprospeccion OS — MVP Setup
echo.
echo  ================================
echo   Conprospeccion OS - Iniciando
echo  ================================
echo.
echo  Abre en tu navegador: http://localhost:8501
echo  Para cerrar: Ctrl+C o cierra esta ventana
echo.

cd /d "%~dp0"
streamlit run app.py --server.port 8501
pause
