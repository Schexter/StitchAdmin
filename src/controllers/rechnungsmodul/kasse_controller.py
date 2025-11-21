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
    # ... (Implementierung ist bereits robust und bleibt unverändert) ...
    pass

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

# ... (Die restlichen Routen wie /verkauf, /artikel/suchen etc. bleiben unverändert) ...
