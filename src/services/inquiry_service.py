# -*- coding: utf-8 -*-
"""
Inquiry Service - Anfrage-Logik für die öffentliche Website
StitchAdmin 2.0
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import uuid
import os
import logging
from datetime import datetime, date
from werkzeug.utils import secure_filename
from flask import current_app

from src.models.models import db, Customer
from src.models.inquiry import Inquiry, InquiryStatus, INQUIRY_TYPE_LABELS
from src.models.crm_contact import CustomerContact, ContactType, ContactStatus

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'ai', 'eps', 'svg', 'dst', 'emb'}
DSGVO_CONSENT_TEXT = (
    'Ich willige ein, dass meine personenbezogenen Daten (Name, E-Mail, Telefon, Firma) '
    'zum Zweck der Bearbeitung meiner Anfrage gespeichert und verarbeitet werden. '
    'Die Einwilligung kann jederzeit widerrufen werden. '
    'Weitere Informationen finden Sie in unserer Datenschutzerklärung.'
)


def create_inquiry(form_data, files=None, remote_ip=None):
    """
    Erstellt eine Anfrage + CRM-Eintrag.

    Args:
        form_data: dict mit Formulardaten
        files: request.files (optional, für Design-Upload)
        remote_ip: IP-Adresse des Nutzers

    Returns:
        Inquiry Objekt mit tracking_token
    """
    # 1. Nummer und Token generieren
    inquiry_number = _generate_inquiry_number()
    tracking_token = uuid.uuid4().hex

    # 2. Design-Upload verarbeiten
    design_file_path = None
    design_file_name = None
    if files and 'design_file' in files:
        file = files['design_file']
        if file and file.filename and _allowed_file(file.filename):
            design_file_name = secure_filename(file.filename)
            filename = f"{inquiry_number}_{design_file_name}"
            upload_dir = os.path.join(current_app.static_folder, 'uploads', 'inquiries')
            os.makedirs(upload_dir, exist_ok=True)
            file.save(os.path.join(upload_dir, filename))
            design_file_path = f'uploads/inquiries/{filename}'

    # 3. Kunden per E-Mail suchen
    email = form_data.get('email', '').strip().lower()
    customer = None
    if email:
        customer = Customer.query.filter_by(email=email).first()

    # Falls nicht gefunden, neuen Kunden anlegen
    if not customer and email:
        customer_id = str(uuid.uuid4())
        customer_type = 'business' if form_data.get('company_name') else 'private'
        customer = Customer(
            id=customer_id,
            customer_type=customer_type,
            first_name=form_data.get('first_name', ''),
            last_name=form_data.get('last_name', ''),
            email=email,
            phone=form_data.get('phone', ''),
            company_name=form_data.get('company_name', ''),
            country='Deutschland',
            created_at=datetime.utcnow(),
            created_by='website_anfrage'
        )
        db.session.add(customer)
        db.session.flush()

    # 4. Anfrage erstellen
    desired_date = None
    if form_data.get('desired_date'):
        try:
            desired_date = datetime.strptime(form_data['desired_date'], '%Y-%m-%d').date()
        except ValueError:
            pass

    inquiry = Inquiry(
        inquiry_number=inquiry_number,
        tracking_token=tracking_token,
        first_name=form_data.get('first_name', ''),
        last_name=form_data.get('last_name', ''),
        email=email,
        phone=form_data.get('phone', ''),
        company_name=form_data.get('company_name', ''),
        customer_id=customer.id if customer else None,
        inquiry_type=form_data.get('inquiry_type', 'sonstige'),
        status='neu',
        description=form_data.get('description', ''),
        quantity=int(form_data['quantity']) if form_data.get('quantity') else None,
        textile_type=form_data.get('textile_type', ''),
        textile_color=form_data.get('textile_color', ''),
        desired_date=desired_date,
        design_file_path=design_file_path,
        design_file_name=design_file_name,
        dsgvo_consent=True,
        dsgvo_consent_at=datetime.utcnow(),
        dsgvo_consent_ip=remote_ip,
        dsgvo_consent_text=DSGVO_CONSENT_TEXT,
        source='website',
        created_at=datetime.utcnow()
    )
    db.session.add(inquiry)
    db.session.flush()

    # 5. CRM-Eintrag erstellen
    if customer:
        type_label = INQUIRY_TYPE_LABELS.get(inquiry.inquiry_type, inquiry.inquiry_type)
        contact = CustomerContact(
            customer_id=customer.id,
            contact_type=ContactType.WEBSITE_ANFRAGE,
            status=ContactStatus.OFFEN,
            subject=f'Website-Anfrage: {type_label} ({inquiry_number})',
            body_text=(
                f'Anfrage über die Website:\n\n'
                f'Typ: {type_label}\n'
                f'Beschreibung: {inquiry.description}\n'
                f'Menge: {inquiry.quantity or "-"}\n'
                f'Textil: {inquiry.textile_type or "-"}\n'
                f'Wunschtermin: {inquiry.desired_date or "-"}\n'
                f'Design-Datei: {design_file_name or "Keine"}\n\n'
                f'Kontakt: {inquiry.full_name}\n'
                f'E-Mail: {inquiry.email}\n'
                f'Telefon: {inquiry.phone or "-"}\n'
                f'Firma: {inquiry.company_name or "-"}'
            ),
            contact_date=datetime.utcnow(),
            created_at=datetime.utcnow(),
            created_by='website'
        )
        db.session.add(contact)
        db.session.flush()
        inquiry.crm_contact_id = contact.id

    db.session.commit()
    logger.info(f"Website-Anfrage {inquiry_number} erstellt (Token: {tracking_token})")

    return inquiry


def get_inquiry_by_token(token):
    """Anfrage anhand Tracking-Token finden"""
    return Inquiry.query.filter_by(tracking_token=token).first()


def get_inquiry_by_number(number):
    """Anfrage anhand Nummer finden"""
    return Inquiry.query.filter_by(inquiry_number=number).first()


def find_inquiries_by_email(email):
    """Alle Anfragen zu einer E-Mail-Adresse finden"""
    return Inquiry.query.filter_by(email=email.strip().lower()).order_by(
        Inquiry.created_at.desc()
    ).all()


def update_inquiry_status(inquiry_id, new_status, updated_by=None):
    """Status einer Anfrage ändern + CRM-Notiz erstellen"""
    inquiry = Inquiry.query.get(inquiry_id)
    if not inquiry:
        return None

    old_status = inquiry.status
    inquiry.status = new_status
    inquiry.updated_at = datetime.utcnow()
    inquiry.updated_by = updated_by

    # CRM-Notiz über Statusänderung
    if inquiry.customer_id:
        old_label = Inquiry(status=old_status).status_label
        new_label = Inquiry(status=new_status).status_label
        contact = CustomerContact(
            customer_id=inquiry.customer_id,
            contact_type=ContactType.NOTIZ,
            status=ContactStatus.ERLEDIGT,
            subject=f'Anfrage {inquiry.inquiry_number}: Status geändert',
            body_text=f'Status geändert von "{old_label}" auf "{new_label}"',
            contact_date=datetime.utcnow(),
            created_at=datetime.utcnow(),
            created_by=updated_by or 'system'
        )
        db.session.add(contact)

    db.session.commit()
    return inquiry


def _generate_inquiry_number():
    """Generiert eine neue Anfragen-Nummer: ANF-YYYYMM-NNNN"""
    today = date.today()
    prefix = f"ANF-{today.strftime('%Y%m')}-"

    last = Inquiry.query.filter(
        Inquiry.inquiry_number.like(f'{prefix}%')
    ).order_by(Inquiry.inquiry_number.desc()).first()

    if last:
        try:
            last_num = int(last.inquiry_number.replace(prefix, ''))
            return f"{prefix}{last_num + 1:04d}"
        except ValueError:
            pass

    return f"{prefix}0001"


def _allowed_file(filename):
    """Prüft ob Dateiendung erlaubt ist"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
