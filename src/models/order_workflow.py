# StitchAdmin 2.0 - Order Workflow Models
# Multi-Position-Design und Personalisierung
# Erstellt von Hans Hahn - Alle Rechte vorbehalten

from datetime import datetime
import json
from .models import db


class OrderDesign(db.Model):
    """
    Mehrere Designs pro Auftrag (Multi-Position)

    Beispiel: T-Shirt mit 3 Positionen:
    - Brust links: Personalisierter Name (Stick)
    - Ärmel rechts: Praxislogo (Stick)
    - Rücken: "Alpentour 2025" mit allen Namen (Stick)
    """
    __tablename__ = 'order_designs'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50), db.ForeignKey('orders.id'), nullable=False)

    # Position auf dem Textil
    position = db.Column(db.String(50), nullable=False)  # 'brust_links', 'brust_rechts', 'brust_mitte', 'aermel_links', 'aermel_rechts', 'ruecken', 'ruecken_oben', 'ruecken_unten', 'kragen', 'bauch'
    position_label = db.Column(db.String(100))  # 'Brust links', 'Ärmel rechts', etc.

    # Design-Typ
    design_type = db.Column(db.String(20), default='stick')  # 'stick', 'druck', 'dtf', 'flex', 'flock'
    is_personalized = db.Column(db.Boolean, default=False)  # True = jedes Stück hat anderen Text

    # Design-Datei
    design_file_path = db.Column(db.String(255))  # Pfad zur Original-Datei (DST, EMB, PNG, etc.)
    design_thumbnail_path = db.Column(db.String(255))  # Vorschau-Bild
    design_name = db.Column(db.String(200))  # Beschreibender Name

    # Stickerei-Details (falls design_type = 'stick')
    stitch_count = db.Column(db.Integer)  # Automatisch aus DST-Analyse
    width_mm = db.Column(db.Float)
    height_mm = db.Column(db.Float)
    thread_colors = db.Column(db.Text)  # JSON: [{"color": "Rot", "madeira_nr": "1147"}, ...]
    estimated_time_minutes = db.Column(db.Integer)  # Geschätzte Stickzeit pro Stück

    # Druck-Details (falls design_type in ['druck', 'dtf', 'flex', 'flock'])
    print_width_cm = db.Column(db.Float)
    print_height_cm = db.Column(db.Float)
    print_colors = db.Column(db.Integer)  # Anzahl Farben
    print_method = db.Column(db.String(50))  # 'siebdruck', 'digitaldruck', 'transfer'

    # Freigabe-Status (pro Position)
    approval_status = db.Column(db.String(20), default='pending')  # 'pending', 'sent', 'approved', 'rejected', 'revision_requested'
    approved_at = db.Column(db.DateTime)
    approval_notes = db.Column(db.Text)  # Kunden-Anmerkungen

    # Preisberechnung
    setup_price = db.Column(db.Float, default=0)  # Einrichtungskosten
    price_per_piece = db.Column(db.Float, default=0)  # Preis pro Stück für diese Position

    # Sortierung
    sort_order = db.Column(db.Integer, default=0)  # Reihenfolge der Positionen

    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    order = db.relationship('Order', backref=db.backref('designs', lazy='dynamic', cascade='all, delete-orphan'))
    personalizations = db.relationship('OrderItemPersonalization', backref='design', lazy='dynamic', cascade='all, delete-orphan')

    # Position-Optionen (statische Liste)
    POSITION_CHOICES = [
        ('brust_links', 'Brust links'),
        ('brust_rechts', 'Brust rechts'),
        ('brust_mitte', 'Brust Mitte'),
        ('aermel_links', 'Ärmel links'),
        ('aermel_rechts', 'Ärmel rechts'),
        ('ruecken', 'Rücken'),
        ('ruecken_oben', 'Rücken oben'),
        ('ruecken_unten', 'Rücken unten'),
        ('kragen', 'Kragen/Nacken'),
        ('bauch', 'Bauch'),
        ('hosenbein_links', 'Hosenbein links'),
        ('hosenbein_rechts', 'Hosenbein rechts'),
        ('kappe_vorne', 'Kappe vorne'),
        ('kappe_seite', 'Kappe Seite'),
        ('andere', 'Andere Position')
    ]

    DESIGN_TYPE_CHOICES = [
        ('stick', 'Stickerei'),
        ('druck', 'Druck'),
        ('flex', 'Flex/Flock')
    ]

    def get_thread_colors(self):
        """Gibt Garnfarben als Liste zurück"""
        if self.thread_colors:
            try:
                return json.loads(self.thread_colors)
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    def set_thread_colors(self, colors_list):
        """Speichert Garnfarben als JSON"""
        if colors_list:
            self.thread_colors = json.dumps(colors_list, ensure_ascii=False)
        else:
            self.thread_colors = None

    def get_position_label(self):
        """Gibt benutzerfreundliche Position zurück"""
        if self.position_label:
            return self.position_label
        # Fallback auf POSITION_CHOICES
        for code, label in self.POSITION_CHOICES:
            if code == self.position:
                return label
        return self.position

    def get_design_type_label(self):
        """Gibt benutzerfreundlichen Design-Typ zurück"""
        for code, label in self.DESIGN_TYPE_CHOICES:
            if code == self.design_type:
                return label
        return self.design_type

    def get_approval_status_label(self):
        """Gibt Freigabe-Status als Text zurück"""
        status_map = {
            'pending': 'Ausstehend',
            'sent': 'Zur Freigabe gesendet',
            'approved': 'Freigegeben',
            'rejected': 'Abgelehnt',
            'revision_requested': 'Änderung gewünscht'
        }
        return status_map.get(self.approval_status, self.approval_status)

    def get_approval_status_badge_class(self):
        """Bootstrap-Badge-Klasse für Status"""
        badge_map = {
            'pending': 'bg-secondary',
            'sent': 'bg-warning',
            'approved': 'bg-success',
            'rejected': 'bg-danger',
            'revision_requested': 'bg-info'
        }
        return badge_map.get(self.approval_status, 'bg-secondary')

    def calculate_total_price(self, quantity):
        """Berechnet Gesamtpreis für diese Position"""
        return self.setup_price + (self.price_per_piece * quantity)

    def __repr__(self):
        return f'<OrderDesign {self.id}: {self.get_position_label()} ({self.design_type})>'


