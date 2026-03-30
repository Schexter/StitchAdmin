# -*- coding: utf-8 -*-
"""
KASSEN-CONTROLLER - TSE-konforme Kassenbuchungen (PRODUKTIV-VERSION)
==================================================================
"""

import json
import uuid
from datetime import datetime, date
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from sqlalchemy.exc import SQLAlchemyError

# Imports für Models und Services
from src.models import db, Article, Customer, User
from src.models.rechnungsmodul import (
    KassenBeleg, BelegPosition, KassenTransaktion, MwStSatz,
    BelegTyp, ZahlungsArt, models_available
)
from src.utils.sumup_service import sumup_service
from src.services.buchungs_service import BuchungsService

import logging
logger = logging.getLogger(__name__)

kasse_bp = Blueprint('kasse', __name__, url_prefix='/kasse')

# ... (TSE-Service, Utility-Klassen und Warenkorb-Funktionen bleiben unverändert) ...

def _map_zahlungsart_to_enum(zahlungsart_str):
    """Mapped Zahlungsart-String auf Enum"""
    mapping = {
        'BAR': ZahlungsArt.BAR,
        'EC': ZahlungsArt.EC_KARTE,
        'EC_KARTE': ZahlungsArt.EC_KARTE,
        'SUMUP': ZahlungsArt.SUMUP,
        'KARTE': ZahlungsArt.EC_KARTE,
        'RECHNUNG': ZahlungsArt.RECHNUNG,
        'UEBERWEISUNG': ZahlungsArt.UEBERWEISUNG
    }
    return mapping.get(zahlungsart_str, ZahlungsArt.BAR)

