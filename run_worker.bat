@echo off
title YouthHub Celery Worker (Windows-Compatible)
echo ACTIVATING VENV...
call .\venv\Scripts\activate

echo STARTING CELERY WORKERS...
echo   NOTE: Using 'solo' pool - Windows-compatible (no eventlet/gevent needed)
echo   For production (Linux), switch to eventlet/gevent for higher concurrency.

REM Worker 1: Check-in queue — solo pool, high priority
REM 'solo' runs in the main thread, avoids Windows pipe/fcntl issues
start "YouthHub Worker [checkin]" cmd /k "call .\venv\Scripts\activate && celery -A youthhub worker -l info -Q checkin -P solo -n worker-checkin@%%h"

REM Worker 2: Email queue — solo pool
start "YouthHub Worker [email]" cmd /k "call .\venv\Scripts\activate && celery -A youthhub worker -l info -Q email -P solo -n worker-email@%%h"

echo.
echo Workers started in separate windows.
echo TIP: For higher concurrency on Windows, run multiple worker windows manually.
pause
