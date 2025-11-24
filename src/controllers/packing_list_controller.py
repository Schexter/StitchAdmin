# -*- coding: utf-8 -*-
"""
Packing List Controller - Packlisten-Verwaltung
Verwaltet Packlisten für Versandvorbereitung
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
from src.models import db, PackingList, Order, Customer, ActivityLog, PostEntry, DeliveryNote
from sqlalchemy import or_
import json

# Blueprint erstellen
packing_list_bp = Blueprint('packing_lists', __name__, url_prefix='/packing_lists')

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


@packing_list_bp.route('/')
@login_required
def index():
    """Packlisten-Übersicht"""
    status_filter = request.args.get('status', '')
    search_query = request.args.get('search', '').lower()

    # Query erstellen
    query = PackingList.query

    if status_filter:
        query = query.filter_by(status=status_filter)

    if search_query:
        query = query.outerjoin(Customer).outerjoin(Order).filter(
            or_(
                PackingList.packing_list_number.ilike(f'%{search_query}%'),
                Customer.company_name.ilike(f'%{search_query}%'),
                Customer.first_name.ilike(f'%{search_query}%'),
                Customer.last_name.ilike(f'%{search_query}%'),
                Order.order_number.ilike(f'%{search_query}%')
            )
        )

    # Nach Erstellungsdatum sortieren (neueste zuerst)
    packing_lists = query.order_by(PackingList.created_at.desc()).all()

    # Gruppiere nach Status für Tabs
    lists_by_status = {
        'ready': [],
        'qc_passed': [],
        'packed': [],
        'shipped': [],
        'draft': []
    }

    for pl in packing_lists:
        if pl.status in lists_by_status:
            lists_by_status[pl.status].append(pl)

    return render_template('packing_lists/list.html',
                         packing_lists=packing_lists,
                         lists_by_status=lists_by_status,
                         status_filter=status_filter,
                         search_query=search_query)


@packing_list_bp.route('/<int:id>')
@login_required
def detail(id):
    """Packlisten-Detail-Ansicht"""
    packing_list = PackingList.query.get_or_404(id)

    # Lade Items als Liste
    items = packing_list.get_items_list()

    # Lade QC-Fotos
    qc_photos = packing_list.get_qc_photos_list()

    return render_template('packing_lists/detail.html',
                         packing_list=packing_list,
                         items=items,
                         qc_photos=qc_photos)


@packing_list_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Neue Packliste erstellen"""
    if request.method == 'POST':
        # Erstelle neue Packliste
        packing_list = PackingList(
            packing_list_number=PackingList.generate_packing_list_number(),
            order_id=request.form.get('order_id') or None,
            customer_id=request.form.get('customer_id') or None,
            status=request.form.get('status', 'ready'),
            customer_notes=request.form.get('customer_notes', ''),
            packing_notes=request.form.get('packing_notes', ''),
            created_by=current_user.id
        )

        # Carton-Informationen
        total_cartons = int(request.form.get('total_cartons', 1))
        packing_list.total_cartons = total_cartons
        packing_list.carton_number = int(request.form.get('carton_number', 1))
        packing_list.is_partial_delivery = (total_cartons > 1)

        # Gewicht & Maße
        if request.form.get('total_weight'):
            packing_list.total_weight = float(request.form.get('total_weight'))
        if request.form.get('package_length'):
            packing_list.package_length = float(request.form.get('package_length'))
        if request.form.get('package_width'):
            packing_list.package_width = float(request.form.get('package_width'))
        if request.form.get('package_height'):
            packing_list.package_height = float(request.form.get('package_height'))

        # Items aus Formular
        items_json = request.form.get('items_json', '[]')
        packing_list.items = items_json

        db.session.add(packing_list)
        db.session.commit()

        log_activity('packing_list_created',
                    f'Packliste {packing_list.packing_list_number} erstellt')

        flash(f'Packliste {packing_list.packing_list_number} wurde erstellt.', 'success')
        return redirect(url_for('packing_lists.detail', id=packing_list.id))

    # GET: Formular anzeigen
    orders = Order.query.filter_by(status='completed').all()
    customers = Customer.query.order_by(Customer.company_name).all()

    # Wenn order_id in URL, vorausfüllen
    order_id = request.args.get('order_id')
    preselected_order = None
    if order_id:
        preselected_order = Order.query.get(order_id)

    return render_template('packing_lists/form.html',
                         packing_list=None,
                         orders=orders,
                         customers=customers,
                         preselected_order=preselected_order)


