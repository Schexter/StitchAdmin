# StitchAdmin 2.0 - Migration von alter Struktur
# Erstellt von Hans Hahn - Alle Rechte vorbehalten
# Datum: 2025-11-05

$ErrorActionPreference = "Stop"

$OLD_PATH = "C:\SoftwareEntwicklung\StitchAdmin"
$NEW_PATH = "C:\SoftwareEntwicklung\StitchAdmin2.0"

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "StitchAdmin 2.0 - Datei Migration" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Prüfe ob Quell-Verzeichnis existiert
if (-not (Test-Path $OLD_PATH)) {
    Write-Host "FEHLER: Altes Verzeichnis nicht gefunden: $OLD_PATH" -ForegroundColor Red
    exit 1
}

Write-Host "Schritt 1: Basis-Konfigurationsdateien kopieren..." -ForegroundColor Yellow

# .env Datei
if (Test-Path "$OLD_PATH\.env") {
    Copy-Item "$OLD_PATH\.env" "$NEW_PATH\.env" -Force
    Write-Host "  ✓ .env kopiert" -ForegroundColor Green
}

# requirements
if (Test-Path "$OLD_PATH\requirements_stable.txt") {
    Copy-Item "$OLD_PATH\requirements_stable.txt" "$NEW_PATH\requirements.txt" -Force
    Write-Host "  ✓ requirements.txt kopiert" -ForegroundColor Green
}

# README.md
if (Test-Path "$OLD_PATH\README.md") {
    Copy-Item "$OLD_PATH\README.md" "$NEW_PATH\docs\README_OLD.md" -Force
    Write-Host "  ✓ README.md nach docs/ kopiert" -ForegroundColor Green
}

Write-Host ""
Write-Host "Schritt 2: Models kopieren..." -ForegroundColor Yellow

# Erstelle models Unterverzeichnisse
$modelDirs = @("rechnungsmodul")
foreach ($dir in $modelDirs) {
    $targetDir = "$NEW_PATH\src\models\$dir"
    if (-not (Test-Path $targetDir)) {
        New-Item -Path $targetDir -ItemType Directory -Force | Out-Null
    }
}

# Kopiere Models
$modelFiles = @(
    "__init__.py",
    "models.py",
    "article_supplier.py",
    "article_variant.py",
    "rechnungsmodul.py",
    "settings.py",
    "supplier_contact.py",
    "supplier_order_item.py"
)

foreach ($file in $modelFiles) {
    $source = "$OLD_PATH\src\models\$file"
    $target = "$NEW_PATH\src\models\$file"
    if (Test-Path $source) {
        Copy-Item $source $target -Force
        Write-Host "  ✓ $file kopiert" -ForegroundColor Green
    }
}

# Kopiere Rechnungsmodul Models
if (Test-Path "$OLD_PATH\src\models\rechnungsmodul") {
    Copy-Item "$OLD_PATH\src\models\rechnungsmodul\*" "$NEW_PATH\src\models\rechnungsmodul\" -Force -Recurse
    Write-Host "  ✓ Rechnungsmodul Models kopiert" -ForegroundColor Green
}

Write-Host ""
Write-Host "Schritt 3: Controllers kopieren..." -ForegroundColor Yellow

# Erstelle controller Unterverzeichnisse
$controllerDirs = @("rechnungsmodul")
foreach ($dir in $controllerDirs) {
    $targetDir = "$NEW_PATH\src\controllers\$dir"
    if (-not (Test-Path $targetDir)) {
        New-Item -Path $targetDir -ItemType Directory -Force | Out-Null
    }
}

# Kopiere alle _db.py Controller (die aktuellen, funktionierenden)
$controllerFiles = @(
    "__init__.py",
    "activity_controller_db.py",
    "api_controller.py",
    "article_controller_db.py",
    "customer_controller_db.py",
    "design_workflow_controller.py",
    "file_browser_controller.py",
    "machine_controller_db.py",
    "order_controller_db.py",
    "production_controller_db.py",
    "settings_controller_unified.py",
    "shipping_controller_db.py",
    "supplier_controller_db.py",
    "thread_controller_db.py",
    "thread_online_controller_db.py",
    "user_controller_db.py"
)

foreach ($file in $controllerFiles) {
    $source = "$OLD_PATH\src\controllers\$file"
    $target = "$NEW_PATH\src\controllers\$file"
    if (Test-Path $source) {
        Copy-Item $source $target -Force
        Write-Host "  ✓ $file kopiert" -ForegroundColor Green
    }
}

# Kopiere Rechnungsmodul Controllers
if (Test-Path "$OLD_PATH\src\controllers\rechnungsmodul") {
    Copy-Item "$OLD_PATH\src\controllers\rechnungsmodul\*" "$NEW_PATH\src\controllers\rechnungsmodul\" -Force -Recurse
    Write-Host "  ✓ Rechnungsmodul Controllers kopiert" -ForegroundColor Green
}

