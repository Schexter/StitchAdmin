# -*- coding: utf-8 -*-
"""
Veredelungsverfahren - Konfigurierbare Veredelungsmethoden
==========================================================
Definiert Veredelungsverfahren (Stickerei, Textildruck, DTF, Sublimation...),
deren Positionen (Brust links, Ruecken...) und verfahrensspezifische Parameter
(Temperatur, Zeit, Geschwindigkeit...).
"""

from src.models import db
from datetime import datetime


class VeredelungsVerfahren(db.Model):
    """Veredelungsverfahren (z.B. Stickerei, Textildruck, DTF, Sublimation)"""
    __tablename__ = 'veredelungsverfahren'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    code = db.Column(db.String(30), nullable=False, unique=True)  # embroidery, printing, dtf, sublimation
    icon = db.Column(db.String(50), default='bi-brush')  # Bootstrap Icon
    beschreibung = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Preiskalkulation
    einrichtungspauschale = db.Column(db.Float, default=0)       # Setup-Kosten einmalig pro Design
    preis_pro_1000_stiche = db.Column(db.Float, default=0)       # Stickerei: EUR/1000 Stiche
    preis_pro_cm2 = db.Column(db.Float, default=0)               # Druck: EUR/cm2 Druckflaeche
    mindestpreis_pro_stueck = db.Column(db.Float, default=0)     # Mindestpreis pro Stueck
    staffelpreise = db.Column(db.Text)                           # JSON: [{"ab_menge": 50, "rabatt_prozent": 10}]

    # Beziehungen
    positionen = db.relationship('VeredelungsPosition', back_populates='verfahren',
                                 cascade='all, delete-orphan', order_by='VeredelungsPosition.sort_order')
    parameter = db.relationship('VeredelungsParameter', back_populates='verfahren',
                                cascade='all, delete-orphan', order_by='VeredelungsParameter.sort_order')

    def __repr__(self):
        return f'<VeredelungsVerfahren {self.name}>'

    @classmethod
    def get_active(cls):
        return cls.query.filter_by(active=True).order_by(cls.sort_order, cls.name).all()

    @classmethod
    def get_by_code(cls, code):
        return cls.query.filter_by(code=code).first()

    @classmethod
    def seed_defaults(cls):
        """Erstellt die Standard-Veredelungsverfahren falls leer"""
        if cls.query.count() > 0:
            return

        defaults = [
            {'name': 'Stickerei', 'code': 'embroidery', 'icon': 'bi-brush',
             'beschreibung': 'Maschinenstickerei auf Textilien',
             'positionen': ['Brust links', 'Brust rechts', 'Ruecken oben', 'Ruecken gross',
                           'Aermel links', 'Aermel rechts', 'Kragen', 'Muetze vorne', 'Muetze seite'],
             'parameter': [
                 {'name': 'Geschwindigkeit', 'einheit': 'Stiche/min', 'param_type': 'number', 'default_value': '800'},
                 {'name': 'Unterfaden', 'einheit': '', 'param_type': 'text', 'default_value': ''},
                 {'name': 'Vlies', 'einheit': '', 'param_type': 'select',
                  'optionen': 'Abreissvlies,Schneidevlies,Wasserlöslich,Klebebvlies'},
             ]},
            {'name': 'Textildruck', 'code': 'printing', 'icon': 'bi-printer',
             'beschreibung': 'Siebdruck / Transferdruck auf Textilien',
             'positionen': ['Brust mittig', 'Brust links', 'Ruecken gross', 'Ruecken oben',
                           'Aermel links', 'Aermel rechts', 'Bein links', 'Bein rechts'],
             'parameter': [
                 {'name': 'Druckverfahren', 'einheit': '', 'param_type': 'select',
                  'optionen': 'Siebdruck,Transferdruck,Flexdruck,Flockdruck'},
                 {'name': 'Temperatur', 'einheit': '°C', 'param_type': 'number', 'default_value': '160'},
                 {'name': 'Presszeit', 'einheit': 'Sek', 'param_type': 'number', 'default_value': '15'},
             ]},
            {'name': 'DTF', 'code': 'dtf', 'icon': 'bi-layers',
             'beschreibung': 'Direct-to-Film Transfer',
             'positionen': ['Brust mittig', 'Brust links', 'Ruecken gross', 'Ruecken oben',
                           'Aermel links', 'Aermel rechts', 'Ganzes Motiv'],
             'parameter': [
                 {'name': 'Temperatur', 'einheit': '°C', 'param_type': 'number', 'default_value': '165'},
                 {'name': 'Presszeit', 'einheit': 'Sek', 'param_type': 'number', 'default_value': '15'},
                 {'name': 'Kaltabziehen', 'einheit': '', 'param_type': 'select', 'optionen': 'Ja,Nein'},
             ]},
            {'name': 'Sublimation', 'code': 'sublimation', 'icon': 'bi-droplet-half',
             'beschreibung': 'Sublimationsdruck (nur Polyester)',
             'positionen': ['Gesamtflaeche', 'Brust A4', 'Ruecken A3', 'Aermel',
                           'Allover Front', 'Allover Ruecken', 'Allover komplett'],
             'parameter': [
                 {'name': 'Temperatur', 'einheit': '°C', 'param_type': 'number', 'default_value': '200'},
                 {'name': 'Presszeit', 'einheit': 'Sek', 'param_type': 'text', 'default_value': '45'},
                 {'name': 'Druck', 'einheit': '', 'param_type': 'select',
                  'optionen': 'Sehr leicht,Leicht,Leicht/Mittel,Mittel,Stark'},
                 {'name': 'Papiertyp', 'einheit': '', 'param_type': 'select',
                  'optionen': 'Standard,Hochleistung,Tacky'},
                 {'name': 'Papierposition', 'einheit': '', 'param_type': 'select',
                  'optionen': 'Oben,Unten'},
                 {'name': 'Bemerkung', 'einheit': '', 'param_type': 'text', 'default_value': ''},
             ]},
        ]

        for vd in defaults:
            verfahren = cls(
                name=vd['name'], code=vd['code'], icon=vd['icon'],
                beschreibung=vd['beschreibung'], sort_order=defaults.index(vd)
            )
            db.session.add(verfahren)
            db.session.flush()

            for i, pos_name in enumerate(vd.get('positionen', [])):
                pos = VeredelungsPosition(
                    verfahren_id=verfahren.id, name=pos_name, sort_order=i
                )
                db.session.add(pos)

            for i, param in enumerate(vd.get('parameter', [])):
                p = VeredelungsParameter(
                    verfahren_id=verfahren.id,
                    name=param['name'],
                    einheit=param.get('einheit', ''),
                    param_type=param.get('param_type', 'text'),
                    default_value=param.get('default_value', ''),
                    optionen=param.get('optionen', ''),
                    sort_order=i
                )
                db.session.add(p)

        db.session.commit()


