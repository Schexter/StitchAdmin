# -*- coding: utf-8 -*-
"""
RECHNUNG SERVICE
================
Zentrale Geschaeftslogik fuer alle Rechnungs-Operationen.

Regeln:
- Jede Statusaenderung erzeugt automatisch die korrekte Buchung
- Buchungsfehler werden NICHT verschluckt, sondern zurueckgemeldet
- Ein Commit pro Operation (atomar)
- Kontenzuordnung zentral hier, nicht im Controller

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from src.models import db
from src.models.rechnungsmodul.models import (
    Rechnung, RechnungsPosition, RechnungsStatus,
    RechnungsRichtung, ZugpferdProfil
)
from flask_login import current_user
import logging

logger = logging.getLogger(__name__)


# =========================================================================
# KONTENZUORDNUNG (SKR03) - EINE QUELLE DER WAHRHEIT
# =========================================================================

# Erloeskonten nach MwSt-Satz
ERLOESKONTEN = {
    19: {'erloese': '8400', 'ust': '1776'},
    7:  {'erloese': '8300', 'ust': '1771'},
    0:  {'erloese': '8125', 'ust': None},
}

# Aufwandskonten nach MwSt-Satz (Eingangsrechnungen)
AUFWANDSKONTEN = {
    19: {'aufwand': '3400', 'vorsteuer': '1576'},
    7:  {'aufwand': '3800', 'vorsteuer': '1571'},
    0:  {'aufwand': '4980', 'vorsteuer': None},
}

# Aufwandskonten nach Kategorie (Eingangsrechnungen)
KATEGORIE_KONTEN = {
    'ware':        '3400',  # Wareneingang
    'material':    '3400',  # Wareneingang (Material = Ware in SKR03)
    'buero':       '4930',  # Bueroausgaben
    'miete':       '4210',  # Miete
    'versicherung':'4360',  # Versicherungen
    'kfz':         '4510',  # Kfz-Kosten
    'reise':       '4660',  # Reisekosten
    'werbung':     '4600',  # Werbekosten
    'telefon':     '4920',  # Telefon/Internet
    'sonstiges':   '4980',  # Sonstige betriebliche Aufwendungen
}

# Forderungen / Verbindlichkeiten
KONTO_FORDERUNGEN = '1400'
KONTO_VERBINDLICHKEITEN = '1600'


class RechnungService:
    """Zentrale Geschaeftslogik fuer Rechnungen"""

    # =====================================================================
    # AUSGANGSRECHNUNG: Erstellen -> Versenden -> Bezahlen
    # =====================================================================

    @staticmethod
    def erstelle_rechnung(kunde, positionen_data: List[Dict],
                          rechnungsdatum: date = None,
                          leistungsdatum: date = None,
                          zahlungsbedingungen: str = 'Zahlbar innerhalb 14 Tagen',
                          zugpferd_profil: str = 'BASIC',
                          bemerkungen: str = '',
                          auftrag_ids: List[int] = None) -> Tuple[Rechnung, Optional[str]]:
        """
        Erstellt eine neue Ausgangsrechnung als Entwurf.

        Args:
            kunde: Customer-Objekt
            positionen_data: Liste von Dicts mit Positionsdaten
            rechnungsdatum: Rechnungsdatum (default: heute)
            leistungsdatum: Leistungsdatum (default: rechnungsdatum)
            zahlungsbedingungen: Zahlungstext
            zugpferd_profil: ZUGPFERD-Profil
            bemerkungen: Freitext
            auftrag_ids: Optionale Auftrags-IDs zum Verknuepfen

        Returns:
            Tuple (Rechnung, Fehlermeldung oder None)
        """
        if rechnungsdatum is None:
            rechnungsdatum = date.today()
        if leistungsdatum is None:
            leistungsdatum = rechnungsdatum

        username = current_user.username if current_user.is_authenticated else 'System'

        try:
            rechnung = Rechnung(
                richtung=RechnungsRichtung.AUSGANG,
                kunde_id=kunde.id,
                kunde_name=kunde.display_name,
                kunde_adresse=f"{kunde.street or ''} {kunde.house_number or ''}\n{kunde.postal_code or ''} {kunde.city or ''}".strip(),
                kunde_email=kunde.email,
                kunde_steuernummer=getattr(kunde, 'tax_id', None),
                kunde_ust_id=getattr(kunde, 'vat_id', None),
                rechnungsdatum=rechnungsdatum,
                leistungsdatum=leistungsdatum,
                zahlungsbedingungen=zahlungsbedingungen,
                zugpferd_profil=ZugpferdProfil[zugpferd_profil],
                bemerkungen=bemerkungen,
                status=RechnungsStatus.ENTWURF,
                erstellt_von=username
            )

            # Positionen anlegen
            pos_idx = 1
            for pos_data in positionen_data:
                if pos_data.get('is_header'):
                    continue

                ep = pos_data.get('einzelpreis_netto') or pos_data.get('einzelpreis', 0)
                position = RechnungsPosition(
                    position=pos_idx,
                    artikel_id=pos_data.get('artikel_id'),
                    artikel_nummer=pos_data.get('artikel_nummer', ''),
                    artikel_name=pos_data.get('artikel_name', ''),
                    beschreibung=pos_data.get('beschreibung', ''),
                    menge=Decimal(str(pos_data.get('menge', 1))),
                    einheit=pos_data.get('einheit', 'Stueck'),
                    einzelpreis=Decimal(str(ep)),
                    mwst_satz=Decimal(str(pos_data.get('mwst_satz', 19))),
                    rabatt_prozent=Decimal(str(pos_data.get('rabatt_prozent', 0)))
                )
                position.calculate_amounts()
                rechnung.positionen.append(position)
                pos_idx += 1

            # Summen berechnen
            rechnung.calculate_totals()

            db.session.add(rechnung)
            db.session.flush()  # ID vergeben

            # Auftraege verknuepfen
            if auftrag_ids:
                from src.models.models import Order
                for order in Order.query.filter(Order.id.in_(auftrag_ids)).all():
                    order.invoice_id = rechnung.id
                    order.workflow_status = 'invoiced'

            db.session.commit()
            logger.info(f"Rechnung {rechnung.rechnungsnummer} erstellt (Entwurf)")
            return rechnung, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler beim Erstellen der Rechnung: {e}")
            return None, str(e)

    @staticmethod
    def versende_rechnung(rechnung_id: int) -> Tuple[bool, str]:
        """
        Finalisiert einen Entwurf: Echte RE-Nummer vergeben, Status OFFEN, Buchung erzeugen.

        Returns:
            Tuple (Erfolg, Nachricht)
        """
        rechnung = Rechnung.query.get(rechnung_id)
        if not rechnung:
            return False, 'Rechnung nicht gefunden'

        if rechnung.status != RechnungsStatus.ENTWURF:
            return False, 'Nur Entwuerfe koennen versendet werden'

        try:
            # Echte Rechnungsnummer vergeben
            if rechnung.rechnungsnummer.startswith('ENT-'):
                from src.controllers.rechnungsmodul.rechnung_controller import RechnungsUtils
                rechnung.rechnungsnummer = RechnungsUtils.get_next_invoice_number()

            rechnung.status = RechnungsStatus.OFFEN
            rechnung.versendet_am = datetime.utcnow()
            rechnung.versendet_von = current_user.username if current_user.is_authenticated else 'System'

            # Buchung erzeugen - NICHT optional, NICHT im try/except verschluckt
            buchung_ok = RechnungService._buche_ausgangsrechnung(rechnung)
            if not buchung_ok:
                db.session.rollback()
                return False, f'Rechnung {rechnung.rechnungsnummer}: Buchung fehlgeschlagen - Rechnung wurde NICHT versendet'

            db.session.commit()
            logger.info(f"Rechnung {rechnung.rechnungsnummer} versendet + gebucht")
            return True, f'Rechnung {rechnung.rechnungsnummer} erstellt und gebucht'

        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler beim Versenden: {e}")
            return False, str(e)

    @staticmethod
    def zahlung_erfassen(rechnung_id: int, betrag: float,
                         zahlungsart: str = 'ueberweisung',
                         datum: date = None) -> Tuple[bool, str]:
        """
        Erfasst eine Zahlung fuer eine Rechnung und bucht den Zahlungseingang.

        Returns:
            Tuple (Erfolg, Nachricht)
        """
        rechnung = Rechnung.query.get(rechnung_id)
        if not rechnung:
            return False, 'Rechnung nicht gefunden'

        if rechnung.status not in (RechnungsStatus.OFFEN, RechnungsStatus.TEILBEZAHLT, RechnungsStatus.UEBERFAELLIG):
            return False, f'Zahlung nicht moeglich bei Status: {rechnung.status.value}'

        if datum is None:
            datum = date.today()

        betrag_decimal = Decimal(str(betrag))
        brutto = Decimal(str(rechnung.brutto_gesamt or 0))
        username = current_user.username if current_user.is_authenticated else 'System'

        try:
            rechnung.zahlungsart = zahlungsart
            rechnung.bezahlt_am = datum
            rechnung.bezahlt_betrag = betrag_decimal
            rechnung.bearbeitet_am = datetime.utcnow()
            rechnung.bearbeitet_von = username

            if betrag_decimal >= brutto:
                rechnung.status = RechnungsStatus.BEZAHLT
                msg = f'Rechnung {rechnung.rechnungsnummer} vollstaendig bezahlt'
            else:
                rechnung.status = RechnungsStatus.TEILBEZAHLT
                msg = f'Teilzahlung {betrag_decimal:.2f} EUR erfasst'

            # Zahlungseingang buchen
            buchung_ok = RechnungService._buche_zahlungseingang(rechnung, betrag_decimal, zahlungsart, datum)
            if not buchung_ok:
                db.session.rollback()
                return False, 'Zahlungsbuchung fehlgeschlagen'

            db.session.commit()
            logger.info(msg)
            return True, msg

        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler bei Zahlungserfassung: {e}")
            return False, str(e)

    # =====================================================================
    # EINGANGSRECHNUNG: Erfassen -> Buchen (in einem Schritt)
    # =====================================================================

    @staticmethod
    def erfasse_eingangsrechnung(
        lieferant_name: str,
        rechnungsnummer: str,
        rechnungsdatum: date,
        netto: Decimal,
        mwst_betrag: Decimal,
        mwst_satz: int = 19,
        kategorie: str = 'sonstiges',
        bemerkungen: str = '',
        lieferant_id: str = None,
        faelligkeitsdatum: date = None,
        auto_buchen: bool = True
    ) -> Tuple[Optional[Rechnung], Optional[str]]:
        """
        Erfasst eine Eingangsrechnung und erstellt automatisch die Buchungen.

        Returns:
            Tuple (Rechnung oder None, Fehlermeldung oder None)
        """
        brutto = netto + mwst_betrag
        username = current_user.username if current_user.is_authenticated else 'System'

        try:
            rechnung = Rechnung(
                rechnungsnummer=rechnungsnummer or f"ER-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                richtung=RechnungsRichtung.EINGANG,
                lieferant_id=lieferant_id,
                lieferant_name=lieferant_name,
                kunde_name=lieferant_name,  # Kompatibilitaet
                rechnungsdatum=rechnungsdatum,
                faelligkeitsdatum=faelligkeitsdatum,
                netto_gesamt=netto,
                mwst_gesamt=mwst_betrag,
                brutto_gesamt=brutto,
                bemerkungen=bemerkungen,
                status=RechnungsStatus.OFFEN,
                erstellt_von=username
            )

            db.session.add(rechnung)
            db.session.flush()

            # Automatisch buchen
            if auto_buchen:
                buchung_ok = RechnungService._buche_eingangsrechnung(
                    rechnung, netto, mwst_betrag, mwst_satz, kategorie
                )
                if not buchung_ok:
                    db.session.rollback()
                    return None, 'Eingangsrechnung konnte nicht gebucht werden'

            db.session.commit()
            logger.info(f"Eingangsrechnung {rechnung.rechnungsnummer} von {lieferant_name} erfasst + gebucht")
            return rechnung, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler bei Eingangsrechnung: {e}")
            return None, str(e)

    # =====================================================================
    # STORNO
    # =====================================================================

    @staticmethod
    def storniere_rechnung(rechnung_id: int, grund: str = '') -> Tuple[bool, str]:
        """
        Storniert eine Rechnung und macht die Buchungen rueckgaengig.

        Returns:
            Tuple (Erfolg, Nachricht)
        """
        rechnung = Rechnung.query.get(rechnung_id)
        if not rechnung:
            return False, 'Rechnung nicht gefunden'

        if rechnung.status == RechnungsStatus.STORNIERT:
            return False, 'Rechnung ist bereits storniert'

        try:
            altes_status = rechnung.status
            rechnung.status = RechnungsStatus.STORNIERT
            rechnung.bemerkungen = (rechnung.bemerkungen or '') + f'\nStorniert: {grund}'
            rechnung.bearbeitet_am = datetime.utcnow()
            rechnung.bearbeitet_von = current_user.username if current_user.is_authenticated else 'System'

            # Storno-Buchungen erzeugen (Gegenbuchungen)
            if altes_status in (RechnungsStatus.OFFEN, RechnungsStatus.TEILBEZAHLT, RechnungsStatus.UEBERFAELLIG):
                RechnungService._storno_buchungen(rechnung)

            # Verknuepfte Auftraege freigeben
            from src.models.models import Order
            linked_orders = Order.query.filter_by(invoice_id=rechnung_id).all()
            for order in linked_orders:
                order.invoice_id = None
                if order.status in ('invoiced', 'completed'):
                    order.status = 'ready'

            db.session.commit()
            logger.info(f"Rechnung {rechnung.rechnungsnummer} storniert: {grund}")
            return True, f'Rechnung {rechnung.rechnungsnummer} storniert'

        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler beim Stornieren: {e}")
            return False, str(e)

    # =====================================================================
    # STATISTIKEN (aus Controller hierher verschoben)
    # =====================================================================

    @staticmethod
    def get_dashboard_stats(monat_start: date = None) -> Dict:
        """
        Berechnet Rechnungs-Statistiken fuer das Dashboard.

        Returns:
            Dict mit allen relevanten Kennzahlen
        """
        if monat_start is None:
            today = date.today()
            monat_start = today.replace(day=1)

        try:
            ausgang = Rechnung.query.filter(
                Rechnung.richtung == RechnungsRichtung.AUSGANG,
                Rechnung.status != RechnungsStatus.STORNIERT
            ).all()

            offen = [r for r in ausgang if r.status == RechnungsStatus.OFFEN]
            ueberfaellig = [r for r in offen if r.is_overdue()]
            bezahlt = [r for r in ausgang
                       if r.status == RechnungsStatus.BEZAHLT
                       and r.bezahlt_am and r.bezahlt_am >= monat_start]

            return {
                'ausgang_offen_count': len(offen),
                'ausgang_offen_total': sum(float(r.brutto_gesamt or 0) for r in offen),
                'ausgang_ueberfaellig_count': len(ueberfaellig),
                'ausgang_ueberfaellig_total': sum(float(r.brutto_gesamt or 0) for r in ueberfaellig),
                'ausgang_bezahlt_count': len(bezahlt),
                'ausgang_bezahlt_total': sum(float(r.brutto_gesamt or 0) for r in bezahlt),
                'ausgang_total_count': len(ausgang),
                'ausgang_total_summe': sum(float(r.brutto_gesamt or 0) for r in ausgang),
            }
        except Exception as e:
            logger.error(f"Fehler bei Rechnungsstatistik: {e}")
            return {k: 0 for k in [
                'ausgang_offen_count', 'ausgang_offen_total',
                'ausgang_ueberfaellig_count', 'ausgang_ueberfaellig_total',
                'ausgang_bezahlt_count', 'ausgang_bezahlt_total',
                'ausgang_total_count', 'ausgang_total_summe'
            ]}

    # =====================================================================
    # INTERNE BUCHUNGSMETHODEN (privat - nur von diesem Service aufgerufen)
    # =====================================================================

    @staticmethod
    def _buche_ausgangsrechnung(rechnung: Rechnung) -> bool:
        """Erzeugt Buchungen fuer eine Ausgangsrechnung (Forderung an Erloese + USt)"""
        try:
            from src.models.buchungsmodul import Buchung

            netto = Decimal(str(rechnung.netto_gesamt or 0))
            mwst = Decimal(str(rechnung.mwst_gesamt or 0))
            username = current_user.username if current_user.is_authenticated else 'System'

            # MwSt-Satz aus Positionen ermitteln (Haupt-Satz)
            mwst_satz = RechnungService._ermittle_haupt_mwst_satz(rechnung)
            konten = ERLOESKONTEN.get(mwst_satz, ERLOESKONTEN[19])

            # Buchung: Forderung an Erloese (Netto)
            db.session.add(Buchung(
                buchungsdatum=rechnung.rechnungsdatum,
                belegnummer=rechnung.rechnungsnummer,
                konto_soll=KONTO_FORDERUNGEN,
                konto_haben=konten['erloese'],
                betrag=netto,
                steuer_betrag=mwst,
                buchungstext=f'Rechnung {rechnung.rechnungsnummer} - {rechnung.kunde_name or ""}',
                beleg_typ='Rechnung',
                beleg_id=rechnung.id,
                beleg_tabelle='rechnungen',
                created_by=username
            ))

            # Buchung: Forderung an USt (MwSt)
            if mwst > 0 and konten['ust']:
                db.session.add(Buchung(
                    buchungsdatum=rechnung.rechnungsdatum,
                    belegnummer=rechnung.rechnungsnummer,
                    konto_soll=KONTO_FORDERUNGEN,
                    konto_haben=konten['ust'],
                    betrag=mwst,
                    buchungstext=f'USt {rechnung.rechnungsnummer}',
                    beleg_typ='Steuer',
                    beleg_id=rechnung.id,
                    beleg_tabelle='rechnungen',
                    created_by=username
                ))

            logger.info(f"Buchung Ausgangsrechnung {rechnung.rechnungsnummer}: "
                        f"{KONTO_FORDERUNGEN} an {konten['erloese']}/{konten.get('ust', '-')}")
            return True

        except Exception as e:
            logger.error(f"Buchung Ausgangsrechnung fehlgeschlagen: {e}")
            return False

    @staticmethod
    def _buche_eingangsrechnung(rechnung: Rechnung, netto: Decimal,
                                 mwst_betrag: Decimal, mwst_satz: int,
                                 kategorie: str = 'sonstiges') -> bool:
        """Erzeugt Buchungen fuer eine Eingangsrechnung (Aufwand + Vorsteuer an Verbindlichkeit)"""
        try:
            from src.models.buchungsmodul import Buchung

            username = current_user.username if current_user.is_authenticated else 'System'

            # Aufwandskonto nach Kategorie (spezifischer) oder MwSt-Default
            konto_aufwand = KATEGORIE_KONTEN.get(kategorie)
            if not konto_aufwand:
                konten = AUFWANDSKONTEN.get(mwst_satz, AUFWANDSKONTEN[19])
                konto_aufwand = konten['aufwand']

            # Vorsteuerkonto nach MwSt-Satz
            konten_vst = AUFWANDSKONTEN.get(mwst_satz, AUFWANDSKONTEN[19])
            konto_vorsteuer = konten_vst['vorsteuer']

            # Buchung 1: Aufwand an Verbindlichkeit (Netto)
            db.session.add(Buchung(
                buchungsdatum=rechnung.rechnungsdatum,
                belegnummer=rechnung.rechnungsnummer,
                konto_soll=konto_aufwand,
                konto_haben=KONTO_VERBINDLICHKEITEN,
                betrag=netto,
                steuer_betrag=mwst_betrag,
                buchungstext=f'Eingangsrechnung {rechnung.lieferant_name or ""}: {rechnung.rechnungsnummer}',
                beleg_typ='Eingangsrechnung',
                beleg_id=rechnung.id,
                beleg_tabelle='rechnungen',
                created_by=username
            ))

            # Buchung 2: Vorsteuer an Verbindlichkeit (MwSt)
            if mwst_betrag > 0 and konto_vorsteuer:
                db.session.add(Buchung(
                    buchungsdatum=rechnung.rechnungsdatum,
                    belegnummer=rechnung.rechnungsnummer,
                    konto_soll=konto_vorsteuer,
                    konto_haben=KONTO_VERBINDLICHKEITEN,
                    betrag=mwst_betrag,
                    buchungstext=f'VSt {mwst_satz}% {rechnung.lieferant_name or ""}',
                    beleg_typ='Vorsteuer',
                    beleg_id=rechnung.id,
                    beleg_tabelle='rechnungen',
                    created_by=username
                ))

            logger.info(f"Buchung Eingangsrechnung {rechnung.rechnungsnummer}: "
                        f"{konto_aufwand}/{konto_vorsteuer or '-'} an {KONTO_VERBINDLICHKEITEN}")
            return True

        except Exception as e:
            logger.error(f"Buchung Eingangsrechnung fehlgeschlagen: {e}")
            return False

    @staticmethod
    def _buche_zahlungseingang(rechnung: Rechnung, betrag: Decimal,
                                zahlungsart: str, datum: date) -> bool:
        """Bucht einen Zahlungseingang (Bank/Kasse an Forderung)"""
        try:
            from src.models.buchungsmodul import Buchung, ZahlungsartKontoMapping

            username = current_user.username if current_user.is_authenticated else 'System'
            konto_soll = ZahlungsartKontoMapping.get_konto_fuer_zahlungsart(zahlungsart.upper())

            db.session.add(Buchung(
                buchungsdatum=datum,
                belegnummer=f'ZE-{rechnung.rechnungsnummer}',
                konto_soll=konto_soll,
                konto_haben=KONTO_FORDERUNGEN,
                betrag=betrag,
                buchungstext=f'Zahlungseingang {rechnung.rechnungsnummer} ({zahlungsart})',
                beleg_typ='Zahlung',
                beleg_id=rechnung.id,
                beleg_tabelle='rechnungen',
                created_by=username
            ))

            logger.info(f"Zahlungseingang {rechnung.rechnungsnummer}: {betrag} EUR via {zahlungsart}")
            return True

        except Exception as e:
            logger.error(f"Buchung Zahlungseingang fehlgeschlagen: {e}")
            return False

    @staticmethod
    def _storno_buchungen(rechnung: Rechnung) -> bool:
        """Erzeugt Gegenbuchungen fuer eine Stornierung"""
        try:
            from src.models.buchungsmodul import Buchung

            username = current_user.username if current_user.is_authenticated else 'System'

            # Alle Buchungen zu dieser Rechnung finden und Gegenbuchungen erzeugen
            original_buchungen = Buchung.query.filter_by(
                beleg_id=rechnung.id,
                beleg_tabelle='rechnungen',
                storniert=False
            ).all()

            for orig in original_buchungen:
                # Gegenbuchung: Soll/Haben tauschen
                db.session.add(Buchung(
                    buchungsdatum=date.today(),
                    belegnummer=f'ST-{orig.belegnummer}',
                    konto_soll=orig.konto_haben,  # umgekehrt
                    konto_haben=orig.konto_soll,   # umgekehrt
                    betrag=orig.betrag,
                    buchungstext=f'STORNO: {orig.buchungstext}',
                    beleg_typ='Storno',
                    beleg_id=rechnung.id,
                    beleg_tabelle='rechnungen',
                    created_by=username
                ))
                # Original als storniert markieren
                orig.storniert = True

            return True

        except Exception as e:
            logger.error(f"Storno-Buchungen fehlgeschlagen: {e}")
            return False

    @staticmethod
    def _ermittle_haupt_mwst_satz(rechnung: Rechnung) -> int:
        """Ermittelt den Haupt-MwSt-Satz einer Rechnung aus den Positionen"""
        try:
            positionen = list(rechnung.positionen)
            if not positionen:
                return 19  # Default

            # Haeufigsten MwSt-Satz nach Netto-Betrag ermitteln
            satz_summen = {}
            for pos in positionen:
                satz = int(pos.mwst_satz or 19)
                satz_summen[satz] = satz_summen.get(satz, Decimal('0')) + (pos.netto_betrag or Decimal('0'))

            return max(satz_summen, key=satz_summen.get)
        except Exception:
            return 19
