# -*- coding: utf-8 -*-
"""
SUMUP-SERVICE - Integration für SumUp-Zahlungen (PRODUKTIV-VERSION)
=================================================================

Erstellt von: Hans Hahn - Alle Rechte vorbehalten
Datum: 10. Juli 2024
Zweck: Service-Klasse für die Interaktion mit der SumUp API

Features:
- Erstellen von Zahlungs-Checkouts
- OAuth2-Flow für die Kontoverknüpfung
- Automatische Erneuerung von Access Tokens
"""

import os
import uuid
import logging
import requests
from flask import url_for, current_app
from src.models import db
from src.models.sumup_token import SumUpToken

logger = logging.getLogger(__name__)

# Offizielle SumUp API Endpunkte
SUMUP_API_BASE_URL = "https://api.sumup.com"
SUMUP_AUTH_URL = f"{SUMUP_API_BASE_URL}/authorize"
SUMUP_TOKEN_URL = f"{SUMUP_API_BASE_URL}/token"
SUMUP_CHECKOUT_URL = f"{SUMUP_API_BASE_URL}/v0.1/checkouts"

class SumUpService:
    """
    Service-Klasse für die SumUp-Integration.
    """
    
    def __init__(self):
        self.client_id = os.environ.get('SUMUP_CLIENT_ID')
        self.client_secret = os.environ.get('SUMUP_CLIENT_SECRET')
        
        if not self.client_id or not self.client_secret:
            logger.critical("SUMUP_CLIENT_ID oder SUMUP_CLIENT_SECRET sind nicht konfiguriert! SumUp-Dienst ist nicht funktionsfähig.")

    def get_authorization_url(self):
        """
        Generiert die URL für den OAuth2-Authentifizierungs-Flow.
        """
        if not self.client_id:
            return None, "SumUp Client ID nicht konfiguriert."

        redirect_uri = url_for('settings.sumup_callback', _external=True)
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': redirect_uri,
            'scope': 'payments transactions.history',
            'state': str(uuid.uuid4())
        }
        
        req = requests.Request('GET', SUMUP_AUTH_URL, params=params)
        return req.prepare().url, None

    def exchange_code_for_token(self, code):
        """
        Tauscht den Autorisierungscode gegen Access- und Refresh-Token.
        """
        redirect_uri = url_for('settings.sumup_callback', _external=True)
        data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': redirect_uri
        }
        
        try:
            response = requests.post(SUMUP_TOKEN_URL, data=data)
            response.raise_for_status()
            token_data = response.json()
            
            # Speichere den Token in der Datenbank
            SumUpToken.save_token(token_data)
            return {'success': True}

        except requests.exceptions.RequestException as e:
            error_content = e.response.json() if e.response else str(e)
            logger.error(f"Fehler beim Austausch des SumUp-Codes: {error_content}")
            return {'success': False, 'error': error_content.get('error_description', str(e))}

    def _refresh_token(self, token_obj):
        """
        Erneuert einen abgelaufenen Access Token mit dem Refresh Token.
        """
        logger.info(f"SumUp Access Token ist abgelaufen. Erneuere Token...")
        data = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': token_obj.refresh_token
        }
        
        try:
            response = requests.post(SUMUP_TOKEN_URL, data=data)
            response.raise_for_status()
            new_token_data = response.json()
            
            # Aktualisiere den Token in der Datenbank
            updated_token = SumUpToken.save_token(new_token_data)
            logger.info("SumUp Access Token erfolgreich erneuert.")
            return updated_token

        except requests.exceptions.RequestException as e:
            logger.error(f"Fehler beim Erneuern des SumUp-Tokens: {e}")
            # Wenn der Refresh fehlschlägt, ist die Verbindung ungültig.
            db.session.delete(token_obj)
            db.session.commit()
            return None

    def _get_valid_token(self):
        """
        Holt den aktuellen Token und erneuert ihn bei Bedarf.
        """
        token = SumUpToken.get_token()
        if not token:
            return None, "Kein SumUp-Konto verbunden."

        if token.is_expired():
            refreshed_token = self._refresh_token(token)
            if not refreshed_token:
                return None, "SumUp-Verbindung ist abgelaufen und konnte nicht erneuert werden. Bitte neu verbinden."
            return refreshed_token, None
        
        return token, None

    def create_checkout(self, amount, currency='EUR', description='StitchAdmin-Verkauf', sale_uuid=None):
        """
        Erstellt einen neuen Checkout bei SumUp mit einem gültigen Token.
        """
        token, error = self._get_valid_token()
        if error:
            return {'success': False, 'error': error}

        headers = {
            'Authorization': f'Bearer {token.access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'checkout_reference': sale_uuid or str(uuid.uuid4()),
            'amount': amount,
            'currency': currency,
            'description': description,
            'pay_to_email': 'hans.hahn@hahn-stickerei.de', # Beispiel, sollte aus den Einstellungen kommen
            'redirect_url': url_for('kasse.verkauf_interface', _external=True),
            'webhook_url': url_for('kasse.webhook_sumup', _external=True)
        }

        try:
            response = requests.post(SUMUP_CHECKOUT_URL, headers=headers, json=payload)
            response.raise_for_status()
            checkout_data = response.json()
            
            return {
                'success': True,
                'checkout_id': checkout_data['id'],
                'amount': checkout_data['amount'],
                'currency': checkout_data['currency'],
                'status': checkout_data['status']
            }

        except requests.exceptions.RequestException as e:
            error_content = e.response.json() if e.response else str(e)
            logger.error(f"Fehler beim Erstellen des SumUp Checkouts: {error_content}")
            return {'success': False, 'error': error_content.get('error_message', str(e))}

# Globale Instanz für einfachen Zugriff
sumup_service = SumUpService()

__all__ = ['SumUpService', 'sumup_service']
