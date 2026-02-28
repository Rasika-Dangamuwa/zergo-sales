# Stable HTTPS Server - Disables auto-reload to prevent crashes
Write-Host "Starting HTTPS Django Server (stable mode)..." -ForegroundColor Green
Write-Host "Access at: https://192.168.1.4:8000" -ForegroundColor Cyan
Write-Host ""

# Set environment to prevent werkzeug issues
$env:PYTHONDONTWRITEBYTECODE = "1"

# Change to script directory
Set-Location $PSScriptRoot

# Start server - let it run and stay in foreground
& ".\venv\Scripts\python.exe" -u manage.py runserver_plus 0.0.0.0:8000 --cert-file cert.pem --key-file key.pem

Write-Host ""
Write-Host "Server stopped." -ForegroundColor Yellow
