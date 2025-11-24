# -*- coding: utf-8 -*-
"""
Migration: Foto-Feld zu Orders Tabelle hinzufügen
=================================================
Fügt photos (TEXT) Spalte zur orders Tabelle hinzu

Erstellt von: Hans Hahn - Alle Rechte vorbehalten
"""

import sys
import os

# Pfad zum Projekt-Root hinzufügen
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from src.models import db
import sqlite3

def run_migration():
    """Führt Migration durch"""
    app = create_app()

    with app.app_context():
        db_path = app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', '')

        if not db_path:
            print("[ERROR] Datenbankpfad konnte nicht ermittelt werden")
            return False

        print(f"[INFO] Datenbank: {db_path}")

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Pruefen ob Spalte bereits existiert
            cursor.execute("PRAGMA table_info(orders)")
            columns = [column[1] for column in cursor.fetchall()]

            if 'photos' in columns:
                print("[OK] Spalte 'photos' existiert bereits")
                conn.close()
                return True

            # Spalte hinzufuegen
            print("[INFO] Fuege Spalte 'photos' hinzu...")
            cursor.execute("""
                ALTER TABLE orders
                ADD COLUMN photos TEXT
            """)

            conn.commit()
            conn.close()

            print("[SUCCESS] Migration erfolgreich!")
            print("  - Spalte 'photos' zu orders Tabelle hinzugefuegt")

            return True

        except sqlite3.OperationalError as e:
            print(f"[ERROR] SQL-Fehler: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] Fehler: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    print("=" * 60)
    print("Migration: Foto-Feld zu Orders")
    print("=" * 60)

    success = run_migration()

    if success:
        print("\n[SUCCESS] Migration abgeschlossen!")
    else:
        print("\n[ERROR] Migration fehlgeschlagen!")
        sys.exit(1)
