# Run Django development server with HTTPS
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         ZERGO DISTRIBUTORS - HTTPS SERVER                 ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "✓ SSL Certificate: cert.pem" -ForegroundColor Green
Write-Host "✓ Private Key: key.pem" -ForegroundColor Green
Write-Host ""
Write-Host "Server URLs:" -ForegroundColor White
Write-Host "  ➜ https://192.168.1.4:8000" -ForegroundColor Yellow
Write-Host "  ➜ https://localhost:8000" -ForegroundColor Yellow
Write-Host "  ➜ https://127.0.0.1:8000" -ForegroundColor Yellow
Write-Host ""
Write-Host "⚠ Browser Warning: You'll see a security warning because this" -ForegroundColor DarkYellow
Write-Host "  is a self-signed certificate. Click 'Advanced' → 'Proceed'" -ForegroundColor DarkYellow
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Gray
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

cd "c:\Users\LENOVO\Desktop\My Projects\zergo_distributors_sales_app"

# Check if certificates exist
if (-not (Test-Path "cert.pem") -or -not (Test-Path "key.pem")) {
    Write-Host "⚠ SSL certificates not found. Generating..." -ForegroundColor Yellow
    python generate_cert.py
    Write-Host ""
}

# Stop any existing server on port 8000
$existingProcess = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($existingProcess) {
    Write-Host "⚠ Stopping existing server on port 8000..." -ForegroundColor Yellow
    $processId = $existingProcess.OwningProcess
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

.\venv\Scripts\Activate.ps1
Write-Host "🚀 Starting HTTPS server..." -ForegroundColor Green
Write-Host ""
python manage.py runserver_plus --cert-file cert.pem --key-file key.pem 0.0.0.0:8000
