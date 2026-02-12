# -*- coding: utf-8 -*-
"""
DOKUMENT-WORKFLOW MODELS
========================
Datenmodelle für die vollständige Belegkette:
- Nummernkreise (GoBD-konform)
- Geschäftsdokumente (Angebot, AB, Lieferschein, Rechnung)
- Dokumentpositionen
- Zahlungen & Anzahlungen
- Zahlungsbedingungen

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Date, Boolean, Text,
    ForeignKey, JSON, Numeric, UniqueConstraint, Index, event
)
from sqlalchemy.orm import relationship
from src.models import db

# ============================================================================
# ENUMS
# ============================================================================

class DokumentTyp(Enum):
    """Dokumenttypen im Workflow"""
    ANGEBOT = "angebot"
    AUFTRAGSBESTAETIGUNG = "auftragsbestaetigung"
    LIEFERSCHEIN = "lieferschein"
    RECHNUNG = "rechnung"
    ANZAHLUNG = "anzahlung"
    TEILRECHNUNG = "teilrechnung"
    SCHLUSSRECHNUNG = "schlussrechnung"
    GUTSCHRIFT = "gutschrift"
    

class DokumentStatus(Enum):
    """Status eines Dokuments"""
    ENTWURF = "entwurf"
    VERSENDET = "versendet"
    ANGENOMMEN = "angenommen"          # Für Angebote
    ABGELEHNT = "abgelehnt"            # Für Angebote
    VERFALLEN = "verfallen"            # Für Angebote
    IN_BEARBEITUNG = "in_bearbeitung"  # Für AB/Aufträge
    TEILGELIEFERT = "teilgeliefert"    # Für Lieferscheine
    GELIEFERT = "geliefert"            # Für Lieferscheine
    OFFEN = "offen"                    # Für Rechnungen
    TEILBEZAHLT = "teilbezahlt"        # Für Rechnungen
    BEZAHLT = "bezahlt"                # Für Rechnungen
    UEBERFAELLIG = "ueberfaellig"      # Für Rechnungen
    GEMAHNT = "gemahnt"                # Für Rechnungen
    STORNIERT = "storniert"


class PositionsTyp(Enum):
    """Typ einer Dokumentposition"""
    ARTIKEL = "artikel"
    TEXTIL = "textil"
    VEREDELUNG_STICKEREI = "veredelung_stickerei"
    VEREDELUNG_DRUCK = "veredelung_druck"
    EINRICHTUNG = "einrichtung"
    DIENSTLEISTUNG = "dienstleistung"
    VERSAND = "versand"
    RABATT = "rabatt"
    ANZAHLUNG_ABZUG = "anzahlung_abzug"
    ZWISCHENSUMME = "zwischensumme"
    TEXT = "text"  # Nur Text, keine Berechnung


class MwStKennzeichen(Enum):
    """MwSt-Kennzeichen"""
    STANDARD = "S"      # 19%
    ERMAESSIGT = "E"    # 7%
    FREI = "F"          # 0%
    INNERGEMEINSCHAFTLICH = "I"  # 0% (EU)
    DRITTLAND = "D"     # 0% (Export)


# ============================================================================
# NUMMERNKREISE
# ============================================================================

class Nummernkreis(db.Model):
    """
    Verwaltung der Belegnummern (GoBD-konform)
    
    Regeln:
    - Fortlaufend & lückenlos innerhalb eines Jahres
    - Keine Wiederverwendung von Nummern
    - Jahreswechsel: Optional Reset auf 0001
    - Thread-safe durch DB-Lock
    """
    __tablename__ = 'nummernkreise'
    
    id = Column(Integer, primary_key=True)
    
    # Identifikation
    belegart = Column(String(30), unique=True, nullable=False)
    # z.B. 'angebot', 'rechnung', 'lieferschein', 'anzahlung', 'gutschrift', 'kassenbeleg'
    
    bezeichnung = Column(String(100))  # z.B. "Angebote", "Rechnungen"
    
    # Nummernformat
    praefix = Column(String(10), nullable=False)  # z.B. 'AN', 'RE', 'LS'
    aktuelles_jahr = Column(Integer, nullable=False)
    aktuelle_nummer = Column(Integer, default=0)
    
    # Formatierung
    stellen = Column(Integer, default=4)  # Anzahl Stellen: 0001 vs 000001
    trennzeichen = Column(String(5), default='-')  # AN-2025-0001
    jahr_format = Column(String(10), default='YYYY')  # YYYY oder YY
    
    # Optionen
    jahreswechsel_reset = Column(Boolean, default=True)  # Bei Jahreswechsel auf 1 zurück
    aktiv = Column(Boolean, default=True)
    
    # Tracking
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    geaendert_am = Column(DateTime, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Nummernkreis {self.belegart}: {self.praefix}-{self.aktuelles_jahr}-{self.aktuelle_nummer}>"
    
    def naechste_nummer(self):
        """
        Generiert die nächste Belegnummer (Thread-safe)
        
        Returns:
            str: Formatierte Belegnummer, z.B. "AN-2025-0001"
        """
        aktuelles_jahr = datetime.now().year
        
        # Jahreswechsel prüfen
        if self.jahreswechsel_reset and self.aktuelles_jahr != aktuelles_jahr:
            self.aktuelles_jahr = aktuelles_jahr
            self.aktuelle_nummer = 0
        
        # Nummer erhöhen
        self.aktuelle_nummer += 1
        
        # Format zusammenbauen
        if self.jahr_format == 'YY':
            jahr_str = str(self.aktuelles_jahr)[-2:]
        else:
            jahr_str = str(self.aktuelles_jahr)
        
        nummer_str = str(self.aktuelle_nummer).zfill(self.stellen)
        
        return f"{self.praefix}{self.trennzeichen}{jahr_str}{self.trennzeichen}{nummer_str}"
    
    def vorschau_naechste(self):
        """Zeigt Vorschau der nächsten Nummer ohne zu inkrementieren"""
        aktuelles_jahr = datetime.now().year
        
        if self.jahreswechsel_reset and self.aktuelles_jahr != aktuelles_jahr:
            jahr = aktuelles_jahr
            nummer = 1
        else:
            jahr = self.aktuelles_jahr
            nummer = self.aktuelle_nummer + 1
        
        if self.jahr_format == 'YY':
            jahr_str = str(jahr)[-2:]
        else:
            jahr_str = str(jahr)
        
        nummer_str = str(nummer).zfill(self.stellen)
        
        return f"{self.praefix}{self.trennzeichen}{jahr_str}{self.trennzeichen}{nummer_str}"
    
    @classmethod
    def hole_naechste_nummer(cls, belegart):
        """
        Holt die nächste Nummer für eine Belegart (Thread-safe)
        
        Args:
            belegart: z.B. 'angebot', 'rechnung'
            
        Returns:
            str: Formatierte Belegnummer
        """
        # Mit Row-Lock für Thread-Safety
        nk = cls.query.filter_by(belegart=belegart, aktiv=True).with_for_update().first()
        
        if not nk:
            raise ValueError(f"Kein aktiver Nummernkreis für '{belegart}' gefunden")
        
        nummer = nk.naechste_nummer()
        db.session.commit()
        
        return nummer


# ============================================================================
# ZAHLUNGSBEDINGUNGEN
# ============================================================================

class Zahlungsbedingung(db.Model):
    """
    Vordefinierte Zahlungsbedingungen
    
    Beispiele:
    - "14 Tage netto"
    - "30 Tage mit 2% Skonto bei Zahlung innerhalb 7 Tagen"
    - "50% Anzahlung, Rest bei Lieferung"
    """
    __tablename__ = 'zahlungsbedingungen'
    
    id = Column(Integer, primary_key=True)
    
    bezeichnung = Column(String(100), nullable=False)
    # z.B. "14 Tage netto", "50% Anzahlung"
    
    kurztext = Column(String(50))
    # z.B. "14T", "50%AZ"
    
    # Zahlungsziel
    zahlungsziel_tage = Column(Integer, default=14)
    
    # Skonto
    skonto_prozent = Column(Numeric(5, 2), default=0)
    skonto_tage = Column(Integer, default=0)
    
    # Anzahlung
    anzahlung_erforderlich = Column(Boolean, default=False)
    anzahlung_prozent = Column(Numeric(5, 2), default=0)  # z.B. 50.00
    anzahlung_festbetrag = Column(Numeric(12, 2), default=0)  # Alternativ: Fester Betrag
    anzahlung_text = Column(String(200))
    # z.B. "50% bei Auftragserteilung, Rest bei Lieferung"
    
    # Text für Dokumente
    text_rechnung = Column(Text)
    # z.B. "Zahlbar innerhalb von 14 Tagen ohne Abzug."
    
    text_rechnung_skonto = Column(Text)
    # z.B. "Bei Zahlung innerhalb von 7 Tagen gewähren wir 2% Skonto."
    
    # Status
    aktiv = Column(Boolean, default=True)
    standard = Column(Boolean, default=False)  # Default für neue Kunden
    sortierung = Column(Integer, default=0)
    
    # Tracking
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    geaendert_am = Column(DateTime, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Zahlungsbedingung {self.bezeichnung}>"
    
    def berechne_faelligkeit(self, rechnungsdatum=None):
        """Berechnet das Fälligkeitsdatum"""
        if rechnungsdatum is None:
            rechnungsdatum = date.today()
        from datetime import timedelta
        return rechnungsdatum + timedelta(days=self.zahlungsziel_tage)
    
    def berechne_skonto_datum(self, rechnungsdatum=None):
        """Berechnet das Skonto-Datum"""
        if self.skonto_tage <= 0:
            return None
        if rechnungsdatum is None:
            rechnungsdatum = date.today()
        from datetime import timedelta
        return rechnungsdatum + timedelta(days=self.skonto_tage)
    
    def berechne_anzahlung(self, brutto_summe):
        """Berechnet den Anzahlungsbetrag"""
        if not self.anzahlung_erforderlich:
            return Decimal('0.00')
        
        if self.anzahlung_festbetrag > 0:
            return min(self.anzahlung_festbetrag, brutto_summe)
        
        if self.anzahlung_prozent > 0:
            return (brutto_summe * self.anzahlung_prozent / 100).quantize(Decimal('0.01'))
        
        return Decimal('0.00')
    
    def generiere_zahlungstext(self):
        """Generiert den kompletten Zahlungstext für Rechnungen"""
        texte = []
        
        if self.text_rechnung:
            texte.append(self.text_rechnung)
        else:
            texte.append(f"Zahlbar innerhalb von {self.zahlungsziel_tage} Tagen ohne Abzug.")
        
        if self.skonto_prozent > 0 and self.skonto_tage > 0:
            if self.text_rechnung_skonto:
                texte.append(self.text_rechnung_skonto)
            else:
                texte.append(
                    f"Bei Zahlung innerhalb von {self.skonto_tage} Tagen "
                    f"gewähren wir {self.skonto_prozent}% Skonto."
                )
        
        return " ".join(texte)


# ============================================================================
# GESCHÄFTSDOKUMENTE
# ============================================================================

class BusinessDocument(db.Model):
    """
    Einheitliches Model für alle Geschäftsdokumente:
    - Angebote
    - Auftragsbestätigungen
    - Lieferscheine
    - Rechnungen (inkl. Anzahlung, Teil-, Schlussrechnung)
    - Gutschriften
    """
    __tablename__ = 'business_documents'
    
    id = Column(Integer, primary_key=True)
    
    # ─── IDENTIFIKATION ───────────────────────────────────────────────────
    dokument_nummer = Column(String(50), unique=True, nullable=False, index=True)
    dokument_typ = Column(String(30), nullable=False, index=True)
    # Werte aus DokumentTyp Enum
    
    # ─── VERKETTUNG ───────────────────────────────────────────────────────
    # Vorgänger-Dokument (z.B. Angebot → AB)
    vorgaenger_id = Column(Integer, ForeignKey('business_documents.id'))
    vorgaenger = relationship('BusinessDocument', remote_side=[id],
                             backref='nachfolger', foreign_keys=[vorgaenger_id])
    
    # Verknüpfung zum internen Auftrag
    auftrag_id = Column(String(50), ForeignKey('orders.id'), index=True)
    auftrag = relationship('Order', backref='dokumente')
    
    # Bei Schlussrechnung: Verweis auf Anzahlungsrechnungen
    # (wird über nachfolger/vorgaenger abgebildet)
    
    # ─── KUNDE ────────────────────────────────────────────────────────────
    kunde_id = Column(String(50), ForeignKey('customers.id'), nullable=False, index=True)
    kunde = relationship('Customer', backref='business_documents')
    
    # Adressen-Snapshot (zum Zeitpunkt der Erstellung, für Archivierung)
    rechnungsadresse = Column(JSON)
    lieferadresse = Column(JSON)  # Falls abweichend
    
    # Ansprechpartner
    ansprechpartner = Column(String(200))
    
    # ─── DATUM ────────────────────────────────────────────────────────────
    dokument_datum = Column(Date, default=date.today, nullable=False)
    gueltig_bis = Column(Date)  # Für Angebote (Gültigkeitsdauer)
    lieferdatum = Column(Date)  # Für Lieferscheine
    leistungsdatum = Column(Date)  # Für Rechnungen (Leistungszeitraum)
    leistungszeitraum_bis = Column(Date)  # Ende Leistungszeitraum
    faelligkeitsdatum = Column(Date)  # Für Rechnungen
    
    # ─── BETRÄGE ──────────────────────────────────────────────────────────
    summe_netto = Column(Numeric(12, 2), default=0)
    summe_mwst = Column(Numeric(12, 2), default=0)
    summe_brutto = Column(Numeric(12, 2), default=0)
    
    # Rabatte
    rabatt_prozent = Column(Numeric(5, 2), default=0)
    rabatt_betrag = Column(Numeric(12, 2), default=0)
    
    # Anzahlungen (für Schlussrechnungen)
    bereits_gezahlt = Column(Numeric(12, 2), default=0)  # Summe aller Anzahlungen
    restbetrag = Column(Numeric(12, 2), default=0)  # Noch zu zahlen
    
    # ─── STATUS ───────────────────────────────────────────────────────────
    status = Column(String(30), default=DokumentStatus.ENTWURF.value, index=True)
    # Werte aus DokumentStatus Enum
    
    # ─── TEXTE ────────────────────────────────────────────────────────────
    betreff = Column(String(500))
    einleitung = Column(Text)
    schlussbemerkung = Column(Text)
    interne_notiz = Column(Text)  # Nicht auf Dokument sichtbar
    
    # Referenz/Bestellnummer des Kunden
    kunden_referenz = Column(String(200))
    kunden_bestellnummer = Column(String(100))
    
    # ─── ZAHLUNGSBEDINGUNGEN ──────────────────────────────────────────────
    zahlungsbedingung_id = Column(Integer, ForeignKey('zahlungsbedingungen.id'))
    zahlungsbedingung = relationship('Zahlungsbedingung')
    
    zahlungsziel_tage = Column(Integer, default=14)
    skonto_prozent = Column(Numeric(5, 2), default=0)
    skonto_tage = Column(Integer, default=0)
    skonto_betrag = Column(Numeric(12, 2), default=0)  # Berechneter Skonto-Abzug
    
    zahlungstext = Column(Text)  # Generierter oder manueller Text
    
    # ─── VERSAND ──────────────────────────────────────────────────────────
    versandart = Column(String(50))  # 'abholung', 'versand', 'spedition'
    versandkosten = Column(Numeric(10, 2), default=0)
    tracking_nummer = Column(String(100))
    
    # ─── PDF & ARCHIVIERUNG ───────────────────────────────────────────────
    pdf_pfad = Column(String(500))
    pdf_erstellt_am = Column(DateTime)
    pdf_hash = Column(String(64))  # SHA256 für Integrität
    
    # ─── TRACKING ─────────────────────────────────────────────────────────
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    erstellt_von = Column(String(100))
    geaendert_am = Column(DateTime, onupdate=datetime.utcnow)
    geaendert_von = Column(String(100))
    
    versendet_am = Column(DateTime)
    versendet_per = Column(String(50))  # 'email', 'post', 'fax', 'abholung'
    versendet_an = Column(String(200))  # E-Mail-Adresse oder Beschreibung
    
    # Für Angebote
    angenommen_am = Column(DateTime)
    abgelehnt_am = Column(DateTime)
    ablehnungsgrund = Column(Text)
    
    # Für Rechnungen
    bezahlt_am = Column(Date)
    letzte_mahnung_am = Column(Date)
    mahnstufe = Column(Integer, default=0)
    
    # ─── RELATIONSHIPS ────────────────────────────────────────────────────
    positionen = relationship('DocumentPosition', back_populates='dokument',
                             cascade='all, delete-orphan',
                             order_by='DocumentPosition.position',
                             foreign_keys='DocumentPosition.dokument_id')
    
    zahlungen = relationship('DocumentPayment', back_populates='dokument',
                            cascade='all, delete-orphan',
                            order_by='DocumentPayment.zahlung_datum',
                            foreign_keys='DocumentPayment.dokument_id')
    
    # ─── INDEXES ──────────────────────────────────────────────────────────
    __table_args__ = (
        Index('idx_doc_kunde_typ', 'kunde_id', 'dokument_typ'),
        Index('idx_doc_datum', 'dokument_datum'),
        Index('idx_doc_status', 'status'),
    )
    
    def __repr__(self):
        return f"<BusinessDocument {self.dokument_nummer} ({self.dokument_typ})>"
    
    # ─── BERECHNUNGSMETHODEN ──────────────────────────────────────────────
    
    def berechne_summen(self):
        """Berechnet alle Summen aus den Positionen"""
        self.summe_netto = Decimal('0.00')
        self.summe_mwst = Decimal('0.00')
        
        for pos in self.positionen:
            if pos.typ not in [PositionsTyp.TEXT.value, PositionsTyp.ZWISCHENSUMME.value]:
                self.summe_netto += pos.netto_gesamt or Decimal('0.00')
                self.summe_mwst += pos.mwst_betrag or Decimal('0.00')
        
        # Gesamtrabatt anwenden
        if self.rabatt_prozent > 0:
            self.rabatt_betrag = (self.summe_netto * self.rabatt_prozent / 100).quantize(Decimal('0.01'))
            self.summe_netto -= self.rabatt_betrag
            # MwSt auf reduzierten Netto-Betrag neu berechnen
            # (vereinfacht - bei gemischten MwSt-Sätzen komplexer)
        
        self.summe_brutto = self.summe_netto + self.summe_mwst
        
        # Restbetrag (für Schlussrechnungen)
        self.restbetrag = self.summe_brutto - self.bereits_gezahlt
        
        # Skonto berechnen
        if self.skonto_prozent > 0:
            self.skonto_betrag = (self.summe_brutto * self.skonto_prozent / 100).quantize(Decimal('0.01'))
    
    def ist_ueberfaellig(self):
        """Prüft ob das Dokument überfällig ist (für Rechnungen)"""
        if self.dokument_typ not in [DokumentTyp.RECHNUNG.value, 
                                      DokumentTyp.ANZAHLUNG.value,
                                      DokumentTyp.TEILRECHNUNG.value]:
            return False
        
        if self.status in [DokumentStatus.BEZAHLT.value, DokumentStatus.STORNIERT.value]:
            return False
        
        if not self.faelligkeitsdatum:
            return False
        
        return date.today() > self.faelligkeitsdatum
    
    def tage_ueberfaellig(self):
        """Anzahl Tage überfällig"""
        if not self.ist_ueberfaellig():
            return 0
        return (date.today() - self.faelligkeitsdatum).days
    
    def offener_betrag(self):
        """Berechnet den noch offenen Betrag"""
        if not self.zahlungen:
            return self.restbetrag or self.summe_brutto
        
        gezahlt = sum(
            z.betrag for z in self.zahlungen 
            if z.bestaetigt and z.zahlungsart != 'anzahlung_verrechnung'
        )
        return (self.summe_brutto or Decimal('0.00')) - gezahlt - (self.bereits_gezahlt or Decimal('0.00'))
    
    def ist_vollstaendig_bezahlt(self):
        """Prüft ob vollständig bezahlt"""
        return self.offener_betrag() <= Decimal('0.01')  # Toleranz für Rundung
    
    # ─── STATUS-METHODEN ──────────────────────────────────────────────────
    
    def kann_bearbeitet_werden(self):
        """Prüft ob das Dokument noch bearbeitet werden kann"""
        return self.status == DokumentStatus.ENTWURF.value
    
    def kann_versendet_werden(self):
        """Prüft ob das Dokument versendet werden kann"""
        return self.status == DokumentStatus.ENTWURF.value and len(self.positionen) > 0
    
    def kann_storniert_werden(self):
        """Prüft ob das Dokument storniert werden kann"""
        # Bereits bezahlte Rechnungen können nicht direkt storniert werden
        if self.dokument_typ in [DokumentTyp.RECHNUNG.value] and self.status == DokumentStatus.BEZAHLT.value:
            return False  # Stattdessen Gutschrift erstellen
        return self.status != DokumentStatus.STORNIERT.value
    
    # ─── KONVERTIERUNGSMETHODEN ───────────────────────────────────────────
    
    def zu_auftragsbestaetigung(self):
        """Konvertiert Angebot zu Auftragsbestätigung"""
        if self.dokument_typ != DokumentTyp.ANGEBOT.value:
            raise ValueError("Nur Angebote können in AB umgewandelt werden")
        
        # Neues Dokument erstellen (wird im Controller gemacht)
        return {
            'dokument_typ': DokumentTyp.AUFTRAGSBESTAETIGUNG.value,
            'vorgaenger_id': self.id,
            'kunde_id': self.kunde_id,
            'positionen': self.positionen,
            # ... weitere Felder
        }
    
    def erstelle_anzahlungsrechnung(self, prozent=None, betrag=None):
        """Erstellt Anzahlungsrechnung aus AB"""
        if self.dokument_typ != DokumentTyp.AUFTRAGSBESTAETIGUNG.value:
            raise ValueError("Anzahlungsrechnungen nur aus AB möglich")
        
        if betrag is None and prozent is not None:
            betrag = (self.summe_brutto * Decimal(str(prozent)) / 100).quantize(Decimal('0.01'))
        
        return {
            'dokument_typ': DokumentTyp.ANZAHLUNG.value,
            'vorgaenger_id': self.id,
            'kunde_id': self.kunde_id,
            'summe_brutto': betrag,
            # ... weitere Felder
        }


# ============================================================================
# DOKUMENTPOSITIONEN
# ============================================================================

class DocumentPosition(db.Model):
    """
    Positionen auf Geschäftsdokumenten
    
    Unterstützt verschiedene Positionstypen:
    - Artikel/Textilien
    - Veredelung (Stickerei, Druck)
    - Einrichtungspauschalen
    - Versand
    - Rabatte
    - Anzahlungsabzüge
    """
    __tablename__ = 'document_positions'
    
    id = Column(Integer, primary_key=True)
    
    dokument_id = Column(Integer, ForeignKey('business_documents.id'), nullable=False)
    dokument = relationship('BusinessDocument', back_populates='positionen',
                           foreign_keys=[dokument_id])
    
    position = Column(Integer, nullable=False)  # Sortierung (1, 2, 3...)
    
    # ─── POSITIONSTYP ─────────────────────────────────────────────────────
    typ = Column(String(30), default=PositionsTyp.ARTIKEL.value)
    # Werte aus PositionsTyp Enum
    
    # ─── REFERENZEN ───────────────────────────────────────────────────────
    artikel_id = Column(Integer, ForeignKey('articles.id'))
    artikel = relationship('Article')
    
    # Referenz zum Auftragsposten (für Nachverfolgung)
    order_item_id = Column(Integer)  # Ohne FK, da order_items anders strukturiert sein könnte
    
    # Bei Anzahlungsabzug: Verweis auf Anzahlungsrechnung
    anzahlung_dokument_id = Column(Integer, ForeignKey('business_documents.id'))
    
    # ─── BESCHREIBUNG ─────────────────────────────────────────────────────
    artikelnummer = Column(String(100))
    bezeichnung = Column(String(500), nullable=False)
    beschreibung = Column(Text)  # Zusätzliche Details (mehrzeilig)
    
    # Für Veredelung: Details
    veredelung_position = Column(String(50))  # z.B. "Brust links", "Rücken"
    veredelung_details = Column(JSON)  # Stiche, Größe, Farben, etc.
    
    # ─── MENGEN & EINHEITEN ───────────────────────────────────────────────
    menge = Column(Numeric(10, 3), nullable=False, default=1)
    einheit = Column(String(20), default='Stk.')
    
    # ─── PREISE ───────────────────────────────────────────────────────────
    einzelpreis_netto = Column(Numeric(12, 4), nullable=False, default=0)
    einzelpreis_brutto = Column(Numeric(12, 4), default=0)  # Optional, für Endkundenpreise
    
    rabatt_prozent = Column(Numeric(5, 2), default=0)
    rabatt_betrag = Column(Numeric(12, 2), default=0)  # Berechnet
    
    # ─── MWST ─────────────────────────────────────────────────────────────
    mwst_satz = Column(Numeric(5, 2), nullable=False, default=19.00)
    mwst_kennzeichen = Column(String(10), default=MwStKennzeichen.STANDARD.value)
    
    # ─── BERECHNETE WERTE ─────────────────────────────────────────────────
    netto_gesamt = Column(Numeric(12, 2), nullable=False, default=0)
    mwst_betrag = Column(Numeric(12, 2), nullable=False, default=0)
    brutto_gesamt = Column(Numeric(12, 2), nullable=False, default=0)
    
    # ─── OPTIONALE FELDER ─────────────────────────────────────────────────
    kostenstelle = Column(String(50))
    notiz = Column(Text)  # Interne Notiz zur Position
    
    # ─── CONSTRAINTS ──────────────────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint('dokument_id', 'position', name='uq_doc_position'),
    )
    
    def __repr__(self):
        return f"<DocumentPosition {self.position}: {self.bezeichnung[:30]}>"
    
    def berechne(self):
        """Berechnet alle Werte der Position"""
        # Basis-Berechnung
        basis = self.menge * self.einzelpreis_netto
        
        # Rabatt anwenden
        if self.rabatt_prozent > 0:
            self.rabatt_betrag = (basis * self.rabatt_prozent / 100).quantize(Decimal('0.0001'))
        else:
            self.rabatt_betrag = Decimal('0.00')
        
        self.netto_gesamt = (basis - self.rabatt_betrag).quantize(Decimal('0.01'))
        
        # MwSt berechnen
        if self.mwst_kennzeichen in [MwStKennzeichen.FREI.value, 
                                      MwStKennzeichen.INNERGEMEINSCHAFTLICH.value,
                                      MwStKennzeichen.DRITTLAND.value]:
            self.mwst_betrag = Decimal('0.00')
        else:
            self.mwst_betrag = (self.netto_gesamt * self.mwst_satz / 100).quantize(Decimal('0.01'))
        
        self.brutto_gesamt = self.netto_gesamt + self.mwst_betrag
        
        # Auch Brutto-Einzelpreis setzen
        if self.menge > 0:
            self.einzelpreis_brutto = (self.brutto_gesamt / self.menge).quantize(Decimal('0.0001'))
    
    @classmethod
    def erstelle_textil_position(cls, artikel, menge, position_nr):
        """Factory für Textil-Position"""
        pos = cls(
            position=position_nr,
            typ=PositionsTyp.TEXTIL.value,
            artikel_id=artikel.id,
            artikelnummer=artikel.article_number,
            bezeichnung=artikel.name,
            menge=menge,
            einheit='Stk.',
            einzelpreis_netto=artikel.price,
            mwst_satz=Decimal('19.00')
        )
        pos.berechne()
        return pos
    
    @classmethod
    def erstelle_veredelung_position(cls, bezeichnung, menge, einzelpreis, position_nr,
                                     typ='stickerei', details=None):
        """Factory für Veredelungs-Position"""
        pos = cls(
            position=position_nr,
            typ=PositionsTyp.VEREDELUNG_STICKEREI.value if typ == 'stickerei' 
                else PositionsTyp.VEREDELUNG_DRUCK.value,
            bezeichnung=bezeichnung,
            beschreibung=details.get('beschreibung') if details else None,
            veredelung_position=details.get('position') if details else None,
            veredelung_details=details,
            menge=menge,
            einheit='Stk.',
            einzelpreis_netto=einzelpreis,
            mwst_satz=Decimal('19.00')
        )
        pos.berechne()
        return pos
    
    @classmethod
    def erstelle_einrichtung_position(cls, bezeichnung, betrag, position_nr):
        """Factory für Einrichtungspauschale"""
        pos = cls(
            position=position_nr,
            typ=PositionsTyp.EINRICHTUNG.value,
            bezeichnung=bezeichnung,
            menge=1,
            einheit='pauschal',
            einzelpreis_netto=betrag,
            mwst_satz=Decimal('19.00')
        )
        pos.berechne()
        return pos
    
    @classmethod
    def erstelle_anzahlung_abzug(cls, anzahlung_doc, position_nr):
        """Factory für Anzahlungsabzug in Schlussrechnung"""
        pos = cls(
            position=position_nr,
            typ=PositionsTyp.ANZAHLUNG_ABZUG.value,
            anzahlung_dokument_id=anzahlung_doc.id,
            bezeichnung=f"Abzgl. Anzahlung {anzahlung_doc.dokument_nummer}",
            menge=1,
            einheit='',
            einzelpreis_netto=-anzahlung_doc.summe_netto,  # Negativ!
            mwst_satz=Decimal('19.00')
        )
        pos.berechne()
        return pos


# ============================================================================
# ZAHLUNGEN
# ============================================================================

class DocumentPayment(db.Model):
    """
    Zahlungen zu Dokumenten
    
    Unterstützt:
    - Normale Zahlungen (Bar, Überweisung, Karte)
    - Anzahlungsverrechnung
    - Teilzahlungen
    """
    __tablename__ = 'document_payments'
    
    id = Column(Integer, primary_key=True)
    
    dokument_id = Column(Integer, ForeignKey('business_documents.id'), nullable=False)
    dokument = relationship('BusinessDocument', back_populates='zahlungen',
                           foreign_keys=[dokument_id])
    
    # ─── ZAHLUNGSART ──────────────────────────────────────────────────────
    zahlungsart = Column(String(30), nullable=False)
    # 'bar', 'ec_karte', 'kreditkarte', 'ueberweisung', 'lastschrift',
    # 'paypal', 'sumup', 'anzahlung_verrechnung', 'gutschrift_verrechnung'
    
    # ─── BETRAG & DATUM ───────────────────────────────────────────────────
    betrag = Column(Numeric(12, 2), nullable=False)
    zahlung_datum = Column(Date, nullable=False)
    
    # ─── REFERENZEN ───────────────────────────────────────────────────────
    transaktions_id = Column(String(100))  # Bank-Referenz, PayPal-ID, etc.
    
    # Bei Verrechnung: Verweis auf Anzahlungs-/Gutschriftsdokument
    verrechnungs_dokument_id = Column(Integer, ForeignKey('business_documents.id'))
    verrechnungs_dokument = relationship('BusinessDocument', 
                                         foreign_keys=[verrechnungs_dokument_id])
    
    # ─── BANK-DETAILS ─────────────────────────────────────────────────────
    bank_referenz = Column(String(200))  # Verwendungszweck
    kontoauszug_datum = Column(Date)
    
    # ─── STATUS ───────────────────────────────────────────────────────────
    bestaetigt = Column(Boolean, default=False)
    bestaetigt_von = Column(String(100))
    bestaetigt_am = Column(DateTime)
    
    # ─── NOTIZEN ──────────────────────────────────────────────────────────
    notiz = Column(Text)
    
    # ─── TRACKING ─────────────────────────────────────────────────────────
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    erstellt_von = Column(String(100))
    
    def __repr__(self):
        return f"<DocumentPayment {self.betrag}€ ({self.zahlungsart}) am {self.zahlung_datum}>"
    
    def bestaetigen(self, benutzer):
        """Bestätigt die Zahlung"""
        self.bestaetigt = True
        self.bestaetigt_von = benutzer
        self.bestaetigt_am = datetime.utcnow()
        
        # Prüfen ob Dokument vollständig bezahlt
        if self.dokument.ist_vollstaendig_bezahlt():
            self.dokument.status = DokumentStatus.BEZAHLT.value
            self.dokument.bezahlt_am = self.zahlung_datum


# ============================================================================
# EVENT LISTENER
# ============================================================================

@event.listens_for(DocumentPosition, 'before_insert')
@event.listens_for(DocumentPosition, 'before_update')
def position_berechnung(mapper, connection, target):
    """Automatische Berechnung vor Speicherung"""
    target.berechne()


# ============================================================================
# HELPER FUNKTIONEN
# ============================================================================

def initialisiere_nummernkreise():
    """Initialisiert die Standard-Nummernkreise"""
    standard_kreise = [
        ('angebot', 'AN', 'Angebote', 4),
        ('auftragsbestaetigung', 'AB', 'Auftragsbestätigungen', 4),
        ('auftrag', 'A', 'Aufträge (intern)', 4),
        ('lieferschein', 'LS', 'Lieferscheine', 4),
        ('rechnung', 'RE', 'Rechnungen', 4),
        ('anzahlung', 'AR', 'Anzahlungsrechnungen', 4),
        ('gutschrift', 'GS', 'Gutschriften', 4),
        ('kassenbeleg', 'K', 'Kassenbelege', 6),
    ]
    
    aktuelles_jahr = datetime.now().year
    
    for belegart, praefix, bezeichnung, stellen in standard_kreise:
        existiert = Nummernkreis.query.filter_by(belegart=belegart).first()
        if not existiert:
            nk = Nummernkreis(
                belegart=belegart,
                bezeichnung=bezeichnung,
                praefix=praefix,
                aktuelles_jahr=aktuelles_jahr,
                aktuelle_nummer=0,
                stellen=stellen
            )
            db.session.add(nk)
    
    db.session.commit()


def initialisiere_zahlungsbedingungen():
    """Initialisiert Standard-Zahlungsbedingungen"""
    standard_bedingungen = [
        {
            'bezeichnung': 'Sofort fällig',
            'kurztext': 'sofort',
            'zahlungsziel_tage': 0,
            'text_rechnung': 'Zahlbar sofort ohne Abzug.',
            'sortierung': 1
        },
        {
            'bezeichnung': '7 Tage netto',
            'kurztext': '7T',
            'zahlungsziel_tage': 7,
            'text_rechnung': 'Zahlbar innerhalb von 7 Tagen ohne Abzug.',
            'sortierung': 2
        },
        {
            'bezeichnung': '14 Tage netto',
            'kurztext': '14T',
            'zahlungsziel_tage': 14,
            'text_rechnung': 'Zahlbar innerhalb von 14 Tagen ohne Abzug.',
            'standard': True,
            'sortierung': 3
        },
        {
            'bezeichnung': '30 Tage netto',
            'kurztext': '30T',
            'zahlungsziel_tage': 30,
            'text_rechnung': 'Zahlbar innerhalb von 30 Tagen ohne Abzug.',
            'sortierung': 4
        },
        {
            'bezeichnung': '14 Tage 2% Skonto, 30 Tage netto',
            'kurztext': '2%/30T',
            'zahlungsziel_tage': 30,
            'skonto_prozent': Decimal('2.00'),
            'skonto_tage': 14,
            'text_rechnung': 'Zahlbar innerhalb von 30 Tagen ohne Abzug.',
            'text_rechnung_skonto': 'Bei Zahlung innerhalb von 14 Tagen gewähren wir 2% Skonto.',
            'sortierung': 5
        },
        {
            'bezeichnung': '50% Anzahlung, Rest bei Lieferung',
            'kurztext': '50%AZ',
            'zahlungsziel_tage': 0,
            'anzahlung_erforderlich': True,
            'anzahlung_prozent': Decimal('50.00'),
            'anzahlung_text': '50% bei Auftragserteilung, Restbetrag bei Lieferung.',
            'text_rechnung': 'Restbetrag zahlbar bei Lieferung.',
            'sortierung': 6
        },
        {
            'bezeichnung': 'Vorkasse',
            'kurztext': 'VK',
            'zahlungsziel_tage': 0,
            'anzahlung_erforderlich': True,
            'anzahlung_prozent': Decimal('100.00'),
            'anzahlung_text': 'Zahlung vor Lieferung erforderlich.',
            'text_rechnung': 'Vielen Dank für Ihre Vorauszahlung.',
            'sortierung': 7
        },
    ]
    
    for daten in standard_bedingungen:
        existiert = Zahlungsbedingung.query.filter_by(bezeichnung=daten['bezeichnung']).first()
        if not existiert:
            zb = Zahlungsbedingung(**daten)
            db.session.add(zb)
    
    db.session.commit()
