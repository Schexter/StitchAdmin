"""
Unit Tests für Customer Controller
Testet die Kunden-Verwaltungsrouten
"""

import pytest
from flask import url_for


@pytest.mark.unit
@pytest.mark.controller
class TestCustomerController:
    """Test-Klasse für Customer Controller"""

    def test_customers_list_requires_login(self, client):
        """Test: Kundenliste erfordert Login"""
        response = client.get('/customers/')

        # Sollte zu Login umleiten
        assert response.status_code in [302, 401]

    def test_customers_list_authenticated(self, authenticated_client, test_customer):
        """Test: Kundenliste für eingeloggten User"""
        response = authenticated_client.get('/customers/')

        assert response.status_code == 200
        # Check if customer appears in response
        assert b'Kunden' in response.data or b'Customer' in response.data

    def test_customer_detail_view(self, authenticated_client, test_customer):
        """Test: Kundendetails anzeigen"""
        response = authenticated_client.get(f'/customers/{test_customer.id}')

        assert response.status_code == 200

    def test_customer_create_page_loads(self, authenticated_client):
        """Test: Kunden-Erstellungs-Seite lädt"""
        response = authenticated_client.get('/customers/new')

        assert response.status_code == 200
        assert b'Neuer Kunde' in response.data or b'Kunde anlegen' in response.data or b'form' in response.data
