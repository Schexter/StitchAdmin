# -*- coding: utf-8 -*-
"""
Buchungs-Service - Automatische Buchungen nach SKR03

Erstellt von: Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func

from src.models import db
from src.models.buchungsmodul import Buchung, Kontenrahmen, ZahlungsartKontoMapping
from flask_login import current_user
import logging

logger = logging.getLogger(__name__)

class BuchungsService:
    """Service für alle Buchungs-Operationen"""
    
    @staticmethod
    def buche_kassenverkauf(beleg, zahlungsart: str) -> bool:
        """
        Bucht einen Kassenverkauf nach SKR03
        
        Args:
            beleg: KassenBeleg-Objekt
            zahlungsart: 'BAR', 'EC', 'SUMUP', 'RECHNUNG'
        
        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            # Ermittle Ziel-Konto anhand Zahlungsart
            konto_soll = ZahlungsartKontoMapping.get_konto_fuer_zahlungsart(zahlungsart)
            
            # Ermittle Erlös-Konto basierend auf MwSt-Satz
            # Annahme: Hauptsächlich 19% USt
            mwst_prozent = 19 if beleg.mwst_gesamt > 0 else 0
            
            if mwst_prozent == 19:
                konto_haben_erloese = '8400'  # Erlöse 19%
                konto_haben_ust = '1776'  # Umsatzsteuer 19%
            elif mwst_prozent == 7:
                konto_haben_erloese = '8300'  # Erlöse 7%
                konto_haben_ust = '1771'  # Umsatzsteuer 7%
            else:
                konto_haben_erloese = '8125'  # Erlöse steuerfrei
                konto_haben_ust = None
            
            username = current_user.username if current_user.is_authenticated else 'System'
            
            # Buchung 1: Hauptbetrag (Netto)
            buchung_netto = Buchung(
                buchungsdatum=beleg.erstellt_am.date() if isinstance(beleg.erstellt_am, datetime) else beleg.erstellt_am,
                belegnummer=beleg.belegnummer,
                konto_soll=konto_soll,
                konto_haben=konto_haben_erloese,
                betrag=Decimal(str(beleg.netto_gesamt)),
                steuer_betrag=Decimal(str(beleg.mwst_gesamt)),
                buchungstext=f'Verkauf {beleg.belegnummer} ({zahlungsart})',
                beleg_typ='Verkauf',
                beleg_id=beleg.id,
                beleg_tabelle='kassenbeleg',
                created_by=username
            )
            db.session.add(buchung_netto)

            # Buchung 2: Umsatzsteuer (falls vorhanden)
            if beleg.mwst_gesamt > 0 and konto_haben_ust:
                buchung_ust = Buchung(
                    buchungsdatum=beleg.erstellt_am.date() if isinstance(beleg.erstellt_am, datetime) else beleg.erstellt_am,
                    belegnummer=beleg.belegnummer,
                    konto_soll=konto_soll,
                    konto_haben=konto_haben_ust,
                    betrag=Decimal(str(beleg.mwst_gesamt)),
                    buchungstext=f'USt {beleg.belegnummer} ({zahlungsart})',
                    beleg_typ='Steuer',
                    beleg_id=beleg.id,
                    beleg_tabelle='kassenbeleg',
                    created_by=username
                )
                db.session.add(buchung_ust)
            
            db.session.commit()
            logger.info(f'Kassenverkauf {beleg.belegnummer} erfolgreich gebucht: {konto_soll} an {konto_haben_erloese}/{konto_haben_ust}')
            return True

        except Exception as e:
            db.session.rollback()
            logger.error(f'Fehler beim Buchen von Kassenverkauf {beleg.belegnummer}: {e}')
            return False
    
    @staticmethod
    def buche_rechnung(rechnung) -> bool:
        """
        Bucht eine Rechnung nach SKR03
        
        Args:
            rechnung: Rechnung-Objekt
        
        Returns:
            True bei Erfolg
        """
        try:
            # Rechnung wird als Forderung gebucht
            konto_soll = '1400'  # Forderungen
            
            # Erlös-Konto basierend auf MwSt
            # TODO: Multi-MwSt-Sätze aus Positionen berechnen
            konto_haben_erloese = '8400'  # Erlöse 19%
            konto_haben_ust = '1776'  # Umsatzsteuer 19%
            
            username = current_user.username if current_user.is_authenticated else 'System'
            
            # Buchung Netto
            buchung_netto = Buchung(
                buchungsdatum=rechnung.rechnungsdatum,
                belegnummer=rechnung.rechnungsnummer,
                konto_soll=konto_soll,
                konto_haben=konto_haben_erloese,
                betrag=Decimal(str(rechnung.summe_netto)),
                steuer_betrag=Decimal(str(rechnung.summe_mwst)),
                buchungstext=f'Rechnung {rechnung.rechnungsnummer}',
                beleg_typ='Rechnung',
                beleg_id=rechnung.id,
                beleg_tabelle='rechnung',
                created_by=username
            )
            db.session.add(buchung_netto)
            
            # Buchung USt
            if rechnung.summe_mwst > 0:
                buchung_ust = Buchung(
                    buchungsdatum=rechnung.rechnungsdatum,
                    belegnummer=rechnung.rechnungsnummer,
                    konto_soll=konto_soll,
                    konto_haben=konto_haben_ust,
                    betrag=Decimal(str(rechnung.summe_mwst)),
                    buchungstext=f'USt {rechnung.rechnungsnummer}',
                    beleg_typ='Steuer',
                    beleg_id=rechnung.id,
                    beleg_tabelle='rechnung',
                    created_by=username
                )
                db.session.add(buchung_ust)
            
            db.session.commit()
            logger.info(f'Rechnung {rechnung.rechnungsnummer} erfolgreich gebucht')
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f'Fehler beim Buchen von Rechnung {rechnung.rechnungsnummer}: {e}')
            return False
    
    @staticmethod
    def buche_eingangsrechnung(
        lieferant: str,
        rechnungsnummer: str,
        rechnungsdatum: date,
        netto_betrag: Decimal,
        mwst_satz: int,
        mwst_betrag: Decimal,
        beschreibung: str = None
    ) -> bool:
        """
        Bucht eine Eingangsrechnung (Lieferantenrechnung) nach SKR03

        Args:
            lieferant: Lieferantenname
            rechnungsnummer: Rechnungsnummer des Lieferanten
            rechnungsdatum: Datum der Rechnung
            netto_betrag: Nettobetrag
            mwst_satz: MwSt-Satz (7, 19 oder 0)
            mwst_betrag: MwSt-Betrag
            beschreibung: Optionale Beschreibung

        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            # Konten nach MwSt-Satz
            if mwst_satz == 19:
                konto_soll_aufwand = '3400'  # Wareneingang 19% Vorsteuer
                konto_soll_vorsteuer = '1576'  # Abziehbare Vorsteuer 19%
            elif mwst_satz == 7:
                konto_soll_aufwand = '3800'  # Wareneingang 7% Vorsteuer
                konto_soll_vorsteuer = '1571'  # Abziehbare Vorsteuer 7%
            else:
                konto_soll_aufwand = '4980'  # Sonstige betriebliche Aufwendungen
                konto_soll_vorsteuer = None

            konto_haben = '1600'  # Verbindlichkeiten aus Lieferungen und Leistungen

            username = current_user.username if current_user.is_authenticated else 'System'
            buchungstext = beschreibung or f'Eingangsrechnung {lieferant}'

            # Buchung 1: Aufwand (Netto)
            buchung_aufwand = Buchung(
                buchungsdatum=rechnungsdatum,
                belegnummer=rechnungsnummer,
                konto_soll=konto_soll_aufwand,
                konto_haben=konto_haben,
                betrag=netto_betrag,
                steuer_betrag=mwst_betrag,
                buchungstext=buchungstext,
                beleg_typ='Eingangsrechnung',
                created_by=username
            )
            db.session.add(buchung_aufwand)

            # Buchung 2: Vorsteuer (falls vorhanden)
            if mwst_betrag > 0 and konto_soll_vorsteuer:
                buchung_vorsteuer = Buchung(
                    buchungsdatum=rechnungsdatum,
                    belegnummer=rechnungsnummer,
                    konto_soll=konto_soll_vorsteuer,
                    konto_haben=konto_haben,
                    betrag=mwst_betrag,
                    buchungstext=f'Vorsteuer {buchungstext}',
                    beleg_typ='Vorsteuer',
                    created_by=username
                )
                db.session.add(buchung_vorsteuer)

            db.session.commit()
            logger.info(f'Eingangsrechnung {rechnungsnummer} von {lieferant} erfolgreich gebucht')
            return True

        except Exception as e:
            db.session.rollback()
            logger.error(f'Fehler beim Buchen von Eingangsrechnung {rechnungsnummer}: {e}')
            return False

    @staticmethod
    def buche_zahlungseingang(rechnung, betrag: Decimal, zahlungsart: str, datum: date = None) -> bool:
        """
        Bucht einen Zahlungseingang für eine Rechnung
        
        Args:
            rechnung: Rechnung-Objekt
            betrag: Gezahlter Betrag
            zahlungsart: 'UEBERWEISUNG', 'BAR', 'EC'
            datum: Zahlungsdatum (optional, default: heute)
        """
        try:
            if datum is None:
                datum = date.today()
            
            # Ziel-Konto für Zahlungseingang
            konto_soll = ZahlungsartKontoMapping.get_konto_fuer_zahlungsart(zahlungsart)
            
            # Ausgleich der Forderung
            konto_haben = '1400'  # Forderungen
            
            username = current_user.username if current_user.is_authenticated else 'System'
            
            buchung = Buchung(
                buchungsdatum=datum,
                belegnummer=f'ZE-{rechnung.rechnungsnummer}',
                konto_soll=konto_soll,
                konto_haben=konto_haben,
                betrag=betrag,
                buchungstext=f'Zahlungseingang {rechnung.rechnungsnummer}',
                beleg_typ='Zahlung',
                beleg_id=rechnung.id,
                beleg_tabelle='rechnung',
                created_by=username
            )
            db.session.add(buchung)
            db.session.commit()
            
            logger.info(f'Zahlungseingang für {rechnung.rechnungsnummer} gebucht: {betrag} EUR')
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f'Fehler beim Buchen von Zahlungseingang: {e}')
            return False
    
    @staticmethod
    def get_konto_saldo(konto_nummer: str, datum_von: date = None, datum_bis: date = None) -> Decimal:
        """
        Berechnet Saldo eines Kontos
        
        Args:
            konto_nummer: Konto-Nummer (z.B. '1000', '8400')
            datum_von: Start-Datum (optional)
            datum_bis: End-Datum (optional)
        
        Returns:
            Saldo als Decimal
        """
        konto = Kontenrahmen.query.filter_by(konto_nummer=konto_nummer).first()
        if not konto:
            logger.warning(f'Konto {konto_nummer} nicht gefunden')
            return Decimal('0')
        
        return konto.get_saldo(datum_von, datum_bis)
    
    @staticmethod
    def get_buchungen(
        konto_nummer: str = None,
        datum_von: date = None,
        datum_bis: date = None,
        beleg_typ: str = None,
        limit: int = None
    ) -> List[Buchung]:
        """
        Lädt Buchungen mit Filtern
        
        Args:
            konto_nummer: Filter nach Konto
            datum_von: Filter Start-Datum
            datum_bis: Filter End-Datum
            beleg_typ: Filter nach Beleg-Typ
            limit: Max. Anzahl Ergebnisse
        
        Returns:
            Liste von Buchungen
        """
        query = Buchung.query.filter_by(storniert=False)
        
        if konto_nummer:
            query = query.filter(
                db.or_(
                    Buchung.konto_soll == konto_nummer,
                    Buchung.konto_haben == konto_nummer
                )
            )
        
        if datum_von:
            query = query.filter(Buchung.buchungsdatum >= datum_von)
        
        if datum_bis:
            query = query.filter(Buchung.buchungsdatum <= datum_bis)
        
        if beleg_typ:
            query = query.filter(Buchung.beleg_typ == beleg_typ)
        
        query = query.order_by(Buchung.buchungsdatum.desc(), Buchung.id.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def export_datev(datum_von: date, datum_bis: date) -> Tuple[str, str]:
        """
        Exportiert Buchungen im DATEV-Format
        
        Args:
            datum_von: Start-Datum
            datum_bis: End-Datum
        
        Returns:
            Tuple (content, filename)
        """
        buchungen = BuchungsService.get_buchungen(
            datum_von=datum_von,
            datum_bis=datum_bis
        )
        
        # DATEV-Header
        lines = []
        lines.append(f"EXTF;700;21;Buchungsstapel;{datum_von.strftime('%Y')};{datum_von};{datum_bis};StitchAdmin")
        
        # Buchungszeilen
        for b in buchungen:
            line_parts = [
                f'{b.betrag:.2f}',  # Umsatz
                'S',  # Soll/Haben-Kennzeichen
                'EUR',  # Währung
                '',  # Kurs (leer für EUR)
                b.konto_soll,  # Soll-Konto
                b.konto_haben,  # Haben-Konto
                '',  # Steuerschlüssel (TODO)
                b.buchungsdatum.strftime('%d%m'),  # Datum TTMM
                b.belegnummer or '',  # Belegnummer
                (b.buchungstext or '')[:60],  # Buchungstext (max 60 Zeichen)
            ]
            lines.append(';'.join(str(p) for p in line_parts))
        
        content = '\n'.join(lines)
        filename = f'DATEV_Export_{datum_von.strftime("%Y%m%d")}_{datum_bis.strftime("%Y%m%d")}.csv'
        
        return content, filename
    
    @staticmethod
    def get_statistiken(datum_von: date = None, datum_bis: date = None) -> Dict:
        """
        Berechnet Buchungsstatistiken
        
        Returns:
            Dict mit Statistiken
        """
        query = Buchung.query.filter_by(storniert=False)
        
        if datum_von:
            query = query.filter(Buchung.buchungsdatum >= datum_von)
        if datum_bis:
            query = query.filter(Buchung.buchungsdatum <= datum_bis)
        
        # Summen pro Konto-Art
        erloese = db.session.query(func.sum(Buchung.betrag)).filter(
            Buchung.konto_haben.in_(['8400', '8300', '8125']),
            Buchung.storniert == False
        )
        if datum_von:
            erloese = erloese.filter(Buchung.buchungsdatum >= datum_von)
        if datum_bis:
            erloese = erloese.filter(Buchung.buchungsdatum <= datum_bis)
        
        erloese_summe = erloese.scalar() or Decimal('0')
        
        return {
            'anzahl_buchungen': query.count(),
            'erloese_gesamt': float(erloese_summe),
            'kasse_saldo': float(BuchungsService.get_konto_saldo('1000', datum_von, datum_bis)),
            'bank_saldo': float(BuchungsService.get_konto_saldo('1200', datum_von, datum_bis)),
            'forderungen_saldo': float(BuchungsService.get_konto_saldo('1400', datum_von, datum_bis)),
        }
