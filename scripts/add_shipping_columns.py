"""
Fügt neue Spalten zu post_entries Tabelle hinzu
"""

import sys
import os
import sqlite3

# Füge Projekt-Root zum Path hinzu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def migrate():
    """Fügt Spalten zur post_entries Tabelle hinzu"""
    print("[OK] Starte Spalten-Migration für post_entries")

    # Hole Datenbank-Pfad
    from app import get_data_path
    data_dir = get_data_path()
    db_path = os.path.join(data_dir, 'instance', 'stitchadmin.db')

    print(f"[OK] Datenbank: {db_path}")

    # Verbinde zur Datenbank
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Liste der neuen Spalten
    columns_to_add = [
        ('shipping_bulk_id', 'INTEGER'),
        ('expected_delivery_date', 'DATE'),
        ('email_notification_sent', 'BOOLEAN DEFAULT 0'),
        ('email_notification_date', 'DATETIME'),
        ('printed_at', 'DATETIME'),
        ('shipped_at', 'DATETIME'),
    ]

    try:
        # Prüfe welche Spalten bereits existieren
        cursor.execute("PRAGMA table_info(post_entries)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        print(f"[OK] Bestehende Spalten: {len(existing_columns)}")

        # Füge fehlende Spalten hinzu
        added = 0
        for column_name, column_type in columns_to_add:
            if column_name not in existing_columns:
                sql = f"ALTER TABLE post_entries ADD COLUMN {column_name} {column_type}"
                print(f"[OK] Füge Spalte hinzu: {column_name}")
                cursor.execute(sql)
                added += 1
            else:
                print(f"[SKIP] Spalte existiert bereits: {column_name}")

        conn.commit()
        print(f"\n[OK] {added} Spalten hinzugefügt")
        print("[OK] Migration erfolgreich!")
        return True

    except Exception as e:
        print(f"[FEHLER] Migration fehlgeschlagen: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    if migrate():
        print("\n" + "="*60)
        print("MIGRATION ERFOLGREICH ABGESCHLOSSEN")
        print("="*60)
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print("MIGRATION FEHLGESCHLAGEN")
        print("="*60)
        sys.exit(1)
