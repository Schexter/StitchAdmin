#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration Script: Fügt die neuen Workflow- und Design-Freigabe Felder zur Order-Tabelle hinzu
Erstellt: 26.11.2025
"""

import sys
import os

# Projekt-Root zum Path hinzufügen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from src.models import db
from sqlalchemy import text

def migrate():
    """Führt die Migration durch"""
    app = create_app()

    with app.app_context():
        # Neue Spalten für die orders-Tabelle
        new_columns = [
            # Angebots-Felder
            ("is_offer", "BOOLEAN DEFAULT 0"),
            ("offer_valid_until", "DATE"),
            ("offer_sent_at", "DATETIME"),
            ("offer_accepted_at", "DATETIME"),
            ("offer_rejected_at", "DATETIME"),
            ("offer_rejection_reason", "TEXT"),

            # Design-Freigabe Felder
            ("design_approval_status", "VARCHAR(50)"),
            ("design_approval_token", "VARCHAR(100) UNIQUE"),
            ("design_approval_sent_at", "DATETIME"),
            ("design_approval_date", "DATETIME"),
            ("design_approval_signature", "TEXT"),
            ("design_approval_ip", "VARCHAR(50)"),
            ("design_approval_user_agent", "VARCHAR(500)"),
            ("design_approval_notes", "TEXT"),

            # Rechnungs-Verknüpfung
            ("invoice_id", "INTEGER REFERENCES rechnungen(id)"),
        ]

        print("=" * 60)
        print("Migration: Order Workflow & Design-Freigabe Felder")
        print("=" * 60)

        # Prüfe welche Spalten bereits existieren
        result = db.session.execute(text("PRAGMA table_info(orders)"))
        existing_columns = {row[1] for row in result.fetchall()}

        print(f"\nExistierende Spalten: {len(existing_columns)}")

        added = 0
        skipped = 0

        for column_name, column_def in new_columns:
            if column_name in existing_columns:
                print(f"  [SKIP] {column_name} - existiert bereits")
                skipped += 1
            else:
                try:
                    sql = f"ALTER TABLE orders ADD COLUMN {column_name} {column_def}"
                    db.session.execute(text(sql))
                    print(f"  [ADD]  {column_name} - hinzugefügt")
                    added += 1
                except Exception as e:
                    print(f"  [ERR]  {column_name} - Fehler: {e}")

        db.session.commit()

        print("\n" + "=" * 60)
        print(f"Migration abgeschlossen: {added} hinzugefügt, {skipped} übersprungen")
        print("=" * 60)

        # Setze Standard-Werte für bestehende Aufträge
        print("\nSetze Standard-Werte für bestehende Aufträge...")

        # Alle bestehenden Aufträge auf is_offer=False setzen (sind ja bereits Aufträge)
        db.session.execute(text("""
            UPDATE orders
            SET is_offer = 0
            WHERE is_offer IS NULL
        """))

        # Workflow-Status setzen wenn leer
        db.session.execute(text("""
            UPDATE orders
            SET workflow_status = 'confirmed'
            WHERE workflow_status IS NULL AND status != 'cancelled'
        """))

        db.session.commit()
        print("Standard-Werte gesetzt.")

        return True


if __name__ == '__main__':
    try:
        migrate()
        print("\nMigration erfolgreich!")
    except Exception as e:
        print(f"\nFehler bei Migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
