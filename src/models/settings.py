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


class OperatingCostCategory(db.Model):
    """Betriebskosten-Kategorien (Fixkosten)"""
    __tablename__ = 'operating_cost_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))  # Bootstrap Icon Name
    color = db.Column(db.String(20))  # CSS Color
    active = db.Column(db.Boolean, default=True)

    # Sortierung
    sort_order = db.Column(db.Integer, default=0)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))

    # Relationships
    costs = db.relationship('OperatingCost', backref='category', lazy='dynamic', cascade='all, delete-orphan')

    def get_total_monthly_cost(self):
        """Berechnet Gesamtkosten dieser Kategorie pro Monat"""
        total = 0.0
        for cost in self.costs.filter_by(active=True):
            total += cost.get_monthly_amount()
        return total

    @classmethod
    def get_default_categories(cls):
        """Gibt Standard-Kategorien zurück oder erstellt sie"""
        defaults = [
            {'name': 'Raumkosten', 'icon': 'house-door', 'color': '#0d6efd', 'sort_order': 1},
            {'name': 'Personalkosten', 'icon': 'people', 'color': '#198754', 'sort_order': 2},
            {'name': 'Versicherungen', 'icon': 'shield-check', 'color': '#ffc107', 'sort_order': 3},
            {'name': 'Software & Lizenzen', 'icon': 'laptop', 'color': '#0dcaf0', 'sort_order': 4},
            {'name': 'Marketing & Werbung', 'icon': 'megaphone', 'color': '#d63384', 'sort_order': 5},
            {'name': 'Sonstiges', 'icon': 'three-dots', 'color': '#6c757d', 'sort_order': 99}
        ]

        for default in defaults:
            existing = cls.query.filter_by(name=default['name']).first()
            if not existing:
                category = cls(**default)
                db.session.add(category)

        db.session.commit()
        return cls.query.filter_by(active=True).order_by(cls.sort_order).all()

    def __repr__(self):
        return f'<OperatingCostCategory {self.name}>'


class OperatingCost(db.Model):
    """Einzelne Betriebskosten (Fixkosten)"""
    __tablename__ = 'operating_costs'

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('operating_cost_categories.id'), nullable=False)

    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    # Kosten
    amount = db.Column(db.Float, nullable=False)
    interval = db.Column(db.String(20), default='monthly')  # monthly, yearly, quarterly, one-time

    # Gültigkeitszeitraum
    valid_from = db.Column(db.Date)
    valid_to = db.Column(db.Date)
    active = db.Column(db.Boolean, default=True)

    # Verteilung
    distribute_over_machines = db.Column(db.Boolean, default=True)  # Auf alle Maschinen verteilen?
    specific_machine_id = db.Column(db.String(50), db.ForeignKey('machines.id'))  # Oder nur eine Maschine

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))

    # Relationships
    specific_machine = db.relationship('Machine', backref='specific_operating_costs')

    def get_monthly_amount(self):
        """Berechnet monatlichen Betrag"""
        if self.interval == 'monthly':
            return self.amount
        elif self.interval == 'yearly':
            return self.amount / 12
        elif self.interval == 'quarterly':
            return self.amount / 3
        elif self.interval == 'one-time':
            # Einmalkosten über 12 Monate verteilen
            return self.amount / 12
        return self.amount

    def get_hourly_rate(self, total_production_hours_per_month=160):
        """Berechnet Stundensatz für diese Kostenposition"""
        monthly_amount = self.get_monthly_amount()
        return monthly_amount / total_production_hours_per_month if total_production_hours_per_month > 0 else 0

    @classmethod
    def get_total_monthly_costs(cls):
        """Berechnet alle monatlichen Fixkosten"""
        costs = cls.query.filter_by(active=True).all()
        return sum(cost.get_monthly_amount() for cost in costs)

    @classmethod
    def get_total_hourly_rate(cls, total_production_hours_per_month=160):
        """Berechnet gesamten Fixkosten-Stundensatz"""
        total_monthly = cls.get_total_monthly_costs()
        return total_monthly / total_production_hours_per_month if total_production_hours_per_month > 0 else 0

    def __repr__(self):
        return f'<OperatingCost {self.name}: {self.amount}€/{self.interval}>'


