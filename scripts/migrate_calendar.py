"""
Migration Script - Kalender mit CRM-Funktionen
Erstellt/Aktualisiert die ProductionBlock Tabelle

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import sys
import os

# Füge Projektroot zum Pfad hinzu
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def run_migration():
    """Führt die Migration durch"""
    print("=" * 60)
    print("StitchAdmin 2.0 - Kalender + CRM Migration")
    print("=" * 60)
    
    # App importieren
    try:
        from app import app
        print("✓ Flask App importiert")
    except ImportError as e:
        print(f"✗ Konnte App nicht importieren: {e}")
        print("\nAlternative: Führe die Migration manuell in der SQLite-Konsole aus:")
        print_manual_sql()
        return
    
    with app.app_context():
        from src.models import db
        from sqlalchemy import text, inspect
        
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        # 1. ProductionBlock Tabelle erstellen/aktualisieren
        print("\n1. Prüfe ProductionBlock Tabelle...")
        
        if 'production_blocks' not in existing_tables:
            print("   → Erstelle neue Tabelle mit allen CRM-Feldern...")
            try:
                db.session.execute(text('''
                    CREATE TABLE production_blocks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        
                        -- Basis
                        block_type VARCHAR(50) NOT NULL,
                        title VARCHAR(200),
                        
                        -- Zeit
                        start_date DATE NOT NULL,
                        start_time TIME NOT NULL,
                        end_date DATE NOT NULL,
                        end_time TIME NOT NULL,
                        
                        -- Verknüpfungen
                        customer_id VARCHAR(50),
                        order_id VARCHAR(50),
                        machine_id INTEGER,
                        user_id INTEGER,
                        
                        -- CRM-Felder
                        contact_person VARCHAR(200),
                        contact_phone VARCHAR(50),
                        contact_email VARCHAR(200),
                        summary TEXT,
                        content TEXT,
                        outcome VARCHAR(50),
                        follow_up_date DATE,
                        follow_up_notes TEXT,
                        priority VARCHAR(20) DEFAULT 'normal',
                        
                        -- Wiederkehrend
                        is_recurring BOOLEAN DEFAULT 0,
                        recurrence_pattern VARCHAR(50),
                        recurrence_days VARCHAR(50),
                        recurrence_end_date DATE,
                        parent_block_id INTEGER,
                        
                        -- Darstellung
                        color VARCHAR(20),
                        is_active BOOLEAN DEFAULT 1,
                        is_all_day BOOLEAN DEFAULT 0,
                        is_private BOOLEAN DEFAULT 0,
                        notes TEXT,
                        
                        -- Audit
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        created_by VARCHAR(100),
                        updated_at DATETIME,
                        updated_by VARCHAR(100),
                        
                        -- Foreign Keys
                        FOREIGN KEY (customer_id) REFERENCES customers (id),
                        FOREIGN KEY (order_id) REFERENCES orders (id),
                        FOREIGN KEY (machine_id) REFERENCES machines (id),
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        FOREIGN KEY (parent_block_id) REFERENCES production_blocks (id)
                    )
                '''))
                db.session.commit()
                print("   ✓ Tabelle erstellt")
            except Exception as e:
                print(f"   ✗ Fehler: {e}")
                db.session.rollback()
        else:
            print("   → Tabelle existiert, prüfe auf fehlende Spalten...")
            
            # Hole existierende Spalten
            columns = inspector.get_columns('production_blocks')
            existing_columns = [c['name'] for c in columns]
            
            # Neue CRM-Spalten die hinzugefügt werden sollen
            new_columns = {
                'customer_id': 'VARCHAR(50)',
                'order_id': 'VARCHAR(50)',
                'contact_person': 'VARCHAR(200)',
                'contact_phone': 'VARCHAR(50)',
                'contact_email': 'VARCHAR(200)',
                'summary': 'TEXT',
                'content': 'TEXT',
                'outcome': 'VARCHAR(50)',
                'follow_up_date': 'DATE',
                'follow_up_notes': 'TEXT',
                'priority': "VARCHAR(20) DEFAULT 'normal'",
                'is_private': 'BOOLEAN DEFAULT 0'
            }
            
            for col_name, col_type in new_columns.items():
                if col_name not in existing_columns:
                    try:
                        db.session.execute(text(
                            f"ALTER TABLE production_blocks ADD COLUMN {col_name} {col_type}"
                        ))
                        db.session.commit()
                        print(f"   ✓ Spalte '{col_name}' hinzugefügt")
                    except Exception as e:
                        print(f"   ⚠ Spalte '{col_name}': {e}")
                        db.session.rollback()
            
            print("   ✓ Tabelle aktualisiert")
        
        # 2. calendar_color Spalte zu machines hinzufügen
        print("\n2. Prüfe Machine.calendar_color Spalte...")
        try:
            columns = inspector.get_columns('machines')
            existing_columns = [c['name'] for c in columns]
            
            if 'calendar_color' not in existing_columns:
                db.session.execute(text(
                    "ALTER TABLE machines ADD COLUMN calendar_color VARCHAR(20)"
                ))
                db.session.commit()
                print("   ✓ calendar_color Spalte hinzugefügt")
            else:
                print("   ✓ calendar_color Spalte existiert bereits")
        except Exception as e:
            print(f"   ⚠ {e}")
        
        # 3. Indizes erstellen
        print("\n3. Erstelle Indizes für schnelle Suche...")
        indexes = [
            ("idx_pb_dates", "production_blocks", "(start_date, end_date)"),
            ("idx_pb_active", "production_blocks", "(is_active)"),
            ("idx_pb_customer", "production_blocks", "(customer_id)"),
            ("idx_pb_order", "production_blocks", "(order_id)"),
            ("idx_pb_type", "production_blocks", "(block_type)"),
            ("idx_pb_follow_up", "production_blocks", "(follow_up_date)"),
            ("idx_pb_user", "production_blocks", "(user_id)")
        ]
        
        for idx_name, table, columns in indexes:
            try:
                db.session.execute(text(
                    f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} {columns}"
                ))
                db.session.commit()
                print(f"   ✓ Index {idx_name}")
            except Exception as e:
                print(f"   ⚠ Index {idx_name}: {e}")
                db.session.rollback()
        
        # 4. Volltextsuche vorbereiten (FTS5 für SQLite)
        print("\n4. Prüfe Volltext-Suchindex...")
        try:
            # Prüfe ob FTS-Tabelle existiert
            if 'production_blocks_fts' not in existing_tables:
                db.session.execute(text('''
                    CREATE VIRTUAL TABLE IF NOT EXISTS production_blocks_fts 
                    USING fts5(
                        title, 
                        summary, 
                        content, 
                        contact_person, 
                        notes,
                        content=production_blocks,
                        content_rowid=id
                    )
                '''))
                db.session.commit()
                print("   ✓ Volltext-Suchindex erstellt")
            else:
                print("   ✓ Volltext-Suchindex existiert bereits")
        except Exception as e:
            print(f"   ⚠ FTS nicht erstellt (optional): {e}")
            db.session.rollback()
        
        print("\n" + "=" * 60)
        print("✅ Migration abgeschlossen!")
        print("=" * 60)
        
        print("\n📋 Neue CRM-Funktionen:")
        print("   • Telefonate erfassen (eingehend/ausgehend)")
        print("   • Kundenbesuche dokumentieren")
        print("   • E-Mail-Korrespondenz notieren")
        print("   • Angebote & Reklamationen tracken")
        print("   • Wiedervorlagen mit Erinnerung")
        print("   • Volltextsuche über alle Einträge")
        
        print("\n🔗 Nächste Schritte:")
        print("   1. Anwendung neu starten")
        print("   2. /production/calendar/new öffnen")
        print("   3. '+Zeitblock' für CRM-Aktivitäten nutzen")


def print_manual_sql():
    """Zeigt SQL für manuelle Migration"""
    print("""
