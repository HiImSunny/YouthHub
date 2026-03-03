@echo off
title YouthHub Celery Worker
echo ACTIVATING VENV...
call .\venv\Scripts\activate
echo STARTING CELERY WORKER (EVENTLET)...
celery -A youthhub worker -l info -P eventlet
pause
