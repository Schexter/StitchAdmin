"""
EINFACHES Design Upload - NUR PFAD SPEICHERN
Gleiche Behandlung für Stickerei UND Druck
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
from werkzeug.utils import secure_filename
from datetime import datetime
from src.utils.dst_analyzer import analyze_dst_file_robust

def save_design_file(file_obj, order_id=None):
    """
    Speichert Design-Datei - NUR PFAD, KEINE GRÖSSE
    Gleiche Behandlung für Stick- und Druckdateien
    """
    try:
        if not file_obj or not file_obj.filename:
            return {'success': False, 'error': 'Keine Datei'}
        
        # Sicherer Dateiname
        filename = secure_filename(file_obj.filename)
        
        # Mit Order-ID ergänzen falls vorhanden
        if order_id:
            name, ext = os.path.splitext(filename)
            filename = f"{order_id}_{name}{ext}"
        
        # Upload-Ordner erstellen
        upload_dir = 'uploads/designs'
        os.makedirs(upload_dir, exist_ok=True)
        
        # Datei speichern
        filepath = os.path.join(upload_dir, filename)
        file_obj.save(filepath)
        
        # NUR PFAD SPEICHERN - GRÖSSE EGAL
        storage_path = f"uploads/designs/{filename}"
        
        # Dateityp bestimmen
        file_type = get_file_type(filename)
        
        # Analyse je nach Typ
        analysis = None
        if file_type == 'embroidery':
            analysis = analyze_dst_file_robust(filepath)
        elif file_type == 'print':
            analysis = analyze_print_file(filepath)
        
        return {
            'success': True,
            'filename': filename,
            'storage_path': storage_path,  # NUR PFAD
            'file_type': file_type,
            'analysis': analysis
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_file_type(filename):
    """Bestimmt Dateityp"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    if ext in ['dst', 'pes', 'jef', 'exp', 'vp3', 'vp4']:
        return 'embroidery'
    elif ext in ['png', 'jpg', 'jpeg', 'svg', 'ai', 'pdf']:
        return 'print'
    else:
        return 'unknown'

def analyze_print_file(filepath):
    """Einfache Analyse für Druckdateien"""
    try:
        from PIL import Image
        
        ext = filepath.rsplit('.', 1)[1].lower()
        
        if ext in ['png', 'jpg', 'jpeg']:
            img = Image.open(filepath)
            
            # DPI
            dpi = img.info.get('dpi', (72, 72))
            if isinstance(dpi, tuple):
                dpi_x, dpi_y = dpi
            else:
                dpi_x = dpi_y = dpi
            
            # Dimensionen
            width_mm = (img.width / dpi_x) * 25.4
            height_mm = (img.height / dpi_y) * 25.4
            
            return {
                'success': True,
                'width_px': img.width,
                'height_px': img.height,
                'width_mm': round(width_mm, 2),
                'height_mm': round(height_mm, 2),
                'width_cm': round(width_mm / 10, 2),
                'height_cm': round(height_mm / 10, 2),
                'dpi_x': dpi_x,
                'dpi_y': dpi_y,
                'mode': img.mode,
                'format': img.format
            }
        else:
            return {
                'success': True,
                'format': ext.upper(),
                'note': 'Begrenzte Analyse für dieses Format'
            }
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def check_for_link(order_id):
    """Prüft ob Link vorhanden ist"""
    try:
        link_file = f"data/links/{order_id}_link.txt"
        return os.path.exists(link_file)
    except:
        return False

def save_link(order_id, url):
    """Speichert Link - NUR PFAD"""
    try:
        os.makedirs('data/links', exist_ok=True)
        
        link_file = f"data/links/{order_id}_link.txt"
        with open(link_file, 'w') as f:
            f.write(url)
        
        return {
            'success': True,
            'storage_path': f"link:{url}",  # NUR PFAD
            'link_file': link_file
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_link(order_id):
    """Holt Link"""
    try:
        link_file = f"data/links/{order_id}_link.txt"
        if os.path.exists(link_file):
            with open(link_file, 'r') as f:
                return f.read().strip()
        return None
    except:
        return None

def needs_graphics_manager(order_id):
    """
    Prüft ob Grafikmanager benötigt wird
    WICHTIG: Wenn Link da ist -> KEIN Grafikmanager
    """
    # Wenn Link vorhanden -> KEIN Grafikmanager
    if check_for_link(order_id):
        return False
    
    # Sonst immer Grafikmanager anzeigen
    return True

def should_show_graphics_manager(order_id):
    """
    Bestimmt ob Grafikmanager angezeigt werden soll
    REGEL: Wenn Link da ist -> Grafikmanager verschwindet
    """
    return not check_for_link(order_id)
