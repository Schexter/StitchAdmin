"""
Shipping Controller - PostgreSQL-Version
Versand-Verwaltung mit Datenbank
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app
from flask_login import login_required, current_user
from datetime import datetime
import io
from src.models import db, Order, Shipment, ShipmentItem, ActivityLog
from src.utils.activity_logger import log_activity

# Blueprint erstellen
shipping_bp = Blueprint('shipping', __name__, url_prefix='/shipping')

def generate_shipment_id():
    """Generiere neue Versand-ID"""
    current_year = datetime.now().year
    prefix = f"VS{current_year}-"
    
    last_shipment = Shipment.query.filter(
        Shipment.id.like(f'{prefix}%')
    ).order_by(Shipment.id.desc()).first()
    
    if last_shipment:
        try:
            last_num = int(last_shipment.id.split('-')[1])
            return f"{prefix}{last_num + 1:04d}"
        except (ValueError, IndexError):
            return f"{prefix}0001"
    return f"{prefix}0001"

@shipping_bp.route('/')
@login_required
def index():
    """Versand-Übersicht"""
    status_filter = request.args.get('status', '')
    carrier_filter = request.args.get('carrier', '')

    # Query erstellen
    query = Shipment.query

    if status_filter:
        query = query.filter_by(status=status_filter)

    if carrier_filter:
        query = query.filter_by(carrier=carrier_filter)

    # Nach Datum sortieren (neueste zuerst)
    shipments = query.order_by(Shipment.created_at.desc()).all()

    # Versandbereit Aufträge nach Lieferart trennen
    all_ready = Order.query.filter_by(status='ready').all()
    abholung_orders = [o for o in all_ready if o.delivery_type == 'pickup']
    versand_orders = [o for o in all_ready if o.delivery_type != 'pickup']
    ready_orders = all_ready  # Rückwärtskompatibilität

    # Statistiken
    stats = {
        'pending': Shipment.query.filter_by(status='created').count(),
        'shipped': Shipment.query.filter_by(status='shipped').count(),
        'delivered': Shipment.query.filter_by(status='delivered').count(),
        'ready_to_ship': len(versand_orders),
        'abholung': len(abholung_orders),
    }

    # Verfügbare Carrier
    carriers = ['DHL', 'DPD', 'UPS', 'GLS', 'Hermes', 'Post', 'Abholung']

    return render_template('shipping/index.html',
                         shipments=shipments,
                         ready_orders=ready_orders,
                         versand_orders=versand_orders,
                         abholung_orders=abholung_orders,
                         carriers=carriers,
                         status_filter=status_filter,
                         carrier_filter=carrier_filter,
                         stats=stats)

@shipping_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Neuen Versand erstellen"""
    if request.method == 'POST':
        order_id = request.form.get('order_id')
        order = Order.query.get_or_404(order_id)
        
        # Prüfen ob Auftrag versandbereit ist
        if order.status != 'ready':
            flash('Nur fertige Aufträge können versendet werden!', 'danger')
            return redirect(url_for('shipping.index'))
        
        # Versand erstellen
        shipment = Shipment(
            id=generate_shipment_id(),
            order_id=order_id,
            tracking_number=request.form.get('tracking_number', ''),
            carrier=request.form.get('carrier'),
            service=request.form.get('service', 'Standard'),
            weight=float(request.form.get('weight', 0) or 0),
            length=float(request.form.get('length', 0) or 0),
            width=float(request.form.get('width', 0) or 0),
            height=float(request.form.get('height', 0) or 0),
            shipping_cost=float(request.form.get('shipping_cost', 0) or 0),
            insurance_value=float(request.form.get('insurance_value', 0) or 0),
            status='created',
            created_by=current_user.username
        )
        
        # Empfänger-Adresse
        if order.customer:
            shipment.recipient_name = order.customer.display_name
            shipment.recipient_street = f"{order.customer.street} {order.customer.house_number}".strip()
            shipment.recipient_postal_code = order.customer.postal_code
            shipment.recipient_city = order.customer.city
            shipment.recipient_country = order.customer.country or 'Deutschland'
        
        # Alternative Adresse wenn angegeben
        if request.form.get('use_custom_address'):
            shipment.recipient_name = request.form.get('recipient_name')
            shipment.recipient_street = request.form.get('recipient_street')
            shipment.recipient_postal_code = request.form.get('recipient_postal_code')
            shipment.recipient_city = request.form.get('recipient_city')
            shipment.recipient_country = request.form.get('recipient_country', 'Deutschland')
        
        db.session.add(shipment)
        
        # Versand-Items aus Auftrag übernehmen
        for order_item in order.items:
            shipment_item = ShipmentItem(
                shipment_id=shipment.id,
                order_item_id=order_item.id,
                quantity=order_item.quantity,
                description=f"{order_item.article.name if order_item.article else 'Artikel'} - {order_item.textile_size} {order_item.textile_color}".strip()
            )
            db.session.add(shipment_item)
        
        db.session.commit()
        
        # Aktivität protokollieren
        log_activity('shipment_created', 
                    f'Versand erstellt: {shipment.id} für Auftrag {order_id}')
        
        flash(f'Versand {shipment.id} wurde erstellt!', 'success')
        
        # Direkt zum Versand-Label
        if request.form.get('print_label'):
            return redirect(url_for('shipping.label', shipment_id=shipment.id))
        
        return redirect(url_for('shipping.show', shipment_id=shipment.id))
    
    # Versandbereit Aufträge für Formular
    ready_orders = Order.query.filter_by(status='ready').all()
    selected_order_id = request.args.get('order_id')
    
    return render_template('shipping/new.html',
                         ready_orders=ready_orders,
                         selected_order_id=selected_order_id,
                         carriers=['DHL', 'DPD', 'UPS', 'GLS', 'Hermes', 'Post', 'Abholung'])

