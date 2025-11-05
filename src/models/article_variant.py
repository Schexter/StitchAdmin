"""
Article Variant Model
Für L-Shop Artikel mit Farb- und Größenvarianten
"""

from datetime import datetime
from src.models import db

class ArticleVariant(db.Model):
    """Artikel-Varianten (Farbe/Größe Kombinationen)"""
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
    stock = db.Column(db.Integer, default=0)
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
    def display_name(self):
        """Anzeigename der Variante"""
        parts = []
        if self.color:
            parts.append(f"Farbe: {self.color}")
        if self.size:
            parts.append(f"Größe: {self.size}")
        return " | ".join(parts) if parts else "Standard"
    
    @property
    def best_price(self):
        """Günstigster verfügbarer Preis"""
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
        """Konvertiere zu Dictionary für JSON"""
        return {
            'id': self.id,
            'article_id': self.article_id,
            'variant_type': self.variant_type,
            'color': self.color,
            'size': self.size,
            'ean': self.ean,
            'single_price': self.single_price,
            'carton_price': self.carton_price,
            'ten_carton_price': self.ten_carton_price,
            'stock': self.stock,
            'active': self.active,
            'display_name': self.display_name
        }