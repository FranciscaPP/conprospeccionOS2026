@echo off
REM Bot interactivo de Telegram de la SDR (long-polling). Corre siempre.
REM Lo mantiene vivo el Task Scheduler (al iniciar sesion + reinicio si falla).
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
"C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe" -u report_sdr_bot.py >> "%~dp0sdr_bot.log" 2>&1
