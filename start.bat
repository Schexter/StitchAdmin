@echo off
:: StitchAdmin 2.0 - Schnellstart-Script
:: Erstellt von Hans Hahn - Alle Rechte vorbehalten

echo ================================================================
echo              StitchAdmin 2.0 - Schnellstart
echo ================================================================
echo.

cd /d "%~dp0"

:: Prüfe ob Virtual Environment existiert
if not exist ".venv\" (
    echo [!] Virtual Environment nicht gefunden!
    echo.
    echo Erstelle Virtual Environment...
    python -m venv .venv
    
    if errorlevel 1 (
        echo [FEHLER] Virtual Environment konnte nicht erstellt werden!
        echo Bitte stellen Sie sicher, dass Python installiert ist.
        pause
        exit /b 1
    )
    
    echo [OK] Virtual Environment erstellt
    echo.
)

:: Aktiviere Virtual Environment
echo Aktiviere Virtual Environment...
call .venv\Scripts\activate.bat

if errorlevel 1 (
    echo [FEHLER] Virtual Environment konnte nicht aktiviert werden!
    pause
    exit /b 1
)

echo [OK] Virtual Environment aktiviert
echo.

:: Prüfe ob Requirements installiert sind
pip show Flask >nul 2>&1
if errorlevel 1 (
    echo [!] Dependencies nicht installiert
    echo.
    echo Installiere Requirements...
    pip install -r requirements.txt
    
    if errorlevel 1 (
        echo [FEHLER] Requirements konnten nicht installiert werden!
        pause
        exit /b 1
    )
    
    echo [OK] Requirements installiert
    echo.
)

:: Starte Anwendung
echo ================================================================
echo                     Starte Anwendung
echo ================================================================
echo.
echo URL: http://localhost:5000
echo Login: admin / admin
echo.
echo Zum Beenden: STRG+C
echo ================================================================
echo.

python app.py

:: Falls Fehler beim Start
if errorlevel 1 (
    echo.
    echo [FEHLER] Anwendung konnte nicht gestartet werden!
    echo Bitte pruefen Sie die Fehlermeldungen oben.
    pause
    exit /b 1
)

pause
