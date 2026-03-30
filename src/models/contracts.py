# -*- coding: utf-8 -*-
"""
Vertraege & Policen Models
===========================
Verwaltung von Vertraegen, Versicherungspolicen, Wartungsvertraegen
inkl. Ansprechpartner und Kommunikationshistorie.

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime, date
from src.models import db


class Contract(db.Model):
    """Vertrag / Police"""
    __tablename__ = 'contracts'

    id = db.Column(db.Integer, primary_key=True)

    # Typ: insurance, supplier, maintenance, lease, service, other
    contract_type = db.Column(db.String(30), nullable=False, default='other')

    # Bezeichnung
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    contract_number = db.Column(db.String(100))  # Vertragsnummer / Policennummer

    # Anbieter / Partner
    provider_name = db.Column(db.String(200))  # Versicherung, Lieferant, etc.
    provider_contact = db.Column(db.String(200))  # Allg. Kontakt
    provider_phone = db.Column(db.String(50))
    provider_email = db.Column(db.String(200))
    provider_website = db.Column(db.String(300))

    # Laufzeit
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    renewal_date = db.Column(db.Date)  # Kuendigungsfrist / naechste Verlaengerung
    auto_renew = db.Column(db.Boolean, default=False)
    notice_period_days = db.Column(db.Integer, default=90)  # Kuendigungsfrist in Tagen

    # Kosten
    amount = db.Column(db.Float, default=0)
    payment_interval = db.Column(db.String(20), default='monthly')  # monthly, quarterly, yearly, one-time
    currency = db.Column(db.String(3), default='EUR')

    # Versicherungs-Felder
    coverage_amount = db.Column(db.Float)  # Deckungssumme
    deductible = db.Column(db.Float)  # Selbstbeteiligung
    insurance_type = db.Column(db.String(50))  # haftpflicht, gebaude, inventar, kfz, etc.

    # Dokumente (Pfad zum Vertragsdokument)
    document_path = db.Column(db.String(500))

    # Verknuepfung zu Maschinen (optional)
    machine_id = db.Column(db.String(50), db.ForeignKey('machines.id', ondelete='SET NULL'), nullable=True)

    # === BUCHHALTUNG / KOSTENZUORDNUNG ===
    # Kostenkategorie fuer Buchhaltung
    cost_category = db.Column(db.String(50), default='sonstige')  # miete, telefon, versicherung, leasing, wartung, software, sonstige
    # Kostenstelle (optional, z.B. "Produktion", "Verwaltung", "Vertrieb")
    cost_center = db.Column(db.String(100))
    # Buchungskonto (SKR03/SKR04)
    booking_account = db.Column(db.String(20))  # z.B. "4210" fuer Miete
    # Steuer: Vorsteuer abziehbar?
    vat_deductible = db.Column(db.Boolean, default=True)
    vat_rate = db.Column(db.Float, default=19.0)
    # Naechste Faelligkeit (wird automatisch berechnet/aktualisiert)
    next_due_date = db.Column(db.Date)
    # Letzte Buchung (wann wurde zuletzt eine Ausgabe erfasst)
    last_booked_date = db.Column(db.Date)
    # Automatisch Buchungen erzeugen?
    auto_booking = db.Column(db.Boolean, default=False)

    # Status: active, expired, cancelled, pending
    status = db.Column(db.String(20), default='active')
    notes = db.Column(db.Text)

    # Meta
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    contacts = db.relationship('ContractContact', backref='contract',
                               lazy='dynamic', cascade='all, delete-orphan')
    communications = db.relationship('ContractCommunication', backref='contract',
                                     lazy='dynamic', cascade='all, delete-orphan',
                                     order_by='ContractCommunication.date.desc()')
    machine = db.relationship('Machine', backref='contracts')

    # --- Labels & Hilfsfunktionen ---

    TYPE_LABELS = {
        'insurance': 'Versicherung',
        'supplier': 'Lieferantenvertrag',
        'maintenance': 'Wartungsvertrag',
        'lease': 'Miet-/Leasingvertrag',
        'service': 'Dienstleistungsvertrag',
        'other': 'Sonstiger Vertrag',
    }

    TYPE_ICONS = {
        'insurance': 'bi-shield-check',
        'supplier': 'bi-truck',
        'maintenance': 'bi-tools',
        'lease': 'bi-building',
        'service': 'bi-briefcase',
        'other': 'bi-file-earmark-text',
    }

    TYPE_COLORS = {
        'insurance': 'primary',
        'supplier': 'success',
        'maintenance': 'warning',
        'lease': 'info',
        'service': 'secondary',
        'other': 'dark',
    }

    INTERVAL_LABELS = {
        'monthly': 'Monatlich',
        'quarterly': 'Vierteljährlich',
        'half_yearly': 'Halbjährlich',
        'yearly': 'Jährlich',
        'one-time': 'Einmalig',
    }

    COST_CATEGORIES = {
        'miete': ('Miete & Nebenkosten', 'bi-house-door', '4210'),
        'telefon': ('Telefon & Internet', 'bi-phone', '4920'),
        'versicherung': ('Versicherungen', 'bi-shield-check', '4360'),
        'leasing': ('Leasing & Finanzierung', 'bi-credit-card', '4570'),
        'wartung': ('Wartung & Reparatur', 'bi-tools', '4805'),
        'software': ('Software & Lizenzen', 'bi-laptop', '4964'),
        'fahrzeug': ('Fahrzeugkosten', 'bi-car-front', '4510'),
        'energie': ('Strom & Gas', 'bi-lightning', '4240'),
        'entsorgung': ('Entsorgung & Reinigung', 'bi-trash', '4250'),
        'marketing': ('Marketing & Werbung', 'bi-megaphone', '4600'),
        'mitgliedschaft': ('Beitraege & Mitgliedschaften', 'bi-people', '4380'),
        'sonstige': ('Sonstige Kosten', 'bi-three-dots', '4900'),
    }

    STATUS_LABELS = {
        'active': 'Aktiv',
        'expired': 'Abgelaufen',
        'cancelled': 'Gekuendigt',
        'pending': 'In Vorbereitung',
    }

    @property
    def type_label(self):
        return self.TYPE_LABELS.get(self.contract_type, self.contract_type)

    @property
    def type_icon(self):
        return self.TYPE_ICONS.get(self.contract_type, 'bi-file-text')

    @property
    def type_color(self):
        return self.TYPE_COLORS.get(self.contract_type, 'secondary')

    @property
    def interval_label(self):
        return self.INTERVAL_LABELS.get(self.payment_interval, self.payment_interval)

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, self.status)

    @property
    def monthly_cost(self):
        """Berechnet monatliche Kosten"""
        if not self.amount:
            return 0
        factors = {
            'monthly': 1,
            'quarterly': 1 / 3,
            'half_yearly': 1 / 6,
            'yearly': 1 / 12,
            'one-time': 0,
        }
        return self.amount * factors.get(self.payment_interval, 1)

    @property
    def yearly_cost(self):
        """Berechnet jaehrliche Kosten"""
        return self.monthly_cost * 12

    @property
    def is_expiring_soon(self):
        """Laeuft in den naechsten 30 Tagen aus"""
        if not self.end_date:
            return False
        days_left = (self.end_date - date.today()).days
        return 0 < days_left <= 30

    @property
    def is_renewal_due(self):
        """Kuendigungsfrist naht (30 Tage)"""
        if not self.renewal_date:
            return False
        days_left = (self.renewal_date - date.today()).days
        return 0 < days_left <= 30

    @property
    def days_until_end(self):
        """Tage bis Vertragsende"""
        if not self.end_date:
            return None
        return (self.end_date - date.today()).days

    @property
    def days_until_renewal(self):
        """Tage bis Kuendigungsfrist"""
        if not self.renewal_date:
            return None
        return (self.renewal_date - date.today()).days

    @property
    def cost_category_label(self):
        cat = self.COST_CATEGORIES.get(self.cost_category)
        return cat[0] if cat else self.cost_category

    @property
    def cost_category_icon(self):
        cat = self.COST_CATEGORIES.get(self.cost_category)
        return cat[1] if cat else 'bi-three-dots'

    @property
    def suggested_account(self):
        """Vorgeschlagenes Buchungskonto basierend auf Kostenkategorie"""
        cat = self.COST_CATEGORIES.get(self.cost_category)
        return cat[2] if cat else '4900'

    @property
    def netto_amount(self):
        """Netto-Betrag (ohne MwSt)"""
        if not self.amount:
            return 0
        if self.vat_deductible and self.vat_rate:
            return round(self.amount / (1 + self.vat_rate / 100), 2)
        return self.amount

    @property
    def vat_amount(self):
        """MwSt-Betrag"""
        if not self.amount or not self.vat_deductible or not self.vat_rate:
            return 0
        return round(self.amount - self.netto_amount, 2)

    def calculate_next_due_date(self):
        """Berechnet die naechste Faelligkeit basierend auf Intervall"""
        from dateutil.relativedelta import relativedelta
        base = self.last_booked_date or self.start_date or date.today()
        intervals = {
            'monthly': relativedelta(months=1),
            'quarterly': relativedelta(months=3),
            'half_yearly': relativedelta(months=6),
            'yearly': relativedelta(years=1),
        }
        delta = intervals.get(self.payment_interval)
        if delta:
            self.next_due_date = base + delta
        return self.next_due_date

    def __repr__(self):
        return f"<Contract {self.id} '{self.name}' [{self.status}]>"


class ContractContact(db.Model):
    """Ansprechpartner fuer einen Vertrag"""
    __tablename__ = 'contract_contacts'

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id', ondelete='CASCADE'), nullable=False)

    name = db.Column(db.String(200), nullable=False)
    position = db.Column(db.String(100))  # z.B. "Sachbearbeiter", "Schadensabteilung"
    department = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    mobile = db.Column(db.String(50))
    email = db.Column(db.String(200))
    is_primary = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ContractContact {self.name} ({self.position})>"


class ContractCommunication(db.Model):
    """Kommunikationshistorie zu einem Vertrag"""
    __tablename__ = 'contract_communications'

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id', ondelete='CASCADE'), nullable=False)

    # Typ: call, email, letter, meeting, note
    comm_type = db.Column(db.String(20), default='note')
    subject = db.Column(db.String(300))
    content = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    # Kontaktperson (optional)
    contact_id = db.Column(db.Integer, db.ForeignKey('contract_contacts.id', ondelete='SET NULL'), nullable=True)
    contact_person = db.relationship('ContractContact')

    # Wer hat kommuniziert
    created_by = db.Column(db.String(100))

    TYPE_LABELS = {
        'call': 'Telefonat',
        'email': 'E-Mail',
        'letter': 'Brief/Post',
        'meeting': 'Termin',
        'note': 'Notiz',
    }

    TYPE_ICONS = {
        'call': 'bi-telephone',
        'email': 'bi-envelope',
        'letter': 'bi-mailbox',
        'meeting': 'bi-calendar-event',
        'note': 'bi-sticky',
    }

    @property
    def type_label(self):
        return self.TYPE_LABELS.get(self.comm_type, self.comm_type)

    @property
    def type_icon(self):
        return self.TYPE_ICONS.get(self.comm_type, 'bi-chat-dots')

    def __repr__(self):
        return f"<ContractCommunication {self.comm_type} '{self.subject}'>"
