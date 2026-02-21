# -*- coding: utf-8 -*-
"""
Vertraege & Policen Controller
================================
CRUD fuer Vertraege, Ansprechpartner und Kommunikation.

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta

from src.models import db
from src.models.contracts import Contract, ContractContact, ContractCommunication

import logging
logger = logging.getLogger(__name__)

contracts_bp = Blueprint('contracts', __name__, url_prefix='/contracts')


# === Vertraege CRUD ===

@contracts_bp.route('/')
@login_required
def index():
    """Uebersicht aller Vertraege"""
    filter_type = request.args.get('type', '')
    filter_status = request.args.get('status', 'active')
    search = request.args.get('q', '').strip()

    query = Contract.query

    if filter_type:
        query = query.filter_by(contract_type=filter_type)
    if filter_status:
        query = query.filter_by(status=filter_status)
    if search:
        query = query.filter(
            db.or_(
                Contract.name.ilike(f'%{search}%'),
                Contract.provider_name.ilike(f'%{search}%'),
                Contract.contract_number.ilike(f'%{search}%'),
            )
        )

    contracts = query.order_by(Contract.name).all()

    # Statistiken
    stats = {
        'total': Contract.query.filter_by(status='active').count(),
        'monthly_cost': sum(c.monthly_cost for c in Contract.query.filter_by(status='active').all()),
        'expiring': Contract.query.filter(
            Contract.status == 'active',
            Contract.end_date.isnot(None),
            Contract.end_date <= date.today() + timedelta(days=30),
            Contract.end_date >= date.today(),
        ).count(),
        'renewal_due': Contract.query.filter(
            Contract.status == 'active',
            Contract.renewal_date.isnot(None),
            Contract.renewal_date <= date.today() + timedelta(days=30),
            Contract.renewal_date >= date.today(),
        ).count(),
    }

    return render_template('contracts/index.html',
                         contracts=contracts,
                         stats=stats,
                         filter_type=filter_type,
                         filter_status=filter_status,
                         search=search,
                         type_labels=Contract.TYPE_LABELS,
                         status_labels=Contract.STATUS_LABELS)


@contracts_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Neuen Vertrag erstellen"""
    if request.method == 'POST':
        try:
            contract = Contract(
                contract_type=request.form.get('contract_type', 'other'),
                name=request.form.get('name', '').strip(),
                description=request.form.get('description', '').strip() or None,
                contract_number=request.form.get('contract_number', '').strip() or None,
                provider_name=request.form.get('provider_name', '').strip() or None,
                provider_contact=request.form.get('provider_contact', '').strip() or None,
                provider_phone=request.form.get('provider_phone', '').strip() or None,
                provider_email=request.form.get('provider_email', '').strip() or None,
                provider_website=request.form.get('provider_website', '').strip() or None,
                start_date=_parse_date(request.form.get('start_date')),
                end_date=_parse_date(request.form.get('end_date')),
                renewal_date=_parse_date(request.form.get('renewal_date')),
                auto_renew=request.form.get('auto_renew') == 'on',
                notice_period_days=int(request.form.get('notice_period_days', 90) or 90),
                amount=_parse_float(request.form.get('amount')),
                payment_interval=request.form.get('payment_interval', 'monthly'),
                coverage_amount=_parse_float(request.form.get('coverage_amount')),
                deductible=_parse_float(request.form.get('deductible')),
                insurance_type=request.form.get('insurance_type', '').strip() or None,
                status=request.form.get('status', 'active'),
                notes=request.form.get('notes', '').strip() or None,
                created_by=current_user.username,
            )

            machine_id = request.form.get('machine_id')
            if machine_id:
                contract.machine_id = int(machine_id)

            db.session.add(contract)
            db.session.commit()

            flash(f'Vertrag "{contract.name}" erstellt.', 'success')
            return redirect(url_for('contracts.detail', contract_id=contract.id))

        except Exception as e:
            db.session.rollback()
            logger.error(f'Fehler beim Erstellen: {e}')
            flash(f'Fehler: {e}', 'danger')

    # Maschinen fuer Dropdown
    machines = _get_machines()

    return render_template('contracts/form.html',
                         contract=None,
                         machines=machines,
                         type_labels=Contract.TYPE_LABELS,
                         interval_labels=Contract.INTERVAL_LABELS)


