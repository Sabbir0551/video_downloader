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

echo.
echo ========================================================
echo   All services launched in separate windows!
echo   Swagger UI: http://127.0.0.1:8000/docs
echo ========================================================
echo You can keep this window open or close it.
pause
