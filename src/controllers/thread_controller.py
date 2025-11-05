"""
Garnfarben-Verwaltung Controller
Verwaltet Garn-Datenbanken, Import/Export und Farbkonvertierungen
"""

from flask import Blueprint, render_template, request, jsonify, send_file, current_app
import json
import os
import csv
from datetime import datetime
from werkzeug.utils import secure_filename
from io import StringIO, BytesIO

thread_bp = Blueprint('thread', __name__, url_prefix='/threads')

# Erlaubte Dateitypen
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'pdf', 'json'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_threads():
    """Lädt Garnfarben aus JSON-Datei"""
    try:
        with open('threads.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            'manufacturers': [],
            'thread_types': [],
            'colors': []
        }

def save_threads(data):
    """Speichert Garnfarben in JSON-Datei"""
    with open('threads.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_threads_dict():
    """Lädt Garnfarben als Dictionary mit ID als Schlüssel"""
    data = load_threads()
    threads_dict = {}
    
    for color in data.get('colors', []):
        thread_id = color.get('id')
        if thread_id:
            threads_dict[thread_id] = {
                'id': thread_id,
                'brand': color.get('manufacturer', ''),
                'color_code': color.get('color_number', ''),
                'color_name': color.get('color_name_de') or color.get('color_name_en', ''),
                'color_hex': color.get('hex_color', '#CCCCCC'),
                'stock': color.get('in_stock', 0)
            }
    
    return threads_dict

def load_thread_stock():
    """Lädt Garnbestand als Dictionary"""
    data = load_threads()
    stock_dict = {}
    
    for color in data.get('colors', []):
        thread_id = color.get('id')
        if thread_id:
            stock_dict[thread_id] = {
                'quantity': color.get('in_stock', 0),
                'location': color.get('stock_location', '')
            }
    
    return stock_dict

@thread_bp.route('/')
def index():
    """Hauptseite der Garnverwaltung"""
    return render_template('thread/index.html')

@thread_bp.route('/colors')
def colors():
    """Zeigt alle Garnfarben"""
    data = load_threads()
    return render_template('thread/colors.html', 
                         colors=data.get('colors', []),
                         manufacturers=data.get('manufacturers', []))

@thread_bp.route('/import')
def import_page():
    """Import-Seite für verschiedene Formate"""
    return render_template('thread/import.html')

@thread_bp.route('/api/colors', methods=['GET'])
def api_get_colors():
    """API: Alle Farben abrufen"""
    data = load_threads()
    
    # Filter anwenden
    manufacturer = request.args.get('manufacturer')
    thread_type = request.args.get('type')
    search = request.args.get('search', '').lower()
    
    colors = data.get('colors', [])
    
    if manufacturer:
        colors = [c for c in colors if c.get('manufacturer') == manufacturer]
    
    if thread_type:
        colors = [c for c in colors if c.get('thread_type') == thread_type]
    
    if search:
        colors = [c for c in colors if 
                 search in c.get('color_number', '').lower() or
                 search in c.get('color_name_de', '').lower() or
                 search in c.get('color_name_en', '').lower()]
    
    return jsonify({
        'success': True,
        'colors': colors,
        'manufacturers': data.get('manufacturers', []),
        'total': len(colors)
    })

@thread_bp.route('/api/print-colors', methods=['GET'])
def api_get_print_colors():
    """API: Druckfarben abrufen (Pantone, RAL, HKS, etc.)"""
    try:
        # Lade Druckfarben
        with open('print_colors.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Filter anwenden
        system = request.args.get('system')  # Pantone, RAL, HKS, etc.
        category = request.args.get('category')  # Standard, Metallic, Neon, etc.
        search = request.args.get('search', '').lower()
        
        colors = data.get('colors', [])
        
        if system:
            colors = [c for c in colors if c.get('system') == system]
        
        if category:
            colors = [c for c in colors if c.get('category') == category]
        
        if search:
            colors = [c for c in colors if 
                     search in c.get('code', '').lower() or
                     search in c.get('name', '').lower() or
                     search in c.get('hex', '').lower() or
                     search in c.get('rgb', '').lower() or
                     search in c.get('cmyk', '').lower()]
        
        return jsonify({
            'success': True,
            'colors': colors,
            'systems': data.get('color_systems', []),
            'categories': data.get('categories', []),
            'total': len(colors)
        })
        
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'error': 'Druckfarben-Datenbank nicht gefunden'
        }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@thread_bp.route('/api/color', methods=['POST'])
def api_add_color():
    """API: Neue Farbe hinzufügen"""
    try:
        color_data = request.json
        data = load_threads()
        
        # Neue Farbe erstellen
        new_color = {
            'id': str(datetime.now().timestamp()),
            'manufacturer': color_data.get('manufacturer'),
            'thread_type': color_data.get('thread_type'),
            'color_number': color_data.get('color_number'),
            'color_name_de': color_data.get('color_name_de'),
            'color_name_en': color_data.get('color_name_en'),
            'hex_color': color_data.get('hex_color'),
            'pantone': color_data.get('pantone'),
            'category': color_data.get('category', 'Standard'),
            'in_stock': color_data.get('in_stock', 0),
            'price': color_data.get('price', 0),
            'created_at': datetime.now().isoformat()
        }
        
        # Prüfe ob Farbe bereits existiert
        existing = next((c for c in data['colors'] if 
                        c['manufacturer'] == new_color['manufacturer'] and
                        c['color_number'] == new_color['color_number']), None)
        
        if existing:
            return jsonify({
                'success': False,
                'message': 'Farbe existiert bereits'
            }), 400
        
        data['colors'].append(new_color)
        save_threads(data)
        
        return jsonify({
            'success': True,
            'color': new_color
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@thread_bp.route('/api/color/<color_id>', methods=['PUT'])
def api_update_color(color_id):
    """API: Farbe aktualisieren"""
    try:
        color_data = request.json
        data = load_threads()
        
        # Farbe finden
        color = next((c for c in data['colors'] if c['id'] == color_id), None)
        if not color:
            return jsonify({
                'success': False,
                'message': 'Farbe nicht gefunden'
            }), 404
        
        # Aktualisieren
        color.update({
            'manufacturer': color_data.get('manufacturer', color['manufacturer']),
            'thread_type': color_data.get('thread_type', color['thread_type']),
            'color_number': color_data.get('color_number', color['color_number']),
            'color_name_de': color_data.get('color_name_de', color['color_name_de']),
            'color_name_en': color_data.get('color_name_en', color['color_name_en']),
            'hex_color': color_data.get('hex_color', color['hex_color']),
            'pantone': color_data.get('pantone', color.get('pantone')),
            'category': color_data.get('category', color.get('category', 'Standard')),
            'in_stock': color_data.get('in_stock', color.get('in_stock', 0)),
            'price': color_data.get('price', color.get('price', 0)),
            'updated_at': datetime.now().isoformat()
        })
        
        save_threads(data)
        
        return jsonify({
            'success': True,
            'color': color
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@thread_bp.route('/api/import/csv', methods=['POST'])
def api_import_csv():
    """API: CSV-Import"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'Keine Datei hochgeladen'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'Keine Datei ausgewählt'
            }), 400
        
        if file and allowed_file(file.filename):
            # CSV lesen
            stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_input = csv.DictReader(stream)
            
            data = load_threads()
            imported = 0
            updated = 0
            
            for row in csv_input:
                # Neue Farbe aus CSV-Zeile erstellen
                new_color = {
                    'id': str(datetime.now().timestamp()) + str(imported),
                    'manufacturer': row.get('Hersteller', ''),
                    'thread_type': row.get('Produktlinie', ''),
                    'color_number': row.get('Farbnummer', ''),
                    'color_name_de': row.get('Farbname_DE', ''),
                    'color_name_en': row.get('Farbname_EN', ''),
                    'hex_color': row.get('HexWert', ''),
                    'pantone': row.get('Pantone', ''),
                    'category': row.get('Kategorie', 'Standard'),
                    'created_at': datetime.now().isoformat()
                }
                
                # Prüfe ob Farbe bereits existiert
                existing = next((c for c in data['colors'] if 
                               c.get('manufacturer') == new_color['manufacturer'] and
                               c.get('color_number') == new_color['color_number']), None)
                
                if existing:
                    # Aktualisiere existierende Farbe
                    existing.update(new_color)
                    updated += 1
                else:
                    # Füge neue Farbe hinzu
                    data['colors'].append(new_color)
                    imported += 1
                
                # Hersteller hinzufügen wenn neu
                if new_color['manufacturer'] and new_color['manufacturer'] not in data['manufacturers']:
                    data['manufacturers'].append(new_color['manufacturer'])
            
            save_threads(data)
            
            return jsonify({
                'success': True,
                'message': f'{imported} Farben importiert, {updated} aktualisiert',
                'imported': imported,
                'updated': updated
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler beim Import: {str(e)}'
        }), 500

@thread_bp.route('/api/export/csv')
def api_export_csv():
    """API: CSV-Export"""
    try:
        data = load_threads()
        colors = data.get('colors', [])
        
        # CSV erstellen
        output = StringIO()
        fieldnames = ['Hersteller', 'Produktlinie', 'Farbnummer', 'Farbname_DE', 
                     'Farbname_EN', 'Pantone', 'HexWert', 'Kategorie', 'Lagerbestand']
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for color in colors:
            writer.writerow({
                'Hersteller': color.get('manufacturer', ''),
                'Produktlinie': color.get('thread_type', ''),
                'Farbnummer': color.get('color_number', ''),
                'Farbname_DE': color.get('color_name_de', ''),
                'Farbname_EN': color.get('color_name_en', ''),
                'Pantone': color.get('pantone', ''),
                'HexWert': color.get('hex_color', ''),
                'Kategorie': color.get('category', 'Standard'),
                'Lagerbestand': color.get('in_stock', 0)
            })
        
        # Als Datei senden
        output.seek(0)
        return send_file(
            BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'garnfarben_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@thread_bp.route('/api/manufacturers', methods=['GET'])
def api_get_manufacturers():
    """API: Hersteller abrufen"""
    data = load_threads()
    return jsonify({
        'success': True,
        'manufacturers': data.get('manufacturers', [])
    })

@thread_bp.route('/api/statistics', methods=['GET'])
def api_get_statistics():
    """API: Statistiken abrufen"""
    data = load_threads()
    colors = data.get('colors', [])
    
    # Statistiken berechnen
    stats = {
        'total_colors': len(colors),
        'manufacturers': {},
        'categories': {},
        'with_hex': sum(1 for c in colors if c.get('hex_color')),
        'with_pantone': sum(1 for c in colors if c.get('pantone')),
        'in_stock': sum(1 for c in colors if c.get('in_stock', 0) > 0)
    }
    
    # Nach Hersteller gruppieren
    for color in colors:
        manufacturer = color.get('manufacturer', 'Unbekannt')
        stats['manufacturers'][manufacturer] = stats['manufacturers'].get(manufacturer, 0) + 1
        
        category = color.get('category', 'Standard')
        stats['categories'][category] = stats['categories'].get(category, 0) + 1
    
    return jsonify({
        'success': True,
        'statistics': stats
    })

@thread_bp.route('/api/analyze/pdf', methods=['POST'])
def api_analyze_pdf():
    """API: PDF-Analyse mit echtem Parser"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'Keine PDF hochgeladen'
            }), 400
        
        file = request.files['file']
        if file and file.filename.endswith('.pdf'):
            # PDF temporär speichern
            filename = secure_filename(file.filename)
            temp_path = os.path.join('uploads', 'temp', filename)
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            file.save(temp_path)
            
            # PDF analysieren
            try:
                from src.utils.pdf_analyzer import ThreadColorPDFAnalyzer
                analyzer = ThreadColorPDFAnalyzer()
            except ImportError:
                # Fallback auf Lite-Version ohne pandas/tabula
                from src.utils.pdf_analyzer_lite import ThreadColorPDFAnalyzerLite
                analyzer = ThreadColorPDFAnalyzerLite()
            
            result = analyzer.analyze_pdf(temp_path)
            
            # Wenn Farben gefunden wurden, importieren
            if result['success'] and result['colors']:
                data = load_threads()
                imported = 0
                updated = 0
                manufacturer = result.get('manufacturer', 'Unbekannt')
                
                for color in result['colors']:
                    # Neue Farbe erstellen
                    new_color = {
                        'id': str(datetime.now().timestamp()) + str(imported),
                        'manufacturer': manufacturer,
                        'thread_type': '',  # Kann später aus PDF extrahiert werden
                        'color_number': color.get('color_number', ''),
                        'color_name_de': color.get('color_name_de', ''),
                        'color_name_en': color.get('color_name_en', ''),
                        'hex_color': color.get('hex_color', ''),
                        'pantone': color.get('pantone', ''),
                        'category': 'Standard',
                        'in_stock': 0,
                        'created_at': datetime.now().isoformat(),
                        'imported_from': filename
                    }
                    
                    # Prüfe ob Farbe bereits existiert
                    existing = next((c for c in data['colors'] if 
                                   c.get('manufacturer') == manufacturer and
                                   c.get('color_number') == new_color['color_number']), None)
                    
                    if existing:
                        # Aktualisiere existierende Farbe nur mit neuen Daten
                        if new_color['hex_color'] and not existing.get('hex_color'):
                            existing['hex_color'] = new_color['hex_color']
                        if new_color['pantone'] and not existing.get('pantone'):
                            existing['pantone'] = new_color['pantone']
                        if new_color['color_name_de'] and not existing.get('color_name_de'):
                            existing['color_name_de'] = new_color['color_name_de']
                        if new_color['color_name_en'] and not existing.get('color_name_en'):
                            existing['color_name_en'] = new_color['color_name_en']
                        existing['updated_at'] = datetime.now().isoformat()
                        updated += 1
                    else:
                        # Füge neue Farbe hinzu
                        data['colors'].append(new_color)
                        imported += 1
                    
                    # Hersteller hinzufügen wenn neu
                    if manufacturer and manufacturer not in data['manufacturers']:
                        data['manufacturers'].append(manufacturer)
                
                save_threads(data)
            
            # Aufräumen
            os.remove(temp_path)
            
            return jsonify({
                'success': True,
                'message': f'{imported} neue Farben importiert, {updated} aktualisiert',
                'colors_found': len(result['colors']),
                'manufacturer': manufacturer,
                'imported': imported,
                'updated': updated
            })
            
    except Exception as e:
        # Aufräumen bei Fehler
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
            
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@thread_bp.route('/converter')
def converter():
    """Farbkonverter zwischen Herstellern"""
    data = load_threads()
    manufacturers = data.get('manufacturers', [])
    return render_template('thread/converter.html', manufacturers=manufacturers)

@thread_bp.route('/api/convert', methods=['POST'])
def api_convert_color():
    """API: Farbe zwischen Herstellern konvertieren"""
    try:
        request_data = request.json
        from_manufacturer = request_data.get('from_manufacturer')
        to_manufacturer = request_data.get('to_manufacturer')
        color_number = request_data.get('color_number')
        
        data = load_threads()
        colors = data.get('colors', [])
        
        # Originalfarbe finden
        original = next((c for c in colors if 
                        c.get('manufacturer') == from_manufacturer and
                        c.get('color_number') == color_number), None)
        
        if not original:
            return jsonify({
                'success': False,
                'message': 'Farbe nicht gefunden'
            }), 404
        
        # Ähnliche Farbe im Zielhersteller finden (vereinfacht: gleicher Hex-Wert)
        hex_color = original.get('hex_color')
        if hex_color:
            matches = [c for c in colors if 
                      c.get('manufacturer') == to_manufacturer and
                      c.get('hex_color') == hex_color]
            
            if matches:
                return jsonify({
                    'success': True,
                    'original': original,
                    'matches': matches
                })
        
        # Keine exakte Übereinstimmung - ähnliche Farben suchen
        # TODO: Implementiere Farbähnlichkeits-Algorithmus
        
        return jsonify({
            'success': True,
            'original': original,
            'matches': [],
            'message': 'Keine exakte Übereinstimmung gefunden'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@thread_bp.route('/web-scraper')
def web_scraper():
    """Advanced Web Scraper für Garnfarben"""
    return render_template('thread/web_scraper.html')

@thread_bp.route('/api/web-scraper/analyze', methods=['POST'])
def api_web_scraper_analyze():
    """API: URL mit Advanced Web Scraper analysieren"""
    try:
        url = request.json.get('url')
        deep_scan = request.json.get('deep_scan', False)
        
        if not url:
            return jsonify({
                'success': False,
                'message': 'Keine URL angegeben'
            }), 400
        
        # Import des Advanced Web Scrapers
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '..'))
        from thread_color_fetcher.advanced_web_scraper import AdvancedWebScraper
        
        scraper = AdvancedWebScraper()
        results = scraper.analyze_url(url, deep_scan=deep_scan)
        
        # Farben in unser Format konvertieren
        converted_colors = []
        for product in results.get('products', []):
            if product.number and product.name:
                converted_colors.append({
                    'color_number': product.number,
                    'color_name': product.name,
                    'hex_color': product.hex_code,
                    'price': product.price,
                    'url': product.url
                })
        
        for color in results.get('colors', []):
            if color.number and color.name:
                converted_colors.append({
                    'color_number': color.number,
                    'color_name': color.name,
                    'hex_color': color.hex_code
                })
        
        return jsonify({
            'success': True,
            'url': url,
            'colors_found': len(converted_colors),
            'colors': converted_colors[:50],  # Max 50 für Vorschau
            'summary': results.get('summary', {}),
            'links': results.get('links', [])
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler bei der Analyse: {str(e)}'
        }), 500

@thread_bp.route('/api/web-scraper/import', methods=['POST'])
def api_web_scraper_import():
    """API: Farben aus Web Scraper importieren"""
    try:
        colors_to_import = request.json.get('colors', [])
        manufacturer = request.json.get('manufacturer', 'Unbekannt')
        
        data = load_threads()
        imported = 0
        updated = 0
        
        for color in colors_to_import:
            new_color = {
                'id': str(datetime.now().timestamp()) + str(imported),
                'manufacturer': manufacturer,
                'thread_type': '',
                'color_number': color.get('color_number'),
                'color_name_de': color.get('color_name'),
                'color_name_en': '',
                'hex_color': color.get('hex_color', ''),
                'pantone': '',
                'category': 'Standard',
                'in_stock': 0,
                'price': color.get('price', 0),
                'created_at': datetime.now().isoformat(),
                'imported_from': 'web_scraper',
                'source_url': color.get('url', '')
            }
            
            # Prüfe ob Farbe bereits existiert
            existing = next((c for c in data['colors'] if 
                           c.get('manufacturer') == manufacturer and
                           c.get('color_number') == new_color['color_number']), None)
            
            if existing:
                # Aktualisiere nur wenn neue Daten vorhanden
                if new_color['hex_color'] and not existing.get('hex_color'):
                    existing['hex_color'] = new_color['hex_color']
                if new_color['price'] and not existing.get('price'):
                    existing['price'] = new_color['price']
                existing['updated_at'] = datetime.now().isoformat()
                updated += 1
            else:
                data['colors'].append(new_color)
                imported += 1
        
        # Hersteller hinzufügen wenn neu
        if manufacturer and manufacturer not in data['manufacturers']:
            data['manufacturers'].append(manufacturer)
        
        save_threads(data)
        
        return jsonify({
            'success': True,
            'imported': imported,
            'updated': updated,
            'message': f'{imported} neue Farben importiert, {updated} aktualisiert'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500