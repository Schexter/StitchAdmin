#!/usr/bin/env python3
"""
Migriert alle Daten von SQLite nach PostgreSQL
- Konvertiert SQLite-Typen (Boolean als 0/1) korrekt
- Filtert Spalten die in PG nicht existieren
- Deaktiviert FK-Trigger pro Tabelle (kein Superuser noetig)
- Verwendet SAVEPOINT pro Zeile um Transaktionsfehler abzufangen

Verwendung: python3 migrate_to_postgres.py
"""
import sqlite3
import sys
import os

sys.path.insert(0, "/opt/stitchadmin/app")
os.chdir("/opt/stitchadmin/app")

PG_URI = "postgresql://stitchadmin:7887fbf399dd233b5d345b7126877c09@localhost/stitchadmin"
SQLITE_PATH = "/opt/stitchadmin/data/instance/stitchadmin.db"

os.environ["DATABASE_URL"] = PG_URI

from app import create_app
app = create_app()

with app.app_context():
    from src.models.models import db
    from sqlalchemy import text, inspect

    print(f"[INFO] Engine: {db.engine.url}")

    # Tabellen in PostgreSQL erstellen
    db.create_all()
    print("[OK] PostgreSQL-Tabellen erstellt")

    # PostgreSQL-Schema analysieren
    inspector = inspect(db.engine)
    pg_tables = inspector.get_table_names()
    print(f"[INFO] {len(pg_tables)} PostgreSQL-Tabellen vorhanden")

    # Boolean-Spalten und vorhandene Spalten pro Tabelle ermitteln
    bool_columns = {}
    pg_table_columns = {}
    for tbl in pg_tables:
        cols = inspector.get_columns(tbl)
        bools = set()
        col_names = set()
        for col in cols:
            col_names.add(col['name'])
            if str(col['type']).upper() == 'BOOLEAN':
                bools.add(col['name'])
        if bools:
            bool_columns[tbl] = bools
        pg_table_columns[tbl] = col_names

    # SQLite-Verbindung
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    cur = sqlite_conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    sqlite_tables = [r[0] for r in cur.fetchall()]
    print(f"[INFO] {len(sqlite_tables)} SQLite-Tabellen gefunden")

    migrated = 0
    skipped = 0
    errors = 0

    # EINE Connection fuer alles
    with db.engine.connect() as conn:
        # FK-Trigger pro Tabelle deaktivieren (braucht nur Table-Owner, kein Superuser)
        for tbl in pg_tables:
            try:
                conn.execute(text(f'ALTER TABLE "{tbl}" DISABLE TRIGGER ALL'))
            except Exception:
                pass
        print("[INFO] FK-Trigger fuer alle Tabellen deaktiviert")

        for table in sqlite_tables:
            if table not in pg_tables:
                print(f"[SKIP] {table} - nicht in PostgreSQL")
                skipped += 1
                continue

            try:
                cur.execute(f'SELECT * FROM [{table}]')
                rows = cur.fetchall()

                if not rows:
                    print(f"[LEER] {table}")
                    continue

                sqlite_columns = [d[0] for d in cur.description]
                table_bools = bool_columns.get(table, set())
                pg_cols = pg_table_columns.get(table, set())

                # Nur Spalten die in PG existieren
                valid_columns = [c for c in sqlite_columns if c in pg_cols]
                skipped_cols = [c for c in sqlite_columns if c not in pg_cols]

                if skipped_cols:
                    print(f"  [INFO] {table}: Spalten uebersprungen: {', '.join(skipped_cols)}")

                if not valid_columns:
                    print(f"[SKIP] {table} - keine gemeinsamen Spalten")
                    skipped += 1
                    continue

                # Bestehende Daten loeschen
                conn.execute(text(f'DELETE FROM "{table}"'))

                # SQL vorbereiten
                cols_str = ", ".join([f'"{c}"' for c in valid_columns])
                placeholders = ", ".join([f":{c}" for c in valid_columns])
                sql = f'INSERT INTO "{table}" ({cols_str}) VALUES ({placeholders})'

                inserted = 0
                first_error = None

                for row in rows:
                    values = {}
                    for i, col in enumerate(sqlite_columns):
                        if col not in pg_cols:
                            continue
                        val = row[i]
                        # SQLite Boolean (0/1) -> Python bool
                        if col in table_bools and val is not None:
                            val = bool(val)
                        values[col] = val

                    try:
                        # SAVEPOINT pro Zeile: bei Fehler kann nur diese Zeile
                        # zurueckgerollt werden, ohne die ganze Transaktion abzubrechen
                        conn.execute(text("SAVEPOINT row_sp"))
                        conn.execute(text(sql), values)
                        conn.execute(text("RELEASE SAVEPOINT row_sp"))
                        inserted += 1
                    except Exception as row_err:
                        conn.execute(text("ROLLBACK TO SAVEPOINT row_sp"))
                        if first_error is None:
                            first_error = str(row_err).split('\n')[0]

                # Auto-Increment Sequenz aktualisieren (nur fuer Integer-PKs)
                try:
                    seq_sql = f"""
                        SELECT setval(pg_get_serial_sequence('"{table}"', 'id'),
                               COALESCE((SELECT MAX(id) FROM "{table}"), 1))
                    """
                    conn.execute(text("SAVEPOINT seq_sp"))
                    conn.execute(text(seq_sql))
                    conn.execute(text("RELEASE SAVEPOINT seq_sp"))
                except Exception:
                    try:
                        conn.execute(text("ROLLBACK TO SAVEPOINT seq_sp"))
                    except Exception:
                        pass

                if inserted == len(rows):
                    print(f"[OK] {table}: {inserted}/{len(rows)} Zeilen migriert")
                elif inserted > 0:
                    print(f"[TEIL] {table}: {inserted}/{len(rows)} Zeilen migriert")
                    if first_error:
                        print(f"  -> Erster Fehler: {first_error}")
                else:
                    print(f"[FEHLER] {table}: 0/{len(rows)} Zeilen - {first_error}")
                    errors += 1
                    continue

                migrated += 1

            except Exception as e:
                print(f"[FEHLER] {table}: {str(e).split(chr(10))[0]}")
                errors += 1

        # FK-Trigger wieder aktivieren
        for tbl in pg_tables:
            try:
                conn.execute(text(f'ALTER TABLE "{tbl}" ENABLE TRIGGER ALL'))
            except Exception:
                pass
        print("[INFO] FK-Trigger reaktiviert")

        # Alles committen
        conn.commit()
        print("[OK] Alle Daten committed")

    sqlite_conn.close()

    print(f"\n{'='*50}")
    print(f"Migration abgeschlossen!")
    print(f"Migriert: {migrated} | Uebersprungen: {skipped} | Fehler: {errors}")
    print(f"{'='*50}")
