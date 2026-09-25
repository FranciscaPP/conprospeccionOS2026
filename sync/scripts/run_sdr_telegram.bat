@echo off
REM Reporte operativo de Nora para los tres clientes. Guardia L-V 11-20h Chile.
REM A las 20h agrega cierre diario y los viernes agrega resumen semanal.
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
"C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe" report_sdr_telegram.py --operational --scheduled --send >> "%~dp0sdr_telegram.log" 2>&1
