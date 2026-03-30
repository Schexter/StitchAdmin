# -*- coding: utf-8 -*-
"""
Angebote-Controller
==================

Erstellt von: StitchAdmin
Zweck: Angebots-Verwaltung mit CRM-Tracking
"""

import json
import os
import shutil
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import func, and_, or_
from werkzeug.utils import secure_filename
from src.models import db
from src.models.models import Order, Customer, Article
from src.models.angebot import Angebot, AngebotStatus, AngebotsPosition
from src.models.textbaustein import Textbaustein, TEXTBAUSTEIN_CATEGORIES
from src.models.crm_activities import AngebotTracking, Activity, ActivityType
from src.models.veredelung import VeredelungsVerfahren

angebote_bp = Blueprint('angebote', __name__, url_prefix='/angebote')

import logging
logger = logging.getLogger(__name__)


def _save_design_fields(angebot):
    """Design-Status und Kosten aus Formular speichern"""
    angebot.design_status = request.form.get('design_status', '')
    dk = request.form.get('design_kosten', '0').replace(',', '.')
    angebot.design_kosten = float(dk) if dk else 0.0
    dak = request.form.get('design_anpassung_kosten', '0').replace(',', '.')
    angebot.design_anpassung_kosten = float(dak) if dak else 0.0
    angebot.design_anforderungen = request.form.get('design_anforderungen', '')
    angebot.design_anpassung_details = request.form.get('design_anpassung', '')


def _create_positionen_from_form(angebot):
    """Erstellt AngebotsPosition-Eintraege aus Formular-Arrays"""
    article_ids = request.form.getlist('article_id[]')
    quantities = request.form.getlist('quantity[]')
    prices = request.form.getlist('article_price[]')
    textilarten = request.form.getlist('textilart[]')
    sizes = request.form.getlist('size[]')
    colors = request.form.getlist('color[]')

    auftragstyp = angebot.auftragstyp or 'embroidery'
    type_labels = {
        'embroidery': 'Stickerei', 'printing': 'Textildruck',
        'dtf': 'DTF', 'sublimation': 'Sublimation', 'combined': 'Kombiniert'
    }
    v_label = type_labels.get(auftragstyp, auftragstyp)

    # Veredelungs-Details sammeln
    veredlung_details = []
    position_val = request.form.get('position', '') or request.form.get('druck_position', '')
    design_groesse = request.form.get('design_groesse', '')
    stichzahl = request.form.get('stichzahl', '')
    druckverfahren = request.form.get('druckverfahren', '')

    if position_val:
        veredlung_details.append(f"Position: {position_val}")
    if design_groesse:
        veredlung_details.append(f"Groesse: {design_groesse}")
    if stichzahl:
        veredlung_details.append(f"Stichzahl: {stichzahl}")
    if druckverfahren:
        veredlung_details.append(f"Verfahren: {druckverfahren}")

    pos_nr = 0
    artikel_netto_sum = 0.0
    total_qty = 0.0
    max_qty = 0.0  # Maximale Einzelposition-Menge (fuer Veredelung)

    # Kundenware-Menge hat Vorrang
    kw_menge_str = request.form.get('kundenware_menge', '')
    kundenware_qty = float(kw_menge_str) if kw_menge_str else 0.0

    # --- Artikel-Positionen ---
    for i in range(len(quantities)):
        qty_str = quantities[i] if i < len(quantities) else ''
        if not qty_str:
            continue

        qty = float(qty_str or 1)
        total_qty += qty
        if qty > max_qty:
            max_qty = qty
        price_str = prices[i] if i < len(prices) else '0'
        price = float(price_str) if price_str else 0.0

        art_id = article_ids[i] if i < len(article_ids) else ''
        textilart = textilarten[i] if i < len(textilarten) else ''
        size = sizes[i] if i < len(sizes) else ''
        color = colors[i] if i < len(colors) else ''

        # Artikel-Name bestimmen
        artikel_name = textilart
        article = None
        if art_id:
            article = Article.query.get(art_id)
            if article:
                artikel_name = article.name or textilart

        if not artikel_name:
            artikel_name = f"Artikel {i + 1}"

        # Beschreibung: nur Artikel-Details (keine Veredelung)
        beschr_parts = []
        if article and article.article_number:
            beschr_parts.append(f"Art.-Nr.: {article.article_number}")
        if size:
            beschr_parts.append(f"Groesse: {size}")
        if color:
            beschr_parts.append(f"Farbe: {color}")

        pos_nr += 1
        pos = AngebotsPosition(
            angebot_id=angebot.id,
            position=pos_nr,
            artikel_id=art_id if art_id else None,
            artikel_name=artikel_name,
            beschreibung=" | ".join(beschr_parts) if beschr_parts else '',
            menge=qty,
            einheit='Stk.',
            einzelpreis=price,
            mwst_satz=19.0
        )
        pos.calculate_amounts()
        db.session.add(pos)
        artikel_netto_sum += pos.netto_betrag or (qty * price)

    # --- Veredelungs-Positionen (neu: pro Design-Position) ---
    v_verfahren_ids = request.form.getlist('v_verfahren_id[]')
    v_design_positions = request.form.getlist('v_design_position[]')
    v_design_labels = request.form.getlist('v_design_label[]')
    v_stichzahlen = request.form.getlist('v_stichzahl[]')
    v_breiten = request.form.getlist('v_breite_mm[]')
    v_hoehen = request.form.getlist('v_hoehe_mm[]')
    v_stueckpreise = request.form.getlist('v_stueckpreis[]')
    v_einrichtungen = request.form.getlist('v_einrichtung[]')
    v_file_paths = request.form.getlist('v_file_path[]')
    v_thumb_paths = request.form.getlist('v_thumb_path[]')
    v_fadenfarben_list = request.form.getlist('v_fadenfarben[]')

    veredlung_netto_sum = 0.0

    if v_verfahren_ids:
        for i in range(len(v_verfahren_ids)):
            vid = v_verfahren_ids[i] if i < len(v_verfahren_ids) else ''
            if not vid:
                continue

            verfahren = VeredelungsVerfahren.query.get(int(vid))
            if not verfahren:
                continue

            d_pos = v_design_positions[i] if i < len(v_design_positions) else ''
            d_label = v_design_labels[i] if i < len(v_design_labels) else ''
            stich = int(v_stichzahlen[i]) if i < len(v_stichzahlen) and v_stichzahlen[i] else None
            breite = float(v_breiten[i]) if i < len(v_breiten) and v_breiten[i] else None
            hoehe = float(v_hoehen[i]) if i < len(v_hoehen) and v_hoehen[i] else None
            stueckpreis = float(v_stueckpreise[i]) if i < len(v_stueckpreise) and v_stueckpreise[i] else 0.0
            einrichtung = float(v_einrichtungen[i]) if i < len(v_einrichtungen) and v_einrichtungen[i] else 0.0
            file_path = v_file_paths[i] if i < len(v_file_paths) else ''
            thumb_path = v_thumb_paths[i] if i < len(v_thumb_paths) else ''
            fadenfarben = v_fadenfarben_list[i] if i < len(v_fadenfarben_list) else '[]'

            # Beschreibung zusammenbauen
            beschr_parts = []
            if stich:
                beschr_parts.append(f"Stichzahl: {stich:,}".replace(',', '.'))
            if breite and hoehe:
                beschr_parts.append(f"Groesse: {breite:.0f}x{hoehe:.0f}mm")

            pos_nr += 1
            v_pos = AngebotsPosition(
                angebot_id=angebot.id,
                position=pos_nr,
                is_veredelung=True,
                veredelung_verfahren_id=int(vid),
                design_position=d_pos,
                design_position_label=d_label or d_pos,
                stichzahl=stich,
                design_breite_mm=breite,
                design_hoehe_mm=hoehe,
                fadenfarben=fadenfarben,
                design_file_path=file_path,
                design_thumbnail_path=thumb_path,
                einrichtungskosten=einrichtung,
                artikel_name=f"Veredelung: {verfahren.name} – {d_label or d_pos or 'Position'}",
                beschreibung=" | ".join(beschr_parts) if beschr_parts else '',
                menge=kundenware_qty if kundenware_qty > 0 else (max_qty if max_qty > 0 else 1),
                einheit='Stk.',
                einzelpreis=stueckpreis,
                mwst_satz=19.0
            )
            v_pos.calculate_amounts()
            db.session.add(v_pos)
            veredlung_netto_sum += (v_pos.netto_betrag or 0) + einrichtung
    else:
        # Fallback: alte Methode (einfacher Veredelungspreis)
        veredlung_preis_str = request.form.get('veredlung_preis', '') or '0'
        veredlung_preis = float(veredlung_preis_str) if veredlung_preis_str else 0.0

        preis_schaetzung_str = request.form.get('preis_schaetzung', '')
        if veredlung_preis == 0 and preis_schaetzung_str and total_qty > 0:
            try:
                gesamt = float(preis_schaetzung_str)
                diff = gesamt - artikel_netto_sum
                if diff > 0:
                    veredlung_preis = round(diff / total_qty, 2)
            except (ValueError, ZeroDivisionError):
                pass

        v_qty = kundenware_qty if kundenware_qty > 0 else (max_qty if max_qty > 0 else total_qty)
        if v_qty > 0 and veredlung_preis > 0:
            pos_nr += 1
            v_beschr = " | ".join(veredlung_details) if veredlung_details else ''
            v_pos = AngebotsPosition(
                angebot_id=angebot.id,
                position=pos_nr,
                artikel_name=f"Veredelung ({v_label})",
                beschreibung=v_beschr,
                menge=v_qty,
                einheit='Stk.',
                einzelpreis=veredlung_preis,
                mwst_satz=19.0
            )
            v_pos.calculate_amounts()
            db.session.add(v_pos)
            veredlung_netto_sum = v_pos.netto_betrag or (v_qty * veredlung_preis)

    # Betraege aus Positionen berechnen (inkl. Designkosten)
    preis_schaetzung_str = request.form.get('preis_schaetzung', '')
    dk_str = request.form.get('design_kosten', '0').replace(',', '.')
    dak_str = request.form.get('design_anpassung_kosten', '0').replace(',', '.')
    design_kosten_sum = (float(dk_str) if dk_str else 0) + (float(dak_str) if dak_str else 0)
    netto_sum = artikel_netto_sum + veredlung_netto_sum + design_kosten_sum
    if netto_sum > 0:
        angebot.netto_gesamt = netto_sum
        mwst = netto_sum * 0.19
        try:
            from src.models.company_settings import CompanySettings
            company = CompanySettings.get_settings()
            if company and company.small_business:
                mwst = 0.0
        except Exception:
            pass
        angebot.mwst_gesamt = mwst
        angebot.brutto_gesamt = netto_sum + mwst
    elif preis_schaetzung_str:
        angebot.netto_gesamt = float(preis_schaetzung_str)
        angebot.brutto_gesamt = float(preis_schaetzung_str)


