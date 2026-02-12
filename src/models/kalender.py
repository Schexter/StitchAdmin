# -*- coding: utf-8 -*-
"""
KALENDER MODELS
===============
Umfassendes Kalendersystem für:
- Produktionsplanung (Maschinen nebeneinander)
- Ratentermine / Zahlungserinnerungen
- Kundentermine / CRM-Aktivitäten
- Mitarbeiter-Termine
- Wartung / Maschinenpflege

Outlook-Style: Wochen-/Monatsansicht mit Ressourcen-Spalten

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime, date, time, timedelta
from enum import Enum
from src.models import db


class TerminTyp(Enum):
    """Typen von Kalendereinträgen"""
    PRODUKTION = "produktion"          # Produktionsauftrag
    KUNDE = "kunde"                    # Kundentermin
    RATE = "rate"                      # Ratenzahlung fällig
    MAHNUNG = "mahnung"                # Mahntermin
    WARTUNG = "wartung"                # Maschinenwartung
    LIEFERUNG = "lieferung"            # Liefertermin
    ABHOLUNG = "abholung"              # Abholtermin
    INTERN = "intern"                  # Interner Termin
    ERINNERUNG = "erinnerung"          # Allgemeine Erinnerung
    CRM_FOLLOWUP = "crm_followup"      # CRM Nachfasstermin
    ANGEBOT_ABLAUF = "angebot_ablauf"  # Angebot läuft ab


class TerminStatus(Enum):
    """Status eines Termins"""
    GEPLANT = "geplant"
    BESTAETIGT = "bestaetigt"
    IN_BEARBEITUNG = "in_bearbeitung"
    ABGESCHLOSSEN = "abgeschlossen"
    VERSCHOBEN = "verschoben"
    STORNIERT = "storniert"


class WiederholungTyp(Enum):
    """Wiederholungstypen"""
    KEINE = "keine"
    TAEGLICH = "taeglich"
    WOECHENTLICH = "woechentlich"
    MONATLICH = "monatlich"
    JAEHRLICH = "jaehrlich"


class KalenderTermin(db.Model):
    """
    Zentraler Kalendertermin
    """
    __tablename__ = 'kalender_termine'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Basis-Informationen
    titel = db.Column(db.String(200), nullable=False)
    beschreibung = db.Column(db.Text)
    
    # Zeitraum
    start_datum = db.Column(db.Date, nullable=False)
    start_zeit = db.Column(db.Time)
    ende_datum = db.Column(db.Date)
    ende_zeit = db.Column(db.Time)
    ganztaegig = db.Column(db.Boolean, default=False)
    
    # Typ & Status
    termin_typ = db.Column(db.String(30), default='intern')
    status = db.Column(db.String(30), default='geplant')
    prioritaet = db.Column(db.Integer, default=2)  # 1=Hoch, 2=Normal, 3=Niedrig
    
    # Farbe für Kalenderdarstellung
    farbe = db.Column(db.String(20), default='#3788d8')
    
    # Verknüpfungen
    kunde_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    auftrag_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    dokument_id = db.Column(db.Integer, db.ForeignKey('business_documents.id'))
    maschine_id = db.Column(db.Integer, db.ForeignKey('kalender_ressourcen.id'))
    mitarbeiter_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    ratenzahlung_id = db.Column(db.Integer, db.ForeignKey('ratenzahlungen.id'))
    
    # Ressource (für Produktionsplanung)
    ressource_id = db.Column(db.Integer, db.ForeignKey('kalender_ressourcen.id'))
    
    # Wiederholung
    wiederholung = db.Column(db.String(20), default='keine')
    wiederholung_ende = db.Column(db.Date)
    parent_termin_id = db.Column(db.Integer, db.ForeignKey('kalender_termine.id'))
    
    # Erinnerung
    erinnerung_minuten = db.Column(db.Integer)  # z.B. 15, 60, 1440 (1 Tag)
    erinnerung_gesendet = db.Column(db.Boolean, default=False)
    
    # Notizen & Tags
    notizen = db.Column(db.Text)
    tags = db.Column(db.String(500))  # Komma-separiert
    
    # Betrag (für Ratentermine)
    betrag = db.Column(db.Numeric(12, 2))
    
    # Tracking
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)
    erstellt_von = db.Column(db.String(100))
    aktualisiert_am = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Beziehungen
    kunde = db.relationship('Customer', backref='kalender_termine')
    ressource = db.relationship('KalenderRessource', foreign_keys=[ressource_id], backref='termine')
    
    def __repr__(self):
        return f"<KalenderTermin {self.titel} ({self.start_datum})>"
    
    @property
    def dauer_minuten(self) -> int:
        """Berechnet Dauer in Minuten"""
        if not self.start_zeit or not self.ende_zeit:
            return 0
        
        start = datetime.combine(self.start_datum, self.start_zeit)
        ende_datum = self.ende_datum or self.start_datum
        ende = datetime.combine(ende_datum, self.ende_zeit)
        
        return int((ende - start).total_seconds() / 60)
    
    @property
    def ist_ueberfaellig(self) -> bool:
        """Prüft ob Termin überfällig"""
        if self.status in ['abgeschlossen', 'storniert']:
            return False
        return self.start_datum < date.today()
    
    def to_fullcalendar(self) -> dict:
        """Konvertiert zu FullCalendar Event-Format"""
        event = {
            'id': self.id,
            'title': self.titel,
            'start': self.start_datum.isoformat(),
            'backgroundColor': self.farbe,
            'borderColor': self.farbe,
            'extendedProps': {
                'typ': self.termin_typ,
                'status': self.status,
                'kunde_id': self.kunde_id,
                'ressource_id': self.ressource_id,
                'beschreibung': self.beschreibung,
                'betrag': float(self.betrag) if self.betrag else None,
            }
        }
        
        if self.ganztaegig:
            event['allDay'] = True
        else:
            if self.start_zeit:
                event['start'] = f"{self.start_datum.isoformat()}T{self.start_zeit.isoformat()}"
            if self.ende_datum and self.ende_zeit:
                event['end'] = f"{self.ende_datum.isoformat()}T{self.ende_zeit.isoformat()}"
        
        # Ressource für Spalten-Darstellung
        if self.ressource_id:
            event['resourceId'] = self.ressource_id
        
        return event


class KalenderRessource(db.Model):
    """
    Ressourcen für Kalender (Maschinen, Räume, Mitarbeiter)
    """
    __tablename__ = 'kalender_ressourcen'
    
    id = db.Column(db.Integer, primary_key=True)
    
    name = db.Column(db.String(100), nullable=False)
    typ = db.Column(db.String(50))  # maschine, raum, mitarbeiter
    beschreibung = db.Column(db.Text)
    
    # Für Maschinen
    maschinen_typ = db.Column(db.String(50))  # stickmaschine, drucker, presse, plotter
    kapazitaet = db.Column(db.String(100))  # z.B. "4 Köpfe", "A3"
    
    # Darstellung
    farbe = db.Column(db.String(20), default='#3788d8')
    icon = db.Column(db.String(50))
    reihenfolge = db.Column(db.Integer, default=0)
    
    # Verfügbarkeit
    ist_aktiv = db.Column(db.Boolean, default=True)
    verfuegbar_von = db.Column(db.Time, default=time(8, 0))
    verfuegbar_bis = db.Column(db.Time, default=time(17, 0))
    
    # Arbeitstage (JSON: [1,2,3,4,5] = Mo-Fr)
    arbeitstage = db.Column(db.String(50), default='[1,2,3,4,5]')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<KalenderRessource {self.name}>"
    
    def to_fullcalendar(self) -> dict:
        """Für FullCalendar Resource-Format"""
        return {
            'id': self.id,
            'title': self.name,
            'eventColor': self.farbe,
            'extendedProps': {
                'typ': self.typ,
                'maschinen_typ': self.maschinen_typ,
                'kapazitaet': self.kapazitaet,
            }
        }


class RatenzahlungTermin(db.Model):
    """
    Ratenzahlungs-Termine (verknüpft mit Kalender)
    """
    __tablename__ = 'ratenzahlungen'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Verknüpfung
    kunde_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    dokument_id = db.Column(db.Integer, db.ForeignKey('business_documents.id'))
    
    # Ratenplan
    gesamtbetrag = db.Column(db.Numeric(12, 2), nullable=False)
    anzahl_raten = db.Column(db.Integer, nullable=False)
    rate_betrag = db.Column(db.Numeric(12, 2), nullable=False)
    
    # Termine
    erste_rate = db.Column(db.Date, nullable=False)
    intervall_tage = db.Column(db.Integer, default=30)  # Standard: monatlich
    
    # Status
    bezahlte_raten = db.Column(db.Integer, default=0)
    restbetrag = db.Column(db.Numeric(12, 2))
    ist_abgeschlossen = db.Column(db.Boolean, default=False)
    
    # Notizen
    notizen = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Beziehungen
    kunde = db.relationship('Customer', backref='ratenzahlungen')
    kalender_termine = db.relationship('KalenderTermin', backref='ratenzahlung', 
                                       foreign_keys='KalenderTermin.ratenzahlung_id')
    
    def erstelle_kalendertermine(self):
        """Erstellt Kalendertermine für alle Raten"""
        termine = []
        
        for i in range(self.anzahl_raten):
            faellig = self.erste_rate + timedelta(days=i * self.intervall_tage)
            
            termin = KalenderTermin(
                titel=f"Rate {i+1}/{self.anzahl_raten}: {self.rate_betrag}€",
                beschreibung=f"Ratenzahlung für Rechnung",
                start_datum=faellig,
                ganztaegig=True,
                termin_typ='rate',
                status='geplant',
                farbe='#dc3545',  # Rot für Zahlungen
                kunde_id=self.kunde_id,
                dokument_id=self.dokument_id,
                ratenzahlung_id=self.id,
                betrag=self.rate_betrag,
                erinnerung_minuten=1440 * 3,  # 3 Tage vorher
            )
            termine.append(termin)
        
        return termine


# ============================================================================
# STANDARD-RESSOURCEN (Maschinen)
# ============================================================================

STANDARD_RESSOURCEN = [
    {
        'name': 'Stickmaschine 1',
        'typ': 'maschine',
        'maschinen_typ': 'stickmaschine',
        'kapazitaet': '4 Köpfe',
        'farbe': '#28a745',
        'icon': 'fa-cogs',
    },
    {
        'name': 'Stickmaschine 2',
        'typ': 'maschine',
        'maschinen_typ': 'stickmaschine',
        'kapazitaet': '6 Köpfe',
        'farbe': '#17a2b8',
        'icon': 'fa-cogs',
    },
    {
        'name': 'DTG-Drucker',
        'typ': 'maschine',
        'maschinen_typ': 'drucker',
        'kapazitaet': 'A3',
        'farbe': '#ffc107',
        'icon': 'fa-print',
    },
    {
        'name': 'Transferpresse',
        'typ': 'maschine',
        'maschinen_typ': 'presse',
        'kapazitaet': '40x50cm',
        'farbe': '#fd7e14',
        'icon': 'fa-compress',
    },
    {
        'name': 'Schneideplotter',
        'typ': 'maschine',
        'maschinen_typ': 'plotter',
        'kapazitaet': '160cm Breite',
        'farbe': '#6f42c1',
        'icon': 'fa-cut',
    },
]


def init_standard_ressourcen():
    """Initialisiert Standard-Maschinenressourcen"""
    for i, res_def in enumerate(STANDARD_RESSOURCEN):
        existing = KalenderRessource.query.filter_by(name=res_def['name']).first()
        if not existing:
            ressource = KalenderRessource(
                name=res_def['name'],
                typ=res_def['typ'],
                maschinen_typ=res_def['maschinen_typ'],
                kapazitaet=res_def['kapazitaet'],
                farbe=res_def['farbe'],
                icon=res_def['icon'],
                reihenfolge=i,
            )
            db.session.add(ressource)
    
    db.session.commit()
