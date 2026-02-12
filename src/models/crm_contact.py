# -*- coding: utf-8 -*-
"""
CRM Kontakt-Management Models
StitchAdmin 2.0
Erstellt von Hans Hahn - Alle Rechte vorbehalten

Models fuer:
- Kundenkontakte (E-Mails, Telefonate, Notizen)
- E-Mail-Vorlagen
- Kontakthistorie
"""

from datetime import datetime
from enum import Enum
from src.models import db


class ContactType(Enum):
    """Art des Kontakts"""
    EMAIL_AUSGANG = 'email_ausgang'      # Gesendete E-Mail
    EMAIL_EINGANG = 'email_eingang'      # Empfangene E-Mail
    TELEFON_AUSGANG = 'telefon_ausgang'  # Ausgehender Anruf
    TELEFON_EINGANG = 'telefon_eingang'  # Eingehender Anruf
    NOTIZ = 'notiz'                      # Interne Notiz
    TERMIN = 'termin'                    # Terminvereinbarung
    BESUCH = 'besuch'                    # Kundenbesuch


class ContactStatus(Enum):
    """Status des Kontakts"""
    ENTWURF = 'entwurf'
    GESENDET = 'gesendet'
    GEPLANT = 'geplant'
    ERLEDIGT = 'erledigt'
    OFFEN = 'offen'           # Noch zu bearbeiten
    WARTE_ANTWORT = 'warte'   # Warte auf Kundenantwort


class EmailTemplateCategory(Enum):
    """Kategorien fuer E-Mail-Vorlagen"""
    # Allgemein
    ALLGEMEIN = 'allgemein'
    ANGEBOT = 'angebot'
    NACHFRAGE = 'nachfrage'
    DANKE = 'danke'

    # Auftragsablauf
    AUFTRAG_BESTAETIGUNG = 'auftrag_bestaetigung'
    GRAFIK_FREIGABE = 'grafik_freigabe'
    PRODUKTION_GEPLANT = 'produktion_geplant'
    QM_ABNAHME = 'qm_abnahme'
    VERSAND_INFO = 'versand_info'

    # Rechnungen
    RECHNUNG = 'rechnung'
    MAHNUNG = 'mahnung'
    ZAHLUNGSERINNERUNG = 'zahlungserinnerung'


