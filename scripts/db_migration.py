#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Datenbank-Migrations-Skript für StitchAdmin 2.0
Fügt fehlende Spalten zu bestehenden Tabellen hinzu
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)


def column_exists(cursor, table_name, column_name):
    """Prüft, ob eine Spalte in einer Tabelle existiert"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def migrate_database(db):
    """
    Führt Datenbank-Migrationen durch
    Fügt fehlende Spalten zur machines Tabelle hinzu
    """
    try:
        # Verwende die raw SQLite-Verbindung
        connection = db.engine.raw_connection()
        cursor = connection.cursor()

        print("[MIGRATION] Starte Datenbank-Migration...")

        # ==========================================
        # MACHINES TABELLE: Kalkulationsfelder
        # ==========================================
        migrations_needed = []

        # Liste der neuen Spalten für machines Tabelle
        machine_columns = {
            'purchase_price': 'REAL',
            'depreciation_years': 'INTEGER DEFAULT 10',
            'expected_lifetime_hours': 'INTEGER DEFAULT 20000',
            'energy_cost_per_hour': 'REAL DEFAULT 2.0',
            'maintenance_cost_per_hour': 'REAL DEFAULT 1.5',
            'space_cost_per_hour': 'REAL DEFAULT 0.5',
            'calculated_hourly_rate': 'REAL',
            'custom_hourly_rate': 'REAL',
            'use_custom_rate': 'INTEGER DEFAULT 0',  # Boolean als INTEGER
            'labor_cost_per_hour': 'REAL DEFAULT 35.0'
        }

        # Prüfe welche Spalten fehlen
        for column_name, column_type in machine_columns.items():
            if not column_exists(cursor, 'machines', column_name):
                migrations_needed.append((column_name, column_type))
                print(f"[MIGRATION] Spalte 'machines.{column_name}' fehlt - wird hinzugefügt")

        # Füge fehlende Spalten hinzu
        if migrations_needed:
            for column_name, column_type in migrations_needed:
                try:
                    sql = f"ALTER TABLE machines ADD COLUMN {column_name} {column_type}"
                    cursor.execute(sql)
                    print(f"[OK] Spalte 'machines.{column_name}' hinzugefügt")
                except sqlite3.OperationalError as e:
                    if 'duplicate column name' in str(e).lower():
                        print(f"[INFO] Spalte 'machines.{column_name}' existiert bereits")
                    else:
                        raise

            connection.commit()
            print(f"[OK] {len(migrations_needed)} Spalten zur machines-Tabelle hinzugefügt")
        else:
            print("[INFO] Keine Migrationen für machines-Tabelle erforderlich")

        # ==========================================
        # SHELLY DEVICE TABELLEN
        # ==========================================

        # Erstelle Shelly Devices Tabelle
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shelly_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                ip_address VARCHAR(15) NOT NULL UNIQUE,
                device_type VARCHAR(50),
                mac_address VARCHAR(17),
                firmware_version VARCHAR(20),
                machine_id VARCHAR(50),
                assigned_to_type VARCHAR(50),
                channel INTEGER DEFAULT 0,
                active BOOLEAN DEFAULT 1,
                track_energy BOOLEAN DEFAULT 1,
                auto_control BOOLEAN DEFAULT 0,
                electricity_price_per_kwh REAL DEFAULT 0.30,
                last_seen DATETIME,
                last_power_w REAL,
                is_online BOOLEAN DEFAULT 0,
                is_on BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(80),
                updated_at DATETIME,
                updated_by VARCHAR(80),
                FOREIGN KEY (machine_id) REFERENCES machines(id)
            )
        """)
        print("[OK] Tabelle 'shelly_devices' erstellt/geprüft")

        # Erstelle Shelly Energy Readings Tabelle
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shelly_energy_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER NOT NULL,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                power_w REAL,
                voltage_v REAL,
                current_a REAL,
                power_factor REAL,
                energy_wh REAL,
                energy_delta_wh REAL,
                is_on BOOLEAN,
                temperature_c REAL,
                production_schedule_id INTEGER,
                FOREIGN KEY (device_id) REFERENCES shelly_devices(id) ON DELETE CASCADE,
                FOREIGN KEY (production_schedule_id) REFERENCES production_schedules(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_energy_readings_timestamp ON shelly_energy_readings(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_energy_readings_device ON shelly_energy_readings(device_id)")
        print("[OK] Tabelle 'shelly_energy_readings' erstellt/geprüft")

        # Erstelle Shelly Production Energy Tabelle
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shelly_production_energy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                production_schedule_id INTEGER NOT NULL,
                shelly_device_id INTEGER NOT NULL,
                start_time DATETIME NOT NULL,
                end_time DATETIME,
                total_energy_kwh REAL DEFAULT 0,
                avg_power_w REAL,
                max_power_w REAL,
                min_power_w REAL,
                electricity_price_per_kwh REAL,
                total_cost_eur REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (production_schedule_id) REFERENCES production_schedules(id),
                FOREIGN KEY (shelly_device_id) REFERENCES shelly_devices(id)
            )
        """)
        print("[OK] Tabelle 'shelly_production_energy' erstellt/geprüft")

        connection.commit()

        # ==========================================
        # Weitere Migrationen hier hinzufügen
        # ==========================================

        connection.close()
        print("[OK] Datenbank-Migration abgeschlossen")
        return True

    except Exception as e:
        logger.error(f"Fehler bei der Datenbank-Migration: {e}")
        print(f"[FEHLER] Migration fehlgeschlagen: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    # Standalone-Ausführung für Tests
    import sys
    import os

    # Füge Projekt-Root zum Python-Path hinzu
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, BASE_DIR)

    from src.models.models import db
    from app import create_app

    app = create_app()
    with app.app_context():
        success = migrate_database(db)
        sys.exit(0 if success else 1)
