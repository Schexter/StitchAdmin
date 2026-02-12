#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Import: Garnfarben aus CSV
Importiert Garnfarben aus der Vorlage in die Datenbank

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import sys
import os
import csv

# Projektpfad hinzufuegen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from src.models.models import db
from sqlalchemy import text


def import_thread_colors_from_csv(csv_path=None):
    """Importiert Garnfarben aus CSV-Datei"""
    
    if csv_path is None:
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'src', 'static', 'templates', 'garnfarben_vorlage.csv'
        )
    
    if not os.path.exists(csv_path):
        print(f"[FEHLER] CSV-Datei nicht gefunden: {csv_path}")
        return False
    
    print("\n" + "="*60)
    print("Import: Garnfarben aus CSV")
    print("="*60)
    print(f"\nQuelle: {csv_path}")
    
    app = create_app()
    
    with app.app_context():
        # Marken und Produktlinien cachen
        brands_cache = {}
        lines_cache = {}
        
        # Bestehende Marken laden
        result = db.session.execute(text('SELECT id, name FROM thread_brands'))
        for row in result:
            brands_cache[row[1]] = row[0]
        
        # Bestehende Produktlinien laden
        result = db.session.execute(text('SELECT id, brand_id, name FROM thread_product_lines'))
        for row in result:
            key = f"{row[1]}_{row[2]}"
            lines_cache[key] = row[0]
        
        imported = 0
        skipped = 0
        errors = 0
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    # Marke finden oder erstellen
                    brand_name = row.get('Hersteller', '').strip()
                    if not brand_name:
                        continue
                    
                    if brand_name not in brands_cache:
                        # Neue Marke erstellen
                        sql = text('''
                            INSERT INTO thread_brands (name, short_code, is_active)
                            VALUES (:name, :code, 1)
                        ''')
                        short_code = ''.join([c for c in brand_name[:3].upper() if c.isalpha()])
                        db.session.execute(sql, {'name': brand_name, 'code': short_code})
                        db.session.commit()
                        
                        # ID holen
                        result = db.session.execute(
                            text('SELECT id FROM thread_brands WHERE name = :name'),
                            {'name': brand_name}
                        )
                        brand_id = result.fetchone()[0]
                        brands_cache[brand_name] = brand_id
                        print(f"  [+] Neue Marke erstellt: {brand_name}")
                    else:
                        brand_id = brands_cache[brand_name]
                    
                    # Produktlinie finden oder erstellen
                    line_name = row.get('Produktlinie', '').strip()
                    line_id = None
                    
                    if line_name:
                        cache_key = f"{brand_id}_{line_name}"
                        
                        if cache_key not in lines_cache:
                            # Neue Produktlinie erstellen
                            sql = text('''
                                INSERT INTO thread_product_lines (brand_id, name, is_active)
                                VALUES (:brand_id, :name, 1)
                            ''')
                            db.session.execute(sql, {'brand_id': brand_id, 'name': line_name})
                            db.session.commit()
                            
                            # ID holen
                            result = db.session.execute(
                                text('SELECT id FROM thread_product_lines WHERE brand_id = :brand_id AND name = :name'),
                                {'brand_id': brand_id, 'name': line_name}
                            )
                            line_id = result.fetchone()[0]
                            lines_cache[cache_key] = line_id
                            print(f"  [+] Neue Produktlinie erstellt: {brand_name} - {line_name}")
                        else:
                            line_id = lines_cache[cache_key]
                    
                    # Farbe importieren
                    color_code = row.get('Farbnummer', '').strip()
                    if not color_code:
                        continue
                    
                    # Pruefen ob Farbe bereits existiert
                    check_sql = text('''
                        SELECT id FROM thread_colors 
                        WHERE brand_id = :brand_id 
                        AND (product_line_id = :line_id OR (product_line_id IS NULL AND :line_id IS NULL))
                        AND color_code = :color_code
                    ''')
                    existing = db.session.execute(check_sql, {
                        'brand_id': brand_id,
                        'line_id': line_id,
                        'color_code': color_code
                    }).fetchone()
                    
                    if existing:
                        skipped += 1
                        continue
                    
                    # Farbwerte extrahieren
                    hex_color = row.get('HexWert', '').strip()
                    rgb_r, rgb_g, rgb_b = None, None, None
                    
                    if hex_color and hex_color.startswith('#') and len(hex_color) == 7:
                        try:
                            rgb_r = int(hex_color[1:3], 16)
                            rgb_g = int(hex_color[3:5], 16)
                            rgb_b = int(hex_color[5:7], 16)
                        except:
                            pass
                    
                    # Kategorie ermitteln
                    category = row.get('Kategorie', 'Standard').strip() or 'Standard'
                    is_metallic = category.lower() == 'metallic'
                    is_glow = category.lower() in ('fluoreszent', 'neon', 'glow')
                    
                    # Farbfamilie ermitteln
                    color_family = detect_color_family(rgb_r, rgb_g, rgb_b)
                    
                    # Farbe einfuegen
                    sql = text('''
                        INSERT INTO thread_colors (
                            brand_id, product_line_id, color_code, color_name, color_name_en,
                            hex_color, rgb_r, rgb_g, rgb_b, pantone_code,
                            color_family, category, is_metallic, is_glow, is_active
                        ) VALUES (
                            :brand_id, :line_id, :code, :name_de, :name_en,
                            :hex, :r, :g, :b, :pantone,
                            :family, :category, :metallic, :glow, 1
                        )
                    ''')
                    
                    db.session.execute(sql, {
                        'brand_id': brand_id,
                        'line_id': line_id,
                        'code': color_code,
                        'name_de': row.get('Farbname_DE', '').strip() or None,
                        'name_en': row.get('Farbname_EN', '').strip() or None,
                        'hex': hex_color or None,
                        'r': rgb_r,
                        'g': rgb_g,
                        'b': rgb_b,
                        'pantone': row.get('Pantone', '').strip() or None,
                        'family': color_family,
                        'category': category,
                        'metallic': 1 if is_metallic else 0,
                        'glow': 1 if is_glow else 0
                    })
                    
                    imported += 1
                    
                except Exception as e:
                    errors += 1
                    print(f"  [!] Fehler bei Zeile: {row} - {e}")
        
        db.session.commit()
        
        print("\n" + "-"*60)
        print(f"Import abgeschlossen:")
        print(f"  Importiert: {imported}")
        print(f"  Uebersprungen (bereits vorhanden): {skipped}")
        print(f"  Fehler: {errors}")
        print("="*60)
        
        return True


