"""
Order Controller - Kundenaufträge für Stickerei & Textildruck
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
import json
import os
from datetime import datetime
from werkzeug.utils import secure_filename

# Blueprint erstellen
order_bp = Blueprint('orders', __name__, url_prefix='/orders')

ORDERS_FILE = 'customer_orders.json'
MATERIAL_PRICES_FILE = 'material_prices.json'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Bitte melden Sie sich an.', 'info')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def safe_int(value, default=0):
    """Konvertiert Wert sicher zu Integer"""
    try:
        return int(value) if value and str(value).strip() else default
    except (ValueError, TypeError):
        return default

def safe_float(value, default=0.0):
    """Konvertiert Wert sicher zu Float"""
    try:
        return float(value) if value and str(value).strip() else default
    except (ValueError, TypeError):
        return default

def load_orders():
    """Lade Kundenaufträge aus JSON-Datei"""
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_orders(orders):
    """Speichere Kundenaufträge in JSON-Datei"""
    with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(orders, f, indent=2, ensure_ascii=False)

def generate_order_id():
    """Generiere neue Auftrags-ID"""
    orders = load_orders()
    current_year = datetime.now().year
    year_suffix = str(current_year)[-2:]  # z.B. "24" für 2024
    
    if not orders:
        return f"A{current_year}-001"
    
    # Finde höchste ID für das aktuelle Jahr
    max_num = 0
    prefix = f"A{current_year}-"
    for order_id in orders.keys():
        if order_id.startswith(prefix):
            try:
                num = int(order_id.split('-')[1])
                max_num = max(max_num, num)
            except:
                pass
    
    return f"A{current_year}-{max_num + 1:03d}"

def load_material_prices():
    """Lade Material-Preise aus JSON-Datei"""
    if os.path.exists(MATERIAL_PRICES_FILE):
        with open(MATERIAL_PRICES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    # Standard-Preise
    return {
        'textile_prices': {
            't-shirt': 5.00,
            'polo': 8.00,
            'hoodie': 15.00,
            'pullover': 12.00,
            'jacket': 20.00,
            'cap': 4.00,
            'bag': 6.00,
            'other': 10.00
        },
        'embroidery': {
            'price_per_1000_stitches': 1.50,
            'setup_fee': 15.00,
            'thread_price_per_cone': 3.50
        },
        'dtf': {
            'film_price_per_meter': 12.00,  # bei 60cm Breite
            'powder_price_per_kg': 18.00,
            'ink_price_per_liter': 45.00,
            'powder_usage_per_m2': 0.08,  # kg/m²
            'ink_coverage': 0.012,  # Liter/m² bei 50% Deckung
            'waste_factor': 1.15,  # 15% Verschnitt
            'energy_cost_per_m2': 0.50,
            'labor_cost_per_print': 2.00
        },
        'sublimation': {
            'paper_prices': {
                'standard': 2.50,  # €/m²
                'premium': 4.00,
                'textile': 3.20
            },
            'ink_price_per_liter': 65.00,
            'ink_coverage': 0.008,  # Liter/m²
            'heat_press_cost': 0.50,
            'labor_cost': 3.00
        }
    }

def calculate_embroidery_price(stitch_count, quantity, textile_type='t-shirt'):
    """Berechnet Stickerei-Preis basierend auf Stichzahl und Menge"""
    prices = load_material_prices()
    
    # Textilpreis
    base_textile = prices['textile_prices'].get(textile_type, 10.00)
    
    # Stickerei-Kosten
    price_per_1000 = prices['embroidery']['price_per_1000_stitches']
    setup_fee = prices['embroidery']['setup_fee']
    
    embroidery_cost = (stitch_count / 1000) * price_per_1000
    unit_price = base_textile + embroidery_cost
    
    # Mengenstaffel aus Einstellungen
    discounts = prices.get('discounts', {})
    if quantity >= 500:
        discount = discounts.get('qty_500', 30) / 100
    elif quantity >= 250:
        discount = discounts.get('qty_250', 25) / 100
    elif quantity >= 100:
        discount = discounts.get('qty_100', 20) / 100
    elif quantity >= 50:
        discount = discounts.get('qty_50', 15) / 100
    elif quantity >= 25:
        discount = discounts.get('qty_25', 10) / 100
    elif quantity >= 10:
        discount = discounts.get('qty_10', 5) / 100
    else:
        discount = 0
    
    subtotal = unit_price * quantity
    discount_amount = subtotal * discount
    total = subtotal - discount_amount + setup_fee
    
    return {
        'unit_price': round(unit_price, 2),
        'subtotal': round(subtotal, 2),
        'discount_percent': discount * 100,
        'discount_amount': round(discount_amount, 2),
        'setup_fee': setup_fee,
        'total': round(total, 2)
    }

def calculate_order_thread_usage(order):
    """Berechnet Garnverbrauch für einen Auftrag"""
    try:
        from src.controllers.thread_controller import calculate_thread_usage
        
        order_type = order.get('order_type', 'embroidery')
        if order_type not in ['embroidery', 'combined']:
            return {}
        
        stitch_count = order.get('stitch_count', 5000)
        thread_colors = order.get('thread_colors', '').split(',')
        thread_changes = max(1, len([c for c in thread_colors if c.strip()]))
        quantity = order.get('quantity', 1)
        
        # Berechne Garnverbrauch pro Stück
        usage_per_piece = calculate_thread_usage(stitch_count, thread_changes)
        total_usage = usage_per_piece * quantity
        
        return {
            'stitch_count': stitch_count,
            'thread_colors_count': thread_changes,
            'usage_per_piece_meters': usage_per_piece,
            'total_usage_meters': total_usage,
            'thread_colors': [c.strip() for c in thread_colors if c.strip()]
        }
        
    except ImportError:
        return {}
    except Exception:
        return {}

def calculate_dtf_price(width_cm, height_cm, quantity, coverage_percent=50, production_type='internal'):
    """Berechnet DTF-Preis basierend auf tatsächlichen Materialkosten"""
    prices = load_material_prices()['dtf']
    
    # Fläche in m²
    area_m2 = (width_cm * height_cm) / 10000
    
    if production_type == 'internal':
        # Eigene Produktion - detaillierte Materialkalkulation
        film_width_m = 0.60  # Standard DTF-Rolle 60cm
        film_length_m = (height_cm / 100) * prices['waste_factor']
        
        # Materialkosten
        film_cost = film_length_m * prices['film_price_per_meter']
        powder_cost = area_m2 * prices['powder_usage_per_m2'] * prices['powder_price_per_kg']
        ink_cost = area_m2 * prices['ink_coverage'] * (coverage_percent/50) * prices['ink_price_per_liter']
        
        # Produktionskosten
        material_cost = film_cost + powder_cost + ink_cost
        production_cost = prices['energy_cost_per_m2'] * area_m2 + prices['labor_cost_per_print']
        
        unit_cost = material_cost + production_cost
        
        # Mengenstaffel aus Einstellungen
        discount_settings = prices.get('discounts', {})
        if quantity >= 500:
            discount = discount_settings.get('qty_500', 30) / 100
        elif quantity >= 250:
            discount = discount_settings.get('qty_250', 25) / 100
        elif quantity >= 100:
            discount = discount_settings.get('qty_100', 20) / 100
        elif quantity >= 50:
            discount = discount_settings.get('qty_50', 15) / 100
        elif quantity >= 25:
            discount = discount_settings.get('qty_25', 10) / 100
        elif quantity >= 10:
            discount = discount_settings.get('qty_10', 5) / 100
        else:
            discount = 0
            
        unit_cost *= (1 - discount)
        
        return {
            'film_cost': round(film_cost, 2),
            'powder_cost': round(powder_cost, 2),
            'ink_cost': round(ink_cost, 2),
            'material_total': round(material_cost, 2),
            'production_cost': round(production_cost, 2),
            'unit_cost': round(unit_cost, 2),
            'total_cost': round(unit_cost * quantity, 2),
            'film_usage_m': round(film_length_m, 2),
            'coverage_m2': round(area_m2, 4)
        }
    else:
        # Lieferantenbezug - vereinfachte Kalkulation
        base_price = area_m2 * 180  # 0.018€/cm² = 180€/m²
        if quantity >= 100:
            base_price *= 0.75
        elif quantity >= 50:
            base_price *= 0.85
        
        return {
            'unit_cost': round(base_price, 2),
            'total_cost': round(base_price * quantity, 2),
            'supplier': True
        }

@order_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Neuen Kundenauftrag erstellen"""
    from src.controllers.customer_controller import load_customers
    from src.controllers.article_controller import load_articles
    customers = load_customers()
    articles = load_articles()
    
    if request.method == 'POST':
        orders = load_orders()
        order_id = generate_order_id()
        
        customer_id = request.form.get('customer_id')
        if not customer_id or customer_id not in customers:
            flash('Bitte wählen Sie einen Kunden aus!', 'danger')
            return render_template('orders/new.html', customers=customers, articles=articles)
        
        try:
            price = safe_float(request.form.get('price'), 0)
            if price <= 0:
                raise ValueError
        except ValueError:
            flash('Ungültiger Preis!', 'danger')
            return render_template('orders/new.html', customers=customers, articles=articles)
        
        # Verarbeite Textil-Items
        article_ids = request.form.getlist('article_id[]')
        quantities = request.form.getlist('quantity[]')
        textile_sizes = request.form.getlist('textile_size[]')
        textile_color_notes = request.form.getlist('textile_color_note[]')
        
        textile_items = []
        total_quantity = 0
        
        for i, article_id in enumerate(article_ids):
            if article_id and i < len(quantities):
                quantity = safe_int(quantities[i], 0)
                if quantity > 0:
                    article = articles.get(article_id, {})
                    
                    # Verwende Artikel-Größe falls nicht überschrieben
                    final_size = textile_sizes[i] if i < len(textile_sizes) and textile_sizes[i] else article.get('size', '')
                    
                    # Verwende Artikel-Farbe als Basis, ergänze mit Notiz
                    article_color = article.get('color', '')
                    color_note = textile_color_notes[i] if i < len(textile_color_notes) else ''
                    final_color = f"{article_color} {color_note}".strip() if article_color else color_note
                    
                    textile_items.append({
                        'article_id': article_id,
                        'article_name': article.get('name', ''),
                        'article_sku': article.get('sku', ''),
                        'article_material': article.get('material', ''),
                        'quantity': quantity,
                        'size': final_size,
                        'original_article_size': article.get('size', ''),
                        'color_note': final_color,
                        'original_article_color': article.get('color', ''),
                        'price': article.get('price', 0),
                        'weight': article.get('weight', 0.5)
                    })
                    total_quantity += quantity
        
        if not textile_items:
            flash('Bitte wählen Sie mindestens ein Textil aus!', 'danger')
            return render_template('orders/new.html', customers=customers, articles=articles)

        customer = customers[customer_id]
        customer_name = get_customer_display_name(customer)
        order = {
            'id': order_id,
            'customer_id': customer_id,
            'customer_name': customer_name,
            'order_type': request.form.get('order_type', 'embroidery'),  # embroidery, printing, combined
            'description': request.form.get('description', ''),
            'price': price,
            'status': 'accepted',  # accepted, in_progress, ready, completed, cancelled
            'priority': request.form.get('priority', 'normal'),  # urgent, high, normal, low
            'pickup_date': request.form.get('pickup_date', ''),
            'notes': request.form.get('notes', ''),
            'created_at': datetime.now().isoformat(),
            'created_by': session['username'],
            # Textil-Items (neue Struktur)
            'textile_items': textile_items,
            'quantity': total_quantity,  # Gesamtmenge
            # Legacy-Felder für Kompatibilität (aus erstem Item)
            'textile_type': textile_items[0]['article_name'] if textile_items else '',
            'textile_size': textile_items[0]['size'] if textile_items else '',
            'textile_color': textile_items[0]['color_note'] if textile_items else '',
            # Design-Details
            'design_description': request.form.get('design_description', ''),
            'embroidery_position': request.form.get('embroidery_position', ''),  # Brust links, Rücken, etc.
            'embroidery_size': request.form.get('embroidery_size', ''),  # in cm
            'thread_colors': request.form.get('thread_colors', ''),
            'selected_threads': json.loads(request.form.get('selected_threads', '[]')),
            'print_method': request.form.get('print_method', ''),  # DTG, Flex, Flock, Siebdruck
            'print_colors': request.form.get('print_colors', ''),
            'selected_print_colors': json.loads(request.form.get('selected_print_colors', '[]')),
            'print_position': request.form.get('print_position', ''),
            'special_instructions': request.form.get('special_instructions', ''),
            'rush_order': request.form.get('rush_order') == 'on',
            'design_file_path': '',  # Später für File-Upload
            'estimated_completion_days': request.form.get('estimated_completion_days', ''),
            # Neue Felder für professionelle Kalkulation
            'stitch_count': safe_int(request.form.get('stitch_count'), 0),
            'design_width_mm': safe_int(request.form.get('design_width_mm'), 0),
            'design_height_mm': safe_int(request.form.get('design_height_mm'), 0),
            'num_color_changes': safe_int(request.form.get('num_color_changes'), 0),
            'print_width_cm': safe_float(request.form.get('print_width_cm'), 0.0),
            'print_height_cm': safe_float(request.form.get('print_height_cm'), 0.0),
            'production_type': request.form.get('production_type', 'internal'),
            'ink_coverage_percent': safe_int(request.form.get('ink_coverage_percent'), 50),
            'calculated_price': request.form.get('calculated_price', ''),
            # Garnverbrauch wird später berechnet
            'thread_usage': {}
        }
        
        # Design-Workflow verarbeiten
        design_status = request.form.get('design_status')
        if design_status == 'logo_available':
            # Logo vorhanden - Pfad oder Upload
            design_file_path = request.form.get('design_file_path')
            
            # Prüfe erst Upload, dann Pfad
            if 'design_file' in request.files:
                file = request.files['design_file']
                if file and file.filename:
                    # Datei-Upload verarbeiten
                    filename = secure_filename(file.filename)
                    filename = f"{order_id}_{filename}"
                    upload_dir = os.path.join('uploads', 'designs')
                    os.makedirs(upload_dir, exist_ok=True)
                    filepath = os.path.join(upload_dir, filename)
                    file.save(filepath)
                    order['design_file_path'] = filepath
                    order['design_status'] = 'customer_provided'
                    
                    # Datei analysieren
                    try:
                        from src.utils.file_analysis import analyze_design_file
                        analysis = analyze_design_file(filepath)
                        
                        if analysis['success']:
                            order['file_analysis'] = analysis
                            
                            # Automatisch Felder ausfüllen
                            if analysis.get('stitch_count'):
                                if not order['stitch_count']:
                                    order['stitch_count'] = analysis['stitch_count']
                                if not order['design_width_mm']:
                                    order['design_width_mm'] = int(analysis['width_mm'])
                                if not order['design_height_mm']:
                                    order['design_height_mm'] = int(analysis['height_mm'])
                            
                            elif analysis.get('width_cm'):
                                if not order['print_width_cm']:
                                    order['print_width_cm'] = analysis['width_cm']
                                if not order['print_height_cm']:
                                    order['print_height_cm'] = analysis['height_cm']
                    
                    except Exception as e:
                        order['notes'] = (order['notes'] + '\n' if order['notes'] else '') + \
                                       f"Dateianalyse-Fehler: {str(e)}"
            
            elif design_file_path and os.path.exists(design_file_path):
                # Pfad zu bestehender Datei
                order['design_file_path'] = design_file_path
                order['design_status'] = 'customer_provided'
                
                # Datei analysieren
                try:
                    from src.utils.file_analysis import analyze_design_file
                    analysis = analyze_design_file(design_file_path)
                    
                    if analysis['success']:
                        order['file_analysis'] = analysis
                        
                        # Automatisch Felder ausfüllen
                        if analysis.get('stitch_count'):
                            if not order['stitch_count']:
                                order['stitch_count'] = analysis['stitch_count']
                            if not order['design_width_mm']:
                                order['design_width_mm'] = int(analysis['width_mm'])
                            if not order['design_height_mm']:
                                order['design_height_mm'] = int(analysis['height_mm'])
                        
                        elif analysis.get('width_cm'):
                            if not order['print_width_cm']:
                                order['print_width_cm'] = analysis['width_cm']
                            if not order['print_height_cm']:
                                order['print_height_cm'] = analysis['height_cm']
                
                except Exception as e:
                    order['notes'] = (order['notes'] + '\n' if order['notes'] else '') + \
                                   f"Dateianalyse-Fehler: {str(e)}"
        
        elif design_status == 'logo_needs_creation':
            # Logo muss erstellt werden
            order['design_status'] = 'needs_creation'
            order['designer_id'] = request.form.get('designer_id')
            order['design_estimated_date'] = request.form.get('design_estimated_date')
            order['design_requirements'] = request.form.get('design_requirements')
            order['design_priority'] = request.form.get('design_priority', 'normal')
            order['design_cost'] = safe_float(request.form.get('design_cost'), 0)
        
        elif design_status == 'logo_needs_adaptation':
            # Logo muss angepasst werden
            order['design_status'] = 'needs_adaptation'
            order['original_logo_path'] = request.form.get('original_logo_path')
            order['adaptation_days'] = safe_int(request.form.get('adaptation_days'), 2)
            order['adaptation_details'] = request.form.get('adaptation_details')
            order['target_format'] = request.form.get('target_format')
            order['adaptation_cost'] = safe_float(request.form.get('adaptation_cost'), 0)
        
        # Speichere Design-Status
        order['design_workflow_status'] = design_status
        
        # Garnverbrauch berechnen
        order['thread_usage'] = calculate_order_thread_usage(order)
        
        orders[order_id] = order
        save_orders(orders)
        
        flash(f'Auftrag {order_id} wurde erstellt!', 'success')
        return redirect(url_for('orders.show', order_id=order_id))
    
    return render_template('orders/new.html', customers=customers, articles=articles)

