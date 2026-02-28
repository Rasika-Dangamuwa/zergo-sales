# Quick HTTPS Setup Script for Bluetooth Printing
# Run this script to set up SSL/HTTPS for mobile Bluetooth printing

Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║    ZERGO DISTRIBUTORS - HTTPS/BLUETOOTH SETUP            ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Get local IP
$localIP = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "Wi-Fi*" | Select-Object -First 1).IPAddress
if (-not $localIP) {
    $localIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -like "192.168.*"} | Select-Object -First 1).IPAddress
}

Write-Host "📡 Network Information:" -ForegroundColor Yellow
Write-Host "   Local IP: $localIP" -ForegroundColor White
Write-Host ""

# Check if certificates exist
$certExists = Test-Path "cert.pem"
$keyExists = Test-Path "key.pem"

if (-not $certExists -or -not $keyExists) {
    Write-Host "🔐 Generating SSL Certificates..." -ForegroundColor Yellow
    Write-Host ""
    
    # Check if pyOpenSSL is installed
    $pyOpenSSL = pip list | Select-String "pyOpenSSL"
    if (-not $pyOpenSSL) {
        Write-Host "Installing pyOpenSSL..." -ForegroundColor Yellow
        pip install pyOpenSSL
        Write-Host ""
    }
    
    # Generate certificates
    python generate_cert.py
    Write-Host ""
} else {
    Write-Host "✓ SSL certificates already exist" -ForegroundColor Green
    Write-Host "   cert.pem - $(Get-Item cert.pem | Select-Object -ExpandProperty Length) bytes" -ForegroundColor Gray
    Write-Host "   key.pem  - $(Get-Item key.pem | Select-Object -ExpandProperty Length) bytes" -ForegroundColor Gray
    Write-Host ""
}

# Check firewall
Write-Host "🔥 Checking Windows Firewall..." -ForegroundColor Yellow
$firewallRule = Get-NetFirewallRule -DisplayName "Django HTTPS" -ErrorAction SilentlyContinue

if (-not $firewallRule) {
    Write-Host "   Adding firewall rule for port 8000..." -ForegroundColor Yellow
    try {
        New-NetFirewallRule -DisplayName "Django HTTPS" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -ErrorAction Stop | Out-Null
        Write-Host "   ✓ Firewall rule added" -ForegroundColor Green
    } catch {
        Write-Host "   ⚠ Failed to add firewall rule (run as Administrator)" -ForegroundColor DarkYellow
        Write-Host "   Manual: Windows Defender Firewall → Advanced → New Rule → Port 8000" -ForegroundColor Gray
    }
} else {
    Write-Host "   ✓ Firewall rule already exists" -ForegroundColor Green
}
Write-Host ""

# Display access URLs
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                HTTPS URLs (Ready to Use)                  ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Desktop Access:" -ForegroundColor White
Write-Host "  https://localhost:8000" -ForegroundColor Cyan
Write-Host "  https://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Mobile Access (Same WiFi):" -ForegroundColor White
Write-Host "  https://$localIP:8000" -ForegroundColor Yellow -NoNewline
Write-Host " ← Use this on your phone!" -ForegroundColor Green
Write-Host ""

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Write-Host "📱 Mobile Setup Instructions:" -ForegroundColor Yellow
Write-Host "   1. Connect your phone to the same WiFi" -ForegroundColor White
Write-Host "   2. Open Chrome or Edge browser (not Safari)" -ForegroundColor White
Write-Host "   3. Go to: https://$localIP:8000" -ForegroundColor Cyan
Write-Host "   4. Accept the security warning:" -ForegroundColor White
Write-Host "      → Tap 'Advanced'" -ForegroundColor Gray
Write-Host "      → Tap 'Proceed to $localIP (unsafe)'" -ForegroundColor Gray
Write-Host "   5. Enable Bluetooth on your phone" -ForegroundColor White
Write-Host "   6. Turn on your Bluetooth printer" -ForegroundColor White
Write-Host "   7. Navigate to a bill → Mobile Print → Print via Bluetooth" -ForegroundColor White
Write-Host ""

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Ask to start server
$startServer = Read-Host "Start HTTPS server now? (Y/N)"

if ($startServer -eq "Y" -or $startServer -eq "y") {
    Write-Host ""
    Write-Host "🚀 Starting HTTPS server..." -ForegroundColor Green
    Write-Host "   Press Ctrl+C to stop" -ForegroundColor Gray
    Write-Host ""
    
    # Stop existing servers
    $existingProcess = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
    if ($existingProcess) {
        Write-Host "   Stopping existing server..." -ForegroundColor Yellow
        $processId = $existingProcess.OwningProcess
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
    
    # Start server
    .\venv\Scripts\Activate.ps1
    python manage.py runserver_plus --cert-file cert.pem --key-file key.pem 0.0.0.0:8000
} else {
    Write-Host ""
    Write-Host "To start the server later, run:" -ForegroundColor Yellow
    Write-Host "   .\run_https.ps1" -ForegroundColor Cyan
    Write-Host ""
}
