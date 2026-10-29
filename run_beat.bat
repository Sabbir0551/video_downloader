@echo off
title AnyStream Celery Beat Scheduler
cd /d "%~dp0backend"
echo ========================================================
echo   AnyStream Video Platform - Celery Beat Janitor
echo ========================================================
echo Activating virtual environment...
call .venv\Scripts\activate.bat
echo.
echo Starting Celery Beat scheduler...
echo Evicts expired files and marks jobs EXPIRED after 30 minutes.
echo Schedule: Every 5 minutes (300 seconds).
echo.
echo Press CTRL+C to stop the scheduler.
echo ========================================================
if exist celerybeat-schedule* del /f /q celerybeat-schedule* 2>nul
.\.venv\Scripts\python.exe -m celery -A app.worker.celery_app beat --loglevel=info
pause

