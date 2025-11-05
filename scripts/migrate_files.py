#!/usr/bin/env python3
"""
StitchAdmin 2.0 - Python-basiertes Migrations-Script
Erstellt von Hans Hahn - Alle Rechte vorbehalten

Kopiert alle relevanten Dateien vom alten ins neue Projekt
"""

import os
import shutil
from pathlib import Path

# Pfade
OLD_PATH = Path("C:/SoftwareEntwicklung/StitchAdmin")
NEW_PATH = Path("C:/SoftwareEntwicklung/StitchAdmin2.0")

def copy_file(source, target):
    """Kopiert eine Datei und erstellt Verzeichnisse falls nötig"""
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        print(f"  ✓ {source.name}")
        return True
    except Exception as e:
        print(f"  ✗ {source.name}: {e}")
        return False

def copy_directory(source, target):
    """Kopiert ein ganzes Verzeichnis"""
    try:
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
        print(f"  ✓ {source.name}/ (komplett)")
        return True
    except Exception as e:
        print(f"  ✗ {source.name}/: {e}")
        return False

def main():
    print("="*50)
    print("StitchAdmin 2.0 - Datei-Migration")
    print("="*50)
    print()
    
    if not OLD_PATH.exists():
        print(f"FEHLER: Altes Verzeichnis nicht gefunden: {OLD_PATH}")
        return False
    
    success_count = 0
    total_count = 0
    
    # 1. Models kopieren
    print("Schritt 1: Models kopieren...")
    models_files = [
        "models.py",
        "article_supplier.py",
        "article_variant.py",
        "rechnungsmodul.py",
        "settings.py",
        "supplier_contact.py",
        "supplier_order_item.py",
    ]
    
    for file in models_files:
        source = OLD_PATH / "src" / "models" / file
        target = NEW_PATH / "src" / "models" / file
        total_count += 1
        if copy_file(source, target):
            success_count += 1
    
    # Rechnungsmodul Models
    source_dir = OLD_PATH / "src" / "models" / "rechnungsmodul"
    target_dir = NEW_PATH / "src" / "models" / "rechnungsmodul"
    if source_dir.exists():
        total_count += 1
        if copy_directory(source_dir, target_dir):
            success_count += 1
    
    # POS Models (falls vorhanden)
    source_dir = OLD_PATH / "src" / "models" / "pos"
    target_dir = NEW_PATH / "src" / "models" / "pos"
    if source_dir.exists():
        total_count += 1
        if copy_directory(source_dir, target_dir):
            success_count += 1
    
    print()
    
    # 2. Controllers kopieren
    print("Schritt 2: Controllers kopieren...")
    controller_files = [
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
        "user_controller_db.py",
    ]
    
    for file in controller_files:
        source = OLD_PATH / "src" / "controllers" / file
        target = NEW_PATH / "src" / "controllers" / file
        total_count += 1
        if copy_file(source, target):
            success_count += 1
    
    # Rechnungsmodul Controllers
    source_dir = OLD_PATH / "src" / "controllers" / "rechnungsmodul"
    target_dir = NEW_PATH / "src" / "controllers" / "rechnungsmodul"
    if source_dir.exists():
        total_count += 1
        if copy_directory(source_dir, target_dir):
            success_count += 1
    
    # POS Controllers (falls vorhanden)
    source_dir = OLD_PATH / "src" / "controllers" / "pos"
    target_dir = NEW_PATH / "src" / "controllers" / "pos"
    if source_dir.exists():
        total_count += 1
        if copy_directory(source_dir, target_dir):
            success_count += 1
    
    print()
    
    # 3. Services, Utils, Templates, Static
    print("Schritt 3: Services, Utils, Templates, Static...")
    
    directories = [
        ("services", "services"),
        ("utils", "utils"),
        ("templates", "templates"),
        ("static", "static"),
    ]
    
    for src_name, tgt_name in directories:
        source_dir = OLD_PATH / "src" / src_name
        target_dir = NEW_PATH / "src" / tgt_name
        if source_dir.exists():
            total_count += 1
            if copy_directory(source_dir, target_dir):
                success_count += 1
    
    print()
    
    # 4. Instance Daten
    print("Schritt 4: Instance Daten...")
    
    # Datenbank
    db_file = OLD_PATH / "instance" / "stitchadmin.db"
    if db_file.exists():
        target = NEW_PATH / "instance" / "stitchadmin.db"
        total_count += 1
        if copy_file(db_file, target):
            success_count += 1
    
    # Uploads
    upload_dirs = ["designs", "documents", "images"]
    for dir_name in upload_dirs:
        source_dir = OLD_PATH / "instance" / "uploads" / dir_name
        target_dir = NEW_PATH / "instance" / "uploads" / dir_name
        if source_dir.exists() and list(source_dir.iterdir()):  # Nur wenn nicht leer
            total_count += 1
            if copy_directory(source_dir, target_dir):
                success_count += 1
    
    print()
    
    # 5. Hilfsdateien
    print("Schritt 5: Hilfsdateien...")
    
    # db_migration.py
    source = OLD_PATH / "db_migration.py"
    target = NEW_PATH / "scripts" / "db_migration.py"
    if source.exists():
        total_count += 1
        if copy_file(source, target):
            success_count += 1
    
    # TODO und Docs
    doc_files = [
        ("TODO_FAHRPLAN.md", "docs/TODO_FAHRPLAN_OLD.md"),
        ("STRUKTUR_ANALYSE_20251105.md", "docs/STRUKTUR_ANALYSE_20251105.md"),
        ("README.md", "docs/README_OLD.md"),
    ]
    
    for src_file, tgt_file in doc_files:
        source = OLD_PATH / src_file
        target = NEW_PATH / tgt_file
        if source.exists():
            total_count += 1
            if copy_file(source, target):
                success_count += 1
    
    print()
    print("="*50)
    print(f"Migration abgeschlossen: {success_count}/{total_count} erfolgreich")
    print("="*50)
    print()
    print("Nächste Schritte:")
    print("1. Virtual Environment erstellen: python -m venv .venv")
    print("2. venv aktivieren: .venv\\Scripts\\activate")
    print("3. Requirements installieren: pip install -r requirements.txt")
    print("4. Anwendung starten: python app.py")
    print()
    
    return success_count == total_count

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
