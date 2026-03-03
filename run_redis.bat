@echo off
title YouthHub - Redis (Docker)
echo CHECKING FOR EXISTING REDIS CONTAINER...
docker stop youthhub-redis >nul 2>&1
docker rm youthhub-redis >nul 2>&1

echo STARTING REDIS VIA DOCKER...
echo Port: 6379
docker run --name youthhub-redis -p 6379:6379 redis
pause
