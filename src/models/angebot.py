# -*- coding: utf-8 -*-
"""
Angebots-Verwaltung
===================

Erstellt von: StitchAdmin
Zweck: Verwaltung von Kundenangeboten
"""

from datetime import datetime, timedelta, date
from decimal import Decimal
from src.models import db
from src.models.nummernkreis import DocumentType, number_sequence_service


class AngebotStatus:
    """Status-Optionen für Angebote"""
    ENTWURF = 'entwurf'              # Noch nicht verschickt
    VERSCHICKT = 'verschickt'        # An Kunden verschickt
    ANGENOMMEN = 'angenommen'        # Kunde hat angenommen
    ABGELEHNT = 'abgelehnt'          # Kunde hat abgelehnt
    ABGELAUFEN = 'abgelaufen'        # Gültigkeitsdauer überschritten
    STORNIERT = 'storniert'          # Vom Verkäufer storniert


class Angebot(db.Model):
    """Angebote für Kunden"""
    __tablename__ = 'angebote'

    id = db.Column(db.Integer, primary_key=True)

    # Angebots-Identifikation
    angebotsnummer = db.Column(db.String(50), unique=True, nullable=False, index=True)

    # Kunde
    kunde_id = db.Column(db.String(50), db.ForeignKey('customers.id'), nullable=False)
    kunde_name = db.Column(db.String(200), nullable=False)
    kunde_adresse = db.Column(db.Text)
    kunde_email = db.Column(db.String(120))

    # Status
    status = db.Column(db.String(20), default=AngebotStatus.ENTWURF, index=True)

    # Daten
    angebotsdatum = db.Column(db.Date, nullable=False, default=date.today)
    gueltig_bis = db.Column(db.Date)  # Gültigkeitsdatum
    gueltig_tage = db.Column(db.Integer, default=30)  # Gültig für X Tage

    # Titel und Beschreibung
    titel = db.Column(db.String(200))
    beschreibung = db.Column(db.Text)
    bemerkungen = db.Column(db.Text)  # Interne Notizen

    # Beträge (werden aus Positionen berechnet)
    netto_gesamt = db.Column(db.Float, default=0.0)
    mwst_gesamt = db.Column(db.Float, default=0.0)
    brutto_gesamt = db.Column(db.Float, default=0.0)

    # Rabatt
    rabatt_prozent = db.Column(db.Float, default=0.0)
    rabatt_betrag = db.Column(db.Float, default=0.0)

    # Zahlungsbedingungen
    zahlungsbedingungen = db.Column(db.Text)

    # Lieferbedingungen
    lieferzeit = db.Column(db.String(100))  # z.B. "2-3 Werktage"
    versandkosten = db.Column(db.Float, default=0.0)

    # Verknüpfung mit Auftrag
    auftrag_id = db.Column(db.String(50), db.ForeignKey('orders.id'))  # Wenn Angebot angenommen wurde
    erstellt_aus_auftrag_id = db.Column(db.String(50), db.ForeignKey('orders.id'))  # Wenn aus Auftrag erstellt
    in_auftrag_umgewandelt_am = db.Column(db.DateTime)

    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))

    # PDF
    pdf_erstellt_am = db.Column(db.DateTime)
    pdf_path = db.Column(db.String(500))

    # Beziehungen
    kunde = db.relationship('Customer', foreign_keys=[kunde_id], backref='angebote')
    auftrag = db.relationship('Order', foreign_keys=[auftrag_id], backref='angebote')
    positionen = db.relationship('AngebotsPosition', back_populates='angebot',
                                 cascade='all, delete-orphan', order_by='AngebotsPosition.position')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Angebotsnummer generieren
        if not self.angebotsnummer:
            self.angebotsnummer = number_sequence_service.get_next_number(
                document_type=DocumentType.ANGEBOT,
                created_by=self.created_by
            )

        # Gültigkeitsdatum berechnen
        if not self.gueltig_bis and self.angebotsdatum:
            self.gueltig_bis = self.angebotsdatum + timedelta(days=self.gueltig_tage)

    def calculate_totals(self):
        """Berechnet die Gesamtsummen aus den Positionen"""
        netto = Decimal('0.0')
        mwst = Decimal('0.0')

        for position in self.positionen:
            netto += Decimal(str(position.netto_betrag or 0))
            mwst += Decimal(str(position.mwst_betrag or 0))

        # Rabatt anwenden
        if self.rabatt_prozent:
            rabatt = netto * Decimal(str(self.rabatt_prozent)) / Decimal('100')
            self.rabatt_betrag = float(rabatt)
            netto -= rabatt

        # Versandkosten hinzufügen
        if self.versandkosten:
            netto += Decimal(str(self.versandkosten))

        self.netto_gesamt = float(netto)
        self.mwst_gesamt = float(mwst)
        self.brutto_gesamt = float(netto + mwst)

    @property
    def ist_gueltig(self):
        """Prüft ob Angebot noch gültig ist"""
        if not self.gueltig_bis:
            return True
        return date.today() <= self.gueltig_bis

    @property
    def ist_abgelaufen(self):
        """Prüft ob Angebot abgelaufen ist"""
        return not self.ist_gueltig

    def annehmen(self, created_by=None):
        """
        Markiert das Angebot als angenommen

        Args:
            created_by: Benutzer der die Annahme durchführt
        """
        if self.status == AngebotStatus.VERSCHICKT:
            self.status = AngebotStatus.ANGENOMMEN
            self.updated_by = created_by
            self.updated_at = datetime.utcnow()
            db.session.commit()
            return True
        return False

    def ablehnen(self, created_by=None):
        """
        Markiert das Angebot als abgelehnt

        Args:
            created_by: Benutzer der die Ablehnung durchführt
        """
        if self.status in [AngebotStatus.VERSCHICKT, AngebotStatus.ENTWURF]:
            self.status = AngebotStatus.ABGELEHNT
            self.updated_by = created_by
            self.updated_at = datetime.utcnow()
            db.session.commit()
            return True
        return False

    def stornieren(self, created_by=None):
        """
        Storniert das Angebot

        Args:
            created_by: Benutzer der storniert
        """
        self.status = AngebotStatus.STORNIERT
        self.updated_by = created_by
        self.updated_at = datetime.utcnow()

        # Im Nummernkreis-Log als storniert markieren
        number_sequence_service.cancel_document(
            document_number=self.angebotsnummer,
            cancelled_by=created_by,
            reason='Angebot storniert'
        )

        db.session.commit()
        return True

    def in_auftrag_umwandeln(self, created_by=None):
        """
        Wandelt das Angebot in einen Auftrag um

        Args:
            created_by: Benutzer der die Umwandlung durchführt

        Returns:
            Order: Der erstellte Auftrag
        """
        from src.models.models import Order, OrderItem

        if self.status != AngebotStatus.ANGENOMMEN:
            raise ValueError("Nur angenommene Angebote können in Aufträge umgewandelt werden")

        if self.auftrag_id:
            raise ValueError("Angebot wurde bereits in Auftrag umgewandelt")

        # Auftrag erstellen
        auftrag = Order(
            customer_id=self.kunde_id,
            description=self.beschreibung or self.titel,
            internal_notes=f"Erstellt aus Angebot {self.angebotsnummer}",
            customer_notes=self.bemerkungen,
            total_price=self.brutto_gesamt,
            discount_percent=self.rabatt_prozent,
            status='confirmed'
        )
        db.session.add(auftrag)
        db.session.flush()  # Um ID zu bekommen

        # Positionen übertragen
        for angebots_pos in self.positionen:
            auftrag_item = OrderItem(
                order_id=auftrag.id,
                article_id=angebots_pos.artikel_id,
                description=angebots_pos.beschreibung,
                quantity=angebots_pos.menge,
                unit_price=angebots_pos.einzelpreis,
                total_price=angebots_pos.brutto_betrag,
                notes=angebots_pos.bemerkungen
            )
            db.session.add(auftrag_item)

        # Angebot aktualisieren
        self.auftrag_id = auftrag.id
        self.in_auftrag_umgewandelt_am = datetime.utcnow()
        self.updated_by = created_by
        self.updated_at = datetime.utcnow()

        db.session.commit()

        return auftrag

    @classmethod
    def von_auftrag_erstellen(cls, auftrag, created_by=None, gueltig_tage=30):
        """
        Erstellt ein Angebot aus einem bestehenden Auftrag

        Der Auftrag dient als Kalkulationsgrundlage.
        Ideal für: "Erst kalkulieren, dann entscheiden ob Angebot oder direkt Produktion"

        Args:
            auftrag: Order-Objekt
            created_by: Benutzer
            gueltig_tage: Gültigkeit in Tagen (default: 30)

        Returns:
            Angebot: Das erstellte Angebot
        """
        from src.models.crm_activities import Activity, ActivityType, AngebotTracking

        # Angebot erstellen
        angebot = cls(
            kunde_id=auftrag.customer_id,
            kunde_name=auftrag.customer.display_name if auftrag.customer else '',
            kunde_adresse=f"{auftrag.customer.street}\n{auftrag.customer.postal_code} {auftrag.customer.city}" if auftrag.customer else '',
            kunde_email=auftrag.customer.email if auftrag.customer else '',
            titel=auftrag.description or f"Angebot für Auftrag {auftrag.order_number}",
            beschreibung=auftrag.description,
            bemerkungen=auftrag.internal_notes,
            gueltig_tage=gueltig_tage,
            erstellt_aus_auftrag_id=auftrag.id,
            created_by=created_by
        )

        # Preise aus Auftrag übernehmen
        angebot.netto_gesamt = auftrag.total_price or 0.0
        angebot.rabatt_prozent = auftrag.discount_percent or 0.0

        # Wenn Auftrag bereits Positionen hat, übernehmen
        # (wird noch erweitert wenn OrderItem-Details vorhanden sind)

        db.session.add(angebot)
        db.session.flush()  # Um ID zu bekommen

        # CRM-Tracking erstellen
        tracking = AngebotTracking(
            angebot_id=angebot.id,
            erwarteter_abschluss_datum=date.today() + timedelta(days=gueltig_tage)
        )
        db.session.add(tracking)

        # Aktivität erstellen
        Activity.create_activity(
            activity_type=ActivityType.NOTE,
            titel=f"Angebot {angebot.angebotsnummer} aus Auftrag {auftrag.order_number} erstellt",
            beschreibung=f"Angebot basiert auf Kalkulation von Auftrag {auftrag.order_number}",
            kunde_id=auftrag.customer_id,
            angebot_id=angebot.id,
            auftrag_id=auftrag.id,
            created_by=created_by
        )

        db.session.commit()

        return angebot

    def versenden_und_tracken(self, created_by=None, naechster_kontakt_tage=7):
        """
        Versendet Angebot und aktiviert Tracking

        Args:
            created_by: Benutzer
            naechster_kontakt_tage: Tage bis nächster Kontakt (default: 7)
        """
        from src.models.crm_activities import Activity, ActivityType, AngebotTracking

        # Status ändern
        self.status = AngebotStatus.VERSCHICKT
        self.updated_by = created_by
        self.updated_at = datetime.utcnow()

        # Tracking aktivieren (falls noch nicht vorhanden)
        if not hasattr(self, 'tracking') or not self.tracking:
            tracking = AngebotTracking(
                angebot_id=self.id,
                letzter_kontakt=date.today(),
                erwarteter_abschluss_datum=self.gueltig_bis
            )
            db.session.add(tracking)
        else:
            tracking = self.tracking
            tracking.letzter_kontakt = date.today()

        # Nächsten Kontakt planen
        tracking.naechsten_kontakt_planen(tage_bis_kontakt=naechster_kontakt_tage)

        # Aktivität erstellen
        Activity.create_activity(
            activity_type=ActivityType.ANGEBOT_VERSENDET,
            titel=f"Angebot {self.angebotsnummer} versendet",
            beschreibung=f"Angebot an {self.kunde_name} versendet. Gültig bis {self.gueltig_bis.strftime('%d.%m.%Y')}",
            kunde_id=self.kunde_id,
            angebot_id=self.id,
            created_by=created_by,
            follow_up_datum=tracking.naechster_kontakt_geplant
        )

        db.session.commit()

        return tracking

    def __repr__(self):
        return f'<Angebot {self.angebotsnummer}>'


