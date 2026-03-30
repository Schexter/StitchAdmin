# -*- coding: utf-8 -*-
"""
E-Mail Automation Models
=========================
Regeln und Logs fuer automatischen E-Mail-Versand bei Status-Aenderungen.

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime
from src.models import db


class EmailAutomationRule(db.Model):
    """Automation-Regel: Bei Event X -> Template Y senden"""
    __tablename__ = 'email_automation_rules'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    # Trigger-Event
    trigger_event = db.Column(db.String(50), nullable=False)
    # z.B. 'order_status', 'workflow_status', 'payment_status', 'design_approval_status'

    trigger_value = db.Column(db.String(50), nullable=False)
    # z.B. 'shipped', 'design_approved', 'paid'

    # E-Mail Template
    template_id = db.Column(db.Integer, db.ForeignKey('email_templates.id', ondelete='SET NULL'), nullable=True)
    template = db.relationship('EmailTemplate')

    # Konfiguration
    is_enabled = db.Column(db.Boolean, default=True)
    delay_minutes = db.Column(db.Integer, default=0)  # 0 = sofort
    send_copy_to = db.Column(db.String(300))  # CC-Adresse(n)

    # Bedingungen (JSON, optional)
    # z.B. {"customer_type": "business", "min_order_value": 100}
    conditions = db.Column(db.JSON)

    # Meta
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Statistiken
    send_count = db.Column(db.Integer, default=0)
    last_sent_at = db.Column(db.DateTime)

    # Relationships
    logs = db.relationship('EmailAutomationLog', backref='rule', lazy='dynamic')

    # === Labels ===

    TRIGGER_EVENTS = {
        'order_status': 'Auftragsstatus',
        'workflow_status': 'Workflow-Status',
        'payment_status': 'Zahlungsstatus',
        'design_approval_status': 'Design-Freigabe',
    }

    TRIGGER_VALUES = {
        'order_status': {
            'accepted': 'Angenommen',
            'in_progress': 'In Bearbeitung',
            'ready': 'Fertig',
            'completed': 'Abgeschlossen',
            'cancelled': 'Storniert',
        },
        'workflow_status': {
            'confirmed': 'Bestaetigt',
            'design_approved': 'Design freigegeben',
            'in_production': 'In Produktion',
            'ready_to_ship': 'Versandbereit',
            'shipped': 'Versendet',
            'invoiced': 'Rechnung gestellt',
            'completed': 'Abgeschlossen',
        },
        'payment_status': {
            'deposit_paid': 'Anzahlung bezahlt',
            'paid': 'Vollstaendig bezahlt',
        },
        'design_approval_status': {
            'sent': 'Zur Freigabe gesendet',
            'approved': 'Freigegeben',
            'rejected': 'Abgelehnt',
        },
    }

    @property
    def trigger_event_label(self):
        return self.TRIGGER_EVENTS.get(self.trigger_event, self.trigger_event)

    @property
    def trigger_value_label(self):
        values = self.TRIGGER_VALUES.get(self.trigger_event, {})
        return values.get(self.trigger_value, self.trigger_value)

    def __repr__(self):
        return f"<EmailAutomationRule {self.id} '{self.name}' [{self.trigger_event}={self.trigger_value}]>"


class EmailAutomationLog(db.Model):
    """Log fuer gesendete Automation-Mails"""
    __tablename__ = 'email_automation_logs'

    id = db.Column(db.Integer, primary_key=True)

    rule_id = db.Column(db.Integer, db.ForeignKey('email_automation_rules.id', ondelete='SET NULL'), nullable=True)
    order_id = db.Column(db.String(50), nullable=True)
    customer_id = db.Column(db.String(50), nullable=True)

    # E-Mail Details
    to_email = db.Column(db.String(300))
    subject = db.Column(db.String(300))
    template_name = db.Column(db.String(200))

    # Status: pending, sent, failed, skipped
    status = db.Column(db.String(20), default='pending')
    error_message = db.Column(db.Text)

    # Trigger-Info
    trigger_event = db.Column(db.String(50))
    trigger_value = db.Column(db.String(50))

    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<EmailAutomationLog {self.id} [{self.status}] -> {self.to_email}>"
