"""
Customer Controller - Kunden-Verwaltung
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
import json
import os
import re
from datetime import datetime
from src.utils.activity_logger import log_activity
from src.utils.customer_history import add_customer_history, get_customer_history

# Blueprint erstellen
customer_bp = Blueprint('customers', __name__, url_prefix='/customers')

CUSTOMERS_FILE = 'customers.json'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Bitte melden Sie sich an.', 'info')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def load_customers():
    """Lade Kunden aus JSON-Datei"""
    if os.path.exists(CUSTOMERS_FILE):
        with open(CUSTOMERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_customers(customers):
    """Speichere Kunden in JSON-Datei"""
    with open(CUSTOMERS_FILE, 'w') as f:
        json.dump(customers, f, indent=2)

def validate_vat_id(vat_id):
    """
    Validiert eine USt-ID (VAT ID)
    Unterstützt deutsche USt-IDs (DE + 9 Ziffern)
    Kann später für andere EU-Länder erweitert werden
    """
    if not vat_id:
        return True  # Leer ist OK (nicht Pflichtfeld)
    
    # Entferne Leerzeichen
    vat_id = vat_id.replace(' ', '').upper()
    
    # Deutsche USt-ID: DE + 9 Ziffern
    if vat_id.startswith('DE'):
        if re.match(r'^DE[0-9]{9}$', vat_id):
            return True
        else:
            return False
    
    # Weitere EU-Länder können hier hinzugefügt werden
    # AT: ATU + 8 Ziffern
    # FR: FR + 2 Zeichen + 9 Ziffern
    # etc.
    
    # Für andere Länder erstmal akzeptieren
    return True

def generate_customer_id():
    """Generiere neue Kunden-ID"""
    customers = load_customers()
    if not customers:
        return "KD001"
    
    # Finde höchste ID
    max_num = 0
    for customer_id in customers.keys():
        if customer_id.startswith("KD"):
            try:
                num = int(customer_id[2:])
                max_num = max(max_num, num)
            except:
                pass
    
    return f"KD{max_num + 1:03d}"

@customer_bp.route('/')
@login_required
def index():
    """Kunden-Übersicht"""
    customers = load_customers()
    
    # Suchfilter
    search_query = request.args.get('search', '').lower()
    
    if search_query:
        filtered_customers = {}
        for customer_id, customer in customers.items():
            # Suche in allgemeinen Feldern
            if (search_query in customer.get('email', '').lower() or
                search_query in customer.get('phone', '').lower() or
                search_query in customer.get('mobile', '').lower() or
                search_query in customer.get('city', '').lower() or
                search_query in customer.get('display_name', '').lower()):
                filtered_customers[customer_id] = customer
            # Suche in Privatpersonen-Feldern
            elif (search_query in customer.get('first_name', '').lower() or
                  search_query in customer.get('last_name', '').lower()):
                filtered_customers[customer_id] = customer
            # Suche in Firmenkunden-Feldern
            elif (search_query in customer.get('company_name', '').lower() or
                  search_query in customer.get('contact_person', '').lower() or
                  search_query in customer.get('vat_id', '').lower()):
                filtered_customers[customer_id] = customer
    else:
        filtered_customers = customers
    
    return render_template('customers/index.html', 
                         customers=filtered_customers,
                         search_query=search_query)

@customer_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Neuen Kunden erstellen"""
    if request.method == 'POST':
        customers = load_customers()
        customer_id = generate_customer_id()
        
        customer_type = request.form.get('customer_type', 'private')
        
        # Basis-Kundendaten
        customer_data = {
            'id': customer_id,
            'customer_type': customer_type,
            'email': request.form.get('email', ''),
            'phone': request.form.get('phone', ''),
            'mobile': request.form.get('mobile', ''),
            'street': request.form.get('street', ''),
            'house_number': request.form.get('house_number', ''),
            'postal_code': request.form.get('postal_code', ''),
            'city': request.form.get('city', ''),
            'country': request.form.get('country', 'Deutschland'),
            'newsletter': request.form.get('newsletter', False) == 'on',
            'notes': request.form.get('notes', ''),
            'created_at': datetime.now().isoformat(),
            'created_by': session['username']
        }
        
        # Spezifische Felder je nach Kundentyp
        if customer_type == 'business':
            # USt-ID validieren
            vat_id = request.form.get('vat_id', '')
            if vat_id and not validate_vat_id(vat_id):
                flash('Ungültige USt-ID! Deutsche USt-IDs müssen das Format DE123456789 haben (DE + 9 Ziffern).', 'danger')
                return render_template('customers/new.html')
            
            # Firmenkunden-Felder
            customer_data.update({
                'company_name': request.form.get('company_name'),
                'tax_id': request.form.get('tax_id', ''),
                'vat_id': vat_id.replace(' ', '').upper() if vat_id else '',
                'contact_person': request.form.get('contact_person', ''),
                'department': request.form.get('department', ''),
                'position': request.form.get('position', ''),
                # Für Anzeigezwecke
                'display_name': request.form.get('company_name')
            })
        else:
            # Privatpersonen-Felder
            customer_data.update({
                'first_name': request.form.get('first_name'),
                'last_name': request.form.get('last_name'),
                'birth_date': request.form.get('birth_date', ''),
                # Für Anzeigezwecke
                'display_name': f"{request.form.get('first_name')} {request.form.get('last_name')}"
            })
        
        customers[customer_id] = customer_data
        
        save_customers(customers)
        log_activity(session['username'], 'customer_created', 
                    f'Kunde erstellt: {customer_id} - {customer_data["display_name"]}')
        
        # Historie hinzufügen
        add_customer_history(customer_id, 'created', 
                           f'Kunde angelegt', 
                           session['username'])
        
        flash(f'Kunde {customer_data["display_name"]} wurde erstellt!', 'success')
        return redirect(url_for('customers.show', customer_id=customer_id))
    
    return render_template('customers/new.html')

