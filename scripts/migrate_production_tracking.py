#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration: Produktionszeit-Tracking Tabellen erstellen
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from src.models import db

app = create_app()

def migrate():
    """Erstellt die Tabellen für Produktionszeit-Tracking"""

    with app.app_context():
        # production_time_logs Tabelle erstellen
        print("=== Produktionszeit-Tracking Migration ===\n")

        # Prüfen ob Tabelle existiert
        result = db.session.execute(db.text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='production_time_logs'"
        ))
        if result.fetchone():
            print("[=] Tabelle 'production_time_logs' existiert bereits")
        else:
            print("[+] Erstelle Tabelle 'production_time_logs'...")
            db.session.execute(db.text("""
                CREATE TABLE production_time_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id VARCHAR(50) NOT NULL,
                    order_item_id INTEGER,
                    work_type VARCHAR(50) NOT NULL,
                    started_at DATETIME NOT NULL,
                    ended_at DATETIME,
                    paused_duration_minutes INTEGER DEFAULT 0,
                    duration_minutes FLOAT,
                    started_by VARCHAR(80),
                    ended_by VARCHAR(80),
                    machine_id VARCHAR(50),
                    stitch_count INTEGER,
                    color_changes INTEGER,
                    embroidery_position VARCHAR(100),
                    embroidery_size_mm2 FLOAT,
                    quantity_planned INTEGER,
                    quantity_produced INTEGER,
                    quantity_rejected INTEGER DEFAULT 0,
                    fabric_type VARCHAR(100),
                    fabric_difficulty INTEGER,
                    complexity_rating INTEGER,
                    is_new_design BOOLEAN DEFAULT 0,
                    notes TEXT,
                    issues TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders(id),
                    FOREIGN KEY (order_item_id) REFERENCES order_items(id),
                    FOREIGN KEY (machine_id) REFERENCES machines(id)
                )
            """))
            print("    [OK] Tabelle erstellt")

        # production_statistics Tabelle erstellen
        result = db.session.execute(db.text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='production_statistics'"
        ))
        if result.fetchone():
            print("[=] Tabelle 'production_statistics' existiert bereits")
        else:
            print("[+] Erstelle Tabelle 'production_statistics'...")
            db.session.execute(db.text("""
                CREATE TABLE production_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_type VARCHAR(50) NOT NULL,
                    embroidery_position VARCHAR(100),
                    fabric_type VARCHAR(100),
                    stitch_range_min INTEGER,
                    stitch_range_max INTEGER,
                    sample_count INTEGER DEFAULT 0,
                    avg_duration_minutes FLOAT,
                    min_duration_minutes FLOAT,
                    max_duration_minutes FLOAT,
                    std_deviation FLOAT,
                    avg_time_per_piece FLOAT,
                    avg_stitches_per_minute FLOAT,
                    avg_setup_time FLOAT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("    [OK] Tabelle erstellt")

        # position_time_estimates Tabelle erstellen
        result = db.session.execute(db.text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='position_time_estimates'"
        ))
        if result.fetchone():
            print("[=] Tabelle 'position_time_estimates' existiert bereits")
        else:
            print("[+] Erstelle Tabelle 'position_time_estimates'...")
            db.session.execute(db.text("""
                CREATE TABLE position_time_estimates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    position_name VARCHAR(100) UNIQUE NOT NULL,
                    typical_stitch_count INTEGER,
                    typical_size_mm2 FLOAT,
                    setup_time_minutes FLOAT DEFAULT 5,
                    time_per_piece_minutes FLOAT,
                    complexity_multiplier FLOAT DEFAULT 1.0,
                    fabric_difficulty_multiplier FLOAT DEFAULT 1.0,
                    sample_count INTEGER DEFAULT 0,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("    [OK] Tabelle erstellt")

            # Standard-Positionen einfügen
            print("[+] Füge Standard-Positionen ein...")
            positions = [
                ('brust_links', 5000, 2500, 5, 3.5),
                ('brust_rechts', 5000, 2500, 5, 3.5),
                ('brust_mitte', 8000, 4000, 5, 4.5),
                ('ruecken_gross', 25000, 40000, 8, 12.0),
                ('ruecken_klein', 10000, 10000, 6, 6.0),
                ('aermel_links', 3000, 1500, 4, 2.5),
                ('aermel_rechts', 3000, 1500, 4, 2.5),
                ('kragen', 2000, 800, 3, 2.0),
                ('kappe_vorne', 6000, 3000, 5, 4.0),
                ('kappe_seite', 4000, 2000, 4, 3.0),
            ]
            for pos_name, stitches, size, setup, time_pp in positions:
                db.session.execute(db.text("""
                    INSERT INTO position_time_estimates
                    (position_name, typical_stitch_count, typical_size_mm2, setup_time_minutes, time_per_piece_minutes)
                    VALUES (:name, :stitches, :size, :setup, :time_pp)
                """), {'name': pos_name, 'stitches': stitches, 'size': size, 'setup': setup, 'time_pp': time_pp})
            print("    [OK] 10 Standard-Positionen eingefügt")

        # Indizes erstellen
        print("\n[+] Erstelle Indizes...")
        indices = [
            ("idx_ptl_order_id", "production_time_logs", "order_id"),
            ("idx_ptl_work_type", "production_time_logs", "work_type"),
            ("idx_ptl_started_at", "production_time_logs", "started_at"),
            ("idx_ptl_position", "production_time_logs", "embroidery_position"),
        ]
        for idx_name, table, column in indices:
            try:
                db.session.execute(db.text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})"))
                print(f"    [OK] Index {idx_name}")
            except Exception as e:
                print(f"    [!] Index {idx_name}: {e}")

        db.session.commit()
        print("\n=== Migration abgeschlossen ===")


if __name__ == '__main__':
    migrate()
