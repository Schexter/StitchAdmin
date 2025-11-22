# -*- coding: utf-8 -*-
"""
Mahnwesen und Forderungsmanagement
===================================

Erstellt von: StitchAdmin
Zweck: Verwaltung von Mahnungen, Verzugszinsen und offenen Forderungen

Gesetzliche Grundlagen:
- §§ 280, 286, 288 BGB (Verzug, Verzugszinsen)
- Basiszinssatz nach § 247 BGB
- Mahngebührenverordnung (MahnGebV)
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from src.models import db
from src.models.nummernkreis import DocumentType, number_sequence_service


class MahnStatus:
    """Status-Optionen für Mahnungen"""
    ENTWURF = 'entwurf'              # Noch nicht versendet
    VERSENDET = 'versendet'          # An Kunde versendet
    BEZAHLT = 'bezahlt'              # Rechnung wurde bezahlt
    STORNIERT = 'storniert'          # Mahnung storniert
    INKASSO = 'inkasso'              # An Inkasso übergeben
    GERICHTLICH = 'gerichtlich'      # Gerichtliches Mahnverfahren


class Mahnung(db.Model):
    """Mahnungen für überfällige Rechnungen"""
    __tablename__ = 'mahnungen'

    id = db.Column(db.Integer, primary_key=True)

    # Identifikation
    mahnungsnummer = db.Column(db.String(50), unique=True, nullable=False, index=True)

    # Referenzen
    rechnung_id = db.Column(db.Integer, db.ForeignKey('rechnungen.id'), nullable=False)
    kunde_id = db.Column(db.String(50), db.ForeignKey('customers.id'), nullable=False)

    # Mahnstufe
    mahnstufe = db.Column(db.Integer, nullable=False)  # 1, 2, 3
    status = db.Column(db.String(20), default=MahnStatus.ENTWURF, index=True)

    # Daten
    mahndatum = db.Column(db.Date, nullable=False, default=date.today)
    versanddatum = db.Column(db.Date)
    zahlungsfrist = db.Column(db.Date, nullable=False)  # Neue Zahlungsfrist
    zahlungsfrist_tage = db.Column(db.Integer, default=7)  # Tage ab Mahnung

    # Beträge
    forderungsbetrag = db.Column(db.Float, nullable=False)  # Ursprüngliche Forderung
    offener_betrag = db.Column(db.Float, nullable=False)    # Noch offener Betrag
    mahngebuehr = db.Column(db.Float, default=0.0)          # Mahngebühren
    verzugszinsen = db.Column(db.Float, default=0.0)        # Verzugszinsen
    gesamtbetrag = db.Column(db.Float, nullable=False)      # Gesamt inkl. Gebühren

    # Zinsberechnung
    zinssatz_prozent = db.Column(db.Float)                  # Verwendeter Zinssatz
    zinsen_von_datum = db.Column(db.Date)                   # Zinsen ab diesem Datum
    zinsen_bis_datum = db.Column(db.Date)                   # Zinsen bis zu diesem Datum
    verzugstage = db.Column(db.Integer)                     # Tage im Verzug

    # Text
    mahntext = db.Column(db.Text)                           # Individueller Mahntext
    bemerkungen = db.Column(db.Text)                        # Interne Notizen

    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))

    # PDF
    pdf_erstellt_am = db.Column(db.DateTime)
    pdf_path = db.Column(db.String(500))

    # Beziehungen
    rechnung = db.relationship('Rechnung', backref='mahnungen')
    kunde = db.relationship('Customer', foreign_keys=[kunde_id], backref='mahnungen')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Mahnungsnummer generieren
        if not self.mahnungsnummer:
            self.mahnungsnummer = self._generate_mahnungsnummer()

        # Zahlungsfrist berechnen
        if not self.zahlungsfrist and self.mahndatum:
            self.zahlungsfrist = self.mahndatum + timedelta(days=self.zahlungsfrist_tage)

    def _generate_mahnungsnummer(self):
        """Generiert Mahnungsnummer basierend auf Rechnungsnummer und Mahnstufe"""
        if self.rechnung:
            base = self.rechnung.rechnungsnummer
            return f"{base}-M{self.mahnstufe}"
        else:
            # Fallback: Eigene Nummerierung
            return number_sequence_service.get_next_number(
                document_type='mahnung',
                created_by=self.created_by
            )

    def berechne_verzugszinsen(self, ist_geschaeftskunde=False):
        """
        Berechnet Verzugszinsen nach § 288 BGB

        Args:
            ist_geschaeftskunde: True wenn B2B, False wenn B2C

        Zinssätze:
        - Privatkunden: Basiszinssatz + 5 Prozentpunkte
        - Geschäftskunden: Basiszinssatz + 9 Prozentpunkte (bis 29.07.2014: 8%)

        Basiszinssatz 2024: -0,88% (Stand: Januar 2024)
        → Privat: 4,12%
        → Geschäftlich: 8,12%
        """
        # Basiszinssatz (sollte aus Einstellungen/Datenbank kommen)
        # Für 2024/2025 verwenden wir den aktuellen Wert
        basiszinssatz = Decimal('-0.88')  # Stand Januar 2024

        # Verzugszinssatz berechnen
        if ist_geschaeftskunde:
            zinssatz = basiszinssatz + Decimal('9.0')  # BGB § 288 Abs. 2
        else:
            zinssatz = basiszinssatz + Decimal('5.0')  # BGB § 288 Abs. 1

        self.zinssatz_prozent = float(zinssatz)

        # Verzugstage berechnen
        if not self.zinsen_von_datum:
            # Standard: 30 Tage nach Rechnungsdatum
            self.zinsen_von_datum = self.rechnung.faelligkeitsdatum

        if not self.zinsen_bis_datum:
            self.zinsen_bis_datum = date.today()

        verzugstage = (self.zinsen_bis_datum - self.zinsen_von_datum).days
        self.verzugstage = max(0, verzugstage)

        # Zinsen berechnen: Betrag × Zinssatz × Tage / (100 × 360)
        # Deutschland verwendet kaufmännische Zinsberechnung (360-Tage-Jahr)
        if self.verzugstage > 0:
            betrag = Decimal(str(self.offener_betrag))
            zinsen = (betrag * zinssatz * Decimal(str(self.verzugstage))) / (Decimal('100') * Decimal('360'))
            self.verzugszinsen = float(zinsen)
        else:
            self.verzugszinsen = 0.0

        return self.verzugszinsen

    def berechne_mahngebuehren(self):
        """
        Berechnet Mahngebühren nach üblichen Sätzen

        Übliche Staffelung:
        - 1. Mahnung: 0-5 EUR (oft kostenlos)
        - 2. Mahnung: 5-10 EUR
        - 3. Mahnung: 10-15 EUR
        """
        gebuehren_staffel = {
            1: Decimal('0.00'),    # 1. Mahnung oft kostenlos
            2: Decimal('5.00'),    # 2. Mahnung
            3: Decimal('10.00'),   # 3. Mahnung
        }

        # Aus Einstellungen laden (später implementieren)
        from src.models.company_settings import CompanySettings
        try:
            settings = CompanySettings.get_settings()
            # TODO: Mahngebühren in CompanySettings hinzufügen
            # Für jetzt verwenden wir die Standard-Staffelung
        except:
            pass

        gebuehr = gebuehren_staffel.get(self.mahnstufe, Decimal('15.00'))
        self.mahngebuehr = float(gebuehr)

        return self.mahngebuehr

    def berechne_gesamtbetrag(self):
        """Berechnet den Gesamtbetrag inkl. Gebühren und Zinsen"""
        gesamt = Decimal(str(self.offener_betrag))
        gesamt += Decimal(str(self.mahngebuehr or 0))
        gesamt += Decimal(str(self.verzugszinsen or 0))

        self.gesamtbetrag = float(gesamt)
        return self.gesamtbetrag

    def versenden(self, created_by=None):
        """
        Markiert Mahnung als versendet

        Args:
            created_by: Benutzer
        """
        self.status = MahnStatus.VERSENDET
        self.versanddatum = date.today()
        self.updated_by = created_by
        self.updated_at = datetime.utcnow()
        db.session.commit()

    def bezahlt_markieren(self, created_by=None):
        """
        Markiert Mahnung als bezahlt

        Args:
            created_by: Benutzer
        """
        self.status = MahnStatus.BEZAHLT
        self.updated_by = created_by
        self.updated_at = datetime.utcnow()
        db.session.commit()

    @classmethod
    def erstelle_mahnung(cls, rechnung, mahnstufe=1, ist_geschaeftskunde=False, created_by=None):
        """
        Erstellt eine neue Mahnung für eine überfällige Rechnung

        Args:
            rechnung: Rechnung-Objekt
            mahnstufe: Mahnstufe (1, 2, 3)
            ist_geschaeftskunde: True wenn B2B
            created_by: Benutzer

        Returns:
            Mahnung: Die erstellte Mahnung
        """
        # Prüfe ob Rechnung überfällig ist
        if rechnung.faelligkeitsdatum >= date.today():
            raise ValueError("Rechnung ist noch nicht überfällig")

        # Prüfe offenen Betrag
        offener_betrag = rechnung.offener_betrag
        if offener_betrag <= 0:
            raise ValueError("Rechnung ist bereits vollständig bezahlt")

        # Mahnung erstellen
        mahnung = cls(
            rechnung_id=rechnung.id,
            kunde_id=rechnung.kunde_id,
            mahnstufe=mahnstufe,
            forderungsbetrag=rechnung.brutto_gesamt,
            offener_betrag=offener_betrag,
            created_by=created_by
        )

        # Gebühren berechnen
        mahnung.berechne_mahngebuehren()
        mahnung.berechne_verzugszinsen(ist_geschaeftskunde)
        mahnung.berechne_gesamtbetrag()

        # Standard-Mahntext
        mahnung.mahntext = mahnung._generiere_mahntext()

        db.session.add(mahnung)
        db.session.commit()

        return mahnung

    def _generiere_mahntext(self):
        """Generiert Standard-Mahntext je nach Mahnstufe"""
        from src.models.company_settings import CompanySettings

        try:
            settings = CompanySettings.get_settings()
            firmenname = settings.display_name
        except:
            firmenname = "Unsere Firma"

        texte = {
            1: f"""Sehr geehrte Damen und Herren,

