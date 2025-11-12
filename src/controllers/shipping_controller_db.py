"""
Shipping Controller - PostgreSQL-Version
Versand-Verwaltung mit Datenbank
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from src.models import db, Order, Shipment, ShipmentItem, ActivityLog

# Blueprint erstellen
shipping_bp = Blueprint('shipping', __name__, url_prefix='/shipping')

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
        except:
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
    
    # Versandbereit Aufträge (Status: ready)
    ready_orders = Order.query.filter_by(status='ready').all()
    
    # Statistiken
    stats = {
        'pending': Shipment.query.filter_by(status='created').count(),
        'shipped': Shipment.query.filter_by(status='shipped').count(),
        'delivered': Shipment.query.filter_by(status='delivered').count(),
        'ready_to_ship': len(ready_orders)
    }
    
    # Verfügbare Carrier
    carriers = ['DHL', 'DPD', 'UPS', 'GLS', 'Hermes', 'Post', 'Abholung']
    
    return render_template('shipping/index.html',
                         shipments=shipments,
                         ready_orders=ready_orders,
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
    
    # E-Mail an Kunden senden (TODO: E-Mail-Service implementieren)
    
    flash('Versand wurde als versendet markiert!', 'success')
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
