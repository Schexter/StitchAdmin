"""
Integration Tests für Hauptworkflows
Testet vollständige Business-Workflows von Anfang bis Ende
"""

import pytest
from datetime import datetime, date
from decimal import Decimal

from src.models.models import (
    Customer, Order, OrderItem, Article, Machine
)


class TestCompleteOrderWorkflow:
    """Tests für vollständigen Auftrags-Workflow"""

    def test_order_creation_to_completion(self, client, db_session):
        """Test: Vollständiger Order-Workflow (Erstellung bis Abschluss)"""

        # 1. Erstelle Customer
        customer = Customer(
            company='Test GmbH',
            first_name='Max',
            last_name='Mustermann',
            email='max@test.de',
            phone='01234567890',
            street='Teststr. 1',
            zip_code='12345',
            city='Teststadt',
            country='Deutschland'
        )
        db_session.add(customer)
        db_session.flush()

        assert customer.id is not None

        # 2. Erstelle Article
        article = Article(
            article_number='ART-001',
            name='Test T-Shirt',
            category='Textilien',
            unit_price=Decimal('15.00'),
            stock=100
        )
        db_session.add(article)
        db_session.flush()

        # 3. Erstelle Order
        order = Order(
            order_number='ORD-2025-001',
            customer_id=customer.id,
            order_date=date.today(),
            delivery_date=date.today(),
            status='Open',
            net_total=Decimal('150.00'),
            tax_total=Decimal('28.50'),
            gross_total=Decimal('178.50')
        )
        db_session.add(order)
        db_session.flush()

        # 4. Erstelle OrderItem
        item = OrderItem(
            order_id=order.id,
            article_id=article.id,
            quantity=10,
            unit_price=Decimal('15.00'),
            total_price=Decimal('150.00'),
            description='T-Shirt mit Logo'
        )
        db_session.add(item)

        db_session.commit()

        # 5. Verifiziere Workflow
        created_order = db_session.query(Order).filter_by(
            order_number='ORD-2025-001'
        ).first()

        assert created_order is not None
        assert created_order.customer_id == customer.id
        assert created_order.gross_total == Decimal('178.50')
        assert len(created_order.items.all()) >= 1

    def test_order_status_progression(self, client, db_session):
        """Test: Order-Status-Progression"""

        customer = Customer(
            company='Status Test GmbH',
            email='status@test.de'
        )
        db_session.add(customer)
        db_session.flush()

        order = Order(
            order_number='ORD-STATUS-001',
            customer_id=customer.id,
            order_date=date.today(),
            status='Open'
        )
        db_session.add(order)
        db_session.commit()

        # Status: Open -> In Progress
        order.status = 'In Progress'
        db_session.commit()

        reloaded = db_session.query(Order).get(order.id)
        assert reloaded.status == 'In Progress'

        # Status: In Progress -> Completed
        order.status = 'Completed'
        db_session.commit()

        reloaded = db_session.query(Order).get(order.id)
        assert reloaded.status == 'Completed'


class TestCustomerWorkflow:
    """Tests für Customer-Workflows"""

    def test_create_customer_with_orders(self, client, db_session):
        """Test: Customer mit mehreren Orders"""

        customer = Customer(
            company='Multi-Order GmbH',
            email='multiorder@test.de'
        )
        db_session.add(customer)
        db_session.flush()

        # Erstelle 3 Orders
        for i in range(1, 4):
            order = Order(
                order_number=f'ORD-MULTI-{i:03d}',
                customer_id=customer.id,
                order_date=date.today(),
                status='Open',
                gross_total=Decimal('100.00') * i
            )
            db_session.add(order)

        db_session.commit()

        # Verify
        customer_orders = db_session.query(Order).filter_by(
            customer_id=customer.id
        ).all()

        assert len(customer_orders) == 3
        assert all(o.customer_id == customer.id for o in customer_orders)

    def test_find_customers_by_email(self, client, db_session):
        """Test: Kunden nach Email finden"""

        customers = [
            Customer(company=f'Company {i}', email=f'test{i}@example.com')
            for i in range(1, 4)
        ]
        db_session.add_all(customers)
        db_session.commit()

        # Suche nach spezifischer Email
        found = db_session.query(Customer).filter_by(
            email='test2@example.com'
        ).first()

        assert found is not None
        assert found.company == 'Company 2'


class TestArticleWorkflow:
    """Tests für Article-Workflows"""

    def test_article_stock_management(self, client, db_session):
        """Test: Artikel-Lagerbestand-Management"""

        article = Article(
            article_number='ART-STOCK-001',
            name='Stock Test Article',
            unit_price=Decimal('10.00'),
            stock=100
        )
        db_session.add(article)
        db_session.commit()

        # Verify initial stock
        assert article.stock == 100

        # Simulate order: reduce stock
        article.stock -= 10
        db_session.commit()

        reloaded = db_session.query(Article).get(article.id)
        assert reloaded.stock == 90

    def test_find_articles_by_category(self, client, db_session):
        """Test: Artikel nach Kategorie filtern"""

        articles = [
            Article(
                article_number=f'ART-CAT-{i}',
                name=f'Article {i}',
                category='Textilien' if i % 2 == 0 else 'Zubehör',
                unit_price=Decimal('10.00'),
                stock=100
            )
            for i in range(1, 6)
        ]
        db_session.add_all(articles)
        db_session.commit()

        # Filter by category
        textilien = db_session.query(Article).filter_by(
            category='Textilien'
        ).all()

        assert len(textilien) == 2
        assert all(a.category == 'Textilien' for a in textilien)


