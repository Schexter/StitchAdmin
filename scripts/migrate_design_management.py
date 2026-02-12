#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migration: Design-Management System
Erstellt alle Tabellen fuer das Design-Archiv

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import sys
import os

# Projektpfad hinzufuegen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from src.models.models import db
from sqlalchemy import text, inspect
from datetime import datetime


def create_design_tables():
    """Erstellt alle Design-Management Tabellen"""
    
    print("\n" + "="*60)
    print("Migration: Design-Management System")
    print("="*60)
    
    app = create_app()
    
    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        # ═══════════════════════════════════════════════════════════
        # 1. THREAD_BRANDS Tabelle
        # ═══════════════════════════════════════════════════════════
        print("\n[1/6] Pruefe thread_brands Tabelle...")
        
        if 'thread_brands' not in existing_tables:
            sql = text('''
                CREATE TABLE thread_brands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    short_code VARCHAR(10),
                    website VARCHAR(200),
                    notes TEXT,
                    is_default BOOLEAN DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    sort_order INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            db.session.execute(sql)
            db.session.commit()
            print("  [OK] thread_brands Tabelle erstellt")
            
            # Standard-Marken einfuegen
            brands = [
                ('Madeira', 'MA', 'https://www.madeira.com', 1, 1),
                ('Gunold', 'GU', 'https://www.gunold.de', 0, 2),
                ('Polystar', 'PS', None, 0, 3),
                ('Isacord', 'IS', 'https://www.isacord.com', 0, 4),
            ]
            for name, code, website, is_default, sort_order in brands:
                sql = text('''
                    INSERT INTO thread_brands (name, short_code, website, is_default, sort_order)
                    VALUES (:name, :code, :website, :is_default, :sort_order)
                ''')
                db.session.execute(sql, {'name': name, 'code': code, 'website': website, 
                                         'is_default': is_default, 'sort_order': sort_order})
            db.session.commit()
            print("  [OK] Standard-Marken eingefuegt (Madeira, Gunold, Polystar, Isacord)")
        else:
            print("  - thread_brands Tabelle existiert bereits")
        
        # ═══════════════════════════════════════════════════════════
        # 2. THREAD_PRODUCT_LINES Tabelle
        # ═══════════════════════════════════════════════════════════
        print("\n[2/6] Pruefe thread_product_lines Tabelle...")
        
        if 'thread_product_lines' not in existing_tables:
            sql = text('''
                CREATE TABLE thread_product_lines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    brand_id INTEGER NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    short_code VARCHAR(20),
                    description TEXT,
                    material VARCHAR(50),
                    thickness VARCHAR(20),
                    is_active BOOLEAN DEFAULT 1,
                    sort_order INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (brand_id) REFERENCES thread_brands(id),
                    UNIQUE (brand_id, name)
                )
            ''')
            db.session.execute(sql)
            db.session.commit()
            print("  [OK] thread_product_lines Tabelle erstellt")
            
            # Standard-Produktlinien einfuegen (Madeira = ID 1)
            lines = [
                (1, 'Polyneon No.40', 'PN40', 'Standard Polyester Stickgarn', 'Polyester', 'No.40', 1),
                (1, 'Rayon No.40', 'RN40', 'Rayon/Viskose Stickgarn', 'Rayon', 'No.40', 2),
                (1, 'Metallic', 'MET', 'Metallic Stickgarn', 'Metallic', None, 3),
                (1, 'Frosted Matt', 'FM', 'Mattes Stickgarn', 'Polyester', 'No.40', 4),
                (2, 'POLY 40', 'GP40', 'Gunold Polyester', 'Polyester', 'No.40', 1),
                (2, 'SULKY RAYON 40', 'SR40', 'Gunold Rayon', 'Rayon', 'No.40', 2),
            ]
            for brand_id, name, code, desc, material, thickness, sort_order in lines:
                sql = text('''
                    INSERT INTO thread_product_lines (brand_id, name, short_code, description, material, thickness, sort_order)
                    VALUES (:brand_id, :name, :code, :desc, :material, :thickness, :sort_order)
                ''')
                db.session.execute(sql, {'brand_id': brand_id, 'name': name, 'code': code, 
                                         'desc': desc, 'material': material, 'thickness': thickness, 
                                         'sort_order': sort_order})
            db.session.commit()
            print("  [OK] Standard-Produktlinien eingefuegt")
        else:
            print("  - thread_product_lines Tabelle existiert bereits")
        
        # ═══════════════════════════════════════════════════════════
        # 3. THREAD_COLORS Tabelle
        # ═══════════════════════════════════════════════════════════
        print("\n[3/6] Pruefe thread_colors Tabelle...")
        
        if 'thread_colors' not in existing_tables:
            sql = text('''
                CREATE TABLE thread_colors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    brand_id INTEGER NOT NULL,
                    product_line_id INTEGER,
                    color_code VARCHAR(20) NOT NULL,
                    color_name VARCHAR(100),
                    color_name_en VARCHAR(100),
                    hex_color VARCHAR(7),
                    rgb_r INTEGER,
                    rgb_g INTEGER,
                    rgb_b INTEGER,
                    pantone_code VARCHAR(20),
                    color_family VARCHAR(50),
                    category VARCHAR(50) DEFAULT 'Standard',
                    is_metallic BOOLEAN DEFAULT 0,
                    is_glow BOOLEAN DEFAULT 0,
                    is_multicolor BOOLEAN DEFAULT 0,
                    stock_quantity INTEGER DEFAULT 0,
                    min_stock INTEGER DEFAULT 1,
                    stock_location VARCHAR(50),
                    is_active BOOLEAN DEFAULT 1,
                    is_favorite BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME,
                    FOREIGN KEY (brand_id) REFERENCES thread_brands(id),
                    FOREIGN KEY (product_line_id) REFERENCES thread_product_lines(id),
                    UNIQUE (brand_id, product_line_id, color_code)
                )
            ''')
            db.session.execute(sql)
            db.session.commit()
            print("  [OK] thread_colors Tabelle erstellt")
        else:
            print("  - thread_colors Tabelle existiert bereits")
        
        # ═══════════════════════════════════════════════════════════
        # 4. DESIGNS Tabelle
        # ═══════════════════════════════════════════════════════════
        print("\n[4/6] Pruefe designs Tabelle...")
        
        if 'designs' not in existing_tables:
            sql = text('''
                CREATE TABLE designs (
                    id VARCHAR(50) PRIMARY KEY,
                    design_number VARCHAR(50) UNIQUE,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    design_type VARCHAR(50) NOT NULL,
                    category VARCHAR(100),
                    tags TEXT,
                    customer_id VARCHAR(50),
                    is_customer_design BOOLEAN DEFAULT 1,
                    
                    -- Dateien & Vorschau
                    file_path VARCHAR(500),
                    file_name VARCHAR(255),
                    file_type VARCHAR(20),
                    file_size_kb INTEGER,
                    file_hash VARCHAR(64),
                    thumbnail_path VARCHAR(500),
                    preview_path VARCHAR(500),
                    preview_generated_at DATETIME,
                    production_file_path VARCHAR(500),
                    production_file_type VARCHAR(20),
                    
                    -- Stickerei-spezifisch
                    width_mm FLOAT,
                    height_mm FLOAT,
                    stitch_count INTEGER,
                    color_changes INTEGER,
                    estimated_time_minutes INTEGER,
                    thread_colors TEXT,
                    dst_analysis TEXT,
                    
                    -- Druck-spezifisch
                    print_width_cm FLOAT,
                    print_height_cm FLOAT,
                    dpi INTEGER,
                    color_mode VARCHAR(20),
                    print_colors TEXT,
                    print_method VARCHAR(50),
                    has_white_underbase BOOLEAN DEFAULT 0,
                    has_transparent_bg BOOLEAN DEFAULT 0,
                    
                    -- Status & Workflow
                    status VARCHAR(50) DEFAULT 'active',
                    quality_rating INTEGER,
                    quality_notes TEXT,
                    is_approved BOOLEAN DEFAULT 0,
                    approved_at DATETIME,
                    approved_by VARCHAR(80),
                    
                    -- Herkunft & Kosten
                    source VARCHAR(50) DEFAULT 'customer',
                    source_order_id VARCHAR(50),
                    creation_cost FLOAT,
                    supplier_id VARCHAR(50),
                    
                    -- Verwendungszaehler
                    usage_count INTEGER DEFAULT 0,
                    last_used_at DATETIME,
                    last_used_order_id VARCHAR(50),
                    
                    -- Metadaten
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(80),
                    updated_at DATETIME,
                    updated_by VARCHAR(80),
                    
                    FOREIGN KEY (customer_id) REFERENCES customers(id),
                    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
                )
            ''')
            db.session.execute(sql)
            db.session.commit()
            print("  [OK] designs Tabelle erstellt")
            
            # Index fuer schnelle Suche
            db.session.execute(text('CREATE INDEX idx_designs_customer ON designs(customer_id)'))
            db.session.execute(text('CREATE INDEX idx_designs_type ON designs(design_type)'))
            db.session.execute(text('CREATE INDEX idx_designs_status ON designs(status)'))
            db.session.commit()
            print("  [OK] Indizes erstellt")
        else:
            print("  - designs Tabelle existiert bereits")
        
        # ═══════════════════════════════════════════════════════════
        # 5. DESIGN_VERSIONS Tabelle
        # ═══════════════════════════════════════════════════════════
        print("\n[5/6] Pruefe design_versions Tabelle...")
        
        if 'design_versions' not in existing_tables:
            sql = text('''
                CREATE TABLE design_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    design_id VARCHAR(50) NOT NULL,
                    version_number INTEGER NOT NULL,
                    version_name VARCHAR(100),
                    change_description TEXT,
                    change_reason VARCHAR(200),
                    file_path VARCHAR(500),
                    file_name VARCHAR(255),
                    thumbnail_path VARCHAR(500),
                    file_hash VARCHAR(64),
                    technical_data TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(80),
                    is_active BOOLEAN DEFAULT 0,
                    FOREIGN KEY (design_id) REFERENCES designs(id)
                )
            ''')
            db.session.execute(sql)
            db.session.commit()
            print("  [OK] design_versions Tabelle erstellt")
        else:
            print("  - design_versions Tabelle existiert bereits")
        
        # ═══════════════════════════════════════════════════════════
        # 6. DESIGN_USAGE Tabelle
        # ═══════════════════════════════════════════════════════════
        print("\n[6/6] Pruefe design_usage Tabelle...")
        
        if 'design_usage' not in existing_tables:
            sql = text('''
                CREATE TABLE design_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    design_id VARCHAR(50) NOT NULL,
                    order_id VARCHAR(50),
                    order_item_id INTEGER,
                    order_number VARCHAR(50),
                    customer_id VARCHAR(50),
                    customer_name VARCHAR(200),
                    position VARCHAR(100),
                    quantity INTEGER DEFAULT 1,
                    size_adjustment VARCHAR(50),
                    color_adjustments TEXT,
                    quality_feedback INTEGER,
                    feedback_notes TEXT,
                    production_issues TEXT,
                    used_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    used_by VARCHAR(80),
                    FOREIGN KEY (design_id) REFERENCES designs(id),
                    FOREIGN KEY (order_id) REFERENCES orders(id),
                    FOREIGN KEY (order_item_id) REFERENCES order_items(id),
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            ''')
            db.session.execute(sql)
            db.session.commit()
            print("  [OK] design_usage Tabelle erstellt")
            
            # Index
            db.session.execute(text('CREATE INDEX idx_design_usage_design ON design_usage(design_id)'))
            db.session.execute(text('CREATE INDEX idx_design_usage_order ON design_usage(order_id)'))
            db.session.commit()
            print("  [OK] Indizes erstellt")
        else:
            print("  - design_usage Tabelle existiert bereits")
        
        # ═══════════════════════════════════════════════════════════
        # 7. DESIGN_ORDERS Tabelle (falls nicht existiert)
        # ═══════════════════════════════════════════════════════════
        print("\n[BONUS] Pruefe design_orders Tabelle...")
        
        if 'design_orders' not in existing_tables:
            sql = text('''
                CREATE TABLE design_orders (
                    id VARCHAR(50) PRIMARY KEY,
                    design_order_number VARCHAR(50) UNIQUE,
                    order_id VARCHAR(50),
                    design_id VARCHAR(50),
                    supplier_id VARCHAR(50),
                    customer_id VARCHAR(50),
                    
                    -- Typ & Spezifikation
                    design_type VARCHAR(50) NOT NULL,
                    order_type VARCHAR(50),
                    design_name VARCHAR(200),
                    design_description TEXT,
                    
                    -- Stickerei
                    target_width_mm FLOAT,
                    target_height_mm FLOAT,
                    max_stitch_count INTEGER,
                    max_colors INTEGER,
                    stitch_density VARCHAR(50),
                    requested_thread_colors TEXT,
                    underlay_type VARCHAR(50),
                    fabric_type VARCHAR(100),
                    
                    -- Druck
                    target_print_width_cm FLOAT,
                    target_print_height_cm FLOAT,
                    print_method VARCHAR(50),
                    min_dpi INTEGER DEFAULT 300,
                    color_mode VARCHAR(20),
                    requested_print_colors TEXT,
                    needs_transparent_bg BOOLEAN DEFAULT 0,
                    needs_white_underbase BOOLEAN DEFAULT 0,
                    
                    -- Vorlage
                    source_file_path VARCHAR(500),
                    source_file_name VARCHAR(255),
                    source_file_type VARCHAR(50),
                    reference_images TEXT,
                    special_requirements TEXT,
                    
                    -- Status
                    status VARCHAR(50) DEFAULT 'draft',
                    request_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    request_sent_at DATETIME,
                    request_sent_to VARCHAR(200),
                    request_sent_method VARCHAR(50),
                    
                    -- Angebot
                    quote_received_date DATETIME,
                    quote_price FLOAT,
                    quote_delivery_days INTEGER,
                    quote_notes TEXT,
                    quote_accepted BOOLEAN,
                    quote_accepted_at DATETIME,
                    
                    -- Anzahlung
                    deposit_required BOOLEAN DEFAULT 0,
                    deposit_percent FLOAT,
                    deposit_amount FLOAT,
                    deposit_status VARCHAR(50),
                    deposit_paid_date DATETIME,
                    
                    -- Bestellung
                    order_date DATETIME,
                    expected_delivery DATE,
                    
                    -- Lieferung
                    delivered_date DATETIME,
                    delivered_file_path VARCHAR(500),
                    delivered_file_name VARCHAR(255),
                    delivered_preview_path VARCHAR(500),
                    
                    -- Pruefung
                    review_status VARCHAR(50),
                    review_date DATETIME,
                    review_notes TEXT,
                    revision_count INTEGER DEFAULT 0,
                    completed_at DATETIME,
                    final_design_id VARCHAR(50),
                    
                    -- Kosten
                    total_price FLOAT,
                    payment_status VARCHAR(50),
                    paid_amount FLOAT DEFAULT 0,
                    paid_at DATETIME,
                    
                    -- PDF
                    order_pdf_path VARCHAR(500),
                    order_pdf_generated_at DATETIME,
                    
                    -- Sonstiges
                    priority VARCHAR(20) DEFAULT 'normal',
                    internal_notes TEXT,
                    communication_log TEXT,
                    
                    -- Metadaten
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(80),
                    updated_at DATETIME,
                    updated_by VARCHAR(80),
                    
                    FOREIGN KEY (order_id) REFERENCES orders(id),
                    FOREIGN KEY (design_id) REFERENCES designs(id),
                    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            ''')
            db.session.execute(sql)
            db.session.commit()
            print("  [OK] design_orders Tabelle erstellt")
        else:
            print("  - design_orders Tabelle existiert bereits")
        
        # ═══════════════════════════════════════════════════════════
        # MODUL REGISTRIEREN
        # ═══════════════════════════════════════════════════════════
        print("\n[MODUL] Pruefe Design-Archiv Modul...")
        
        from src.models.user_permissions import Module
        existing = Module.query.filter_by(name='designs').first()
        
        if not existing:
            max_order = db.session.query(db.func.max(Module.sort_order)).scalar() or 0
            
            design_module = Module(
                name='designs',
                display_name='Design-Archiv',
                description='Zentrale Bibliothek fuer Stick- und Druck-Designs',
                icon='palette',
                route='designs.index',
                category='core',
                default_enabled=True,
                is_enabled=True,
                sort_order=max_order + 1,
                required_role='user'
            )
            db.session.add(design_module)
            db.session.commit()
            print("  [OK] Design-Archiv Modul registriert")
        else:
            print("  - Design-Archiv Modul existiert bereits")
        
        print("\n" + "="*60)
        print("Migration abgeschlossen!")
        print("="*60)
        print("\nErstellte Tabellen:")
        print("  - thread_brands (Garn-Marken)")
        print("  - thread_product_lines (Garn-Produktlinien)")
        print("  - thread_colors (Garnfarben-Bibliothek)")
        print("  - designs (Design-Archiv)")
        print("  - design_versions (Versionierung)")
        print("  - design_usage (Verwendungs-Historie)")
        print("  - design_orders (Design-Bestellungen)")
        print("\nNaechster Schritt:")
        print("  python scripts/import_thread_colors.py")
        print("  (Importiert Garnfarben aus CSV-Vorlage)")


if __name__ == '__main__':
    create_design_tables()