@angebote_bp.route('/')
@login_required
def index():
    """Angebots-Übersicht"""

    # Filter-Parameter
    status_filter = request.args.get('status', 'alle')
    kunde_filter = request.args.get('kunde', '')
    sortierung = request.args.get('sort', 'datum')  # datum, nummer, kunde

    query = Angebot.query

    # Status filtern
    if status_filter != 'alle':
        query = query.filter_by(status=status_filter)

    # Kunde filtern
    if kunde_filter:
        query = query.filter(
            or_(
                Angebot.kunde_name.ilike(f'%{kunde_filter}%'),
                Angebot.angebotsnummer.ilike(f'%{kunde_filter}%')
            )
        )

    # Sortierung
    if sortierung == 'nummer':
        query = query.order_by(Angebot.angebotsnummer.desc())
    elif sortierung == 'kunde':
        query = query.order_by(Angebot.kunde_name)
    else:  # datum
        query = query.order_by(Angebot.angebotsdatum.desc())

    angebote = query.all()

    # Statistiken (1 Query statt 6)
    status_counts = db.session.query(
        Angebot.status, func.count(Angebot.id)
    ).group_by(Angebot.status).all()
    count_map = {str(s): c for s, c in status_counts}
    stats = {
        'gesamt': sum(count_map.values()),
        'entwurf': count_map.get(str(AngebotStatus.ENTWURF), 0),
        'verschickt': count_map.get(str(AngebotStatus.VERSCHICKT), 0),
        'angenommen': count_map.get(str(AngebotStatus.ANGENOMMEN), 0),
        'abgelehnt': count_map.get(str(AngebotStatus.ABGELEHNT), 0),
        'abgelaufen': count_map.get(str(AngebotStatus.ABGELAUFEN), 0),
    }

    # Angebote mit Follow-up
    heute = date.today()
    follow_up_needed = AngebotTracking.query.filter(
        or_(
            AngebotTracking.naechster_kontakt_geplant <= heute,
            and_(
                AngebotTracking.letzter_kontakt.isnot(None),
                AngebotTracking.naechster_kontakt_geplant.is_(None)
            )
        )
    ).all()

    return render_template('angebote/index.html',
                         angebote=angebote,
                         stats=stats,
                         follow_up_needed=follow_up_needed,
                         status_filter=status_filter,
                         kunde_filter=kunde_filter,
                         sortierung=sortierung)


@angebote_bp.route('/<int:angebot_id>')
@login_required
def show(angebot_id):
    """Angebots-Details anzeigen"""

    angebot = Angebot.query.get_or_404(angebot_id)

    # Hole Tracking-Daten falls vorhanden
    tracking = AngebotTracking.query.filter_by(angebot_id=angebot_id).first()

    # Hole alle Aktivitäten zu diesem Angebot
    aktivitaeten = Activity.query.filter_by(angebot_id=angebot_id).order_by(Activity.created_at.desc()).all()

    return render_template('angebote/show.html',
                         angebot=angebot,
                         tracking=tracking,
                         aktivitaeten=aktivitaeten)


