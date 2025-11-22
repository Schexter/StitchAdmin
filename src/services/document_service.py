# -*- coding: utf-8 -*-
"""
Document Upload & Management Service
StitchAdmin 2.0
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
import shutil
from datetime import datetime, date
from werkzeug.utils import secure_filename
from src.models.document import Document, DocumentAccessLog
from src.models.models import db
import logging
import mimetypes
from pathlib import Path

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Service für Dokumenten-Verwaltung und Upload
    """
    
    # Erlaubte Dateitypen
    ALLOWED_EXTENSIONS = {
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
        'txt', 'csv', 'odt', 'ods', 'odp',
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff',
        'zip', 'rar', '7z',
        'msg', 'eml'  # E-Mail-Formate
    }
    
    # Maximale Dateigröße (in Bytes) - 50MB
    MAX_FILE_SIZE = 50 * 1024 * 1024
    
    # Upload-Ordner
    UPLOAD_BASE_DIR = 'uploads/documents'
    
    def __init__(self):
        """Initialisiert Service"""
        self._ensure_upload_dir()
    
    def _ensure_upload_dir(self):
        """Stellt sicher dass Upload-Ordner existiert"""
        os.makedirs(self.UPLOAD_BASE_DIR, exist_ok=True)
    
    def allowed_file(self, filename):
        """Prüft ob Dateityp erlaubt ist"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS
    
    def upload_document(self, file, title, category, subcategory=None, tags=None,
                       customer_id=None, order_id=None, invoice_id=None, supplier_id=None,
                       document_date=None, uploaded_by_user_id=None, description=None,
                       visibility='private', department=None):
        """
        Lädt Dokument hoch und speichert in Datenbank
        
        Args:
            file: Werkzeug FileStorage Objekt
            title: Titel des Dokuments
            category: Kategorie (rechnung, vertrag, etc.)
            ... weitere Parameter siehe Document Model
        
        Returns:
            Document Objekt oder None bei Fehler
        """
        try:
            # Validierungen
            if not file:
                raise ValueError("Keine Datei angegeben")
            
            if not self.allowed_file(file.filename):
                raise ValueError(f"Dateityp nicht erlaubt: {file.filename}")
            
            # Datei-Infos
            original_filename = secure_filename(file.filename)
            file_size = self._get_file_size(file)
            
            if file_size > self.MAX_FILE_SIZE:
                raise ValueError(f"Datei zu groß: {file_size / 1024 / 1024:.2f} MB (Max: 50 MB)")
            
            # Generiere eindeutigen Dateinamen
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = f"{timestamp}_{original_filename}"
            
            # Erstelle Ordnerstruktur: Jahr/Monat/Kategorie
            year = datetime.now().year
            month = datetime.now().strftime('%m_%B')
            category_folder = category or 'sonstiges'
            
            relative_path = os.path.join(str(year), month, category_folder)
            full_folder = os.path.join(self.UPLOAD_BASE_DIR, relative_path)
            os.makedirs(full_folder, exist_ok=True)
            
            # Vollständiger Dateipfad
            file_path = os.path.join(full_folder, safe_filename)
            
            # Speichere Datei
            file.save(file_path)
            logger.info(f"Datei gespeichert: {file_path}")
            
            # Berechne Hash
            file_hash = Document.calculate_file_hash(file_path)
            
            # Prüfe auf Duplikat
            existing = Document.query.filter_by(file_hash=file_hash).first()
            if existing:
                logger.warning(f"Duplikat gefunden: {existing.document_number}")
                # Optional: Trotzdem speichern oder Fehler werfen?
            
            # Mime-Type ermitteln
            mime_type, _ = mimetypes.guess_type(original_filename)
            
            # Erstelle Document-Eintrag
            doc = Document(
                title=title,
                document_number=Document.generate_document_number(),
                category=category,
                subcategory=subcategory,
                tags=tags,
                filename=safe_filename,
                original_filename=original_filename,
                file_path=file_path,
                file_size=file_size,
                mime_type=mime_type or 'application/octet-stream',
                file_hash=file_hash,
                customer_id=customer_id,
                order_id=order_id,
                invoice_id=invoice_id,
                supplier_id=supplier_id,
                document_date=document_date or date.today(),
                uploaded_by=uploaded_by_user_id,
                description=description,
                visibility=visibility,
                department=department
            )
            
            db.session.add(doc)
            db.session.flush()  # Um ID zu bekommen
            
            # OCR für PDFs und Bilder (optional)
            if doc.is_pdf() or doc.is_image():
                self._extract_text(doc)
            
            # Access Log
            if uploaded_by_user_id:
                self._log_access(doc.id, uploaded_by_user_id, 'upload')
            
            db.session.commit()
            
            logger.info(f"Dokument erstellt: {doc.document_number}")
            return doc
            
        except Exception as e:
            logger.error(f"Fehler beim Upload: {e}")
            db.session.rollback()
            
            # Lösche Datei falls vorhanden
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
            
            raise
    
    def _get_file_size(self, file):
        """Ermittelt Dateigröße"""
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)  # Zurück zum Anfang
        return size
    
    def _extract_text(self, document):
        """
        Extrahiert Text aus PDF/Bildern via OCR
        (Vereinfachte Version - für Produktion Tesseract/PyPDF2 nutzen)
        """
        try:
            if document.is_pdf():
                # TODO: PyPDF2 oder pdfplumber nutzen
                pass
            elif document.is_image():
                # TODO: Tesseract OCR nutzen
                pass
            
            # Speichere extrahierten Text
            # document.ocr_text = extracted_text
            # document.searchable_content = extracted_text
            
        except Exception as e:
            logger.error(f"OCR Fehler: {e}")
    
    def get_document(self, document_id, user_id=None):
        """
        Holt Dokument mit Access-Logging
        
        Args:
            document_id: ID des Dokuments
            user_id: User der zugreift
        
        Returns:
            Document Objekt
        """
        doc = Document.query.get_or_404(document_id)
        
        # Log Access
        if user_id:
            self._log_access(document_id, user_id, 'view')
        
        return doc
    
    def download_document(self, document_id, user_id=None):
        """
        Bereitet Download vor und loggt Zugriff
        
        Args:
            document_id: ID des Dokuments
            user_id: User der downloaded
        
        Returns:
            Tuple (file_path, original_filename, mime_type)
        """
        doc = Document.query.get_or_404(document_id)
        
        # Prüfe ob Datei existiert
        if not os.path.exists(doc.file_path):
            raise FileNotFoundError(f"Datei nicht gefunden: {doc.file_path}")
        
        # Log Access
        if user_id:
            self._log_access(document_id, user_id, 'download')
        
        return (doc.file_path, doc.original_filename, doc.mime_type)
    
    def update_document(self, document_id, user_id=None, **kwargs):
        """
        Aktualisiert Dokument-Metadaten
        
        Args:
            document_id: ID des Dokuments
            user_id: User der ändert
            **kwargs: Zu ändernde Felder
        
        Returns:
            Document Objekt
        """
        doc = Document.query.get_or_404(document_id)
        
        # Prüfe ob gesperrt
        if doc.is_locked:
            raise ValueError("Dokument ist gesperrt und kann nicht geändert werden")
        
        # Erlaubte Felder
        allowed_fields = [
            'title', 'category', 'subcategory', 'tags', 'description', 'notes',
            'customer_id', 'order_id', 'invoice_id', 'supplier_id',
            'document_date', 'visibility', 'department'
        ]
        
        # Update Felder
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(doc, field, value)
        
        doc.updated_at = datetime.utcnow()
        
        # Log Access
        if user_id:
            self._log_access(document_id, user_id, 'edit', 
                           details=f"Updated: {', '.join(kwargs.keys())}")
        
        db.session.commit()
        return doc
    
    def delete_document(self, document_id, user_id=None):
        """
        Löscht Dokument (Soft-Delete für GoBD)
        
        Args:
            document_id: ID des Dokuments
            user_id: User der löscht
        
        Returns:
            True bei Erfolg
        """
        doc = Document.query.get_or_404(document_id)
        
        # Prüfe ob gesperrt
        if doc.is_locked:
            raise ValueError("Gesperrtes Dokument kann nicht gelöscht werden")
        
        # Log Access
        if user_id:
            self._log_access(document_id, user_id, 'delete')
        
        # Soft-Delete: Markiere als archiviert
        doc.is_archived = True
        doc.archive_date = datetime.utcnow()
        
        # Optional: Datei wirklich löschen (NICHT für GoBD!)
        # os.remove(doc.file_path)
        
        db.session.commit()
        return True
    
    def search_documents(self, query=None, category=None, customer_id=None,
                        order_id=None, date_from=None, date_to=None,
                        tags=None, limit=100):
        """
        Sucht Dokumente
        
        Args:
            query: Suchbegriff (Titel, OCR-Text)
            category: Kategorie-Filter
            customer_id: Kunden-Filter
            order_id: Auftrags-Filter
            date_from: Datum von
            date_to: Datum bis
            tags: Tag-Filter
            limit: Max. Ergebnisse
        
        Returns:
            Liste von Documents
        """
        q = Document.query.filter_by(is_archived=False)
        
        # Text-Suche
        if query:
            search_pattern = f'%{query}%'
            q = q.filter(
                db.or_(
                    Document.title.ilike(search_pattern),
                    Document.description.ilike(search_pattern),
                    Document.ocr_text.ilike(search_pattern),
                    Document.tags.ilike(search_pattern)
                )
            )
        
        # Filter
        if category:
            q = q.filter_by(category=category)
        
        if customer_id:
            q = q.filter_by(customer_id=customer_id)
        
        if order_id:
            q = q.filter_by(order_id=order_id)
        
        if date_from:
            q = q.filter(Document.document_date >= date_from)
        
        if date_to:
            q = q.filter(Document.document_date <= date_to)
        
        if tags:
            for tag in tags.split(','):
                q = q.filter(Document.tags.ilike(f'%{tag.strip()}%'))
        
        # Sortierung
        q = q.order_by(Document.created_at.desc())
        
        return q.limit(limit).all()
    
    def create_folder_structure(self, customer_id):
        """
        Erstellt Ordnerstruktur für Kunden
        
        Args:
            customer_id: ID des Kunden
        
        Returns:
            Pfad zum Kunden-Ordner
        """
        from src.models.models import Customer
        customer = Customer.query.get_or_404(customer_id)
        
        # Erstelle Ordner: uploads/documents/Kunden/KUN-00001_Firmenname/
        customer_folder = f"KUN-{customer.id:05d}_{customer.name}"
        customer_folder = secure_filename(customer_folder)
        
        base_path = os.path.join(self.UPLOAD_BASE_DIR, 'Kunden', customer_folder)
        
        # Unterordner
        subfolders = ['Verträge', 'Rechnungen', 'Angebote', 'Korrespondenz', 'Projekte']
        
        for subfolder in subfolders:
            os.makedirs(os.path.join(base_path, subfolder), exist_ok=True)
        
        logger.info(f"Ordnerstruktur erstellt: {base_path}")
        return base_path
    
    def _log_access(self, document_id, user_id, action, details=None):
        """Loggt Dokumenten-Zugriff"""
        log = DocumentAccessLog(
            document_id=document_id,
            user_id=user_id,
            action=action,
            details=details
        )
        db.session.add(log)
    
    def get_statistics(self):
        """Holt Statistiken über Dokumente"""
        total = Document.query.count()
        by_category = db.session.query(
            Document.category,
            db.func.count(Document.id)
        ).group_by(Document.category).all()
        
        total_size = db.session.query(
            db.func.sum(Document.file_size)
        ).scalar() or 0
        
        return {
            'total_documents': total,
            'by_category': dict(by_category),
            'total_size_mb': total_size / 1024 / 1024,
            'upload_folder': self.UPLOAD_BASE_DIR
        }
