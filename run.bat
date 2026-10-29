@echo off
title AnyStream Video Platform - API Server
cd /d "%~dp0backend"
echo ========================================================
echo   AnyStream Video Platform - Backend Server
echo ========================================================
echo Activating virtual environment...
call .venv\Scripts\activate.bat
echo.
echo Server running at: http://127.0.0.1:8000
echo Swagger UI Docs:  http://127.0.0.1:8000/docs
echo.
echo Press CTRL+C to stop the server.
echo ========================================================
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause

