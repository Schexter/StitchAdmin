# -*- coding: utf-8 -*-
"""
Shop Models für StitchAdmin
Kategorien, Veredelungsarten und Shop-Motive

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime
from src.models.models import db
import json


class ShopCategory(db.Model):
    """Kategorien für Shop-Artikel (z.B. T-Shirts, Poloshirts, Caps)"""
    __tablename__ = 'shop_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    image_path = db.Column(db.String(255))

    # Unterkategorien
    parent_id = db.Column(db.Integer, db.ForeignKey('shop_categories.id'))

    # Sortierung & Status
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)

    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    parent = db.relationship('ShopCategory', remote_side=[id], backref='subcategories')

    def __repr__(self):
        return f'<ShopCategory {self.name}>'


class ShopFinishingType(db.Model):
    """Veredelungsarten die im Shop angeboten werden"""
    __tablename__ = 'shop_finishing_types'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    finishing_type = db.Column(db.String(50), nullable=False)
    # stick, druck, flex, flock, dtf, sublimation, tassendruck

    description = db.Column(db.Text)
    icon = db.Column(db.String(50))  # Bootstrap Icon Klasse (bi-xxx)
    image_path = db.Column(db.String(255))

    # Preise
    setup_price = db.Column(db.Float, default=0)  # Einrichtungskosten
    price_per_piece = db.Column(db.Float, default=0)  # Pro Stück
    price_per_1000_stitches = db.Column(db.Float, default=0)  # Für Stick
    min_quantity = db.Column(db.Integer, default=1)  # Mindestmenge

    # Konfiguration
    available_positions = db.Column(db.Text)  # JSON: ['brust_links', 'ruecken', ...]
    max_colors = db.Column(db.Integer)
    max_width_mm = db.Column(db.Integer)
    max_height_mm = db.Column(db.Integer)
    size_surcharges = db.Column(db.Text)  # JSON: {'>100mm': 5.00, '>200mm': 10.00}

    # Sortierung & Status
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)

    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def get_available_positions(self):
        if self.available_positions:
            try:
                return json.loads(self.available_positions)
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    def set_available_positions(self, positions):
        self.available_positions = json.dumps(positions, ensure_ascii=False)

    def get_size_surcharges(self):
        if self.size_surcharges:
            try:
                return json.loads(self.size_surcharges)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    def set_size_surcharges(self, surcharges):
        self.size_surcharges = json.dumps(surcharges, ensure_ascii=False)

    @property
    def type_display(self):
        types = {
            'stick': 'Stickerei',
            'druck': 'Siebdruck',
            'flex': 'Flex-Folie',
            'flock': 'Flock-Folie',
            'dtf': 'DTF-Druck',
            'sublimation': 'Sublimation',
            'tassendruck': 'Tassendruck'
        }
        return types.get(self.finishing_type, self.finishing_type)

    def __repr__(self):
        return f'<ShopFinishingType {self.name}>'


class ShopDesignTemplate(db.Model):
    """Vorgefertigte Motive für den Shop-Konfigurator"""
    __tablename__ = 'shop_design_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    # Verknüpfung mit Designbibliothek (optional)
    design_id = db.Column(db.String(50), db.ForeignKey('designs.id'))

    # Bilder
    image_path = db.Column(db.String(255))
    thumbnail_path = db.Column(db.String(255))

    # Kategorisierung
    category = db.Column(db.String(50))  # logo, schrift, motiv, wappen, clipart

    # Technische Details (für Preisberechnung)
    stitch_count = db.Column(db.Integer)  # Für Stick-Preisberechnung
    color_count = db.Column(db.Integer)
    width_mm = db.Column(db.Integer)
    height_mm = db.Column(db.Integer)

    # Für welche Veredelungsarten verfügbar
    available_for_types = db.Column(db.Text)  # JSON: ['stick', 'druck', 'flex']

    # Sortierung & Status
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)

    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    design = db.relationship('Design', backref='shop_templates')

    def get_available_for_types(self):
        if self.available_for_types:
            try:
                return json.loads(self.available_for_types)
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    def set_available_for_types(self, types):
        self.available_for_types = json.dumps(types, ensure_ascii=False)

    @property
    def category_display(self):
        categories = {
            'logo': 'Logo',
            'schrift': 'Schriftzug',
            'motiv': 'Motiv',
            'wappen': 'Wappen',
            'clipart': 'Clipart'
        }
        return categories.get(self.category, self.category)

    def __repr__(self):
        return f'<ShopDesignTemplate {self.name}>'
