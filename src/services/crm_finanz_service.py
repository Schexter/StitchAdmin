# -*- coding: utf-8 -*-
"""
CRM-FINANZ SERVICE
==================
Verknüpfung von CRM und Finanzdaten:
- Kundenumsatz & Statistiken
- Zahlungsmoral-Score
- Offene Posten pro Kunde
- Ratenzahlungen
- Automatische Kalendertermine

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import logging

from src.models import db

logger = logging.getLogger(__name__)


class CRMFinanzService:
    """
    Service für CRM-Finanz-Integration
    """
    
    def get_kunde_finanzdaten(self, kunde_id: int) -> Dict:
        """
        Holt alle Finanzdaten für einen Kunden
        """
        from src.models.document_workflow import BusinessDocument, DokumentStatus
        from src.models.models import Customer
        
        kunde = Customer.query.get(kunde_id)
        if not kunde:
            return None
        
        # Alle Dokumente des Kunden
        dokumente = BusinessDocument.query.filter_by(kunde_id=kunde_id).all()
        
        # Rechnungen
        rechnungen = [d for d in dokumente if d.dokument_typ in 
                      ['rechnung', 'teilrechnung', 'schlussrechnung']]
        
        # Berechnungen
        umsatz_gesamt = sum(Decimal(str(r.summe_brutto or 0)) for r in rechnungen 
                           if r.status in ['bezahlt', 'offen', 'teilbezahlt'])
        
        umsatz_jahr = sum(Decimal(str(r.summe_brutto or 0)) for r in rechnungen 
                         if r.status in ['bezahlt', 'offen', 'teilbezahlt']
                         and r.datum and r.datum.year == date.today().year)
        
        # Offene Posten
        offene_rechnungen = [r for r in rechnungen if r.status in ['offen', 'teilbezahlt']]
        offene_summe = sum(Decimal(str(r.offener_betrag or r.summe_brutto or 0)) 
                          for r in offene_rechnungen)
        
        # Überfällige
        heute = date.today()
        ueberfaellige = [r for r in offene_rechnungen 
                        if r.faelligkeitsdatum and r.faelligkeitsdatum < heute]
        ueberfaellig_summe = sum(Decimal(str(r.offener_betrag or r.summe_brutto or 0)) 
                                for r in ueberfaellige)
        
        # Zahlungsmoral
        zahlungsmoral = self._berechne_zahlungsmoral(rechnungen)
        
        # Durchschnittlicher Auftragswert
        bezahlte = [r for r in rechnungen if r.status == 'bezahlt']
        avg_auftrag = (sum(Decimal(str(r.summe_brutto or 0)) for r in bezahlte) / 
                      len(bezahlte)) if bezahlte else Decimal('0')
        
        # Letzte Aktivität
        letzte_rechnung = max((r.datum for r in rechnungen if r.datum), default=None)
        
        return {
            'kunde_id': kunde_id,
            'kunde_name': kunde.display_name,
            
            # Umsatz
            'umsatz_gesamt': float(umsatz_gesamt),
            'umsatz_aktuelles_jahr': float(umsatz_jahr),
            'anzahl_rechnungen': len(rechnungen),
            'durchschnitt_auftrag': float(avg_auftrag),
            
            # Offene Posten
            'offene_posten_anzahl': len(offene_rechnungen),
            'offene_posten_summe': float(offene_summe),
            'ueberfaellig_anzahl': len(ueberfaellige),
            'ueberfaellig_summe': float(ueberfaellig_summe),
            
            # Zahlungsmoral
            'zahlungsmoral_score': zahlungsmoral['score'],
            'zahlungsmoral_label': zahlungsmoral['label'],
            'zahlungsmoral_farbe': zahlungsmoral['farbe'],
            'durchschnitt_zahlungsziel_tage': zahlungsmoral['avg_tage'],
            
            # Aktivität
            'letzte_rechnung': letzte_rechnung.isoformat() if letzte_rechnung else None,
            'tage_seit_letzter_rechnung': (heute - letzte_rechnung).days if letzte_rechnung else None,
            
            # Details
            'offene_rechnungen': [
                {
                    'id': r.id,
                    'nummer': r.dokumentnummer,
                    'datum': r.datum.isoformat() if r.datum else None,
                    'betrag': float(r.summe_brutto or 0),
                    'offen': float(r.offener_betrag or r.summe_brutto or 0),
                    'faellig': r.faelligkeitsdatum.isoformat() if r.faelligkeitsdatum else None,
                    'ueberfaellig': r.faelligkeitsdatum < heute if r.faelligkeitsdatum else False,
                }
                for r in offene_rechnungen
            ],
        }
    
    def _berechne_zahlungsmoral(self, rechnungen: List) -> Dict:
        """
        Berechnet Zahlungsmoral-Score basierend auf Zahlungsverhalten
        
        Score: 0-100 (100 = immer pünktlich)
        """
        bezahlte = [r for r in rechnungen if r.status == 'bezahlt' 
                    and r.faelligkeitsdatum and r.bezahlt_am]
        
        if not bezahlte:
            return {
                'score': 50,  # Neutral für neue Kunden
                'label': 'Keine Daten',
                'farbe': 'secondary',
                'avg_tage': 0,
            }
        
        # Durchschnittliche Abweichung vom Zahlungsziel
        abweichungen = []
        for r in bezahlte:
            if isinstance(r.bezahlt_am, datetime):
                bezahlt_datum = r.bezahlt_am.date()
            else:
                bezahlt_datum = r.bezahlt_am
            
            tage_diff = (bezahlt_datum - r.faelligkeitsdatum).days
            abweichungen.append(tage_diff)
        
        avg_abweichung = sum(abweichungen) / len(abweichungen)
        
        # Score berechnen
        if avg_abweichung <= 0:
            score = 100  # Immer pünktlich oder früher
        elif avg_abweichung <= 7:
            score = 80  # Bis 1 Woche Verzug
        elif avg_abweichung <= 14:
            score = 60  # Bis 2 Wochen
        elif avg_abweichung <= 30:
            score = 40  # Bis 1 Monat
        else:
            score = max(0, 30 - int(avg_abweichung / 10))  # Stark reduziert
        
        # Label
        if score >= 90:
            label = 'Ausgezeichnet'
            farbe = 'success'
        elif score >= 70:
            label = 'Gut'
            farbe = 'info'
        elif score >= 50:
            label = 'Durchschnittlich'
            farbe = 'warning'
        elif score >= 30:
            label = 'Problematisch'
            farbe = 'danger'
        else:
            label = 'Kritisch'
            farbe = 'dark'
        
        return {
            'score': score,
            'label': label,
            'farbe': farbe,
            'avg_tage': round(avg_abweichung, 1),
        }
    
    def get_top_kunden(self, limit: int = 10, jahr: int = None) -> List[Dict]:
        """
        Top-Kunden nach Umsatz
        """
        from src.models.document_workflow import BusinessDocument
        from src.models.models import Customer
        
        jahr = jahr or date.today().year
        
        # Alle Rechnungen des Jahres
        rechnungen = BusinessDocument.query.filter(
            BusinessDocument.dokument_typ.in_(['rechnung', 'teilrechnung', 'schlussrechnung']),
            BusinessDocument.status.in_(['bezahlt', 'offen', 'teilbezahlt']),
            db.extract('year', BusinessDocument.datum) == jahr
        ).all()
        
        # Nach Kunde gruppieren
        kunde_umsatz = defaultdict(Decimal)
        for r in rechnungen:
            if r.kunde_id:
                kunde_umsatz[r.kunde_id] += Decimal(str(r.summe_brutto or 0))
        
        # Sortieren und Top X
        top = sorted(kunde_umsatz.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        result = []
        for kunde_id, umsatz in top:
            kunde = Customer.query.get(kunde_id)
            if kunde:
                result.append({
                    'kunde_id': kunde_id,
                    'kunde_name': kunde.display_name,
                    'umsatz': float(umsatz),
                })
        
        return result
    
    def erstelle_ratenzahlung(self, 
                              kunde_id: int,
                              dokument_id: int,
                              gesamtbetrag: Decimal,
                              anzahl_raten: int,
                              erste_rate: date,
                              intervall_tage: int = 30) -> Dict:
        """
        Erstellt Ratenzahlung mit automatischen Kalenderterminen
        """
        from src.models.kalender import RatenzahlungTermin, KalenderTermin
        
        rate_betrag = (gesamtbetrag / anzahl_raten).quantize(Decimal('0.01'))
        
        # Ratenzahlung erstellen
        ratenzahlung = RatenzahlungTermin(
            kunde_id=kunde_id,
            dokument_id=dokument_id,
            gesamtbetrag=gesamtbetrag,
            anzahl_raten=anzahl_raten,
            rate_betrag=rate_betrag,
            erste_rate=erste_rate,
            intervall_tage=intervall_tage,
            restbetrag=gesamtbetrag,
        )
        
        db.session.add(ratenzahlung)
        db.session.flush()  # ID generieren
        
        # Kalendertermine erstellen
        termine = ratenzahlung.erstelle_kalendertermine()
        for termin in termine:
            db.session.add(termin)
        
        db.session.commit()
        
        return {
            'ratenzahlung_id': ratenzahlung.id,
            'rate_betrag': float(rate_betrag),
            'termine_erstellt': len(termine),
            'erste_rate': erste_rate.isoformat(),
            'letzte_rate': (erste_rate + timedelta(days=(anzahl_raten-1) * intervall_tage)).isoformat(),
        }
    
    def get_faellige_raten(self, tage_voraus: int = 7) -> List[Dict]:
        """
        Holt alle Raten die in den nächsten X Tagen fällig sind
        """
        from src.models.kalender import KalenderTermin
        from src.models.models import Customer
        
        heute = date.today()
        grenze = heute + timedelta(days=tage_voraus)
        
        termine = KalenderTermin.query.filter(
            KalenderTermin.termin_typ == 'rate',
            KalenderTermin.status != 'abgeschlossen',
            KalenderTermin.start_datum >= heute,
            KalenderTermin.start_datum <= grenze
        ).order_by(KalenderTermin.start_datum).all()
        
        result = []
        for t in termine:
            kunde = Customer.query.get(t.kunde_id) if t.kunde_id else None
            result.append({
                'termin_id': t.id,
                'datum': t.start_datum.isoformat(),
                'titel': t.titel,
                'betrag': float(t.betrag) if t.betrag else 0,
                'kunde_id': t.kunde_id,
                'kunde_name': kunde.display_name if kunde else 'Unbekannt',
                'tage_bis': (t.start_datum - heute).days,
            })
        
        return result
    
    def erstelle_crm_followup(self,
                              kunde_id: int,
                              datum: date,
                              titel: str,
                              beschreibung: str = None,
                              mitarbeiter_id: int = None) -> int:
        """
        Erstellt CRM-Nachfasstermin im Kalender
        """
        from src.models.kalender import KalenderTermin
        
        termin = KalenderTermin(
            titel=titel,
            beschreibung=beschreibung,
            start_datum=datum,
            ganztaegig=True,
            termin_typ='crm_followup',
            status='geplant',
            farbe='#17a2b8',  # Info-Blau
            kunde_id=kunde_id,
            mitarbeiter_id=mitarbeiter_id,
            erinnerung_minuten=1440,  # 1 Tag vorher
        )
        
        db.session.add(termin)
        db.session.commit()
        
        return termin.id


class KalenderService:
    """
    Service für Kalender-Operationen
    """
    
    def get_termine(self,
                    start: date,
                    ende: date,
                    ressource_ids: List[int] = None,
                    termin_typen: List[str] = None) -> List[Dict]:
        """
        Holt Termine für Zeitraum (für FullCalendar)
        """
        from src.models.kalender import KalenderTermin
        
        query = KalenderTermin.query.filter(
            KalenderTermin.start_datum >= start,
            KalenderTermin.start_datum <= ende,
            KalenderTermin.status != 'storniert'
        )
        
        if ressource_ids:
            query = query.filter(KalenderTermin.ressource_id.in_(ressource_ids))
        
        if termin_typen:
            query = query.filter(KalenderTermin.termin_typ.in_(termin_typen))
        
        termine = query.order_by(KalenderTermin.start_datum, KalenderTermin.start_zeit).all()
        
        return [t.to_fullcalendar() for t in termine]
    
    def get_ressourcen(self, nur_aktiv: bool = True) -> List[Dict]:
        """
        Holt alle Ressourcen (für FullCalendar Resources)
        """
        from src.models.kalender import KalenderRessource
        
        query = KalenderRessource.query
        if nur_aktiv:
            query = query.filter_by(ist_aktiv=True)
        
        ressourcen = query.order_by(KalenderRessource.reihenfolge).all()
        
        return [r.to_fullcalendar() for r in ressourcen]
    
    def erstelle_produktionstermin(self,
                                    auftrag_id: int,
                                    ressource_id: int,
                                    start_datum: date,
                                    start_zeit: time,
                                    ende_zeit: time,
                                    titel: str = None) -> int:
        """
        Erstellt Produktionstermin
        """
        from src.models.kalender import KalenderTermin
        from src.models.models import Order
        
        auftrag = Order.query.get(auftrag_id)
        
        termin = KalenderTermin(
            titel=titel or f"Auftrag {auftrag.order_number}" if auftrag else "Produktion",
            start_datum=start_datum,
            start_zeit=start_zeit,
            ende_datum=start_datum,
            ende_zeit=ende_zeit,
            termin_typ='produktion',
            status='geplant',
            auftrag_id=auftrag_id,
            ressource_id=ressource_id,
            kunde_id=auftrag.customer_id if auftrag else None,
            farbe='#28a745',  # Grün für Produktion
        )
        
        db.session.add(termin)
        db.session.commit()
        
        return termin.id
    
    def get_ressource_auslastung(self, 
                                  ressource_id: int,
                                  start: date,
                                  ende: date) -> Dict:
        """
        Berechnet Auslastung einer Ressource
        """
        from src.models.kalender import KalenderTermin, KalenderRessource
        
        ressource = KalenderRessource.query.get(ressource_id)
        if not ressource:
            return None
        
        termine = KalenderTermin.query.filter(
            KalenderTermin.ressource_id == ressource_id,
            KalenderTermin.start_datum >= start,
            KalenderTermin.start_datum <= ende,
            KalenderTermin.status.notin_(['storniert', 'verschoben'])
        ).all()
        
        # Verfügbare Stunden berechnen
        tage = (ende - start).days + 1
        arbeitstage = sum(1 for i in range(tage) 
                        if (start + timedelta(days=i)).isoweekday() <= 5)
        
        if ressource.verfuegbar_von and ressource.verfuegbar_bis:
            stunden_pro_tag = (datetime.combine(date.today(), ressource.verfuegbar_bis) - 
                              datetime.combine(date.today(), ressource.verfuegbar_von)).seconds / 3600
        else:
            stunden_pro_tag = 8
        
        verfuegbar_stunden = arbeitstage * stunden_pro_tag
        
        # Gebuchte Stunden
        gebucht_minuten = sum(t.dauer_minuten for t in termine)
        gebucht_stunden = gebucht_minuten / 60
        
        # Auslastung
        auslastung = (gebucht_stunden / verfuegbar_stunden * 100) if verfuegbar_stunden > 0 else 0
        
        return {
            'ressource_id': ressource_id,
            'ressource_name': ressource.name,
            'zeitraum_start': start.isoformat(),
            'zeitraum_ende': ende.isoformat(),
            'verfuegbar_stunden': round(verfuegbar_stunden, 1),
            'gebucht_stunden': round(gebucht_stunden, 1),
            'frei_stunden': round(verfuegbar_stunden - gebucht_stunden, 1),
            'auslastung_prozent': round(auslastung, 1),
            'anzahl_termine': len(termine),
        }
