@echo off
cd /d "C:\Users\Admin\OneDrive\Documents\Con Prospección\ConprospeccionOS"
echo Iniciando dashboard ConProspeccion...
start "" python -m streamlit run dashboard/app.py --server.port 8502
timeout /t 4 /nobreak > nul
start http://localhost:8502/Reuniones_del_Dia
