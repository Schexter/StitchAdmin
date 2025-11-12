"""
StitchAdmin 2.0 - Pytest Configuration & Fixtures
Erstellt von Hans Hahn - Alle Rechte vorbehalten

Zentrale Test-Konfiguration mit Fixtures für:
- Flask App
- Test Database
- Test Client
- Authentication
"""

import os
import sys
import pytest
from datetime import datetime

# Füge das Projektverzeichnis zum Python Path hinzu
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import os
os.environ['TESTING'] = '1'  # Set before importing app

from app import create_app
from src.models.models import db, User, Customer, Article, Order, Machine, Thread, Supplier


@pytest.fixture(scope='session')
def app():
    """
    Flask App Fixture für die gesamte Test-Session
    Verwendet eine In-Memory SQLite Datenbank
    """
    # Nutze die echte create_app() Funktion mit Test-Konfiguration
    os.environ['TESTING'] = '1'
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

    app = create_app()

    # Überschreibe Konfiguration für Tests
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'WTF_CSRF_ENABLED': False,  # Disable CSRF for testing
    })

    # Application context für die gesamte Test-Session
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """
    Test Client Fixture
    Wird für jeden Test neu erstellt
    """
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """
    CLI Runner Fixture für CLI-Tests
    """
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def db_session(app):
    """
    Database Session Fixture
    Rollback nach jedem Test für Isolation
    """
    with app.app_context():
        # Beginne eine Transaktion
        connection = db.engine.connect()
        transaction = connection.begin()

        # Binde Session an Transaktion
        session = db.session

        yield session

        # Rollback nach dem Test
        transaction.rollback()
        connection.close()
        session.remove()


@pytest.fixture
def test_user(app):
    """
    Test User Fixture
    Erstellt einen Test-Benutzer
    """
    with app.app_context():
        user = User(
            username='testuser',
            email='test@example.com',
            is_active=True,
            is_admin=False
        )
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()

        yield user

        # Cleanup
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def test_admin(app):
    """
    Test Admin User Fixture
    Erstellt einen Test-Admin
    """
    with app.app_context():
        admin = User(
            username='admin',
            email='admin@example.com',
            is_active=True,
            is_admin=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

        yield admin

        # Cleanup
        db.session.delete(admin)
        db.session.commit()


@pytest.fixture
def authenticated_client(client, test_user):
    """
    Authenticated Test Client Fixture
    Client ist bereits mit test_user eingeloggt
    """
    with client:
        client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        }, follow_redirects=True)
        yield client


@pytest.fixture
def test_customer(app):
    """
    Test Customer Fixture
    Erstellt einen Test-Kunden
    """
    # Nutze existierenden App-Context (von app-Fixture)
    # Prüfe ob Kunde bereits existiert und lösche ihn
    existing = Customer.query.filter_by(id='TEST001').first()
    if existing:
        db.session.delete(existing)
        db.session.commit()

    customer = Customer(
        id='TEST001',
        customer_type='private',
        first_name='Max',
        last_name='Mustermann',
        email='max@example.com',
        phone='0123456789',
        street='Teststraße',
        house_number='1',
        postal_code='12345',
        city='Teststadt',
        country='Deutschland',
        created_by='testuser'
    )
    db.session.add(customer)
    db.session.commit()

    yield customer

    # Cleanup - mit Error-Handling
    try:
        customer_to_delete = Customer.query.filter_by(id='TEST001').first()
        if customer_to_delete:
            db.session.delete(customer_to_delete)
            db.session.commit()
    except Exception:
        db.session.rollback()


@pytest.fixture
def test_article(app):
    """
    Test Article Fixture
    Erstellt einen Test-Artikel
    """
    with app.app_context():
        # Lösche existierende Artikel mit dieser ID (falls vorhanden)
        existing = Article.query.filter_by(id='ART001').first()
        if existing:
            db.session.delete(existing)
            db.session.commit()

        article = Article(
            id='ART001',
            name='Test Artikel',
            category='Test-Kategorie',
            price=10.00,
            stock=100,
            created_by='testuser'
        )
        db.session.add(article)
        db.session.commit()

        yield article

        # Cleanup - mit Error-Handling
        try:
            db.session.delete(article)
            db.session.commit()
        except Exception:
            db.session.rollback()


@pytest.fixture
def test_thread(app):
    """
    Test Thread Fixture
    Erstellt ein Test-Garn
    """
    with app.app_context():
        # Lösche existierendes Garn mit dieser ID (falls vorhanden)
        existing = Thread.query.filter_by(id='THR001').first()
        if existing:
            db.session.delete(existing)
            db.session.commit()

        thread = Thread(
            id='THR001',
            manufacturer='Madeira',
            thread_type='Polyneon',
            color_number='1234',
            color_name_de='Test Rot',
            created_by='testuser'
        )
        db.session.add(thread)
        db.session.commit()

        yield thread

        # Cleanup - mit Error-Handling
        try:
            db.session.delete(thread)
            db.session.commit()
        except Exception:
            db.session.rollback()


@pytest.fixture
def test_machine(app):
    """
    Test Machine Fixture
    Erstellt eine Test-Maschine
    """
    with app.app_context():
        machine = Machine(
            id='M001',
            name='Test Stickmaschine',
            type='embroidery',
            created_by='testuser'
        )
        db.session.add(machine)
        db.session.commit()

        yield machine

        # Cleanup
        db.session.delete(machine)
        db.session.commit()


@pytest.fixture
def sample_customers(app):
    """
    Fixture für mehrere Test-Kunden
    """
    with app.app_context():
        # Lösche existierende Kunden mit diesen IDs (falls vorhanden)
        for cust_id in ['PRIV001', 'BUS001']:
            existing = Customer.query.filter_by(id=cust_id).first()
            if existing:
                db.session.delete(existing)
        db.session.commit()

        # Privatkunde
        customer1 = Customer(
            id='PRIV001',
            customer_type='private',
            first_name='Anna',
            last_name='Schmidt',
            email='anna@example.com',
            created_by='testuser'
        )

        # Geschäftskunde
        customer2 = Customer(
            id='BUS001',
            customer_type='business',
            company_name='Test GmbH',
            contact_person='Hans Müller',
            email='info@test-gmbh.de',
            tax_id='DE123456789',
            created_by='testuser'
        )

        customers = [customer1, customer2]
        db.session.add_all(customers)
        db.session.commit()

        yield customers

        # Cleanup - mit Error-Handling
        try:
            for customer in customers:
                db.session.delete(customer)
            db.session.commit()
        except Exception:
            db.session.rollback()
