"""
File Analysis Utilities für StitchAdmin
Analysiert Design-Dateien (DST, SVG, PNG, etc.) und extrahiert Informationen
"""

import os
import struct
from PIL import Image
import xml.etree.ElementTree as ET
import re

def analyze_dst_file(filepath):
    """
    Analysiert DST-Stickerei-Datei und extrahiert Stichzahl und Dimensionen
    
    Versucht zuerst pyembroidery zu verwenden, falls verfügbar,
    andernfalls Fallback auf manuelle Analyse
    """
    try:
        # Versuche pyembroidery zu verwenden
        try:
            import pyembroidery
            
            pattern = pyembroidery.read_dst(filepath)
            stitch_count = pattern.count_stitch_commands(pyembroidery.STITCH)
            
            # Bounding Box berechnen
            bounds = pattern.bounds()
            if bounds:
                min_x, min_y, max_x, max_y = bounds
                width_mm = abs(max_x - min_x) / 10  # pyembroidery nutzt auch 1/10 mm
                height_mm = abs(max_y - min_y) / 10
            else:
                width_mm = height_mm = 0
            
            return {
                'success': True,
                'stitch_count': stitch_count,
                'width_mm': round(width_mm, 1),
                'height_mm': round(height_mm, 1),
                'bounds': {
                    'min_x': min_x / 10 if bounds else 0,
                    'max_x': max_x / 10 if bounds else 0,
                    'min_y': min_y / 10 if bounds else 0,
                    'max_y': max_y / 10 if bounds else 0
                },
                'method': 'pyembroidery'
            }
            
        except ImportError:
            # Fallback auf manuelle Analyse
            pass
        
        # Manuelle DST-Analyse (Original-Code)
        with open(filepath, 'rb') as f:
            # Header überspringen (512 Bytes)
            f.seek(512)
            
            stitch_count = 0
            min_x = max_x = min_y = max_y = 0
            current_x = current_y = 0
            first_stitch = True
            
            while True:
                # 3 Bytes lesen
                data = f.read(3)
                if len(data) < 3:
                    break
                
                b1, b2, b3 = data
                
                # Delta-Koordinaten dekodieren
                dx = decode_dst_coordinate(b1, b2, 0x01, 0x02, 0x04, 0x08)
                dy = decode_dst_coordinate(b1, b3, 0x10, 0x20, 0x40, 0x80)
                
                current_x += dx
                current_y += dy
                
                # Prüfe ob es ein Stich ist (nicht JUMP oder END)
                if not (b3 & 0x83):  # Kein JUMP/MOVE/END
                    stitch_count += 1
                    
                    if first_stitch:
                        min_x = max_x = current_x
                        min_y = max_y = current_y
                        first_stitch = False
                    else:
                        min_x = min(min_x, current_x)
                        max_x = max(max_x, current_x)
                        min_y = min(min_y, current_y)
                        max_y = max(max_y, current_y)
                
                # Prüfe auf END-Kommando
                if b3 == 0xF3:  # END
                    break
        
        # Dimensionen in mm (DST ist in 1/10 mm)
        width_mm = abs(max_x - min_x) / 10
        height_mm = abs(max_y - min_y) / 10
        
        return {
            'success': True,
            'stitch_count': stitch_count,
            'width_mm': round(width_mm, 1),
            'height_mm': round(height_mm, 1),
            'bounds': {
                'min_x': min_x / 10,
                'max_x': max_x / 10,
                'min_y': min_y / 10,
                'max_y': max_y / 10
            },
            'method': 'manual'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Fehler beim Analysieren der DST-Datei: {str(e)}'
        }

def decode_dst_coordinate(b1, b2, bit1, bit2, bit4, bit8):
    """Dekodiert DST-Koordinaten aus 2 Bytes"""
    val = 0
    if b1 & bit1: val += 1
    if b1 & bit2: val += 2
    if b1 & bit4: val += 4
    if b1 & bit8: val += 8
    if b2 & bit1: val += 16
    if b2 & bit2: val += 32
    if b2 & bit4: val += 64
    if b2 & bit8: val += 128
    
    # Vorzeichenerweiterung für negative Werte
    if val & 0x80:
        val = val - 256
    
    return val

def analyze_image_file(filepath):
    """
    Analysiert Bilddateien (PNG, JPG, etc.) und extrahiert Dimensionen und DPI
    """
    try:
        with Image.open(filepath) as img:
            width, height = img.size
            
            # DPI/PPI Information
            dpi = img.info.get('dpi', (72, 72))
            if isinstance(dpi, (int, float)):
                dpi = (dpi, dpi)
            
            # Dimensionen in cm bei aktueller DPI
            width_cm = (width / dpi[0]) * 2.54
            height_cm = (height / dpi[1]) * 2.54
            
            return {
                'success': True,
                'width_px': width,
                'height_px': height,
                'width_cm': round(width_cm, 1),
                'height_cm': round(height_cm, 1),
                'dpi': dpi,
                'format': img.format,
                'mode': img.mode
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Fehler beim Analysieren der Bilddatei: {str(e)}'
        }

