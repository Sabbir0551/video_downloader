$Host.UI.RawUI.WindowTitle = "AnyStream Video Platform - API Server"
Set-Location "$PSScriptRoot\backend"
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  AnyStream Video Platform - Backend Server" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "Server running at: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Swagger UI Docs:  http://127.0.0.1:8000/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press CTRL+C to stop the server." -ForegroundColor Gray
Write-Host "========================================================" -ForegroundColor Cyan
& ".\.venv\Scripts\uvicorn.exe" app.main:app --host 0.0.0.0 --port 8000 --reload

