"""
Order Controller - PostgreSQL-Version
Auftrags-Verwaltung mit Datenbank
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
from src.models import db, Order, Customer, Article, OrderItem, ActivityLog, Supplier
from sqlalchemy import text
from src.utils.dst_analyzer import analyze_dst_file_robust
from werkzeug.utils import secure_filename
import json
import os

# Blueprint erstellen
order_bp = Blueprint('orders', __name__, url_prefix='/orders')

def log_activity(action, details):
    """Aktivität in Datenbank protokollieren"""
    activity = ActivityLog(
        username=current_user.username,  # Geändert von 'user' zu 'username'
        action=action,
        details=details,
        ip_address=request.remote_addr
    )
    db.session.add(activity)
    db.session.commit()

def generate_order_id():
    """Generiere neue Auftrags-ID im Format A2025-XXX"""
    current_year = datetime.now().year
    prefix = f"A{current_year}-"
    
    # Finde höchste ID für dieses Jahr
    last_order = Order.query.filter(
        Order.id.like(f'{prefix}%')
    ).order_by(Order.id.desc()).first()
    
    if last_order:
        try:
            last_num = int(last_order.id.split('-')[1])
            return f"{prefix}{last_num + 1:03d}"
        except:
            return f"{prefix}001"
    return f"{prefix}001"

@order_bp.route('/')
@login_required
def index():
    """Auftrags-Übersicht"""
    status_filter = request.args.get('status', '')
    search_query = request.args.get('search', '').lower()
    
    # Query erstellen
    query = Order.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    if search_query:
        query = query.join(Customer).filter(
            db.or_(
                Order.id.ilike(f'%{search_query}%'),
                Order.order_number.ilike(f'%{search_query}%'),
                Customer.company_name.ilike(f'%{search_query}%'),
                Customer.first_name.ilike(f'%{search_query}%'),
                Customer.last_name.ilike(f'%{search_query}%'),
                Order.description.ilike(f'%{search_query}%')
            )
        )
    
    # Nach Datum sortieren (neueste zuerst)
    orders = query.order_by(Order.created_at.desc()).all()
    
    return render_template('orders/index.html',
                         orders=orders,
                         status_filter=status_filter,
                         search_query=search_query)

@order_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Neuen Auftrag erstellen"""
    if request.method == 'POST':
        # Neuen Auftrag erstellen
        order = Order(
            id=generate_order_id(),
            order_number=generate_order_id(),  # Gleich wie ID
            customer_id=request.form.get('customer_id'),
            order_type=request.form.get('order_type', 'embroidery'),
            status='accepted',
            description=request.form.get('description', ''),
            internal_notes=request.form.get('notes', ''),
            customer_notes=request.form.get('customer_notes', ''),
            total_price=float(request.form.get('price', 0) or 0),
            due_date=request.form.get('pickup_date') or None,
            rush_order=request.form.get('rush_order', False) == 'on',
            created_by=current_user.username
        )
        
        # Order-Type spezifische Felder
        if order.order_type in ['embroidery', 'combined']:
            order.stitch_count = int(request.form.get('stitch_count', 0) or 0)
            order.design_width_mm = float(request.form.get('design_width_mm', 0) or 0)
            order.design_height_mm = float(request.form.get('design_height_mm', 0) or 0)
            order.embroidery_position = request.form.get('embroidery_position', '')
            order.embroidery_size = request.form.get('embroidery_size', '')
            order.thread_colors = request.form.get('thread_colors', '')
        
        if order.order_type in ['printing', 'dtf', 'combined']:
            order.print_width_cm = float(request.form.get('print_width_cm', 0) or 0)
            order.print_height_cm = float(request.form.get('print_height_cm', 0) or 0)
            order.print_method = request.form.get('print_method', '')
            order.ink_coverage_percent = int(request.form.get('ink_coverage_percent', 50) or 50)
        
        # Design-Workflow-Felder (NEU)
        design_status = request.form.get('design_status', 'none')
        order.design_status = design_status
        
        if design_status == 'needs_order':
            order.design_supplier_id = request.form.get('design_supplier_id')
            order.design_order_notes = request.form.get('design_order_notes')
            
            expected_date_str = request.form.get('design_expected_date')
            if expected_date_str:
                try:
                    order.design_expected_date = datetime.strptime(expected_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
        
        elif design_status == 'customer_provided':
            # Wenn Kunde Design bereitstellt, aber keine Datei hochgeladen wurde
            if not ('design_file' in request.files and request.files['design_file'].filename):
                order.design_status = 'none'  # Zurücksetzen auf "none" wenn keine Datei
        
        # Design-Datei hochladen (wenn vorhanden)
        if 'design_file' in request.files:
            file = request.files['design_file']
            if file and file.filename:
                # Sichere Dateiname generieren
                filename = f"{order.id}_{file.filename}"
                upload_path = os.path.join('uploads', 'designs', filename)
                os.makedirs(os.path.dirname(upload_path), exist_ok=True)
                file.save(upload_path)
                order.design_file_path = upload_path
                
                # Status auf "customer_provided" setzen wenn Datei hochgeladen
                if order.design_status == 'none':
                    order.design_status = 'customer_provided'
        
        # In Datenbank speichern
        db.session.add(order)
        db.session.commit()
        
        # Artikel hinzufügen
        article_ids = request.form.getlist('article_id[]')
        quantities = request.form.getlist('quantity[]')
        sizes = request.form.getlist('size[]')
        colors = request.form.getlist('color[]')
        
        for i, article_id in enumerate(article_ids):
            if article_id:
                item = OrderItem(
                    order_id=order.id,
                    article_id=article_id,
                    quantity=int(quantities[i]) if i < len(quantities) else 1,
                    textile_size=sizes[i] if i < len(sizes) else '',
                    textile_color=colors[i] if i < len(colors) else ''
                )
                
                # Preis aus Artikel übernehmen
                article = Article.query.get(article_id)
                if article:
                    item.unit_price = article.price
                
                db.session.add(item)
        
        db.session.commit()
        
        # Aktivität protokollieren
        log_activity('order_created', 
                    f'Auftrag erstellt: {order.id} für {order.customer.display_name if order.customer else "Unbekannt"}')
        
        flash(f'Auftrag {order.id} wurde erstellt!', 'success')
        return redirect(url_for('orders.show', order_id=order.id))
    
    # Kunden und Artikel für Formular laden
    customers_list = Customer.query.order_by(Customer.company_name, Customer.last_name).all()
    articles_list = Article.query.filter_by(active=True).order_by(Article.name).all()
    suppliers_list = Supplier.query.filter_by(active=True).order_by(Supplier.name).all()
    
    # In Dictionary umwandeln für Template-Kompatibilität
    customers = {}
    for customer in customers_list:
        customers[customer.id] = customer
    
    articles = {}
    for article in articles_list:
        articles[article.id] = article
        
    suppliers = {}
    for supplier in suppliers_list:
        suppliers[supplier.id] = supplier
    
    # Vorauswahl wenn customer_id übergeben wurde
    selected_customer_id = request.args.get('customer_id')
    
    return render_template('orders/new.html',
                         customers=customers,
                         articles=articles,
                         suppliers=suppliers,
                         selected_customer_id=selected_customer_id)

@order_bp.route('/<order_id>')
@login_required
def show(order_id):
    """Auftrags-Details anzeigen"""
    order = Order.query.get_or_404(order_id)
    
    # Lieferanten für Design-Workflow laden
    suppliers = Supplier.query.filter_by(active=True).order_by(Supplier.name).all()
    
    # Status-Historie laden
    status_history = order.status_history.order_by(text('changed_at desc')).all()
    
    # Berechne Bestell-Statistiken
    items_to_order = 0
    items_ordered = 0
    items_delivered = 0
    
    for item in order.items:
        if item.supplier_order_status == 'none':
            # Prüfe ob Lagerbestand ausreicht
            if item.article and (item.article.stock or 0) < item.quantity:
                items_to_order += 1
        elif item.supplier_order_status == 'ordered':
            items_ordered += 1
        elif item.supplier_order_status == 'delivered':
            items_delivered += 1
    
    return render_template('orders/show.html',
                         order=order,
                         suppliers=suppliers,
                         status_history=status_history,
                         items_to_order=items_to_order,
                         items_ordered=items_ordered,
                         items_delivered=items_delivered)

@order_bp.route('/<order_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(order_id):
    """Auftrag bearbeiten"""
    order = Order.query.get_or_404(order_id)
    
    if request.method == 'POST':
        # Auftrag aktualisieren
        order.customer_id = request.form.get('customer_id')
        order.order_type = request.form.get('order_type', 'embroidery')
        order.description = request.form.get('description', '')
        order.internal_notes = request.form.get('notes', '')
        order.customer_notes = request.form.get('customer_notes', '')
        order.total_price = float(request.form.get('price', 0) or 0)
        order.due_date = request.form.get('pickup_date') or None
        order.rush_order = request.form.get('rush_order', False) == 'on'
        order.updated_at = datetime.utcnow()
        order.updated_by = current_user.username
        
        # Order-Type spezifische Felder
        if order.order_type in ['embroidery', 'combined']:
            order.stitch_count = int(request.form.get('stitch_count', 0) or 0)
            order.design_width_mm = float(request.form.get('design_width_mm', 0) or 0)
            order.design_height_mm = float(request.form.get('design_height_mm', 0) or 0)
            order.embroidery_position = request.form.get('embroidery_position', '')
            order.embroidery_size = request.form.get('embroidery_size', '')
            order.thread_colors = request.form.get('thread_colors', '')
        
        if order.order_type in ['printing', 'dtf', 'combined']:
            order.print_width_cm = float(request.form.get('print_width_cm', 0) or 0)
            order.print_height_cm = float(request.form.get('print_height_cm', 0) or 0)
            order.print_method = request.form.get('print_method', '')
            order.ink_coverage_percent = int(request.form.get('ink_coverage_percent', 50) or 50)
        
        # Änderungen speichern
        db.session.commit()
        
        # Aktivität protokollieren
        log_activity('order_updated', 
                    f'Auftrag aktualisiert: {order.id}')
        
        flash(f'Auftrag {order.id} wurde aktualisiert!', 'success')
        return redirect(url_for('orders.show', order_id=order.id))
    
    # Kunden und Artikel für Formular laden
    customers_list = Customer.query.order_by(Customer.company_name, Customer.last_name).all()
    articles_list = Article.query.filter_by(active=True).order_by(Article.name).all()
    
    # In Dictionary umwandeln für Template-Kompatibilität
    customers = {}
    for customer in customers_list:
        customers[customer.id] = customer
    
    articles = {}
    for article in articles_list:
        articles[article.id] = article
    
    return render_template('orders/edit.html',
                         order=order,
                         customers=customers,
                         articles=articles)

@order_bp.route('/<order_id>/status', methods=['POST'])
@login_required
def update_status(order_id):
    """Auftragsstatus aktualisieren"""
    order = Order.query.get_or_404(order_id)
    
    old_status = order.status
    new_status = request.form.get('status')
    comment = request.form.get('comment', '')
    
    # Design-Validierung für Produktionsstart
    if new_status == 'in_progress':
        # Prüfe ob Design-Workflow abgeschlossen ist
        if hasattr(order, 'can_start_production'):
            can_start, message = order.can_start_production()
            if not can_start:
                flash(f'Produktion kann nicht gestartet werden: {message}', 'danger')
                return redirect(url_for('orders.show', order_id=order_id))
        else:
            # Fallback für ältere Aufträge ohne Design-Workflow
            if not order.design_file and not order.design_file_path:
                flash('Produktion kann nicht gestartet werden: Design fehlt!', 'danger')
                return redirect(url_for('orders.show', order_id=order_id))
    
    if new_status and new_status != old_status:
        # Status aktualisieren
        order.status = new_status
        order.updated_at = datetime.utcnow()
        order.updated_by = current_user.username
        
        # Spezielle Felder für bestimmte Status
        if new_status == 'in_progress':
            order.production_start = datetime.utcnow()
        elif new_status == 'ready':
            order.production_end = datetime.utcnow()
        elif new_status == 'completed':
            order.completed_at = datetime.utcnow()
            order.completed_by = current_user.username
        
        # Status-Historie hinzufügen
        from src.models import OrderStatusHistory
        history = OrderStatusHistory(
            order_id=order_id,
            from_status=old_status,
            to_status=new_status,
            comment=comment,
            changed_by=current_user.username
        )
        db.session.add(history)
        
        db.session.commit()
        
        # Aktivität protokollieren
        log_activity('order_status_changed', 
                    f'Auftrag {order.id}: Status von {old_status} auf {new_status} geändert')
        
        flash(f'Status wurde auf {new_status} geändert!', 'success')
    
    return redirect(url_for('orders.show', order_id=order_id))

@order_bp.route('/<order_id>/delete', methods=['POST'])
@login_required
def delete(order_id):
    """Auftrag löschen"""
    order = Order.query.get_or_404(order_id)
    
    # Nur Aufträge im Status 'cancelled' können gelöscht werden
    if order.status != 'cancelled':
        flash('Nur stornierte Aufträge können gelöscht werden!', 'danger')
        return redirect(url_for('orders.show', order_id=order_id))
    
    # Aktivität protokollieren bevor gelöscht wird
    log_activity('order_deleted', 
                f'Auftrag gelöscht: {order.id}')
    
    # Auftrag und zugehörige Items löschen (cascade)
    db.session.delete(order)
    db.session.commit()
    
    flash(f'Auftrag {order_id} wurde gelöscht!', 'success')
    return redirect(url_for('orders.index'))

# API-Endpoints für AJAX
@order_bp.route('/api/customer/<customer_id>')
@login_required
def api_customer_details(customer_id):
    """Kunden-Details für AJAX abrufen"""
    customer = Customer.query.get_or_404(customer_id)
    return jsonify({
        'id': customer.id,
        'name': customer.display_name,
        'email': customer.email,
        'phone': customer.phone or customer.mobile,
        'address': f"{customer.street} {customer.house_number}, {customer.postal_code} {customer.city}".strip()
    })

@order_bp.route('/api/article/<article_id>')
@login_required
def api_article_details(article_id):
    """Artikel-Details für AJAX abrufen"""
    article = Article.query.get_or_404(article_id)
    return jsonify({
        'id': article.id,
        'name': article.name,
        'price': article.price,
        'stock': article.stock,
        'color': article.color,
        'size': article.size
    })

# Hilfsfunktionen für Templates
def get_customer_display_name(customer):
    """Kunden-Anzeigename generieren"""
    if customer:
        return customer.display_name
    return "Unbekannt"

@order_bp.route('/analyze_file', methods=['POST'])
@login_required
def analyze_file():
    """Design-Datei analysieren (DST, PES, etc.)"""
    if 'design_file' not in request.files:
        return jsonify({'success': False, 'error': 'Keine Datei hochgeladen'})
    
    file = request.files['design_file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Keine Datei ausgewählt'})
    
    # Dateierweiterung prüfen
    filename = file.filename.lower()
    file_ext = os.path.splitext(filename)[1]
    
    # Temporäre Datei speichern
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
        file.save(tmp_file.name)
        tmp_path = tmp_file.name
    
    try:
        if file_ext == '.dst':
            # DST-Datei analysieren mit robustem Analyzer
            try:
                result = analyze_dst_file_robust(tmp_path)
                if result.get('success'):
                    return jsonify({
                        'success': True,
                        'stitch_count': result.get('stitch_count', result.get('total_stitches', 0)),
                        'width_mm': result.get('width_mm', 0),
                        'height_mm': result.get('height_mm', 0),
                        'color_count': result.get('color_count', result.get('estimated_colors', 1)),
                        'analysis_details': {
                            'total_stitches': result.get('total_stitches', 0),
                            'normal_stitches': result.get('normal_stitches', 0),
                            'jump_stitches': result.get('jump_stitches', 0),
                            'color_changes': result.get('color_changes', 0),
                            'density_per_cm2': result.get('density_per_cm2', 0),
                            'estimated_time_minutes': result.get('estimated_time_minutes', 0)
                        }
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': result.get('error', 'Unbekannter Fehler beim Analysieren der DST-Datei')
                    })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Fehler beim Analysieren der DST-Datei: {str(e)}'
                })
        
        elif file_ext in ['.png', '.jpg', '.jpeg']:
            # Bilddatei analysieren
            from PIL import Image
            img = Image.open(tmp_path)
            
            # DPI ermitteln (Standard: 72)
            dpi = img.info.get('dpi', (72, 72))
            if isinstance(dpi, int):
                dpi = (dpi, dpi)
            
            # Größe in cm berechnen
            width_cm = (img.width / dpi[0]) * 2.54
            height_cm = (img.height / dpi[1]) * 2.54
            
            return jsonify({
                'success': True,
                'width_px': img.width,
                'height_px': img.height,
                'width_cm': round(width_cm, 1),
                'height_cm': round(height_cm, 1),
                'dpi': dpi
            })
        
        else:
            return jsonify({
                'success': False,
                'error': f'Dateityp {file_ext} wird noch nicht unterstützt'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Fehler beim Analysieren der Datei: {str(e)}',
            'filename': filename,
            'file_ext': file_ext
        })
    
    finally:
        # Temporäre Datei löschen
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