@angebote_bp.route('/wizard', methods=['GET', 'POST'])
@login_required
def wizard():
    """Angebots-Wizard: 4 Steps (Kunde -> Positionen -> Veredelung -> Kalkulation)"""

    if request.method == 'POST':
        # Angebot speichern - gleiche Logik wie neu()
        return _save_new_angebot()

    # Kunden laden
    kunden = Customer.query.filter_by(is_active=True).order_by(
        Customer.company_name, Customer.last_name
    ).all()

    # Veredelungsverfahren laden
    veredelungsverfahren = []
    try:
        veredelungsverfahren = VeredelungsVerfahren.query.filter_by(aktiv=True).order_by(
            VeredelungsVerfahren.sort_order
        ).all()
    except Exception:
        pass

    # Anfrage-ID oder Kunden-ID aus URL
    kunde_id = request.args.get('kunde_id')
    anfrage_id = request.args.get('anfrage_id')
    anfrage = None
    if anfrage_id:
        try:
            from src.models.inquiry import Inquiry
            anfrage = Inquiry.query.get(anfrage_id)
        except Exception:
            pass

    return render_template('angebote/wizard.html',
                         kunden=kunden,
                         veredelungsverfahren=veredelungsverfahren,
                         anfrage=anfrage,
                         preselected_kunde_id=kunde_id)


