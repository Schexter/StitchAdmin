"""
Article Variant Model
Fuer L-Shop Artikel mit Farb- und Groessenvarianten
"""

from datetime import datetime
from src.models import db


class ArticleVariant(db.Model):
    """Artikel-Varianten (Farbe/Groesse Kombinationen)"""
    __tablename__ = 'article_variants'

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.String(50), db.ForeignKey('articles.id', ondelete='CASCADE'), nullable=False)
    variant_type = db.Column(db.String(20), nullable=False)  # 'color', 'size', 'color_size'
    color = db.Column(db.String(100))
    size = db.Column(db.String(100))
    ean = db.Column(db.String(20))
    single_price = db.Column(db.Float)
    carton_price = db.Column(db.Float)
    ten_carton_price = db.Column(db.Float)
    units_per_carton = db.Column(db.Integer)
    stock = db.Column(db.Integer, default=0)
    min_stock = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)

    # Audit fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))

    # Relationships
    article = db.relationship('Article', back_populates='variants')

    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('article_id', 'color', 'size', name='uq_article_color_size'),
    )

    def __repr__(self):
        return f'<ArticleVariant {self.article_id} - {self.color}/{self.size}>'

    @property
    def variant_number(self):
        """Generierte Varianten-Nummer aus Artikel-ID + Farbe/Groesse"""
        parts = [self.article_id or '']
        if self.color:
            parts.append(self.color)
        if self.size:
            parts.append(self.size)
        return '-'.join(parts)

    @property
    def is_main_variant(self):
        """True wenn dies die erste (aelteste) Variante des Artikels ist"""
        if not self.article_id or not self.id:
            return False
        first = ArticleVariant.query.filter_by(
            article_id=self.article_id
        ).order_by(ArticleVariant.id).first()
        return first and first.id == self.id

    @property
    def purchase_price_single(self):
        """Alias fuer Template-Kompatibilitaet"""
        return self.single_price or 0

    @property
    def purchase_price_carton(self):
        """Alias fuer Template-Kompatibilitaet"""
        return self.carton_price or 0

    @property
    def price(self):
        """Verkaufspreis (EK * Aufschlag vom Hauptartikel oder Faktor 2.0)"""
        if not self.single_price:
            return 0
        if self.article:
            # Aufschlagfaktor vom Hauptartikel berechnen
            if self.article.purchase_price_single and self.article.purchase_price_single > 0 and self.article.price:
                factor = self.article.price / self.article.purchase_price_single
                return round(self.single_price * factor, 2)
        return round(self.single_price * 2.0, 2)

    @property
    def display_name(self):
        """Anzeigename der Variante"""
        parts = []
        if self.color:
            parts.append(self.color)
        if self.size:
            parts.append(self.size)
        return " / ".join(parts) if parts else "Standard"

    @property
    def best_price(self):
        """Guenstigster verfuegbarer Preis"""
        prices = [p for p in [self.single_price, self.carton_price, self.ten_carton_price] if p]
        return min(prices) if prices else 0

    def get_price_for_quantity(self, quantity):
        """Berechne Preis basierend auf Menge"""
        if quantity >= 10 and self.ten_carton_price:
            return self.ten_carton_price * quantity
        elif quantity >= 1 and self.carton_price:
            return self.carton_price * quantity
        elif self.single_price:
            return self.single_price * quantity
        return 0

    def to_dict(self):
        """Konvertiere zu Dictionary fuer JSON"""
        return {
            'id': self.id,
            'article_id': self.article_id,
            'variant_type': self.variant_type,
            'variant_number': self.variant_number,
            'color': self.color,
            'size': self.size,
            'ean': self.ean,
            'single_price': self.single_price,
            'carton_price': self.carton_price,
            'ten_carton_price': self.ten_carton_price,
            'units_per_carton': self.units_per_carton,
            'stock': self.stock,
            'min_stock': self.min_stock,
            'active': self.active,
            'display_name': self.display_name,
            'price': self.price,
        }
