# -*- coding: utf-8 -*-
"""
E-Mail-Sync Controller
======================
IMAP-Konten verwalten, E-Mails synchronisieren und anzeigen

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from functools import wraps

from src.models import db
from src.models.document import EmailAccount, ArchivedEmail

import logging
logger = logging.getLogger(__name__)

email_sync_bp = Blueprint('email_sync', __name__, url_prefix='/email-sync')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Nur Administratoren haben Zugriff.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@email_sync_bp.route('/')
@login_required
@admin_required
def index():
    """Posteingang - gesynchte E-Mails"""
    page = request.args.get('page', 1, type=int)
    account_id = request.args.get('account_id', type=int)
    unread_only = request.args.get('unread') == '1'

    query = ArchivedEmail.query

    if account_id:
        query = query.filter_by(email_account_id=account_id)
    if unread_only:
        query = query.filter_by(is_read=False)

    emails = query.order_by(ArchivedEmail.received_date.desc()).paginate(
        page=page, per_page=30, error_out=False
    )

    accounts = EmailAccount.query.filter_by(is_active=True).all()
    unread_count = ArchivedEmail.query.filter_by(is_read=False).count()

    return render_template('email_sync/index.html',
                         emails=emails,
                         accounts=accounts,
                         unread_count=unread_count,
                         filter_account=account_id,
                         filter_unread=unread_only)


@email_sync_bp.route('/accounts', methods=['GET', 'POST'])
@login_required
@admin_required
def accounts():
    """IMAP-Konten verwalten"""
    if request.method == 'POST':
        account = EmailAccount(
            name=request.form.get('name', ''),
            email_address=request.form.get('email_address', ''),
            imap_server=request.form.get('imap_server', ''),
            imap_port=int(request.form.get('imap_port', 993)),
            imap_use_ssl=request.form.get('imap_use_ssl') == 'on',
            imap_username=request.form.get('imap_username', ''),
            smtp_server=request.form.get('smtp_server', ''),
            smtp_port=int(request.form.get('smtp_port', 587)),
            smtp_use_tls=request.form.get('smtp_use_tls') == 'on',
            smtp_username=request.form.get('smtp_username', ''),
            archive_folder=request.form.get('archive_folder', 'INBOX'),
        )

        # Passwoerter verschluesseln
        imap_pw = request.form.get('imap_password', '')
        smtp_pw = request.form.get('smtp_password', '')
        if imap_pw:
            try:
                account.set_imap_password(imap_pw)
            except Exception:
                account.imap_password_encrypted = imap_pw
        if smtp_pw:
            try:
                account.set_smtp_password(smtp_pw)
            except Exception:
                account.smtp_password_encrypted = smtp_pw

        db.session.add(account)
        db.session.commit()
        flash(f'E-Mail-Konto "{account.name}" angelegt.', 'success')
        return redirect(url_for('email_sync.accounts'))

    all_accounts = EmailAccount.query.order_by(EmailAccount.name).all()
    return render_template('email_sync/accounts.html', accounts=all_accounts)


@email_sync_bp.route('/accounts/<int:account_id>/test', methods=['POST'])
@login_required
@admin_required
def test_account(account_id):
    """IMAP-Verbindung testen"""
    from src.services.imap_sync_service import IMAPSyncService

    account = EmailAccount.query.get_or_404(account_id)
    service = IMAPSyncService()
    result = service.test_connection(account)

    if result['success']:
        flash(f'Verbindung erfolgreich: {result["message"]}', 'success')
    else:
        flash(f'Verbindung fehlgeschlagen: {result["message"]}', 'danger')

    return redirect(url_for('email_sync.accounts'))


@email_sync_bp.route('/accounts/<int:account_id>/sync', methods=['POST'])
@login_required
@admin_required
def sync_account(account_id):
    """Manueller E-Mail-Sync"""
    from src.services.imap_sync_service import IMAPSyncService

    service = IMAPSyncService()
    result = service.fetch_new_emails(account_id)

    if 'error' in result:
        flash(f'Sync-Fehler: {result["error"]}', 'danger')
    else:
        flash(f'Sync erfolgreich: {result["fetched"]} neue E-Mails, '
              f'{result["duplicates"]} Duplikate.', 'success')

    return redirect(url_for('email_sync.index'))


@email_sync_bp.route('/email/<int:email_id>')
@login_required
@admin_required
def email_detail(email_id):
    """E-Mail-Detail-Ansicht"""
    archived = ArchivedEmail.query.get_or_404(email_id)

    # Als gelesen markieren
    if not archived.is_read:
        archived.is_read = True
        db.session.commit()

    return render_template('email_sync/email_detail.html', email=archived)


@email_sync_bp.route('/email/<int:email_id>/assign', methods=['POST'])
@login_required
@admin_required
def assign_customer(email_id):
    """Kunden zuordnen"""
    archived = ArchivedEmail.query.get_or_404(email_id)
    customer_id = request.form.get('customer_id')

    if customer_id:
        archived.customer_id = customer_id
        db.session.commit()
        flash('Kunde zugeordnet.', 'success')
    else:
        # Auto-Zuordnung versuchen
        from src.services.imap_sync_service import IMAPSyncService
        service = IMAPSyncService()
        cid = service.auto_assign_customer(email_id)
        if cid:
            flash('Kunde automatisch zugeordnet.', 'success')
        else:
            flash('Kein passender Kunde gefunden.', 'warning')

    return redirect(url_for('email_sync.email_detail', email_id=email_id))