Write-Host ""
Write-Host "Schritt 4: Services kopieren..." -ForegroundColor Yellow

if (Test-Path "$OLD_PATH\src\services") {
    Copy-Item "$OLD_PATH\src\services\*" "$NEW_PATH\src\services\" -Force -Recurse
    Write-Host "  ✓ Services komplett kopiert" -ForegroundColor Green
}

Write-Host ""
Write-Host "Schritt 5: Utils kopieren..." -ForegroundColor Yellow

if (Test-Path "$OLD_PATH\src\utils") {
    Copy-Item "$OLD_PATH\src\utils\*" "$NEW_PATH\src\utils\" -Force -Recurse
    Write-Host "  ✓ Utils komplett kopiert" -ForegroundColor Green
}

Write-Host ""
Write-Host "Schritt 6: Templates kopieren..." -ForegroundColor Yellow

if (Test-Path "$OLD_PATH\src\templates") {
    Copy-Item "$OLD_PATH\src\templates\*" "$NEW_PATH\src\templates\" -Force -Recurse
    Write-Host "  ✓ Templates komplett kopiert" -ForegroundColor Green
}

Write-Host ""
Write-Host "Schritt 7: Static Files kopieren..." -ForegroundColor Yellow

if (Test-Path "$OLD_PATH\src\static") {
    Copy-Item "$OLD_PATH\src\static\*" "$NEW_PATH\src\static\" -Force -Recurse
    Write-Host "  ✓ Static Files komplett kopiert" -ForegroundColor Green
}

Write-Host ""
Write-Host "Schritt 8: Instance Daten kopieren..." -ForegroundColor Yellow

# Kopiere Datenbank
if (Test-Path "$OLD_PATH\instance\stitchadmin.db") {
    Copy-Item "$OLD_PATH\instance\stitchadmin.db" "$NEW_PATH\instance\stitchadmin.db" -Force
    Write-Host "  ✓ Datenbank kopiert" -ForegroundColor Green
}

# Kopiere Uploads/Designs
if (Test-Path "$OLD_PATH\instance\uploads\designs") {
    Copy-Item "$OLD_PATH\instance\uploads\designs\*" "$NEW_PATH\instance\uploads\designs\" -Force -Recurse
    Write-Host "  ✓ Design-Dateien kopiert" -ForegroundColor Green
}

# Kopiere Uploads/Documents
if (Test-Path "$OLD_PATH\instance\uploads\documents") {
    Copy-Item "$OLD_PATH\instance\uploads\documents\*" "$NEW_PATH\instance\uploads\documents\" -Force -Recurse
    Write-Host "  ✓ Dokumente kopiert" -ForegroundColor Green
}

# Kopiere Uploads/Images
if (Test-Path "$OLD_PATH\instance\uploads\images") {
    Copy-Item "$OLD_PATH\instance\uploads\images\*" "$NEW_PATH\instance\uploads\images\" -Force -Recurse
    Write-Host "  ✓ Bilder kopiert" -ForegroundColor Green
}

Write-Host ""
Write-Host "Schritt 9: Hilfsdateien kopieren..." -ForegroundColor Yellow

# Kopiere wichtige Migrations- und Hilfsdateien
$utilFiles = @(
    "db_migration.py"
)

foreach ($file in $utilFiles) {
    $source = "$OLD_PATH\$file"
    $target = "$NEW_PATH\scripts\$file"
    if (Test-Path $source) {
        Copy-Item $source $target -Force
        Write-Host "  ✓ $file nach scripts/ kopiert" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Schritt 10: Dokumentation kopieren..." -ForegroundColor Yellow

# Kopiere wichtige Dokumentationsdateien
$docFiles = @(
    "TODO_FAHRPLAN.md",
    "STRUKTUR_ANALYSE_20251105.md"
)

foreach ($file in $docFiles) {
    $source = "$OLD_PATH\$file"
    $target = "$NEW_PATH\docs\$file"
    if (Test-Path $source) {
        Copy-Item $source $target -Force
        Write-Host "  ✓ $file nach docs/ kopiert" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "==================================" -ForegroundColor Green
Write-Host "Migration erfolgreich abgeschlossen!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green
Write-Host ""
Write-Host "Nächste Schritte:" -ForegroundColor Cyan
Write-Host "1. Erstelle neue app.py in $NEW_PATH" -ForegroundColor White
Write-Host "2. Erstelle Virtual Environment" -ForegroundColor White
Write-Host "3. Installiere requirements: pip install -r requirements.txt" -ForegroundColor White
Write-Host "4. Teste die Anwendung" -ForegroundColor White
Write-Host ""
