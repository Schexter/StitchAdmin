"""
Unit Tests für Email Service
Testet E-Mail-Versand und Benachrichtigungen
"""

import pytest
import json
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from src.utils import email_service


@pytest.fixture
def temp_settings_file(monkeypatch):
    """Fixture für temporäre Settings-Datei"""
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
    temp_file.close()

    monkeypatch.setattr(email_service, 'SETTINGS_FILE', temp_file.name)

    yield temp_file.name

    # Cleanup
    try:
        os.unlink(temp_file.name)
    except:
        pass


@pytest.fixture
def valid_email_settings():
    """Fixture für gültige E-Mail-Einstellungen"""
    return {
        'smtp_server': 'smtp.example.com',
        'smtp_port': 587,
        'smtp_username': 'test@example.com',
        'smtp_password': 'testpassword',
        'smtp_from_email': 'noreply@example.com',
        'enable_email_notifications': True
    }


@pytest.fixture
def disabled_email_settings():
    """Fixture für deaktivierte E-Mail-Einstellungen"""
    return {
        'smtp_server': 'smtp.example.com',
        'smtp_port': 587,
        'smtp_username': 'test@example.com',
        'smtp_password': 'testpassword',
        'smtp_from_email': 'noreply@example.com',
        'enable_email_notifications': False
    }


class TestLoadEmailSettings:
    """Tests für load_email_settings Funktion"""

    def test_load_settings_file_exists(self, temp_settings_file, valid_email_settings):
        """Test: Einstellungen aus existierender Datei laden"""
        with open(temp_settings_file, 'w') as f:
            json.dump(valid_email_settings, f)

        settings = email_service.load_email_settings()

        assert settings['smtp_server'] == 'smtp.example.com'
        assert settings['smtp_port'] == 587
        assert settings['smtp_username'] == 'test@example.com'
        assert settings['enable_email_notifications'] is True

    def test_load_settings_file_not_exists(self, temp_settings_file):
        """Test: Nicht existierende Datei"""
        os.unlink(temp_settings_file)

        settings = email_service.load_email_settings()
        assert settings is None

    def test_load_settings_default_values(self, temp_settings_file):
        """Test: Default-Werte für fehlende Einstellungen"""
        partial_settings = {
            'smtp_server': 'smtp.test.com'
            # smtp_port fehlt
        }

        with open(temp_settings_file, 'w') as f:
            json.dump(partial_settings, f)

        settings = email_service.load_email_settings()
        assert settings['smtp_server'] == 'smtp.test.com'
        assert settings['smtp_port'] == 587  # Default
        assert settings['enable_email_notifications'] is False  # Default

    def test_load_settings_empty_file(self, temp_settings_file):
        """Test: Leere Settings-Datei"""
        with open(temp_settings_file, 'w') as f:
            json.dump({}, f)

        settings = email_service.load_email_settings()
        assert settings['smtp_server'] == ''
        assert settings['smtp_port'] == 587
        assert settings['enable_email_notifications'] is False


