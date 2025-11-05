from datetime import datetime
from src.models.models import db


class SupplierContact(db.Model):
    """Ansprechpartner bei Lieferanten"""
    __tablename__ = 'supplier_contacts'
    
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.String(50), db.ForeignKey('suppliers.id'), nullable=False)
    
    # Persönliche Daten
    salutation = db.Column(db.String(20))  # Herr, Frau, Dr., etc.
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100))  # Position/Funktion
    department = db.Column(db.String(100))  # Abteilung
    
    # Kontaktdaten
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    phone_direct = db.Column(db.String(50))  # Durchwahl
    mobile = db.Column(db.String(50))
    fax = db.Column(db.String(50))
    
    # Kommunikationspräferenzen
    preferred_contact_method = db.Column(db.String(20), default='email')  # email, phone, mobile
    language = db.Column(db.String(10), default='de')  # Sprache (de, en, fr, etc.)
    
    # Zuständigkeiten
    is_primary_contact = db.Column(db.Boolean, default=False)
    is_sales_contact = db.Column(db.Boolean, default=True)
    is_technical_contact = db.Column(db.Boolean, default=False)
    is_accounting_contact = db.Column(db.Boolean, default=False)
    is_complaints_contact = db.Column(db.Boolean, default=False)
    
    # Verfügbarkeit
    availability_notes = db.Column(db.Text)  # z.B. "Mo-Fr 8-17 Uhr"
    vacation_substitute_id = db.Column(db.Integer, db.ForeignKey('supplier_contacts.id'))
    
    # Status
    active = db.Column(db.Boolean, default=True)
    
    # Notizen
    notes = db.Column(db.Text)
    internal_notes = db.Column(db.Text)  # Nur für interne Zwecke
    
    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))
    
    # Relationships
    supplier = db.relationship('Supplier', backref=db.backref('contacts', lazy='dynamic'))
    vacation_substitute = db.relationship('SupplierContact', remote_side=[id])
    communication_log = db.relationship('SupplierCommunicationLog', backref='contact', lazy='dynamic')
    
    @property
    def full_name(self):
        """Vollständiger Name"""
        parts = []
        if self.salutation:
            parts.append(self.salutation)
        if self.first_name:
            parts.append(self.first_name)
        parts.append(self.last_name)
        return ' '.join(parts)
    
    @property
    def display_name(self):
        """Anzeigename mit Position"""
        name = self.full_name
        if self.position:
            name += f' ({self.position})'
        return name
    
    def get_primary_phone(self):
        """Primäre Telefonnummer basierend auf Präferenz"""
        if self.preferred_contact_method == 'mobile' and self.mobile:
            return self.mobile
        elif self.phone_direct:
            return self.phone_direct
        elif self.phone:
            return self.phone
        return self.mobile or self.phone or self.phone_direct
    
    def __repr__(self):
        return f'<SupplierContact {self.full_name} @ {self.supplier_id}>'


class SupplierCommunicationLog(db.Model):
    """Kommunikationsprotokoll mit Lieferanten"""
    __tablename__ = 'supplier_communication_log'
    
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.String(50), db.ForeignKey('suppliers.id'), nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey('supplier_contacts.id'))
    
    # Kommunikationsdaten
    communication_type = db.Column(db.String(20), nullable=False)  # email, phone, meeting, letter
    direction = db.Column(db.String(10), nullable=False)  # inbound, outbound
    subject = db.Column(db.String(200))
    content = db.Column(db.Text)
    
    # Verknüpfungen
    order_id = db.Column(db.String(50), db.ForeignKey('supplier_orders.id'))
    article_id = db.Column(db.String(50), db.ForeignKey('articles.id'))
    
    # Status
    status = db.Column(db.String(20), default='completed')  # completed, pending, failed
    follow_up_required = db.Column(db.Boolean, default=False)
    follow_up_date = db.Column(db.Date)
    follow_up_notes = db.Column(db.Text)
    
    # Dateien
    attachment_count = db.Column(db.Integer, default=0)
    attachment_paths = db.Column(db.Text)  # JSON Array von Dateipfaden
    
    # Metadaten
    communication_date = db.Column(db.DateTime, default=datetime.utcnow)
    logged_at = db.Column(db.DateTime, default=datetime.utcnow)
    logged_by = db.Column(db.String(80))
    
    # Relationships
    supplier = db.relationship('Supplier', backref=db.backref('communication_log', lazy='dynamic'))
    order = db.relationship('SupplierOrder', backref=db.backref('communication_log', lazy='dynamic'))
    article = db.relationship('Article', backref=db.backref('supplier_communication_log', lazy='dynamic'))
    
    def __repr__(self):
        return f'<CommunicationLog {self.communication_type} {self.supplier_id} @ {self.communication_date}>'