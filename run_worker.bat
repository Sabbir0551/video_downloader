@echo off
title AnyStream Media Download Worker - Celery
set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin;%PATH%"
cd /d "%~dp0backend"
echo ========================================================
echo   AnyStream Video Platform - Celery Download Worker
echo ========================================================
echo Activating virtual environment...
call .venv\Scripts\activate.bat
echo.
echo Starting Celery Worker (Windows mode: --pool=solo)...
echo Redis is connected on port 6379.
echo FFmpeg version:
ffmpeg -version | findstr /C:"ffmpeg version"
echo.
echo Press CTRL+C to stop the worker.
echo ========================================================
.\.venv\Scripts\python.exe -m celery -A app.worker.celery_app worker --loglevel=info --pool=solo
pause
