# -*- coding: utf-8 -*-
"""
ERWEITERTER E-MAIL SERVICE
===========================
Vollständige E-Mail-Funktionalität für StitchAdmin 2.0

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import smtplib
import imaplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formataddr
import os
from datetime import datetime
import re
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class EmailService:
    """
    Zentraler E-Mail-Service für alle E-Mail-Funktionen
    
    Features:
    - SMTP-Versand
    - Vorlagen-System
    - Platzhalter-Ersetzung
    - HTML-E-Mails
    - Anhänge
    - Tracking
    """
    
    def __init__(self, account_id: int = None):
        """
        Initialisiert den E-Mail-Service
        
        Args:
            account_id: Optional - ID eines spezifischen EmailAccount
        """
        self.account = None
        self.smtp = None
        
        if account_id:
            from src.models.document import EmailAccount
            self.account = EmailAccount.query.get(account_id)
        else:
            self._load_default_account()
    
    def _load_default_account(self):
        """Lädt Standard-E-Mail-Account aus Settings"""
        try:
            from src.models import CompanySettings
            settings = CompanySettings.get_settings()
            
            # Erstelle virtuellen Account aus Settings
            self.smtp_config = {
                'server': getattr(settings, 'smtp_server', 'localhost'),
                'port': getattr(settings, 'smtp_port', 587),
                'username': getattr(settings, 'smtp_username', ''),
                'password': getattr(settings, 'smtp_password', ''),
                'use_tls': getattr(settings, 'smtp_use_tls', True),
                'from_email': getattr(settings, 'company_email', ''),
                'from_name': getattr(settings, 'company_name', 'StitchAdmin')
            }
        except Exception as e:
            logger.warning(f"Could not load email settings: {e}")
            self.smtp_config = {
                'server': 'localhost',
                'port': 587,
                'use_tls': True
            }
    
    def send_email(self, 
                   to: str,
                   subject: str,
                   body: str,
                   html_body: str = None,
                   attachments: List[str] = None,
                   cc: str = None,
                   bcc: str = None,
                   reply_to: str = None,
                   track: bool = True) -> Dict[str, Any]:
        """
        Sendet eine E-Mail
        
        Args:
            to: Empfänger-Adresse(n), kommasepariert
            subject: Betreff
            body: Text-Body
            html_body: Optional HTML-Body
            attachments: Liste von Dateipfaden
            cc: CC-Empfänger
            bcc: BCC-Empfänger
            reply_to: Reply-To Adresse
            track: E-Mail-Versand tracken
            
        Returns:
            Dict mit success, message_id, error
        """
        result = {
            'success': False,
            'message_id': None,
            'error': None
        }
        
        try:
            # Hole SMTP-Config
            if self.account:
                smtp_server = self.account.smtp_server
                smtp_port = self.account.smtp_port
                smtp_user = self.account.smtp_username or self.account.email_address
                smtp_pass = self.account.get_smtp_password()
                use_tls = self.account.smtp_use_tls
                from_email = self.account.email_address
                from_name = self.account.display_name or ''
            else:
                smtp_server = self.smtp_config.get('server')
                smtp_port = self.smtp_config.get('port', 587)
                smtp_user = self.smtp_config.get('username')
                smtp_pass = self.smtp_config.get('password')
                use_tls = self.smtp_config.get('use_tls', True)
                from_email = self.smtp_config.get('from_email')
                from_name = self.smtp_config.get('from_name', '')
            
            if not smtp_server or not from_email:
                result['error'] = 'E-Mail-Server nicht konfiguriert'
                return result
            
            # Erstelle Nachricht
            msg = MIMEMultipart('alternative')
            msg['From'] = formataddr((from_name, from_email))
            msg['To'] = to
            msg['Subject'] = subject
            
            if cc:
                msg['Cc'] = cc
            if reply_to:
                msg['Reply-To'] = reply_to
            
            # Message-ID generieren
            import uuid
            message_id = f"<{uuid.uuid4()}@stitchadmin.local>"
            msg['Message-ID'] = message_id
            
            # Body hinzufügen
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            if html_body:
                msg.attach(MIMEText(html_body, 'html', 'utf-8'))
            
            # Anhänge
            if attachments:
                for filepath in attachments:
                    if os.path.exists(filepath):
                        self._attach_file(msg, filepath)
            
            # SMTP-Verbindung
            if use_tls:
                self.smtp = smtplib.SMTP(smtp_server, smtp_port)
                self.smtp.starttls()
            else:
                self.smtp = smtplib.SMTP_SSL(smtp_server, smtp_port)
            
            if smtp_user and smtp_pass:
                self.smtp.login(smtp_user, smtp_pass)
            
            # Alle Empfänger sammeln
            recipients = [addr.strip() for addr in to.split(',')]
            if cc:
                recipients.extend([addr.strip() for addr in cc.split(',')])
            if bcc:
                recipients.extend([addr.strip() for addr in bcc.split(',')])
            
            # Senden
            self.smtp.send_message(msg)
            self.smtp.quit()
            
            result['success'] = True
            result['message_id'] = message_id
            
            # Tracking
            if track:
                self._track_sent_email(to, subject, message_id)
            
            logger.info(f"Email sent to {to}: {subject}")
            
        except smtplib.SMTPAuthenticationError as e:
            result['error'] = 'SMTP-Authentifizierung fehlgeschlagen'
            logger.error(f"SMTP auth error: {e}")
        except smtplib.SMTPException as e:
            result['error'] = f'SMTP-Fehler: {str(e)}'
            logger.error(f"SMTP error: {e}")
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Email send error: {e}")
        
        return result
    
    def _attach_file(self, msg: MIMEMultipart, filepath: str):
        """Fügt Datei als Anhang hinzu"""
        filename = os.path.basename(filepath)
        
        # MIME-Type erkennen
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filepath)
        if mime_type is None:
            mime_type = 'application/octet-stream'
        
        main_type, sub_type = mime_type.split('/', 1)
        
        with open(filepath, 'rb') as f:
            if main_type == 'text':
                part = MIMEText(f.read().decode('utf-8', errors='ignore'), _subtype=sub_type)
            else:
                part = MIMEBase(main_type, sub_type)
                part.set_payload(f.read())
                encoders.encode_base64(part)
        
        part.add_header('Content-Disposition', 'attachment', filename=filename)
        msg.attach(part)
    
    def _track_sent_email(self, to: str, subject: str, message_id: str):
        """Speichert gesendete E-Mail für Tracking"""
        try:
            from src.models.models import db, ActivityLog
            
            activity = ActivityLog(
                username='system',
                action='email_sent',
                details=f'E-Mail an {to}: {subject[:100]}'
            )
            db.session.add(activity)
            db.session.commit()
        except Exception as e:
            logger.warning(f"Email tracking failed: {e}")
    
    # ==========================================
    # VORLAGEN-BASIERTE E-MAILS
    # ==========================================
    
    def send_template_email(self,
                            to: str,
                            template_id: int = None,
                            template_category: str = None,
                            context: Dict = None,
                            attachments: List[str] = None) -> Dict[str, Any]:
        """
        Sendet E-Mail basierend auf Vorlage
        
        Args:
            to: Empfänger
            template_id: ID der EmailTemplate
            template_category: Oder Kategorie für Standard-Vorlage
            context: Dict mit Platzhalter-Werten
            attachments: Optional Anhänge
        """
        try:
            from src.models.document import EmailTemplate
            
            # Hole Vorlage
            if template_id:
                template = EmailTemplate.query.get(template_id)
            elif template_category:
                template = EmailTemplate.query.filter_by(
                    category=template_category,
                    is_active=True
                ).first()
            else:
                return {'success': False, 'error': 'Keine Vorlage angegeben'}
            
            if not template:
                return {'success': False, 'error': 'Vorlage nicht gefunden'}
            
            # Platzhalter ersetzen
            subject = self._replace_placeholders(template.subject, context or {})
            body = self._replace_placeholders(template.body_text, context or {})
            html_body = None
            if template.body_html:
                html_body = self._replace_placeholders(template.body_html, context or {})
            
            return self.send_email(
                to=to,
                subject=subject,
                body=body,
                html_body=html_body,
                attachments=attachments
            )
            
        except Exception as e:
            logger.error(f"Template email error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _replace_placeholders(self, text: str, context: Dict) -> str:
        """
        Ersetzt Platzhalter in Text
        
        Unterstützte Formate:
        - {{variable}}
        - {variable}
        - $variable
        """
        if not text:
            return ''
        
        result = text
        
        for key, value in context.items():
            # Verschiedene Formate
            result = result.replace(f'{{{{{key}}}}}', str(value or ''))
            result = result.replace(f'{{{key}}}', str(value or ''))
            result = result.replace(f'${key}', str(value or ''))
        
        return result
    
    # ==========================================
    # SPEZIFISCHE E-MAIL-TYPEN
    # ==========================================
    
    def send_order_confirmation(self, order) -> Dict[str, Any]:
        """Sendet Auftragsbestätigung"""
        if not order.customer or not order.customer.email:
            return {'success': False, 'error': 'Keine Kunden-E-Mail'}
        
        context = self._build_order_context(order)
        
        return self.send_template_email(
            to=order.customer.email,
            template_category='AUFTRAGSBESTAETIGUNG',
            context=context
        )
    
    def send_design_approval_request(self, 
                                      to: str,
                                      customer_name: str,
                                      order_number: str,
                                      approval_url: str) -> Dict[str, Any]:
        """Sendet Design-Freigabe-Anfrage"""
        
        context = {
            'customer_name': customer_name,
            'order_number': order_number,
            'approval_url': approval_url
        }
        
        # Versuche Vorlage, sonst Fallback
        result = self.send_template_email(
            to=to,
            template_category='GRAFIK_FREIGABE',
            context=context
        )
        
        if not result.get('success'):
            # Fallback mit Standard-Text
            subject = f"Design-Freigabe für Auftrag {order_number}"
            body = f"""