unsere Rechnung {self.rechnung.rechnungsnummer} vom {self.rechnung.rechnungsdatum.strftime('%d.%m.%Y')}
über {self.forderungsbetrag:.2f} EUR ist bis heute noch nicht bei uns eingegangen.

Möglicherweise haben Sie die Zahlung übersehen. Wir bitten Sie daher, den ausstehenden Betrag
bis zum {self.zahlungsfrist.strftime('%d.%m.%Y')} auf unser Konto zu überweisen.

Falls Sie bereits gezahlt haben, betrachten Sie dieses Schreiben bitte als gegenstandslos.

Mit freundlichen Grüßen
{firmenname}""",

            2: f"""Sehr geehrte Damen und Herren,

trotz unserer Zahlungserinnerung vom {self._get_vorherige_mahnung_datum()} haben wir die Zahlung
für Rechnung {self.rechnung.rechnungsnummer} noch nicht erhalten.

Offener Betrag: {self.offener_betrag:.2f} EUR
Mahngebühren: {self.mahngebuehr:.2f} EUR
Gesamtbetrag: {self.gesamtbetrag:.2f} EUR

Wir bitten Sie dringend, den Gesamtbetrag bis zum {self.zahlungsfrist.strftime('%d.%m.%Y')} zu begleichen.

