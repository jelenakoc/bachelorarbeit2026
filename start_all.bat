@echo off
setlocal
cd /d "%~dp0"

set "DASHBOARD_URL=http://127.0.0.1:8000/dashboard"

call :start_dashboard
timeout /t 2 >nul
call :start_tracker
goto :eof

:dashboard_running
netstat -ano | findstr "127.0.0.1:8000" | findstr "LISTENING" >nul
if errorlevel 1 (
    netstat -ano | findstr "127.0.0.1:8000" | findstr "ABH" >nul
)
exit /b %errorlevel%

:open_dashboard
start "" "%DASHBOARD_URL%"
exit /b 0

:start_dashboard
call :dashboard_running
if not errorlevel 1 (
    call :open_dashboard
    exit /b 0
)

if exist "Dashboard\Dashboard.exe" (
    start "Zeiterfassung Dashboard" "Dashboard\Dashboard.exe"
    exit /b 0
)

if exist "dist\Dashboard\Dashboard.exe" (
    start "Zeiterfassung Dashboard" "dist\Dashboard\Dashboard.exe"
    exit /b 0
)

if exist "dist_portable\Zeiterfassung\Dashboard\Dashboard.exe" (
    start "Zeiterfassung Dashboard" "dist_portable\Zeiterfassung\Dashboard\Dashboard.exe"
    exit /b 0
)

if exist ".venv\Scripts\python.exe" (
    start "Zeiterfassung Dashboard" cmd /k ".venv\Scripts\python.exe run_dashboard.py"
    exit /b 0
)

echo Dashboard konnte nicht gestartet werden.
pause
exit /b 1

:start_tracker
if exist "Tracker\Tracker.exe" (
    start "Zeiterfassung Tracker" "Tracker\Tracker.exe"
    exit /b 0
)

if exist "dist\Tracker\Tracker.exe" (
    start "Zeiterfassung Tracker" "dist\Tracker\Tracker.exe"
    exit /b 0
)

if exist "dist_portable\Zeiterfassung\Tracker\Tracker.exe" (
    start "Zeiterfassung Tracker" "dist_portable\Zeiterfassung\Tracker\Tracker.exe"
    exit /b 0
)

if exist ".venv\Scripts\python.exe" (
    start "Zeiterfassung Tracker" cmd /k ".venv\Scripts\python.exe app\tracker.py"
    exit /b 0
)

echo Tracker konnte nicht gestartet werden.
pause
exit /b 1
