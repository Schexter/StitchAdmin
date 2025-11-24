# -*- coding: utf-8 -*-
"""
Fix: Entfernt production_id Foreign Key aus packing_lists Tabelle
SQLite unterstützt kein ALTER TABLE DROP FOREIGN KEY
Daher muss die Tabelle neu erstellt werden
"""

import sys
import os
import sqlite3
from datetime import datetime

# Füge Projekt-Root zum Path hinzu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import get_data_path

def fix_packing_list_fk():
    """Entfernt Foreign Key Constraint auf productions Tabelle"""
    print("=" * 70)
    print("  FIX: Packing List Foreign Key")
    print("=" * 70)
    print()

    # Hole Datenbank-Pfad
    data_dir = get_data_path()
    db_path = os.path.join(data_dir, 'instance', 'stitchadmin.db')

    print(f"[INFO] Datenbank: {db_path}")
    print()

    if not os.path.exists(db_path):
        print("[FEHLER] Datenbank-Datei nicht gefunden!")
        return False

    # Verbinde zur Datenbank
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Prüfe ob Tabelle existiert
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='packing_lists'")
        if not cursor.fetchone():
            print("[INFO] Tabelle packing_lists existiert nicht - kein Fix nötig")
            return True

        print("[1/3] Erstelle temporäre Tabelle ohne production_id FK...")

        # Erstelle temporäre Tabelle OHNE production_id Foreign Key
        cursor.execute("""
        CREATE TABLE packing_lists_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            packing_list_number VARCHAR(50) UNIQUE NOT NULL,

            -- Verknüpfungen
            order_id INTEGER,
            production_id INTEGER,
            customer_id INTEGER,

            -- Teillieferungen
            carton_number INTEGER DEFAULT 1,
            total_cartons INTEGER DEFAULT 1,
            is_partial_delivery BOOLEAN DEFAULT 0,

            -- Status
            status VARCHAR(20) DEFAULT 'ready' NOT NULL,

            -- Inhalt
            items TEXT,
            customer_notes TEXT,
            packing_notes TEXT,

            -- Gewicht & Maße
            total_weight FLOAT,
            package_length FLOAT,
            package_width FLOAT,
            package_height FLOAT,

            -- Qualitätskontrolle
            qc_performed BOOLEAN DEFAULT 0,
            qc_by INTEGER,
            qc_date DATETIME,
            qc_notes TEXT,
            qc_photos TEXT,

            -- Verpackung
            packed_by INTEGER,
            packed_at DATETIME,
            packed_confirmed BOOLEAN DEFAULT 0,

            -- Lagerbuchung
            inventory_booked BOOLEAN DEFAULT 0,
            inventory_booking_date DATETIME,

            -- Verknüpfungen
            delivery_note_id INTEGER,
            post_entry_id INTEGER,

            -- PDF
            pdf_path VARCHAR(500),

            -- Timestamps
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            created_by INTEGER,
            updated_at DATETIME,

            -- Foreign Keys (OHNE production_id!)
            FOREIGN KEY (order_id) REFERENCES orders (id),
            FOREIGN KEY (customer_id) REFERENCES customers (id),
            FOREIGN KEY (qc_by) REFERENCES users (id),
            FOREIGN KEY (packed_by) REFERENCES users (id),
            FOREIGN KEY (created_by) REFERENCES users (id),
            FOREIGN KEY (delivery_note_id) REFERENCES delivery_notes (id),
            FOREIGN KEY (post_entry_id) REFERENCES post_entries (id)
        )
        """)
        print("[OK] Temporäre Tabelle erstellt")

        print("[2/3] Kopiere Daten...")

        # Kopiere Daten
        cursor.execute("""
        INSERT INTO packing_lists_new
        SELECT * FROM packing_lists
        """)
        print(f"[OK] {cursor.rowcount} Zeilen kopiert")

        print("[3/3] Ersetze Tabellen...")

        # Lösche alte Tabelle
        cursor.execute("DROP TABLE packing_lists")

        # Benenne neue Tabelle um
        cursor.execute("ALTER TABLE packing_lists_new RENAME TO packing_lists")

        print("[OK] Tabellen ersetzt")

        # Commit
        conn.commit()

        print()
        print("=" * 70)
        print("  FIX ERFOLGREICH ABGESCHLOSSEN")
        print("=" * 70)
        print()
        print("Die production_id Foreign Key Constraint wurde entfernt.")
        print("production_id ist jetzt ein einfaches INTEGER Feld.")
        print()

        return True

    except Exception as e:
        print()
        print("=" * 70)
        print("  FIX FEHLGESCHLAGEN")
        print("=" * 70)
        print(f"Fehler: {e}")
        print()
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False

    finally:
        conn.close()


if __name__ == '__main__':
    print()
    print("Dieser Fix entfernt die Foreign Key Constraint auf die productions Tabelle.")
    print()
    response = input("Fix ausführen? (ja/nein): ")

    if response.lower() == 'ja':
        if fix_packing_list_fk():
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        print("Fix abgebrochen.")
        sys.exit(0)
