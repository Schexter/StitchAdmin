"""
Purchasing Controller - Einkauf-Modul
=====================================

Zentrales Modul für:
- Bestellübersicht (alle Lieferanten)
- Bestellvorschläge
- Druckbare Bestelllisten
- Design-Bestellungen (Puncher/Digitizer)
- Wareneingang
- Einkaufsstatistiken

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from src.models.models import db, Supplier, Article, SupplierOrder, OrderItem, Order, ActivityLog
from src.models.nummernkreis import DocumentType, NumberSequenceService
from src.utils.activity_logger import log_activity
from sqlalchemy import or_, and_, func
import json

# Blueprint erstellen
purchasing_bp = Blueprint('purchasing', __name__, url_prefix='/purchasing')


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

@purchasing_bp.route('/')
@login_required
def dashboard():
    """Einkauf-Dashboard mit Übersicht"""
    
    # Statistiken sammeln
    stats = get_purchasing_stats()
    
    # Letzte Bestellungen
    recent_orders = SupplierOrder.query\
        .order_by(SupplierOrder.created_at.desc())\
        .limit(5).all()
    
    # Offene Bestellungen nach Status
    pending_by_status = {
        'draft': SupplierOrder.query.filter_by(status='draft').count(),
        'ordered': SupplierOrder.query.filter_by(status='ordered').count(),
        'confirmed': SupplierOrder.query.filter_by(status='confirmed').count(),
        'shipped': SupplierOrder.query.filter_by(status='shipped').count()
    }
    
    # Erwartete Lieferungen diese Woche
    today = date.today()
    week_end = today + timedelta(days=7)
    expected_deliveries = SupplierOrder.query.filter(
        SupplierOrder.status.in_(['ordered', 'confirmed', 'shipped']),
        SupplierOrder.delivery_date >= today,
        SupplierOrder.delivery_date <= week_end
    ).order_by(SupplierOrder.delivery_date).all()
    
    return render_template('purchasing/dashboard.html',
                         stats=stats,
                         recent_orders=recent_orders,
                         pending_by_status=pending_by_status,
                         expected_deliveries=expected_deliveries,
                         today=today)


def get_purchasing_stats():
    """Sammelt Statistiken für das Einkauf-Dashboard"""
    today = date.today()
    month_start = today.replace(day=1)
    
    # Offene Bestellungen
    open_orders = SupplierOrder.query.filter(
        SupplierOrder.status.in_(['draft', 'ordered', 'confirmed', 'shipped'])
    ).count()
    
    # Bestellvorschläge zählen
    suggestions_count = get_order_suggestions_count()
    
    # Monatliches Einkaufsvolumen
    monthly_volume = db.session.query(func.sum(SupplierOrder.total_amount))\
        .filter(SupplierOrder.order_date >= month_start)\
        .scalar() or 0
    
    # Lieferungen heute erwartet
    expected_today = SupplierOrder.query.filter(
        SupplierOrder.status.in_(['ordered', 'confirmed', 'shipped']),
        SupplierOrder.delivery_date == today
    ).count()
    
    # Überfällige Lieferungen
    overdue = SupplierOrder.query.filter(
        SupplierOrder.status.in_(['ordered', 'confirmed', 'shipped']),
        SupplierOrder.delivery_date < today
    ).count()
    
    return {
        'open_orders': open_orders,
        'suggestions_count': suggestions_count,
        'monthly_volume': monthly_volume,
        'expected_today': expected_today,
        'overdue': overdue,
        'pending_designs': 0  # Wird später mit DesignOrder gefüllt
    }


def get_order_suggestions_count():
    """Zählt Bestellvorschläge (Artikel unter Mindestbestand oder für offene Aufträge benötigt)"""
    # Artikel unter Mindestbestand
    low_stock = Article.query.filter(
        Article.active == True,
        Article.min_stock > 0,
        Article.stock < Article.min_stock
    ).count()
    
    # OrderItems die bestellt werden müssen
    pending_items = OrderItem.query.filter(
        OrderItem.supplier_order_status.in_(['none', 'to_order'])
    ).join(Order).filter(
        Order.status.notin_(['cancelled', 'delivered', 'completed'])
    ).count()
    
    return low_stock + pending_items


# ═══════════════════════════════════════════════════════════════════════════════
# BESTELLÜBERSICHT
# ═══════════════════════════════════════════════════════════════════════════════

@purchasing_bp.route('/orders')
@login_required
def orders():
    """Alle Bestellungen (alle Lieferanten)"""
    # Filter
    status_filter = request.args.get('status', '')
    supplier_filter = request.args.get('supplier', '')
    search = request.args.get('search', '')
    
    # Basis-Query
    query = SupplierOrder.query
    
    # Filter anwenden
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    if supplier_filter:
        query = query.filter_by(supplier_id=supplier_filter)
    
    if search:
        query = query.filter(
            or_(
                SupplierOrder.order_number.ilike(f'%{search}%'),
                SupplierOrder.purchase_order_number.ilike(f'%{search}%'),
                SupplierOrder.supplier_order_number.ilike(f'%{search}%')
            )
        )
    
    # Sortierung und Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    pagination = query.order_by(SupplierOrder.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    orders = pagination.items
    
    # Alle Lieferanten für Filter-Dropdown
    suppliers = Supplier.query.filter_by(active=True).order_by(Supplier.name).all()
    
    # Statistiken
    total_value = db.session.query(func.sum(SupplierOrder.total_amount))\
        .filter(SupplierOrder.status.notin_(['cancelled'])).scalar() or 0
    
    return render_template('purchasing/orders/index.html',
                         orders=orders,
                         pagination=pagination,
                         suppliers=suppliers,
                         status_filter=status_filter,
                         supplier_filter=supplier_filter,
                         search=search,
                         total_value=total_value,
                         today=date.today())


@purchasing_bp.route('/orders/pending')
@login_required
def pending_orders():
    """Offene Bestellungen"""
    # Offene Status
    orders = SupplierOrder.query.filter(
        SupplierOrder.status.in_(['draft', 'ordered', 'confirmed', 'shipped'])
    ).order_by(
        # Sortierung: Status-Priorität, dann Datum
        db.case(
            (SupplierOrder.status == 'draft', 1),
            (SupplierOrder.status == 'ordered', 2),
            (SupplierOrder.status == 'confirmed', 3),
            (SupplierOrder.status == 'shipped', 4),
            else_=5
        ),
        SupplierOrder.created_at.desc()
    ).all()
    
    # Gruppiere nach Status
    orders_by_status = {
        'draft': [],
        'ordered': [],
        'confirmed': [],
        'shipped': []
    }
    
    for order in orders:
        if order.status in orders_by_status:
            orders_by_status[order.status].append(order)
    
    # Überfällige Bestellungen
    today = date.today()
    overdue_orders = [o for o in orders if o.delivery_date and o.delivery_date < today]
    
    # Statistiken
    total_pending_value = sum(o.total_amount or 0 for o in orders)
    
    return render_template('purchasing/orders/pending.html',
                         orders_by_status=orders_by_status,
                         total_orders=len(orders),
                         total_value=total_pending_value,
                         overdue_orders=overdue_orders,
                         today=today)


@purchasing_bp.route('/orders/<order_id>')
@login_required
def order_detail(order_id):
    """Bestelldetails"""
    order = SupplierOrder.query.get_or_404(order_id)
    supplier = order.supplier
    
    # Items laden
    items = order.get_items() if hasattr(order, 'get_items') else []
    
    # Verknüpfte Kundenaufträge
    linked_orders = []
    if hasattr(order, 'linked_customer_orders') and order.linked_customer_orders:
        try:
            order_ids = json.loads(order.linked_customer_orders)
            linked_orders = Order.query.filter(Order.id.in_(order_ids)).all()
        except:
            pass

    # Alternativ: Aus den Items die verknüpften Aufträge ermitteln
    if not linked_orders and items:
        linked_order_ids = set()
        for item in items:
            if item.get('order_id'):
                linked_order_ids.add(item['order_id'])
        if linked_order_ids:
            linked_orders = Order.query.filter(Order.id.in_(linked_order_ids)).all()
    
    return render_template('purchasing/orders/detail.html',
                         order=order,
                         supplier=supplier,
                         items=items,
                         linked_orders=linked_orders,
                         today=date.today())


# ═══════════════════════════════════════════════════════════════════════════════
# DRUCKBARE BESTELLLISTE
# ═══════════════════════════════════════════════════════════════════════════════

@purchasing_bp.route('/orders/<order_id>/print-list')
@login_required
def print_order_list(order_id):
    """Druckbare Bestellliste mit Abhak-Funktion"""
    order = SupplierOrder.query.get_or_404(order_id)
    supplier = order.supplier
    
    # Items laden und gruppieren
    items = order.get_items() if hasattr(order, 'get_items') else []
    
    # Verknüpfte Kundenaufträge für Referenz
    linked_orders = []
    if order.linked_customer_orders:
        try:
            order_ids = json.loads(order.linked_customer_orders)
            linked_orders = Order.query.filter(Order.id.in_(order_ids)).all()
        except:
            pass
    
    # Druck-Tracking aktualisieren
    order.print_count = (order.print_count or 0) + 1
    order.last_printed_at = datetime.utcnow()
    order.last_printed_by = current_user.username
    db.session.commit()
    
    log_activity(current_user.username, 'purchase_order_printed',
                f'Bestellliste gedruckt: {order.purchase_order_number or order.order_number}')
    
    return render_template('purchasing/orders/print_list.html',
                         order=order,
                         supplier=supplier,
                         items=items,
                         linked_orders=linked_orders,
                         print_date=datetime.now())


# ═══════════════════════════════════════════════════════════════════════════════
# BESTELLVORSCHLÄGE
# ═══════════════════════════════════════════════════════════════════════════════

@purchasing_bp.route('/suggestions')
@login_required
def suggestions():
    """Bestellvorschläge basierend auf Aufträgen und Lagerbestand"""
    
    # 1. Artikel unter Mindestbestand
    low_stock_articles = Article.query.filter(
        Article.active == True,
        Article.min_stock > 0,
        Article.stock < Article.min_stock
    ).all()
    
    # 2. OrderItems die bestellt werden müssen
    pending_items = db.session.query(
        OrderItem,
        Article,
        Order,
        Supplier
    ).join(
        Article, OrderItem.article_id == Article.id
    ).join(
        Order, OrderItem.order_id == Order.id
    ).outerjoin(
        Supplier, Article.supplier == Supplier.name
    ).filter(
        OrderItem.supplier_order_status.in_(['none', 'to_order']),
        Order.status.notin_(['cancelled', 'delivered', 'completed'])
    ).all()
    
    # Gruppiere nach Lieferant
    supplier_suggestions = {}
    
    # Niedrigen Lagerbestand hinzufügen
    for article in low_stock_articles:
        supplier_name = article.supplier or 'Kein Lieferant'
        supplier = Supplier.query.filter_by(name=supplier_name).first()
        supplier_id = supplier.id if supplier else 'no_supplier'
        
        if supplier_id not in supplier_suggestions:
            supplier_suggestions[supplier_id] = {
                'supplier': supplier,
                'supplier_name': supplier_name,
                'order_items': [],
                'low_stock_items': []
            }

        reorder_qty = (article.min_stock or 0) - (article.stock or 0)
        supplier_suggestions[supplier_id]['low_stock_items'].append({
            'article': article,
            'current_stock': article.stock or 0,
            'min_stock': article.min_stock,
            'reorder_quantity': max(reorder_qty, 1)
        })

    # Auftrags-Items hinzufügen
    for item, article, order, supplier in pending_items:
        supplier_id = supplier.id if supplier else 'no_supplier'
        supplier_name = supplier.name if supplier else 'Kein Lieferant'

        if supplier_id not in supplier_suggestions:
            supplier_suggestions[supplier_id] = {
                'supplier': supplier,
                'supplier_name': supplier_name,
                'order_items': [],
                'low_stock_items': []
            }

        # Benötigte Menge berechnen
        current_stock = article.stock or 0
        needed_quantity = max(0, item.quantity - current_stock)

        if needed_quantity > 0:
            supplier_suggestions[supplier_id]['order_items'].append({
                'order_item': item,
                'article': article,
                'order': order,
                'needed_quantity': needed_quantity,
                'current_stock': current_stock
            })
    
    return render_template('suppliers/order_suggestions.html',
                         supplier_suggestions=supplier_suggestions)


# ═══════════════════════════════════════════════════════════════════════════════
# WARENEINGANG
# ═══════════════════════════════════════════════════════════════════════════════

@purchasing_bp.route('/receiving')
@login_required
def receiving():
    """Wareneingang - Übersicht erwarteter Lieferungen"""
    today = date.today()
    
    # Heute erwartete Lieferungen
    expected_today = SupplierOrder.query.filter(
        SupplierOrder.status.in_(['ordered', 'confirmed', 'shipped']),
        SupplierOrder.delivery_date == today
    ).all()
    
    # Diese Woche erwartet
    week_end = today + timedelta(days=7)
    expected_week = SupplierOrder.query.filter(
        SupplierOrder.status.in_(['ordered', 'confirmed', 'shipped']),
        SupplierOrder.delivery_date > today,
        SupplierOrder.delivery_date <= week_end
    ).order_by(SupplierOrder.delivery_date).all()
    
    # Überfällige Lieferungen
    overdue = SupplierOrder.query.filter(
        SupplierOrder.status.in_(['ordered', 'confirmed', 'shipped']),
        SupplierOrder.delivery_date < today
    ).order_by(SupplierOrder.delivery_date).all()
    
    # Kürzlich geliefert (letzte 7 Tage)
    week_ago = today - timedelta(days=7)
    recently_received = SupplierOrder.query.filter(
        SupplierOrder.status == 'delivered',
        SupplierOrder.delivery_date >= week_ago
    ).order_by(SupplierOrder.delivery_date.desc()).limit(10).all()
    
    return render_template('purchasing/receiving/index.html',
                         expected_today=expected_today,
                         expected_week=expected_week,
                         overdue=overdue,
                         recently_received=recently_received,
                         today=today)


# ═══════════════════════════════════════════════════════════════════════════════
# STATISTIKEN
# ═══════════════════════════════════════════════════════════════════════════════

@purchasing_bp.route('/statistics')
@login_required
def statistics():
    """Einkaufsstatistiken"""
    today = date.today()
    year_start = today.replace(month=1, day=1)
    month_start = today.replace(day=1)
    
    # Jahresstatistik
    yearly_volume = db.session.query(func.sum(SupplierOrder.total_amount))\
        .filter(
            SupplierOrder.order_date >= year_start,
            SupplierOrder.status != 'cancelled'
        ).scalar() or 0
    
    yearly_orders = SupplierOrder.query.filter(
        SupplierOrder.order_date >= year_start,
        SupplierOrder.status != 'cancelled'
    ).count()
    
    # Monatsstatistik
    monthly_volume = db.session.query(func.sum(SupplierOrder.total_amount))\
        .filter(
            SupplierOrder.order_date >= month_start,
            SupplierOrder.status != 'cancelled'
        ).scalar() or 0
    
    monthly_orders = SupplierOrder.query.filter(
        SupplierOrder.order_date >= month_start,
        SupplierOrder.status != 'cancelled'
    ).count()
    
    # Top Lieferanten nach Umsatz (dieses Jahr)
    top_suppliers = db.session.query(
        Supplier.name,
        func.sum(SupplierOrder.total_amount).label('total'),
        func.count(SupplierOrder.id).label('order_count')
    ).join(
        SupplierOrder, Supplier.id == SupplierOrder.supplier_id
    ).filter(
        SupplierOrder.order_date >= year_start,
        SupplierOrder.status != 'cancelled'
    ).group_by(
        Supplier.id
    ).order_by(
        func.sum(SupplierOrder.total_amount).desc()
    ).limit(10).all()
    
    # Monatliche Entwicklung
    monthly_data = []
    for i in range(12):
        month = today.replace(month=i+1, day=1) if i+1 <= today.month else None
        if month and month <= today:
            month_end = (month.replace(month=month.month+1, day=1) - timedelta(days=1)) if month.month < 12 else month.replace(day=31)
            volume = db.session.query(func.sum(SupplierOrder.total_amount))\
                .filter(
                    SupplierOrder.order_date >= month,
                    SupplierOrder.order_date <= month_end,
                    SupplierOrder.status != 'cancelled'
                ).scalar() or 0
            monthly_data.append({
                'month': month.strftime('%b'),
                'volume': volume
            })
    
    return render_template('purchasing/statistics/index.html',
                         yearly_volume=yearly_volume,
                         yearly_orders=yearly_orders,
                         monthly_volume=monthly_volume,
                         monthly_orders=monthly_orders,
                         top_suppliers=top_suppliers,
                         monthly_data=monthly_data,
                         year=today.year)


# ═══════════════════════════════════════════════════════════════════════════════
# REDIRECT VON ALTEN ROUTEN
# ═══════════════════════════════════════════════════════════════════════════════

# Diese werden in supplier_controller_db.py hinzugefügt als Redirects


# ═══════════════════════════════════════════════════════════════════════════════
# HILFSFUNKTIONEN
# ═══════════════════════════════════════════════════════════════════════════════

def generate_purchase_order_number(order_id=None, created_by=None):
    """Generiert eine neue Einkaufsbestellnummer"""
    return NumberSequenceService.get_next_number(
        DocumentType.PURCHASE_ORDER,
        document_id=order_id,
        created_by=created_by
    )


def generate_design_order_number(order_id=None, created_by=None):
    """Generiert eine neue Design-Bestellnummer"""
    return NumberSequenceService.get_next_number(
        DocumentType.DESIGN_ORDER,
        document_id=order_id,
        created_by=created_by
    )


# ═══════════════════════════════════════════════════════════════════════════════
# OFFENE BESTELLUNGEN AUS AUFTRÄGEN
# ═══════════════════════════════════════════════════════════════════════════════

@purchasing_bp.route('/pending-items')
@login_required
def pending_items():
    """
    Zeigt alle Artikel die aus Aufträgen bestellt werden müssen.
    Hier können Lieferanten zugewiesen und Bestelllisten erstellt werden.
    """
    from src.models.article_supplier import ArticleSupplier

    # Druckansicht?
    print_mode = request.args.get('print') == '1'
    selected_item_ids = request.args.get('items', '')

    # Basis-Query für OrderItems
    query = db.session.query(
        OrderItem,
        Article,
        Order
    ).join(
        Article, OrderItem.article_id == Article.id
    ).join(
        Order, OrderItem.order_id == Order.id
    ).filter(
        OrderItem.supplier_order_status.in_(['none', 'to_order']),
        Order.status.notin_(['cancelled', 'completed'])
    )

    # Bei Druckansicht nur ausgewählte Items
    if print_mode and selected_item_ids:
        try:
            item_id_list = [int(x) for x in selected_item_ids.split(',') if x.strip()]
            if item_id_list:
                query = query.filter(OrderItem.id.in_(item_id_list))
        except ValueError:
            pass

    pending = query.order_by(
        Order.due_date.asc().nullslast(),
        Order.created_at.asc()
    ).all()

    # Gruppiere nach Artikel und sammle Lieferanten-Optionen
    items_data = []
    for item, article, order in pending:
        # Finde mögliche Lieferanten für diesen Artikel
        article_suppliers = ArticleSupplier.query.filter_by(
            article_id=article.id,
            active=True
        ).all()

        # Standard-Lieferant aus Artikel
        default_supplier = None
        if article.supplier:
            default_supplier = Supplier.query.filter_by(name=article.supplier).first()

        items_data.append({
            'order_item': item,
            'article': article,
            'order': order,
            'article_suppliers': article_suppliers,
            'default_supplier': default_supplier,
            'selected_supplier_id': item.supplier_id if hasattr(item, 'supplier_id') else (default_supplier.id if default_supplier else None)
        })

    # Alle aktiven Lieferanten für Dropdown
    suppliers = Supplier.query.filter_by(active=True).order_by(Supplier.name).all()

    # Druckansicht nutzt anderes Template
    if print_mode:
        return render_template('purchasing/pending_items_print.html',
                             items_data=items_data,
                             suppliers=suppliers,
                             total_items=len(items_data),
                             today=date.today(),
                             print_date=datetime.now())

    return render_template('purchasing/pending_items.html',
                         items_data=items_data,
                         suppliers=suppliers,
                         total_items=len(items_data),
                         today=date.today())


@purchasing_bp.route('/pending-items/mark-to-order', methods=['POST'])
@login_required
def mark_items_to_order():
    """Markiert ausgewählte Items als 'zu bestellen' mit Lieferant"""
    data = request.get_json()
    item_ids = data.get('item_ids', [])
    supplier_assignments = data.get('supplier_assignments', {})  # {item_id: supplier_id}

    if not item_ids:
        return jsonify({'success': False, 'message': 'Keine Artikel ausgewählt'}), 400

    updated = 0
    for item_id in item_ids:
        item = OrderItem.query.get(item_id)
        if item:
            item.supplier_order_status = 'to_order'
            supplier_id = supplier_assignments.get(str(item_id))
            if supplier_id:
                # Speichere den gewählten Lieferanten (falls Feld existiert)
                if hasattr(item, 'preferred_supplier_id'):
                    item.preferred_supplier_id = int(supplier_id)
            updated += 1

    db.session.commit()

    log_activity(current_user.username, 'items_marked_to_order',
                f'{updated} Artikel zum Bestellen markiert')

    return jsonify({
        'success': True,
        'message': f'{updated} Artikel zum Bestellen markiert',
        'updated': updated
    })


@purchasing_bp.route('/create-order-from-items', methods=['POST'])
@login_required
def create_order_from_items():
    """
    Erstellt eine Lieferantenbestellung aus ausgewählten Artikeln.
    Gruppiert automatisch nach Lieferant.
    Fügt den Lieferanten automatisch zum Artikel hinzu, falls noch nicht vorhanden.
    """
    from src.models.article_supplier import ArticleSupplier
    import logging
    import traceback

    try:
        data = request.get_json()
        logging.info(f"create_order_from_items - Received data: {data}")

        if not data:
            logging.error("create_order_from_items - No JSON data received")
            return jsonify({'success': False, 'message': 'Keine Daten empfangen'}), 400

        item_ids = data.get('item_ids', [])
        supplier_id = data.get('supplier_id')

        logging.info(f"create_order_from_items - item_ids: {item_ids}, supplier_id: {supplier_id}, type: {type(supplier_id)}")

        if not item_ids:
            logging.error("create_order_from_items - No items selected")
            return jsonify({'success': False, 'message': 'Keine Artikel ausgewählt'}), 400

        if not supplier_id:
            logging.error("create_order_from_items - No supplier selected")
            return jsonify({'success': False, 'message': 'Kein Lieferant ausgewählt'}), 400

        # Supplier ID kann String oder Int sein
        supplier_id_str = str(supplier_id)
        logging.info(f"create_order_from_items - Looking for supplier with ID: {supplier_id_str}")

        supplier = Supplier.query.get(supplier_id_str)
        if not supplier:
            logging.error(f"create_order_from_items - Supplier not found: {supplier_id_str}")
            return jsonify({'success': False, 'message': f'Lieferant nicht gefunden (ID: {supplier_id_str})'}), 404

        # Hole alle OrderItems
        order_items = OrderItem.query.filter(OrderItem.id.in_(item_ids)).all()
        logging.info(f"create_order_from_items - Found {len(order_items)} order items")

        if not order_items:
            return jsonify({'success': False, 'message': 'Keine gültigen Artikel gefunden'}), 400

        # Berechne Lieferzeit
        delivery_days = supplier.delivery_time_days or 7
        expected_delivery = date.today() + timedelta(days=delivery_days)

        # Generiere IDs
        order_id = f"SO{datetime.now().strftime('%Y%m%d%H%M%S')}"
        order_number = generate_purchase_order_number(created_by=current_user.username)
        logging.info(f"create_order_from_items - Generated order_id: {order_id}, order_number: {order_number}")

        # Erstelle neue Bestellung
        new_order = SupplierOrder(
            id=order_id,
            supplier_id=supplier_id_str,
            order_number=order_number,
            status='draft',
            order_date=date.today(),
            delivery_date=expected_delivery,
            created_by=current_user.username
        )

        # Sammle Items und berechne Gesamtbetrag
        items_list = []
        total = 0
        linked_order_ids = set()
        articles_linked_to_supplier = 0

        for item in order_items:
            article = Article.query.get(item.article_id)
            if not article:
                logging.warning(f"create_order_from_items - Article not found for item {item.id}")
                continue

            # Preis vom ArticleSupplier oder Artikel (Article hat purchase_price_single, nicht purchase_price)
            price = getattr(article, 'purchase_price_single', 0) or getattr(article, 'purchase_price_carton', 0) or 0
            article_supplier = ArticleSupplier.query.filter_by(
                article_id=article.id,
                supplier_id=supplier_id_str
            ).first()

            if article_supplier:
                # Lieferant bereits zugeordnet - nutze dessen Preis
                if article_supplier.purchase_price:
                    price = article_supplier.purchase_price
            else:
                # Lieferant noch nicht zugeordnet - automatisch anlegen
                # Prüfe ob Artikel bereits einen Hauptlieferanten hat
                has_main_supplier = article.supplier and len(article.supplier) > 0
                existing_suppliers = ArticleSupplier.query.filter_by(
                    article_id=article.id,
                    active=True
                ).count()

                # Neuen ArticleSupplier erstellen
                new_article_supplier = ArticleSupplier(
                    article_id=article.id,
                    supplier_id=supplier_id_str,
                    purchase_price=price if price > 0 else 0.01,  # Mindestpreis
                    preferred=not has_main_supplier and existing_suppliers == 0,  # Bevorzugt wenn kein anderer Lieferant
                    active=True,
                    created_by=current_user.username,
                    notes=f'Automatisch erstellt bei Bestellung am {date.today().strftime("%d.%m.%Y")}'
                )
                db.session.add(new_article_supplier)
                logging.info(f"create_order_from_items - Created ArticleSupplier for article {article.id}")

                # Wenn kein Hauptlieferant vorhanden, diesen als Hauptlieferant setzen
                if not has_main_supplier:
                    article.supplier = supplier.name

                articles_linked_to_supplier += 1

            item_total = price * item.quantity
            total += item_total

            items_list.append({
                'article_id': str(article.id),
                'article_number': article.article_number,
                'article_name': article.name,
                'quantity': item.quantity,
                'unit_price': float(price),
                'total': float(item_total),
                'order_item_id': item.id,
                'order_id': item.order_id,
                'size': getattr(item, 'textile_size', None),
                'color': getattr(item, 'textile_color', None)
            })

            linked_order_ids.add(item.order_id)

            # Update OrderItem Status
            item.supplier_order_status = 'ordered'
            if hasattr(item, 'supplier_order_date'):
                item.supplier_order_date = date.today()
            if hasattr(item, 'supplier_expected_date'):
                item.supplier_expected_date = expected_delivery

        logging.info(f"create_order_from_items - Created {len(items_list)} items for order")

        new_order.set_items(items_list)
        new_order.subtotal = total
        new_order.total_amount = total
        new_order.notes = f"Verknüpfte Aufträge: {', '.join(str(oid) for oid in linked_order_ids)}"

        db.session.add(new_order)
        db.session.commit()

        logging.info(f"create_order_from_items - Order created with ID: {new_order.id}")

        # Verknüpfe OrderItems mit der SupplierOrder
        for item in order_items:
            if hasattr(item, 'supplier_order_id'):
                item.supplier_order_id = new_order.id
        db.session.commit()

        # Log-Nachricht mit Info über neu verknüpfte Artikel
        log_msg = f'Bestellung {new_order.order_number} für {supplier.name} erstellt'
        if articles_linked_to_supplier > 0:
            log_msg += f' ({articles_linked_to_supplier} Artikel neu mit Lieferant verknüpft)'
        log_activity(current_user.username, 'supplier_order_created', log_msg)

        # Erfolgsmeldung mit Info über Lieferanten-Verknüpfungen
        message = f'Bestellung {new_order.order_number} erstellt'
        if articles_linked_to_supplier > 0:
            message += f' - {articles_linked_to_supplier} Artikel wurden mit dem Lieferanten verknüpft'

        return jsonify({
            'success': True,
            'message': message,
            'order_id': new_order.id,
            'order_number': new_order.order_number,
            'articles_linked': articles_linked_to_supplier
        })

    except Exception as e:
        logging.error(f"create_order_from_items - Exception: {str(e)}")
        logging.error(traceback.format_exc())
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Fehler: {str(e)}'}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# BESTELLVORGANG - ONLINE/TELEFON
# ═══════════════════════════════════════════════════════════════════════════════

@purchasing_bp.route('/orders/<order_id>/place', methods=['GET', 'POST'])
@login_required
def place_order(order_id):
    """
    Bestellung aufgeben - zeigt Dialog für Online/Telefon Bestellung
    """
    order = SupplierOrder.query.get_or_404(order_id)

    if order.status != 'draft':
        flash('Bestellung wurde bereits aufgegeben', 'warning')
        return redirect(url_for('purchasing.order_detail', order_id=order_id))

    if request.method == 'POST':
        order_method = request.form.get('order_method', 'online')  # online oder phone
        supplier_order_number = request.form.get('supplier_order_number', '')
        notes = request.form.get('notes', '')

        # Status aktualisieren
        order.status = 'ordered'
        order.order_date = date.today()
        order.supplier_order_number = supplier_order_number
        order.order_method = order_method  # Falls Feld existiert

        if notes:
            order.notes = (order.notes or '') + f'\n[{datetime.now().strftime("%d.%m.%Y %H:%M")}] Bestellt via {order_method}: {notes}'

        # Berechne erwartetes Lieferdatum basierend auf Lieferant
        if order.supplier:
            delivery_days = order.supplier.delivery_time_days or 7
            # Nutze Durchschnitt wenn verfügbar
            if order.supplier.avg_delivery_days:
                delivery_days = int(order.supplier.avg_delivery_days)
            order.delivery_date = date.today() + timedelta(days=delivery_days)

        db.session.commit()

        log_activity(current_user.username, 'order_placed',
                    f'Bestellung {order.order_number} aufgegeben ({order_method})')

        flash(f'Bestellung {order.order_number} wurde aufgegeben!', 'success')
        return redirect(url_for('purchasing.order_detail', order_id=order_id))

    # GET - Zeige Dialog
    return render_template('purchasing/orders/place_order.html',
                         order=order,
                         supplier=order.supplier,
                         today=date.today(),
                         timedelta=timedelta)


# ═══════════════════════════════════════════════════════════════════════════════
# WARENEINGANG MIT CHECKLISTE
# ═══════════════════════════════════════════════════════════════════════════════

@purchasing_bp.route('/receiving/<order_id>')
@login_required
def receiving_checklist(order_id):
    """
    Wareneingang-Checkliste für eine Bestellung.
    Zeigt alle erwarteten Positionen zum Abhaken.
    """
    order = SupplierOrder.query.get_or_404(order_id)

    if order.status not in ['ordered', 'confirmed', 'shipped', 'partial']:
        flash('Diese Bestellung erwartet keinen Wareneingang', 'warning')
        return redirect(url_for('purchasing.order_detail', order_id=order_id))

    items = order.get_items()

    # Füge Empfangsstatus zu jedem Item hinzu
    for item in items:
        item['received_quantity'] = item.get('received_quantity', 0)
        item['is_complete'] = item['received_quantity'] >= item['quantity']

    return render_template('purchasing/receiving/checklist.html',
                         order=order,
                         items=items,
                         supplier=order.supplier,
                         today=date.today())


@purchasing_bp.route('/receiving/<order_id>/confirm', methods=['POST'])
@login_required
def confirm_receiving(order_id):
    """
    Bestätigt den Wareneingang für eine Bestellung.
    Aktualisiert Lagerbestände und markiert Items als geliefert.
    """
    order = SupplierOrder.query.get_or_404(order_id)
    data = request.get_json()

    received_items = data.get('received_items', {})  # {item_index: received_quantity}
    all_complete = data.get('all_complete', False)
    notes = data.get('notes', '')

    items = order.get_items()
    has_incomplete = False

    for idx, item in enumerate(items):
        idx_str = str(idx)
        if idx_str in received_items:
            received_qty = int(received_items[idx_str])
            item['received_quantity'] = received_qty

            if received_qty < item['quantity']:
                has_incomplete = True

            # Lagerbestand aktualisieren
            if received_qty > 0 and item.get('article_id'):
                article = Article.query.get(item['article_id'])
                if article:
                    article.stock = (article.stock or 0) + received_qty

                # Verknüpftes OrderItem aktualisieren
                if item.get('order_item_id'):
                    order_item = OrderItem.query.get(item['order_item_id'])
                    if order_item:
                        order_item.supplier_order_status = 'delivered' if received_qty >= item['quantity'] else 'partial'
                        order_item.supplier_delivered_date = date.today()

    # Items speichern
    order.set_items(items)

    # Status aktualisieren
    if has_incomplete:
        order.status = 'partial'
        order.notes = (order.notes or '') + f'\n[{datetime.now().strftime("%d.%m.%Y %H:%M")}] Teillieferung eingegangen - nicht vollständig!'
    else:
        order.status = 'delivered'
        order.actual_delivery_date = date.today()

        # Lieferzeit-Statistik aktualisieren
        if order.supplier and order.order_date:
            actual_days = (date.today() - order.order_date).days
            update_supplier_delivery_stats(order.supplier, actual_days)

    if notes:
        order.notes = (order.notes or '') + f'\n[{datetime.now().strftime("%d.%m.%Y %H:%M")}] {notes}'

    order.received_by = current_user.username
    order.received_at = datetime.utcnow()

    db.session.commit()

    log_activity(current_user.username, 'goods_received',
                f'Wareneingang für {order.order_number}: {"Vollständig" if not has_incomplete else "Teillieferung"}')

    return jsonify({
        'success': True,
        'message': 'Wareneingang bestätigt' if not has_incomplete else 'Teillieferung bestätigt - Bestellung bleibt offen',
        'status': order.status,
        'has_incomplete': has_incomplete
    })


def update_supplier_delivery_stats(supplier, actual_days):
    """
    Aktualisiert die durchschnittliche Lieferzeit eines Lieferanten.
    Verwendet einen gleitenden Durchschnitt.
    """
    if not supplier.avg_delivery_days:
        supplier.avg_delivery_days = actual_days
    else:
        # Gleitender Durchschnitt: 80% alter Wert, 20% neuer Wert
        supplier.avg_delivery_days = (supplier.avg_delivery_days * 0.8) + (actual_days * 0.2)

    # Statistik aktualisieren
    supplier.total_orders = (supplier.total_orders or 0) + 1

    # Pünktlichkeit berechnen
    expected_days = supplier.delivery_time_days or 7
    if actual_days <= expected_days:
        # Pünktlich oder früher
        current_rate = supplier.on_time_delivery_rate or 100
        new_count = supplier.total_orders
        supplier.on_time_delivery_rate = ((current_rate * (new_count - 1)) + 100) / new_count
    else:
        # Verspätet
        current_rate = supplier.on_time_delivery_rate or 100
        new_count = supplier.total_orders
        supplier.on_time_delivery_rate = ((current_rate * (new_count - 1)) + 0) / new_count


# ═══════════════════════════════════════════════════════════════════════════════
# DRUCKBARE BESTELLLISTE
# ═══════════════════════════════════════════════════════════════════════════════

@purchasing_bp.route('/orders/<order_id>/print-checklist')
@login_required
def print_order_checklist(order_id):
    """
    Druckbare Bestellliste mit Abhak-Kästchen.
    Kann ausgedruckt und beim Wareneingang verwendet werden.
    """
    order = SupplierOrder.query.get_or_404(order_id)
    items = order.get_items()

    # Artikeldetails anreichern
    for item in items:
        if item.get('article_id'):
            article = Article.query.get(item['article_id'])
            if article:
                item['article'] = article
                item['ean'] = getattr(article, 'ean', '') or getattr(article, 'barcode', '') or ''
                item['location'] = getattr(article, 'location', '') or getattr(article, 'storage_location', '') or ''

    return render_template('purchasing/orders/print_checklist.html',
                         order=order,
                         items=items,
                         supplier=order.supplier,
                         print_date=datetime.now())


# ═══════════════════════════════════════════════════════════════════════════════
# STATUS-UPDATES UND STORNO
# ═══════════════════════════════════════════════════════════════════════════════

@purchasing_bp.route('/orders/<order_id>/update-status', methods=['POST'])
@login_required
def update_status(order_id):
    """Aktualisiert den Status einer Bestellung"""
    order = SupplierOrder.query.get_or_404(order_id)
    new_status = request.form.get('status')

    valid_transitions = {
        'draft': ['ordered', 'cancelled'],
        'ordered': ['confirmed', 'shipped', 'cancelled'],
        'confirmed': ['shipped', 'delivered', 'cancelled'],
        'shipped': ['delivered', 'partial'],
        'partial': ['delivered'],
        'delivered': [],
        'cancelled': []
    }

    if new_status not in valid_transitions.get(order.status, []):
        flash(f'Ungültiger Statusübergang von {order.status} zu {new_status}', 'danger')
        return redirect(url_for('purchasing.order_detail', order_id=order_id))

    old_status = order.status
    order.status = new_status

    if new_status == 'shipped':
        order.notes = (order.notes or '') + f'\n[{datetime.now().strftime("%d.%m.%Y %H:%M")}] Status: Unterwegs'
    elif new_status == 'confirmed':
        order.notes = (order.notes or '') + f'\n[{datetime.now().strftime("%d.%m.%Y %H:%M")}] Status: Vom Lieferanten bestätigt'

    db.session.commit()

    log_activity(current_user.username, 'order_status_updated',
                f'Bestellung {order.order_number}: {old_status} -> {new_status}')

    flash(f'Status auf "{new_status}" geändert', 'success')
    return redirect(url_for('purchasing.order_detail', order_id=order_id))


@purchasing_bp.route('/orders/<order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    """Storniert eine Bestellung"""
    order = SupplierOrder.query.get_or_404(order_id)

    if order.status not in ['draft', 'ordered']:
        flash('Diese Bestellung kann nicht mehr storniert werden', 'danger')
        return redirect(url_for('purchasing.order_detail', order_id=order_id))

    order.status = 'cancelled'
    order.notes = (order.notes or '') + f'\n[{datetime.now().strftime("%d.%m.%Y %H:%M")}] Storniert von {current_user.username}'

    # Verknüpfte OrderItems zurücksetzen
    items = order.get_items()
    for item in items:
        if item.get('order_item_id'):
            order_item = OrderItem.query.get(item['order_item_id'])
            if order_item:
                order_item.supplier_order_status = 'none'
                order_item.supplier_order_id = None

    db.session.commit()

    log_activity(current_user.username, 'order_cancelled',
                f'Bestellung {order.order_number} storniert')

    flash('Bestellung wurde storniert', 'success')
    return redirect(url_for('purchasing.orders'))
