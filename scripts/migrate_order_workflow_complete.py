#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration Script: Vollständiger Auftragswolkflow
- Neue Tabellen: order_designs, order_item_personalizations, order_design_name_lists
- Neue Felder in orders: payment_status, delivery_type, archived_at, etc.
Erstellt: 30.11.2025
"""

import sys
import os

# Projekt-Root zum Path hinzufügen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from src.models import db
from sqlalchemy import text


def check_table_exists(table_name):
    """Prüft ob eine Tabelle existiert"""
    result = db.session.execute(text(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
    ))
    return result.fetchone() is not None


def check_column_exists(table_name, column_name):
    """Prüft ob eine Spalte existiert"""
    result = db.session.execute(text(f"PRAGMA table_info({table_name})"))
    existing_columns = {row[1] for row in result.fetchall()}
    return column_name in existing_columns


def migrate():
    """Führt die Migration durch"""
    app = create_app()

    with app.app_context():
        print("=" * 70)
        print("Migration: Vollständiger Auftrags-Workflow")
        print("=" * 70)

        # =====================================================
        # 1. NEUE TABELLEN ERSTELLEN
        # =====================================================
        print("\n[1/3] Erstelle neue Tabellen...")

        # order_designs Tabelle
        if not check_table_exists('order_designs'):
            db.session.execute(text("""
                CREATE TABLE order_designs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id VARCHAR(50) NOT NULL REFERENCES orders(id),

                    -- Position auf dem Textil
                    position VARCHAR(50) NOT NULL,
                    position_label VARCHAR(100),

                    -- Design-Typ
                    design_type VARCHAR(20) DEFAULT 'stick',
                    is_personalized BOOLEAN DEFAULT 0,

                    -- Design-Datei
                    design_file_path VARCHAR(255),
                    design_thumbnail_path VARCHAR(255),
                    design_name VARCHAR(200),

                    -- Stickerei-Details
                    stitch_count INTEGER,
                    width_mm FLOAT,
                    height_mm FLOAT,
                    thread_colors TEXT,
                    estimated_time_minutes INTEGER,

                    -- Druck-Details
                    print_width_cm FLOAT,
                    print_height_cm FLOAT,
                    print_colors INTEGER,
                    print_method VARCHAR(50),

                    -- Freigabe-Status
                    approval_status VARCHAR(20) DEFAULT 'pending',
                    approved_at DATETIME,
                    approval_notes TEXT,

                    -- Preisberechnung
                    setup_price FLOAT DEFAULT 0,
                    price_per_piece FLOAT DEFAULT 0,

                    -- Sortierung
                    sort_order INTEGER DEFAULT 0,

                    -- Metadaten
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(80),
                    updated_at DATETIME
                )
            """))
            print("  [OK] Tabelle 'order_designs' erstellt")
        else:
            print("  [SKIP] Tabelle 'order_designs' existiert bereits")

        # order_item_personalizations Tabelle
        if not check_table_exists('order_item_personalizations'):
            db.session.execute(text("""
                CREATE TABLE order_item_personalizations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_item_id INTEGER NOT NULL REFERENCES order_items(id),
                    order_design_id INTEGER NOT NULL REFERENCES order_designs(id),

                    -- Personalisierungs-Text
                    text_line_1 VARCHAR(100),
                    text_line_2 VARCHAR(100),
                    text_line_3 VARCHAR(100),

                    -- Zusätzliche Optionen
                    font_name VARCHAR(100),
                    custom_color VARCHAR(50),
                    custom_design_file VARCHAR(255),

                    -- Sortierung
                    sequence_number INTEGER,

                    -- Produktions-Tracking
                    is_produced BOOLEAN DEFAULT 0,
                    produced_at DATETIME,
                    produced_by VARCHAR(80),

                    -- QM-Tracking
                    qm_checked BOOLEAN DEFAULT 0,
                    qm_notes TEXT,

                    -- Metadaten
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME
                )
            """))
            print("  [OK] Tabelle 'order_item_personalizations' erstellt")
        else:
            print("  [SKIP] Tabelle 'order_item_personalizations' existiert bereits")

        # order_design_name_lists Tabelle (für Sammeldesigns)
        if not check_table_exists('order_design_name_lists'):
            db.session.execute(text("""
                CREATE TABLE order_design_name_lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_design_id INTEGER NOT NULL REFERENCES order_designs(id),

                    -- Name/Text
                    name VARCHAR(100) NOT NULL,
                    subtitle VARCHAR(100),

                    -- Sortierung
                    sort_order INTEGER DEFAULT 0,

                    -- Metadaten
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("  [OK] Tabelle 'order_design_name_lists' erstellt")
        else:
            print("  [SKIP] Tabelle 'order_design_name_lists' existiert bereits")

        db.session.commit()

        # =====================================================
        # 2. NEUE SPALTEN ZU orders HINZUFÜGEN
        # =====================================================
        print("\n[2/3] Erweitere orders-Tabelle...")

        new_order_columns = [
            # Zahlungs-Status
            ("payment_status", "VARCHAR(20) DEFAULT 'pending'"),
            ("deposit_paid_at", "DATETIME"),
            ("deposit_payment_method", "VARCHAR(50)"),
            ("deposit_transaction_id", "VARCHAR(100)"),
            ("final_payment_at", "DATETIME"),
            ("final_payment_method", "VARCHAR(50)"),

            # Lieferart
            ("delivery_type", "VARCHAR(20) DEFAULT 'pickup'"),
            ("pickup_confirmed_at", "DATETIME"),
            ("pickup_signature", "TEXT"),
            ("pickup_signature_name", "VARCHAR(100)"),

            # Archivierung
            ("archived_at", "DATETIME"),
            ("archived_by", "VARCHAR(80)"),
            ("archive_reason", "VARCHAR(100)"),
        ]

        added = 0
        skipped = 0

        for column_name, column_def in new_order_columns:
            if check_column_exists('orders', column_name):
                print(f"  [SKIP] {column_name} - existiert bereits")
                skipped += 1
            else:
                try:
                    sql = f"ALTER TABLE orders ADD COLUMN {column_name} {column_def}"
                    db.session.execute(text(sql))
                    print(f"  [ADD]  {column_name}")
                    added += 1
                except Exception as e:
                    print(f"  [ERR]  {column_name} - {e}")

        db.session.commit()
        print(f"\n  Ergebnis: {added} hinzugefügt, {skipped} übersprungen")

        # =====================================================
        # 3. INDIZES ERSTELLEN
        # =====================================================
        print("\n[3/3] Erstelle Indizes...")

        indices = [
            ("idx_order_designs_order_id", "order_designs", "order_id"),
            ("idx_order_designs_position", "order_designs", "position"),
            ("idx_order_item_personalizations_item_id", "order_item_personalizations", "order_item_id"),
            ("idx_order_item_personalizations_design_id", "order_item_personalizations", "order_design_id"),
            ("idx_order_design_name_lists_design_id", "order_design_name_lists", "order_design_id"),
            ("idx_orders_payment_status", "orders", "payment_status"),
            ("idx_orders_archived_at", "orders", "archived_at"),
            ("idx_orders_delivery_type", "orders", "delivery_type"),
        ]

        for idx_name, table_name, column_name in indices:
            try:
                db.session.execute(text(
                    f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name}({column_name})"
                ))
                print(f"  [OK] Index {idx_name}")
            except Exception as e:
                print(f"  [SKIP] Index {idx_name} - {e}")

        db.session.commit()

        # =====================================================
        # 4. STANDARD-WERTE SETZEN
        # =====================================================
        print("\n[4/4] Setze Standard-Werte für bestehende Aufträge...")

        # Payment-Status auf 'pending' setzen wo NULL
        db.session.execute(text("""
            UPDATE orders
            SET payment_status = 'pending'
            WHERE payment_status IS NULL
        """))

        # Delivery-Type auf 'pickup' setzen wo NULL
        db.session.execute(text("""
            UPDATE orders
            SET delivery_type = 'pickup'
            WHERE delivery_type IS NULL
        """))

        db.session.commit()
        print("  [OK] Standard-Werte gesetzt")

        print("\n" + "=" * 70)
        print("Migration erfolgreich abgeschlossen!")
        print("=" * 70)

        # Zusammenfassung
        print("\nNeue Tabellen:")
        print("  - order_designs (Multi-Position-Design)")
        print("  - order_item_personalizations (Personalisierung pro Stück)")
        print("  - order_design_name_lists (Sammeldesign-Namen)")

        print("\nNeue Felder in 'orders':")
        print("  - payment_status, deposit_paid_at, deposit_payment_method, ...")
        print("  - delivery_type, pickup_confirmed_at, pickup_signature, ...")
        print("  - archived_at, archived_by, archive_reason")

        return True


if __name__ == '__main__':
    try:
        migrate()
    except Exception as e:
        print(f"\nFehler bei Migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
