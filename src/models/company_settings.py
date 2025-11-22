# -*- coding: utf-8 -*-
"""
Firmeneinstellungen Model
Speichert alle wichtigen Firmendaten für Rechnungen
"""

from datetime import datetime
from src.models import db


class CompanySettings(db.Model):
    """Firmeneinstellungen für Rechnungen und Dokumente"""
    __tablename__ = 'company_settings'

    id = db.Column(db.Integer, primary_key=True)

    # Firmendaten
    company_name = db.Column(db.String(200), nullable=False, default='Ihre Firma')
    company_addition = db.Column(db.String(200))  # z.B. "GmbH", "e.K."
    owner_name = db.Column(db.String(200))  # Inhaber/Geschäftsführer

    # Adresse
    street = db.Column(db.String(200))
    house_number = db.Column(db.String(20))
    postal_code = db.Column(db.String(20))
    city = db.Column(db.String(100))
    country = db.Column(db.String(100), default='Deutschland')

    # Kontakt
    phone = db.Column(db.String(50))
    fax = db.Column(db.String(50))
    email = db.Column(db.String(120))
    website = db.Column(db.String(200))

    # Steuerdaten
    tax_id = db.Column(db.String(50))  # Steuernummer
    vat_id = db.Column(db.String(50))  # USt-IdNr. (DE...)
    tax_office = db.Column(db.String(200))  # Finanzamt

    # Bankverbindung
    bank_name = db.Column(db.String(200))
    iban = db.Column(db.String(34))
    bic = db.Column(db.String(11))
    account_holder = db.Column(db.String(200))  # Kontoinhaber (falls abweichend)

    # Handelsregister (optional)
    commercial_register = db.Column(db.String(200))  # z.B. "HRB 12345, AG München"

    # Rechnungseinstellungen
    invoice_prefix = db.Column(db.String(10), default='RE')
    invoice_footer_text = db.Column(db.Text)  # Fußtext auf Rechnungen
    payment_terms_days = db.Column(db.Integer, default=14)  # Zahlungsziel in Tagen
    default_tax_rate = db.Column(db.Float, default=19.0)  # Standard MwSt-Satz

    # Kleinunternehmer nach §19 UStG
    small_business = db.Column(db.Boolean, default=False)
    small_business_text = db.Column(db.Text, default='Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.')

    # Logo
    logo_path = db.Column(db.String(500))  # Pfad zum Logo

    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))

    @classmethod
    def get_settings(cls):
        """Hole die Firmeneinstellungen (oder erstelle Default)"""
        settings = cls.query.first()
        if not settings:
            # Erstelle Default-Einstellungen
            settings = cls(
                company_name='Ihre Firma',
                city='Musterstadt',
                country='Deutschland',
                payment_terms_days=14,
                default_tax_rate=19.0
            )
            db.session.add(settings)
            try:
                db.session.commit()
            except:
                db.session.rollback()
        return settings

    @property
    def full_address(self):
        """Vollständige Adresse als String"""
        parts = []
        if self.street and self.house_number:
            parts.append(f"{self.street} {self.house_number}")
        elif self.street:
            parts.append(self.street)

        if self.postal_code and self.city:
            parts.append(f"{self.postal_code} {self.city}")
        elif self.city:
            parts.append(self.city)

        if self.country and self.country != 'Deutschland':
            parts.append(self.country)

        return '\n'.join(parts)

    @property
    def display_name(self):
        """Firmenname mit Zusatz"""
        if self.company_addition:
            return f"{self.company_name} {self.company_addition}"
        return self.company_name
