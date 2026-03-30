# -*- coding: utf-8 -*-
"""
Energie-Tracking: Stromzähler, Ablesungen, Tarifberechnung
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""
from datetime import date
from src.models import db


class StromTarif(db.Model):
    """Stromtarif-Konfiguration"""
    __tablename__ = 'strom_tarife'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default='Haupttarif')
    grundgebuehr_monat = db.Column(db.Numeric(8, 2), default=0)   # € pro Monat
    arbeitspreis_kwh = db.Column(db.Numeric(8, 4), nullable=False)  # € pro kWh
    netzentgelt_kwh = db.Column(db.Numeric(8, 4), default=0)      # Netzentgelt inkl.
    gueltig_ab = db.Column(db.Date, nullable=False, default=date.today)
    anbieter = db.Column(db.String(100))
    notiz = db.Column(db.Text)
    erstellt_am = db.Column(db.DateTime, default=db.func.now())

    @property
    def gesamtpreis_kwh(self):
        return float(self.arbeitspreis_kwh or 0) + float(self.netzentgelt_kwh or 0)


class StromAblesung(db.Model):
    """Stromzähler-Ablesung"""
    __tablename__ = 'strom_ablesungen'

    id = db.Column(db.Integer, primary_key=True)
    ablesedatum = db.Column(db.Date, nullable=False, default=date.today, index=True)
    zaehlerstand = db.Column(db.Numeric(12, 1), nullable=False)   # kWh-Stand
    kommentar = db.Column(db.String(200))
    erstellt_von = db.Column(db.String(50))
    erstellt_am = db.Column(db.DateTime, default=db.func.now())

    @property
    def monat_label(self):
        return self.ablesedatum.strftime('%B %Y') if self.ablesedatum else ''
