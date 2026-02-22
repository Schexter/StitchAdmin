# -*- coding: utf-8 -*-
"""
IMAP Sync Service
=================
Liest E-Mails via IMAP und ordnet sie automatisch Kunden zu.
Nutzt bestehende EmailAccount + ArchivedEmail Models.

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from src.models import db
from src.models.document import EmailAccount, ArchivedEmail

logger = logging.getLogger(__name__)


class IMAPSyncService:
    """Service fuer IMAP E-Mail-Synchronisation"""

    def connect(self, account: EmailAccount):
        """IMAP-Verbindung herstellen"""
        try:
            if account.imap_use_ssl:
                conn = imaplib.IMAP4_SSL(account.imap_server, account.imap_port or 993)
            else:
                conn = imaplib.IMAP4(account.imap_server, account.imap_port or 143)

            # Passwort entschluesseln
            try:
                password = account.get_imap_password()
            except Exception:
                password = account.imap_password_encrypted  # Fallback: unverschluesselt

            conn.login(account.imap_username or account.email_address, password)
            return conn
        except Exception as e:
            logger.error(f"IMAP-Verbindung fehlgeschlagen fuer {account.email_address}: {e}")
            account.last_error = str(e)
            db.session.commit()
            return None

    def test_connection(self, account: EmailAccount) -> Dict:
        """IMAP-Verbindung testen"""
        conn = self.connect(account)
        if not conn:
            return {'success': False, 'message': account.last_error or 'Verbindung fehlgeschlagen'}

        try:
            status, folders = conn.list()
            folder_count = len(folders) if folders else 0
            conn.logout()
            return {'success': True, 'message': f'Verbunden - {folder_count} Ordner gefunden'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def fetch_new_emails(self, account_id: int, max_emails: int = 50) -> Dict:
        """
        Neue E-Mails abrufen und archivieren.

        Returns:
            Dict mit fetched, duplicates, errors
        """
        account = EmailAccount.query.get(account_id)
        if not account:
            return {'error': 'Konto nicht gefunden'}

        conn = self.connect(account)
        if not conn:
            return {'error': f'IMAP-Verbindung fehlgeschlagen: {account.last_error}'}

        try:
            conn.select(account.archive_folder or 'INBOX')

            # Nur neuere E-Mails suchen
            since = account.last_check or (datetime.utcnow() - timedelta(days=7))
            since_str = since.strftime('%d-%b-%Y')
            status, messages = conn.search(None, f'(SINCE "{since_str}")')

            if status != 'OK' or not messages[0]:
                conn.logout()
                account.last_check = datetime.utcnow()
                account.last_error = None
                db.session.commit()
                return {'fetched': 0, 'duplicates': 0, 'errors': 0}

            msg_ids = messages[0].split()[-max_emails:]  # Letzte N

            fetched = 0
            duplicates = 0
            errors = 0

            for msg_id in msg_ids:
                try:
                    status, data = conn.fetch(msg_id, '(RFC822)')
                    if status != 'OK':
                        errors += 1
                        continue

                    raw_email = data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    # Message-ID pruefen (Duplikat?)
                    message_id = msg.get('Message-ID', '')
                    if message_id:
                        existing = ArchivedEmail.query.filter_by(
                            email_account_id=account.id,
                            message_id=message_id
                        ).first()
                        if existing:
                            duplicates += 1
                            continue

                    # E-Mail parsen
                    parsed = self._parse_email(msg)

                    archived = ArchivedEmail(
                        email_account_id=account.id,
                        message_id=message_id,
                        subject=parsed['subject'][:500] if parsed['subject'] else '',
                        from_address=parsed['from'][:255] if parsed['from'] else '',
                        to_address=parsed['to'][:500] if parsed['to'] else '',
                        cc_address=parsed.get('cc', '')[:500] if parsed.get('cc') else None,
                        body_text=parsed['body_text'],
                        body_html=parsed['body_html'],
                        received_date=parsed['date'],
                        has_attachments=parsed['has_attachments'],
                        attachment_count=parsed['attachment_count'],
                        is_read=False,
                    )

                    # Auto-Kunden-Zuordnung
                    customer_id = self._auto_assign_customer(parsed['from'])
                    if customer_id:
                        archived.customer_id = customer_id

                    db.session.add(archived)
                    fetched += 1

                    if fetched % 20 == 0:
                        db.session.flush()

                except Exception as e:
                    logger.warning(f"Fehler beim Parsen von E-Mail {msg_id}: {e}")
                    errors += 1

            account.last_check = datetime.utcnow()
            account.last_error = None
            db.session.commit()
            conn.logout()

            return {'fetched': fetched, 'duplicates': duplicates, 'errors': errors}

        except Exception as e:
            logger.error(f"IMAP-Sync fehlgeschlagen: {e}")
            account.last_error = str(e)
            db.session.commit()
            try:
                conn.logout()
            except Exception:
                pass
            return {'error': str(e)}

    def auto_assign_customer(self, email_id: int) -> Optional[str]:
        """Ordnet eine archivierte E-Mail einem Kunden zu"""
        archived = ArchivedEmail.query.get(email_id)
        if not archived or not archived.from_address:
            return None

        customer_id = self._auto_assign_customer(archived.from_address)
        if customer_id:
            archived.customer_id = customer_id
            db.session.commit()
        return customer_id

    def _parse_email(self, msg) -> Dict:
        """Parst eine E-Mail-Nachricht"""
        subject = self._decode_header(msg.get('Subject', ''))
        from_addr = self._decode_header(msg.get('From', ''))
        to_addr = self._decode_header(msg.get('To', ''))
        cc_addr = self._decode_header(msg.get('Cc', ''))

        # Datum
        date_str = msg.get('Date')
        try:
            parsed_date = parsedate_to_datetime(date_str) if date_str else datetime.utcnow()
        except Exception:
            parsed_date = datetime.utcnow()

        # Body extrahieren
        body_text = ''
        body_html = ''
        attachment_count = 0

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get('Content-Disposition', ''))

                if 'attachment' in disposition:
                    attachment_count += 1
                    continue

                if content_type == 'text/plain':
                    try:
                        body_text = part.get_payload(decode=True).decode('utf-8', errors='replace')
                    except Exception:
                        pass
                elif content_type == 'text/html':
                    try:
                        body_html = part.get_payload(decode=True).decode('utf-8', errors='replace')
                    except Exception:
                        pass
        else:
            content_type = msg.get_content_type()
            try:
                payload = msg.get_payload(decode=True).decode('utf-8', errors='replace')
                if content_type == 'text/html':
                    body_html = payload
                else:
                    body_text = payload
            except Exception:
                pass

        return {
            'subject': subject,
            'from': from_addr,
            'to': to_addr,
            'cc': cc_addr,
            'date': parsed_date,
            'body_text': body_text,
            'body_html': body_html,
            'has_attachments': attachment_count > 0,
            'attachment_count': attachment_count,
        }

    def _decode_header(self, header_value: str) -> str:
        """Decodiert einen E-Mail-Header"""
        if not header_value:
            return ''
        parts = decode_header(header_value)
        decoded = []
        for part, charset in parts:
            if isinstance(part, bytes):
                decoded.append(part.decode(charset or 'utf-8', errors='replace'))
            else:
                decoded.append(part)
        return ' '.join(decoded)

    def _auto_assign_customer(self, from_address: str) -> Optional[str]:
        """Findet Kunden anhand der Absender-Adresse"""
        if not from_address:
            return None

        # E-Mail-Adresse extrahieren
        import re
        match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', from_address)
        if not match:
            return None

        email_addr = match.group().lower()

        from src.models.models import Customer
        customer = Customer.query.filter(
            db.func.lower(Customer.email) == email_addr
        ).first()

        return customer.id if customer else None
