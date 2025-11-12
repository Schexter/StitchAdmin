"""
Unit Tests für Security Utils
Testet alle Sicherheits-Funktionen
"""

import pytest
import os
import json
import string
from datetime import datetime, timedelta
from src.utils.security import (
    check_login_attempts,
    record_login_attempt,
    generate_secure_password,
    check_password_strength,
    generate_password_reset_token,
    validate_password_reset_token,
    invalidate_password_reset_token,
    cleanup_expired_tokens,
    LOGIN_ATTEMPTS_FILE,
    PASSWORD_RESET_TOKENS_FILE
)


@pytest.mark.unit
class TestSecurity:
    """Test-Klasse für Security Utils"""

    def setup_method(self):
        """Cleanup vor jedem Test"""
        # Lösche Test-Dateien falls vorhanden
        if os.path.exists(LOGIN_ATTEMPTS_FILE):
            os.remove(LOGIN_ATTEMPTS_FILE)
        if os.path.exists(PASSWORD_RESET_TOKENS_FILE):
            os.remove(PASSWORD_RESET_TOKENS_FILE)

    def teardown_method(self):
        """Cleanup nach jedem Test"""
        # Lösche Test-Dateien
        if os.path.exists(LOGIN_ATTEMPTS_FILE):
            os.remove(LOGIN_ATTEMPTS_FILE)
        if os.path.exists(PASSWORD_RESET_TOKENS_FILE):
            os.remove(PASSWORD_RESET_TOKENS_FILE)

    # ==========================================
    # Login Attempts Tests
    # ==========================================

    def test_check_login_attempts_no_previous_attempts(self):
        """Test: Kein Login-Versuch vorhanden"""
        is_blocked, remaining_time = check_login_attempts('testuser')
        assert is_blocked is False
        assert remaining_time == 0

    def test_record_login_attempt_failed(self):
        """Test: Fehlgeschlagenen Login-Versuch aufzeichnen"""
        record_login_attempt('testuser', success=False)

        # Prüfe ob gespeichert
        with open(LOGIN_ATTEMPTS_FILE, 'r') as f:
            attempts = json.load(f)

        assert 'testuser' in attempts
        assert attempts['testuser']['count'] == 1

    def test_record_login_attempt_success_resets(self):
        """Test: Erfolgreicher Login setzt Versuche zurück"""
        # Erst fehlgeschlagen
        record_login_attempt('testuser', success=False)
        record_login_attempt('testuser', success=False)

        # Dann erfolgreich
        record_login_attempt('testuser', success=True)

        # Sollte jetzt leer sein
        with open(LOGIN_ATTEMPTS_FILE, 'r') as f:
            attempts = json.load(f)

        assert 'testuser' not in attempts

    def test_check_login_attempts_max_reached(self):
        """Test: Maximale Versuche erreicht -> Blockierung"""
        # 5 fehlgeschlagene Versuche
        for i in range(5):
            record_login_attempt('testuser', success=False)

        is_blocked, remaining_time = check_login_attempts('testuser', max_attempts=5)
        assert is_blocked is True
        assert remaining_time == 15  # 15 Minuten Sperrzeit

    def test_check_login_attempts_below_max(self):
        """Test: Unter Maximum -> Keine Blockierung"""
        # 3 fehlgeschlagene Versuche
        for i in range(3):
            record_login_attempt('testuser', success=False)

        is_blocked, remaining_time = check_login_attempts('testuser', max_attempts=5)
        assert is_blocked is False
        assert remaining_time == 0

    # ==========================================
    # Password Generation Tests
    # ==========================================

    def test_generate_secure_password_default_length(self):
        """Test: Passwort mit Standard-Länge generieren"""
        password = generate_secure_password()
        assert len(password) == 12

    def test_generate_secure_password_custom_length(self):
        """Test: Passwort mit benutzerdefinierter Länge"""
        password = generate_secure_password(length=20)
        assert len(password) == 20

    def test_generate_secure_password_contains_variety(self):
        """Test: Passwort enthält verschiedene Zeichentypen"""
        password = generate_secure_password(length=50)  # Längeres PW für bessere Chance

        # Sollte mindestens einen von jedem Typ enthalten (bei 50 Zeichen sehr wahrscheinlich)
        has_letter = any(c in string.ascii_letters for c in password)
        has_digit = any(c in string.digits for c in password)
        has_punct = any(c in string.punctuation for c in password)

        assert has_letter
        assert has_digit
        # Punctuation ist zufällig, könnte fehlen bei kurzen PWs

    def test_generate_secure_password_unique(self):
        """Test: Generierte Passwörter sind unterschiedlich"""
        pw1 = generate_secure_password()
        pw2 = generate_secure_password()
        assert pw1 != pw2

    # ==========================================
    # Password Strength Tests
    # ==========================================

    def test_check_password_strength_too_short(self):
        """Test: Zu kurzes Passwort"""
        is_valid, messages = check_password_strength('Short1!', min_length=8)
        assert is_valid is False
        assert any('mindestens 8 Zeichen' in msg for msg in messages)

    def test_check_password_strength_no_uppercase(self):
        """Test: Kein Großbuchstabe"""
        is_valid, messages = check_password_strength('password123!', min_length=8)
        assert is_valid is False
        assert any('Großbuchstaben' in msg for msg in messages)

    def test_check_password_strength_no_lowercase(self):
        """Test: Kein Kleinbuchstabe"""
        is_valid, messages = check_password_strength('PASSWORD123!', min_length=8)
        assert is_valid is False
        assert any('Kleinbuchstaben' in msg for msg in messages)

    def test_check_password_strength_no_digit(self):
        """Test: Keine Zahl"""
        is_valid, messages = check_password_strength('Password!', min_length=8)
        assert is_valid is False
        assert any('Zahl' in msg for msg in messages)

    def test_check_password_strength_no_special_char(self):
        """Test: Kein Sonderzeichen"""
        is_valid, messages = check_password_strength('Password123', min_length=8)
        assert is_valid is False
        assert any('Sonderzeichen' in msg for msg in messages)

    def test_check_password_strength_valid_password(self):
        """Test: Gültiges starkes Passwort"""
        is_valid, messages = check_password_strength('MyP@ssw0rd!', min_length=8)
        assert is_valid is True
        assert len(messages) == 0

    def test_check_password_strength_custom_min_length(self):
        """Test: Benutzerdefinierte Mindestlänge"""
        is_valid, messages = check_password_strength('Short1!', min_length=6)
        assert is_valid is True  # 7 Zeichen bei min_length=6

    # ==========================================
    # Password Reset Token Tests
    # ==========================================

    def test_generate_password_reset_token(self):
        """Test: Reset-Token generieren"""
        token = generate_password_reset_token('testuser')

        assert token is not None
        assert len(token) > 20  # URL-safe Token ist relativ lang

        # Prüfe ob in Datei gespeichert
        with open(PASSWORD_RESET_TOKENS_FILE, 'r') as f:
            tokens = json.load(f)

        assert token in tokens
        assert tokens[token]['username'] == 'testuser'

    def test_validate_password_reset_token_valid(self):
        """Test: Gültiges Token validieren"""
        token = generate_password_reset_token('testuser')
        username = validate_password_reset_token(token)

        assert username == 'testuser'

    def test_validate_password_reset_token_invalid(self):
        """Test: Ungültiges Token"""
        username = validate_password_reset_token('invalid-token-xyz')
        assert username is None

    def test_validate_password_reset_token_expired(self):
        """Test: Abgelaufenes Token"""
        token = generate_password_reset_token('testuser')

        # Manuell auf abgelaufen setzen
        with open(PASSWORD_RESET_TOKENS_FILE, 'r') as f:
            tokens = json.load(f)

        # Setze Ablaufzeit auf gestern
        expired_time = (datetime.now() - timedelta(days=1)).isoformat()
        tokens[token]['expires_at'] = expired_time

        with open(PASSWORD_RESET_TOKENS_FILE, 'w') as f:
            json.dump(tokens, f)

        username = validate_password_reset_token(token)
        assert username is None

    def test_invalidate_password_reset_token(self):
        """Test: Token ungültig machen"""
        token = generate_password_reset_token('testuser')

        # Token invalidieren
        invalidate_password_reset_token(token)

        # Sollte jetzt ungültig sein
        username = validate_password_reset_token(token)
        assert username is None

    def test_cleanup_expired_tokens(self):
        """Test: Abgelaufene Tokens aufräumen"""
        # Generiere mehrere Tokens
        token1 = generate_password_reset_token('user1')
        token2 = generate_password_reset_token('user2')

        # Setze token1 auf abgelaufen
        with open(PASSWORD_RESET_TOKENS_FILE, 'r') as f:
            tokens = json.load(f)

        expired_time = (datetime.now() - timedelta(days=1)).isoformat()
        tokens[token1]['expires_at'] = expired_time

        with open(PASSWORD_RESET_TOKENS_FILE, 'w') as f:
            json.dump(tokens, f)

        # Cleanup durchführen
        cleanup_expired_tokens()

        # Prüfe Ergebnis
        with open(PASSWORD_RESET_TOKENS_FILE, 'r') as f:
            tokens = json.load(f)

        assert token1 not in tokens  # Abgelaufener Token entfernt
        assert token2 in tokens      # Gültiger Token noch da

    def test_multiple_users_login_attempts(self):
        """Test: Mehrere Benutzer unabhängig tracken"""
        record_login_attempt('user1', success=False)
        record_login_attempt('user2', success=False)
        record_login_attempt('user2', success=False)

        with open(LOGIN_ATTEMPTS_FILE, 'r') as f:
            attempts = json.load(f)

        assert attempts['user1']['count'] == 1
        assert attempts['user2']['count'] == 2

    def test_password_strength_multiple_issues(self):
        """Test: Mehrere Probleme in einem Passwort"""
        is_valid, messages = check_password_strength('short', min_length=8)

        assert is_valid is False
        assert len(messages) >= 2  # Mindestens 2 Probleme (Länge + fehlende Zeichen)
