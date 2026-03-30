# -*- coding: utf-8 -*-
"""
Dashboard Controller
====================
Personalisiertes Dashboard mit Modulen, Stats, Events.

Herausgeloest aus app.py beim Refactoring 2026-03-17.
"""

from datetime import datetime, date, timedelta
from flask import render_template
from flask_login import current_user
from sqlalchemy import func

from src.models import db
from src.models.models import Order, Customer, Article, Thread

import logging
logger = logging.getLogger(__name__)


def dashboard():
    """Dashboard Hauptseite mit personalisierten Modulen.
    Wird aus app.py aufgerufen (@app.route('/dashboard')).
    """
    from src.utils.permissions import get_user_dashboard_modules

    # Module laden
    try:
        user_modules = get_user_dashboard_modules(current_user)
    except Exception as e:
        logger.error(f"Dashboard Module konnten nicht geladen werden: {e}")
        user_modules = []

    stats = _build_stats()
    recent_events = _build_recent_events()
    my_todos = _build_todos()

    return render_template('dashboard_personalized.html',
                         user_modules=user_modules,
                         stats=stats,
                         recent_events=recent_events,
                         my_todos=my_todos)


def _build_stats():
    """Sammelt alle Dashboard-Statistiken"""
    stats = {
        'open_orders': Order.query.filter(
            Order.status.in_(['pending', 'approved', 'in_progress'])
        ).count(),
        'in_production': Order.query.filter_by(status='in_progress').count(),
        'ready_pickup': Order.query.filter_by(status='ready_for_pickup').count(),
        'today_revenue': 0,
        'total_customers': Customer.query.count(),
        'open_leads': 0,
        'document_count': 0,
        'open_post': 0,
        'unread_emails': 0,
        'open_invoices': 0,
        'overdue_payments': 0,
        'today_transactions': 0,
        'user_count': 0,
        'article_count': Article.query.count(),
        'thread_count': Thread.query.count(),
        'low_stock': 0,
        'design_count': 0,
        'dst_count': 0,
        'pending_supplier_orders': 0,
        'items_to_order': 0,
    }

    # Einkauf
    try:
        from src.models.models import SupplierOrder, OrderItem
        stats['pending_supplier_orders'] = SupplierOrder.query.filter(
            SupplierOrder.status.in_(['draft', 'ordered'])
        ).count()
        stats['items_to_order'] = OrderItem.query.filter(
            OrderItem.supplier_order_status.in_(['none', 'to_order'])
        ).join(Article).filter(OrderItem.quantity > Article.stock).count()
    except Exception:
        pass

    # Tagesumsatz (Kasse)
    try:
        from src.models.rechnungsmodul.models import KassenBeleg
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        today_sum = db.session.query(func.sum(KassenBeleg.brutto_gesamt)).filter(
            KassenBeleg.erstellt_am.between(today_start, today_end),
            KassenBeleg.storniert == False
        ).scalar()
        stats['today_revenue'] = round(float(today_sum or 0), 2)
        stats['today_transactions'] = KassenBeleg.query.filter(
            KassenBeleg.erstellt_am.between(today_start, today_end),
            KassenBeleg.storniert == False
        ).count()
    except Exception:
        pass

    # Dokumente
    try:
        from src.models.document import Document, PostEntry, ArchivedEmail
        stats['document_count'] = Document.query.filter_by(is_latest_version=True).count()
        stats['open_post'] = PostEntry.query.filter_by(status='open').count()
        stats['unread_emails'] = ArchivedEmail.query.filter_by(is_read=False).count()
    except Exception:
        pass

    # Website / Anfragen
    try:
        from src.models.inquiry import Inquiry
        stats['new_inquiries'] = Inquiry.query.filter_by(status='neu').count()
        stats['total_inquiries_open'] = Inquiry.query.filter(
            Inquiry.status.in_(['neu', 'in_bearbeitung'])
        ).count()
    except Exception:
        pass

    try:
        stats['shop_orders'] = Order.query.filter_by(source='shop').count()
    except Exception:
        pass

    # Versand
    try:
        from src.models.models import Shipment
        stats['ready_to_ship'] = Order.query.filter_by(status='ready').count()
        stats['shipped_today'] = Shipment.query.filter(
            Shipment.created_at >= datetime.combine(date.today(), datetime.min.time())
        ).count()
    except Exception:
        pass

    # Rechnungen
    try:
        from src.models.rechnungsmodul.models import Rechnung, RechnungsStatus
        stats['open_invoices'] = Rechnung.query.filter(
            Rechnung.status.in_([RechnungsStatus.ENTWURF, RechnungsStatus.OFFEN, RechnungsStatus.UEBERFAELLIG])
        ).count()
    except Exception:
        pass

    # Angebote
    try:
        from src.models.angebot import Angebot, AngebotStatus
        stats['open_angebote'] = Angebot.query.filter(
            Angebot.status.in_([AngebotStatus.ENTWURF, AngebotStatus.VERSCHICKT])
        ).count()
    except Exception:
        pass

    # Aufgaben
    try:
        from src.models.todo import Todo
        stats['open_tasks'] = Todo.query.filter(
            Todo.status.notin_(['completed', 'cancelled'])
        ).count()
        stats['overdue_tasks'] = Todo.query.filter(
            Todo.status.notin_(['completed', 'cancelled']),
            Todo.due_date.isnot(None),
            Todo.due_date < date.today()
        ).count()
        open_orders_count = Order.query.filter(
            Order.workflow_status.notin_(['completed', 'cancelled', None]),
            Order.archived_at.is_(None),
            Order.status != 'cancelled'
        ).count()
        stats['open_tasks'] += open_orders_count + stats.get('new_inquiries', 0)
    except Exception:
        pass

    return stats


