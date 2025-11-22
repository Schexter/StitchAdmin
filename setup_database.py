#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Datenbank-Setup Script
======================

Erstellt alle neuen Tabellen für:
- Nummernkreise
- Angebote & Lieferscheine
- Mahnwesen & Ratenzahlungen
- CRM & Aktivitäten
"""

import sqlite3
import os

DB_PATH = 'instance/stitchadmin.db'

def execute_sql_file(cursor, filename):
    """Führt SQL-Befehle aus einer Datei aus"""
    print(f"\n[*] Fuehre aus: {filename}")

    with open(filename, 'r', encoding='utf-8') as f:
        sql_script = f.read()

    # SQL-Befehle ausführen
    statements = sql_script.split(';')

    for i, statement in enumerate(statements, 1):
        statement = statement.strip()
        if statement and not statement.startswith('--'):
            try:
                cursor.execute(statement)
                if 'CREATE TABLE' in statement.upper():
                    table_name = statement.split('TABLE')[1].split('(')[0].strip()
                    if 'IF NOT EXISTS' in statement.upper():
                        table_name = table_name.replace('IF NOT EXISTS', '').strip()
                    print(f"  [OK] Tabelle: {table_name}")
            except sqlite3.Error as e:
                if 'duplicate column name' not in str(e).lower() and 'already exists' not in str(e).lower():
                    print(f"  [WARN] Warnung: {e}")

def main():
    """Hauptfunktion"""
    print("=" * 60)
    print("StitchAdmin 2.0 - Datenbank Setup")
    print("=" * 60)

    if not os.path.exists(DB_PATH):
        print(f"\n[FEHLER] Datenbank nicht gefunden: {DB_PATH}")
        print("Bitte erst die Anwendung starten, damit die Datenbank erstellt wird.")
        return

    # Verbindung zur Datenbank
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # SQL-Dateien in der richtigen Reihenfolge ausführen
    sql_files = [
        'create_nummernkreis_tables.sql',
        'create_workflow_tables.sql',
        'create_finanzmanagement_tables.sql',
        'create_crm_tables.sql'
    ]

    for sql_file in sql_files:
        if os.path.exists(sql_file):
            execute_sql_file(cursor, sql_file)
        else:
            print(f"[WARN] Datei nicht gefunden: {sql_file}")

    # Änderungen speichern
    conn.commit()

    # Uebersicht der Tabellen
    print("\n" + "=" * 60)
    print("Vorhandene Tabellen:")
    print("=" * 60)

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()

    for i, (table_name,) in enumerate(tables, 1):
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"{i:2}. {table_name:30} ({count} Einträge)")

    conn.close()

    print("\n[OK] Datenbank-Setup abgeschlossen!")
    print("=" * 60)

if __name__ == '__main__':
    main()
