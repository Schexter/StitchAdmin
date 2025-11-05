"""
Dashboard Controller - Hauptübersicht
"""

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from src.models import db, Customer, Order, Article
from datetime import datetime, timedelta
from sqlalchemy import func

# Blueprint erstellen
dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard mit Übersicht anzeigen"""
    # Statistiken sammeln
    total_customers = Customer.query.count()
    total_orders = Order.query.count()
    total_articles = Article.query.count()
    
    # Aktive Aufträge
    active_orders = Order.query.filter(
        Order.status.in_(['accepted', 'in_progress', 'ready'])
    ).count()
    
    # Heutige Aufträge
    today = datetime.now().date()
    today_orders = Order.query.filter(
        db.func.date(Order.created_at) == today
    ).count()
    
    # Letzte 7 Tage Umsatz
    week_ago = datetime.now() - timedelta(days=7)
    week_revenue = db.session.query(
        func.sum(Order.total_price)
    ).filter(
        Order.created_at >= week_ago,
        Order.status != 'cancelled'
    ).scalar() or 0
    
    # Neueste Aufträge
    recent_orders = Order.query.order_by(
        Order.created_at.desc()
    ).limit(5).all()
    
    # Niedrige Lagerbestände
    low_stock_articles = Article.query.filter(
        Article.active == True,
        Article.stock <= Article.min_stock
    ).order_by(Article.stock).limit(5).all()
    
    return render_template('dashboard.html',
                         total_customers=total_customers,
                         total_orders=total_orders,
                         total_articles=total_articles,
                         active_orders=active_orders,
                         today_orders=today_orders,
                         week_revenue=week_revenue,
                         recent_orders=recent_orders,
                         low_stock_articles=low_stock_articles)
