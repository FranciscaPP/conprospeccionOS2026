@echo off
setlocal
cd /d "%~dp0"
echo Iniciando Conprospeccion OS2026 en Streamlit...
start "" python -m streamlit run dashboard/app.py --server.port 8502
timeout /t 4 /nobreak > nul
start "" http://localhost:8502
endlocal

