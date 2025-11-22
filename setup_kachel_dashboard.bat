@echo off
chcp 65001 > nul
echo ========================================
echo   StitchAdmin 2.0 - Kachel-Dashboard 
echo   Automatische Installation
echo ========================================
echo.

REM Aktiviere Virtual Environment
echo [1/6] Aktiviere Virtual Environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [FEHLER] Virtual Environment nicht gefunden!
    echo Bitte zuerst Python Virtual Environment erstellen:
    echo python -m venv .venv
    pause
    exit /b 1
)
echo [OK] Virtual Environment aktiviert
echo.

REM Installiere Dependencies
echo [2/6] Installiere Dependencies...
pip install --quiet --upgrade cryptography
if errorlevel 1 (
    echo [FEHLER] Konnte cryptography nicht installieren!
    pause
    exit /b 1
)
echo [OK] Dependencies installiert
echo.

REM Backup von app.py erstellen
echo [3/6] Erstelle Backup von app.py...
copy /Y app.py app.py.backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2% > nul
echo [OK] Backup erstellt
echo.

REM Blueprint hinzufügen (mit PowerShell)
echo [4/6] Füge Documents-Blueprint hinzu...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"$content = Get-Content app.py -Raw; ^
$search = '    register_blueprint_safe(''src.controllers.auth_controller'', ''auth_bp'', ''Authentifizierung'')'; ^
$replace = $search + \"`r`n    `r`n    # Dokumente ^& Post`r`n    register_blueprint_safe('src.controllers.documents.documents_controller', 'documents_bp', 'Dokumente ^& Post')\"; ^
if ($content -notmatch 'documents_controller') { ^
    $content = $content -replace [regex]::Escape($search), $replace; ^
    $content | Set-Content app.py -Encoding UTF8; ^
    Write-Host '[OK] Blueprint hinzugefügt'; ^
} else { ^
    Write-Host '[INFO] Blueprint bereits vorhanden'; ^
}"
echo.

REM Datenbank-Tabellen anlegen
echo [5/6] Lege Datenbank-Tabellen an...
python -c "from app import create_app; app = create_app(); app.app_context().push(); from src.models.models import db; from src.models.document import Document; db.create_all(); print('[OK] Tabellen angelegt')"
if errorlevel 1 (
    echo [WARNUNG] Einige Tabellen konnten nicht angelegt werden
    echo          Das ist OK wenn sie bereits existieren
)
echo.

REM Zusammenfassung
echo [6/6] Installation abgeschlossen!
echo.
echo ========================================
echo   ERFOLG! Kachel-Dashboard aktiviert
echo ========================================
echo.
echo Neue Features:
echo   [+] Modernes Kachel-Dashboard (8 Module)
echo   [+] Dokumenten-Management (DMS)
echo   [+] Postbuch
echo   [+] E-Mail-Integration (Vorbereitet)
echo   [+] Verschlüsselte Credentials
echo   [+] GoBD-konforme Archivierung
echo.
echo Starte jetzt StitchAdmin mit:
echo   start.bat
echo.
echo Oder direkt:
echo   python app.py
echo.
pause