@shipping_bp.route('/<shipment_id>')
@login_required
def show(shipment_id):
    """Versand-Details anzeigen"""
    shipment = Shipment.query.get_or_404(shipment_id)
    
    return render_template('shipping/show.html', shipment=shipment)

@shipping_bp.route('/<shipment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(shipment_id):
    """Versand bearbeiten"""
    shipment = Shipment.query.get_or_404(shipment_id)
    
    if shipment.status == 'delivered':
        flash('Zugestellte Sendungen können nicht mehr bearbeitet werden!', 'danger')
        return redirect(url_for('shipping.show', shipment_id=shipment_id))
    
    if request.method == 'POST':
        # Versand aktualisieren
        shipment.tracking_number = request.form.get('tracking_number', '')
        shipment.carrier = request.form.get('carrier')
        shipment.service = request.form.get('service', 'Standard')
        shipment.weight = float(request.form.get('weight', 0) or 0)
        shipment.length = float(request.form.get('length', 0) or 0)
        shipment.width = float(request.form.get('width', 0) or 0)
        shipment.height = float(request.form.get('height', 0) or 0)
        shipment.shipping_cost = float(request.form.get('shipping_cost', 0) or 0)
        shipment.insurance_value = float(request.form.get('insurance_value', 0) or 0)
        
        # Empfänger-Adresse
        shipment.recipient_name = request.form.get('recipient_name')
        shipment.recipient_street = request.form.get('recipient_street')
        shipment.recipient_postal_code = request.form.get('recipient_postal_code')
        shipment.recipient_city = request.form.get('recipient_city')
        shipment.recipient_country = request.form.get('recipient_country', 'Deutschland')
        
        shipment.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Aktivität protokollieren
        log_activity('shipment_updated', 
                    f'Versand aktualisiert: {shipment.id}')
        
        flash('Versand wurde aktualisiert!', 'success')
        return redirect(url_for('shipping.show', shipment_id=shipment.id))
    
    return render_template('shipping/edit.html',
                         shipment=shipment,
                         carriers=['DHL', 'DPD', 'UPS', 'GLS', 'Hermes', 'Post', 'Abholung'])

@shipping_bp.route('/<shipment_id>/ship', methods=['POST'])
@login_required
def mark_shipped(shipment_id):
    """Versand als versendet markieren"""
    shipment = Shipment.query.get_or_404(shipment_id)
    
    if shipment.status != 'created':
        flash('Nur erstellte Sendungen können als versendet markiert werden!', 'danger')
        return redirect(url_for('shipping.show', shipment_id=shipment_id))
    
    # Status aktualisieren
    shipment.status = 'shipped'
    shipment.shipped_date = datetime.utcnow()
    
    # Auftragsstatus aktualisieren
    if shipment.order:
        shipment.order.status = 'completed'
        shipment.order.completed_at = datetime.utcnow()
        shipment.order.completed_by = current_user.username
        
        # Status-Historie
        from src.models import OrderStatusHistory
        history = OrderStatusHistory(
            order_id=shipment.order_id,
            from_status='ready',
            to_status='completed',
            comment=f'Versendet mit {shipment.carrier} - Tracking: {shipment.tracking_number}',
            changed_by=current_user.username
        )
        db.session.add(history)
    
    db.session.commit()
    
    # Aktivität protokollieren
    log_activity('shipment_shipped', 
                f'Versand versendet: {shipment.id}')
    
    # E-Mail an Kunden senden via Automation
    try:
        from src.services.email_automation_service import EmailAutomationService
        automation = EmailAutomationService()
        automation.check_and_send(shipment.order, 'workflow_status', 'shipped')
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f'Versand-Automation: {e}')

    flash('Versand wurde als versendet markiert!', 'success')
    return redirect(url_for('shipping.show', shipment_id=shipment_id))