@order_bp.route('/')
@login_required
def index():
    """Aufträge-Übersicht"""
    orders = load_orders()
    
    # Lade Kunden für Namen-Updates
    from src.controllers.customer_controller import load_customers
    customers = load_customers()
    
    # Aktualisiere Kundennamen in bestehenden Aufträgen (für Abwärtskompatibilität)
    updated = False
    for order_id, order in orders.items():
        customer_id = order.get('customer_id')
        if customer_id and customer_id in customers:
            customer = customers[customer_id]
            correct_name = get_customer_display_name(customer)
            if order.get('customer_name') != correct_name:
                order['customer_name'] = correct_name
                updated = True
    
    if updated:
        save_orders(orders)
    
    # Nach Status filtern
    status_filter = request.args.get('status', '')
    
    if status_filter:
        filtered_orders = {
            oid: order for oid, order in orders.items() 
            if order.get('status') == status_filter
        }
    else:
        filtered_orders = orders
    
    # Nach Datum sortieren (neueste zuerst)
    sorted_orders = sorted(
        filtered_orders.items(),
        key=lambda x: x[1].get('created_at', ''),
        reverse=True
    )
    
    return render_template('orders/index.html', 
                         orders=dict(sorted_orders),
                         status_filter=status_filter)

@order_bp.route('/<order_id>/status', methods=['POST'])
@login_required
def update_status(order_id):
    """Auftragsstatus aktualisieren"""
    orders = load_orders()
    order = orders.get(order_id)
    
    if not order:
        flash('Auftrag nicht gefunden!', 'danger')
        return redirect(url_for('orders.index'))
    
    new_status = request.form.get('status')
    valid_statuses = ['accepted', 'in_progress', 'ready', 'completed', 'cancelled']
    if new_status not in valid_statuses:
        flash('Ungültiger Status!', 'danger')
        return redirect(url_for('orders.index'))
    
    old_status = order['status']
    order['status'] = new_status
    order['updated_at'] = datetime.now().isoformat()
    order['updated_by'] = session['username']
    
    # Bei Fertigstellung: Abschlussdatum setzen
    if new_status == 'completed' and old_status != 'completed':
        order['completed_at'] = datetime.now().isoformat()
    
    save_orders(orders)
    
    status_names = {
        'accepted': 'Angenommen',
        'in_progress': 'In Arbeit', 
        'ready': 'Abholbereit',
        'completed': 'Abgeholt',
        'cancelled': 'Storniert'
    }
    
    flash(f'Status von Auftrag {order_id} wurde auf "{status_names.get(new_status, new_status)}" geändert!', 'success')
    return redirect(url_for('orders.index'))

