# Zergo Distributors Sales App - Setup Script
# Run this script after installing requirements.txt

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Zergo Distributors Sales App - Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "WARNING: Virtual environment is not activated!" -ForegroundColor Yellow
    Write-Host "Please activate it first: .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne 'y') {
        exit
    }
}

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file from .env.example..." -ForegroundColor Green
    Copy-Item ".env.example" ".env"
    Write-Host "Please edit .env file with your database credentials!" -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Press Enter after editing .env file"
}

# Create static directory
Write-Host "Creating static directory..." -ForegroundColor Green
if (-not (Test-Path "static")) {
    New-Item -ItemType Directory -Path "static" | Out-Null
}

# Create media directory
Write-Host "Creating media directory..." -ForegroundColor Green
if (-not (Test-Path "media")) {
    New-Item -ItemType Directory -Path "media" | Out-Null
    New-Item -ItemType Directory -Path "media\profiles" | Out-Null
    New-Item -ItemType Directory -Path "media\products" | Out-Null
    New-Item -ItemType Directory -Path "media\shop_visits" | Out-Null
    New-Item -ItemType Directory -Path "media\payment_proofs" | Out-Null
}

# Run migrations
Write-Host ""
Write-Host "Running database migrations..." -ForegroundColor Green
python manage.py makemigrations
python manage.py migrate

# Create superuser
Write-Host ""
Write-Host "Creating superuser account..." -ForegroundColor Green
Write-Host "Please provide admin credentials:" -ForegroundColor Yellow
python manage.py createsuperuser

# Collect static files
Write-Host ""
Write-Host "Collecting static files..." -ForegroundColor Green
python manage.py collectstatic --noinput

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Run: python manage.py runserver" -ForegroundColor White
Write-Host "2. Open: http://127.0.0.1:8000/" -ForegroundColor White
Write-Host "3. Admin panel: http://127.0.0.1:8000/admin/" -ForegroundColor White
Write-Host ""
Write-Host "Don't forget to:" -ForegroundColor Yellow
Write-Host "- Create users (sales reps, office staff)" -ForegroundColor White
Write-Host "- Add companies and products" -ForegroundColor White
Write-Host "- Add shops and assign sales reps" -ForegroundColor White
Write-Host ""
Write-Host "Happy selling with Zergo Distributors!" -ForegroundColor Cyan