@shipping_bp.route('/<shipment_id>/tracking', methods=['POST'])
@login_required
def update_tracking(shipment_id):
    """Sendungsnummer nachträglich eintragen/ändern"""
    shipment = Shipment.query.get_or_404(shipment_id)

    shipment.tracking_number = request.form.get('tracking_number', '').strip()
    shipment.updated_at = datetime.utcnow()
    db.session.commit()

    log_activity('tracking_updated',
                f'Sendungsnummer aktualisiert: {shipment.id} → {shipment.tracking_number}')

    flash('Sendungsnummer wurde gespeichert!', 'success')
    return redirect(url_for('shipping.show', shipment_id=shipment_id))


@shipping_bp.route('/<shipment_id>/send-tracking', methods=['POST'])
@login_required
def send_tracking_email(shipment_id):
    """Tracking-Info per E-Mail an Kunden senden"""
    shipment = Shipment.query.get_or_404(shipment_id)

    if not shipment.tracking_number:
        flash('Bitte zuerst eine Sendungsnummer eintragen!', 'warning')
        return redirect(url_for('shipping.show', shipment_id=shipment_id))

    customer = shipment.order.customer if shipment.order else None
    if not customer or not customer.email:
        flash('Kunde hat keine E-Mail-Adresse hinterlegt!', 'danger')
        return redirect(url_for('shipping.show', shipment_id=shipment_id))

    # Tracking-URL je nach Carrier
    tracking_url = ''
    if shipment.carrier == 'DHL':
        tracking_url = f'https://www.dhl.de/de/privatkunden/pakete-empfangen/verfolgen.html?piececode={shipment.tracking_number}'
    elif shipment.carrier == 'DPD':
        tracking_url = f'https://tracking.dpd.de/parcelstatus?query={shipment.tracking_number}'
    elif shipment.carrier == 'UPS':
        tracking_url = f'https://www.ups.com/track?tracknum={shipment.tracking_number}'
    elif shipment.carrier == 'GLS':
        tracking_url = f'https://gls-group.eu/DE/de/paketverfolgung?match={shipment.tracking_number}'
    elif shipment.carrier == 'Hermes':
        tracking_url = f'https://www.myhermes.de/empfangen/sendungsverfolgung/sendungsinformation/#{shipment.tracking_number}'

    order_nr = shipment.order.order_number or shipment.order_id if shipment.order else shipment.id

    try:
        from src.utils.email_service import send_email
        subject = f'Ihre Sendung ist unterwegs – Auftrag {order_nr}'

        body = f"""Guten Tag {customer.first_name or ''} {customer.last_name or ''},

Ihr Auftrag {order_nr} wurde versendet!

Versanddienstleister: {shipment.carrier}
Sendungsnummer: {shipment.tracking_number}
"""
        if tracking_url:
            body += f"""
Sie können Ihre Sendung hier verfolgen:
{tracking_url}
"""
        body += """
Mit freundlichen Grüßen
Ihr Team"""

        send_email(to_email=customer.email, subject=subject, body=body)
        flash(f'Tracking-Info an {customer.email} gesendet!', 'success')
        log_activity('tracking_email_sent',
                    f'Tracking-Mail für {shipment.id} an {customer.email}')
    except Exception as e:
        flash(f'E-Mail konnte nicht gesendet werden: {e}', 'danger')

    return redirect(url_for('shipping.show', shipment_id=shipment_id))


