@echo off
REM ============================================================================
REM StitchAdmin 2.0 - Build Script
REM Erstellt automatisch den vollständigen Windows-Installer
REM 
REM Erstellt von Hans Hahn - Alle Rechte vorbehalten
REM ============================================================================

setlocal EnableDelayedExpansion

echo.
echo ============================================================================
echo   ____  _   _ _       _        _       _           _         ____    ___  
echo  / ___^|^| ^|_(_) ^|_ ___^| ^|__    / \   __^| ^|_ __ ___ (_)_ __   ^|___ \  / _ \ 
echo  \___ \^| __^| ^| __/ __^| '_ \  / _ \ / _` ^| '_ ` _ \^| ^| '_ \    __) ^|^| ^| ^| ^|
echo   ___) ^| ^|_^| ^| ^|_\__ \ ^| ^| ^|/ ___ \ (_^| ^| ^| ^| ^| ^| ^| ^| ^| ^| ^|  / __/ ^| ^|_^| ^|
echo  ^|____/ \__^|_^|\__^|___/_^| ^|_/_/   \_\__,_^|_^| ^|_^| ^|_^|_^|_^| ^|_^| ^|_____^| \___/ 
echo.
echo                         BUILD SCRIPT v2.0
echo ============================================================================
echo.

REM ============================================================================
REM KONFIGURATION
REM ============================================================================
set "APP_NAME=StitchAdmin"
set "APP_VERSION=2.0.0"
set "INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
set "PYTHON_CMD=python"

REM ============================================================================
REM SCHRITT 1: Prüfe Voraussetzungen
REM ============================================================================
echo [1/8] Pruefe Voraussetzungen...
echo.

REM Prüfe Python
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    echo   [FEHLER] Python ist nicht installiert oder nicht im PATH!
    echo   Bitte installieren Sie Python 3.9+ von https://python.org
    goto :error
)
for /f "tokens=2" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYTHON_VERSION=%%i
echo   [OK] Python %PYTHON_VERSION% gefunden

REM Prüfe pip
%PYTHON_CMD% -m pip --version >nul 2>&1
if errorlevel 1 (
    echo   [FEHLER] pip ist nicht installiert!
    goto :error
)
echo   [OK] pip gefunden

REM Prüfe Inno Setup
if exist "%INNO_PATH%" (
    echo   [OK] Inno Setup gefunden
    set "INNO_AVAILABLE=1"
) else (
    echo   [WARNUNG] Inno Setup nicht gefunden unter:
    echo            %INNO_PATH%
    echo            Der Installer wird nicht erstellt.
    echo            Download: https://jrsoftware.org/isdl.php
    set "INNO_AVAILABLE=0"
)
echo.

REM ============================================================================
REM SCHRITT 2: Virtuelle Umgebung aktivieren (falls vorhanden)
REM ============================================================================
echo [2/8] Pruefe virtuelle Umgebung...
if exist ".venv\Scripts\activate.bat" (
    echo   [OK] Aktiviere .venv
    call .venv\Scripts\activate.bat
) else (
    echo   [INFO] Keine virtuelle Umgebung gefunden - nutze System-Python
)
echo.

REM ============================================================================
REM SCHRITT 3: Dependencies installieren
REM ============================================================================
echo [3/8] Installiere/Aktualisiere Dependencies...
%PYTHON_CMD% -m pip install --upgrade pip >nul 2>&1
%PYTHON_CMD% -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo   [FEHLER] Dependencies konnten nicht installiert werden!
    goto :error
)

REM PyInstaller separat installieren falls nicht vorhanden
%PYTHON_CMD% -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo   [INFO] Installiere PyInstaller...
    %PYTHON_CMD% -m pip install pyinstaller --quiet
)
echo   [OK] Alle Dependencies installiert
echo.

REM ============================================================================
REM SCHRITT 4: Bereinige alte Builds
REM ============================================================================
echo [4/8] Bereinige alte Builds...
if exist "dist" (
    rmdir /s /q "dist" 2>nul
    echo   - dist/ entfernt
)
if exist "build" (
    rmdir /s /q "build" 2>nul
    echo   - build/ entfernt
)
if exist "installer_output" (
    rmdir /s /q "installer_output" 2>nul
    echo   - installer_output/ entfernt
)
echo   [OK] Alte Builds entfernt
echo.

REM ============================================================================
REM SCHRITT 5: Erstelle Version-Info Datei
REM ============================================================================
echo [5/8] Erstelle Version-Info...
%PYTHON_CMD% -c "from build_config import create_version_file; create_version_file()" 2>nul
if exist "version_info.txt" (
    echo   [OK] version_info.txt erstellt
) else (
    echo   [INFO] Keine Version-Info erstellt (optional)
)
echo.

REM ============================================================================
REM SCHRITT 6: Erstelle EXE mit PyInstaller
REM ============================================================================
echo [6/8] Erstelle EXE mit PyInstaller...
echo   Dies kann einige Minuten dauern...
echo.

%PYTHON_CMD% -m PyInstaller StitchAdmin.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo   [FEHLER] PyInstaller Build fehlgeschlagen!
    echo   Pruefen Sie die Fehlermeldungen oben.
    goto :error
)

REM Prüfe ob EXE erstellt wurde
if not exist "dist\StitchAdmin\StitchAdmin.exe" (
    echo   [FEHLER] StitchAdmin.exe wurde nicht erstellt!
    goto :error
)
echo.
echo   [OK] StitchAdmin.exe erfolgreich erstellt!
echo.

REM ============================================================================
REM SCHRITT 7: Erstelle Init-Database Script
REM ============================================================================
echo [7/8] Erstelle Initialisierungs-Script...
%PYTHON_CMD% -m PyInstaller --onefile --console --name init_database init_database.py --clean --noconfirm --distpath dist\StitchAdmin 2>nul
if exist "dist\StitchAdmin\init_database.exe" (
    echo   [OK] init_database.exe erstellt
) else (
    echo   [WARNUNG] init_database.exe konnte nicht erstellt werden
    echo            Die Datenbank wird beim ersten Start initialisiert.
)
echo.

REM ============================================================================
REM SCHRITT 8: Erstelle Installer mit Inno Setup
REM ============================================================================
if "%INNO_AVAILABLE%"=="1" (
    echo [8/8] Erstelle Windows-Installer mit Inno Setup...
    
    mkdir installer_output 2>nul
    
    "%INNO_PATH%" installer.iss
    if errorlevel 1 (
        echo   [FEHLER] Installer-Erstellung fehlgeschlagen!
        goto :error
    )
    
    if exist "installer_output\StitchAdmin_2.0_Setup.exe" (
        echo.
        echo   [OK] Installer erfolgreich erstellt!
    ) else (
        echo   [FEHLER] Installer-Datei nicht gefunden!
        goto :error
    )
) else (
    echo [8/8] Installer-Erstellung uebersprungen (Inno Setup nicht gefunden)
)

echo.
echo ============================================================================
echo                         BUILD ERFOLGREICH!
echo ============================================================================
echo.
echo   Erstellte Dateien:
echo.
echo   Portable Version:
echo     dist\StitchAdmin\StitchAdmin.exe
echo.
if "%INNO_AVAILABLE%"=="1" (
    echo   Windows-Installer:
    echo     installer_output\StitchAdmin_2.0_Setup.exe
    echo.
)
echo   Naechste Schritte:
echo   1. Testen Sie die EXE: dist\StitchAdmin\StitchAdmin.exe
echo   2. Verteilen Sie den Installer an Kunden
echo.
echo ============================================================================
goto :end

:error
echo.
echo ============================================================================
echo                         BUILD FEHLGESCHLAGEN!
echo ============================================================================
echo.
echo   Bitte pruefen Sie die Fehlermeldungen oben.
echo   Haeufige Probleme:
echo   - Python nicht im PATH
echo   - Fehlende Dependencies
echo   - Syntax-Fehler im Code
echo.
pause
exit /b 1

:end
pause
exit /b 0
