# -*- coding: utf-8 -*-
"""
Task-Board Controller - Zentrales Aufgaben-Board
=================================================
Aggregiert Aufgaben, Anfragen, Auftraege und Design-Freigaben
in einer zentralen Uebersicht (Kanban + Liste).

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import logging
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from sqlalchemy.orm import joinedload
from src.models.models import db, Order, User, SupplierOrder, Supplier
from src.models.todo import Todo
from src.models.inquiry import Inquiry, INQUIRY_TYPE_LABELS

logger = logging.getLogger(__name__)

taskboard_bp = Blueprint('taskboard', __name__, url_prefix='/tasks')


# ═══════════════════════════════════════════════════════════════
# HAUPTANSICHT
# ═══════════════════════════════════════════════════════════════

@taskboard_bp.route('/')
@login_required
def index():
    """Task-Board Hauptansicht (Kanban + Liste)"""
    users = User.query.filter_by(is_active=True).order_by(User.username).all()
    return render_template('tasks/board.html', users=users)


# ═══════════════════════════════════════════════════════════════
# API: ALLE AUFGABEN LADEN
# ═══════════════════════════════════════════════════════════════

@taskboard_bp.route('/api/all')
@login_required
def api_all():
    """JSON: Alle offenen Aufgaben + aggregierte Items aus allen Quellen"""
    tasks = []
    today = date.today()

    # --- 1. Manuelle Aufgaben (Todo) ---
    try:
        from sqlalchemy import or_
        todos = Todo.query.filter(
            Todo.status.notin_(['completed', 'cancelled']),
            or_(
                Todo.is_private != True,  # Öffentliche Aufgaben
                Todo.created_by == current_user.username,  # Eigene private
                Todo.assigned_to == current_user.username,  # Mir zugewiesene
                Todo.is_private.is_(None)  # Alte Aufgaben ohne Feld
            )
        ).order_by(Todo.due_date.asc().nullslast(), Todo.priority.desc()).limit(200).all()

        for t in todos:
            source_url = None
            if t.order_id:
                source_url = f'/orders/{t.order_id}'
            elif t.customer_id:
                source_url = f'/customers/{t.customer_id}'

            tasks.append({
                'id': f'todo_{t.id}',
                'type': 'task',
                'title': t.title,
                'description': t.description or '',
                'status': _map_todo_status(t.status),
                'priority': t.priority or 'normal',
                'assigned_to': t.assigned_to or '',
                'due_date': t.due_date.isoformat() if t.due_date else None,
                'customer_name': _get_customer_name_for_todo(t),
                'source_url': source_url,
                'created_at': t.created_at.isoformat() if t.created_at else None,
                'type_icon': 'bi-check2-square',
                'type_color': 'primary',
                'type_label': t.type_display,
                'category': t.category or '',
                'is_overdue': t.is_overdue,
                'is_private': bool(t.is_private),
                'created_by': t.created_by or '',
            })
    except Exception as e:
        logger.error(f"Fehler beim Laden der Aufgaben: {e}")

    # --- 2. Offene Anfragen ---
    try:
        inquiries = Inquiry.query.filter(
            Inquiry.status.in_(['neu', 'in_bearbeitung'])
        ).order_by(Inquiry.created_at.desc()).limit(200).all()

        for inq in inquiries:
            status = 'open'
            if inq.status == 'in_bearbeitung':
                status = 'in_progress'
            elif inq.status in ('angebot_erstellt', 'angebot_versendet'):
                status = 'waiting'

            tasks.append({
                'id': f'inq_{inq.id}',
                'type': 'inquiry',
                'title': f'Anfrage {inq.inquiry_number}',
                'description': f'{INQUIRY_TYPE_LABELS.get(inq.inquiry_type, inq.inquiry_type)}: {(inq.description or "")[:100]}',
                'status': status,
                'priority': 'high' if inq.status == 'neu' else 'normal',
                'assigned_to': inq.assigned_to or '',
                'due_date': inq.desired_date.isoformat() if inq.desired_date else None,
                'customer_name': inq.full_name,
                'source_url': f'/inquiry-admin/{inq.id}',
                'created_at': inq.created_at.isoformat() if inq.created_at else None,
                'type_icon': 'bi-envelope-paper',
                'type_color': 'warning',
                'type_label': 'Anfrage',
                'category': INQUIRY_TYPE_LABELS.get(inq.inquiry_type, ''),
                'is_overdue': (datetime.now() - inq.created_at).days > 14 if inq.created_at else False,
            })
    except Exception as e:
        logger.error(f"Fehler beim Laden der Anfragen: {e}")

    # --- 3. Offene Auftraege ---
    try:
        orders = Order.query.options(
            joinedload(Order.customer)
        ).filter(
            Order.workflow_status.notin_(['completed', 'cancelled', None]),
            Order.archived_at.is_(None),
            Order.status != 'cancelled'
        ).order_by(Order.due_date.asc().nullslast(), Order.created_at.desc()).limit(200).all()

        for o in orders:
            status = _map_order_status(o.workflow_status)
            priority = 'normal'
            is_overdue = False

            if o.due_date:
                due_dt = o.due_date if isinstance(o.due_date, date) else o.due_date.date()
                if due_dt < today:
                    is_overdue = True
                    priority = 'urgent'
                elif due_dt <= today + timedelta(days=2):
                    priority = 'high'

            if o.rush_order:
                priority = 'urgent'

            customer_name = ''
            if o.customer:
                if o.customer.company_name:
                    customer_name = o.customer.company_name
                else:
                    customer_name = f'{o.customer.first_name or ""} {o.customer.last_name or ""}'.strip()

            tasks.append({
                'id': f'ord_{o.id}',
                'type': 'order',
                'title': f'Auftrag {o.order_number}',
                'description': (o.description or '')[:100],
                'status': status,
                'priority': priority,
                'assigned_to': o.created_by or '',
                'due_date': o.due_date.isoformat() if o.due_date else None,
                'customer_name': customer_name,
                'source_url': f'/orders/{o.id}',
                'created_at': o.created_at.isoformat() if o.created_at else None,
                'type_icon': 'bi-bag',
                'type_color': 'success',
                'type_label': o.get_workflow_status_display(),
                'category': o.workflow_status or '',
                'is_overdue': is_overdue,
            })
    except Exception as e:
        logger.error(f"Fehler beim Laden der Auftraege: {e}")

    # --- 4. Wartende Design-Freigaben ---
    try:
        approvals = Order.query.options(
            joinedload(Order.customer)
        ).filter(
            Order.design_approval_status.in_(['pending', 'sent']),
            Order.archived_at.is_(None)
        ).order_by(Order.design_approval_sent_at.desc().nullslast()).limit(100).all()

        for o in approvals:
            # Nur hinzufuegen wenn nicht schon als Auftrag enthalten
            ord_id = f'ord_{o.id}'
            if any(t['id'] == ord_id for t in tasks):
                continue

            customer_name = ''
            if o.customer:
                if o.customer.company_name:
                    customer_name = o.customer.company_name
                else:
                    customer_name = f'{o.customer.first_name or ""} {o.customer.last_name or ""}'.strip()

            tasks.append({
                'id': f'appr_{o.id}',
                'type': 'approval',
                'title': f'Freigabe {o.order_number}',
                'description': f'Design-Freigabe wartet auf Kundenrueckmeldung',
                'status': 'waiting',
                'priority': 'high',
                'assigned_to': '',
                'due_date': None,
                'customer_name': customer_name,
                'source_url': f'/orders/{o.id}',
                'created_at': o.design_approval_sent_at.isoformat() if o.design_approval_sent_at else None,
                'type_icon': 'bi-palette',
                'type_color': 'info',
                'type_label': 'Design-Freigabe',
                'category': 'Design',
                'is_overdue': False,
            })
    except Exception as e:
        logger.error(f"Fehler beim Laden der Design-Freigaben: {e}")

    # --- 5. CRM-Kontakte (offene Telefonate, Termine, Wiedervorlagen) ---
    try:
        from src.models.crm_contact import CustomerContact, ContactType, ContactStatus
        crm_items = CustomerContact.query.options(
            joinedload(CustomerContact.customer)
        ).filter(
            CustomerContact.status.in_([ContactStatus.OFFEN, ContactStatus.GEPLANT, ContactStatus.WARTE_ANTWORT])
        ).order_by(CustomerContact.follow_up_date.asc().nullslast(), CustomerContact.contact_date.desc()).limit(200).all()

        for c in crm_items:
            status = 'open'
            if c.status == ContactStatus.WARTE_ANTWORT:
                status = 'waiting'
            elif c.status == ContactStatus.GEPLANT:
                status = 'open'

            due = None
            is_overdue = False
            if c.follow_up_date:
                due = c.follow_up_date.date() if hasattr(c.follow_up_date, 'date') else c.follow_up_date
                due_str = due.isoformat()
                is_overdue = due < today
            elif c.callback_date:
                due = c.callback_date.date() if hasattr(c.callback_date, 'date') else c.callback_date
                due_str = due.isoformat()
                is_overdue = due < today
            else:
                due_str = None

            customer_name = ''
            if c.customer:
                if c.customer.company_name:
                    customer_name = c.customer.company_name
                else:
                    customer_name = f'{c.customer.first_name or ""} {c.customer.last_name or ""}'.strip()

            tasks.append({
                'id': f'crm_{c.id}',
                'type': 'crm',
                'title': c.subject or c.type_label,
                'description': (c.body_text or '')[:100],
                'status': status,
                'priority': 'high' if is_overdue else ('high' if c.callback_required else 'normal'),
                'assigned_to': c.created_by or '',
                'due_date': due_str,
                'customer_name': customer_name,
                'source_url': f'/crm/contact/{c.id}' if c.customer_id else '#',
                'created_at': c.created_at.isoformat() if c.created_at else None,
                'type_icon': c.type_icon,
                'type_color': 'danger',
                'type_label': c.type_label,
                'category': 'CRM',
                'is_overdue': is_overdue,
            })
    except Exception as e:
        logger.error(f"Fehler beim Laden der CRM-Kontakte: {e}")

    # --- 6. Ueberfaellige / offene Rechnungen ---
    try:
        from src.models.rechnungsmodul.models import Rechnung, RechnungsStatus, RechnungsRichtung
        offene_rechnungen = Rechnung.query.filter(
            Rechnung.status.in_([RechnungsStatus.OFFEN, RechnungsStatus.TEILBEZAHLT, RechnungsStatus.UEBERFAELLIG]),
            Rechnung.richtung == RechnungsRichtung.AUSGANG
        ).order_by(Rechnung.faelligkeitsdatum.asc().nullslast()).limit(200).all()

        for r in offene_rechnungen:
            is_overdue = False
            due_str = None
            if r.faelligkeitsdatum:
                due_str = r.faelligkeitsdatum.isoformat()
                is_overdue = r.faelligkeitsdatum < today

            priority = 'normal'
            if is_overdue:
                priority = 'urgent'
            elif r.faelligkeitsdatum and r.faelligkeitsdatum <= today + timedelta(days=3):
                priority = 'high'

            status = 'waiting'
            if is_overdue:
                status = 'open'  # Ueberfaellig = braucht Aktion

            tasks.append({
                'id': f'inv_{r.id}',
                'type': 'invoice',
                'title': f'Rechnung {r.rechnungsnummer}',
                'description': f'{r.kunde_name or ""} - {float(r.brutto_gesamt or 0):.2f} EUR',
                'status': status,
                'priority': priority,
                'assigned_to': '',
                'due_date': due_str,
                'customer_name': r.kunde_name or '',
                'source_url': f'/rechnungen/{r.id}',
                'created_at': r.rechnungsdatum.isoformat() if r.rechnungsdatum else None,
                'type_icon': 'bi-receipt',
                'type_color': 'danger' if is_overdue else 'secondary',
                'type_label': 'Ueberfaellig' if is_overdue else 'Offene Rechnung',
                'category': 'Buchhaltung',
                'is_overdue': is_overdue,
            })
    except Exception as e:
        logger.error(f"Fehler beim Laden der Rechnungen: {e}")

    # --- 7. Offene Lieferantenbestellungen ---
    try:
        offene_bestellungen = SupplierOrder.query.filter(
            SupplierOrder.status.in_(['draft', 'ordered', 'confirmed', 'shipped'])
        ).order_by(SupplierOrder.delivery_date.asc().nullslast(), SupplierOrder.order_date.desc()).limit(200).all()

        # Supplier-Map vorab laden (vermeidet N+1)
        supplier_ids = {so.supplier_id for so in offene_bestellungen if so.supplier_id}
        supplier_map = {}
        if supplier_ids:
            suppliers = Supplier.query.filter(Supplier.id.in_(supplier_ids)).all()
            supplier_map = {s.id: s.name or '' for s in suppliers}

        for so in offene_bestellungen:
            status = 'open'
            if so.status == 'ordered':
                status = 'waiting'
            elif so.status == 'confirmed':
                status = 'waiting'
            elif so.status == 'shipped':
                status = 'in_progress'

            is_overdue = False
            priority = 'normal'
            due_str = None
            if so.delivery_date:
                due_str = so.delivery_date.isoformat()
                if so.delivery_date < today:
                    is_overdue = True
                    priority = 'urgent'
                elif so.delivery_date <= today + timedelta(days=2):
                    priority = 'high'

            supplier_name = supplier_map.get(so.supplier_id, '')

            status_labels = {
                'draft': 'Entwurf',
                'ordered': 'Bestellt',
                'confirmed': 'Bestaetigt',
                'shipped': 'In Zulauf',
            }

            tasks.append({
                'id': f'po_{so.id}',
                'type': 'purchase',
                'title': f'Bestellung {so.order_number or so.id}',
                'description': f'{supplier_name} - {float(so.total_amount or 0):.2f} EUR',
                'status': status,
                'priority': priority,
                'assigned_to': '',
                'due_date': due_str,
                'customer_name': supplier_name,
                'source_url': f'/purchasing/orders/{so.id}',
                'created_at': so.order_date.isoformat() if so.order_date else None,
                'type_icon': 'bi-truck',
                'type_color': 'purple',
                'type_label': status_labels.get(so.status, so.status),
                'category': 'Einkauf',
                'is_overdue': is_overdue,
            })
    except Exception as e:
        logger.error(f"Fehler beim Laden der Lieferantenbestellungen: {e}")

    # --- Statistiken ---
    stats = _calc_stats(tasks, today)

    return jsonify({'tasks': tasks, 'stats': stats})


# ═══════════════════════════════════════════════════════════════
# API: AUFGABE ERSTELLEN
# ═══════════════════════════════════════════════════════════════

@taskboard_bp.route('/api/create', methods=['POST'])
@login_required
def api_create():
    """Neue manuelle Aufgabe erstellen"""
    try:
        title = request.form.get('title', '').strip()
        if not title:
            return jsonify({'success': False, 'error': 'Titel ist erforderlich'})

        todo = Todo(
            title=title,
            description=request.form.get('description', '').strip(),
            todo_type=request.form.get('todo_type', 'general'),
            priority=request.form.get('priority', 'normal'),
            assigned_to=request.form.get('assigned_to', '').strip() or None,
            created_by=current_user.username,
            status='open',
            is_private=request.form.get('is_private', 'true') != 'false',
        )

        due_date_str = request.form.get('due_date', '').strip()
        if due_date_str:
            try:
                todo.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        order_id = request.form.get('order_id', '').strip()
        if order_id:
            todo.order_id = order_id

        customer_id = request.form.get('customer_id', '').strip()
        if customer_id:
            todo.customer_id = customer_id

        db.session.add(todo)
        db.session.commit()

        return jsonify({'success': True, 'id': todo.id})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Aufgabe erstellen fehlgeschlagen: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ═══════════════════════════════════════════════════════════════
# API: AUFGABE AKTUALISIEREN
# ═══════════════════════════════════════════════════════════════

@taskboard_bp.route('/api/<int:todo_id>/update', methods=['POST'])
@login_required
def api_update(todo_id):
    """Aufgabe aktualisieren (Status, Zuweisung, etc.)"""
    try:
        todo = Todo.query.get(todo_id)
        if not todo:
            return jsonify({'success': False, 'error': 'Aufgabe nicht gefunden'})

        if 'status' in request.form:
            new_status = request.form['status']
            if new_status == 'completed':
                todo.complete(current_user.username)
            else:
                todo.status = new_status

        if 'priority' in request.form:
            todo.priority = request.form['priority']

        if 'assigned_to' in request.form:
            todo.assigned_to = request.form['assigned_to'] or None

        if 'title' in request.form:
            todo.title = request.form['title']

        if 'description' in request.form:
            todo.description = request.form['description']

        if 'due_date' in request.form:
            due_str = request.form['due_date'].strip()
            if due_str:
                try:
                    todo.due_date = datetime.strptime(due_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            else:
                todo.due_date = None

        if 'is_private' in request.form:
            todo.is_private = request.form['is_private'] != 'false'

        todo.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Aufgabe aktualisieren fehlgeschlagen: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ═══════════════════════════════════════════════════════════════
# API: KOMMENTAR HINZUFUEGEN
# ═══════════════════════════════════════════════════════════════

@taskboard_bp.route('/api/<int:todo_id>/comment', methods=['POST'])
@login_required
def api_comment(todo_id):
    """Kommentar zu Aufgabe hinzufuegen"""
    try:
        todo = Todo.query.get(todo_id)
        if not todo:
            return jsonify({'success': False, 'error': 'Aufgabe nicht gefunden'})

        text = request.form.get('text', '').strip()
        if not text:
            return jsonify({'success': False, 'error': 'Kommentar darf nicht leer sein'})

        todo.add_comment(current_user.username, text)
        todo.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Kommentar fehlgeschlagen: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ═══════════════════════════════════════════════════════════════
# API: AUFGABE LOESCHEN
# ═══════════════════════════════════════════════════════════════

@taskboard_bp.route('/api/<int:todo_id>/delete', methods=['POST'])
@login_required
def api_delete(todo_id):
    """Aufgabe loeschen"""
    try:
        todo = Todo.query.get(todo_id)
        if not todo:
            return jsonify({'success': False, 'error': 'Aufgabe nicht gefunden'})

        db.session.delete(todo)
        db.session.commit()

        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Aufgabe loeschen fehlgeschlagen: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ═══════════════════════════════════════════════════════════════
# HILFSFUNKTIONEN
# ═══════════════════════════════════════════════════════════════

def _map_todo_status(status):
    """Mappt Todo-Status auf Board-Status"""
    mapping = {
        'open': 'open',
        'in_progress': 'in_progress',
        'waiting': 'waiting',
        'completed': 'completed',
        'cancelled': 'completed',
    }
    return mapping.get(status, 'open')


def _map_order_status(workflow_status):
    """Mappt Order workflow_status auf Board-Status"""
    mapping = {
        'offer': 'open',
        'confirmed': 'open',
        'design_pending': 'waiting',
        'design_approved': 'in_progress',
        'in_production': 'in_progress',
        'packing': 'in_progress',
        'ready_to_ship': 'in_progress',
        'shipped': 'waiting',
        'invoiced': 'waiting',
        'completed': 'completed',
    }
    return mapping.get(workflow_status, 'open')


def _get_customer_name_for_todo(todo):
    """Holt Kundenname fuer eine Todo-Aufgabe"""
    if todo.customer:
        if todo.customer.company_name:
            return todo.customer.company_name
        return f'{todo.customer.first_name or ""} {todo.customer.last_name or ""}'.strip()
    if todo.order and todo.order.customer:
        c = todo.order.customer
        if c.company_name:
            return c.company_name
        return f'{c.first_name or ""} {c.last_name or ""}'.strip()
    return ''


def _calc_stats(tasks, today):
    """Berechnet Statistiken fuer das Board"""
    total_open = len([t for t in tasks if t['status'] != 'completed'])
    overdue = len([t for t in tasks if t.get('is_overdue')])
    due_today = len([t for t in tasks if t.get('due_date') and t['due_date'] == today.isoformat()])
    unassigned = len([t for t in tasks if not t.get('assigned_to') and t['status'] != 'completed'])

    by_type = {}
    for t in tasks:
        if t['status'] != 'completed':
            tp = t['type']
            by_type[tp] = by_type.get(tp, 0) + 1

    return {
        'total_open': total_open,
        'overdue': overdue,
        'due_today': due_today,
        'unassigned': unassigned,
        'by_type': by_type,
    }
