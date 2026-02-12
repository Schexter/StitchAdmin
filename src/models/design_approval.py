# -*- coding: utf-8 -*-
"""
DESIGN-FREIGABE-HISTORIE MODEL
==============================
Vollständige Tracking-Historie für Design-Freigaben

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
from src.models import db


class DesignApprovalStatus(Enum):
    """Status einer Design-Freigabe"""
    DRAFT = 'draft'                    # Entwurf, noch nicht gesendet
    SENT = 'sent'                      # An Kunde gesendet
    VIEWED = 'viewed'                  # Kunde hat Link geöffnet
    APPROVED = 'approved'              # Freigegeben
    REVISION_REQUESTED = 'revision'    # Änderung angefordert
    EXPIRED = 'expired'                # Link abgelaufen
    CANCELLED = 'cancelled'            # Abgebrochen


class SignatureType(Enum):
    """Art der Signatur"""
    CANVAS = 'canvas'                  # Auf Webseite gezeichnet
    PDF_SIGNED = 'pdf_signed'          # Per E-Mail zurückgesendete signierte PDF
    CERTIFICATE = 'certificate'        # Mit digitalem Zertifikat signiert
    SCANNED = 'scanned'                # Eingescannte Unterschrift
    VERBAL = 'verbal'                  # Telefonische Freigabe (dokumentiert)


class DesignApprovalRequest(db.Model):
    """
    Freigabe-Anfrage für ein Design
    
    Eine Anfrage kann mehrere Designs enthalten (z.B. Vorder- und Rückseite)
    und hat eine eigene Historie von Events.
    """
    __tablename__ = 'design_approval_requests'
    
    id = Column(Integer, primary_key=True)
    
    # Referenz zum Auftrag
    order_id = Column(String(50), ForeignKey('orders.id'), nullable=False)
    order = relationship('Order', backref='approval_requests')
    
    # Referenz zum Design (bei Multi-Position-Aufträgen)
    design_id = Column(Integer, ForeignKey('order_designs.id'), nullable=True)
    design = relationship('OrderDesign', backref='approval_requests')
    
    # Token für öffentlichen Zugang
    token = Column(String(100), unique=True, nullable=False, index=True)
    
    # Status
    status = Column(String(30), default=DesignApprovalStatus.DRAFT.value)
    
    # PDF-Dokumentation
    pdf_file_path = Column(String(500))           # Gesendete PDF
    pdf_file_hash = Column(String(64))            # SHA256 Hash der gesendeten PDF
    signed_pdf_path = Column(String(500))         # Zurückerhaltene signierte PDF
    
    # Signatur-Details
    signature_type = Column(String(30))           # Art der Signatur
    signature_data = Column(Text)                 # Base64 Signatur-Bild (bei Canvas)
    signature_certificate = Column(Text)          # Zertifikat-Info (bei Certificate)
    signer_name = Column(String(200))             # Name des Unterzeichners
    signer_email = Column(String(200))            # E-Mail des Unterzeichners
    
    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime)                    # Wann gesendet
    viewed_at = Column(DateTime)                  # Wann erstmals angesehen
    approved_at = Column(DateTime)                # Wann freigegeben
    expires_at = Column(DateTime)                 # Ablaufdatum
    
    # Nachweisführung
    ip_address = Column(String(50))               # IP bei Freigabe
    user_agent = Column(String(500))              # Browser bei Freigabe
    
    # Notizen
    customer_notes = Column(Text)                 # Anmerkungen vom Kunden
    internal_notes = Column(Text)                 # Interne Notizen
    revision_details = Column(Text)               # Details bei Änderungswunsch
    
    # Ersteller
    created_by = Column(String(100))
    
    # Historie
    history_entries = relationship('DesignApprovalHistory', 
                                   back_populates='request',
                                   order_by='DesignApprovalHistory.created_at.desc()',
                                   cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<DesignApprovalRequest {self.id} Order:{self.order_id} Status:{self.status}>"
    
    def get_status_label(self):
        """Deutscher Status-Text"""
        labels = {
            'draft': 'Entwurf',
            'sent': 'Gesendet',
            'viewed': 'Angesehen',
            'approved': 'Freigegeben',
            'revision': 'Änderung angefordert',
            'expired': 'Abgelaufen',
            'cancelled': 'Abgebrochen'
        }
        return labels.get(self.status, self.status)
    
    def get_status_color(self):
        """Bootstrap-Farbe für Status"""
        colors = {
            'draft': 'secondary',
            'sent': 'info',
            'viewed': 'primary',
            'approved': 'success',
            'revision': 'warning',
            'expired': 'danger',
            'cancelled': 'dark'
        }
        return colors.get(self.status, 'secondary')
    
    def is_pending(self):
        """Noch offen?"""
        return self.status in ['draft', 'sent', 'viewed']
    
    def add_history(self, action, details=None, by=None, ip=None):
        """Fügt einen Historie-Eintrag hinzu"""
        entry = DesignApprovalHistory(
            request_id=self.id,
            action=action,
            details=details,
            performed_by=by or 'system',
            ip_address=ip
        )
        db.session.add(entry)
        return entry


class DesignApprovalHistory(db.Model):
    """
    Historie-Eintrag für eine Freigabe-Anfrage
    Dokumentiert jeden Schritt im Freigabe-Prozess
    """
    __tablename__ = 'design_approval_history'
    
    id = Column(Integer, primary_key=True)
    
    # Referenz zur Anfrage
    request_id = Column(Integer, ForeignKey('design_approval_requests.id'), nullable=False)
    request = relationship('DesignApprovalRequest', back_populates='history_entries')
    
    # Aktion
    action = Column(String(50), nullable=False)
    details = Column(Text)
    
    # Wer hat die Aktion ausgeführt
    performed_by = Column(String(100))            # Username oder 'customer' oder 'system'
    ip_address = Column(String(50))
    
    # Zeitstempel
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Optionale Anhänge
    attachment_path = Column(String(500))         # z.B. signierte PDF
    attachment_name = Column(String(200))
    
    def __repr__(self):
        return f"<DesignApprovalHistory {self.action} at {self.created_at}>"
    
    def get_action_label(self):
        """Deutscher Aktions-Text"""
        labels = {
            'created': 'Freigabe-Anfrage erstellt',
            'pdf_generated': 'PDF generiert',
            'email_sent': 'E-Mail an Kunde gesendet',
            'email_opened': 'E-Mail geöffnet',
            'link_clicked': 'Freigabe-Link geöffnet',
            'design_viewed': 'Design angesehen',
            'approved': 'Design freigegeben',
            'revision_requested': 'Änderung angefordert',
            'pdf_returned': 'Signierte PDF empfangen',
            'reminder_sent': 'Erinnerung gesendet',
            'expired': 'Anfrage abgelaufen',
            'cancelled': 'Anfrage abgebrochen',
            'resent': 'Erneut gesendet',
            'signature_verified': 'Signatur verifiziert',
            'note_added': 'Notiz hinzugefügt'
        }
        return labels.get(self.action, self.action)
    
    def get_action_icon(self):
        """Bootstrap-Icon für Aktion"""
        icons = {
            'created': 'bi-plus-circle',
            'pdf_generated': 'bi-file-pdf',
            'email_sent': 'bi-envelope',
            'email_opened': 'bi-envelope-open',
            'link_clicked': 'bi-link-45deg',
            'design_viewed': 'bi-eye',
            'approved': 'bi-check-circle-fill',
            'revision_requested': 'bi-pencil',
            'pdf_returned': 'bi-file-earmark-check',
            'reminder_sent': 'bi-bell',
            'expired': 'bi-clock-history',
            'cancelled': 'bi-x-circle',
            'resent': 'bi-arrow-repeat',
            'signature_verified': 'bi-shield-check',
            'note_added': 'bi-sticky'
        }
        return icons.get(self.action, 'bi-circle')


class DesignApprovalEmailTracking(db.Model):
    """
    Tracking für E-Mail-Zustellung und Öffnung
    """
    __tablename__ = 'design_approval_email_tracking'
    
    id = Column(Integer, primary_key=True)
    
    # Referenz zur Anfrage
    request_id = Column(Integer, ForeignKey('design_approval_requests.id'), nullable=False)
    request = relationship('DesignApprovalRequest', backref='email_tracking')
    
    # E-Mail-Details
    message_id = Column(String(200))              # Message-ID für Tracking
    recipient_email = Column(String(200))
    subject = Column(String(500))
    
    # Status
    sent_at = Column(DateTime)
    delivered_at = Column(DateTime)
    opened_at = Column(DateTime)
    clicked_at = Column(DateTime)
    bounced = Column(Boolean, default=False)
    bounce_reason = Column(Text)
    
    # Anhänge
    has_pdf_attachment = Column(Boolean, default=False)
    pdf_attachment_hash = Column(String(64))
    
    def __repr__(self):
        return f"<DesignApprovalEmailTracking {self.recipient_email}>"
