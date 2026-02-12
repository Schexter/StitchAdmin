#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration: Fehlende Spalten in design_orders Tabelle hinzufügen
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from src.models import db

app = create_app()

def migrate():
    """Fügt fehlende Spalten zur design_orders Tabelle hinzu"""

    # Spalten die hinzugefügt werden müssen
    columns_to_add = [
        ("quote_received_at", "DATETIME"),
        ("quote_price", "FLOAT"),
        ("quote_delivery_days", "INTEGER"),
        ("quote_notes", "TEXT"),
        ("quote_valid_until", "DATE"),
        ("quote_accepted_at", "DATETIME"),
        ("deposit_required", "BOOLEAN DEFAULT 0"),
        ("deposit_percent", "FLOAT"),
        ("deposit_amount", "FLOAT"),
        ("deposit_status", "VARCHAR(50)"),
        ("deposit_paid_at", "DATETIME"),
        ("ordered_at", "DATETIME"),
        ("expected_delivery", "DATE"),
        ("delivered_at", "DATETIME"),
        ("delivered_file_path", "VARCHAR(500)"),
        ("delivered_file_name", "VARCHAR(255)"),
        ("delivered_preview_path", "VARCHAR(500)"),
        ("review_status", "VARCHAR(50)"),
        ("review_date", "DATETIME"),
        ("review_notes", "TEXT"),
        ("revision_count", "INTEGER DEFAULT 0"),
        ("completed_at", "DATETIME"),
        ("final_design_id", "VARCHAR(50)"),
        ("total_price", "FLOAT"),
        ("payment_status", "VARCHAR(50)"),
        ("paid_at", "DATETIME"),
        ("order_pdf_path", "VARCHAR(500)"),
        ("order_pdf_generated_at", "DATETIME"),
        ("priority", "VARCHAR(20) DEFAULT 'normal'"),
        ("internal_notes", "TEXT"),
        ("communication_log", "TEXT"),
        ("updated_at", "DATETIME"),
        ("updated_by", "VARCHAR(80)"),
    ]

    with app.app_context():
        # Prüfen welche Spalten existieren
        result = db.session.execute(db.text("PRAGMA table_info(design_orders)"))
        existing_columns = {row[1] for row in result.fetchall()}

        print(f"Existierende Spalten: {len(existing_columns)}")

        added = 0
        for col_name, col_type in columns_to_add:
            if col_name not in existing_columns:
                try:
                    sql = f"ALTER TABLE design_orders ADD COLUMN {col_name} {col_type}"
                    db.session.execute(db.text(sql))
                    print(f"  [+] Spalte hinzugefügt: {col_name}")
                    added += 1
                except Exception as e:
                    print(f"  [!] Fehler bei {col_name}: {e}")
            else:
                print(f"  [=] Spalte existiert bereits: {col_name}")

        db.session.commit()
        print(f"\n{added} Spalten hinzugefügt.")

        # Auch designs Tabelle prüfen
        print("\n--- Prüfe designs Tabelle ---")
        design_columns = [
            ("is_approved", "BOOLEAN DEFAULT 0"),
            ("approved_at", "DATETIME"),
            ("approved_by", "VARCHAR(80)"),
            ("source", "VARCHAR(50)"),
            ("source_order_id", "VARCHAR(50)"),
            ("creation_cost", "FLOAT"),
        ]

        result = db.session.execute(db.text("PRAGMA table_info(designs)"))
        existing_design_cols = {row[1] for row in result.fetchall()}

        for col_name, col_type in design_columns:
            if col_name not in existing_design_cols:
                try:
                    sql = f"ALTER TABLE designs ADD COLUMN {col_name} {col_type}"
                    db.session.execute(db.text(sql))
                    print(f"  [+] Spalte hinzugefügt: {col_name}")
                except Exception as e:
                    print(f"  [!] Fehler bei {col_name}: {e}")
            else:
                print(f"  [=] Spalte existiert bereits: {col_name}")

        db.session.commit()

        # Auch todos Tabelle prüfen
        print("\n--- Prüfe todos Tabelle ---")
        todo_columns = [
            ("result_file_path", "VARCHAR(500)"),
            ("result_file_name", "VARCHAR(255)"),
            ("progress", "INTEGER DEFAULT 0"),
            ("document_path", "VARCHAR(500)"),
            ("document_name", "VARCHAR(255)"),
            ("design_type", "VARCHAR(50)"),
            ("design_width_mm", "FLOAT"),
            ("design_height_mm", "FLOAT"),
            ("max_stitch_count", "INTEGER"),
            ("max_colors", "INTEGER"),
            ("fabric_type", "VARCHAR(100)"),
            ("source_file_path", "VARCHAR(500)"),
            ("source_file_name", "VARCHAR(255)"),
            ("design_specs", "TEXT"),
        ]

        result = db.session.execute(db.text("PRAGMA table_info(todos)"))
        existing_todo_cols = {row[1] for row in result.fetchall()}

        for col_name, col_type in todo_columns:
            if col_name not in existing_todo_cols:
                try:
                    sql = f"ALTER TABLE todos ADD COLUMN {col_name} {col_type}"
                    db.session.execute(db.text(sql))
                    print(f"  [+] Spalte hinzugefügt: {col_name}")
                except Exception as e:
                    print(f"  [!] Fehler bei {col_name}: {e}")
            else:
                print(f"  [=] Spalte existiert bereits: {col_name}")

        db.session.commit()
        print("\nMigration abgeschlossen!")


if __name__ == '__main__':
    migrate()
