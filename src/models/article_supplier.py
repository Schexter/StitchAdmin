from datetime import datetime
from src.models.models import db


class ArticleSupplier(db.Model):
    """Verknüpfung zwischen Artikeln und Lieferanten mit lieferantenspezifischen Daten"""
    __tablename__ = 'article_suppliers'
    
    # Composite Primary Key
    article_id = db.Column(db.String(50), db.ForeignKey('articles.id'), primary_key=True)
    supplier_id = db.Column(db.String(50), db.ForeignKey('suppliers.id'), primary_key=True)
    
    # Lieferantenspezifische Artikeldaten
    supplier_article_number = db.Column(db.String(100))
    purchase_price = db.Column(db.Float, nullable=False)
    
    # Bestellkonditionen
    minimum_order_quantity = db.Column(db.Integer, default=1)
    quantity_unit = db.Column(db.String(20), default='Stück')  # Stück, Meter, kg, etc.
    packaging_unit = db.Column(db.Integer, default=1)  # Verpackungseinheit
    
    # Lieferzeiten
    delivery_time_days = db.Column(db.Integer)
    express_delivery_available = db.Column(db.Boolean, default=False)
    express_delivery_days = db.Column(db.Integer)
    express_surcharge_percent = db.Column(db.Float, default=0)
    
    # Status und Präferenzen
    active = db.Column(db.Boolean, default=True)
    preferred = db.Column(db.Boolean, default=False)  # Bevorzugter Lieferant für diesen Artikel
    
    # Verfügbarkeit
    availability_status = db.Column(db.String(20), default='available')  # available, limited, out_of_stock
    last_availability_check = db.Column(db.DateTime)
    next_availability_date = db.Column(db.Date)
    
    # Notizen
    notes = db.Column(db.Text)
    internal_notes = db.Column(db.Text)
    
    # Statistik
    last_order_date = db.Column(db.DateTime)
    total_ordered_quantity = db.Column(db.Float, default=0)
    average_delivery_time_days = db.Column(db.Float)
    quality_rating = db.Column(db.Integer)  # 1-5 Sterne
    
    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))
    
    # Relationships
    article = db.relationship('Article', backref=db.backref('supplier_articles', lazy='dynamic'))
    supplier = db.relationship('Supplier', backref=db.backref('article_suppliers', lazy='dynamic'))
    price_history = db.relationship('ArticleSupplierPriceHistory', backref='article_supplier', lazy='dynamic', 
                                  foreign_keys='ArticleSupplierPriceHistory.article_id, ArticleSupplierPriceHistory.supplier_id')
    
    def __repr__(self):
        return f'<ArticleSupplier {self.article_id}/{self.supplier_id}>'
    
    @property
    def current_price(self):
        """Aktueller Preis"""
        return self.purchase_price
    
    @property
    def total_cost(self, quantity=1):
        """Gesamtkosten für eine bestimmte Menge"""
        # Berücksichtigung der Mindestbestellmenge
        order_quantity = max(quantity, self.minimum_order_quantity or 1)
        return self.purchase_price * order_quantity
    
    def is_available(self):
        """Prüft ob der Artikel beim Lieferanten verfügbar ist"""
        return self.active and self.availability_status == 'available'
    
    def get_delivery_time(self, express=False):
        """Lieferzeit in Tagen"""
        if express and self.express_delivery_available:
            return self.express_delivery_days or 1
        return self.delivery_time_days or self.supplier.delivery_time_days or 7
    
    def get_price_with_express(self, express=False):
        """Preis inkl. Express-Zuschlag"""
        price = self.purchase_price
        if express and self.express_delivery_available and self.express_surcharge_percent:
            price *= (1 + self.express_surcharge_percent / 100)
        return price


class ArticleSupplierPriceHistory(db.Model):
    """Preishistorie für Artikel-Lieferanten-Kombinationen"""
    __tablename__ = 'article_supplier_price_history'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys für zusammengesetzten Schlüssel
    article_id = db.Column(db.String(50), nullable=False)
    supplier_id = db.Column(db.String(50), nullable=False)
    
    # Preisdaten
    price = db.Column(db.Float, nullable=False)
    previous_price = db.Column(db.Float)
    price_change_percent = db.Column(db.Float)
    
    # Gültigkeit
    valid_from = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    valid_until = db.Column(db.DateTime)
    
    # Zusatzinformationen
    reason = db.Column(db.String(200))  # Grund für Preisänderung
    notes = db.Column(db.Text)
    
    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    
    # Foreign Key Constraint
    __table_args__ = (
        db.ForeignKeyConstraint(
            ['article_id', 'supplier_id'],
            ['article_suppliers.article_id', 'article_suppliers.supplier_id']
        ),
    )
    
    def __repr__(self):
        return f'<PriceHistory {self.article_id}/{self.supplier_id}: {self.price}>'
    
    @classmethod
    def add_price_change(cls, article_id, supplier_id, new_price, old_price=None, reason=None, user=None):
        """Fügt einen neuen Preiseintrag zur Historie hinzu"""
        price_change = None
        if old_price and old_price > 0:
            price_change = ((new_price - old_price) / old_price) * 100
        
        history_entry = cls(
            article_id=article_id,
            supplier_id=supplier_id,
            price=new_price,
            previous_price=old_price,
            price_change_percent=price_change,
            reason=reason,
            created_by=user
        )
        
        db.session.add(history_entry)
        return history_entry