class CustomerContact(db.Model):
    """
    Kundenkontakt - E-Mails, Telefonate, Notizen
    Zentrale Kontakthistorie fuer CRM
    """
    __tablename__ = 'customer_contacts'

    id = db.Column(db.Integer, primary_key=True)

    # Zuordnung
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), index=True)  # Optional: Auftragsbezug

    # Kontaktart
    contact_type = db.Column(db.Enum(ContactType), nullable=False)
    status = db.Column(db.Enum(ContactStatus), default=ContactStatus.ERLEDIGT)

    # Inhalt
    subject = db.Column(db.String(500))  # Betreff (bei E-Mails) oder Titel
    body_text = db.Column(db.Text)       # Inhalt als Text
    body_html = db.Column(db.Text)       # Inhalt als HTML (bei E-Mails)

    # E-Mail-spezifisch
    email_to = db.Column(db.String(500))      # Empfaenger
    email_cc = db.Column(db.String(500))      # CC
    email_bcc = db.Column(db.String(500))     # BCC
    email_from = db.Column(db.String(200))    # Absender
    email_message_id = db.Column(db.String(500))  # Message-ID fuer Threading

    # Telefon-spezifisch
    phone_number = db.Column(db.String(50))   # Angerufene/Anrufende Nummer
    call_duration = db.Column(db.Integer)     # Dauer in Sekunden
    callback_required = db.Column(db.Boolean, default=False)  # Rueckruf erforderlich?
    callback_date = db.Column(db.DateTime)    # Rueckruf bis wann?

    # Anhaenge (JSON-Liste)
    attachments = db.Column(db.Text)  # JSON: [{filename, path, size, mime_type}]

    # Nachverfolgung
    follow_up_date = db.Column(db.DateTime)   # Wiedervorlage
    follow_up_note = db.Column(db.String(500))  # Wiedervorlage-Notiz

    # Metadaten
    contact_date = db.Column(db.DateTime, default=datetime.utcnow)  # Wann war der Kontakt?
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))     # User der den Eintrag erstellt hat
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    customer = db.relationship('Customer', backref=db.backref('contacts', lazy='dynamic', order_by='CustomerContact.contact_date.desc()'))
    order = db.relationship('Order', backref=db.backref('contacts', lazy='dynamic'))

    def get_attachments(self):
        """Gibt Anhaenge als Liste zurueck"""
        if self.attachments:
            import json
            try:
                return json.loads(self.attachments)
            except:
                return []
        return []

    def set_attachments(self, attachments_list):
        """Setzt Anhaenge aus Liste"""
        import json
        self.attachments = json.dumps(attachments_list, ensure_ascii=False) if attachments_list else None

    def add_attachment(self, filename, path, size=None, mime_type=None):
        """Fuegt einen Anhang hinzu"""
        attachments = self.get_attachments()
        attachments.append({
            'filename': filename,
            'path': path,
            'size': size,
            'mime_type': mime_type
        })
        self.set_attachments(attachments)

    @property
    def type_icon(self):
        """Bootstrap-Icon fuer Kontakttyp"""
        icons = {
            ContactType.EMAIL_AUSGANG: 'bi-envelope-arrow-up',
            ContactType.EMAIL_EINGANG: 'bi-envelope-arrow-down',
            ContactType.TELEFON_AUSGANG: 'bi-telephone-outbound',
            ContactType.TELEFON_EINGANG: 'bi-telephone-inbound',
            ContactType.NOTIZ: 'bi-sticky',
            ContactType.TERMIN: 'bi-calendar-event',
            ContactType.BESUCH: 'bi-person-walking'
        }
        return icons.get(self.contact_type, 'bi-chat-dots')

    @property
    def type_color(self):
        """Bootstrap-Farbe fuer Kontakttyp"""
        colors = {
            ContactType.EMAIL_AUSGANG: 'primary',
            ContactType.EMAIL_EINGANG: 'info',
            ContactType.TELEFON_AUSGANG: 'success',
            ContactType.TELEFON_EINGANG: 'success',
            ContactType.NOTIZ: 'warning',
            ContactType.TERMIN: 'danger',
            ContactType.BESUCH: 'secondary'
        }
        return colors.get(self.contact_type, 'secondary')

    @property
    def type_label(self):
        """Deutsches Label fuer Kontakttyp"""
        labels = {
            ContactType.EMAIL_AUSGANG: 'E-Mail gesendet',
            ContactType.EMAIL_EINGANG: 'E-Mail erhalten',
            ContactType.TELEFON_AUSGANG: 'Anruf (ausgehend)',
            ContactType.TELEFON_EINGANG: 'Anruf (eingehend)',
            ContactType.NOTIZ: 'Notiz',
            ContactType.TERMIN: 'Termin',
            ContactType.BESUCH: 'Besuch'
        }
        return labels.get(self.contact_type, str(self.contact_type.value))

    def __repr__(self):
        return f'<CustomerContact {self.id}: {self.contact_type.value} - {self.customer_id}>'