class TestOrderCalculationWorkflow:
    """Tests für Order-Berechnungs-Workflows"""

    def test_order_total_calculation(self, client, db_session):
        """Test: Automatische Gesamtsummen-Berechnung"""

        customer = Customer(company='Calc Test', email='calc@test.de')
        db_session.add(customer)
        db_session.flush()

        article = Article(
            article_number='ART-CALC',
            name='Calc Test',
            unit_price=Decimal('10.00'),
            stock=1000
        )
        db_session.add(article)
        db_session.flush()

        order = Order(
            order_number='ORD-CALC-001',
            customer_id=customer.id,
            order_date=date.today(),
            status='Open',
            net_total=Decimal('0.00')
        )
        db_session.add(order)
        db_session.flush()

        # Add items with different quantities and prices
        positions = [
            (10, Decimal('10.00')),  # 100
            (5, Decimal('20.00')),   # 100
            (2, Decimal('50.00'))    # 100
        ]

        total = Decimal('0.00')
        for qty, price in positions:
            item = OrderItem(
                order_id=order.id,
                article_id=article.id,
                quantity=qty,
                unit_price=price,
                total_price=qty * price
            )
            db_session.add(item)
            total += qty * price

        order.net_total = total
        order.tax_total = total * Decimal('0.19')  # 19% VAT
        order.gross_total = total + order.tax_total

        db_session.commit()

        # Verify
        reloaded = db_session.query(Order).get(order.id)
        assert reloaded.net_total == Decimal('300.00')
        assert reloaded.tax_total == Decimal('57.00')
        assert reloaded.gross_total == Decimal('357.00')


class TestOrderQueryWorkflow:
    """Tests für Order-Abfrage-Workflows"""

    def test_find_orders_by_status(self, client, db_session):
        """Test: Orders nach Status filtern"""

        customer = Customer(company='Filter Test', email='filter@test.de')
        db_session.add(customer)
        db_session.flush()

        statuses = ['Open', 'In Progress', 'Completed', 'Open', 'Open']

        for i, status in enumerate(statuses):
            order = Order(
                order_number=f'ORD-FILTER-{i+1:03d}',
                customer_id=customer.id,
                order_date=date.today(),
                status=status
            )
            db_session.add(order)

        db_session.commit()

        # Query by status
        open_orders = db_session.query(Order).filter_by(
            status='Open'
        ).all()

        assert len(open_orders) == 3
        assert all(o.status == 'Open' for o in open_orders)

    def test_find_orders_by_date_range(self, client, db_session):
        """Test: Orders nach Datums-Bereich"""

        customer = Customer(company='Date Test', email='date@test.de')
        db_session.add(customer)
        db_session.flush()

        today = date.today()

        order = Order(
            order_number='ORD-DATE-001',
            customer_id=customer.id,
            order_date=today,
            status='Open'
        )
        db_session.add(order)
        db_session.commit()

        # Query by date
        today_orders = db_session.query(Order).filter(
            Order.order_date == today
        ).all()

        assert len(today_orders) >= 1
        assert any(o.order_number == 'ORD-DATE-001' for o in today_orders)


class TestOrderDeletionWorkflow:
    """Tests für Order-Löschungs-Workflows"""

    def test_delete_order_with_items(self, client, db_session):
        """Test: Order mit Items löschen"""

        customer = Customer(company='Delete Test', email='delete@test.de')
        db_session.add(customer)
        db_session.flush()

        article = Article(
            article_number='ART-DEL',
            name='Delete Test',
            unit_price=Decimal('10.00'),
            stock=100
        )
        db_session.add(article)
        db_session.flush()

        order = Order(
            order_number='ORD-DEL-001',
            customer_id=customer.id,
            order_date=date.today(),
            status='Open'
        )
        db_session.add(order)
        db_session.flush()

        item = OrderItem(
            order_id=order.id,
            article_id=article.id,
            quantity=5,
            unit_price=Decimal('10.00'),
            total_price=Decimal('50.00')
        )
        db_session.add(item)
        db_session.commit()

        order_id = order.id

        # Delete order (items should be CASCADE deleted)
        db_session.delete(order)
        db_session.commit()

        # Verify deletion
        deleted_order = db_session.query(Order).get(order_id)
        assert deleted_order is None

        # Items should also be deleted
        orphan_items = db_session.query(OrderItem).filter_by(
            order_id=order_id
        ).all()
        assert len(orphan_items) == 0
