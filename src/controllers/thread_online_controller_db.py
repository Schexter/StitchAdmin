"""
Thread Color Online Controller für StitchAdmin (DB-Version)
===========================================================
Integration des Web Fetchers mit PostgreSQL-Datenbank
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
import pandas as pd
from datetime import datetime
import json
import sys
import os

# Füge thread_color_fetcher zum Python-Pfad hinzu
import sys
import os

# Verschiedene Pfade probieren
possible_paths = [
    os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'thread_color_fetcher'),
    os.path.join(os.path.dirname(__file__), '..', '..', '..', 'thread_color_fetcher'),
    os.path.join(os.path.dirname(__file__), '..', '..', 'thread_color_fetcher'),
    'C:\\SoftwareEntwicklung\\StitchAdmin\\thread_color_fetcher'
]

for path in possible_paths:
    if os.path.exists(path):
        sys.path.append(path)
        break

from thread_color_web_fetcher import ThreadColorWebFetcher
from madeira_scraper import MadeiraWebScraper

# Blueprint erstellen
thread_online_bp = Blueprint('thread_online', __name__, url_prefix='/thread/online')


@thread_online_bp.route('/')
@login_required
def index():
    """Hauptseite des Online Thread Color Fetchers"""
    return render_template('thread/online/index.html')


@thread_online_bp.route('/api/search', methods=['POST'])
@login_required
def search_colors():
    """API-Endpoint für die Farbsuche"""
    data = request.get_json()
    manufacturer = data.get('manufacturer', '').lower()
    search_type = data.get('search_type', 'all')  # all, number, name, color
    search_value = data.get('search_value', '')
    
    try:
        fetcher = ThreadColorWebFetcher()
        
        # Hole Daten vom Hersteller
        if manufacturer in fetcher.scrapers:
            results = fetcher.fetch_all_manufacturers([manufacturer])
            
            if results[manufacturer]['status'] == 'success':
                colors = results[manufacturer]['data']
                
                # Filter anwenden
                if search_type == 'number' and search_value:
                    colors = [c for c in colors if search_value.lower() in str(c.get('number', '')).lower()]
                elif search_type == 'name' and search_value:
                    colors = [c for c in colors if search_value.lower() in c.get('name', '').lower()]
                elif search_type == 'color' and search_value:
                    # Hex-Code-Suche
                    colors = [c for c in colors if search_value.lower() in c.get('hex_code', '').lower()]
                
                return jsonify({
                    'success': True,
                    'count': len(colors),
                    'colors': colors[:100]  # Maximal 100 Ergebnisse
                })
            else:
                return jsonify({
                    'success': False,
                    'error': results[manufacturer].get('error', 'Keine Daten gefunden')
                })
        else:
            return jsonify({
                'success': False,
                'error': f'Hersteller {manufacturer} nicht unterstützt'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@thread_online_bp.route('/api/import', methods=['POST'])
@login_required
def import_colors():
    """Importiert ausgewählte Farben in die Datenbank"""
    data = request.get_json()
    manufacturer = data.get('manufacturer')
    color_ids = data.get('color_ids', [])
    import_all = data.get('import_all', False)
    
    try:
        from src.models import db, Thread
        
        fetcher = ThreadColorWebFetcher()
        results = fetcher.fetch_all_manufacturers([manufacturer])
        
        if results[manufacturer]['status'] == 'success':
            colors = results[manufacturer]['data']
            
            # Filter nach ausgewählten IDs oder alle
            if not import_all and color_ids:
                colors = [c for c in colors if c.get('number') in color_ids]
            
            imported = 0
            updated = 0
            errors = []
            
            for color_data in colors:
                try:
                    # Prüfe ob Farbe bereits existiert
                    existing = Thread.query.filter_by(
                        manufacturer=manufacturer.upper(),
                        color_number=color_data.get('number')
                    ).first()
                    
                    if existing:
                        # Update
                        existing.color_name = color_data.get('name', existing.color_name)
                        existing.hex_code = color_data.get('hex_code', existing.hex_code)
                        existing.rgb = color_data.get('rgb', existing.rgb)
                        existing.pantone_code = color_data.get('pantone', existing.pantone_code)
                        existing.updated_at = datetime.now()
                        updated += 1
                    else:
                        # Neu anlegen
                        new_color = Thread(
                            manufacturer=manufacturer.upper(),
                            color_number=color_data.get('number'),
                            color_name=color_data.get('name'),
                            hex_code=color_data.get('hex_code'),
                            rgb=color_data.get('rgb'),
                            pantone_code=color_data.get('pantone'),
                            category=color_data.get('type', 'Standard'),
                            in_stock=True,
                            stock_amount=0
                        )
                        db.session.add(new_color)
                        imported += 1
                        
                except Exception as e:
                    errors.append(f"Fehler bei {color_data.get('number')}: {str(e)}")
            
            # Commit
            db.session.commit()
            
            # Activity Log
            from src.models import ActivityLog
            activity = ActivityLog(
                username=current_user.username,
                action='thread_color_import',
                details=f'Imported {imported} and updated {updated} colors from {manufacturer} via web fetcher',
                ip_address=request.remote_addr
            )
            db.session.add(activity)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'imported': imported,
                'updated': updated,
                'errors': errors,
                'message': f'{imported} neue Farben importiert, {updated} aktualisiert'
            })
            
        else:
            return jsonify({
                'success': False,
                'error': 'Keine Daten zum Importieren gefunden'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@thread_online_bp.route('/api/manufacturers', methods=['GET'])
@login_required
def get_manufacturers():
    """Gibt verfügbare Hersteller und deren Status zurück"""
    fetcher = ThreadColorWebFetcher()
    
    from src.models import Thread
    
    manufacturers = []
    for key, scraper in fetcher.scrapers.items():
        # Prüfe ob Hersteller in DB vorhanden
        count = Thread.query.filter_by(manufacturer=key.upper()).count()
        
        manufacturers.append({
            'id': key,
            'name': key.title(),
            'available': True,
            'colors_in_db': count,
            'last_sync': None  # TODO: Aus Activity Log holen
        })
    
    return jsonify({
        'success': True,
        'manufacturers': manufacturers
    })


@thread_online_bp.route('/api/sync', methods=['POST'])
@login_required
def sync_manufacturer():
    """Synchronisiert alle Farben eines Herstellers"""
    data = request.get_json()
    manufacturer = data.get('manufacturer')
    
    try:
        fetcher = ThreadColorWebFetcher()
        results = fetcher.fetch_all_manufacturers([manufacturer])
        
        if results[manufacturer]['status'] == 'success':
            # Automatisch alle importieren
            import_data = {
                'manufacturer': manufacturer,
                'import_all': True
            }
            
            # Rufe Import-Funktion auf
            request._cached_json = import_data
            return import_colors()
        else:
            return jsonify({
                'success': False,
                'error': results[manufacturer].get('error', 'Sync fehlgeschlagen')
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@thread_online_bp.route('/api/match', methods=['POST'])
@login_required
def match_color():
    """Findet ähnliche Farben basierend auf Hex-Code"""
    data = request.get_json()
    hex_code = data.get('hex_code', '').strip()
    tolerance = data.get('tolerance', 50)
    
    if not hex_code:
        return jsonify({
            'success': False,
            'error': 'Kein Hex-Code angegeben'
        })
    
    try:
        # Nutze Madeira Scraper für Farb-Matching
        scraper = MadeiraWebScraper()
        similar_colors = scraper.find_similar_colors(hex_code, tolerance)
        
        # Erweitere auf andere Hersteller
        all_matches = []
        
        # TODO: Implementiere Farb-Matching für alle Hersteller
        
        return jsonify({
            'success': True,
            'matches': similar_colors[:20],  # Top 20 Matches
            'hex_code': hex_code
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@thread_online_bp.route('/preview/<manufacturer>')
@login_required
def preview_manufacturer(manufacturer):
    """Zeigt Vorschau der verfügbaren Farben eines Herstellers"""
    try:
        fetcher = ThreadColorWebFetcher()
        results = fetcher.fetch_all_manufacturers([manufacturer])
        
        if results[manufacturer]['status'] == 'success':
            colors = results[manufacturer]['data']
            
            return render_template('thread/online/preview.html',
                manufacturer=manufacturer.title(),
                colors=colors[:50],  # Erste 50 als Vorschau
                total_count=len(colors)
            )
        else:
            flash(f"Fehler beim Abrufen der {manufacturer.title()} Farben", 'error')
            return redirect(url_for('thread_online.index'))
            
    except Exception as e:
        flash(f"Fehler: {str(e)}", 'error')
        return redirect(url_for('thread_online.index'))


# Registriere Blueprint in der Haupt-App
def register_thread_online_blueprint(app):
    """Registriert den Thread Online Blueprint"""
    app.register_blueprint(thread_online_bp)
