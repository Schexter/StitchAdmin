# -*- coding: utf-8 -*-
"""
E-Mail Automation Service
==========================
Prueft Trigger-Regeln und sendet automatische E-Mails bei Status-Aenderungen.

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import logging
from datetime import datetime

from src.models import db
from src.models.email_automation import EmailAutomationRule, EmailAutomationLog

logger = logging.getLogger(__name__)


class EmailAutomationService:
    """Service fuer automatischen E-Mail-Versand"""

    def check_and_send(self, order, trigger_event, new_value, old_value=None):
        """
        Prueft alle aktiven Regeln fuer ein Event und sendet passende E-Mails.

        Args:
            order: Order-Objekt
            trigger_event: z.B. 'order_status', 'workflow_status'
            new_value: Neuer Status-Wert
            old_value: Alter Status-Wert (optional, fuer Logging)
        """
        if not order or not order.customer:
            return

        customer = order.customer
        if not customer.email:
            logger.info(f'Automation: Kein E-Mail fuer Kunde {customer.id} - uebersprungen')
            return

        # Passende aktive Regeln finden
        rules = EmailAutomationRule.query.filter_by(
            trigger_event=trigger_event,
            trigger_value=new_value,
            is_enabled=True,
        ).all()

        for rule in rules:
            try:
                # Bedingungen pruefen
                if not self._check_conditions(rule, order, customer):
                    self._log(rule, order, customer, 'skipped', 'Bedingungen nicht erfuellt')
                    continue

                # Template laden
                if not rule.template:
                    self._log(rule, order, customer, 'skipped', 'Kein Template zugewiesen')
                    continue

                # Kontext aufbauen
                context = self._build_context(order, customer)

                # Template rendern
                subject, body_text, body_html = rule.template.render(context)

                # Senden
                success = self._send_email(
                    to_email=customer.email,
                    subject=subject,
                    body_html=body_html,
                    body_text=body_text,
                    cc=rule.send_copy_to,
                )

                if success:
                    self._log(rule, order, customer, 'sent', subject=subject)
                    rule.send_count = (rule.send_count or 0) + 1
                    rule.last_sent_at = datetime.utcnow()
                    db.session.commit()

                    # CRM-Kontakthistorie
                    self._save_contact_history(order, customer, subject, body_html)

                    logger.info(
                        f'Automation: E-Mail "{rule.name}" an {customer.email} '
                        f'(Auftrag {order.order_number}) gesendet'
                    )
                else:
                    self._log(rule, order, customer, 'failed', 'SMTP-Versand fehlgeschlagen')

            except Exception as e:
                logger.error(f'Automation-Fehler bei Regel {rule.id}: {e}')
                self._log(rule, order, customer, 'failed', str(e))

    def _check_conditions(self, rule, order, customer):
        """Prueft optionale Bedingungen einer Regel"""
        if not rule.conditions:
            return True

        conditions = rule.conditions

        # Kundentyp pruefen
        if 'customer_type' in conditions:
            if customer.customer_type != conditions['customer_type']:
                return False

        # Mindest-Auftragswert
        if 'min_order_value' in conditions:
            if not order.total_price or order.total_price < conditions['min_order_value']:
                return False

        return True

    def _build_context(self, order, customer):
        """Baut den Template-Kontext fuer eine Bestellung"""
        context = {
            'anrede': self._get_anrede(customer),
            'kunde_name': customer.display_name or '',
            'firma': customer.company_name or '',
            'auftragsnummer': order.order_number or '',
            'auftragsdatum': order.created_at.strftime('%d.%m.%Y') if order.created_at else '',
            'status': order.status or '',
        }

        # Optionale Felder
        if order.total_price:
            context['gesamtbetrag'] = f'{order.total_price:.2f} EUR'

        if order.description:
            context['beschreibung'] = order.description

        if hasattr(order, 'tracking_number') and order.tracking_number:
            context['sendungsnummer'] = order.tracking_number

        if hasattr(order, 'shipping_carrier') and order.shipping_carrier:
            context['versanddienstleister'] = order.shipping_carrier

        return context

    def _get_anrede(self, customer):
        """Ermittelt die Anrede"""
        if hasattr(customer, 'gender'):
            if customer.gender == 'female':
                return 'Frau'
            elif customer.gender == 'male':
                return 'Herr'
        return ''

    def _send_email(self, to_email, subject, body_html, body_text=None, cc=None):
        """Sendet E-Mail ueber SMTP"""
        try:
            from src.services.email_service_new import EmailService
            service = EmailService()

            result = service.send_email(
                to=to_email,
                subject=subject,
                body_html=body_html,
                body_text=body_text or '',
                cc=cc,
            )
            return result.get('success', False)
        except Exception as e:
            logger.error(f'SMTP-Fehler: {e}')
            return False

    def _save_contact_history(self, order, customer, subject, body_html):
        """Speichert in CRM-Kontakthistorie"""
        try:
            from src.models.crm_contact import CustomerContact
            contact = CustomerContact(
                customer_id=customer.id,
                contact_type='email_ausgang',
                subject=f'[Auto] {subject}',
                body_html=body_html,
                email_to=customer.email,
                status='gesendet',
                order_id=order.id if hasattr(order, 'id') else None,
                created_by='System (Automation)',
            )
            db.session.add(contact)
            db.session.commit()
        except Exception as e:
            logger.warning(f'Kontakthistorie konnte nicht gespeichert werden: {e}')

    def _log(self, rule, order, customer, status, error_message=None, subject=None):
        """Erstellt Log-Eintrag"""
        try:
            log = EmailAutomationLog(
                rule_id=rule.id,
                order_id=order.id if order else None,
                customer_id=customer.id if customer else None,
                to_email=customer.email if customer else None,
                subject=subject or (rule.template.subject if rule.template else ''),
                template_name=rule.template.name if rule.template else '',
                status=status,
                error_message=error_message,
                trigger_event=rule.trigger_event,
                trigger_value=rule.trigger_value,
            )
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            logger.error(f'Automation-Log Fehler: {e}')
