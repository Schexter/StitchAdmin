# -*- coding: utf-8 -*-
"""
E-Mail Integration Service - IMAP/SMTP
StitchAdmin 2.0
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import imaplib
import smtplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from datetime import datetime
import re
from src.models.document import EmailAccount, ArchivedEmail, EmailAttachment, Document
from src.models.models import db, Customer, Order
import logging

logger = logging.getLogger(__name__)


class EmailIntegrationService:
    """
    Service für E-Mail-Integration (IMAP/SMTP)
    """
    
    def __init__(self, email_account_id):
        """
        Initialisiert Service mit E-Mail-Account
        
        Args:
            email_account_id: ID des EmailAccount-Eintrags
        """
        self.account = EmailAccount.query.get_or_404(email_account_id)
        self.imap = None
        self.smtp = None
    
    def connect_imap(self):
        """Verbindet mit IMAP-Server"""
        try:
            if self.account.imap_use_ssl:
                self.imap = imaplib.IMAP4_SSL(self.account.imap_server, self.account.imap_port)
            else:
                self.imap = imaplib.IMAP4(self.account.imap_server, self.account.imap_port)
            
            # Login
            password = self.account.get_imap_password()
            self.imap.login(self.account.imap_username or self.account.email_address, password)
            
            logger.info(f"IMAP connected: {self.account.email_address}")
            return True
            
        except Exception as e:
            logger.error(f"IMAP connection failed: {e}")
            self.account.last_error = str(e)
            db.session.commit()
            return False
    
    def disconnect_imap(self):
        """Trennt IMAP-Verbindung"""
        if self.imap:
            try:
                self.imap.logout()
            except:
                pass
    
    def fetch_emails(self, folder='INBOX', limit=50, unread_only=False):
        """
        Holt E-Mails vom Server
        
        Args:
            folder: IMAP-Ordner (default: INBOX)
            limit: Maximale Anzahl (default: 50)
            unread_only: Nur ungelesene E-Mails (default: False)
        
        Returns:
            Liste von E-Mail-Dictionaries
        """
        if not self.connect_imap():
            return []
        
        try:
            # Ordner auswählen
            self.imap.select(folder)
            
            # Suche
            if unread_only:
                status, messages = self.imap.search(None, 'UNSEEN')
            else:
                status, messages = self.imap.search(None, 'ALL')
            
            email_ids = messages[0].split()
            emails = []
            
            # Limitiere auf letzte N E-Mails
            for email_id in email_ids[-limit:]:
                try:
                    email_data = self.fetch_email_by_id(email_id)
                    if email_data:
                        emails.append(email_data)
                except Exception as e:
                    logger.error(f"Error fetching email {email_id}: {e}")
                    continue
            
            # Update last_check
            self.account.last_check = datetime.utcnow()
            self.account.last_error = None
            db.session.commit()
            
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            self.account.last_error = str(e)
            db.session.commit()
            return []
        
        finally:
            self.disconnect_imap()
    
    def fetch_email_by_id(self, email_id):
        """
        Holt einzelne E-Mail anhand ID
        
        Args:
            email_id: IMAP E-Mail ID
        
        Returns:
            Dictionary mit E-Mail-Daten
        """
        status, msg_data = self.imap.fetch(email_id, '(RFC822)')
        
        if status != 'OK':
            return None
        
        msg = email.message_from_bytes(msg_data[0][1])
        
        # Decode Header
        subject = self._decode_header(msg.get('Subject', ''))
        from_addr = self._decode_header(msg.get('From', ''))
        to_addr = self._decode_header(msg.get('To', ''))
        cc_addr = self._decode_header(msg.get('Cc', ''))
        date_str = msg.get('Date', '')
        message_id = msg.get('Message-ID', '')
        
        # Parse Date
        try:
            received_date = email.utils.parsedate_to_datetime(date_str)
        except:
            received_date = datetime.utcnow()
        
        # Body extrahieren
        body_text, body_html = self._extract_body(msg)
        
        # Attachments
        attachments = self._extract_attachments(msg)
        
        return {
            'email_id': email_id.decode() if isinstance(email_id, bytes) else email_id,
            'message_id': message_id,
            'subject': subject,
            'from': from_addr,
            'to': to_addr,
            'cc': cc_addr,
            'date': received_date,
            'body_text': body_text,
            'body_html': body_html,
            'attachments': attachments,
            'size': len(msg_data[0][1])
        }
    
    def _decode_header(self, header_value):
        """Decodiert E-Mail Header"""
        if not header_value:
            return ''
        
        decoded_parts = decode_header(header_value)
        decoded_string = ''
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    if encoding:
                        decoded_string += part.decode(encoding)
                    else:
                        decoded_string += part.decode('utf-8', errors='ignore')
                except:
                    decoded_string += part.decode('utf-8', errors='ignore')
            else:
                decoded_string += str(part)
        
        return decoded_string
    
    def _extract_body(self, msg):
        """Extrahiert Text und HTML Body"""
        body_text = ''
        body_html = ''
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                
                try:
                    if content_type == 'text/plain':
                        body_text = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    elif content_type == 'text/html':
                        body_html = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    pass
        else:
            content_type = msg.get_content_type()
            try:
                if content_type == 'text/plain':
                    body_text = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                elif content_type == 'text/html':
                    body_html = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                pass
        
        return body_text, body_html
    
    def _extract_attachments(self, msg):
        """Extrahiert Anhänge aus E-Mail"""
        attachments = []
        
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_disposition() == 'attachment':
                    filename = part.get_filename()
                    if filename:
                        filename = self._decode_header(filename)
                        attachments.append({
                            'filename': filename,
                            'content_type': part.get_content_type(),
                            'size': len(part.get_payload(decode=True)),
                            'data': part.get_payload(decode=True)
                        })
        
        return attachments
    
    def archive_email(self, email_data, customer_id=None, order_id=None, archived_by_user_id=None):
        """
        Archiviert E-Mail in Datenbank
        
        Args:
            email_data: Dictionary von fetch_email_by_id()
            customer_id: Optional - Kunde zuordnen
            order_id: Optional - Auftrag zuordnen
            archived_by_user_id: User der archiviert
        
        Returns:
            ArchivedEmail Objekt
        """
        # Prüfe ob bereits archiviert
        existing = ArchivedEmail.query.filter_by(
            email_account_id=self.account.id,
            message_id=email_data['message_id']
        ).first()
        
        if existing:
            logger.info(f"Email bereits archiviert: {email_data['message_id']}")
            return existing
        
        # Auto-Klassifizierung
        category = self._classify_email(email_data)
        
        # Auto-Kunde erkennen (wenn nicht angegeben)
        if not customer_id:
            customer_id = self._detect_customer(email_data)
        
        # Auto-Auftrag erkennen (wenn nicht angegeben)
        if not order_id:
            order_id = self._detect_order(email_data)
        
        # Erstelle ArchivedEmail
        archived = ArchivedEmail(
            email_account_id=self.account.id,
            message_id=email_data['message_id'],
            subject=email_data['subject'][:500],  # Limit
            from_address=email_data['from'][:255],
            to_address=email_data['to'][:500] if email_data['to'] else None,
            cc_address=email_data['cc'][:500] if email_data['cc'] else None,
            body_text=email_data['body_text'],
            body_html=email_data['body_html'],
            received_date=email_data['date'],
            size=email_data['size'],
            has_attachments=len(email_data['attachments']) > 0,
            attachment_count=len(email_data['attachments']),
            customer_id=customer_id,
            order_id=order_id,
            category=category,
            archived_by=archived_by_user_id
        )
        
        db.session.add(archived)
        db.session.flush()  # Um ID zu bekommen
        
        # E-Mail als PDF speichern (optional)
        if self.account.auto_archive:
            document = self._save_email_as_pdf(archived, email_data)
            if document:
                archived.document_id = document.id
        
        # Anhänge speichern
        self._save_attachments(archived, email_data['attachments'])
        
        db.session.commit()
        
        logger.info(f"Email archiviert: {archived.id}")
        return archived
    
    def _classify_email(self, email_data):
        """Klassifiziert E-Mail automatisch"""
        subject = email_data['subject'].lower()
        body = (email_data['body_text'] or '').lower()
        text = f"{subject} {body}"
        
        # Keyword-Matching
        keywords = {
            'rechnung': ['rechnung', 'invoice', 'faktura', 're:'],
            'angebot': ['angebot', 'quote', 'quotation', 'offer', 'ang:'],
            'bestellung': ['bestellung', 'order', 'bestell'],
            'mahnung': ['mahnung', 'reminder', 'zahlungserinnerung'],
            'anfrage': ['anfrage', 'inquiry', 'request', 'frage']
        }
        
        for category, terms in keywords.items():
            if any(term in text for term in terms):
                return category
        
        return 'sonstiges'
    
    def _detect_customer(self, email_data):
        """Versucht Kunde zu erkennen"""
        from_email = email_data['from'].lower()
        
        # Extrahiere E-Mail-Adresse
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_email)
        if email_match:
            email_addr = email_match.group(0)
            
            # Suche Kunde mit dieser E-Mail
            customer = Customer.query.filter(
                Customer.email.ilike(f'%{email_addr}%')
            ).first()
            
            if customer:
                return customer.id
        
        return None
    
    def _detect_order(self, email_data):
        """Versucht Auftrag zu erkennen"""
        subject = email_data['subject']
        body = email_data['body_text'] or ''
        text = f"{subject} {body}"
        
        # Suche Auftragsnummer (z.B. AUF-2025-000123)
        order_pattern = r'AUF-\d{4}-\d{6}'
        matches = re.findall(order_pattern, text)
        
        if matches:
            order_number = matches[0]
            order = Order.query.filter_by(order_number=order_number).first()
            if order:
                return order.id
        
        return None
    
    def _save_email_as_pdf(self, archived_email, email_data):
        """
        Speichert E-Mail als PDF-Dokument
        (Vereinfachte Version - für Produktion HTML→PDF Bibliothek nutzen)
        """
        # TODO: Implementiere HTML→PDF Konvertierung
        # z.B. mit pdfkit oder weasyprint
        return None
    
    def _save_attachments(self, archived_email, attachments):
        """Speichert E-Mail-Anhänge"""
        upload_folder = 'uploads/email_attachments'
        os.makedirs(upload_folder, exist_ok=True)
        
        for att in attachments:
            try:
                # Generiere sicheren Dateinamen
                safe_filename = self._make_safe_filename(att['filename'])
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{archived_email.id}_{timestamp}_{safe_filename}"
                filepath = os.path.join(upload_folder, filename)
                
                # Speichere Datei
                with open(filepath, 'wb') as f:
                    f.write(att['data'])
                
                # Erstelle EmailAttachment
                email_att = EmailAttachment(
                    archived_email_id=archived_email.id,
                    filename=att['filename'],
                    file_path=filepath,
                    file_size=att['size'],
                    mime_type=att['content_type']
                )
                
                db.session.add(email_att)
                
                # Optional: Als Document speichern
                if self._should_save_as_document(att):
                    doc = self._create_document_from_attachment(email_att, archived_email)
                    if doc:
                        email_att.document_id = doc.id
                
            except Exception as e:
                logger.error(f"Error saving attachment: {e}")
        
        db.session.commit()
    
    def _make_safe_filename(self, filename):
        """Macht Dateinamen sicher"""
        # Ersetze unsichere Zeichen
        safe = re.sub(r'[^\w\s.-]', '', filename)
        return safe[:100]  # Limit length
    
    def _should_save_as_document(self, attachment):
        """Prüft ob Anhang als Dokument gespeichert werden soll"""
        # PDF, Word, Excel etc. → Ja
        extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpg', '.jpeg']
        filename = attachment['filename'].lower()
        return any(filename.endswith(ext) for ext in extensions)
    
    def _create_document_from_attachment(self, email_attachment, archived_email):
        """Erstellt Document-Eintrag aus E-Mail-Anhang"""
        from src.models.document import Document
        
        doc = Document(
            title=f"E-Mail Anhang: {email_attachment.filename}",
            document_number=Document.generate_document_number(),
            category='email_attachment',
            filename=email_attachment.filename,
            original_filename=email_attachment.filename,
            file_path=email_attachment.file_path,
            file_size=email_attachment.file_size,
            mime_type=email_attachment.mime_type,
            file_hash=Document.calculate_file_hash(email_attachment.file_path),
            customer_id=archived_email.customer_id,
            order_id=archived_email.order_id,
            document_date=archived_email.received_date.date(),
            visibility='private'
        )
        
        db.session.add(doc)
        return doc
    
    def send_email(self, to_address, subject, body, attachments=None, html=False):
        """
        Sendet E-Mail via SMTP
        
        Args:
            to_address: Empfänger-Adresse
            subject: Betreff
            body: Nachricht
            attachments: Liste von Dateipfaden
            html: Ob body HTML ist
        
        Returns:
            True bei Erfolg
        """
        try:
            # SMTP Verbindung
            if self.account.smtp_use_tls:
                self.smtp = smtplib.SMTP(self.account.smtp_server, self.account.smtp_port)
                self.smtp.starttls()
            else:
                self.smtp = smtplib.SMTP_SSL(self.account.smtp_server, self.account.smtp_port)
            
            # Login
            password = self.account.get_smtp_password()
            self.smtp.login(self.account.smtp_username or self.account.email_address, password)
            
            # Erstelle Nachricht
            msg = MIMEMultipart()
            msg['From'] = self.account.email_address
            msg['To'] = to_address
            msg['Subject'] = subject
            
            # Body
            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Anhänge
            if attachments:
                for filepath in attachments:
                    self._attach_file(msg, filepath)
            
            # Senden
            self.smtp.send_message(msg)
            self.smtp.quit()
            
            logger.info(f"Email sent to {to_address}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def _attach_file(self, msg, filepath):
        """Fügt Datei als Anhang hinzu"""
        filename = os.path.basename(filepath)
        
        with open(filepath, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename= {filename}')
        msg.attach(part)
