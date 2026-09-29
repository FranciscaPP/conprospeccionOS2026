@echo off
REM Snov reply -> contacto en CRM (GHL) + aviso Telegram. Lo dispara el Task Scheduler cada 2 horas.
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
"C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe" sync_snov_replies_to_ghl.py --client bambutech --client gbs --client balia >> "%~dp0snov_replies_to_ghl.log" 2>&1
