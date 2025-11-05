@echo off
:: StitchAdmin 2.0 - SQLAlchemy Update Script
:: Behebt Python 3.13 Kompatibilitätsproblem

echo ================================================================
echo         StitchAdmin 2.0 - SQLAlchemy Update
echo ================================================================
echo.

cd /d "%~dp0"

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

:: Upgrade SQLAlchemy
echo Aktualisiere SQLAlchemy fuer Python 3.13...
echo.

pip install --upgrade SQLAlchemy>=2.0.36

if errorlevel 1 (
    echo.
    echo [FEHLER] SQLAlchemy konnte nicht aktualisiert werden!
    pause
    exit /b 1
)

echo.
echo [OK] SQLAlchemy erfolgreich aktualisiert!
echo.

:: Zeige installierte Version
echo Installierte Version:
pip show SQLAlchemy | findstr "Version"

echo.
echo ================================================================
echo Update abgeschlossen!
echo ================================================================
echo.
echo Starte jetzt die Anwendung mit: start.bat
echo.
pause
