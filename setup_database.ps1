# Database Setup Script for Zergo Distributors Sales App
# This script will help you set up the PostgreSQL database

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Database Setup - Zergo Sales App" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Function to find PostgreSQL installation
function Find-PostgreSQL {
    $possiblePaths = @(
        "C:\Program Files\PostgreSQL",
        "C:\Program Files (x86)\PostgreSQL",
        "C:\PostgreSQL"
    )
    
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $versions = Get-ChildItem $path -Directory | Sort-Object Name -Descending
            if ($versions) {
                $latestVersion = $versions[0]
                $psqlPath = Join-Path $latestVersion.FullName "bin\psql.exe"
                if (Test-Path $psqlPath) {
                    return $psqlPath
                }
            }
        }
    }
    return $null
}

# Try to find PostgreSQL
$psqlPath = Find-PostgreSQL

if (-not $psqlPath) {
    Write-Host "PostgreSQL not found in default locations." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please choose an option:" -ForegroundColor Yellow
    Write-Host "1. Enter the path to psql.exe manually" -ForegroundColor White
    Write-Host "2. Use pgAdmin or another PostgreSQL client" -ForegroundColor White
    Write-Host "3. Exit and install PostgreSQL" -ForegroundColor White
    Write-Host ""
    $choice = Read-Host "Enter your choice (1-3)"
    
    switch ($choice) {
        "1" {
            $psqlPath = Read-Host "Enter the full path to psql.exe"
            if (-not (Test-Path $psqlPath)) {
                Write-Host "Invalid path. Exiting..." -ForegroundColor Red
                exit
            }
        }
        "2" {
            Write-Host ""
            Write-Host "Please execute the following SQL commands in pgAdmin or your PostgreSQL client:" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "-- Step 1: Create Database" -ForegroundColor Green
            Write-Host "CREATE DATABASE zergo_sales_db;" -ForegroundColor White
            Write-Host ""
            Write-Host "-- Step 2: Connect to the new database, then run:" -ForegroundColor Green
            Write-Host "CREATE EXTENSION IF NOT EXISTS postgis;" -ForegroundColor White
            Write-Host ""
            Write-Host "After executing these commands, press Enter to continue with Django setup..." -ForegroundColor Yellow
            Read-Host
            
            # Continue with Django migrations
            Write-Host ""
            Write-Host "Proceeding with Django migrations..." -ForegroundColor Green
            
            # Check if .env exists
            if (-not (Test-Path ".env")) {
                Write-Host "Creating .env file..." -ForegroundColor Yellow
                Copy-Item ".env.example" ".env"
                Write-Host ""
                Write-Host "IMPORTANT: Please edit .env file with your PostgreSQL credentials!" -ForegroundColor Red
                Write-Host "Press Enter after editing .env file..." -ForegroundColor Yellow
                Read-Host
            }
            
            # Run Django migrations
            Write-Host "Running makemigrations..." -ForegroundColor Green
            python manage.py makemigrations
            
            Write-Host ""
            Write-Host "Running migrate..." -ForegroundColor Green
            python manage.py migrate
            
            Write-Host ""
            Write-Host "Database setup complete!" -ForegroundColor Green
            exit
        }
        "3" {
            Write-Host ""
            Write-Host "Download PostgreSQL from: https://www.postgresql.org/download/windows/" -ForegroundColor Cyan
            Write-Host "Make sure to install PostGIS extension during installation." -ForegroundColor Yellow
            exit
        }
        default {
            Write-Host "Invalid choice. Exiting..." -ForegroundColor Red
            exit
        }
    }
}

Write-Host "Found PostgreSQL at: $psqlPath" -ForegroundColor Green
Write-Host ""

# Get PostgreSQL credentials
Write-Host "Enter PostgreSQL credentials:" -ForegroundColor Yellow
$dbUser = Read-Host "PostgreSQL username (default: postgres)"
if ([string]::IsNullOrWhiteSpace($dbUser)) {
    $dbUser = "postgres"
}

$securePassword = Read-Host "PostgreSQL password" -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
$dbPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

$dbName = "zergo_sales_db"

Write-Host ""
Write-Host "Creating database: $dbName" -ForegroundColor Green

# Set environment variable for password
$env:PGPASSWORD = $dbPassword

# Create database
$createDbCommand = "CREATE DATABASE $dbName;"
& $psqlPath -U $dbUser -c $createDbCommand 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Database created successfully!" -ForegroundColor Green
} else {
    Write-Host "Database might already exist or there was an error." -ForegroundColor Yellow
    Write-Host "Continuing with PostGIS setup..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Enabling PostGIS extension..." -ForegroundColor Green

# Enable PostGIS
$enablePostGISCommand = "CREATE EXTENSION IF NOT EXISTS postgis;"
& $psqlPath -U $dbUser -d $dbName -c $enablePostGISCommand 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ PostGIS extension enabled successfully!" -ForegroundColor Green
} else {
    Write-Host "✗ Error enabling PostGIS. You may need to install it separately." -ForegroundColor Red
    Write-Host "Download PostGIS from: https://postgis.net/windows_downloads/" -ForegroundColor Yellow
}

# Clear password from environment
Remove-Item Env:\PGPASSWORD

Write-Host ""
Write-Host "Database setup complete!" -ForegroundColor Green
Write-Host ""

# Update .env file
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file..." -ForegroundColor Green
    Copy-Item ".env.example" ".env"
}

Write-Host "Updating .env file with database credentials..." -ForegroundColor Green
$envContent = Get-Content ".env"
$envContent = $envContent -replace "DB_NAME=.*", "DB_NAME=$dbName"
$envContent = $envContent -replace "DB_USER=.*", "DB_USER=$dbUser"
$envContent = $envContent -replace "DB_PASSWORD=.*", "DB_PASSWORD=$dbPassword"
$envContent | Set-Content ".env"

Write-Host "✓ .env file updated!" -ForegroundColor Green
Write-Host ""

# Continue with Django setup
Write-Host "Running Django migrations..." -ForegroundColor Green
Write-Host ""

Write-Host "Step 1: makemigrations" -ForegroundColor Yellow
python manage.py makemigrations

Write-Host ""
Write-Host "Step 2: migrate" -ForegroundColor Yellow
python manage.py migrate

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Database Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Create superuser: python manage.py createsuperuser" -ForegroundColor White
Write-Host "2. Run server: python manage.py runserver" -ForegroundColor White
Write-Host "3. Access: http://127.0.0.1:8000/" -ForegroundColor White
Write-Host ""
