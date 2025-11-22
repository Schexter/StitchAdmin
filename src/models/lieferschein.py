# -*- coding: utf-8 -*-
"""
Lieferschein- und Packschein-Verwaltung
========================================

Erstellt von: StitchAdmin
Zweck: Verwaltung von Lieferscheinen und Packscheinen
"""

from datetime import datetime, date
from decimal import Decimal
from src.models import db
from src.models.nummernkreis import DocumentType, number_sequence_service


class LieferscheinStatus:
    """Status-Optionen für Lieferscheine"""
    ENTWURF = 'entwurf'              # Noch nicht gedruckt
    GEDRUCKT = 'gedruckt'            # Gedruckt/Erstellt
    VERSENDET = 'versendet'          # Paket versendet
    ZUGESTELLT = 'zugestellt'        # Beim Kunden angekommen
    STORNIERT = 'storniert'          # Storniert


class Lieferschein(db.Model):
    """Lieferscheine für Warenausgang"""
    __tablename__ = 'lieferscheine'

    id = db.Column(db.Integer, primary_key=True)

    # Identifikation
    lieferscheinnummer = db.Column(db.String(50), unique=True, nullable=False, index=True)
    typ = db.Column(db.String(20), default='lieferschein')  # 'lieferschein' oder 'packschein'

    # Referenzen
    auftrag_id = db.Column(db.String(50), db.ForeignKey('orders.id'))
    rechnung_id = db.Column(db.Integer, db.ForeignKey('rechnungen.id'))

    # Kunde
    kunde_id = db.Column(db.String(50), db.ForeignKey('customers.id'), nullable=False)
    kunde_name = db.Column(db.String(200), nullable=False)
    kunde_adresse = db.Column(db.Text)

    # Lieferadresse (falls abweichend)
    lieferadresse_name = db.Column(db.String(200))
    lieferadresse_adresse = db.Column(db.Text)

    # Status
    status = db.Column(db.String(20), default=LieferscheinStatus.ENTWURF, index=True)

    # Daten
    lieferdatum = db.Column(db.Date, nullable=False, default=date.today)
    geplantes_versanddatum = db.Column(db.Date)
    tatsaechliches_versanddatum = db.Column(db.Date)

    # Versandinformationen
    versandart = db.Column(db.String(100))  # z.B. "DHL Paket", "DPD", "Abholung"
    trackingnummer = db.Column(db.String(100))
    anzahl_pakete = db.Column(db.Integer, default=1)
    gewicht_kg = db.Column(db.Float)

    # Bemerkungen
    bemerkungen = db.Column(db.Text)
    interne_notizen = db.Column(db.Text)

    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))

    # PDF
    pdf_erstellt_am = db.Column(db.DateTime)
    pdf_path = db.Column(db.String(500))

    # Beziehungen
    kunde = db.relationship('Customer', foreign_keys=[kunde_id], backref='lieferscheine')
    auftrag = db.relationship('Order', foreign_keys=[auftrag_id], backref='lieferscheine')
    rechnung = db.relationship('Rechnung', foreign_keys=[rechnung_id], backref='lieferscheine')
    positionen = db.relationship('LieferscheinPosition', back_populates='lieferschein',
                                 cascade='all, delete-orphan', order_by='LieferscheinPosition.position')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Nummer generieren
        if not self.lieferscheinnummer:
            doc_type = DocumentType.PACKSCHEIN if self.typ == 'packschein' else DocumentType.LIEFERSCHEIN
            self.lieferscheinnummer = number_sequence_service.get_next_number(
                document_type=doc_type,
                created_by=self.created_by
            )

    def versenden(self, trackingnummer=None, versandart=None, created_by=None):
        """
        Markiert den Lieferschein als versendet

        Args:
            trackingnummer: Tracking-Nummer (optional)
            versandart: Versandart (optional)
            created_by: Benutzer
        """
        self.status = LieferscheinStatus.VERSENDET
        self.tatsaechliches_versanddatum = date.today()

        if trackingnummer:
            self.trackingnummer = trackingnummer
        if versandart:
            self.versandart = versandart

        self.updated_by = created_by
        self.updated_at = datetime.utcnow()
        db.session.commit()

    def zustellen(self, created_by=None):
        """
        Markiert den Lieferschein als zugestellt

        Args:
            created_by: Benutzer
        """
        self.status = LieferscheinStatus.ZUGESTELLT
        self.updated_by = created_by
        self.updated_at = datetime.utcnow()
        db.session.commit()

    def stornieren(self, created_by=None):
        """
        Storniert den Lieferschein

        Args:
            created_by: Benutzer
        """
        self.status = LieferscheinStatus.STORNIERT
        self.updated_by = created_by
        self.updated_at = datetime.utcnow()

        # Im Nummernkreis-Log als storniert markieren
        number_sequence_service.cancel_document(
            document_number=self.lieferscheinnummer,
            cancelled_by=created_by,
            reason='Lieferschein storniert'
        )

        db.session.commit()

    @classmethod
    def von_auftrag_erstellen(cls, auftrag_id, created_by=None):
        """
        Erstellt einen Lieferschein aus einem Auftrag

        Args:
            auftrag_id: ID des Auftrags
            created_by: Benutzer

        Returns:
            Lieferschein: Der erstellte Lieferschein
        """
        from src.models.models import Order

        auftrag = Order.query.get(auftrag_id)
        if not auftrag:
            raise ValueError("Auftrag nicht gefunden")

        # Lieferschein erstellen
        lieferschein = cls(
            auftrag_id=auftrag.id,
            kunde_id=auftrag.customer_id,
            kunde_name=auftrag.customer.display_name if auftrag.customer else '',
            kunde_adresse=f"{auftrag.customer.street}\n{auftrag.customer.postal_code} {auftrag.customer.city}" if auftrag.customer else '',
            bemerkungen=auftrag.customer_notes,
            interne_notizen=auftrag.internal_notes,
            created_by=created_by
        )
        db.session.add(lieferschein)
        db.session.flush()

        # Positionen übertragen
        for i, auftrag_item in enumerate(auftrag.items, start=1):
            position = LieferscheinPosition(
                lieferschein_id=lieferschein.id,
                position=i,
                artikel_id=auftrag_item.article_id,
                artikel_name=auftrag_item.description,
                menge=auftrag_item.quantity,
                einheit='Stück'
            )
            db.session.add(position)

        db.session.commit()
        return lieferschein

    def __repr__(self):
        return f'<Lieferschein {self.lieferscheinnummer}>'


class LieferscheinPosition(db.Model):
    """Positionen eines Lieferscheins"""
    __tablename__ = 'lieferschein_positionen'

    id = db.Column(db.Integer, primary_key=True)
    lieferschein_id = db.Column(db.Integer, db.ForeignKey('lieferscheine.id'), nullable=False)

    # Position
    position = db.Column(db.Integer, nullable=False)

    # Artikel
    artikel_id = db.Column(db.String(50), db.ForeignKey('articles.id'))
    artikel_name = db.Column(db.String(200), nullable=False)
    artikelnummer = db.Column(db.String(100))

    # Menge
    menge = db.Column(db.Float, nullable=False, default=1)
    einheit = db.Column(db.String(20), default='Stück')

    # Seriennummern / Chargennummern (optional)
    seriennummern = db.Column(db.Text)  # Komma-getrennt oder JSON

    # Bemerkungen
    bemerkungen = db.Column(db.Text)

    # Beziehungen
    lieferschein = db.relationship('Lieferschein', back_populates='positionen')
    artikel = db.relationship('Article', foreign_keys=[artikel_id])

    def __repr__(self):
        return f'<LieferscheinPosition {self.position}: {self.artikel_name}>'