def analyze_dst_file(filepath):
    """DST-Stickdatei analysieren"""
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
        
        # DST Header lesen (512 Bytes)
        if len(data) < 512:
            raise ValueError("Datei zu klein für DST-Format")
        
        # Koordinaten für Bounding Box
        min_x = max_x = min_y = max_y = 0
        x = y = 0
        stitch_count = 0
        color_changes = 0
        
        # DST-Befehle beginnen nach dem 512-Byte Header
        i = 512
        
        while i < len(data) - 2:
            b1 = data[i]
            b2 = data[i + 1]
            b3 = data[i + 2]
            
            # Prüfe auf Spezial-Befehle
            if b3 & 0xF0 == 0xF0:
                # Farbwechsel
                if b3 == 0xFE and b2 == 0xB0:
                    color_changes += 1
                    i += 3
                    continue
                # Ende der Datei
                elif b3 == 0xF3:
                    break
                # Andere Befehle überspringen
                else:
                    i += 3
                    continue
            
            # Normale Stiche
            # X-Koordinate (b1 und untere 2 Bits von b3)
            dx = b1
            if b3 & 0x01:
                dx = -dx
            
            # Y-Koordinate (b2 und Bits 2-3 von b3)
            dy = b2
            if b3 & 0x02:
                dy = -dy
            
            # 0.1mm Einheiten
            x += dx
            y += dy
            
            # Bounding Box aktualisieren
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)
            
            stitch_count += 1
            i += 3
        
        # Berechne Größe in mm (DST verwendet 0.1mm Einheiten)
        width_mm = (max_x - min_x) / 10.0
        height_mm = (max_y - min_y) / 10.0
        
        return {
            'stitch_count': stitch_count,
            'width_mm': abs(width_mm),
            'height_mm': abs(height_mm),
            'color_count': color_changes + 1  # +1 für die Startfarbe
        }
    
    except Exception as e:
        raise ValueError(f"Fehler beim Lesen der DST-Datei: {str(e)}")

