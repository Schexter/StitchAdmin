# -*- coding: utf-8 -*-
"""
SUMUP-SERVICE - Integration für SumUp-Zahlungen
================================================

Erstellt von: Hans Hahn - Alle Rechte vorbehalten
Datum: 10. Juli 2024
Zweck: Service-Klasse für die Interaktion mit der SumUp API

Features:
- Erstellen von Zahlungs-Checkouts
- Verarbeiten von Webhooks
- Abrufen von Transaktionsdetails
"""

import os
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SumUpService:
    """
    Service-Klasse für die SumUp-Integration.
    Diese Klasse kapselt die Logik für die Kommunikation mit der SumUp API.
    """
    
    def __init__(self, app_id=None, app_secret=None, is_mock=True):
        """
        Initialisiert den SumUp-Service.
        
        :param app_id: SumUp Application ID
        :param app_secret: SumUp Application Secret
        :param is_mock: Wenn True, werden keine echten API-Aufrufe gemacht.
        """
        self.app_id = app_id or os.environ.get('SUMUP_APP_ID')
        self.app_secret = app_secret or os.environ.get('SUMUP_APP_SECRET')
        self.is_mock = is_mock
        
        if not self.is_mock and (not self.app_id or not self.app_secret):
            logger.warning("SumUp Service ist im Live-Modus, aber es fehlen APP_ID oder APP_SECRET.")

    def create_checkout(self, amount, currency='EUR', description='StitchAdmin-Verkauf', receipt_id=None):
        """
        Erstellt einen neuen Checkout bei SumUp.
        
        :param amount: Der zu zahlende Betrag (z.B. 12.99)
        :param currency: Währung (Standard: EUR)
        :param description: Beschreibung der Zahlung
        :param receipt_id: Interne Beleg-ID zur Nachverfolgung
        :return: Ein Dictionary mit den Checkout-Details oder eine Fehlermeldung.
        """
        if self.is_mock:
            # Mock-Implementierung
            checkout_id = f"mock_checkout_{uuid.uuid4()}"
            logger.info(f"Mock-Checkout erstellt: {checkout_id} für Betrag {amount} {currency}")
            return {
                'success': True,
                'checkout_id': checkout_id,
                'amount': amount,
                'currency': currency,
                'status': 'PENDING',
                'created_at': datetime.utcnow().isoformat()
            }
        else:
            # TODO: Echte API-Implementierung
            # - Authentifizierung mit SumUp (OAuth2)
            # - POST-Request an /checkouts Endpunkt
            logger.error("Echte SumUp API ist noch nicht implementiert.")
            return {'success': False, 'error': 'Nicht implementiert'}

    def handle_webhook(self, payload):
        """
        Verarbeitet einen eingehenden Webhook von SumUp.
        
        :param payload: Das JSON-Payload vom SumUp-Webhook
        :return: Ein Dictionary mit dem Ergebnis der Verarbeitung.
        """
        event_type = payload.get('event_type')
        
        if event_type == 'CHECKOUT_STATUS_CHANGED':
            checkout_id = payload.get('checkout_id')
            new_status = payload.get('status')
            
            logger.info(f"Webhook erhalten: Checkout {checkout_id} hat neuen Status: {new_status}")
            
            # Hier würde die Logik zur Aktualisierung der Bestellung/des Belegs stehen.
            # z.B. Aufruf einer Funktion, die den Verkauf abschließt.
            
            return {
                'success': True,
                'message': f'Webhook für Checkout {checkout_id} verarbeitet.',
                'status': new_status
            }
        
        logger.warning(f"Unbekannter Webhook-Typ erhalten: {event_type}")
        return {'success': False, 'error': 'Unbekannter Event-Typ'}

# Globale Instanz für einfachen Zugriff
# In einer echten Anwendung würde dies besser über die App-Factory verwaltet werden.
sumup_service = SumUpService(is_mock=True)

__all__ = ['SumUpService', 'sumup_service']
