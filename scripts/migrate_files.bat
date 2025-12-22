@echo off
REM StitchAdmin 2.0 - Datei-Migration Batch
REM Erstellt von Hans Hahn - Alle Rechte vorbehalten

echo ====================================
echo StitchAdmin 2.0 - Datei Migration
echo ====================================
echo.

set OLD_PATH=C:\SoftwareEntwicklung\StitchAdmin
set NEW_PATH=C:\SoftwareEntwicklung\StitchAdmin2.0

echo Schritt 1: Models kopieren...
echo.


REM Models Dateien
xcopy "%OLD_PATH%\src\models\models.py" "%NEW_PATH%\src\models\" /Y /Q
xcopy "%OLD_PATH%\src\models\article_supplier.py" "%NEW_PATH%\src\models\" /Y /Q
xcopy "%OLD_PATH%\src\models\article_variant.py" "%NEW_PATH%\src\models\" /Y /Q
xcopy "%OLD_PATH%\src\models\rechnungsmodul.py" "%NEW_PATH%\src\models\" /Y /Q
xcopy "%OLD_PATH%\src\models\settings.py" "%NEW_PATH%\src\models\" /Y /Q
xcopy "%OLD_PATH%\src\models\supplier_contact.py" "%NEW_PATH%\src\models\" /Y /Q
xcopy "%OLD_PATH%\src\models\supplier_order_item.py" "%NEW_PATH%\src\models\" /Y /Q

REM Rechnungsmodul Models
xcopy "%OLD_PATH%\src\models\rechnungsmodul\*.*" "%NEW_PATH%\src\models\rechnungsmodul\" /Y /Q /E

echo   [OK] Models kopiert
echo.

echo Schritt 2: Controllers kopieren...
echo.

REM Core Controllers (_db.py Versionen)
xcopy "%OLD_PATH%\src\controllers\activity_controller_db.py" "%NEW_PATH%\src\controllers\" /Y /Q
xcopy "%OLD_PATH%\src\controllers\api_controller.py" "%NEW_PATH%\src\controllers\" /Y /Q
xcopy "%OLD_PATH%\src\controllers\article_controller_db.py" "%NEW_PATH%\src\controllers\" /Y /Q
xcopy "%OLD_PATH%\src\controllers\customer_controller_db.py" "%NEW_PATH%\src\controllers\" /Y /Q
xcopy "%OLD_PATH%\src\controllers\design_workflow_controller.py" "%NEW_PATH%\src\controllers\" /Y /Q
xcopy "%OLD_PATH%\src\controllers\file_browser_controller.py" "%NEW_PATH%\src\controllers\" /Y /Q
xcopy "%OLD_PATH%\src\controllers\machine_controller_db.py" "%NEW_PATH%\src\controllers\" /Y /Q
xcopy "%OLD_PATH%\src\controllers\order_controller_db.py" "%NEW_PATH%\src\controllers\" /Y /Q
xcopy "%OLD_PATH%\src\controllers\production_controller_db.py" "%NEW_PATH%\src\controllers\" /Y /Q
xcopy "%OLD_PATH%\src\controllers\settings_controller_unified.py" "%NEW_PATH%\src\controllers\" /Y /Q
xcopy "%OLD_PATH%\src\controllers\shipping_controller_db.py" "%NEW_PATH%\src\controllers\" /Y /Q
xcopy "%OLD_PATH%\src\controllers\supplier_controller_db.py" "%NEW_PATH%\src\controllers\" /Y /Q
xcopy "%OLD_PATH%\src\controllers\thread_controller_db.py" "%NEW_PATH%\src\controllers\" /Y /Q
xcopy "%OLD_PATH%\src\controllers\user_controller_db.py" "%NEW_PATH%\src\controllers\" /Y /Q

REM Rechnungsmodul Controllers
xcopy "%OLD_PATH%\src\controllers\rechnungsmodul\*.*" "%NEW_PATH%\src\controllers\rechnungsmodul\" /Y /Q /E

echo   [OK] Controllers kopiert
echo.

echo Schritt 3: Services, Utils, Templates, Static kopieren...
echo.

REM Services
xcopy "%OLD_PATH%\src\services\*.*" "%NEW_PATH%\src\services\" /Y /Q /E /I

REM Utils
xcopy "%OLD_PATH%\src\utils\*.*" "%NEW_PATH%\src\utils\" /Y /Q /E /I

REM Templates
xcopy "%OLD_PATH%\src\templates\*.*" "%NEW_PATH%\src\templates\" /Y /Q /E /I

REM Static
xcopy "%OLD_PATH%\src\static\*.*" "%NEW_PATH%\src\static\" /Y /Q /E /I

echo   [OK] Services, Utils, Templates, Static kopiert
echo.

echo Schritt 4: Instance Daten kopieren...
echo.

REM Datenbank
if exist "%OLD_PATH%\instance\stitchadmin.db" (
    xcopy "%OLD_PATH%\instance\stitchadmin.db" "%NEW_PATH%\instance\" /Y /Q
    echo   [OK] Datenbank kopiert
)

REM Uploads
if exist "%OLD_PATH%\instance\uploads\designs" (
    xcopy "%OLD_PATH%\instance\uploads\designs\*.*" "%NEW_PATH%\instance\uploads\designs\" /Y /Q /E /I
    echo   [OK] Design-Dateien kopiert
)

if exist "%OLD_PATH%\instance\uploads\documents" (
    xcopy "%OLD_PATH%\instance\uploads\documents\*.*" "%NEW_PATH%\instance\uploads\documents\" /Y /Q /E /I
    echo   [OK] Dokumente kopiert
)

if exist "%OLD_PATH%\instance\uploads\images" (
    xcopy "%OLD_PATH%\instance\uploads\images\*.*" "%NEW_PATH%\instance\uploads\images\" /Y /Q /E /I
    echo   [OK] Bilder kopiert
)

echo.
echo Schritt 5: Hilfsdateien kopieren...
echo.

REM Scripts
if exist "%OLD_PATH%\db_migration.py" (
    xcopy "%OLD_PATH%\db_migration.py" "%NEW_PATH%\scripts\" /Y /Q
    echo   [OK] db_migration.py kopiert
)

REM Docs
if exist "%OLD_PATH%\TODO_FAHRPLAN.md" (
    xcopy "%OLD_PATH%\TODO_FAHRPLAN.md" "%NEW_PATH%\docs\" /Y /Q
)

if exist "%OLD_PATH%\README.md" (
    xcopy "%OLD_PATH%\README.md" "%NEW_PATH%\docs\README_OLD.md" /Y /Q
)

echo   [OK] Hilfsdateien kopiert
echo.

echo ====================================
echo Migration abgeschlossen!
echo ====================================
echo.
echo Naechste Schritte:
echo 1. Virtual Environment erstellen: python -m venv .venv
echo 2. venv aktivieren: .venv\Scripts\activate
echo 3. Requirements installieren: pip install -r requirements.txt
echo 4. Anwendung starten: python app.py
echo.
pause
