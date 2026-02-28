# Start HTTPS Django Server
Write-Host "Starting HTTPS Django Development Server..."
Write-Host "Access at: https://192.168.1.4:8000" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Change to project directory
Set-Location $PSScriptRoot

# Activate venv and run server
& ".\venv\Scripts\python.exe" manage.py runserver_plus 0.0.0.0:8000 --cert-file cert.pem --key-file key.pem