@contracts_bp.route('/<int:contract_id>')
@login_required
def detail(contract_id):
    """Vertragsdetails"""
    contract = Contract.query.get_or_404(contract_id)
    contacts = contract.contacts.order_by(ContractContact.is_primary.desc(), ContractContact.name).all()
    communications = contract.communications.order_by(ContractCommunication.date.desc()).limit(20).all()

    return render_template('contracts/detail.html',
                         contract=contract,
                         contacts=contacts,
                         communications=communications)


@contracts_bp.route('/<int:contract_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(contract_id):
    """Vertrag bearbeiten"""
    contract = Contract.query.get_or_404(contract_id)

    if request.method == 'POST':
        try:
            contract.contract_type = request.form.get('contract_type', contract.contract_type)
            contract.name = request.form.get('name', '').strip()
            contract.description = request.form.get('description', '').strip() or None
            contract.contract_number = request.form.get('contract_number', '').strip() or None
            contract.provider_name = request.form.get('provider_name', '').strip() or None
            contract.provider_contact = request.form.get('provider_contact', '').strip() or None
            contract.provider_phone = request.form.get('provider_phone', '').strip() or None
            contract.provider_email = request.form.get('provider_email', '').strip() or None
            contract.provider_website = request.form.get('provider_website', '').strip() or None
            contract.start_date = _parse_date(request.form.get('start_date'))
            contract.end_date = _parse_date(request.form.get('end_date'))
            contract.renewal_date = _parse_date(request.form.get('renewal_date'))
            contract.auto_renew = request.form.get('auto_renew') == 'on'
            contract.notice_period_days = int(request.form.get('notice_period_days', 90) or 90)
            contract.amount = _parse_float(request.form.get('amount'))
            contract.payment_interval = request.form.get('payment_interval', 'monthly')
            contract.coverage_amount = _parse_float(request.form.get('coverage_amount'))
            contract.deductible = _parse_float(request.form.get('deductible'))
            contract.insurance_type = request.form.get('insurance_type', '').strip() or None
            contract.status = request.form.get('status', contract.status)
            contract.notes = request.form.get('notes', '').strip() or None

            machine_id = request.form.get('machine_id')
            contract.machine_id = int(machine_id) if machine_id else None

            db.session.commit()
            flash(f'Vertrag "{contract.name}" aktualisiert.', 'success')
            return redirect(url_for('contracts.detail', contract_id=contract.id))

        except Exception as e:
            db.session.rollback()
            logger.error(f'Fehler beim Bearbeiten: {e}')
            flash(f'Fehler: {e}', 'danger')

    machines = _get_machines()

    return render_template('contracts/form.html',
                         contract=contract,
                         machines=machines,
                         type_labels=Contract.TYPE_LABELS,
                         interval_labels=Contract.INTERVAL_LABELS)


@contracts_bp.route('/<int:contract_id>/delete', methods=['POST'])
@login_required
def delete(contract_id):
    """Vertrag loeschen"""
    contract = Contract.query.get_or_404(contract_id)
    name = contract.name
    try:
        db.session.delete(contract)
        db.session.commit()
        flash(f'Vertrag "{name}" geloescht.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {e}', 'danger')
    return redirect(url_for('contracts.index'))


# === Ansprechpartner ===

@contracts_bp.route('/<int:contract_id>/contacts/add', methods=['POST'])
@login_required
def add_contact(contract_id):
    """Ansprechpartner hinzufuegen"""
    contract = Contract.query.get_or_404(contract_id)
    try:
        contact = ContractContact(
            contract_id=contract.id,
            name=request.form.get('contact_name', '').strip(),
            position=request.form.get('contact_position', '').strip() or None,
            department=request.form.get('contact_department', '').strip() or None,
            phone=request.form.get('contact_phone', '').strip() or None,
            mobile=request.form.get('contact_mobile', '').strip() or None,
            email=request.form.get('contact_email', '').strip() or None,
            is_primary=request.form.get('contact_primary') == 'on',
            notes=request.form.get('contact_notes', '').strip() or None,
        )

        # Nur ein Primary-Kontakt
        if contact.is_primary:
            ContractContact.query.filter_by(
                contract_id=contract.id, is_primary=True
            ).update({'is_primary': False})

        db.session.add(contact)
        db.session.commit()
        flash(f'Ansprechpartner "{contact.name}" hinzugefuegt.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {e}', 'danger')

    return redirect(url_for('contracts.detail', contract_id=contract.id))


@contracts_bp.route('/contacts/<int:contact_id>/delete', methods=['POST'])
@login_required
def delete_contact(contact_id):
    """Ansprechpartner loeschen"""
    contact = ContractContact.query.get_or_404(contact_id)
    contract_id = contact.contract_id
    try:
        db.session.delete(contact)
        db.session.commit()
        flash('Ansprechpartner entfernt.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {e}', 'danger')
    return redirect(url_for('contracts.detail', contract_id=contract_id))


# === Kommunikation ===

@contracts_bp.route('/<int:contract_id>/communication/add', methods=['POST'])
@login_required
def add_communication(contract_id):
    """Kommunikation erfassen"""
    contract = Contract.query.get_or_404(contract_id)
    try:
        comm_date = _parse_datetime(request.form.get('comm_date'))

        comm = ContractCommunication(
            contract_id=contract.id,
            comm_type=request.form.get('comm_type', 'note'),
            subject=request.form.get('comm_subject', '').strip() or None,
            content=request.form.get('comm_content', '').strip() or None,
            date=comm_date or datetime.utcnow(),
            created_by=current_user.username,
        )

        contact_id = request.form.get('comm_contact_id')
        if contact_id:
            comm.contact_id = int(contact_id)

        db.session.add(comm)
        db.session.commit()
        flash('Kommunikation erfasst.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {e}', 'danger')

    return redirect(url_for('contracts.detail', contract_id=contract.id))


@contracts_bp.route('/communication/<int:comm_id>/delete', methods=['POST'])
@login_required
def delete_communication(comm_id):
    """Kommunikation loeschen"""
    comm = ContractCommunication.query.get_or_404(comm_id)
    contract_id = comm.contract_id
    try:
        db.session.delete(comm)
        db.session.commit()
        flash('Eintrag geloescht.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {e}', 'danger')
    return redirect(url_for('contracts.detail', contract_id=contract_id))


# === API fuer Dashboard-Widget ===

@contracts_bp.route('/api/alerts')
@login_required
def api_alerts():
    """Anstehende Vertrags-Warnungen"""
    today = date.today()
    in_30 = today + timedelta(days=30)

    expiring = Contract.query.filter(
        Contract.status == 'active',
        Contract.end_date.isnot(None),
        Contract.end_date.between(today, in_30),
    ).all()

    renewal_due = Contract.query.filter(
        Contract.status == 'active',
        Contract.renewal_date.isnot(None),
        Contract.renewal_date.between(today, in_30),
    ).all()

    alerts = []
    for c in expiring:
        alerts.append({
            'id': c.id,
            'name': c.name,
            'type': 'expiring',
            'label': f'Laeuft ab am {c.end_date.strftime("%d.%m.%Y")}',
            'days': c.days_until_end,
            'color': 'danger' if c.days_until_end <= 7 else 'warning',
        })
    for c in renewal_due:
        alerts.append({
            'id': c.id,
            'name': c.name,
            'type': 'renewal',
            'label': f'Kuendigungsfrist am {c.renewal_date.strftime("%d.%m.%Y")}',
            'days': c.days_until_renewal,
            'color': 'danger' if c.days_until_renewal <= 7 else 'info',
        })

    alerts.sort(key=lambda x: x['days'])
    return jsonify(alerts)


# === Hilfsfunktionen ===

def _parse_date(val):
    """Parst Datum aus Formular"""
    if not val:
        return None
    try:
        return datetime.strptime(val.strip(), '%Y-%m-%d').date()
    except (ValueError, AttributeError):
        return None


def _parse_datetime(val):
    """Parst Datetime aus Formular"""
    if not val:
        return None
    try:
        return datetime.strptime(val.strip(), '%Y-%m-%dT%H:%M')
    except (ValueError, AttributeError):
        try:
            return datetime.strptime(val.strip(), '%Y-%m-%d')
        except (ValueError, AttributeError):
            return None


def _parse_float(val):
    """Parst Float aus Formular (DE oder EN Format)"""
    if not val:
        return 0
    val = val.strip().replace(',', '.')
    try:
        return float(val)
    except ValueError:
        return 0


def _get_machines():
    """Holt Maschinen-Liste fuer Dropdown"""
    try:
        from src.models.models import Machine
        return Machine.query.filter_by(active=True).order_by(Machine.name).all()
    except Exception:
        return []
