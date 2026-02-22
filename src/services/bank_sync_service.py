# -*- coding: utf-8 -*-
"""
Bank-Sync Service
=================
Synchronisiert Bankkonten via FinTS und importiert Transaktionen.
Nutzt bestehenden BankingService fuer FinTS-Kommunikation.

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import hashlib
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from src.models import db
from src.models.banking import BankAccount, BankTransaction

logger = logging.getLogger(__name__)


class BankSyncService:
    """Service fuer Bank-Synchronisation"""

    def sync_account(self, account_id: int) -> Dict:
        """
        Synchronisiert ein Bankkonto via FinTS.

        Returns:
            Dict mit new_transactions, duplicates, errors
        """
        from src.services.banking_service import BankingService

        account = BankAccount.query.get(account_id)
        if not account:
            return {'error': 'Konto nicht gefunden'}

        service = BankingService()
        connected = service.connect_fints(
            blz=account.fints_blz,
            login=account.fints_login,
            pin=account.fints_pin_encrypted,  # TODO: Entschluesseln
            endpoint=account.fints_endpoint,
        )

        if not connected:
            account.last_sync_status = 'error'
            account.last_sync_message = 'FinTS-Verbindung fehlgeschlagen'
            db.session.commit()
            return {'error': 'FinTS-Verbindung fehlgeschlagen'}

        # Saldo abrufen
        try:
            balance_data = service.get_balance()
            if balance_data:
                account.balance = Decimal(str(balance_data['balance']))
                account.balance_date = balance_data.get('date', date.today())
        except Exception as e:
            logger.warning(f"Saldo-Abruf fehlgeschlagen: {e}")

        # Transaktionen abrufen (letzte 30 Tage)
        start = account.last_sync_at.date() if account.last_sync_at else date.today() - timedelta(days=30)
        transactions = service.get_transactions(start_date=start)

        new_count = 0
        dup_count = 0

        for tx in transactions:
            tx_hash = self._transaction_hash(tx, account.id)

            existing = BankTransaction.query.filter_by(import_hash=tx_hash).first()
            if existing:
                dup_count += 1
                continue

            bank_tx = BankTransaction(
                bank_account_id=account.id,
                transaction_date=tx.get('date', date.today()),
                amount=Decimal(str(tx.get('amount', 0))),
                currency=tx.get('currency', 'EUR'),
                purpose=tx.get('purpose', ''),
                applicant_name=tx.get('applicant_name', ''),
                applicant_iban=tx.get('applicant_iban', ''),
                import_source='fints',
                import_hash=tx_hash,
            )
            db.session.add(bank_tx)
            new_count += 1

        account.last_sync_at = datetime.utcnow()
        account.last_sync_status = 'success'
        account.last_sync_message = f'{new_count} neue Transaktionen'
        db.session.commit()

        return {
            'new_transactions': new_count,
            'duplicates': dup_count,
            'balance': float(account.balance) if account.balance else None,
        }

    def auto_match_transactions(self, account_id: int) -> Dict:
        """
        Automatischer Abgleich ungematchter Transaktionen mit offenen Rechnungen.

        Returns:
            Dict mit matched, unmatched
        """
        from src.models.rechnungsmodul.models import Rechnung, RechnungsStatus

        unmatched = BankTransaction.query.filter_by(
            bank_account_id=account_id,
            match_status='unmatched',
        ).filter(BankTransaction.amount > 0).all()

        if not unmatched:
            return {'matched': 0, 'unmatched': 0}

        # Offene Rechnungen laden
        offene_rechnungen = Rechnung.query.filter(
            Rechnung.status.in_([RechnungsStatus.GESENDET, RechnungsStatus.FAELLIG, RechnungsStatus.UEBERFAELLIG])
        ).all()

        matched = 0
        for tx in unmatched:
            best_match = None
            best_confidence = 0

            for rechnung in offene_rechnungen:
                confidence = self._calc_match_confidence(tx, rechnung)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = rechnung

            if best_match and best_confidence >= 50:
                tx.matched_invoice_id = best_match.id
                tx.match_confidence = best_confidence
                tx.match_status = 'auto' if best_confidence >= 80 else 'unmatched'
                if best_confidence >= 80:
                    matched += 1

        db.session.commit()
        return {'matched': matched, 'unmatched': len(unmatched) - matched}

    def manual_match(self, tx_id: int, invoice_id: int) -> bool:
        """Manueller Abgleich einer Transaktion mit einer Rechnung"""
        tx = BankTransaction.query.get(tx_id)
        if not tx:
            return False

        tx.matched_invoice_id = invoice_id
        tx.match_status = 'manual'
        tx.match_confidence = 100
        db.session.commit()
        return True

    def ignore_transaction(self, tx_id: int) -> bool:
        """Transaktion als ignoriert markieren"""
        tx = BankTransaction.query.get(tx_id)
        if not tx:
            return False

        tx.match_status = 'ignored'
        db.session.commit()
        return True

    def test_connection(self, blz: str, login: str, pin: str, endpoint: str = None) -> Dict:
        """Testet FinTS-Verbindung"""
        from src.services.banking_service import BankingService

        service = BankingService()
        connected = service.connect_fints(blz=blz, login=login, pin=pin, endpoint=endpoint)

        if not connected:
            return {'success': False, 'message': 'Verbindung fehlgeschlagen'}

        accounts = service.get_accounts()
        return {
            'success': True,
            'message': f'{len(accounts)} Konten gefunden',
            'accounts': accounts,
        }

    def _transaction_hash(self, tx: Dict, account_id: int) -> str:
        """Erzeugt eindeutigen Hash fuer eine Transaktion"""
        data = f"{account_id}|{tx.get('date')}|{tx.get('amount')}|{tx.get('purpose', '')}|{tx.get('applicant_name', '')}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _calc_match_confidence(self, tx: BankTransaction, rechnung) -> int:
        """Berechnet Uebereinstimmung zwischen Transaktion und Rechnung"""
        confidence = 0

        # Betrag-Match
        if rechnung.brutto_gesamt:
            diff = abs(tx.amount - rechnung.brutto_gesamt)
            if diff <= Decimal('0.01'):
                confidence += 35

        # Rechnungsnummer im Verwendungszweck
        purpose_upper = (tx.purpose or '').upper()
        if rechnung.rechnungsnummer and rechnung.rechnungsnummer.upper() in purpose_upper:
            confidence += 50

        # Kundenname
        if tx.applicant_name and rechnung.kunde_name:
            name_upper = rechnung.kunde_name.upper()
            app_upper = tx.applicant_name.upper()
            if name_upper in app_upper or app_upper in name_upper:
                confidence += 15

        return min(confidence, 100)
