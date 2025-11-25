# -*- coding: utf-8 -*-
"""
Nummernkreis-Verwaltung für alle Dokumententypen
=================================================

Erstellt von: StitchAdmin
Zweck: Gesetzeskonforme, fortlaufende Nummerierung für:
- Angebote
- Aufträge
- Lieferscheine/Packscheine
- Rechnungen
- Gutschriften/Stornierungen

Gesetzliche Anforderungen:
- Fortlaufende, lückenlose Nummerierung (§14 UStG)
- Eindeutige Zuordnung zu Geschäftsvorfällen
- Unveränderbarkeit (einmal vergeben, nicht wiederverwendbar)
- Nachvollziehbarkeit
"""

from datetime import datetime
from src.models import db
from sqlalchemy import func
import threading


# Thread-Lock für thread-sichere Nummernvergabe
_number_lock = threading.Lock()


class DocumentType:
    """Dokumenttypen"""
    ANGEBOT = 'angebot'            # Angebot
    AUFTRAG = 'auftrag'            # Arbeitsauftrag/Kundenauftrag
    LIEFERSCHEIN = 'lieferschein'  # Lieferschein
    PACKSCHEIN = 'packschein'      # Packschein
    RECHNUNG = 'rechnung'          # Rechnung
    GUTSCHRIFT = 'gutschrift'      # Gutschrift
    STORNORECHNUNG = 'stornorechnung'  # Stornorechnung
    
    # Einkauf-Modul (NEU)
    PURCHASE_ORDER = 'purchase_order'  # Einkaufsbestellung (Artikel bei Lieferanten)
    DESIGN_ORDER = 'design_order'      # Design-Bestellung (Puncher/Digitizer)


class NumberSequenceSettings(db.Model):
    """Einstellungen für Nummernkreise"""
    __tablename__ = 'number_sequence_settings'

    id = db.Column(db.Integer, primary_key=True)
    document_type = db.Column(db.String(50), unique=True, nullable=False)  # z.B. 'rechnung'

    # Format-Einstellungen
    prefix = db.Column(db.String(10), nullable=False)  # z.B. 'RE', 'AN', 'LS'
    use_year = db.Column(db.Boolean, default=True)     # Jahr einbeziehen?
    use_month = db.Column(db.Boolean, default=False)   # Monat einbeziehen?
    number_length = db.Column(db.Integer, default=4)   # Länge der laufenden Nummer

    # Beispiel-Format: RE-2024-0001, AN-202401-0001, LS-0001
    format_pattern = db.Column(db.String(100))  # z.B. '{prefix}-{year}-{number:04d}'

    # Zähler
    current_year = db.Column(db.Integer)
    current_month = db.Column(db.Integer)
    current_number = db.Column(db.Integer, default=0)

    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    @classmethod
    def get_settings(cls, document_type):
        """
        Hole oder erstelle Einstellungen für einen Dokumenttyp

        Args:
            document_type: Typ des Dokuments (DocumentType)

        Returns:
            NumberSequenceSettings Instanz
        """
        settings = cls.query.filter_by(document_type=document_type).first()

        if not settings:
            # Default-Einstellungen erstellen
            default_settings = {
                DocumentType.ANGEBOT: {
                    'prefix': 'AN',
                    'use_year': True,
                    'use_month': False,
                    'format_pattern': '{prefix}-{year}-{number:04d}'
                },
                DocumentType.AUFTRAG: {
                    'prefix': 'AU',
                    'use_year': True,
                    'use_month': False,
                    'format_pattern': '{prefix}-{year}-{number:04d}'
                },
                DocumentType.LIEFERSCHEIN: {
                    'prefix': 'LS',
                    'use_year': True,
                    'use_month': False,
                    'format_pattern': '{prefix}-{year}-{number:04d}'
                },
                DocumentType.PACKSCHEIN: {
                    'prefix': 'PS',
                    'use_year': True,
                    'use_month': False,
                    'format_pattern': '{prefix}-{year}-{number:04d}'
                },
                DocumentType.RECHNUNG: {
                    'prefix': 'RE',
                    'use_year': True,
                    'use_month': True,
                    'format_pattern': '{prefix}-{year}{month:02d}-{number:04d}'
                },
                DocumentType.GUTSCHRIFT: {
                    'prefix': 'GS',
                    'use_year': True,
                    'use_month': True,
                    'format_pattern': '{prefix}-{year}{month:02d}-{number:04d}'
                },
                DocumentType.STORNORECHNUNG: {
                    'prefix': 'SR',
                    'use_year': True,
                    'use_month': True,
                    'format_pattern': '{prefix}-{year}{month:02d}-{number:04d}'
                },
                # Einkauf-Modul
                DocumentType.PURCHASE_ORDER: {
                    'prefix': 'PO',
                    'use_year': True,
                    'use_month': False,
                    'format_pattern': '{prefix}-{year}-{number:04d}'
                },
                DocumentType.DESIGN_ORDER: {
                    'prefix': 'DO',
                    'use_year': True,
                    'use_month': False,
                    'format_pattern': '{prefix}-{year}-{number:04d}'
                }
            }

            config = default_settings.get(document_type, {
                'prefix': 'DOC',
                'use_year': True,
                'use_month': False,
                'format_pattern': '{prefix}-{year}-{number:04d}'
            })

            settings = cls(
                document_type=document_type,
                prefix=config['prefix'],
                use_year=config['use_year'],
                use_month=config['use_month'],
                format_pattern=config['format_pattern'],
                current_year=datetime.now().year,
                current_month=datetime.now().month,
                current_number=0
            )
            db.session.add(settings)
            try:
                db.session.commit()
            except:
                db.session.rollback()
                # Erneut versuchen zu laden (falls parallel erstellt)
                settings = cls.query.filter_by(document_type=document_type).first()

        return settings

    def generate_next_number(self):
        """
        Generiert die nächste Nummer für diesen Dokumenttyp

        Thread-sicher durch Lock-Mechanismus

        Returns:
            str: Die generierte Dokumentnummer
        """
        with _number_lock:
            now = datetime.now()
            current_year = now.year
            current_month = now.month

            # Prüfen ob Jahr/Monat gewechselt hat
            reset_counter = False

            if self.use_year and self.current_year != current_year:
                reset_counter = True
                self.current_year = current_year
                self.current_month = current_month

            if self.use_month and self.current_month != current_month:
                reset_counter = True
                self.current_month = current_month

            if reset_counter:
                self.current_number = 0

            # Nächste Nummer
            self.current_number += 1
            number = self.current_number

            # Nummer formatieren
            formatted_number = self.format_pattern.format(
                prefix=self.prefix,
                year=current_year,
                month=current_month,
                number=number
            )

            # Speichern
            self.updated_at = datetime.utcnow()
            db.session.commit()

            return formatted_number