Guten Tag {customer_name},

Ihr Design für Auftrag {order_number} ist fertig zur Freigabe.

Bitte prüfen Sie das Design unter folgendem Link:
{approval_url}

Mit freundlichen Grüßen
Ihr StitchAdmin-Team
            """
            
            result = self.send_email(to=to, subject=subject, body=body)
        
        return result
    
    def send_shipping_notification(self,
                                    to: str,
                                    customer_name: str,
                                    order_number: str,
                                    carrier: str,
                                    tracking_number: str) -> Dict[str, Any]:
        """Sendet Versandbenachrichtigung"""
        
        # Tracking-URL generieren
        tracking_url = self._get_tracking_url(carrier, tracking_number)
        
        context = {
            'customer_name': customer_name,
            'order_number': order_number,
            'carrier': carrier,
            'tracking_number': tracking_number,
            'tracking_url': tracking_url
        }
        
        result = self.send_template_email(
            to=to,
            template_category='VERSAND_INFO',
            context=context
        )
        
        if not result.get('success'):
            subject = f"Ihre Sendung {order_number} wurde versendet"
            body = f"""
Guten Tag {customer_name},

Ihre Bestellung {order_number} wurde versendet.

Versanddienstleister: {carrier}
Sendungsnummer: {tracking_number}

