#!/usr/bin/env python3
"""
StitchAdmin 2.0 - Erweiterte Migrations-Script
Erstellt von Hans Hahn - Alle Rechte vorbehalten

Kopiert alle relevanten Dateien vom alten ins neue Projekt mit detailliertem Logging
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

# Pfade
OLD_PATH = Path("C:/SoftwareEntwicklung/StitchAdmin")
NEW_PATH = Path("C:/SoftwareEntwicklung/StitchAdmin2.0")

# Log-Datei
log_file = NEW_PATH / "logs" / f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
log_file.parent.mkdir(exist_ok=True)

def log_message(message):
    """Schreibt Nachricht in Konsole und Log-Datei"""
    print(message)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(message + '\n')

def copy_file(source, target, description=""):
    """Kopiert eine Datei und erstellt Verzeichnisse falls nötig"""
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        msg = f"  ✓ {source.name}"
        if description:
            msg += f" - {description}"
        log_message(msg)
        return True
    except Exception as e:
        log_message(f"  ✗ {source.name}: {e}")
        return False

def copy_directory(source, target, description=""):
    """Kopiert ein ganzes Verzeichnis"""
    try:
        if not source.exists():
            log_message(f"  ⊘ {source.name}/ nicht gefunden, überspringe...")
            return False
            
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
        
        file_count = sum(1 for _ in target.rglob('*') if _.is_file())
        msg = f"  ✓ {source.name}/ ({file_count} Dateien)"
        if description:
            msg += f" - {description}"
        log_message(msg)
        return True
    except Exception as e:
        log_message(f"  ✗ {source.name}/: {e}")
        return False

def main():
    log_message("="*70)
    log_message("StitchAdmin 2.0 - Erweiterte Datei-Migration")
    log_message(f"Zeitpunkt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_message("="*70)
    log_message("")
    
    if not OLD_PATH.exists():
        log_message(f"FEHLER: Altes Verzeichnis nicht gefunden: {OLD_PATH}")
        return False
    
    success_count = 0
    total_count = 0
    
    # ========================================================================
    # 1. MODELS - Datenmodelle
    # ========================================================================
    log_message("=" * 70)
    log_message("SCHRITT 1: Models kopieren")
    log_message("=" * 70)
    
    models_files = [
        ("models.py", "Hauptmodelle (Customer, Article, Order, etc.)"),
        ("article_supplier.py", "Artikel-Lieferanten-Zuordnung"),
        ("article_variant.py", "Artikel-Varianten"),
        ("rechnungsmodul.py", "Rechnungs-/Kassenmodelle"),
        ("settings.py", "Einstellungen-Modell"),
        ("supplier_contact.py", "Lieferanten-Kontakte"),
        ("supplier_order_item.py", "Lieferanten-Bestellpositionen"),
        ("__init__.py", "Models Package Init"),
    ]
    
    for file, desc in models_files:
        source = OLD_PATH / "src" / "models" / file
        target = NEW_PATH / "src" / "models" / file
        if source.exists():
            total_count += 1
            if copy_file(source, target, desc):
                success_count += 1
    
    # Rechnungsmodul Models Unterordner
    source_dir = OLD_PATH / "src" / "models" / "rechnungsmodul"
    target_dir = NEW_PATH / "src" / "models" / "rechnungsmodul"
    if source_dir.exists():
        total_count += 1
        if copy_directory(source_dir, target_dir, "Kassenmodule"):
            success_count += 1
    
    # POS Models (falls vorhanden)
    source_dir = OLD_PATH / "src" / "models" / "pos"
    target_dir = NEW_PATH / "src" / "models" / "pos"
    if source_dir.exists():
        total_count += 1
        if copy_directory(source_dir, target_dir, "POS-System Modelle"):
            success_count += 1
    
    log_message("")
    
    # ========================================================================
    # 2. CONTROLLERS - Geschäftslogik
    # ========================================================================
    log_message("=" * 70)
    log_message("SCHRITT 2: Controllers kopieren")
    log_message("=" * 70)
    
    controller_files = [
        ("activity_controller_db.py", "Aktivitäten-Verwaltung"),
        ("api_controller.py", "REST API Endpunkte"),
        ("article_controller_db.py", "Artikel-Verwaltung"),
        ("auth_controller.py", "Authentifizierung"),
        ("backup_controller.py", "Backup-Funktionalität"),
        ("customer_controller_db.py", "Kunden-Verwaltung"),
        ("dashboard_controller.py", "Dashboard"),
        ("design_workflow_controller.py", "Design-Workflow"),
        ("file_browser_controller.py", "Datei-Browser"),
        ("machine_controller_db.py", "Maschinen-Verwaltung"),
        ("order_controller_db.py", "Auftrags-Verwaltung"),
        ("production_controller_db.py", "Produktions-Verwaltung"),
        ("security_controller.py", "Sicherheits-Features"),
        ("settings_advanced_controller.py", "Erweiterte Einstellungen"),
        ("settings_controller_unified.py", "Einstellungen-Verwaltung"),
        ("settings_controller_db.py", "Einstellungen-Datenbank"),
        ("shipping_controller_db.py", "Versand-Verwaltung"),
        ("supplier_controller_db.py", "Lieferanten-Verwaltung"),
        ("supplier_controller_db_extension.py", "Lieferanten-Erweiterungen"),
        ("thread_controller_db.py", "Garn-Verwaltung"),
        ("thread_online_controller_db.py", "Garn-Online-Suche"),
        ("thread_web_search_routes.py", "Garn-Web-Suche"),
        ("user_controller_db.py", "Benutzer-Verwaltung"),
        ("webshop_automation_routes.py", "Webshop-Automatisierung"),
        ("webshop_automation_routes_complete.py", "Webshop-Auto komplett"),
        ("__init__.py", "Controllers Package Init"),
    ]
    
    for file, desc in controller_files:
        source = OLD_PATH / "src" / "controllers" / file
        target = NEW_PATH / "src" / "controllers" / file
        if source.exists():
            total_count += 1
            if copy_file(source, target, desc):
                success_count += 1
    
    # Rechnungsmodul Controllers
    source_dir = OLD_PATH / "src" / "controllers" / "rechnungsmodul"
    target_dir = NEW_PATH / "src" / "controllers" / "rechnungsmodul"
    if source_dir.exists():
        total_count += 1
        if copy_directory(source_dir, target_dir, "Kassen-Controller"):
            success_count += 1
    
    # POS Controllers
    source_dir = OLD_PATH / "src" / "controllers" / "pos"
    target_dir = NEW_PATH / "src" / "controllers" / "pos"
    if source_dir.exists():
        total_count += 1
        if copy_directory(source_dir, target_dir, "POS-System Controller"):
            success_count += 1
    
    log_message("")
    
    # ========================================================================
    # 3. SERVICES - Business-Services
    # ========================================================================
    log_message("=" * 70)
    log_message("SCHRITT 3: Services kopieren")
    log_message("=" * 70)
    
    source_dir = OLD_PATH / "src" / "services"
    target_dir = NEW_PATH / "src" / "services"
    if source_dir.exists():
        total_count += 1
        if copy_directory(source_dir, target_dir, "Business-Services"):
            success_count += 1
    
    log_message("")
    
    # ========================================================================
    # 4. UTILS - Hilfsfunktionen
    # ========================================================================
    log_message("=" * 70)
    log_message("SCHRITT 4: Utils kopieren")
    log_message("=" * 70)
    
    source_dir = OLD_PATH / "src" / "utils"
    target_dir = NEW_PATH / "src" / "utils"
    if source_dir.exists():
        total_count += 1
        if copy_directory(source_dir, target_dir, "Hilfsfunktionen"):
            success_count += 1
    
    log_message("")
    
    # ========================================================================
    # 5. TEMPLATES - Jinja2 Templates
    # ========================================================================
    log_message("=" * 70)
    log_message("SCHRITT 5: Templates kopieren")
    log_message("=" * 70)
    
    source_dir = OLD_PATH / "src" / "templates"
    target_dir = NEW_PATH / "src" / "templates"
    if source_dir.exists():
        total_count += 1
        if copy_directory(source_dir, target_dir, "HTML-Templates"):
            success_count += 1
    
    log_message("")
    
    # ========================================================================
    # 6. STATIC - CSS/JS/Images
    # ========================================================================
    log_message("=" * 70)
    log_message("SCHRITT 6: Static Files kopieren")
    log_message("=" * 70)
    
    source_dir = OLD_PATH / "src" / "static"
    target_dir = NEW_PATH / "src" / "static"
    if source_dir.exists():
        total_count += 1
        if copy_directory(source_dir, target_dir, "CSS/JS/Images"):
            success_count += 1
    
    log_message("")
    
    # ========================================================================
    # 7. INSTANCE - Datenbank & Uploads
    # ========================================================================
    log_message("=" * 70)
    log_message("SCHRITT 7: Instance Daten kopieren")
    log_message("=" * 70)
    
    # Datenbank
    db_file = OLD_PATH / "instance" / "stitchadmin.db"
    if db_file.exists():
        target = NEW_PATH / "instance" / "stitchadmin.db"
        total_count += 1
        if copy_file(db_file, target, "SQLite Datenbank"):
            success_count += 1
            
            # Backup der Datenbank erstellen
            backup_target = NEW_PATH / "backups" / f"stitchadmin_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            backup_target.parent.mkdir(exist_ok=True)
            shutil.copy2(db_file, backup_target)
            log_message(f"  ℹ Backup erstellt: {backup_target.name}")
    
    # Uploads - nur wenn Dateien vorhanden
    upload_dirs = [
        ("designs", "Design-Dateien"),
        ("documents", "Dokumente"),
        ("images", "Bilder"),
    ]
    
    for dir_name, desc in upload_dirs:
        source_dir = OLD_PATH / "instance" / "uploads" / dir_name
        target_dir = NEW_PATH / "instance" / "uploads" / dir_name
        if source_dir.exists() and any(source_dir.iterdir()):
            total_count += 1
            if copy_directory(source_dir, target_dir, desc):
                success_count += 1
    
    log_message("")
    
    # ========================================================================
    # 8. KONFIGURATION & DOCS
    # ========================================================================
    log_message("=" * 70)
    log_message("SCHRITT 8: Konfiguration & Dokumentation")
    log_message("=" * 70)
    
    # .env Datei
    env_file = OLD_PATH / ".env"
    if env_file.exists():
        target = NEW_PATH / ".env"
        total_count += 1
        if copy_file(env_file, target, "Umgebungsvariablen"):
            success_count += 1
    
    # app.py
    app_file = OLD_PATH / "app.py"
    if app_file.exists():
        target = NEW_PATH / "app_old_reference.py"
        total_count += 1
        if copy_file(app_file, target, "Alte Haupt-App (Referenz)"):
            success_count += 1
    
    # Migrations-Script
    migration_file = OLD_PATH / "db_migration.py"
    if migration_file.exists():
        target = NEW_PATH / "scripts" / "db_migration.py"
        total_count += 1
        if copy_file(migration_file, target, "Datenbank-Migration"):
            success_count += 1
    
    # Dokumentation
    doc_files = [
        ("TODO_FAHRPLAN.md", "docs/TODO_FAHRPLAN_OLD.md", "Alter TODO-Plan"),
        ("STRUKTUR_ANALYSE_20251105.md", "docs/STRUKTUR_ANALYSE_20251105.md", "Struktur-Analyse"),
        ("README.md", "docs/README_OLD.md", "Alte README"),
    ]
    
    for src_file, tgt_file, desc in doc_files:
        source = OLD_PATH / src_file
        target = NEW_PATH / tgt_file
        if source.exists():
            total_count += 1
            if copy_file(source, target, desc):
                success_count += 1
    
    log_message("")
    
    # ========================================================================
    # ZUSAMMENFASSUNG
    # ========================================================================
    log_message("=" * 70)
    log_message(f"Migration abgeschlossen: {success_count}/{total_count} Operationen erfolgreich")
    log_message(f"Fehlerquote: {((total_count - success_count) / total_count * 100):.1f}%")
    log_message("=" * 70)
    log_message("")
    log_message("NÄCHSTE SCHRITTE:")
    log_message("-" * 70)
    log_message("1. Virtual Environment prüfen/erstellen:")
    log_message("   python -m venv .venv")
    log_message("")
    log_message("2. venv aktivieren:")
    log_message("   .venv\\Scripts\\activate")
    log_message("")
    log_message("3. Requirements installieren:")
    log_message("   pip install -r requirements.txt")
    log_message("")
    log_message("4. app.py überprüfen und anpassen")
    log_message("")
    log_message("5. Anwendung testen:")
    log_message("   python app.py")
    log_message("")
    log_message(f"Migrations-Log gespeichert: {log_file}")
    log_message("")
    
    return success_count == total_count

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
