# -*- coding: utf-8 -*-
"""
Migration: Workflow-Integration (Packlisten & Lieferscheine)
Fügt neue Tabellen und Spalten hinzu
"""

import sys
import os
import sqlite3
from datetime import datetime

# Füge Projekt-Root zum Path hinzu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def migrate():
    """Führt die Workflow-Migration durch"""
    print("=" * 70)
    print("  WORKFLOW-MIGRATION: Packlisten & Lieferscheine")
    print("=" * 70)
    print()

    # Hole Datenbank-Pfad
    from app import get_data_path
    data_dir = get_data_path()
    db_path = os.path.join(data_dir, 'instance', 'stitchadmin.db')

    print(f"[INFO] Datenbank: {db_path}")
    print()

    if not os.path.exists(db_path):
        print("[FEHLER] Datenbank-Datei nicht gefunden!")
        return False

    # Backup erstellen
    backup_path = db_path + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"[INFO] Erstelle Backup: {backup_path}")
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print("[OK] Backup erstellt")
    except Exception as e:
        print(f"[WARNUNG] Backup fehlgeschlagen: {e}")
        response = input("Trotzdem fortfahren? (ja/nein): ")
        if response.lower() != 'ja':
            return False

    print()

    # Verbinde zur Datenbank
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # ================================================================
        # 1. Neue Tabelle: packing_lists
        # ================================================================
        print("[1/6] Erstelle Tabelle: packing_lists")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS packing_lists (
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

            -- Foreign Keys
            FOREIGN KEY (order_id) REFERENCES orders (id),
            FOREIGN KEY (production_id) REFERENCES productions (id),
            FOREIGN KEY (customer_id) REFERENCES customers (id),
            FOREIGN KEY (qc_by) REFERENCES users (id),
            FOREIGN KEY (packed_by) REFERENCES users (id),
            FOREIGN KEY (created_by) REFERENCES users (id),
            FOREIGN KEY (delivery_note_id) REFERENCES delivery_notes (id),
            FOREIGN KEY (post_entry_id) REFERENCES post_entries (id)
        )
        """)
        print("[OK] Tabelle packing_lists erstellt")

        # ================================================================
        # 2. Neue Tabelle: delivery_notes
        # ================================================================
        print("[2/6] Erstelle Tabelle: delivery_notes")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS delivery_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            delivery_note_number VARCHAR(50) UNIQUE NOT NULL,

            -- Verknüpfungen
            order_id INTEGER,
            packing_list_id INTEGER,
            customer_id INTEGER,
            post_entry_id INTEGER,

            -- Datum
            delivery_date DATE DEFAULT CURRENT_DATE NOT NULL,

            -- Inhalt
            items TEXT,
            notes TEXT,

            -- Lieferart
            delivery_method VARCHAR(20) DEFAULT 'shipping',

            -- Unterschrift
            signature_type VARCHAR(20),
            signature_image VARCHAR(500),
            signature_name VARCHAR(200),
            signature_date DATETIME,
            signature_device VARCHAR(100),

            -- Fotos
            photos TEXT,

            -- Status
            status VARCHAR(20) DEFAULT 'ready' NOT NULL,

            -- PDFs
            pdf_path VARCHAR(500),
            pdf_with_signature_path VARCHAR(500),

            -- Timestamps
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            created_by INTEGER,
            updated_at DATETIME,

            -- Foreign Keys
            FOREIGN KEY (order_id) REFERENCES orders (id),
            FOREIGN KEY (packing_list_id) REFERENCES packing_lists (id),
            FOREIGN KEY (customer_id) REFERENCES customers (id),
            FOREIGN KEY (post_entry_id) REFERENCES post_entries (id),
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
        """)
        print("[OK] Tabelle delivery_notes erstellt")

        # ================================================================
        # 3. Erweitere Tabelle: orders
        # ================================================================
        print("[3/6] Erweitere Tabelle: orders")

        # Prüfe welche Spalten existieren
        cursor.execute("PRAGMA table_info(orders)")
        existing_order_columns = [row[1] for row in cursor.fetchall()]

        order_columns = [
            ('workflow_status', 'VARCHAR(50)'),
            ('packing_list_id', 'INTEGER'),
            ('delivery_note_id', 'INTEGER'),
            ('auto_create_packing_list', 'BOOLEAN DEFAULT 1'),
        ]

        for column_name, column_type in order_columns:
            if column_name not in existing_order_columns:
                sql = f"ALTER TABLE orders ADD COLUMN {column_name} {column_type}"
                cursor.execute(sql)
                print(f"  [OK] Spalte hinzugefügt: {column_name}")
            else:
                print(f"  [SKIP] Spalte existiert bereits: {column_name}")

        # ================================================================
        # 4. Erweitere Tabelle: productions (falls vorhanden)
        # ================================================================
        print("[4/6] Erweitere Tabelle: productions")

        # Prüfe ob Tabelle existiert
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='productions'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(productions)")
            existing_production_columns = [row[1] for row in cursor.fetchall()]

            production_columns = [
                ('packing_list_created', 'BOOLEAN DEFAULT 0'),
                ('packing_list_id', 'INTEGER'),
            ]

            for column_name, column_type in production_columns:
                if column_name not in existing_production_columns:
                    sql = f"ALTER TABLE productions ADD COLUMN {column_name} {column_type}"
                    cursor.execute(sql)
                    print(f"  [OK] Spalte hinzugefügt: {column_name}")
                else:
                    print(f"  [SKIP] Spalte existiert bereits: {column_name}")
        else:
            print("  [SKIP] Tabelle 'productions' existiert nicht")

        # ================================================================
        # 5. Erweitere Tabelle: post_entries
        # ================================================================
        print("[5/6] Erweitere Tabelle: post_entries")

        cursor.execute("PRAGMA table_info(post_entries)")
        existing_post_columns = [row[1] for row in cursor.fetchall()]

        post_columns = [
            ('packing_list_id', 'INTEGER'),
            ('delivery_note_id', 'INTEGER'),
            ('is_auto_created', 'BOOLEAN DEFAULT 0'),
        ]

        for column_name, column_type in post_columns:
            if column_name not in existing_post_columns:
                sql = f"ALTER TABLE post_entries ADD COLUMN {column_name} {column_type}"
                cursor.execute(sql)
                print(f"  [OK] Spalte hinzugefügt: {column_name}")
            else:
                print(f"  [SKIP] Spalte existiert bereits: {column_name}")

        # ================================================================
        # 6. Erweitere Tabelle: company_settings
        # ================================================================
        print("[6/6] Erweitere Tabelle: company_settings")

        cursor.execute("PRAGMA table_info(company_settings)")
        existing_company_columns = [row[1] for row in cursor.fetchall()]

        company_columns = [
            # Rechnungserstellung
            ('invoice_creation_mode', "VARCHAR(20) DEFAULT 'manual'"),
            ('invoice_creation_delay_days', 'INTEGER DEFAULT 0'),

            # Workflow-Automatisierung
            ('auto_create_packing_list', 'BOOLEAN DEFAULT 1'),
            ('auto_create_delivery_note', 'BOOLEAN DEFAULT 1'),
            ('auto_send_tracking_email', 'BOOLEAN DEFAULT 1'),

            # Qualitätskontrolle
            ('require_qc_before_packing', 'BOOLEAN DEFAULT 0'),
            ('require_qc_photos', 'BOOLEAN DEFAULT 0'),

            # Lagerbuchung
            ('auto_inventory_booking', 'BOOLEAN DEFAULT 1'),
        ]

        for column_name, column_type in company_columns:
            if column_name not in existing_company_columns:
                sql = f"ALTER TABLE company_settings ADD COLUMN {column_name} {column_type}"
                cursor.execute(sql)
                print(f"  [OK] Spalte hinzugefügt: {column_name}")
            else:
                print(f"  [SKIP] Spalte existiert bereits: {column_name}")

        # ================================================================
        # Commit
        # ================================================================
        conn.commit()

        print()
        print("=" * 70)
        print("  MIGRATION ERFOLGREICH ABGESCHLOSSEN")
        print("=" * 70)
        print()
        print("Neue Tabellen:")
        print("  - packing_lists")
        print("  - delivery_notes")
        print()
        print("Erweiterte Tabellen:")
        print("  - orders (4 neue Spalten)")
        print("  - productions (2 neue Spalten)")
        print("  - post_entries (3 neue Spalten)")
        print("  - company_settings (8 neue Spalten)")
        print()
        print(f"Backup: {backup_path}")
        print()

        return True

    except Exception as e:
        print()
        print("=" * 70)
        print("  MIGRATION FEHLGESCHLAGEN")
        print("=" * 70)
        print(f"Fehler: {e}")
        print()
        import traceback
        traceback.print_exc()
        print()
        print("Datenbank wird nicht verändert (Rollback)")
        print(f"Backup verfügbar: {backup_path}")
        conn.rollback()
        return False

    finally:
        conn.close()


if __name__ == '__main__':
    print()
    print("WARNUNG: Diese Migration ändert die Datenbank-Struktur!")
    print("Ein Backup wird automatisch erstellt.")
    print()
    response = input("Migration starten? (ja/nein): ")

    if response.lower() == 'ja':
        if migrate():
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        print("Migration abgebrochen.")
        sys.exit(0)