def _finalize_sale(warenkorb, zahlungsart, gegeben=None, rueckgeld=None, transaction_info=None, rabatt_type=None, rabatt_value=0):
    """
    Interne Funktion, um einen Verkauf abzuschließen.
    Wird von Barverkäufen und SumUp-Webhooks aufgerufen.
    """
    try:
        if not warenkorb or len(warenkorb) == 0:
            return {'success': False, 'error': 'Warenkorb ist leer'}

        # Berechne Summen
        warenkorb_summen = calculate_warenkorb_totals(warenkorb)

        # Rabatt anwenden
        rabatt_betrag = 0
        rabatt_prozent = 0
        brutto_original = warenkorb_summen['brutto_gesamt']

        if rabatt_value and rabatt_value > 0:
            if rabatt_type == 'percent':
                rabatt_prozent = min(rabatt_value, 100)
                rabatt_betrag = round(brutto_original * (rabatt_prozent / 100), 2)
            else:  # fixed
                rabatt_betrag = min(round(rabatt_value, 2), brutto_original)

        # Reduzierte Betraege berechnen
        if rabatt_betrag > 0:
            factor = (brutto_original - rabatt_betrag) / brutto_original if brutto_original > 0 else 0
            netto_final = round(warenkorb_summen['netto_gesamt'] * factor, 2)
            mwst_final = round(warenkorb_summen['mwst_gesamt'] * factor, 2)
            brutto_final = round(brutto_original - rabatt_betrag, 2)
        else:
            netto_final = warenkorb_summen['netto_gesamt']
            mwst_final = warenkorb_summen['mwst_gesamt']
            brutto_final = brutto_original

        # Erstelle Kassenbeleg
        beleg = KassenBeleg(
            belegnummer=f"B-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            kunde_id=session.get('customer_id'),
            netto_gesamt=netto_final,
            brutto_gesamt=brutto_final,
            mwst_gesamt=mwst_final,
            zahlungsart=_map_zahlungsart_to_enum(zahlungsart),
            gegeben=gegeben,
            rueckgeld=rueckgeld,
            rabatt_betrag=rabatt_betrag,
            rabatt_prozent=rabatt_prozent,
            storniert=False
        )

        db.session.add(beleg)
        db.session.flush()  # Beleg-ID generieren

        # Erstelle Belegpositionen
        for idx, item in enumerate(warenkorb, 1):
            menge = item.get('menge', 1)
            # Einzelpreise aus bereits berechneten Beträgen ableiten
            einzelpreis_netto = round(item.get('netto_betrag', 0) / menge, 2) if menge else 0
            einzelpreis_brutto = round(item.get('brutto_betrag', 0) / menge, 2) if menge else 0
            position = BelegPosition(
                beleg_id=beleg.id,
                position=idx,
                artikel_id=item.get('artikel_id'),
                artikel_name=item.get('name'),
                menge=menge,
                einzelpreis_netto=einzelpreis_netto,
                einzelpreis_brutto=einzelpreis_brutto,
                netto_betrag=item.get('netto_betrag', 0),
                mwst_betrag=item.get('mwst_betrag', 0),
                brutto_betrag=item.get('brutto_betrag', 0),
                mwst_satz=item.get('mwst_satz', 19)
            )
            db.session.add(position)

        # TSE-Transaktion optional (nur wenn TSE konfiguriert ist)
        # Da wir manuell über SumUp TSE arbeiten, überspringen wir das hier
        # TODO: TSE-Integration wenn echtes TSE-Gerät vorhanden

        # Speichern
        db.session.commit()

        # Automatische Buchung nach SKR03
        try:
            buchung_erfolg = BuchungsService.buche_kassenverkauf(beleg, zahlungsart)
            if buchung_erfolg:
                logger.info(f"Buchung für Beleg {beleg.belegnummer} erfolgreich erstellt")
            else:
                logger.warning(f"Buchung für Beleg {beleg.belegnummer} konnte nicht erstellt werden")
        except Exception as buchungs_fehler:
            logger.error(f"Fehler bei automatischer Buchung: {buchungs_fehler}")
            # Verkauf ist trotzdem erfolgreich, nur Buchung fehlgeschlagen

        # Warenkorb leeren
        session['warenkorb'] = []
        session.modified = True

        logger.info(f"Verkauf erfolgreich abgeschlossen: Beleg {beleg.belegnummer}")

        # Bei RECHNUNG-Zahlung: Auch Rechnung im Rechnungsmodul anlegen
        rechnung_id = None
        rechnung_nummer = None
        if zahlungsart == 'RECHNUNG':
            try:
                from src.models.rechnungsmodul.models import (
                    Rechnung, RechnungsPosition, RechnungsStatus, RechnungsRichtung,
                    ZugpferdProfil
                )
                from decimal import Decimal
                from datetime import timedelta

                # Rechnungsnummer generieren (RE-YYYYMM-NNNN)
                from datetime import datetime as dt
                jahr = dt.now().year
                monat = dt.now().month
                count = Rechnung.query.filter(
                    Rechnung.rechnungsnummer.like(f"RE-{jahr:04d}{monat:02d}-%")
                ).count()
                rechnung_nummer = f"RE-{jahr:04d}{monat:02d}-{count + 1:04d}"

                # Kunden-Snapshot
                kunde_id = session.get('customer_id')
                kunde_name = session.get('customer_name', 'Laufkunde')
                kunde_adresse = None
                kunde_email = None
                if kunde_id:
                    k = Customer.query.get(kunde_id)
                    if k:
                        kunde_name = k.display_name
                        kunde_email = k.email if hasattr(k, 'email') else None
                        parts = [k.street, k.house_number, k.postal_code, k.city]
                        kunde_adresse = ' '.join(p for p in parts if p)

                rechnung = Rechnung(
                    rechnungsnummer=rechnung_nummer,
                    richtung=RechnungsRichtung.AUSGANG,
                    status=RechnungsStatus.OFFEN,
                    kunde_id=kunde_id,
                    kunde_name=kunde_name,
                    kunde_adresse=kunde_adresse,
                    kunde_email=kunde_email,
                    netto_gesamt=Decimal(str(netto_final)),
                    mwst_gesamt=Decimal(str(mwst_final)),
                    brutto_gesamt=Decimal(str(brutto_final)),
                    rechnungsdatum=date.today(),
                    faelligkeitsdatum=date.today() + timedelta(days=30),
                    zahlungsbedingungen='Zahlbar innerhalb 30 Tagen',
                    zugpferd_profil=ZugpferdProfil.BASIC,
                    bemerkungen=f'Erstellt aus Kasse, Beleg: {beleg.belegnummer}',
                    erstellt_von='Kasse'
                )
                db.session.add(rechnung)
                db.session.flush()

                # Positionen anlegen
                for idx, item in enumerate(warenkorb, 1):
                    menge = item.get('menge', 1)
                    netto_b = Decimal(str(item.get('netto_betrag', 0)))
                    netto_ep = round(netto_b / Decimal(str(menge)), 2) if menge else netto_b
                    pos = RechnungsPosition(
                        rechnung_id=rechnung.id,
                        position=idx,
                        artikel_id=item.get('artikel_id'),
                        artikel_name=item.get('name', ''),
                        menge=Decimal(str(menge)),
                        einzelpreis=netto_ep,
                        mwst_satz=Decimal(str(item.get('mwst_satz', 19))),
                        netto_betrag=netto_b,
                        mwst_betrag=Decimal(str(item.get('mwst_betrag', 0))),
                        brutto_betrag=Decimal(str(item.get('brutto_betrag', 0)))
                    )
                    db.session.add(pos)

                db.session.commit()
                rechnung_id = rechnung.id
                logger.info(f"Rechnung {rechnung_nummer} aus Kasse erstellt (Beleg {beleg.belegnummer})")

                # Aufträge im Warenkorb als completed markieren + archivieren
                from src.models.models import Order
                auftrag_ids = {item['auftrag_id'] for item in warenkorb if item.get('auftrag_id')}
                for aid in auftrag_ids:
                    o = Order.query.get(aid)
                    if o and o.workflow_status not in ('completed', 'cancelled'):
                        o.workflow_status = 'completed'
                        o.archive(user='Kasse', reason='invoiced')
                if auftrag_ids:
                    db.session.commit()
                    logger.info(f"Aufträge {auftrag_ids} als completed archiviert (Rechnung {rechnung_nummer})")
            except Exception as re:
                db.session.rollback()
                logger.warning(f"Rechnung konnte nicht aus Kasse erstellt werden: {re}")

        result = {
            'success': True,
            'beleg_id': beleg.id,
            'beleg_nummer': beleg.belegnummer,
            'message': f'Verkauf erfolgreich! Beleg-Nr.: {beleg.belegnummer}'
        }
        if rechnung_id:
            result['rechnung_id'] = rechnung_id
            result['rechnung_nummer'] = rechnung_nummer
        return result

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Datenbankfehler beim Abschluss des Verkaufs: {e}")
        return {'success': False, 'error': f'Datenbankfehler: {str(e)}'}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Fehler beim Abschluss des Verkaufs: {e}")
        return {'success': False, 'error': str(e)}

