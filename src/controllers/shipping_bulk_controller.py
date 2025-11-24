# -*- coding: utf-8 -*-
"""
Shipping Bulk Controller - Massen-Versand-Verwaltung
StitchAdmin 2.0
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from src.models.models import db, Customer, Order
from src.models.document import ShippingBulk, PostEntry
from datetime import datetime, date
import csv
import io
import os

shipping_bulk_bp = Blueprint('shipping_bulk', __name__, url_prefix='/shipping/bulk')


@shipping_bulk_bp.route('/')
@login_required
def index():
    """Liste aller Shipping Bulks"""
    # Filter
    status = request.args.get('status', '')
    carrier = request.args.get('carrier', '')

    query = ShippingBulk.query

    if status:
        query = query.filter_by(status=status)

    if carrier:
        query = query.filter_by(carrier=carrier)

    bulks = query.order_by(ShippingBulk.created_at.desc()).all()

    # Statistiken
    stats = {
        'total': ShippingBulk.query.count(),
        'draft': ShippingBulk.query.filter_by(status='draft').count(),
        'ready': ShippingBulk.query.filter_by(status='ready').count(),
        'shipped': ShippingBulk.query.filter_by(status='shipped').count(),
    }

    return render_template('shipping/bulk_list.html', bulks=bulks, stats=stats)


@shipping_bulk_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Neuer Shipping Bulk"""
    if request.method == 'POST':
        try:
            bulk = ShippingBulk(
                bulk_number=ShippingBulk.generate_bulk_number(),
                name=request.form.get('name'),
                carrier=request.form.get('carrier'),
                planned_ship_date=datetime.strptime(request.form.get('planned_ship_date'), '%Y-%m-%d').date() if request.form.get('planned_ship_date') else None,
                notes=request.form.get('notes'),
                created_by=current_user.id
            )

            db.session.add(bulk)
            db.session.commit()

            flash(f'Shipping Bulk "{bulk.bulk_number}" erstellt', 'success')
            return redirect(url_for('shipping_bulk.view', bulk_id=bulk.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {str(e)}', 'error')

    return render_template('shipping/bulk_form.html')


@shipping_bulk_bp.route('/<int:bulk_id>')
@login_required
def view(bulk_id):
    """Shipping Bulk Details"""
    bulk = ShippingBulk.query.get_or_404(bulk_id)

    # Hole zugehörige PostEntries
    entries = PostEntry.query.filter_by(
        shipping_bulk_id=bulk_id,
        direction='outbound'
    ).all()

    # Aktualisiere Statistiken
    bulk.total_items = len(entries)
    bulk.total_cost = sum(e.shipping_cost or 0 for e in entries)
    db.session.commit()

    return render_template('shipping/bulk_view.html', bulk=bulk, entries=entries)


@shipping_bulk_bp.route('/<int:bulk_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(bulk_id):
    """Shipping Bulk bearbeiten"""
    bulk = ShippingBulk.query.get_or_404(bulk_id)

    if request.method == 'POST':
        try:
            bulk.name = request.form.get('name')
            bulk.carrier = request.form.get('carrier')
            bulk.planned_ship_date = datetime.strptime(request.form.get('planned_ship_date'), '%Y-%m-%d').date() if request.form.get('planned_ship_date') else None
            bulk.notes = request.form.get('notes')

            db.session.commit()
            flash('Shipping Bulk aktualisiert', 'success')
            return redirect(url_for('shipping_bulk.view', bulk_id=bulk.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {str(e)}', 'error')

    return render_template('shipping/bulk_form.html', bulk=bulk)


@shipping_bulk_bp.route('/<int:bulk_id>/add_entries', methods=['POST'])
@login_required
def add_entries(bulk_id):
    """Fügt ausgewählte PostEntries zum Bulk hinzu"""
    bulk = ShippingBulk.query.get_or_404(bulk_id)

    entry_ids = request.form.getlist('entry_ids')

    if not entry_ids:
        flash('Keine Einträge ausgewählt', 'warning')
        return redirect(url_for('shipping_bulk.view', bulk_id=bulk_id))

    try:
        count = 0
        for entry_id in entry_ids:
            entry = PostEntry.query.get(int(entry_id))
            if entry and entry.direction == 'outbound' and not entry.shipping_bulk_id:
                entry.shipping_bulk_id = bulk_id
                count += 1

        db.session.commit()
        flash(f'{count} Einträge zum Bulk hinzugefügt', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'error')

    return redirect(url_for('shipping_bulk.view', bulk_id=bulk_id))


@shipping_bulk_bp.route('/<int:bulk_id>/remove_entry/<int:entry_id>', methods=['POST'])
@login_required
def remove_entry(bulk_id, entry_id):
    """Entfernt PostEntry aus Bulk"""
    entry = PostEntry.query.get_or_404(entry_id)

    if entry.shipping_bulk_id == bulk_id:
        entry.shipping_bulk_id = None
        db.session.commit()
        flash('Eintrag aus Bulk entfernt', 'success')
    else:
        flash('Eintrag gehört nicht zu diesem Bulk', 'error')

    return redirect(url_for('shipping_bulk.view', bulk_id=bulk_id))


@shipping_bulk_bp.route('/<int:bulk_id>/export_csv')
@login_required
def export_csv(bulk_id):
    """Exportiert Bulk als CSV für DPD/DHL"""
    bulk = ShippingBulk.query.get_or_404(bulk_id)
    entries = PostEntry.query.filter_by(shipping_bulk_id=bulk_id).all()

    if not entries:
        flash('Keine Einträge zum Exportieren', 'warning')
        return redirect(url_for('shipping_bulk.view', bulk_id=bulk_id))

    # CSV erstellen
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')

    # Header (DPD/DHL Standard)
    writer.writerow([
        'Empfänger Name',
        'Straße',
        'PLZ',
        'Ort',
        'Land',
        'Telefon',
        'E-Mail',
        'Gewicht (kg)',
        'Referenz',
        'Inhalt'
    ])

    # Daten
    for entry in entries:
        # Parse Adresse (einfache Variante)
        address_lines = (entry.recipient_address or '').split('\n')
        street = address_lines[0] if len(address_lines) > 0 else ''
        plz_ort = address_lines[1] if len(address_lines) > 1 else ''
        plz = plz_ort.split()[0] if plz_ort else ''
        ort = ' '.join(plz_ort.split()[1:]) if plz_ort else ''

        writer.writerow([
            entry.recipient or '',
            street,
            plz,
            ort,
            'DE',  # Default Deutschland
            '',  # Telefon (nicht in PostEntry)
            '',  # E-Mail (nicht in PostEntry)
            '',  # Gewicht (optional)
            entry.reference_number or entry.entry_number,
            entry.subject
        ])

    # Als Datei zurückgeben
    output.seek(0)
    filename = f'{bulk.bulk_number}_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

    # Markiere als exportiert
    bulk.csv_exported = True
    bulk.csv_export_date = datetime.utcnow()
    db.session.commit()

    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),  # BOM für Excel
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


@shipping_bulk_bp.route('/<int:bulk_id>/mark_printed', methods=['POST'])
@login_required
def mark_printed(bulk_id):
    """Markiert Bulk als gedruckt und fragt nach Sendungsnummern"""
    bulk = ShippingBulk.query.get_or_404(bulk_id)

    bulk.labels_printed = True
    bulk.labels_print_date = datetime.utcnow()
    bulk.status = 'printed'

    # Markiere alle Einträge als gedruckt
    entries = PostEntry.query.filter_by(shipping_bulk_id=bulk_id).all()
    for entry in entries:
        entry.printed_at = datetime.utcnow()

    db.session.commit()

    flash(f'Bulk als gedruckt markiert ({len(entries)} Etiketten)', 'success')
    return redirect(url_for('shipping_bulk.enter_tracking', bulk_id=bulk_id))


@shipping_bulk_bp.route('/<int:bulk_id>/enter_tracking', methods=['GET', 'POST'])
@login_required
def enter_tracking(bulk_id):
    """Sendungsnummern erfassen"""
    bulk = ShippingBulk.query.get_or_404(bulk_id)
    entries = PostEntry.query.filter_by(shipping_bulk_id=bulk_id).all()

    if request.method == 'POST':
        try:
            shipped_count = 0

            for entry in entries:
                tracking_key = f'tracking_{entry.id}'
                tracking_number = request.form.get(tracking_key, '').strip()

                if tracking_number:
                    entry.tracking_number = tracking_number
                    entry.delivery_status = 'in_transit'
                    entry.shipped_at = datetime.utcnow()
                    entry.status = 'shipped'
                    shipped_count += 1

            # Update Bulk Status
            if shipped_count == len(entries):
                bulk.status = 'shipped'
                bulk.actual_ship_date = date.today()

            db.session.commit()

            flash(f'{shipped_count} Sendungsnummern erfasst', 'success')
            return redirect(url_for('shipping_bulk.view', bulk_id=bulk_id))

        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {str(e)}', 'error')

    return render_template('shipping/bulk_enter_tracking.html', bulk=bulk, entries=entries)


@shipping_bulk_bp.route('/<int:bulk_id>/ship_without_tracking', methods=['POST'])
@login_required
def ship_without_tracking(bulk_id):
    """Markiert alle als versendet ohne Sendungsnummern"""
    bulk = ShippingBulk.query.get_or_404(bulk_id)
    entries = PostEntry.query.filter_by(shipping_bulk_id=bulk_id).all()

    try:
        for entry in entries:
            entry.shipped_at = datetime.utcnow()
            entry.status = 'shipped'
            entry.delivery_status = 'pending'

        bulk.status = 'shipped'
        bulk.actual_ship_date = date.today()

        db.session.commit()

        flash(f'{len(entries)} Sendungen als versendet markiert', 'success')
        return redirect(url_for('shipping_bulk.view', bulk_id=bulk_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'error')
        return redirect(url_for('shipping_bulk.view', bulk_id=bulk_id))


@shipping_bulk_bp.route('/<int:bulk_id>/delete', methods=['POST'])
@login_required
def delete(bulk_id):
    """Löscht Shipping Bulk (entfernt nur Zuordnung, nicht die Einträge)"""
    bulk = ShippingBulk.query.get_or_404(bulk_id)

    try:
        # Entferne Bulk-Zuordnung von allen Einträgen
        entries = PostEntry.query.filter_by(shipping_bulk_id=bulk_id).all()
        for entry in entries:
            entry.shipping_bulk_id = None

        # Lösche Bulk
        db.session.delete(bulk)
        db.session.commit()

        flash('Shipping Bulk gelöscht', 'success')
        return redirect(url_for('shipping_bulk.index'))

    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'error')
        return redirect(url_for('shipping_bulk.view', bulk_id=bulk_id))
