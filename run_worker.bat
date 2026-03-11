@echo off
title YouthHub Celery Worker (High-Concurrency)
echo ACTIVATING VENV...
call .\venv\Scripts\activate

echo STARTING CELERY WORKERS...
echo   - Queue [checkin]: High-concurrency check-in processing (eventlet, 100 coroutines)
echo   - Queue [email]:   Email notification tasks

REM Worker 1: Check-in queue — high concurrency (eventlet for I/O bound tasks)
start "YouthHub Worker [checkin]" cmd /k "call .\venv\Scripts\activate && celery -A youthhub worker -l info -Q checkin -P eventlet -c 100 -n worker-checkin@%%h"

REM Worker 2: Email queue — standard concurrency
start "YouthHub Worker [email]" cmd /k "call .\venv\Scripts\activate && celery -A youthhub worker -l info -Q email -P eventlet -c 20 -n worker-email@%%h"

echo Workers started in separate windows.
pause
