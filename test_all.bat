@echo off
title AnyStream - Full Test Suite (Vitest + Playwright)
cd /d "%~dp0web"
echo ========================================================
echo   AnyStream Video Platform - Running Full Test Suite
echo ========================================================
echo.
echo [1/2] Running Vitest Unit ^& Component Tests...
call pnpm test
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Vitest unit tests failed!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================================
echo [2/2] Running Playwright End-to-End (E2E) Smoke Test...
call pnpm test:e2e
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Playwright E2E smoke test failed!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================================
echo   ALL TESTS PASSED SUCCESSFULLY! (Vitest + Playwright)
echo ========================================================
pause