@shipping_bp.route('/<shipment_id>/delivered', methods=['POST'])
@login_required
def mark_delivered(shipment_id):
    """Versand als zugestellt markieren"""
    shipment = Shipment.query.get_or_404(shipment_id)
    
    if shipment.status != 'shipped':
        flash('Nur versendete Sendungen können als zugestellt markiert werden!', 'danger')
        return redirect(url_for('shipping.show', shipment_id=shipment_id))
    
    # Status aktualisieren
    shipment.status = 'delivered'
    shipment.delivered_date = datetime.utcnow()
    
    db.session.commit()
    
    # Aktivität protokollieren
    log_activity('shipment_delivered', 
                f'Versand zugestellt: {shipment.id}')
    
    flash('Versand wurde als zugestellt markiert!', 'success')
    return redirect(url_for('shipping.show', shipment_id=shipment_id))

@shipping_bp.route('/<shipment_id>/label')
@login_required
def label(shipment_id):
    """Versandlabel anzeigen/drucken"""
    shipment = Shipment.query.get_or_404(shipment_id)
    
    # Absender-Daten (Firmen-Daten)
    # TODO: Diese sollten aus den Einstellungen oder einer Config kommen
    sender = {
        'company': 'StitchAdmin GmbH',
        'name': 'Versandabteilung',
        'street': 'Musterstraße 123',
        'postal_code': '12345',
        'city': 'Musterstadt',
        'country': 'Deutschland',
        'phone': '+49 123 456789'
    }
    
    # Generierungszeitpunkt
    generated_at = datetime.now()
    
    return render_template('shipping/label.html', 
                         shipment=shipment,
                         sender=sender,
                         generated_at=generated_at)

@shipping_bp.route('/<shipment_id>/delete', methods=['POST'])
@login_required
def delete(shipment_id):
    """Versand löschen"""
    shipment = Shipment.query.get_or_404(shipment_id)
    
    if shipment.status != 'created':
        flash('Nur erstellte (nicht versendete) Sendungen können gelöscht werden!', 'danger')
        return redirect(url_for('shipping.show', shipment_id=shipment_id))
    
    # Aktivität protokollieren bevor gelöscht wird
    log_activity('shipment_deleted', 
                f'Versand gelöscht: {shipment.id}')
    
    # Versand löschen
    db.session.delete(shipment)
    db.session.commit()
    
    flash('Versand wurde gelöscht!', 'success')
    return redirect(url_for('shipping.index'))


# ═══════════════════════════════════════════════════════════════════════════════
# PROBEBOX (Versand ohne Auftrag, z.B. aus Anfrage)
# ═══════════════════════════════════════════════════════════════════════════════

@shipping_bp.route('/probebox', methods=['GET', 'POST'])
@login_required
def probebox():
    """Probebox erstellen (Versand ohne Auftrag)"""
    from src.models.inquiry import Inquiry

    if request.method == 'POST':
        inquiry_id = request.form.get('inquiry_id') or None

        # Versand erstellen
        shipment = Shipment(
            id=generate_shipment_id(),
            shipment_type='probebox',
            inquiry_id=int(inquiry_id) if inquiry_id else None,
            description=request.form.get('description', 'Probebox').strip(),
            tracking_number=request.form.get('tracking_number', ''),
            carrier=request.form.get('carrier', 'DHL'),
            service=request.form.get('service', 'Standard'),
            weight=float(request.form.get('weight', 0) or 0),
            length=float(request.form.get('length', 0) or 0),
            width=float(request.form.get('width', 0) or 0),
            height=float(request.form.get('height', 0) or 0),
            shipping_cost=float(request.form.get('shipping_cost', 0) or 0),
            recipient_name=request.form.get('recipient_name', ''),
            recipient_street=request.form.get('recipient_street', ''),
            recipient_postal_code=request.form.get('recipient_postal_code', ''),
            recipient_city=request.form.get('recipient_city', ''),
            recipient_country=request.form.get('recipient_country', 'Deutschland'),
            status='created',
            created_by=current_user.username
        )

        # Positionen (Inhalt der Probebox)
        item_descriptions = request.form.getlist('item_description')
        item_quantities = request.form.getlist('item_quantity')
        for desc, qty in zip(item_descriptions, item_quantities):
            if desc and desc.strip():
                item = ShipmentItem(
                    shipment_id=shipment.id,
                    quantity=int(qty) if qty else 1,
                    description=desc.strip()
                )
                db.session.add(item)

        db.session.add(shipment)
        db.session.commit()

        log_activity('shipment_created',
                     f'Probebox erstellt: {shipment.id}' +
                     (f' fuer Anfrage {inquiry_id}' if inquiry_id else ''))

        flash(f'Probebox {shipment.id} wurde erstellt!', 'success')
        return redirect(url_for('shipping.show', shipment_id=shipment.id))

    # GET: Formular
    inquiry_id = request.args.get('inquiry_id')
    inquiry = None
    prefill = {}

    if inquiry_id:
        inquiry = Inquiry.query.get(inquiry_id)
        if inquiry:
            # Adresse aus Kunde oder Anfrage vorbelegen
            if inquiry.customer:
                c = inquiry.customer
                prefill = {
                    'name': c.display_name,
                    'street': f"{c.street or ''} {c.house_number or ''}".strip(),
                    'postal_code': c.postal_code or '',
                    'city': c.city or '',
                    'country': c.country or 'Deutschland'
                }
            else:
                name = f"{inquiry.first_name or ''} {inquiry.last_name or ''}".strip()
                if inquiry.company_name:
                    name = f"{inquiry.company_name} - {name}"
                prefill = {'name': name}

    carriers = ['DHL', 'DPD', 'UPS', 'GLS', 'Hermes', 'Post']

    return render_template('shipping/probebox.html',
                           inquiry=inquiry,
                           prefill=prefill,
                           carriers=carriers)