class AngebotsPosition(db.Model):
    """Positionen eines Angebots"""
    __tablename__ = 'angebots_positionen'

    id = db.Column(db.Integer, primary_key=True)
    angebot_id = db.Column(db.Integer, db.ForeignKey('angebote.id'), nullable=False)

    # Position
    position = db.Column(db.Integer, nullable=False)  # Laufende Nummer

    # Artikel-Referenz (optional)
    artikel_id = db.Column(db.String(50), db.ForeignKey('articles.id'))

    # Beschreibung
    artikel_name = db.Column(db.String(200), nullable=False)
    beschreibung = db.Column(db.Text)
    bemerkungen = db.Column(db.Text)  # Interne Notizen

    # Menge und Preis
    menge = db.Column(db.Float, nullable=False, default=1)
    einheit = db.Column(db.String(20), default='Stück')
    einzelpreis = db.Column(db.Float, nullable=False)  # Netto-Einzelpreis

    # MwSt
    mwst_satz = db.Column(db.Float, default=19.0)

    # Rabatt (optional, zusätzlich zum Gesamt-Rabatt)
    rabatt_prozent = db.Column(db.Float, default=0.0)
    rabatt_betrag = db.Column(db.Float, default=0.0)

    # Berechnete Beträge
    netto_betrag = db.Column(db.Float)
    mwst_betrag = db.Column(db.Float)
    brutto_betrag = db.Column(db.Float)

    # Beziehungen
    angebot = db.relationship('Angebot', back_populates='positionen')
    artikel = db.relationship('Article', foreign_keys=[artikel_id])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.calculate_amounts()

    def calculate_amounts(self):
        """Berechnet die Beträge dieser Position"""
        menge = Decimal(str(self.menge or 1))
        einzelpreis = Decimal(str(self.einzelpreis or 0))
        mwst_satz = Decimal(str(self.mwst_satz or 19)) / Decimal('100')
        rabatt_prozent = Decimal(str(self.rabatt_prozent or 0)) / Decimal('100')

        # Netto-Gesamtpreis
        netto = menge * einzelpreis

        # Rabatt anwenden
        if rabatt_prozent > 0:
            rabatt = netto * rabatt_prozent
            self.rabatt_betrag = float(rabatt)
            netto -= rabatt

        # MwSt berechnen
        mwst = netto * mwst_satz

        # Brutto berechnen
        brutto = netto + mwst

        self.netto_betrag = float(netto)
        self.mwst_betrag = float(mwst)
        self.brutto_betrag = float(brutto)

    def __repr__(self):
        return f'<AngebotsPosition {self.position}: {self.artikel_name}>'
