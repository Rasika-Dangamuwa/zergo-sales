@echo off
REM Quick HTTPS Server Launcher
echo.
echo ===================================
echo   ZERGO DISTRIBUTORS - HTTPS
echo ===================================
echo.

REM Check if certificates exist
if not exist cert.pem (
    echo Generating SSL certificates...
    python generate_cert.py
    echo.
)

echo Starting HTTPS server...
echo.
echo Access URLs:
echo   Desktop: https://localhost:8000
echo   Mobile:  https://192.168.1.4:8000
echo.
echo Press Ctrl+C to stop
echo.

REM Activate virtual environment and start server
call venv\Scripts\activate.bat
python manage.py runserver_plus --cert-file cert.pem --key-file key.pem 0.0.0.0:8000
