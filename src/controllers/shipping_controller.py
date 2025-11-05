"""
Shipping Controller - Versandabwicklung für fertige Aufträge
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import uuid

# Blueprint erstellen
shipping_bp = Blueprint('shipping', __name__, url_prefix='/shipping')

SHIPMENTS_FILE = 'shipments.json'
SHIPPING_SETTINGS_FILE = 'shipping_settings.json'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Bitte melden Sie sich an.', 'info')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def load_orders():
    """Lade Kundenaufträge"""
    from src.controllers.order_controller import load_orders
    return load_orders()

def save_orders(orders):
    """Speichere Kundenaufträge"""
    from src.controllers.order_controller import save_orders
    return save_orders(orders)

def load_customers():
    """Lade Kundendaten"""
    from src.controllers.customer_controller import load_customers
    return load_customers()

def load_shipments():
    """Lade Versendungen aus JSON-Datei"""
    if os.path.exists(SHIPMENTS_FILE):
        with open(SHIPMENTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_shipments(shipments):
    """Speichere Versendungen in JSON-Datei"""
    with open(SHIPMENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(shipments, f, indent=2, ensure_ascii=False)

def get_shipping_address_name(customer, order):
    """Gibt den korrekten Namen für die Versandadresse zurück"""
    if not customer:
        return order.get('customer_name', '')
    
    if customer.get('customer_type') == 'business':
        # Bei Geschäftskunden: Firmenname und Ansprechpartner
        company_name = customer.get('company_name', '')
        contact_person = customer.get('contact_person', '')
        if company_name and contact_person:
            return f"{company_name}<br>z.Hd. {contact_person}"
        elif company_name:
            return company_name
        else:
            return order.get('customer_name', '')
    else:
        # Bei Privatkunden: Vor- und Nachname
        first_name = customer.get('first_name', '')
        last_name = customer.get('last_name', '')
        if first_name or last_name:
            return f"{first_name} {last_name}".strip()
        else:
            return order.get('customer_name', '')

def load_shipping_settings():
    """Lade Versandeinstellungen"""
    if os.path.exists(SHIPPING_SETTINGS_FILE):
        with open(SHIPPING_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # Standard-Einstellungen
    return {
        'carriers': {
            'dhl': {
                'name': 'DHL',
                'enabled': True,
                'cost_domestic': 4.99,
                'cost_eu': 7.99,
                'cost_international': 12.99,
                'tracking_url': 'https://www.dhl.de/de/privatkunden/pakete-empfangen/verfolgen.html?lang=de&idc={tracking_number}'
            },
            'dpd': {
                'name': 'DPD',
                'enabled': True,
                'cost_domestic': 5.49,
                'cost_eu': 8.99,
                'cost_international': 15.99,
                'tracking_url': 'https://tracking.dpd.de/status/de_DE/parcel/{tracking_number}'
            },
            'hermes': {
                'name': 'Hermes',
                'enabled': True,
                'cost_domestic': 3.89,
                'cost_eu': 6.99,
                'cost_international': 11.99,
                'tracking_url': 'https://www.myhermes.de/empfangen/sendungsverfolgung/sendungsinformation/#pno={tracking_number}'
            },
            'ups': {
                'name': 'UPS',
                'enabled': True,
                'cost_domestic': 6.99,
                'cost_eu': 12.99,
                'cost_international': 19.99,
                'tracking_url': 'https://www.ups.com/track?loc=de_DE&tracknum={tracking_number}'
            },
            'pickup': {
                'name': 'Selbstabholung',
                'enabled': True,
                'cost_domestic': 0.00,
                'cost_eu': 0.00,
                'cost_international': 0.00,
                'tracking_url': ''
            }
        },
        'sender_address': {
            'company': 'StitchAdmin GmbH',
            'name': 'Max Mustermann',
            'street': 'Musterstraße 123',
            'postal_code': '12345',
            'city': 'Musterstadt',
            'country': 'Deutschland',
            'phone': '+49 123 456789',
            'email': 'versand@stitchadmin.com'
        },
        'free_shipping_threshold': 50.00,
        'default_package_weight': 0.5,  # kg
        'weight_tiers': [
            {'max_weight': 2.0, 'multiplier': 1.0},
            {'max_weight': 5.0, 'multiplier': 1.5},
            {'max_weight': 10.0, 'multiplier': 2.0},
            {'max_weight': 20.0, 'multiplier': 3.0}
        ],
        'eu_countries': [
            'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR',
            'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL',
            'PT', 'RO', 'SK', 'SI', 'ES', 'SE'
        ]
    }

def generate_tracking_number(carrier):
    """Generiere eine Tracking-Nummer"""
    # Vereinfachte Tracking-Nummer für Demo
    import random
    import string
    
    if carrier == 'dhl':
        return f"00340434{random.randint(100000000, 999999999)}"
    elif carrier == 'dpd':
        return f"05{random.randint(100000000000, 999999999999)}"
    elif carrier == 'hermes':
        return f"H{''.join(random.choices(string.digits, k=12))}"
    elif carrier == 'ups':
        return f"1Z{''.join(random.choices(string.ascii_uppercase + string.digits, k=16))}"
    else:
        return f"{''.join(random.choices(string.ascii_uppercase + string.digits, k=10))}"

def calculate_order_weight(order):
    """Berechne Gesamtgewicht eines Auftrags basierend auf Artikeln"""
    from src.controllers.article_controller import load_articles
    
    articles = load_articles()
    total_weight = 0.0
    
    # Gewicht basierend auf Artikel-ID (falls vorhanden)
    article_id = order.get('article_id')
    if article_id and article_id in articles:
        article = articles[article_id]
        article_weight = float(article.get('weight', 0.5))  # Standard 0.5kg
        quantity = int(order.get('quantity', 1))
        total_weight = article_weight * quantity
    else:
        # Fallback: Schätze Gewicht basierend auf Textiltyp und Menge
        quantity = int(order.get('quantity', 1))
        textile_type = order.get('textile_type', '').lower()
        
        # Geschätzte Gewichte pro Stück in kg
        weight_estimates = {
            't-shirt': 0.15,
            'polo': 0.20,
            'hoodie': 0.50,
            'jacke': 0.60,
            'cap': 0.10,
            'tasche': 0.25,
            'handtuch': 0.30
        }
        
        estimated_weight = 0.25  # Standard 250g pro Stück
        for textile, weight in weight_estimates.items():
            if textile in textile_type:
                estimated_weight = weight
                break
        
        total_weight = estimated_weight * quantity
    
    return max(total_weight, 0.1)  # Minimum 100g

def get_ready_for_shipping_orders():
    """Hole alle Aufträge die versandbereit sind"""
    orders = load_orders()
    
    ready_orders = {
        oid: order for oid, order in orders.items() 
        if order.get('status') == 'ready'
    }
    
    return ready_orders

def calculate_shipping_cost(order, carrier, settings, destination_country='DE', total_weight=None):
    """Berechne Versandkosten für einen Auftrag"""
    carrier_info = settings['carriers'].get(carrier, {})
    order_value = order.get('price', 0)
    
    # Kostenloser Versand bei Mindestbestellwert
    if order_value >= settings.get('free_shipping_threshold', 50.00):
        return 0.00
    
    # Selbstabholung ist immer kostenlos
    if carrier == 'pickup':
        return 0.00
    
    # Bestimme Versandzone
    if destination_country in ['DE', 'Deutschland']:
        base_cost = carrier_info.get('cost_domestic', 5.00)
    elif destination_country in settings.get('eu_countries', []):
        base_cost = carrier_info.get('cost_eu', carrier_info.get('cost_domestic', 5.00) * 1.5)
    else:
        base_cost = carrier_info.get('cost_international', carrier_info.get('cost_domestic', 5.00) * 2.0)
    
    # Gewichts-Multiplikator anwenden
    if total_weight is not None:
        weight_multiplier = 1.0
        for tier in settings.get('weight_tiers', []):
            if total_weight <= tier['max_weight']:
                weight_multiplier = tier['multiplier']
                break
        else:
            # Über alle Gewichtsstufen hinaus
            weight_multiplier = settings.get('weight_tiers', [{'multiplier': 1.0}])[-1]['multiplier']
        
        base_cost *= weight_multiplier
    
    return round(base_cost, 2)

@shipping_bp.route('/')
@login_required
def index():
    """Versand-Übersicht"""
    ready_orders = get_ready_for_shipping_orders()
    shipments = load_shipments()
    settings = load_shipping_settings()
    
    # Versandstatistiken
    stats = {
        'ready_for_shipping': len(ready_orders),
        'shipped_today': len([s for s in shipments.values() 
                             if s.get('shipped_date') and s.get('shipped_date')[:10] == datetime.now().strftime('%Y-%m-%d')]),
        'total_shipments': len(shipments),
        'pending_pickups': len([o for o in ready_orders.values() 
                               if o.get('shipping_method') == 'pickup'])
    }
    
    return render_template('shipping/index.html', 
                         ready_orders=ready_orders,
                         shipments=shipments,
                         settings=settings,
                         stats=stats)

@shipping_bp.route('/prepare/<order_id>')
@login_required
def prepare_shipment(order_id):
    """Versand vorbereiten"""
    orders = load_orders()
    order = orders.get(order_id)
    
    if not order:
        flash('Auftrag nicht gefunden!', 'danger')
        return redirect(url_for('shipping.index'))
    
    if order.get('status') != 'ready':
        flash('Auftrag ist nicht versandbereit!', 'warning')
        return redirect(url_for('shipping.index'))
    
    customers = load_customers()
    customer = customers.get(order['customer_id'])
    settings = load_shipping_settings()
    
    # Berechne Versandkosten für alle Träger
    order_weight = calculate_order_weight(order)
    destination_country = customer.get('country', 'DE') if customer else 'DE'
    
    shipping_costs = {}
    for carrier_id, carrier_info in settings['carriers'].items():
        if carrier_info.get('enabled', True):
            shipping_costs[carrier_id] = calculate_shipping_cost(
                order, carrier_id, settings, destination_country, order_weight
            )
    
    return render_template('shipping/prepare.html', 
                         order=order,
                         customer=customer,
                         settings=settings,
                         shipping_costs=shipping_costs,
                         order_weight=order_weight)

@shipping_bp.route('/create_shipment/<order_id>', methods=['POST'])
@login_required
def create_shipment(order_id):
    """Versendung erstellen"""
    orders = load_orders()
    order = orders.get(order_id)
    
    if not order:
        flash('Auftrag nicht gefunden!', 'danger')
        return redirect(url_for('shipping.index'))
    
    customers = load_customers()
    customer = customers.get(order['customer_id'])
    settings = load_shipping_settings()
    
    carrier = request.form.get('carrier')
    if not carrier or carrier not in settings['carriers']:
        flash('Ungültiger Versanddienstleister!', 'danger')
        return redirect(url_for('shipping.prepare_shipment', order_id=order_id))
    
    # Versendung erstellen
    shipments = load_shipments()
    shipment_id = f"SHIP-{datetime.now().strftime('%Y%m%d')}-{len(shipments) + 1:04d}"
    
    tracking_number = ""
    if carrier != 'pickup':
        tracking_number = generate_tracking_number(carrier)
    
    order_weight = calculate_order_weight(order)
    destination_country = customer.get('country', 'DE') if customer else 'DE'
    shipping_cost = calculate_shipping_cost(order, carrier, settings, destination_country, order_weight)
    
    shipment = {
        'id': shipment_id,
        'order_id': order_id,
        'customer_id': order['customer_id'],
        'customer_name': order['customer_name'],
        'carrier': carrier,
        'carrier_name': settings['carriers'][carrier]['name'],
        'tracking_number': tracking_number,
        'shipping_cost': shipping_cost,
        'package_weight': float(request.form.get('package_weight', settings.get('default_package_weight', 0.5))),
        'package_dimensions': request.form.get('package_dimensions', ''),
        'special_instructions': request.form.get('special_instructions', ''),
        'shipping_address': {
            'name': get_shipping_address_name(customer, order),
            'street': customer.get('street', '') if customer else '',
            'house_number': customer.get('house_number', '') if customer else '',
            'postal_code': customer.get('postal_code', '') if customer else '',
            'city': customer.get('city', '') if customer else '',
            'country': customer.get('country', 'Deutschland') if customer else 'Deutschland'
        },
        'status': 'prepared',  # prepared, shipped, delivered, returned
        'created_at': datetime.now().isoformat(),
        'created_by': session['username'],
        'shipped_date': None,
        'delivered_date': None
    }
    
    # Bei Selbstabholung sofort als versendet markieren
    if carrier == 'pickup':
        shipment['status'] = 'ready_for_pickup'
        shipment['shipped_date'] = datetime.now().isoformat()
        # Auftrag als abgeschlossen markieren
        order['status'] = 'completed'
        order['completed_at'] = datetime.now().isoformat()
        order['completed_by'] = session['username']
    
    shipments[shipment_id] = shipment
    save_shipments(shipments)
    save_orders(orders)
    
    if carrier == 'pickup':
        flash(f'Auftrag {order_id} zur Selbstabholung vorbereitet!', 'success')
    else:
        flash(f'Versendung {shipment_id} erstellt! Tracking: {tracking_number}', 'success')
    
    return redirect(url_for('shipping.shipment_details', shipment_id=shipment_id))

@shipping_bp.route('/shipment/<shipment_id>')
@login_required
def shipment_details(shipment_id):
    """Versendungsdetails anzeigen"""
    shipments = load_shipments()
    shipment = shipments.get(shipment_id)
    
    if not shipment:
        flash('Versendung nicht gefunden!', 'danger')
        return redirect(url_for('shipping.index'))
    
    orders = load_orders()
    order = orders.get(shipment['order_id'])
    
    settings = load_shipping_settings()
    carrier_info = settings['carriers'].get(shipment['carrier'], {})
    
    # Tracking URL generieren
    tracking_url = ""
    if shipment.get('tracking_number') and carrier_info.get('tracking_url'):
        tracking_url = carrier_info['tracking_url'].format(tracking_number=shipment['tracking_number'])
    
    return render_template('shipping/details.html', 
                         shipment=shipment,
                         order=order,
                         tracking_url=tracking_url,
                         carrier_info=carrier_info)

@shipping_bp.route('/mark_shipped/<shipment_id>', methods=['POST'])
@login_required
def mark_shipped(shipment_id):
    """Versendung als versendet markieren"""
    shipments = load_shipments()
    shipment = shipments.get(shipment_id)
    
    if not shipment:
        flash('Versendung nicht gefunden!', 'danger')
        return redirect(url_for('shipping.index'))
    
    if shipment.get('status') != 'prepared':
        flash('Versendung ist nicht bereit zum Versand!', 'warning')
        return redirect(url_for('shipping.shipment_details', shipment_id=shipment_id))
    
    shipment['status'] = 'shipped'
    shipment['shipped_date'] = datetime.now().isoformat()
    shipment['shipped_by'] = session['username']
    
    save_shipments(shipments)
    
    flash(f'Versendung {shipment_id} als versendet markiert!', 'success')
    return redirect(url_for('shipping.shipment_details', shipment_id=shipment_id))

@shipping_bp.route('/mark_delivered/<shipment_id>', methods=['POST'])
@login_required
def mark_delivered(shipment_id):
    """Versendung als zugestellt markieren"""
    shipments = load_shipments()
    shipment = shipments.get(shipment_id)
    
    if not shipment:
        flash('Versendung nicht gefunden!', 'danger')
        return redirect(url_for('shipping.index'))
    
    orders = load_orders()
    order = orders.get(shipment['order_id'])
    
    if order:
        order['status'] = 'completed'
        order['completed_at'] = datetime.now().isoformat()
        order['completed_by'] = session['username']
        save_orders(orders)
    
    shipment['status'] = 'delivered'
    shipment['delivered_date'] = datetime.now().isoformat()
    
    save_shipments(shipments)
    
    flash(f'Versendung {shipment_id} als zugestellt markiert! Auftrag abgeschlossen.', 'success')
    return redirect(url_for('shipping.shipment_details', shipment_id=shipment_id))

@shipping_bp.route('/packing_list/<order_id>')
@login_required
def generate_packing_list(order_id):
    """Packliste generieren"""
    orders = load_orders()
    order = orders.get(order_id)
    
    if not order:
        flash('Auftrag nicht gefunden!', 'danger')
        return redirect(url_for('shipping.index'))
    
    customers = load_customers()
    customer = customers.get(order['customer_id'])
    
    return render_template('shipping/packing_list.html', 
                         order=order,
                         customer=customer,
                         generated_at=datetime.now())

@shipping_bp.route('/label/<shipment_id>')
@login_required
def generate_shipping_label(shipment_id):
    """Versandetikett generieren"""
    shipments = load_shipments()
    shipment = shipments.get(shipment_id)
    
    if not shipment:
        flash('Versendung nicht gefunden!', 'danger')
        return redirect(url_for('shipping.index'))
    
    settings = load_shipping_settings()
    
    return render_template('shipping/label.html', 
                         shipment=shipment,
                         sender=settings['sender_address'],
                         generated_at=datetime.now())

@shipping_bp.route('/api/tracking/<tracking_number>')
@login_required
def api_tracking_info(tracking_number):
    """API für Tracking-Informationen"""
    shipments = load_shipments()
    
    # Finde Versendung mit dieser Tracking-Nummer
    shipment = None
    for s in shipments.values():
        if s.get('tracking_number') == tracking_number:
            shipment = s
            break
    
    if not shipment:
        return jsonify({'error': 'Tracking-Nummer nicht gefunden'}), 404
    
    return jsonify({
        'shipment_id': shipment['id'],
        'status': shipment['status'],
        'carrier': shipment['carrier_name'],
        'shipped_date': shipment.get('shipped_date'),
        'delivered_date': shipment.get('delivered_date'),
        'customer_name': shipment['customer_name']
    })

@shipping_bp.route('/overview')
@login_required
def overview():
    """Versand-Übersicht mit allen Versendungen"""
    shipments = load_shipments()
    
    # Nach Status gruppieren
    grouped_shipments = defaultdict(list)
    for shipment in shipments.values():
        grouped_shipments[shipment.get('status', 'unknown')].append(shipment)
    
    # Nach Datum sortieren (neueste zuerst)
    for status in grouped_shipments:
        grouped_shipments[status].sort(
            key=lambda x: x.get('created_at', ''),
            reverse=True
        )
    
    return render_template('shipping/overview.html', 
                         grouped_shipments=dict(grouped_shipments))