@customer_bp.route('/<customer_id>')
@login_required
def show(customer_id):
    """Kunden-Details anzeigen"""
    customers = load_customers()
    customer = customers.get(customer_id)
    
    if not customer:
        flash('Kunde nicht gefunden!', 'danger')
        return redirect(url_for('customers.index'))
    
    # Lade Kunden-Historie
    history = get_customer_history(customer_id)
    
    return render_template('customers/show.html', customer=customer, history=history)

@customer_bp.route('/<customer_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(customer_id):
    """Kunde bearbeiten"""
    customers = load_customers()
    customer = customers.get(customer_id)
    
    if not customer:
        flash('Kunde nicht gefunden!', 'danger')
        return redirect(url_for('customers.index'))
    
    if request.method == 'POST':
        # Basis-Daten aktualisieren
        customer['email'] = request.form.get('email', '')
        customer['phone'] = request.form.get('phone', '')
        customer['mobile'] = request.form.get('mobile', '')
        customer['street'] = request.form.get('street', '')
        customer['house_number'] = request.form.get('house_number', '')
        customer['postal_code'] = request.form.get('postal_code', '')
        customer['city'] = request.form.get('city', '')
        customer['country'] = request.form.get('country', 'Deutschland')
        customer['newsletter'] = request.form.get('newsletter', False) == 'on'
        customer['notes'] = request.form.get('notes', '')
        customer['updated_at'] = datetime.now().isoformat()
        customer['updated_by'] = session['username']
        
        # Spezifische Felder je nach Kundentyp
        if customer.get('customer_type', 'private') == 'business':
            # USt-ID validieren
            vat_id = request.form.get('vat_id', '')
            if vat_id and not validate_vat_id(vat_id):
                flash('Ungültige USt-ID! Deutsche USt-IDs müssen das Format DE123456789 haben (DE + 9 Ziffern).', 'danger')
                return render_template('customers/edit.html', customer=customer)
            
            # Firmenkunden-Felder
            customer['company_name'] = request.form.get('company_name')
            customer['tax_id'] = request.form.get('tax_id', '')
            customer['vat_id'] = vat_id.replace(' ', '').upper() if vat_id else ''
            customer['contact_person'] = request.form.get('contact_person', '')
            customer['department'] = request.form.get('department', '')
            customer['position'] = request.form.get('position', '')
            customer['display_name'] = customer['company_name']
        else:
            # Privatpersonen-Felder
            customer['first_name'] = request.form.get('first_name')
            customer['last_name'] = request.form.get('last_name')
            customer['birth_date'] = request.form.get('birth_date', '')
            customer['display_name'] = f"{customer['first_name']} {customer['last_name']}"
        
        save_customers(customers)
        log_activity(session['username'], 'customer_updated', 
                    f'Kunde aktualisiert: {customer_id} - {customer["display_name"]}')
        
        # Historie hinzufügen
        add_customer_history(customer_id, 'updated', 
                           'Kundendaten aktualisiert', 
                           session['username'])
        
        flash(f'Kunde {customer["display_name"]} wurde aktualisiert!', 'success')
        return redirect(url_for('customers.show', customer_id=customer_id))
    
    return render_template('customers/edit.html', customer=customer)

@customer_bp.route('/<customer_id>/delete', methods=['POST'])
@login_required
def delete(customer_id):
    """Kunde löschen"""
    customers = load_customers()
    
    if customer_id in customers:
        customer = customers[customer_id]
        # Verwende display_name oder generiere einen aus vorhandenen Daten
        if 'display_name' in customer:
            customer_name = customer['display_name']
        elif 'company_name' in customer:
            customer_name = customer['company_name']
        elif 'first_name' in customer and 'last_name' in customer:
            customer_name = f"{customer['first_name']} {customer['last_name']}"
        else:
            customer_name = customer_id
            
        # Historie hinzufügen bevor Kunde gelöscht wird
        add_customer_history(customer_id, 'deleted', 
                           f'Kunde gelöscht', 
                           session['username'])
        
        del customers[customer_id]
        save_customers(customers)
        
        log_activity(session['username'], 'customer_deleted', f'Kunde gelöscht: {customer_id} - {customer_name}')
        flash(f'Kunde {customer_name} wurde gelöscht!', 'success')
    else:
        flash('Kunde nicht gefunden!', 'danger')
    
    return redirect(url_for('customers.index'))