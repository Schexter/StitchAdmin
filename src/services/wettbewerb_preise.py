# -*- coding: utf-8 -*-
"""
WETTBEWERBS-PREISVERGLEICH SERVICE
==================================
Crawlt und vergleicht Preise von Textildruck-Anbietern

Unterstützte Anbieter:
- Shirtigo
- Spreadshirt
- Printful
- Vistaprint
- Flyeralarm
- WIRmachenDRUCK
- Lokale Anbieter (manuell)

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import hashlib

from src.models import db

logger = logging.getLogger(__name__)

# Requests optional (für Crawling)
try:
    import requests
    from bs4 import BeautifulSoup
    CRAWLING_AVAILABLE = True
except ImportError:
    CRAWLING_AVAILABLE = False
    logger.warning("requests/beautifulsoup nicht installiert - Crawling deaktiviert")


@dataclass
class WettbewerbsPreis:
    """Einzelner Wettbewerbs-Preis"""
    anbieter: str
    produkt: str
    verfahren: str  # siebdruck, dtg, stickerei, etc.
    menge: int
    stueckpreis_netto: Decimal
    stueckpreis_brutto: Decimal
    gesamtpreis_netto: Decimal
    gesamtpreis_brutto: Decimal
    lieferzeit_tage: int = 0
    mindestmenge: int = 1
    quelle_url: str = ""
    erfasst_am: datetime = None
    notizen: str = ""
    
    def __post_init__(self):
        if self.erfasst_am is None:
            self.erfasst_am = datetime.now()


class WettbewerbsPreisDB(db.Model):
    """Datenbank-Model für gecrawlte/manuelle Preise"""
    __tablename__ = 'wettbewerb_preise'
    
    id = db.Column(db.Integer, primary_key=True)
    
    anbieter = db.Column(db.String(100), nullable=False)
    produkt = db.Column(db.String(200))
    verfahren = db.Column(db.String(50))  # siebdruck, dtg, stickerei
    
    menge = db.Column(db.Integer, nullable=False)
    stueckpreis_netto = db.Column(db.Numeric(10, 2))
    stueckpreis_brutto = db.Column(db.Numeric(10, 2))
    gesamtpreis_netto = db.Column(db.Numeric(10, 2))
    gesamtpreis_brutto = db.Column(db.Numeric(10, 2))
    
    lieferzeit_tage = db.Column(db.Integer, default=0)
    mindestmenge = db.Column(db.Integer, default=1)
    
    quelle_url = db.Column(db.String(500))
    ist_manuell = db.Column(db.Boolean, default=False)
    
    erfasst_am = db.Column(db.DateTime, default=datetime.utcnow)
    gueltig_bis = db.Column(db.DateTime)
    
    # Hash für Duplikat-Erkennung
    preis_hash = db.Column(db.String(64), unique=True)
    
    def berechne_hash(self):
        """Erstellt Hash aus Anbieter+Produkt+Menge+Verfahren"""
        key = f"{self.anbieter}|{self.produkt}|{self.menge}|{self.verfahren}"
        return hashlib.sha256(key.encode()).hexdigest()


class WettbewerbsPreisService:
    """
    Service für Wettbewerbs-Preisvergleich
    """
    
    # Bekannte Anbieter mit Basis-URLs
    ANBIETER = {
        'shirtigo': {
            'name': 'Shirtigo',
            'url': 'https://www.shirtigo.de',
            'api': True,
        },
        'spreadshirt': {
            'name': 'Spreadshirt',
            'url': 'https://www.spreadshirt.de',
            'api': False,
        },
        'printful': {
            'name': 'Printful',
            'url': 'https://www.printful.com',
            'api': True,
        },
        'vistaprint': {
            'name': 'Vistaprint',
            'url': 'https://www.vistaprint.de',
            'api': False,
        },
        'flyeralarm': {
            'name': 'Flyeralarm',
            'url': 'https://www.flyeralarm.com/de',
            'api': False,
        },
        'wirmachendruck': {
            'name': 'WIRmachenDRUCK',
            'url': 'https://www.wir-machen-druck.de',
            'api': False,
        },
    }
    
    # Standard-Referenzpreise (Marktdurchschnitt)
    REFERENZ_PREISE = {
        'siebdruck': {
            25: {'stueck_brutto': Decimal('8.50')},
            50: {'stueck_brutto': Decimal('6.50')},
            100: {'stueck_brutto': Decimal('5.00')},
            250: {'stueck_brutto': Decimal('4.00')},
            500: {'stueck_brutto': Decimal('3.20')},
            1000: {'stueck_brutto': Decimal('2.80')},
        },
        'dtg': {
            1: {'stueck_brutto': Decimal('25.00')},
            10: {'stueck_brutto': Decimal('18.00')},
            25: {'stueck_brutto': Decimal('15.00')},
            50: {'stueck_brutto': Decimal('12.00')},
            100: {'stueck_brutto': Decimal('10.00')},
        },
        'stickerei': {
            25: {'stueck_brutto': Decimal('12.00')},  # 10.000 Stiche
            50: {'stueck_brutto': Decimal('9.00')},
            100: {'stueck_brutto': Decimal('7.00')},
            250: {'stueck_brutto': Decimal('5.50')},
            500: {'stueck_brutto': Decimal('4.50')},
        },
        'flex': {
            10: {'stueck_brutto': Decimal('10.00')},
            25: {'stueck_brutto': Decimal('7.00')},
            50: {'stueck_brutto': Decimal('5.50')},
            100: {'stueck_brutto': Decimal('4.50')},
        },
    }
    
    def __init__(self):
        self.cache_dauer = timedelta(days=7)
    
    def lade_preise(self, 
                    verfahren: str,
                    menge: int,
                    nur_aktuell: bool = True) -> List[Dict]:
        """
        Lädt gespeicherte Wettbewerbspreise aus DB
        """
        query = WettbewerbsPreisDB.query.filter_by(
            verfahren=verfahren,
            menge=menge
        )
        
        if nur_aktuell:
            # Nur Preise der letzten 30 Tage
            grenze = datetime.utcnow() - timedelta(days=30)
            query = query.filter(WettbewerbsPreisDB.erfasst_am >= grenze)
        
        preise = query.order_by(WettbewerbsPreisDB.stueckpreis_brutto).all()
        
        return [
            {
                'anbieter': p.anbieter,
                'produkt': p.produkt,
                'menge': p.menge,
                'stueckpreis_brutto': float(p.stueckpreis_brutto or 0),
                'gesamtpreis_brutto': float(p.gesamtpreis_brutto or 0),
                'lieferzeit_tage': p.lieferzeit_tage,
                'quelle_url': p.quelle_url,
                'erfasst_am': p.erfasst_am.isoformat() if p.erfasst_am else None,
                'ist_manuell': p.ist_manuell,
            }
            for p in preise
        ]
    
    def speichere_preis(self,
                        anbieter: str,
                        verfahren: str,
                        menge: int,
                        stueckpreis_brutto: Decimal,
                        produkt: str = "",
                        lieferzeit_tage: int = 0,
                        quelle_url: str = "",
                        ist_manuell: bool = True) -> bool:
        """
        Speichert einen Wettbewerbspreis (manuell oder gecrawlt)
        """
        try:
            preis = WettbewerbsPreisDB(
                anbieter=anbieter,
                produkt=produkt,
                verfahren=verfahren,
                menge=menge,
                stueckpreis_brutto=stueckpreis_brutto,
                stueckpreis_netto=stueckpreis_brutto / Decimal('1.19'),
                gesamtpreis_brutto=stueckpreis_brutto * Decimal(str(menge)),
                gesamtpreis_netto=(stueckpreis_brutto / Decimal('1.19')) * Decimal(str(menge)),
                lieferzeit_tage=lieferzeit_tage,
                quelle_url=quelle_url,
                ist_manuell=ist_manuell,
            )
            preis.preis_hash = preis.berechne_hash()
            
            # Duplikat prüfen und ggf. aktualisieren
            existing = WettbewerbsPreisDB.query.filter_by(preis_hash=preis.preis_hash).first()
            if existing:
                existing.stueckpreis_brutto = stueckpreis_brutto
                existing.stueckpreis_netto = stueckpreis_brutto / Decimal('1.19')
                existing.gesamtpreis_brutto = stueckpreis_brutto * Decimal(str(menge))
                existing.erfasst_am = datetime.utcnow()
            else:
                db.session.add(preis)
            
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")
            db.session.rollback()
            return False
    
    def vergleiche_mit_wettbewerb(self,
                                   eigener_preis: Decimal,
                                   verfahren: str,
                                   menge: int) -> Dict:
        """
        Vergleicht eigenen Preis mit Wettbewerb und Referenz
        """
        # Wettbewerbspreise aus DB
        wettbewerb = self.lade_preise(verfahren, menge)
        
        # Referenzpreise
        referenz = self._get_referenzpreis(verfahren, menge)
        
        # Günstigster Wettbewerber
        guenstigster = min(wettbewerb, key=lambda x: x['stueckpreis_brutto']) if wettbewerb else None
        
        # Durchschnitt
        if wettbewerb:
            durchschnitt = sum(w['stueckpreis_brutto'] for w in wettbewerb) / len(wettbewerb)
        else:
            durchschnitt = float(referenz) if referenz else 0
        
        # Position berechnen
        eigener_float = float(eigener_preis)
        
        if guenstigster:
            diff_guenstigster = eigener_float - guenstigster['stueckpreis_brutto']
            diff_prozent = (diff_guenstigster / guenstigster['stueckpreis_brutto'] * 100) if guenstigster['stueckpreis_brutto'] > 0 else 0
        else:
            diff_guenstigster = 0
            diff_prozent = 0
        
        # Empfehlung
        if diff_prozent > 20:
            empfehlung = "Preis deutlich über Markt - Anpassung prüfen"
            status = "teuer"
        elif diff_prozent > 10:
            empfehlung = "Preis leicht über Markt"
            status = "hoch"
        elif diff_prozent > -10:
            empfehlung = "Preis im Marktdurchschnitt"
            status = "ok"
        elif diff_prozent > -20:
            empfehlung = "Preis unter Markt - gute Wettbewerbsposition"
            status = "guenstig"
        else:
            empfehlung = "Preis deutlich unter Markt - Marge prüfen!"
            status = "sehr_guenstig"
        
        return {
            'eigener_preis': eigener_float,
            'verfahren': verfahren,
            'menge': menge,
            
            'guenstigster_anbieter': guenstigster['anbieter'] if guenstigster else None,
            'guenstigster_preis': guenstigster['stueckpreis_brutto'] if guenstigster else None,
            
            'durchschnitt_markt': round(durchschnitt, 2),
            'referenzpreis': float(referenz) if referenz else None,
            
            'differenz_euro': round(diff_guenstigster, 2),
            'differenz_prozent': round(diff_prozent, 1),
            
            'status': status,
            'empfehlung': empfehlung,
            
            'anzahl_wettbewerber': len(wettbewerb),
            'wettbewerber': wettbewerb[:5],  # Top 5
        }
    
    def _get_referenzpreis(self, verfahren: str, menge: int) -> Optional[Decimal]:
        """Holt Referenzpreis für Verfahren und Menge"""
        if verfahren not in self.REFERENZ_PREISE:
            return None
        
        preise = self.REFERENZ_PREISE[verfahren]
        
        # Exakter Match
        if menge in preise:
            return preise[menge]['stueck_brutto']
        
        # Interpolation
        mengen = sorted(preise.keys())
        
        if menge < mengen[0]:
            return preise[mengen[0]]['stueck_brutto']
        if menge > mengen[-1]:
            return preise[mengen[-1]]['stueck_brutto']
        
        # Linear interpolieren
        for i in range(len(mengen) - 1):
            if mengen[i] <= menge <= mengen[i + 1]:
                m1, m2 = mengen[i], mengen[i + 1]
                p1 = preise[m1]['stueck_brutto']
                p2 = preise[m2]['stueck_brutto']
                
                faktor = (menge - m1) / (m2 - m1)
                return p1 + (p2 - p1) * Decimal(str(faktor))
        
        return None
    
    def get_marktueberblick(self, verfahren: str) -> Dict:
        """
        Gibt Marktüberblick für ein Verfahren
        """
        alle_preise = WettbewerbsPreisDB.query.filter_by(verfahren=verfahren).all()
        
        if not alle_preise:
            return {
                'verfahren': verfahren,
                'anzahl_datenpunkte': 0,
                'anbieter': [],
            }
        
        # Nach Anbieter gruppieren
        anbieter_preise = {}
        for p in alle_preise:
            if p.anbieter not in anbieter_preise:
                anbieter_preise[p.anbieter] = []
            anbieter_preise[p.anbieter].append({
                'menge': p.menge,
                'preis': float(p.stueckpreis_brutto or 0),
            })
        
        return {
            'verfahren': verfahren,
            'anzahl_datenpunkte': len(alle_preise),
            'anbieter': list(anbieter_preise.keys()),
            'preise_nach_anbieter': anbieter_preise,
            'referenz': {m: float(v['stueck_brutto']) for m, v in self.REFERENZ_PREISE.get(verfahren, {}).items()},
        }


# Optional: Einfacher Crawler für öffentliche Preislisten
class PreisCrawler:
    """
    Einfacher Web-Crawler für Preislisten
    
    HINWEIS: Nur für öffentlich zugängliche Preislisten!
    Robots.txt beachten!
    """
    
    def __init__(self):
        if not CRAWLING_AVAILABLE:
            raise RuntimeError("requests/beautifulsoup nicht installiert")
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'StitchAdmin/2.0 (Preisvergleich)'
        })
    
    def crawl_shirtigo(self) -> List[Dict]:
        """
        Beispiel-Crawler für Shirtigo
        (Nur als Demonstration - echte Implementation benötigt API-Key)
        """
        # Shirtigo hat eine API - besser diese nutzen
        # https://api.shirtigo.de/
        logger.info("Shirtigo-Crawling: API empfohlen statt Scraping")
        return []
    
    def crawl_flyeralarm_textil(self) -> List[Dict]:
        """
        Beispiel für Flyeralarm Textildruck-Preise
        """
        # Flyeralarm zeigt Preise dynamisch an
        # Besser: Preise manuell aus Konfigurator übernehmen
        logger.info("Flyeralarm: Manuelle Preiseingabe empfohlen")
        return []
