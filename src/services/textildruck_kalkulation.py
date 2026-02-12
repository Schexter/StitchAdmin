# -*- coding: utf-8 -*-
"""
TEXTILDRUCK & STICKEREI KALKULATION
===================================
Umfassende Kalkulationsmodule für:
- Siebdruck (Screen Printing)
- DTG (Direct-to-Garment)
- Transferdruck
- Stickerei
- Flex/Flock

Mit Fixkosten, Staffelpreisen, Reserve und Wettbewerbsvergleich

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
from enum import Enum
import math


class DruckVerfahren(Enum):
    """Verfügbare Druckverfahren"""
    SIEBDRUCK = "siebdruck"
    DTG = "dtg"
    TRANSFER = "transfer"
    FLEX = "flex"
    FLOCK = "flock"
    SUBLIMATION = "sublimation"
    STICKEREI = "stickerei"


class TextildruckKalkulator:
    """
    Vollständige Textildruck-Kalkulation
    
    Berücksichtigt:
    - Fixkosten (Siebe, Einrichtung, Film)
    - Variable Kosten (Farbe, Arbeit)
    - Staffelpreise
    - Reserve/Ausschuss
    - Mindestmengen
    """
    
    # Standard-Preislisten (können überschrieben werden)
    STANDARD_PREISE = {
        'siebdruck': {
            'sieb_kosten': Decimal('35.00'),      # Pro Farbe/Sieb
            'film_kosten': Decimal('15.00'),      # Pro Farbe
            'einrichtung': Decimal('25.00'),      # Grundeinrichtung
            'farbe_pro_druck': Decimal('0.08'),   # Pro Druck pro Farbe
            'arbeit_pro_stueck': Decimal('0.50'), # Arbeitszeit pro Stück
            'mindestmenge': 25,
        },
        'dtg': {
            'einrichtung': Decimal('10.00'),
            'tinte_pro_cm2': Decimal('0.02'),     # Tintenkosten pro cm²
            'vorbehandlung': Decimal('0.80'),     # Bei dunklen Textilien
            'arbeit_pro_stueck': Decimal('1.50'),
            'mindestmenge': 1,
        },
        'transfer': {
            'transfer_pro_stueck': Decimal('2.50'),  # Transferfolie
            'presse_einrichtung': Decimal('5.00'),
            'arbeit_pro_stueck': Decimal('0.80'),
            'mindestmenge': 10,
        },
        'flex': {
            'material_pro_cm2': Decimal('0.015'),
            'schnitt_grundpreis': Decimal('8.00'),
            'entgitterung_pro_element': Decimal('0.30'),
            'presse_pro_stueck': Decimal('0.50'),
            'mindestmenge': 5,
        },
        'flock': {
            'material_pro_cm2': Decimal('0.020'),
            'schnitt_grundpreis': Decimal('10.00'),
            'entgitterung_pro_element': Decimal('0.40'),
            'presse_pro_stueck': Decimal('0.60'),
            'mindestmenge': 5,
        },
        'sublimation': {
            'druck_pro_a4': Decimal('1.50'),
            'papier_pro_a4': Decimal('0.30'),
            'presse_pro_stueck': Decimal('0.50'),
            'mindestmenge': 10,
        },
    }
    
    # Staffelrabatte (ab Menge -> Rabatt %)
    STAFFEL_RABATTE = [
        (1, Decimal('0')),
        (25, Decimal('5')),
        (50, Decimal('10')),
        (100, Decimal('15')),
        (250, Decimal('20')),
        (500, Decimal('25')),
        (1000, Decimal('30')),
    ]
    
    def __init__(self, preise: Dict = None):
        """
        Initialisiert Kalkulator mit optionalen Custom-Preisen
        """
        self.preise = preise or self.STANDARD_PREISE
    
    def berechne_siebdruck(self,
                           menge: int,
                           anzahl_farben: int,
                           druckgroesse_cm2: float = 200,
                           reserve_prozent: float = 5.0,
                           textil_ek: Decimal = Decimal('0'),
                           gewinn_prozent: float = 30.0) -> Dict:
        """
        Siebdruck-Kalkulation
        
        Args:
            menge: Bestellmenge
            anzahl_farben: Anzahl Druckfarben
            druckgroesse_cm2: Druckfläche in cm²
            reserve_prozent: Ausschuss-Reserve in %
            textil_ek: Einkaufspreis Textil
            gewinn_prozent: Gewinnaufschlag in %
        """
        p = self.preise['siebdruck']
        
        # Reserve berechnen
        reserve_stueck = math.ceil(menge * (reserve_prozent / 100))
        produktionsmenge = menge + reserve_stueck
        
        # === FIXKOSTEN ===
        sieb_kosten = p['sieb_kosten'] * Decimal(str(anzahl_farben))
        film_kosten = p['film_kosten'] * Decimal(str(anzahl_farben))
        einrichtung = p['einrichtung']
        
        fixkosten_gesamt = sieb_kosten + film_kosten + einrichtung
        fixkosten_pro_stueck = fixkosten_gesamt / Decimal(str(menge))
        
        # === VARIABLE KOSTEN ===
        farbe_kosten = p['farbe_pro_druck'] * Decimal(str(anzahl_farben)) * Decimal(str(produktionsmenge))
        arbeit_kosten = p['arbeit_pro_stueck'] * Decimal(str(produktionsmenge))
        textil_kosten = textil_ek * Decimal(str(produktionsmenge))
        
        variable_kosten_gesamt = farbe_kosten + arbeit_kosten + textil_kosten
        variable_kosten_pro_stueck = variable_kosten_gesamt / Decimal(str(menge))
        
        # === SELBSTKOSTEN ===
        selbstkosten_pro_stueck = fixkosten_pro_stueck + variable_kosten_pro_stueck
        selbstkosten_gesamt = selbstkosten_pro_stueck * Decimal(str(menge))
        
        # === STAFFELRABATT ===
        staffel_rabatt = self._get_staffelrabatt(menge)
        
        # === VERKAUFSPREIS ===
        gewinn = selbstkosten_pro_stueck * (Decimal(str(gewinn_prozent)) / 100)
        vk_netto = selbstkosten_pro_stueck + gewinn
        vk_netto_mit_staffel = vk_netto * (1 - staffel_rabatt / 100)
        vk_brutto = vk_netto_mit_staffel * Decimal('1.19')
        
        # === AUFTRAGSWERT ===
        auftragswert_netto = vk_netto_mit_staffel * Decimal(str(menge))
        auftragswert_brutto = auftragswert_netto * Decimal('1.19')
        
        return {
            'verfahren': 'Siebdruck',
            'menge': menge,
            'anzahl_farben': anzahl_farben,
            'reserve_stueck': reserve_stueck,
            'produktionsmenge': produktionsmenge,
            
            # Fixkosten
            'sieb_kosten': sieb_kosten.quantize(Decimal('0.01')),
            'film_kosten': film_kosten.quantize(Decimal('0.01')),
            'einrichtung': einrichtung.quantize(Decimal('0.01')),
            'fixkosten_gesamt': fixkosten_gesamt.quantize(Decimal('0.01')),
            'fixkosten_pro_stueck': fixkosten_pro_stueck.quantize(Decimal('0.01')),
            
            # Variable Kosten
            'farbe_kosten': farbe_kosten.quantize(Decimal('0.01')),
            'arbeit_kosten': arbeit_kosten.quantize(Decimal('0.01')),
            'textil_kosten': textil_kosten.quantize(Decimal('0.01')),
            'variable_kosten_gesamt': variable_kosten_gesamt.quantize(Decimal('0.01')),
            'variable_kosten_pro_stueck': variable_kosten_pro_stueck.quantize(Decimal('0.01')),
            
            # Kalkulation
            'selbstkosten_pro_stueck': selbstkosten_pro_stueck.quantize(Decimal('0.01')),
            'selbstkosten_gesamt': selbstkosten_gesamt.quantize(Decimal('0.01')),
            'gewinn_aufschlag': gewinn.quantize(Decimal('0.01')),
            'staffel_rabatt_prozent': staffel_rabatt,
            
            # Verkaufspreise
            'vk_pro_stueck_netto': vk_netto_mit_staffel.quantize(Decimal('0.01')),
            'vk_pro_stueck_brutto': vk_brutto.quantize(Decimal('0.01')),
            'auftragswert_netto': auftragswert_netto.quantize(Decimal('0.01')),
            'auftragswert_brutto': auftragswert_brutto.quantize(Decimal('0.01')),
            
            # Rentabilität
            'deckungsbeitrag': (auftragswert_netto - selbstkosten_gesamt).quantize(Decimal('0.01')),
            'marge_prozent': ((auftragswert_netto - selbstkosten_gesamt) / auftragswert_netto * 100).quantize(Decimal('0.1')) if auftragswert_netto > 0 else Decimal('0'),
        }
    
    def berechne_dtg(self,
                     menge: int,
                     druckgroesse_cm2: float,
                     dunkles_textil: bool = False,
                     reserve_prozent: float = 3.0,
                     textil_ek: Decimal = Decimal('0'),
                     gewinn_prozent: float = 35.0) -> Dict:
        """
        DTG (Direct-to-Garment) Kalkulation
        """
        p = self.preise['dtg']
        
        reserve_stueck = math.ceil(menge * (reserve_prozent / 100))
        produktionsmenge = menge + reserve_stueck
        
        # Fixkosten
        einrichtung = p['einrichtung']
        
        # Variable Kosten
        tinte_kosten = p['tinte_pro_cm2'] * Decimal(str(druckgroesse_cm2)) * Decimal(str(produktionsmenge))
        vorbehandlung = p['vorbehandlung'] * Decimal(str(produktionsmenge)) if dunkles_textil else Decimal('0')
        arbeit_kosten = p['arbeit_pro_stueck'] * Decimal(str(produktionsmenge))
        textil_kosten = textil_ek * Decimal(str(produktionsmenge))
        
        variable_gesamt = tinte_kosten + vorbehandlung + arbeit_kosten + textil_kosten
        variable_pro_stueck = variable_gesamt / Decimal(str(menge))
        
        selbstkosten = (einrichtung / Decimal(str(menge))) + variable_pro_stueck
        
        gewinn = selbstkosten * (Decimal(str(gewinn_prozent)) / 100)
        staffel = self._get_staffelrabatt(menge)
        vk_netto = (selbstkosten + gewinn) * (1 - staffel / 100)
        
        return {
            'verfahren': 'DTG-Druck',
            'menge': menge,
            'druckgroesse_cm2': druckgroesse_cm2,
            'dunkles_textil': dunkles_textil,
            'reserve_stueck': reserve_stueck,
            
            'einrichtung': einrichtung.quantize(Decimal('0.01')),
            'tinte_kosten': tinte_kosten.quantize(Decimal('0.01')),
            'vorbehandlung': vorbehandlung.quantize(Decimal('0.01')),
            'arbeit_kosten': arbeit_kosten.quantize(Decimal('0.01')),
            
            'selbstkosten_pro_stueck': selbstkosten.quantize(Decimal('0.01')),
            'staffel_rabatt_prozent': staffel,
            'vk_pro_stueck_netto': vk_netto.quantize(Decimal('0.01')),
            'vk_pro_stueck_brutto': (vk_netto * Decimal('1.19')).quantize(Decimal('0.01')),
            'auftragswert_netto': (vk_netto * Decimal(str(menge))).quantize(Decimal('0.01')),
            'auftragswert_brutto': (vk_netto * Decimal(str(menge)) * Decimal('1.19')).quantize(Decimal('0.01')),
        }
    
    def berechne_flex_flock(self,
                            menge: int,
                            flaeche_cm2: float,
                            anzahl_elemente: int = 1,
                            ist_flock: bool = False,
                            reserve_prozent: float = 5.0,
                            textil_ek: Decimal = Decimal('0'),
                            gewinn_prozent: float = 40.0) -> Dict:
        """
        Flex- oder Flock-Druck Kalkulation
        """
        verfahren = 'flock' if ist_flock else 'flex'
        p = self.preise[verfahren]
        
        reserve_stueck = math.ceil(menge * (reserve_prozent / 100))
        produktionsmenge = menge + reserve_stueck
        
        # Fixkosten
        schnitt_kosten = p['schnitt_grundpreis']
        
        # Variable Kosten
        material_kosten = p['material_pro_cm2'] * Decimal(str(flaeche_cm2)) * Decimal(str(produktionsmenge))
        entgitterung = p['entgitterung_pro_element'] * Decimal(str(anzahl_elemente)) * Decimal(str(produktionsmenge))
        presse_kosten = p['presse_pro_stueck'] * Decimal(str(produktionsmenge))
        textil_kosten = textil_ek * Decimal(str(produktionsmenge))
        
        variable_gesamt = material_kosten + entgitterung + presse_kosten + textil_kosten
        selbstkosten = (schnitt_kosten / Decimal(str(menge))) + (variable_gesamt / Decimal(str(menge)))
        
        gewinn = selbstkosten * (Decimal(str(gewinn_prozent)) / 100)
        staffel = self._get_staffelrabatt(menge)
        vk_netto = (selbstkosten + gewinn) * (1 - staffel / 100)
        
        return {
            'verfahren': 'Flock-Druck' if ist_flock else 'Flex-Druck',
            'menge': menge,
            'flaeche_cm2': flaeche_cm2,
            'anzahl_elemente': anzahl_elemente,
            'reserve_stueck': reserve_stueck,
            
            'schnitt_kosten': schnitt_kosten.quantize(Decimal('0.01')),
            'material_kosten': material_kosten.quantize(Decimal('0.01')),
            'entgitterung': entgitterung.quantize(Decimal('0.01')),
            'presse_kosten': presse_kosten.quantize(Decimal('0.01')),
            
            'selbstkosten_pro_stueck': selbstkosten.quantize(Decimal('0.01')),
            'staffel_rabatt_prozent': staffel,
            'vk_pro_stueck_netto': vk_netto.quantize(Decimal('0.01')),
            'vk_pro_stueck_brutto': (vk_netto * Decimal('1.19')).quantize(Decimal('0.01')),
            'auftragswert_netto': (vk_netto * Decimal(str(menge))).quantize(Decimal('0.01')),
            'auftragswert_brutto': (vk_netto * Decimal(str(menge)) * Decimal('1.19')).quantize(Decimal('0.01')),
        }
    
    def berechne_staffelpreise(self,
                               verfahren: str,
                               mengen: List[int],
                               **kwargs) -> List[Dict]:
        """
        Berechnet Preise für verschiedene Staffelmengen
        
        Args:
            verfahren: 'siebdruck', 'dtg', 'flex', etc.
            mengen: Liste von Mengen [25, 50, 100, 250, 500]
            **kwargs: Parameter für das jeweilige Verfahren
        """
        ergebnisse = []
        
        for menge in mengen:
            if verfahren == 'siebdruck':
                result = self.berechne_siebdruck(menge=menge, **kwargs)
            elif verfahren == 'dtg':
                result = self.berechne_dtg(menge=menge, **kwargs)
            elif verfahren in ('flex', 'flock'):
                result = self.berechne_flex_flock(menge=menge, ist_flock=(verfahren == 'flock'), **kwargs)
            else:
                continue
            
            ergebnisse.append({
                'menge': menge,
                'stueckpreis_netto': result['vk_pro_stueck_netto'],
                'stueckpreis_brutto': result['vk_pro_stueck_brutto'],
                'auftragswert_netto': result['auftragswert_netto'],
                'auftragswert_brutto': result['auftragswert_brutto'],
                'staffel_rabatt': result['staffel_rabatt_prozent'],
            })
        
        return ergebnisse
    
    def vergleiche_verfahren(self,
                             menge: int,
                             anzahl_farben: int = 1,
                             druckgroesse_cm2: float = 200,
                             textil_ek: Decimal = Decimal('0')) -> List[Dict]:
        """
        Vergleicht alle Verfahren für eine Bestellung
        """
        vergleich = []
        
        # Siebdruck
        try:
            sieb = self.berechne_siebdruck(menge, anzahl_farben, druckgroesse_cm2, textil_ek=textil_ek)
            vergleich.append({
                'verfahren': 'Siebdruck',
                'stueckpreis': sieb['vk_pro_stueck_brutto'],
                'auftragswert': sieb['auftragswert_brutto'],
                'mindestmenge': self.preise['siebdruck']['mindestmenge'],
                'empfohlen_ab': 50,
                'vorteile': 'Günstig bei großen Mengen, brillante Farben',
                'nachteile': 'Hohe Fixkosten bei kleinen Mengen',
            })
        except:
            pass
        
        # DTG
        try:
            dtg = self.berechne_dtg(menge, druckgroesse_cm2, textil_ek=textil_ek)
            vergleich.append({
                'verfahren': 'DTG-Druck',
                'stueckpreis': dtg['vk_pro_stueck_brutto'],
                'auftragswert': dtg['auftragswert_brutto'],
                'mindestmenge': self.preise['dtg']['mindestmenge'],
                'empfohlen_ab': 1,
                'vorteile': 'Keine Mindestmenge, Fotodruck möglich',
                'nachteile': 'Teurer bei großen Mengen',
            })
        except:
            pass
        
        # Flex
        try:
            flex = self.berechne_flex_flock(menge, druckgroesse_cm2, textil_ek=textil_ek)
            vergleich.append({
                'verfahren': 'Flex-Druck',
                'stueckpreis': flex['vk_pro_stueck_brutto'],
                'auftragswert': flex['auftragswert_brutto'],
                'mindestmenge': self.preise['flex']['mindestmenge'],
                'empfohlen_ab': 5,
                'vorteile': 'Langlebig, einfarbige Motive',
                'nachteile': 'Nur einfarbig, aufwendig bei Details',
            })
        except:
            pass
        
        # Nach Preis sortieren
        vergleich.sort(key=lambda x: x['stueckpreis'])
        
        # Günstigstes markieren
        if vergleich:
            vergleich[0]['ist_guenstigste'] = True
        
        return vergleich
    
    def _get_staffelrabatt(self, menge: int) -> Decimal:
        """Ermittelt Staffelrabatt für Menge"""
        rabatt = Decimal('0')
        for min_menge, prozent in self.STAFFEL_RABATTE:
            if menge >= min_menge:
                rabatt = prozent
        return rabatt


class StickKalkulator:
    """
    Erweiterte Stickerei-Kalkulation
    """
    
    def berechne_komplett(self,
                          stichzahl: int,
                          farbwechsel: int,
                          menge: int,
                          preis_pro_1000: Decimal = Decimal('0.80'),
                          preis_farbwechsel: Decimal = Decimal('0.50'),
                          mindestpreis: Decimal = Decimal('5.00'),
                          einrichtekosten: Decimal = Decimal('0'),
                          digitalisierung: Decimal = Decimal('0'),
                          textil_ek: Decimal = Decimal('0'),
                          reserve_prozent: float = 3.0,
                          gewinn_prozent: float = 30.0) -> Dict:
        """
        Vollständige Stickerei-Kalkulation inkl. Digitalisierung
        """
        reserve = math.ceil(menge * (reserve_prozent / 100))
        produktionsmenge = menge + reserve
        
        # Stickkosten
        preis_stiche = (Decimal(str(stichzahl)) / 1000) * preis_pro_1000
        preis_farben = Decimal(str(farbwechsel)) * preis_farbwechsel
        stickpreis = max(preis_stiche + preis_farben, mindestpreis)
        
        # Fixkosten auf Menge verteilen
        fix_pro_stueck = (einrichtekosten + digitalisierung) / Decimal(str(menge))
        
        # Textil
        textil_pro_stueck = textil_ek
        
        # Selbstkosten
        selbstkosten = stickpreis + fix_pro_stueck + textil_pro_stueck
        
        # Verkaufspreis
        gewinn = selbstkosten * (Decimal(str(gewinn_prozent)) / 100)
        vk_netto = selbstkosten + gewinn
        vk_brutto = vk_netto * Decimal('1.19')
        
        return {
            'verfahren': 'Stickerei',
            'stichzahl': stichzahl,
            'farbwechsel': farbwechsel,
            'menge': menge,
            'reserve': reserve,
            
            'preis_stiche': preis_stiche.quantize(Decimal('0.01')),
            'preis_farben': preis_farben.quantize(Decimal('0.01')),
            'stickpreis': stickpreis.quantize(Decimal('0.01')),
            'mindestpreis_aktiv': stickpreis == mindestpreis,
            
            'einrichtekosten': einrichtekosten.quantize(Decimal('0.01')),
            'digitalisierung': digitalisierung.quantize(Decimal('0.01')),
            'fix_pro_stueck': fix_pro_stueck.quantize(Decimal('0.01')),
            
            'textil_pro_stueck': textil_pro_stueck.quantize(Decimal('0.01')),
            'selbstkosten': selbstkosten.quantize(Decimal('0.01')),
            
            'vk_pro_stueck_netto': vk_netto.quantize(Decimal('0.01')),
            'vk_pro_stueck_brutto': vk_brutto.quantize(Decimal('0.01')),
            'auftragswert_netto': (vk_netto * Decimal(str(menge))).quantize(Decimal('0.01')),
            'auftragswert_brutto': (vk_brutto * Decimal(str(menge))).quantize(Decimal('0.01')),
            
            'deckungsbeitrag': (vk_netto * Decimal(str(menge)) - selbstkosten * Decimal(str(menge))).quantize(Decimal('0.01')),
        }
