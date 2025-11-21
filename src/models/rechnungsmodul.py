# -*- coding: utf-8 -*-
"""
RECHNUNGSMODUL MODELS - Datenbank-Modelle für Rechnungs- und Kassensystem
=========================================================================
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Date, Boolean, Text, 
    ForeignKey, JSON, Numeric, UniqueConstraint, Index, CheckConstraint
)
from sqlalchemy.orm import relationship, backref
from src.models import db

# Basis für alle Models
Base = db.Model

# Flag um zu prüfen ob Models verfügbar sind
models_available = True

# Enums
class BelegTyp(Enum):
    """Belegtypen"""
    KASSENBELEG = "KASSENBELEG"
    STORNO = "STORNO"
    TRAININGSBELEG = "TRAININGSBELEG"
    NULLBELEG = "NULLBELEG"
    
class ZahlungsArt(Enum):
    """Zahlungsarten"""
    BAR = "BAR"
    EC_KARTE = "EC_KARTE"
    KREDITKARTE = "KREDITKARTE"
    SUMUP = "SUMUP"  # Hinzugefügt für die SumUp-Integration
    UEBERWEISUNG = "UEBERWEISUNG"
    PAYPAL = "PAYPAL"
    RECHNUNG = "RECHNUNG"
    SONSTIGE = "SONSTIGE"
    
class RechnungsStatus(Enum):
    """Rechnungsstatus"""
    ENTWURF = "draft"
    VERSENDET = "sent"
    BEZAHLT = "paid"
    UEBERFAELLIG = "overdue"
    STORNIERT = "cancelled"

# ... (Rest der Datei bleibt unverändert) ...
# (Hier aus Gründen der Kürze weggelassen)

# Models
class MwStSatz(Base):
    """Mehrwertsteuersätze"""
    __tablename__ = 'mwst_saetze'
    
    id = Column(Integer, primary_key=True)
    bezeichnung = Column(String(100), nullable=False)
    satz = Column(Numeric(5, 2), nullable=False)  # z.B. 19.00
    gueltig_ab = Column(Date, default=date.today)
    gueltig_bis = Column(Date, nullable=True)
    aktiv = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<MwStSatz {self.bezeichnung} ({self.satz}%)>"

class Rechnung(Base):
    """Rechnungen"""
    __tablename__ = 'rechnungen'
    
    id = Column(Integer, primary_key=True)
    rechnungsnummer = Column(String(50), unique=True, nullable=False)
    rechnungsdatum = Column(Date, default=date.today)
    faelligkeitsdatum = Column(Date, nullable=False)
    
    # Kunde
    kunde_id = Column(String(50), ForeignKey('customers.id'), nullable=False)
    kunde = relationship('Customer', backref='rechnungen')
    
    # Beträge
    summe_netto = Column(Numeric(10, 2), default=0)
    summe_mwst = Column(Numeric(10, 2), default=0)
    summe_brutto = Column(Numeric(10, 2), default=0)
    
    # Status und Details
    status = Column(String(20), default=RechnungsStatus.ENTWURF.value)
    betreff = Column(String(200))
    einleitungstext = Column(Text)
    schlusstext = Column(Text)
    interne_notiz = Column(Text)
    
    # ZUGPFERD
    zugpferd_profil = Column(String(50), default='BASIC')
    zugpferd_xml = Column(Text)
    
    # Referenzen
    auftrag_id = Column(String(50), ForeignKey('orders.id'), nullable=True)
    auftrag = relationship('Order', backref='rechnungen')
    
    # Tracking
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    erstellt_von = Column(String(100))
    geaendert_am = Column(DateTime, onupdate=datetime.utcnow)
    geaendert_von = Column(String(100))
    
    # Relationships
    positionen = relationship('RechnungsPosition', back_populates='rechnung', cascade='all, delete-orphan')
    zahlungen = relationship('RechnungsZahlung', back_populates='rechnung', cascade='all, delete-orphan')
    
    def ist_ueberfaellig(self):
        """Prüfe ob Rechnung überfällig ist"""
        if self.status in [RechnungsStatus.BEZAHLT.value, RechnungsStatus.STORNIERT.value]:
            return False
        return date.today() > self.faelligkeitsdatum
        
    def tage_ueberfaellig(self):
        """Anzahl Tage überfällig"""
        if not self.ist_ueberfaellig():
            return 0
        return (date.today() - self.faelligkeitsdatum).days
        
    def offener_betrag(self):
        """Berechne offenen Betrag"""
        gezahlt = sum(z.betrag for z in self.zahlungen if z.bestaetigt)
        return self.summe_brutto - gezahlt

class RechnungsPosition(Base):
    """Rechnungspositionen"""
    __tablename__ = 'rechnungs_positionen'
    
    id = Column(Integer, primary_key=True)
    rechnung_id = Column(Integer, ForeignKey('rechnungen.id'), nullable=False)
    rechnung = relationship('Rechnung', back_populates='positionen')
    
    position = Column(Integer, nullable=False)
    artikel_id = Column(Integer, ForeignKey('articles.id'), nullable=True)
    artikel = relationship('Article')
    
    bezeichnung = Column(String(500), nullable=False)
    menge = Column(Numeric(10, 3), nullable=False)
    einheit = Column(String(20), default='Stk.')
    einzelpreis = Column(Numeric(10, 2), nullable=False)
    
    rabatt_prozent = Column(Numeric(5, 2), default=0)
    rabatt_betrag = Column(Numeric(10, 2), default=0)
    
    mwst_satz_id = Column(Integer, ForeignKey('mwst_saetze.id'), nullable=False)
    mwst_satz = relationship('MwStSatz')
    
    netto_gesamt = Column(Numeric(10, 2), nullable=False)
    mwst_betrag = Column(Numeric(10, 2), nullable=False)
    brutto_gesamt = Column(Numeric(10, 2), nullable=False)
    
    # Unique constraint für Position pro Rechnung
    __table_args__ = (
        UniqueConstraint('rechnung_id', 'position'),
    )

class RechnungsZahlung(Base):
    """Zahlungen zu Rechnungen"""
    __tablename__ = 'rechnungs_zahlungen'
    
    id = Column(Integer, primary_key=True)
    rechnung_id = Column(Integer, ForeignKey('rechnungen.id'), nullable=False)
    rechnung = relationship('Rechnung', back_populates='zahlungen')
    
    zahlungsdatum = Column(Date, nullable=False)
    betrag = Column(Numeric(10, 2), nullable=False)
    zahlungsart = Column(String(50), nullable=False)
    
    referenz = Column(String(200))
    notiz = Column(Text)
    bestaetigt = Column(Boolean, default=False)
    
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    erstellt_von = Column(String(100))

class TSEKonfiguration(Base):
    """TSE-Konfiguration für Kassensystem"""
    __tablename__ = 'tse_konfiguration'
    
    id = Column(Integer, primary_key=True)
    serial_number = Column(String(100), unique=True, nullable=False)
    public_key = Column(Text)
    certificate = Column(Text)
    
    aktiv = Column(Boolean, default=True)
    hersteller = Column(String(100))
    modell = Column(String(100))
    firmware_version = Column(String(50))
    
    letzte_pruefung = Column(DateTime)
    naechste_wartung = Column(Date)
    
    konfiguration = Column(JSON)  # Zusätzliche Konfig-Parameter
    
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    geaendert_am = Column(DateTime, onupdate=datetime.utcnow)

class KassenBeleg(Base):
    """Kassenbelege"""
    __tablename__ = 'kassen_belege'
    
    id = Column(Integer, primary_key=True)
    belegnummer = Column(String(50), unique=True, nullable=False)
    belegtyp = Column(String(20), default=BelegTyp.KASSENBELEG.value)
    
    kasse_id = Column(String(50), nullable=False)  # Terminal-ID
    kassierer_id = Column(String(100), ForeignKey('users.username'), nullable=False)
    kassierer = relationship('User', backref='kassenbelege')
    
    kunde_id = Column(String(50), ForeignKey('customers.id'), nullable=True)
    kunde = relationship('Customer', backref='kassenbelege')
    
    # Beträge
    summe_netto = Column(Numeric(10, 2), default=0)
    summe_mwst = Column(Numeric(10, 2), default=0)
    summe_brutto = Column(Numeric(10, 2), default=0)
    
    # TSE-Daten
    tse_transaktion_nummer = Column(String(100))
    tse_start = Column(DateTime)
    tse_ende = Column(DateTime)
    tse_serial = Column(String(100))
    tse_signatur_zaehler = Column(Integer)
    tse_signatur = Column(Text)
    tse_fehler = Column(Text)  # Falls TSE-Ausfall
    
    # Storno
    storniert = Column(Boolean, default=False)
    storno_beleg_id = Column(Integer, ForeignKey('kassen_belege.id'), nullable=True)
    storno_beleg = relationship('KassenBeleg', remote_side=[id])
    storno_grund = Column(String(200))
    
    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    positionen = relationship('BelegPosition', back_populates='beleg', cascade='all, delete-orphan')
    transaktionen = relationship('KassenTransaktion', back_populates='beleg', cascade='all, delete-orphan')
    
    # Index für Performance
    __table_args__ = (
        Index('idx_beleg_datum', 'erstellt_am'),
        Index('idx_beleg_kassierer', 'kassierer_id'),
    )

class BelegPosition(Base):
    """Positionen auf Kassenbelegen"""
    __tablename__ = 'beleg_positionen'
    
    id = Column(Integer, primary_key=True)
    beleg_id = Column(Integer, ForeignKey('kassen_belege.id'), nullable=False)
    beleg = relationship('KassenBeleg', back_populates='positionen')
    
    position = Column(Integer, nullable=False)
    artikel_id = Column(Integer, ForeignKey('articles.id'), nullable=True)
    artikel = relationship('Article')
    
    bezeichnung = Column(String(500), nullable=False)
    menge = Column(Numeric(10, 3), nullable=False)
    einzelpreis = Column(Numeric(10, 2), nullable=False)
    
    rabatt_prozent = Column(Numeric(5, 2), default=0)
    
    mwst_satz = Column(Numeric(5, 2), nullable=False)  # Direkt gespeichert für Historie
    
    netto_gesamt = Column(Numeric(10, 2), nullable=False)
    mwst_betrag = Column(Numeric(10, 2), nullable=False)
    brutto_gesamt = Column(Numeric(10, 2), nullable=False)
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('beleg_id', 'position'),
    )

class KassenTransaktion(Base):
    """Zahlungstransaktionen pro Beleg"""
    __tablename__ = 'kassen_transaktionen'
    
    id = Column(Integer, primary_key=True)
    beleg_id = Column(Integer, ForeignKey('kassen_belege.id'), nullable=False)
    beleg = relationship('KassenBeleg', back_populates='transaktionen')
    
    zahlungsart = Column(String(20), nullable=False)
    betrag = Column(Numeric(10, 2), nullable=False)
    
    # Für Kartenzahlungen
    terminal_id = Column(String(50))
    transaktions_id = Column(String(100))
    autorisierungs_code = Column(String(50))
    
    erstellt_am = Column(DateTime, default=datetime.utcnow)

class Tagesabschluss(Base):
    """Tagesabschlüsse (Z-Berichte)"""
    __tablename__ = 'tagesabschluesse'
    
    id = Column(Integer, primary_key=True)
    datum = Column(Date, nullable=False)
    kasse_id = Column(String(50), nullable=False)
    z_nummer = Column(Integer, nullable=False)  # Fortlaufende Z-Nummer
    
    kassierer_id = Column(String(100), ForeignKey('users.username'), nullable=False)
    kassierer = relationship('User')
    
    # Belege
    erster_beleg = Column(String(50))
    letzter_beleg = Column(String(50))
    anzahl_belege = Column(Integer, default=0)
    anzahl_stornos = Column(Integer, default=0)
    
    # Umsätze nach Zahlungsart
    umsatz_bar = Column(Numeric(10, 2), default=0)
    umsatz_karte = Column(Numeric(10, 2), default=0)
    umsatz_sonstige = Column(Numeric(10, 2), default=0)
    umsatz_gesamt_brutto = Column(Numeric(10, 2), default=0)
    
    # Steuern
    umsatz_steuersatz_normal = Column(Numeric(10, 2), default=0)
    umsatz_steuersatz_ermaessigt = Column(Numeric(10, 2), default=0)
    umsatz_steuerfrei = Column(Numeric(10, 2), default=0)
    
    steuer_normal = Column(Numeric(10, 2), default=0)
    steuer_ermaessigt = Column(Numeric(10, 2), default=0)
    
    # Kassenzählung
    kassenstand_soll = Column(Numeric(10, 2), default=0)
    kassenstand_ist = Column(Numeric(10, 2), default=0)
    differenz = Column(Numeric(10, 2), default=0)
    
    # TSE-Signatur
    tse_serial = Column(String(100))
    tse_signatur = Column(Text)
    tse_signatur_zaehler = Column(Integer)
    
    # Status
    abgeschlossen = Column(Boolean, default=False)
    abschluss_zeit = Column(DateTime)
    
    # JSON für erweiterte Daten
    zusatzdaten = Column(JSON)
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('datum', 'kasse_id'),
        UniqueConstraint('kasse_id', 'z_nummer'),
    )
    
    def __repr__(self):
        return f"<Tagesabschluss {self.datum} Kasse:{self.kasse_id}>"