def analyze_svg_file(filepath):
    """
    Analysiert SVG-Dateien und extrahiert Dimensionen
    """
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        # SVG Namespace
        ns = {'svg': 'http://www.w3.org/2000/svg'}
        
        # Versuche width/height Attribute zu finden
        width = root.attrib.get('width', '')
        height = root.attrib.get('height', '')
        
        # ViewBox als Fallback
        viewbox = root.attrib.get('viewBox', '')
        
        def parse_dimension(dim_str):
            """Parst Dimensionsstring (z.B. '100px', '10cm', '50mm')"""
            if not dim_str:
                return None
            
            # Entferne Einheiten und konvertiere
            dim_str = dim_str.strip()
            
            # Regex für Zahl + Einheit
            match = re.match(r'([\d.]+)(\w*)', dim_str)
            if not match:
                return None
            
            value = float(match.group(1))
            unit = match.group(2).lower()
            
            # Konvertiere zu cm
            if unit in ['cm']:
                return value
            elif unit in ['mm']:
                return value / 10
            elif unit in ['px', '']:
                return value / 28.35  # 72 DPI Standard
            elif unit in ['pt']:
                return value / 28.35
            elif unit in ['in']:
                return value * 2.54
            else:
                return value / 28.35  # Fallback zu Pixel
        
        width_cm = parse_dimension(width)
        height_cm = parse_dimension(height)
        
        # Fallback zu ViewBox
        if not width_cm or not height_cm:
            if viewbox:
                parts = viewbox.split()
                if len(parts) >= 4:
                    vb_width = float(parts[2])
                    vb_height = float(parts[3])
                    if not width_cm:
                        width_cm = vb_width / 28.35
                    if not height_cm:
                        height_cm = vb_height / 28.35
        
        return {
            'success': True,
            'width_cm': round(width_cm or 0, 1),
            'height_cm': round(height_cm or 0, 1),
            'original_width': width,
            'original_height': height,
            'viewbox': viewbox
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Fehler beim Analysieren der SVG-Datei: {str(e)}'
        }

def analyze_embroidery_file(filepath):
    """
    Analysiert Stickerei-Dateien verschiedener Formate mit pyembroidery
    """
    try:
        import pyembroidery
        
        # Unterstützte Formate: DST, PES, JEF, EXP, VP3, etc.
        pattern = pyembroidery.read(filepath)
        stitch_count = pattern.count_stitch_commands(pyembroidery.STITCH)
        
        # Bounding Box berechnen
        bounds = pattern.bounds()
        if bounds:
            min_x, min_y, max_x, max_y = bounds
            width_mm = abs(max_x - min_x) / 10  # pyembroidery nutzt 1/10 mm
            height_mm = abs(max_y - min_y) / 10
        else:
            width_mm = height_mm = 0
        
        # Zusätzliche Informationen
        color_count = len(pattern.threadlist) if hasattr(pattern, 'threadlist') else 0
        
        return {
            'success': True,
            'stitch_count': stitch_count,
            'width_mm': round(width_mm, 1),
            'height_mm': round(height_mm, 1),
            'color_count': color_count,
            'bounds': {
                'min_x': min_x / 10 if bounds else 0,
                'max_x': max_x / 10 if bounds else 0,
                'min_y': min_y / 10 if bounds else 0,
                'max_y': max_y / 10 if bounds else 0
            },
            'method': 'pyembroidery'
        }
        
    except ImportError:
        return {
            'success': False,
            'error': 'pyembroidery nicht verfügbar - nur DST-Format mit manueller Analyse unterstützt'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Fehler beim Analysieren der Stickerei-Datei: {str(e)}'
        }

def analyze_design_file(filepath):
    """
    Universelle Analyse-Funktion für verschiedene Dateitypen
    """
    if not os.path.exists(filepath):
        return {'success': False, 'error': 'Datei nicht gefunden'}
    
    _, ext = os.path.splitext(filepath.lower())
    
    # Stickerei-Formate
    embroidery_formats = ['.dst', '.pes', '.jef', '.exp', '.vp3', '.hus', '.xxx', '.pec']
    if ext in embroidery_formats:
        if ext == '.dst':
            # DST hat sowohl pyembroidery als auch manuelle Fallback-Analyse
            return analyze_dst_file(filepath)
        else:
            # Andere Formate nur mit pyembroidery
            return analyze_embroidery_file(filepath)
    
    # Bild-Formate
    elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']:
        return analyze_image_file(filepath)
    
    # Vektor-Formate
    elif ext == '.svg':
        return analyze_svg_file(filepath)
    
    else:
        return {
            'success': False,
            'error': f'Dateityp {ext} wird nicht unterstützt. Unterstützte Formate: DST, PES, JEF, EXP, VP3, SVG, PNG, JPG'
        }