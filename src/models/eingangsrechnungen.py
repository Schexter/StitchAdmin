# -*- coding: utf-8 -*-
"""
EINGANGSRECHNUNGEN & VERBINDLICHKEITEN
======================================
Verwaltung von:
- Eingangsrechnungen (Lieferanten)
- Eigene Ratenzahlungen (Verbindlichkeiten)
- Fälligkeitsüberwachung
- Skonto-Berechnung
- Kalender-Integration

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, List, Optional
from src.models import db

import logging
logger = logging.getLogger(__name__)


class ZahlungsStatus(Enum):
    """Status einer Ein-/Ausgangsrechnung"""
    OFFEN = "offen"
    TEILBEZAHLT = "teilbezahlt"
    BEZAHLT = "bezahlt"
    UEBERFAELLIG = "ueberfaellig"
    GEMAHNT = "gemahnt"
    STORNIERT = "storniert"


class Eingangsrechnung(db.Model):
    """
    Eingangsrechnungen von Lieferanten
    """
    __tablename__ = 'eingangsrechnungen'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Rechnungsdaten
    rechnungsnummer = db.Column(db.String(100), nullable=False)
    rechnungsdatum = db.Column(db.Date, nullable=False)
    eingangsdatum = db.Column(db.Date, default=date.today)
    
    # Lieferant
    lieferant_id = db.Column(db.Integer, db.ForeignKey('lieferanten.id'))
    lieferant_name = db.Column(db.String(200))  # Fallback
    
    # Beträge
    nettobetrag = db.Column(db.Numeric(12, 2), nullable=False)
    mwst_satz = db.Column(db.Numeric(5, 2), default=19.0)
    mwst_betrag = db.Column(db.Numeric(12, 2))
    bruttobetrag = db.Column(db.Numeric(12, 2), nullable=False)
    
    # Zahlungsbedingungen
    zahlungsziel_tage = db.Column(db.Integer, default=30)
    faelligkeitsdatum = db.Column(db.Date)
    skonto_prozent = db.Column(db.Numeric(5, 2), default=0)
    skonto_tage = db.Column(db.Integer, default=0)
    skonto_datum = db.Column(db.Date)
    
    # Zahlung
    status = db.Column(db.String(30), default='offen')
    bezahlt_am = db.Column(db.Date)
    bezahlt_betrag = db.Column(db.Numeric(12, 2), default=0)
    offener_betrag = db.Column(db.Numeric(12, 2))
    skonto_genutzt = db.Column(db.Boolean, default=False)
    
    # Ratenzahlung
    ist_ratenzahlung = db.Column(db.Boolean, default=False)
    anzahl_raten = db.Column(db.Integer)
    rate_betrag = db.Column(db.Numeric(12, 2))
    
    # Kategorisierung
    kategorie = db.Column(db.String(100))  # Material, Maschinen, Miete, etc.
    kostenstelle = db.Column(db.String(50))
    buchungskonto = db.Column(db.String(20))  # SKR03 Konto
    
    # Dokument
    dokument_pfad = db.Column(db.String(500))
    notizen = db.Column(db.Text)
    
    # Tracking
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)
    aktualisiert_am = db.Column(db.DateTime, onupdate=datetime.utcnow)
    erstellt_von = db.Column(db.String(100))
    
    # Beziehungen
    lieferant = db.relationship('Lieferant', backref='eingangsrechnungen')
    zahlungen = db.relationship('EingangsrechnungZahlung', backref='rechnung', 
                                cascade='all, delete-orphan')
    raten = db.relationship('EigeneRate', backref='eingangsrechnung',
                           cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Eingangsrechnung {self.rechnungsnummer}>"
    
    def berechne_faelligkeit(self):
        """Berechnet Fälligkeits- und Skontodatum"""
        if self.rechnungsdatum:
            self.faelligkeitsdatum = self.rechnungsdatum + timedelta(days=self.zahlungsziel_tage or 30)
            if self.skonto_tage:
                self.skonto_datum = self.rechnungsdatum + timedelta(days=self.skonto_tage)
    
    @property
    def ist_ueberfaellig(self) -> bool:
        if self.status in ['bezahlt', 'storniert']:
            return False
        return self.faelligkeitsdatum and self.faelligkeitsdatum < date.today()
    
    @property
    def tage_ueberfaellig(self) -> int:
        if not self.ist_ueberfaellig:
            return 0
        return (date.today() - self.faelligkeitsdatum).days
    
    @property
    def skonto_moeglich(self) -> bool:
        if not self.skonto_datum or self.skonto_prozent <= 0:
            return False
        return date.today() <= self.skonto_datum
    
    @property
    def skonto_betrag(self) -> Decimal:
        if not self.skonto_prozent:
            return Decimal('0')
        return (self.bruttobetrag * self.skonto_prozent / 100).quantize(Decimal('0.01'))
    
    @property
    def betrag_mit_skonto(self) -> Decimal:
        return self.bruttobetrag - self.skonto_betrag


class EingangsrechnungZahlung(db.Model):
    """Teilzahlungen für Eingangsrechnungen"""
    __tablename__ = 'eingangsrechnung_zahlungen'
    
    id = db.Column(db.Integer, primary_key=True)
    eingangsrechnung_id = db.Column(db.Integer, db.ForeignKey('eingangsrechnungen.id'), nullable=False)
    
    datum = db.Column(db.Date, nullable=False, default=date.today)
    betrag = db.Column(db.Numeric(12, 2), nullable=False)
    zahlungsart = db.Column(db.String(50))  # Überweisung, Lastschrift, Bar
    referenz = db.Column(db.String(100))  # Verwendungszweck/Referenz
    
    ist_skonto = db.Column(db.Boolean, default=False)
    skonto_betrag = db.Column(db.Numeric(12, 2), default=0)
    
    notiz = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class EigeneRate(db.Model):
    """
    Eigene Ratenzahlungen (Verbindlichkeiten)
    z.B. Maschinenfinanzierung, Leasingraten
    """
    __tablename__ = 'eigene_raten'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Verknüpfung
    eingangsrechnung_id = db.Column(db.Integer, db.ForeignKey('eingangsrechnungen.id'))
    lieferant_id = db.Column(db.Integer, db.ForeignKey('lieferanten.id'))
    
    # Bezeichnung
    bezeichnung = db.Column(db.String(200), nullable=False)
    beschreibung = db.Column(db.Text)
    
    # Ratendetails
    rate_nummer = db.Column(db.Integer)
    gesamt_raten = db.Column(db.Integer)
    
    faelligkeitsdatum = db.Column(db.Date, nullable=False)
    betrag = db.Column(db.Numeric(12, 2), nullable=False)
    
    # Status
    status = db.Column(db.String(30), default='offen')
    bezahlt_am = db.Column(db.Date)
    
    # Kalender-Verknüpfung
    kalender_termin_id = db.Column(db.Integer, db.ForeignKey('kalender_termine.id'))
    
    # Kategorisierung
    kategorie = db.Column(db.String(100))  # Leasing, Finanzierung, Miete
    buchungskonto = db.Column(db.String(20))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Beziehungen
    lieferant = db.relationship('Lieferant', backref='raten')
    kalender_termin = db.relationship('KalenderTermin', backref='eigene_rate')


class Lieferant(db.Model):
    """Lieferanten-Stammdaten"""
    __tablename__ = 'lieferanten'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Stammdaten
    nummer = db.Column(db.String(50), unique=True)
    name = db.Column(db.String(200), nullable=False)
    
    # Adresse
    strasse = db.Column(db.String(200))
    plz = db.Column(db.String(10))
    ort = db.Column(db.String(100))
    land = db.Column(db.String(50), default='Deutschland')
    
    # Kontakt
    telefon = db.Column(db.String(50))
    email = db.Column(db.String(200))
    ansprechpartner = db.Column(db.String(100))
    website = db.Column(db.String(200))
    
    # Zahlungsbedingungen (Standard)
    standard_zahlungsziel = db.Column(db.Integer, default=30)
    standard_skonto_prozent = db.Column(db.Numeric(5, 2), default=0)
    standard_skonto_tage = db.Column(db.Integer, default=0)
    
    # Bankverbindung
    iban = db.Column(db.String(34))
    bic = db.Column(db.String(11))
    bank = db.Column(db.String(100))
    
    # Steuer
    ust_id = db.Column(db.String(50))
    steuernummer = db.Column(db.String(50))
    
    # Kategorisierung
    kategorie = db.Column(db.String(100))  # Textilien, Garne, Maschinen, etc.
    buchungskonto = db.Column(db.String(20))  # Standard-Konto
    
    # Status
    ist_aktiv = db.Column(db.Boolean, default=True)
    notizen = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Lieferant {self.name}>"


# ============================================================================
# STANDARD-KATEGORIEN
# ============================================================================

EINGANGSRECHNUNG_KATEGORIEN = [
    {'key': 'textilien', 'name': 'Textilien & Rohlinge', 'konto': '3200'},
    {'key': 'garne', 'name': 'Stickgarne', 'konto': '3500'},
    {'key': 'folien', 'name': 'Flex-/Flockfolien', 'konto': '3510'},
    {'key': 'farben', 'name': 'Druckfarben & Tinten', 'konto': '3530'},
    {'key': 'verbrauch', 'name': 'Verbrauchsmaterial', 'konto': '3000'},
    {'key': 'maschinen', 'name': 'Maschinen & Geräte', 'konto': '0400'},
    {'key': 'wartung', 'name': 'Wartung & Reparatur', 'konto': '4800'},
    {'key': 'miete', 'name': 'Miete & Nebenkosten', 'konto': '4210'},
    {'key': 'leasing', 'name': 'Leasing', 'konto': '4830'},
    {'key': 'versicherung', 'name': 'Versicherungen', 'konto': '4300'},
    {'key': 'software', 'name': 'Software & Lizenzen', 'konto': '4820'},
    {'key': 'buero', 'name': 'Bürobedarf', 'konto': '4750'},
    {'key': 'sonstiges', 'name': 'Sonstiges', 'konto': '4900'},
]
