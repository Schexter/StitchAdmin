# -*- coding: utf-8 -*-
"""
KONTENRAHMEN SERVICE
====================
Automatische Kontenrahmen-Auswahl und -Initialisierung

Unterstützte Kontenrahmen:
- SKR03 (Standard für kleine/mittlere Unternehmen)
- SKR04 (Prozessorientiert)

Branchen-Vorlagen:
- Textildruck/Stickerei
- Handel
- Handwerk
- Dienstleistung

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from typing import Dict, List, Optional
from decimal import Decimal
from src.models import db

import logging
logger = logging.getLogger(__name__)


# ============================================================================
# VOLLSTÄNDIGER SKR03 KONTENRAHMEN
# ============================================================================

SKR03_KOMPLETT = {
    # ========== KLASSE 0: ANLAGEVERMÖGEN ==========
    'klasse_0': {
        'name': 'Anlagevermögen',
        'konten': [
            {'nr': '0027', 'bez': 'EDV-Software', 'bestand': True},
            {'nr': '0210', 'bez': 'Maschinen', 'bestand': True},
            {'nr': '0400', 'bez': 'Technische Anlagen und Maschinen', 'bestand': True},
            {'nr': '0410', 'bez': 'Stickmaschinen', 'bestand': True},  # BRANCHE
            {'nr': '0420', 'bez': 'Druckmaschinen', 'bestand': True},  # BRANCHE
            {'nr': '0430', 'bez': 'Transferpressen', 'bestand': True},  # BRANCHE
            {'nr': '0440', 'bez': 'Schneideplotter', 'bestand': True},  # BRANCHE
            {'nr': '0480', 'bez': 'Geringwertige Wirtschaftsgüter', 'bestand': True},
            {'nr': '0650', 'bez': 'Büroeinrichtung', 'bestand': True},
            {'nr': '0670', 'bez': 'Geschäftsausstattung', 'bestand': True},
            {'nr': '0690', 'bez': 'Sonstige Betriebs- und Geschäftsausstattung', 'bestand': True},
        ]
    },
    
    # ========== KLASSE 1: UMLAUFVERMÖGEN ==========
    'klasse_1': {
        'name': 'Umlaufvermögen',
        'konten': [
            {'nr': '1000', 'bez': 'Kasse', 'bestand': True},
            {'nr': '1200', 'bez': 'Bank', 'bestand': True},
            {'nr': '1210', 'bez': 'Sparkasse', 'bestand': True},
            {'nr': '1220', 'bez': 'Volksbank', 'bestand': True},
            {'nr': '1300', 'bez': 'Wechsel', 'bestand': True},
            {'nr': '1400', 'bez': 'Forderungen aus Lieferungen und Leistungen', 'bestand': True},
            {'nr': '1410', 'bez': 'Forderungen aus L+L (Inland)', 'bestand': True},
            {'nr': '1420', 'bez': 'Forderungen aus L+L (EU)', 'bestand': True},
            {'nr': '1450', 'bez': 'Forderungen gegen verbundene Unternehmen', 'bestand': True},
            {'nr': '1500', 'bez': 'Sonstige Vermögensgegenstände', 'bestand': True},
            {'nr': '1510', 'bez': 'Geleistete Anzahlungen', 'bestand': True},
            {'nr': '1520', 'bez': 'Kautionen', 'bestand': True},
            {'nr': '1540', 'bez': 'Steuererstattungsansprüche', 'bestand': True},
            {'nr': '1570', 'bez': 'Abziehbare Vorsteuer', 'bestand': True},
            {'nr': '1571', 'bez': 'Abziehbare Vorsteuer 7%', 'bestand': True},
            {'nr': '1576', 'bez': 'Abziehbare Vorsteuer 19%', 'bestand': True},
            {'nr': '1580', 'bez': 'Vorsteuer aus innergem. Erwerb', 'bestand': True},
            {'nr': '1590', 'bez': 'Durchlaufende Posten', 'bestand': True},
            {'nr': '1600', 'bez': 'Verbindlichkeiten aus Lieferungen und Leistungen', 'bestand': True},
            {'nr': '1700', 'bez': 'Sonstige Verbindlichkeiten', 'bestand': True},
            {'nr': '1710', 'bez': 'Erhaltene Anzahlungen auf Bestellungen', 'bestand': True},
            {'nr': '1740', 'bez': 'Verbindlichkeiten aus Steuern', 'bestand': True},
            {'nr': '1750', 'bez': 'Verbindlichkeiten im Rahmen der sozialen Sicherheit', 'bestand': True},
            {'nr': '1770', 'bez': 'Umsatzsteuer 7%', 'bestand': True},
            {'nr': '1771', 'bez': 'Umsatzsteuer 19%', 'bestand': True},
            {'nr': '1780', 'bez': 'Umsatzsteuer-Vorauszahlungen', 'bestand': True},
            {'nr': '1790', 'bez': 'Umsatzsteuer Vorjahr', 'bestand': True},
        ]
    },
    
    # ========== KLASSE 2: EIGENKAPITAL ==========
    'klasse_2': {
        'name': 'Eigenkapital/Schulden',
        'konten': [
            {'nr': '2000', 'bez': 'Eigenkapital', 'bestand': True},
            {'nr': '2010', 'bez': 'Gezeichnetes Kapital', 'bestand': True},
            {'nr': '2100', 'bez': 'Kapitalrücklage', 'bestand': True},
            {'nr': '2900', 'bez': 'Privat', 'bestand': True},
            {'nr': '2910', 'bez': 'Privatentnahmen', 'bestand': True},
            {'nr': '2920', 'bez': 'Privateinlagen', 'bestand': True},
        ]
    },
    
    # ========== KLASSE 3: WARENEINGANG ==========
    'klasse_3': {
        'name': 'Wareneingang/Fremdleistungen',
        'konten': [
            {'nr': '3000', 'bez': 'Einkauf Roh-, Hilfs- und Betriebsstoffe', 'aufwand': True},
            {'nr': '3100', 'bez': 'Fremdleistungen', 'aufwand': True},
            {'nr': '3110', 'bez': 'Fremdleistungen Digitalisierung', 'aufwand': True},  # BRANCHE
            {'nr': '3120', 'bez': 'Fremdleistungen Stickerei', 'aufwand': True},  # BRANCHE
            {'nr': '3130', 'bez': 'Fremdleistungen Druck', 'aufwand': True},  # BRANCHE
            {'nr': '3200', 'bez': 'Wareneingang Textilien', 'aufwand': True},  # BRANCHE
            {'nr': '3210', 'bez': 'Wareneingang T-Shirts', 'aufwand': True},  # BRANCHE
            {'nr': '3220', 'bez': 'Wareneingang Poloshirts', 'aufwand': True},  # BRANCHE
            {'nr': '3230', 'bez': 'Wareneingang Jacken/Pullover', 'aufwand': True},  # BRANCHE
            {'nr': '3240', 'bez': 'Wareneingang Arbeitskleidung', 'aufwand': True},  # BRANCHE
            {'nr': '3300', 'bez': 'Wareneingang 7% VSt', 'aufwand': True},
            {'nr': '3400', 'bez': 'Wareneingang 19% VSt', 'aufwand': True},
            {'nr': '3500', 'bez': 'Stickgarne', 'aufwand': True},  # BRANCHE
            {'nr': '3510', 'bez': 'Flexfolien', 'aufwand': True},  # BRANCHE
            {'nr': '3520', 'bez': 'Flockfolien', 'aufwand': True},  # BRANCHE
            {'nr': '3530', 'bez': 'Druckfarben/Tinten', 'aufwand': True},  # BRANCHE
            {'nr': '3540', 'bez': 'Transferpapier', 'aufwand': True},  # BRANCHE
            {'nr': '3550', 'bez': 'Stickvlies/Unterlegmaterial', 'aufwand': True},  # BRANCHE
            {'nr': '3560', 'bez': 'Siebe/Rahmen', 'aufwand': True},  # BRANCHE
            {'nr': '3700', 'bez': 'Nachlässe aus Einkauf', 'aufwand': True},
            {'nr': '3800', 'bez': 'Bezugsnebenkosten', 'aufwand': True},
        ]
    },
    
    # ========== KLASSE 4: AUFWENDUNGEN ==========
    'klasse_4': {
        'name': 'Betriebliche Aufwendungen',
        'konten': [
            {'nr': '4100', 'bez': 'Löhne', 'aufwand': True},
            {'nr': '4110', 'bez': 'Löhne Produktion', 'aufwand': True},
            {'nr': '4120', 'bez': 'Gehälter', 'aufwand': True},
            {'nr': '4125', 'bez': 'Löhne für Minijobber', 'aufwand': True},
            {'nr': '4130', 'bez': 'Gesetzliche Sozialaufwendungen', 'aufwand': True},
            {'nr': '4138', 'bez': 'Beiträge zur Berufsgenossenschaft', 'aufwand': True},
            {'nr': '4140', 'bez': 'Freiwillige Sozialaufwendungen', 'aufwand': True},
            {'nr': '4170', 'bez': 'Vermögenswirksame Leistungen', 'aufwand': True},
            {'nr': '4190', 'bez': 'Aushilfslöhne', 'aufwand': True},
            {'nr': '4200', 'bez': 'Raumkosten', 'aufwand': True},
            {'nr': '4210', 'bez': 'Miete', 'aufwand': True},
            {'nr': '4220', 'bez': 'Pacht', 'aufwand': True},
            {'nr': '4230', 'bez': 'Heizung', 'aufwand': True},
            {'nr': '4240', 'bez': 'Gas, Strom, Wasser', 'aufwand': True},
            {'nr': '4250', 'bez': 'Reinigung', 'aufwand': True},
            {'nr': '4260', 'bez': 'Instandhaltung Gebäude', 'aufwand': True},
            {'nr': '4280', 'bez': 'Sonstige Raumkosten', 'aufwand': True},
            {'nr': '4300', 'bez': 'Versicherungen', 'aufwand': True},
            {'nr': '4320', 'bez': 'Beiträge', 'aufwand': True},
            {'nr': '4360', 'bez': 'Kfz-Steuer', 'aufwand': True},
            {'nr': '4380', 'bez': 'Sonstige Abgaben', 'aufwand': True},
            {'nr': '4500', 'bez': 'Kfz-Kosten', 'aufwand': True},
            {'nr': '4510', 'bez': 'Kfz-Steuer', 'aufwand': True},
            {'nr': '4520', 'bez': 'Kfz-Versicherung', 'aufwand': True},
            {'nr': '4530', 'bez': 'Laufende Kfz-Kosten', 'aufwand': True},
            {'nr': '4540', 'bez': 'Kfz-Reparaturen', 'aufwand': True},
            {'nr': '4580', 'bez': 'Sonstige Kfz-Kosten', 'aufwand': True},
            {'nr': '4600', 'bez': 'Werbekosten', 'aufwand': True},
            {'nr': '4610', 'bez': 'Werbekosten Online', 'aufwand': True},
            {'nr': '4630', 'bez': 'Geschenke an Kunden', 'aufwand': True},
            {'nr': '4640', 'bez': 'Repräsentationskosten', 'aufwand': True},
            {'nr': '4650', 'bez': 'Reisekosten', 'aufwand': True},
            {'nr': '4660', 'bez': 'Reisekosten Arbeitnehmer', 'aufwand': True},
            {'nr': '4670', 'bez': 'Bewirtungskosten', 'aufwand': True},
            {'nr': '4700', 'bez': 'Porto', 'aufwand': True},
            {'nr': '4710', 'bez': 'Porto', 'aufwand': True},
            {'nr': '4720', 'bez': 'Telefon', 'aufwand': True},
            {'nr': '4730', 'bez': 'Internet/Onlinedienste', 'aufwand': True},
            {'nr': '4750', 'bez': 'Bürobedarf', 'aufwand': True},
            {'nr': '4760', 'bez': 'Zeitschriften, Bücher', 'aufwand': True},
            {'nr': '4780', 'bez': 'Fremdarbeiten', 'aufwand': True},
            {'nr': '4800', 'bez': 'Reparaturen und Instandhaltung', 'aufwand': True},
            {'nr': '4810', 'bez': 'Reparaturen Maschinen', 'aufwand': True},  # BRANCHE
            {'nr': '4820', 'bez': 'Wartung Software', 'aufwand': True},
            {'nr': '4830', 'bez': 'Leasingkosten', 'aufwand': True},
            {'nr': '4900', 'bez': 'Sonstige betriebliche Aufwendungen', 'aufwand': True},
            {'nr': '4910', 'bez': 'Nebenkosten des Geldverkehrs', 'aufwand': True},
            {'nr': '4920', 'bez': 'Rechts- und Beratungskosten', 'aufwand': True},
            {'nr': '4930', 'bez': 'Buchführungskosten', 'aufwand': True},
            {'nr': '4940', 'bez': 'Mieten für Einrichtungen', 'aufwand': True},
            {'nr': '4950', 'bez': 'Aus- und Fortbildung', 'aufwand': True},
            {'nr': '4960', 'bez': 'Zeitarbeit/Leiharbeit', 'aufwand': True},
            {'nr': '4970', 'bez': 'Nebenkosten des Geldverkehrs', 'aufwand': True},
            {'nr': '4980', 'bez': 'Betriebsbedarf', 'aufwand': True},
        ]
    },
    
    # ========== KLASSE 7: ABSCHREIBUNGEN ==========
    'klasse_7': {
        'name': 'Abschreibungen/Zinsen',
        'konten': [
            {'nr': '7000', 'bez': 'Abschreibungen auf Sachanlagen', 'aufwand': True},
            {'nr': '7010', 'bez': 'Abschreibungen Maschinen', 'aufwand': True},
            {'nr': '7020', 'bez': 'Abschreibungen Büroausstattung', 'aufwand': True},
            {'nr': '7030', 'bez': 'Abschreibungen Kfz', 'aufwand': True},
            {'nr': '7050', 'bez': 'Abschreibungen GWG', 'aufwand': True},
            {'nr': '7080', 'bez': 'Abschreibungen Gebäude', 'aufwand': True},
            {'nr': '7100', 'bez': 'Abschreibungen auf immaterielle Vermögensgegenstände', 'aufwand': True},
            {'nr': '7300', 'bez': 'Zinsen und ähnliche Aufwendungen', 'aufwand': True},
            {'nr': '7310', 'bez': 'Zinsen für kurzfristige Verbindlichkeiten', 'aufwand': True},
            {'nr': '7320', 'bez': 'Zinsen für langfristige Verbindlichkeiten', 'aufwand': True},
        ]
    },
    
    # ========== KLASSE 8: ERLÖSE ==========
    'klasse_8': {
        'name': 'Erlöse',
        'konten': [
            {'nr': '8100', 'bez': 'Steuerfreie Umsätze', 'ertrag': True},
            {'nr': '8120', 'bez': 'Steuerfreie Umsätze §4 UStG', 'ertrag': True},
            {'nr': '8125', 'bez': 'Steuerfreie innergem. Lieferungen', 'ertrag': True},
            {'nr': '8200', 'bez': 'Erlöse aus Anlagenverkäufen', 'ertrag': True},
            {'nr': '8300', 'bez': 'Erlöse 7% USt', 'ertrag': True},
            {'nr': '8400', 'bez': 'Erlöse 19% USt', 'ertrag': True},
            {'nr': '8500', 'bez': 'Erlöse Stickerei', 'ertrag': True},  # BRANCHE
            {'nr': '8510', 'bez': 'Erlöse Siebdruck', 'ertrag': True},  # BRANCHE
            {'nr': '8520', 'bez': 'Erlöse DTG-Druck', 'ertrag': True},  # BRANCHE
            {'nr': '8530', 'bez': 'Erlöse Flex/Flock', 'ertrag': True},  # BRANCHE
            {'nr': '8540', 'bez': 'Erlöse Transferdruck', 'ertrag': True},  # BRANCHE
            {'nr': '8550', 'bez': 'Erlöse Sublimation', 'ertrag': True},  # BRANCHE
            {'nr': '8560', 'bez': 'Erlöse Digitalisierung', 'ertrag': True},  # BRANCHE
            {'nr': '8570', 'bez': 'Erlöse Textilverkauf', 'ertrag': True},  # BRANCHE
            {'nr': '8590', 'bez': 'Erlöse Sonstige', 'ertrag': True},
            {'nr': '8600', 'bez': 'Erlösschmälerungen', 'ertrag': True},
            {'nr': '8700', 'bez': 'Erlöse aus Vermietung', 'ertrag': True},
            {'nr': '8800', 'bez': 'Provisionserlöse', 'ertrag': True},
            {'nr': '8900', 'bez': 'Sonstige betriebliche Erträge', 'ertrag': True},
            {'nr': '8910', 'bez': 'Erträge aus Zuschreibungen', 'ertrag': True},
            {'nr': '8920', 'bez': 'Erträge aus Abgängen Anlagevermögen', 'ertrag': True},
            {'nr': '8950', 'bez': 'Periodenfremde Erträge', 'ertrag': True},
        ]
    },
}


# ============================================================================
# BRANCHEN-VORLAGEN
# ============================================================================

BRANCHEN_VORLAGEN = {
    'textildruck_stickerei': {
        'name': 'Textildruck & Stickerei',
        'beschreibung': 'Kontenrahmen für Textilveredler, Stickereien und Druckereien',
        'zusatz_konten': [
            # Anlagen
            {'nr': '0410', 'bez': 'Stickmaschinen'},
            {'nr': '0420', 'bez': 'Druckmaschinen'},
            {'nr': '0430', 'bez': 'Transferpressen'},
            {'nr': '0440', 'bez': 'Schneideplotter'},
            # Waren
            {'nr': '3200', 'bez': 'Wareneingang Textilien'},
            {'nr': '3500', 'bez': 'Stickgarne'},
            {'nr': '3510', 'bez': 'Flexfolien'},
            {'nr': '3530', 'bez': 'Druckfarben/Tinten'},
            # Erlöse
            {'nr': '8500', 'bez': 'Erlöse Stickerei'},
            {'nr': '8510', 'bez': 'Erlöse Siebdruck'},
            {'nr': '8520', 'bez': 'Erlöse DTG-Druck'},
            {'nr': '8530', 'bez': 'Erlöse Flex/Flock'},
        ],
    },
    'handel': {
        'name': 'Handel',
        'beschreibung': 'Standard-Kontenrahmen für Handelsunternehmen',
        'zusatz_konten': [],
    },
    'handwerk': {
        'name': 'Handwerk',
        'beschreibung': 'Kontenrahmen für Handwerksbetriebe',
        'zusatz_konten': [],
    },
    'dienstleistung': {
        'name': 'Dienstleistung',
        'beschreibung': 'Kontenrahmen für Dienstleister',
        'zusatz_konten': [],
    },
}


class KontenrahmenService:
    """Service für Kontenrahmen-Verwaltung"""
    
    def __init__(self):
        self.kontenrahmen = SKR03_KOMPLETT
    
    def initialisiere_kontenrahmen(self, 
                                    rahmen: str = 'SKR03',
                                    branche: str = None) -> Dict:
        """
        Initialisiert Kontenrahmen mit optionaler Branchen-Vorlage
        
        Args:
            rahmen: 'SKR03' oder 'SKR04'
            branche: 'textildruck_stickerei', 'handel', 'handwerk', 'dienstleistung'
        """
        from src.models.buchhaltung import Konto
        
        ergebnis = {
            'rahmen': rahmen,
            'branche': branche,
            'angelegt': 0,
            'uebersprungen': 0,
            'fehler': [],
        }
        
        # Basis-Konten anlegen
        for klasse_key, klasse_data in self.kontenrahmen.items():
            for konto_def in klasse_data['konten']:
                try:
                    existing = Konto.query.filter_by(kontonummer=konto_def['nr']).first()
                    if existing:
                        ergebnis['uebersprungen'] += 1
                        continue
                    
                    konto = Konto(
                        kontonummer=konto_def['nr'],
                        bezeichnung=konto_def['bez'],
                        kontenrahmen=rahmen,
                        kontenklasse=int(konto_def['nr'][0]),
                        ist_bestandskonto=konto_def.get('bestand', False),
                        ist_ertragskonto=konto_def.get('ertrag', False),
                        ist_aufwandskonto=konto_def.get('aufwand', False),
                        datev_kontonummer=konto_def['nr'],
                    )
                    db.session.add(konto)
                    ergebnis['angelegt'] += 1
                    
                except Exception as e:
                    ergebnis['fehler'].append(f"{konto_def['nr']}: {e}")
        
        db.session.commit()
        
        return ergebnis
    
    def get_branchen(self) -> List[Dict]:
        """Liste verfügbarer Branchen-Vorlagen"""
        return [
            {
                'key': key,
                'name': data['name'],
                'beschreibung': data['beschreibung'],
                'anzahl_zusatz': len(data['zusatz_konten']),
            }
            for key, data in BRANCHEN_VORLAGEN.items()
        ]
    
    def get_konten_vorschau(self, klasse: int = None) -> List[Dict]:
        """Vorschau der Konten für eine Klasse"""
        if klasse is not None:
            klasse_key = f'klasse_{klasse}'
            if klasse_key in self.kontenrahmen:
                return self.kontenrahmen[klasse_key]['konten']
        
        # Alle Konten
        alle = []
        for klasse_data in self.kontenrahmen.values():
            alle.extend(klasse_data['konten'])
        return alle
