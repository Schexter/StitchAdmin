# -*- coding: utf-8 -*-
"""
Banking Models
==============
BankAccount + BankTransaction fuer Bank-Synchronisation

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime, date
from src.models import db


class BankAccount(db.Model):
    """Bankkonto fuer FinTS/CSV-Sync"""
    __tablename__ = 'bank_accounts'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    iban = db.Column(db.String(34), unique=True)
    bic = db.Column(db.String(11))
    bank_name = db.Column(db.String(200))

    # FinTS-Zugangsdaten (verschluesselt speichern!)
    fints_blz = db.Column(db.String(8))
    fints_login = db.Column(db.String(100))
    fints_pin_encrypted = db.Column(db.String(500))
    fints_endpoint = db.Column(db.String(500))

    # Auto-Sync
    auto_sync = db.Column(db.Boolean, default=False)
    sync_interval_minutes = db.Column(db.Integer, default=360)

    # Status
    last_sync_at = db.Column(db.DateTime)
    last_sync_status = db.Column(db.String(20))  # success, error
    last_sync_message = db.Column(db.String(500))

    # Saldo
    balance = db.Column(db.Numeric(12, 2))
    balance_date = db.Column(db.Date)

    # Meta
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Beziehungen
    transactions = db.relationship('BankTransaction', backref='bank_account', lazy='dynamic')

    def __repr__(self):
        return f"<BankAccount {self.name} ({self.iban})>"


class BankTransaction(db.Model):
    """Einzelne Bank-Transaktion"""
    __tablename__ = 'bank_transactions'

    id = db.Column(db.Integer, primary_key=True)
    bank_account_id = db.Column(db.Integer, db.ForeignKey('bank_accounts.id'), nullable=False, index=True)

    # Transaktions-Daten
    transaction_date = db.Column(db.Date, nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), default='EUR')

    # Details
    purpose = db.Column(db.Text)
    applicant_name = db.Column(db.String(200))
    applicant_iban = db.Column(db.String(34))

    # Zuordnung
    matched_invoice_id = db.Column(db.Integer, db.ForeignKey('rechnungen.id'))
    match_status = db.Column(db.String(20), default='unmatched')  # unmatched, auto, manual, ignored
    match_confidence = db.Column(db.Integer, default=0)

    # Import-Tracking
    import_source = db.Column(db.String(20))  # fints, csv, mt940
    import_hash = db.Column(db.String(64), unique=True)  # SHA-256 gegen Duplikate

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Beziehung
    matched_invoice = db.relationship('Rechnung', foreign_keys=[matched_invoice_id])

    def __repr__(self):
        return f"<BankTransaction {self.transaction_date} {self.amount}€>"
