@echo off
title YouthHub Web Server
echo ACTIVATING VENV...
call .\venv\Scripts\activate
echo STARTING DJANGO SERVER...
python manage.py runserver
pause