Falls Sie bereits gezahlt haben, betrachten Sie dieses Schreiben bitte als gegenstandslos.

Mit freundlichen Grüßen
{firmenname}""",

            3: f"""Sehr geehrte Damen und Herren,

trotz mehrfacher Zahlungserinnerungen ist die Zahlung für Rechnung {self.rechnung.rechnungsnummer}
weiterhin ausgeblieben.

Offener Betrag: {self.offener_betrag:.2f} EUR
Mahngebühren: {self.mahngebuehr:.2f} EUR
Verzugszinsen ({self.zinssatz_prozent:.2f}%): {self.verzugszinsen:.2f} EUR
Gesamtbetrag: {self.gesamtbetrag:.2f} EUR

Dies ist unsere LETZTE MAHNUNG. Sollte der Gesamtbetrag nicht bis zum {self.zahlungsfrist.strftime('%d.%m.%Y')}
eingehen, sehen wir uns gezwungen, ein gerichtliches Mahnverfahren einzuleiten und/oder die Forderung
an ein Inkassounternehmen abzugeben. Die hierdurch entstehenden Kosten gehen zu Ihren Lasten.

Sollten Sie Probleme mit der Zahlung haben, nehmen Sie bitte umgehend Kontakt mit uns auf,
um eine Ratenzahlung zu vereinbaren.