# DPD CSV-Export
@shipping_bp.route('/export/dpd')
@login_required
def export_dpd():
    """DPD-Export für myDPD Business Portal"""
    from src.utils.dpd_csv import build_dpd_row, generate_dpd_csv, parse_address_for_dpd
    from src.models.company_settings import CompanySettings

    # Welche Sendungen exportieren?
    ids = request.args.get('ids', '')
    if ids:
        shipment_ids = [s.strip() for s in ids.split(',') if s.strip()]
        shipments = Shipment.query.filter(Shipment.id.in_(shipment_ids)).all()
    else:
        # Alle erstellten (noch nicht versendeten) Sendungen
        shipments = Shipment.query.filter_by(status='created').order_by(Shipment.created_at.desc()).all()

    if not shipments:
        flash('Keine Sendungen zum Exportieren gefunden', 'warning')
        return redirect(url_for('shipping.index'))

    settings = CompanySettings.get_settings()
    rows = []

    for s in shipments:
        # Adresse parsen
        addr = parse_address_for_dpd(
            s.recipient_name or '',
            s.recipient_street or ''
        )

        # Kunden-Daten für Telefon/Email
        customer = s.order.customer if s.order else None

        rows.append({
            'firma': addr['firma'],
            'vorname': addr['vorname'],
            'nachname': addr['nachname'],
            'strasse': addr['strasse'],
            'hausnummer': addr['hausnummer'],
            'plz': s.recipient_postal_code or '',
            'ort': s.recipient_city or '',
            'land': _country_code(s.recipient_country),
            'telefon': (customer.phone if customer and hasattr(customer, 'phone') else '') or '',
            'email': (customer.email if customer and hasattr(customer, 'email') else '') or '',
            'gewicht': s.weight or 0.5,
            'referenz': s.order_id or s.id,
            'referenz2': s.id,
            'inhalt': 'Textilien/Stickerei',
        })

    csv_bytes = generate_dpd_csv(rows)
    filename = f'dpd_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

    log_activity('dpd_export', f'{len(rows)} Sendungen als DPD-CSV exportiert')

    return send_file(
        io.BytesIO(csv_bytes),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


def _country_code(country_str):
    """Konvertiert Ländernamen zu ISO-Code"""
    if not country_str:
        return 'DE'
    country_str = country_str.strip().upper()
    if country_str in ('DE', 'AT', 'CH', 'NL', 'BE', 'FR', 'IT', 'PL', 'CZ'):
        return country_str
    mapping = {
        'DEUTSCHLAND': 'DE', 'GERMANY': 'DE',
        'OESTERREICH': 'AT', 'AUSTRIA': 'AT',
        'SCHWEIZ': 'CH', 'SWITZERLAND': 'CH',
        'NIEDERLANDE': 'NL', 'NETHERLANDS': 'NL',
        'BELGIEN': 'BE', 'BELGIUM': 'BE',
        'FRANKREICH': 'FR', 'FRANCE': 'FR',
        'ITALIEN': 'IT', 'ITALY': 'IT',
        'POLEN': 'PL', 'POLAND': 'PL',
        'TSCHECHIEN': 'CZ', 'CZECH REPUBLIC': 'CZ',
    }
    return mapping.get(country_str, 'DE')


# Abholung & Unterschrift
@shipping_bp.route('/abholung/<order_id>/unterschrift', methods=['GET'])
@login_required
def abholung_unterschrift(order_id):
    """Unterschrift-Pad für Abholung (Fullscreen, Touchscreen-optimiert)"""
    order = Order.query.get_or_404(order_id)
    return render_template('shipping/abholung_unterschrift.html', order=order)


@shipping_bp.route('/abholung/<order_id>/unterschrift-mail')
@login_required
def abholung_unterschrift_mail(order_id):
    """Sendet dem Kunden einen Link zur Unterschrift per E-Mail"""
    order = Order.query.get_or_404(order_id)
    customer = order.customer

    if not customer or not customer.email:
        flash('Kunde hat keine E-Mail-Adresse hinterlegt!', 'danger')
        return redirect(url_for('shipping.index'))

    # Token für externen Zugang generieren (ohne Login)
    import hashlib
    token = hashlib.sha256(f'{order.id}-{order.created_at}-pickup'.encode()).hexdigest()[:32]
    order.pickup_token = token
    db.session.commit()

    # URL für externe Unterschrift
    from flask import url_for as _url_for
    sign_url = _url_for('shipping.abholung_unterschrift_extern', order_id=order.id, token=token, _external=True)

    # E-Mail senden
    try:
        from src.utils.email_service import send_email
        subject = f'Abholung bestätigen – Auftrag {order.order_number or order.id}'
        body = f"""Guten Tag {customer.first_name or ''} {customer.last_name or ''},

Ihr Auftrag {order.order_number or order.id} ist fertig und kann abgeholt werden.

Bitte bestätigen Sie die Abholung mit Ihrer Unterschrift unter folgendem Link:

{sign_url}

Mit freundlichen Grüßen
Ihr Team"""

        send_email(to_email=customer.email, subject=subject, body=body)
        flash(f'Unterschrift-Link an {customer.email} gesendet!', 'success')
        log_activity('abholung_mail_gesendet', f'Unterschrift-Mail für Auftrag {order.id} an {customer.email}')
    except Exception as e:
        flash(f'E-Mail konnte nicht gesendet werden: {e}', 'danger')

    return redirect(url_for('shipping.index'))


@shipping_bp.route('/abholung/<order_id>/unterschrift-extern/<token>', methods=['GET'])
def abholung_unterschrift_extern(order_id, token):
    """Externe Unterschrift-Seite (ohne Login, über Token)"""
    order = Order.query.get_or_404(order_id)

    if not hasattr(order, 'pickup_token') or order.pickup_token != token:
        return 'Ungültiger oder abgelaufener Link.', 403

    if order.pickup_confirmed_at:
        return render_template('shipping/abholung_bereits_bestaetigt.html', order=order)

    return render_template('shipping/abholung_unterschrift.html', order=order, extern=True, token=token)


@shipping_bp.route('/abholung/<order_id>/unterschrift-extern-speichern/<token>', methods=['POST'])
def abholung_unterschrift_extern_speichern(order_id, token):
    """Externe Unterschrift speichern (ohne Login)"""
    import base64
    import os as _os

    order = Order.query.get_or_404(order_id)

    if not hasattr(order, 'pickup_token') or order.pickup_token != token:
        return jsonify({'success': False, 'error': 'Ungültiger Link'}), 403

    if order.pickup_confirmed_at:
        return jsonify({'success': False, 'error': 'Bereits bestätigt'}), 400

    signature_data = request.form.get('signature', '')
    abholer_name = request.form.get('abholer_name', '').strip()

    if not signature_data or not signature_data.startswith('data:image/png;base64,'):
        return jsonify({'success': False, 'error': 'Keine gültige Unterschrift'}), 400

    try:
        b64 = signature_data.split(',', 1)[1]
        png_bytes = base64.b64decode(b64)

        unterschriften_dir = _os.path.join(current_app.root_path, '..', 'instance', 'unterschriften')
        _os.makedirs(unterschriften_dir, exist_ok=True)

        dateiname = f'abholung_{order_id}_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.png'
        pfad = _os.path.join(unterschriften_dir, dateiname)
        with open(pfad, 'wb') as f:
            f.write(png_bytes)

        order.confirm_pickup(signature=signature_data, signature_name=abholer_name or 'Unterschrift per Mail')
        order.status = 'completed'
        order.completed_at = datetime.utcnow()
        order.pickup_token = None  # Token ungültig machen

        from src.models import OrderStatusHistory
        history = OrderStatusHistory(
            order_id=order.id,
            from_status='ready',
            to_status='completed',
            comment=f'Abgeholt (Unterschrift per Mail) von: {abholer_name or "Kunde"}',
            changed_by='extern'
        )
        db.session.add(history)
        db.session.commit()

        log_activity('abholung_extern_bestaetigt', f'Auftrag {order_id} extern bestätigt von {abholer_name}')
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

    return jsonify({'success': True, 'redirect': '/abholung-danke'})


@shipping_bp.route('/abholung/<order_id>/unterschrift-speichern', methods=['POST'])
@login_required
def abholung_unterschrift_speichern(order_id):
    """Unterschrift speichern + Auftrag als abgeholt markieren"""
    import base64
    import os as _os

    order = Order.query.get_or_404(order_id)

    signature_data = request.form.get('signature', '')
    abholer_name = request.form.get('abholer_name', '').strip()

    if not signature_data or not signature_data.startswith('data:image/png;base64,'):
        return jsonify({'success': False, 'error': 'Keine gültige Unterschrift übermittelt'}), 400

    # Base64-Daten extrahieren und als PNG speichern
    try:
        b64 = signature_data.split(',', 1)[1]
        png_bytes = base64.b64decode(b64)

        unterschriften_dir = _os.path.join(
            current_app.root_path, '..', 'instance', 'unterschriften'
        )
        _os.makedirs(unterschriften_dir, exist_ok=True)

        dateiname = f'abholung_{order_id}_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.png'
        pfad = _os.path.join(unterschriften_dir, dateiname)
        with open(pfad, 'wb') as f:
            f.write(png_bytes)

        # Unterschrift + Name am Auftrag speichern
        order.confirm_pickup(
            signature=signature_data,   # Base64 für direkte Anzeige im Browser
            signature_name=abholer_name or 'Unterschrift erfasst'
        )
        order.status = 'completed'
        order.completed_at = datetime.utcnow()
        order.completed_by = current_user.username

        from src.models import OrderStatusHistory
        history = OrderStatusHistory(
            order_id=order.id,
            from_status='ready',
            to_status='completed',
            comment=f'Abgeholt von: {abholer_name or "Unbekannt"} — Unterschrift erfasst',
            changed_by=current_user.username
        )
        db.session.add(history)
        db.session.commit()

        log_activity('abholung_bestaetigt',
                     f'Auftrag {order_id} abgeholt von {abholer_name}')

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

    return jsonify({'success': True, 'redirect': url_for('shipping.index')})


@shipping_bp.route('/abholung/<order_id>/unterschrift-bild')
@login_required
def abholung_unterschrift_bild(order_id):
    """Unterschrift-PNG direkt ausliefern"""
    import base64
    from flask import Response
    order = Order.query.get_or_404(order_id)
    if not order.pickup_signature:
        return '', 404
    b64 = order.pickup_signature.split(',', 1)[1]
    png_bytes = base64.b64decode(b64)
    return Response(png_bytes, mimetype='image/png')


# DHL CSV-Export (multi-select)
@shipping_bp.route('/export/dhl')
@login_required
def export_dhl():
    """DHL Business CSV-Export"""
    from src.utils.dpd_csv import build_dhl_row, generate_dhl_csv, parse_address_for_dpd
    from src.models.company_settings import CompanySettings

    ids = request.args.get('ids', '')
    if ids:
        shipment_ids = [s.strip() for s in ids.split(',') if s.strip()]
        shipments = Shipment.query.filter(Shipment.id.in_(shipment_ids)).all()
    else:
        shipments = Shipment.query.filter_by(status='created').order_by(Shipment.created_at.desc()).all()

    if not shipments:
        flash('Keine Sendungen zum Exportieren gefunden', 'warning')
        return redirect(url_for('shipping.index'))

    rows = []
    for s in shipments:
        addr = parse_address_for_dpd(s.recipient_name or '', s.recipient_street or '')
        customer = s.order.customer if s.order else None
        rows.append({
            'referenz': s.order_id or s.id,
            'referenz2': s.id,
            'firma': addr['firma'],
            'vorname': addr['vorname'],
            'nachname': addr['nachname'],
            'strasse': addr['strasse'],
            'hausnummer': addr['hausnummer'],
            'plz': s.recipient_postal_code or '',
            'ort': s.recipient_city or '',
            'land': _country_code(s.recipient_country),
            'telefon': (customer.phone if customer and hasattr(customer, 'phone') else '') or '',
            'email': (customer.email if customer and hasattr(customer, 'email') else '') or '',
            'gewicht': s.weight or 0.5,
            'inhalt': 'Textilien/Stickerei',
        })

    csv_bytes = generate_dhl_csv(rows)
    filename = f'dhl_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    log_activity('dhl_export', f'{len(rows)} Sendungen als DHL-CSV exportiert')

    return send_file(
        io.BytesIO(csv_bytes),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


# Auftrags-basierter CSV-Export (direkt aus versandbereiten Aufträgen)
@shipping_bp.route('/export/orders/dpd')
@login_required
def export_orders_dpd():
    """DPD CSV aus versandbereiten Aufträgen (ohne vorher Sendung anlegen)"""
    from src.utils.dpd_csv import generate_dpd_csv
    ids = request.args.get('ids', '')
    if not ids:
        flash('Keine Aufträge ausgewählt', 'warning')
        return redirect(url_for('shipping.index'))

    order_ids = [s.strip() for s in ids.split(',') if s.strip()]
    orders = Order.query.filter(Order.id.in_(order_ids)).all()

    if not orders:
        flash('Keine Aufträge gefunden', 'warning')
        return redirect(url_for('shipping.index'))

    rows = []
    for o in orders:
        c = o.customer
        if not c:
            continue
        rows.append({
            'firma': c.company_name or '',
            'vorname': c.first_name or '',
            'nachname': c.last_name or '',
            'strasse': c.street or '',
            'hausnummer': c.house_number or '',
            'adresszusatz': c.address_supplement or '',
            'plz': c.postal_code or '',
            'ort': c.city or '',
            'land': _country_code(c.country),
            'telefon': c.phone or c.mobile or '',
            'email': c.email or '',
            'gewicht': 0.5,
            'referenz': o.order_number or o.id,
            'inhalt': 'Textilien/Stickerei',
        })

    if not rows:
        flash('Keine Adressen für den Export gefunden', 'warning')
        return redirect(url_for('shipping.index'))

    csv_bytes = generate_dpd_csv(rows)
    filename = f'dpd_auftraege_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    log_activity('dpd_export', f'{len(rows)} Aufträge als DPD-CSV exportiert')
    return send_file(io.BytesIO(csv_bytes), mimetype='text/csv',
                     as_attachment=True, download_name=filename)


@shipping_bp.route('/export/orders/dhl')
@login_required
def export_orders_dhl():
    """DHL Business CSV aus versandbereiten Aufträgen"""
    from src.utils.dpd_csv import generate_dhl_csv
    ids = request.args.get('ids', '')
    if not ids:
        flash('Keine Aufträge ausgewählt', 'warning')
        return redirect(url_for('shipping.index'))

    order_ids = [s.strip() for s in ids.split(',') if s.strip()]
    orders = Order.query.filter(Order.id.in_(order_ids)).all()

    if not orders:
        flash('Keine Aufträge gefunden', 'warning')
        return redirect(url_for('shipping.index'))

    rows = []
    for o in orders:
        c = o.customer
        if not c:
            continue
        rows.append({
            'referenz': o.order_number or o.id,
            'firma': c.company_name or '',
            'vorname': c.first_name or '',
            'nachname': c.last_name or '',
            'strasse': c.street or '',
            'hausnummer': c.house_number or '',
            'plz': c.postal_code or '',
            'ort': c.city or '',
            'land': _country_code(c.country),
            'telefon': c.phone or c.mobile or '',
            'email': c.email or '',
            'gewicht': 0.5,
            'inhalt': 'Textilien/Stickerei',
        })

    if not rows:
        flash('Keine Adressen für den Export gefunden', 'warning')
        return redirect(url_for('shipping.index'))

    csv_bytes = generate_dhl_csv(rows)
    filename = f'dhl_auftraege_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    log_activity('dhl_export', f'{len(rows)} Aufträge als DHL-CSV exportiert')
    return send_file(io.BytesIO(csv_bytes), mimetype='text/csv',
                     as_attachment=True, download_name=filename)


# API-Endpoints
@shipping_bp.route('/api/tracking/<tracking_number>')
@login_required
def api_tracking_status(tracking_number):
    """Tracking-Status abrufen (Mock)"""
    # TODO: Integration mit echten Carrier-APIs
    return jsonify({
        'tracking_number': tracking_number,
        'status': 'in_transit',
        'last_update': datetime.now().isoformat(),
        'events': [
            {
                'date': datetime.now().isoformat(),
                'status': 'Paket ist unterwegs',
                'location': 'Paketzentrum Frankfurt'
            }
        ]
    })
