# -*- coding: utf-8 -*-
"""
KALENDER CONTROLLER
===================
Outlook-Style Kalender mit:
- Tages-/Wochen-/Monatsansicht
- Ressourcen-Spalten (Maschinen nebeneinander)
- Produktionsplanung
- Ratentermine
- CRM-Followups

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, date, time, timedelta
from decimal import Decimal
import json

from src.models import db

import logging
logger = logging.getLogger(__name__)

kalender_bp = Blueprint('kalender', __name__, url_prefix='/kalender')


# ============================================================================
# HAUPTANSICHTEN
# ============================================================================

@kalender_bp.route('/')
@login_required
def index():
    """Kalender-Hauptansicht (Standard: Wochenansicht mit Ressourcen)"""
    from src.models.kalender import KalenderRessource
    from src.services.crm_finanz_service import KalenderService
    
    ansicht = request.args.get('ansicht', 'resourceTimelineWeek')
    
    # Ressourcen laden
    kal_service = KalenderService()
    ressourcen = kal_service.get_ressourcen()
    
    return render_template('kalender/index.html',
                         ressourcen=ressourcen,
                         default_ansicht=ansicht)


@kalender_bp.route('/produktion')
@login_required
def produktion():
    """Produktionskalender (Maschinen-Fokus)"""
    from src.services.crm_finanz_service import KalenderService
    
    kal_service = KalenderService()
    ressourcen = kal_service.get_ressourcen()
    
    # Nur Maschinen
    maschinen = [r for r in ressourcen if r.get('extendedProps', {}).get('typ') == 'maschine']
    
    return render_template('kalender/produktion.html',
                         ressourcen=maschinen)


@kalender_bp.route('/finanzen')
@login_required
def finanzen():
    """Finanz-Kalender (Raten, Mahnungen, Zahlungen)"""
    return render_template('kalender/finanzen.html')


# ============================================================================
# API ENDPUNKTE (für FullCalendar)
# ============================================================================

@kalender_bp.route('/api/termine')
@login_required
def api_termine():
    """API: Termine für FullCalendar"""
    from src.services.crm_finanz_service import KalenderService
    
    start = request.args.get('start')
    end = request.args.get('end')
    ressource_ids = request.args.getlist('ressource_id', type=int)
    termin_typen = request.args.getlist('typ')
    
    if start:
        start = datetime.fromisoformat(start.replace('Z', '')).date()
    else:
        start = date.today() - timedelta(days=30)
    
    if end:
        end = datetime.fromisoformat(end.replace('Z', '')).date()
    else:
        end = date.today() + timedelta(days=60)
    
    kal_service = KalenderService()
    termine = kal_service.get_termine(
        start, end, 
        ressource_ids=ressource_ids if ressource_ids else None,
        termin_typen=termin_typen if termin_typen else None
    )
    
    return jsonify(termine)


@kalender_bp.route('/api/ressourcen')
@login_required
def api_ressourcen():
    """API: Ressourcen für FullCalendar"""
    from src.services.crm_finanz_service import KalenderService
    
    kal_service = KalenderService()
    ressourcen = kal_service.get_ressourcen()
    
    return jsonify(ressourcen)


@kalender_bp.route('/api/termin', methods=['POST'])
@login_required
def api_termin_erstellen():
    """API: Neuen Termin erstellen"""
    from src.models.kalender import KalenderTermin
    
    data = request.get_json()
    
    try:
        termin = KalenderTermin(
            titel=data.get('title', 'Neuer Termin'),
            start_datum=datetime.fromisoformat(data['start'].replace('Z', '')).date(),
            ende_datum=datetime.fromisoformat(data.get('end', data['start']).replace('Z', '')).date() if data.get('end') else None,
            ganztaegig=data.get('allDay', False),
            termin_typ=data.get('typ', 'intern'),
            ressource_id=data.get('resourceId'),
            kunde_id=data.get('kunde_id'),
            auftrag_id=data.get('auftrag_id'),
            farbe=data.get('color', '#3788d8'),
            erstellt_von=current_user.username,
        )
        
        if not data.get('allDay'):
            start_dt = datetime.fromisoformat(data['start'].replace('Z', ''))
            termin.start_zeit = start_dt.time()
            if data.get('end'):
                ende_dt = datetime.fromisoformat(data['end'].replace('Z', ''))
                termin.ende_zeit = ende_dt.time()
        
        db.session.add(termin)
        db.session.commit()
        
        return jsonify({'success': True, 'id': termin.id, 'event': termin.to_fullcalendar()})
        
    except Exception as e:
        logger.error(f"Termin-Erstellung fehlgeschlagen: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400


@kalender_bp.route('/api/termin/<int:id>', methods=['PUT'])
@login_required
def api_termin_update(id):
    """API: Termin aktualisieren (Drag & Drop)"""
    from src.models.kalender import KalenderTermin
    
    termin = KalenderTermin.query.get_or_404(id)
    data = request.get_json()
    
    try:
        if 'start' in data:
            start_dt = datetime.fromisoformat(data['start'].replace('Z', ''))
            termin.start_datum = start_dt.date()
            if not data.get('allDay', termin.ganztaegig):
                termin.start_zeit = start_dt.time()
        
        if 'end' in data:
            ende_dt = datetime.fromisoformat(data['end'].replace('Z', ''))
            termin.ende_datum = ende_dt.date()
            if not data.get('allDay', termin.ganztaegig):
                termin.ende_zeit = ende_dt.time()
        
        if 'resourceId' in data:
            termin.ressource_id = data['resourceId']
        
        if 'title' in data:
            termin.titel = data['title']
        
        db.session.commit()
        
        return jsonify({'success': True, 'event': termin.to_fullcalendar()})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@kalender_bp.route('/api/termin/<int:id>', methods=['DELETE'])
@login_required
def api_termin_loeschen(id):
    """API: Termin löschen"""
    from src.models.kalender import KalenderTermin
    
    termin = KalenderTermin.query.get_or_404(id)
    
    try:
        db.session.delete(termin)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@kalender_bp.route('/api/auslastung')
@login_required
def api_auslastung():
    """API: Ressourcen-Auslastung"""
    from src.services.crm_finanz_service import KalenderService
    
    start = request.args.get('start')
    ende = request.args.get('ende')
    
    if start:
        start = datetime.fromisoformat(start).date()
    else:
        start = date.today()
    
    if ende:
        ende = datetime.fromisoformat(ende).date()
    else:
        ende = start + timedelta(days=7)
    
    kal_service = KalenderService()
    ressourcen = kal_service.get_ressourcen()
    
    auslastungen = []
    for r in ressourcen:
        auslastung = kal_service.get_ressource_auslastung(r['id'], start, ende)
        if auslastung:
            auslastungen.append(auslastung)
    
    return jsonify(auslastungen)


# ============================================================================
# RATENZAHLUNGEN
# ============================================================================

@kalender_bp.route('/raten')
@login_required
def raten_uebersicht():
    """Übersicht fälliger Ratenzahlungen"""
    from src.services.crm_finanz_service import CRMFinanzService
    
    crm_service = CRMFinanzService()
    
    # Fällige Raten (nächste 30 Tage)
    faellige_raten = crm_service.get_faellige_raten(tage_voraus=30)
    
    # Überfällige
    ueberfaellige = [r for r in faellige_raten if r['tage_bis'] < 0]
    kommende = [r for r in faellige_raten if r['tage_bis'] >= 0]
    
    return render_template('kalender/raten.html',
                         ueberfaellige=ueberfaellige,
                         kommende=kommende)


@kalender_bp.route('/raten/neu', methods=['GET', 'POST'])
@login_required
def raten_neu():
    """Neue Ratenzahlung erstellen"""
    from src.services.crm_finanz_service import CRMFinanzService
    from src.models.models import Customer
    from src.models.document_workflow import BusinessDocument
    
    if request.method == 'POST':
        crm_service = CRMFinanzService()
        
        try:
            ergebnis = crm_service.erstelle_ratenzahlung(
                kunde_id=int(request.form['kunde_id']),
                dokument_id=int(request.form.get('dokument_id', 0)) or None,
                gesamtbetrag=Decimal(request.form['gesamtbetrag'].replace(',', '.')),
                anzahl_raten=int(request.form['anzahl_raten']),
                erste_rate=datetime.strptime(request.form['erste_rate'], '%Y-%m-%d').date(),
                intervall_tage=int(request.form.get('intervall', 30)),
            )
            
            flash(f'Ratenzahlung erstellt: {ergebnis["termine_erstellt"]} Termine angelegt.', 'success')
            return redirect(url_for('kalender.raten_uebersicht'))
            
        except Exception as e:
            flash(f'Fehler: {e}', 'danger')
    
    # Daten für Formular
    kunden = Customer.query.order_by(Customer.company_name).all()
    rechnungen = BusinessDocument.query.filter(
        BusinessDocument.dokument_typ.in_(['rechnung', 'schlussrechnung']),
        BusinessDocument.status.in_(['offen', 'teilbezahlt'])
    ).all()
    
    return render_template('kalender/raten_neu.html',
                         kunden=kunden,
                         rechnungen=rechnungen)


# ============================================================================
# RESSOURCEN-VERWALTUNG
# ============================================================================

@kalender_bp.route('/ressourcen')
@login_required
def ressourcen_liste():
    """Ressourcen verwalten"""
    from src.models.kalender import KalenderRessource
    
    ressourcen = KalenderRessource.query.order_by(KalenderRessource.reihenfolge).all()
    
    return render_template('kalender/ressourcen.html',
                         ressourcen=ressourcen)


@kalender_bp.route('/ressourcen/neu', methods=['GET', 'POST'])
@login_required
def ressource_neu():
    """Neue Ressource erstellen"""
    from src.models.kalender import KalenderRessource
    
    if request.method == 'POST':
        ressource = KalenderRessource(
            name=request.form['name'],
            typ=request.form.get('typ', 'maschine'),
            maschinen_typ=request.form.get('maschinen_typ'),
            kapazitaet=request.form.get('kapazitaet'),
            farbe=request.form.get('farbe', '#3788d8'),
            beschreibung=request.form.get('beschreibung'),
        )
        
        db.session.add(ressource)
        db.session.commit()
        
        flash('Ressource erstellt.', 'success')
        return redirect(url_for('kalender.ressourcen_liste'))
    
    return render_template('kalender/ressource_form.html')


@kalender_bp.route('/ressourcen/init', methods=['POST'])
@login_required
def ressourcen_init():
    """Standard-Ressourcen initialisieren"""
    from src.models.kalender import init_standard_ressourcen
    
    init_standard_ressourcen()
    flash('Standard-Ressourcen (Maschinen) initialisiert.', 'success')
    
    return redirect(url_for('kalender.ressourcen_liste'))
