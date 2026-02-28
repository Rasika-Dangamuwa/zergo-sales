@echo off
echo ================================================
echo  Zergo Distributors Sales App - Server Startup
echo ================================================
echo.

cd /d "%~dp0"

echo Step 1: Checking for new migrations...
python manage.py makemigrations sales
echo.

echo Step 2: Applying migrations...
python manage.py migrate
echo.

echo Step 3: Starting server on http://192.168.1.4:8000
echo.
echo Access the application:
echo   - From this computer: http://localhost:8000
echo   - From phone/tablet: http://192.168.1.4:8000
echo.
echo Press Ctrl+C to stop the server
echo.

python manage.py runserver 192.168.1.4:8000

pause