@angebote_bp.route('/neu', methods=['GET', 'POST'])
@login_required
def neu():
    """Neues Angebot erstellen"""

    if request.method == 'GET':
        # Hole Auftrag-ID, Anfrage-ID oder Kunden-ID falls vorhanden
        auftrag_id = request.args.get('auftrag_id')
        anfrage_id = request.args.get('anfrage_id')
        vorselektierter_kunde = request.args.get('kunde_id', '')
        auftrag = None
        anfrage = None

        if auftrag_id:
            auftrag = Order.query.get_or_404(auftrag_id)
        if anfrage_id:
            from src.models.inquiry import Inquiry
            anfrage = Inquiry.query.get_or_404(anfrage_id)

        # Hole alle Kunden und Artikel für Dropdowns
        kunden = Customer.query.order_by(Customer.company_name, Customer.last_name).all()
        articles_list = Article.query.filter_by(active=True).order_by(Article.name).all()
        articles = {a.id: a for a in articles_list}

        # Textbausteine laden
        textbausteine = Textbaustein.get_active()
        default_ids = [str(tb.id) for tb in Textbaustein.get_defaults()]

        return render_template('angebote/neu.html',
                             auftrag=auftrag,
                             anfrage=anfrage,
                             kunden=kunden,
                             articles=articles,
                             vorselektierter_kunde=vorselektierter_kunde,
                             textbausteine=textbausteine,
                             textbaustein_kategorien=TEXTBAUSTEIN_CATEGORIES,
                             default_textbaustein_ids=default_ids)

    # POST: Angebot erstellen
    try:
        auftrag_id = request.form.get('auftrag_id')
        anfrage_id = request.form.get('anfrage_id')

        # Gemeinsame Felder aus dem Formular
        auftragstyp = request.form.get('auftragstyp', 'embroidery')
        is_kundenware = request.form.get('is_kundenware', False) == 'on'
        lieferzeit = request.form.get('lieferzeit', '')
        bemerkungen = request.form.get('bemerkungen', '')
        versandkosten_str = request.form.get('versandkosten', '0').replace(',', '.')
        versandkosten = float(versandkosten_str) if versandkosten_str else 0.0
        menge = request.form.get('menge', '')
        preis_schaetzung = request.form.get('preis_schaetzung', '')

        # Design-Details in Beschreibung zusammenbauen
        beschreibung = request.form.get('beschreibung', '')
        position = request.form.get('position', '')
        design_groesse = request.form.get('design_groesse', '')
        stichzahl = request.form.get('stichzahl', '')
        druckverfahren = request.form.get('druckverfahren', '')
        textilart = request.form.get('textilart', '')
        besondere_anweisungen = request.form.get('besondere_anweisungen', '')

        # Zusatz-Infos an Beschreibung anhängen
        details = []
        if menge:
            details.append(f"Menge: {menge} Stück")
        if textilart:
            details.append(f"Textilart: {textilart}")
        if position:
            details.append(f"Position: {position}")
        if design_groesse:
            details.append(f"Größe: {design_groesse}")
        if stichzahl:
            details.append(f"Stichzahl: {stichzahl}")
        if druckverfahren:
            details.append(f"Druckverfahren: {druckverfahren}")
        if besondere_anweisungen:
            details.append(f"Besondere Anweisungen: {besondere_anweisungen}")
        if details:
            beschreibung = beschreibung.rstrip() + '\n\n' + '\n'.join(details) if beschreibung else '\n'.join(details)

        # Textbausteine verarbeiten
        selected_tb_ids = request.form.getlist('textbausteine')
        textbausteine_text = ''
        if selected_tb_ids:
            tbs = Textbaustein.query.filter(Textbaustein.id.in_([int(i) for i in selected_tb_ids])).order_by(Textbaustein.sort_order).all()
            textbausteine_text = '\n\n'.join([f'{tb.titel}:\n{tb.inhalt}' for tb in tbs])

        if anfrage_id:
            # Aus Anfrage erstellen
            from src.models.inquiry import Inquiry
            anfrage = Inquiry.query.get_or_404(anfrage_id)

            angebot = Angebot.von_anfrage_erstellen(
                anfrage=anfrage,
                created_by=current_user.username,
                gueltig_tage=int(request.form.get('gueltig_tage', 30))
            )
            angebot.auftragstyp = auftragstyp
            angebot.is_kundenware = is_kundenware
            _save_design_fields(angebot)
            angebot.titel = request.form.get('titel', '') or angebot.titel
            angebot.beschreibung = beschreibung or angebot.beschreibung
            angebot.bemerkungen = bemerkungen
            angebot.lieferzeit = lieferzeit
            angebot.textbausteine_ids = ','.join(selected_tb_ids)
            angebot.textbausteine_text = textbausteine_text
            if preis_schaetzung:
                angebot.netto_gesamt = float(preis_schaetzung)
                angebot.brutto_gesamt = float(preis_schaetzung)

            flash(f'Angebot {angebot.angebotsnummer} aus Anfrage {anfrage.inquiry_number} erstellt.', 'success')

        elif auftrag_id:
            # Aus Auftrag erstellen
            auftrag = Order.query.get_or_404(auftrag_id)

            angebot = Angebot.von_auftrag_erstellen(
                auftrag=auftrag,
                created_by=current_user.username,
                gueltig_tage=int(request.form.get('gueltig_tage', 30))
            )
            angebot.auftragstyp = auftragstyp
            angebot.is_kundenware = is_kundenware
            _save_design_fields(angebot)
            angebot.titel = request.form.get('titel', '') or angebot.titel
            angebot.beschreibung = beschreibung or angebot.beschreibung
            angebot.bemerkungen = bemerkungen
            angebot.lieferzeit = lieferzeit
            angebot.textbausteine_ids = ','.join(selected_tb_ids)
            angebot.textbausteine_text = textbausteine_text

            flash(f'Angebot {angebot.angebotsnummer} aus Auftrag {auftrag.id} erstellt.', 'success')
        else:
            # Neues Angebot ohne Auftrag
            kunde = Customer.query.get_or_404(request.form.get('kunde_id'))

            # Kundenadresse zusammenbauen
            adresse_teile = []
            if kunde.customer_type == 'business' and kunde.first_name:
                adresse_teile.append(f"{kunde.first_name} {kunde.last_name or ''}".strip())
            street = f"{kunde.street or ''} {kunde.house_number or ''}".strip()
            if street:
                adresse_teile.append(street)
            city = f"{kunde.postal_code or ''} {kunde.city or ''}".strip()
            if city:
                adresse_teile.append(city)

            angebot = Angebot(
                kunde_id=kunde.id,
                kunde_name=kunde.display_name,
                kunde_adresse='\n'.join(adresse_teile),
                kunde_email=kunde.email,
                titel=request.form.get('titel', ''),
                beschreibung=beschreibung,
                bemerkungen=bemerkungen,
                gueltig_tage=int(request.form.get('gueltig_tage', 30)),
                auftragstyp=auftragstyp,
                is_kundenware=is_kundenware,
                lieferzeit=lieferzeit,
                textbausteine_ids=','.join(selected_tb_ids),
                textbausteine_text=textbausteine_text,
                created_by=current_user.username
            )
            if preis_schaetzung:
                angebot.netto_gesamt = float(preis_schaetzung)
                angebot.brutto_gesamt = float(preis_schaetzung)

            angebot.versandkosten = versandkosten

            db.session.add(angebot)
            db.session.flush()

            flash(f'Angebot {angebot.angebotsnummer} erstellt.', 'success')

        # Positionen aus Formular-Arrays erstellen
        _create_positionen_from_form(angebot)

        db.session.commit()
        return redirect(url_for('angebote.show', angebot_id=angebot.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Erstellen des Angebots: {str(e)}', 'danger')
        return redirect(url_for('angebote.index'))


@angebote_bp.route('/<int:angebot_id>/bearbeiten', methods=['GET', 'POST'])
@login_required
def bearbeiten(angebot_id):
    """Angebot bearbeiten"""

    angebot = Angebot.query.get_or_404(angebot_id)

    # Nur Entwürfe können bearbeitet werden
    if angebot.status != AngebotStatus.ENTWURF:
        flash('Nur Angebots-Entwürfe können bearbeitet werden.', 'warning')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))

    if request.method == 'GET':
        kunden = Customer.query.order_by(Customer.company_name, Customer.last_name).all()
        articles_list = Article.query.filter_by(active=True).order_by(Article.name).all()
        articles = {a.id: a for a in articles_list}

        # Textbausteine laden
        textbausteine = Textbaustein.get_active()
        # Bereits ausgewaehlte IDs aus dem Angebot
        selected_ids = [s.strip() for s in (angebot.textbausteine_ids or '').split(',') if s.strip()]

        # Veredelungsverfahren laden
        veredelungsverfahren = []
        try:
            veredelungsverfahren = VeredelungsVerfahren.query.filter_by(aktiv=True).order_by(
                VeredelungsVerfahren.sort_order
            ).all()
        except Exception:
            pass

        # Positionen aufteilen: Artikel vs. Veredelung
        artikel_positionen = []
        veredelungs_positionen = []
        for pos in angebot.positionen:
            if pos.is_veredelung:
                veredelungs_positionen.append(pos)
            else:
                artikel_positionen.append(pos)

        # Edit-Daten als JSON fuer JS-Vorbelegung
        edit_data = {
            'kunde_id': angebot.kunde_id,
            'kunde_name': angebot.kunde_name,
            'auftragstyp': angebot.auftragstyp or 'embroidery',
            'is_kundenware': bool(angebot.is_kundenware),
            'design_status': angebot.design_status or '',
            'design_kosten': float(angebot.design_kosten or 0),
            'design_anpassung_kosten': float(angebot.design_anpassung_kosten or 0),
            'design_anforderungen': angebot.design_anforderungen or '',
            'design_anpassung_details': angebot.design_anpassung_details or '',
            'titel': angebot.titel or '',
            'beschreibung': angebot.beschreibung or '',
            'bemerkungen': angebot.bemerkungen or '',
            'lieferzeit': angebot.lieferzeit or '',
            'gueltig_tage': angebot.gueltig_tage or 30,
            'versandkosten': float(angebot.versandkosten or 0),
            'netto_gesamt': float(angebot.netto_gesamt or 0),
            'artikel_positionen': [{
                'artikel_id': p.artikel_id or '',
                'artikel_name': p.artikel_name or '',
                'beschreibung': p.beschreibung or '',
                'menge': int(p.menge) if p.menge else 1,
                'einzelpreis': float(p.einzelpreis or 0),
                'rabatt_prozent': float(p.rabatt_prozent or 0),
            } for p in artikel_positionen],
            'veredelungs_positionen': [{
                'verfahren_id': p.veredelung_verfahren_id or '',
                'design_position': p.design_position or '',
                'design_label': p.design_position_label or '',
                'stichzahl': p.stichzahl or '',
                'breite_mm': float(p.design_breite_mm or 0),
                'hoehe_mm': float(p.design_hoehe_mm or 0),
                'stueckpreis': float(p.einzelpreis or 0),
                'einrichtung': float(p.einrichtungskosten or 0),
                'fadenfarben': p.fadenfarben or '[]',
            } for p in veredelungs_positionen],
        }

        return render_template('angebote/neu.html',
                             edit_mode=True,
                             angebot=angebot,
                             edit_data=edit_data,
                             kunden=kunden,
                             articles=articles,
                             veredelungsverfahren=veredelungsverfahren,
                             textbausteine=textbausteine,
                             textbaustein_kategorien=TEXTBAUSTEIN_CATEGORIES,
                             default_textbaustein_ids=selected_ids,
                             anfrage=None,
                             auftrag=None,
                             vorselektierter_kunde=angebot.kunde_id)

    # POST: Änderungen speichern
    try:
        angebot.titel = request.form.get('titel', '')
        angebot.beschreibung = request.form.get('beschreibung', '')
        angebot.bemerkungen = request.form.get('bemerkungen', '')
        angebot.gueltig_tage = int(request.form.get('gueltig_tage', 30))
        angebot.auftragstyp = request.form.get('auftragstyp', angebot.auftragstyp or 'embroidery')
        angebot.is_kundenware = request.form.get('is_kundenware', False) == 'on'
        _save_design_fields(angebot)
        angebot.lieferzeit = request.form.get('lieferzeit', '')

        # Versandkosten
        vk_str = request.form.get('versandkosten', '0').replace(',', '.')
        angebot.versandkosten = float(vk_str) if vk_str else 0.0

        # Preis aktualisieren
        preis_schaetzung = request.form.get('preis_schaetzung', '')
        if preis_schaetzung:
            angebot.netto_gesamt = float(preis_schaetzung)
            angebot.brutto_gesamt = float(preis_schaetzung)

        # Textbausteine verarbeiten
        selected_tb_ids = request.form.getlist('textbausteine')
        textbausteine_text = ''
        if selected_tb_ids:
            tbs = Textbaustein.query.filter(Textbaustein.id.in_([int(i) for i in selected_tb_ids])).order_by(Textbaustein.sort_order).all()
            textbausteine_text = '\n\n'.join([f'{tb.titel}:\n{tb.inhalt}' for tb in tbs])
        angebot.textbausteine_ids = ','.join(selected_tb_ids)
        angebot.textbausteine_text = textbausteine_text

        angebot.updated_by = current_user.username
        angebot.updated_at = datetime.utcnow()

        # Alte Positionen loeschen und neu erstellen
        # Gleiche Logik wie beim Erstellen (neu.html Formular)
        AngebotsPosition.query.filter_by(angebot_id=angebot.id).delete()
        db.session.flush()
        _create_positionen_from_form(angebot)

        db.session.commit()
        flash(f'Angebot {angebot.angebotsnummer} aktualisiert.', 'success')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Aktualisieren: {str(e)}', 'danger')
        return redirect(url_for('angebote.bearbeiten', angebot_id=angebot_id))


