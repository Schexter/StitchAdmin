# -*- coding: utf-8 -*-
"""
NUMMERNKREISE - GoBD-konforme Belegnummern-Verwaltung
=====================================================
StitchAdmin 2.0

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime, date
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.exc import IntegrityError
from src.models import db
import threading

# Thread-Lock für sichere Nummernvergabe
_nummer_lock = threading.Lock()


class Nummernkreis(db.Model):
    """
    Konfiguration der Nummernkreise für alle Belegarten
    
    Beispiel:
        nk = Nummernkreis.query.filter_by(belegart='rechnung').first()
        neue_nummer = nk.naechste_nummer()  # 'RE-2025-0001'
    """
    __tablename__ = 'nummernkreise'
    
    id = Column(Integer, primary_key=True)
    
    # Belegart (eindeutig)
    belegart = Column(String(30), unique=True, nullable=False)
    # 'angebot', 'auftragsbestaetigung', 'auftrag', 'lieferschein', 
    # 'rechnung', 'anzahlung', 'gutschrift', 'kassenbeleg'
    
    # Bezeichnung für UI
    bezeichnung = Column(String(100), nullable=False)
    
    # Präfix
    praefix = Column(String(10), nullable=False)  # z.B. 'AN', 'RE', 'LS'
    
    # Aktueller Stand
    aktuelles_jahr = Column(Integer, nullable=False)
    aktuelle_nummer = Column(Integer, default=0)
    
    # Format-Optionen
    stellen = Column(Integer, default=4)  # Anzahl Ziffern (0001 vs 000001)
    trennzeichen = Column(String(5), default='-')
    jahr_format = Column(String(10), default='YYYY')  # 'YYYY' oder 'YY'
    
    # Verhalten
    jahreswechsel_reset = Column(Boolean, default=True)  # Bei neuem Jahr auf 1 zurücksetzen
    aktiv = Column(Boolean, default=True)
    
    # Tracking
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    geaendert_am = Column(DateTime, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Nummernkreis {self.belegart}: {self.praefix}-{self.aktuelles_jahr}-{self.aktuelle_nummer}>"
    
    def naechste_nummer(self, commit=True):
        """
        Generiert die nächste Belegnummer (Thread-safe)
        
        Args:
            commit: Änderung sofort in DB speichern (default: True)
        
        Returns:
            str: Formatierte Belegnummer, z.B. 'RE-2025-0001'
        
        Raises:
            ValueError: Wenn Nummernkreis nicht aktiv
        """
        if not self.aktiv:
            raise ValueError(f"Nummernkreis '{self.belegart}' ist nicht aktiv")
        
        with _nummer_lock:
            aktuelles_jahr = datetime.now().year
            
            # Jahreswechsel prüfen
            if self.jahreswechsel_reset and self.aktuelles_jahr != aktuelles_jahr:
                self.aktuelles_jahr = aktuelles_jahr
                self.aktuelle_nummer = 0
            
            # Nummer erhöhen
            self.aktuelle_nummer += 1
            
            # Formatieren
            if self.jahr_format == 'YY':
                jahr_str = str(self.aktuelles_jahr)[-2:]
            else:
                jahr_str = str(self.aktuelles_jahr)
            
            nummer_str = str(self.aktuelle_nummer).zfill(self.stellen)
            
            belegnummer = f"{self.praefix}{self.trennzeichen}{jahr_str}{self.trennzeichen}{nummer_str}"
            
            if commit:
                db.session.commit()
            
            return belegnummer
    
    def vorschau_naechste(self):
        """
        Zeigt die nächste Nummer ohne sie zu vergeben
        
        Returns:
            str: Vorschau der nächsten Nummer
        """
        aktuelles_jahr = datetime.now().year
        
        # Jahreswechsel simulieren
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
    
    def reset_fuer_jahr(self, jahr=None):
        """
        Setzt den Nummernkreis für ein neues Jahr zurück
        
        Args:
            jahr: Zieljahr (default: aktuelles Jahr)
        """
        if jahr is None:
            jahr = datetime.now().year
        
        self.aktuelles_jahr = jahr
        self.aktuelle_nummer = 0
        db.session.commit()
    
    @classmethod
    def get_oder_erstellen(cls, belegart):
        """
        Holt einen Nummernkreis oder erstellt ihn mit Standardwerten
        
        Args:
            belegart: Name der Belegart
        
        Returns:
            Nummernkreis: Instanz
        """
        nk = cls.query.filter_by(belegart=belegart).first()
        
        if not nk:
            # Standardkonfigurationen
            defaults = {
                'angebot': ('AN', 'Angebote', 4),
                'auftragsbestaetigung': ('AB', 'Auftragsbestätigungen', 4),
                'auftrag': ('A', 'Aufträge (intern)', 4),
                'lieferschein': ('LS', 'Lieferscheine', 4),
                'rechnung': ('RE', 'Rechnungen', 4),
                'anzahlung': ('AR', 'Anzahlungsrechnungen', 4),
                'gutschrift': ('GS', 'Gutschriften', 4),
                'kassenbeleg': ('K', 'Kassenbelege', 6),
            }
            
            if belegart in defaults:
                praefix, bezeichnung, stellen = defaults[belegart]
            else:
                praefix = belegart[:2].upper()
                bezeichnung = belegart.title()
                stellen = 4
            
            nk = cls(
                belegart=belegart,
                bezeichnung=bezeichnung,
                praefix=praefix,
                aktuelles_jahr=datetime.now().year,
                aktuelle_nummer=0,
                stellen=stellen
            )
            db.session.add(nk)
            db.session.commit()
        
        return nk
    
    @classmethod
    def neue_belegnummer(cls, belegart):
        """
        Shortcut: Generiert direkt eine neue Belegnummer
        
        Args:
            belegart: Name der Belegart
        
        Returns:
            str: Neue Belegnummer
        
        Beispiel:
            nummer = Nummernkreis.neue_belegnummer('rechnung')
            # 'RE-2025-0001'
        """
        nk = cls.get_oder_erstellen(belegart)
        return nk.naechste_nummer()


class Zahlungsbedingung(db.Model):
    """
    Vordefinierte Zahlungsbedingungen
    
    Beispiele:
        - "14 Tage netto"
        - "30 Tage mit 2% Skonto bei Zahlung innerhalb 7 Tagen"
        - "50% Anzahlung bei Auftragserteilung"
    """
    __tablename__ = 'zahlungsbedingungen'
    
    id = Column(Integer, primary_key=True)
    
    # Bezeichnung
    bezeichnung = Column(String(100), nullable=False)
    kurztext = Column(String(50))  # Für Dropdown
    
    # Zahlungsziel
    zahlungsziel_tage = Column(Integer, default=14)
    
    # Skonto
    skonto_prozent = Column(Integer, default=0)  # In Ganzzahl (2 = 2%)
    skonto_tage = Column(Integer, default=0)
    
    # Anzahlung
    anzahlung_erforderlich = Column(Boolean, default=False)
    anzahlung_prozent = Column(Integer, default=0)  # z.B. 50
    anzahlung_text = Column(String(200))
    
    # Texte für Dokumente
    text_rechnung = Column(Text)
    text_angebot = Column(Text)
    
    # Status
    aktiv = Column(Boolean, default=True)
    standard = Column(Boolean, default=False)  # Default für neue Dokumente
    sortierung = Column(Integer, default=0)
    
    # Tracking
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Zahlungsbedingung {self.bezeichnung}>"
    
    def generiere_text(self):
        """
        Generiert den Zahlungstext für Dokumente
        
        Returns:
            str: Formatierter Zahlungstext
        """
        teile = []
        
        if self.skonto_prozent and self.skonto_tage:
            teile.append(
                f"Bei Zahlung innerhalb von {self.skonto_tage} Tagen "
                f"gewähren wir {self.skonto_prozent}% Skonto."
            )
        
        if self.zahlungsziel_tage:
            teile.append(
                f"Zahlbar innerhalb von {self.zahlungsziel_tage} Tagen ohne Abzug."
            )
        
        if self.anzahlung_erforderlich and self.anzahlung_prozent:
            teile.append(
                f"Anzahlung: {self.anzahlung_prozent}% bei Auftragserteilung."
            )
        
        return " ".join(teile) if teile else self.text_rechnung or ""
    
    def berechne_faelligkeit(self, belegdatum=None):
        """
        Berechnet das Fälligkeitsdatum
        
        Args:
            belegdatum: Datum des Belegs (default: heute)
        
        Returns:
            date: Fälligkeitsdatum
        """
        from datetime import timedelta
        
        if belegdatum is None:
            belegdatum = date.today()
        
        return belegdatum + timedelta(days=self.zahlungsziel_tage)
    
    def berechne_skonto_datum(self, belegdatum=None):
        """
        Berechnet das letzte Datum für Skonto
        
        Args:
            belegdatum: Datum des Belegs (default: heute)
        
        Returns:
            date or None: Skonto-Datum oder None wenn kein Skonto
        """
        from datetime import timedelta
        
        if not self.skonto_tage or not self.skonto_prozent:
            return None
        
        if belegdatum is None:
            belegdatum = date.today()
        
        return belegdatum + timedelta(days=self.skonto_tage)
    
    @classmethod
    def get_standard(cls):
        """Holt die Standard-Zahlungsbedingung"""
        return cls.query.filter_by(standard=True, aktiv=True).first()
    
    @classmethod
    def get_aktive(cls):
        """Holt alle aktiven Zahlungsbedingungen sortiert"""
        return cls.query.filter_by(aktiv=True).order_by(cls.sortierung).all()


# ============================================================
# Initialisierungs-Funktionen
# ============================================================

def init_nummernkreise():
    """
    Initialisiert alle Standard-Nummernkreise
    (Wird beim ersten Start aufgerufen)
    """
    standard_kreise = [
        {
            'belegart': 'angebot',
            'bezeichnung': 'Angebote',
            'praefix': 'AN',
            'stellen': 4
        },
        {
            'belegart': 'auftragsbestaetigung',
            'bezeichnung': 'Auftragsbestätigungen',
            'praefix': 'AB',
            'stellen': 4
        },
        {
            'belegart': 'auftrag',
            'bezeichnung': 'Aufträge (intern)',
            'praefix': 'A',
            'stellen': 4
        },
        {
            'belegart': 'lieferschein',
            'bezeichnung': 'Lieferscheine',
            'praefix': 'LS',
            'stellen': 4
        },
        {
            'belegart': 'rechnung',
            'bezeichnung': 'Rechnungen',
            'praefix': 'RE',
            'stellen': 4
        },
        {
            'belegart': 'anzahlung',
            'bezeichnung': 'Anzahlungsrechnungen',
            'praefix': 'AR',
            'stellen': 4
        },
        {
            'belegart': 'gutschrift',
            'bezeichnung': 'Gutschriften',
            'praefix': 'GS',
            'stellen': 4
        },
        {
            'belegart': 'kassenbeleg',
            'bezeichnung': 'Kassenbelege',
            'praefix': 'K',
            'stellen': 6
        },
    ]
    
    aktuelles_jahr = datetime.now().year
    erstellt = 0
    
    for kreis_data in standard_kreise:
        existing = Nummernkreis.query.filter_by(belegart=kreis_data['belegart']).first()
        if not existing:
            nk = Nummernkreis(
                belegart=kreis_data['belegart'],
                bezeichnung=kreis_data['bezeichnung'],
                praefix=kreis_data['praefix'],
                stellen=kreis_data['stellen'],
                aktuelles_jahr=aktuelles_jahr,
                aktuelle_nummer=0
            )
            db.session.add(nk)
            erstellt += 1
    
    if erstellt > 0:
        db.session.commit()
    
    return erstellt


def init_zahlungsbedingungen():
    """
    Initialisiert Standard-Zahlungsbedingungen
    """
    standard_bedingungen = [
        {
            'bezeichnung': 'Sofort fällig',
            'kurztext': 'Sofort',
            'zahlungsziel_tage': 0,
            'text_rechnung': 'Der Rechnungsbetrag ist sofort fällig.',
            'sortierung': 1
        },
        {
            'bezeichnung': '7 Tage netto',
            'kurztext': '7 Tage',
            'zahlungsziel_tage': 7,
            'text_rechnung': 'Zahlbar innerhalb von 7 Tagen ohne Abzug.',
            'sortierung': 2
        },
        {
            'bezeichnung': '14 Tage netto',
            'kurztext': '14 Tage',
            'zahlungsziel_tage': 14,
            'text_rechnung': 'Zahlbar innerhalb von 14 Tagen ohne Abzug.',
            'standard': True,
            'sortierung': 3
        },
        {
            'bezeichnung': '14 Tage 2% Skonto, 30 Tage netto',
            'kurztext': '14/30 Skonto',
            'zahlungsziel_tage': 30,
            'skonto_prozent': 2,
            'skonto_tage': 14,
            'text_rechnung': 'Bei Zahlung innerhalb von 14 Tagen gewähren wir 2% Skonto. Zahlbar innerhalb von 30 Tagen ohne Abzug.',
            'sortierung': 4
        },
        {
            'bezeichnung': '30 Tage netto',
            'kurztext': '30 Tage',
            'zahlungsziel_tage': 30,
            'text_rechnung': 'Zahlbar innerhalb von 30 Tagen ohne Abzug.',
            'sortierung': 5
        },
        {
            'bezeichnung': '50% Anzahlung, Rest bei Lieferung',
            'kurztext': '50% Anzahlung',
            'zahlungsziel_tage': 0,
            'anzahlung_erforderlich': True,
            'anzahlung_prozent': 50,
            'anzahlung_text': '50% bei Auftragserteilung',
            'text_rechnung': 'Anzahlung: 50% bei Auftragserteilung. Restbetrag bei Lieferung.',
            'sortierung': 6
        },
        {
            'bezeichnung': 'Vorkasse',
            'kurztext': 'Vorkasse',
            'zahlungsziel_tage': 0,
            'anzahlung_erforderlich': True,
            'anzahlung_prozent': 100,
            'anzahlung_text': 'Vorauszahlung',
            'text_rechnung': 'Lieferung erfolgt nach Zahlungseingang.',
            'sortierung': 7
        },
    ]
    
    erstellt = 0
    
    for bed_data in standard_bedingungen:
        existing = Zahlungsbedingung.query.filter_by(bezeichnung=bed_data['bezeichnung']).first()
        if not existing:
            zb = Zahlungsbedingung(**bed_data)
            db.session.add(zb)
            erstellt += 1
    
    if erstellt > 0:
        db.session.commit()
    
    return erstellt
