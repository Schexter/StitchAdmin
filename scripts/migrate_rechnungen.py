#!/usr/bin/env python3
"""
Migration: Fügt neue Spalten zur rechnungen-Tabelle hinzu
- richtung (AUSGANG/EINGANG)
- lieferant_id
- lieferant_name

Außerdem: supplier_ratings Tabelle erstellen
"""

import sqlite3
import os

# Pfad zur Datenbank
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'stitchadmin.db')

def migrate():
    print(f"Verbinde mit Datenbank: {DB_PATH}")

    if not os.path.exists(DB_PATH):
        print(f"FEHLER: Datenbank nicht gefunden: {DB_PATH}")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Prüfe ob Spalten bereits existieren
        cursor.execute("PRAGMA table_info(rechnungen)")
        columns = [col[1] for col in cursor.fetchall()]

        # Füge richtung hinzu (wenn nicht vorhanden)
        if 'richtung' not in columns:
            print("Füge Spalte 'richtung' hinzu...")
            cursor.execute("ALTER TABLE rechnungen ADD COLUMN richtung VARCHAR(20) DEFAULT 'AUSGANG'")
            print("  -> OK")
        else:
            print("Spalte 'richtung' existiert bereits")

        # Füge lieferant_id hinzu (wenn nicht vorhanden)
        if 'lieferant_id' not in columns:
            print("Füge Spalte 'lieferant_id' hinzu...")
            cursor.execute("ALTER TABLE rechnungen ADD COLUMN lieferant_id VARCHAR(50)")
            print("  -> OK")
        else:
            print("Spalte 'lieferant_id' existiert bereits")

        # Füge lieferant_name hinzu (wenn nicht vorhanden)
        if 'lieferant_name' not in columns:
            print("Füge Spalte 'lieferant_name' hinzu...")
            cursor.execute("ALTER TABLE rechnungen ADD COLUMN lieferant_name VARCHAR(200)")
            print("  -> OK")
        else:
            print("Spalte 'lieferant_name' existiert bereits")

        # Setze bestehende Rechnungen auf AUSGANG
        print("Setze bestehende Rechnungen auf 'AUSGANG'...")
        cursor.execute("UPDATE rechnungen SET richtung = 'AUSGANG' WHERE richtung IS NULL")
        print(f"  -> {cursor.rowcount} Rechnungen aktualisiert")

        # Erstelle supplier_ratings Tabelle
        print("\nPrüfe supplier_ratings Tabelle...")
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='supplier_ratings'
        """)

        if not cursor.fetchone():
            print("Erstelle Tabelle 'supplier_ratings'...")
            cursor.execute("""
                CREATE TABLE supplier_ratings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    supplier_id VARCHAR(50) NOT NULL,
                    quality INTEGER,
                    delivery_speed INTEGER,
                    price_performance INTEGER,
                    communication INTEGER,
                    packaging INTEGER,
                    reliability INTEGER,
                    overall_rating FLOAT,
                    order_id VARCHAR(50),
                    comment TEXT,
                    positive_aspects TEXT,
                    negative_aspects TEXT,
                    rated_by VARCHAR(80),
                    rated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
                    FOREIGN KEY (order_id) REFERENCES supplier_orders(id)
                )
            """)
            print("  -> OK")
        else:
            print("Tabelle 'supplier_ratings' existiert bereits")

        # Prüfe/Erstelle supplier_contacts Tabelle (falls nicht vorhanden)
        print("\nPrüfe supplier_contacts Tabelle...")
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='supplier_contacts'
        """)

        if not cursor.fetchone():
            print("Erstelle Tabelle 'supplier_contacts'...")
            cursor.execute("""
                CREATE TABLE supplier_contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    supplier_id VARCHAR(50) NOT NULL,
                    salutation VARCHAR(20),
                    first_name VARCHAR(100),
                    last_name VARCHAR(100) NOT NULL,
                    position VARCHAR(100),
                    department VARCHAR(100),
                    email VARCHAR(120),
                    phone VARCHAR(50),
                    phone_direct VARCHAR(50),
                    mobile VARCHAR(50),
                    fax VARCHAR(50),
                    preferred_contact_method VARCHAR(20) DEFAULT 'email',
                    language VARCHAR(10) DEFAULT 'de',
                    is_primary_contact BOOLEAN DEFAULT 0,
                    is_sales_contact BOOLEAN DEFAULT 1,
                    is_technical_contact BOOLEAN DEFAULT 0,
                    is_accounting_contact BOOLEAN DEFAULT 0,
                    is_complaints_contact BOOLEAN DEFAULT 0,
                    availability_notes TEXT,
                    vacation_substitute_id INTEGER,
                    active BOOLEAN DEFAULT 1,
                    notes TEXT,
                    internal_notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(80),
                    updated_at DATETIME,
                    updated_by VARCHAR(80),
                    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
                    FOREIGN KEY (vacation_substitute_id) REFERENCES supplier_contacts(id)
                )
            """)
            print("  -> OK")
        else:
            print("Tabelle 'supplier_contacts' existiert bereits")

        # Prüfe/Erstelle supplier_communication_log Tabelle
        print("\nPrüfe supplier_communication_log Tabelle...")
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='supplier_communication_log'
        """)

        if not cursor.fetchone():
            print("Erstelle Tabelle 'supplier_communication_log'...")
            cursor.execute("""
                CREATE TABLE supplier_communication_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    supplier_id VARCHAR(50) NOT NULL,
                    contact_id INTEGER,
                    communication_type VARCHAR(20) NOT NULL,
                    direction VARCHAR(10) NOT NULL,
                    subject VARCHAR(200),
                    content TEXT,
                    order_id VARCHAR(50),
                    article_id VARCHAR(50),
                    status VARCHAR(20) DEFAULT 'completed',
                    follow_up_required BOOLEAN DEFAULT 0,
                    follow_up_date DATE,
                    follow_up_notes TEXT,
                    attachment_count INTEGER DEFAULT 0,
                    attachment_paths TEXT,
                    communication_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    logged_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    logged_by VARCHAR(80),
                    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
                    FOREIGN KEY (contact_id) REFERENCES supplier_contacts(id),
                    FOREIGN KEY (order_id) REFERENCES supplier_orders(id),
                    FOREIGN KEY (article_id) REFERENCES articles(id)
                )
            """)
            print("  -> OK")
        else:
            print("Tabelle 'supplier_communication_log' existiert bereits")

        # Prüfe Supplier-Tabelle auf neue Bewertungsfelder
        print("\nPrüfe Supplier-Bewertungsfelder...")
        cursor.execute("PRAGMA table_info(suppliers)")
        supplier_columns = [col[1] for col in cursor.fetchall()]

        new_supplier_columns = [
            ('rating_overall', 'FLOAT DEFAULT 0'),
            ('rating_quality', 'FLOAT DEFAULT 0'),
            ('rating_delivery', 'FLOAT DEFAULT 0'),
            ('rating_price', 'FLOAT DEFAULT 0'),
            ('rating_communication', 'FLOAT DEFAULT 0'),
            ('rating_count', 'INTEGER DEFAULT 0'),
            ('avg_delivery_days', 'FLOAT'),
            ('on_time_delivery_rate', 'FLOAT'),
            ('total_orders', 'INTEGER DEFAULT 0'),
            ('total_order_value', 'FLOAT DEFAULT 0'),
            ('yearly_revenue', 'TEXT'),
            ('bank_name', 'VARCHAR(100)'),
            ('iban', 'VARCHAR(34)'),
            ('bic', 'VARCHAR(11)'),
            ('bank_account_holder', 'VARCHAR(200)'),
            ('categories', 'VARCHAR(500)'),
            ('notes', 'TEXT'),
        ]

        for col_name, col_type in new_supplier_columns:
            if col_name not in supplier_columns:
                print(f"  Füge Spalte '{col_name}' hinzu...")
                cursor.execute(f"ALTER TABLE suppliers ADD COLUMN {col_name} {col_type}")
            else:
                print(f"  Spalte '{col_name}' existiert bereits")

        conn.commit()
        print("\n=== Migration erfolgreich abgeschlossen! ===")
        return True

    except Exception as e:
        conn.rollback()
        print(f"\nFEHLER bei Migration: {e}")
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
