# -*- coding: utf-8 -*-
"""
Veredelungs-Controller
======================
Einstellungen fuer Veredelungsverfahren, Positionen und Parameter.
API-Endpunkte fuer Auftraege/Angebote.
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required
from src.models import db
from src.models.veredelung import (
    VeredelungsVerfahren, VeredelungsPosition,
    VeredelungsParameter, ArtikelVeredelung
)
import logging

logger = logging.getLogger(__name__)

veredelung_bp = Blueprint('veredelung', __name__, url_prefix='/veredelung')


# ============================================================
# EINSTELLUNGSSEITE
# ============================================================

@veredelung_bp.route('/einstellungen')
@login_required
def einstellungen():
    """Veredelungsverfahren verwalten"""
    verfahren = VeredelungsVerfahren.query.order_by(
        VeredelungsVerfahren.sort_order, VeredelungsVerfahren.name
    ).all()
    return render_template('settings/veredelung.html', verfahren=verfahren)


@veredelung_bp.route('/api/verfahren', methods=['POST'])
@login_required
def api_verfahren_create():
    """Neues Veredelungsverfahren anlegen"""
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    code = data.get('code', '').strip().lower()

    if not name or not code:
        return jsonify({'success': False, 'error': 'Name und Code erforderlich'}), 400

    if VeredelungsVerfahren.query.filter_by(code=code).first():
        return jsonify({'success': False, 'error': f'Code "{code}" existiert bereits'}), 400

    max_sort = db.session.query(db.func.max(VeredelungsVerfahren.sort_order)).scalar() or 0
    verfahren = VeredelungsVerfahren(
        name=name, code=code,
        icon=data.get('icon', 'bi-brush'),
        beschreibung=data.get('beschreibung', ''),
        sort_order=max_sort + 1
    )
    db.session.add(verfahren)
    db.session.commit()

    return jsonify({'success': True, 'id': verfahren.id, 'name': verfahren.name})


@veredelung_bp.route('/api/verfahren/<int:vid>', methods=['PUT'])
@login_required
def api_verfahren_update(vid):
    """Veredelungsverfahren aktualisieren"""
    verfahren = VeredelungsVerfahren.query.get_or_404(vid)
    data = request.get_json() or {}

    if 'name' in data:
        verfahren.name = data['name'].strip()
    if 'icon' in data:
        verfahren.icon = data['icon'].strip()
    if 'beschreibung' in data:
        verfahren.beschreibung = data['beschreibung']
    if 'active' in data:
        verfahren.active = bool(data['active'])

    # Preiskalkulation
    for field in ['einrichtungspauschale', 'preis_pro_1000_stiche', 'preis_pro_cm2', 'mindestpreis_pro_stueck']:
        if field in data:
            setattr(verfahren, field, float(data[field] or 0))
    if 'staffelpreise' in data:
        import json
        verfahren.staffelpreise = json.dumps(data['staffelpreise']) if isinstance(data['staffelpreise'], list) else data['staffelpreise']

    db.session.commit()
    return jsonify({'success': True})


@veredelung_bp.route('/api/verfahren/<int:vid>', methods=['DELETE'])
@login_required
def api_verfahren_delete(vid):
    """Veredelungsverfahren loeschen"""
    verfahren = VeredelungsVerfahren.query.get_or_404(vid)
    db.session.delete(verfahren)
    db.session.commit()
    return jsonify({'success': True})


# ============================================================
# POSITIONEN
# ============================================================

@veredelung_bp.route('/api/verfahren/<int:vid>/positionen', methods=['POST'])
@login_required
def api_position_create(vid):
    """Neue Position anlegen"""
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'error': 'Name erforderlich'}), 400

    max_sort = db.session.query(db.func.max(VeredelungsPosition.sort_order)).filter_by(
        verfahren_id=vid).scalar() or 0

    pos = VeredelungsPosition(verfahren_id=vid, name=name, sort_order=max_sort + 1)
    db.session.add(pos)
    db.session.commit()
    return jsonify({'success': True, 'id': pos.id, 'name': pos.name})


@veredelung_bp.route('/api/position/<int:pid>', methods=['PUT'])
@login_required
def api_position_update(pid):
    """Position aktualisieren"""
    pos = VeredelungsPosition.query.get_or_404(pid)
    data = request.get_json() or {}
    if 'name' in data:
        pos.name = data['name'].strip()
    if 'active' in data:
        pos.active = bool(data['active'])
    db.session.commit()
    return jsonify({'success': True})


@veredelung_bp.route('/api/position/<int:pid>', methods=['DELETE'])
@login_required
def api_position_delete(pid):
    """Position loeschen"""
    pos = VeredelungsPosition.query.get_or_404(pid)
    db.session.delete(pos)
    db.session.commit()
    return jsonify({'success': True})


# ============================================================
# PARAMETER
# ============================================================

@veredelung_bp.route('/api/verfahren/<int:vid>/parameter', methods=['POST'])
@login_required
def api_parameter_create(vid):
    """Neuen Parameter anlegen"""
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'error': 'Name erforderlich'}), 400

    max_sort = db.session.query(db.func.max(VeredelungsParameter.sort_order)).filter_by(
        verfahren_id=vid).scalar() or 0

    param = VeredelungsParameter(
        verfahren_id=vid, name=name,
        einheit=data.get('einheit', ''),
        param_type=data.get('param_type', 'text'),
        default_value=data.get('default_value', ''),
        optionen=data.get('optionen', ''),
        sort_order=max_sort + 1
    )
    db.session.add(param)
    db.session.commit()
    return jsonify({'success': True, 'id': param.id, 'name': param.name})


@veredelung_bp.route('/api/parameter/<int:pid>', methods=['PUT'])
@login_required
def api_parameter_update(pid):
    """Parameter aktualisieren"""
    param = VeredelungsParameter.query.get_or_404(pid)
    data = request.get_json() or {}
    for field in ['name', 'einheit', 'param_type', 'default_value', 'optionen']:
        if field in data:
            setattr(param, field, data[field])
    if 'active' in data:
        param.active = bool(data['active'])
    db.session.commit()
    return jsonify({'success': True})


@veredelung_bp.route('/api/parameter/<int:pid>', methods=['DELETE'])
@login_required
def api_parameter_delete(pid):
    """Parameter loeschen"""
    param = VeredelungsParameter.query.get_or_404(pid)
    db.session.delete(param)
    db.session.commit()
    return jsonify({'success': True})


# ============================================================
# API: Positionen + Parameter fuer Auftraege/Angebote
# ============================================================

@veredelung_bp.route('/api/positionen/<code>')
@login_required
def api_get_positionen(code):
    """Liefert Positionen fuer ein Verfahren (fuer Dropdown in Auftraegen)"""
    verfahren = VeredelungsVerfahren.query.filter_by(code=code, active=True).first()
    if not verfahren:
        return jsonify([])

    positionen = [{'id': p.id, 'name': p.name}
                  for p in verfahren.positionen if p.active]
    return jsonify(positionen)


@veredelung_bp.route('/api/parameter-fuer/<code>')
@login_required
def api_get_parameter(code):
    """Liefert Parameter-Definitionen fuer ein Verfahren"""
    verfahren = VeredelungsVerfahren.query.filter_by(code=code, active=True).first()
    if not verfahren:
        return jsonify([])

    params = [{
        'id': p.id, 'name': p.name, 'einheit': p.einheit,
        'param_type': p.param_type, 'default_value': p.default_value,
        'optionen': p.get_optionen_list()
    } for p in verfahren.parameter if p.active]
    return jsonify(params)


@veredelung_bp.route('/api/alle')
@login_required
def api_get_alle():
    """Liefert alle aktiven Verfahren mit Positionen (fuer Dropdowns)"""
    import json as _json
    verfahren_list = VeredelungsVerfahren.get_active()
    result = []
    for v in verfahren_list:
        staffel = []
        if v.staffelpreise:
            try:
                staffel = _json.loads(v.staffelpreise)
            except Exception:
                pass
        result.append({
            'id': v.id, 'name': v.name, 'code': v.code, 'icon': v.icon,
            'einrichtungspauschale': v.einrichtungspauschale or 0,
            'preis_pro_1000_stiche': v.preis_pro_1000_stiche or 0,
            'preis_pro_cm2': v.preis_pro_cm2 or 0,
            'mindestpreis_pro_stueck': v.mindestpreis_pro_stueck or 0,
            'staffelpreise': staffel,
            'positionen': [{'id': p.id, 'name': p.name} for p in v.positionen if p.active],
            'parameter': [{
                'id': p.id, 'name': p.name, 'einheit': p.einheit,
                'param_type': p.param_type, 'default_value': p.default_value,
                'optionen': p.get_optionen_list()
            } for p in v.parameter if p.active]
        })
    return jsonify(result)


# ============================================================
# ARTIKEL-VEREDELUNG
# ============================================================

@veredelung_bp.route('/api/artikel/<article_id>')
@login_required
def api_artikel_veredelung(article_id):
    """Liefert Veredelungswerte fuer einen Artikel"""
    werte = ArtikelVeredelung.query.filter_by(article_id=article_id).all()
    result = {}
    for w in werte:
        key = f"{w.verfahren_id}_{w.parameter_id}"
        result[key] = {
            'verfahren_id': w.verfahren_id,
            'parameter_id': w.parameter_id,
            'wert': w.wert
        }
    return jsonify(result)


@veredelung_bp.route('/api/seed', methods=['POST'])
@login_required
def api_seed_defaults():
    """Standard-Veredelungsverfahren anlegen"""
    try:
        VeredelungsVerfahren.seed_defaults()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@veredelung_bp.route('/import-druckparameter', methods=['POST'])
@login_required
def import_druckparameter():
    """Importiert Druckparameter aus der Printequipment-PDF und weist sie Artikeln zu"""
    import os
    try:
        # PDF-Pfad relativ zum Projektroot
        pdf_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'Printequipment', 'Artikeldruckparameter_DE_2026-02-25_-_.pdf'
        )

        if not os.path.exists(pdf_path):
            return jsonify({'success': False, 'error': f'PDF nicht gefunden: {pdf_path}'}), 404

        from src.services.printequipment_pdf_parser import parse_druckparameter_pdf
        from src.services.printequipment_import_service import assign_druckparameter

        # Schritt 1: PDF parsen
        entries = parse_druckparameter_pdf(pdf_path)
        if not entries:
            return jsonify({'success': False, 'error': 'Keine Eintraege in der PDF gefunden'}), 400

        # Schritt 2: Parameter zuweisen
        stats = assign_druckparameter(entries)

        return jsonify({
            'success': True,
            'pdf_entries': len(entries),
            'matched': stats['matched'],
            'assigned': stats['assigned'],
            'skipped': stats['skipped'],
            'errors': stats['errors'],
        })

    except Exception as e:
        logger.error(f"Druckparameter-Import fehlgeschlagen: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@veredelung_bp.route('/api/artikel/<article_id>/save', methods=['POST'])
@login_required
def api_artikel_veredelung_save(article_id):
    """Speichert Veredelungswerte fuer einen Artikel"""
    data = request.get_json() or {}
    werte = data.get('werte', [])

    # Alte Werte loeschen
    ArtikelVeredelung.query.filter_by(article_id=article_id).delete()

    # Neue Werte speichern
    for w in werte:
        if w.get('wert', '').strip():
            av = ArtikelVeredelung(
                article_id=article_id,
                verfahren_id=w['verfahren_id'],
                parameter_id=w['parameter_id'],
                wert=w['wert'].strip()
            )
            db.session.add(av)

    db.session.commit()
    return jsonify({'success': True})