@order_bp.route('/<order_id>')
@login_required
def show(order_id):
    """Auftragsdetails anzeigen"""
    orders = load_orders()
    order = orders.get(order_id)
    
    if not order:
        flash('Auftrag nicht gefunden!', 'danger')
        return redirect(url_for('orders.index'))
    
    # Lade zugehörigen Kunden
    from src.controllers.customer_controller import load_customers
    customers = load_customers()
    customer = customers.get(order['customer_id'])
    
    # Aktualisiere Kundenname falls nötig (für Abwärtskompatibilität)
    if customer and (not order.get('customer_name') or order['customer_name'] != get_customer_display_name(customer)):
        order['customer_name'] = get_customer_display_name(customer)
        save_orders(orders)
    
    return render_template('orders/show.html', 
                         order=order, 
                         customer=customer)

def get_customer_display_name(customer):
    """Gibt den korrekten Anzeigenamen für einen Kunden zurück"""
    if customer.get('customer_type') == 'business':
        return customer.get('company_name') or customer.get('display_name', 'Unbekannter Geschäftskunde')
    else:
        return customer.get('display_name') or f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()

@order_bp.route('/<order_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(order_id):
    """Auftrag bearbeiten"""
    orders = load_orders()
    order = orders.get(order_id)
    
    if not order:
        flash('Auftrag nicht gefunden!', 'danger')
        return redirect(url_for('orders.index'))
    
    from src.controllers.customer_controller import load_customers
    from src.controllers.article_controller import load_articles
    customers = load_customers()
    articles = load_articles()
    
    if request.method == 'POST':
        try:
            price = safe_float(request.form.get('price'), 0)
            if price <= 0:
                raise ValueError
        except ValueError:
            flash('Ungültiger Preis!', 'danger')
            return render_template('orders/edit.html', order=order, customers=customers, articles=articles)
        
        # Update order details
        order['description'] = request.form.get('description', '')
        order['price'] = price
        order['priority'] = request.form.get('priority', 'normal')
        order['pickup_date'] = request.form.get('pickup_date', '')
        order['notes'] = request.form.get('notes', '')
        order['quantity'] = int(request.form.get('quantity', order.get('quantity', 1)))
        order['textile_type'] = request.form.get('textile_type', '')
        order['textile_size'] = request.form.get('textile_size', '')
        order['textile_color'] = request.form.get('textile_color', '')
        order['design_description'] = request.form.get('design_description', '')
        order['embroidery_position'] = request.form.get('embroidery_position', '')
        order['embroidery_size'] = request.form.get('embroidery_size', '')
        order['thread_colors'] = request.form.get('thread_colors', '')
        order['selected_threads'] = json.loads(request.form.get('selected_threads', '[]'))
        order['print_method'] = request.form.get('print_method', '')
        order['print_colors'] = request.form.get('print_colors', '')
        order['selected_print_colors'] = json.loads(request.form.get('selected_print_colors', '[]'))
        order['print_position'] = request.form.get('print_position', '')
        order['special_instructions'] = request.form.get('special_instructions', '')
        order['rush_order'] = request.form.get('rush_order') == 'on'
        order['estimated_completion_days'] = request.form.get('estimated_completion_days', '')
        # Neue Kalkulationsfelder
        order['stitch_count'] = safe_int(request.form.get('stitch_count'), 0)
        order['design_width_mm'] = safe_int(request.form.get('design_width_mm'), 0)
        order['design_height_mm'] = safe_int(request.form.get('design_height_mm'), 0)
        order['print_width_cm'] = safe_float(request.form.get('print_width_cm'), 0.0)
        order['print_height_cm'] = safe_float(request.form.get('print_height_cm'), 0.0)
        order['production_type'] = request.form.get('production_type', 'internal')
        order['ink_coverage_percent'] = safe_int(request.form.get('ink_coverage_percent'), 50)
        order['updated_at'] = datetime.now().isoformat()
        order['updated_by'] = session['username']
        
        save_orders(orders)
        
        flash('Auftrag wurde aktualisiert!', 'success')
        return redirect(url_for('orders.show', order_id=order_id))
    
    return render_template('orders/edit.html', order=order, customers=customers, articles=articles)

@order_bp.route('/calculate_price', methods=['POST'])
@login_required
def calculate_price():
    """AJAX-Endpoint für Live-Preiskalkulation"""
    data = request.get_json()
    
    order_type = data.get('order_type', 'embroidery')
    quantity = int(data.get('quantity', 1))
    textile_items = data.get('textile_items', [])
    
    # Berechne Basis-Textilkosten aus den tatsächlichen Artikeln
    textile_base_cost = 0
    if textile_items:
        for item in textile_items:
            item_cost = item.get('price', 0) * item.get('quantity', 0)
            textile_base_cost += item_cost
    else:
        # Fallback für alte Struktur
        textile_type = data.get('textile_type', 't-shirt')
        prices = load_material_prices()
        textile_base_cost = prices['textile_prices'].get(textile_type, 10.00) * quantity
    
    if order_type in ['embroidery', 'combined']:
        stitch_count = int(data.get('stitch_count', 0))
        if stitch_count > 0:
            # Verwende Textil-Grundpreis aus Artikeln
            prices = load_material_prices()
            
            # Stickerei-Kosten
            price_per_1000 = prices['embroidery']['price_per_1000_stitches']
            setup_fee = prices['embroidery']['setup_fee']
            
            embroidery_cost = (stitch_count / 1000) * price_per_1000
            unit_price = (textile_base_cost / quantity) + embroidery_cost
            
            # Mengenstaffel aus Einstellungen
            discount_settings = prices.get('discounts', {})
            if quantity >= 500:
                discount = discount_settings.get('qty_500', 30) / 100
            elif quantity >= 250:
                discount = discount_settings.get('qty_250', 25) / 100
            elif quantity >= 100:
                discount = discount_settings.get('qty_100', 20) / 100
            elif quantity >= 50:
                discount = discount_settings.get('qty_50', 15) / 100
            elif quantity >= 25:
                discount = discount_settings.get('qty_25', 10) / 100
            elif quantity >= 10:
                discount = discount_settings.get('qty_10', 5) / 100
            else:
                discount = 0
            
            subtotal = unit_price * quantity
            discount_amount = subtotal * discount
            total = subtotal - discount_amount + setup_fee
            
            pricing = {
                'unit_price': round(unit_price, 2),
                'subtotal': round(subtotal, 2),
                'discount_percent': discount * 100,
                'discount_amount': round(discount_amount, 2),
                'setup_fee': setup_fee,
                'total': round(total, 2)
            }
        else:
            pricing = {'error': 'Bitte Stichzahl eingeben'}
    
    elif order_type in ['printing', 'dtf']:
        width_cm = float(data.get('print_width_cm', 0))
        height_cm = float(data.get('print_height_cm', 0))
        coverage = int(data.get('ink_coverage_percent', 50))
        production_type = data.get('production_type', 'internal')
        
        if width_cm > 0 and height_cm > 0:
            dtf_pricing = calculate_dtf_price(width_cm, height_cm, quantity, coverage, production_type)
            # Addiere Textilkosten zu DTF-Kosten
            total_cost = dtf_pricing.get('total_cost', 0) + textile_base_cost
            pricing = dtf_pricing.copy()
            pricing['textile_cost'] = textile_base_cost
            pricing['total_cost'] = round(total_cost, 2)
        else:
            pricing = {'error': 'Bitte Druckgröße eingeben'}
    
    else:
        # Einfache Kalkulation für andere Typen
        pricing = {
            'unit_price': (textile_base_cost / quantity) + 5.00,  # Aufschlag
            'subtotal': textile_base_cost + (5.00 * quantity),
            'discount_percent': 0,
            'discount_amount': 0,
            'setup_fee': 10.00,
            'total': textile_base_cost + (5.00 * quantity) + 10.00
        }
    
    return jsonify(pricing)

@order_bp.route('/analyze_file', methods=['POST'])
@login_required
def analyze_file():
    """AJAX-Endpoint für Live-Dateianalyse"""
    if 'design_file' not in request.files:
        return jsonify({'success': False, 'error': 'Keine Datei hochgeladen'}), 400
    
    file = request.files['design_file']
    if not file or not file.filename:
        return jsonify({'success': False, 'error': 'Leere Datei'}), 400
    
    # Temporäre Datei speichern
    filename = secure_filename(file.filename)
    temp_dir = os.path.join('uploads', 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    temp_filepath = os.path.join(temp_dir, f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
    
    try:
        file.save(temp_filepath)
        
        # Datei analysieren
        from src.utils.file_analysis import analyze_design_file
        analysis = analyze_design_file(temp_filepath)
        
        # Temporäre Datei wieder löschen
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        
        return jsonify(analysis)
        
    except Exception as e:
        # Temporäre Datei aufräumen
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        
        return jsonify({
            'success': False,
            'error': f'Fehler beim Verarbeiten der Datei: {str(e)}'
        }), 500