@angebote_bp.route('/<int:angebot_id>/versenden', methods=['POST'])
@login_required
def versenden(angebot_id):
    """Angebot versenden und Tracking aktivieren"""

    angebot = Angebot.query.get_or_404(angebot_id)

    if angebot.status != AngebotStatus.ENTWURF:
        flash('Angebot wurde bereits versendet.', 'warning')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))

    try:
        # Follow-up Tage aus Form
        follow_up_tage = int(request.form.get('follow_up_tage', 7))
        verkaufschance = int(request.form.get('verkaufschance', 50))

        # Angebot versenden mit Tracking
        tracking = angebot.versenden_und_tracken(
            created_by=current_user.username,
            naechster_kontakt_tage=follow_up_tage
        )

        # Verkaufschance setzen
        tracking.verkaufschance_prozent = verkaufschance

        db.session.commit()

        flash(f'Angebot {angebot.angebotsnummer} versendet. Nächster Follow-up in {follow_up_tage} Tagen.', 'success')

        # TODO: PDF generieren und per E-Mail versenden

        return redirect(url_for('angebote.show', angebot_id=angebot_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Versenden: {str(e)}', 'danger')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))


@angebote_bp.route('/<int:angebot_id>/annehmen', methods=['POST'])
@login_required
def annehmen(angebot_id):
    """Angebot als angenommen markieren"""

    angebot = Angebot.query.get_or_404(angebot_id)

    try:
        angebot.annehmen(created_by=current_user.username)
        db.session.commit()

        flash(f'Angebot {angebot.angebotsnummer} wurde angenommen!', 'success')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))


@angebote_bp.route('/<int:angebot_id>/ablehnen', methods=['POST'])
@login_required
def ablehnen(angebot_id):
    """Angebot als abgelehnt markieren"""

    angebot = Angebot.query.get_or_404(angebot_id)

    try:
        grund = request.form.get('grund', '')

        angebot.ablehnen(
            grund=grund,
            created_by=current_user.username
        )

        db.session.commit()

        flash(f'Angebot {angebot.angebotsnummer} wurde abgelehnt.', 'info')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))


@angebote_bp.route('/<int:angebot_id>/direkt-als-auftrag', methods=['POST'])
@login_required
def direkt_als_auftrag(angebot_id):
    """Angebot direkt als Auftrag uebernehmen (telefonische Zusage etc.)"""
    from src.services.id_generator_service import IdGenerator
    generate_order_id = IdGenerator.order
    from src.models.models import OrderItem

    angebot = Angebot.query.get_or_404(angebot_id)

    try:
        # Angebot als angenommen markieren
        zusage_grund = request.form.get('zusage_grund', 'telefon')
        zusage_notiz = request.form.get('zusage_notiz', '')
        grund_labels = {
            'telefon': 'Telefonische Zusage',
            'email': 'E-Mail Bestaetigung',
            'persoenlich': 'Persoenliche Absprache',
            'stammkunde': 'Stammkunde',
            'sonstiges': 'Sonstiges'
        }
        angebot.status = AngebotStatus.ANGENOMMEN
        angebot.bemerkungen = (angebot.bemerkungen or '') + f'\n[{datetime.now().strftime("%d.%m.%Y %H:%M")}] {grund_labels.get(zusage_grund, zusage_grund)}: {zusage_notiz}'.strip()
        angebot.updated_by = current_user.username

        # Split oder einzelner Auftrag?
        split = request.form.get('split_auftraege') == 'on'
        split_typen = request.form.getlist('split_typ') if split else [angebot.auftragstyp or 'embroidery']

        created_orders = []
        for auftrag_typ in split_typen:
            order_id = generate_order_id()
            order = Order(
                id=order_id,
                customer_id=angebot.kunde_id,
                order_type=auftrag_typ if auftrag_typ != 'design' else angebot.auftragstyp,
                auftrag_typ=auftrag_typ,
                angebot_id=angebot.id,
                status='new',
                description=angebot.beschreibung or angebot.titel or '',
                is_kundenware=angebot.is_kundenware or False,
                total_price=float(angebot.netto_gesamt or 0) if len(split_typen) == 1 else 0,
                created_by=current_user.username,
            )

            if angebot.lieferzeit:
                try:
                    tage = int(''.join(c for c in angebot.lieferzeit if c.isdigit())[:3])
                    order.due_date = datetime.now() + timedelta(days=tage)
                except (ValueError, TypeError):
                    pass

            db.session.add(order)

            # Artikel-Positionen uebernehmen (nur bei Produktions-Auftraegen)
            if auftrag_typ not in ('design', 'shipping'):
                for pos in angebot.positionen:
                    if not pos.is_veredelung:
                        item = OrderItem(
                            order_id=order_id,
                            article_id=pos.artikel_id,
                            quantity=int(pos.menge or 1),
                            unit_price=float(pos.einzelpreis or 0),
                        )
                        db.session.add(item)

            # Design/Veredelungs-Positionen uebernehmen -> order_designs
            from src.models.order_workflow import OrderDesign
            design_total = 0
            for pos in angebot.positionen:
                if pos.is_veredelung:
                    od = OrderDesign(
                        order_id=order_id,
                        position=pos.design_position or f"pos_{pos.position}",
                        position_label=pos.design_position_label or pos.artikel_name or '',
                        design_type=auftrag_typ if auftrag_typ in ('embroidery', 'printing', 'dtf') else 'embroidery',
                        stitch_count=pos.stichzahl,
                        width_mm=float(pos.design_breite_mm) if pos.design_breite_mm else None,
                        height_mm=float(pos.design_hoehe_mm) if pos.design_hoehe_mm else None,
                        setup_price=float(pos.einrichtungskosten or 0),
                        price_per_piece=float(pos.einzelpreis or 0),
                        sort_order=pos.position,
                        created_by=current_user.username,
                    )
                    db.session.add(od)
                    # Design-Kosten summieren
                    menge = max(int(m.menge or 0) for m in angebot.positionen if not m.is_veredelung) if any(not p.is_veredelung for p in angebot.positionen) else int(pos.menge or 1)
                    design_total += (float(pos.einzelpreis or 0) * menge) + float(pos.einrichtungskosten or 0)

            # Design-Kosten am Auftrag setzen
            if design_total > 0:
                order.design_cost = design_total

            # Design-Status vom Angebot uebernehmen
            if angebot.design_status:
                order.design_status = angebot.design_status

            created_orders.append(order)

        # Angebot mit erstem Auftrag verknuepfen
        if created_orders:
            angebot.auftrag_id = created_orders[0].id
            angebot.in_auftrag_umgewandelt_am = datetime.utcnow()

        db.session.commit()

        if len(created_orders) == 1:
            flash(f'Auftrag {created_orders[0].id} aus Angebot {angebot.angebotsnummer} erstellt ({grund_labels.get(zusage_grund, "")}).', 'success')
            return redirect(url_for('orders.show', order_id=created_orders[0].id))
        else:
            nummern = ', '.join(o.id for o in created_orders)
            flash(f'{len(created_orders)} Auftraege erstellt: {nummern}', 'success')
            return redirect(url_for('orders.index'))

    except Exception as e:
        db.session.rollback()
        logger.error(f"Direkt-Auftrag Fehler: {e}")
        flash(f'Fehler: {str(e)}', 'danger')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))


