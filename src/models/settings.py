"""
Erweiterte Einstellungs-Models für StitchAdmin
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

# Importiere aus models.py
from .models import db

class TaxRate(db.Model):
    """Mehrwertsteuersätze"""
    __tablename__ = 'tax_rates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # z.B. "Standard", "Ermäßigt", "Bücher"
    rate = db.Column(db.Float, nullable=False)  # z.B. 19.0, 7.0, 0.0
    country = db.Column(db.String(3), default='DE')  # ISO Country Code
    description = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)
    
    # Gültigkeitszeitraum
    valid_from = db.Column(db.Date)
    valid_to = db.Column(db.Date)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))
    
    @classmethod
    def get_default_rate(cls):
        """Hole den Standard-MwSt-Satz"""
        default_tax = cls.query.filter_by(is_default=True, active=True).first()
        return default_tax.rate if default_tax else 19.0
    
    @classmethod
    def get_active_rates(cls):
        """Hole alle aktiven MwSt-Sätze"""
        return cls.query.filter_by(active=True).order_by(cls.rate.desc()).all()
    
    def __repr__(self):
        return f'<TaxRate {self.name}: {self.rate}%>'


class PriceCalculationRule(db.Model):
    """Erweiterte Preiskalkulationsregeln"""
    __tablename__ = 'price_calculation_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    
    # Kalkulationsfaktoren
    factor_calculated = db.Column(db.Float, default=1.5)  # EK * Factor = VK kalkuliert
    factor_recommended = db.Column(db.Float, default=2.0)  # EK * Factor = VK empfohlen
    
    # MwSt-Integration
    tax_rate_id = db.Column(db.Integer, db.ForeignKey('tax_rates.id'))
    include_tax_in_calculation = db.Column(db.Boolean, default=False)  # Ob MwSt in Kalkulation einbezogen wird
    
    # Runden
    round_to_cents = db.Column(db.Integer, default=1)  # 1=auf Cent, 5=auf 5 Cent, 10=auf 10 Cent
    round_up_threshold = db.Column(db.Float, default=0.5)  # Ab welchem Wert aufrunden
    
    # Kategorien-spezifisch
    applies_to_categories = db.Column(db.Text)  # JSON Array von Kategorie-IDs
    applies_to_suppliers = db.Column(db.Text)  # JSON Array von Lieferanten
    
    # Mindest/Höchstpreise
    min_price = db.Column(db.Float)  # Mindest-VK
    max_markup_percent = db.Column(db.Float)  # Maximaler Aufschlag in %
    
    # Priorität (niedrigere Zahl = höhere Priorität)
    priority = db.Column(db.Integer, default=100)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))
    
    # Relationships
    tax_rate = db.relationship('TaxRate', backref='calculation_rules')
    
    def get_categories(self):
        """Gibt die zugeordneten Kategorien zurück"""
        if self.applies_to_categories:
            try:
                return json.loads(self.applies_to_categories)
            except:
                return []
        return []
    
    def set_categories(self, category_ids):
        """Setzt die zugeordneten Kategorien"""
        self.applies_to_categories = json.dumps(category_ids) if category_ids else None
    
    def get_suppliers(self):
        """Gibt die zugeordneten Lieferanten zurück"""
        if self.applies_to_suppliers:
            try:
                return json.loads(self.applies_to_suppliers)
            except:
                return []
        return []
    
    def set_suppliers(self, supplier_ids):
        """Setzt die zugeordneten Lieferanten"""
        self.applies_to_suppliers = json.dumps(supplier_ids) if supplier_ids else None
    
    def calculate_price(self, purchase_price, price_type='calculated'):
        """Berechnet VK-Preis basierend auf EK-Preis"""
        if not purchase_price or purchase_price <= 0:
            return 0.0
        
        # Wähle Faktor
        factor = self.factor_calculated if price_type == 'calculated' else self.factor_recommended
        
        # Grundpreis berechnen
        base_price = purchase_price * factor
        
        # MwSt hinzufügen falls gewünscht
        if self.include_tax_in_calculation and self.tax_rate:
            base_price = base_price * (1 + self.tax_rate.rate / 100)
        
        # Mindestpreis prüfen
        if self.min_price and base_price < self.min_price:
            base_price = self.min_price
        
        # Maximaler Aufschlag prüfen
        if self.max_markup_percent:
            max_price = purchase_price * (1 + self.max_markup_percent / 100)
            if base_price > max_price:
                base_price = max_price
        
        # Runden
        if self.round_to_cents > 1:
            base_price = round(base_price * (100 / self.round_to_cents)) * (self.round_to_cents / 100)
        else:
            base_price = round(base_price, 2)
        
        return base_price
    
    @classmethod
    def get_default_rule(cls):
        """Hole die Standard-Kalkulationsregel"""
        return cls.query.filter_by(active=True).order_by(cls.priority).first()
    
    @classmethod
    def get_rule_for_article(cls, article):
        """Hole die passende Regel für einen Artikel"""
        # Implementierung für kategorien-/lieferanten-spezifische Regeln
        rules = cls.query.filter_by(active=True).order_by(cls.priority).all()
        
        for rule in rules:
            # Prüfe Kategorien
            if rule.applies_to_categories:
                categories = rule.get_categories()
                if article.category_id and article.category_id in categories:
                    return rule
                if article.category and article.category in categories:
                    return rule
            
            # Prüfe Lieferanten
            if rule.applies_to_suppliers:
                suppliers = rule.get_suppliers()
                if article.supplier and article.supplier in suppliers:
                    return rule
        
        # Fallback: Standard-Regel
        return cls.get_default_rule()
    
    def __repr__(self):
        return f'<PriceCalculationRule {self.name}: {self.factor_calculated}x/{self.factor_recommended}x>'


class ImportSettings(db.Model):
    """Einstellungen für L-Shop Import"""
    __tablename__ = 'import_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    
    # Standard-Einstellungen
    default_supplier = db.Column(db.String(100), default='L-SHOP')
    default_tax_rate_id = db.Column(db.Integer, db.ForeignKey('tax_rates.id'))
    default_calculation_rule_id = db.Column(db.Integer, db.ForeignKey('price_calculation_rules.id'))
    
    # Import-Verhalten
    update_existing_articles = db.Column(db.Boolean, default=True)
    create_missing_categories = db.Column(db.Boolean, default=True)
    create_missing_brands = db.Column(db.Boolean, default=True)
    auto_calculate_prices = db.Column(db.Boolean, default=True)
    
    # Spalten-Mapping (JSON)
    column_mapping = db.Column(db.Text)  # JSON mit Spalten-Zuordnung
    
    # Filter
    import_only_active = db.Column(db.Boolean, default=True)
    min_stock_threshold = db.Column(db.Integer, default=0)
    
    # Preisbehandlung
    price_update_strategy = db.Column(db.String(50), default='calculate')  # calculate, keep, update
    stock_update_strategy = db.Column(db.String(50), default='add')  # add, replace, keep
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))
    
    # Relationships
    default_tax_rate = db.relationship('TaxRate', backref='import_settings')
    default_calculation_rule = db.relationship('PriceCalculationRule', backref='import_settings')
    
    def get_column_mapping(self):
        """Gibt das Spalten-Mapping zurück"""
        if self.column_mapping:
            try:
                return json.loads(self.column_mapping)
            except:
                return {}
        return {}
    
    def set_column_mapping(self, mapping):
        """Setzt das Spalten-Mapping"""
        self.column_mapping = json.dumps(mapping, ensure_ascii=False) if mapping else None
    
    @classmethod
    def get_default_settings(cls):
        """Hole die Standard-Import-Einstellungen"""
        return cls.query.first()  # Für jetzt nehmen wir die erste
    
    def __repr__(self):
        return f'<ImportSettings {self.name}>'