class TestSendEmail:
    """Tests für send_email Funktion"""

    @patch('smtplib.SMTP')
    def test_send_email_success(self, mock_smtp, temp_settings_file, valid_email_settings):
        """Test: Erfolgreicher E-Mail-Versand"""
        with open(temp_settings_file, 'w') as f:
            json.dump(valid_email_settings, f)

        # Mock SMTP
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = email_service.send_email(
            'recipient@example.com',
            'Test Subject',
            'Test Body'
        )

        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with('test@example.com', 'testpassword')
        mock_server.send_message.assert_called_once()

    @patch('smtplib.SMTP')
    def test_send_email_with_html(self, mock_smtp, temp_settings_file, valid_email_settings):
        """Test: E-Mail mit HTML-Teil"""
        with open(temp_settings_file, 'w') as f:
            json.dump(valid_email_settings, f)

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = email_service.send_email(
            'recipient@example.com',
            'Test Subject',
            'Text Body',
            '<html><body>HTML Body</body></html>'
        )

        assert result is True
        mock_server.send_message.assert_called_once()

    def test_send_email_notifications_disabled(self, temp_settings_file, disabled_email_settings):
        """Test: E-Mail-Benachrichtigungen deaktiviert"""
        with open(temp_settings_file, 'w') as f:
            json.dump(disabled_email_settings, f)

        result = email_service.send_email(
            'recipient@example.com',
            'Test Subject',
            'Test Body'
        )

        assert result is False

    def test_send_email_no_settings(self, temp_settings_file):
        """Test: Keine Settings-Datei vorhanden"""
        os.unlink(temp_settings_file)

        result = email_service.send_email(
            'recipient@example.com',
            'Test Subject',
            'Test Body'
        )

        assert result is False

    def test_send_email_incomplete_settings(self, temp_settings_file):
        """Test: Unvollständige Einstellungen"""
        incomplete_settings = {
            'smtp_server': 'smtp.example.com',
            'smtp_port': 587,
            'smtp_username': '',  # Leer
            'smtp_password': '',  # Leer
            'enable_email_notifications': True
        }

        with open(temp_settings_file, 'w') as f:
            json.dump(incomplete_settings, f)

        result = email_service.send_email(
            'recipient@example.com',
            'Test Subject',
            'Test Body'
        )

        assert result is False

    @patch('smtplib.SMTP')
    def test_send_email_smtp_exception(self, mock_smtp, temp_settings_file, valid_email_settings):
        """Test: SMTP-Fehler"""
        with open(temp_settings_file, 'w') as f:
            json.dump(valid_email_settings, f)

        # Mock SMTP mit Exception
        mock_smtp.side_effect = Exception("SMTP Connection Failed")

        result = email_service.send_email(
            'recipient@example.com',
            'Test Subject',
            'Test Body'
        )

        assert result is False

    @patch('smtplib.SMTP')
    def test_send_email_uses_from_email(self, mock_smtp, temp_settings_file, valid_email_settings):
        """Test: From-Email wird korrekt gesetzt"""
        with open(temp_settings_file, 'w') as f:
            json.dump(valid_email_settings, f)

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        email_service.send_email(
            'recipient@example.com',
            'Test Subject',
            'Test Body'
        )

        # Prüfe dass send_message aufgerufen wurde
        assert mock_server.send_message.called
        # Die Message sollte From-Header haben
        msg = mock_server.send_message.call_args[0][0]
        assert msg['From'] == 'noreply@example.com'

    @patch('smtplib.SMTP')
    def test_send_email_falls_back_to_username(self, mock_smtp, temp_settings_file):
        """Test: Fallback zu username wenn smtp_from_email leer"""
        settings = {
            'smtp_server': 'smtp.example.com',
            'smtp_port': 587,
            'smtp_username': 'test@example.com',
            'smtp_password': 'testpassword',
            'smtp_from_email': '',  # Leer
            'enable_email_notifications': True
        }

        with open(temp_settings_file, 'w') as f:
            json.dump(settings, f)

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        email_service.send_email(
            'recipient@example.com',
            'Test Subject',
            'Test Body'
        )

        msg = mock_server.send_message.call_args[0][0]
        assert msg['From'] == 'test@example.com'  # Fallback zu username


class TestSendWelcomeEmail:
    """Tests für send_welcome_email Funktion"""

    @patch('src.utils.email_service.send_email')
    def test_send_welcome_email(self, mock_send):
        """Test: Willkommens-E-Mail"""
        mock_send.return_value = True

        result = email_service.send_welcome_email('user@example.com', 'testuser')

        assert result is True
        mock_send.assert_called_once()

        # Prüfe Argumente
        args = mock_send.call_args[0]
        assert args[0] == 'user@example.com'
        assert 'Willkommen' in args[1]  # Subject
        assert 'testuser' in args[2]  # Body
        assert 'testuser' in args[3]  # HTML Body

    @patch('src.utils.email_service.send_email')
    def test_welcome_email_content(self, mock_send):
        """Test: Inhalt der Willkommens-E-Mail"""
        mock_send.return_value = True

        email_service.send_welcome_email('user@example.com', 'MaxMuster')

        args = mock_send.call_args[0]
        body = args[2]
        html_body = args[3]

        assert 'MaxMuster' in body
        assert 'anmelden' in body.lower()
        assert 'MaxMuster' in html_body
        assert '<html>' in html_body


class TestSendPasswordResetEmail:
    """Tests für send_password_reset_email Funktion"""

    @patch('src.utils.email_service.send_email')
    def test_send_password_reset_email(self, mock_send):
        """Test: Passwort-Reset E-Mail"""
        mock_send.return_value = True

        result = email_service.send_password_reset_email(
            'user@example.com',
            'testuser',
            'https://example.com/reset?token=abc123'
        )

        assert result is True
        mock_send.assert_called_once()

        # Prüfe Argumente
        args = mock_send.call_args[0]
        assert args[0] == 'user@example.com'
        assert 'Passwort' in args[1]  # Subject
        assert 'https://example.com/reset?token=abc123' in args[2]  # Body
        assert 'https://example.com/reset?token=abc123' in args[3]  # HTML Body

    @patch('src.utils.email_service.send_email')
    def test_password_reset_email_content(self, mock_send):
        """Test: Inhalt der Passwort-Reset E-Mail"""
        mock_send.return_value = True

        reset_link = 'https://test.com/reset?token=xyz'
        email_service.send_password_reset_email('user@example.com', 'JohnDoe', reset_link)

        args = mock_send.call_args[0]
        body = args[2]
        html_body = args[3]

        assert 'JohnDoe' in body
        assert reset_link in body
        assert '24 Stunden' in body
        assert reset_link in html_body
        assert '<a href=' in html_body