def _build_recent_events():
    """Sammelt aktuelle Ereignisse fuer das Dashboard"""
    events = []

    # Neueste Auftraege
    try:
        recent_orders = Order.query.filter(
            Order.archived_at.is_(None),
            Order.status != 'cancelled',
            db.or_(
                Order.workflow_status == None,
                Order.workflow_status.notin_(['completed', 'invoiced', 'cancelled'])
            )
        ).order_by(Order.created_at.desc()).limit(5).all()

        for o in recent_orders:
            cname = ''
            if o.customer:
                cname = o.customer.company_name or f'{o.customer.first_name or ""} {o.customer.last_name or ""}'.strip()
            events.append({
                'type': 'order', 'icon': 'bi-bag', 'color': 'success',
                'title': f'Auftrag {o.order_number}',
                'subtitle': cname,
                'status': o.get_workflow_status_display() if hasattr(o, 'get_workflow_status_display') else (o.workflow_status or 'Neu'),
                'url': f'/orders/{o.id}',
                'date': o.created_at,
            })
    except Exception:
        pass

    # Neue Anfragen
    try:
        from src.models.inquiry import Inquiry
        recent_inqs = Inquiry.query.filter(
            Inquiry.status.in_(['neu', 'in_bearbeitung'])
        ).order_by(Inquiry.created_at.desc()).limit(5).all()
        for inq in recent_inqs:
            events.append({
                'type': 'inquiry', 'icon': 'bi-envelope-paper', 'color': 'warning',
                'title': f'Anfrage {inq.inquiry_number}',
                'subtitle': inq.full_name,
                'status': inq.status_label,
                'url': f'/admin/anfragen/{inq.id}',
                'date': inq.created_at,
            })
    except Exception:
        pass

    # Ueberfaellige Rechnungen
    try:
        from src.models.rechnungsmodul.models import Rechnung, RechnungsStatus, RechnungsRichtung
        overdue = Rechnung.query.filter(
            Rechnung.status.in_([RechnungsStatus.OFFEN, RechnungsStatus.UEBERFAELLIG]),
            Rechnung.richtung == RechnungsRichtung.AUSGANG,
            Rechnung.faelligkeitsdatum < date.today()
        ).order_by(Rechnung.faelligkeitsdatum.asc()).limit(5).all()
        for r in overdue:
            events.append({
                'type': 'invoice', 'icon': 'bi-receipt', 'color': 'danger',
                'title': f'Rechnung {r.rechnungsnummer}',
                'subtitle': f'{r.kunde_name or ""} - {float(r.brutto_gesamt or 0):.2f} EUR',
                'status': 'Ueberfaellig',
                'url': f'/rechnung/{r.id}',
                'date': r.faelligkeitsdatum,
            })
    except Exception:
        pass

    # Sortieren (datetime/date vereinheitlichen)
    def _sort_key(e):
        d = e.get('date')
        if d is None:
            return datetime.min
        if isinstance(d, date) and not isinstance(d, datetime):
            return datetime.combine(d, datetime.min.time())
        return d

    events.sort(key=_sort_key, reverse=True)
    return events[:10]


def _build_todos():
    """Laedt offene Todos fuer das Dashboard"""
    try:
        from src.models.todo import Todo
        return Todo.query.filter(
            Todo.status.notin_(['completed', 'cancelled'])
        ).order_by(Todo.due_date.asc().nullslast(), Todo.priority.desc()).limit(5).all()
    except Exception:
        return []
