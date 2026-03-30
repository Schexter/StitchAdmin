# -*- coding: utf-8 -*-
"""
Inquiry (Anfrage) Model für öffentliche Website-Anfragen
StitchAdmin 2.0
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import enum
from datetime import datetime
from src.models.models import db


class InquiryStatus(enum.Enum):
    """Status einer Anfrage"""
    NEU = 'neu'
    IN_BEARBEITUNG = 'in_bearbeitung'
    ANGEBOT_ERSTELLT = 'angebot_erstellt'
    ANGEBOT_VERSENDET = 'angebot_versendet'
    ANGENOMMEN = 'angenommen'
    ERLEDIGT = 'erledigt'
    STORNIERT = 'storniert'


INQUIRY_TYPE_LABELS = {
    'stickerei': 'Stickerei',
    'druck': 'Druck',
    'flex': 'Flex-Transfer',
    'flock': 'Flock-Transfer',
    'dtf': 'DTF-Druck',
    'tassendruck': 'Tassendruck',
    'design': 'Design-Erstellung',
    'sonstige': 'Sonstige Anfrage',
}


class Inquiry(db.Model):
    """
    Kundenanfrage über die öffentliche Website.
    Wird automatisch ins CRM übernommen.
    """
    __tablename__ = 'inquiries'

    id = db.Column(db.Integer, primary_key=True)

    # Öffentliches Tracking
    inquiry_number = db.Column(db.String(50), unique=True, nullable=False)
    tracking_token = db.Column(db.String(64), unique=True, nullable=False, index=True)

    # Kundendaten (direkt gespeichert)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(200), nullable=False, index=True)
    phone = db.Column(db.String(50))
    company_name = db.Column(db.String(200))

    # Verknüpfung zu bestehendem Kunden (optional)
    customer_id = db.Column(db.String(50), db.ForeignKey('customers.id'), index=True)

    # Anfrage-Details
    inquiry_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(30), nullable=False, default='neu')
    description = db.Column(db.Text, nullable=False)
    quantity = db.Column(db.Integer)
    textile_type = db.Column(db.String(200))
    textile_color = db.Column(db.String(100))
    desired_date = db.Column(db.Date)

    # Design-Upload
    design_file_path = db.Column(db.String(500))
    design_file_name = db.Column(db.String(255))

    # DSGVO-Einwilligung
    dsgvo_consent = db.Column(db.Boolean, nullable=False, default=False)
    dsgvo_consent_at = db.Column(db.DateTime)
    dsgvo_consent_ip = db.Column(db.String(50))
    dsgvo_consent_text = db.Column(db.Text)

    # Interne Bearbeitung
    assigned_to = db.Column(db.String(80))
    internal_notes = db.Column(db.Text)

    # CRM-Verknüpfung
    crm_contact_id = db.Column(db.Integer, db.ForeignKey('customer_contacts.id'))

    # Auftrags-Verknüpfung (bei Konvertierung)
    order_id = db.Column(db.String(50), db.ForeignKey('orders.id'))

    # Angebots-Verknüpfung
    angebot_id = db.Column(db.Integer, db.ForeignKey('angebote.id'))

    # Metadaten
    source = db.Column(db.String(20), default='website')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))

    # Relationships
    customer = db.relationship('Customer', backref=db.backref('inquiries', lazy='dynamic'))
    order = db.relationship('Order', backref='inquiry')
    angebot = db.relationship('Angebot', backref='anfrage')

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def type_label(self):
        return INQUIRY_TYPE_LABELS.get(self.inquiry_type, self.inquiry_type)

    @property
    def status_label(self):
        labels = {
            'neu': 'Neu',
            'in_bearbeitung': 'In Bearbeitung',
            'angebot_erstellt': 'Angebot erstellt',
            'angebot_versendet': 'Angebot versendet',
            'angenommen': 'Angenommen',
            'erledigt': 'Erledigt',
            'storniert': 'Storniert',
        }
        return labels.get(self.status, self.status)

    @property
    def status_color(self):
        colors = {
            'neu': 'primary',
            'in_bearbeitung': 'warning',
            'angebot_erstellt': 'info',
            'angebot_versendet': 'info',
            'angenommen': 'success',
            'erledigt': 'secondary',
            'storniert': 'danger',
        }
        return colors.get(self.status, 'secondary')

    @property
    def status_icon(self):
        icons = {
            'neu': 'bi-envelope-open',
            'in_bearbeitung': 'bi-gear',
            'angebot_erstellt': 'bi-file-text',
            'angebot_versendet': 'bi-send',
            'angenommen': 'bi-check-circle',
            'erledigt': 'bi-check-all',
            'storniert': 'bi-x-circle',
        }
        return icons.get(self.status, 'bi-question-circle')

    def __repr__(self):
        return f'<Inquiry {self.inquiry_number}: {self.inquiry_type} - {self.status}>'
