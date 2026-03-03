@echo off
title YouthHub - Master Starter
echo ========================================
echo   YOUTHHUB PROJECT - STARTING ALL
echo ========================================

echo 0. Starting Redis (Docker)...
start "YouthHub Redis" run_redis.bat

echo 1. Starting AI (Ollama)...
start "YouthHub AI" run_ai.bat

echo 2. Starting Worker (Celery)...
start "YouthHub Worker" run_worker.bat

echo 3. Starting Web (Django)...
start "YouthHub Web" run_web.bat

echo ----------------------------------------
echo ALL SYSTEMS ARE STARTING IN NEW WINDOWS.
echo YOU CAN CLOSE THIS TERMINAL.
echo ----------------------------------------
timeout /t 5
