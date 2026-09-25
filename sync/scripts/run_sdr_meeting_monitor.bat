@echo off
cd /d "%~dp0"
"C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe" report_sdr_telegram.py --operational --scheduled --monitor-meetings --send >> "%~dp0sdr_meeting_monitor.log" 2>&1