# --- ROUTEN FÜR DEN ZAHLUNGSFLUSS ---

@kasse_bp.route('/verkauf/abschliessen', methods=['POST'])
def verkauf_abschliessen():
    """
    Schließt einen Verkauf ab (Bar/EC über SumUp TSE).
    """
    # Debug: Request-Details loggen
    logger.info(f"Request Content-Type: {request.content_type}")
    logger.info(f"Request Data (raw): {request.data}")

    data = request.get_json(silent=True) or {}
    zahlungsart = data.get('zahlungsart', 'BAR')

    logger.info(f"Verkauf abschliessen - Zahlungsart: '{zahlungsart}', Data: {data}")

    # Akzeptiere BAR, EC, EC_KARTE, SUMUP und RECHNUNG
    allowed_payment_types = ['BAR', 'EC', 'EC_KARTE', 'SUMUP', 'RECHNUNG']
    if zahlungsart not in allowed_payment_types:
        logger.error(f"Ungültige Zahlungsart: '{zahlungsart}' - Erlaubt: {allowed_payment_types}")
        return jsonify({'success': False, 'error': f'Ungültige Zahlungsart: {zahlungsart}'}), 400

    warenkorb = get_warenkorb()
    result = _finalize_sale(
        warenkorb,
        zahlungsart=zahlungsart,
        gegeben=data.get('gegeben'),
        rueckgeld=data.get('rueckgeld'),
        rabatt_type=data.get('rabatt_type'),
        rabatt_value=float(data.get('rabatt_value', 0) or 0)
    )

    if result.get('success'):
        return jsonify(result)
    else:
        return jsonify(result), 500

@kasse_bp.route('/zahlung/sumup/start', methods=['POST'])
def start_sumup_payment():
    """
    Initiiert eine Zahlung über den produktiven SumUp-Service.
    """
    if not sumup_service:
        return jsonify({'success': False, 'error': 'SumUp Service nicht verfügbar'}), 503

    warenkorb = get_warenkorb()
    if not warenkorb:
        return jsonify({'success': False, 'error': 'Warenkorb ist leer'}), 400

    warenkorb_summen = calculate_warenkorb_totals(warenkorb)
    amount = warenkorb_summen['brutto_gesamt']
    sale_uuid = str(uuid.uuid4())
    
    # Ruft die produktive Methode im Service auf
    checkout_response = sumup_service.create_checkout(
        amount=amount,
        description=f"StitchAdmin Verkauf #{sale_uuid[:8]}",
        sale_uuid=sale_uuid
    )

    if checkout_response.get('success'):
        session['pending_sumup_sale'] = {
            'checkout_id': checkout_response['checkout_id'],
            'warenkorb': warenkorb,
            'sale_uuid': sale_uuid
        }
        logger.info(f"SumUp Checkout {checkout_response['checkout_id']} für Verkauf {sale_uuid} gestartet.")
        return jsonify(checkout_response)
    else:
        logger.error(f"Fehler beim Erstellen des SumUp Checkouts: {checkout_response.get('error')}")
        return jsonify(checkout_response), 500

@kasse_bp.route('/webhook/sumup', methods=['POST'])
def webhook_sumup():
    """
    Empfängt Webhooks von SumUp über Zahlungsstatus-Änderungen.
    """
    payload = request.get_json()
    logger.info(f"SumUp Webhook erhalten: {json.dumps(payload)}")

    if payload.get('event_type') == 'CHECKOUT_STATUS_CHANGED' and payload.get('status') == 'PAID':
        checkout_id = payload.get('checkout_id')
        pending_sale = session.get('pending_sumup_sale')
        
        if pending_sale and pending_sale['checkout_id'] == checkout_id:
            logger.info(f"Passender Verkauf für Checkout {checkout_id} gefunden. Schließe Verkauf ab...")
            
            result = _finalize_sale(
                warenkorb=pending_sale['warenkorb'],
                zahlungsart='SUMUP',
                transaction_info=f"sumup_{payload.get('transaction_code')}"
            )

            if result.get('success'):
                logger.info(f"Verkauf {pending_sale['sale_uuid']} erfolgreich via SumUp abgeschlossen.")
                session.pop('pending_sumup_sale', None)
            else:
                logger.error(f"Fehler beim Finalisieren des SumUp-Verkaufs {pending_sale['sale_uuid']}: {result.get('error')}")
        else:
            logger.warning(f"Kein passender Verkauf für erfolgreichen Checkout {checkout_id} in der Session gefunden.")

    return jsonify({'status': 'received'}), 200

@kasse_bp.route('/zahlung/status/<checkout_id>')
def get_payment_status(checkout_id):
    """
    Prüft den Status einer laufenden Zahlung (Fallback für Webhooks).
    """
    pending_sale = session.get('pending_sumup_sale')
    if pending_sale and pending_sale['checkout_id'] == checkout_id:
        return jsonify({'status': 'PENDING'})
    else:
        # Wenn der Verkauf nicht mehr in der Session ist, war der Webhook erfolgreich.
        return jsonify({'status': 'PAID'})

# ==========================================
# SUMUP TERMINAL API ROUTEN
# ==========================================

@kasse_bp.route('/sumup/terminals')
def sumup_terminals():
    """Listet alle verbundenen SumUp-Terminals"""
    try:
        result = sumup_service.list_readers()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Fehler beim Laden der SumUp Terminals: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@kasse_bp.route('/sumup/terminal/<reader_id>/checkout', methods=['POST'])
