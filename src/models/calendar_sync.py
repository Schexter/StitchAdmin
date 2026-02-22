# -*- coding: utf-8 -*-
"""
Calendar Sync Models
====================
CalendarConnection + CalendarSyncMapping fuer Microsoft Graph Kalender-Sync

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime
from src.models import db


class CalendarConnection(db.Model):
    """OAuth-Verbindung zu einem Kalender-Provider"""
    __tablename__ = 'calendar_connections'

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(20), nullable=False, default='microsoft')  # microsoft
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # OAuth Tokens (verschluesselt!)
    access_token_encrypted = db.Column(db.Text)
    refresh_token_encrypted = db.Column(db.Text)
    token_expiry = db.Column(db.DateTime)

    # Sync-Einstellungen
    sync_direction = db.Column(db.String(20), default='bidirectional')  # read_only, write_only, bidirectional
    calendar_id = db.Column(db.String(200))  # Outlook-Kalender-ID
    calendar_name = db.Column(db.String(200))

    # Status
    is_active = db.Column(db.Boolean, default=True)
    last_sync_at = db.Column(db.DateTime)
    last_sync_status = db.Column(db.String(20))
    last_sync_message = db.Column(db.String(500))

    # Meta
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Beziehungen
    user = db.relationship('User', backref='calendar_connections')
    mappings = db.relationship('CalendarSyncMapping', backref='connection', lazy='dynamic')

    def __repr__(self):
        return f"<CalendarConnection {self.provider} user={self.user_id}>"


class CalendarSyncMapping(db.Model):
    """Zuordnung zwischen lokalem Termin und externem Event"""
    __tablename__ = 'calendar_sync_mappings'

    id = db.Column(db.Integer, primary_key=True)
    kalender_termin_id = db.Column(db.Integer, db.ForeignKey('kalender_termine.id'))
    external_event_id = db.Column(db.String(200))
    connection_id = db.Column(db.Integer, db.ForeignKey('calendar_connections.id'), nullable=False)

    last_synced_at = db.Column(db.DateTime)
    sync_hash = db.Column(db.String(64))  # Aenderungs-Erkennung

    def __repr__(self):
        return f"<CalendarSyncMapping local={self.kalender_termin_id} ext={self.external_event_id}>"
