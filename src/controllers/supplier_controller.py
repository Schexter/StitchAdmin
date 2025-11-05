"""
Supplier Controller - Datenbankbasierte Lieferanten-Verwaltung
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from src.models.models import db, Supplier, Article, SupplierOrder, OrderItem
from src.utils.activity_logger import log_activity
from sqlalchemy import or_
import json
from cryptography.fernet import Fernet
import os

# Blueprint erstellen
supplier_bp = Blueprint('suppliers', __name__, url_prefix='/suppliers')

# Verschlüsselung für Passwörter
def get_encryption_key():
    """Hole oder erstelle Verschlüsselungsschlüssel"""
    key_file = 'encryption.key'
    if os.path.exists(key_file):
        with open(key_file, 'rb') as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(key_file, 'wb') as f:
            f.write(key)
        return key

def encrypt_password(password):
    """Verschlüssele Passwort"""
    if not password:
        return None
    f = Fernet(get_encryption_key())
    return f.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password):
    """Entschlüssele Passwort"""
    if not encrypted_password:
        return None
    f = Fernet(get_encryption_key())
    return f.decrypt(encrypted_password.encode()).decode()

def generate_supplier_id():
    """Generiere neue Lieferanten-ID"""
    # Finde die höchste existierende ID
    last_supplier = Supplier.query.filter(Supplier.id.like('LF%')).order_by(Supplier.id.desc()).first()
    
    if not last_supplier:
        return "LF001"
    
    # Extrahiere Nummer und erhöhe um 1
    try:
        last_num = int(last_supplier.id[2:])
        return f"LF{last_num + 1:03d}"
    except ValueError:
        # Fallback wenn ID nicht dem erwarteten Format entspricht
        return f"LF{Supplier.query.count() + 1:03d}"

@supplier_bp.route('/')
@login_required
def index():
    """Alle Lieferanten anzeigen"""
    search_query = request.args.get('search', '')
    
    # Basis-Query
    query = Supplier.query
    
    # Suchfilter
    if search_query:
        query = query.filter(
            or_(
                Supplier.name.ilike(f'%{search_query}%'),
                Supplier.contact_person.ilike(f'%{search_query}%'),
                Supplier.email.ilike(f'%{search_query}%'),
                Supplier.id.ilike(f'%{search_query}%')
            )
        )
    
    # Sortierung
    suppliers = query.order_by(Supplier.name).all()
    
    return render_template('suppliers/index.html', 
                         suppliers=suppliers,
                         search_query=search_query)

@supplier_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Neuen Lieferanten erstellen"""
    if request.method == 'POST':
        try:
            supplier = Supplier(
                id=generate_supplier_id(),
                name=request.form.get('name'),
                contact_person=request.form.get('contact_person', ''),
                email=request.form.get('email', ''),
                phone=request.form.get('phone', ''),
                website=request.form.get('website', ''),
                street=request.form.get('street', ''),
                postal_code=request.form.get('postal_code', ''),
                city=request.form.get('city', ''),
                country=request.form.get('country', 'Deutschland'),
                tax_id=request.form.get('tax_id', ''),
                customer_number=request.form.get('customer_number', ''),
                payment_terms=request.form.get('payment_terms', '30 Tage netto'),
                delivery_time_days=int(request.form.get('delivery_time_days', 0)) if request.form.get('delivery_time_days') else None,
                minimum_order_value=float(request.form.get('minimum_order_value', 0)) if request.form.get('minimum_order_value') else None,
                return_street=request.form.get('return_street', ''),
                return_postal_code=request.form.get('return_postal_code', ''),
                return_city=request.form.get('return_city', ''),
                return_country=request.form.get('return_country', ''),
                return_contact=request.form.get('return_contact', ''),
                return_phone=request.form.get('return_phone', ''),
                return_notes=request.form.get('return_notes', ''),
                active=request.form.get('active', 'off') == 'on',
                preferred=request.form.get('preferred', 'off') == 'on',
                created_by=current_user.username
            )
            
            db.session.add(supplier)
            db.session.commit()
            
            log_activity(current_user.username, 'supplier_created', 
                        f'Lieferant erstellt: {supplier.id} - {supplier.name}')
            
            flash(f'Lieferant {supplier.name} wurde erstellt!', 'success')
            return redirect(url_for('suppliers.show', supplier_id=supplier.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Erstellen des Lieferanten: {str(e)}', 'danger')
            return redirect(url_for('suppliers.new'))
    
    return render_template('suppliers/new.html')

@supplier_bp.route('/<supplier_id>')
@login_required
def show(supplier_id):
    """Lieferanten-Details anzeigen"""
    supplier = Supplier.query.get_or_404(supplier_id)
    
    # Lade zugehörige Artikel
    supplier_articles = Article.query.filter_by(supplier=supplier.name).all()
    
    # Lade letzte Bestellungen
    recent_orders = SupplierOrder.query.filter_by(supplier_id=supplier_id)\
                                       .order_by(SupplierOrder.created_at.desc())\
                                       .limit(5).all()
    
    # Berechne Gesamtvolumen der Bestellungen
    total_amount = 0
    if recent_orders:
        total_amount = sum(order.total_amount or 0 for order in recent_orders)
    
    return render_template('suppliers/show.html', 
                         supplier=supplier, 
                         supplier_articles=supplier_articles,
                         recent_orders=recent_orders,
                         total_amount=total_amount)

@supplier_bp.route('/<supplier_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(supplier_id):
    """Lieferant bearbeiten"""
    supplier = Supplier.query.get_or_404(supplier_id)
    
    if request.method == 'POST':
        try:
            # Lieferant aktualisieren
            supplier.name = request.form.get('name')
            supplier.contact_person = request.form.get('contact_person', '')
            supplier.email = request.form.get('email', '')
            supplier.phone = request.form.get('phone', '')
            supplier.website = request.form.get('website', '')
            supplier.street = request.form.get('street', '')
            supplier.postal_code = request.form.get('postal_code', '')
            supplier.city = request.form.get('city', '')
            supplier.country = request.form.get('country', 'Deutschland')
            supplier.tax_id = request.form.get('tax_id', '')
            supplier.customer_number = request.form.get('customer_number', '')
            supplier.payment_terms = request.form.get('payment_terms', '30 Tage netto')
            supplier.delivery_time_days = int(request.form.get('delivery_time_days', 0)) if request.form.get('delivery_time_days') else None
            supplier.minimum_order_value = float(request.form.get('minimum_order_value', 0)) if request.form.get('minimum_order_value') else None
            supplier.return_street = request.form.get('return_street', '')
            supplier.return_postal_code = request.form.get('return_postal_code', '')
            supplier.return_city = request.form.get('return_city', '')
            supplier.return_country = request.form.get('return_country', '')
            supplier.return_contact = request.form.get('return_contact', '')
            supplier.return_phone = request.form.get('return_phone', '')
            supplier.return_notes = request.form.get('return_notes', '')
            supplier.active = request.form.get('active', 'off') == 'on'
            supplier.preferred = request.form.get('preferred', 'off') == 'on'
            
            # Webshop-Felder
            supplier.webshop_url = request.form.get('webshop_url', '')
            supplier.webshop_article_url_pattern = request.form.get('webshop_article_url_pattern', '')
            supplier.webshop_type = request.form.get('webshop_type', '')
            supplier.webshop_username = request.form.get('webshop_username', '')
            supplier.webshop_notes = request.form.get('webshop_notes', '')
            supplier.auto_order_enabled = request.form.get('auto_order_enabled', 'off') == 'on'
            
            # Passwort nur verschlüsseln wenn neu eingegeben
            new_password = request.form.get('webshop_password', '')
            if new_password:
                supplier.webshop_password_encrypted = encrypt_password(new_password)
            
            supplier.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            log_activity(current_user.username, 'supplier_updated', 
                        f'Lieferant aktualisiert: {supplier.id} - {supplier.name}')
            
            flash(f'Lieferant {supplier.name} wurde aktualisiert!', 'success')
            return redirect(url_for('suppliers.show', supplier_id=supplier.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Aktualisieren: {str(e)}', 'danger')
            return redirect(url_for('suppliers.edit', supplier_id=supplier_id))
    
    return render_template('suppliers/edit.html', supplier=supplier)

@supplier_bp.route('/<supplier_id>/delete', methods=['POST'])
@login_required
def delete(supplier_id):
    """Lieferant löschen"""
    supplier = Supplier.query.get_or_404(supplier_id)
    
    # Prüfe ob Artikel mit diesem Lieferanten existieren
    has_articles = Article.query.filter_by(supplier=supplier.name).count() > 0
    
    if has_articles:
        flash('Lieferant kann nicht gelöscht werden, da noch Artikel zugeordnet sind!', 'danger')
        return redirect(url_for('suppliers.show', supplier_id=supplier_id))
    
    # Prüfe ob Bestellungen existieren
    has_orders = SupplierOrder.query.filter_by(supplier_id=supplier_id).count() > 0
    
    if has_orders:
        flash('Lieferant kann nicht gelöscht werden, da Bestellungen existieren!', 'danger')
        return redirect(url_for('suppliers.show', supplier_id=supplier_id))
    
    try:
        db.session.delete(supplier)
        db.session.commit()
        
        log_activity(current_user.username, 'supplier_deleted', 
                    f'Lieferant gelöscht: {supplier_id} - {supplier.name}')
        flash(f'Lieferant {supplier.name} wurde gelöscht!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Löschen: {str(e)}', 'danger')
        return redirect(url_for('suppliers.show', supplier_id=supplier_id))
    
    return redirect(url_for('suppliers.index'))

@supplier_bp.route('/<supplier_id>/orders/new', methods=['GET', 'POST'])
@login_required
def new_order(supplier_id):
    """Neue Bestellung bei Lieferant erstellen"""
    supplier = Supplier.query.get_or_404(supplier_id)
    
    if request.method == 'POST':
        try:
            # Bestellnummer generieren wenn nicht angegeben
            order_number = request.form.get('order_number', '').strip()
            if not order_number:
                # Generiere automatische Bestellnummer
                last_order = SupplierOrder.query.order_by(SupplierOrder.id.desc()).first()
                if last_order and last_order.order_number and last_order.order_number.startswith('PO'):
                    try:
                        last_num = int(last_order.order_number[2:])
                        order_number = f"PO{last_num + 1:06d}"
                    except:
                        order_number = f"PO{datetime.now().strftime('%Y%m%d%H%M%S')}"
                else:
                    order_number = f"PO{datetime.now().strftime('%Y%m%d')}001"
            
            # Neue Bestellung erstellen
            order = SupplierOrder(
                id=f"SO{datetime.now().strftime('%Y%m%d%H%M%S')}",
                supplier_id=supplier_id,
                order_number=order_number,
                supplier_order_number=request.form.get('supplier_order_number', ''),
                order_date=datetime.strptime(request.form.get('order_date'), '%Y-%m-%d').date() if request.form.get('order_date') else datetime.utcnow().date(),
                delivery_date=datetime.strptime(request.form.get('delivery_date'), '%Y-%m-%d').date() if request.form.get('delivery_date') else None,
                shipping_method=request.form.get('shipping_method', ''),
                payment_method=request.form.get('payment_method', 'invoice'),
                notes=request.form.get('notes', ''),
                internal_notes=request.form.get('internal_notes', ''),
                shipping_cost=float(request.form.get('shipping_cost', 0)),
                tax_amount=float(request.form.get('tax_amount', 0)),
                discount_amount=float(request.form.get('discount_amount', 0)),
                subtotal=float(request.form.get('subtotal', 0)),
                total_amount=float(request.form.get('total_amount', 0)),
                status='draft' if request.form.get('action') == 'draft' else 'ordered',
                created_by=current_user.username
            )
            
            # Lieferadresse wenn abweichend
            if request.form.get('delivery_name'):
                order.delivery_name = request.form.get('delivery_name', '')
                order.delivery_street = request.form.get('delivery_street', '')
                order.delivery_postal_code = request.form.get('delivery_postal_code', '')
                order.delivery_city = request.form.get('delivery_city', '')
                order.delivery_country = request.form.get('delivery_country', 'Deutschland')
            
            # Positionen parsen und speichern
            import json
            items_json = request.form.get('items_json', '[]')
            items = json.loads(items_json)
            order.set_items(items)
            
            db.session.add(order)
            db.session.commit()
            
            # Verknüpfte Auftrags-Positionen aktualisieren
            linked_items_json = request.form.get('linked_order_items', '[]')
            linked_items = json.loads(linked_items_json)
            
            for linked in linked_items:
                order_item = OrderItem.query.get(linked['order_item_id'])
                if order_item:
                    order_item.supplier_order_status = 'ordered'
                    order_item.supplier_order_id = order.id
                    order_item.supplier_order_date = order.order_date
                    order_item.supplier_expected_date = order.delivery_date
            
            db.session.commit()
            
            if order.status == 'draft':
                flash(f'Bestellung als Entwurf gespeichert!', 'success')
            else:
                flash(f'Bestellung {order.order_number} wurde erstellt!', 'success')
            
            log_activity(current_user.username, 'supplier_order_created', 
                        f'Bestellung erstellt: {order.order_number} bei {supplier.name}')
            
            return redirect(url_for('suppliers.show_order', 
                                  supplier_id=supplier_id, 
                                  order_id=order.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Erstellen der Bestellung: {str(e)}', 'danger')
            return redirect(url_for('suppliers.new_order', supplier_id=supplier_id))
    
    # GET Request - Hole offene Aufträge mit Artikeln dieses Lieferanten
    orders_with_items = {}
    
    # Finde alle OrderItems die noch nicht bestellt wurden und wo der Artikel von diesem Lieferanten ist
    open_items = db.session.query(OrderItem)\
        .join(Article)\
        .filter(
            OrderItem.supplier_order_status.in_(['none', 'to_order']),
            Article.supplier == supplier.name
        ).all()
    
    # Gruppiere nach Auftrag
    for item in open_items:
        if item.order_id not in orders_with_items:
            orders_with_items[item.order_id] = {
                'order': item.order,
                'items': []
            }
        
        # Berechne benötigte Menge
        available_stock = item.article.stock or 0
        needed_quantity = max(0, item.quantity - available_stock)
        
        if needed_quantity > 0:
            orders_with_items[item.order_id]['items'].append({
                'order_item': item,
                'article': item.article,
                'available_stock': available_stock,
                'needed_quantity': needed_quantity
            })
    
    # Entferne Aufträge ohne benötigte Artikel
    orders_with_items = {k: v for k, v in orders_with_items.items() if v['items']}
    
    return render_template('suppliers/new_order.html', 
                         supplier=supplier,
                         orders_with_items=orders_with_items,
                         now=datetime.now())

@supplier_bp.route('/<supplier_id>/orders')
@login_required
def orders(supplier_id):
    """Alle Bestellungen bei einem Lieferanten anzeigen"""
    supplier = Supplier.query.get_or_404(supplier_id)
    
    # Hole alle Bestellungen dieses Lieferanten
    supplier_orders = SupplierOrder.query.filter_by(supplier_id=supplier_id)\
                                         .order_by(SupplierOrder.created_at.desc())\
                                         .all()
    
    return render_template('suppliers/orders.html', 
                         supplier=supplier,
                         orders=supplier_orders)

@supplier_bp.route('/<supplier_id>/orders/<order_id>')
@login_required
def show_order(supplier_id, order_id):
    """Bestelldetails anzeigen"""
    supplier = Supplier.query.get_or_404(supplier_id)
    order = SupplierOrder.query.get_or_404(order_id)
    
    if order.supplier_id != supplier_id:
        flash('Bestellung nicht gefunden!', 'danger')
        return redirect(url_for('suppliers.orders', supplier_id=supplier_id))
    
    return render_template('suppliers/order_detail.html', 
                         supplier=supplier,
                         order=order)

@supplier_bp.route('/<supplier_id>/orders/<order_id>/update_status', methods=['POST'])
@login_required
def update_order_status(supplier_id, order_id):
    """Bestellstatus aktualisieren"""
    order = SupplierOrder.query.get_or_404(order_id)
    
    if order.supplier_id != supplier_id:
        return jsonify({'success': False, 'error': 'Invalid order'}), 404
    
    new_status = request.form.get('status')
    valid_statuses = ['draft', 'ordered', 'confirmed', 'shipped', 'delivered', 'cancelled']
    
    if new_status not in valid_statuses:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400
    
    try:
        order.status = new_status
        order.updated_at = datetime.utcnow()
        
        # Update verknüpfte OrderItems wenn geliefert
        if new_status == 'delivered':
            linked_items = OrderItem.query.filter_by(supplier_order_id=order.id).all()
            for item in linked_items:
                item.supplier_order_status = 'delivered'
                item.supplier_delivered_date = datetime.utcnow().date()
        
        db.session.commit()
        
        log_activity(current_user.username, 'supplier_order_status_updated', 
                    f'Bestellstatus aktualisiert: {order.order_number} -> {new_status}')
        
        flash(f'Bestellstatus wurde auf {new_status} gesetzt!', 'success')
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@supplier_bp.route('/<supplier_id>/orders/<order_id>/open_webshop')
@login_required
def open_webshop_for_order(supplier_id, order_id):
    """Öffne Webshop für eine spezifische Bestellung"""
    supplier = Supplier.query.get_or_404(supplier_id)
    order = SupplierOrder.query.get_or_404(order_id)
    
    if order.supplier_id != supplier_id:
        flash('Bestellung gehört nicht zu diesem Lieferanten!', 'danger')
        return redirect(url_for('suppliers.show_order', supplier_id=supplier_id, order_id=order_id))
    
    if not supplier.webshop_url:
        flash('Keine Webshop-URL hinterlegt!', 'warning')
        return redirect(url_for('suppliers.show_order', supplier_id=supplier_id, order_id=order_id))
    
    # Log activity
    log_activity(current_user.username, 'webshop_opened', 
                f'Webshop geöffnet für Bestellung {order.order_number} bei {supplier.name}')
    
    # Erstelle Session-Daten für Auto-Fill (optional)
    session['webshop_order'] = {
        'supplier_id': supplier_id,
        'order_id': order_id,
        'items': order.get_items(),
        'username': supplier.webshop_username
    }
    
    return redirect(supplier.webshop_url)

@supplier_bp.route('/<supplier_id>/webshop/article/<article_id>')
@login_required
def open_webshop_for_article(supplier_id, article_id):
    """Öffne Webshop für einen spezifischen Artikel"""
    supplier = Supplier.query.get_or_404(supplier_id)
    article = Article.query.get_or_404(article_id)
    
    if not supplier.webshop_url:
        flash('Keine Webshop-URL hinterlegt!', 'warning')
        return redirect(url_for('articles.show', article_id=article_id))
    
    # Wenn URL-Pattern vorhanden, nutze es
    if supplier.webshop_article_url_pattern and article.supplier_article_number:
        url = supplier.webshop_article_url_pattern.replace(
            '{article_number}', 
            article.supplier_article_number
        )
        return redirect(url)
    
    # Ansonsten zur Hauptseite
    return redirect(supplier.webshop_url)

@supplier_bp.route('/api/webshop/credentials/<supplier_id>')
@login_required
def get_webshop_credentials(supplier_id):
    """API-Endpunkt für Webshop-Zugangsdaten (für Browser-Extension)"""
    supplier = Supplier.query.get_or_404(supplier_id)
    
    # Nur für Admins
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Entschlüssele Passwort
    password = None
    if supplier.webshop_password_encrypted:
        try:
            password = decrypt_password(supplier.webshop_password_encrypted)
        except:
            password = None
    
    return jsonify({
        'success': True,
        'webshop_url': supplier.webshop_url,
        'username': supplier.webshop_username,
        'password': password,
        'shop_type': supplier.webshop_type,
        'customer_number': supplier.customer_number
    })
