@echo off
title AnyStream Platform Launcher
cd /d "%~dp0"
echo ========================================================
echo   AnyStream Video Platform - All-In-One Launcher
echo ========================================================
echo Starting Backend Server (Uvicorn)...
start "AnyStream Server" cmd /k "run.bat"

echo Starting Celery Download Worker...
start "AnyStream Worker" cmd /k "run_worker.bat"

echo Starting Celery Beat Janitor Scheduler...
start "AnyStream Beat" cmd /k "run_beat.bat"

echo Starting Next.js Web Frontend...
start "AnyStream Web" cmd /k "run_web.bat"

echo.
echo ========================================================
echo   All services launched in separate windows!
echo   Web Frontend: http://localhost:3000
echo   Backend API:  http://localhost:8000
echo   Swagger UI:   http://localhost:8000/docs
echo ========================================================
echo You can keep this window open or close it.
pause