class EmailTemplate(db.Model):
    """
    E-Mail-Vorlagen fuer verschiedene Anlaesse
    """
    __tablename__ = 'email_templates'

    id = db.Column(db.Integer, primary_key=True)

    # Basis
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500))
    category = db.Column(db.Enum(EmailTemplateCategory), nullable=False)

    # Inhalt
    subject = db.Column(db.String(500), nullable=False)
    body_text = db.Column(db.Text)       # Plain-Text Version
    body_html = db.Column(db.Text)       # HTML-Version

    # Verfuegbare Platzhalter (JSON)
    # z.B. ["kunde_name", "firma", "auftragsnummer"]
    available_placeholders = db.Column(db.Text)

    # Einstellungen
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)  # Standard fuer diese Kategorie?
    sort_order = db.Column(db.Integer, default=0)

    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))

    def get_placeholders(self):
        """Gibt verfuegbare Platzhalter als Liste zurueck"""
        if self.available_placeholders:
            import json
            try:
                return json.loads(self.available_placeholders)
            except:
                return []
        return []

    def set_placeholders(self, placeholders_list):
        """Setzt verfuegbare Platzhalter"""
        import json
        self.available_placeholders = json.dumps(placeholders_list, ensure_ascii=False) if placeholders_list else None

    def render(self, context: dict) -> tuple:
        """
        Rendert die Vorlage mit Kontext-Variablen

        Args:
            context: Dict mit Platzhalter-Werten, z.B.:
                {
                    'kunde_name': 'Max Mustermann',
                    'firma': 'Muster GmbH',
                    'auftragsnummer': 'A2025-001'
                }

        Returns:
            Tuple (subject, body_text, body_html)
        """
        def replace_placeholders(text, ctx):
            if not text:
                return text
            for key, value in ctx.items():
                text = text.replace(f'{{{key}}}', str(value) if value else '')
            return text

        rendered_subject = replace_placeholders(self.subject, context)
        rendered_text = replace_placeholders(self.body_text, context)
        rendered_html = replace_placeholders(self.body_html, context)

        return rendered_subject, rendered_text, rendered_html

    @classmethod
    def get_by_category(cls, category: EmailTemplateCategory):
        """Holt alle aktiven Vorlagen einer Kategorie"""
        return cls.query.filter_by(
            category=category,
            is_active=True
        ).order_by(cls.sort_order, cls.name).all()

    @classmethod
    def get_default_for_category(cls, category: EmailTemplateCategory):
        """Holt die Standard-Vorlage einer Kategorie"""
        return cls.query.filter_by(
            category=category,
            is_active=True,
            is_default=True
        ).first()

    @classmethod
    def create_default_templates(cls):
        """Erstellt Standard-Vorlagen falls nicht vorhanden"""
        default_templates = [
            # Auftragsbestaetigung
            {
                'name': 'Auftragsbestaetigung',
                'category': EmailTemplateCategory.AUFTRAG_BESTAETIGUNG,
                'subject': 'Auftragsbestaetigung - {auftragsnummer}',
                'body_html': '''<p>Sehr geehrte(r) {anrede} {kunde_name},</p>

<p>vielen Dank fuer Ihren Auftrag!</p>

<p>Hiermit bestaetigen wir Ihnen den Eingang Ihres Auftrags:</p>

<table style="border-collapse: collapse; margin: 20px 0;">
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Auftragsnummer:</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{auftragsnummer}</td>
    </tr>
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Auftragsdatum:</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{auftragsdatum}</td>
    </tr>
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Gesamtbetrag:</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{gesamtbetrag}</td>
    </tr>
</table>

<p>Wir werden Ihren Auftrag schnellstmoeglich bearbeiten und Sie ueber den weiteren Fortschritt informieren.</p>

<p>Mit freundlichen Gruessen</p>''',
                'available_placeholders': ['anrede', 'kunde_name', 'firma', 'auftragsnummer', 'auftragsdatum', 'gesamtbetrag'],
                'is_default': True
            },

            # Grafik-Freigabe
            {
                'name': 'Grafik zur Freigabe',
                'category': EmailTemplateCategory.GRAFIK_FREIGABE,
                'subject': 'Grafik zur Freigabe - Auftrag {auftragsnummer}',
                'body_html': '''<p>Sehr geehrte(r) {anrede} {kunde_name},</p>

<p>die Grafik fuer Ihren Auftrag <strong>{auftragsnummer}</strong> ist fertig und wartet auf Ihre Freigabe.</p>

<p>Bitte pruefen Sie das angehaengte Design sorgfaeltig auf:</p>
<ul>
    <li>Korrekte Schreibweise aller Texte</li>
    <li>Richtige Farben und Positionierung</li>
    <li>Groesse und Platzierung auf dem Textil</li>
</ul>

<p><strong>Freigabe-Link:</strong> <a href="{freigabe_link}">Hier klicken zur Freigabe</a></p>

<p>Nach Ihrer Freigabe geht der Auftrag direkt in die Produktion.</p>

<p>Bei Aenderungswuenschen antworten Sie bitte auf diese E-Mail.</p>

<p>Mit freundlichen Gruessen</p>''',
                'available_placeholders': ['anrede', 'kunde_name', 'auftragsnummer', 'freigabe_link'],
                'is_default': True
            },

            # Produktion geplant
            {
                'name': 'Produktion geplant',
                'category': EmailTemplateCategory.PRODUKTION_GEPLANT,
                'subject': 'Ihr Auftrag {auftragsnummer} ist in Produktion',
                'body_html': '''<p>Sehr geehrte(r) {anrede} {kunde_name},</p>

<p>gute Nachrichten! Ihr Auftrag <strong>{auftragsnummer}</strong> befindet sich jetzt in der Produktion.</p>

<p><strong>Voraussichtliche Fertigstellung:</strong> {fertigstellungsdatum}</p>

<p>Wir werden Sie informieren, sobald Ihr Auftrag versandbereit ist.</p>

<p>Mit freundlichen Gruessen</p>''',
                'available_placeholders': ['anrede', 'kunde_name', 'auftragsnummer', 'fertigstellungsdatum'],
                'is_default': True
            },

            # QM-Abnahme mit Foto
            {
                'name': 'Qualitaetskontrolle abgeschlossen',
                'category': EmailTemplateCategory.QM_ABNAHME,
                'subject': 'Qualitaetskontrolle Auftrag {auftragsnummer} - Fotos',
                'body_html': '''<p>Sehr geehrte(r) {anrede} {kunde_name},</p>

<p>die Qualitaetskontrolle fuer Ihren Auftrag <strong>{auftragsnummer}</strong> wurde erfolgreich abgeschlossen.</p>

<p>Anbei finden Sie Fotos der fertigen Produkte zur Ansicht.</p>

<p>Der Auftrag wird nun fuer den Versand vorbereitet.</p>

<p>Mit freundlichen Gruessen</p>''',
                'available_placeholders': ['anrede', 'kunde_name', 'auftragsnummer'],
                'is_default': True
            },

            # Versandbestaetigung
            {
                'name': 'Versandbestaetigung',
                'category': EmailTemplateCategory.VERSAND_INFO,
                'subject': 'Ihr Auftrag {auftragsnummer} wurde versendet',
                'body_html': '''<p>Sehr geehrte(r) {anrede} {kunde_name},</p>

<p>Ihr Auftrag <strong>{auftragsnummer}</strong> wurde soeben versendet!</p>

<table style="border-collapse: collapse; margin: 20px 0;">
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Versanddienstleister:</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{versanddienstleister}</td>
    </tr>
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Sendungsnummer:</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{sendungsnummer}</td>
    </tr>
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Tracking-Link:</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;"><a href="{tracking_link}">Sendung verfolgen</a></td>
    </tr>
</table>

<p>Die voraussichtliche Lieferzeit betraegt {lieferzeit}.</p>

<p>Vielen Dank fuer Ihren Auftrag!</p>

<p>Mit freundlichen Gruessen</p>''',
                'available_placeholders': ['anrede', 'kunde_name', 'auftragsnummer', 'versanddienstleister', 'sendungsnummer', 'tracking_link', 'lieferzeit'],
                'is_default': True
            },

            # Allgemeine Anfrage
            {
                'name': 'Allgemeine Nachricht',
                'category': EmailTemplateCategory.ALLGEMEIN,
                'subject': '{betreff}',
                'body_html': '''<p>Sehr geehrte(r) {anrede} {kunde_name},</p>

<p>{nachricht}</p>

<p>Mit freundlichen Gruessen</p>''',
                'available_placeholders': ['anrede', 'kunde_name', 'firma', 'betreff', 'nachricht'],
                'is_default': True
            },

            # Rechnung
            {
                'name': 'Rechnungsversand',
                'category': EmailTemplateCategory.RECHNUNG,
                'subject': 'Rechnung {rechnungsnummer}',
                'body_html': '''<p>Sehr geehrte(r) {anrede} {kunde_name},</p>

<p>anbei erhalten Sie unsere Rechnung <strong>{rechnungsnummer}</strong> ueber <strong>{betrag}</strong>.</p>

<p><strong>Faelligkeitsdatum:</strong> {faelligkeitsdatum}</p>

<p>Bei Fragen stehen wir Ihnen gerne zur Verfuegung.</p>

<p>Mit freundlichen Gruessen</p>''',
                'available_placeholders': ['anrede', 'kunde_name', 'rechnungsnummer', 'betrag', 'faelligkeitsdatum'],
                'is_default': True
            },

            # Zahlungserinnerung
            {
                'name': 'Zahlungserinnerung',
                'category': EmailTemplateCategory.ZAHLUNGSERINNERUNG,
                'subject': 'Zahlungserinnerung - Rechnung {rechnungsnummer}',
                'body_html': '''<p>Sehr geehrte(r) {anrede} {kunde_name},</p>

<p>wir moechten Sie freundlich daran erinnern, dass die folgende Rechnung noch offen ist:</p>

<table style="border-collapse: collapse; margin: 20px 0;">
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Rechnungsnummer:</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{rechnungsnummer}</td>
    </tr>
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Offener Betrag:</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{betrag}</td>
    </tr>
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Faellig seit:</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{faelligkeitsdatum}</td>
    </tr>
</table>

<p>Wir bitten Sie, den offenen Betrag zeitnah zu ueberweisen.</p>

<p>Sollte sich diese E-Mail mit Ihrer Zahlung ueberschneiden, betrachten Sie diese bitte als gegenstandslos.</p>

<p>Mit freundlichen Gruessen</p>''',
                'available_placeholders': ['anrede', 'kunde_name', 'rechnungsnummer', 'betrag', 'faelligkeitsdatum'],
                'is_default': True
            }
        ]

        for template_data in default_templates:
            existing = cls.query.filter_by(
                name=template_data['name'],
                category=template_data['category']
            ).first()

            if not existing:
                placeholders = template_data.pop('available_placeholders', [])
                template = cls(**template_data)
                template.set_placeholders(placeholders)
                db.session.add(template)

        db.session.commit()

    @property
    def category_label(self):
        """Deutsches Label fuer Kategorie"""
        labels = {
            EmailTemplateCategory.ALLGEMEIN: 'Allgemein',
            EmailTemplateCategory.ANGEBOT: 'Angebot',
            EmailTemplateCategory.NACHFRAGE: 'Nachfrage',
            EmailTemplateCategory.DANKE: 'Dankeschoen',
            EmailTemplateCategory.AUFTRAG_BESTAETIGUNG: 'Auftragsbestaetigung',
            EmailTemplateCategory.GRAFIK_FREIGABE: 'Grafik-Freigabe',
            EmailTemplateCategory.PRODUKTION_GEPLANT: 'Produktion geplant',
            EmailTemplateCategory.QM_ABNAHME: 'QM-Abnahme',
            EmailTemplateCategory.VERSAND_INFO: 'Versandinfo',
            EmailTemplateCategory.RECHNUNG: 'Rechnung',
            EmailTemplateCategory.MAHNUNG: 'Mahnung',
            EmailTemplateCategory.ZAHLUNGSERINNERUNG: 'Zahlungserinnerung'
        }
        return labels.get(self.category, str(self.category.value))

    def __repr__(self):
        return f'<EmailTemplate {self.name}>'
