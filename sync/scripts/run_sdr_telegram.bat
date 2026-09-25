@echo off
REM Update horario de la SDR a Telegram. Lo dispara el Task Scheduler cada hora (10-20h).
REM El propio script se salta fines de semana y fuera de 10-22h Chile. Cierre del dia = envio de las 21h.
REM --solo bambutech: desde 23-sep-2026 solo BambuTech + cumplimiento de tareas GHL (quitar para volver a 2 clientes).
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
"C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe" report_sdr_telegram.py --operational --scheduled --send >> "%~dp0sdr_telegram.log" 2>&1
