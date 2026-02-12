"""
Migration Script für Design-Management Module
Erstellt alle notwendigen Tabellen und Standarddaten

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import sys
import os

# Pfad zum Projekt hinzufügen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from src.models.models import db


def migrate_design_module():
    """Hauptmigration für Design-Management"""
    print("=" * 60)
    print("Migration: Design-Management Module")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        # 1. Tabellen erstellen
        print("\n[1/4] Erstelle Design-Tabellen...")
        create_design_tables()
        
        # 2. Modul registrieren
        print("\n[2/4] Registriere Design-Modul...")
        add_design_module()
        
        # 3. Standard-Garnmarken anlegen
        print("\n[3/4] Erstelle Standard-Garnmarken...")
        create_default_thread_brands()
        
        # 4. Nummernkreis initialisieren
        print("\n[4/4] Initialisiere Nummernkreise...")
        init_design_number_sequences()
        
        print("\n" + "=" * 60)
        print("Migration abgeschlossen!")
        print("=" * 60)


def create_design_tables():
    """Erstellt alle Design-Tabellen"""
    from sqlalchemy import text, inspect
    
    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()
    
    tables_to_create = [
        'designs',
        'design_versions',
        'design_usage',
        'thread_brands',
        'thread_colors',
        'design_orders'
    ]
    
    # Importiere Models um sie zu registrieren
    from src.models.design import (
        Design, DesignVersion, DesignUsage,
        ThreadBrand, ThreadColor, DesignOrder
    )
    
    created = []
    for table in tables_to_create:
        if table not in existing_tables:
            try:
                # Erstelle nur diese Tabelle
                model = {
                    'designs': Design,
                    'design_versions': DesignVersion,
                    'design_usage': DesignUsage,
                    'thread_brands': ThreadBrand,
                    'thread_colors': ThreadColor,
                    'design_orders': DesignOrder
                }.get(table)
                
                if model:
                    model.__table__.create(db.engine, checkfirst=True)
                    created.append(table)
                    print(f"  [OK] Tabelle '{table}' erstellt")
            except Exception as e:
                print(f"  [WARNUNG] Tabelle '{table}': {e}")
        else:
            print(f"  - Tabelle '{table}' existiert bereits")
    
    if not created:
        print("  [OK] Alle Tabellen bereits vorhanden")
    
    db.session.commit()


def add_design_module():
    """Fügt das Design-Modul zur modules-Tabelle hinzu"""
    from src.models.models import db
    from sqlalchemy import text
    
    # Prüfe ob modules-Tabelle existiert
    try:
        result = db.session.execute(text("SELECT * FROM modules WHERE name = 'designs'"))
        existing = result.fetchone()
        
        if existing:
            print("  [OK] Design-Modul existiert bereits")
            return
        
        # Finde höchste sort_order
        result = db.session.execute(text("SELECT MAX(sort_order) FROM modules"))
        max_order = result.scalar() or 0
        
        # Füge Modul hinzu
        db.session.execute(text("""
            INSERT INTO modules (name, display_name, icon, route, description, category, default_enabled, sort_order)
            VALUES (:name, :display_name, :icon, :route, :description, :category, :default_enabled, :sort_order)
        """), {
            'name': 'designs',
            'display_name': 'Design-Archiv',
            'icon': 'palette',
            'route': 'designs.index',
            'description': 'Zentrale Design-Bibliothek fuer Stick- und Druck-Designs',
            'category': 'core',
            'default_enabled': True,
            'sort_order': max_order + 1
        })
        
        db.session.commit()
        print("  [OK] Design-Modul registriert")
        
    except Exception as e:
        print(f"  [WARNUNG] Modul-Registrierung: {e}")
        db.session.rollback()


def create_default_thread_brands():
    """Erstellt Standard-Garnmarken mit Basisfarben"""
    from src.models.design import ThreadBrand, ThreadColor
    
    # Standard-Garnmarken
    brands_data = [
        {'name': 'Madeira', 'short_code': 'MA', 'website': 'https://www.madeira.de', 'is_default': True, 'sort_order': 1},
        {'name': 'Polystar', 'short_code': 'PO', 'website': '', 'is_default': False, 'sort_order': 2},
        {'name': 'Gunold', 'short_code': 'GU', 'website': 'https://www.gunold.de', 'is_default': False, 'sort_order': 3},
        {'name': 'Isacord', 'short_code': 'IS', 'website': '', 'is_default': False, 'sort_order': 4},
        {'name': 'Marathon', 'short_code': 'MR', 'website': '', 'is_default': False, 'sort_order': 5},
        {'name': 'Andere', 'short_code': 'XX', 'website': '', 'is_default': False, 'sort_order': 99},
    ]
    
    created_brands = 0
    for brand_data in brands_data:
        existing = ThreadBrand.query.filter_by(name=brand_data['name']).first()
        if not existing:
            brand = ThreadBrand(**brand_data)
            db.session.add(brand)
            created_brands += 1
    
    db.session.commit()
    
    if created_brands > 0:
        print(f"  [OK] {created_brands} Garnmarken erstellt")
    else:
        print("  - Alle Garnmarken bereits vorhanden")
    
    # Standard-Farben für Madeira anlegen
    madeira = ThreadBrand.query.filter_by(name='Madeira').first()
    if madeira:
        created_colors = create_madeira_basic_colors(madeira.id)
        if created_colors > 0:
            print(f"  [OK] {created_colors} Madeira-Grundfarben erstellt")
        else:
            print("  - Madeira-Farben bereits vorhanden")


def create_madeira_basic_colors(brand_id):
    """Erstellt Madeira Grundfarben"""
    from src.models.design import ThreadColor
    
    # Basis-Farbpalette Madeira Rayon
    madeira_colors = [
        # Weiß/Schwarz/Grau
        {'color_code': '1001', 'color_name': 'Weiss', 'rgb_hex': '#FFFFFF', 'color_family': 'weiss'},
        {'color_code': '1000', 'color_name': 'Schwarz', 'rgb_hex': '#000000', 'color_family': 'schwarz'},
        {'color_code': '1011', 'color_name': 'Grau hell', 'rgb_hex': '#C0C0C0', 'color_family': 'grau'},
        {'color_code': '1041', 'color_name': 'Grau mittel', 'rgb_hex': '#808080', 'color_family': 'grau'},
        
        # Rot-Töne
        {'color_code': '1147', 'color_name': 'Weihnachtsrot', 'rgb_hex': '#CC0000', 'color_family': 'rot'},
        {'color_code': '1037', 'color_name': 'Rubinrot', 'rgb_hex': '#9B111E', 'color_family': 'rot'},
        {'color_code': '1181', 'color_name': 'Bordeaux', 'rgb_hex': '#722F37', 'color_family': 'rot'},
        {'color_code': '1039', 'color_name': 'Dunkelrot', 'rgb_hex': '#8B0000', 'color_family': 'rot'},
        
        # Blau-Töne
        {'color_code': '1042', 'color_name': 'Dunkelblau', 'rgb_hex': '#00008B', 'color_family': 'blau'},
        {'color_code': '1076', 'color_name': 'Koenigsblau', 'rgb_hex': '#4169E1', 'color_family': 'blau'},
        {'color_code': '1133', 'color_name': 'Hellblau', 'rgb_hex': '#87CEEB', 'color_family': 'blau'},
        {'color_code': '1096', 'color_name': 'Marine', 'rgb_hex': '#000080', 'color_family': 'blau'},
        {'color_code': '1029', 'color_name': 'Tuerkis', 'rgb_hex': '#40E0D0', 'color_family': 'blau'},
        
        # Grün-Töne
        {'color_code': '1051', 'color_name': 'Dunkelgruen', 'rgb_hex': '#006400', 'color_family': 'gruen'},
        {'color_code': '1049', 'color_name': 'Grasgruen', 'rgb_hex': '#228B22', 'color_family': 'gruen'},
        {'color_code': '1169', 'color_name': 'Flaschengruen', 'rgb_hex': '#006A4E', 'color_family': 'gruen'},
        {'color_code': '1100', 'color_name': 'Hellgruen', 'rgb_hex': '#90EE90', 'color_family': 'gruen'},
        
        # Gelb/Orange-Töne
        {'color_code': '1024', 'color_name': 'Sonnengelb', 'rgb_hex': '#FFD700', 'color_family': 'gelb'},
        {'color_code': '1023', 'color_name': 'Zitronengelb', 'rgb_hex': '#FFF44F', 'color_family': 'gelb'},
        {'color_code': '1065', 'color_name': 'Orange', 'rgb_hex': '#FF8C00', 'color_family': 'orange'},
        
        # Braun-Töne
        {'color_code': '1144', 'color_name': 'Dunkelbraun', 'rgb_hex': '#654321', 'color_family': 'braun'},
        {'color_code': '1057', 'color_name': 'Schokobraun', 'rgb_hex': '#7B3F00', 'color_family': 'braun'},
        {'color_code': '1128', 'color_name': 'Beige', 'rgb_hex': '#F5F5DC', 'color_family': 'braun'},
        
        # Rosa/Lila-Töne
        {'color_code': '1080', 'color_name': 'Pink', 'rgb_hex': '#FFC0CB', 'color_family': 'rosa'},
        {'color_code': '1033', 'color_name': 'Magenta', 'rgb_hex': '#FF00FF', 'color_family': 'rosa'},
        {'color_code': '1032', 'color_name': 'Violett', 'rgb_hex': '#8B00FF', 'color_family': 'lila'},
        {'color_code': '1112', 'color_name': 'Flieder', 'rgb_hex': '#C8A2C8', 'color_family': 'lila'},
        
        # Metallic (falls vorhanden)
        {'color_code': '4001', 'color_name': 'Gold', 'rgb_hex': '#FFD700', 'color_family': 'metallic', 'is_metallic': True},
        {'color_code': '4011', 'color_name': 'Silber', 'rgb_hex': '#C0C0C0', 'color_family': 'metallic', 'is_metallic': True},
    ]
    
    created = 0
    for color_data in madeira_colors:
        existing = ThreadColor.query.filter_by(
            brand_id=brand_id, 
            color_code=color_data['color_code']
        ).first()
        
        if not existing:
            color = ThreadColor(brand_id=brand_id, **color_data)
            # RGB-Werte aus Hex setzen
            if color_data.get('rgb_hex'):
                color.set_rgb_from_hex(color_data['rgb_hex'])
            db.session.add(color)
            created += 1
    
    db.session.commit()
    return created


def init_design_number_sequences():
    """Initialisiert Nummernkreise für Designs"""
    from src.models.nummernkreis import NumberSequenceSettings, DocumentType
    from datetime import datetime
    
    # Design-Nummernkreis (D-2025-0001)
    design_settings = NumberSequenceSettings.query.filter_by(
        document_type=DocumentType.DESIGN.value if hasattr(DocumentType, 'DESIGN') else 'design'
    ).first()
    
    if not design_settings:
        # Prüfe ob DESIGN in DocumentType existiert
        try:
            doc_type = DocumentType.DESIGN.value
        except AttributeError:
            doc_type = 'design'
        
        design_settings = NumberSequenceSettings(
            document_type=doc_type,
            prefix='D',
            include_year=True,
            year_format='YYYY',
            separator='-',
            number_length=4,
            reset_yearly=True,
            current_year=datetime.now().year,
            current_month=datetime.now().month,
            current_number=0
        )
        db.session.add(design_settings)
        print("  [OK] Nummernkreis 'Design' (D) erstellt")
    else:
        print("  - Nummernkreis 'Design' existiert bereits")
    
    db.session.commit()
    print("  [OK] Nummernkreise gespeichert")


if __name__ == '__main__':
    migrate_design_module()
