# -*- coding: utf-8 -*-
"""
Textbausteine (Reusable Text Modules) for Angebote
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime
from src.models import db


TEXTBAUSTEIN_CATEGORIES = {
    'zahlung': 'Zahlungsbedingungen',
    'gueltigkeit': 'Gültigkeit',
    'lieferung': 'Lieferbedingungen',
    'haftung': 'Haftung & Gewährleistung',
    'kundenware': 'Kundenware',
    'sonstiges': 'Sonstiges',
}


class Textbaustein(db.Model):
    """Wiederverwendbare Textbausteine für Angebote"""
    __tablename__ = 'textbausteine'

    id = db.Column(db.Integer, primary_key=True)
    titel = db.Column(db.String(200), nullable=False)
    inhalt = db.Column(db.Text, nullable=False)
    kategorie = db.Column(db.String(50), default='sonstiges')
    sort_order = db.Column(db.Integer, default=0)
    aktiv = db.Column(db.Boolean, default=True)
    ist_standard = db.Column(db.Boolean, default=False)  # Default bei neuem Angebot vorausgewählt

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Textbaustein {self.id}: {self.titel}>'

    @classmethod
    def get_active(cls):
        """Alle aktiven Textbausteine, sortiert nach Kategorie und Reihenfolge"""
        return cls.query.filter_by(aktiv=True).order_by(cls.kategorie, cls.sort_order, cls.titel).all()

    @classmethod
    def get_defaults(cls):
        """Alle als Standard markierten Textbausteine"""
        return cls.query.filter_by(aktiv=True, ist_standard=True).order_by(cls.sort_order).all()

    @classmethod
    def ensure_defaults(cls):
        """Erstellt Standard-Textbausteine falls noch keine vorhanden"""
        if cls.query.count() > 0:
            return

        defaults = [
            {
                'titel': 'Angebotsgültigkeit 30 Tage',
                'inhalt': 'Dieses Angebot ist 30 Tage ab Angebotsdatum gültig.',
                'kategorie': 'gueltigkeit',
                'sort_order': 1,
                'ist_standard': True,
            },
            {
                'titel': '50% Anzahlung',
                'inhalt': 'Bei Auftragserteilung wird eine Anzahlung von 50% des Gesamtbetrages fällig. Die Restforderung wird bei Lieferung/Abholung fällig.',
                'kategorie': 'zahlung',
                'sort_order': 1,
                'ist_standard': True,
            },
            {
                'titel': 'Zahlung bei Abholung/Lieferung',
                'inhalt': 'Der Gesamtbetrag ist bei Abholung bzw. Lieferung der Ware fällig.',
                'kategorie': 'zahlung',
                'sort_order': 2,
                'ist_standard': False,
            },
            {
                'titel': 'Zahlung per Vorkasse',
                'inhalt': 'Der Gesamtbetrag ist per Vorkasse vor Produktionsbeginn zu begleichen. Die Produktion startet nach Zahlungseingang.',
                'kategorie': 'zahlung',
                'sort_order': 3,
                'ist_standard': False,
            },
            {
                'titel': 'Zahlungsziel 14 Tage',
                'inhalt': 'Zahlbar innerhalb von 14 Tagen nach Rechnungsdatum ohne Abzug.',
                'kategorie': 'zahlung',
                'sort_order': 4,
                'ist_standard': False,
            },
            {
                'titel': 'Lieferzeit 2-3 Wochen',
                'inhalt': 'Die voraussichtliche Lieferzeit beträgt 2-3 Wochen ab Auftragserteilung und Freigabe des Designs.',
                'kategorie': 'lieferung',
                'sort_order': 1,
                'ist_standard': True,
            },
            {
                'titel': 'Versandkosten',
                'inhalt': 'Die Versandkosten werden nach Gewicht und Versandart berechnet und separat in Rechnung gestellt. Selbstabholung ist kostenfrei möglich.',
                'kategorie': 'lieferung',
                'sort_order': 2,
                'ist_standard': False,
            },
            {
                'titel': 'Haftungsausschluss Kundenware',
                'inhalt': 'Bei vom Kunden bereitgestellten Textilien (Kundenware) übernehmen wir keine Haftung für materialbedingte Schäden während der Veredelung. Wir empfehlen, 5-10% Ersatztextilien bereitzustellen.',
                'kategorie': 'kundenware',
                'sort_order': 1,
                'ist_standard': False,
            },
            {
                'titel': 'Farbabweichungen',
                'inhalt': 'Geringfügige Farbabweichungen zwischen Design-Vorlage und fertigem Produkt sind produktionsbedingt möglich und stellen keinen Reklamationsgrund dar.',
                'kategorie': 'haftung',
                'sort_order': 1,
                'ist_standard': False,
            },
            {
                'titel': 'Design-Freigabe erforderlich',
                'inhalt': 'Vor Produktionsbeginn erhalten Sie eine digitale Vorschau zur Freigabe. Die Produktion startet erst nach schriftlicher Freigabe des Designs.',
                'kategorie': 'sonstiges',
                'sort_order': 1,
                'ist_standard': True,
            },
        ]

        for data in defaults:
            tb = cls(**data, created_by='System')
            db.session.add(tb)

        db.session.commit()
