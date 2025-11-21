"""
Vollständige Datenbank-Models für StitchAdmin
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """Benutzer Model für Authentifizierung"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    # activities = db.relationship('ActivityLog', backref='user_obj', lazy='dynamic')  # Temporär deaktiviert
    
    def set_password(self, password):
        """Passwort hashen und speichern"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Passwort überprüfen"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Customer(db.Model):
    """Kunden Model"""
    __tablename__ = 'customers'
    
    id = db.Column(db.String(50), primary_key=True)
    customer_type = db.Column(db.String(20), default='private')  # private/business
    
    # Persönliche Daten
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    birth_date = db.Column(db.Date)
    
    # Firmendaten
    company_name = db.Column(db.String(200))
    contact_person = db.Column(db.String(100))
    department = db.Column(db.String(100))
    position = db.Column(db.String(100))
    tax_id = db.Column(db.String(50))
    vat_id = db.Column(db.String(50))
    
    # Kontaktdaten
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    mobile = db.Column(db.String(50))
    
    # Adresse
    street = db.Column(db.String(200))
    house_number = db.Column(db.String(20))
    postal_code = db.Column(db.String(20))
    city = db.Column(db.String(100))
    country = db.Column(db.String(100), default='Deutschland')
    
    # Sonstiges
    newsletter = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    
    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))
    
    # Relationships
    orders = db.relationship('Order', backref='customer', lazy='dynamic')
    
    @property
    def display_name(self):
        if self.customer_type == 'business':
            return self.company_name or 'Unbekannte Firma'
        else:
            return f"{self.first_name or ''} {self.last_name or ''}".strip() or 'Unbekannt'
    
    def get(self, key, default=None):
        """Kompatibilität mit Dictionary-Zugriff"""
        return getattr(self, key, default)
    
    def __repr__(self):
        return f'<Customer {self.id}: {self.display_name}>'


class Article(db.Model):
    """Artikel Model"""
    __tablename__ = 'articles'
    
    id = db.Column(db.String(50), primary_key=True)
    article_number = db.Column(db.String(100), unique=True)  # L-Shop Artikelnummer
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Kategorie und Marke (Foreign Keys)
    category_id = db.Column(db.Integer, db.ForeignKey('product_categories.id'))
    brand_id = db.Column(db.Integer, db.ForeignKey('brands.id'))
    
    # Alte Felder für Kompatibilität
    category = db.Column(db.String(100))  # Deprecated - use category_id
    brand = db.Column(db.String(100))     # Deprecated - use brand_id
    
    # Produktdetails
    material = db.Column(db.String(100))
    weight = db.Column(db.Float, default=0)
    color = db.Column(db.String(50))
    size = db.Column(db.String(50))
    
    # L-Shop Preise (Einkauf)
    purchase_price_single = db.Column(db.Float, default=0)  # Einzelpreis EK
    purchase_price_carton = db.Column(db.Float, default=0)  # Kartonpreis EK
    purchase_price_10carton = db.Column(db.Float, default=0)  # 10-Karton-Preis EK
    
    # Kalkulierte Verkaufspreise (ohne MwSt)
    price = db.Column(db.Float, default=0)  # VK aktuell (kann manuell überschrieben werden)
    price_calculated = db.Column(db.Float, default=0)  # VK kalkuliert (EK x Faktor)
    price_recommended = db.Column(db.Float, default=0)  # VK empfohlen (EK x Faktor)
    
    # Lager
    stock = db.Column(db.Integer, default=0)
    min_stock = db.Column(db.Integer, default=0)
    location = db.Column(db.String(100))
    
    # Lieferant
    supplier = db.Column(db.String(100))
    supplier_article_number = db.Column(db.String(100))  # Herstellernummer
    
    # Status
    active = db.Column(db.Boolean, default=True)
    
    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))
    
    # L-Shop spezifische Felder
    product_type = db.Column(db.String(100))
    manufacturer_number = db.Column(db.String(100))
    has_variants = db.Column(db.Boolean, default=False)
    units_per_carton = db.Column(db.Integer)
    catalog_page_texstyles = db.Column(db.Integer)
    catalog_page_corporate = db.Column(db.Integer)
    catalog_page_wahlbuch = db.Column(db.Integer)
    
    # Relationships
    order_items = db.relationship('OrderItem', backref='article', lazy='dynamic')
    variants = db.relationship('ArticleVariant', back_populates='article', lazy='dynamic', cascade='all, delete-orphan')
    # article_suppliers = db.relationship('ArticleSupplier', back_populates='article', lazy='dynamic', cascade='all, delete-orphan')  # Deaktiviert - wird durch article_supplier.py definiert
    
    def get(self, key, default=None):
        """Kompatibilität mit Dictionary-Zugriff"""
        return getattr(self, key, default)
    
    def calculate_prices(self, use_new_system=True):
        """Berechne VK-Preise basierend auf EK und erweiterten Einstellungen"""
        if use_new_system:
            try:
                # Importiere die neuen Settings-Models
                from .settings import PriceCalculationRule, TaxRate
                
                # Hole die passende Kalkulationsregel für diesen Artikel
                rule = PriceCalculationRule.get_rule_for_article(self)
                if not rule:
                    # Fallback auf alte Methode
                    return self._calculate_prices_legacy()
                
                # Verwende den niedrigsten EK-Preis als Basis
                base_price = self._get_best_purchase_price()
                if base_price <= 0:
                    return {'base_price': 0, 'calculated': 0, 'recommended': 0, 'calculated_with_tax': 0, 'recommended_with_tax': 0}
                
                # Hole Steuersatz
                tax_rate = rule.tax_rate.rate if rule.tax_rate else TaxRate.get_default_rate()
                tax_multiplier = 1 + (tax_rate / 100)
                
                # Berechne VK-Preise MIT Steuer: EK * Faktor * (1 + Steuersatz/100)
                calc_factor = rule.factor_calculated
                rec_factor = rule.factor_recommended
                
                self.price_calculated = round(base_price * calc_factor * tax_multiplier, 2)
                self.price_recommended = round(base_price * rec_factor * tax_multiplier, 2)
                
                # Setze aktuellen Preis auf kalkulierten Preis, wenn noch kein Preis gesetzt
                if not self.price:
                    self.price = self.price_calculated
                
                return {
                    'base_price': base_price,
                    'calculated': self.price_calculated,
                    'recommended': self.price_recommended,
                    'calculated_with_tax': self.price_calculated,  # Bereits inkl. MwSt
                    'recommended_with_tax': self.price_recommended,  # Bereits inkl. MwSt
                    'tax_rate': tax_rate,
                    'rule_used': rule.name
                }
                
            except (ImportError, Exception) as e:
                # Fallback wenn neue Models nicht verfügbar oder Tabellen nicht existieren
                print(f"Fehler bei erweiterter Preiskalkulation: {e}")
                return self._calculate_prices_legacy()
        else:
            return self._calculate_prices_legacy()
    
    def _get_best_purchase_price(self):
        """Ermittelt den EK-Einzelpreis als Basis für die Kalkulation"""
        # Verwende immer den Einzelpreis als Basis für die Kalkulation
        if self.purchase_price_single and self.purchase_price_single > 0:
            return self.purchase_price_single
        
        # Falls kein Einzelpreis vorhanden, verwende den Kartonpreis
        if self.purchase_price_carton and self.purchase_price_carton > 0:
            return self.purchase_price_carton
            
        # Als letztes den 10-Karton-Preis
        if self.purchase_price_10carton and self.purchase_price_10carton > 0:
            return self.purchase_price_10carton
        
        return 0
    
    def _calculate_prices_legacy(self):
        """Legacy Preiskalkulation (fallback)"""
        # Hole Kalkulationsfaktoren aus Einstellungen
        factor_calculated = PriceCalculationSettings.get_setting('price_factor_calculated', 1.5)
        factor_recommended = PriceCalculationSettings.get_setting('price_factor_recommended', 2.0)
        
        # Hole Steuersatz aus Einstellungen (Standard 19%)
        try:
            from .settings import TaxRate
            default_tax_rate = TaxRate.get_default_rate()
        except:
            default_tax_rate = PriceCalculationSettings.get_setting('default_tax_rate', 19.0)
        
        # Verwende den niedrigsten EK-Preis als Basis
        base_price = self._get_best_purchase_price()
        
        # Berechne VK-Preise: EK * Faktor * (1 + Steuersatz/100)
        tax_multiplier = 1 + (default_tax_rate / 100)
        self.price_calculated = round(base_price * factor_calculated * tax_multiplier, 2)
        self.price_recommended = round(base_price * rec_factor * tax_multiplier, 2)
        
        # Setze aktuellen Preis auf kalkulierten Preis, wenn noch kein Preis gesetzt
        if not self.price:
            self.price = self.price_calculated
        
        return {
            'base_price': base_price,
            'calculated': self.price_calculated,
            'recommended': self.price_recommended,
            'calculated_with_tax': self.price_calculated,  # Bereits inkl. MwSt
            'recommended_with_tax': self.price_recommended,  # Bereits inkl. MwSt
            'tax_rate': default_tax_rate,
            'rule_used': 'Legacy'
        }
    
    def __repr__(self):
        return f'<Article {self.article_number}: {self.name}>'


class Order(db.Model):
    """Aufträge Model"""
    __tablename__ = 'orders'
    
    id = db.Column(db.String(50), primary_key=True)
    customer_id = db.Column(db.String(50), db.ForeignKey('customers.id'))
    order_number = db.Column(db.String(50), unique=True)
    order_type = db.Column(db.String(20))  # embroidery, printing, dtf, combined
    status = db.Column(db.String(50), default='new')
    
    # Allgemeine Details
    description = db.Column(db.Text)
    internal_notes = db.Column(db.Text)
    customer_notes = db.Column(db.Text)
    
    # Stickerei-Details
    stitch_count = db.Column(db.Integer)
    design_width_mm = db.Column(db.Float)
    design_height_mm = db.Column(db.Float)
    embroidery_position = db.Column(db.String(100))
    embroidery_size = db.Column(db.String(50))
    thread_colors = db.Column(db.Text)  # Komma-getrennt
    selected_threads = db.Column(db.Text)  # JSON
    
    # Druck-Details
    print_width_cm = db.Column(db.Float)
    print_height_cm = db.Column(db.Float)
    print_method = db.Column(db.String(50))
    ink_coverage_percent = db.Column(db.Integer)
    print_colors = db.Column(db.Text)  # JSON
    
    # Design-Workflow (Erweiterte Felder)
    design_status = db.Column(db.String(50), default='none')  # none, customer_provided, needs_order, ordered, received, ready
    design_supplier_id = db.Column(db.String(50), db.ForeignKey('suppliers.id'))
    design_order_date = db.Column(db.Date)
    design_expected_date = db.Column(db.Date)
    design_received_date = db.Column(db.Date)
    design_order_notes = db.Column(db.Text)
    
    # Dateien
    design_file = db.Column(db.String(255))
    design_file_path = db.Column(db.String(255))  # Vollständiger Pfad zur Design-Datei
    design_thumbnail_path = db.Column(db.String(255))  # Thumbnail-Pfad
    production_file = db.Column(db.String(255))
    
    # Preise
    total_price = db.Column(db.Float, default=0)
    deposit_amount = db.Column(db.Float, default=0)
    discount_percent = db.Column(db.Float, default=0)
    
    # Termine
    due_date = db.Column(db.DateTime)
    rush_order = db.Column(db.Boolean, default=False)
    
    # Produktion
    assigned_machine_id = db.Column(db.String(50), db.ForeignKey('machines.id'))
    production_start = db.Column(db.DateTime)
    production_end = db.Column(db.DateTime)
    production_minutes = db.Column(db.Integer)
    
    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))
    completed_at = db.Column(db.DateTime)
    completed_by = db.Column(db.String(80))
    
    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    status_history = db.relationship('OrderStatusHistory', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    shipments = db.relationship('Shipment', backref='order', lazy='dynamic')
    design_supplier = db.relationship('Supplier', backref='design_orders', foreign_keys=[design_supplier_id])
    
    def get_selected_threads(self):
        """Gibt die ausgewählten Garne als Liste zurück"""
        if self.selected_threads:
            # Prüfe ob selected_threads bereits eine Liste ist
            if isinstance(self.selected_threads, list):
                return self.selected_threads
            # Wenn es ein String ist, parse es als JSON
            try:
                return json.loads(self.selected_threads)
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Fehler beim Parsen von selected_threads: {e}")
                return []
        return []
    
    def set_selected_threads(self, threads_list):
        """Speichert die ausgewählten Garne als JSON"""
        if threads_list is None:
            self.selected_threads = None
        else:
            self.selected_threads = json.dumps(threads_list)
    
    def can_start_production(self):
        """Prüft ob Auftrag produktionsbereit ist"""
        # Design-Check
        if self.design_status not in ['customer_provided', 'ready']:
            return False, "Design nicht verfügbar"
        
        # Weitere Validierungen können hier hinzugefügt werden
        # z.B. Materialverfügbarkeit, Maschinenkapazität, etc.
        
        return True, "OK"
    
    def get_design_status_display(self):
        """Gibt den Design-Status als benutzerfreundlichen Text zurück"""
        status_map = {
            'none': 'Kein Design',
            'customer_provided': 'Kunde bereitgestellt',
            'needs_order': 'Muss bestellt werden',
            'ordered': 'Bei Lieferant bestellt',
            'received': 'Vom Lieferant erhalten',
            'ready': 'Produktionsbereit'
        }
        return status_map.get(self.design_status, self.design_status)
    
    def get_design_status_badge_class(self):
        """Gibt die Bootstrap-Badge-Klasse für den Design-Status zurück"""
        badge_map = {
            'none': 'bg-danger',
            'customer_provided': 'bg-success',
            'needs_order': 'bg-warning',
            'ordered': 'bg-info',
            'received': 'bg-primary',
            'ready': 'bg-success'
        }
        return badge_map.get(self.design_status, 'bg-secondary')
    
    def has_design_file(self):
        """Prüft ob eine Design-Datei vorhanden ist"""
        return bool(self.design_file_path or self.design_file)
    
    def needs_design_order(self):
        """Prüft ob ein Design beim Lieferanten bestellt werden muss"""
        return self.design_status == 'needs_order'
    
    def is_design_in_progress(self):
        """Prüft ob Design-Bestellung im Gange ist"""
        return self.design_status == 'ordered'
    
    def is_design_ready(self):
        """Prüft ob Design produktionsbereit ist"""
        return self.design_status in ['customer_provided', 'ready']
    
    def get(self, key, default=None):
        """Kompatibilität mit Dictionary-Zugriff"""
        return getattr(self, key, default)
    
    def __repr__(self):
        return f'<Order {self.order_number}>'


class OrderItem(db.Model):
    """Auftragspositionen Model"""
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50), db.ForeignKey('orders.id'), nullable=False)
    article_id = db.Column(db.String(50), db.ForeignKey('articles.id'))
    
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, default=0)
    
    # Details
    textile_size = db.Column(db.String(20))
    textile_color = db.Column(db.String(50))
    position_details = db.Column(db.Text)
    
    # Lieferanten-Bestellstatus
    supplier_order_status = db.Column(db.String(50), default='none')  # none, to_order, ordered, delivered
    supplier_order_id = db.Column(db.String(50), db.ForeignKey('supplier_orders.id', ondelete='SET NULL'))
    supplier_order_date = db.Column(db.Date)
    supplier_expected_date = db.Column(db.Date)
    supplier_delivered_date = db.Column(db.Date)
    supplier_order_notes = db.Column(db.Text)
    
    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    supplier_order = db.relationship('SupplierOrder', backref='linked_order_items', foreign_keys=[supplier_order_id])
    
    def __repr__(self):
        return f'<OrderItem {self.id}: {self.quantity}x {self.article_id}>'


class OrderStatusHistory(db.Model):
    """Auftrags-Status-Historie"""
    __tablename__ = 'order_status_history'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50), db.ForeignKey('orders.id'), nullable=False)
    
    from_status = db.Column(db.String(50))
    to_status = db.Column(db.String(50), nullable=False)
    comment = db.Column(db.Text)
    
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    changed_by = db.Column(db.String(80))
    
    def __repr__(self):
        return f'<StatusHistory {self.order_id}: {self.from_status} -> {self.to_status}>'


class Machine(db.Model):
    """Maschinen Model"""
    __tablename__ = 'machines'

    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50))  # embroidery, printing, dtf

    # Maschinendetails
    manufacturer = db.Column(db.String(100))
    model = db.Column(db.String(100))
    serial_number = db.Column(db.String(100))
    purchase_date = db.Column(db.Date)

    # Stickmaschinen-Details
    num_heads = db.Column(db.Integer, default=1)
    needles_per_head = db.Column(db.Integer, default=15)
    max_speed = db.Column(db.Integer, default=1000)
    max_area_width = db.Column(db.Integer)  # mm
    max_area_height = db.Column(db.Integer)  # mm
    
    # Konfiguration
    thread_setup = db.Column(db.Text)  # JSON
    default_settings = db.Column(db.Text)  # JSON
    
    # Status
    status = db.Column(db.String(50), default='active')
    maintenance_due = db.Column(db.Date)
    
    # Zeiten
    setup_time_minutes = db.Column(db.Integer, default=15)
    thread_change_time_minutes = db.Column(db.Integer, default=3)
    hoop_change_time_minutes = db.Column(db.Integer, default=5)

    # NEUE FELDER: Kosten & Kalkulation
    # Anschaffung
    purchase_price = db.Column(db.Float)  # Anschaffungspreis
    depreciation_years = db.Column(db.Integer, default=10)  # Abschreibungsdauer
    expected_lifetime_hours = db.Column(db.Integer, default=20000)  # Erwartete Nutzungsdauer

    # Betriebskosten pro Stunde
    energy_cost_per_hour = db.Column(db.Float, default=2.0)  # Stromkosten €/h
    maintenance_cost_per_hour = db.Column(db.Float, default=1.5)  # Wartung €/h
    space_cost_per_hour = db.Column(db.Float, default=0.5)  # Platzkosten €/h

    # Kalkulierter Maschinenstundensatz (wird automatisch berechnet)
    calculated_hourly_rate = db.Column(db.Float)
    custom_hourly_rate = db.Column(db.Float)  # Manuell überschreibbar
    use_custom_rate = db.Column(db.Boolean, default=False)

    # Personalkostensatz für diese Maschine
    labor_cost_per_hour = db.Column(db.Float, default=35.0)  # Lohnkosten €/h

    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))
    
    # Relationships
    orders = db.relationship('Order', backref='assigned_machine', lazy='dynamic')
    schedules = db.relationship('ProductionSchedule', backref='machine', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_thread_setup(self):
        """Gibt die Thread-Konfiguration als Liste zurück"""
        if self.thread_setup:
            # Prüfe ob thread_setup bereits eine Liste ist
            if isinstance(self.thread_setup, list):
                return self.thread_setup
            # Wenn es ein String ist, parse es als JSON
            try:
                return json.loads(self.thread_setup)
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Fehler beim Parsen von thread_setup: {e}")
                return []
        return []
    
    def set_thread_setup(self, setup_list):
        """Speichert die Thread-Konfiguration als JSON"""
        if setup_list is None:
            self.thread_setup = None
        else:
            self.thread_setup = json.dumps(setup_list)
    
    def get(self, key, default=None):
        """Kompatibilität mit Dictionary-Zugriff"""
        return getattr(self, key, default)

    def calculate_hourly_rate(self):
        """
        Berechnet den Maschinenstundensatz automatisch

        Formel:
        Stundensatz = Abschreibung/h + Energiekosten/h + Wartung/h + Platzkosten/h
        """
        depreciation_per_hour = 0.0
        if self.purchase_price and self.expected_lifetime_hours and self.expected_lifetime_hours > 0:
            depreciation_per_hour = self.purchase_price / self.expected_lifetime_hours

        energy = self.energy_cost_per_hour or 0.0
        maintenance = self.maintenance_cost_per_hour or 0.0
        space = self.space_cost_per_hour or 0.0

        self.calculated_hourly_rate = depreciation_per_hour + energy + maintenance + space
        return self.calculated_hourly_rate

    def get_hourly_rate(self):
        """
        Gibt den effektiven Maschinenstundensatz zurück
        Custom Rate wird bevorzugt, wenn aktiviert
        """
        if self.use_custom_rate and self.custom_hourly_rate:
            return self.custom_hourly_rate

        if not self.calculated_hourly_rate:
            return self.calculate_hourly_rate()

        return self.calculated_hourly_rate

    def get_labor_cost_per_hour(self):
        """Gibt Personalkostensatz zurück"""
        return self.labor_cost_per_hour or 35.0

    def __repr__(self):
        return f'<Machine {self.name}>'


class ProductionSchedule(db.Model):
    """Produktionsplanung Model"""
    __tablename__ = 'production_schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.String(50), db.ForeignKey('machines.id'), nullable=False)
    order_id = db.Column(db.String(50), db.ForeignKey('orders.id'))
    
    # Zeitplanung
    scheduled_start = db.Column(db.DateTime, nullable=False)
    scheduled_end = db.Column(db.DateTime, nullable=False)
    actual_start = db.Column(db.DateTime)
    actual_end = db.Column(db.DateTime)
    
    # Details
    status = db.Column(db.String(50), default='scheduled')  # scheduled, in_progress, completed, cancelled
    priority = db.Column(db.Integer, default=5)  # 1-10, 1 = höchste
    notes = db.Column(db.Text)
    
    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))
    
    # Relationships
    # machine relationship ist bereits in Machine model definiert
    order = db.relationship('Order', backref='production_schedules')
    
    def __repr__(self):
        return f'<Schedule {self.id}: {self.machine_id} - {self.scheduled_start}>'


class Thread(db.Model):
    """Garne/Farben Model"""
    __tablename__ = 'threads'
    
    id = db.Column(db.String(50), primary_key=True)
    manufacturer = db.Column(db.String(100), nullable=False)
    thread_type = db.Column(db.String(100))
    color_number = db.Column(db.String(50), nullable=False)
    
    # Farbnamen
    color_name_de = db.Column(db.String(100))
    color_name_en = db.Column(db.String(100))
    
    # Farbwerte
    hex_color = db.Column(db.String(7))
    pantone = db.Column(db.String(50))
    rgb_r = db.Column(db.Integer)
    rgb_g = db.Column(db.Integer)
    rgb_b = db.Column(db.Integer)
    
    # Details
    category = db.Column(db.String(50), default='Standard')
    weight = db.Column(db.Integer, default=40)  # z.B. 40 für No.40
    material = db.Column(db.String(50))  # Polyester, Rayon, etc.
    
    # Preis
    price = db.Column(db.Float, default=0)
    supplier = db.Column(db.String(100))
    supplier_article_number = db.Column(db.String(100))
    
    # Status
    active = db.Column(db.Boolean, default=True)
    discontinued = db.Column(db.Boolean, default=False)
    
    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))
    
    # Relationships
    stock = db.relationship('ThreadStock', backref='thread', uselist=False, cascade='all, delete-orphan')
    usage_history = db.relationship('ThreadUsage', backref='thread', lazy='dynamic')
    
    def get(self, key, default=None):
        """Kompatibilität mit Dictionary-Zugriff"""
        return getattr(self, key, default)
    
    def __repr__(self):
        return f'<Thread {self.manufacturer} {self.color_number}>'


class ThreadStock(db.Model):
    """Garnbestand Model"""
    __tablename__ = 'thread_stock'
    
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.String(50), db.ForeignKey('threads.id'), nullable=False)
    
    quantity = db.Column(db.Integer, default=0)
    min_stock = db.Column(db.Integer, default=5)
    location = db.Column(db.String(100))
    
    # Bestellinfo
    last_order_date = db.Column(db.Date)
    supplier_order_number = db.Column(db.String(100))
    
    # Metadaten
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))
    
    def __repr__(self):
        return f'<ThreadStock {self.thread_id}: {self.quantity}>'


class ThreadUsage(db.Model):
    """Garnverbrauch Model"""
    __tablename__ = 'thread_usage'

    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.String(50), db.ForeignKey('threads.id'), nullable=False)
    order_id = db.Column(db.String(50), db.ForeignKey('orders.id'))
    machine_id = db.Column(db.String(50), db.ForeignKey('machines.id'))

    quantity_used = db.Column(db.Float, default=0)  # in Meter oder Konen
    usage_type = db.Column(db.String(50))  # production, test, waste, correction

    # Metadaten
    used_at = db.Column(db.DateTime, default=datetime.utcnow)
    recorded_by = db.Column(db.String(80))
    notes = db.Column(db.Text)

    # Relationships
    thread = db.relationship('Thread', backref='usage_records')
    order = db.relationship('Order', backref='thread_usage_records')
    machine = db.relationship('Machine', backref='thread_usage_records')

    def __repr__(self):
        return f'<ThreadUsage {self.thread_id}: {self.quantity_used}m on {self.machine_id}>'


class Shipment(db.Model):
    """Versand Model"""
    __tablename__ = 'shipments'
    
    id = db.Column(db.String(50), primary_key=True)
    order_id = db.Column(db.String(50), db.ForeignKey('orders.id'))
    
    # Versanddetails
    tracking_number = db.Column(db.String(100))
    carrier = db.Column(db.String(50))  # DHL, DPD, etc.
    service = db.Column(db.String(50))  # Express, Standard, etc.
    
    # Paketdetails
    weight = db.Column(db.Float)  # kg
    length = db.Column(db.Float)  # cm
    width = db.Column(db.Float)   # cm
    height = db.Column(db.Float)  # cm
    
    # Status
    status = db.Column(db.String(50), default='created')
    shipped_date = db.Column(db.DateTime)
    delivered_date = db.Column(db.DateTime)
    
    # Kosten
    shipping_cost = db.Column(db.Float, default=0)
    insurance_value = db.Column(db.Float)
    
    # Empfänger
    recipient_name = db.Column(db.String(200))
    recipient_street = db.Column(db.String(200))
    recipient_postal_code = db.Column(db.String(20))
    recipient_city = db.Column(db.String(100))
    recipient_country = db.Column(db.String(100), default='Deutschland')
    
    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('ShipmentItem', backref='shipment', lazy='dynamic', cascade='all, delete-orphan')
    
    def get(self, key, default=None):
        """Kompatibilität mit Dictionary-Zugriff"""
        return getattr(self, key, default)
    
    def __repr__(self):
        return f'<Shipment {self.tracking_number or self.id}>'


class ShipmentItem(db.Model):
    """Versand-Positionen Model"""
    __tablename__ = 'shipment_items'
    
    id = db.Column(db.Integer, primary_key=True)
    shipment_id = db.Column(db.String(50), db.ForeignKey('shipments.id'), nullable=False)
    order_item_id = db.Column(db.Integer, db.ForeignKey('order_items.id'))
    
    quantity = db.Column(db.Integer, default=1)
    description = db.Column(db.String(200))
    
    def __repr__(self):
        return f'<ShipmentItem {self.id}>'


class Supplier(db.Model):
    """Lieferanten Model"""
    __tablename__ = 'suppliers'
    
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    
    # Kontakt
    contact_person = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    website = db.Column(db.String(200))
    
    # Adresse
    street = db.Column(db.String(200))
    postal_code = db.Column(db.String(20))
    city = db.Column(db.String(100))
    country = db.Column(db.String(100))
    
    # Details
    tax_id = db.Column(db.String(50))
    customer_number = db.Column(db.String(100))  # Unsere Kundennummer beim Lieferanten
    payment_terms = db.Column(db.String(100))
    delivery_time_days = db.Column(db.Integer)
    minimum_order_value = db.Column(db.Float)
    
    # Webshop-Integration
    webshop_url = db.Column(db.String(500))
    webshop_username = db.Column(db.String(100))
    webshop_password_encrypted = db.Column(db.String(500))
    webshop_type = db.Column(db.String(50))  # generic, shopware, woocommerce, etc.
    webshop_article_url_pattern = db.Column(db.String(500))  # z.B. https://shop.de/artikel/{article_number}
    auto_order_enabled = db.Column(db.Boolean, default=False)
    webshop_notes = db.Column(db.Text)
    
    # Retourenadresse
    return_street = db.Column(db.String(200))
    return_postal_code = db.Column(db.String(20))
    return_city = db.Column(db.String(100))
    return_country = db.Column(db.String(100))
    return_contact = db.Column(db.String(100))
    return_phone = db.Column(db.String(50))
    return_notes = db.Column(db.Text)
    
    # Status
    active = db.Column(db.Boolean, default=True)
    preferred = db.Column(db.Boolean, default=False)
    
    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    orders = db.relationship('SupplierOrder', backref='supplier', lazy='dynamic')
    
    def __repr__(self):
        return f'<Supplier {self.name}>'


class SupplierOrder(db.Model):
    """Lieferanten-Bestellungen Model"""
    __tablename__ = 'supplier_orders'
    
    id = db.Column(db.String(50), primary_key=True)
    supplier_id = db.Column(db.String(50), db.ForeignKey('suppliers.id'), nullable=False)
    
    # Bestellinformationen
    order_number = db.Column(db.String(100))
    supplier_order_number = db.Column(db.String(100))  # Bestellnummer des Lieferanten
    order_date = db.Column(db.Date)
    delivery_date = db.Column(db.Date)
    
    # Status
    status = db.Column(db.String(50), default='draft')  # draft, ordered, confirmed, shipped, delivered, cancelled
    
    # Versand
    shipping_method = db.Column(db.String(100))
    tracking_number = db.Column(db.String(200))
    
    # Kosten
    subtotal = db.Column(db.Float, default=0)
    shipping_cost = db.Column(db.Float, default=0)
    tax_amount = db.Column(db.Float, default=0)
    discount_amount = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, default=0)
    currency = db.Column(db.String(3), default='EUR')
    
    # Zahlungsinformationen
    payment_method = db.Column(db.String(50))  # invoice, credit_card, paypal, etc.
    payment_status = db.Column(db.String(50), default='pending')  # pending, paid, partial, overdue
    payment_date = db.Column(db.Date)
    invoice_number = db.Column(db.String(100))
    
    # Details
    items = db.Column(db.Text)  # JSON mit Bestellpositionen
    notes = db.Column(db.Text)
    internal_notes = db.Column(db.Text)
    
    # Lieferadresse (falls abweichend)
    delivery_name = db.Column(db.String(200))
    delivery_street = db.Column(db.String(200))
    delivery_postal_code = db.Column(db.String(20))
    delivery_city = db.Column(db.String(100))
    delivery_country = db.Column(db.String(100))
    
    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))
    
    def get_items(self):
        """Gibt die Bestellpositionen als Liste zurück"""
        if self.items:
            try:
                items_list = json.loads(self.items)
                # Berechne line_total für jedes Item
                for item in items_list:
                    quantity = float(item.get('quantity', 1))
                    unit_price = float(item.get('unit_price', 0))
                    discount = float(item.get('discount', 0))
                    item['line_total'] = (quantity * unit_price) - discount
                return items_list
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    def set_items(self, items_list):
        """Speichert die Bestellpositionen als JSON"""
        if items_list is None:
            self.items = None
        else:
            self.items = json.dumps(items_list, ensure_ascii=False)
    
    def calculate_total(self):
        """Berechnet den Gesamtbetrag"""
        self.total_amount = (self.subtotal or 0) + (self.shipping_cost or 0) + \
                           (self.tax_amount or 0) - (self.discount_amount or 0)
        return self.total_amount
    
    def __repr__(self):
        return f'<SupplierOrder {self.order_number}>'


class ActivityLog(db.Model):
    """Aktivitätsprotokoll Model"""
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), name='username')  # Geändert von 'user' zu 'username'
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    
    # Request-Details
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(200))
    
    # Zeitstempel
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<Activity {self.username} - {self.action}>'


class ProductCategory(db.Model):
    """Produktkategorien für Artikel"""
    __tablename__ = 'product_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('product_categories.id'), nullable=True)
    active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    parent = db.relationship('ProductCategory', remote_side=[id], backref='subcategories')
    articles = db.relationship('Article', backref='category_obj', lazy='dynamic')
    
    def __repr__(self):
        return f'<ProductCategory {self.name}>'


class Brand(db.Model):
    """Marken/Hersteller für Artikel"""
    __tablename__ = 'brands'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    logo_url = db.Column(db.String(255))
    website = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    articles = db.relationship('Article', backref='brand_obj', lazy='dynamic')
    
    def __repr__(self):
        return f'<Brand {self.name}>'


class PriceCalculationSettings(db.Model):
    """Einstellungen für Preiskalkulationen"""
    __tablename__ = 'price_calculation_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255))
    
    # Timestamps
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))
    
    @classmethod
    def get_setting(cls, name, default=None):
        """Hole eine Einstellung oder gib Default zurück"""
        setting = cls.query.filter_by(name=name).first()
        return setting.value if setting else default
    
    @classmethod
    def set_setting(cls, name, value, description=None, user=None):
        """Setze oder update eine Einstellung"""
        setting = cls.query.filter_by(name=name).first()
        if not setting:
            setting = cls(name=name, description=description)
            db.session.add(setting)
        setting.value = value
        setting.updated_by = user
        db.session.commit()
        return setting
    
    def __repr__(self):
        return f'<PriceCalculationSettings {self.name}={self.value}>'

from .sumup_token import SumUpToken
