# -*- coding: utf-8 -*-
"""
BUCHHALTUNG BERECHNUNGS-SERVICE
===============================
Berechnungen für:
- BWA (Betriebswirtschaftliche Auswertung)
- GuV (Gewinn- und Verlustrechnung)
- USt-Voranmeldung
- Liquiditätsplanung
- Kalkulationen (Stundensatz, Stickpreis)
- Deckungsbeitragsrechnung

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import calendar
import logging

from src.models import db

logger = logging.getLogger(__name__)


class BWAService:
    """
    Betriebswirtschaftliche Auswertung (BWA)
    
    Standardform nach DATEV-BWA Nr. 1
    """
    
    # BWA-Positionen nach Kontenklassen
    BWA_STRUKTUR = {
        'umsatzerloese': {'klassen': [8], 'label': 'Umsatzerlöse', 'positiv': True},
        'bestandsveraenderung': {'klassen': [], 'label': 'Bestandsveränderung'},
        'aktivierte_eigenleistung': {'klassen': [], 'label': 'Aktivierte Eigenleistungen'},
        'gesamtleistung': {'label': 'Gesamtleistung', 'summe': True},
        
        'materialaufwand': {'klassen': [3], 'label': 'Materialaufwand/Wareneinkauf'},
        'rohertrag': {'label': 'Rohertrag', 'summe': True},
        
        'personalaufwand': {'konten': ['41', '42', '43'], 'label': 'Personalaufwand'},
        'raumkosten': {'konten': ['42'], 'label': 'Raumkosten'},
        'betriebliche_steuern': {'konten': ['70'], 'label': 'Betriebliche Steuern'},
        'versicherungen': {'konten': ['44'], 'label': 'Versicherungen'},
        'kfz_kosten': {'konten': ['45'], 'label': 'Kfz-Kosten'},
        'werbekosten': {'konten': ['46'], 'label': 'Werbe-/Reisekosten'},
        'reparaturen': {'konten': ['47'], 'label': 'Reparaturen/Instandhaltung'},
        'sonstige_kosten': {'konten': ['49'], 'label': 'Sonstige Kosten'},
        
        'betriebsergebnis': {'label': 'Betriebsergebnis', 'summe': True},
        
        'zinsen': {'konten': ['70'], 'label': 'Zinsaufwand'},
        'abschreibungen': {'klassen': [7], 'label': 'Abschreibungen'},
        
        'ergebnis_vor_steuern': {'label': 'Ergebnis vor Steuern', 'summe': True},
        'steuern_einkommen': {'label': 'Steuern vom Einkommen'},
        'jahresueberschuss': {'label': 'Jahresüberschuss/-fehlbetrag', 'summe': True},
    }
    
    def berechne_bwa(self, jahr: int, monat: int = None, 
                     quartal: int = None) -> Dict:
        """
        Berechnet BWA für einen Zeitraum
        
        Args:
            jahr: Geschäftsjahr
            monat: Optional - Einzelmonat (1-12)
            quartal: Optional - Quartal (1-4)
        
        Returns:
            Dict mit BWA-Positionen und Werten
        """
        from src.models.buchhaltung import Buchung, Konto
        
        # Zeitraum bestimmen
        if monat:
            datum_von = date(jahr, monat, 1)
            letzter_tag = calendar.monthrange(jahr, monat)[1]
            datum_bis = date(jahr, monat, letzter_tag)
            zeitraum_label = f"{monat:02d}/{jahr}"
        elif quartal:
            start_monat = (quartal - 1) * 3 + 1
            end_monat = quartal * 3
            datum_von = date(jahr, start_monat, 1)
            letzter_tag = calendar.monthrange(jahr, end_monat)[1]
            datum_bis = date(jahr, end_monat, letzter_tag)
            zeitraum_label = f"Q{quartal}/{jahr}"
        else:
            datum_von = date(jahr, 1, 1)
            datum_bis = date(jahr, 12, 31)
            zeitraum_label = str(jahr)
        
        # Buchungen laden
        buchungen = Buchung.query.filter(
            Buchung.buchungsdatum >= datum_von,
            Buchung.buchungsdatum <= datum_bis,
            Buchung.ist_storniert == False
        ).all()
        
        # Nach Konten aggregieren
        konten_summen = defaultdict(Decimal)
        
        for b in buchungen:
            if b.konto:
                konten_summen[b.konto.kontonummer] += Decimal(str(b.betrag_netto or 0))
        
        # BWA berechnen
        bwa = {
            'zeitraum': zeitraum_label,
            'datum_von': datum_von,
            'datum_bis': datum_bis,
            'positionen': {},
            'erloese': {},
            'aufwendungen': {},
        }
        
        # Erlöse (Klasse 8)
        erloese_gesamt = Decimal('0')
        for konto_nr, summe in konten_summen.items():
            if konto_nr.startswith('8'):
                konto = Konto.query.filter_by(kontonummer=konto_nr).first()
                bwa['erloese'][konto.bezeichnung if konto else konto_nr] = summe
                erloese_gesamt += summe
        
        bwa['summe_erloese'] = erloese_gesamt
        
        # Aufwendungen (Klassen 3, 4, 7)
        aufwendungen_gesamt = Decimal('0')
        for konto_nr, summe in konten_summen.items():
            if konto_nr.startswith(('3', '4', '7')):
                konto = Konto.query.filter_by(kontonummer=konto_nr).first()
                bwa['aufwendungen'][konto.bezeichnung if konto else konto_nr] = summe
                aufwendungen_gesamt += summe
        
        bwa['summe_aufwendungen'] = aufwendungen_gesamt
        
        # Betriebsergebnis
        bwa['betriebsergebnis'] = erloese_gesamt - aufwendungen_gesamt
        
        # Rohertrag (Erlöse - Wareneinkauf)
        wareneinkauf = sum(v for k, v in konten_summen.items() if k.startswith('3'))
        bwa['rohertrag'] = erloese_gesamt - wareneinkauf
        
        # Rohertrag-Marge
        if erloese_gesamt > 0:
            bwa['rohertrag_marge'] = (bwa['rohertrag'] / erloese_gesamt * 100).quantize(Decimal('0.1'))
        else:
            bwa['rohertrag_marge'] = Decimal('0')
        
        return bwa
    
    def berechne_bwa_vergleich(self, jahr: int) -> Dict:
        """
        Berechnet BWA mit Vorjahresvergleich und Monatsübersicht
        """
        ergebnis = {
            'aktuelles_jahr': jahr,
            'vorjahr': jahr - 1,
            'monate': [],
            'jahressumme': None,
            'vorjahr_summe': None,
        }
        
        # Aktuelles Jahr - alle Monate
        for monat in range(1, 13):
            try:
                bwa_monat = self.berechne_bwa(jahr, monat=monat)
                ergebnis['monate'].append(bwa_monat)
            except Exception:
                ergebnis['monate'].append(None)
        
        # Jahressumme
        ergebnis['jahressumme'] = self.berechne_bwa(jahr)
        
        # Vorjahr
        ergebnis['vorjahr_summe'] = self.berechne_bwa(jahr - 1)
        
        # Veränderung berechnen
        if ergebnis['jahressumme'] and ergebnis['vorjahr_summe']:
            akt = ergebnis['jahressumme']['betriebsergebnis']
            vor = ergebnis['vorjahr_summe']['betriebsergebnis']
            
            if vor and vor != 0:
                ergebnis['veraenderung_prozent'] = ((akt - vor) / abs(vor) * 100).quantize(Decimal('0.1'))
            else:
                ergebnis['veraenderung_prozent'] = Decimal('0')
        
        return ergebnis


class UStService:
    """
    USt-Voranmeldung Berechnung
    """
    
    def berechne_voranmeldung(self, jahr: int, monat: int = None, 
                               quartal: int = None) -> Dict:
        """
        Berechnet USt-Voranmeldung aus Buchungen
        """
        from src.models.buchhaltung import Buchung, UStVoranmeldung
        
        # Zeitraum
        if monat:
            datum_von = date(jahr, monat, 1)
            letzter_tag = calendar.monthrange(jahr, monat)[1]
            datum_bis = date(jahr, monat, letzter_tag)
        elif quartal:
            start_monat = (quartal - 1) * 3 + 1
            end_monat = quartal * 3
            datum_von = date(jahr, start_monat, 1)
            letzter_tag = calendar.monthrange(jahr, end_monat)[1]
            datum_bis = date(jahr, end_monat, letzter_tag)
        else:
            raise ValueError("Monat oder Quartal muss angegeben werden")
        
        # Buchungen laden
        buchungen = Buchung.query.filter(
            Buchung.buchungsdatum >= datum_von,
            Buchung.buchungsdatum <= datum_bis,
            Buchung.ist_storniert == False
        ).all()
        
        # Berechnung
        ergebnis = {
            'zeitraum_von': datum_von,
            'zeitraum_bis': datum_bis,
            'umsatz_19_netto': Decimal('0'),
            'ust_19': Decimal('0'),
            'umsatz_7_netto': Decimal('0'),
            'ust_7': Decimal('0'),
            'vorsteuer_19': Decimal('0'),
            'vorsteuer_7': Decimal('0'),
            'vorsteuer_gesamt': Decimal('0'),
            'ust_zahllast': Decimal('0'),
        }
        
        for b in buchungen:
            mwst = Decimal(str(b.mwst_satz or 0))
            netto = Decimal(str(b.betrag_netto or 0))
            mwst_betrag = Decimal(str(b.mwst_betrag or 0))
            
            if b.buchungs_art == 'einnahme':
                # Umsatzsteuer
                if mwst == Decimal('19'):
                    ergebnis['umsatz_19_netto'] += netto
                    ergebnis['ust_19'] += mwst_betrag
                elif mwst == Decimal('7'):
                    ergebnis['umsatz_7_netto'] += netto
                    ergebnis['ust_7'] += mwst_betrag
            
            elif b.buchungs_art == 'ausgabe':
                # Vorsteuer
                if mwst == Decimal('19'):
                    ergebnis['vorsteuer_19'] += mwst_betrag
                elif mwst == Decimal('7'):
                    ergebnis['vorsteuer_7'] += mwst_betrag
        
        # Vorsteuer gesamt
        ergebnis['vorsteuer_gesamt'] = ergebnis['vorsteuer_19'] + ergebnis['vorsteuer_7']
        
        # Zahllast (USt - Vorsteuer)
        ust_gesamt = ergebnis['ust_19'] + ergebnis['ust_7']
        ergebnis['ust_zahllast'] = ust_gesamt - ergebnis['vorsteuer_gesamt']
        
        return ergebnis


class LiquiditaetsService:
    """
    Liquiditätsplanung und -prognose
    """
    
    def berechne_liquiditaet(self, stichtag: date = None) -> Dict:
        """
        Berechnet aktuelle Liquidität
        """
        from src.models.document_workflow import BusinessDocument, DokumentStatus
        from src.models.models import Customer
        
        if stichtag is None:
            stichtag = date.today()
        
        ergebnis = {
            'stichtag': stichtag,
            'verfuegbar': Decimal('0'),
            'forderungen_offen': Decimal('0'),
            'forderungen_ueberfaellig': Decimal('0'),
            'verbindlichkeiten_offen': Decimal('0'),
            'liquiditaet_prognose': {},
        }
        
        # Offene Forderungen aus Rechnungen
        try:
            offene_rechnungen = BusinessDocument.query.filter(
                BusinessDocument.dokument_typ.in_(['rechnung', 'anzahlung', 'teilrechnung']),
                BusinessDocument.status.in_([DokumentStatus.OFFEN.value, DokumentStatus.TEILBEZAHLT.value])
            ).all()
            
            for r in offene_rechnungen:
                offen = Decimal(str(r.offener_betrag or r.summe_brutto or 0))
                ergebnis['forderungen_offen'] += offen
                
                if r.faelligkeitsdatum and r.faelligkeitsdatum < stichtag:
                    ergebnis['forderungen_ueberfaellig'] += offen
        except Exception as e:
            logger.warning(f"Fehler bei Forderungsberechnung: {e}")
        
        # Prognose für nächste Wochen
        for wochen in [1, 2, 4, 8, 12]:
            prognose_datum = stichtag + timedelta(weeks=wochen)
            
            # Fällige Forderungen bis dahin
            try:
                faellig_bis = BusinessDocument.query.filter(
                    BusinessDocument.dokument_typ.in_(['rechnung', 'anzahlung', 'teilrechnung']),
                    BusinessDocument.status.in_([DokumentStatus.OFFEN.value, DokumentStatus.TEILBEZAHLT.value]),
                    BusinessDocument.faelligkeitsdatum <= prognose_datum
                ).all()
                
                summe = sum(Decimal(str(r.offener_betrag or r.summe_brutto or 0)) for r in faellig_bis)
                ergebnis['liquiditaet_prognose'][f'{wochen}_wochen'] = summe
            except Exception:
                ergebnis['liquiditaet_prognose'][f'{wochen}_wochen'] = Decimal('0')
        
        return ergebnis
    
    def berechne_cashflow(self, jahr: int, monat: int = None) -> Dict:
        """
        Berechnet Cashflow (vereinfacht)
        """
        from src.models.buchhaltung import Buchung
        
        if monat:
            datum_von = date(jahr, monat, 1)
            letzter_tag = calendar.monthrange(jahr, monat)[1]
            datum_bis = date(jahr, monat, letzter_tag)
        else:
            datum_von = date(jahr, 1, 1)
            datum_bis = date(jahr, 12, 31)
        
        buchungen = Buchung.query.filter(
            Buchung.buchungsdatum >= datum_von,
            Buchung.buchungsdatum <= datum_bis,
            Buchung.ist_storniert == False
        ).all()
        
        einnahmen = Decimal('0')
        ausgaben = Decimal('0')
        
        for b in buchungen:
            if b.buchungs_art == 'einnahme':
                einnahmen += Decimal(str(b.betrag_brutto or 0))
            elif b.buchungs_art == 'ausgabe':
                ausgaben += Decimal(str(b.betrag_brutto or 0))
        
        return {
            'zeitraum_von': datum_von,
            'zeitraum_bis': datum_bis,
            'einnahmen': einnahmen,
            'ausgaben': ausgaben,
            'cashflow': einnahmen - ausgaben,
        }


class KalkulationsService:
    """
    Kalkulationen für Stickerei
    """
    
    def berechne_stundensatz(self, 
                             jahresgehalt: Decimal,
                             arbeitsstunden_jahr: int = 1720,
                             gemeinkosten_prozent: Decimal = Decimal('50'),
                             gewinn_prozent: Decimal = Decimal('20')) -> Dict:
        """
        Berechnet Stundensatz auf Vollkostenbasis
        
        Args:
            jahresgehalt: Brutto-Jahresgehalt inkl. AG-Anteil
            arbeitsstunden_jahr: Produktive Stunden/Jahr (Standard: 1720)
            gemeinkosten_prozent: Gemeinkostenaufschlag in %
            gewinn_prozent: Gewinnaufschlag in %
        """
        # Grundkosten pro Stunde
        kosten_pro_stunde = jahresgehalt / Decimal(str(arbeitsstunden_jahr))
        
        # Gemeinkosten
        gemeinkosten = kosten_pro_stunde * (gemeinkosten_prozent / 100)
        
        # Selbstkosten
        selbstkosten = kosten_pro_stunde + gemeinkosten
        
        # Gewinn
        gewinn = selbstkosten * (gewinn_prozent / 100)
        
        # Stundensatz netto
        stundensatz_netto = selbstkosten + gewinn
        
        # Brutto (19% MwSt)
        stundensatz_brutto = stundensatz_netto * Decimal('1.19')
        
        return {
            'grundkosten_stunde': kosten_pro_stunde.quantize(Decimal('0.01')),
            'gemeinkosten': gemeinkosten.quantize(Decimal('0.01')),
            'selbstkosten': selbstkosten.quantize(Decimal('0.01')),
            'gewinn': gewinn.quantize(Decimal('0.01')),
            'stundensatz_netto': stundensatz_netto.quantize(Decimal('0.01')),
            'stundensatz_brutto': stundensatz_brutto.quantize(Decimal('0.01')),
            'parameter': {
                'jahresgehalt': jahresgehalt,
                'arbeitsstunden': arbeitsstunden_jahr,
                'gemeinkosten_prozent': gemeinkosten_prozent,
                'gewinn_prozent': gewinn_prozent,
            }
        }
    
    def berechne_stickpreis(self,
                            stichzahl: int,
                            farbwechsel: int = 0,
                            preis_pro_1000: Decimal = Decimal('0.80'),
                            preis_farbwechsel: Decimal = Decimal('0.50'),
                            mindestpreis: Decimal = Decimal('5.00'),
                            einrichtekosten: Decimal = Decimal('0'),
                            menge: int = 1) -> Dict:
        """
        Berechnet Stickpreis pro Stück
        
        Args:
            stichzahl: Anzahl Stiche im Design
            farbwechsel: Anzahl Farbwechsel
            preis_pro_1000: Preis pro 1000 Stiche
            preis_farbwechsel: Preis pro Farbwechsel
            mindestpreis: Mindestpreis pro Stück
            einrichtekosten: Einmalige Einrichtekosten
            menge: Stückzahl
        """
        # Grundpreis
        preis_stiche = (Decimal(str(stichzahl)) / 1000) * preis_pro_1000
        preis_farben = Decimal(str(farbwechsel)) * preis_farbwechsel
        
        # Stückpreis
        stueckpreis = preis_stiche + preis_farben
        
        # Mindestpreis prüfen
        if stueckpreis < mindestpreis:
            stueckpreis = mindestpreis
        
        # Einrichtekosten auf Menge verteilen
        einrichte_pro_stueck = einrichtekosten / Decimal(str(menge)) if menge > 0 else Decimal('0')
        
        # Gesamtpreis pro Stück
        gesamtpreis_stueck = stueckpreis + einrichte_pro_stueck
        
        # Auftragssumme
        auftragssumme_netto = gesamtpreis_stueck * Decimal(str(menge))
        auftragssumme_brutto = auftragssumme_netto * Decimal('1.19')
        
        return {
            'stichzahl': stichzahl,
            'farbwechsel': farbwechsel,
            'menge': menge,
            'preis_stiche': preis_stiche.quantize(Decimal('0.01')),
            'preis_farbwechsel': preis_farben.quantize(Decimal('0.01')),
            'stueckpreis_basis': (preis_stiche + preis_farben).quantize(Decimal('0.01')),
            'mindestpreis_aktiv': stueckpreis == mindestpreis,
            'einrichte_pro_stueck': einrichte_pro_stueck.quantize(Decimal('0.01')),
            'stueckpreis_netto': gesamtpreis_stueck.quantize(Decimal('0.01')),
            'stueckpreis_brutto': (gesamtpreis_stueck * Decimal('1.19')).quantize(Decimal('0.01')),
            'auftragssumme_netto': auftragssumme_netto.quantize(Decimal('0.01')),
            'auftragssumme_brutto': auftragssumme_brutto.quantize(Decimal('0.01')),
            'einrichtekosten_gesamt': einrichtekosten,
        }
    
    def berechne_deckungsbeitrag(self,
                                  umsatz: Decimal,
                                  variable_kosten: Decimal,
                                  fixkosten: Decimal = Decimal('0')) -> Dict:
        """
        Berechnet Deckungsbeitrag
        
        DB I = Umsatz - variable Kosten
        DB II = DB I - Fixkosten
        """
        db_1 = umsatz - variable_kosten
        db_1_prozent = (db_1 / umsatz * 100) if umsatz > 0 else Decimal('0')
        
        db_2 = db_1 - fixkosten
        db_2_prozent = (db_2 / umsatz * 100) if umsatz > 0 else Decimal('0')
        
        # Break-Even
        if db_1_prozent > 0:
            break_even = fixkosten / (db_1_prozent / 100)
        else:
            break_even = None
        
        return {
            'umsatz': umsatz,
            'variable_kosten': variable_kosten,
            'fixkosten': fixkosten,
            'deckungsbeitrag_1': db_1.quantize(Decimal('0.01')),
            'deckungsbeitrag_1_prozent': db_1_prozent.quantize(Decimal('0.1')),
            'deckungsbeitrag_2': db_2.quantize(Decimal('0.01')),
            'deckungsbeitrag_2_prozent': db_2_prozent.quantize(Decimal('0.1')),
            'break_even_umsatz': break_even.quantize(Decimal('0.01')) if break_even else None,
        }


class FinanzplanService:
    """
    Finanzplanung und Budget-Vergleich
    """
    
    def erstelle_finanzplan(self, jahr: int, 
                            umsatz_plan: Decimal,
                            kosten_plan: Dict[str, Decimal]) -> Dict:
        """
        Erstellt Finanzplan für ein Jahr
        """
        from src.models.buchhaltung import Finanzplan
        
        plan = {
            'jahr': jahr,
            'umsatz_plan': umsatz_plan,
            'kosten_plan': kosten_plan,
            'monate': []
        }
        
        # Monatliche Verteilung (gleichmäßig)
        umsatz_monat = umsatz_plan / 12
        
        for monat in range(1, 13):
            plan['monate'].append({
                'monat': monat,
                'umsatz_plan': umsatz_monat.quantize(Decimal('0.01')),
                'kosten_plan': {k: (v / 12).quantize(Decimal('0.01')) for k, v in kosten_plan.items()},
            })
        
        # Summen
        plan['kosten_gesamt'] = sum(kosten_plan.values())
        plan['ergebnis_plan'] = umsatz_plan - plan['kosten_gesamt']
        
        return plan
    
    def plan_ist_vergleich(self, jahr: int, monat: int = None) -> Dict:
        """
        Vergleicht Plan mit Ist-Werten
        """
        bwa_service = BWAService()
        
        # Ist-Werte
        if monat:
            ist = bwa_service.berechne_bwa(jahr, monat=monat)
        else:
            ist = bwa_service.berechne_bwa(jahr)
        
        # Plan laden (TODO: aus Finanzplan-Tabelle)
        # Hier vereinfachte Dummy-Werte
        plan = {
            'umsatz': Decimal('100000'),
            'kosten': Decimal('80000'),
        }
        
        # Abweichungen
        umsatz_abweichung = ist['summe_erloese'] - plan['umsatz']
        kosten_abweichung = ist['summe_aufwendungen'] - plan['kosten']
        
        return {
            'zeitraum': ist['zeitraum'],
            'plan': plan,
            'ist': {
                'umsatz': ist['summe_erloese'],
                'kosten': ist['summe_aufwendungen'],
                'ergebnis': ist['betriebsergebnis'],
            },
            'abweichung': {
                'umsatz': umsatz_abweichung,
                'umsatz_prozent': (umsatz_abweichung / plan['umsatz'] * 100).quantize(Decimal('0.1')) if plan['umsatz'] else Decimal('0'),
                'kosten': kosten_abweichung,
                'kosten_prozent': (kosten_abweichung / plan['kosten'] * 100).quantize(Decimal('0.1')) if plan['kosten'] else Decimal('0'),
            }
        }
