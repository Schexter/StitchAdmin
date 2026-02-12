# -*- coding: utf-8 -*-
"""
Admin-Controller für Dokument-Workflow
======================================
Verwaltung von:
- Nummernkreise
- Zahlungsbedingungen

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime
from decimal import Decimal

from src.models import db

# Prüfen ob Models verfügbar
try:
    from src.models.document_workflow import (
        Nummernkreis, Zahlungsbedingung,
        initialisiere_nummernkreise, initialisiere_zahlungsbedingungen
    )
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False

import logging
logger = logging.getLogger(__name__)

# Blueprint
document_admin_bp = Blueprint('document_admin', __name__, url_prefix='/admin/dokumente')


def admin_required(f):
    """Decorator: Nur Admins erlaubt"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Administratorrechte erforderlich.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def models_required(f):
    """Decorator: Prüft ob Models verfügbar"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not MODELS_AVAILABLE:
            flash('Dokument-Workflow nicht verfügbar. Bitte Migration ausführen.', 'warning')
            return redirect(url_for('settings.index'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# ÜBERSICHT
# ============================================================================

@document_admin_bp.route('/')
@login_required
@admin_required
@models_required
def index():
    """Übersicht Dokument-Einstellungen"""
    nummernkreise = Nummernkreis.query.order_by(Nummernkreis.belegart).all()
    zahlungsbedingungen = Zahlungsbedingung.query.filter_by(aktiv=True).order_by(Zahlungsbedingung.sortierung).all()
    
    return render_template('admin/dokumente/index.html',
                         nummernkreise=nummernkreise,
                         zahlungsbedingungen=zahlungsbedingungen)


# ============================================================================
# NUMMERNKREISE
# ============================================================================

@document_admin_bp.route('/nummernkreise')
@login_required
@admin_required
@models_required
def nummernkreise_index():
    """Liste aller Nummernkreise"""
    nummernkreise = Nummernkreis.query.order_by(Nummernkreis.belegart).all()
    
    return render_template('admin/dokumente/nummernkreise.html',
                         nummernkreise=nummernkreise)


@document_admin_bp.route('/nummernkreise/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
@models_required
def nummernkreis_edit(id):
    """Nummernkreis bearbeiten"""
    nk = Nummernkreis.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Nur bestimmte Felder sind editierbar
            nk.bezeichnung = request.form.get('bezeichnung', nk.bezeichnung)
            nk.praefix = request.form.get('praefix', nk.praefix).upper()
            nk.stellen = int(request.form.get('stellen', nk.stellen))
            nk.trennzeichen = request.form.get('trennzeichen', nk.trennzeichen)
            nk.jahr_format = request.form.get('jahr_format', nk.jahr_format)
            nk.jahreswechsel_reset = request.form.get('jahreswechsel_reset') == 'on'
            nk.aktiv = request.form.get('aktiv') == 'on'
            
            # Manuelle Nummer-Korrektur (nur erhöhen!)
            neue_nummer = request.form.get('aktuelle_nummer')
            if neue_nummer:
                neue_nummer = int(neue_nummer)
                if neue_nummer > nk.aktuelle_nummer:
                    nk.aktuelle_nummer = neue_nummer
                    logger.warning(f"Nummernkreis {nk.belegart}: Nummer manuell auf {neue_nummer} gesetzt von {current_user.username}")
            
            nk.geaendert_am = datetime.utcnow()
            db.session.commit()
            
            flash(f'Nummernkreis "{nk.bezeichnung}" gespeichert.', 'success')
            return redirect(url_for('document_admin.nummernkreise_index'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler beim Speichern Nummernkreis: {e}")
            flash(f'Fehler: {str(e)}', 'danger')
    
    return render_template('admin/dokumente/nummernkreis_edit.html', nk=nk)


@document_admin_bp.route('/nummernkreise/reset', methods=['POST'])
@login_required
@admin_required
@models_required
def nummernkreise_reset():
    """Initialisiert fehlende Nummernkreise"""
    try:
        initialisiere_nummernkreise()
        flash('Nummernkreise initialisiert.', 'success')
    except Exception as e:
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('document_admin.nummernkreise_index'))


@document_admin_bp.route('/api/nummernkreis/<belegart>/vorschau')
@login_required
@models_required
def api_nummernkreis_vorschau(belegart):
    """API: Vorschau der nächsten Nummer"""
    nk = Nummernkreis.query.filter_by(belegart=belegart, aktiv=True).first()
    
    if not nk:
        return jsonify({'error': 'Nummernkreis nicht gefunden'}), 404
    
    return jsonify({
        'belegart': nk.belegart,
        'naechste_nummer': nk.vorschau_naechste(),
        'aktuelle_nummer': nk.aktuelle_nummer
    })


# ============================================================================
# ZAHLUNGSBEDINGUNGEN
# ============================================================================

@document_admin_bp.route('/zahlungsbedingungen')
@login_required
@admin_required
@models_required
def zahlungsbedingungen_index():
    """Liste aller Zahlungsbedingungen"""
    bedingungen = Zahlungsbedingung.query.order_by(
        Zahlungsbedingung.aktiv.desc(),
        Zahlungsbedingung.sortierung
    ).all()
    
    return render_template('admin/dokumente/zahlungsbedingungen.html',
                         bedingungen=bedingungen)


@document_admin_bp.route('/zahlungsbedingungen/neu', methods=['GET', 'POST'])
@login_required
@admin_required
@models_required
def zahlungsbedingung_neu():
    """Neue Zahlungsbedingung anlegen"""
    if request.method == 'POST':
        try:
            zb = Zahlungsbedingung(
                bezeichnung=request.form.get('bezeichnung'),
                kurztext=request.form.get('kurztext'),
                zahlungsziel_tage=int(request.form.get('zahlungsziel_tage', 14)),
                skonto_prozent=Decimal(request.form.get('skonto_prozent', '0') or '0'),
                skonto_tage=int(request.form.get('skonto_tage', 0) or 0),
                anzahlung_erforderlich=request.form.get('anzahlung_erforderlich') == 'on',
                anzahlung_prozent=Decimal(request.form.get('anzahlung_prozent', '0') or '0'),
                anzahlung_festbetrag=Decimal(request.form.get('anzahlung_festbetrag', '0') or '0'),
                anzahlung_text=request.form.get('anzahlung_text'),
                text_rechnung=request.form.get('text_rechnung'),
                text_rechnung_skonto=request.form.get('text_rechnung_skonto'),
                sortierung=int(request.form.get('sortierung', 0) or 0),
                aktiv=True
            )
            
            # Standard?
            if request.form.get('standard') == 'on':
                # Alle anderen auf nicht-Standard setzen
                Zahlungsbedingung.query.update({'standard': False})
                zb.standard = True
            
            db.session.add(zb)
            db.session.commit()
            
            flash(f'Zahlungsbedingung "{zb.bezeichnung}" erstellt.', 'success')
            return redirect(url_for('document_admin.zahlungsbedingungen_index'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler beim Erstellen Zahlungsbedingung: {e}")
            flash(f'Fehler: {str(e)}', 'danger')
    
    return render_template('admin/dokumente/zahlungsbedingung_edit.html', zb=None)


@document_admin_bp.route('/zahlungsbedingungen/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
@models_required
def zahlungsbedingung_edit(id):
    """Zahlungsbedingung bearbeiten"""
    zb = Zahlungsbedingung.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            zb.bezeichnung = request.form.get('bezeichnung')
            zb.kurztext = request.form.get('kurztext')
            zb.zahlungsziel_tage = int(request.form.get('zahlungsziel_tage', 14))
            zb.skonto_prozent = Decimal(request.form.get('skonto_prozent', '0') or '0')
            zb.skonto_tage = int(request.form.get('skonto_tage', 0) or 0)
            zb.anzahlung_erforderlich = request.form.get('anzahlung_erforderlich') == 'on'
            zb.anzahlung_prozent = Decimal(request.form.get('anzahlung_prozent', '0') or '0')
            zb.anzahlung_festbetrag = Decimal(request.form.get('anzahlung_festbetrag', '0') or '0')
            zb.anzahlung_text = request.form.get('anzahlung_text')
            zb.text_rechnung = request.form.get('text_rechnung')
            zb.text_rechnung_skonto = request.form.get('text_rechnung_skonto')
            zb.sortierung = int(request.form.get('sortierung', 0) or 0)
            zb.aktiv = request.form.get('aktiv') == 'on'
            
            # Standard?
            if request.form.get('standard') == 'on':
                Zahlungsbedingung.query.update({'standard': False})
                zb.standard = True
            else:
                zb.standard = False
            
            zb.geaendert_am = datetime.utcnow()
            db.session.commit()
            
            flash(f'Zahlungsbedingung "{zb.bezeichnung}" gespeichert.', 'success')
            return redirect(url_for('document_admin.zahlungsbedingungen_index'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler beim Speichern Zahlungsbedingung: {e}")
            flash(f'Fehler: {str(e)}', 'danger')
    
    return render_template('admin/dokumente/zahlungsbedingung_edit.html', zb=zb)


@document_admin_bp.route('/zahlungsbedingungen/<int:id>/loeschen', methods=['POST'])
@login_required
@admin_required
@models_required
def zahlungsbedingung_loeschen(id):
    """Zahlungsbedingung löschen (deaktivieren)"""
    zb = Zahlungsbedingung.query.get_or_404(id)
    
    # Nicht wirklich löschen, nur deaktivieren
    zb.aktiv = False
    zb.geaendert_am = datetime.utcnow()
    db.session.commit()
    
    flash(f'Zahlungsbedingung "{zb.bezeichnung}" deaktiviert.', 'info')
    return redirect(url_for('document_admin.zahlungsbedingungen_index'))


@document_admin_bp.route('/zahlungsbedingungen/reset', methods=['POST'])
@login_required
@admin_required
@models_required
def zahlungsbedingungen_reset():
    """Initialisiert Standard-Zahlungsbedingungen"""
    try:
        initialisiere_zahlungsbedingungen()
        flash('Standard-Zahlungsbedingungen initialisiert.', 'success')
    except Exception as e:
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('document_admin.zahlungsbedingungen_index'))


@document_admin_bp.route('/api/zahlungsbedingung/<int:id>')
@login_required
@models_required
def api_zahlungsbedingung(id):
    """API: Zahlungsbedingung Details"""
    zb = Zahlungsbedingung.query.get_or_404(id)
    
    return jsonify({
        'id': zb.id,
        'bezeichnung': zb.bezeichnung,
        'kurztext': zb.kurztext,
        'zahlungsziel_tage': zb.zahlungsziel_tage,
        'skonto_prozent': float(zb.skonto_prozent or 0),
        'skonto_tage': zb.skonto_tage,
        'anzahlung_erforderlich': zb.anzahlung_erforderlich,
        'anzahlung_prozent': float(zb.anzahlung_prozent or 0),
        'text': zb.generiere_zahlungstext()
    })