@angebote_bp.route('/<int:angebot_id>/in-auftrag-umwandeln', methods=['POST'])
@login_required
def in_auftrag_umwandeln(angebot_id):
    """Angebot in Produktionsauftrag umwandeln"""

    angebot = Angebot.query.get_or_404(angebot_id)

    if angebot.status != AngebotStatus.ANGENOMMEN:
        flash('Nur angenommene Angebote können in Aufträge umgewandelt werden.', 'warning')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))

    try:
        auftrag = angebot.in_auftrag_umwandeln(created_by=current_user.username)
        db.session.commit()

        flash(f'Angebot {angebot.angebotsnummer} in Auftrag {auftrag.id} umgewandelt!', 'success')
        return redirect(url_for('orders.view_order', order_id=auftrag.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Fehler bei der Umwandlung: {str(e)}', 'danger')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))


@angebote_bp.route('/<int:angebot_id>/kontakt', methods=['POST'])
@login_required
def kontakt_durchgefuehrt(angebot_id):
    """Registriere einen durchgeführten Kontakt (Follow-up)"""

    angebot = Angebot.query.get_or_404(angebot_id)
    tracking = AngebotTracking.query.filter_by(angebot_id=angebot_id).first()

    if not tracking:
        flash('Kein Tracking für dieses Angebot gefunden.', 'warning')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))

    try:
        ergebnis = request.form.get('ergebnis', '')
        verkaufschance = request.form.get('verkaufschance', None)
        naechster_kontakt_tage = request.form.get('naechster_kontakt_tage', None)

        # Kontakt registrieren
        tracking.kontakt_durchgefuehrt(
            ergebnis=ergebnis,
            created_by=current_user.username
        )

        # Verkaufschance aktualisieren
        if verkaufschance:
            tracking.verkaufschance_aktualisieren(
                prozent=int(verkaufschance),
                begruendung=ergebnis
            )

        # Nächsten Kontakt planen
        if naechster_kontakt_tage:
            tracking.naechsten_kontakt_planen(
                tage_bis_kontakt=int(naechster_kontakt_tage)
            )

        db.session.commit()

        flash(f'Kontakt für Angebot {angebot.angebotsnummer} registriert.', 'success')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))


@angebote_bp.route('/<int:angebot_id>/loeschen', methods=['POST'])
@login_required
def loeschen(angebot_id):
    """Angebot löschen"""

    if not current_user.is_admin:
        flash('Nur Administratoren können Angebote löschen.', 'danger')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))

    angebot = Angebot.query.get_or_404(angebot_id)

    # Nur Entwürfe können gelöscht werden
    if angebot.status != AngebotStatus.ENTWURF:
        flash('Nur Angebots-Entwürfe können gelöscht werden.', 'warning')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))

    try:
        nummer = angebot.angebotsnummer
        db.session.delete(angebot)
        db.session.commit()

        flash(f'Angebot {nummer} wurde gelöscht.', 'success')
        return redirect(url_for('angebote.index'))

    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Löschen: {str(e)}', 'danger')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))