class NumberSequenceLog(db.Model):
    """
    Protokoll aller vergebenen Nummern

    Wichtig für:
    - Gesetzliche Nachvollziehbarkeit
    - Audit-Trail
    - Finanzamt-Prüfungen
    - TSE-Konformität
    """
    __tablename__ = 'number_sequence_log'

    id = db.Column(db.Integer, primary_key=True)

    # Dokumentinformationen
    document_type = db.Column(db.String(50), nullable=False, index=True)
    document_number = db.Column(db.String(100), nullable=False, unique=True, index=True)
    document_id = db.Column(db.String(100))  # Referenz zum eigentlichen Dokument

    # Zeitstempel
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.String(80))  # Benutzer der das Dokument erstellt hat

    # Finanzinformationen (für Rechnungen)
    amount_net = db.Column(db.Float)
    amount_tax = db.Column(db.Float)
    amount_gross = db.Column(db.Float)

    # Status
    is_cancelled = db.Column(db.Boolean, default=False)  # Wurde storniert?
    cancelled_at = db.Column(db.DateTime)
    cancelled_by = db.Column(db.String(80))
    cancellation_reason = db.Column(db.Text)

    # TSE-Daten (falls vorhanden)
    tse_transaction_number = db.Column(db.String(100))
    tse_signature = db.Column(db.Text)
    tse_time_format = db.Column(db.String(50))

    # Zusätzliche Metadaten
    metadata_json = db.Column(db.Text)  # Zusätzliche Daten als JSON

    @classmethod
    def log_number(cls, document_type, document_number, document_id=None,
                   created_by=None, amount_net=None, amount_tax=None, amount_gross=None,
                   tse_data=None, metadata=None):
        """
        Protokolliert eine vergebene Nummer

        Args:
            document_type: Dokumenttyp
            document_number: Vergebene Nummer
            document_id: ID des Dokuments
            created_by: Benutzername
            amount_net: Nettobetrag
            amount_tax: Steuerbetrag
            amount_gross: Bruttobetrag
            tse_data: TSE-Daten (dict)
            metadata: Zusätzliche Metadaten (dict)
        """
        import json

        log_entry = cls(
            document_type=document_type,
            document_number=document_number,
            document_id=document_id,
            created_by=created_by,
            amount_net=amount_net,
            amount_tax=amount_tax,
            amount_gross=amount_gross,
            metadata_json=json.dumps(metadata) if metadata else None
        )

        if tse_data:
            log_entry.tse_transaction_number = tse_data.get('transaction_number')
            log_entry.tse_signature = tse_data.get('signature')
            log_entry.tse_time_format = tse_data.get('time_format')

        db.session.add(log_entry)
        db.session.commit()

        return log_entry

    def cancel(self, cancelled_by, reason):
        """
        Markiert ein Dokument als storniert

        Args:
            cancelled_by: Benutzer der storniert hat
            reason: Grund der Stornierung
        """
        self.is_cancelled = True
        self.cancelled_at = datetime.utcnow()
        self.cancelled_by = cancelled_by
        self.cancellation_reason = reason
        db.session.commit()


