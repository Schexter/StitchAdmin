@echo off
REM StitchAdmin 2.0 - Dependency Installation Script (Windows)
REM =============================================================
REM Installiert alle Python-Dependencies
REM System-Packages (Tesseract OCR) müssen manuell installiert werden
REM
REM Erstellt von: Hans Hahn - Alle Rechte vorbehalten

echo ======================================================
echo StitchAdmin 2.0 - Dependency Installation (Windows)
echo ======================================================
echo.

REM Wechsel zum Projekt-Verzeichnis
cd /d "%~dp0\.."

REM ==========================================
REM 1. PYTHON PRÜFEN
REM ==========================================
echo ======================================================
echo 1. Python-Installation pruefen
echo ======================================================

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python nicht gefunden!
    echo Bitte installieren Sie Python 3.11+ von https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [OK] %PYTHON_VERSION% gefunden
echo.

REM ==========================================
REM 2. TESSERACT OCR PRÜFEN
REM ==========================================
echo ======================================================
echo 2. Tesseract OCR pruefen
echo ======================================================

tesseract --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNUNG] Tesseract OCR nicht gefunden!
    echo.
    echo Tesseract muss manuell installiert werden:
    echo   1. Download: https://github.com/UB-Mannheim/tesseract/wiki
    echo   2. Installieren Sie "tesseract-ocr-w64-setup-5.x.x.exe"
    echo   3. Waehlen Sie bei der Installation "Deutsche Sprache" aus
    echo   4. Fuegen Sie Tesseract zum PATH hinzu
    echo.
    echo Installation trotzdem fortfahren? (Ohne OCR-Funktionen^)
    pause
) else (
    for /f "tokens=*" %%i in ('tesseract --version 2^>^&1 ^| findstr /C:"tesseract"') do set TESSERACT_VERSION=%%i
    echo [OK] !TESSERACT_VERSION! gefunden
)

echo.

REM ==========================================
REM 3. PIP UPGRADE
REM ==========================================
echo ======================================================
echo 3. pip aktualisieren
echo ======================================================

python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo [ERROR] pip upgrade fehlgeschlagen!
    pause
    exit /b 1
)

echo [OK] pip aktualisiert
echo.

REM ==========================================
REM 4. PYTHON-PACKAGES INSTALLIEREN
REM ==========================================
echo ======================================================
echo 4. Python-Packages installieren
echo ======================================================

if not exist "requirements.txt" (
    echo [ERROR] requirements.txt nicht gefunden!
    pause
    exit /b 1
)

echo [INFO] Installiere Packages aus requirements.txt...
echo.

python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Installation fehlgeschlagen!
    pause
    exit /b 1
)

echo.
echo [OK] Python-Packages installiert
echo.

REM ==========================================
REM 5. INSTALLATION VERIFIZIEREN
REM ==========================================
echo ======================================================
echo 5. Installation verifizieren
echo ======================================================

echo [CHECK] Python: %PYTHON_VERSION%

REM Kritische Packages prüfen
python -c "import flask; print('[CHECK] flask:', flask.__version__)" 2>nul || echo [ERROR] flask nicht installiert!
python -c "import pytesseract; print('[CHECK] pytesseract:', pytesseract.__version__)" 2>nul || echo [ERROR] pytesseract nicht installiert!
python -c "import PIL; print('[CHECK] Pillow:', PIL.__version__)" 2>nul || echo [ERROR] Pillow nicht installiert!
python -c "import reportlab; print('[CHECK] reportlab:', reportlab.Version)" 2>nul || echo [ERROR] reportlab nicht installiert!
python -c "import sqlalchemy; print('[CHECK] sqlalchemy:', sqlalchemy.__version__)" 2>nul || echo [ERROR] sqlalchemy nicht installiert!

echo.

REM ==========================================
REM 6. DATENBANK MIGRATIONEN
REM ==========================================
echo ======================================================
echo 6. Datenbank-Migrationen (optional)
echo ======================================================

echo Moechten Sie die Datenbank-Migrationen jetzt ausfuehren?
echo   - add_order_photos_field.py (Fotos fuer Auftraege)
echo   - add_post_entry_photos_fields.py (Fotos ^& OCR fuer PostEntry)
echo.
set /p MIGRATE="Migrationen ausfuehren? [y/N]: "

if /i "%MIGRATE%"=="y" (
    if exist "scripts\add_order_photos_field.py" (
        echo Fuehre Order-Migration aus...
        python scripts\add_order_photos_field.py
    )

    if exist "scripts\add_post_entry_photos_fields.py" (
        echo Fuehre PostEntry-Migration aus...
        python scripts\add_post_entry_photos_fields.py
    )
)

echo.

REM ==========================================
REM FERTIG!
REM ==========================================
echo ======================================================
echo Installation erfolgreich abgeschlossen!
echo ======================================================
echo.
echo Naechste Schritte:
echo   1. Konfiguration anpassen: copy .env.example .env
echo   2. Server starten: python app.py
echo   3. Im Browser oeffnen: http://localhost:5000
echo.
echo Fuer OCR-Funktionen:
echo   - Dokumente scannen: /documents/post/^<ID^>/scan
echo   - Auftrag-Fotos: /orders/^<ID^>/photos
echo.
echo Dokumentation:
echo   - docs\MOBILE_WORKFLOW_FEATURES.md
echo   - docs\POSTENTRY_OCR_FEATURES.md
echo.
echo ======================================================
pause