def _build_angebot_pdf_bytes(angebot, include_signature=False):
    """Erzeugt PDF-Bytes fuer ein Angebot. Mit include_signature=True wird die Kundenunterschrift angehaengt."""
    import io
    import os
    import base64

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from flask import current_app

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=20*mm, leftMargin=20*mm,
                            topMargin=20*mm, bottomMargin=25*mm)

    styles = getSampleStyleSheet()
    style_header = ParagraphStyle('Header', parent=styles['Heading1'], fontSize=18, spaceAfter=10)
    style_normal = ParagraphStyle('Normal2', parent=styles['Normal'], fontSize=10, leading=14)
    style_small = ParagraphStyle('Small', parent=styles['Normal'], fontSize=8, leading=10)

    elements = []

    # --- Firmen-Header ---
    company = None
    try:
        from src.models.company_settings import CompanySettings
        company = CompanySettings.get_settings()
    except Exception:
        pass

    logo_cell = ""
    logo_path_to_use = None
    if company and company.logo_path:
        logo_path_to_use = company.logo_path
    if not logo_path_to_use:
        try:
            from src.models.branding_settings import BrandingSettings
            branding = BrandingSettings.get_settings()
            if branding and branding.logo_path:
                logo_path_to_use = branding.logo_path
        except Exception:
            pass

    if logo_path_to_use:
        try:
            from reportlab.lib.utils import ImageReader
            logo_full = os.path.join(current_app.static_folder, logo_path_to_use)
            if os.path.exists(logo_full):
                img_reader = ImageReader(logo_full)
                iw, ih = img_reader.getSize()
                target_h = 22*mm
                target_w = target_h * (iw / ih) if ih else 50*mm
                if target_w > 60*mm:
                    target_w = 60*mm
                    target_h = target_w * (ih / iw) if iw else 22*mm
                logo_cell = Image(logo_full, width=target_w, height=target_h)
        except Exception:
            pass

    c_name = company.display_name if company else 'Firma'
    if not logo_cell:
        logo_cell = Paragraph(f"<b>{c_name}</b>", style_header)

    c_street = f"{company.street or ''} {company.house_number or ''}".strip() if company else ''
    c_city = f"{company.postal_code or ''} {company.city or ''}".strip() if company else ''
    c_phone = company.phone or '' if company else ''
    c_email = company.email or '' if company else ''

    company_info = f"<b>{c_name}</b><br/>{c_street}<br/>{c_city}<br/>Tel: {c_phone}<br/>{c_email}"

    header_table = Table([[logo_cell, Paragraph(company_info, style_small)]],
                         colWidths=[90*mm, 80*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10*mm))

    absender = f"{c_name} - {c_street} - {c_city}"
    elements.append(Paragraph(f"<u><font size='7'>{absender}</font></u>", style_small))
    elements.append(Spacer(1, 3*mm))

    empfaenger = angebot.kunde_name or ''
    if angebot.kunde_adresse:
        empfaenger += f"<br/>{angebot.kunde_adresse.replace(chr(10), '<br/>')}"
    elements.append(Paragraph(empfaenger, style_normal))
    elements.append(Spacer(1, 12*mm))

    elements.append(Paragraph("<b>ANGEBOT</b>", style_header))
    elements.append(Spacer(1, 5*mm))

    info_data = [
        ['Angebots-Nr.:', angebot.angebotsnummer],
        ['Datum:', angebot.angebotsdatum.strftime('%d.%m.%Y') if angebot.angebotsdatum else '-'],
    ]
    if angebot.gueltig_bis:
        info_data.append(['Gueltig bis:', angebot.gueltig_bis.strftime('%d.%m.%Y')])
    if angebot.titel:
        info_data.append(['Betreff:', angebot.titel])

    info_table = Table(info_data, colWidths=[35*mm, 80*mm])
    info_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ]))
    elements.append(info_table)
    elements.append(Spacer(1, 8*mm))

    # --- Einleitung ---
    if angebot.beschreibung:
        elements.append(Paragraph(angebot.beschreibung, style_normal))
        elements.append(Spacer(1, 5*mm))

    # --- Veredelungstyp anzeigen ---
    type_labels = {
        'embroidery': 'Stickerei', 'printing': 'Textildruck',
        'dtf': 'DTF', 'sublimation': 'Sublimation', 'combined': 'Kombiniert'
    }
    v_label = type_labels.get(angebot.auftragstyp, '')
    if v_label:
        elements.append(Paragraph(f"<b>Veredelung:</b> {v_label}", style_normal))
        elements.append(Spacer(1, 3*mm))

    # --- Positionen ---
    pos_header = ['Pos.', 'Bezeichnung', 'Menge', 'Einheit', 'Einzelpreis', 'Gesamt']
    pos_data = [pos_header]

    if angebot.positionen:
        for pos in angebot.positionen:
            bezeichnung = pos.artikel_name or ''

            if pos.beschreibung:
                bezeichnung += f"\n{pos.beschreibung}"

            pos_data.append([
                str(pos.position),
                Paragraph(bezeichnung.replace('\n', '<br/>'), style_small),
                f"{pos.menge:g}",
                pos.einheit or 'Stk.',
                f"{pos.einzelpreis or 0:,.2f} EUR".replace(',', 'X').replace('.', ',').replace('X', '.'),
                f"{pos.brutto_betrag or 0:,.2f} EUR".replace(',', 'X').replace('.', ',').replace('X', '.'),
            ])
    else:
        # Fallback: Keine Positionen vorhanden, Beschreibung als einzelne Position
        bezeichnung = angebot.beschreibung or angebot.titel or 'Leistung laut Vereinbarung'
        pos_data.append([
            '1',
            Paragraph(bezeichnung.replace('\n', '<br/>'), style_small),
            '1',
            'pauschal',
            f"{angebot.netto_gesamt or 0:,.2f} EUR".replace(',', 'X').replace('.', ',').replace('X', '.'),
            f"{angebot.brutto_gesamt or 0:,.2f} EUR".replace(',', 'X').replace('.', ',').replace('X', '.'),
        ])

    col_widths = [12*mm, 75*mm, 18*mm, 15*mm, 25*mm, 25*mm]
    pos_table = Table(pos_data, colWidths=col_widths, repeatRows=1)
    pos_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
        ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),
    ]))
    elements.append(pos_table)
    elements.append(Spacer(1, 5*mm))

    # --- Summen ---
    def fmt(val):
        return f"{val or 0:,.2f} EUR".replace(',', 'X').replace('.', ',').replace('X', '.')

    is_small_biz = company.small_business if company else False

    summen_data = [['', 'Nettobetrag:', fmt(angebot.netto_gesamt)]]
    if is_small_biz:
        summen_data.append(['', 'MwSt.:', 'entfaellt'])
        if company and company.small_business_text:
            summen_data.append(['', Paragraph(company.small_business_text, style_small), ''])
    else:
        summen_data.append(['', 'MwSt. 19%:', fmt(angebot.mwst_gesamt)])
    summen_data.append(['', 'Gesamtbetrag:', fmt(angebot.brutto_gesamt)])

    if angebot.versandkosten and angebot.versandkosten > 0:
        summen_data.append(['', 'zzgl. Versand:', fmt(angebot.versandkosten)])

    summen_table = Table(summen_data, colWidths=[100*mm, 40*mm, 30*mm])
    summen_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (1, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (1, -1), (-1, -1), 1, colors.black),
    ]))
    elements.append(summen_table)
    elements.append(Spacer(1, 10*mm))

    # --- Textbausteine / Konditionen ---
    if angebot.textbausteine_text:
        elements.append(Paragraph("<b>Konditionen:</b>", style_normal))
        elements.append(Spacer(1, 2*mm))
        for line in angebot.textbausteine_text.split('\n'):
            if line.strip():
                elements.append(Paragraph(line.strip(), style_small))
        elements.append(Spacer(1, 5*mm))

    # --- Zahlungs- / Lieferbedingungen ---
    if angebot.zahlungsbedingungen:
        elements.append(Paragraph(f"<b>Zahlungsbedingungen:</b> {angebot.zahlungsbedingungen}", style_small))
    if angebot.lieferzeit:
        elements.append(Paragraph(f"<b>Lieferzeit:</b> {angebot.lieferzeit}", style_small))
    if angebot.bemerkungen:
        elements.append(Spacer(1, 3*mm))
        elements.append(Paragraph(f"<b>Bemerkungen:</b> {angebot.bemerkungen}", style_small))

    # --- Schluss ---
    elements.append(Spacer(1, 10*mm))
    elements.append(Paragraph("Wir freuen uns auf Ihre Rueckmeldung.", style_normal))
    elements.append(Spacer(1, 5*mm))
    # Name unter "Mit freundlichen Gruessen": User > Firmen-Kontakt > Firmenname
    user_name = ''
    try:
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            fn = (current_user.first_name or '').strip()
            ln = (current_user.last_name or '').strip()
            user_name = f"{fn} {ln}".strip()
            if not user_name:
                user_name = current_user.username
    except Exception:
        pass
    if not user_name and company:
        cfn = (company.contact_first_name or '').strip()
        cln = (company.contact_last_name or '').strip()
        user_name = f"{cfn} {cln}".strip()
    if not user_name:
        user_name = c_name
    elements.append(Paragraph(f"Mit freundlichen Gruessen<br/><b>{user_name}</b>", style_normal))

    # --- Footer ---
    elements.append(Spacer(1, 10*mm))
    footer_parts = []
    if company:
        if company.tax_id:
            footer_parts.append(f"Steuernummer: {company.tax_id}")
        if company.vat_id:
            footer_parts.append(f"USt-IdNr.: {company.vat_id}")
        if company.iban:
            footer_parts.append(f"IBAN: {company.iban}")
        if company.bic:
            footer_parts.append(f"BIC: {company.bic}")
    if footer_parts:
        elements.append(Paragraph(" | ".join(footer_parts), style_small))

    # --- Freigabe-Abschnitt (wenn vom Kunden unterschrieben) ---
    if include_signature and angebot.approval_signature:
        elements.append(Spacer(1, 8*mm))
        elements.append(Paragraph('<para backColor="#f0f8ff"><b>Freigabe durch den Kunden</b></para>', style_normal))
        elements.append(Spacer(1, 3*mm))

        sig_data = [
            ['Freigegeben von:', angebot.approved_by_name or '-'],
            ['Datum:', angebot.approval_date.strftime('%d.%m.%Y %H:%M') if angebot.approval_date else '-'],
        ]
        if angebot.approval_notes:
            sig_data.append(['Anmerkungen:', angebot.approval_notes])

        sig_info_table = Table(sig_data, colWidths=[35*mm, 130*mm])
        sig_info_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ]))
        elements.append(sig_info_table)
        elements.append(Spacer(1, 4*mm))

        # Unterschriftsbild einbetten
        try:
            sig_b64 = angebot.approval_signature
            if sig_b64.startswith('data:image/png;base64,'):
                sig_b64 = sig_b64[len('data:image/png;base64,'):]
            sig_bytes = base64.b64decode(sig_b64)
            sig_img = Image(io.BytesIO(sig_bytes), width=80*mm, height=28*mm)
            elements.append(sig_img)
        except Exception:
            elements.append(Paragraph('<i>(Unterschrift nicht darstellbar)</i>', style_small))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