class OrderItemPersonalization(db.Model):
    """
    Individuelle Personalisierung pro Stück

    Beispiel: 16 T-Shirts, jedes mit anderem Namen auf der Brust
    - Stück 1 (XL): "Max"
    - Stück 2 (L): "Anna"
    - Stück 3 (M): "Peter"
    - ...
    """
    __tablename__ = 'order_item_personalizations'

    id = db.Column(db.Integer, primary_key=True)

    # Verknüpfung zum OrderItem (welches Stück)
    order_item_id = db.Column(db.Integer, db.ForeignKey('order_items.id'), nullable=False)

    # Verknüpfung zum OrderDesign (welche Position)
    order_design_id = db.Column(db.Integer, db.ForeignKey('order_designs.id'), nullable=False)

    # Personalisierungs-Text (bis zu 3 Zeilen)
    text_line_1 = db.Column(db.String(100))  # z.B. "Max"
    text_line_2 = db.Column(db.String(100))  # z.B. "Mustermann"
    text_line_3 = db.Column(db.String(100))  # z.B. "Team Leader"

    # Zusätzliche Optionen
    font_name = db.Column(db.String(100))  # Schriftart (falls abweichend)
    custom_color = db.Column(db.String(50))  # Individuelle Farbe (falls abweichend)

    # Individuelle Datei (falls personalisiertes Logo/Design)
    custom_design_file = db.Column(db.String(255))

    # Sortierung / Produktionsreihenfolge
    sequence_number = db.Column(db.Integer)  # 1, 2, 3, ... für Produktionsreihenfolge

    # Produktions-Tracking
    is_produced = db.Column(db.Boolean, default=False)  # Bereits gefertigt?
    produced_at = db.Column(db.DateTime)
    produced_by = db.Column(db.String(80))

    # QM-Tracking
    qm_checked = db.Column(db.Boolean, default=False)
    qm_notes = db.Column(db.Text)

    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    order_item = db.relationship('OrderItem', backref=db.backref('personalizations', lazy='dynamic', cascade='all, delete-orphan'))

    def get_full_text(self):
        """Gibt den kompletten Personalisierungs-Text zurück"""
        lines = []
        if self.text_line_1:
            lines.append(self.text_line_1)
        if self.text_line_2:
            lines.append(self.text_line_2)
        if self.text_line_3:
            lines.append(self.text_line_3)
        return '\n'.join(lines)

    def get_display_text(self):
        """Kurze Darstellung für Listen"""
        if self.text_line_1:
            if self.text_line_2:
                return f"{self.text_line_1} {self.text_line_2}"
            return self.text_line_1
        return f"#{self.sequence_number}"

    def mark_as_produced(self, user=None):
        """Markiert als gefertigt"""
        self.is_produced = True
        self.produced_at = datetime.utcnow()
        self.produced_by = user

    def __repr__(self):
        return f'<OrderItemPersonalization {self.id}: "{self.get_display_text()}">'


# Positionen für Rücken-Sammeldesign (alle Namen auf einem Design)
class OrderDesignNameList(db.Model):
    """
    Namen-Liste für Sammeldesigns (z.B. alle 16 Namen auf dem Rücken)

    Beispiel: Rücken-Design "Alpentour 2025" mit allen Teilnehmernamen
    """
    __tablename__ = 'order_design_name_lists'

    id = db.Column(db.Integer, primary_key=True)
    order_design_id = db.Column(db.Integer, db.ForeignKey('order_designs.id'), nullable=False)

    # Name/Text
    name = db.Column(db.String(100), nullable=False)

    # Sortierung
    sort_order = db.Column(db.Integer, default=0)

    # Zusätzliche Infos
    subtitle = db.Column(db.String(100))  # z.B. Rolle/Position

    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    order_design = db.relationship('OrderDesign', backref=db.backref('name_list', lazy='dynamic', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<OrderDesignNameList {self.id}: {self.name}>'
