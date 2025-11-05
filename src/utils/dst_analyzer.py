"""
EINFACHE DST-Analyse für StitchAdmin - Maximale Informationen extrahieren
NUR PFAD SPEICHERN - KEINE GRÖSSE
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import struct
import os

def analyze_dst_file_complete(filepath: str) -> dict:
    """
    Extrahiert ALLE verfügbaren Informationen aus DST-Datei
    WICHTIG: Nur Pfad wird gespeichert, Dateigröße ist egal
    """
    try:
        # Pfad speichern - Größe ist egal
        result = {
            'success': True,
            'filepath': filepath,  # NUR PFAD
            'filename': os.path.basename(filepath)
        }
        
        # DST-Datei öffnen
        with open(filepath, 'rb') as f:
            data = f.read()
        
        # Header-Informationen (512 Bytes)
        header = data[:512]
        stitch_data = data[512:]
        
        # ALLE Header-Informationen extrahieren
        header_info = extract_all_header_info(header)
        result.update(header_info)
        
        # ALLE Stich-Informationen extrahieren
        stitch_info = extract_all_stitch_info(stitch_data)
        result.update(stitch_info)
        
        # ALLE Farb-Informationen extrahieren
        color_info = extract_all_color_info(stitch_data)
        result.update(color_info)
        
        # ALLE Dimensions-Informationen extrahieren
        dimension_info = extract_all_dimension_info(stitch_data)
        result.update(dimension_info)
        
        # ALLE Qualitäts-Informationen extrahieren
        quality_info = extract_all_quality_info(stitch_info, dimension_info)
        result.update(quality_info)
        
        # ALLE Produktions-Informationen extrahieren
        production_info = extract_all_production_info(stitch_info, dimension_info)
        result.update(production_info)
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'filepath': filepath  # NUR PFAD, auch bei Fehler
        }

def extract_all_header_info(header: bytes) -> dict:
    """Extrahiert ALLE verfügbaren Header-Informationen"""
    info = {}
    
    # Label (Position 0-20)
    try:
        label = header[0:20].decode('ascii', errors='ignore').strip().rstrip('\\x00')
        if label:
            info['dst_label'] = label
    except:
        pass
    
    # Weitere Header-Segmente durchsuchen
    comments = []
    for i in range(20, 512, 20):
        try:
            chunk = header[i:i+20].decode('ascii', errors='ignore').strip().rstrip('\\x00')
            if chunk and len(chunk) > 2:
                comments.append(chunk)
        except:
            continue
    
    if comments:
        info['dst_comments'] = comments
    
    # Rohe Header-Bytes für weitere Analyse
    info['header_hex'] = header.hex()
    info['header_size'] = len(header)
    
    return info

def extract_all_stitch_info(data: bytes) -> dict:
    """Extrahiert ALLE Stich-Informationen"""
    info = {
        'total_stitches': 0,
        'normal_stitches': 0,
        'jump_stitches': 0,
        'move_stitches': 0,
        'trim_count': 0,
        'color_changes': 0,
        'sequins': 0,
        'stops': 0,
        'unknown_commands': 0,
        'total_length_mm': 0,
        'commands': []
    }
    
    x, y = 0, 0
    i = 0
    
    while i < len(data) - 2:
        try:
            b0, b1, b2 = data[i], data[i+1], data[i+2]
            
            # Ende-Marker
            if b2 == 0xF3:
                break
            
            # Spezial-Befehle
            if b2 & 0xF0 == 0xF0:
                cmd_type = classify_command(b0, b1, b2)
                info['commands'].append({
                    'type': cmd_type,
                    'position': i,
                    'bytes': [b0, b1, b2],
                    'x': x,
                    'y': y
                })
                
                # Zähler erhöhen
                if cmd_type == 'color_change':
                    info['color_changes'] += 1
                elif cmd_type == 'trim':
                    info['trim_count'] += 1
                elif cmd_type == 'sequin':
                    info['sequins'] += 1
                elif cmd_type == 'stop':
                    info['stops'] += 1
                elif cmd_type == 'unknown':
                    info['unknown_commands'] += 1
                
                i += 3
                continue
            
            # Normale Bewegung
            dx, dy = decode_movement(b0, b1, b2)
            old_x, old_y = x, y
            x += dx
            y += dy
            
            # Stich-Länge
            length = (dx**2 + dy**2)**0.5
            info['total_length_mm'] += length / 10
            
            # Stich-Typ klassifizieren
            if abs(dx) <= 121 and abs(dy) <= 121:
                info['normal_stitches'] += 1
            elif abs(dx) > 121 or abs(dy) > 121:
                info['jump_stitches'] += 1
            else:
                info['move_stitches'] += 1
            
            info['total_stitches'] += 1
            i += 3
            
        except:
            i += 1
    
    # Durchschnittliche Stich-Länge
    if info['normal_stitches'] > 0:
        info['avg_stitch_length_mm'] = round(info['total_length_mm'] / info['normal_stitches'], 2)
    
    return info

def extract_all_color_info(data: bytes) -> dict:
    """Extrahiert ALLE Farb-Informationen"""
    info = {
        'color_sequence': [],
        'color_positions': [],
        'estimated_colors': 1
    }
    
    x, y = 0, 0
    current_color = 0
    i = 0
    
    while i < len(data) - 2:
        try:
            b0, b1, b2 = data[i], data[i+1], data[i+2]
            
            if b2 == 0xF3:
                break
            
            if b2 & 0xF0 == 0xF0:
                if b2 == 0xFE and b1 == 0xB0:  # Farbwechsel
                    current_color += 1
                    info['color_sequence'].append(current_color)
                    info['color_positions'].append({'x': x, 'y': y, 'color': current_color})
                i += 3
                continue
            
            # Position tracken
            dx, dy = decode_movement(b0, b1, b2)
            x += dx
            y += dy
            i += 3
            
        except:
            i += 1
    
    info['estimated_colors'] = current_color + 1
    info['total_color_changes'] = len(info['color_sequence'])
    
    return info

def extract_all_dimension_info(data: bytes) -> dict:
    """Extrahiert ALLE Dimensions-Informationen"""
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')
    x = y = 0
    i = 0
    
    while i < len(data) - 2:
        try:
            b0, b1, b2 = data[i], data[i+1], data[i+2]
            
            if b2 == 0xF3:
                break
            
            if b2 & 0xF0 == 0xF0:
                i += 3
                continue
            
            dx, dy = decode_movement(b0, b1, b2)
            x += dx
            y += dy
            
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)
            
            i += 3
            
        except:
            i += 1
    
    # Alle Dimensionen in verschiedenen Einheiten
    width_mm = abs(max_x - min_x) / 10
    height_mm = abs(max_y - min_y) / 10
    
    return {
        'width_mm': round(width_mm, 2),
        'height_mm': round(height_mm, 2),
        'width_cm': round(width_mm / 10, 2),
        'height_cm': round(height_mm / 10, 2),
        'width_inches': round(width_mm / 25.4, 3),
        'height_inches': round(height_mm / 25.4, 3),
        'area_cm2': round((width_mm / 10) * (height_mm / 10), 2),
        'area_inches2': round((width_mm / 25.4) * (height_mm / 25.4), 3),
        'bounding_box': {
            'min_x_mm': round(min_x / 10, 2),
            'max_x_mm': round(max_x / 10, 2),
            'min_y_mm': round(min_y / 10, 2),
            'max_y_mm': round(max_y / 10, 2)
        }
    }

def extract_all_quality_info(stitch_info: dict, dimension_info: dict) -> dict:
    """Extrahiert ALLE Qualitäts-Informationen"""
    area_cm2 = dimension_info.get('area_cm2', 0)
    normal_stitches = stitch_info.get('normal_stitches', 0)
    
    if area_cm2 > 0:
        density = normal_stitches / area_cm2
    else:
        density = 0
    
    # Qualitätsbewertungen
    density_rating = 'Niedrig'
    if density > 900:
        density_rating = 'Sehr hoch'
    elif density > 600:
        density_rating = 'Hoch'
    elif density > 300:
        density_rating = 'Normal'
    
    complexity_score = 0
    if stitch_info.get('color_changes', 0) > 10:
        complexity_score += 3
    if stitch_info.get('jump_stitches', 0) > 50:
        complexity_score += 2
    if normal_stitches > 50000:
        complexity_score += 2
    
    complexity_rating = 'Niedrig'
    if complexity_score >= 6:
        complexity_rating = 'Sehr hoch'
    elif complexity_score >= 4:
        complexity_rating = 'Hoch'
    elif complexity_score >= 2:
        complexity_rating = 'Mittel'
    
    return {
        'density_per_cm2': round(density, 1),
        'density_rating': density_rating,
        'complexity_score': complexity_score,
        'complexity_rating': complexity_rating,
        'total_length_meters': round(stitch_info.get('total_length_mm', 0) / 1000, 3),
        'efficiency_rating': calculate_efficiency_rating(stitch_info)
    }

def extract_all_production_info(stitch_info: dict, dimension_info: dict) -> dict:
    """Extrahiert ALLE Produktions-Informationen"""
    normal_stitches = stitch_info.get('normal_stitches', 0)
    color_changes = stitch_info.get('color_changes', 0)
    
    # Zeitschätzung
    base_time = normal_stitches / 800  # 800 Stiche/Minute
    color_time = color_changes * 2     # 2 Minuten pro Farbwechsel
    setup_time = 5                     # 5 Minuten Setup
    
    total_time = base_time + color_time + setup_time
    
    # Maschinenkompatibilität
    width_mm = dimension_info.get('width_mm', 0)
    height_mm = dimension_info.get('height_mm', 0)
    
    compatible_machines = []
    if width_mm <= 100 and height_mm <= 100:
        compatible_machines.append('Kleinfeld (100x100mm)')
    if width_mm <= 200 and height_mm <= 200:
        compatible_machines.append('Standard (200x200mm)')
    if width_mm <= 400 and height_mm <= 400:
        compatible_machines.append('Großfeld (400x400mm)')
    
    if not compatible_machines:
        compatible_machines.append('Spezialmaschine erforderlich')
    
    # Garnempfehlungen
    density = stitch_info.get('normal_stitches', 0) / max(dimension_info.get('area_cm2', 1), 1)
    
    thread_weight = 'No. 40 (Standard)'
    if density < 400:
        thread_weight = 'No. 30 (Dick)'
    elif density > 700:
        thread_weight = 'No. 50 (Fein)'
    
    # Vlies-Empfehlungen
    backing = 'Mittleres Vlies'
    if density > 800 or normal_stitches > 30000:
        backing = 'Schweres Vlies + Obervlies'
    elif density < 400:
        backing = 'Leichtes Vlies'
    
    return {
        'estimated_time_minutes': round(total_time, 0),
        'estimated_time_hours': round(total_time / 60, 2),
        'compatible_machines': compatible_machines,
        'recommended_thread_weight': thread_weight,
        'recommended_backing': backing,
        'production_difficulty': calculate_production_difficulty(stitch_info, dimension_info)
    }

def classify_command(b0: int, b1: int, b2: int) -> str:
    """Klassifiziert DST-Kommando"""
    if b2 == 0xF3:
        return 'end'
    elif b2 == 0xFE and b1 == 0xB0:
        return 'color_change'
    elif b2 == 0xFB:
        return 'jump'
    elif b2 == 0xFC:
        return 'move'
    elif b2 == 0xFD:
        return 'trim'
    elif b2 == 0xFE:
        return 'sequin'
    elif b2 == 0xFF:
        return 'stop'
    else:
        return 'unknown'

def decode_movement(b0: int, b1: int, b2: int) -> tuple:
    """Dekodiert Bewegung"""
    dx = b0
    if b2 & 0x01:
        dx = -dx
    if b2 & 0x80:
        dx *= 81
    
    dy = b1
    if b2 & 0x02:
        dy = -dy
    if b2 & 0x40:
        dy *= 81
    
    return dx, dy

def calculate_efficiency_rating(stitch_info: dict) -> str:
    """Berechnet Effizienz-Rating"""
    total = stitch_info.get('total_stitches', 0)
    normal = stitch_info.get('normal_stitches', 0)
    
    if total > 0:
        efficiency = normal / total
        if efficiency > 0.9:
            return 'Sehr effizient'
        elif efficiency > 0.7:
            return 'Effizient'
        elif efficiency > 0.5:
            return 'Akzeptabel'
        else:
            return 'Ineffizient'
    return 'Unbekannt'

def calculate_production_difficulty(stitch_info: dict, dimension_info: dict) -> str:
    """Berechnet Produktions-Schwierigkeit"""
    score = 0
    
    if stitch_info.get('color_changes', 0) > 10:
        score += 2
    if stitch_info.get('jump_stitches', 0) > 100:
        score += 2
    if dimension_info.get('width_mm', 0) > 300:
        score += 1
    if stitch_info.get('normal_stitches', 0) > 50000:
        score += 1
    
    if score >= 5:
        return 'Sehr schwierig'
    elif score >= 3:
        return 'Schwierig'
    elif score >= 1:
        return 'Mittel'
    else:
        return 'Einfach'

# Hauptfunktion für einfache Nutzung
def analyze_dst_file_robust(filepath: str) -> dict:
    """
    Hauptfunktion: Analysiert DST-Datei komplett
    WICHTIG: Speichert nur Pfad, Größe ist egal
    """
    result = analyze_dst_file_complete(filepath)
    
    # Kompatibilität: stitch_count aus total_stitches
    if result.get('success') and 'total_stitches' in result:
        result['stitch_count'] = result['total_stitches']
    
    # Kompatibilität: color_count aus estimated_colors
    if result.get('success') and 'estimated_colors' in result:
        result['color_count'] = result['estimated_colors']
    
    return result
