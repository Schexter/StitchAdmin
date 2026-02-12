# -*- coding: utf-8 -*-
"""
DESIGN-FREIGABE SERVICE (On-Premise Version)
=============================================
PDF-basierter Workflow für lokale Installationen

Workflow:
1. PDF mit Design-Vorschau erstellen
2. PDF per E-Mail an Kunden senden
3. Kunde unterschreibt (digital oder analog)
4. Signierte PDF zurück per E-Mail oder Upload
5. System archiviert und verknüpft

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
import io
import uuid
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, List

from flask import current_app, url_for

from src.models import db
from src.models.models import Order, Customer, CompanySettings

logger = logging.getLogger(__name__)


class DesignApprovalService:
    """
    Service für den PDF-basierten Design-Freigabe-Workflow (On-Premise)
    """
    
    def __init__(self):
        self.pdf_dir = None
        self.signed_pdf_dir = None
    
    def _init_dirs(self):
        """Initialisiert die Verzeichnisse"""
        if not self.pdf_dir:
            # Versuche instance_path, sonst Fallback
            try:
                base = current_app.instance_path
            except RuntimeError:
                base = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance')
            
            self.pdf_dir = os.path.join(base, 'design_approvals', 'sent')
            self.signed_pdf_dir = os.path.join(base, 'design_approvals', 'signed')
            
            os.makedirs(self.pdf_dir, exist_ok=True)
            os.makedirs(self.signed_pdf_dir, exist_ok=True)
    
    # ============================================
    # PDF ERSTELLEN
    # ============================================
    
    def generate_approval_pdf(
        self, 
        order: Order,
        design=None
    ) -> Tuple[str, str]:
        """
        Generiert die Freigabe-PDF für einen Auftrag
        
        Args:
            order: Der Auftrag
            design: Optionales OrderDesign (bei Multi-Position)
            
        Returns:
            Tuple (file_path, file_hash)
        """
        self._init_dirs()
        
        from src.services.design_approval_pdf import (
            create_design_approval_pdf,
            get_design_image_path
        )
        
        company = CompanySettings.get_settings()
        
        # Design-Bild finden
        try:
            app_root = current_app.root_path
        except RuntimeError:
            app_root = os.path.dirname(os.path.dirname(__file__))
        
        design_image = get_design_image_path(order, design, app_root)
        
        # Dateiname mit Timestamp für Eindeutigkeit
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"freigabe_{order.order_number}_{timestamp}.pdf"
        filepath = os.path.join(self.pdf_dir, filename)
        
        # PDF generieren
        create_design_approval_pdf(
            order=order,
            design=design,
            company_settings=company,
            design_image_path=design_image,
            output_path=filepath
        )
        
        # Hash berechnen für Integritätsprüfung
        with open(filepath, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        logger.info(f"Approval PDF generated: {filepath}")
        
        return filepath, file_hash
    
    # ============================================
    # E-MAIL MIT PDF-ANHANG SENDEN
    # ============================================
    
    def send_approval_email(
        self, 
        order: Order,
        pdf_path: str,
        custom_message: str = None
    ) -> dict:
        """
        Sendet die Freigabe-E-Mail mit PDF als Anhang
        
        Args:
            order: Der Auftrag
            pdf_path: Pfad zur Freigabe-PDF
            custom_message: Optionale zusätzliche Nachricht
            
        Returns:
            Dict mit Ergebnis
        """
        customer = order.customer
        
        if not customer or not customer.email:
            return {'success': False, 'error': 'Keine Kunden-E-Mail vorhanden'}
        
        if not os.path.exists(pdf_path):
            return {'success': False, 'error': 'PDF nicht gefunden'}
        
        company = CompanySettings.get_settings()
        
        # E-Mail-Content
        subject = f"Design-Freigabe für Auftrag {order.order_number} - {company.company_name}"
        
        custom_section = ""
        if custom_message:
            custom_section = f"""
            <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
                <strong>Hinweis:</strong><br>
                {custom_message}
            </div>
            """
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color: white; padding: 25px; text-align: center; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0; font-size: 24px;">🎨 Design-Freigabe</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">Auftrag {order.order_number}</p>
            </div>
            
            <div style="padding: 30px; background: #f8f9fa; border-radius: 0 0 8px 8px;">
                <p>Guten Tag {customer.display_name},</p>
                
                <p>Ihr Design für <strong>Auftrag {order.order_number}</strong> ist fertig 
                und wartet auf Ihre Freigabe.</p>
                
                {custom_section}
                
                <div style="background: white; padding: 20px; border-radius: 8px; margin: 25px 0; border: 1px solid #e0e0e0;">
                    <h3 style="margin-top: 0; color: #2563eb;">📎 So funktioniert die Freigabe:</h3>
                    
                    <ol style="padding-left: 20px;">
                        <li style="margin-bottom: 10px;">
                            <strong>PDF öffnen</strong><br>
                            <span style="color: #666;">Die Freigabe-PDF ist dieser E-Mail angehängt</span>
                        </li>
                        <li style="margin-bottom: 10px;">
                            <strong>Design prüfen</strong><br>
                            <span style="color: #666;">Kontrollieren Sie Position, Größe und Farben</span>
                        </li>
                        <li style="margin-bottom: 10px;">
                            <strong>Unterschreiben</strong><br>
                            <span style="color: #666;">Ausdrucken & unterschreiben ODER digital signieren</span>
                        </li>
                        <li style="margin-bottom: 10px;">
                            <strong>Zurücksenden</strong><br>
                            <span style="color: #666;">Signierte PDF per Antwort-Mail an uns senden</span>
                        </li>
                    </ol>
                </div>
                
                <div style="background: #e8f5e9; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <strong>💡 Tipp:</strong> Sie können die PDF auch digital unterschreiben 
                    (z.B. mit Adobe Acrobat, Apple Preview oder einem kostenlosen Tool wie 
                    <a href="https://smallpdf.com/de/pdf-unterschreiben" style="color: #2563eb;">SmallPDF</a>).
                </div>
                
                <p style="color: #666; font-size: 14px;">
                    <strong>Änderungen gewünscht?</strong><br>
                    Antworten Sie einfach auf diese E-Mail mit Ihren Änderungswünschen. 
                    Wir passen das Design entsprechend an.
                </p>
                
                <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 25px 0;">
                
                <p>Mit freundlichen Grüßen<br>
                <strong>{company.company_name}</strong></p>
                
                <p style="font-size: 12px; color: #888; margin-top: 20px;">
                    {company.street} {company.house_number or ''}<br>
                    {company.postal_code} {company.city}<br>
                    {f'Tel: {company.phone}' if company.phone else ''}<br>
                    {company.email or ''}
                </p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
Guten Tag {customer.display_name},

Ihr Design für Auftrag {order.order_number} ist fertig und wartet auf Ihre Freigabe.

{'Hinweis: ' + custom_message if custom_message else ''}

=== SO FUNKTIONIERT DIE FREIGABE ===

1. PDF öffnen
   Die Freigabe-PDF ist dieser E-Mail angehängt

2. Design prüfen
   Kontrollieren Sie Position, Größe und Farben

3. Unterschreiben
   Ausdrucken & unterschreiben ODER digital signieren

4. Zurücksenden
   Signierte PDF per Antwort-Mail an uns senden

---

Änderungen gewünscht?
Antworten Sie einfach auf diese E-Mail mit Ihren Änderungswünschen.

Mit freundlichen Grüßen
{company.company_name}

{company.street} {company.house_number or ''}
{company.postal_code} {company.city}
{f'Tel: {company.phone}' if company.phone else ''}
{company.email or ''}
        """
        
        # E-Mail senden mit Anhang
        try:
            from src.services.email_service import EmailService
            email_service = EmailService()
            
            # Anhang vorbereiten
            attachments = [{
                'path': pdf_path,
                'filename': f'Design-Freigabe_{order.order_number}.pdf',
                'content_type': 'application/pdf'
            }]
            
            result = email_service.send_email(
                to=customer.email,
                subject=subject,
                body=text_body,
                html_body=html_body,
                attachments=attachments
            )
            
            if result.get('success'):
                # Auftrag aktualisieren
                order.design_approval_status = 'sent'
                order.design_approval_sent_at = datetime.utcnow()
                order.workflow_status = 'design_pending'
                db.session.commit()
                
                logger.info(f"Approval email sent to {customer.email} for order {order.id}")
                
                return {
                    'success': True,
                    'message': f'E-Mail mit PDF gesendet an {customer.email}',
                    'pdf_path': pdf_path
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'E-Mail konnte nicht gesendet werden')
                }
                
        except Exception as e:
            logger.error(f"Error sending approval email: {e}")
            return {'success': False, 'error': str(e)}
    
    # ============================================
    # SIGNIERTE PDF HOCHLADEN/VERARBEITEN
    # ============================================
    
    def process_signed_pdf(
        self,
        order: Order,
        pdf_data: bytes,
        filename: str = None,
        source: str = 'upload',
        signer_info: dict = None
    ) -> dict:
        """
        Verarbeitet eine zurückerhaltene signierte PDF
        
        Args:
            order: Der Auftrag
            pdf_data: PDF-Daten als Bytes
            filename: Original-Dateiname
            source: 'upload' oder 'email'
            signer_info: Dict mit Name, Email des Unterzeichners
            
        Returns:
            Dict mit Ergebnis
        """
        self._init_dirs()
        
        try:
            # Dateiname erstellen
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = f"signed_{order.order_number}_{timestamp}.pdf"
            signed_path = os.path.join(self.signed_pdf_dir, safe_filename)
            
            # PDF speichern
            with open(signed_path, 'wb') as f:
                f.write(pdf_data)
            
            # Hash berechnen
            pdf_hash = hashlib.sha256(pdf_data).hexdigest()
            
            # Prüfen ob PDF signiert ist
            is_signed, signature_info = self._check_pdf_signature(pdf_data)
            
            # Auftrag aktualisieren
            order.design_approval_status = 'approved'
            order.design_approval_date = datetime.utcnow()
            order.workflow_status = 'design_approved'
            
            # Zusätzliche Infos speichern
            if signer_info:
                order.design_approval_notes = f"Freigegeben von: {signer_info.get('name', 'Kunde')}\n" \
                                              f"Quelle: {source}\n" \
                                              f"Datei: {filename or safe_filename}"
            
            db.session.commit()
            
            # Team benachrichtigen
            self._notify_team_approval(order, source, is_signed)
            
            logger.info(f"Signed PDF processed for order {order.id}: {signed_path}")
            
            return {
                'success': True,
                'message': 'Design-Freigabe erfolgreich verarbeitet',
                'saved_path': signed_path,
                'is_digitally_signed': is_signed,
                'signature_info': signature_info
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing signed PDF: {e}")
            return {'success': False, 'error': str(e)}
    
    def _check_pdf_signature(self, pdf_data: bytes) -> Tuple[bool, dict]:
        """
        Prüft ob PDF digital signiert ist
        
        Returns:
            Tuple (is_signed, signature_info)
        """
        try:
            import pypdf
            
            reader = pypdf.PdfReader(io.BytesIO(pdf_data))
            
            # Prüfe auf Signatur-Felder
            if hasattr(reader, 'trailer') and '/Root' in reader.trailer:
                root = reader.trailer['/Root']
                if hasattr(root, 'get_object'):
                    root_obj = root.get_object()
                    if '/AcroForm' in root_obj:
                        acroform = root_obj['/AcroForm']
                        if hasattr(acroform, 'get_object'):
                            acroform_obj = acroform.get_object()
                            if '/SigFlags' in acroform_obj:
                                return True, {'type': 'digital_signature'}
            
            # Prüfe Annotationen auf Signatur
            for page in reader.pages:
                if '/Annots' in page:
                    annots = page['/Annots']
                    if annots:
                        for annot in annots:
                            if hasattr(annot, 'get_object'):
                                annot_obj = annot.get_object()
                                if annot_obj.get('/FT') == '/Sig':
                                    sig_dict = annot_obj.get('/V')
                                    if sig_dict:
                                        return True, {
                                            'type': 'digital_signature',
                                            'name': str(sig_dict.get('/Name', 'Unknown')),
                                        }
            
            return False, None
            
        except Exception as e:
            logger.debug(f"Could not check PDF signature: {e}")
            return False, None
    
    # ============================================
    # ÄNDERUNGSWUNSCH VERARBEITEN
    # ============================================
    
    def process_revision_request(
        self,
        order: Order,
        reason: str,
        requested_changes: str,
        customer_name: str = None
    ) -> dict:
        """
        Verarbeitet einen Änderungswunsch
        """
        try:
            order.design_approval_status = 'revision_requested'
            order.design_approval_notes = f"Änderungswunsch von {customer_name or 'Kunde'}:\n" \
                                          f"Grund: {reason}\n" \
                                          f"Gewünschte Änderungen:\n{requested_changes}"
            order.workflow_status = 'design_pending'
            
            db.session.commit()
            
            # Team benachrichtigen
            self._notify_team_revision(order, reason, requested_changes)
            
            return {'success': True, 'message': 'Änderungswunsch gespeichert'}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    # ============================================
    # BENACHRICHTIGUNGEN
    # ============================================
    
    def _notify_team_approval(self, order: Order, source: str, is_signed: bool):
        """Benachrichtigt das Team über Freigabe"""
        try:
            from src.services.email_service import EmailService
            
            company = CompanySettings.get_settings()
            if not company.notification_email:
                return
            
            method = "Digital signierte PDF" if is_signed else "Unterschriebene PDF"
            source_text = "per E-Mail" if source == 'email' else "per Upload"
            
            EmailService().send_email(
                to=company.notification_email,
                subject=f"✅ Design freigegeben: {order.order_number}",
                body=f"""
Design-Freigabe erfolgt!

Auftrag: {order.order_number}
Kunde: {order.customer.display_name if order.customer else 'Unbekannt'}
Methode: {method} ({source_text})
Zeitpunkt: {datetime.now().strftime('%d.%m.%Y %H:%M')}

Der Auftrag kann jetzt in die Produktion gehen.
                """
            )
        except Exception as e:
            logger.warning(f"Team notification failed: {e}")
    
    def _notify_team_revision(self, order: Order, reason: str, changes: str):
        """Benachrichtigt das Team über Änderungswunsch"""
        try:
            from src.services.email_service import EmailService
            
            company = CompanySettings.get_settings()
            if not company.notification_email:
                return
            
            EmailService().send_email(
                to=company.notification_email,
                subject=f"⚠️ Design-Änderung angefordert: {order.order_number}",
                body=f"""
Design-Änderung angefordert!

Auftrag: {order.order_number}
Kunde: {order.customer.display_name if order.customer else 'Unbekannt'}
Zeitpunkt: {datetime.now().strftime('%d.%m.%Y %H:%M')}

Grund:
{reason}

Gewünschte Änderungen:
{changes}

Bitte das Design anpassen und erneut zur Freigabe senden.
                """
            )
        except Exception as e:
            logger.warning(f"Team notification failed: {e}")
    
    # ============================================
    # HILFSFUNKTIONEN
    # ============================================
    
    def get_pending_orders(self) -> List[Order]:
        """Holt alle Aufträge mit ausstehender Design-Freigabe"""
        return Order.query.filter(
            Order.design_approval_status.in_(['pending', 'sent', None]),
            (Order.design_file.isnot(None)) | (Order.design_file_path.isnot(None))
        ).order_by(Order.created_at.desc()).all()
    
    def get_revision_orders(self) -> List[Order]:
        """Holt alle Aufträge mit Änderungswunsch"""
        return Order.query.filter(
            Order.design_approval_status == 'revision_requested'
        ).order_by(Order.created_at.desc()).all()
    
    def get_recently_approved(self, days: int = 30) -> List[Order]:
        """Holt kürzlich freigegebene Aufträge"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        return Order.query.filter(
            Order.design_approval_status == 'approved',
            Order.design_approval_date >= cutoff
        ).order_by(Order.design_approval_date.desc()).all()


# Singleton-Instanz
_service_instance = None

def get_design_approval_service() -> DesignApprovalService:
    """Gibt die Service-Instanz zurück"""
    global _service_instance
    if _service_instance is None:
        _service_instance = DesignApprovalService()
    return _service_instance
