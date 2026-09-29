@echo off
REM Bot interactivo de Telegram para mover estatus/crear tareas/responder correo/agendar (long-polling). Corre siempre.
REM Lo mantiene vivo el Task Scheduler (al iniciar sesion + reinicio si falla).
REM Sin --client: corre los 3 clientes (bambutech, gbs, balia) en threads separados.
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
"C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe" -u telegram_ghl_bot.py >> "%~dp0telegram_ghl_bot.log" 2>&1
