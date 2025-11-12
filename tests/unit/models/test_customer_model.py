"""
Unit Tests für Customer Model
Testet alle Customer-bezogenen Funktionalitäten
"""

import pytest
from datetime import date
from src.models.models import Customer, db


@pytest.mark.unit
@pytest.mark.model
class TestCustomerModel:
    """Test-Klasse für Customer Model"""

    def test_create_private_customer(self, app):
        """Test: Privatkunde erstellen"""
        with app.app_context():
            customer = Customer(
                id='PRIV001',
                customer_type='private',
                first_name='Max',
                last_name='Mustermann',
                email='max@example.com',
                phone='0123456789',
                created_by='testuser'
            )
            db.session.add(customer)
            db.session.commit()

            # Assertions
            assert customer.id == 'PRIV001'
            assert customer.customer_type == 'private'
            assert customer.first_name == 'Max'
            assert customer.last_name == 'Mustermann'
            assert customer.email == 'max@example.com'

    def test_create_business_customer(self, app):
        """Test: Geschäftskunde erstellen"""
        with app.app_context():
            customer = Customer(
                id='BUS001',
                customer_type='business',
                company_name='Test GmbH',
                contact_person='Anna Schmidt',
                department='Einkauf',
                tax_id='DE123456789',
                vat_id='DE987654321',
                email='info@test-gmbh.de',
                created_by='testuser'
            )
            db.session.add(customer)
            db.session.commit()

            # Assertions
            assert customer.id == 'BUS001'
            assert customer.customer_type == 'business'
            assert customer.company_name == 'Test GmbH'
            assert customer.contact_person == 'Anna Schmidt'
            assert customer.tax_id == 'DE123456789'
            assert customer.vat_id == 'DE987654321'

    def test_customer_display_name_private(self, app):
        """Test: Display Name für Privatkunden"""
        with app.app_context():
            customer = Customer(
                id='TEST001',
                customer_type='private',
                first_name='Max',
                last_name='Mustermann'
            )

            assert customer.display_name == 'Max Mustermann'

    def test_customer_display_name_business(self, app):
        """Test: Display Name für Geschäftskunden"""
        with app.app_context():
            customer = Customer(
                id='TEST002',
                customer_type='business',
                company_name='Musterfirma GmbH'
            )

            assert customer.display_name == 'Musterfirma GmbH'

    def test_customer_with_address(self, app):
        """Test: Kunde mit vollständiger Adresse"""
        with app.app_context():
            customer = Customer(
                id='ADDR001',
                customer_type='private',
                first_name='Anna',
                last_name='Schmidt',
                street='Hauptstraße',
                house_number='42',
                postal_code='12345',
                city='Berlin',
                country='Deutschland'
            )
            db.session.add(customer)
            db.session.commit()

            assert customer.street == 'Hauptstraße'
            assert customer.house_number == '42'
            assert customer.postal_code == '12345'
            assert customer.city == 'Berlin'
            assert customer.country == 'Deutschland'

    def test_customer_newsletter_opt_in(self, app):
        """Test: Newsletter-Anmeldung"""
        with app.app_context():
            customer = Customer(
                id='NEWS001',
                customer_type='private',
                first_name='Test',
                last_name='User',
                newsletter=True
            )
            db.session.add(customer)
            db.session.commit()

            assert customer.newsletter is True

    def test_customer_with_notes(self, app):
        """Test: Kunde mit Notizen"""
        with app.app_context():
            notes_text = "Wichtiger Kunde. Immer schnelle Lieferung gewünscht."
            customer = Customer(
                id='NOTE001',
                customer_type='private',
                first_name='VIP',
                last_name='Kunde',
                notes=notes_text
            )
            db.session.add(customer)
            db.session.commit()

            assert customer.notes == notes_text

    def test_customer_get_method(self, app):
        """Test: get() Methode für Dictionary-Kompatibilität"""
        with app.app_context():
            customer = Customer(
                id='DICT001',
                first_name='Test',
                email='test@example.com'
            )

            assert customer.get('first_name') == 'Test'
            assert customer.get('email') == 'test@example.com'
            assert customer.get('nonexistent', 'default') == 'default'

    def test_customer_metadata(self, app):
        """Test: Metadaten (created_by, created_at)"""
        with app.app_context():
            customer = Customer(
                id='META001',
                customer_type='private',
                first_name='Meta',
                last_name='Test',
                created_by='admin'
            )
            db.session.add(customer)
            db.session.commit()

            assert customer.created_by == 'admin'
            assert customer.created_at is not None

    def test_customer_repr(self, app):
        """Test: String-Repräsentation"""
        with app.app_context():
            customer = Customer(
                id='REPR001',
                customer_type='private',
                first_name='Test',
                last_name='User'
            )

            repr_string = repr(customer)
            assert 'Customer REPR001' in repr_string
            assert 'Test User' in repr_string

    def test_query_customer_by_id(self, app, test_customer):
        """Test: Kunde per ID abfragen"""
        with app.app_context():
            customer = Customer.query.get('TEST001')
            assert customer is not None
            assert customer.id == 'TEST001'

    def test_query_customers_by_type(self, app, sample_customers):
        """Test: Kunden nach Typ filtern"""
        with app.app_context():
            private_customers = Customer.query.filter_by(customer_type='private').all()
            business_customers = Customer.query.filter_by(customer_type='business').all()

            assert len(private_customers) >= 1
            assert len(business_customers) >= 1
