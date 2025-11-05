"""
Supplier Controller Extension - Order Suggestions
"""

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from src.models.models import db, Supplier, SupplierOrder, ActivityLog, OrderItem, Article, Order
import json

def add_order_suggestion_routes(supplier_bp):
    """Add order suggestion routes to supplier blueprint"""
    
    @supplier_bp.route('/order-suggestions')
    @login_required
    def order_suggestions():
        """Zeige Bestellvorschläge basierend auf Aufträgen ohne Lagerbestand"""
        # Hole alle OrderItems die noch nicht bestellt wurden und wo der Artikel nicht auf Lager ist
        # WICHTIG: Verwende LEFT JOIN für Supplier, damit auch Artikel ohne Supplier angezeigt werden
        suggestions = db.session.query(
            OrderItem,
            Article,
            Order,
            Supplier
        ).join(
            Article, OrderItem.article_id == Article.id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).outerjoin(
            Supplier, Article.supplier == Supplier.id  # LEFT JOIN - zeigt auch Artikel ohne Supplier
        ).filter(
            OrderItem.supplier_order_status.in_(['none', 'to_order', None]),  # Auch NULL Status berücksichtigen
            db.or_(
                Article.stock == None,
                Article.stock < OrderItem.quantity
            ),
            Order.status.notin_(['cancelled', 'delivered'])
        ).all()
        
        # Gruppiere nach Lieferant
        supplier_suggestions = {}
        for item, article, order, supplier in suggestions:
            # Bestimme Supplier ID und Name
            if article.supplier and supplier:
                supplier_id = article.supplier
                supplier_name = supplier.name
            else:
                # Artikel ohne zugewiesenen Lieferant
                supplier_id = 'no_supplier'
                supplier_name = 'Kein Lieferant zugewiesen'
            
            if supplier_id not in supplier_suggestions:
                supplier_suggestions[supplier_id] = {
                    'supplier': supplier,
                    'supplier_name': supplier_name,
                    'items': [],
                    'is_unassigned': (supplier_id == 'no_supplier')
                }
            
            # Berechne benötigte Menge
            current_stock = article.stock or 0
            needed_quantity = max(0, item.quantity - current_stock)
            
            supplier_suggestions[supplier_id]['items'].append({
                'order_item': item,
                'article': article,
                'order': order,
                'needed_quantity': needed_quantity,
                'current_stock': current_stock
            })
        
        return render_template('suppliers/order_suggestions.html', 
                             supplier_suggestions=supplier_suggestions)
    
    
    @supplier_bp.route('/create-order-from-suggestions', methods=['POST'])
    @login_required  
    def create_order_from_suggestions():
        """Erstelle Lieferantenbestellung aus Vorschlägen"""
        supplier_id = request.form.get('supplier_id')
        selected_items = request.form.getlist('selected_items')
        
        if not supplier_id or not selected_items:
            flash('Bitte wählen Sie einen Lieferanten und mindestens einen Artikel aus.', 'warning')
            return redirect(url_for('suppliers.order_suggestions'))
        
        supplier = Supplier.query.get_or_404(supplier_id)
        
        try:
            # Erstelle neue Lieferantenbestellung
            order_id = f"SO{datetime.now().strftime('%Y%m%d%H%M%S')}"
            supplier_order = SupplierOrder(
                id=order_id,
                supplier_id=supplier_id,
                order_number=order_id,
                order_date=datetime.now().date(),
                status='draft',
                created_by=current_user.username,
                currency='EUR',
                subtotal=0,
                total_amount=0
            )
            db.session.add(supplier_order)
            
            # Verarbeite ausgewählte Artikel
            order_items = []
            total_amount = 0
            
            for item_id in selected_items:
                order_item_id = int(item_id)
                quantity = int(request.form.get(f'quantity_{item_id}', 0))
                
                if quantity <= 0:
                    continue
                    
                order_item = OrderItem.query.get(order_item_id)
                article = Article.query.get(order_item.article_id)
                
                # Preis berechnen
                unit_price = article.purchase_price or 0
                line_total = unit_price * quantity
                total_amount += line_total
                
                # Füge zur Bestellliste hinzu
                order_items.append({
                    'article_number': article.article_number or article.id,
                    'supplier_article_number': article.supplier_article_number or '',
                    'description': article.name,
                    'quantity': quantity,
                    'unit': 'Stück',
                    'unit_price': unit_price,
                    'line_total': line_total
                })
                
                # Aktualisiere OrderItem Status
                order_item.supplier_order_status = 'to_order'
                order_item.supplier_order_id = order_id
                order_item.supplier_order_date = datetime.now().date()
            
            # Aktualisiere Bestellung
            supplier_order.items = json.dumps(order_items)
            supplier_order.subtotal = total_amount
            supplier_order.total_amount = total_amount
            
            db.session.commit()
            
            # Aktivität protokollieren
            activity = ActivityLog(
                username=current_user.username,
                action='supplier_order_created',
                details=f'Lieferantenbestellung {order_id} für {supplier.name} aus Vorschlägen erstellt',
                ip_address=request.remote_addr
            )
            db.session.add(activity)
            db.session.commit()
            
            flash(f'Bestellung {order_id} wurde erfolgreich erstellt!', 'success')
            return redirect(url_for('suppliers.show', supplier_id=supplier_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Erstellen der Bestellung: {str(e)}', 'danger')
            return redirect(url_for('suppliers.order_suggestions'))
    
    
    @supplier_bp.route('/order/<order_id>/mark-ordered', methods=['POST'])
    @login_required
    def mark_order_as_ordered(order_id):
        """Markiere Bestellung als bestellt und aktualisiere verknüpfte OrderItems"""
        supplier_order = SupplierOrder.query.get_or_404(order_id)
        
        try:
            # Update supplier order status
            supplier_order.status = 'ordered'
            supplier_order.updated_at = datetime.utcnow()
            supplier_order.updated_by = current_user.username
            
            # Update all linked order items
            linked_items = OrderItem.query.filter_by(supplier_order_id=order_id).all()
            for item in linked_items:
                item.supplier_order_status = 'ordered'
                item.supplier_order_date = datetime.now().date()
            
            db.session.commit()
            
            # Log activity
            activity = ActivityLog(
                username=current_user.username,
                action='supplier_order_placed',
                details=f'Lieferantenbestellung {order_id} als bestellt markiert',
                ip_address=request.remote_addr
            )
            db.session.add(activity)
            db.session.commit()
            
            flash('Bestellung wurde als bestellt markiert!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Aktualisieren: {str(e)}', 'danger')
        
        return redirect(request.referrer or url_for('suppliers.index'))