Mit freundlichen Grüßen
{firmenname}"""
        }

        return texte.get(self.mahnstufe, texte[1])

    def _get_vorherige_mahnung_datum(self):
        """Holt das Datum der vorherigen Mahnung"""
        vorherige = Mahnung.query.filter_by(
            rechnung_id=self.rechnung_id,
            mahnstufe=self.mahnstufe - 1
        ).first()

        if vorherige and vorherige.versanddatum:
            return vorherige.versanddatum.strftime('%d.%m.%Y')
        return "unbekannt"

    def __repr__(self):
        return f'<Mahnung {self.mahnungsnummer} (Stufe {self.mahnstufe})>'


class Ratenzahlung(db.Model):
    """Ratenzahlungsvereinbarungen"""
    __tablename__ = 'ratenzahlungen'

    id = db.Column(db.Integer, primary_key=True)

    # Referenzen
    rechnung_id = db.Column(db.Integer, db.ForeignKey('rechnungen.id'), nullable=False)
    kunde_id = db.Column(db.String(50), db.ForeignKey('customers.id'), nullable=False)

    # Vereinbarung
    vereinbarungsnummer = db.Column(db.String(50), unique=True, nullable=False)
    vereinbarungsdatum = db.Column(db.Date, nullable=False, default=date.today)

    # Beträge
    gesamtbetrag = db.Column(db.Float, nullable=False)      # Gesamtschuld
    anzahl_raten = db.Column(db.Integer, nullable=False)     # Anzahl der Raten
    ratenbetrag = db.Column(db.Float, nullable=False)        # Betrag pro Rate
    erste_rate_datum = db.Column(db.Date, nullable=False)    # Datum der ersten Rate
    raten_intervall_tage = db.Column(db.Integer, default=30) # Tage zwischen Raten (meist 30)

    # Zinsen (optional)
    zinssatz_prozent = db.Column(db.Float, default=0.0)

    # Status
    status = db.Column(db.String(20), default='aktiv')  # aktiv, abgeschlossen, gekündigt
    bezahlt_betrag = db.Column(db.Float, default=0.0)

    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))

    # Beziehungen
    rechnung = db.relationship('Rechnung', backref='ratenzahlungen')
    kunde = db.relationship('Customer', foreign_keys=[kunde_id], backref='ratenzahlungen')
    raten = db.relationship('Rate', back_populates='ratenzahlung',
                           cascade='all, delete-orphan', order_by='Rate.faelligkeitsdatum')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Vereinbarungsnummer generieren
        if not self.vereinbarungsnummer:
            self.vereinbarungsnummer = self._generate_vereinbarungsnummer()

    def _generate_vereinbarungsnummer(self):
        """Generiert Vereinbarungsnummer"""
        if self.rechnung:
            return f"{self.rechnung.rechnungsnummer}-RZ"
        return number_sequence_service.get_next_number(
            document_type='ratenzahlung',
            created_by=self.created_by
        )

    def erstelle_raten(self):
        """Erstellt die einzelnen Raten"""
        # Lösche bestehende Raten
        for rate in self.raten:
            db.session.delete(rate)

        # Neue Raten erstellen
        aktuelles_datum = self.erste_rate_datum

        for i in range(1, self.anzahl_raten + 1):
            # Letzte Rate könnte anders sein (wegen Rundung)
            if i == self.anzahl_raten:
                betrag = self.gesamtbetrag - (self.ratenbetrag * (self.anzahl_raten - 1))
            else:
                betrag = self.ratenbetrag

            rate = Rate(
                ratenzahlung_id=self.id,
                ratennummer=i,
                betrag=betrag,
                faelligkeitsdatum=aktuelles_datum,
                status='offen'
            )
            db.session.add(rate)

            # Nächstes Datum
            aktuelles_datum = aktuelles_datum + timedelta(days=self.raten_intervall_tage)

        db.session.commit()

    @property
    def naechste_faellige_rate(self):
        """Gibt die nächste fällige Rate zurück"""
        return Rate.query.filter_by(
            ratenzahlung_id=self.id,
            status='offen'
        ).order_by(Rate.faelligkeitsdatum).first()

    @property
    def offener_betrag(self):
        """Berechnet den noch offenen Betrag"""
        return self.gesamtbetrag - self.bezahlt_betrag

    def __repr__(self):
        return f'<Ratenzahlung {self.vereinbarungsnummer}>'


class Rate(db.Model):
    """Einzelne Rate einer Ratenzahlung"""
    __tablename__ = 'raten'

    id = db.Column(db.Integer, primary_key=True)
    ratenzahlung_id = db.Column(db.Integer, db.ForeignKey('ratenzahlungen.id'), nullable=False)

    # Rate
    ratennummer = db.Column(db.Integer, nullable=False)  # 1, 2, 3, ...
    betrag = db.Column(db.Float, nullable=False)
    faelligkeitsdatum = db.Column(db.Date, nullable=False)

    # Status
    status = db.Column(db.String(20), default='offen')  # offen, bezahlt, überfällig
    bezahlt_datum = db.Column(db.Date)
    bezahlt_betrag = db.Column(db.Float, default=0.0)

    # Beziehungen
    ratenzahlung = db.relationship('Ratenzahlung', back_populates='raten')

    @property
    def ist_ueberfaellig(self):
        """Prüft ob Rate überfällig ist"""
        return self.status == 'offen' and self.faelligkeitsdatum < date.today()

    def bezahlen(self, betrag, created_by=None):
        """
        Markiert Rate als bezahlt

        Args:
            betrag: Bezahlter Betrag
            created_by: Benutzer
        """
        self.status = 'bezahlt'
        self.bezahlt_datum = date.today()
        self.bezahlt_betrag = betrag

        # Aktualisiere Ratenzahlung
        self.ratenzahlung.bezahlt_betrag += betrag

        # Prüfe ob alle Raten bezahlt sind
        alle_bezahlt = all(r.status == 'bezahlt' for r in self.ratenzahlung.raten)
        if alle_bezahlt:
            self.ratenzahlung.status = 'abgeschlossen'

        db.session.commit()

    def __repr__(self):
        return f'<Rate {self.ratennummer} von {self.ratenzahlung.vereinbarungsnummer}>'
