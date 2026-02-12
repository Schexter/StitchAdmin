# -*- coding: utf-8 -*-
"""
Migration: StorageSettings Tabelle erstellen
============================================
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import sqlite3
import os
from datetime import datetime

def migrate_storage_settings(db_path):
    """Erstellt die storage_settings Tabelle"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Prüfen ob Tabelle existiert
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='storage_settings'
    """)
    
    if cursor.fetchone():
        print("✓ storage_settings Tabelle existiert bereits")
        conn.close()
        return True
    
    # Tabelle erstellen
    cursor.execute("""
        CREATE TABLE storage_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Basispfade
            base_path VARCHAR(500) DEFAULT '',
            
            -- Dokument-Pfade
            angebote_path VARCHAR(200) DEFAULT 'Angebote',
            auftraege_path VARCHAR(200) DEFAULT 'Auftragsbestätigungen',
            lieferscheine_path VARCHAR(200) DEFAULT 'Lieferscheine',
            rechnungen_ausgang_path VARCHAR(200) DEFAULT 'Rechnungen\\Ausgang',
            rechnungen_eingang_path VARCHAR(200) DEFAULT 'Rechnungen\\Eingang',
            gutschriften_path VARCHAR(200) DEFAULT 'Gutschriften',
            mahnungen_path VARCHAR(200) DEFAULT 'Mahnungen',
            
            -- Design-Pfade
            designs_path VARCHAR(200) DEFAULT 'Designs',
            design_freigaben_path VARCHAR(200) DEFAULT 'Design-Freigaben',
            
            -- Sonstige Pfade
            backup_path VARCHAR(200) DEFAULT 'Backups',
            temp_path VARCHAR(200) DEFAULT 'Temp',
            import_path VARCHAR(200) DEFAULT 'Importe',
            export_path VARCHAR(200) DEFAULT 'Exporte',
            
            -- Ordnerstruktur-Optionen
            folder_structure VARCHAR(50) DEFAULT 'year_month',
            include_customer_in_filename BOOLEAN DEFAULT 1,
            include_date_in_filename BOOLEAN DEFAULT 1,
            
            -- Archivierung
            auto_archive BOOLEAN DEFAULT 0,
            archive_after_years INTEGER DEFAULT 10,
            archive_path VARCHAR(200) DEFAULT 'Archiv',
            
            -- Metadaten
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)
    
    # Default-Eintrag erstellen
    cursor.execute("""
        INSERT INTO storage_settings (base_path, folder_structure) 
        VALUES ('', 'year_month')
    """)
    
    conn.commit()
    conn.close()
    
    print("✓ storage_settings Tabelle erstellt")
    return True


def migrate_document_workflow_extensions(db_path):
    """Erweitert business_documents um PDF-Pfad-Felder"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Prüfen welche Spalten existieren
    cursor.execute("PRAGMA table_info(business_documents)")
    columns = [row[1] for row in cursor.fetchall()]
    
    new_columns = [
        ("pdf_pfad", "VARCHAR(500)"),
        ("pdf_erstellt_am", "TIMESTAMP"),
        ("xml_pfad", "VARCHAR(500)"),  # Für ZugPferd
        ("zugpferd_profil", "VARCHAR(50)"),  # BASIC, COMFORT, EXTENDED
    ]
    
    for col_name, col_type in new_columns:
        if col_name not in columns:
            try:
                cursor.execute(f"ALTER TABLE business_documents ADD COLUMN {col_name} {col_type}")
                print(f"✓ Spalte {col_name} hinzugefügt")
            except Exception as e:
                print(f"⚠ Spalte {col_name}: {e}")
    
    conn.commit()
    conn.close()
    
    return True


def run_migrations(db_path=None):
    """Führt alle Migrationen aus"""
    
    if db_path is None:
        # Standard-Pfad
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(base_dir, 'instance', 'stitchadmin.db')
    
    if not os.path.exists(db_path):
        print(f"⚠ Datenbank nicht gefunden: {db_path}")
        return False
    
    print(f"Migriere: {db_path}")
    print("-" * 50)
    
    migrate_storage_settings(db_path)
    migrate_document_workflow_extensions(db_path)
    
    print("-" * 50)
    print("✓ Migration abgeschlossen")
    
    return True


if __name__ == '__main__':
    run_migrations()