@order_bp.route('/calculate_price', methods=['POST'])
@login_required
def calculate_price():
    """Preis für Auftrag kalkulieren"""
    data = request.get_json()
    
    order_type = data.get('order_type', 'embroidery')
    quantity = int(data.get('quantity', 1))
    textile_items = data.get('textile_items', [])
    
    # Basis-Textilkosten
    textile_cost = 0
    for item in textile_items:
        textile_cost += item['price'] * item['quantity']
    
    # Produktionskosten
    production_cost = 0
    
    if order_type in ['embroidery', 'combined']:
        stitch_count = int(data.get('stitch_count', 0))
        if stitch_count > 0:
            # Preis pro 1000 Stiche (aus Settings oder Default)
            price_per_1000 = 1.50  # TODO: Aus Settings laden
            production_cost += (stitch_count / 1000) * price_per_1000 * quantity
    
    if order_type in ['printing', 'dtf', 'combined']:
        width_cm = float(data.get('print_width_cm', 0))
        height_cm = float(data.get('print_height_cm', 0))
        if width_cm > 0 and height_cm > 0:
            # Preis pro cm² (aus Settings oder Default)
            price_per_cm2 = 0.05  # TODO: Aus Settings laden
            area_cm2 = width_cm * height_cm
            production_cost += area_cm2 * price_per_cm2 * quantity
    
    # Einrichtungskosten
    setup_fee = 15.00  # TODO: Aus Settings laden
    
    # Mengenrabatt
    discount_percent = 0
    if quantity >= 50:
        discount_percent = 5
    elif quantity >= 100:
        discount_percent = 10
    elif quantity >= 250:
        discount_percent = 15
    
    # Gesamtpreis berechnen
    subtotal = textile_cost + production_cost
    discount_amount = subtotal * (discount_percent / 100)
    total = subtotal - discount_amount + setup_fee
    
    return jsonify({
        'textile_cost': round(textile_cost, 2),
        'production_cost': round(production_cost, 2),
        'subtotal': round(subtotal, 2),
        'setup_fee': round(setup_fee, 2),
        'discount_percent': discount_percent,
        'discount_amount': round(discount_amount, 2),
        'total': round(total, 2)
    })


