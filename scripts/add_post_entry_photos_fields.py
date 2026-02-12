#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration Script: PostEntry Photos & OCR Fields
================================================
Fuegt die Felder 'photos', 'ocr_text' und 'extracted_data' zur post_entries Tabelle hinzu

Erstellt von: Hans Hahn - Alle Rechte vorbehalten
"""

import sqlite3
import sys
from pathlib import Path

# Pfade
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / 'instance' / 'stitchadmin.db'


def check_column_exists(cursor, table_name, column_name):
    """Prueft ob eine Spalte bereits existiert"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def add_post_entry_photos_fields():
    """Fuegt photos, ocr_text und extracted_data Felder zur post_entries Tabelle hinzu"""

    print("\n" + "="*60)
    print("PostEntry Migration: Photos & OCR Fields")
    print("="*60)

    if not DB_PATH.exists():
        print(f"[ERROR] Datenbank nicht gefunden: {DB_PATH}")
        print("Bitte zuerst die Datenbank initialisieren!")
        sys.exit(1)

    print(f"[INFO] Datenbank gefunden: {DB_PATH}")

    # Verbindung zur Datenbank
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Pruefe ob post_entries Tabelle existiert
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='post_entries'")
        if not cursor.fetchone():
            print("[ERROR] post_entries Tabelle existiert nicht!")
            sys.exit(1)

        print("[OK] post_entries Tabelle gefunden")

        # 2. Pruefe ob Felder bereits existieren
        columns_to_add = {
            'photos': 'TEXT',
            'ocr_text': 'TEXT',
            'extracted_data': 'TEXT'
        }

        added_columns = []
        skipped_columns = []

        for column_name, column_type in columns_to_add.items():
            if check_column_exists(cursor, 'post_entries', column_name):
                print(f"[SKIP] Spalte '{column_name}' existiert bereits")
                skipped_columns.append(column_name)
            else:
                print(f"[ADD] Fuege Spalte '{column_name}' hinzu...")
                cursor.execute(f"ALTER TABLE post_entries ADD COLUMN {column_name} {column_type}")
                added_columns.append(column_name)
                print(f"[OK] Spalte '{column_name}' hinzugefuegt")

        # 3. Commit
        conn.commit()
        print("\n[SUCCESS] Migration erfolgreich abgeschlossen!")

        if added_columns:
            print(f"[INFO] Hinzugefuegte Spalten: {', '.join(added_columns)}")
        if skipped_columns:
            print(f"[INFO] Uebersprungene Spalten: {', '.join(skipped_columns)}")

        # 4. Pruefe Tabellen-Struktur
        cursor.execute("PRAGMA table_info(post_entries)")
        columns = cursor.fetchall()

        print("\n[INFO] Aktuelle post_entries Tabellen-Struktur:")
        print("-" * 60)
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")

        print("\n" + "="*60)
        print("[DONE] PostEntry ist bereit fuer Foto & OCR Funktionen!")
        print("="*60)

    except sqlite3.Error as e:
        print(f"\n[ERROR] Datenbankfehler: {e}")
        conn.rollback()
        sys.exit(1)

    finally:
        conn.close()


if __name__ == '__main__':
    add_post_entry_photos_fields()
