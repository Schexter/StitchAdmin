"""
Design File Browser - Datei-Browser für Design-Auswahl
"""

import os
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from functools import wraps
import mimetypes

# Blueprint für Datei-Browser
file_browser_bp = Blueprint('file_browser', __name__, url_prefix='/file_browser')

def is_design_file(filename):
    """Prüft ob die Datei ein Design-File ist"""
    design_extensions = ['.dst', '.pes', '.jef', '.exp', '.svg', '.ai', '.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.tiff']
    return any(filename.lower().endswith(ext) for ext in design_extensions)

def get_file_icon(filename):
    """Gibt das entsprechende Icon für den Dateityp zurück"""
    filename_lower = filename.lower()
    
    if filename_lower.endswith('.dst'):
        return 'bi-file-earmark-binary'
    elif filename_lower.endswith(('.pes', '.jef', '.exp')):
        return 'bi-file-earmark-code'
    elif filename_lower.endswith('.svg'):
        return 'bi-file-earmark-image'
    elif filename_lower.endswith('.ai'):
        return 'bi-file-earmark-richtext'
    elif filename_lower.endswith('.pdf'):
        return 'bi-file-earmark-pdf'
    elif filename_lower.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
        return 'bi-file-earmark-image'
    elif os.path.isdir(filename):
        return 'bi-folder'
    else:
        return 'bi-file-earmark'

def get_design_directories():
    """Gibt Standard-Design-Verzeichnisse zurück"""
    base_paths = [
        "C:/Designs",
        "C:/SoftwareEntwicklung/StitchAdmin/uploads/designs",
        "C:/Users/Public/Documents/Designs",
        "D:/Designs",
        "E:/Designs"
    ]
    
    existing_paths = []
    for path in base_paths:
        if os.path.exists(path):
            existing_paths.append(path)
    
    # Erstelle Standard-Verzeichnis falls keines existiert
    if not existing_paths:
        default_path = "C:/Designs"
        try:
            os.makedirs(default_path, exist_ok=True)
            existing_paths.append(default_path)
        except:
            pass
    
    return existing_paths

@file_browser_bp.route('/browse')
@login_required
def browse():
    """Datei-Browser für Design-Auswahl"""
    current_path = request.args.get('path', '')
    
    # Sicherheitscheck: Nur erlaubte Pfade
    if not current_path:
        design_dirs = get_design_directories()
        current_path = design_dirs[0] if design_dirs else "C:/"
    
    # Normalisiere den Pfad
    current_path = os.path.normpath(current_path)
    
    # Prüfe ob Pfad existiert
    if not os.path.exists(current_path):
        return jsonify({'error': 'Pfad nicht gefunden'}), 404
    
    # Sammle Dateien und Ordner
    items = []
    
    try:
        # Parent-Verzeichnis hinzufügen (falls nicht Root)
        parent_path = os.path.dirname(current_path)
        if parent_path != current_path and parent_path:
            items.append({
                'name': '..',
                'path': parent_path,
                'type': 'directory',
                'icon': 'bi-arrow-up-circle',
                'is_parent': True
            })
        
        # Durchsuche aktuelles Verzeichnis
        for item_name in sorted(os.listdir(current_path)):
            item_path = os.path.join(current_path, item_name)
            
            # Versteckte Dateien überspringen
            if item_name.startswith('.'):
                continue
            
            if os.path.isdir(item_path):
                items.append({
                    'name': item_name,
                    'path': item_path,
                    'type': 'directory',
                    'icon': 'bi-folder',
                    'is_parent': False
                })
            elif is_design_file(item_name):
                # Datei-Informationen
                stat = os.stat(item_path)
                items.append({
                    'name': item_name,
                    'path': item_path,
                    'type': 'file',
                    'icon': get_file_icon(item_name),
                    'size': stat.st_size,
                    'size_mb': round(stat.st_size / 1024 / 1024, 2),
                    'modified': stat.st_mtime,
                    'is_parent': False
                })
    
    except PermissionError:
        return jsonify({'error': 'Keine Berechtigung für diesen Pfad'}), 403
    except Exception as e:
        return jsonify({'error': f'Fehler beim Lesen des Verzeichnisses: {str(e)}'}), 500
    
    return jsonify({
        'current_path': current_path,
        'items': items,
        'breadcrumbs': get_breadcrumbs(current_path)
    })

def get_breadcrumbs(path):
    """Erstellt Breadcrumb-Navigation für den Pfad"""
    breadcrumbs = []
    parts = path.split(os.sep)
    
    current = ""
    for part in parts:
        if part:  # Überspringe leere Teile
            current = os.path.join(current, part) if current else part
            breadcrumbs.append({
                'name': part,
                'path': current
            })
    
    return breadcrumbs

@file_browser_bp.route('/modal')
@login_required
def modal():
    """Datei-Browser Modal"""
    return render_template('file_browser/modal.html')

@file_browser_bp.route('/get_file_info')
@login_required
def get_file_info():
    """Detaillierte Datei-Informationen"""
    file_path = request.args.get('path')
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'Datei nicht gefunden'}), 404
    
    try:
        stat = os.stat(file_path)
        
        # Basis-Informationen
        file_info = {
            'name': os.path.basename(file_path),
            'path': file_path,
            'size': stat.st_size,
            'size_mb': round(stat.st_size / 1024 / 1024, 2),
            'modified': stat.st_mtime,
            'created': stat.st_ctime,
            'mime_type': mimetypes.guess_type(file_path)[0] or 'unknown'
        }
        
        # Versuche Design-Analyse
        try:
            from src.utils.file_analysis import analyze_design_file
            analysis = analyze_design_file(file_path)
            file_info['analysis'] = analysis
        except:
            file_info['analysis'] = {'success': False, 'error': 'Analyse nicht möglich'}
        
        return jsonify(file_info)
        
    except Exception as e:
        return jsonify({'error': f'Fehler beim Lesen der Datei-Informationen: {str(e)}'}), 500

# Erstellt von Hans Hahn - Alle Rechte vorbehalten