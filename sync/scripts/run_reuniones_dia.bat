@echo off
REM Reuniones del dia por cliente a Telegram. Lo dispara el Task Scheduler todos los dias a las 10:00.
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
"C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe" report_reuniones_dia.py >> "%~dp0reuniones_dia.log" 2>&1