-- Führe diese Befehle in SQLite aus:

-- Tabelle erstellen (falls nicht vorhanden)
CREATE TABLE IF NOT EXISTS production_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_type VARCHAR(50) NOT NULL,
    title VARCHAR(200),
    start_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_date DATE NOT NULL,
    end_time TIME NOT NULL,
    customer_id VARCHAR(50),
    order_id VARCHAR(50),
    machine_id INTEGER,
    user_id INTEGER,
    contact_person VARCHAR(200),
    contact_phone VARCHAR(50),
    contact_email VARCHAR(200),
    summary TEXT,
    content TEXT,
    outcome VARCHAR(50),
    follow_up_date DATE,
    follow_up_notes TEXT,
    priority VARCHAR(20) DEFAULT 'normal',
    is_recurring BOOLEAN DEFAULT 0,
    recurrence_pattern VARCHAR(50),
    recurrence_days VARCHAR(50),
    recurrence_end_date DATE,
    parent_block_id INTEGER,
    color VARCHAR(20),
    is_active BOOLEAN DEFAULT 1,
    is_all_day BOOLEAN DEFAULT 0,
    is_private BOOLEAN DEFAULT 0,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_at DATETIME,
    updated_by VARCHAR(100)
);

-- Indizes für schnelle Suche
CREATE INDEX IF NOT EXISTS idx_pb_dates ON production_blocks (start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_pb_customer ON production_blocks (customer_id);
CREATE INDEX IF NOT EXISTS idx_pb_type ON production_blocks (block_type);
CREATE INDEX IF NOT EXISTS idx_pb_follow_up ON production_blocks (follow_up_date);

-- Maschinen-Kalenderfarbe
ALTER TABLE machines ADD COLUMN calendar_color VARCHAR(20);
""")


if __name__ == '__main__':
    run_migration()
