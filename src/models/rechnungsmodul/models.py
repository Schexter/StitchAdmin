# -*- coding: utf-8 -*-
"""
Rechnungsmodul - Vollständige SQLAlchemy Models
Erstellt von: Hans Hahn - Alle Rechte vorbehalten
Datum: 09. Juli 2025

Dieses Modul enthält alle Datenbank-Models für das Rechnungsmodul:
- Kassensystem mit TSE-Integration
- ZUGPFERD-konforme Rechnungserstellung
- Zahlungserfassung und -verwaltung
- Steuer- und MwSt-Verwaltung
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
from decimal import Decimal
from enum import Enum
import json
import uuid

# Import der Haupt-DB-Instanz
try:
    from src.models import db
except ImportError:
    # Fallback für Development
    db = SQLAlchemy()

# Enums für Status-Felder
class BelegTyp(Enum):
    """Beleg-Typen"""
    RECHNUNG = "RECHNUNG"
    GUTSCHRIFT = "GUTSCHRIFT"
    TRAINING = "TRAINING"
    STORNO = "STORNO"

class ZahlungsArt(Enum):
    """Zahlungsarten"""
    BAR = "BAR"
    EC_KARTE = "EC_KARTE"
    SUMUP = "SUMUP"
    KREDITKARTE = "KREDITKARTE"
    RECHNUNG = "RECHNUNG"
    UEBERWEISUNG = "UEBERWEISUNG"
    PAYPAL = "PAYPAL"
    LASTSCHRIFT = "LASTSCHRIFT"

class RechnungsStatus(Enum):
    """Rechnungs-Status"""
    ENTWURF = "ENTWURF"
    OFFEN = "OFFEN"
    TEILBEZAHLT = "TEILBEZAHLT"
    BEZAHLT = "BEZAHLT"
    UEBERFAELLIG = "UEBERFAELLIG"
    STORNIERT = "STORNIERT"
    GUTSCHRIFT = "GUTSCHRIFT"

class TSEStatus(Enum):
    """TSE-Status"""
    AKTIV = "AKTIV"
    INAKTIV = "INAKTIV"
    DEFEKT = "DEFEKT"
    WARTUNG = "WARTUNG"

class ZugpferdProfil(Enum):
    """ZUGPFERD-Profile"""
    MINIMUM = "MINIMUM"
    BASIC = "BASIC"
    COMFORT = "COMFORT"
    EXTENDED = "EXTENDED"

# Hauptmodels für Kassensystem
class KassenBeleg(db.Model):
    """
    Kassenbelegzeilen - TSE-konforme Belegerstellung
    
    Speichert alle Kassenbuchungen mit TSE-Signatur gemäß KassenSichV
    """
    __tablename__ = 'kassen_belege'
    
    # Primärschlüssel
    id = db.Column(db.Integer, primary_key=True)
    
    # Beleg-Identifikation
    belegnummer = db.Column(db.String(50), unique=True, nullable=False, index=True)
    beleg_typ = db.Column(db.Enum(BelegTyp), nullable=False, default=BelegTyp.RECHNUNG)
    
    # Kunde (optional - für Rechnungen)
    kunde_id = db.Column(db.String(50), db.ForeignKey('customers.id'), nullable=True)
    kunde_name = db.Column(db.String(200))  # Snapshot für Belege
    kunde_adresse = db.Column(db.Text)       # Snapshot für Belege
    
    # Beträge (alle in EUR, brutto)
    netto_gesamt = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    mwst_gesamt = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    brutto_gesamt = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    
    # Zahlung
    zahlungsart = db.Column(db.Enum(ZahlungsArt), nullable=False)
    gegeben = db.Column(db.Numeric(10, 2))     # Gegebener Betrag bei Barzahlung
    rueckgeld = db.Column(db.Numeric(10, 2))   # Rückgeld bei Barzahlung
    
    # TSE-Verknüpfung
    tse_transaktion_id = db.Column(db.Integer, db.ForeignKey('kassen_transaktionen.id'), nullable=True)
    
    # Kasse und Personal
    kassen_id = db.Column(db.String(50), nullable=False, default='KASSE-01')
    kassierer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    kassierer_name = db.Column(db.String(100))  # Snapshot
    
    # Status
    storniert = db.Column(db.Boolean, default=False)
    storno_grund = db.Column(db.String(500))
    storno_beleg_id = db.Column(db.Integer, db.ForeignKey('kassen_belege.id'), nullable=True)
    
    # Zeitstempel
    erstellt_am = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    bearbeitet_am = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Sonstiges
    notizen = db.Column(db.Text)
    
    # Relationships
    positionen = db.relationship('BelegPosition', backref='beleg', lazy='dynamic', cascade='all, delete-orphan')
    tse_transaktion = db.relationship('KassenTransaktion', backref='belege', foreign_keys=[tse_transaktion_id])
    kassierer = db.relationship('User', backref='kassen_belege', foreign_keys=[kassierer_id])
    storno_beleg = db.relationship('KassenBeleg', remote_side=[id], backref='stornierte_belege')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.belegnummer:
            self.belegnummer = self.generate_belegnummer()
    
    def generate_belegnummer(self):
        """Generiert eindeutige Belegnummer"""
        prefix = "KAS"
        datum = datetime.now().strftime("%Y%m%d")
        # Hole die nächste Nummer für heute
        heute_count = KassenBeleg.query.filter(
            KassenBeleg.belegnummer.like(f"{prefix}-{datum}-%")
        ).count()
        return f"{prefix}-{datum}-{heute_count + 1:04d}"
    
    def calculate_totals(self):
        """Berechnet Gesamtsummen aus Positionen"""
        self.netto_gesamt = sum(pos.netto_betrag for pos in self.positionen)
        self.mwst_gesamt = sum(pos.mwst_betrag for pos in self.positionen)
        self.brutto_gesamt = sum(pos.brutto_betrag for pos in self.positionen)
    
    def to_dict(self):
        """Konvertiert zu Dictionary für JSON-Export"""
        return {
            'id': self.id,
            'belegnummer': self.belegnummer,
            'beleg_typ': self.beleg_typ.value if self.beleg_typ else None,
            'kunde_name': self.kunde_name,
            'netto_gesamt': float(self.netto_gesamt),
            'mwst_gesamt': float(self.mwst_gesamt),
            'brutto_gesamt': float(self.brutto_gesamt),
            'zahlungsart': self.zahlungsart.value if self.zahlungsart else None,
            'erstellt_am': self.erstellt_am.isoformat() if self.erstellt_am else None,
            'kassierer_name': self.kassierer_name,
            'storniert': self.storniert
        }
    
    def __repr__(self):
        return f'<KassenBeleg {self.belegnummer}>'

class BelegPosition(db.Model):
    """
    Belegpositionen - Einzelne Artikel auf Kassenbelegen
    """
    __tablename__ = 'beleg_positionen'
    
    # Primärschlüssel
    id = db.Column(db.Integer, primary_key=True)
    
    # Beleg-Zuordnung
    beleg_id = db.Column(db.Integer, db.ForeignKey('kassen_belege.id'), nullable=False)
    position = db.Column(db.Integer, nullable=False)  # Laufende Nummer
    
    # Artikel-Informationen
    artikel_id = db.Column(db.String(50), db.ForeignKey('articles.id'), nullable=True)
    artikel_nummer = db.Column(db.String(100))  # Snapshot
    artikel_name = db.Column(db.String(200), nullable=False)  # Snapshot
    artikel_kategorie = db.Column(db.String(100))  # Snapshot
    
    # Mengen und Preise
    menge = db.Column(db.Numeric(10, 3), nullable=False, default=1)
    einzelpreis_netto = db.Column(db.Numeric(10, 2), nullable=False)
    einzelpreis_brutto = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Steuer
    mwst_satz = db.Column(db.Numeric(5, 2), nullable=False, default=19.0)
    mwst_betrag = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Rabatt
    rabatt_prozent = db.Column(db.Numeric(5, 2), default=0)
    rabatt_betrag = db.Column(db.Numeric(10, 2), default=0)
    
    # Berechnete Beträge
    netto_betrag = db.Column(db.Numeric(10, 2), nullable=False)
    brutto_betrag = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Sonstiges
    notizen = db.Column(db.Text)
    
    # Relationships
    artikel = db.relationship('Article', backref='kassen_positionen', foreign_keys=[artikel_id])
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.calculate_amounts()
    
    def calculate_amounts(self):
        """Berechnet alle Beträge basierend auf Grunddaten"""
        # Wenn Beträge bereits gesetzt sind, nicht neu berechnen
        if self.netto_betrag is not None and self.brutto_betrag is not None:
            return

        # Sichere Defaults
        if self.menge is None:
            self.menge = 1
        if self.einzelpreis_netto is None:
            self.einzelpreis_netto = 0
        if self.mwst_satz is None:
            self.mwst_satz = 19
        if self.rabatt_prozent is None:
            self.rabatt_prozent = 0

        # Netto-Gesamtbetrag
        netto_gesamt = self.menge * self.einzelpreis_netto

        # Rabatt abziehen
        self.rabatt_betrag = netto_gesamt * (self.rabatt_prozent / 100)
        self.netto_betrag = netto_gesamt - self.rabatt_betrag

        # MwSt berechnen
        self.mwst_betrag = self.netto_betrag * (self.mwst_satz / 100)

        # Brutto-Betrag
        self.brutto_betrag = self.netto_betrag + self.mwst_betrag

        # Einzelpreis brutto berechnen (falls noch nicht gesetzt)
        if self.einzelpreis_brutto is None:
            self.einzelpreis_brutto = self.einzelpreis_netto * (1 + self.mwst_satz / 100)
    
    def __repr__(self):
        return f'<BelegPosition {self.position}: {self.artikel_name}>'

class KassenTransaktion(db.Model):
    """
    TSE-Transaktionen - Technische Sicherheitseinrichtung
    
    Speichert alle TSE-signierten Transaktionen gemäß KassenSichV
    """
    __tablename__ = 'kassen_transaktionen'
    
    # Primärschlüssel
    id = db.Column(db.Integer, primary_key=True)
    
    # TSE-Identifikation
    tse_serial = db.Column(db.String(100), nullable=False, index=True)
    tse_transaktion_nummer = db.Column(db.String(100), nullable=False, unique=True, index=True)
    
    # Transaktions-Zeitstempel
    tse_start = db.Column(db.DateTime, nullable=False)
    tse_ende = db.Column(db.DateTime, nullable=False)
    
    # Signatur-Informationen
    tse_signatur_zaehler = db.Column(db.Integer, nullable=False)
    tse_signatur_algorithmus = db.Column(db.String(50), nullable=False, default='SHA256')
    tse_signatur = db.Column(db.Text, nullable=False)
    
    # Prozess-Informationen
    tse_prozess_typ = db.Column(db.String(100), nullable=False, default='Kassenbeleg-V1')
    tse_prozess_daten = db.Column(db.Text)  # JSON mit Transaktionsdaten
    tse_client_id = db.Column(db.String(50), nullable=False, default='KASSE-01')
    
    # Zeitstempel
    erstellt_am = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    def get_prozess_daten(self):
        """Gibt die Prozess-Daten als Dictionary zurück"""
        if self.tse_prozess_daten:
            try:
                return json.loads(self.tse_prozess_daten)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    def set_prozess_daten(self, data):
        """Speichert die Prozess-Daten als JSON"""
        if data is None:
            self.tse_prozess_daten = None
        else:
            self.tse_prozess_daten = json.dumps(data, ensure_ascii=False, default=str)
    
    def __repr__(self):
        return f'<KassenTransaktion {self.tse_transaktion_nummer}>'

class MwStSatz(db.Model):
    """
    Mehrwertsteuersätze - Steuerliche Konfiguration
    """
    __tablename__ = 'mwst_saetze'
    
    # Primärschlüssel
    id = db.Column(db.Integer, primary_key=True)
    
    # Steuer-Informationen
    bezeichnung = db.Column(db.String(100), nullable=False)
    satz = db.Column(db.Numeric(5, 2), nullable=False)  # z.B. 19.00 für 19%
    
    # Gültigkeitszeitraum
    gueltig_von = db.Column(db.Date, nullable=False, default=date.today)
    gueltig_bis = db.Column(db.Date, nullable=True)
    
    # Status
    aktiv = db.Column(db.Boolean, default=True)
    standard = db.Column(db.Boolean, default=False)
    
    # Verwendung
    verwendung = db.Column(db.String(100))  # normal, ermäßigt, befreit, export
    
    # Zeitstempel
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)
    erstellt_von = db.Column(db.String(100))
    
    @classmethod
    def get_standard_satz(cls):
        """Gibt den Standard-MwSt-Satz zurück"""
        return cls.query.filter_by(standard=True, aktiv=True).first()
    
    @classmethod
    def get_aktuelle_saetze(cls):
        """Gibt alle aktuell gültigen Sätze zurück"""
        heute = date.today()
        return cls.query.filter(
            cls.aktiv == True,
            cls.gueltig_von <= heute,
            db.or_(cls.gueltig_bis == None, cls.gueltig_bis >= heute)
        ).order_by(cls.satz.desc()).all()
    
    def __repr__(self):
        return f'<MwStSatz {self.bezeichnung}: {self.satz}%>'

class TSEKonfiguration(db.Model):
    """
    TSE-Konfiguration - Technische Sicherheitseinrichtung
    """
    __tablename__ = 'tse_konfigurationen'
    
    # Primärschlüssel
    id = db.Column(db.Integer, primary_key=True)
    
    # TSE-Hardware
    tse_seriennummer = db.Column(db.String(100), nullable=False, unique=True, index=True)
    tse_hersteller = db.Column(db.String(100), nullable=False)
    tse_modell = db.Column(db.String(100))
    tse_version = db.Column(db.String(50))
    
    # Zertifikat-Informationen
    zertifikat_seriennummer = db.Column(db.String(100))
    zertifikat_gueltig_von = db.Column(db.Date)
    zertifikat_gueltig_bis = db.Column(db.Date)
    
    # Konfiguration
    kassen_id = db.Column(db.String(50), nullable=False, default='KASSE-01')
    client_id = db.Column(db.String(50), nullable=False, default='CLIENT-01')
    
    # Status
    status = db.Column(db.Enum(TSEStatus), nullable=False, default=TSEStatus.AKTIV)
    aktiv = db.Column(db.Boolean, default=True)
    
    # Wartung
    letzte_wartung = db.Column(db.Date)
    naechste_wartung = db.Column(db.Date)
    wartungsnotizen = db.Column(db.Text)
    
    # Zeitstempel
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)
    aktualisiert_am = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<TSEKonfiguration {self.tse_seriennummer}>'

# Hauptmodels für Rechnungssystem
class Rechnung(db.Model):
    """
    Rechnungen - ZUGPFERD-konforme Rechnungserstellung
    """
    __tablename__ = 'rechnungen'
    
    # Primärschlüssel
    id = db.Column(db.Integer, primary_key=True)
    
    # Rechnungs-Identifikation
    rechnungsnummer = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # Kunde
    kunde_id = db.Column(db.String(50), db.ForeignKey('customers.id'), nullable=False)
    
    # Kunde-Snapshot (für unveränderliche Rechnungen)
    kunde_name = db.Column(db.String(200), nullable=False)
    kunde_adresse = db.Column(db.Text)
    kunde_email = db.Column(db.String(120))
    kunde_steuernummer = db.Column(db.String(50))
    kunde_ust_id = db.Column(db.String(50))
    
    # Rechnungs-Daten
    rechnungsdatum = db.Column(db.Date, nullable=False, default=date.today)
    leistungsdatum = db.Column(db.Date)
    faelligkeitsdatum = db.Column(db.Date)
    
    # Beträge (alle in EUR)
    netto_gesamt = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    mwst_gesamt = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    brutto_gesamt = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    
    # Rabatt
    rabatt_prozent = db.Column(db.Numeric(5, 2), default=0)
    rabatt_betrag = db.Column(db.Numeric(10, 2), default=0)
    
    # Skonto
    skonto_prozent = db.Column(db.Numeric(5, 2), default=0)
    skonto_tage = db.Column(db.Integer, default=0)
    
    # Status
    status = db.Column(db.Enum(RechnungsStatus), nullable=False, default=RechnungsStatus.ENTWURF)
    
    # ZUGPFERD-Konfiguration
    zugpferd_profil = db.Column(db.Enum(ZugpferdProfil), nullable=False, default=ZugpferdProfil.BASIC)
    zugpferd_xml = db.Column(db.Text)  # Generiertes XML
    
    # Dateien
    pdf_datei = db.Column(db.String(500))  # Pfad zur PDF-Datei
    xml_datei = db.Column(db.String(500))  # Pfad zur XML-Datei
    
    # Versand
    versendet_am = db.Column(db.DateTime)
    versendet_von = db.Column(db.String(100))
    versand_email = db.Column(db.String(120))
    
    # Zahlung
    zahlungsbedingungen = db.Column(db.Text)
    mahnstufe = db.Column(db.Integer, default=0)
    letzte_mahnung = db.Column(db.Date)
    
    # Bezahlung
    bezahlt_am = db.Column(db.Date)
    bezahlt_betrag = db.Column(db.Numeric(10, 2), default=0)
    
    # Sonstiges
    bemerkungen = db.Column(db.Text)
    interne_notizen = db.Column(db.Text)
    
    # Zeitstempel
    erstellt_am = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    erstellt_von = db.Column(db.String(100))
    bearbeitet_am = db.Column(db.DateTime, onupdate=datetime.utcnow)
    bearbeitet_von = db.Column(db.String(100))
    
    # Relationships
    kunde = db.relationship('Customer', backref='rechnungen', foreign_keys=[kunde_id])
    positionen = db.relationship('RechnungsPosition', backref='rechnung', lazy='dynamic', cascade='all, delete-orphan')
    zahlungen = db.relationship('RechnungsZahlung', backref='rechnung', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.rechnungsnummer:
            self.rechnungsnummer = self.generate_rechnungsnummer()
        
        # Fälligkeitsdatum berechnen (Standard: 14 Tage)
        if not self.faelligkeitsdatum and self.rechnungsdatum:
            self.faelligkeitsdatum = self.rechnungsdatum + timedelta(days=14)
    
    def generate_rechnungsnummer(self):
        """Generiert eindeutige Rechnungsnummer"""
        prefix = "RE"
        jahr = datetime.now().year
        monat = datetime.now().month
        
        # Hole die nächste Nummer für diesen Monat
        count = Rechnung.query.filter(
            Rechnung.rechnungsnummer.like(f"{prefix}-{jahr:04d}{monat:02d}-%")
        ).count()
        
        return f"{prefix}-{jahr:04d}{monat:02d}-{count + 1:04d}"
    
    def calculate_totals(self):
        """Berechnet Gesamtsummen aus Positionen"""
        self.netto_gesamt = sum(pos.netto_betrag for pos in self.positionen)
        self.mwst_gesamt = sum(pos.mwst_betrag for pos in self.positionen)
        
        # Rabatt abziehen
        netto_nach_rabatt = self.netto_gesamt - self.rabatt_betrag
        mwst_nach_rabatt = netto_nach_rabatt * (self.mwst_gesamt / self.netto_gesamt if self.netto_gesamt > 0 else 0)
        
        self.brutto_gesamt = netto_nach_rabatt + mwst_nach_rabatt
    
    def is_overdue(self):
        """Prüft ob die Rechnung überfällig ist"""
        return (self.status == RechnungsStatus.OFFEN and 
                self.faelligkeitsdatum and 
                self.faelligkeitsdatum < date.today())
    
    def get_open_amount(self):
        """Gibt den offenen Betrag zurück"""
        return self.brutto_gesamt - self.bezahlt_betrag
    
    def __repr__(self):
        return f'<Rechnung {self.rechnungsnummer}>'

class RechnungsPosition(db.Model):
    """
    Rechnungspositionen - Einzelne Artikel auf Rechnungen
    """
    __tablename__ = 'rechnungs_positionen'
    
    # Primärschlüssel
    id = db.Column(db.Integer, primary_key=True)
    
    # Rechnungs-Zuordnung
    rechnung_id = db.Column(db.Integer, db.ForeignKey('rechnungen.id'), nullable=False)
    position = db.Column(db.Integer, nullable=False)  # Laufende Nummer
    
    # Artikel-Informationen
    artikel_id = db.Column(db.String(50), db.ForeignKey('articles.id'), nullable=True)
    artikel_nummer = db.Column(db.String(100))  # Snapshot
    artikel_name = db.Column(db.String(200), nullable=False)  # Snapshot
    beschreibung = db.Column(db.Text)
    
    # Mengen und Preise
    menge = db.Column(db.Numeric(10, 3), nullable=False, default=1)
    einheit = db.Column(db.String(20), default='Stück')
    einzelpreis = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Steuer
    mwst_satz = db.Column(db.Numeric(5, 2), nullable=False, default=19.0)
    mwst_betrag = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Rabatt
    rabatt_prozent = db.Column(db.Numeric(5, 2), default=0)
    rabatt_betrag = db.Column(db.Numeric(10, 2), default=0)
    
    # Berechnete Beträge
    netto_betrag = db.Column(db.Numeric(10, 2), nullable=False)
    brutto_betrag = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Relationships
    artikel = db.relationship('Article', backref='rechnungs_positionen', foreign_keys=[artikel_id])
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.calculate_amounts()
    
    def calculate_amounts(self):
        """Berechnet alle Beträge basierend auf Grunddaten"""
        # Netto-Gesamtbetrag
        netto_gesamt = self.menge * self.einzelpreis
        
        # Rabatt abziehen
        self.rabatt_betrag = netto_gesamt * (self.rabatt_prozent / 100)
        self.netto_betrag = netto_gesamt - self.rabatt_betrag
        
        # MwSt berechnen
        self.mwst_betrag = self.netto_betrag * (self.mwst_satz / 100)
        
        # Brutto-Betrag
        self.brutto_betrag = self.netto_betrag + self.mwst_betrag
    
    def __repr__(self):
        return f'<RechnungsPosition {self.position}: {self.artikel_name}>'

class RechnungsZahlung(db.Model):
    """
    Rechnungs-Zahlungen - Zahlungserfassung
    """
    __tablename__ = 'rechnungs_zahlungen'
    
    # Primärschlüssel
    id = db.Column(db.Integer, primary_key=True)
    
    # Rechnungs-Zuordnung
    rechnung_id = db.Column(db.Integer, db.ForeignKey('rechnungen.id'), nullable=False)
    
    # Zahlungs-Informationen
    betrag = db.Column(db.Numeric(10, 2), nullable=False)
    zahlungsart = db.Column(db.Enum(ZahlungsArt), nullable=False)
    zahlungsdatum = db.Column(db.Date, nullable=False, default=date.today)
    
    # Zusätzliche Informationen
    referenz = db.Column(db.String(200))  # Überweisungsreferenz, etc.
    bank_name = db.Column(db.String(100))
    verwendungszweck = db.Column(db.String(200))
    
    # Skonto
    skonto_prozent = db.Column(db.Numeric(5, 2), default=0)
    skonto_betrag = db.Column(db.Numeric(10, 2), default=0)
    
    # Status
    status = db.Column(db.String(50), default='erfasst')  # erfasst, geprueft, verbucht
    
    # Notizen
    bemerkungen = db.Column(db.Text)
    
    # Zeitstempel
    erfasst_am = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    erfasst_von = db.Column(db.String(100))
    
    def __repr__(self):
        return f'<RechnungsZahlung {self.betrag}€ für {self.rechnung_id}>'

# Utility-Models
class TagesAbschluss(db.Model):
    """
    Tagesabschlüsse - Kassenbuch-Funktion
    """
    __tablename__ = 'tagesabschluesse'
    
    # Primärschlüssel
    id = db.Column(db.Integer, primary_key=True)
    
    # Datum und Kasse
    datum = db.Column(db.Date, nullable=False, index=True)
    kassen_id = db.Column(db.String(50), nullable=False, index=True)
    
    # Beleg-Statistiken
    anzahl_belege = db.Column(db.Integer, default=0)
    anzahl_stornos = db.Column(db.Integer, default=0)
    
    # Umsätze nach Zahlungsart
    umsatz_bar = db.Column(db.Numeric(10, 2), default=0)
    umsatz_ec = db.Column(db.Numeric(10, 2), default=0)
    umsatz_kreditkarte = db.Column(db.Numeric(10, 2), default=0)
    umsatz_rechnung = db.Column(db.Numeric(10, 2), default=0)
    umsatz_sonstige = db.Column(db.Numeric(10, 2), default=0)
    
    # Gesamtumsätze
    umsatz_netto = db.Column(db.Numeric(10, 2), default=0)
    umsatz_mwst = db.Column(db.Numeric(10, 2), default=0)
    umsatz_brutto = db.Column(db.Numeric(10, 2), default=0)
    
    # Kassenstand
    kassenstand_anfang = db.Column(db.Numeric(10, 2), default=0)
    kassenstand_ende = db.Column(db.Numeric(10, 2), default=0)
    
    # TSE-Informationen
    tse_von = db.Column(db.String(100))  # Erste TSE-Transaktion
    tse_bis = db.Column(db.String(100))  # Letzte TSE-Transaktion
    
    # Status
    abgeschlossen = db.Column(db.Boolean, default=False)
    geprueft = db.Column(db.Boolean, default=False)
    
    # Zeitstempel
    erstellt_am = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    erstellt_von = db.Column(db.String(100))
    abgeschlossen_am = db.Column(db.DateTime)
    abgeschlossen_von = db.Column(db.String(100))
    
    # Unique Constraint
    __table_args__ = (db.UniqueConstraint('datum', 'kassen_id'),)
    
    def __repr__(self):
        return f'<TagesAbschluss {self.datum} - {self.kassen_id}>'

class ZugpferdKonfiguration(db.Model):
    """
    ZUGPFERD-Konfiguration - Einstellungen für elektronische Rechnungen
    """
    __tablename__ = 'zugpferd_konfigurationen'
    
    # Primärschlüssel
    id = db.Column(db.Integer, primary_key=True)
    
    # Unternehmensdaten
    unternehmen_name = db.Column(db.String(200), nullable=False)
    unternehmen_adresse = db.Column(db.Text)
    unternehmen_plz = db.Column(db.String(20))
    unternehmen_ort = db.Column(db.String(100))
    unternehmen_land = db.Column(db.String(100), default='DE')
    
    # Steuerdaten
    steuernummer = db.Column(db.String(50))
    ust_id = db.Column(db.String(50))
    handelsregisternummer = db.Column(db.String(50))
    
    # Kontaktdaten
    telefon = db.Column(db.String(50))
    email = db.Column(db.String(120))
    website = db.Column(db.String(200))
    
    # Bankdaten
    bank_name = db.Column(db.String(100))
    iban = db.Column(db.String(34))
    bic = db.Column(db.String(11))
    
    # ZUGPFERD-Einstellungen
    standard_profil = db.Column(db.Enum(ZugpferdProfil), default=ZugpferdProfil.BASIC)
    xml_validierung = db.Column(db.Boolean, default=True)
    
    # Aktiv-Flag
    aktiv = db.Column(db.Boolean, default=True)
    
    # Zeitstempel
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)
    aktualisiert_am = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ZugpferdKonfiguration {self.unternehmen_name}>'

# Alle Models exportieren
__all__ = [
    'KassenBeleg', 'BelegPosition', 'KassenTransaktion', 'MwStSatz', 'TSEKonfiguration',
    'Rechnung', 'RechnungsPosition', 'RechnungsZahlung', 'TagesAbschluss', 'ZugpferdKonfiguration',
    'BelegTyp', 'ZahlungsArt', 'RechnungsStatus', 'TSEStatus', 'ZugpferdProfil'
]
