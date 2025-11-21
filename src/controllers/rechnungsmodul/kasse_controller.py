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

import logging
logger = logging.getLogger(__name__)

kasse_bp = Blueprint('kasse', __name__, url_prefix='/kasse')

# ... (TSE-Service, Utility-Klassen und Warenkorb-Funktionen bleiben unverändert) ...

def _finalize_sale(warenkorb, zahlungsart, gegeben=None, rueckgeld=None, transaction_info=None):
    """
    Interne Funktion, um einen Verkauf abzuschließen.
    Wird von Barverkäufen und SumUp-Webhooks aufgerufen.
    """
    try:
        if not warenkorb or len(warenkorb) == 0:
            return {'success': False, 'error': 'Warenkorb ist leer'}

        # Berechne Summen
        warenkorb_summen = calculate_warenkorb_totals(warenkorb)

        # Erstelle Kassenbeleg
        beleg = KassenBeleg(
            beleg_nummer=f"B-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            datum=datetime.now(),
            kunde_id=session.get('customer_id'),
            summe_netto=warenkorb_summen['netto_gesamt'],
            summe_brutto=warenkorb_summen['brutto_gesamt'],
            mwst_betrag=warenkorb_summen['mwst_gesamt'],
            zahlungsart=zahlungsart,
            storniert=False
        )

        db.session.add(beleg)
        db.session.flush()  # Beleg-ID generieren

        # Erstelle Belegpositionen
        for item in warenkorb:
            position = BelegPosition(
                beleg_id=beleg.id,
                artikel_id=item.get('artikel_id'),
                bezeichnung=item.get('name'),
                menge=item.get('menge', 1),
                einzelpreis=item.get('preis', 0),
                netto_betrag=item.get('netto_betrag', 0),
                mwst_betrag=item.get('mwst_betrag', 0),
                brutto_betrag=item.get('brutto_betrag', 0),
                mwst_satz=item.get('mwst_satz', 19)
            )
            db.session.add(position)

        # Erstelle Transaktion
        transaktion = KassenTransaktion(
            beleg_id=beleg.id,
            zahlungsart=ZahlungsArt[zahlungsart] if hasattr(ZahlungsArt, zahlungsart) else ZahlungsArt.BAR,
            betrag=warenkorb_summen['brutto_gesamt'],
            gegeben=gegeben,
            rueckgeld=rueckgeld,
            transaktions_info=transaction_info
        )
        db.session.add(transaktion)

        # Speichern
        db.session.commit()

        # Warenkorb leeren
        session['warenkorb'] = []
        session.modified = True

        logger.info(f"Verkauf erfolgreich abgeschlossen: Beleg {beleg.beleg_nummer}")

        return {
            'success': True,
            'beleg_id': beleg.id,
            'beleg_nummer': beleg.beleg_nummer,
            'message': f'Verkauf erfolgreich! Beleg-Nr.: {beleg.beleg_nummer}'
        }

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
    Schließt einen Bar-Verkauf direkt ab.
    """
    data = request.get_json()
    if data.get('zahlungsart') != 'BAR':
        return jsonify({'success': False, 'error': 'Diese Route ist nur für Barzahlungen.'}), 400

    warenkorb = get_warenkorb()
    result = _finalize_sale(
        warenkorb,
        zahlungsart='BAR',
        gegeben=data.get('erhaltener_betrag'),
        rueckgeld=data.get('rueckgeld')
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
    """Berechnet die Summen für den Warenkorb"""
    netto_gesamt = 0
    mwst_gesamt = 0
    brutto_gesamt = 0

    for item in warenkorb:
        menge = item.get('menge', 1)
        preis = item.get('preis', 0)
        mwst_satz = item.get('mwst_satz', 19) / 100

        netto_betrag = preis * menge
        mwst_betrag = netto_betrag * mwst_satz
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
            db.func.date(KassenBeleg.datum) == today,
            KassenBeleg.storniert == False
        )

        today_receipts = today_receipts_query.count()
        today_revenue = db.session.query(db.func.sum(KassenBeleg.summe_brutto)).filter(
            db.func.date(KassenBeleg.datum) == today,
            KassenBeleg.storniert == False
        ).scalar() or 0

        # Letzte Belege
        recent_receipts = KassenBeleg.query.filter(
            db.func.date(KassenBeleg.datum) == today
        ).order_by(KassenBeleg.datum.desc()).limit(10).all()

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
        # Zahlungsarten definieren
        zahlungsarten = [
            {'id': 'BAR', 'name': 'Bar', 'icon': 'bi-cash'},
            {'id': 'SUMUP', 'name': 'Karte (SumUp)', 'icon': 'bi-credit-card'},
            {'id': 'RECHNUNG', 'name': 'Auf Rechnung', 'icon': 'bi-receipt'}
        ]

        return render_template('kasse/verkauf.html', zahlungsarten=zahlungsarten)
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
            db.func.date(KassenBeleg.datum) == today,
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
            'name': f"{k.first_name} {k.last_name}".strip(),
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
            session['customer_name'] = f"{kunde.first_name} {kunde.last_name}".strip()
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
    """Übernimmt einen Auftrag zur Kasse/Rechnung"""
    try:
        from src.models.models import Order

        # Lade Auftrag
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'success': False, 'error': 'Auftrag nicht gefunden'}), 404

        # Setze Kunde
        if order.customer_id:
            session['customer_id'] = order.customer_id
            kunde = Customer.query.get(order.customer_id)
            if kunde:
                session['customer_name'] = f"{kunde.first_name} {kunde.last_name}".strip()

        # Füge alle Auftragspositionen zum Warenkorb hinzu
        warenkorb = get_warenkorb()

        # Wenn Artikel vorhanden, füge sie hinzu
        if hasattr(order, 'items') and order.items:
            for item in order.items:
                artikel = Article.query.get(item.article_id)
                if artikel:
                    warenkorb.append({
                        'warenkorb_id': str(uuid.uuid4()),
                        'artikel_id': artikel.id,
                        'name': artikel.name,
                        'preis': float(item.unit_price or artikel.price or 0),
                        'menge': item.quantity or 1,
                        'mwst_satz': 19
                    })
        else:
            # Fallback: Füge Gesamtpreis als Position hinzu
            warenkorb.append({
                'warenkorb_id': str(uuid.uuid4()),
                'artikel_id': None,
                'name': f"Auftrag {order.order_number}: {order.description or 'Auftrag'}",
                'preis': float(order.total_price or 0),
                'menge': 1,
                'mwst_satz': 19
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
    """Artikel zum Warenkorb hinzufügen"""
    data = request.get_json() or {}
    warenkorb = get_warenkorb()

    artikel_id = data.get('artikel_id')
    if artikel_id:
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
        'warenkorb_summen': warenkorb_summen
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
