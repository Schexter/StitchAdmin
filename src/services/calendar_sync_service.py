# -*- coding: utf-8 -*-
"""
Calendar Sync Service (Microsoft Graph)
========================================
OAuth2-Authentifizierung und Kalender-Synchronisation mit Microsoft Outlook.

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

from src.models import db
from src.models.calendar_sync import CalendarConnection, CalendarSyncMapping

logger = logging.getLogger(__name__)

GRAPH_BASE = 'https://graph.microsoft.com/v1.0'
AUTH_BASE = 'https://login.microsoftonline.com'


class MicrosoftGraphCalendarService:
    """Microsoft Graph API Kalender-Service"""

    def __init__(self):
        self.client_id = None
        self.client_secret = None
        self.tenant_id = 'common'
        self.redirect_uri = None
        self._load_config()

    def _load_config(self):
        """Laedt Microsoft Graph Konfiguration aus CompanySettings"""
        try:
            from src.models.company_settings import CompanySettings
            settings = CompanySettings.query.first()
            if settings:
                self.client_id = getattr(settings, 'ms_graph_client_id', None)
                self.client_secret = getattr(settings, 'ms_graph_client_secret', None)
                self.tenant_id = getattr(settings, 'ms_graph_tenant_id', None) or 'common'
        except Exception:
            pass

    def is_configured(self) -> bool:
        """Prueft ob Microsoft Graph konfiguriert ist"""
        return bool(self.client_id and self.client_secret)

    def get_auth_url(self, redirect_uri: str) -> str:
        """Generiert OAuth2 Authorization URL"""
        self.redirect_uri = redirect_uri
        scopes = 'Calendars.ReadWrite offline_access'
        return (
            f'{AUTH_BASE}/{self.tenant_id}/oauth2/v2.0/authorize'
            f'?client_id={self.client_id}'
            f'&response_type=code'
            f'&redirect_uri={redirect_uri}'
            f'&scope={scopes}'
            f'&response_mode=query'
        )

    def exchange_code(self, code: str, redirect_uri: str) -> Optional[Dict]:
        """Tauscht Authorization Code gegen Tokens"""
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
            'scope': 'Calendars.ReadWrite offline_access',
        }

        resp = requests.post(
            f'{AUTH_BASE}/{self.tenant_id}/oauth2/v2.0/token',
            data=data
        )

        if resp.status_code == 200:
            return resp.json()
        logger.error(f"Token-Exchange fehlgeschlagen: {resp.text}")
        return None

    def refresh_token(self, connection: CalendarConnection) -> bool:
        """Erneuert abgelaufenen Access Token"""
        if not connection.refresh_token_encrypted:
            return False

        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': connection.refresh_token_encrypted,
            'grant_type': 'refresh_token',
            'scope': 'Calendars.ReadWrite offline_access',
        }

        resp = requests.post(
            f'{AUTH_BASE}/{self.tenant_id}/oauth2/v2.0/token',
            data=data
        )

        if resp.status_code == 200:
            tokens = resp.json()
            connection.access_token_encrypted = tokens['access_token']
            if 'refresh_token' in tokens:
                connection.refresh_token_encrypted = tokens['refresh_token']
            connection.token_expiry = datetime.utcnow() + timedelta(seconds=tokens.get('expires_in', 3600))
            db.session.commit()
            return True

        logger.error(f"Token-Refresh fehlgeschlagen: {resp.text}")
        return False

    def _get_headers(self, connection: CalendarConnection) -> Dict:
        """Erstellt Auth-Headers, refresht Token bei Bedarf"""
        if connection.token_expiry and connection.token_expiry < datetime.utcnow():
            self.refresh_token(connection)

        return {
            'Authorization': f'Bearer {connection.access_token_encrypted}',
            'Content-Type': 'application/json',
        }

    def list_calendars(self, connection: CalendarConnection) -> List[Dict]:
        """Listet alle Kalender des Benutzers"""
        headers = self._get_headers(connection)
        resp = requests.get(f'{GRAPH_BASE}/me/calendars', headers=headers)

        if resp.status_code == 200:
            return resp.json().get('value', [])
        logger.error(f"Kalender-Abruf fehlgeschlagen: {resp.status_code}")
        return []

    def fetch_events(self, connection: CalendarConnection,
                     start: datetime = None, end: datetime = None) -> List[Dict]:
        """Holt Events aus Outlook-Kalender"""
        headers = self._get_headers(connection)
        start = start or datetime.utcnow()
        end = end or (start + timedelta(days=30))

        calendar_path = f'/me/calendars/{connection.calendar_id}/events' if connection.calendar_id else '/me/events'

        resp = requests.get(
            f'{GRAPH_BASE}{calendar_path}',
            headers=headers,
            params={
                '$filter': f"start/dateTime ge '{start.isoformat()}' and end/dateTime le '{end.isoformat()}'",
                '$top': 100,
                '$orderby': 'start/dateTime',
            }
        )

        if resp.status_code == 200:
            return resp.json().get('value', [])
        return []

    def create_event(self, connection: CalendarConnection, termin) -> Optional[str]:
        """Erstellt Event in Outlook"""
        headers = self._get_headers(connection)
        calendar_path = f'/me/calendars/{connection.calendar_id}/events' if connection.calendar_id else '/me/events'

        event_data = {
            'subject': termin.titel,
            'body': {'contentType': 'text', 'content': termin.beschreibung or ''},
            'start': {
                'dateTime': termin.start_zeit.isoformat(),
                'timeZone': 'Europe/Berlin',
            },
            'end': {
                'dateTime': termin.end_zeit.isoformat(),
                'timeZone': 'Europe/Berlin',
            },
            'location': {'displayName': termin.ort or ''},
        }

        resp = requests.post(f'{GRAPH_BASE}{calendar_path}', headers=headers, json=event_data)

        if resp.status_code in (200, 201):
            return resp.json().get('id')
        logger.error(f"Event-Erstellung fehlgeschlagen: {resp.status_code} {resp.text}")
        return None

    def update_event(self, connection: CalendarConnection, event_id: str, termin) -> bool:
        """Aktualisiert Event in Outlook"""
        headers = self._get_headers(connection)

        event_data = {
            'subject': termin.titel,
            'body': {'contentType': 'text', 'content': termin.beschreibung or ''},
            'start': {
                'dateTime': termin.start_zeit.isoformat(),
                'timeZone': 'Europe/Berlin',
            },
            'end': {
                'dateTime': termin.end_zeit.isoformat(),
                'timeZone': 'Europe/Berlin',
            },
            'location': {'displayName': termin.ort or ''},
        }

        resp = requests.patch(f'{GRAPH_BASE}/me/events/{event_id}', headers=headers, json=event_data)
        return resp.status_code == 200

    def delete_event(self, connection: CalendarConnection, event_id: str) -> bool:
        """Loescht Event in Outlook"""
        headers = self._get_headers(connection)
        resp = requests.delete(f'{GRAPH_BASE}/me/events/{event_id}', headers=headers)
        return resp.status_code == 204

    def sync_to_outlook(self, connection_id: int) -> Dict:
        """Synchronisiert lokale Termine nach Outlook"""
        from src.models.kalender import KalenderTermin

        connection = CalendarConnection.query.get(connection_id)
        if not connection or not connection.is_active:
            return {'error': 'Verbindung nicht aktiv'}

        # Lokale Termine der naechsten 30 Tage
        now = datetime.utcnow()
        termine = KalenderTermin.query.filter(
            KalenderTermin.start_zeit >= now,
            KalenderTermin.start_zeit <= now + timedelta(days=30)
        ).all()

        created = 0
        updated = 0
        errors = 0

        for termin in termine:
            try:
                mapping = CalendarSyncMapping.query.filter_by(
                    kalender_termin_id=termin.id,
                    connection_id=connection.id
                ).first()

                current_hash = self._termin_hash(termin)

                if mapping and mapping.external_event_id:
                    # Update wenn geaendert
                    if mapping.sync_hash != current_hash:
                        if self.update_event(connection, mapping.external_event_id, termin):
                            mapping.sync_hash = current_hash
                            mapping.last_synced_at = datetime.utcnow()
                            updated += 1
                else:
                    # Neues Event erstellen
                    event_id = self.create_event(connection, termin)
                    if event_id:
                        if not mapping:
                            mapping = CalendarSyncMapping(
                                kalender_termin_id=termin.id,
                                connection_id=connection.id,
                            )
                            db.session.add(mapping)
                        mapping.external_event_id = event_id
                        mapping.sync_hash = current_hash
                        mapping.last_synced_at = datetime.utcnow()
                        created += 1

            except Exception as e:
                logger.warning(f"Sync-Fehler fuer Termin {termin.id}: {e}")
                errors += 1

        connection.last_sync_at = datetime.utcnow()
        connection.last_sync_status = 'success' if not errors else 'partial'
        connection.last_sync_message = f'{created} erstellt, {updated} aktualisiert'
        db.session.commit()

        return {'created': created, 'updated': updated, 'errors': errors}

    def _termin_hash(self, termin) -> str:
        """Erzeugt Hash fuer Aenderungserkennung"""
        data = f"{termin.titel}|{termin.start_zeit}|{termin.end_zeit}|{termin.ort}|{termin.beschreibung}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]