class TestSendSecurityAlert:
    """Tests für send_security_alert Funktion"""

    @patch('src.utils.email_service.send_email')
    def test_send_security_alert(self, mock_send):
        """Test: Sicherheitswarnung"""
        mock_send.return_value = True

        result = email_service.send_security_alert(
            'user@example.com',
            'testuser',
            'Verdächtiger Login',
            'Login von unbekannter IP-Adresse'
        )

        assert result is True
        mock_send.assert_called_once()

        # Prüfe Argumente
        args = mock_send.call_args[0]
        assert args[0] == 'user@example.com'
        assert 'Sicherheitswarnung' in args[1]
        assert 'Verdächtiger Login' in args[1]
        assert 'testuser' in args[2]
        assert 'Verdächtiger Login' in args[2]
        assert 'unbekannter IP' in args[2]

    @patch('src.utils.email_service.send_email')
    def test_security_alert_includes_timestamp(self, mock_send):
        """Test: Sicherheitswarnung enthält Zeitstempel"""
        mock_send.return_value = True

        email_service.send_security_alert(
            'user@example.com',
            'testuser',
            'Test Alert',
            'Test Details'
        )

        args = mock_send.call_args[0]
        body = args[2]

        assert 'Zeitpunkt:' in body
        # Sollte Datum im deutschen Format enthalten
        import re
        assert re.search(r'\d{2}\.\d{2}\.\d{4}', body) is not None


class TestSendAdminNotification:
    """Tests für send_admin_notification Funktion"""

    @patch('src.utils.email_service.send_email')
    @patch('src.controllers.user_controller.load_users')
    def test_send_admin_notification_single_admin(self, mock_load_users, mock_send):
        """Test: Benachrichtigung an einen Admin"""
        # Mock user data
        mock_load_users.return_value = {
            'user1': {
                'email': 'admin@example.com',
                'is_admin': True
            },
            'user2': {
                'email': 'user@example.com',
                'is_admin': False
            }
        }

        mock_send.return_value = True

        result = email_service.send_admin_notification('Test Subject', 'Test Message')

        assert result == 1  # 1 Admin benachrichtigt
        mock_send.assert_called_once_with('admin@example.com', '[Admin] Test Subject', 'Test Message')

    @patch('src.utils.email_service.send_email')
    @patch('src.controllers.user_controller.load_users')
    def test_send_admin_notification_multiple_admins(self, mock_load_users, mock_send):
        """Test: Benachrichtigung an mehrere Admins"""
        mock_load_users.return_value = {
            'admin1': {'email': 'admin1@example.com', 'is_admin': True},
            'admin2': {'email': 'admin2@example.com', 'is_admin': True},
            'user1': {'email': 'user@example.com', 'is_admin': False}
        }

        mock_send.return_value = True

        result = email_service.send_admin_notification('System Alert', 'Important Message')

        assert result == 2  # 2 Admins benachrichtigt
        assert mock_send.call_count == 2

    @patch('src.utils.email_service.send_email')
    @patch('src.controllers.user_controller.load_users')
    def test_send_admin_notification_no_admins(self, mock_load_users, mock_send):
        """Test: Keine Admins vorhanden"""
        mock_load_users.return_value = {
            'user1': {'email': 'user@example.com', 'is_admin': False}
        }

        result = email_service.send_admin_notification('Test', 'Message')

        assert result == 0
        mock_send.assert_not_called()

    @patch('src.utils.email_service.send_email')
    @patch('src.controllers.user_controller.load_users')
    def test_send_admin_notification_admin_without_email(self, mock_load_users, mock_send):
        """Test: Admin ohne E-Mail-Adresse"""
        mock_load_users.return_value = {
            'admin1': {'email': 'admin@example.com', 'is_admin': True},
            'admin2': {'email': None, 'is_admin': True},  # Keine Email
            'admin3': {'is_admin': True}  # Email-Feld fehlt
        }

        mock_send.return_value = True

        result = email_service.send_admin_notification('Test', 'Message')

        assert result == 1  # Nur admin1 wird benachrichtigt
        mock_send.assert_called_once()

    @patch('src.utils.email_service.send_email')
    @patch('src.controllers.user_controller.load_users')
    def test_send_admin_notification_partial_success(self, mock_load_users, mock_send):
        """Test: Teilweise erfolgreich"""
        mock_load_users.return_value = {
            'admin1': {'email': 'admin1@example.com', 'is_admin': True},
            'admin2': {'email': 'admin2@example.com', 'is_admin': True}
        }

        # Erster Aufruf erfolgreich, zweiter fehlgeschlagen
        mock_send.side_effect = [True, False]

        result = email_service.send_admin_notification('Test', 'Message')

        assert result == 1  # Nur 1 erfolgreich
        assert mock_send.call_count == 2


class TestIntegration:
    """Integrationstests für Email Service"""

    @patch('smtplib.SMTP')
    def test_full_email_workflow(self, mock_smtp, temp_settings_file, valid_email_settings):
        """Test: Vollständiger E-Mail-Workflow"""
        # Setup
        with open(temp_settings_file, 'w') as f:
            json.dump(valid_email_settings, f)

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        # 1. Einstellungen laden
        settings = email_service.load_email_settings()
        assert settings is not None
        assert settings['enable_email_notifications'] is True

        # 2. E-Mail senden
        result = email_service.send_email(
            'test@example.com',
            'Test Subject',
            'Test Body',
            '<html><body>Test HTML</body></html>'
        )

        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()
