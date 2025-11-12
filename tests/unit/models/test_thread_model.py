"""
Unit Tests für Thread Model
Testet alle Garn-bezogenen Funktionalitäten
"""

import pytest
from src.models.models import Thread, db


@pytest.mark.unit
@pytest.mark.model
class TestThreadModel:
    """Test-Klasse für Thread Model"""

    def test_create_thread_basic(self, app):
        """Test: Basis-Garn erstellen"""
        with app.app_context():
            thread = Thread(
                id='THR001',
                manufacturer='Madeira',
                thread_type='Polyneon',
                color_number='1234',
                color_name_de='Rot',
                created_by='testuser'
            )
            db.session.add(thread)
            db.session.commit()

            assert thread.id == 'THR001'
            assert thread.manufacturer == 'Madeira'
            assert thread.product_line == 'Polyneon'
            assert thread.color_number == '1234'
            assert thread.color_name == 'Rot'

    def test_thread_with_stock(self, app):
        """Test: Garn mit Lagerbestand"""
        with app.app_context():
            thread = Thread(
                id='STOCK001',
                manufacturer='Madeira',
                color_number='5678',
                color_name_de='Blau',
                stock=50,
                unit='Spule',
                created_by='testuser'
            )
            db.session.add(thread)
            db.session.commit()

            assert thread.stock == 50
            assert thread.unit == 'Spule'

    def test_thread_with_pricing(self, app):
        """Test: Garn mit Preisinformationen"""
        with app.app_context():
            thread = Thread(
                id='PRICE001',
                manufacturer='Madeira',
                color_number='9999',
                color_name_de='Grün',
                price_per_unit=5.50,
                currency='EUR',
                created_by='testuser'
            )
            db.session.add(thread)
            db.session.commit()

            assert thread.price_per_unit == 5.50
            assert thread.currency == 'EUR'

    def test_thread_metadata(self, app):
        """Test: Garn Metadaten"""
        with app.app_context():
            thread = Thread(
                id='META001',
                manufacturer='Test',
                color_number='0000',
                color_name_de='Test',
                created_by='admin'
            )
            db.session.add(thread)
            db.session.commit()

            assert thread.created_by == 'admin'
            assert thread.created_at is not None

    def test_thread_repr(self, app):
        """Test: String-Repräsentation"""
        with app.app_context():
            thread = Thread(
                id='REPR001',
                manufacturer='Madeira',
                color_number='1111',
                color_name_de='Test Farbe'
            )

            repr_string = repr(thread)
            assert 'Thread' in repr_string or 'THR' in repr_string or 'REPR001' in repr_string

    def test_query_thread_by_id(self, app, test_thread):
        """Test: Garn per ID abfragen"""
        with app.app_context():
            thread = Thread.query.filter_by(id='THR001').first()
            assert thread is not None
            assert thread.id == 'THR001'

    def test_query_threads_by_brand(self, app):
        """Test: Garne nach Marke filtern"""
        with app.app_context():
            thread1 = Thread(id='BR001', manufacturer='Madeira', color_number='1', color_name_de='R1')
            thread2 = Thread(id='BR002', manufacturer='Isacord', color_number='2', color_name_de='R2')
            thread3 = Thread(id='BR003', manufacturer='Madeira', color_number='3', color_name_de='R3')

            db.session.add_all([thread1, thread2, thread3])
            db.session.commit()

            madeira_threads = Thread.query.filter_by(manufacturer='Madeira').all()
            assert len(madeira_threads) >= 2

    def test_low_stock_thread(self, app):
        """Test: Niedriger Garnbestand"""
        with app.app_context():
            thread = Thread(
                id='LOW001',
                manufacturer='Madeira',
                color_number='0001',
                color_name_de='Niedrig',
                stock=2,
                min_stock=10
            )
            db.session.add(thread)
            db.session.commit()

            assert thread.stock < thread.min_stock
