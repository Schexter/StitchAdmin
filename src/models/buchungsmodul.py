# -*- coding: utf-8 -*-
"""
Buchungsmodul - SKR03 Kontenrahmen & Doppelte Buchführung

Erstellt von: Hans Hahn - Alle Rechte vorbehalten
Datum: 25. November 2025
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, Date, Text, ForeignKey
from sqlalchemy.orm import relationship
from src.models import db

class KontoArt(str, Enum):
    """Kontoarten im Kontenrahmen"""
    AKTIVA = 'Aktiva'
    PASSIVA = 'Passiva'
    ERLOESE = 'Erlöse'
    AUFWAND = 'Aufwand'
    NEUTRAL = 'Neutral'

class Kontenrahmen(db.Model):
    """
    Kontenrahmen-Stammdaten (SKR03, SKR04, etc.)
    """
    __tablename__ = 'kontenrahmen'
    
    id = Column(Integer, primary_key=True)
    kontenrahmen_typ = Column(String(10), nullable=False, default='SKR03')  # SKR03, SKR04, IKR
    konto_nummer = Column(String(10), unique=True, nullable=False, index=True)
    konto_bezeichnung = Column(String(255), nullable=False)
    konto_art = Column(String(50), nullable=False)  # Aktiva, Passiva, Erlöse, Aufwand
    steuer_relevant = Column(Boolean, default=False)
    steuer_satz = Column(Numeric(5, 2), default=0)  # 19.00, 7.00, 0.00
    verwendung = Column(Text)  # Beschreibung der Verwendung
    aktiv = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # Beziehungen
    buchungen_soll = relationship('Buchung', foreign_keys='Buchung.konto_soll_id', back_populates='konto_soll_ref')
    buchungen_haben = relationship('Buchung', foreign_keys='Buchung.konto_haben_id', back_populates='konto_haben_ref')
    
    def __repr__(self):
        return f'<Konto {self.konto_nummer} - {self.konto_bezeichnung}>'
    
    @property
    def display_name(self):
        """Anzeigename für Dropdown"""
        return f'{self.konto_nummer} - {self.konto_bezeichnung}'
    
    def get_saldo(self, datum_von=None, datum_bis=None):
        """Berechnet Saldo des Kontos"""
        from sqlalchemy import func
        
        query_soll = db.session.query(func.sum(Buchung.betrag)).filter(
            Buchung.konto_soll == self.konto_nummer,
            Buchung.storniert == False
        )
        query_haben = db.session.query(func.sum(Buchung.betrag)).filter(
            Buchung.konto_haben == self.konto_nummer,
            Buchung.storniert == False
        )
        
        if datum_von:
            query_soll = query_soll.filter(Buchung.buchungsdatum >= datum_von)
            query_haben = query_haben.filter(Buchung.buchungsdatum >= datum_von)
        if datum_bis:
            query_soll = query_soll.filter(Buchung.buchungsdatum <= datum_bis)
            query_haben = query_haben.filter(Buchung.buchungsdatum <= datum_bis)
        
        soll_summe = query_soll.scalar() or Decimal('0')
        haben_summe = query_haben.scalar() or Decimal('0')
        
        # Aktiv-Konten: Saldo = Soll - Haben
        # Passiv-Konten: Saldo = Haben - Soll
        if self.konto_art in ['Aktiva', 'Aufwand']:
            return soll_summe - haben_summe
        else:
            return haben_summe - soll_summe

class Buchung(db.Model):
    """
    Buchungen nach SKR03
    Jede Transaktion erzeugt eine Buchung (Soll an Haben)
    """
    __tablename__ = 'buchungen'
    
    id = Column(Integer, primary_key=True)
    buchungsdatum = Column(Date, nullable=False, index=True)
    belegnummer = Column(String(50), nullable=False, index=True)
    
    # Konten (als String-Referenz für Flexibilität)
    konto_soll = Column(String(10), nullable=False, index=True)
    konto_haben = Column(String(10), nullable=False, index=True)
    
    # Konten (als FK für Beziehungen)
    konto_soll_id = Column(Integer, ForeignKey('kontenrahmen.id'))
    konto_haben_id = Column(Integer, ForeignKey('kontenrahmen.id'))
    
    # Beträge
    betrag = Column(Numeric(10, 2), nullable=False)
    steuer_betrag = Column(Numeric(10, 2), default=0)
    
    # Beschreibung
    buchungstext = Column(Text)
    beleg_typ = Column(String(50))  # 'Verkauf', 'Einkauf', 'Zahlung', 'Steuer'
    
    # Referenzen zu anderen Tabellen
    beleg_id = Column(Integer)  # ID des Kassenbelegs oder Rechnung
    beleg_tabelle = Column(String(50))  # 'kassenbeleg', 'rechnung', etc.
    
    # Kostenstelle (optional für erweiterte Auswertungen)
    kostenstelle = Column(String(50))
    
    # Audit-Trail
    created_at = Column(DateTime, default=datetime.now)
    created_by = Column(String(50))
    
    # Stornierung
    storniert = Column(Boolean, default=False)
    storno_buchung_id = Column(Integer, ForeignKey('buchungen.id'))
    storno_grund = Column(Text)
    storniert_am = Column(DateTime)
    
    # Beziehungen
    konto_soll_ref = relationship('Kontenrahmen', foreign_keys=[konto_soll_id], back_populates='buchungen_soll')
    konto_haben_ref = relationship('Kontenrahmen', foreign_keys=[konto_haben_id], back_populates='buchungen_haben')
    
    def __repr__(self):
        return f'<Buchung {self.belegnummer}: {self.konto_soll} an {self.konto_haben} = {self.betrag}>'
    
    def stornieren(self, grund, user):
        """Storniert diese Buchung durch Gegenbuchung"""
        if self.storniert:
            raise ValueError('Buchung ist bereits storniert')
        
        # Erstelle Storno-Buchung (umgekehrte Buchung)
        storno = Buchung(
            buchungsdatum=date.today(),
            belegnummer=f'STORNO-{self.belegnummer}',
            konto_soll=self.konto_haben,  # Vertauscht!
            konto_haben=self.konto_soll,  # Vertauscht!
            betrag=self.betrag,
            steuer_betrag=self.steuer_betrag,
            buchungstext=f'Storno: {self.buchungstext}',
            beleg_typ='Storno',
            created_by=user,
            storno_buchung_id=self.id
        )
        
        # Markiere Original als storniert
        self.storniert = True
        self.storno_grund = grund
        self.storniert_am = datetime.now()
        
        db.session.add(storno)
        return storno

class ZahlungsartKontoMapping(db.Model):
    """
    Mapping von Zahlungsarten zu Konten
    Definiert, auf welches Konto eine Zahlungsart gebucht wird
    """
    __tablename__ = 'zahlungsart_konto_mapping'
    
    id = Column(Integer, primary_key=True)
    zahlungsart = Column(String(50), unique=True, nullable=False)  # 'BAR', 'EC', 'RECHNUNG', 'SUMUP'
    konto_nummer = Column(String(10), nullable=False)  # Ziel-Konto
    beschreibung = Column(Text)
    aktiv = Column(Boolean, default=True)
    
    def __repr__(self):
        return f'<Mapping {self.zahlungsart} → Konto {self.konto_nummer}>'
    
    @staticmethod
    def get_konto_fuer_zahlungsart(zahlungsart):
        """Gibt Konto-Nummer für Zahlungsart zurück"""
        mapping = ZahlungsartKontoMapping.query.filter_by(
            zahlungsart=zahlungsart,
            aktiv=True
        ).first()
        
        if mapping:
            return mapping.konto_nummer
        
        # Fallback zu Standardwerten
        defaults = {
            'BAR': '1000',  # Kasse
            'EC': '1200',   # Bank
            'SUMUP': '1200',  # Bank
            'RECHNUNG': '1400'  # Forderungen
        }
        return defaults.get(zahlungsart, '1000')
