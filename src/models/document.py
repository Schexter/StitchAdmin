# -*- coding: utf-8 -*-
"""
Dokumentenmanagement System (DMS) - Datenbank-Modelle
StitchAdmin 2.0
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime, date
from src.models.models import db
import hashlib
import os


class Document(db.Model):
    """
    Zentrale Dokumenten-Verwaltung mit GoBD-Compliance
    """
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Identifikation
    title = db.Column(db.String(300), nullable=False)
    document_number = db.Column(db.String(50), unique=True, index=True)  # DOC-2025-001234
    
    # Klassifizierung
    category = db.Column(db.String(50), index=True)  # vertrag, rechnung, angebot, lieferschein, email, post
    subcategory = db.Column(db.String(50))
    tags = db.Column(db.String(500))  # Komma-getrennt für Suche
    
    # Datei-Info
    filename = db.Column(db.String(255))
    original_filename = db.Column(db.String(255))
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)  # in Bytes
    mime_type = db.Column(db.String(100))
    file_hash = db.Column(db.String(64))  # SHA-256 für Integrität und Duplikatserkennung
    
    # OCR & Volltextsuche
    ocr_text = db.Column(db.Text)  # Extrahierter Text
    searchable_content = db.Column(db.Text)  # Für Fulltext-Index
    
    # Verknüpfungen zu anderen Modulen
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    invoice_id = db.Column(db.Integer, nullable=True)  # Optional: db.ForeignKey('rechnungen.id')
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    
    # Metadaten
    document_date = db.Column(db.Date)  # Rechnungsdatum, Vertragsdatum etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Versionierung
    version = db.Column(db.Integer, default=1)
    parent_document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=True)
    is_latest_version = db.Column(db.Boolean, default=True)
    version_comment = db.Column(db.Text)
    
    # GoBD / Compliance
    is_archived = db.Column(db.Boolean, default=False)
    archive_date = db.Column(db.DateTime)
    retention_until = db.Column(db.Date)  # Aufbewahrungsfrist (10 Jahre für Rechnungen)
    is_locked = db.Column(db.Boolean, default=False)  # Unveränderbar nach Archivierung
    
    # Zugriffsrechte
    visibility = db.Column(db.String(20), default='private')  # private, team, public
    department = db.Column(db.String(50))  # Für größere Organisationen
    
    # Zusätzliche Felder
    description = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    # Relationships
    customer = db.relationship('Customer', backref='documents', foreign_keys=[customer_id])
    order = db.relationship('Order', backref='documents', foreign_keys=[order_id])
    uploaded_by_user = db.relationship('User', backref='uploaded_documents', foreign_keys=[uploaded_by])
    access_logs = db.relationship('DocumentAccessLog', backref='document', lazy='dynamic', cascade='all, delete-orphan')
    versions = db.relationship('Document', 
                              backref=db.backref('parent', remote_side=[id]),
                              foreign_keys=[parent_document_id])
    
    def __repr__(self):
        return f'<Document {self.document_number}: {self.title}>'
    
    @staticmethod
    def generate_document_number():
        """Generiert eine eindeutige Dokumentennummer: DOC-YYYY-NNNNNN"""
        year = datetime.now().year
        last_doc = Document.query.filter(
            Document.document_number.like(f'DOC-{year}-%')
        ).order_by(Document.id.desc()).first()
        
        if last_doc:
            last_number = int(last_doc.document_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f'DOC-{year}-{new_number:06d}'
    
    @staticmethod
    def calculate_file_hash(filepath):
        """Berechnet SHA-256 Hash einer Datei"""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def create_version(self, new_file_path, version_comment=''):
        """Erstellt eine neue Version des Dokuments"""
        # Alte Version als nicht-latest markieren
        self.is_latest_version = False
        
        # Neue Version erstellen
        new_version = Document(
            title=self.title,
            document_number=self.document_number,
            category=self.category,
            subcategory=self.subcategory,
            tags=self.tags,
            filename=os.path.basename(new_file_path),
            original_filename=self.original_filename,
            file_path=new_file_path,
            file_size=os.path.getsize(new_file_path),
            mime_type=self.mime_type,
            file_hash=Document.calculate_file_hash(new_file_path),
            customer_id=self.customer_id,
            order_id=self.order_id,
            invoice_id=self.invoice_id,
            document_date=self.document_date,
            version=self.version + 1,
            parent_document_id=self.id,
            is_latest_version=True,
            version_comment=version_comment,
            visibility=self.visibility
        )
        
        db.session.add(new_version)
        return new_version
    
    def lock_document(self):
        """Sperrt Dokument gegen Änderungen (GoBD)"""
        self.is_locked = True
        self.archive_date = datetime.utcnow()
        
        # Berechne Aufbewahrungsfrist (z.B. 10 Jahre für Rechnungen)
        if self.category in ['rechnung', 'invoice']:
            from dateutil.relativedelta import relativedelta
            self.retention_until = date.today() + relativedelta(years=10)
    
    def get_file_extension(self):
        """Gibt die Dateiendung zurück"""
        if self.filename:
            return os.path.splitext(self.filename)[1].lower()
        return ''
    
    def is_pdf(self):
        """Prüft ob Dokument ein PDF ist"""
        return self.get_file_extension() == '.pdf'
    
    def is_image(self):
        """Prüft ob Dokument ein Bild ist"""
        return self.get_file_extension() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']


class DocumentAccessLog(db.Model):
    """
    Audit Trail - Wer hat wann was mit dem Dokument gemacht
    Wichtig für GoBD-Compliance
    """
    __tablename__ = 'document_access_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Aktion
    action = db.Column(db.String(50), nullable=False)  # view, download, edit, delete, archive, version
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Technische Details
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    
    # Zusätzliche Info
    details = db.Column(db.Text)  # JSON für zusätzliche Details
    
    # Relationships
    user = db.relationship('User', backref='document_access_logs')
    
    def __repr__(self):
        return f'<DocumentAccessLog {self.action} by User {self.user_id} at {self.timestamp}>'


class ShippingBulk(db.Model):
    """
    Versand-Bulk für Massen-Versand
    Gruppiert mehrere Sendungen für gemeinsamen Export/Druck
    """
    __tablename__ = 'shipping_bulks'

    id = db.Column(db.Integer, primary_key=True)

    # Basis-Daten
    bulk_number = db.Column(db.String(50), unique=True, nullable=False)  # BULK-2025-001
    name = db.Column(db.String(200))  # "Weihnachtsversand 2025"
    carrier = db.Column(db.String(50))  # DHL, DPD, etc.

    # Status
    status = db.Column(db.String(20), default='draft')  # draft, ready, printed, shipped, completed

    # Versand-Details
    planned_ship_date = db.Column(db.Date)  # Geplantes Versanddatum
    actual_ship_date = db.Column(db.Date)  # Tatsächliches Versanddatum

    # Export-Informationen
    csv_exported = db.Column(db.Boolean, default=False)
    csv_export_date = db.Column(db.DateTime)
    csv_file_path = db.Column(db.String(500))  # Pfad zur generierten CSV

    # Druck-Informationen
    labels_printed = db.Column(db.Boolean, default=False)
    labels_print_date = db.Column(db.DateTime)

    # Statistiken
    total_items = db.Column(db.Integer, default=0)
    total_weight = db.Column(db.Numeric(10, 2))  # kg
    total_cost = db.Column(db.Numeric(10, 2))

    # Notizen
    notes = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator = db.relationship('User', backref='shipping_bulks', foreign_keys=[created_by])

    def __repr__(self):
        return f'<ShippingBulk {self.bulk_number}: {self.name}>'

    @staticmethod
    def generate_bulk_number():
        """Generiert eine eindeutige Bulk-Nummer: BULK-YYYY-NNN"""
        year = datetime.now().year
        last_bulk = ShippingBulk.query.filter(
            ShippingBulk.bulk_number.like(f'BULK-{year}-%')
        ).order_by(ShippingBulk.id.desc()).first()

        if last_bulk:
            last_number = int(last_bulk.bulk_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1

        return f'BULK-{year}-{new_number:03d}'


class PostEntry(db.Model):
    """
    Postbuch - Ein- und ausgehende Post
    Erfüllt rechtliche Anforderungen für Nachweispflicht
    """
    __tablename__ = 'post_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Basis-Daten
    entry_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    entry_number = db.Column(db.String(50), unique=True)  # POST-2025-001234
    direction = db.Column(db.String(10), nullable=False)  # inbound, outbound
    type = db.Column(db.String(30), nullable=False)  # brief, einschreiben, einschreiben_rueckschein, paket, fax, email
    
    # Absender/Empfänger
    sender = db.Column(db.String(200))
    sender_address = db.Column(db.Text)
    recipient = db.Column(db.String(200))
    recipient_address = db.Column(db.Text)
    
    # Verknüpfung zu Kunden/Lieferanten
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    
    # Inhalt
    subject = db.Column(db.String(300), nullable=False)
    reference_number = db.Column(db.String(100))  # Aktenzeichen, Kundennummer etc.
    description = db.Column(db.Text)
    
    # Tracking (für Versand)
    tracking_number = db.Column(db.String(100))
    carrier = db.Column(db.String(50))  # DHL, DPD, Hermes, Deutsche Post
    shipping_cost = db.Column(db.Numeric(10, 2))
    delivery_status = db.Column(db.String(30))  # pending, in_transit, delivered, returned
    delivery_date = db.Column(db.DateTime)
    signature_received = db.Column(db.Boolean, default=False)
    signature_name = db.Column(db.String(100))
    
    # Verknüpfungen zu anderen Modulen
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    invoice_id = db.Column(db.Integer, nullable=True)  # Optional: db.ForeignKey('rechnungen.id')
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=True)
    
    # Bearbeitung
    handled_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.Column(db.String(20), default='open')  # open, in_progress, completed, archived
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    
    # Fristen
    due_date = db.Column(db.Date)  # Antwort-Frist
    reminder_date = db.Column(db.Date)  # Wiedervorlage
    
    # Kosten
    postage_cost = db.Column(db.Numeric(10, 2))
    
    # Notizen
    notes = db.Column(db.Text)
    internal_notes = db.Column(db.Text)  # Nicht für Kunden sichtbar

    # Bulk-Versand (für Massen-Versand)
    shipping_bulk_id = db.Column(db.Integer, db.ForeignKey('shipping_bulks.id'), nullable=True)

    # Erwartete Lieferung
    expected_delivery_date = db.Column(db.Date)  # Für erwartete Eingänge

    # Versand-Workflow
    email_notification_sent = db.Column(db.Boolean, default=False)
    email_notification_date = db.Column(db.DateTime)
    printed_at = db.Column(db.DateTime)  # Wann Versandetikett gedruckt
    shipped_at = db.Column(db.DateTime)  # Wann tatsächlich versendet

    # Workflow-Integration (Packlisten & Lieferscheine)
    packing_list_id = db.Column(db.Integer, db.ForeignKey('packing_lists.id'), nullable=True)
    delivery_note_id = db.Column(db.Integer, db.ForeignKey('delivery_notes.id'), nullable=True)
    is_auto_created = db.Column(db.Boolean, default=False)  # Automatisch aus Workflow erstellt

    # Foto-Dokumentation & OCR
    photos = db.Column(db.Text)  # JSON Array: [{"path": "...", "type": "invoice|letter|package|other", "description": "...", "timestamp": "..."}]
    ocr_text = db.Column(db.Text)  # Volltext aus OCR (für Briefe)
    extracted_data = db.Column(db.Text)  # JSON: {"amount": 123.45, "date": "2025-11-25", "tracking": "...", "reference": "..."}

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = db.relationship('Customer', backref='post_entries', foreign_keys=[customer_id])
    order = db.relationship('Order', backref='post_entries', foreign_keys=[order_id])
    document = db.relationship('Document', backref='post_entries', foreign_keys=[document_id])
    handler = db.relationship('User', backref='handled_post_entries', foreign_keys=[handled_by])
    shipping_bulk = db.relationship('ShippingBulk', backref='post_entries', foreign_keys=[shipping_bulk_id])
    
    def __repr__(self):
        return f'<PostEntry {self.entry_number}: {self.subject}>'
    
    @staticmethod
    def generate_entry_number():
        """Generiert eine eindeutige Postbuch-Nummer: POST-YYYY-NNNNNN"""
        year = datetime.now().year
        last_entry = PostEntry.query.filter(
            PostEntry.entry_number.like(f'POST-{year}-%')
        ).order_by(PostEntry.id.desc()).first()
        
        if last_entry:
            last_number = int(last_entry.entry_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f'POST-{year}-{new_number:06d}'
    
    def is_overdue(self):
        """Prüft ob Frist überschritten"""
        if self.due_date:
            return date.today() > self.due_date
        return False
    
    def needs_reminder(self):
        """Prüft ob Wiedervorlage fällig ist"""
        if self.reminder_date:
            return date.today() >= self.reminder_date
        return False

    # Foto-Management
    def get_photos(self):
        """Gibt alle Fotos als Liste zurück"""
        if not self.photos:
            return []
        try:
            return json.loads(self.photos)
        except (json.JSONDecodeError, TypeError):
            return []

    def add_photo(self, photo_path, photo_type='other', description=''):
        """Fügt ein Foto hinzu"""
        photos = self.get_photos()
        photos.append({
            'path': photo_path,
            'type': photo_type,
            'description': description,
            'timestamp': datetime.utcnow().isoformat()
        })
        self.photos = json.dumps(photos)

    def remove_photo(self, photo_path):
        """Entfernt ein Foto"""
        photos = self.get_photos()
        photos = [p for p in photos if p.get('path') != photo_path]
        self.photos = json.dumps(photos) if photos else None

    # OCR & Smart Extraction
    def get_extracted_data(self):
        """Gibt extrahierte Daten als Dict zurück"""
        if not self.extracted_data:
            return {}
        try:
            return json.loads(self.extracted_data)
        except (json.JSONDecodeError, TypeError):
            return {}

    def update_extracted_data(self, data_dict):
        """Aktualisiert extrahierte Daten"""
        current_data = self.get_extracted_data()
        current_data.update(data_dict)
        self.extracted_data = json.dumps(current_data)

    def set_ocr_text(self, text):
        """Setzt den OCR-erkannten Text"""
        self.ocr_text = text


class EmailAccount(db.Model):
    """
    E-Mail-Konten für IMAP/SMTP Integration
    Credentials werden verschlüsselt gespeichert
    """
    __tablename__ = 'email_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Account-Info
    name = db.Column(db.String(100), nullable=False)  # z.B. "Firmen-Hauptadresse"
    email_address = db.Column(db.String(255), nullable=False, unique=True)
    
    # IMAP Settings
    imap_server = db.Column(db.String(255))
    imap_port = db.Column(db.Integer, default=993)
    imap_use_ssl = db.Column(db.Boolean, default=True)
    imap_username = db.Column(db.String(255))
    imap_password_encrypted = db.Column(db.String(500))  # Verschlüsselt!
    
    # SMTP Settings
    smtp_server = db.Column(db.String(255))
    smtp_port = db.Column(db.Integer, default=587)
    smtp_use_tls = db.Column(db.Boolean, default=True)
    smtp_username = db.Column(db.String(255))
    smtp_password_encrypted = db.Column(db.String(500))  # Verschlüsselt!
    
    # Settings
    auto_archive = db.Column(db.Boolean, default=False)  # Automatisch archivieren
    archive_folder = db.Column(db.String(100), default='INBOX')
    check_interval = db.Column(db.Integer, default=15)  # Minuten
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    last_check = db.Column(db.DateTime)
    last_error = db.Column(db.Text)
    
    # Zuordnung
    default_customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    archived_emails = db.relationship('ArchivedEmail', backref='email_account', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<EmailAccount {self.email_address}>'
    
    def set_imap_password(self, password):
        """Verschlüsselt und speichert IMAP Passwort"""
        from src.utils.encryption import encrypt_password
        self.imap_password_encrypted = encrypt_password(password)
    
    def get_imap_password(self):
        """Entschlüsselt IMAP Passwort"""
        from src.utils.encryption import decrypt_password
        return decrypt_password(self.imap_password_encrypted)
    
    def set_smtp_password(self, password):
        """Verschlüsselt und speichert SMTP Passwort"""
        from src.utils.encryption import encrypt_password
        self.smtp_password_encrypted = encrypt_password(password)
    
    def get_smtp_password(self):
        """Entschlüsselt SMTP Passwort"""
        from src.utils.encryption import decrypt_password
        return decrypt_password(self.smtp_password_encrypted)


class ArchivedEmail(db.Model):
    """
    Archivierte E-Mails mit Metadaten
    """
    __tablename__ = 'archived_emails'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # E-Mail Account
    email_account_id = db.Column(db.Integer, db.ForeignKey('email_accounts.id'), nullable=False)
    
    # E-Mail Daten
    message_id = db.Column(db.String(255))  # Original Message-ID
    subject = db.Column(db.String(500))
    from_address = db.Column(db.String(255))
    to_address = db.Column(db.String(500))
    cc_address = db.Column(db.String(500))
    bcc_address = db.Column(db.String(500))
    
    # Inhalt
    body_text = db.Column(db.Text)
    body_html = db.Column(db.Text)
    
    # Metadaten
    received_date = db.Column(db.DateTime, index=True)
    size = db.Column(db.Integer)  # in Bytes
    has_attachments = db.Column(db.Boolean, default=False)
    attachment_count = db.Column(db.Integer, default=0)
    
    # Verknüpfungen
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=True)  # Als PDF gespeichert
    
    # Klassifizierung
    category = db.Column(db.String(50))  # auto-klassifiziert
    is_read = db.Column(db.Boolean, default=False)
    is_important = db.Column(db.Boolean, default=False)
    
    # Timestamps
    archived_at = db.Column(db.DateTime, default=datetime.utcnow)
    archived_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    customer = db.relationship('Customer', backref='archived_emails', foreign_keys=[customer_id])
    order = db.relationship('Order', backref='archived_emails', foreign_keys=[order_id])
    document = db.relationship('Document', backref='archived_email', foreign_keys=[document_id])
    attachments = db.relationship('EmailAttachment', backref='email', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<ArchivedEmail {self.subject}>'


class EmailAttachment(db.Model):
    """
    E-Mail Anhänge
    """
    __tablename__ = 'email_attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    archived_email_id = db.Column(db.Integer, db.ForeignKey('archived_emails.id'), nullable=False)
    
    # Datei-Info
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500))
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    
    # Als separates Dokument gespeichert?
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    document = db.relationship('Document', backref='email_attachments', foreign_keys=[document_id])
    
    def __repr__(self):
        return f'<EmailAttachment {self.filename}>'