@packing_list_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Packliste bearbeiten"""
    packing_list = PackingList.query.get_or_404(id)

    if request.method == 'POST':
        # Update Packliste
        packing_list.customer_notes = request.form.get('customer_notes', '')
        packing_list.packing_notes = request.form.get('packing_notes', '')

        # Carton-Informationen
        total_cartons = int(request.form.get('total_cartons', 1))
        packing_list.total_cartons = total_cartons
        packing_list.carton_number = int(request.form.get('carton_number', 1))
        packing_list.is_partial_delivery = (total_cartons > 1)

        # Gewicht & Maße
        if request.form.get('total_weight'):
            packing_list.total_weight = float(request.form.get('total_weight'))
        if request.form.get('package_length'):
            packing_list.package_length = float(request.form.get('package_length'))
        if request.form.get('package_width'):
            packing_list.package_width = float(request.form.get('package_width'))
        if request.form.get('package_height'):
            packing_list.package_height = float(request.form.get('package_height'))

        # Items aktualisieren
        items_json = request.form.get('items_json', '[]')
        packing_list.items = items_json

        packing_list.updated_at = datetime.utcnow()
        db.session.commit()

        log_activity('packing_list_updated',
                    f'Packliste {packing_list.packing_list_number} aktualisiert')

        flash(f'Packliste {packing_list.packing_list_number} wurde aktualisiert.', 'success')
        return redirect(url_for('packing_lists.detail', id=packing_list.id))

    # GET: Formular anzeigen
    orders = Order.query.filter_by(status='completed').all()
    customers = Customer.query.order_by(Customer.company_name).all()

    return render_template('packing_lists/form.html',
                         packing_list=packing_list,
                         orders=orders,
                         customers=customers)


@packing_list_bp.route('/<int:id>/qc', methods=['GET', 'POST'])
@login_required
def qc(id):
    """Qualitätskontrolle durchführen"""
    packing_list = PackingList.query.get_or_404(id)

    if request.method == 'POST':
        qc_result = request.form.get('qc_result')

        if qc_result == 'passed':
            # QC bestanden
            packing_list.qc_performed = True
            packing_list.qc_by = current_user.id
            packing_list.qc_date = datetime.utcnow()
            packing_list.qc_notes = request.form.get('qc_notes', '')
            packing_list.status = 'qc_passed'

            # Fotos speichern (wenn vorhanden)
            # TODO: Foto-Upload implementieren

            db.session.commit()

            log_activity('packing_list_qc_passed',
                        f'Packliste {packing_list.packing_list_number} - QC bestanden')

            flash(f'Qualitätskontrolle für Packliste {packing_list.packing_list_number} erfolgreich.', 'success')
        else:
            # QC nicht bestanden
            packing_list.qc_performed = True
            packing_list.qc_by = current_user.id
            packing_list.qc_date = datetime.utcnow()
            packing_list.qc_notes = request.form.get('qc_notes', '')
            packing_list.status = 'ready'  # Zurück zu "ready"

            db.session.commit()

            log_activity('packing_list_qc_failed',
                        f'Packliste {packing_list.packing_list_number} - QC nicht bestanden')

            flash(f'Qualitätskontrolle für Packliste {packing_list.packing_list_number} nicht bestanden. Status zurückgesetzt.', 'warning')

        return redirect(url_for('packing_lists.detail', id=packing_list.id))

    # GET: QC-Formular anzeigen
    items = packing_list.get_items_list()

    return render_template('packing_lists/qc.html',
                         packing_list=packing_list,
                         items=items)


@packing_list_bp.route('/<int:id>/pack', methods=['POST'])
@login_required
def pack(id):
    """Packliste als verpackt markieren"""
    packing_list = PackingList.query.get_or_404(id)

    # Prüfe ob QC erforderlich ist
    from src.models import CompanySettings
    settings = CompanySettings.get_settings()

    if settings.require_qc_before_packing and not packing_list.qc_performed:
        flash('Qualitätskontrolle muss vor dem Verpacken durchgeführt werden.', 'error')
        return redirect(url_for('packing_lists.detail', id=packing_list.id))

    # Markiere als verpackt
    packing_list.packed_by = current_user.id
    packing_list.packed_at = datetime.utcnow()
    packing_list.packed_confirmed = True
    packing_list.status = 'packed'

    # Gewicht & Maße aus Formular (falls angegeben)
    if request.form.get('total_weight'):
        packing_list.total_weight = float(request.form.get('total_weight'))
    if request.form.get('package_length'):
        packing_list.package_length = float(request.form.get('package_length'))
    if request.form.get('package_width'):
        packing_list.package_width = float(request.form.get('package_width'))
    if request.form.get('package_height'):
        packing_list.package_height = float(request.form.get('package_height'))

    db.session.commit()

    # Automatisch Lagerbuchung erstellen (wenn aktiviert)
    if settings.auto_inventory_booking and not packing_list.inventory_booked:
        # TODO: Lagerbuchung implementieren
        packing_list.inventory_booked = True
        packing_list.inventory_booking_date = datetime.utcnow()
        db.session.commit()

    # Automatisch Lieferschein erstellen (wenn aktiviert)
    if settings.auto_create_delivery_note and not packing_list.delivery_note_id:
        try:
            # Nutze workflow_helpers für konsistente Erstellung
            from src.utils.workflow_helpers import create_delivery_note_from_packing_list
            delivery_note = create_delivery_note_from_packing_list(packing_list)

            # Verknüpfe Lieferschein mit Packliste
            packing_list.delivery_note_id = delivery_note.id
            db.session.commit()

            log_activity('delivery_note_auto_created',
                        f'Lieferschein {delivery_note.delivery_note_number} automatisch erstellt')

            flash(f'Lieferschein {delivery_note.delivery_note_number} wurde automatisch erstellt.', 'info')
        except Exception as e:
            flash(f'Fehler beim Erstellen des Lieferscheins: {str(e)}', 'error')

    log_activity('packing_list_packed',
                f'Packliste {packing_list.packing_list_number} als verpackt markiert')

    flash(f'Packliste {packing_list.packing_list_number} wurde als verpackt markiert.', 'success')
    return redirect(url_for('packing_lists.detail', id=packing_list.id))


@packing_list_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    """Packliste löschen"""
    packing_list = PackingList.query.get_or_404(id)

    # Prüfe ob Packliste gelöscht werden kann
    if packing_list.status in ['packed', 'shipped']:
        flash('Verpackte oder versendete Packlisten können nicht gelöscht werden.', 'error')
        return redirect(url_for('packing_lists.detail', id=packing_list.id))

    if packing_list.delivery_note_id:
        flash('Packliste mit verknüpftem Lieferschein kann nicht gelöscht werden.', 'error')
        return redirect(url_for('packing_lists.detail', id=packing_list.id))

    packing_list_number = packing_list.packing_list_number

    db.session.delete(packing_list)
    db.session.commit()

    log_activity('packing_list_deleted',
                f'Packliste {packing_list_number} gelöscht')

    flash(f'Packliste {packing_list_number} wurde gelöscht.', 'success')
    return redirect(url_for('packing_lists.index'))


@packing_list_bp.route('/<int:id>/print')
@login_required
def print_packing_list(id):
    """Packliste als PDF drucken"""
    packing_list = PackingList.query.get_or_404(id)

    # TODO: PDF-Generierung implementieren (Tag 2)
    flash('PDF-Generierung wird in Tag 2 implementiert.', 'info')
    return redirect(url_for('packing_lists.detail', id=packing_list.id))


@packing_list_bp.route('/api/from-order/<int:order_id>')
@login_required
def api_from_order(order_id):
    """API: Hole Items für Packliste von Auftrag"""
    order = Order.query.get_or_404(order_id)

    # Erstelle Items-Liste aus Auftrag
    items = []
    if order.order_items:
        for order_item in order.order_items:
            items.append({
                'article_id': order_item.article_id,
                'name': order_item.article.name if order_item.article else 'Unbekannt',
                'quantity': order_item.quantity,
                'ean': order_item.article.ean if order_item.article else ''
            })

    return jsonify({
        'success': True,
        'items': items,
        'customer_id': order.customer_id,
        'customer_notes': order.customer_notes or ''
    })
