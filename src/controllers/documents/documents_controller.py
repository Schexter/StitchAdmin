# -*- coding: utf-8 -*-
"""
Dokumenten-Management Controller
StitchAdmin 2.0
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from src.models.models import db
from src.models.document import Document, DocumentAccessLog, PostEntry, EmailAccount, ArchivedEmail
from src.models.models import Customer, Order
from src.models.company_settings import CompanySettings
from datetime import datetime, date, timedelta
import os
import mimetypes

documents_bp = Blueprint('documents', __name__, url_prefix='/documents')


@documents_bp.route('/')
@documents_bp.route('/dashboard')
@login_required
def dashboard():
    """Dokumente & Post Dashboard"""
    
    # Statistiken
    total_documents = Document.query.filter_by(is_latest_version=True).count()
    documents_this_month = Document.query.filter(
        Document.created_at >= datetime(datetime.now().year, datetime.now().month, 1)
    ).count()
    
    # Postbuch Statistiken
    open_post = PostEntry.query.filter_by(status='open').count()
    overdue_post = PostEntry.query.filter(
        PostEntry.due_date < date.today(),
        PostEntry.status != 'completed'
    ).count()
    
    # E-Mail Statistiken
    unread_emails = ArchivedEmail.query.filter_by(is_read=False).count()
    
    # Letzte Aktivitäten
    recent_documents = Document.query.filter_by(is_latest_version=True)\
        .order_by(Document.created_at.desc()).limit(10).all()
    
    recent_post = PostEntry.query.order_by(PostEntry.entry_date.desc()).limit(10).all()
    
    # Wiedervorlagen (Reminder)
    reminders = PostEntry.query.filter(
        PostEntry.reminder_date <= date.today(),
        PostEntry.status != 'completed'
    ).order_by(PostEntry.reminder_date).all()
    
    return render_template('documents/dashboard.html',
                         total_documents=total_documents,
                         documents_this_month=documents_this_month,
                         open_post=open_post,
                         overdue_post=overdue_post,
                         unread_emails=unread_emails,
                         recent_documents=recent_documents,
                         recent_post=recent_post,
                         reminders=reminders)


@documents_bp.route('/list')
@login_required
def list_documents():
    """Dokumenten-Liste mit Filtern"""
    
    # Filter Parameter
    category = request.args.get('category', '')
    customer_id = request.args.get('customer_id', '')
    search = request.args.get('search', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Query starten
    query = Document.query.filter_by(is_latest_version=True)
    
    # Filter anwenden
    if category:
        query = query.filter_by(category=category)
    
    if customer_id:
        query = query.filter_by(customer_id=int(customer_id))
    
    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            db.or_(
                Document.title.ilike(search_pattern),
                Document.searchable_content.ilike(search_pattern),
                Document.tags.ilike(search_pattern)
            )
        )
    
    if date_from:
        query = query.filter(Document.document_date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    
    if date_to:
        query = query.filter(Document.document_date <= datetime.strptime(date_to, '%Y-%m-%d').date())
    
    # Sortierung
    documents = query.order_by(Document.created_at.desc()).all()
    
    # Kunden für Filter laden
    customers = Customer.query.order_by(Customer.company_name, Customer.first_name).all()
    
    # Kategorien
    categories = db.session.query(Document.category)\
        .filter(Document.category.isnot(None))\
        .distinct().all()
    categories = [cat[0] for cat in categories]
    
    return render_template('documents/list.html',
                         documents=documents,
                         customers=customers,
                         categories=categories,
                         current_category=category,
                         current_customer_id=customer_id,
                         search=search)


@documents_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Dokument hochladen"""
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Keine Datei ausgewählt', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('Keine Datei ausgewählt', 'error')
            return redirect(request.url)
        
        if file:
            try:
                # Dateiname sichern
                filename = secure_filename(file.filename)
                
                # Upload-Ordner erstellen
                upload_folder = os.path.join('instance', 'uploads', 'documents', str(datetime.now().year))
                os.makedirs(upload_folder, exist_ok=True)
                
                # Eindeutigen Dateinamen generieren
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_filename = f"{timestamp}_{filename}"
                filepath = os.path.join(upload_folder, unique_filename)
                
                # Datei speichern
                file.save(filepath)
                
                # Metadaten sammeln
                file_size = os.path.getsize(filepath)
                mime_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
                file_hash = Document.calculate_file_hash(filepath)
                
                # Dokument in DB anlegen
                document = Document(
                    title=request.form.get('title', filename),
                    document_number=Document.generate_document_number(),
                    category=request.form.get('category', 'sonstiges'),
                    subcategory=request.form.get('subcategory', ''),
                    tags=request.form.get('tags', ''),
                    filename=unique_filename,
                    original_filename=filename,
                    file_path=filepath,
                    file_size=file_size,
                    mime_type=mime_type,
                    file_hash=file_hash,
                    customer_id=request.form.get('customer_id') or None,
                    order_id=request.form.get('order_id') or None,
                    document_date=datetime.strptime(request.form.get('document_date'), '%Y-%m-%d').date() 
                                  if request.form.get('document_date') else date.today(),
                    uploaded_by=current_user.id,
                    description=request.form.get('description', ''),
                    notes=request.form.get('notes', '')
                )
                
                db.session.add(document)
                db.session.commit()
                
                # Access Log
                log = DocumentAccessLog(
                    document_id=document.id,
                    user_id=current_user.id,
                    action='upload',
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
                db.session.add(log)
                db.session.commit()
                
                flash(f'Dokument "{document.title}" erfolgreich hochgeladen!', 'success')
                return redirect(url_for('documents.view', id=document.id))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Fehler beim Hochladen: {str(e)}', 'error')
                return redirect(request.url)
    
    # GET - Formular anzeigen
    customers = Customer.query.order_by(Customer.company_name, Customer.first_name).all()
    
    categories = [
        'rechnung', 'angebot', 'lieferschein', 'vertrag', 
        'korrespondenz', 'email', 'post', 'sonstiges'
    ]
    
    return render_template('documents/upload.html',
                         customers=customers,
                         categories=categories)


@documents_bp.route('/view/<int:id>')
@login_required
def view(id):
    """Dokument anzeigen"""
    
    document = Document.query.get_or_404(id)
    
    # Access Log
    log = DocumentAccessLog(
        document_id=document.id,
        user_id=current_user.id,
        action='view',
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    db.session.add(log)
    db.session.commit()
    
    # Versionen laden
    if document.parent_document_id:
        # Dieses ist eine Version - lade alle Versionen des Parents
        all_versions = Document.query.filter(
            db.or_(
                Document.id == document.parent_document_id,
                Document.parent_document_id == document.parent_document_id
            )
        ).order_by(Document.version.desc()).all()
    else:
        # Dieses ist das Original - lade alle Child-Versionen
        all_versions = Document.query.filter(
            db.or_(
                Document.id == document.id,
                Document.parent_document_id == document.id
            )
        ).order_by(Document.version.desc()).all()
    
    # Zugriffs-Historie
    access_history = DocumentAccessLog.query.filter_by(document_id=document.id)\
        .order_by(DocumentAccessLog.timestamp.desc()).limit(20).all()
    
    return render_template('documents/view.html',
                         document=document,
                         versions=all_versions,
                         access_history=access_history)


@documents_bp.route('/download/<int:id>')
@login_required
def download(id):
    """Dokument herunterladen"""
    
    document = Document.query.get_or_404(id)
    
    # Access Log
    log = DocumentAccessLog(
        document_id=document.id,
        user_id=current_user.id,
        action='download',
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    db.session.add(log)
    db.session.commit()
    
    return send_file(
        document.file_path,
        as_attachment=True,
        download_name=document.original_filename
    )


@documents_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """Dokument löschen"""
    
    document = Document.query.get_or_404(id)
    
    # Prüfen ob gesperrt
    if document.is_locked:
        flash('Gesperrte Dokumente können nicht gelöscht werden!', 'error')
        return redirect(url_for('documents.view', id=id))
    
    try:
        # Access Log
        log = DocumentAccessLog(
            document_id=document.id,
            user_id=current_user.id,
            action='delete',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(log)
        
        # Datei löschen
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        # DB-Eintrag löschen
        db.session.delete(document)
        db.session.commit()
        
        flash('Dokument erfolgreich gelöscht', 'success')
        return redirect(url_for('documents.list_documents'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Löschen: {str(e)}', 'error')
        return redirect(url_for('documents.view', id=id))


@documents_bp.route('/search')
@login_required
def search():
    """Volltextsuche in Dokumenten"""
    
    query = request.args.get('q', '')
    
    if not query or len(query) < 3:
        return jsonify({'error': 'Suchbegriff zu kurz (min. 3 Zeichen)'})
    
    # Suche in verschiedenen Feldern
    search_pattern = f'%{query}%'
    results = Document.query.filter(
        Document.is_latest_version == True,
        db.or_(
            Document.title.ilike(search_pattern),
            Document.searchable_content.ilike(search_pattern),
            Document.ocr_text.ilike(search_pattern),
            Document.tags.ilike(search_pattern),
            Document.description.ilike(search_pattern)
        )
    ).order_by(Document.created_at.desc()).limit(50).all()
    
    return jsonify({
        'results': [{
            'id': doc.id,
            'title': doc.title,
            'document_number': doc.document_number,
            'category': doc.category,
            'document_date': doc.document_date.isoformat() if doc.document_date else None,
            'url': url_for('documents.view', id=doc.id)
        } for doc in results]
    })


# Postbuch Routen

@documents_bp.route('/post/expected')
@login_required
def post_expected():
    """Erwartete Eingänge"""
    from datetime import date

    # Erwartete Lieferungen (Eingänge mit expected_delivery_date)
    expected = PostEntry.query.filter(
        PostEntry.direction == 'inbound',
        PostEntry.expected_delivery_date.isnot(None),
        PostEntry.status.in_(['open', 'in_progress'])
    ).order_by(PostEntry.expected_delivery_date).all()

    # Gruppiere nach Status
    today = date.today()
    overdue = [e for e in expected if e.expected_delivery_date < today]
    today_expected = [e for e in expected if e.expected_delivery_date == today]
    upcoming = [e for e in expected if e.expected_delivery_date > today]

    return render_template('documents/post_expected.html',
                         overdue=overdue,
                         today_expected=today_expected,
                         upcoming=upcoming)


@documents_bp.route('/post')
@login_required
def post_list():
    """Postbuch-Übersicht"""

    # Filter
    direction = request.args.get('direction', '')
    status = request.args.get('status', '')
    search = request.args.get('search', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = PostEntry.query

    if direction:
        query = query.filter_by(direction=direction)

    if status:
        query = query.filter_by(status=status)

    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            db.or_(
                PostEntry.subject.ilike(search_pattern),
                PostEntry.sender.ilike(search_pattern),
                PostEntry.recipient.ilike(search_pattern),
                PostEntry.reference_number.ilike(search_pattern),
                PostEntry.tracking_number.ilike(search_pattern)
            )
        )

    if date_from:
        query = query.filter(PostEntry.entry_date >= datetime.strptime(date_from, '%Y-%m-%d'))

    if date_to:
        query = query.filter(PostEntry.entry_date <= datetime.strptime(date_to, '%Y-%m-%d'))

    entries = query.order_by(PostEntry.entry_date.desc()).all()

    return render_template('documents/post_list.html',
                         entries=entries,
                         direction=direction,
                         status=status,
                         search=search,
                         date_from=date_from,
                         date_to=date_to)


@documents_bp.route('/post/new', methods=['GET', 'POST'])
@login_required
def post_new():
    """Neuen Postbuch-Eintrag erstellen"""

    if request.method == 'POST':
        try:
            # Datums-Felder konvertieren
            due_date = None
            if request.form.get('due_date'):
                due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()

            reminder_date = None
            if request.form.get('reminder_date'):
                reminder_date = datetime.strptime(request.form.get('reminder_date'), '%Y-%m-%d').date()

            delivery_date = None
            if request.form.get('delivery_date'):
                delivery_date = datetime.strptime(request.form.get('delivery_date'), '%Y-%m-%dT%H:%M')

            entry = PostEntry(
                entry_number=PostEntry.generate_entry_number(),
                entry_date=datetime.now(),
                direction=request.form.get('direction'),
                type=request.form.get('type'),
                sender=request.form.get('sender'),
                sender_address=request.form.get('sender_address'),
                recipient=request.form.get('recipient'),
                recipient_address=request.form.get('recipient_address'),
                subject=request.form.get('subject'),
                reference_number=request.form.get('reference_number'),
                customer_id=request.form.get('customer_id') or None,
                order_id=request.form.get('order_id') or None,
                tracking_number=request.form.get('tracking_number'),
                carrier=request.form.get('carrier'),
                shipping_cost=request.form.get('shipping_cost') or None,
                delivery_status=request.form.get('delivery_status'),
                delivery_date=delivery_date,
                signature_received=bool(request.form.get('signature_received')),
                signature_name=request.form.get('signature_name'),
                handled_by=current_user.id,
                status=request.form.get('status', 'open'),
                priority=request.form.get('priority', 'normal'),
                due_date=due_date,
                reminder_date=reminder_date,
                notes=request.form.get('notes')
            )

            db.session.add(entry)
            db.session.commit()

            flash('Postbuch-Eintrag erfolgreich erstellt', 'success')
            return redirect(url_for('documents.post_view', id=entry.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {str(e)}', 'error')

    customers = Customer.query.order_by(Customer.company_name, Customer.first_name).all()
    company = CompanySettings.get_settings()
    return render_template('documents/post_new.html', customers=customers, company=company)


@documents_bp.route('/post/<int:id>')
@login_required
def post_view(id):
    """Post-Eintrag anzeigen"""

    entry = PostEntry.query.get_or_404(id)
    return render_template('documents/post_view.html', entry=entry)


@documents_bp.route('/post/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def post_edit(id):
    """Post-Eintrag bearbeiten"""

    entry = PostEntry.query.get_or_404(id)

    if request.method == 'POST':
        try:
            # Datums-Felder konvertieren
            due_date = None
            if request.form.get('due_date'):
                due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()

            reminder_date = None
            if request.form.get('reminder_date'):
                reminder_date = datetime.strptime(request.form.get('reminder_date'), '%Y-%m-%d').date()

            delivery_date = None
            if request.form.get('delivery_date'):
                delivery_date = datetime.strptime(request.form.get('delivery_date'), '%Y-%m-%dT%H:%M')

            # Felder aktualisieren
            entry.direction = request.form.get('direction')
            entry.type = request.form.get('type')
            entry.sender = request.form.get('sender')
            entry.sender_address = request.form.get('sender_address')
            entry.recipient = request.form.get('recipient')
            entry.recipient_address = request.form.get('recipient_address')
            entry.subject = request.form.get('subject')
            entry.reference_number = request.form.get('reference_number')
            entry.customer_id = request.form.get('customer_id') or None
            entry.order_id = request.form.get('order_id') or None
            entry.tracking_number = request.form.get('tracking_number')
            entry.carrier = request.form.get('carrier')
            entry.shipping_cost = request.form.get('shipping_cost') or None
            entry.delivery_status = request.form.get('delivery_status')
            entry.delivery_date = delivery_date
            entry.signature_received = bool(request.form.get('signature_received'))
            entry.signature_name = request.form.get('signature_name')
            entry.status = request.form.get('status')
            entry.priority = request.form.get('priority')
            entry.due_date = due_date
            entry.reminder_date = reminder_date
            entry.notes = request.form.get('notes')

            db.session.commit()

            flash('Postbuch-Eintrag erfolgreich aktualisiert', 'success')
            return redirect(url_for('documents.post_view', id=entry.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {str(e)}', 'error')

    customers = Customer.query.order_by(Customer.company_name, Customer.first_name).all()
    return render_template('documents/post_edit.html', entry=entry, customers=customers)


@documents_bp.route('/post/<int:id>/complete', methods=['POST'])
@login_required
def post_complete(id):
    """Post-Eintrag als erledigt markieren"""

    try:
        entry = PostEntry.query.get_or_404(id)
        entry.status = 'completed'
        db.session.commit()

        return jsonify({'success': True, 'message': 'Eintrag als erledigt markiert'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@documents_bp.route('/post/<int:id>/send_notification', methods=['POST'])
@login_required
def send_shipping_notification(id):
    """Sendet Versandbenachrichtigung per E-Mail"""
    entry = PostEntry.query.get_or_404(id)

    # Prüfe ob es ein Ausgang ist
    if entry.direction != 'outbound':
        return jsonify({'success': False, 'error': 'Nur für ausgehende Sendungen'}), 400

    # Hole E-Mail-Adresse
    customer_email = None
    if entry.customer:
        customer_email = entry.customer.email

    if not customer_email:
        return jsonify({'success': False, 'error': 'Keine E-Mail-Adresse hinterlegt'}), 400

    try:
        # Hole ersten aktiven E-Mail-Account
        email_account = EmailAccount.query.filter_by(is_active=True).first()
        if not email_account:
            return jsonify({'success': False, 'error': 'Kein E-Mail-Account konfiguriert'}), 400

        # Erstelle Versandbenachrichtigung
        from src.services.email_service import EmailIntegrationService

        service = EmailIntegrationService(email_account.id)

        # Tracking-Link generieren
        tracking_link = ''
        if entry.tracking_number and entry.carrier:
            carriers = {
                'DHL': f'https://www.dhl.de/de/privatkunden/pakete-empfangen/verfolgen.html?piececode={entry.tracking_number}',
                'DPD': f'https://tracking.dpd.de/parcelstatus?query={entry.tracking_number}',
                'Hermes': f'https://www.myhermes.de/empfangen/sendungsverfolgung/sendungsinformation#{entry.tracking_number}',
                'UPS': f'https://www.ups.com/track?tracknum={entry.tracking_number}',
                'GLS': f'https://gls-group.eu/DE/de/paketverfolgung?match={entry.tracking_number}'
            }
            tracking_link = carriers.get(entry.carrier, '')

        # E-Mail-Inhalt
        subject = f'Versandbenachrichtigung - {entry.subject}'

        body = f"""
Sehr geehrte Damen und Herren,

Ihre Sendung wurde versendet:

Referenz: {entry.reference_number or entry.entry_number}
Betreff: {entry.subject}
"""

        if entry.tracking_number:
            body += f"\nSendungsnummer: {entry.tracking_number}\n"

        if tracking_link:
            body += f"\nVerfolgen Sie Ihre Sendung: {tracking_link}\n"

        body += f"""
Carrier: {entry.carrier or 'Post'}

Mit freundlichen Grüßen
{email_account.email_address}
"""

        # E-Mail senden
        success = service.send_email(
            to_address=customer_email,
            subject=subject,
            body=body,
            html=False
        )

        if success:
            entry.email_notification_sent = True
            entry.email_notification_date = datetime.utcnow()
            db.session.commit()

            return jsonify({
                'success': True,
                'message': f'Versandbenachrichtigung an {customer_email} gesendet'
            })
        else:
            return jsonify({'success': False, 'error': 'E-Mail konnte nicht gesendet werden'}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# E-Mail Routen

@documents_bp.route('/email/accounts')
@login_required
def email_accounts():
    """E-Mail-Konten verwalten"""
    
    accounts = EmailAccount.query.all()
    return render_template('documents/email_accounts.html', accounts=accounts)


@documents_bp.route('/email/archived')
@login_required
def email_archived():
    """Archivierte E-Mails"""
    
    emails = ArchivedEmail.query.order_by(ArchivedEmail.received_date.desc()).limit(100).all()
    return render_template('documents/email_archived.html', emails=emails)
