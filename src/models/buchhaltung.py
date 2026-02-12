# -*- coding: utf-8 -*-
"""
BUCHHALTUNG MODELS
==================
Datenmodelle für Buchhaltung, Berichte und Exporte

Features:
- Buchungsjournal mit Kontenrahmen
- DATEV-kompatibler Export
- ELSTER-kompatibler CSV-Export
- BWA-Struktur
- Kostenstellenrechnung

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from src.models import db


class Kontenrahmen(Enum):
    """Unterstützte Kontenrahmen"""
    SKR03 = "SKR03"  # Standard für kleine/mittlere Unternehmen
    SKR04 = "SKR04"  # Alternative


class BuchungsArt(Enum):
    """Art der Buchung"""
    EINNAHME = "einnahme"
    AUSGABE = "ausgabe"
    UMBUCHUNG = "umbuchung"


class MwStSatz(Enum):
    """MwSt-Sätze Deutschland"""
    VOLL = Decimal("19.0")
    ERMAESSIGT = Decimal("7.0")
    STEUERFREI = Decimal("0.0")


class Konto(db.Model):
    """
    Kontenplan basierend auf SKR03/SKR04
    """
    __tablename__ = 'buchhaltung_konten'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Kontonummer (z.B. 8400 für Erlöse)
    kontonummer = db.Column(db.String(10), nullable=False, unique=True)
    bezeichnung = db.Column(db.String(200), nullable=False)
    
    # Kontenrahmen
    kontenrahmen = db.Column(db.String(10), default='SKR03')
    
    # Kontenklasse (0-9)
    kontenklasse = db.Column(db.Integer)  # 0=Anlage, 1=Umlauf, 2=Eigenkapital, etc.
    
    # Kontotyp
    ist_aktiv = db.Column(db.Boolean, default=True)
    ist_ertragskonto = db.Column(db.Boolean, default=False)
    ist_aufwandskonto = db.Column(db.Boolean, default=False)
    ist_bestandskonto = db.Column(db.Boolean, default=False)
    
    # MwSt-Einstellung
    standard_mwst_satz = db.Column(db.Numeric(5, 2), default=19.0)
    
    # DATEV-Kompatibilität
    datev_kontonummer = db.Column(db.String(10))
    
    # Hierarchie
    parent_id = db.Column(db.Integer, db.ForeignKey('buchhaltung_konten.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Beziehungen
    buchungen = db.relationship('Buchung', backref='konto', lazy='dynamic')
    
    def __repr__(self):
        return f"<Konto {self.kontonummer} - {self.bezeichnung}>"


class Buchung(db.Model):
    """
    Einzelne Buchung im Journal
    """
    __tablename__ = 'buchhaltung_buchungen'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Buchungsdatum
    buchungsdatum = db.Column(db.Date, nullable=False, default=date.today)
    erfassungsdatum = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Belegnummer & Referenz
    belegnummer = db.Column(db.String(50))
    beleg_art = db.Column(db.String(50))  # Rechnung, Gutschrift, Bank, Kasse
    
    # Buchungstext
    buchungstext = db.Column(db.String(500), nullable=False)
    
    # Konten (Soll/Haben)
    soll_konto_id = db.Column(db.Integer, db.ForeignKey('buchhaltung_konten.id'))
    haben_konto_id = db.Column(db.Integer, db.ForeignKey('buchhaltung_konten.id'))
    konto_id = db.Column(db.Integer, db.ForeignKey('buchhaltung_konten.id'))  # Hauptkonto
    gegenkonto_id = db.Column(db.Integer, db.ForeignKey('buchhaltung_konten.id'))
    
    # Beträge
    betrag_netto = db.Column(db.Numeric(12, 2), nullable=False)
    betrag_brutto = db.Column(db.Numeric(12, 2))
    mwst_satz = db.Column(db.Numeric(5, 2), default=19.0)
    mwst_betrag = db.Column(db.Numeric(12, 2))
    
    # Art
    buchungs_art = db.Column(db.String(20))  # einnahme, ausgabe, umbuchung
    
    # Verknüpfungen
    rechnung_id = db.Column(db.Integer, db.ForeignKey('business_documents.id'))
    kunde_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    lieferant_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))
    
    # Kostenstelle
    kostenstelle_id = db.Column(db.Integer, db.ForeignKey('buchhaltung_kostenstellen.id'))
    
    # Status
    ist_storniert = db.Column(db.Boolean, default=False)
    storno_buchung_id = db.Column(db.Integer, db.ForeignKey('buchhaltung_buchungen.id'))
    
    # DATEV-Export
    datev_exportiert = db.Column(db.Boolean, default=False)
    datev_export_datum = db.Column(db.DateTime)
    
    # Benutzer
    erstellt_von = db.Column(db.String(100))
    
    # Beziehungen
    soll_konto = db.relationship('Konto', foreign_keys=[soll_konto_id])
    haben_konto = db.relationship('Konto', foreign_keys=[haben_konto_id])
    kostenstelle = db.relationship('Kostenstelle', backref='buchungen')
    kunde = db.relationship('Customer', backref='buchungen')
    
    def __repr__(self):
        return f"<Buchung {self.belegnummer} - {self.betrag_brutto}€>"


class Kostenstelle(db.Model):
    """
    Kostenstellen für Kostenrechnung
    """
    __tablename__ = 'buchhaltung_kostenstellen'
    
    id = db.Column(db.Integer, primary_key=True)
    
    nummer = db.Column(db.String(20), nullable=False, unique=True)
    bezeichnung = db.Column(db.String(200), nullable=False)
    beschreibung = db.Column(db.Text)
    
    # Verantwortlicher
    verantwortlicher = db.Column(db.String(100))
    
    # Budget
    budget_jahr = db.Column(db.Numeric(12, 2))
    budget_monat = db.Column(db.Numeric(12, 2))
    
    # Hierarchie
    parent_id = db.Column(db.Integer, db.ForeignKey('buchhaltung_kostenstellen.id'))
    
    ist_aktiv = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Geschaeftsjahr(db.Model):
    """
    Geschäftsjahre für Periodenabgrenzung
    """
    __tablename__ = 'buchhaltung_geschaeftsjahre'
    
    id = db.Column(db.Integer, primary_key=True)
    
    jahr = db.Column(db.Integer, nullable=False, unique=True)
    beginn = db.Column(db.Date, nullable=False)
    ende = db.Column(db.Date, nullable=False)
    
    ist_abgeschlossen = db.Column(db.Boolean, default=False)
    abschluss_datum = db.Column(db.DateTime)
    
    # Eröffnungsbilanz
    eroeffnungsbilanz_erstellt = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UStVoranmeldung(db.Model):
    """
    USt-Voranmeldung (ELSTER-kompatibel)
    """
    __tablename__ = 'buchhaltung_ust_voranmeldung'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Zeitraum
    jahr = db.Column(db.Integer, nullable=False)
    monat = db.Column(db.Integer)  # None = Quartal
    quartal = db.Column(db.Integer)  # 1-4
    
    # Berechnung
    zeitraum_von = db.Column(db.Date, nullable=False)
    zeitraum_bis = db.Column(db.Date, nullable=False)
    
    # USt auf Umsätze (Kennzahl 81)
    umsatz_19_netto = db.Column(db.Numeric(12, 2), default=0)
    ust_19 = db.Column(db.Numeric(12, 2), default=0)
    
    umsatz_7_netto = db.Column(db.Numeric(12, 2), default=0)
    ust_7 = db.Column(db.Numeric(12, 2), default=0)
    
    # Innergemeinschaftliche Erwerbe
    ig_erwerbe_netto = db.Column(db.Numeric(12, 2), default=0)
    ust_ig_erwerbe = db.Column(db.Numeric(12, 2), default=0)
    
    # Vorsteuer
    vorsteuer_19 = db.Column(db.Numeric(12, 2), default=0)
    vorsteuer_7 = db.Column(db.Numeric(12, 2), default=0)
    vorsteuer_ig = db.Column(db.Numeric(12, 2), default=0)
    vorsteuer_gesamt = db.Column(db.Numeric(12, 2), default=0)
    
    # Ergebnis
    ust_zahllast = db.Column(db.Numeric(12, 2), default=0)  # Positiv = Zahlung, Negativ = Erstattung
    
    # Status
    status = db.Column(db.String(20), default='entwurf')  # entwurf, berechnet, exportiert, eingereicht
    
    # Export
    elster_xml_pfad = db.Column(db.String(500))
    export_datum = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)


class Finanzplan(db.Model):
    """
    Finanzplanung / Budget
    """
    __tablename__ = 'buchhaltung_finanzplan'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Zeitraum
    jahr = db.Column(db.Integer, nullable=False)
    monat = db.Column(db.Integer)  # Optional für Monatsplanung
    
    name = db.Column(db.String(100), nullable=False)
    beschreibung = db.Column(db.Text)
    
    # Geplante Einnahmen
    umsatz_plan = db.Column(db.Numeric(12, 2), default=0)
    sonstige_einnahmen_plan = db.Column(db.Numeric(12, 2), default=0)
    
    # Geplante Ausgaben
    wareneinkauf_plan = db.Column(db.Numeric(12, 2), default=0)
    personalkosten_plan = db.Column(db.Numeric(12, 2), default=0)
    miete_plan = db.Column(db.Numeric(12, 2), default=0)
    marketing_plan = db.Column(db.Numeric(12, 2), default=0)
    sonstige_kosten_plan = db.Column(db.Numeric(12, 2), default=0)
    
    # Investitionen
    investitionen_plan = db.Column(db.Numeric(12, 2), default=0)
    
    # Ist-Werte (für Vergleich)
    umsatz_ist = db.Column(db.Numeric(12, 2), default=0)
    kosten_ist = db.Column(db.Numeric(12, 2), default=0)
    
    # Status
    ist_freigegeben = db.Column(db.Boolean, default=False)
    freigabe_datum = db.Column(db.DateTime)
    freigabe_von = db.Column(db.String(100))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)


class Kalkulation(db.Model):
    """
    Kalkulationen für Stundensätze, Stickpreise, etc.
    """
    __tablename__ = 'buchhaltung_kalkulationen'
    
    id = db.Column(db.Integer, primary_key=True)
    
    name = db.Column(db.String(100), nullable=False)
    typ = db.Column(db.String(50))  # stundensatz, stickpreis, projekt, produkt
    beschreibung = db.Column(db.Text)
    
    # Gültigkeitszeitraum
    gueltig_ab = db.Column(db.Date)
    gueltig_bis = db.Column(db.Date)
    
    # Basiswerte
    basis_stundensatz = db.Column(db.Numeric(10, 2))
    basis_maschinenkosten = db.Column(db.Numeric(10, 2))
    
    # Stickerei-spezifisch
    preis_pro_1000_stiche = db.Column(db.Numeric(10, 4))
    preis_farbwechsel = db.Column(db.Numeric(10, 2))
    mindestpreis = db.Column(db.Numeric(10, 2))
    einrichtekosten = db.Column(db.Numeric(10, 2))
    
    # Aufschläge
    material_aufschlag_prozent = db.Column(db.Numeric(5, 2), default=0)
    gewinn_aufschlag_prozent = db.Column(db.Numeric(5, 2), default=0)
    risiko_aufschlag_prozent = db.Column(db.Numeric(5, 2), default=0)
    
    # Kalkulationsdaten (JSON für Flexibilität)
    kalkulation_details = db.Column(db.JSON)
    
    ist_aktiv = db.Column(db.Boolean, default=True)
    ist_standard = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    erstellt_von = db.Column(db.String(100))


# ============================================================================
# STANDARD-KONTENPLAN SKR03 (Auszug)
# ============================================================================

SKR03_KONTEN = [
    # Klasse 0: Anlagevermögen
    {"nr": "0400", "bez": "Maschinen und Anlagen", "klasse": 0, "bestand": True},
    {"nr": "0420", "bez": "Büroausstattung", "klasse": 0, "bestand": True},
    {"nr": "0650", "bez": "Büroeinrichtung", "klasse": 0, "bestand": True},
    
    # Klasse 1: Umlaufvermögen
    {"nr": "1000", "bez": "Kasse", "klasse": 1, "bestand": True},
    {"nr": "1200", "bez": "Bank", "klasse": 1, "bestand": True},
    {"nr": "1400", "bez": "Forderungen aus L+L", "klasse": 1, "bestand": True},
    {"nr": "1600", "bez": "Vorsteuer", "klasse": 1, "bestand": True},
    
    # Klasse 2: Eigenkapital / Schulden  
    {"nr": "2000", "bez": "Eigenkapital", "klasse": 2, "bestand": True},
    
    # Klasse 3: Wareneingang
    {"nr": "3400", "bez": "Wareneingang 19%", "klasse": 3, "aufwand": True},
    {"nr": "3300", "bez": "Wareneingang 7%", "klasse": 3, "aufwand": True},
    
    # Klasse 4: Betriebliche Aufwendungen
    {"nr": "4100", "bez": "Löhne", "klasse": 4, "aufwand": True},
    {"nr": "4120", "bez": "Gehälter", "klasse": 4, "aufwand": True},
    {"nr": "4130", "bez": "Sozialversicherung AG", "klasse": 4, "aufwand": True},
    {"nr": "4200", "bez": "Raumkosten/Miete", "klasse": 4, "aufwand": True},
    {"nr": "4210", "bez": "Strom, Gas, Wasser", "klasse": 4, "aufwand": True},
    {"nr": "4500", "bez": "Fahrzeugkosten", "klasse": 4, "aufwand": True},
    {"nr": "4600", "bez": "Werbekosten", "klasse": 4, "aufwand": True},
    {"nr": "4900", "bez": "Sonstige Aufwendungen", "klasse": 4, "aufwand": True},
    {"nr": "4930", "bez": "Bürobedarf", "klasse": 4, "aufwand": True},
    {"nr": "4970", "bez": "Nebenkosten Geldverkehr", "klasse": 4, "aufwand": True},
    
    # Klasse 7: Abschreibungen
    {"nr": "7000", "bez": "Abschreibungen Sachanlagen", "klasse": 7, "aufwand": True},
    
    # Klasse 8: Erlöse
    {"nr": "8400", "bez": "Erlöse 19% USt", "klasse": 8, "ertrag": True},
    {"nr": "8300", "bez": "Erlöse 7% USt", "klasse": 8, "ertrag": True},
    {"nr": "8120", "bez": "Steuerfreie Umsätze §4 UStG", "klasse": 8, "ertrag": True},
    {"nr": "8200", "bez": "Erlöse Anlagenverkäufe", "klasse": 8, "ertrag": True},
    {"nr": "8900", "bez": "Sonstige Erträge", "klasse": 8, "ertrag": True},
]


def init_kontenplan(kontenrahmen='SKR03'):
    """
    Initialisiert den Kontenplan mit Standard-Konten
    """
    from flask import current_app
    
    if kontenrahmen == 'SKR03':
        konten = SKR03_KONTEN
    else:
        return False
    
    for k in konten:
        existing = Konto.query.filter_by(kontonummer=k['nr']).first()
        if not existing:
            konto = Konto(
                kontonummer=k['nr'],
                bezeichnung=k['bez'],
                kontenrahmen=kontenrahmen,
                kontenklasse=k['klasse'],
                ist_bestandskonto=k.get('bestand', False),
                ist_ertragskonto=k.get('ertrag', False),
                ist_aufwandskonto=k.get('aufwand', False),
                datev_kontonummer=k['nr']
            )
            db.session.add(konto)
    
    db.session.commit()
    return True
