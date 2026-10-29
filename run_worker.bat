@echo off
title AnyStream Media Download Worker - Celery
cd /d "%~dp0backend"
echo ========================================================
echo   AnyStream Video Platform - Celery Download Worker
echo ========================================================
echo Activating virtual environment...
call .venv\Scripts\activate.bat
echo.
echo Starting Celery Worker (Windows mode: --pool=solo)...
echo Make sure Redis is running on port 6379!
echo.
echo Press CTRL+C to stop the worker.
echo ========================================================
celery -A app.worker.celery_app worker --loglevel=info --pool=solo
pause
