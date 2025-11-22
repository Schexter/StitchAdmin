# -*- coding: utf-8 -*-
"""
Banking-Service für automatische Kontoabfrage
==============================================

Erstellt von: StitchAdmin
Zweck: Integration mit Banken über FinTS/HBCI und PSD2

Unterstützte Methoden:
- FinTS/HBCI (Deutscher Standard)
- PSD2 API (Europäischer Standard)

Funktionen:
- Kontostand abfragen
- Umsätze abrufen
- Zahlungseingänge automatisch Rechnungen zuordnen
"""

import os
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
import re

logger = logging.getLogger(__name__)

# Banking-Libraries (optional)
try:
    from fints.client import FinTS3PinTanClient
    FINTS_AVAILABLE = True
except ImportError:
    FINTS_AVAILABLE = False
    logger.warning("python-fints nicht installiert. Installieren mit: pip install fints")


class BankingService:
    """Service für Banking-Operationen"""

    def __init__(self):
        """Initialisiere Banking Service"""
        self.fints_client = None
        self.bank_credentials = self._load_credentials()

    def _load_credentials(self):
        """
        Lädt Banking-Credentials aus Umgebungsvariablen oder Datenbank

        Umgebungsvariablen:
        - BANK_BLZ: Bankleitzahl
        - BANK_LOGIN: Login/Benutzerkennung
        - BANK_PIN: PIN
        - BANK_ENDPOINT: FinTS-Endpoint (optional)
        """
        return {
            'blz': os.getenv('BANK_BLZ'),
            'login': os.getenv('BANK_LOGIN'),
            'pin': os.getenv('BANK_PIN'),
            'endpoint': os.getenv('BANK_ENDPOINT')  # Optional
        }

    def connect_fints(self, blz=None, login=None, pin=None, endpoint=None):
        """
        Stellt Verbindung zu FinTS-Server her

        Args:
            blz: Bankleitzahl (optional, sonst aus Credentials)
            login: Login/Benutzerkennung (optional)
            pin: PIN (optional)
            endpoint: FinTS-Endpoint URL (optional)

        Returns:
            bool: True wenn erfolgreich verbunden
        """
        if not FINTS_AVAILABLE:
            logger.error("FinTS-Library nicht verfügbar")
            return False

        # Credentials verwenden
        blz = blz or self.bank_credentials.get('blz')
        login = login or self.bank_credentials.get('login')
        pin = pin or self.bank_credentials.get('pin')
        endpoint = endpoint or self.bank_credentials.get('endpoint')

        if not all([blz, login, pin]):
            logger.error("Banking-Credentials fehlen")
            return False

        try:
            # FinTS-Client erstellen
            if endpoint:
                self.fints_client = FinTS3PinTanClient(
                    blz=blz,
                    user=login,
                    pin=pin,
                    endpoint=endpoint
                )
            else:
                self.fints_client = FinTS3PinTanClient(
                    blz=blz,
                    user=login,
                    pin=pin
                )

            logger.info(f"FinTS-Verbindung hergestellt: BLZ {blz}")
            return True

        except Exception as e:
            logger.error(f"Fehler bei FinTS-Verbindung: {str(e)}")
            return False

    def get_accounts(self):
        """
        Holt Liste aller Konten

        Returns:
            List[Dict]: Liste von Konten mit IBAN, Kontonummer, etc.
        """
        if not self.fints_client:
            if not self.connect_fints():
                return []

        try:
            accounts = self.fints_client.get_sepa_accounts()

            result = []
            for account in accounts:
                result.append({
                    'iban': account.iban,
                    'account_number': account.accountnumber,
                    'blz': account.blz,
                    'type': account.type,
                    'currency': getattr(account, 'currency', 'EUR'),
                    'customer_id': account.customer_id
                })

            return result

        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Konten: {str(e)}")
            return []

    def get_balance(self, account=None):
        """
        Holt Kontostand

        Args:
            account: SEPA-Account-Objekt (optional, erstes Konto wenn None)

        Returns:
            Dict: Kontostand-Informationen
        """
        if not self.fints_client:
            if not self.connect_fints():
                return None

        try:
            if not account:
                accounts = self.fints_client.get_sepa_accounts()
                if not accounts:
                    return None
                account = accounts[0]

            balance = self.fints_client.get_balance(account)

            return {
                'iban': account.iban,
                'balance': float(balance.amount.amount),
                'currency': balance.amount.currency,
                'date': balance.date,
                'pending_balance': float(getattr(balance, 'pending_amount', balance.amount).amount) if hasattr(balance, 'pending_amount') else None
            }

        except Exception as e:
            logger.error(f"Fehler beim Abrufen des Kontostands: {str(e)}")
            return None

    def get_transactions(self, start_date=None, end_date=None, account=None):
        """
        Holt Kontoumsätze

        Args:
            start_date: Startdatum (default: vor 30 Tagen)
            end_date: Enddatum (default: heute)
            account: SEPA-Account-Objekt (optional)

        Returns:
            List[Dict]: Liste von Transaktionen
        """
        if not self.fints_client:
            if not self.connect_fints():
                return []

        # Default-Zeitraum: letzte 30 Tage
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        try:
            if not account:
                accounts = self.fints_client.get_sepa_accounts()
                if not accounts:
                    return []
                account = accounts[0]

            transactions = self.fints_client.get_transactions(
                account,
                start_date=start_date,
                end_date=end_date
            )

            result = []
            for trans in transactions:
                transaction_data = trans.data

                result.append({
                    'date': transaction_data.get('date'),
                    'valuta_date': transaction_data.get('valuta_date'),
                    'amount': float(transaction_data.get('amount', 0)),
                    'currency': transaction_data.get('currency', 'EUR'),
                    'purpose': transaction_data.get('purpose', ''),
                    'applicant_name': transaction_data.get('applicant_name', ''),
                    'applicant_iban': transaction_data.get('applicant_iban', ''),
                    'applicant_bic': transaction_data.get('applicant_bic', ''),
                    'recipient_name': transaction_data.get('recipient_name', ''),
                    'recipient_iban': transaction_data.get('recipient_iban', ''),
                    'transaction_code': transaction_data.get('transaction_code', ''),
                    'posting_text': transaction_data.get('posting_text', '')
                })

            return result

        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Transaktionen: {str(e)}")
            return []

    def match_transactions_to_invoices(self, transactions, invoices):
        """
        Ordnet Transaktionen automatisch Rechnungen zu

        Args:
            transactions: Liste von Transaktionen
            invoices: Liste von offenen Rechnungen

        Returns:
            List[Dict]: Matches (transaction, invoice, confidence)
        """
        matches = []

        for transaction in transactions:
            # Nur Eingänge (positive Beträge)
            if transaction['amount'] <= 0:
                continue

            purpose = transaction['purpose'].upper()
            amount = Decimal(str(transaction['amount']))

            for invoice in invoices:
                confidence = 0
                reasons = []

                # Match nach Rechnungsnummer im Verwendungszweck
                if invoice.rechnungsnummer in purpose:
                    confidence += 50
                    reasons.append("Rechnungsnummer gefunden")

                # Match nach Betrag (mit Toleranz von 0.01 EUR)
                invoice_amount = Decimal(str(invoice.offener_betrag))
                if abs(amount - invoice_amount) <= Decimal('0.01'):
                    confidence += 30
                    reasons.append("Betrag stimmt überein")

                # Match nach Kundenname
                kunde_name = invoice.kunde_name.upper()
                applicant_name = transaction['applicant_name'].upper()

                if kunde_name in applicant_name or applicant_name in kunde_name:
                    confidence += 15
                    reasons.append("Kundenname gefunden")

                # Match nach Datum (innerhalb 7 Tage nach Fälligkeit)
                trans_date = transaction['date']
                days_diff = (trans_date - invoice.faelligkeitsdatum).days

                if 0 <= days_diff <= 7:
                    confidence += 5
                    reasons.append("Zeitlich passend")

                # Nur Matches mit ausreichender Confidence
                if confidence >= 50:
                    matches.append({
                        'transaction': transaction,
                        'invoice': invoice,
                        'confidence': confidence,
                        'reasons': reasons,
                        'recommended_action': 'auto_match' if confidence >= 80 else 'manual_review'
                    })

        # Nach Confidence sortieren
        matches.sort(key=lambda x: x['confidence'], reverse=True)

        return matches

    def auto_book_payments(self, matches, min_confidence=80, created_by=None):
        """
        Bucht Zahlungen automatisch für Matches mit hoher Confidence

        Args:
            matches: Liste von Matches (von match_transactions_to_invoices)
            min_confidence: Minimale Confidence für Auto-Buchung (default: 80)
            created_by: Benutzer der die Buchung durchführt

        Returns:
            Dict: Statistik der Buchungen
        """
        from src.models.rechnungsmodul.models import Rechnung, RechnungsZahlung

        stats = {
            'total_matches': len(matches),
            'auto_booked': 0,
            'manual_review': 0,
            'errors': 0
        }

        for match in matches:
            if match['confidence'] < min_confidence:
                stats['manual_review'] += 1
                continue

            try:
                transaction = match['transaction']
                invoice = match['invoice']

                # Prüfe ob schon gebucht
                existing = RechnungsZahlung.query.filter_by(
                    rechnung_id=invoice.id,
                    zahlungsbetrag=transaction['amount']
                ).filter(
                    RechnungsZahlung.zahlungsdatum == transaction['date']
                ).first()

                if existing:
                    logger.info(f"Zahlung für {invoice.rechnungsnummer} bereits gebucht")
                    continue

                # Zahlung buchen
                from src.models import db

                zahlung = RechnungsZahlung(
                    rechnung_id=invoice.id,
                    zahlungsdatum=transaction['date'],
                    zahlungsbetrag=transaction['amount'],
                    zahlungsart='Überweisung',
                    referenz=f"Auto-Import: {transaction['purpose'][:100]}",
                    bemerkungen=f"Automatisch zugeordnet (Confidence: {match['confidence']}%)\n"
                               f"Von: {transaction['applicant_name']}\n"
                               f"IBAN: {transaction['applicant_iban']}"
                )

                db.session.add(zahlung)

                # Rechnung aktualisieren
                invoice.bezahlt_betrag = (invoice.bezahlt_betrag or 0) + transaction['amount']

                if invoice.bezahlt_betrag >= invoice.brutto_gesamt:
                    invoice.status = 'bezahlt'
                    invoice.bezahlt_am = transaction['date']

                db.session.commit()

                stats['auto_booked'] += 1
                logger.info(f"Zahlung für {invoice.rechnungsnummer} automatisch gebucht: {transaction['amount']} EUR")

            except Exception as e:
                logger.error(f"Fehler beim Auto-Buchen: {str(e)}")
                stats['errors'] += 1
                continue

        return stats


# Singleton-Instanz
banking_service = BankingService()