@order_bp.route('/items/<int:item_id>/mark-for-order', methods=['POST'])
@login_required
def mark_item_for_order(item_id):
    """Markiere eine Auftragsposition zur Bestellung"""
    item = OrderItem.query.get_or_404(item_id)
    
    # Prüfe Berechtigung
    if not current_user.is_admin:
        order = Order.query.get(item.order_id)
        if order.created_by != current_user.username:
            return jsonify({'error': 'Keine Berechtigung'}), 403
    
    # Markiere zur Bestellung
    item.supplier_order_status = 'to_order'
    item.supplier_order_notes = f"Markiert zur Bestellung am {datetime.now().strftime('%d.%m.%Y %H:%M')} von {current_user.username}"
    
    db.session.commit()
    
    log_activity('order_item_marked_for_order', 
                f'Position {item_id} zur Bestellung markiert')
    
    return jsonify({'success': True})


@order_bp.route('/create-quick', methods=['POST'])
@login_required
def create_quick_order():
    """Erstelle schnell eine neue Bestellung ohne Kunde"""
    try:
        # Generiere neue Auftrags-ID
        order_id = generate_order_id()
        
        # Erstelle neue Bestellung
        order = Order(
            id=order_id,
            order_number=order_id,
            status='new',
            created_by=current_user.username,
            order_type='combined'
        )
        
        db.session.add(order)
        db.session.commit()
        
        log_activity('order_created_quick', 
                    f'Schnellbestellung {order_id} erstellt')
        
        return jsonify({
            'success': True,
            'order_id': order_id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@order_bp.route('/current')
@login_required  
def current_order():
    """Aktuelle offene Bestellung für den aktuellen Benutzer"""
    # Suche nach einer offenen Bestellung (Status: new)
    current_order = Order.query.filter_by(
        status='new',
        created_by=current_user.username
    ).order_by(Order.created_at.desc()).first()
    
    if current_order:
        return jsonify({
            'exists': True,
            'order_id': current_order.id,
            'customer': current_order.customer.display_name if current_order.customer else 'Unbekannt',
            'item_count': current_order.items.count()
        })
    else:
        return jsonify({
            'exists': False
        })


@order_bp.route('/<order_id>/add-item', methods=['POST'])
@login_required
def add_item_to_order(order_id):
    """Füge Artikel zu einer Bestellung hinzu"""
    try:
        data = request.get_json()
        article_id = data.get('article_id')
        quantity = data.get('quantity', 1)
        
        # Hole Bestellung und Artikel
        order = Order.query.get_or_404(order_id)
        article = Article.query.get_or_404(article_id)
        
        # Prüfe Berechtigung
        if order.created_by != current_user.username and not current_user.is_admin:
            return jsonify({'error': 'Keine Berechtigung'}), 403
        
        # Erstelle neue Auftragsposition
        order_item = OrderItem(
            order_id=order_id,
            article_id=article_id,
            quantity=quantity,
            unit_price=article.price or 0
        )
        
        db.session.add(order_item)
        db.session.commit()
        
        log_activity('order_item_added', 
                    f'Artikel {article.name} zu Auftrag {order_id} hinzugefügt')
        
        return jsonify({
            'success': True,
            'item_id': order_item.id,
            'message': f'{article.name} wurde zur Bestellung hinzugefügt'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@order_bp.route('/items/<int:item_id>/mark-delivered', methods=['POST'])
@login_required
def mark_item_delivered(item_id):
    """Markiere eine Auftragsposition als geliefert"""
    item = OrderItem.query.get_or_404(item_id)
    
    # Prüfe Berechtigung
    if not current_user.is_admin:
        return jsonify({'error': 'Nur Admins können Lieferungen bestätigen'}), 403
    
    # Markiere als geliefert
    item.supplier_order_status = 'delivered'
    item.supplier_delivered_date = datetime.now().date()
    
    # Aktualisiere Bestand wenn Artikel vorhanden
    if item.article:
        if not item.article.stock:
            item.article.stock = 0
        item.article.stock += item.quantity
        
        # Notiz hinzufügen
        existing_notes = item.supplier_order_notes or ''
        new_note = f"\nGeliefert am {datetime.now().strftime('%d.%m.%Y %H:%M')} von {current_user.username}. Bestand erhöht um {item.quantity}."
        item.supplier_order_notes = (existing_notes + new_note).strip()
    
    db.session.commit()
    
    log_activity(current_user.username, 'order_item_delivered', 
                f'Position {item_id} als geliefert markiert')
    
    # Prüfe ob alle Positionen des Auftrags geliefert sind
    order = Order.query.get(item.order_id)
    all_delivered = all(i.supplier_order_status == 'delivered' or 
                       (i.article and i.article.stock >= i.quantity) 
                       for i in order.items)
    
    return jsonify({
        'success': True,
        'all_delivered': all_delivered,
        'new_stock': item.article.stock if item.article else None
    })


@order_bp.route('/create-quick', methods=['POST'])
@login_required
def create_quick():
    """Schnell-Erstellung einer neuen Bestellung (für interne Zwecke)"""
    data = request.get_json()
    
    try:
        # Generiere neue Order ID
        order_id = generate_order_id()
        
        # Erstelle minimale Bestellung
        order = Order(
            id=order_id,
            order_number=order_id,
            customer_id=data.get('customer_id'),  # Optional
            order_type=data.get('order_type', 'internal'),
            status='new',
            description=data.get('description', 'Schnellbestellung'),
            internal_notes=data.get('notes', 'Erstellt über Artikel-Übersicht'),
            customer_notes='',
            total_price=0,
            created_by=current_user.username
        )
        
        # Falls kein Kunde angegeben, suche oder erstelle internen Kunden
        if not order.customer_id:
            from src.models import Customer
            internal_customer = Customer.query.filter_by(
                company_name='Interner Bedarf'
            ).first()
            
            if not internal_customer:
                # Erstelle internen Kunden
                internal_customer = Customer(
                    id='INTERNAL',
                    customer_type='business',
                    company_name='Interner Bedarf',
                    email='intern@stitchadmin.local',
                    created_by=current_user.username
                )
                db.session.add(internal_customer)
                db.session.flush()
            
            order.customer_id = internal_customer.id
        
        db.session.add(order)
        db.session.commit()
        
        log_activity('quick_order_created', 
                    f'Schnellbestellung {order_id} erstellt')
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'order_number': order.order_number
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@order_bp.route('/<string:order_id>/print/order_sheet')
@login_required
def print_order_sheet(order_id):
    """Vollständiges A4 Auftragsblatt drucken"""
    order = Order.query.get_or_404(order_id)
    
    # Füge aktuelles Datum für das Template hinzu
    from datetime import datetime
    now = datetime.now()
    
    # Aktivität protokollieren
    log_activity('order_sheet_printed', 
                f'Auftragsblatt gedruckt für Bestellung: {order.id}')
    
    return render_template('orders/order_sheet.html', 
                         order=order,
                         now=now)

@order_bp.route('/<string:order_id>/print/production_labels')
@login_required
def print_production_labels(order_id):
    """Produktions-Etiketten für Zebra-Drucker"""
    order = Order.query.get_or_404(order_id)
    
    # Füge aktuelles Datum für das Template hinzu
    from datetime import datetime
    now = datetime.now()
    
    # Aktivität protokollieren
    log_activity('production_labels_printed', 
                f'Produktions-Etiketten gedruckt für Bestellung: {order.id}')
    
    return render_template('orders/production_labels.html', 
                         order=order,
                         now=now)

@order_bp.route('/create_logo_order', methods=['GET', 'POST'])
@login_required
def create_logo_order():
    """Logo/Design-Bestellung erstellen"""
    if request.method == 'POST':
        try:
            # TODO: Implementiere Logo-Order-Erstellung
            # Erstelle Eintrag in logo_orders Tabelle
            flash('Logo-Bestellung wurde erstellt', 'success')
            
            # Wenn order_id vorhanden, zurück zur Bestellung
            order_id = request.form.get('order_id')
            if order_id:
                return redirect(url_for('orders.show', order_id=order_id))
            return redirect(url_for('orders.index'))
            
        except Exception as e:
            flash(f'Fehler beim Erstellen der Logo-Bestellung: {str(e)}', 'error')
            return redirect(request.url)
    
    # GET Request - Zeige Formular
    order_id = request.args.get('order_id')
    order = None
    description = ''
    
    if order_id:
        order = Order.query.get(order_id)
        if order:
            description = f"Logo/Design für Auftrag {order.order_number or order.id}"
            if order.design_description:
                description += f"\n{order.design_description}"
    
    # Hole aktive Lieferanten
    suppliers = Supplier.query.filter_by(active=True).order_by(Supplier.name).all()
    
    return render_template('orders/create_logo_order.html',
                         order=order,
                         description=description,
                         suppliers=suppliers)

@order_bp.route('/<string:order_id>/upload_design', methods=['POST'])
@login_required
def upload_design(order_id):
    """Design-Datei für Auftrag hochladen"""
    order = Order.query.get_or_404(order_id)
    
    if 'design_file' not in request.files:
        flash('Keine Datei ausgewählt', 'error')
        return redirect(url_for('orders.show', order_id=order_id))
    
    file = request.files['design_file']
    if file.filename == '':
        flash('Keine Datei ausgewählt', 'error')
        return redirect(url_for('orders.show', order_id=order_id))
    
    if file:
        # Sichere Dateiname generieren
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{order.order_number or order.id}_{timestamp}_{filename}"
        
        # Upload-Verzeichnis erstellen falls nicht vorhanden
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'designs')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Datei speichern
        filepath = os.path.join(upload_dir, unique_filename)
        file.save(filepath)
        
        # Order aktualisieren
        order.design_file = f"uploads/designs/{unique_filename}"
        order.design_file_path = filepath
        order.updated_at = datetime.utcnow()
        order.updated_by = current_user.username
        
        # Optional: Beschreibung hinzufügen
        file_description = request.form.get('file_description')
        if file_description:
            if order.design_description:
                order.design_description += f"\n\nDatei-Info: {file_description}"
            else:
                order.design_description = f"Datei-Info: {file_description}"
        
        db.session.commit()
        
        # Aktivität protokollieren
        log_activity('design_uploaded', 
                    f'Design-Datei hochgeladen für Auftrag {order.order_number or order.id}: {filename}')
        
        flash('Design-Datei erfolgreich hochgeladen', 'success')
        
        # Optional: Datei analysieren
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext in ['.dst', '.pes', '.jef', '.exp']:
            # Stickdatei analysieren
            try:
                analysis = analyze_dst_file_robust(filepath)
                if analysis['success']:
                    order.stitch_count = analysis.get('stitch_count', 0)
                    order.file_analysis = json.dumps(analysis)
                    db.session.commit()
            except:
                pass
    
    return redirect(url_for('orders.show', order_id=order_id))
