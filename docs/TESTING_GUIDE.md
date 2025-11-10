# Testing-Guide: pytest für StitchAdmin 2.0

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Für:** Sprint 1, Woche 2 (18.-22.11.2025)

---

## 📋 Inhaltsverzeichnis

1. [Warum Testing?](#warum-testing)
2. [pytest Setup](#pytest-setup)
3. [Erste Tests schreiben](#erste-tests-schreiben)
4. [Test-Patterns](#test-patterns)
5. [Fixtures](#fixtures)
6. [Coverage](#coverage)
7. [CI/CD Integration](#cicd-integration)

---

## 🎯 Warum Testing?

### Vorteile
- ✅ **Frühe Fehlererkennung** - Bugs vor Produktion finden
- ✅ **Refactoring-Sicherheit** - Änderungen ohne Angst
- ✅ **Dokumentation** - Tests zeigen, wie Code funktioniert
- ✅ **Qualität** - Zwingt zu besserem Code-Design

### Ziele für StitchAdmin
- **Sprint 1:** 20% Coverage
- **Sprint 2:** 40% Coverage
- **Sprint 7:** 60% Coverage

---

## 🔧 pytest Setup

### Schritt 1: Installation (Montag, 18.11, 09:00-09:30)

```bash
# Virtual Environment aktivieren
.venv\Scripts\activate

# pytest installieren
pip install pytest pytest-flask pytest-cov

# requirements.txt aktualisieren
pip freeze > requirements.txt

# Git commit
git add requirements.txt
git commit -m "test: add pytest dependencies"
```

---

### Schritt 2: Projektstruktur (09:30-10:00)

```bash
# Tests-Ordner erstellen
mkdir tests
mkdir tests\unit
mkdir tests\integration
mkdir tests\fixtures

# __init__.py Dateien
type nul > tests\__init__.py
type nul > tests\unit\__init__.py
type nul > tests\integration\__init__.py

# Git commit
git add tests/
git commit -m "test: create test directory structure"
```

**Ergebnis:**
```
StitchAdmin2.0/
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Wird gleich erstellt
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   └── test_utils.py
│   ├── integration/
│   │   ├── __init__.py
│   │   └── test_controllers.py
│   └── fixtures/
│       └── sample_data.py
```

---

### Schritt 3: conftest.py erstellen (10:00-11:00)

**Datei:** `tests/conftest.py`

```python
"""
pytest Konfiguration und Fixtures für StitchAdmin 2.0
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import pytest
import os
import sys
from datetime import datetime

# Projekt-Root zum Path hinzufügen
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from src.models.models import db as _db


@pytest.fixture(scope='session')
def app():
    """
    Test-App-Instanz für die gesamte Test-Session
    Verwendet In-Memory SQLite-Datenbank
    """
    app = create_app()
    
    # Test-Konfiguration
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',  # In-Memory DB
        'WTF_CSRF_ENABLED': False,  # CSRF für Tests deaktivieren
        'SECRET_KEY': 'test-secret-key',
        'DEBUG': False
    })
    
    return app


@pytest.fixture(scope='session')
def db(app):
    """
    Datenbank-Fixture für die gesamte Test-Session
    Erstellt alle Tabellen vor den Tests
    Löscht alle Tabellen nach den Tests
    """
    with app.app_context():
        _db.create_all()
        yield _db
        _db.drop_all()


@pytest.fixture(scope='function')
def session(db):
    """
    Datenbank-Session für jeden einzelnen Test
    Führt Rollback nach jedem Test durch
    """
    connection = db.engine.connect()
    transaction = connection.begin()
    
    # Session an Connection binden
    session = db.create_scoped_session(
        options={'bind': connection, 'binds': {}}
    )
    db.session = session
    
    yield session
    
    # Cleanup nach Test
    transaction.rollback()
    connection.close()
    session.remove()


@pytest.fixture
def client(app):
    """
    Test-Client für HTTP-Requests
    """
    return app.test_client()


@pytest.fixture
def runner(app):
    """
    CLI-Test-Runner
    """
    return app.test_cli_runner()


@pytest.fixture
def test_user(session):
    """
    Test-Benutzer (Admin)
    Wird vor jedem Test erstellt
    """
    from src.models.models import User
    
    user = User(
        username='testuser',
        email='test@stitchadmin.local',
        is_admin=True,
        is_active=True
    )
    user.set_password('test123')
    
    session.add(user)
    session.commit()
    
    return user


@pytest.fixture
def authenticated_client(client, test_user):
    """
    Authentifizierter Test-Client
    Bereits eingeloggt mit test_user
    """
    with client:
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'test123'
        }, follow_redirects=True)
        
        yield client


@pytest.fixture
def test_customer(session):
    """
    Test-Kunde (Privatkunde)
    """
    from src.models.models import Customer
    
    customer = Customer(
        id='TEST-CUST-001',
        customer_type='private',
        first_name='Max',
        last_name='Mustermann',
        email='max@test.local',
        phone='0123456789',
        street='Teststraße',
        house_number='1',
        postal_code='12345',
        city='Teststadt',
        created_by='testuser'
    )
    
    session.add(customer)
    session.commit()
    
    return customer


@pytest.fixture
def test_article(session):
    """
    Test-Artikel
    """
    from src.models.models import Article
    
    article = Article(
        id='TEST-ART-001',
        article_number='TST001',
        name='Test T-Shirt',
        category='Textilien',
        brand='TestBrand',
        purchase_price_single=5.00,
        price=10.00,
        stock=100,
        active=True,
        created_by='testuser'
    )
    
    session.add(article)
    session.commit()
    
    return article


@pytest.fixture
def test_order(session, test_customer, test_article):
    """
    Test-Auftrag (Stickerei)
    """
    from src.models.models import Order, OrderItem
    
    order = Order(
        id='TEST-ORD-001',
        order_number='A-TEST-001',
        customer_id=test_customer.id,
        order_type='embroidery',
        status='new',
        stitch_count=5000,
        total_price=50.00,
        created_by='testuser'
    )
    
    session.add(order)
    session.commit()
    
    # OrderItem hinzufügen
    item = OrderItem(
        order_id=order.id,
        article_id=test_article.id,
        quantity=5,
        unit_price=10.00
    )
    
    session.add(item)
    session.commit()
    
    return order
```

**Commit:**
```bash
git add tests/conftest.py
git commit -m "test: add pytest configuration and base fixtures"
```

---

## ✅ Erste Tests schreiben

### Test 1: Model-Tests (Montag 18.11, 11:00-12:00)

**Datei:** `tests/unit/test_models.py`

```python
"""
Unit-Tests für Models
"""

import pytest
from src.models.models import User, Customer, Article, Order


class TestUserModel:
    """Tests für User Model"""
    
    def test_create_user(self, session):
        """Test: Benutzer erstellen"""
        user = User(
            username='newuser',
            email='new@test.local',
            is_admin=False
        )
        user.set_password('secret123')
        
        session.add(user)
        session.commit()
        
        # Assertions
        assert user.id is not None
        assert user.username == 'newuser'
        assert user.email == 'new@test.local'
        assert user.is_admin is False
        assert user.is_active is True  # Default
    
    def test_password_hashing(self, session):
        """Test: Passwort wird korrekt gehasht"""
        user = User(username='pwtest', email='pw@test.local')
        user.set_password('mypassword')
        
        # Passwort-Hash sollte nicht das Klartext-Passwort sein
        assert user.password_hash != 'mypassword'
        
        # check_password sollte True zurückgeben
        assert user.check_password('mypassword') is True
        
        # Falsches Passwort sollte False zurückgeben
        assert user.check_password('wrongpassword') is False
    
    def test_user_repr(self, test_user):
        """Test: String-Repräsentation"""
        assert repr(test_user) == '<User testuser>'


class TestCustomerModel:
    """Tests für Customer Model"""
    
    def test_create_private_customer(self, session):
        """Test: Privatkunden erstellen"""
        customer = Customer(
            id='TEST-002',
            customer_type='private',
            first_name='Anna',
            last_name='Schmidt',
            email='anna@test.local'
        )
        
        session.add(customer)
        session.commit()
        
        assert customer.id == 'TEST-002'
        assert customer.customer_type == 'private'
        assert customer.display_name == 'Anna Schmidt'
    
    def test_create_business_customer(self, session):
        """Test: Geschäftskunden erstellen"""
        customer = Customer(
            id='TEST-003',
            customer_type='business',
            company_name='Test GmbH',
            contact_person='Peter Müller',
            email='info@test-gmbh.local'
        )
        
        session.add(customer)
        session.commit()
        
        assert customer.customer_type == 'business'
        assert customer.display_name == 'Test GmbH'
    
    def test_customer_display_name(self, test_customer):
        """Test: display_name Property"""
        assert test_customer.display_name == 'Max Mustermann'
        
        # Business-Kunde testen
        test_customer.customer_type = 'business'
        test_customer.company_name = 'Mustermann AG'
        assert test_customer.display_name == 'Mustermann AG'


class TestArticleModel:
    """Tests für Article Model"""
    
    def test_create_article(self, session):
        """Test: Artikel erstellen"""
        article = Article(
            id='TEST-ART-002',
            article_number='TST002',
            name='Test Hoodie',
            purchase_price_single=15.00,
            price=30.00,
            stock=50
        )
        
        session.add(article)
        session.commit()
        
        assert article.id == 'TEST-ART-002'
        assert article.name == 'Test Hoodie'
        assert article.price == 30.00
    
    def test_article_price_calculation(self, session):
        """Test: Preiskalkulation"""
        article = Article(
            id='TEST-ART-003',
            article_number='TST003',
            name='Test Shirt',
            purchase_price_single=10.00
        )
        
        session.add(article)
        session.commit()
        
        # Preise berechnen
        result = article.calculate_prices()
        
        assert result['base_price'] == 10.00
        assert result['calculated'] > 10.00  # VK sollte höher als EK sein
        assert article.price_calculated is not None
    
    def test_article_get_best_purchase_price(self, test_article):
        """Test: Bester EK-Preis wird ermittelt"""
        # Nur single_price gesetzt
        test_article.purchase_price_single = 5.00
        test_article.purchase_price_carton = None
        test_article.purchase_price_10carton = None
        
        assert test_article._get_best_purchase_price() == 5.00
        
        # Kartonpreis niedriger
        test_article.purchase_price_carton = 4.50
        assert test_article._get_best_purchase_price() == 5.00  # Immer single_price
        
        # 10-Karton noch niedriger
        test_article.purchase_price_10carton = 4.00
        assert test_article._get_best_purchase_price() == 5.00  # Immer single_price


class TestOrderModel:
    """Tests für Order Model"""
    
    def test_create_order(self, session, test_customer):
        """Test: Auftrag erstellen"""
        order = Order(
            id='TEST-ORD-002',
            order_number='A-TEST-002',
            customer_id=test_customer.id,
            order_type='embroidery',
            status='new',
            stitch_count=10000,
            total_price=100.00
        )
        
        session.add(order)
        session.commit()
        
        assert order.id == 'TEST-ORD-002'
        assert order.status == 'new'
        assert order.order_type == 'embroidery'
    
    def test_order_can_start_production(self, test_order):
        """Test: Produktions-Bereitschaft prüfen"""
        # Ohne Design
        test_order.design_status = 'none'
        can_start, reason = test_order.can_start_production()
        assert can_start is False
        assert 'Design' in reason
        
        # Mit Design
        test_order.design_status = 'customer_provided'
        can_start, reason = test_order.can_start_production()
        assert can_start is True
        assert reason == 'OK'
    
    def test_order_selected_threads(self, test_order):
        """Test: Garne als JSON speichern/laden"""
        threads = [
            {'thread_id': 'THR-001', 'color': 'Rot'},
            {'thread_id': 'THR-002', 'color': 'Blau'}
        ]
        
        # Setzen
        test_order.set_selected_threads(threads)
        assert test_order.selected_threads is not None
        
        # Laden
        loaded = test_order.get_selected_threads()
        assert len(loaded) == 2
        assert loaded[0]['color'] == 'Rot'


# Pytest ausführen
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

**Tests ausführen:**
```bash
pytest tests/unit/test_models.py -v
```

**Erwartetes Ergebnis:**
```
tests/unit/test_models.py::TestUserModel::test_create_user PASSED
tests/unit/test_models.py::TestUserModel::test_password_hashing PASSED
tests/unit/test_models.py::TestUserModel::test_user_repr PASSED
tests/unit/test_models.py::TestCustomerModel::test_create_private_customer PASSED
tests/unit/test_models.py::TestCustomerModel::test_create_business_customer PASSED
tests/unit/test_models.py::TestCustomerModel::test_customer_display_name PASSED
tests/unit/test_models.py::TestArticleModel::test_create_article PASSED
tests/unit/test_models.py::TestArticleModel::test_article_price_calculation PASSED
tests/unit/test_models.py::TestArticleModel::test_article_get_best_purchase_price PASSED
tests/unit/test_models.py::TestOrderModel::test_create_order PASSED
tests/unit/test_models.py::TestOrderModel::test_order_can_start_production PASSED
tests/unit/test_models.py::TestOrderModel::test_order_selected_threads PASSED

============= 12 passed in 2.34s =============
```

**Commit:**
```bash
git add tests/unit/test_models.py
git commit -m "test: add model unit tests (12 tests)"
```

---

### Test 2: Controller-Tests (Dienstag 19.11, 09:00-12:00)

**Datei:** `tests/integration/test_customer_controller.py`

```python
"""
Integration-Tests für Customer Controller
"""

import pytest
from src.models.models import Customer


class TestCustomerController:
    """Tests für Customer-Routen"""
    
    def test_customer_index_requires_login(self, client):
        """Test: Kunden-Liste erfordert Login"""
        response = client.get('/customers/')
        
        # Sollte zu Login umleiten
        assert response.status_code == 302
        assert '/auth/login' in response.location
    
    def test_customer_index_authenticated(self, authenticated_client, test_customer):
        """Test: Kunden-Liste mit Login"""
        response = authenticated_client.get('/customers/')
        
        assert response.status_code == 200
        assert b'Kunden' in response.data
        assert b'Max Mustermann' in response.data
    
    def test_customer_create_get(self, authenticated_client):
        """Test: Neuer Kunde Formular anzeigen"""
        response = authenticated_client.get('/customers/new')
        
        assert response.status_code == 200
        assert b'Neuer Kunde' in response.data
        assert b'Privatkunde' in response.data
        assert b'Gesch\xc3\xa4ftskunde' in response.data  # Geschäftskunde (UTF-8)
    
    def test_customer_create_post_private(self, authenticated_client, session):
        """Test: Privatkunden erstellen (POST)"""
        response = authenticated_client.post('/customers/create', data={
            'customer_type': 'private',
            'first_name': 'Test',
            'last_name': 'Person',
            'email': 'testperson@example.com',
            'phone': '0987654321',
            'street': 'Testweg',
            'house_number': '42',
            'postal_code': '54321',
            'city': 'Testdorf'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'erstellt' in response.data or b'Kunde' in response.data
        
        # Prüfe ob in DB
        customer = Customer.query.filter_by(email='testperson@example.com').first()
        assert customer is not None
        assert customer.first_name == 'Test'
        assert customer.last_name == 'Person'
    
    def test_customer_show(self, authenticated_client, test_customer):
        """Test: Kunden-Details anzeigen"""
        response = authenticated_client.get(f'/customers/{test_customer.id}')
        
        assert response.status_code == 200
        assert b'Max Mustermann' in response.data
        assert b'max@test.local' in response.data
    
    def test_customer_edit_get(self, authenticated_client, test_customer):
        """Test: Kunde bearbeiten Formular"""
        response = authenticated_client.get(f'/customers/{test_customer.id}/edit')
        
        assert response.status_code == 200
        assert b'Kunde bearbeiten' in response.data
        assert b'Max' in response.data
        assert b'Mustermann' in response.data
    
    def test_customer_update(self, authenticated_client, test_customer):
        """Test: Kunde aktualisieren (POST)"""
        response = authenticated_client.post(
            f'/customers/{test_customer.id}/update',
            data={
                'customer_type': 'private',
                'first_name': 'Maximilian',  # Geändert
                'last_name': 'Mustermann',
                'email': 'max@test.local',
                'phone': '0123456789'
            },
            follow_redirects=True
        )
        
        assert response.status_code == 200
        
        # Prüfe Update in DB
        customer = Customer.query.get(test_customer.id)
        assert customer.first_name == 'Maximilian'
    
    def test_customer_delete(self, authenticated_client, test_customer, session):
        """Test: Kunde löschen"""
        customer_id = test_customer.id
        
        response = authenticated_client.post(
            f'/customers/{customer_id}/delete',
            follow_redirects=True
        )
        
        assert response.status_code == 200
        
        # Prüfe ob gelöscht
        customer = Customer.query.get(customer_id)
        assert customer is None
    
    def test_customer_search(self, authenticated_client, test_customer):
        """Test: Kunden suchen"""
        response = authenticated_client.get('/customers/?search=mustermann')
        
        assert response.status_code == 200
        assert b'Mustermann' in response.data


# Pytest ausführen
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

**Tests ausführen:**
```bash
pytest tests/integration/test_customer_controller.py -v
```

**Commit:**
```bash
git add tests/integration/test_customer_controller.py
git commit -m "test: add customer controller integration tests (9 tests)"
```

---

## 📊 Coverage (Mittwoch 20.11, 14:00-17:00)

### Coverage messen

```bash
# Mit HTML-Report
pytest --cov=src --cov-report=html

# Report öffnen
start htmlcov\index.html
```

**Ziel:** >20% Coverage

### Coverage-Report interpretieren

```
---------- coverage: platform win32, python 3.11.0 -----------
Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
src\__init__.py                             0      0   100%
src\models\__init__.py                      1      0   100%
src\models\models.py                      350    280    20%
src\controllers\customer_controller_db.py 120     96    20%
src\controllers\article_controller_db.py  150    135    10%
-----------------------------------------------------------
TOTAL                                    1250   1000    20%
```

**20% erreicht!** ✅

---

## 🔄 CI/CD (Optional - Donnerstag 21.11)

### GitHub Actions

**Datei:** `.github/workflows/tests.yml`

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        pytest --cov=src --cov-report=term
    
    - name: Check coverage
      run: |
        pytest --cov=src --cov-report=term --cov-fail-under=20
```

---

## ✅ Checkliste Woche 2

### Montag
- [ ] pytest installiert
- [ ] Tests-Struktur erstellt
- [ ] conftest.py erstellt
- [ ] Erste Model-Tests geschrieben (12 Tests)

### Dienstag
- [ ] Customer-Controller-Tests (9 Tests)
- [ ] Article-Controller-Tests (optional)
- [ ] Order-Controller-Tests (optional)

### Mittwoch
- [ ] Coverage messen (Ziel: >20%)
- [ ] Fehlende Tests identifizieren
- [ ] Tests ergänzen

### Donnerstag
- [ ] Code-Review der Tests
- [ ] Dokumentation der Test-Patterns
- [ ] GitHub Actions (optional)

### Freitag
- [ ] Test-Coverage-Report erstellen
- [ ] Sprint-Review vorbereiten
- [ ] TODO.md updaten

---

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Viel Erfolg beim Testen!** 🧪✅