def detect_color_family(r, g, b):
    """Erkennt Farbfamilie anhand von RGB-Werten"""
    if r is None or g is None or b is None:
        return None
    
    # Graustufen
    if abs(r - g) < 20 and abs(g - b) < 20 and abs(r - b) < 20:
        if r < 50:
            return 'schwarz'
        elif r > 200:
            return 'weiss'
        else:
            return 'grau'
    
    # Hauptfarben
    max_val = max(r, g, b)
    
    if r == max_val:
        if g > b + 50:
            return 'orange' if g > 150 else 'rot'
        elif b > g + 50:
            return 'pink'
        else:
            return 'rot'
    elif g == max_val:
        if r > b + 50:
            return 'gelb' if r > 150 else 'gruen'
        elif b > r + 50:
            return 'tuerkis'
        else:
            return 'gruen'
    else:  # b == max_val
        if r > g + 50:
            return 'violett'
        else:
            return 'blau'


def add_sample_colors():
    """Fuegt einige Standard-Garnfarben hinzu (falls CSV leer)"""
    
    print("\n[INFO] Fuege Beispiel-Garnfarben hinzu...")
    
    app = create_app()
    
    with app.app_context():
        # Pruefen ob bereits Farben existieren
        result = db.session.execute(text('SELECT COUNT(*) FROM thread_colors'))
        count = result.fetchone()[0]
        
        if count > 0:
            print(f"  - {count} Farben bereits vorhanden, ueberspringe Beispieldaten")
            return
        
        # Madeira Polyneon No.40 Farben (ID: 1, Produktlinie ID: 1)
        colors = [
            # (code, name_de, name_en, hex, pantone, category)
            ('1800', 'Schwarz', 'Black', '#000000', 'Black C', 'Standard'),
            ('1801', 'Weiss', 'White', '#FFFFFF', 'White', 'Standard'),
            ('1802', 'Naturweiss', 'Natural White', '#FFFEF0', None, 'Standard'),
            ('1803', 'Creme', 'Cream', '#FFFDD0', None, 'Standard'),
            ('1810', 'Rot', 'Red', '#FF0000', '186 C', 'Standard'),
            ('1811', 'Hellrot', 'Light Red', '#FF6B6B', None, 'Standard'),
            ('1812', 'Dunkelrot', 'Dark Red', '#8B0000', None, 'Standard'),
            ('1820', 'Blau', 'Blue', '#0000FF', '286 C', 'Standard'),
            ('1821', 'Hellblau', 'Light Blue', '#ADD8E6', None, 'Standard'),
            ('1825', 'Koenigsblau', 'Royal Blue', '#4169E1', '286 C', 'Standard'),
            ('1826', 'Navy', 'Navy', '#000080', None, 'Standard'),
            ('1830', 'Gruen', 'Green', '#008000', '348 C', 'Standard'),
            ('1831', 'Hellgruen', 'Light Green', '#90EE90', None, 'Standard'),
            ('1835', 'Dunkelgruen', 'Dark Green', '#006400', None, 'Standard'),
            ('1840', 'Gelb', 'Yellow', '#FFFF00', '109 C', 'Standard'),
            ('1841', 'Goldgelb', 'Golden Yellow', '#FFD700', '116 C', 'Standard'),
            ('1850', 'Orange', 'Orange', '#FFA500', '151 C', 'Standard'),
            ('1860', 'Violett', 'Violet', '#EE82EE', None, 'Standard'),
            ('1861', 'Lila', 'Purple', '#800080', None, 'Standard'),
            ('1870', 'Rosa', 'Pink', '#FFC0CB', None, 'Standard'),
            ('1871', 'Pink', 'Hot Pink', '#FF69B4', None, 'Standard'),
            ('1880', 'Braun', 'Brown', '#8B4513', None, 'Standard'),
            ('1881', 'Hellbraun', 'Light Brown', '#D2B48C', None, 'Standard'),
            ('1890', 'Grau', 'Grey', '#808080', None, 'Standard'),
            ('1891', 'Hellgrau', 'Light Grey', '#D3D3D3', None, 'Standard'),
            ('1892', 'Dunkelgrau', 'Dark Grey', '#404040', None, 'Standard'),
            # Neon/Fluoreszent
            ('1520', 'Neongruen', 'Neon Green', '#39FF14', '802 C', 'Fluoreszent'),
            ('1521', 'Neongelb', 'Neon Yellow', '#DFFF00', '809 C', 'Fluoreszent'),
            ('1522', 'Neonorange', 'Neon Orange', '#FF6600', '804 C', 'Fluoreszent'),
            ('1523', 'Neonpink', 'Neon Pink', '#FF1493', '806 C', 'Fluoreszent'),
            # Metallic
            ('1950', 'Gold', 'Gold', '#FFD700', '116 C', 'Metallic'),
            ('1951', 'Silber', 'Silver', '#C0C0C0', '877 C', 'Metallic'),
            ('1952', 'Kupfer', 'Copper', '#B87333', None, 'Metallic'),
        ]
        
        for code, name_de, name_en, hex_color, pantone, category in colors:
            # RGB extrahieren
            rgb_r = int(hex_color[1:3], 16)
            rgb_g = int(hex_color[3:5], 16)
            rgb_b = int(hex_color[5:7], 16)
            color_family = detect_color_family(rgb_r, rgb_g, rgb_b)
            
            is_metallic = category == 'Metallic'
            is_glow = category == 'Fluoreszent'
            
            sql = text('''
                INSERT INTO thread_colors (
                    brand_id, product_line_id, color_code, color_name, color_name_en,
                    hex_color, rgb_r, rgb_g, rgb_b, pantone_code,
                    color_family, category, is_metallic, is_glow, is_active
                ) VALUES (
                    1, 1, :code, :name_de, :name_en,
                    :hex, :r, :g, :b, :pantone,
                    :family, :category, :metallic, :glow, 1
                )
            ''')
            
            try:
                db.session.execute(sql, {
                    'code': code,
                    'name_de': name_de,
                    'name_en': name_en,
                    'hex': hex_color,
                    'r': rgb_r,
                    'g': rgb_g,
                    'b': rgb_b,
                    'pantone': pantone,
                    'family': color_family,
                    'category': category,
                    'metallic': 1 if is_metallic else 0,
                    'glow': 1 if is_glow else 0
                })
            except Exception as e:
                print(f"  [!] Fehler bei {code}: {e}")
        
        db.session.commit()
        print(f"  [OK] {len(colors)} Beispiel-Garnfarben hinzugefuegt")


if __name__ == '__main__':
    # Erst aus CSV importieren
    import_thread_colors_from_csv()
    
    # Falls CSV leer, Beispielfarben hinzufuegen
    add_sample_colors()