class VeredelungsPosition(db.Model):
    """Positionen pro Veredelungsverfahren (z.B. Brust links, Ruecken...)"""
    __tablename__ = 'veredelungs_positionen'

    id = db.Column(db.Integer, primary_key=True)
    verfahren_id = db.Column(db.Integer, db.ForeignKey('veredelungsverfahren.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)

    verfahren = db.relationship('VeredelungsVerfahren', back_populates='positionen')

    def __repr__(self):
        return f'<VeredelungsPosition {self.name}>'


class VeredelungsParameter(db.Model):
    """Parameter-Definitionen pro Verfahren (z.B. Temperatur, Zeit...)"""
    __tablename__ = 'veredelungs_parameter'

    id = db.Column(db.Integer, primary_key=True)
    verfahren_id = db.Column(db.Integer, db.ForeignKey('veredelungsverfahren.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    einheit = db.Column(db.String(30), default='')  # °C, Sek, mm/s, bar...
    param_type = db.Column(db.String(20), default='text')  # text, number, select
    default_value = db.Column(db.String(200), default='')
    optionen = db.Column(db.Text, default='')  # Komma-getrennt fuer select
    active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)

    verfahren = db.relationship('VeredelungsVerfahren', back_populates='parameter')

    def get_optionen_list(self):
        if not self.optionen:
            return []
        return [o.strip() for o in self.optionen.split(',') if o.strip()]

    def __repr__(self):
        return f'<VeredelungsParameter {self.name} ({self.einheit})>'


class ArtikelVeredelung(db.Model):
    """Veredelungs-spezifische Werte pro Artikel (z.B. Sublimation: 200°C, 45s)"""
    __tablename__ = 'artikel_veredelung'

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.String(50), db.ForeignKey('articles.id'), nullable=False, index=True)
    verfahren_id = db.Column(db.Integer, db.ForeignKey('veredelungsverfahren.id'), nullable=False)
    parameter_id = db.Column(db.Integer, db.ForeignKey('veredelungs_parameter.id'), nullable=False)
    wert = db.Column(db.String(200))

    # Beziehungen
    verfahren = db.relationship('VeredelungsVerfahren')
    parameter = db.relationship('VeredelungsParameter')

    __table_args__ = (
        db.UniqueConstraint('article_id', 'parameter_id', name='uq_artikel_parameter'),
    )

    def __repr__(self):
        return f'<ArtikelVeredelung Art={self.article_id} {self.parameter.name}={self.wert}>'
