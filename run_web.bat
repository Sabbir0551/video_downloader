@echo off
title AnyStream Web Frontend (Next.js)
cd /d "%~dp0web"
echo ========================================================
echo   AnyStream Video Platform - Next.js Web Frontend
echo ========================================================
echo Starting Next.js development server on port 3000...
echo Frontend URL: http://localhost:3000
echo Backend API:  http://localhost:8000
echo ========================================================
pnpm run dev --port 3000
pause
