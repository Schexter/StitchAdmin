# -*- coding: utf-8 -*-
"""
Banking Controller
==================
Bank-Synchronisation, Transaktionen und Abgleich

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from functools import wraps
from datetime import date

from src.models import db
from src.models.banking import BankAccount, BankTransaction

import logging
logger = logging.getLogger(__name__)

banking_bp = Blueprint('banking', __name__, url_prefix='/banking')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Nur Administratoren haben Zugriff.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@banking_bp.route('/')
@login_required
@admin_required
def index():
    """Banking-Dashboard"""
    accounts = BankAccount.query.filter_by(is_active=True).all()

    # Statistiken
    total_unmatched = BankTransaction.query.filter_by(match_status='unmatched').count()
    total_transactions = BankTransaction.query.count()

    return render_template('banking/index.html',
                         accounts=accounts,
                         total_unmatched=total_unmatched,
                         total_transactions=total_transactions)


@banking_bp.route('/accounts', methods=['GET', 'POST'])
@login_required
@admin_required
def accounts():
    """Konto-Verwaltung"""
    if request.method == 'POST':
        account = BankAccount(
            name=request.form.get('name', ''),
            iban=request.form.get('iban', '').replace(' ', ''),
            bic=request.form.get('bic', ''),
            bank_name=request.form.get('bank_name', ''),
            fints_blz=request.form.get('fints_blz', ''),
            fints_login=request.form.get('fints_login', ''),
            fints_pin_encrypted=request.form.get('fints_pin', ''),  # TODO: verschluesseln
            fints_endpoint=request.form.get('fints_endpoint', ''),
        )
        db.session.add(account)
        db.session.commit()
        flash(f'Konto "{account.name}" angelegt.', 'success')
        return redirect(url_for('banking.accounts'))

    all_accounts = BankAccount.query.order_by(BankAccount.name).all()
    return render_template('banking/accounts.html', accounts=all_accounts)


@banking_bp.route('/accounts/<int:account_id>/test', methods=['POST'])
@login_required
@admin_required
def test_connection(account_id):
    """FinTS-Verbindung testen"""
    from src.services.bank_sync_service import BankSyncService

    account = BankAccount.query.get_or_404(account_id)
    service = BankSyncService()

    result = service.test_connection(
        blz=account.fints_blz,
        login=account.fints_login,
        pin=account.fints_pin_encrypted,
        endpoint=account.fints_endpoint,
    )

    if result['success']:
        flash(f'Verbindung erfolgreich: {result["message"]}', 'success')
    else:
        flash(f'Verbindung fehlgeschlagen: {result["message"]}', 'danger')

    return redirect(url_for('banking.accounts'))


@banking_bp.route('/accounts/<int:account_id>/sync', methods=['POST'])
@login_required
@admin_required
def sync_account(account_id):
    """Manueller Sync"""
    from src.services.bank_sync_service import BankSyncService

    service = BankSyncService()
    result = service.sync_account(account_id)

    if 'error' in result:
        flash(f'Sync-Fehler: {result["error"]}', 'danger')
    else:
        flash(f'Sync erfolgreich: {result["new_transactions"]} neue Transaktionen, '
              f'{result["duplicates"]} Duplikate uebersprungen.', 'success')

    return redirect(url_for('banking.index'))


@banking_bp.route('/accounts/<int:account_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_account(account_id):
    """Konto loeschen"""
    account = BankAccount.query.get_or_404(account_id)
    account.is_active = False
    db.session.commit()
    flash(f'Konto "{account.name}" deaktiviert.', 'success')
    return redirect(url_for('banking.accounts'))


@banking_bp.route('/transactions')
@login_required
@admin_required
def transactions():
    """Transaktionsliste"""
    account_id = request.args.get('account_id', type=int)
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)

    query = BankTransaction.query

    if account_id:
        query = query.filter_by(bank_account_id=account_id)
    if status:
        query = query.filter_by(match_status=status)

    transactions = query.order_by(BankTransaction.transaction_date.desc()).paginate(
        page=page, per_page=50, error_out=False
    )

    accounts = BankAccount.query.filter_by(is_active=True).all()

    return render_template('banking/transactions.html',
                         transactions=transactions,
                         accounts=accounts,
                         filter_account=account_id,
                         filter_status=status)


@banking_bp.route('/reconciliation')
@login_required
@admin_required
def reconciliation():
    """Abgleich-UI"""
    from src.models.rechnungsmodul.models import Rechnung, RechnungsStatus

    unmatched = BankTransaction.query.filter_by(
        match_status='unmatched'
    ).filter(BankTransaction.amount > 0).order_by(
        BankTransaction.transaction_date.desc()
    ).limit(50).all()

    offene_rechnungen = Rechnung.query.filter(
        Rechnung.status.in_([RechnungsStatus.GESENDET, RechnungsStatus.FAELLIG, RechnungsStatus.UEBERFAELLIG])
    ).order_by(Rechnung.rechnungsdatum.desc()).all()

    return render_template('banking/reconciliation.html',
                         unmatched=unmatched,
                         rechnungen=offene_rechnungen)


@banking_bp.route('/reconciliation/match', methods=['POST'])
@login_required
@admin_required
def match():
    """Manuell zuordnen"""
    from src.services.bank_sync_service import BankSyncService

    tx_id = request.form.get('tx_id', type=int)
    invoice_id = request.form.get('invoice_id', type=int)

    if not tx_id or not invoice_id:
        flash('Transaktion und Rechnung auswaehlen.', 'warning')
        return redirect(url_for('banking.reconciliation'))

    service = BankSyncService()
    if service.manual_match(tx_id, invoice_id):
        flash('Zuordnung gespeichert.', 'success')
    else:
        flash('Fehler bei Zuordnung.', 'danger')

    return redirect(url_for('banking.reconciliation'))


@banking_bp.route('/reconciliation/auto-match', methods=['POST'])
@login_required
@admin_required
def auto_match():
    """Automatischer Abgleich"""
    from src.services.bank_sync_service import BankSyncService

    account_id = request.form.get('account_id', type=int)
    service = BankSyncService()

    if account_id:
        result = service.auto_match_transactions(account_id)
    else:
        # Alle Konten
        accounts = BankAccount.query.filter_by(is_active=True).all()
        total_matched = 0
        total_unmatched = 0
        for acc in accounts:
            r = service.auto_match_transactions(acc.id)
            total_matched += r['matched']
            total_unmatched += r['unmatched']
        result = {'matched': total_matched, 'unmatched': total_unmatched}

    flash(f'Auto-Abgleich: {result["matched"]} zugeordnet, {result["unmatched"]} offen.', 'info')
    return redirect(url_for('banking.reconciliation'))


@banking_bp.route('/reconciliation/ignore/<int:tx_id>', methods=['POST'])
@login_required
@admin_required
def ignore_transaction(tx_id):
    """Transaktion ignorieren"""
    from src.services.bank_sync_service import BankSyncService

    service = BankSyncService()
    service.ignore_transaction(tx_id)
    flash('Transaktion wird ignoriert.', 'info')
    return redirect(url_for('banking.reconciliation'))
