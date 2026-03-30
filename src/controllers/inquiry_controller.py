# -*- coding: utf-8 -*-
"""
Öffentlicher Anfrage-Controller
Anfrage-Formular, Danke-Seite, Status-Tracking (kein Login nötig)

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import time
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash
from src.services.inquiry_service import (
    create_inquiry, get_inquiry_by_token, get_inquiry_by_number,
    find_inquiries_by_email, DSGVO_CONSENT_TEXT
)
from src.models.inquiry import INQUIRY_TYPE_LABELS

inquiry_bp = Blueprint('inquiry', __name__, url_prefix='/anfrage')

# Einheitlicher Tracking-Blueprint (öffentlich)
tracking_bp = Blueprint('tracking', __name__, url_prefix='/tracking')


@inquiry_bp.route('/', methods=['GET', 'POST'], strict_slashes=False)
def form():
    """Anfrage-Formular anzeigen und verarbeiten"""
    company = _get_company()

    if request.method == 'POST':
        # Bot-Schutz: Honeypot-Feld (Bots füllen es aus, echte User nicht)
        if request.form.get('website'):
            logging.getLogger(__name__).warning(f'Bot-Anfrage abgefangen (Honeypot): IP={request.remote_addr}')
            return redirect(url_for('inquiry.form'))

        # Bot-Schutz: Zeitstempel (< 3 Sekunden = zu schnell für echten Menschen)
        try:
            form_ts = int(request.form.get('form_timestamp', 0))
            elapsed = int(time.time()) - form_ts
            if 0 < elapsed < 3:
                logging.getLogger(__name__).warning(f'Bot-Anfrage abgefangen (Zeitstempel {elapsed}s): IP={request.remote_addr}')
                return redirect(url_for('inquiry.form'))
        except (ValueError, TypeError):
            pass

        # Validierung
        errors = []
        if not request.form.get('first_name'):
            errors.append('Bitte geben Sie Ihren Vornamen an.')
        if not request.form.get('last_name'):
            errors.append('Bitte geben Sie Ihren Nachnamen an.')
        if not request.form.get('email'):
            errors.append('Bitte geben Sie Ihre E-Mail-Adresse an.')
        if not request.form.get('inquiry_type'):
            errors.append('Bitte wählen Sie eine Anfrageart.')
        if not request.form.get('description'):
            errors.append('Bitte beschreiben Sie Ihre Anfrage.')
        if not request.form.get('dsgvo_consent'):
            errors.append('Bitte stimmen Sie der Datenverarbeitung zu.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('inquiry/form.html',
                                 form_data=request.form,
                                 inquiry_types=INQUIRY_TYPE_LABELS,
                                 dsgvo_text=DSGVO_CONSENT_TEXT,
                                 company=company,
                                 cart_count=0,
                                 form_timestamp=int(time.time()))

        try:
            inquiry = create_inquiry(
                form_data=request.form,
                files=request.files,
                remote_ip=request.remote_addr
            )
            return redirect(url_for('inquiry.danke', token=inquiry.tracking_token))
        except Exception as e:
            flash(f'Fehler beim Absenden: {str(e)}', 'danger')

    return render_template('inquiry/form.html',
                         form_data={},
                         inquiry_types=INQUIRY_TYPE_LABELS,
                         dsgvo_text=DSGVO_CONSENT_TEXT,
                         company=company,
                         cart_count=0,
                         form_timestamp=int(time.time()))


@inquiry_bp.route('/danke/<token>')
def danke(token):
    """Danke-Seite nach Absenden"""
    inquiry = get_inquiry_by_token(token)
    if not inquiry:
        flash('Anfrage nicht gefunden.', 'danger')
        return redirect(url_for('inquiry.form'))

    return render_template('inquiry/danke.html',
                         inquiry=inquiry,
                         company=_get_company(),
                         cart_count=0)


@inquiry_bp.route('/status/<token>')
def status(token):
    """Weiterleitung auf einheitliche Tracking-Seite"""
    return redirect(url_for('tracking.unified_status', token=token))


@inquiry_bp.route('/status', methods=['GET', 'POST'])
def status_lookup():
    """Status-Lookup per Anfragen-Nummer oder E-Mail"""
    inquiries = None

    if request.method == 'POST':
        search = request.form.get('search', '').strip()
        if not search:
            flash('Bitte geben Sie Ihre Anfragen-Nummer oder E-Mail ein.', 'warning')
        elif '@' in search:
            inquiries = find_inquiries_by_email(search)
            if not inquiries:
                flash('Keine Anfragen zu dieser E-Mail gefunden.', 'info')
        else:
            inquiry = get_inquiry_by_number(search.upper())
            if inquiry:
                return redirect(url_for('inquiry.status', token=inquiry.tracking_token))
            flash('Keine Anfrage mit dieser Nummer gefunden.', 'info')

    return render_template('inquiry/status_lookup.html',
                         inquiries=inquiries,
                         company=_get_company(),
                         cart_count=0)


def _get_company():
    """CompanySettings laden"""
    try:
        from src.models.company_settings import CompanySettings
        return CompanySettings.get_settings()
    except Exception:
        return None


# ============================================================
# EINHEITLICHES TRACKING (/tracking/<token>)
# Ein Link für den gesamten Workflow: Anfrage → Angebot → Freigabe → Produktion → Versand
# ============================================================

def _build_workflow_timeline(token):
    """
    Baut die komplette Workflow-Timeline aus einem Tracking-Token.
    Sucht in Inquiry, Angebot und Order - folgt der Kette.
    """
    from src.models.inquiry import Inquiry
    from src.models.angebot import Angebot, AngebotStatus
    from src.models.models import Order, Shipment

    inquiry = None
    angebot = None
    order = None

    # Token in allen Entities suchen
    inquiry = Inquiry.query.filter_by(tracking_token=token).first()
    angebot = Angebot.query.filter_by(tracking_token=token).first()
    order = Order.query.filter_by(tracking_token=token).first()

    # Kette vervollständigen (falls nur ein Teil gefunden)
    if inquiry and not angebot and inquiry.angebot_id:
        angebot = Angebot.query.get(inquiry.angebot_id)
    if inquiry and not order and inquiry.order_id:
        order = Order.query.get(inquiry.order_id)
    if angebot and not order and angebot.auftrag_id:
        order = Order.query.get(angebot.auftrag_id)
    if angebot and not inquiry:
        inquiry = Inquiry.query.filter_by(angebot_id=angebot.id).first()
    if order and not angebot:
        angebot = Angebot.query.filter_by(auftrag_id=order.id).first()
    if order and not inquiry:
        inquiry = Inquiry.query.filter_by(order_id=order.id).first()

    if not inquiry and not angebot and not order:
        return None

    # Kundenname ermitteln
    customer_name = ''
    if inquiry:
        customer_name = inquiry.full_name
    elif angebot:
        customer_name = angebot.kunde_name
    elif order and order.customer:
        customer_name = order.customer.display_name

    # Timeline-Schritte aufbauen
    steps = []

    # 1. Anfrage
    if inquiry:
        steps.append({
            'key': 'anfrage',
            'label': 'Anfrage',
            'icon': 'bi-envelope-paper',
            'color': 'primary',
            'active': True,
            'completed': inquiry.status not in ('neu',),
            'current': inquiry.status in ('neu', 'in_bearbeitung') and not angebot and not order,
            'detail': f'{inquiry.inquiry_number} - {inquiry.type_label}',
            'date': inquiry.created_at,
        })
    else:
        steps.append({
            'key': 'anfrage',
            'label': 'Anfrage',
            'icon': 'bi-envelope-paper',
            'color': 'secondary',
            'active': False,
            'completed': False,
            'current': False,
            'detail': 'Ohne Anfrage',
            'date': None,
        })

    # 2. Angebot
    if angebot:
        angebot_active = angebot.status in (AngebotStatus.VERSCHICKT,)
        angebot_done = angebot.status in (AngebotStatus.ANGENOMMEN,)
        steps.append({
            'key': 'angebot',
            'label': 'Angebot',
            'icon': 'bi-file-earmark-text',
            'color': 'info',
            'active': True,
            'completed': angebot_done or (order is not None),
            'current': angebot.status in (AngebotStatus.ENTWURF, AngebotStatus.VERSCHICKT) and not order,
            'detail': f'{angebot.angebotsnummer} - {"Gültig bis " + angebot.gueltig_bis.strftime("%d.%m.%Y") if angebot.gueltig_bis else ""}',
            'date': angebot.angebotsdatum,
            'status': angebot.status,
            'betrag': angebot.brutto_gesamt,
        })
    else:
        steps.append({
            'key': 'angebot',
            'label': 'Angebot',
            'icon': 'bi-file-earmark-text',
            'color': 'secondary',
            'active': False,
            'completed': False,
            'current': False,
            'detail': '',
            'date': None,
        })

    # 3. Auftrag / Freigabe
    if order:
        order_confirmed = order.status not in ('new', 'pending')
        steps.append({
            'key': 'auftrag',
            'label': 'Auftrag',
            'icon': 'bi-clipboard-check',
            'color': 'success',
            'active': True,
            'completed': order_confirmed,
            'current': order.status in ('new', 'confirmed') and order.workflow_status in ('design_pending', 'design_uploaded', None, ''),
            'detail': f'Auftrag {order.order_number}',
            'date': order.created_at,
        })
    else:
        steps.append({
            'key': 'auftrag',
            'label': 'Auftrag',
            'icon': 'bi-clipboard-check',
            'color': 'secondary',
            'active': False,
            'completed': False,
            'current': False,
            'detail': '',
            'date': None,
        })

    # 4. Produktion
    if order:
        in_production = order.workflow_status in ('in_production', 'production_done', 'quality_check', 'ready_to_ship', 'shipped', 'delivered')
        production_done = order.workflow_status in ('production_done', 'quality_check', 'ready_to_ship', 'shipped', 'delivered')
        steps.append({
            'key': 'produktion',
            'label': 'Produktion',
            'icon': 'bi-gear',
            'color': 'warning' if in_production and not production_done else ('success' if production_done else 'secondary'),
            'active': in_production,
            'completed': production_done,
            'current': order.workflow_status == 'in_production',
            'detail': 'In Fertigung' if order.workflow_status == 'in_production' else ('Fertiggestellt' if production_done else ''),
            'date': None,
        })
    else:
        steps.append({
            'key': 'produktion',
            'label': 'Produktion',
            'icon': 'bi-gear',
            'color': 'secondary',
            'active': False,
            'completed': False,
            'current': False,
            'detail': '',
            'date': None,
        })

    # 5. Versand
    shipment = None
    if order:
        shipment = Shipment.query.filter_by(order_id=order.id).order_by(Shipment.created_at.desc()).first()
    shipped = order and order.workflow_status in ('shipped', 'delivered')
    steps.append({
        'key': 'versand',
        'label': 'Versand',
        'icon': 'bi-truck',
        'color': 'success' if shipped else ('warning' if (order and order.workflow_status == 'ready_to_ship') else 'secondary'),
        'active': shipped or (order is not None and order.workflow_status == 'ready_to_ship'),
        'completed': shipped,
        'current': order is not None and order.workflow_status == 'ready_to_ship',
        'detail': f'Sendungsnr: {shipment.tracking_number}' if shipment and shipment.tracking_number else ('Versandbereit' if (order and order.workflow_status == 'ready_to_ship') else ''),
        'date': shipment.shipped_at if shipment else None,
    })

    return {
        'steps': steps,
        'inquiry': inquiry,
        'angebot': angebot,
        'order': order,
        'customer_name': customer_name,
        'token': token,
    }


@tracking_bp.route('/<token>')
def unified_status(token):
    """Einheitliche Tracking-Seite für den kompletten Workflow"""
    flow = _build_workflow_timeline(token)

    if not flow:
        flash('Vorgang nicht gefunden.', 'danger')
        return redirect(url_for('inquiry.status_lookup'))

    return render_template('tracking/status.html',
                         flow=flow,
                         company=_get_company(),
                         cart_count=0)


@tracking_bp.route('/', methods=['GET', 'POST'])
def lookup():
    """Status-Lookup per Nummer, Token oder E-Mail"""
    if request.method == 'POST':
        search = request.form.get('search', '').strip()
        if not search:
            flash('Bitte geben Sie Ihre Vorgangsnummer oder E-Mail ein.', 'warning')
        elif '@' in search:
            # E-Mail-Suche
            inquiries = find_inquiries_by_email(search)
            if inquiries:
                # Zum neuesten weiterleiten
                return redirect(url_for('tracking.unified_status', token=inquiries[0].tracking_token))
            flash('Keine Vorgänge zu dieser E-Mail gefunden.', 'info')
        else:
            # Anfragen-Nummer oder Angebots-Nummer suchen
            inquiry = get_inquiry_by_number(search.upper())
            if inquiry:
                return redirect(url_for('tracking.unified_status', token=inquiry.tracking_token))
            # Angebotsnummer suchen
            from src.models.angebot import Angebot
            angebot = Angebot.query.filter_by(angebotsnummer=search.upper()).first()
            if angebot and angebot.tracking_token:
                return redirect(url_for('tracking.unified_status', token=angebot.tracking_token))
            flash('Kein Vorgang mit dieser Nummer gefunden.', 'info')

    return render_template('tracking/lookup.html',
                         company=_get_company(),
                         cart_count=0)
