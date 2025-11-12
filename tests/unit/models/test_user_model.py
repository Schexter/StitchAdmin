"""
Unit Tests für User Model
Testet Authentifizierung und User-Management
"""

import pytest
from src.models.models import User, db


@pytest.mark.unit
@pytest.mark.model
class TestUserModel:
    """Test-Klasse für User Model"""

    def test_create_user(self, app):
        """Test: Benutzer erstellen"""
        with app.app_context():
            user = User(
                username='newuser',
                email='newuser@example.com',
                is_active=True,
                is_admin=False
            )
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()

            assert user.username == 'newuser'
            assert user.email == 'newuser@example.com'
            assert user.is_active is True
            assert user.is_admin is False

    def test_password_hashing(self, app):
        """Test: Passwort wird gehasht"""
        with app.app_context():
            user = User(
                username='testuser',
                email='test@example.com'
            )
            user.set_password('mypassword')

            assert user.password_hash != 'mypassword'
            assert len(user.password_hash) > 20  # Hash sollte länger sein

    def test_password_verification(self, app):
        """Test: Passwort-Überprüfung"""
        with app.app_context():
            user = User(
                username='testuser',
                email='test@example.com'
            )
            user.set_password('correctpassword')

            assert user.check_password('correctpassword') is True
            assert user.check_password('wrongpassword') is False

    def test_user_is_admin(self, app):
        """Test: Admin-User erstellen"""
        with app.app_context():
            admin = User(
                username='admin',
                email='admin@example.com',
                is_admin=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()

            assert admin.is_admin is True

    def test_user_repr(self, app):
        """Test: String-Repräsentation"""
        with app.app_context():
            user = User(
                username='testuser',
                email='test@example.com'
            )

            repr_string = repr(user)
            assert 'User testuser' in repr_string

    def test_user_last_login(self, app, test_user):
        """Test: Last Login Timestamp"""
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()

            # Initially should be None
            assert user.last_login is None

            # Simulate login
            from datetime import datetime
            user.last_login = datetime.utcnow()
            db.session.commit()

            assert user.last_login is not None

    def test_unique_username(self, app, test_user):
        """Test: Username muss eindeutig sein"""
        with app.app_context():
            duplicate_user = User(
                username='testuser',  # Already exists
                email='different@example.com'
            )
            duplicate_user.set_password('pass123')

            db.session.add(duplicate_user)

            # Should raise IntegrityError
            with pytest.raises(Exception):
                db.session.commit()

    def test_unique_email(self, app, test_user):
        """Test: Email muss eindeutig sein"""
        with app.app_context():
            duplicate_user = User(
                username='differentuser',
                email='test@example.com'  # Already exists
            )
            duplicate_user.set_password('pass123')

            db.session.add(duplicate_user)

            # Should raise IntegrityError
            with pytest.raises(Exception):
                db.session.commit()
