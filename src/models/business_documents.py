# -*- coding: utf-8 -*-
"""
BUSINESS DOCUMENTS - Einheitliches Modell für Geschäftsdokumente
================================================================
StitchAdmin 2.0

Unterstützte Dokumenttypen:
- Angebot
- Auftragsbestätigung
- Lieferschein
- Rechnung
- Anzahlungsrechnung
- Gutschrift

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from enum import Enum
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Date, Boolean, Text,
    ForeignKey, JSON, Numeric, Index, event
)
from sqlalchemy.orm import relationship, backref
from src.models import db


# ============================================================
# ENUMS
# ============================================================

class DokumentTyp(Enum):
    """Typen von Geschäftsdokumenten"""
    ANGEBOT = "angebot"
    AUFTRAGSBESTAETIGUNG = "auftragsbestaetigung"
    LIEFERSCHEIN = "lieferschein"
    RECHNUNG = "rechnung"
    ANZAHLUNG = "anzahlung"
    GUTSCHRIFT = "gutschrift"
    
    @property
    def label(self):
        labels = {
            'angebot': 'Angebot',
            'auftragsbestaetigung': 'Auftragsbestätigung',
            'lieferschein': 'Lieferschein',
            'rechnung': 'Rechnung',
            'anzahlung': 'Anzahlungsrechnung',
            'gutschrift': 'Gutschrift'
        }
        return labels.get(self.value, self.value)


class DokumentStatus(Enum):
    """Status eines Dokuments"""
    ENTWURF = "entwurf"
    VERSENDET = "versendet"
    ANGENOMMEN = "angenommen"      # Für Angebote
    ABGELEHNT = "abgelehnt"        # Für Angebote
    VERFALLEN = "verfallen"        # Für Angebote (Gültigkeit abgelaufen)
    IN_BEARBEITUNG = "in_bearbeitung"
    TEILGELIEFERT = "teilgeliefert"
    GELIEFERT = "geliefert"
    OFFEN = "offen"                # Für Rechnungen
    TEILBEZAHLT = "teilbezahlt"
    BEZAHLT = "bezahlt"
    UEBERFAELLIG = "ueberfaellig"
    STORNIERT = "storniert"
    MAHNUNG_1 = "mahnung_1"
    MAHNUNG_2 = "mahnung_2"
    MAHNUNG_3 = "mahnung_3"
    
    @property
    def label(self):
        labels = {
            'entwurf': 'Entwurf',
            'versendet': 'Versendet',
            'angenommen': 'Angenommen',
            'abgelehnt': 'Abgelehnt',
            'verfallen': 'Verfallen',
            'in_bearbeitung': 'In Bearbeitung',
            'teilgeliefert': 'Teilweise geliefert',
            'geliefert': 'Geliefert',
            'offen': 'Offen',
            'teilbezahlt': 'Teilbezahlt',
            'bezahlt': 'Bezahlt',
            'ueberfaellig': 'Überfällig',
            'storniert': 'Storniert',
            'mahnung_1': '1. Mahnung',
            'mahnung_2': '2. Mahnung',
            'mahnung_3': '3. Mahnung',
        }
        return labels.get(self.value, self.value)
    
    @property
    def badge_class(self):
        """Bootstrap Badge-Klasse für Status"""
        classes = {
            'entwurf': 'secondary',
            'versendet': 'info',
            'angenommen': 'success',
            'abgelehnt': 'danger',
            'verfallen': 'dark',
            'in_bearbeitung': 'primary',
            'teilgeliefert': 'warning',
            'geliefert': 'success',
            'offen': 'warning',
            'teilbezahlt': 'info',
            'bezahlt': 'success',
            'ueberfaellig': 'danger',
            'storniert': 'dark',
            'mahnung_1': 'warning',
            'mahnung_2': 'danger',
            'mahnung_3': 'danger',
        }
        return classes.get(self.value, 'secondary')


class PositionTyp(Enum):
    """Typen von Dokumentpositionen"""
    ARTIKEL = "artikel"
    TEXTIL = "textil"
    STICKEREI = "stickerei"
    DRUCK = "druck"
    DIENSTLEISTUNG = "dienstleistung"
    SETUP = "setup"              # Einrichtungspauschale
    VERSAND = "versand"
    RABATT = "rabatt"
    ZWISCHENSUMME = "zwischensumme"
    ANZAHLUNG_ABZUG = "anzahlung_abzug"  # Negative Position
    FREITEXT = "freitext"


class MwStKennzeichen(Enum):
    """MwSt-Kennzeichen nach deutschem Recht"""
    STANDARD = "S"      # 19%
    ERMAESSIGT = "E"    # 7%
    FREI = "F"          # 0% (steuerbefreit)
    
    @property
    def satz(self):
        saetze = {'S': Decimal('19.00'), 'E': Decimal('7.00'), 'F': Decimal('0.00')}
        return saetze.get(self.value, Decimal('19.00'))


# ============================================================
# HAUPTMODELL: BusinessDocument
# ============================================================

class BusinessDocument(db.Model):
    """
    Einheitliches Modell für alle Geschäftsdokumente
    
    Unterstützt:
    - Angebote
    - Auftragsbestätigungen
    - Lieferscheine
    - Rechnungen (inkl. Anzahlung, Teilrechnung, Schlussrechnung)
    - Gutschriften
    """
    __tablename__ = 'business_documents'
    
    id = Column(Integer, primary_key=True)
    
    # ========== IDENTIFIKATION ==========
    dokument_nummer = Column(String(50), unique=True, nullable=False, index=True)
    dokument_typ = Column(String(30), nullable=False, index=True)
    
    # ========== VERKETTUNG ==========
    # Vorgänger-Dokument (z.B. Angebot → AB → Rechnung)
    vorgaenger_id = Column(Integer, ForeignKey('business_documents.id'))
    vorgaenger = relationship('BusinessDocument', remote_side=[id],
                              backref=backref('nachfolger', lazy='dynamic'))
    
    # Verknüpfung zum internen Produktionsauftrag
    auftrag_id = Column(String(50), ForeignKey('orders.id'))
    auftrag = relationship('Order', backref='dokumente')
    
    # Bei Gutschriften: Referenz zur Original-Rechnung
    storno_von_id = Column(Integer, ForeignKey('business_documents.id'))
    storno_von = relationship('BusinessDocument', remote_side=[id], foreign_keys=[storno_von_id])
    
    # ========== KUNDE ==========
    kunde_id = Column(String(50), ForeignKey('customers.id'), nullable=False, index=True)
    kunde = relationship('Customer', backref='business_documents')
    
    # Adressen-Snapshot (für Archivierung - Adresse zum Zeitpunkt der Erstellung)
    rechnungsadresse = Column(JSON)
    lieferadresse = Column(JSON)
    
    # ========== DATUM ==========
    dokument_datum = Column(Date, default=date.today, index=True)
    gueltig_bis = Column(Date)           # Für Angebote
    lieferdatum = Column(Date)           # Für Lieferscheine
    lieferdatum_bis = Column(Date)       # Für Lieferzeitraum
    faelligkeitsdatum = Column(Date)     # Für Rechnungen
    
    # ========== BETRÄGE ==========
    summe_netto = Column(Numeric(12, 2), default=0)
    summe_mwst = Column(Numeric(12, 2), default=0)
    summe_brutto = Column(Numeric(12, 2), default=0)
    
    # Rabatte
    rabatt_prozent = Column(Numeric(5, 2), default=0)
    rabatt_betrag = Column(Numeric(12, 2), default=0)
    
    # Für Schlussrechnungen: Abzug von Anzahlungen
    bereits_gezahlt = Column(Numeric(12, 2), default=0)
    restbetrag = Column(Numeric(12, 2), default=0)
    
    # ========== STATUS ==========
    status = Column(String(30), default=DokumentStatus.ENTWURF.value, index=True)
    
    # ========== TEXTE ==========
    betreff = Column(String(500))
    einleitung = Column(Text)
    schlussbemerkung = Column(Text)
    interne_notiz = Column(Text)
    
    # Kundenreferenz (Bestellnummer des Kunden)
    kunden_referenz = Column(String(100))
    
    # ========== ZAHLUNGSBEDINGUNGEN ==========
    zahlungsbedingung_id = Column(Integer, ForeignKey('zahlungsbedingungen.id'))
    zahlungsbedingung = relationship('Zahlungsbedingung')
    
    zahlungsziel_tage = Column(Integer, default=14)
    skonto_prozent = Column(Numeric(5, 2), default=0)
    skonto_tage = Column(Integer, default=0)
    zahlungstext = Column(Text)
    
    # ========== VERSAND ==========
    versandart = Column(String(50))  # 'abholung', 'post', 'spedition', 'selbstlieferung'
    versandkosten = Column(Numeric(10, 2), default=0)
    sendungsnummer = Column(String(100))
    
    # ========== PDF & ARCHIVIERUNG ==========
    pdf_pfad = Column(String(500))
    pdf_erstellt_am = Column(DateTime)
    pdf_hash = Column(String(64))  # SHA256 für Integrität
    
    # ========== TRACKING ==========
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    erstellt_von = Column(String(100))
    geaendert_am = Column(DateTime, onupdate=datetime.utcnow)
    geaendert_von = Column(String(100))
    
    versendet_am = Column(DateTime)
    versendet_per = Column(String(50))  # 'email', 'post', 'fax'
    versendet_an = Column(String(200))  # E-Mail-Adresse
    
    angenommen_am = Column(DateTime)
    bezahlt_am = Column(DateTime)
    storniert_am = Column(DateTime)
    storno_grund = Column(String(500))
    
    # ========== RELATIONSHIPS ==========
    positionen = relationship('DocumentPosition', back_populates='dokument',
                             cascade='all, delete-orphan',
                             order_by='DocumentPosition.position')
    
    zahlungen = relationship('DocumentPayment', back_populates='dokument',
                            cascade='all, delete-orphan',
                            order_by='DocumentPayment.zahlung_datum')
    
    # ========== INDIZES ==========
    __table_args__ = (
        Index('idx_doc_kunde_datum', 'kunde_id', 'dokument_datum'),
        Index('idx_doc_typ_status', 'dokument_typ', 'status'),
    )
    
    def __repr__(self):
        return f"<BusinessDocument {self.dokument_nummer} ({self.dokument_typ})>"
    
    # ========== PROPERTIES ==========
    
    @property
    def typ_label(self):
        """Lesbare Bezeichnung des Dokumenttyps"""
        try:
            return DokumentTyp(self.dokument_typ).label
        except:
            return self.dokument_typ
    
    @property
    def status_label(self):
        """Lesbare Bezeichnung des Status"""
        try:
            return DokumentStatus(self.status).label
        except:
            return self.status
    
    @property
    def status_badge(self):
        """Bootstrap Badge-Klasse für Status"""
        try:
            return DokumentStatus(self.status).badge_class
        except:
            return 'secondary'
    
    @property
    def ist_entwurf(self):
        return self.status == DokumentStatus.ENTWURF.value
    
    @property
    def ist_storniert(self):
        return self.status == DokumentStatus.STORNIERT.value
    
    @property
    def ist_rechnung(self):
        return self.dokument_typ in ['rechnung', 'anzahlung', 'gutschrift']
    
    @property
    def ist_angebot(self):
        return self.dokument_typ == 'angebot'
    
    @property
    def ist_ueberfaellig(self):
        """Prüft ob Rechnung überfällig ist"""
        if not self.ist_rechnung:
            return False
        if self.status in [DokumentStatus.BEZAHLT.value, DokumentStatus.STORNIERT.value]:
            return False
        if not self.faelligkeitsdatum:
            return False
        return date.today() > self.faelligkeitsdatum
    
    @property
    def tage_ueberfaellig(self):
        """Anzahl Tage überfällig"""
        if not self.ist_ueberfaellig:
            return 0
        return (date.today() - self.faelligkeitsdatum).days
    
    @property
    def offener_betrag(self):
        """Berechnet den noch offenen Betrag"""
        if not self.ist_rechnung:
            return Decimal('0.00')
        
        gezahlt = sum(z.betrag for z in self.zahlungen if z.bestaetigt)
        return self.summe_brutto - gezahlt - self.bereits_gezahlt
    
    @property
    def anzahl_positionen(self):
        """Anzahl der Positionen"""
        return len([p for p in self.positionen if p.typ != PositionTyp.ZWISCHENSUMME.value])
    
    # ========== METHODEN ==========
    
    def berechne_summen(self):
        """
        Berechnet alle Summen aus den Positionen
        """
        netto = Decimal('0.00')
        mwst = Decimal('0.00')
        
        for pos in self.positionen:
            if pos.typ == PositionTyp.RABATT.value:
                netto -= abs(pos.netto_gesamt or 0)
                mwst -= abs(pos.mwst_betrag or 0)
            elif pos.typ == PositionTyp.ANZAHLUNG_ABZUG.value:
                # Wird separat behandelt
                pass
            elif pos.typ != PositionTyp.ZWISCHENSUMME.value:
                netto += pos.netto_gesamt or 0
                mwst += pos.mwst_betrag or 0
        
        # Dokumentrabatt anwenden
        if self.rabatt_prozent:
            rabatt = netto * (self.rabatt_prozent / 100)
            self.rabatt_betrag = rabatt
            netto -= rabatt
            # MwSt proportional reduzieren
            mwst = netto * Decimal('0.19')  # Vereinfacht
        
        self.summe_netto = netto
        self.summe_mwst = mwst
        self.summe_brutto = netto + mwst
        
        # Restbetrag berechnen
        self.restbetrag = self.summe_brutto - self.bereits_gezahlt
    
    def set_zahlungsbedingung(self, zahlungsbedingung):
        """
        Setzt Zahlungsbedingung und berechnet Fälligkeit
        """
        self.zahlungsbedingung = zahlungsbedingung
        self.zahlungsziel_tage = zahlungsbedingung.zahlungsziel_tage
        self.skonto_prozent = zahlungsbedingung.skonto_prozent
        self.skonto_tage = zahlungsbedingung.skonto_tage
        self.zahlungstext = zahlungsbedingung.generiere_text()
        
        # Fälligkeitsdatum setzen
        basis = self.dokument_datum or date.today()
        self.faelligkeitsdatum = basis + timedelta(days=self.zahlungsziel_tage)
    
    def snapshot_adressen(self):
        """
        Speichert aktuelle Kundenadressen als Snapshot
        """
        if self.kunde:
            self.rechnungsadresse = {
                'name': self.kunde.display_name,
                'firma': self.kunde.company_name,
                'strasse': self.kunde.street,
                'plz': self.kunde.zip_code,
                'ort': self.kunde.city,
                'land': self.kunde.country or 'Deutschland',
                'email': self.kunde.email,
                'telefon': self.kunde.phone,
                'ust_id': getattr(self.kunde, 'vat_id', None)
            }
            
            # Lieferadresse nur wenn abweichend
            if hasattr(self.kunde, 'delivery_street') and self.kunde.delivery_street:
                self.lieferadresse = {
                    'name': self.kunde.display_name,
                    'firma': self.kunde.company_name,
                    'strasse': self.kunde.delivery_street,
                    'plz': self.kunde.delivery_zip,
                    'ort': self.kunde.delivery_city,
                    'land': self.kunde.delivery_country or 'Deutschland'
                }
    
    def kann_umgewandelt_werden_zu(self, ziel_typ):
        """
        Prüft ob Dokument in anderen Typ umgewandelt werden kann
        
        Args:
            ziel_typ: DokumentTyp oder String
        
        Returns:
            tuple: (bool, str) - (möglich, Grund wenn nicht)
        """
        if isinstance(ziel_typ, DokumentTyp):
            ziel_typ = ziel_typ.value
        
        if self.ist_storniert:
            return False, "Stornierte Dokumente können nicht umgewandelt werden"
        
        erlaubte_umwandlungen = {
            'angebot': ['auftragsbestaetigung'],
            'auftragsbestaetigung': ['lieferschein', 'anzahlung', 'rechnung'],
            'lieferschein': ['rechnung'],
        }
        
        erlaubt = erlaubte_umwandlungen.get(self.dokument_typ, [])
        
        if ziel_typ in erlaubt:
            return True, ""
        else:
            return False, f"Umwandlung von {self.typ_label} zu {ziel_typ} nicht möglich"
    
    def erstelle_nachfolger(self, ziel_typ, erstellt_von=None):
        """
        Erstellt ein Nachfolge-Dokument (z.B. Angebot → AB)
        
        Args:
            ziel_typ: Typ des neuen Dokuments
            erstellt_von: Benutzername
        
        Returns:
            BusinessDocument: Neues Dokument
        """
        from src.models.nummernkreise import Nummernkreis
        
        if isinstance(ziel_typ, DokumentTyp):
            ziel_typ = ziel_typ.value
        
        kann, grund = self.kann_umgewandelt_werden_zu(ziel_typ)
        if not kann:
            raise ValueError(grund)
        
        # Neue Belegnummer
        neue_nummer = Nummernkreis.neue_belegnummer(ziel_typ)
        
        # Neues Dokument erstellen
        neues_dok = BusinessDocument(
            dokument_nummer=neue_nummer,
            dokument_typ=ziel_typ,
            vorgaenger_id=self.id,
            auftrag_id=self.auftrag_id,
            kunde_id=self.kunde_id,
            rechnungsadresse=self.rechnungsadresse,
            lieferadresse=self.lieferadresse,
            betreff=self.betreff,
            kunden_referenz=self.kunden_referenz,
            erstellt_von=erstellt_von,
        )
        
        # Positionen kopieren
        for pos in self.positionen:
            neue_pos = DocumentPosition(
                position=pos.position,
                typ=pos.typ,
                artikel_id=pos.artikel_id,
                artikelnummer=pos.artikelnummer,
                bezeichnung=pos.bezeichnung,
                beschreibung=pos.beschreibung,
                menge=pos.menge,
                einheit=pos.einheit,
                einzelpreis_netto=pos.einzelpreis_netto,
                rabatt_prozent=pos.rabatt_prozent,
                mwst_satz=pos.mwst_satz,
                mwst_kennzeichen=pos.mwst_kennzeichen,
            )
            neue_pos.berechne()
            neues_dok.positionen.append(neue_pos)
        
        neues_dok.berechne_summen()
        
        return neues_dok
    
    def erstelle_gutschrift(self, erstellt_von=None, grund=None):
        """
        Erstellt eine Gutschrift/Storno für dieses Dokument
        
        Returns:
            BusinessDocument: Gutschrift
        """
        from src.models.nummernkreise import Nummernkreis
        
        if not self.ist_rechnung:
            raise ValueError("Gutschriften können nur für Rechnungen erstellt werden")
        
        if self.ist_storniert:
            raise ValueError("Dokument ist bereits storniert")
        
        neue_nummer = Nummernkreis.neue_belegnummer('gutschrift')
        
        gutschrift = BusinessDocument(
            dokument_nummer=neue_nummer,
            dokument_typ=DokumentTyp.GUTSCHRIFT.value,
            storno_von_id=self.id,
            kunde_id=self.kunde_id,
            rechnungsadresse=self.rechnungsadresse,
            betreff=f"Gutschrift zu {self.dokument_nummer}",
            erstellt_von=erstellt_von,
            interne_notiz=grund,
        )
        
        # Positionen mit negativen Beträgen
        for pos in self.positionen:
            neue_pos = DocumentPosition(
                position=pos.position,
                typ=pos.typ,
                artikel_id=pos.artikel_id,
                artikelnummer=pos.artikelnummer,
                bezeichnung=pos.bezeichnung,
                menge=-abs(pos.menge),  # Negativ!
                einheit=pos.einheit,
                einzelpreis_netto=pos.einzelpreis_netto,
                mwst_satz=pos.mwst_satz,
                mwst_kennzeichen=pos.mwst_kennzeichen,
            )
            neue_pos.berechne()
            gutschrift.positionen.append(neue_pos)
        
        gutschrift.berechne_summen()
        
        # Original stornieren
        self.status = DokumentStatus.STORNIERT.value
        self.storniert_am = datetime.utcnow()
        self.storno_grund = grund
        
        return gutschrift


# ============================================================
# POSITIONEN
# ============================================================

class DocumentPosition(db.Model):
    """
    Positionen auf Geschäftsdokumenten
    """
    __tablename__ = 'document_positions'
    
    id = Column(Integer, primary_key=True)
    dokument_id = Column(Integer, ForeignKey('business_documents.id'), nullable=False)
    dokument = relationship('BusinessDocument', back_populates='positionen')
    
    # Sortierung
    position = Column(Integer, nullable=False)
    
    # Positionstyp
    typ = Column(String(30), default=PositionTyp.ARTIKEL.value)
    
    # Referenzen
    artikel_id = Column(Integer, ForeignKey('articles.id'))
    artikel = relationship('Article')
    
    order_item_id = Column(Integer)  # Für Auftrags-Verknüpfung
    
    # Beschreibung
    artikelnummer = Column(String(100))
    bezeichnung = Column(String(500), nullable=False)
    beschreibung = Column(Text)
    
    # Mengen
    menge = Column(Numeric(10, 3), nullable=False, default=1)
    einheit = Column(String(20), default='Stk.')
    
    # Preise
    einzelpreis_netto = Column(Numeric(12, 4), nullable=False, default=0)
    rabatt_prozent = Column(Numeric(5, 2), default=0)
    
    # MwSt
    mwst_satz = Column(Numeric(5, 2), nullable=False, default=19)
    mwst_kennzeichen = Column(String(10), default=MwStKennzeichen.STANDARD.value)
    
    # Berechnete Werte
    netto_gesamt = Column(Numeric(12, 2), default=0)
    mwst_betrag = Column(Numeric(12, 2), default=0)
    brutto_gesamt = Column(Numeric(12, 2), default=0)
    
    # Optional
    kostenstelle = Column(String(50))
    
    def __repr__(self):
        return f"<DocumentPosition {self.position}: {self.bezeichnung}>"
    
    def berechne(self):
        """Berechnet alle Werte der Position"""
        menge = Decimal(str(self.menge or 0))
        preis = Decimal(str(self.einzelpreis_netto or 0))
        rabatt_p = Decimal(str(self.rabatt_prozent or 0))
        mwst_s = Decimal(str(self.mwst_satz or 19))
        
        basis = menge * preis
        rabatt = basis * (rabatt_p / 100)
        netto = basis - rabatt
        
        self.netto_gesamt = netto
        self.mwst_betrag = netto * (mwst_s / 100)
        self.brutto_gesamt = self.netto_gesamt + self.mwst_betrag
    
    @property
    def typ_label(self):
        try:
            return PositionTyp(self.typ).name.replace('_', ' ').title()
        except:
            return self.typ


# ============================================================
# ZAHLUNGEN
# ============================================================

class DocumentPayment(db.Model):
    """
    Zahlungen zu Dokumenten
    """
    __tablename__ = 'document_payments'
    
    id = Column(Integer, primary_key=True)
    dokument_id = Column(Integer, ForeignKey('business_documents.id'), nullable=False)
    dokument = relationship('BusinessDocument', back_populates='zahlungen')
    
    # Zahlungsart
    zahlungsart = Column(String(30), nullable=False)
    # 'bar', 'ec_karte', 'kreditkarte', 'ueberweisung', 'paypal', 'sumup', 'lastschrift'
    
    betrag = Column(Numeric(12, 2), nullable=False)
    zahlung_datum = Column(Date, nullable=False, default=date.today)
    
    # Referenzen
    transaktions_id = Column(String(100))
    
    # Bei Verrechnung von Anzahlungen
    anzahlungs_rechnung_id = Column(Integer, ForeignKey('business_documents.id'))
    anzahlungs_rechnung = relationship('BusinessDocument', foreign_keys=[anzahlungs_rechnung_id])
    
    # Status
    bestaetigt = Column(Boolean, default=False)
    bestaetigt_von = Column(String(100))
    bestaetigt_am = Column(DateTime)
    
    notiz = Column(Text)
    
    # Tracking
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    erstellt_von = Column(String(100))
    
    def __repr__(self):
        return f"<DocumentPayment {self.betrag}€ am {self.zahlung_datum}>"
    
    def bestaetigen(self, von_benutzer):
        """Markiert Zahlung als bestätigt"""
        self.bestaetigt = True
        self.bestaetigt_von = von_benutzer
        self.bestaetigt_am = datetime.utcnow()
        
        # Dokument-Status aktualisieren
        if self.dokument:
            offen = self.dokument.offener_betrag
            if offen <= 0:
                self.dokument.status = DokumentStatus.BEZAHLT.value
                self.dokument.bezahlt_am = datetime.utcnow()
            else:
                self.dokument.status = DokumentStatus.TEILBEZAHLT.value