@angebote_bp.route('/<int:angebot_id>/pdf')
@login_required
def pdf_generieren(angebot_id):
    """PDF fuer Angebot generieren (mit Unterschrift wenn vorhanden)"""
    import io
    from flask import send_file

    angebot = Angebot.query.get_or_404(angebot_id)

    try:
        include_sig = bool(angebot.approval_signature)
        pdf_bytes = _build_angebot_pdf_bytes(angebot, include_signature=include_sig)
        safe_nr = angebot.angebotsnummer.replace('/', '-').replace('\\', '-')
        suffix = '_unterzeichnet' if include_sig else ''
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Angebot_{safe_nr}{suffix}.pdf'
        )

    except ImportError:
        flash('PDF-Bibliothek (reportlab) nicht installiert.', 'danger')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"PDF-Fehler: {e}")
        flash(f'Fehler bei PDF-Generierung: {str(e)}', 'danger')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))


# ============================================================
# API: Preiskalkulator
# ============================================================

def _kalkuliere_preis(verfahren, stichzahl, breite_mm, hoehe_mm, menge):
    """Berechnet Veredelungspreis basierend auf Verfahrens-Preisregeln"""
    stueckpreis = 0.0

    # Basispreis nach Verfahrenstyp
    if verfahren.preis_pro_1000_stiche and stichzahl:
        stueckpreis = (stichzahl / 1000) * verfahren.preis_pro_1000_stiche
    elif verfahren.preis_pro_cm2 and breite_mm and hoehe_mm:
        flaeche_cm2 = (breite_mm / 10) * (hoehe_mm / 10)
        stueckpreis = flaeche_cm2 * verfahren.preis_pro_cm2

    # Mindestpreis anwenden
    if verfahren.mindestpreis_pro_stueck:
        stueckpreis = max(stueckpreis, verfahren.mindestpreis_pro_stueck)

    # Staffelrabatt
    rabatt = 0
    if verfahren.staffelpreise and menge:
        try:
            staffeln = json.loads(verfahren.staffelpreise)
            for s in sorted(staffeln, key=lambda x: x.get('ab_menge', 0), reverse=True):
                if menge >= s.get('ab_menge', 0):
                    rabatt = s.get('rabatt_prozent', 0)
                    break
        except (json.JSONDecodeError, TypeError):
            pass

    stueckpreis_rabattiert = stueckpreis * (1 - rabatt / 100) if rabatt else stueckpreis
    einrichtung = verfahren.einrichtungspauschale or 0
    gesamt = einrichtung + (stueckpreis_rabattiert * (menge or 1))

    # Details-Text
    details_parts = []
    if stichzahl:
        details_parts.append(f"{stichzahl:,} Stiche".replace(',', '.'))
    if breite_mm and hoehe_mm:
        details_parts.append(f"{breite_mm:.0f}x{hoehe_mm:.0f}mm")
    if menge:
        details_parts.append(f"{int(menge)} Stk")
    if rabatt:
        details_parts.append(f"{rabatt}% Staffelrabatt")

    return {
        'einrichtung': round(einrichtung, 2),
        'stueckpreis': round(stueckpreis_rabattiert, 2),
        'stueckpreis_ohne_rabatt': round(stueckpreis, 2),
        'gesamt': round(gesamt, 2),
        'rabatt_prozent': rabatt,
        'details': ' | '.join(details_parts),
    }


@angebote_bp.route('/api/kalkulation')
@login_required
def api_kalkulation():
    """Berechnet Veredelungspreis anhand von Verfahren + Parametern"""
    verfahren_id = request.args.get('verfahren_id', type=int)
    stichzahl = request.args.get('stichzahl', 0, type=int)
    breite_mm = request.args.get('breite_mm', 0, type=float)
    hoehe_mm = request.args.get('hoehe_mm', 0, type=float)
    menge = request.args.get('menge', 1, type=int)

    verfahren = VeredelungsVerfahren.query.get(verfahren_id)
    if not verfahren:
        return jsonify({'error': 'Verfahren nicht gefunden'}), 404

    result = _kalkuliere_preis(verfahren, stichzahl, breite_mm, hoehe_mm, menge)
    result['verfahren_name'] = verfahren.name
    return jsonify(result)


@angebote_bp.route('/api/design-upload', methods=['POST'])
@login_required
def api_design_upload():
    """Laedt eine Design-Datei hoch und gibt den Pfad zurueck"""
    if 'design_file' not in request.files:
        return jsonify({'error': 'Keine Datei'}), 400

    file = request.files['design_file']
    if not file.filename:
        return jsonify({'error': 'Keine Datei ausgewaehlt'}), 400

    allowed = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'ai', 'eps', 'svg', 'dst', 'emb'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed:
        return jsonify({'error': f'Dateityp .{ext} nicht erlaubt'}), 400

    upload_dir = os.path.join(current_app.static_folder, 'uploads', 'angebote')
    os.makedirs(upload_dir, exist_ok=True)

    safe_name = secure_filename(file.filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    filename = f"{timestamp}_{safe_name}"
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    rel_path = f"uploads/angebote/{filename}"

    # Thumbnail fuer Bildformate
    thumbnail_path = ''
    if ext in {'png', 'jpg', 'jpeg', 'gif'}:
        thumbnail_path = rel_path  # Bild ist sein eigenes Thumbnail

    return jsonify({
        'success': True,
        'file_path': rel_path,
        'thumbnail_path': thumbnail_path,
        'filename': safe_name,
    })
