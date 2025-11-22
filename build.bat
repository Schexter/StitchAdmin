@echo off
REM =====================================
REM StitchAdmin 2.0 - Build Script
REM Erstellt ausführbare EXE-Datei
REM 
REM Erstellt von Hans Hahn - Alle Rechte vorbehalten
REM =====================================

echo.
echo ========================================
echo   StitchAdmin 2.0 - Build Process
echo ========================================
echo.

REM Farbige Ausgabe aktivieren
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do (
  set "DEL=%%a"
)

REM Prüfe ob Python verfügbar ist
python --version >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Python ist nicht installiert oder nicht im PATH!
    echo Bitte installieren Sie Python 3.11+ von https://www.python.org
    pause
    exit /b 1
)

echo [1/7] Python Version pruefen...
python --version
echo.

REM Prüfe ob Virtual Environment existiert
if not exist ".venv" (
    echo [WARNUNG] Kein Virtual Environment gefunden!
    echo Erstelle Virtual Environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [FEHLER] Konnte Virtual Environment nicht erstellen!
        pause
        exit /b 1
    )
    echo [OK] Virtual Environment erstellt
    echo.
)

REM Aktiviere Virtual Environment
echo [2/7] Aktiviere Virtual Environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [FEHLER] Konnte Virtual Environment nicht aktivieren!
    pause
    exit /b 1
)
echo [OK] Virtual Environment aktiviert
echo.

REM Installiere/Update Dependencies
echo [3/7] Installiere/Update Dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
if errorlevel 1 (
    echo [FEHLER] Dependency-Installation fehlgeschlagen!
    pause
    exit /b 1
)
echo [OK] Dependencies installiert
echo.

REM Lösche alte Builds
echo [4/7] Loesche alte Builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "StitchAdmin.spec~" del /q StitchAdmin.spec~
echo [OK] Alte Builds geloescht
echo.

REM Erstelle Logo-Verzeichnis falls nicht vorhanden
if not exist "src\static\img" mkdir src\static\img

REM Prüfe ob Logo existiert
if not exist "src\static\img\logo.ico" (
    echo [WARNUNG] Kein Logo (logo.ico) gefunden!
    echo EXE wird ohne Icon erstellt.
    echo Platzieren Sie logo.ico in src\static\img\ für Icon-Support
    timeout /t 3 >nul
)
echo.

REM Build mit PyInstaller
echo [5/7] Erstelle EXE mit PyInstaller...
echo Dies kann einige Minuten dauern...
echo.
pyinstaller StitchAdmin.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo [FEHLER] PyInstaller Build fehlgeschlagen!
    echo.
    echo Moegliche Ursachen:
    echo - Fehlende Dependencies in requirements.txt
    echo - Import-Fehler im Code
    echo - Unvollstaendige Hidden Imports in StitchAdmin.spec
    echo.
    echo Pruefen Sie die Fehlermeldungen oben.
    pause
    exit /b 1
)
echo.
echo [OK] EXE erfolgreich erstellt
echo.

REM Prüfe ob EXE existiert
if not exist "dist\StitchAdmin.exe" (
    echo [FEHLER] StitchAdmin.exe wurde nicht erstellt!
    pause
    exit /b 1
)

REM Zeige Datei-Informationen
echo [6/7] Build-Informationen:
echo ----------------------------------------
for %%I in (dist\StitchAdmin.exe) do (
    echo Datei:    %%~nxI
    echo Groesse:  %%~zI Bytes (ca. %%~zI / 1048576 MB^)
    echo Pfad:     %%~fI
)
echo ----------------------------------------
echo.

REM Erstelle Installer-Verzeichnis
if not exist "installer" mkdir installer

REM Kopiere zusätzliche Dateien
echo [7/7] Erstelle Deployment-Paket...
if exist "README.md" copy /y README.md dist\README.md >nul
if exist "CHANGELOG.md" copy /y CHANGELOG.md dist\CHANGELOG.md >nul
echo [OK] Deployment-Paket erstellt
echo.

echo ========================================
echo   Build erfolgreich abgeschlossen!
echo ========================================
echo.
echo Die ausfuehrbare Datei befindet sich in:
echo %CD%\dist\StitchAdmin.exe
echo.
echo Naechste Schritte:
echo 1. Testen Sie die EXE durch Doppelklick
echo 2. Erstellen Sie einen Installer mit Inno Setup
echo 3. Fuehren Sie Tests auf einem Clean-System durch
echo.
echo Druecken Sie eine beliebige Taste zum Oeffnen des dist-Ordners...
pause >nul
explorer dist