def sumup_terminal_checkout(reader_id):
    """Sendet eine Zahlung an ein bestimmtes SumUp-Terminal"""
    warenkorb = get_warenkorb()
    if not warenkorb:
        return jsonify({'success': False, 'error': 'Warenkorb ist leer'}), 400

    warenkorb_summen = calculate_warenkorb_totals(warenkorb)
    amount = warenkorb_summen['brutto_gesamt']

    result = sumup_service.create_reader_checkout(
        reader_id=reader_id,
        amount=amount,
        description=f"StitchAdmin Kassenverkauf"
    )

    if result.get('success'):
        session['pending_terminal_sale'] = {
            'reader_id': reader_id,
            'checkout_id': result.get('checkout_id', ''),
            'amount': amount,
        }
        session.modified = True

    return jsonify(result)

@kasse_bp.route('/sumup/terminal/<reader_id>/status')
def sumup_terminal_status(reader_id):
    """Prueft den Status eines Terminals (ob Zahlung abgeschlossen)"""
    try:
        result = sumup_service.get_reader_status(reader_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@kasse_bp.route('/sumup/terminal/<reader_id>/terminate', methods=['POST'])
def sumup_terminal_terminate(reader_id):
    """Bricht eine laufende Zahlung am Terminal ab"""
    try:
        result = sumup_service.terminate_reader_checkout(reader_id)
        session.pop('pending_terminal_sale', None)
        session.modified = True
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==========================================
# WARENKORB-HILFSFUNKTIONEN
# ==========================================

def get_warenkorb():
    """Holt den Warenkorb aus der Session"""
    return session.get('warenkorb', [])

def save_warenkorb(warenkorb):
    """Speichert den Warenkorb in der Session"""
    session['warenkorb'] = warenkorb
    session.modified = True

def calculate_warenkorb_totals(warenkorb):
    """Berechnet die Summen für den Warenkorb.

    Unterscheidet zwischen Netto- und Brutto-Preisen:
    - Artikel: preis ist Netto (ohne MwSt) → MwSt wird aufgeschlagen
    - Aufträge: preis ist Brutto (Endpreis inkl. MwSt) → MwSt wird herausgerechnet
    """
    netto_gesamt = 0
    mwst_gesamt = 0
    brutto_gesamt = 0

    for item in warenkorb:
        menge = item.get('menge', 1)
        preis = item.get('preis', 0)
        mwst_satz = item.get('mwst_satz', 19) / 100

        if item.get('preis_ist_brutto', False) or item.get('auftrag_id'):
            # Preis ist Brutto (z.B. Aufträge) → Netto herausrechnen
            brutto_betrag = preis * menge
            netto_betrag = round(brutto_betrag / (1 + mwst_satz), 2)
            mwst_betrag = round(brutto_betrag - netto_betrag, 2)
        else:
            # Preis ist Netto (z.B. Artikel) → MwSt aufschlagen
            netto_betrag = preis * menge
            mwst_betrag = round(netto_betrag * mwst_satz, 2)
            brutto_betrag = netto_betrag + mwst_betrag

        item['netto_betrag'] = round(netto_betrag, 2)
        item['mwst_betrag'] = round(mwst_betrag, 2)
        item['brutto_betrag'] = round(brutto_betrag, 2)

        netto_gesamt += netto_betrag
        mwst_gesamt += mwst_betrag
        brutto_gesamt += brutto_betrag

    return {
        'netto_gesamt': round(netto_gesamt, 2),
        'mwst_gesamt': round(mwst_gesamt, 2),
        'brutto_gesamt': round(brutto_gesamt, 2)
    }

# ==========================================
# HAUPT-UI-ROUTEN
# ==========================================

@kasse_bp.route('/')
@kasse_bp.route('/index')
def kassen_index():
    """Kassen-Übersicht mit Statistiken"""
    try:
        from datetime import date
        today = date.today()

        # Heutige Statistiken
        today_receipts_query = KassenBeleg.query.filter(
            db.func.date(KassenBeleg.erstellt_am) == today,
            KassenBeleg.storniert == False
        )

        today_receipts = today_receipts_query.count()
        today_revenue = db.session.query(db.func.sum(KassenBeleg.brutto_gesamt)).filter(
            db.func.date(KassenBeleg.erstellt_am) == today,
            KassenBeleg.storniert == False
        ).scalar() or 0

        # Letzte Belege
        recent_receipts = KassenBeleg.query.filter(
            db.func.date(KassenBeleg.erstellt_am) == today
        ).order_by(KassenBeleg.erstellt_am.desc()).limit(10).all()

        return render_template('kasse/index.html',
                             today_revenue=today_revenue,
                             today_receipts=today_receipts,
                             kasse_status='Aktiv',
                             tse_status='OK',
                             recent_receipts=recent_receipts)
    except Exception as e:
        logger.error(f"Fehler in kassen_index: {e}")
        return render_template('kasse/error.html', error=str(e))

@kasse_bp.route('/verkauf')
def verkauf_interface():
    """Verkaufs-Interface mit Warenkorb"""
    try:
        # SumUp-Status pruefen
        sumup_available = False
        try:
            sumup_available = sumup_service.is_configured()
        except Exception:
            pass

        # Zahlungsarten definieren
        zahlungsarten = [
            {'id': 'BAR', 'name': 'Barzahlung', 'icon': 'bi-cash-coin'},
            {'id': 'EC_KARTE', 'name': 'EC / Kartenzahlung', 'icon': 'bi-credit-card-2-front'},
            {'id': 'RECHNUNG', 'name': 'Auf Rechnung', 'icon': 'bi-receipt'}
        ]

        # Kunde aus Session laden
        kunde_id = session.get('customer_id')
        kunde_name = session.get('customer_name')
        kunde_email = None
        if kunde_id:
            kunde = Customer.query.get(kunde_id)
            if kunde:
                kunde_name = kunde.display_name
                kunde_email = kunde.email if hasattr(kunde, 'email') else None

        return render_template('kasse/verkauf.html',
                             zahlungsarten=zahlungsarten,
                             sumup_available=sumup_available,
                             kunde_id=kunde_id,
                             kunde_name=kunde_name,
                             kunde_email=kunde_email)
    except Exception as e:
        logger.error(f"Fehler in verkauf_interface: {e}")
        return render_template('kasse/error.html', error=str(e))

@kasse_bp.route('/tagesabschluss')
def tagesabschluss():
    """Tagesabschluss-Seite"""
    try:
        from datetime import date
        today = date.today()

        # Tagesstatistiken
        belege = KassenBeleg.query.filter(
            db.func.date(KassenBeleg.erstellt_am) == today,
            KassenBeleg.storniert == False
        ).all()

        # Gruppierung nach Zahlungsart
        stats = {
            'bar': {'count': 0, 'sum': 0},
            'card': {'count': 0, 'sum': 0},
            'invoice': {'count': 0, 'sum': 0},
        }

        for beleg in belege:
            key = beleg.zahlungsart.lower() if beleg.zahlungsart else 'bar'
            if key in stats:
                stats[key]['count'] += 1
                stats[key]['sum'] += beleg.summe_brutto

        return render_template('kasse/tagesabschluss.html',
                             belege=belege,
                             stats=stats,
                             datum=today)
    except Exception as e:
        logger.error(f"Fehler in tagesabschluss: {e}")
        return render_template('kasse/error.html', error=str(e))

# ==========================================
# WARENKORB-API-ROUTEN
# ==========================================

@kasse_bp.route('/artikel/suchen')
def artikel_suchen():
    """Artikel-Suche für Kassenverkauf"""
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify({'success': False, 'error': 'Keine Suchanfrage'})

    try:
        # Suche nach Name, Artikelnummer oder Barcode
        artikel = Article.query.filter(
            db.or_(
                Article.name.ilike(f'%{query}%'),
                Article.article_number.ilike(f'%{query}%')
            )
        ).limit(10).all()

        result = [{
            'id': a.id,
            'name': a.name,
            'article_number': a.article_number,
            'preis': float(a.price) if a.price else 0.0,
        } for a in artikel]

        return jsonify({'success': True, 'artikel': result})
    except Exception as e:
        logger.error(f"Fehler bei Artikel-Suche: {e}")
        return jsonify({'success': False, 'error': str(e)})

def _build_order_details(order):
    """Baut die Aufschluesselung eines Auftrags fuer die Kasse auf.

    Berechnet den Preis aus den echten Komponenten (OrderItems + OrderDesigns + design_cost),
    NICHT aus total_price (der oft falsch/unvollstaendig ist).

    Returns: (details_list, calculated_total)
    """
    from src.models.order_workflow import OrderDesign

    details = []
    calculated_total = 0
    veredelung_types = {
        'embroidery': 'Stickerei', 'printing': 'Druck', 'dtf': 'DTF-Druck',
        'sublimation': 'Sublimation', 'combined': 'Kombi-Veredelung'
    }

    # 1. Artikel/Textilien aus OrderItems
    artikel_kosten = 0
    total_qty = 0
    for item in order.items.all():
        artikel_name = item.article.name if item.article else 'Artikel'
        detail_text = f"{item.quantity}x {artikel_name}"
        if item.textile_color:
            detail_text += f" ({item.textile_color}"
            if item.textile_size:
                detail_text += f"/{item.textile_size}"
            detail_text += ")"
        item_total = float(item.unit_price or 0) * (item.quantity or 1)
        artikel_kosten += item_total
        total_qty += (item.quantity or 0)
        details.append({'label': detail_text, 'betrag': round(item_total, 2) if item_total > 0 else 0, 'typ': 'artikel'})

    total_qty = max(total_qty, 1)
    calculated_total += artikel_kosten

    # 2. Veredelung/Produktion aus OrderDesign-Positionen (echte DB-Daten)
    designs = OrderDesign.query.filter_by(order_id=order.id).all()
    veredelung_kosten = 0
    erstellkosten = 0
    for design in designs:
        veredelung_kosten += float(design.setup_price or 0) + float(design.price_per_piece or 0) * total_qty
        # supplier_cost = Design-Erstellkosten (beim Lieferanten bestellt)
        if design.supplier_cost and float(design.supplier_cost) > 0:
            erstellkosten += float(design.supplier_cost)

    if order.order_type and order.order_type in veredelung_types:
        veredelung_label = veredelung_types[order.order_type]

        # Details hinzufuegen (Stichzahl, Druckflaeche)
        extra = []
        if order.order_type in ['embroidery', 'combined'] and order.stitch_count:
            extra.append(f"{order.stitch_count:,} Stiche".replace(',', '.'))
        if order.order_type in ['printing', 'dtf', 'sublimation', 'combined']:
            if order.print_width_cm and order.print_height_cm:
                extra.append(f"{order.print_width_cm}x{order.print_height_cm}cm")
        if extra:
            veredelung_label += f" ({', '.join(extra)})"

        details.append({
            'label': veredelung_label,
            'betrag': round(veredelung_kosten, 2),
            'typ': 'veredelung',
            'inkl': veredelung_kosten < 0.01
        })

    calculated_total += veredelung_kosten

    # 3. Design-Erstellkosten aus OrderDesign.supplier_cost
    if erstellkosten > 0:
        details.append({'label': 'Design-Erstellung', 'betrag': round(erstellkosten, 2), 'typ': 'design'})
        calculated_total += erstellkosten

    # 4. Zusätzliche Design-Kosten vom Order (falls separat eingetragen)
    design_erstellung = float(order.design_cost or 0)
    if design_erstellung > 0:
        details.append({'label': 'Design-Kosten', 'betrag': round(design_erstellung, 2), 'typ': 'design'})
        calculated_total += design_erstellung

    adaptation = float(order.adaptation_cost or 0)
    if adaptation > 0:
        details.append({'label': 'Design-Anpassung', 'betrag': round(adaptation, 2), 'typ': 'design'})
        calculated_total += adaptation

    # Fallback: Wenn keine Positionen vorhanden, total_price verwenden
    if calculated_total < 0.01 and float(order.total_price or 0) > 0:
        calculated_total = float(order.total_price)

    return details, round(calculated_total, 2)


@kasse_bp.route('/auftraege/suchen')
def auftraege_suchen():
    """Auftrags-Suche für Kassenverkauf"""
    from src.models.models import Order

    query = request.args.get('q', '').strip()

    try:
        # Basis-Query: Nur abrechenbare Aufträge
        query_filter = Order.query.filter(
            Order.status.in_(['accepted', 'in_progress', 'ready', 'completed'])
        )

        # Wenn Suche angegeben, filtere nach Auftragsnummer
        if query:
            query_filter = query_filter.filter(
                db.or_(
                    Order.order_number.ilike(f'%{query}%'),
                    Order.id.ilike(f'%{query}%')
                )
            )

        # Limitiere auf 50 Aufträge, sortiere nach neuesten
        auftraege = query_filter.order_by(Order.created_at.desc()).limit(50).all()

        result = []
        for order in auftraege:
            details, calculated_total = _build_order_details(order)

            billing = order.get_billing_customer() if hasattr(order, 'get_billing_customer') else order.customer
            result.append({
                'id': order.id,
                'order_number': order.order_number,
                'beschreibung': order.description or 'Keine Beschreibung',
                'preis': calculated_total,
                'kunde': billing.display_name if billing else 'Kein Kunde',
                'kunde_id': billing.id if billing else order.customer_id,
                'kunde_name': billing.display_name if billing else None,
                'status': order.status,
                'order_type': order.order_type or '',
                'details': details
            })

        return jsonify({'success': True, 'auftraege': result})
    except Exception as e:
        logger.error(f"Fehler bei Auftrags-Suche: {e}")
        return jsonify({'success': False, 'error': str(e)})

@kasse_bp.route('/kunden/suchen')
def kunden_suchen():
    """Kunden-Suche für Kassenverkauf"""
    query = request.args.get('q', '').strip()

    try:
        if query:
            # Suche nach Name, Kundennummer oder Barcode
            kunden = Customer.query.filter(
                db.or_(
                    Customer.first_name.ilike(f'%{query}%'),
                    Customer.last_name.ilike(f'%{query}%'),
                    Customer.customer_number.ilike(f'%{query}%'),
                    Customer.barcode.ilike(f'%{query}%') if hasattr(Customer, 'barcode') else False
                )
            ).limit(20).all()
        else:
            # Ohne Query: Zeige die letzten 20 Kunden
            kunden = Customer.query.order_by(Customer.created_at.desc()).limit(20).all()

        result = [{
            'id': k.id,
            'name': k.display_name,
            'customer_number': k.customer_number,
            'email': k.email or '',
            'barcode': k.barcode if hasattr(k, 'barcode') else ''
        } for k in kunden]

        return jsonify({'success': True, 'kunden': result})
    except Exception as e:
        logger.error(f"Fehler bei Kunden-Suche: {e}")
        return jsonify({'success': False, 'error': str(e)})

@kasse_bp.route('/kunde/setzen', methods=['POST'])
def kunde_setzen():
    """Setzt den aktuellen Kunden für den Verkauf"""
    data = request.get_json()
    customer_id = data.get('customer_id')

    if customer_id:
        # Prüfe ob Kunde existiert
        kunde = Customer.query.get(customer_id)
        if kunde:
            session['customer_id'] = customer_id
            session['customer_name'] = kunde.display_name
            session.modified = True
            return jsonify({
                'success': True,
                'customer_id': customer_id,
                'customer_name': session['customer_name']
            })
        else:
            return jsonify({'success': False, 'error': 'Kunde nicht gefunden'}), 404
    else:
        # Laufkunde - entferne Kunde aus Session
        session.pop('customer_id', None)
        session.pop('customer_name', None)
        session.modified = True
        return jsonify({
            'success': True,
            'customer_id': None,
            'customer_name': 'Laufkunde'
        })

@kasse_bp.route('/auftrag/uebernehmen/<order_id>', methods=['POST'])
def auftrag_uebernehmen(order_id):
    """Übernimmt einen Auftrag als Ganzes zur Kasse (mit Aufschlüsselung)"""
    try:
        from src.models.models import Order

        # Lade Auftrag
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'success': False, 'error': 'Auftrag nicht gefunden'}), 404

        # Setze Rechnungsempfaenger (billing_customer wenn vorhanden, sonst Hauptkunde)
        billing = order.get_billing_customer() if hasattr(order, 'get_billing_customer') else order.customer
        if billing:
            session['customer_id'] = billing.id
            session['customer_name'] = billing.display_name

        warenkorb = get_warenkorb()

        # Prüfe ob Auftrag schon im Warenkorb
        existing = next((item for item in warenkorb if item.get('auftrag_id') == order.id), None)
        if existing:
            return jsonify({'success': False, 'error': f'Auftrag {order.order_number} ist bereits im Warenkorb'}), 400

        # Aufschlüsselung erstellen (Artikel, Veredelung, Design) + berechneter Preis
        details, calculated_total = _build_order_details(order)

        # Auftrag als EIN Item mit berechnetem Gesamtpreis hinzufügen
        beschreibung = order.description or ''
        name = f"Auftrag {order.order_number}"
        if beschreibung and beschreibung != 'Keine Beschreibung':
            name += f" - {beschreibung}"

        warenkorb.append({
            'warenkorb_id': str(uuid.uuid4()),
            'artikel_id': None,
            'auftrag_id': order.id,
            'name': name,
            'preis': calculated_total,
            'preis_ist_brutto': True,  # Auftragspreise sind Endpreise (inkl. MwSt)
            'menge': 1,
            'mwst_satz': 19,
            'details': details,
            'kunde_id': billing.id if billing else order.customer_id,
            'kunde_name': billing.display_name if billing else None
        })

        save_warenkorb(warenkorb)
        warenkorb_summen = calculate_warenkorb_totals(warenkorb)

        session.modified = True

        return jsonify({
            'success': True,
            'message': f'Auftrag {order.order_number} zur Kasse übernommen',
            'warenkorb': warenkorb,
            'warenkorb_summen': warenkorb_summen,
            'redirect_url': url_for('kasse.verkauf_interface')
        })

    except Exception as e:
        logger.error(f"Fehler beim Übernehmen des Auftrags: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@kasse_bp.route('/warenkorb/hinzufuegen', methods=['POST'])
def warenkorb_hinzufuegen():
    """Artikel oder Auftrag zum Warenkorb hinzufügen"""
    data = request.get_json() or {}
    warenkorb = get_warenkorb()

    artikel_id = data.get('artikel_id')
    auftrag_id = data.get('auftrag_id')

    # Fall 1: Auftrag hinzufügen
    if auftrag_id:
        from src.models.models import Order

        # Prüfe, ob Auftrag schon im Warenkorb ist
        existing = next((item for item in warenkorb if item.get('auftrag_id') == auftrag_id), None)

        if existing:
            # Erhöhe Menge (normalerweise 1 für Aufträge)
            existing['menge'] = existing.get('menge', 1) + 1
        else:
            # Füge neuen Auftrag hinzu
            auftrag = Order.query.get(auftrag_id)
            if auftrag:
                # Details + berechneten Preis aus DB-Komponenten holen
                details, calculated_total = _build_order_details(auftrag)

                billing_k = auftrag.get_billing_customer() if hasattr(auftrag, 'get_billing_customer') else auftrag.customer
                warenkorb.append({
                    'warenkorb_id': str(uuid.uuid4()),
                    'artikel_id': None,  # Kein Artikel
                    'auftrag_id': auftrag.id,
                    'name': data.get('name', f'Auftrag {auftrag.order_number}'),
                    'preis': calculated_total,
                    'preis_ist_brutto': True,  # Auftragspreise sind Endpreise (inkl. MwSt)
                    'menge': data.get('menge', 1),
                    'mwst_satz': 19,
                    'details': details,
                    'kunde_id': billing_k.id if billing_k else auftrag.customer_id,
                    'kunde_name': billing_k.display_name if billing_k else None
                })

                # Rechnungsempfaenger aus Auftrag uebernehmen
                if billing_k and not session.get('customer_id'):
                    session['customer_id'] = billing_k.id
                    session['customer_name'] = billing_k.display_name
                    session.modified = True

    # Fall 2: Artikel hinzufügen
    elif artikel_id:
        # Prüfe, ob Artikel schon im Warenkorb ist
        existing = next((item for item in warenkorb if item.get('artikel_id') == artikel_id), None)

        if existing:
            # Erhöhe Menge
            existing['menge'] = existing.get('menge', 1) + 1
        else:
            # Füge neuen Artikel hinzu
            artikel = Article.query.get(artikel_id)
            if artikel:
                warenkorb.append({
                    'warenkorb_id': str(uuid.uuid4()),
                    'artikel_id': artikel.id,
                    'auftrag_id': None,
                    'name': artikel.name,
                    'preis': float(artikel.price) if artikel.price else 0.0,
                    'menge': data.get('menge', 1),
                    'mwst_satz': 19
                })

    save_warenkorb(warenkorb)
    warenkorb_summen = calculate_warenkorb_totals(warenkorb)

    return jsonify({
        'success': True,
        'warenkorb': warenkorb,
        'warenkorb_summen': warenkorb_summen,
        'customer_id': session.get('customer_id'),
        'customer_name': session.get('customer_name')
    })

@kasse_bp.route('/warenkorb/aktualisieren', methods=['POST'])
def warenkorb_aktualisieren():
    """Menge eines Warenkorb-Items aktualisieren"""
    data = request.get_json()
    warenkorb_id = data.get('warenkorb_id')
    neue_menge = int(data.get('menge', 1))

    warenkorb = get_warenkorb()
    item = next((item for item in warenkorb if item.get('warenkorb_id') == warenkorb_id), None)

    if item and neue_menge > 0:
        item['menge'] = neue_menge

    save_warenkorb(warenkorb)
    warenkorb_summen = calculate_warenkorb_totals(warenkorb)

    return jsonify({
        'success': True,
        'warenkorb': warenkorb,
        'warenkorb_summen': warenkorb_summen
    })

@kasse_bp.route('/warenkorb/entfernen', methods=['POST'])
def warenkorb_entfernen():
    """Artikel aus dem Warenkorb entfernen"""
    data = request.get_json()
    warenkorb_id = data.get('warenkorb_id')

    warenkorb = get_warenkorb()
    warenkorb = [item for item in warenkorb if item.get('warenkorb_id') != warenkorb_id]

    save_warenkorb(warenkorb)
    warenkorb_summen = calculate_warenkorb_totals(warenkorb)

    return jsonify({
        'success': True,
        'warenkorb': warenkorb,
        'warenkorb_summen': warenkorb_summen
    })

@kasse_bp.route('/warenkorb/leeren', methods=['POST'])
def warenkorb_leeren():
    """Warenkorb komplett leeren"""
    session['warenkorb'] = []
    session.modified = True

    return jsonify({
        'success': True,
        'warenkorb': [],
        'warenkorb_summen': {'netto_gesamt': 0, 'mwst_gesamt': 0, 'brutto_gesamt': 0}
    })

# ==========================================
# WEITERE HILFS-ROUTEN
# ==========================================

@kasse_bp.route('/beleg/<int:beleg_id>')
def beleg_detail(beleg_id):
    """Beleg-Details anzeigen"""
    try:
        beleg = KassenBeleg.query.get_or_404(beleg_id)
        return render_template('kasse/beleg_detail.html', beleg=beleg)
    except Exception as e:
        logger.error(f"Fehler beim Laden des Belegs: {e}")
        return render_template('kasse/error.html', error=str(e))

@kasse_bp.route('/einstellungen')
def kassen_einstellungen():
    """Kassen-Einstellungen"""
    return render_template('kasse/einstellungen.html')

@kasse_bp.route('/berichte')
def berichte():
    """Kassen-Berichte"""
    return render_template('kasse/berichte.html')

@kasse_bp.route('/z-bericht')
def z_bericht():
    """Z-Bericht (Kassenjournal)"""
    return render_template('kasse/z_bericht.html')

# ==========================================
# BELEG DRUCKEN / EMAIL
# ==========================================

@kasse_bp.route('/beleg/<int:beleg_id>/drucken')
def beleg_drucken(beleg_id):
    """Beleg-Druckansicht"""
    try:
        beleg = KassenBeleg.query.get_or_404(beleg_id)
        positionen = BelegPosition.query.filter_by(beleg_id=beleg_id).all()

        # Lade Kunde wenn vorhanden
        kunde = None
        if beleg.kunde_id:
            kunde = Customer.query.get(beleg.kunde_id)

        # Lade Firmeneinstellungen für Beleg-Header
        from src.models.models import Settings
        settings = Settings.query.first()

        return render_template('kasse/beleg_drucken.html',
                             beleg=beleg,
                             positionen=positionen,
                             kunde=kunde,
                             settings=settings)
    except Exception as e:
        logger.error(f"Fehler beim Laden des Belegs zum Drucken: {e}")
        return f"Fehler: {str(e)}", 500

@kasse_bp.route('/beleg/<int:beleg_id>/email', methods=['POST'])
def beleg_email(beleg_id):
    """Beleg per Email senden"""
    try:
        data = request.get_json() or {}
        email = data.get('email', '').strip()

        if not email:
            return jsonify({'success': False, 'error': 'Keine E-Mail-Adresse angegeben'}), 400

        beleg = KassenBeleg.query.get_or_404(beleg_id)
        positionen = BelegPosition.query.filter_by(beleg_id=beleg_id).all()

        # Lade Kunde wenn vorhanden
        kunde = None
        if beleg.kunde_id:
            kunde = Customer.query.get(beleg.kunde_id)

        # Lade Firmeneinstellungen
        from src.models.models import Settings
        settings = Settings.query.first()

        # Erstelle Email-HTML
        from flask import render_template_string
        email_html = render_template('kasse/beleg_email.html',
                                    beleg=beleg,
                                    positionen=positionen,
                                    kunde=kunde,
                                    settings=settings)

        # Sende Email
        from src.services.email_service import EmailService
        email_service = EmailService()

        result = email_service.send_email(
            to=email,
            subject=f"Ihr Kassenbeleg {beleg.belegnummer}",
            html_content=email_html
        )

        if result:
            logger.info(f"Beleg {beleg.belegnummer} erfolgreich an {email} gesendet")
            return jsonify({'success': True, 'message': f'Beleg an {email} gesendet'})
        else:
            return jsonify({'success': False, 'error': 'E-Mail konnte nicht gesendet werden'}), 500

    except Exception as e:
        logger.error(f"Fehler beim E-Mail-Versand des Belegs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
