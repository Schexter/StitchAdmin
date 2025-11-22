# -*- coding: utf-8 -*-
"""
E-Mail Integration Controller
StitchAdmin 2.0
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from src.models.document import EmailAccount, ArchivedEmail
from src.models.models import db, Customer, Order
from src.services.email_service import EmailIntegrationService
from datetime import datetime

email_bp = Blueprint('email', __name__, url_prefix='/email')


@email_bp.route('/')
@email_bp.route('/accounts')
@login_required
def list_accounts():
    """Liste aller E-Mail-Accounts"""
    accounts = EmailAccount.query.all()
    
    # Statistiken
    total_archived = ArchivedEmail.query.count()
    unread_archived = ArchivedEmail.query.filter_by(is_read=False).count()
    
    return render_template('email/accounts.html',
                         accounts=accounts,
                         total_archived=total_archived,
                         unread_archived=unread_archived)


@email_bp.route('/accounts/new', methods=['GET', 'POST'])
@login_required
def new_account():
    """Neuer E-Mail-Account"""
    if request.method == 'POST':
        try:
            account = EmailAccount(
                name=request.form.get('name'),
                email_address=request.form.get('email_address'),
                imap_server=request.form.get('imap_server'),
                imap_port=int(request.form.get('imap_port', 993)),
                imap_use_ssl=request.form.get('imap_use_ssl') == 'on',
                imap_username=request.form.get('imap_username'),
                smtp_server=request.form.get('smtp_server'),
                smtp_port=int(request.form.get('smtp_port', 587)),
                smtp_use_tls=request.form.get('smtp_use_tls') == 'on',
                smtp_username=request.form.get('smtp_username'),
                auto_archive=request.form.get('auto_archive') == 'on',
                check_interval=int(request.form.get('check_interval', 15))
            )
            
            # Passwörter verschlüsselt speichern
            account.set_imap_password(request.form.get('imap_password'))
            account.set_smtp_password(request.form.get('smtp_password'))
            
            db.session.add(account)
            db.session.commit()
            
            flash(f'E-Mail-Account "{account.name}" erstellt', 'success')
            
            # Verbindungstest
            service = EmailIntegrationService(account.id)
            if service.connect_imap():
                flash('IMAP-Verbindung erfolgreich getestet!', 'success')
                service.disconnect_imap()
            else:
                flash('IMAP-Verbindung fehlgeschlagen - prüfe die Einstellungen', 'warning')
            
            return redirect(url_for('email.list_accounts'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {str(e)}', 'error')
    
    return render_template('email/account_form.html')


@email_bp.route('/accounts/<int:account_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_account(account_id):
    """E-Mail-Account bearbeiten"""
    account = EmailAccount.query.get_or_404(account_id)
    
    if request.method == 'POST':
        try:
            account.name = request.form.get('name')
            account.email_address = request.form.get('email_address')
            account.imap_server = request.form.get('imap_server')
            account.imap_port = int(request.form.get('imap_port', 993))
            account.imap_use_ssl = request.form.get('imap_use_ssl') == 'on'
            account.imap_username = request.form.get('imap_username')
            account.smtp_server = request.form.get('smtp_server')
            account.smtp_port = int(request.form.get('smtp_port', 587))
            account.smtp_use_tls = request.form.get('smtp_use_tls') == 'on'
            account.smtp_username = request.form.get('smtp_username')
            account.auto_archive = request.form.get('auto_archive') == 'on'
            account.check_interval = int(request.form.get('check_interval', 15))
            
            # Passwörter nur updaten wenn eingegeben
            if request.form.get('imap_password'):
                account.set_imap_password(request.form.get('imap_password'))
            
            if request.form.get('smtp_password'):
                account.set_smtp_password(request.form.get('smtp_password'))
            
            account.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash(f'Account "{account.name}" aktualisiert', 'success')
            return redirect(url_for('email.list_accounts'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {str(e)}', 'error')
    
    return render_template('email/account_form.html', account=account)


@email_bp.route('/accounts/<int:account_id>/test')
@login_required
def test_connection(account_id):
    """Testet E-Mail-Verbindung"""
    try:
        service = EmailIntegrationService(account_id)
        
        if service.connect_imap():
            service.disconnect_imap()
            flash('IMAP-Verbindung erfolgreich!', 'success')
        else:
            flash('IMAP-Verbindung fehlgeschlagen', 'error')
            
    except Exception as e:
        flash(f'Fehler: {str(e)}', 'error')
    
    return redirect(url_for('email.list_accounts'))


@email_bp.route('/accounts/<int:account_id>/fetch')
@login_required
def fetch_emails(account_id):
    """Holt E-Mails vom Server"""
    try:
        service = EmailIntegrationService(account_id)
        
        # Parameter
        folder = request.args.get('folder', 'INBOX')
        limit = int(request.args.get('limit', 50))
        unread_only = request.args.get('unread_only') == 'true'
        
        # Hole E-Mails
        emails = service.fetch_emails(folder, limit, unread_only)
        
        if emails:
            flash(f'{len(emails)} E-Mails abgerufen', 'success')
        else:
            flash('Keine E-Mails gefunden', 'info')
        
        # Zeige E-Mails
        return render_template('email/inbox.html',
                             account_id=account_id,
                             emails=emails)
        
    except Exception as e:
        flash(f'Fehler: {str(e)}', 'error')
        return redirect(url_for('email.list_accounts'))


@email_bp.route('/accounts/<int:account_id>/inbox')
@login_required
def inbox(account_id):
    """Zeigt Inbox (bereits archivierte E-Mails)"""
    account = EmailAccount.query.get_or_404(account_id)
    
    # Filter
    is_read = request.args.get('read')
    customer_id = request.args.get('customer_id')
    category = request.args.get('category')
    
    # Query
    query = ArchivedEmail.query.filter_by(email_account_id=account_id)
    
    if is_read is not None:
        query = query.filter_by(is_read=(is_read == 'true'))
    
    if customer_id:
        query = query.filter_by(customer_id=int(customer_id))
    
    if category:
        query = query.filter_by(category=category)
    
    # Sortierung
    query = query.order_by(ArchivedEmail.received_date.desc())
    
    emails = query.limit(100).all()
    
    return render_template('email/archived_list.html',
                         account=account,
                         emails=emails)


@email_bp.route('/archive', methods=['POST'])
@login_required
def archive_email():
    """Archiviert E-Mail (AJAX)"""
    try:
        account_id = int(request.form.get('account_id'))
        email_data = request.get_json()
        
        # Kunde zuordnen
        customer_id = request.form.get('customer_id')
        if customer_id:
            customer_id = int(customer_id)
        
        # Archiviere
        service = EmailIntegrationService(account_id)
        archived = service.archive_email(
            email_data,
            customer_id=customer_id,
            archived_by_user_id=current_user.id
        )
        
        return jsonify({
            'success': True,
            'message': 'E-Mail archiviert',
            'archived_id': archived.id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@email_bp.route('/archived/<int:email_id>')
@login_required
def view_archived(email_id):
    """Zeigt archivierte E-Mail"""
    email = ArchivedEmail.query.get_or_404(email_id)
    
    # Markiere als gelesen
    if not email.is_read:
        email.is_read = True
        db.session.commit()
    
    return render_template('email/view_archived.html', email=email)


@email_bp.route('/archived/<int:email_id>/assign', methods=['POST'])
@login_required
def assign_customer(email_id):
    """Ordnet E-Mail einem Kunden zu"""
    email = ArchivedEmail.query.get_or_404(email_id)
    
    customer_id = request.form.get('customer_id')
    if customer_id:
        email.customer_id = int(customer_id)
        db.session.commit()
        flash('Kunde zugeordnet', 'success')
    
    return redirect(url_for('email.view_archived', email_id=email_id))


@email_bp.route('/send', methods=['GET', 'POST'])
@login_required
def send_email():
    """E-Mail senden"""
    if request.method == 'POST':
        try:
            account_id = int(request.form.get('account_id'))
            to_address = request.form.get('to_address')
            subject = request.form.get('subject')
            body = request.form.get('body')
            html = request.form.get('html') == 'on'
            
            # Sende
            service = EmailIntegrationService(account_id)
            success = service.send_email(
                to_address=to_address,
                subject=subject,
                body=body,
                html=html
            )
            
            if success:
                flash('E-Mail gesendet', 'success')
                return redirect(url_for('email.list_accounts'))
            else:
                flash('Fehler beim Senden', 'error')
                
        except Exception as e:
            flash(f'Fehler: {str(e)}', 'error')
    
    # GET
    accounts = EmailAccount.query.filter_by(is_active=True).all()
    customers = Customer.query.order_by(Customer.name).all()
    
    return render_template('email/compose.html',
                         accounts=accounts,
                         customers=customers)


@email_bp.route('/templates')
@login_required
def email_templates():
    """E-Mail-Vorlagen"""
    # TODO: Implementiere E-Mail-Vorlagen
    templates = [
        {
            'name': 'Auftragsbestätigung',
            'subject': 'Auftragsbestätigung {order_number}',
            'body': 'Sehr geehrte Damen und Herren,\n\nhiermit bestätigen wir Ihren Auftrag...'
        },
        {
            'name': 'Rechnung',
            'subject': 'Rechnung {invoice_number}',
            'body': 'Sehr geehrte Damen und Herren,\n\nanbei erhalten Sie Ihre Rechnung...'
        }
    ]
    
    return render_template('email/templates.html', templates=templates)
