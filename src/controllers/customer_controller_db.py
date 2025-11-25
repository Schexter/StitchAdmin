"""
Customer Controller - PostgreSQL-Version
Vollständige Datenbank-Integration mit SQLAlchemy
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from src.models import db, Customer, Order, ActivityLog
from src.utils.form_helpers import parse_date_from_form, safe_get_form_value

# Blueprint erstellen
customer_bp = Blueprint('customers', __name__, url_prefix='/customers')

def log_activity(action, details):
    """Aktivität in Datenbank protokollieren"""
    activity = ActivityLog(
        username=current_user.username,
        action=action,
        details=details,
        ip_address=request.remote_addr
    )
    db.session.add(activity)
    db.session.commit()

@customer_bp.route('/')
@login_required
def index():
    """Kunden-Übersicht"""
    # Suchfilter
    search_query = request.args.get('search', '').lower()
    
    # Query erstellen
    query = Customer.query
    
    if search_query:
        # Suche in verschiedenen Feldern
        query = query.filter(
            db.or_(
                Customer.email.ilike(f'%{search_query}%'),
                Customer.phone.ilike(f'%{search_query}%'),
                Customer.mobile.ilike(f'%{search_query}%'),
                Customer.city.ilike(f'%{search_query}%'),
                Customer.first_name.ilike(f'%{search_query}%'),
                Customer.last_name.ilike(f'%{search_query}%'),
                Customer.company_name.ilike(f'%{search_query}%'),
                Customer.contact_person.ilike(f'%{search_query}%'),
                Customer.vat_id.ilike(f'%{search_query}%')
            )
        )
    
    # Nach Name sortieren
    customers_list = query.order_by(Customer.created_at.desc()).all()
    
    # In Dictionary umwandeln für Template-Kompatibilität
    customers = {}
    for customer in customers_list:
        customers[customer.id] = customer
    
    return render_template('customers/index.html', 
                         customers=customers,
                         search_query=search_query)

@customer_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Neuen Kunden erstellen"""
    if request.method == 'POST':
        customer_type = request.form.get('customer_type', 'private')
        
        # Neuen Kunden erstellen
        customer = Customer(
            customer_type=customer_type,
            email=request.form.get('email', ''),
            phone=request.form.get('phone', ''),
            mobile=request.form.get('mobile', ''),
            street=request.form.get('street', ''),
            house_number=request.form.get('house_number', ''),
            postal_code=request.form.get('postal_code', ''),
            city=request.form.get('city', ''),
            country=request.form.get('country', 'Deutschland'),
            newsletter=request.form.get('newsletter', False) == 'on',
            notes=request.form.get('notes', ''),
            created_by=current_user.username
        )
        
        # Spezifische Felder je nach Kundentyp
        if customer_type == 'business':
            # Firmenkunden-Felder
            customer.company_name = request.form.get('company_name')
            customer.tax_id = request.form.get('tax_id', '')
            customer.vat_id = request.form.get('vat_id', '').replace(' ', '').upper()
            customer.contact_person = request.form.get('contact_person', '')
            customer.department = request.form.get('department', '')
            customer.position = request.form.get('position', '')
        else:
            # Privatpersonen-Felder
            customer.first_name = safe_get_form_value(request.form, 'first_name')
            customer.last_name = safe_get_form_value(request.form, 'last_name')
            customer.birth_date = parse_date_from_form(request.form.get('birth_date'), 'Geburtsdatum')
        
        # Kunden-ID generieren
        # Finde höchste ID
        last_customer = Customer.query.filter(
            Customer.id.like('KD%')
        ).order_by(Customer.id.desc()).first()
        
        if last_customer:
            try:
                last_num = int(last_customer.id[2:])
                new_id = f"KD{last_num + 1:03d}"
            except:
                new_id = "KD001"
        else:
            new_id = "KD001"
        
        customer.id = new_id
        
        # In Datenbank speichern
        db.session.add(customer)
        db.session.commit()
        
        # Aktivität protokollieren
        log_activity('customer_created', 
                    f'Kunde erstellt: {customer.id} - {customer.display_name}')
        
        flash(f'Kunde {customer.display_name} wurde erstellt!', 'success')
        return redirect(url_for('customers.show', customer_id=customer.id))
    
    return render_template('customers/new.html')

