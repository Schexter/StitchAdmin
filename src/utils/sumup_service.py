# -*- coding: utf-8 -*-
"""
SUMUP-SERVICE - Integration für SumUp-Zahlungen
=================================================================

Erstellt von: Hans Hahn - Alle Rechte vorbehalten
Datum: 10. Juli 2024
Zweck: Service-Klasse für die Interaktion mit der SumUp API

Features:
- Erstellen von Zahlungs-Checkouts
- API-Key Authentifizierung (aus CompanySettings)
- Optional: OAuth2-Flow für die Kontoverknüpfung
"""

import os
import uuid
import logging
import requests
from flask import url_for, current_app
from src.models import db

logger = logging.getLogger(__name__)

# Offizielle SumUp API Endpunkte
SUMUP_API_BASE_URL = "https://api.sumup.com"
SUMUP_AUTH_URL = f"{SUMUP_API_BASE_URL}/authorize"
SUMUP_TOKEN_URL = f"{SUMUP_API_BASE_URL}/token"
SUMUP_CHECKOUT_URL = f"{SUMUP_API_BASE_URL}/v0.1/checkouts"

class SumUpService:
    """
    Service-Klasse für die SumUp-Integration.
    Nutzt primaer den API-Key aus CompanySettings.
    """

    def __init__(self):
        self.client_id = os.environ.get('SUMUP_CLIENT_ID')
        self.client_secret = os.environ.get('SUMUP_CLIENT_SECRET')

    def _get_api_key(self):
        """Holt API-Key aus CompanySettings"""
        try:
            from src.models.company_settings import CompanySettings
            settings = CompanySettings.get_settings()
            return getattr(settings, 'sumup_api_key', None) or None
        except Exception:
            return None

    def _get_merchant_code(self):
        """Holt Merchant-Code aus CompanySettings"""
        try:
            from src.models.company_settings import CompanySettings
            settings = CompanySettings.get_settings()
            return getattr(settings, 'sumup_merchant_code', None) or None
        except Exception:
            return None

    def is_configured(self):
        """Prueft ob SumUp konfiguriert ist (API-Key oder OAuth)"""
        if self._get_api_key():
            return True
        try:
            from src.models.sumup_token import SumUpToken
            token = SumUpToken.get_token()
            return token is not None
        except Exception:
            return False

    def get_authorization_url(self, redirect_uri=None):
        """Generiert URL fuer OAuth2-Flow (optional)"""
        if not self.client_id:
            return None

        if not redirect_uri:
            redirect_uri = url_for('settings.sumup_callback', _external=True)
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': redirect_uri,
            'scope': 'payments transactions.history',
            'state': str(uuid.uuid4())
        }

        req = requests.Request('GET', SUMUP_AUTH_URL, params=params)
        return req.prepare().url

    def exchange_code_for_token(self, code, redirect_uri=None):
        """Tauscht Autorisierungscode gegen Token (OAuth)"""
        if not redirect_uri:
            redirect_uri = url_for('settings.sumup_callback', _external=True)
        data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': redirect_uri
        }

        try:
            from src.models.sumup_token import SumUpToken
            response = requests.post(SUMUP_TOKEN_URL, data=data)
            response.raise_for_status()
            token_data = response.json()
            SumUpToken.save_token(token_data)
            return {'success': True}
        except requests.exceptions.RequestException as e:
            error_content = e.response.json() if e.response else str(e)
            logger.error(f"Fehler beim Austausch des SumUp-Codes: {error_content}")
            return {'success': False, 'error': error_content.get('error_description', str(e))}

    def _get_auth_header(self):
        """
        Holt Authorization-Header.
        Prioritaet: 1) API-Key aus Settings  2) OAuth-Token
        """
        # 1) API-Key aus CompanySettings
        api_key = self._get_api_key()
        if api_key:
            return f'Bearer {api_key}', None

        # 2) Fallback: OAuth-Token
        try:
            from src.models.sumup_token import SumUpToken
            token = SumUpToken.get_token()
            if not token:
                return None, "Kein SumUp-Konto verbunden und kein API-Key hinterlegt."

            if token.is_expired():
                refreshed = self._refresh_token(token)
                if not refreshed:
                    return None, "SumUp-Token abgelaufen. Bitte API-Key in Einstellungen hinterlegen."
                return f'Bearer {refreshed.access_token}', None

            return f'Bearer {token.access_token}', None
        except Exception as e:
            return None, f"SumUp-Authentifizierung fehlgeschlagen: {e}"

    def _refresh_token(self, token_obj):
        """Erneuert abgelaufenen OAuth-Token"""
        if not self.client_id or not self.client_secret:
            return None

        data = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': token_obj.refresh_token
        }

        try:
            from src.models.sumup_token import SumUpToken
            response = requests.post(SUMUP_TOKEN_URL, data=data)
            response.raise_for_status()
            new_token_data = response.json()
            updated_token = SumUpToken.save_token(new_token_data)
            logger.info("SumUp Access Token erneuert.")
            return updated_token
        except requests.exceptions.RequestException as e:
            logger.error(f"Fehler beim Erneuern des SumUp-Tokens: {e}")
            db.session.delete(token_obj)
            db.session.commit()
            return None

    def create_checkout(self, amount, currency='EUR', description='StitchAdmin-Verkauf', sale_uuid=None):
        """Erstellt neuen Checkout bei SumUp"""
        auth_header, error = self._get_auth_header()
        if error:
            return {'success': False, 'error': error}

        merchant_code = self._get_merchant_code()

        headers = {
            'Authorization': auth_header,
            'Content-Type': 'application/json'
        }

        payload = {
            'checkout_reference': sale_uuid or str(uuid.uuid4()),
            'amount': amount,
            'currency': currency,
            'description': description,
            'merchant_code': merchant_code,
            'redirect_url': url_for('kasse.verkauf_interface', _external=True),
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
            error_content = {}
            try:
                error_content = e.response.json() if e.response else {}
            except Exception:
                pass
            error_msg = error_content.get('error_message') or error_content.get('message') or str(e)
            logger.error(f"SumUp Checkout Fehler: {error_msg}")
            return {'success': False, 'error': error_msg}

    def check_connection(self):
        """Prueft ob SumUp-Verbindung funktioniert"""
        auth_header, error = self._get_auth_header()
        if error:
            return {'success': False, 'error': error}

        try:
            headers = {'Authorization': auth_header}
            response = requests.get(f'{SUMUP_API_BASE_URL}/v0.1/me', headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'merchant_code': data.get('merchant_profile', {}).get('merchant_code', ''),
                    'business_name': data.get('merchant_profile', {}).get('legal_type', {}).get('description', '')
                }
            else:
                return {'success': False, 'error': f'HTTP {response.status_code}: {response.text[:200]}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ==========================================
    # TERMINAL / READER API (Cloud API)
    # ==========================================

    def list_readers(self):
        """Listet alle verbundenen SumUp-Terminals/Readers"""
        auth_header, error = self._get_auth_header()
        if error:
            return {'success': False, 'error': error}

        merchant_code = self._get_merchant_code()
        if not merchant_code:
            return {'success': False, 'error': 'Kein Merchant Code konfiguriert'}

        try:
            headers = {'Authorization': auth_header}
            url = f'{SUMUP_API_BASE_URL}/v0.1/merchants/{merchant_code}/readers'
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            readers = response.json()

            # Filtere nur gepaarte/aktive Terminals
            items = readers.get('items', readers) if isinstance(readers, dict) else readers
            if not isinstance(items, list):
                items = []

            result = []
            for r in items:
                result.append({
                    'id': r.get('id', ''),
                    'name': r.get('name', r.get('id', 'Terminal')),
                    'status': r.get('status', 'unknown'),
                    'device': r.get('device', {}),
                })

            return {'success': True, 'readers': result}
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            try:
                if e.response is not None:
                    error_msg = e.response.json().get('message', e.response.text[:200])
            except Exception:
                pass
            logger.error(f"SumUp Readers Fehler: {error_msg}")
            return {'success': False, 'error': error_msg}

    def create_reader_checkout(self, reader_id, amount, currency='EUR', description=None):
        """Sendet eine Zahlung an ein bestimmtes SumUp-Terminal"""
        auth_header, error = self._get_auth_header()
        if error:
            return {'success': False, 'error': error}

        merchant_code = self._get_merchant_code()
        if not merchant_code:
            return {'success': False, 'error': 'Kein Merchant Code konfiguriert'}

        # Betrag in Minor Units (Cent) umrechnen
        minor_unit = 2
        value = int(round(amount * (10 ** minor_unit)))

        headers = {
            'Authorization': auth_header,
            'Content-Type': 'application/json'
        }

        payload = {
            'total_amount': {
                'currency': currency,
                'minor_unit': minor_unit,
                'value': value
            }
        }
        if description:
            payload['description'] = description

        try:
            url = f'{SUMUP_API_BASE_URL}/v0.1/merchants/{merchant_code}/readers/{reader_id}/checkout'
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()

            return {
                'success': True,
                'checkout_id': data.get('id', data.get('client_transaction_id', '')),
                'data': data
            }
        except requests.exceptions.RequestException as e:
            error_content = {}
            try:
                if e.response is not None:
                    error_content = e.response.json()
            except Exception:
                pass
            error_msg = error_content.get('message') or error_content.get('error_message') or str(e)
            logger.error(f"SumUp Reader Checkout Fehler: {error_msg}")
            return {'success': False, 'error': error_msg}

    def terminate_reader_checkout(self, reader_id):
        """Bricht eine laufende Zahlung am Terminal ab"""
        auth_header, error = self._get_auth_header()
        if error:
            return {'success': False, 'error': error}

        merchant_code = self._get_merchant_code()
        if not merchant_code:
            return {'success': False, 'error': 'Kein Merchant Code konfiguriert'}

        try:
            headers = {'Authorization': auth_header}
            url = f'{SUMUP_API_BASE_URL}/v0.1/merchants/{merchant_code}/readers/{reader_id}/terminate'
            response = requests.post(url, headers=headers, timeout=10)
            response.raise_for_status()
            return {'success': True}
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            try:
                if e.response is not None:
                    error_msg = e.response.json().get('message', e.response.text[:200])
            except Exception:
                pass
            return {'success': False, 'error': error_msg}

    def create_reader(self, name, pairing_code):
        """Registriert ein neues SumUp-Terminal (Solo) per Pairing-Code"""
        auth_header, error = self._get_auth_header()
        if error:
            return {'success': False, 'error': error}

        merchant_code = self._get_merchant_code()
        if not merchant_code:
            return {'success': False, 'error': 'Kein Merchant Code konfiguriert'}

        headers = {
            'Authorization': auth_header,
            'Content-Type': 'application/json'
        }
        payload = {
            'name': name,
            'pairing_code': pairing_code.strip().upper()
        }

        try:
            url = f'{SUMUP_API_BASE_URL}/v0.1/merchants/{merchant_code}/readers'
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            logger.info(f"SumUp Reader '{name}' erfolgreich gepairt: {data.get('id', '')}")
            return {'success': True, 'reader': data}
        except requests.exceptions.RequestException as e:
            error_content = {}
            try:
                if e.response is not None:
                    error_content = e.response.json()
            except Exception:
                pass
            error_msg = error_content.get('detail') or error_content.get('message') or str(e)
            logger.error(f"SumUp Reader Pairing Fehler: {error_msg}")
            return {'success': False, 'error': error_msg}

    def delete_reader(self, reader_id):
        """Entfernt ein registriertes Terminal"""
        auth_header, error = self._get_auth_header()
        if error:
            return {'success': False, 'error': error}

        merchant_code = self._get_merchant_code()
        if not merchant_code:
            return {'success': False, 'error': 'Kein Merchant Code konfiguriert'}

        try:
            headers = {'Authorization': auth_header}
            url = f'{SUMUP_API_BASE_URL}/v0.1/merchants/{merchant_code}/readers/{reader_id}'
            response = requests.delete(url, headers=headers, timeout=10)
            response.raise_for_status()
            return {'success': True}
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            try:
                if e.response is not None:
                    error_msg = e.response.json().get('detail', e.response.text[:200])
            except Exception:
                pass
            return {'success': False, 'error': error_msg}

    def get_reader_status(self, reader_id):
        """Holt den aktuellen Status eines Terminals"""
        auth_header, error = self._get_auth_header()
        if error:
            return {'success': False, 'error': error}

        merchant_code = self._get_merchant_code()
        if not merchant_code:
            return {'success': False, 'error': 'Kein Merchant Code konfiguriert'}

        try:
            headers = {'Authorization': auth_header}
            url = f'{SUMUP_API_BASE_URL}/v0.1/merchants/{merchant_code}/readers/{reader_id}'
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return {'success': True, 'data': response.json()}
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            try:
                if e.response is not None:
                    error_msg = e.response.json().get('message', e.response.text[:200])
            except Exception:
                pass
            return {'success': False, 'error': error_msg}


# Globale Instanz
sumup_service = SumUpService()

__all__ = ['SumUpService', 'sumup_service']
