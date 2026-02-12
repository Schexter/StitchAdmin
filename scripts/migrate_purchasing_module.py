"""
Migration: Einkauf-Modul hinzufügen
===================================

Dieses Script:
1. Fügt das "Einkauf"-Modul zur modules-Tabelle hinzu
2. Erweitert die supplier_orders-Tabelle um neue Felder
3. Initialisiert die Nummernkreise für PO und DO

Ausführung:
    python scripts/migrate_purchasing_module.py

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
import sys

# Projekt-Root zum Path hinzufügen
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import create_app
from src.models.models import db


def migrate_purchasing_module():
    """Führt die Migration für das Einkauf-Modul durch"""
    
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("Migration: Einkauf-Modul")
        print("=" * 60)
        
        # 1. Modul hinzufügen
        add_purchasing_module()
        
        # 2. SupplierOrder erweitern
        extend_supplier_order_table()
        
        # 3. Nummernkreise initialisieren
        init_number_sequences()
        
        print("=" * 60)
        print("Migration abgeschlossen!")
        print("=" * 60)


def add_purchasing_module():
    """Fügt das Einkauf-Modul zur modules-Tabelle hinzu"""
    from src.models.user_permissions import Module
    
    print("\n[1/3] Prüfe Einkauf-Modul...")
    
    # Prüfe ob Modul bereits existiert
    existing = Module.query.filter_by(name='purchasing').first()
    
    if existing:
        print("  [OK] Einkauf-Modul existiert bereits (ID: {})".format(existing.id))
        return
    
    # Finde höchste sort_order
    max_order = db.session.query(db.func.max(Module.sort_order)).scalar() or 0
    
    # Neues Modul erstellen
    purchasing_module = Module(
        name='purchasing',
        display_name='Einkauf',
        description='Bestellungen, Wareneingang & Design-Beschaffung',
        icon='🛒',
        color='info',
        route='purchasing.dashboard',
        category='core',
        is_active=True,
        requires_admin=False,
        default_enabled=True,
        sort_order=max_order + 1
    )
    
    db.session.add(purchasing_module)
    db.session.commit()
    
    print("  [OK] Einkauf-Modul erstellt (ID: {})".format(purchasing_module.id))


def extend_supplier_order_table():
    """Erweitert die supplier_orders-Tabelle um neue Felder"""
    from sqlalchemy import inspect, text
    
    print("\n[2/3] Prüfe SupplierOrder-Tabelle...")
    
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('supplier_orders')]
    
    new_columns = {
        'purchase_order_number': 'VARCHAR(50)',
        'linked_customer_orders': 'TEXT',
        'print_count': 'INTEGER DEFAULT 0',
        'last_printed_at': 'DATETIME',
        'last_printed_by': 'VARCHAR(80)'
    }
    
    added = []
    for col_name, col_type in new_columns.items():
        if col_name not in columns:
            try:
                sql = text(f'ALTER TABLE supplier_orders ADD COLUMN {col_name} {col_type}')
                db.session.execute(sql)
                db.session.commit()
                added.append(col_name)
                print(f"  [OK] Spalte '{col_name}' hinzugefuegt")
            except Exception as e:
                print(f"  [WARNUNG] Spalte '{col_name}' konnte nicht hinzugefuegt werden: {e}")
        else:
            print(f"  - Spalte '{col_name}' existiert bereits")
    
    if not added:
        print("  [OK] Alle Spalten bereits vorhanden")


def init_number_sequences():
    """Initialisiert die Nummernkreise für PO und DO"""
    from src.models.nummernkreis import NumberSequenceSettings, DocumentType
    from datetime import datetime
    
    print("\n[3/3] Prüfe Nummernkreise...")
    
    # Purchase Order Nummernkreis
    po_settings = NumberSequenceSettings.query.filter_by(
        document_type=DocumentType.PURCHASE_ORDER
    ).first()
    
    if not po_settings:
        po_settings = NumberSequenceSettings(
            document_type=DocumentType.PURCHASE_ORDER,
            prefix='PO',
            use_year=True,
            use_month=False,
            format_pattern='{prefix}-{year}-{number:04d}',
            current_year=datetime.now().year,
            current_month=datetime.now().month,
            current_number=0
        )
        db.session.add(po_settings)
        print("  [OK] Nummernkreis 'Purchase Order' (PO) erstellt")
    else:
        print("  - Nummernkreis 'Purchase Order' existiert bereits")
    
    # Design Order Nummernkreis
    do_settings = NumberSequenceSettings.query.filter_by(
        document_type=DocumentType.DESIGN_ORDER
    ).first()
    
    if not do_settings:
        do_settings = NumberSequenceSettings(
            document_type=DocumentType.DESIGN_ORDER,
            prefix='DO',
            use_year=True,
            use_month=False,
            format_pattern='{prefix}-{year}-{number:04d}',
            current_year=datetime.now().year,
            current_month=datetime.now().month,
            current_number=0
        )
        db.session.add(do_settings)
        print("  [OK] Nummernkreis 'Design Order' (DO) erstellt")
    else:
        print("  - Nummernkreis 'Design Order' existiert bereits")
    
    db.session.commit()
    print("  [OK] Nummernkreise gespeichert")


if __name__ == '__main__':
    migrate_purchasing_module()