Verfolgen Sie Ihre Sendung: {tracking_url}

Mit freundlichen Grüßen
Ihr StitchAdmin-Team
            """
            result = self.send_email(to=to, subject=subject, body=body)
        
        return result
    
    def send_pickup_ready_notification(self,
                                        to: str,
                                        customer_name: str,
                                        order_number: str) -> Dict[str, Any]:
        """Sendet Abholbereit-Benachrichtigung"""
        
        from src.models import CompanySettings
        settings = CompanySettings.get_settings()
        
        context = {
            'customer_name': customer_name,
            'order_number': order_number,
            'company_name': settings.company_name,
            'company_address': f"{settings.street}, {settings.postal_code} {settings.city}",
            'company_phone': settings.phone
        }
        
        subject = f"Ihre Bestellung {order_number} ist abholbereit"
        body = f"""
Guten Tag {customer_name},

Ihre Bestellung {order_number} ist fertig und kann abgeholt werden.

Abholadresse:
{settings.company_name}
{settings.street}
{settings.postal_code} {settings.city}

Bei Fragen erreichen Sie uns unter: {settings.phone}

Mit freundlichen Grüßen
{settings.company_name}
        """
        
        return self.send_email(to=to, subject=subject, body=body)
    
    def send_invoice(self,
                     to: str,
                     customer_name: str,
                     invoice_number: str,
                     invoice_pdf_path: str,
                     total_amount: float) -> Dict[str, Any]:
        """Sendet Rechnung per E-Mail"""
        
        context = {
            'customer_name': customer_name,
            'invoice_number': invoice_number,
            'total_amount': f"{total_amount:.2f}",
            'currency': '€'
        }
        
        result = self.send_template_email(
            to=to,
            template_category='RECHNUNG',
            context=context,
            attachments=[invoice_pdf_path] if invoice_pdf_path else None
        )
        
        if not result.get('success'):
            subject = f"Rechnung {invoice_number}"
            body = f"""
Guten Tag {customer_name},

anbei erhalten Sie Ihre Rechnung {invoice_number} über {total_amount:.2f} €.

Bei Fragen stehen wir Ihnen gerne zur Verfügung.

