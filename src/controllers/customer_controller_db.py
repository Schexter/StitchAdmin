"""
Customer Controller - PostgreSQL-Version
Vollständige Datenbank-Integration mit SQLAlchemy
"""

import re
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from src.models import db, Customer, Order, ActivityLog
from src.utils.activity_logger import log_activity
from src.utils.form_helpers import parse_date_from_form, safe_get_form_value

# Blueprint erstellen
customer_bp = Blueprint('customers', __name__, url_prefix='/customers')


def generate_customer_id():
    """Erzeugt die naechste fortlaufende Kundennummer - delegiert an IdGeneratorService"""
    from src.services.id_generator_service import IdGenerator
    return IdGenerator.customer()

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
            address_supplement=request.form.get('address_supplement', '').strip() or None,
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
        
        # Kunden-ID generieren (fortlaufend)
        customer.id = generate_customer_id()
        
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
    
    # CRM-Aktivitäten laden (Telefonate, Besuche, E-Mails aus ProductionBlock)
    activities = []
    try:
        from src.models import ProductionBlock
        activities = ProductionBlock.query.filter(
            ProductionBlock.customer_id == customer_id,
            ProductionBlock.is_active == True
        ).order_by(
            ProductionBlock.start_date.desc(),
            ProductionBlock.start_time.desc()
        ).limit(20).all()
    except Exception as e:
        # ProductionBlock noch nicht migriert - ignorieren
        pass
    
    # CRM-Kontakthistorie laden (E-Mails, Anfragen, Notizen)
    contacts = []
    try:
        from src.models.crm_contact import CustomerContact
        contacts = CustomerContact.query.filter_by(
            customer_id=customer_id
        ).order_by(CustomerContact.created_at.desc()).limit(20).all()
    except Exception:
        pass

    # Anfragen des Kunden laden
    inquiries = []
    try:
        from src.models.inquiry import Inquiry
        inquiries = Inquiry.query.filter_by(
            customer_id=customer_id
        ).order_by(Inquiry.created_at.desc()).all()
    except Exception:
        pass

    return render_template('customers/show.html',
                         customer=customer,
                         orders=orders,
                         activities=activities,
                         contacts=contacts,
                         inquiries=inquiries,
                         history=[])

