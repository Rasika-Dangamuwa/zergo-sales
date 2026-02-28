@echo off
REM Automated Commission Payout Processor
REM This script is intended to be run by Windows Task Scheduler

cd /d "%~dp0"

echo ============================================================
echo Commission Payout Processor
echo Started: %date% %time%
echo ============================================================

REM Activate virtual environment and run the command
call venv\Scripts\activate.bat
python manage.py process_commission_payouts

echo.
echo ============================================================
echo Completed: %date% %time%
echo ============================================================

REM Log output to file (uncomment if needed)
REM >> logs\commission_payouts.log 2>&1