Mit freundlichen Grüßen
Ihr StitchAdmin-Team
            """
            result = self.send_email(
                to=to, 
                subject=subject, 
                body=body,
                attachments=[invoice_pdf_path] if invoice_pdf_path else None
            )
        
        return result
    
    def send_payment_reminder(self,
                               to: str,
                               customer_name: str,
                               invoice_number: str,
                               due_date: str,
                               amount: float,
                               reminder_level: int = 1) -> Dict[str, Any]:
        """Sendet Zahlungserinnerung/Mahnung"""
        
        context = {
            'customer_name': customer_name,
            'invoice_number': invoice_number,
            'due_date': due_date,
            'amount': f"{amount:.2f}",
            'reminder_level': reminder_level
        }
        
        if reminder_level == 1:
            subject = f"Zahlungserinnerung - Rechnung {invoice_number}"
            urgency = "freundlich"
        elif reminder_level == 2:
            subject = f"2. Mahnung - Rechnung {invoice_number}"
            urgency = "dringend"
        else:
            subject = f"Letzte Mahnung - Rechnung {invoice_number}"
            urgency = "sehr dringend"
        
        body = f"""
Guten Tag {customer_name},

wir möchten Sie {urgency} an die offene Rechnung {invoice_number} erinnern.

Rechnungsbetrag: {amount:.2f} €
Fällig seit: {due_date}

Bitte überweisen Sie den Betrag umgehend.

Falls Sie die Zahlung bereits veranlasst haben, betrachten Sie dieses Schreiben als gegenstandslos.

Mit freundlichen Grüßen
Ihr StitchAdmin-Team
        """
        
        return self.send_email(to=to, subject=subject, body=body)
    
    # ==========================================
    # HILFSFUNKTIONEN
    # ==========================================
    
    def _build_order_context(self, order) -> Dict:
        """Baut Kontext-Dict für Auftrags-E-Mails"""
        from src.models import CompanySettings
        settings = CompanySettings.get_settings()
        
        items_text = ""
        if order.items:
            for item in order.items:
                items_text += f"- {item.quantity}x {item.article.name if item.article else 'Artikel'}\n"
        
        return {
            'order_number': order.order_number,
            'order_id': order.id,
            'customer_name': order.customer.display_name if order.customer else '',
            'customer_email': order.customer.email if order.customer else '',
            'order_date': order.created_at.strftime('%d.%m.%Y') if order.created_at else '',
            'due_date': order.due_date.strftime('%d.%m.%Y') if order.due_date else '',
            'total_amount': f"{order.calculate_total():.2f}" if hasattr(order, 'calculate_total') else '0.00',
            'items': items_text,
            'notes': order.customer_notes or '',
            'company_name': settings.company_name,
            'company_email': settings.company_email,
            'company_phone': settings.phone
        }
    
    def _get_tracking_url(self, carrier: str, tracking_number: str) -> str:
        """Generiert Tracking-URL für Carrier"""
        carrier_urls = {
            'DHL': f'https://www.dhl.de/de/privatkunden/pakete-empfangen/verfolgen.html?piececode={tracking_number}',
            'DPD': f'https://tracking.dpd.de/status/de_DE/parcel/{tracking_number}',
            'UPS': f'https://www.ups.com/track?tracknum={tracking_number}&loc=de_DE',
            'GLS': f'https://gls-group.eu/DE/de/paketverfolgung?match={tracking_number}',
            'Hermes': f'https://www.myhermes.de/empfangen/sendungsverfolgung/sendungsinformation/{tracking_number}',
            'Deutsche Post': f'https://www.deutschepost.de/de/s/sendungsverfolgung.html?piececode={tracking_number}'
        }
        
        return carrier_urls.get(carrier, f'https://www.google.com/search?q={carrier}+tracking+{tracking_number}')
    
    def test_connection(self) -> Dict[str, Any]:
        """Testet SMTP-Verbindung"""
        try:
            if self.account:
                smtp_server = self.account.smtp_server
                smtp_port = self.account.smtp_port
                smtp_user = self.account.smtp_username or self.account.email_address
                smtp_pass = self.account.get_smtp_password()
                use_tls = self.account.smtp_use_tls
            else:
                smtp_server = self.smtp_config.get('server')
                smtp_port = self.smtp_config.get('port', 587)
                smtp_user = self.smtp_config.get('username')
                smtp_pass = self.smtp_config.get('password')
                use_tls = self.smtp_config.get('use_tls', True)
            
            if use_tls:
                smtp = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
                smtp.starttls()
            else:
                smtp = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)
            
            if smtp_user and smtp_pass:
                smtp.login(smtp_user, smtp_pass)
            
            smtp.quit()
            
            return {'success': True, 'message': 'Verbindung erfolgreich'}
            
        except smtplib.SMTPAuthenticationError:
            return {'success': False, 'error': 'Authentifizierung fehlgeschlagen'}
        except smtplib.SMTPConnectError:
            return {'success': False, 'error': 'Verbindung fehlgeschlagen'}
        except Exception as e:
            return {'success': False, 'error': str(e)}


# Singleton für einfachen Zugriff
_email_service = None

def get_email_service() -> EmailService:
    """Gibt globale EmailService-Instanz zurück"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
