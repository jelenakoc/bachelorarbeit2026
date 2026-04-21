@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtuelle Umgebung wurde nicht gefunden.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\pyinstaller.exe" (
    echo PyInstaller ist nicht installiert.
    echo Bitte zuerst ausfuehren:
    echo .venv\Scripts\python.exe -m pip install pyinstaller
    pause
    exit /b 1
)

if exist "dist_portable" rmdir /s /q "dist_portable"
if exist "build" rmdir /s /q "build"

.venv\Scripts\pyinstaller.exe ^
  --noconfirm ^
  --onedir ^
  --name Dashboard ^
  --paths . ^
  --add-data "app\dashboard.html;app" ^
  --add-data "app\dashboard.js;app" ^
  --hidden-import app.main ^
  run_dashboard.py

.venv\Scripts\pyinstaller.exe ^
  --noconfirm ^
  --onedir ^
  --name Tracker ^
  --paths . ^
  --additional-hooks-dir pyinstaller_hooks ^
  --add-data "C:\Users\milli\AppData\Local\Programs\Python\Python313\tcl\tcl8.6;_tcl_data" ^
  --add-data "C:\Users\milli\AppData\Local\Programs\Python\Python313\tcl\tk8.6;_tk_data" ^
  --collect-submodules tkinter ^
  --collect-data tkinter ^
  --hidden-import win32timezone ^
  --hidden-import _tkinter ^
  app\tracker.py

mkdir "dist_portable\Zeiterfassung"
xcopy /E /I /Y "dist\Dashboard" "dist_portable\Zeiterfassung\Dashboard" >nul
xcopy /E /I /Y "dist\Tracker" "dist_portable\Zeiterfassung\Tracker" >nul
copy /Y "start_all.bat" "dist_portable\Zeiterfassung\start_all.bat" >nul

echo Portable Version wurde erstellt unter:
echo dist_portable\Zeiterfassung
pause
