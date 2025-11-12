"""
Unit Tests für Authentication Controller
Testet Login/Logout Funktionalität
"""

import pytest


@pytest.mark.unit
@pytest.mark.controller
class TestAuthController:
    """Test-Klasse für Auth Controller"""

    def test_login_page_loads(self, client):
        """Test: Login-Seite lädt"""
        response = client.get('/auth/login')

        assert response.status_code == 200
        assert b'Login' in response.data or b'login' in response.data

    def test_login_with_valid_credentials(self, client, test_user):
        """Test: Login mit gültigen Credentials"""
        response = client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        }, follow_redirects=True)

        assert response.status_code == 200

    def test_login_with_invalid_credentials(self, client, test_user):
        """Test: Login mit ungültigen Credentials"""
        response = client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'wrongpassword'
        }, follow_redirects=True)

        # Should either stay on login page or show error
        assert b'Login' in response.data or b'Fehler' in response.data or b'error' in response.data

    def test_logout(self, authenticated_client):
        """Test: Logout funktioniert"""
        response = authenticated_client.get('/auth/logout', follow_redirects=True)

        assert response.status_code == 200