class CalculationMode(db.Model):
    """Kalkulationsmodi (Einfach, Standard, Vollkosten, Custom)"""
    __tablename__ = 'calculation_modes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))
    color = db.Column(db.String(20))

    # Kalkulationskomponenten (JSON-Konfiguration)
    # Welche Komponenten sind in diesem Modus aktiv?
    components = db.Column(db.Text)  # JSON: {material: true, machine_time: true, labor: false, ...}

    # Standard-Einstellungen für diesen Modus
    default_profit_margin = db.Column(db.Float, default=30.0)  # %
    default_safety_buffer = db.Column(db.Float, default=5.0)  # %

    # System-Modi sind nicht löschbar
    is_system_mode = db.Column(db.Boolean, default=False)
    is_default = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))

    def get_components(self):
        """Gibt aktivierte Komponenten zurück"""
        if self.components:
            try:
                return json.loads(self.components)
            except:
                return {}
        return {}

    def set_components(self, components_dict):
        """Setzt aktivierte Komponenten"""
        self.components = json.dumps(components_dict, ensure_ascii=False)

    @classmethod
    def get_default_mode(cls):
        """Hole Standard-Kalkulationsmodus"""
        mode = cls.query.filter_by(is_default=True, active=True).first()
        if not mode:
            mode = cls.query.filter_by(name='simple', active=True).first()
        return mode

    @classmethod
    def initialize_system_modes(cls):
        """Erstellt die 4 System-Kalkulationsmodi"""
        modes = [
            {
                'name': 'simple',
                'display_name': 'Einfach',
                'description': 'Einfache Kalkulation mit Faktor auf Einkaufspreis. Schnell und unkompliziert.',
                'icon': 'calculator',
                'color': '#6c757d',
                'components': {
                    'base_factor': True,
                    'material_costs': False,
                    'machine_time': False,
                    'labor_costs': False,
                    'operating_costs': False,
                    'complexity_markup': False,
                    'quantity_discount': False
                },
                'default_profit_margin': 30.0,
                'is_system_mode': True,
                'is_default': True
            },
            {
                'name': 'standard',
                'display_name': 'Standard',
                'description': 'Standard-Kalkulation mit Material- und Maschinenkosten. Ausgewogen und realistisch.',
                'icon': 'gear',
                'color': '#0d6efd',
                'components': {
                    'base_factor': True,
                    'material_costs': True,
                    'machine_time': True,
                    'labor_costs': True,
                    'operating_costs': False,
                    'complexity_markup': True,
                    'quantity_discount': True
                },
                'default_profit_margin': 25.0,
                'is_system_mode': True
            },
            {
                'name': 'full_cost',
                'display_name': 'Vollkosten',
                'description': 'Vollkostenkalkulation mit allen Betriebskosten. Präzise und transparent.',
                'icon': 'clipboard-data',
                'color': '#198754',
                'components': {
                    'base_factor': True,
                    'material_costs': True,
                    'machine_time': True,
                    'labor_costs': True,
                    'operating_costs': True,
                    'complexity_markup': True,
                    'quantity_discount': True
                },
                'default_profit_margin': 20.0,
                'is_system_mode': True
            },
            {
                'name': 'custom',
                'display_name': 'Custom',
                'description': 'Individuelle Kalkulation - aktiviere nur die Komponenten, die du brauchst.',
                'icon': 'sliders',
                'color': '#d63384',
                'components': {
                    'base_factor': True,
                    'material_costs': True,
                    'machine_time': True,
                    'labor_costs': True,
                    'operating_costs': True,
                    'complexity_markup': True,
                    'quantity_discount': True
                },
                'default_profit_margin': 25.0,
                'is_system_mode': False  # Custom ist editierbar
            }
        ]

        for mode_data in modes:
            components = mode_data.pop('components')
            existing = cls.query.filter_by(name=mode_data['name']).first()

            if not existing:
                mode = cls(**mode_data)
                mode.set_components(components)
                db.session.add(mode)
            else:
                # Update bestehende Modi
                for key, value in mode_data.items():
                    setattr(existing, key, value)
                existing.set_components(components)

        db.session.commit()
        return cls.query.filter_by(active=True).all()

    def __repr__(self):
        return f'<CalculationMode {self.display_name}>'
