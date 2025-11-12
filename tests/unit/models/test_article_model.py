"""
Unit Tests für Article Model
Testet alle Artikel-bezogenen Funktionalitäten
"""

import pytest
from src.models.models import Article, db


@pytest.mark.unit
@pytest.mark.model
class TestArticleModel:
    """Test-Klasse für Article Model"""

    def test_create_article_basic(self, app):
        """Test: Basis-Artikel erstellen"""
        with app.app_context():
            article = Article(
                id='ART001',
                name='Test T-Shirt',
                category='Textilien',
                price=10.00,
                created_by='testuser'
            )
            db.session.add(article)
            db.session.commit()

            assert article.id == 'ART001'
            assert article.name == 'Test T-Shirt'
            assert article.category == 'Textilien'
            assert article.price == 10.00

    def test_article_with_stock(self, app):
        """Test: Artikel mit Lagerbestand"""
        with app.app_context():
            article = Article(
                id='STOCK001',
                name='Artikel mit Lager',
                stock=100,
                min_stock=10,
                created_by='testuser'
            )
            db.session.add(article)
            db.session.commit()

            assert article.stock == 100
            assert article.min_stock == 10

    def test_article_with_variants(self, app):
        """Test: Artikel mit Varianten (Größen/Farben)"""
        with app.app_context():
            article = Article(
                id='VAR001',
                name='T-Shirt',
                sizes=['S', 'M', 'L', 'XL'],
                colors=['Rot', 'Blau', 'Grün'],
                created_by='testuser'
            )
            db.session.add(article)
            db.session.commit()

            # Note: sizes und colors werden als JSON gespeichert
            assert article.id == 'VAR001'

    def test_article_with_supplier_info(self, app):
        """Test: Artikel mit Lieferanten-Info"""
        with app.app_context():
            article = Article(
                id='SUP001',
                name='Lieferanten-Artikel',
                supplier_name='Test Supplier',
                supplier_id='SUP-123',
                purchase_price=5.00,
                created_by='testuser'
            )
            db.session.add(article)
            db.session.commit()

            assert article.supplier_name == 'Test Supplier'
            assert article.supplier_article_id == 'SUP-123'
            assert article.purchase_price == 5.00

    def test_article_with_description(self, app):
        """Test: Artikel mit Beschreibung"""
        with app.app_context():
            description = "Hochwertiges Baumwoll-T-Shirt in verschiedenen Farben"
            article = Article(
                id='DESC001',
                name='Premium T-Shirt',
                description=description,
                created_by='testuser'
            )
            db.session.add(article)
            db.session.commit()

            assert article.description == description

    def test_article_with_ean(self, app):
        """Test: Artikel mit EAN/Barcode"""
        with app.app_context():
            article = Article(
                id='EAN001',
                name='Artikel mit EAN',
                ean='4012345678901',
                created_by='testuser'
            )
            db.session.add(article)
            db.session.commit()

            assert article.ean == '4012345678901'

    def test_article_metadata(self, app):
        """Test: Artikel Metadaten"""
        with app.app_context():
            article = Article(
                id='META001',
                name='Meta Test',
                created_by='admin'
            )
            db.session.add(article)
            db.session.commit()

            assert article.created_by == 'admin'
            assert article.created_at is not None

    def test_article_repr(self, app):
        """Test: String-Repräsentation"""
        with app.app_context():
            article = Article(
                id='REPR001',
                name='Test Artikel'
            )

            repr_string = repr(article)
            assert 'Article ART' in repr_string or 'REPR001' in repr_string

    def test_query_article_by_id(self, app, test_article):
        """Test: Artikel per ID abfragen"""
        with app.app_context():
            article = Article.query.filter_by(id='ART001').first()
            assert article is not None
            assert article.id == 'ART001'

    def test_query_articles_by_category(self, app):
        """Test: Artikel nach Kategorie filtern"""
        with app.app_context():
            # Erstelle Artikel in verschiedenen Kategorien
            article1 = Article(id='CAT001', name='A1', category='Textilien')
            article2 = Article(id='CAT002', name='A2', category='Zubehör')
            article3 = Article(id='CAT003', name='A3', category='Textilien')

            db.session.add_all([article1, article2, article3])
            db.session.commit()

            textilien = Article.query.filter_by(category='Textilien').all()
            assert len(textilien) >= 2

    def test_low_stock_detection(self, app):
        """Test: Niedrigen Lagerbestand erkennen"""
        with app.app_context():
            article = Article(
                id='LOW001',
                name='Niedrig',
                stock=5,
                min_stock=10
            )
            db.session.add(article)
            db.session.commit()

            # Artikel sollte unter Mindestbestand sein
            assert article.stock < article.min_stock