@customer_bp.route('/<customer_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(customer_id):
    """Kunde bearbeiten"""
    customer = Customer.query.get_or_404(customer_id)
    
    if request.method == 'POST':
        # Kundentyp-Wechsel erlauben
        new_type = request.form.get('customer_type', customer.customer_type)
        if new_type in ('private', 'business'):
            customer.customer_type = new_type

        # Basis-Daten aktualisieren
        customer.email = request.form.get('email', '')
        customer.phone = request.form.get('phone', '')
        customer.mobile = request.form.get('mobile', '')
        customer.street = request.form.get('street', '')
        customer.house_number = request.form.get('house_number', '')
        customer.address_supplement = request.form.get('address_supplement', '').strip() or None
        customer.postal_code = request.form.get('postal_code', '')
        customer.city = request.form.get('city', '')
        customer.country = request.form.get('country', 'Deutschland')
        customer.newsletter = request.form.get('newsletter', False) == 'on'
        customer.notes = request.form.get('notes', '')
        customer.updated_at = datetime.utcnow()
        customer.updated_by = current_user.username

        # Felder je nach aktuellem Kundentyp
        if customer.customer_type == 'business':
            customer.company_name = request.form.get('company_name')
            customer.tax_id = request.form.get('tax_id', '')
            customer.vat_id = request.form.get('vat_id', '').replace(' ', '').upper()
            customer.contact_person = request.form.get('contact_person', '')
            customer.department = request.form.get('department', '')
            customer.position = request.form.get('position', '')
        else:
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
    """DSGVO-konforme Datenlöschung: Personendaten anonymisieren, Kundennummer bleibt erhalten."""
    customer = Customer.query.get_or_404(customer_id)

    if customer.anonymized_at:
        flash('Kundendaten wurden bereits anonymisiert.', 'info')
        return redirect(url_for('customers.index'))

    customer_name = customer.display_name
    notify_email = customer.email  # vor Anonymisierung merken

    # Alle personenbezogenen Daten löschen (DSGVO Art. 17)
    from datetime import datetime as dt
    alias = f'Gelöschter Kunde ({customer.id})'
    customer.first_name = None
    customer.last_name = None
    customer.company_name = alias
    customer.email = None
    customer.phone = None
    customer.mobile = None
    customer.fax = None
    customer.street = None
    customer.house_number = None
    customer.postal_code = None
    customer.city = None
    customer.country = None
    customer.address_supplement = None
    customer.vat_id = None
    customer.tax_id = None
    customer.notes = None
    customer.anonymized_at = dt.utcnow()
    customer.updated_by = current_user.username

    # Verknüpfte Anfragen (Inquiries) anonymisieren – kein FK-Crash
    try:
        from src.models.inquiry import Inquiry
        linked_inquiries = Inquiry.query.filter_by(customer_id=customer_id).all()
        for inq in linked_inquiries:
            inq.first_name = 'Gelöscht'
            inq.last_name = customer.id
            inq.email = f'deleted-{customer.id}@anonym.local'
            inq.phone = None
            inq.company_name = alias
            inq.customer_id = None  # FK-Referenz trennen
    except Exception:
        pass  # Inquiry-Tabelle optional

    db.session.commit()
    log_activity('customer_anonymized', f'DSGVO-Löschung: {customer.id} ({customer_name})')

    # Benachrichtigungs-E-Mail an Kunden (falls E-Mail vorhanden)
    if notify_email:
        try:
            from src.models.company_settings import CompanySettings
            settings = CompanySettings.get_settings()
            from src.services.email_service_new import EmailService
            svc = EmailService()
            svc.send_email(
                to=notify_email,
                subject='Ihre Daten wurden gelöscht',
                body=(
                    f'Sehr geehrte Damen und Herren,\n\n'
                    f'gemäß Ihrer Anfrage bzw. nach Ablauf der gesetzlichen Aufbewahrungsfrist '
                    f'wurden Ihre bei uns gespeicherten personenbezogenen Daten gelöscht.\n\n'
                    f'Ihre Kundennummer ({customer.id}) bleibt aus buchhalterischen Gründen erhalten, '
                    f'ist jedoch keiner Person mehr zugeordnet.\n\n'
                    f'Mit freundlichen Grüßen\n{settings.company_name if settings else ""}'
                )
            )
        except Exception:
            pass  # E-Mail-Fehler soll Löschung nicht blockieren

    flash(f'Kundendaten von {customer_name} wurden gemäß DSGVO anonymisiert. Kundennummer {customer.id} bleibt erhalten.', 'success')
    return redirect(url_for('customers.index'))

# ==========================================
# API ENDPOINTS
# ==========================================

@customer_bp.route('/api/search', methods=['GET'])
@login_required
def api_search():
    """API: Kunden + Lieferanten durchsuchen (für CRM Schnellkontakt etc.)"""
    from flask import jsonify
    from src.models import Supplier

    q = request.args.get('q', '').strip()
    limit = int(request.args.get('limit', 15))

    if len(q) < 2:
        return jsonify({'customers': []})

    search = f'%{q}%'

    # Kunden durchsuchen
    customers = Customer.query.filter(
        db.or_(
            Customer.first_name.ilike(search),
            Customer.last_name.ilike(search),
            Customer.company_name.ilike(search),
            Customer.email.ilike(search),
            Customer.phone.ilike(search),
            Customer.mobile.ilike(search),
            Customer.customer_number.ilike(search),
        )
    ).filter_by(is_active=True).limit(limit).all()

    # Lieferanten durchsuchen
    suppliers = Supplier.query.filter(
        db.or_(
            Supplier.name.ilike(search),
            Supplier.contact_person.ilike(search),
            Supplier.email.ilike(search),
            Supplier.phone.ilike(search),
        )
    ).filter_by(active=True).limit(5).all()

    results = []
    for c in customers:
        results.append({
            'id': c.id,
            'type': 'customer',
            'display_name': c.display_name,
            'name': c.display_name,
            'company_name': c.company_name or '',
            'first_name': c.first_name or '',
            'last_name': c.last_name or '',
            'email': c.email or '',
            'phone': c.phone or c.mobile or '',
            'mobile': c.mobile or '',
        })

    for s in suppliers:
        results.append({
            'id': f'SUP:{s.id}',
            'type': 'supplier',
            'display_name': s.name,
            'name': s.name,
            'company_name': s.name,
            'first_name': s.contact_person or '',
            'last_name': '',
            'email': s.email or '',
            'phone': s.phone or '',
            'mobile': '',
        })

    return jsonify({'customers': results})


@customer_bp.route('/api/quick-create', methods=['POST'])
@login_required
def api_quick_create():
    """API: Schnell einen temporären Kontakt anlegen (aus CRM Schnellkontakt)"""
    from flask import jsonify

    name = request.json.get('name', '').strip()
    contact_type = request.json.get('contact_type', 'temporary')  # temporary, customer, supplier
    phone = request.json.get('phone', '').strip()
    email = request.json.get('email', '').strip()

    if not name:
        return jsonify({'success': False, 'error': 'Name ist erforderlich'}), 400

    # Name aufteilen
    parts = name.split(' ', 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ''

    # Kunden-ID generieren
    from datetime import datetime
    prefix = 'TMP' if contact_type == 'temporary' else 'KD'
    year = datetime.now().year
    id_prefix = f'{prefix}{year}-'

    last = Customer.query.filter(Customer.id.like(f'{id_prefix}%')).order_by(Customer.id.desc()).first()
    if last:
        try:
            num = int(last.id.split('-')[1]) + 1
        except (ValueError, IndexError):
            num = 1
    else:
        num = 1

    customer = Customer(
        id=f'{id_prefix}{num:04d}',
        first_name=first_name,
        last_name=last_name,
        email=email or None,
        phone=phone or None,
        customer_type='temporary' if contact_type == 'temporary' else 'private',
        is_active=True,
    )
    db.session.add(customer)
    db.session.commit()

    return jsonify({
        'success': True,
        'customer': {
            'id': customer.id,
            'display_name': customer.display_name,
            'name': customer.display_name,
            'email': customer.email or '',
            'phone': customer.phone or '',
        }
    })


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