class NumberSequenceService:
    """Service-Klasse für Nummernkreis-Verwaltung"""

    @staticmethod
    def get_next_number(document_type, document_id=None, created_by=None,
                       amount_net=None, amount_tax=None, amount_gross=None,
                       tse_data=None, metadata=None):
        """
        Holt die nächste Nummer für einen Dokumenttyp und protokolliert sie

        Args:
            document_type: Typ des Dokuments
            document_id: ID des Dokuments (optional)
            created_by: Benutzer (optional)
            amount_net: Nettobetrag (optional)
            amount_tax: Steuerbetrag (optional)
            amount_gross: Bruttobetrag (optional)
            tse_data: TSE-Daten (optional)
            metadata: Zusätzliche Metadaten (optional)

        Returns:
            str: Die generierte Nummer
        """
        # Einstellungen laden
        settings = NumberSequenceSettings.get_settings(document_type)

        # Nächste Nummer generieren
        document_number = settings.generate_next_number()

        # Protokollieren
        NumberSequenceLog.log_number(
            document_type=document_type,
            document_number=document_number,
            document_id=document_id,
            created_by=created_by,
            amount_net=amount_net,
            amount_tax=amount_tax,
            amount_gross=amount_gross,
            tse_data=tse_data,
            metadata=metadata
        )

        return document_number

    @staticmethod
    def cancel_document(document_number, cancelled_by, reason):
        """
        Storniert ein Dokument

        Args:
            document_number: Dokumentnummer
            cancelled_by: Benutzer
            reason: Grund
        """
        log_entry = NumberSequenceLog.query.filter_by(
            document_number=document_number
        ).first()

        if log_entry:
            log_entry.cancel(cancelled_by, reason)
            return True
        return False

    @staticmethod
    def get_document_history(document_type=None, start_date=None, end_date=None):
        """
        Holt die Historie der Dokumente

        Args:
            document_type: Filter nach Dokumenttyp (optional)
            start_date: Startdatum (optional)
            end_date: Enddatum (optional)

        Returns:
            Query mit Dokumenten
        """
        query = NumberSequenceLog.query

        if document_type:
            query = query.filter_by(document_type=document_type)

        if start_date:
            query = query.filter(NumberSequenceLog.created_at >= start_date)

        if end_date:
            query = query.filter(NumberSequenceLog.created_at <= end_date)

        return query.order_by(NumberSequenceLog.created_at.desc())

    @staticmethod
    def export_for_tax_audit(start_date, end_date, document_type=None):
        """
        Exportiert Daten für Finanzamt-Prüfung

        Args:
            start_date: Startdatum
            end_date: Enddatum
            document_type: Filter nach Dokumenttyp (optional)

        Returns:
            Liste von Dictionaries mit allen relevanten Daten
        """
        logs = NumberSequenceService.get_document_history(
            document_type=document_type,
            start_date=start_date,
            end_date=end_date
        ).all()

        export_data = []
        for log in logs:
            export_data.append({
                'document_type': log.document_type,
                'document_number': log.document_number,
                'document_id': log.document_id,
                'created_at': log.created_at.isoformat(),
                'created_by': log.created_by,
                'amount_net': log.amount_net,
                'amount_tax': log.amount_tax,
                'amount_gross': log.amount_gross,
                'is_cancelled': log.is_cancelled,
                'cancelled_at': log.cancelled_at.isoformat() if log.cancelled_at else None,
                'cancelled_by': log.cancelled_by,
                'cancellation_reason': log.cancellation_reason,
                'tse_transaction_number': log.tse_transaction_number,
                'tse_signature': log.tse_signature
            })

        return export_data


# Singleton-Instanz
number_sequence_service = NumberSequenceService()