@customer_bp.route('/<customer_id>')
@login_required
def show(customer_id):
    """Kunden-Details anzeigen"""
    customer = Customer.query.get_or_404(customer_id)
    
    # Aufträge des Kunden laden
    orders = customer.orders.order_by(Order.created_at.desc()).all() if hasattr(customer, 'orders') else []
    
    return render_template('customers/show.html', 
                         customer=customer, 
                         orders=orders,
                         history=[])  # TODO: Historie-Feature später implementieren

@customer_bp.route('/<customer_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(customer_id):
    """Kunde bearbeiten"""
    customer = Customer.query.get_or_404(customer_id)
    
    if request.method == 'POST':
        # Basis-Daten aktualisieren
        customer.email = request.form.get('email', '')
        customer.phone = request.form.get('phone', '')
        customer.mobile = request.form.get('mobile', '')
        customer.street = request.form.get('street', '')
        customer.house_number = request.form.get('house_number', '')
        customer.postal_code = request.form.get('postal_code', '')
        customer.city = request.form.get('city', '')
        customer.country = request.form.get('country', 'Deutschland')
        customer.newsletter = request.form.get('newsletter', False) == 'on'
        customer.notes = request.form.get('notes', '')
        customer.updated_at = datetime.utcnow()
        customer.updated_by = current_user.username
        
        # Spezifische Felder je nach Kundentyp
        if customer.customer_type == 'business':
            # Firmenkunden-Felder
            customer.company_name = request.form.get('company_name')
            customer.tax_id = request.form.get('tax_id', '')
            customer.vat_id = request.form.get('vat_id', '').replace(' ', '').upper()
            customer.contact_person = request.form.get('contact_person', '')
            customer.department = request.form.get('department', '')
            customer.position = request.form.get('position', '')
        else:
            # Privatpersonen-Felder
            customer.first_name = safe_get_form_value(request.form, 'first_name')
            customer.last_name = safe_get_form_value(request.form, 'last_name')
            customer.birth_date = parse_date_from_form(request.form.get('birth_date'), 'Geburtsdatum')
        
        # Änderungen speichern
        db.session.commit()
        
        # Aktivität protokollieren
        log_activity('customer_updated', 
                    f'Kunde aktualisiert: {customer.id} - {customer.display_name}')
        
        flash(f'Kunde {customer.display_name} wurde aktualisiert!', 'success')
        return redirect(url_for('customers.show', customer_id=customer.id))
    
    return render_template('customers/edit.html', customer=customer)

@customer_bp.route('/<customer_id>/delete', methods=['POST'])
@login_required
def delete(customer_id):
    """Kunde löschen"""
    customer = Customer.query.get_or_404(customer_id)
    customer_name = customer.display_name
    
    # Prüfen ob Kunde Aufträge hat
    if customer.orders.count() > 0:
        flash(f'Kunde {customer_name} kann nicht gelöscht werden, da noch Aufträge vorhanden sind!', 'danger')
        return redirect(url_for('customers.show', customer_id=customer_id))
    
    # Aktivität protokollieren bevor gelöscht wird
    log_activity('customer_deleted', 
                f'Kunde gelöscht: {customer.id} - {customer_name}')
    
    # Kunde löschen
    db.session.delete(customer)
    db.session.commit()
    
    flash(f'Kunde {customer_name} wurde gelöscht!', 'success')
    return redirect(url_for('customers.index'))

# ==========================================
# API ENDPOINTS
# ==========================================

@customer_bp.route('/api/customers', methods=['GET'])
@login_required
def api_customers():
    """API Endpoint: Liste aller Kunden als JSON"""
    from flask import jsonify

    try:
        # Alle Kunden laden, sortiert nach Name
        customers = Customer.query.order_by(Customer.company_name, Customer.first_name).all()

        # Konvertiere zu JSON-Format
        customers_data = [{
            'id': c.id,
            'display_name': c.display_name,
            'company_name': c.company_name or '',
            'first_name': c.first_name or '',
            'last_name': c.last_name or '',
            'customer_number': c.customer_number or '',
            'email': c.email or '',
            'phone': c.phone or '',
            'street': c.street or '',
            'house_number': c.house_number or '',
            'postal_code': c.postal_code or '',
            'city': c.city or '',
            'vat_id': c.vat_id or '',
            'tax_id': c.tax_id or ''
        } for c in customers]

        return jsonify({
            'success': True,
            'customers': customers_data
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
