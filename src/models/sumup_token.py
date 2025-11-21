# -*- coding: utf-8 -*-
"""
SUMUP-TOKEN MODELL
==================

Erstellt von: Hans Hahn - Alle Rechte vorbehalten
Datum: 10. Juli 2024
Zweck: Datenbankmodell zum sicheren Speichern von SumUp OAuth2-Tokens.
"""

from datetime import datetime, timedelta
from src.models.models import db

class SumUpToken(db.Model):
    """
    Speichert die OAuth2-Tokens für die SumUp-API.
    """
    __tablename__ = 'sumup_token'

    id = db.Column(db.Integer, primary_key=True)
    
    # Verknüpfung zum Benutzer, der das Konto verknüpft hat.
    # Falls das System nur eine globale SumUp-Verbindung hat, kann dies optional sein.
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, unique=True)
    user = db.relationship('User', backref=db.backref('sumup_token', uselist=False))

    access_token = db.Column(db.String(2048), nullable=False)
    refresh_token = db.Column(db.String(2048), nullable=False)
    
    # Wann der Access Token abläuft
    expires_at = db.Column(db.DateTime, nullable=False)
    
    # Zusätzliche Informationen
    token_type = db.Column(db.String(50))
    scope = db.Column(db.String(512))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def is_expired(self):
        """Prüft, ob der Access Token abgelaufen ist."""
        return datetime.utcnow() >= self.expires_at

    @staticmethod
    def save_token(token_data, user_id=None):
        """
        Speichert oder aktualisiert einen Token in der Datenbank.
        """
        # Berechne das Ablaufdatum
        expires_in = token_data.get('expires_in', 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        # Suche nach einem existierenden Token für diesen Benutzer (oder global)
        existing_token = SumUpToken.query.filter_by(user_id=user_id).first()

        if existing_token:
            # Token aktualisieren
            token = existing_token
            token.access_token = token_data['access_token']
            token.refresh_token = token_data['refresh_token']
            token.expires_at = expires_at
            token.scope = token_data.get('scope')
        else:
            # Neuen Token erstellen
            token = SumUpToken(
                user_id=user_id,
                access_token=token_data['access_token'],
                refresh_token=token_data['refresh_token'],
                expires_at=expires_at,
                token_type=token_data.get('token_type'),
                scope=token_data.get('scope')
            )
            db.session.add(token)
        
        try:
            db.session.commit()
            return token
        except Exception as e:
            db.session.rollback()
            print(f"Fehler beim Speichern des SumUp-Tokens: {e}")
            return None

    @staticmethod
    def get_token(user_id=None):
        """
        Holt den aktuellen Token aus der Datenbank.
        """
        return SumUpToken.query.filter_by(user_id=user_id).first()

    def __repr__(self):
        return f"<SumUpToken (User: {self.user_id}, Expires: {self.expires_at})>"

__all__ = ['SumUpToken']
