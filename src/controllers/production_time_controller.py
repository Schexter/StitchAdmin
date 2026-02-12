"""
Production Time Tracking Controller
Detaillierte Zeiterfassung für lernende Kalkulation

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from src.models import db
from src.models.production_tracking import ProductionTimeLog, ProductionStatistics, PositionTimeEstimate

# Blueprint erstellen
production_time_bp = Blueprint('production_time', __name__, url_prefix='/production/time')


# ═══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS FÜR ZEITERFASSUNG
# ═══════════════════════════════════════════════════════════════════════════════

@production_time_bp.route('/start', methods=['POST'])
@login_required
def start_tracking():
    """Startet Zeiterfassung für einen Arbeitsschritt"""
    data = request.get_json() or request.form

    order_id = data.get('order_id')
    work_type = data.get('work_type', 'embroidery_run')
    order_item_id = data.get('order_item_id')
    machine_id = data.get('machine_id')

    if not order_id:
        return jsonify({'success': False, 'error': 'Auftrags-ID erforderlich'}), 400

    # Prüfen ob bereits aktive Zeiterfassung läuft
    active_log = ProductionTimeLog.get_active_for_order(order_id)
    if active_log:
        return jsonify({
            'success': False,
            'error': 'Es läuft bereits eine Zeiterfassung für diesen Auftrag',
            'active_log_id': active_log.id,
            'started_at': active_log.started_at.isoformat()
        }), 400

    # Neue Zeiterfassung starten
    log = ProductionTimeLog(
        order_id=order_id,
        order_item_id=order_item_id,
        work_type=work_type,
        started_at=datetime.utcnow(),
        started_by=current_user.username if current_user else session.get('username'),
        machine_id=machine_id,
        # Optionale Details
        stitch_count=data.get('stitch_count'),
        embroidery_position=data.get('position'),
        quantity_planned=data.get('quantity'),
        fabric_type=data.get('fabric_type'),
        complexity_rating=data.get('complexity'),
        is_new_design=data.get('is_new_design', False)
    )

    db.session.add(log)
    db.session.commit()

    return jsonify({
        'success': True,
        'log_id': log.id,
        'started_at': log.started_at.isoformat(),
        'message': f'Zeiterfassung gestartet für {log.work_type_display}'
    })


@production_time_bp.route('/stop', methods=['POST'])
@login_required
def stop_tracking():
    """Stoppt Zeiterfassung"""
    data = request.get_json() or request.form

    log_id = data.get('log_id')
    order_id = data.get('order_id')

    # Finde aktive Zeiterfassung
    if log_id:
        log = ProductionTimeLog.query.get(log_id)
    elif order_id:
        log = ProductionTimeLog.get_active_for_order(order_id)
    else:
        return jsonify({'success': False, 'error': 'Log-ID oder Auftrags-ID erforderlich'}), 400

    if not log:
        return jsonify({'success': False, 'error': 'Keine aktive Zeiterfassung gefunden'}), 404

    if log.ended_at:
        return jsonify({'success': False, 'error': 'Zeiterfassung bereits beendet'}), 400

    # Stoppen und Daten ergänzen
    log.stop(ended_by=current_user.username if current_user else session.get('username'))

    # Optionale Daten beim Stoppen ergänzen
    if data.get('quantity_produced'):
        log.quantity_produced = int(data.get('quantity_produced'))
    if data.get('quantity_rejected'):
        log.quantity_rejected = int(data.get('quantity_rejected'))
    if data.get('notes'):
        log.notes = data.get('notes')
    if data.get('issues'):
        log.issues = data.get('issues')
    if data.get('stitch_count'):
        log.stitch_count = int(data.get('stitch_count'))
    if data.get('color_changes'):
        log.color_changes = int(data.get('color_changes'))

    db.session.commit()

    return jsonify({
        'success': True,
        'log_id': log.id,
        'duration_minutes': round(log.duration_minutes, 1) if log.duration_minutes else 0,
        'time_per_piece': round(log.time_per_piece, 2) if log.time_per_piece else None,
        'stitches_per_minute': round(log.stitches_per_minute, 0) if log.stitches_per_minute else None,
        'message': f'Zeiterfassung beendet: {round(log.duration_minutes, 1)} Minuten'
    })


@production_time_bp.route('/pause', methods=['POST'])
@login_required
def add_pause():
    """Fügt Pausenzeit hinzu"""
    data = request.get_json() or request.form

    log_id = data.get('log_id')
    order_id = data.get('order_id')
    pause_minutes = int(data.get('pause_minutes', 0))

    if pause_minutes <= 0:
        return jsonify({'success': False, 'error': 'Pausenzeit muss positiv sein'}), 400

    # Finde aktive Zeiterfassung
    if log_id:
        log = ProductionTimeLog.query.get(log_id)
    elif order_id:
        log = ProductionTimeLog.get_active_for_order(order_id)
    else:
        return jsonify({'success': False, 'error': 'Log-ID oder Auftrags-ID erforderlich'}), 400

    if not log:
        return jsonify({'success': False, 'error': 'Keine aktive Zeiterfassung gefunden'}), 404

    log.add_pause(pause_minutes)
    db.session.commit()

    return jsonify({
        'success': True,
        'total_pause_minutes': log.paused_duration_minutes,
        'message': f'{pause_minutes} Minuten Pause hinzugefügt'
    })


@production_time_bp.route('/status/<order_id>')
@login_required
def get_status(order_id):
    """Holt aktuellen Tracking-Status für Auftrag"""
    active_log = ProductionTimeLog.get_active_for_order(order_id)

    if active_log:
        return jsonify({
            'is_tracking': True,
            'log_id': active_log.id,
            'work_type': active_log.work_type,
            'work_type_display': active_log.work_type_display,
            'started_at': active_log.started_at.isoformat(),
            'elapsed_minutes': round(active_log.effective_duration, 1),
            'paused_minutes': active_log.paused_duration_minutes or 0,
            'started_by': active_log.started_by
        })

    return jsonify({
        'is_tracking': False,
        'message': 'Keine aktive Zeiterfassung'
    })


@production_time_bp.route('/history/<order_id>')
@login_required
def get_history(order_id):
    """Holt alle Zeiteinträge für einen Auftrag"""
    logs = ProductionTimeLog.query.filter_by(order_id=order_id)\
        .order_by(ProductionTimeLog.started_at.desc()).all()

    history = []
    total_minutes = 0

    for log in logs:
        entry = {
            'id': log.id,
            'work_type': log.work_type,
            'work_type_display': log.work_type_display,
            'started_at': log.started_at.isoformat(),
            'ended_at': log.ended_at.isoformat() if log.ended_at else None,
            'duration_minutes': round(log.duration_minutes, 1) if log.duration_minutes else None,
            'is_running': log.is_running,
            'started_by': log.started_by,
            'ended_by': log.ended_by,
            'quantity_produced': log.quantity_produced,
            'stitch_count': log.stitch_count,
            'position': log.embroidery_position,
            'notes': log.notes
        }
        history.append(entry)

        if log.duration_minutes:
            total_minutes += log.duration_minutes

    return jsonify({
        'order_id': order_id,
        'entries': history,
        'total_minutes': round(total_minutes, 1),
        'total_hours': round(total_minutes / 60, 2)
    })


# ═══════════════════════════════════════════════════════════════════════════════
# ZEITSCHÄTZUNG & KALKULATION
# ═══════════════════════════════════════════════════════════════════════════════

@production_time_bp.route('/estimate')
@login_required
def estimate_time():
    """Schätzt Produktionszeit basierend auf historischen Daten"""
    work_type = request.args.get('work_type', 'embroidery_run')
    stitch_count = request.args.get('stitch_count', type=int)
    position = request.args.get('position')
    quantity = request.args.get('quantity', 1, type=int)
    fabric_type = request.args.get('fabric_type')

    estimate = ProductionStatistics.estimate_time(
        work_type=work_type,
        stitch_count=stitch_count,
        position=position,
        quantity=quantity,
        fabric_type=fabric_type
    )

    return jsonify(estimate)


@production_time_bp.route('/position-estimate')
@login_required
def position_estimate():
    """Zeitschätzung für spezifische Stickposition"""
    position = request.args.get('position')
    quantity = request.args.get('quantity', 1, type=int)
    stitch_count = request.args.get('stitch_count', type=int)
    complexity = request.args.get('complexity', 1, type=int)

    if not position:
        return jsonify({'error': 'Position erforderlich'}), 400

    estimated_minutes = PositionTimeEstimate.get_estimate(
        position=position,
        quantity=quantity,
        stitch_count=stitch_count,
        complexity=complexity
    )

    # Hole auch die Position-Details
    pos_estimate = PositionTimeEstimate.query.filter_by(position_name=position).first()

    return jsonify({
        'position': position,
        'position_display': pos_estimate.display_name if pos_estimate else position,
        'estimated_minutes': estimated_minutes,
        'estimated_hours': round(estimated_minutes / 60, 2),
        'typical_stitch_count': pos_estimate.typical_stitch_count if pos_estimate else None,
        'setup_time': pos_estimate.setup_time_minutes if pos_estimate else 5,
        'sample_count': pos_estimate.sample_count if pos_estimate else 0
    })


# ═══════════════════════════════════════════════════════════════════════════════
# STATISTIK & AUSWERTUNG
# ═══════════════════════════════════════════════════════════════════════════════

@production_time_bp.route('/statistics')
@login_required
def statistics():
    """Zeigt Produktionsstatistik-Übersicht"""
    # Gesamt-Statistiken
    total_logs = ProductionTimeLog.query.filter(ProductionTimeLog.ended_at.isnot(None)).count()

    # Durchschnittliche Zeit pro Arbeitstyp
    from sqlalchemy import func

    work_type_stats = db.session.query(
        ProductionTimeLog.work_type,
        func.count(ProductionTimeLog.id).label('count'),
        func.avg(ProductionTimeLog.duration_minutes).label('avg_duration'),
        func.sum(ProductionTimeLog.quantity_produced).label('total_quantity')
    ).filter(
        ProductionTimeLog.ended_at.isnot(None),
        ProductionTimeLog.duration_minutes > 0
    ).group_by(ProductionTimeLog.work_type).all()

    # Durchschnitt pro Position
    position_stats = db.session.query(
        ProductionTimeLog.embroidery_position,
        func.count(ProductionTimeLog.id).label('count'),
        func.avg(ProductionTimeLog.duration_minutes).label('avg_duration'),
        func.avg(ProductionTimeLog.stitch_count).label('avg_stitches')
    ).filter(
        ProductionTimeLog.ended_at.isnot(None),
        ProductionTimeLog.embroidery_position.isnot(None),
        ProductionTimeLog.duration_minutes > 0
    ).group_by(ProductionTimeLog.embroidery_position).all()

    # Letzte 7 Tage
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_logs = ProductionTimeLog.query.filter(
        ProductionTimeLog.started_at >= week_ago,
        ProductionTimeLog.ended_at.isnot(None)
    ).order_by(ProductionTimeLog.started_at.desc()).limit(50).all()

    # Positions-Schätzungen
    positions = PositionTimeEstimate.query.all()

    return render_template('production/time_statistics.html',
                         total_logs=total_logs,
                         work_type_stats=work_type_stats,
                         position_stats=position_stats,
                         recent_logs=recent_logs,
                         positions=positions)


@production_time_bp.route('/api/dashboard-stats')
@login_required
def dashboard_stats():
    """API für Dashboard-Widget mit Produktionsstatistiken"""
    from sqlalchemy import func

    # Heute
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())

    # Heute produzierte Zeit
    today_stats = db.session.query(
        func.sum(ProductionTimeLog.duration_minutes).label('total_minutes'),
        func.sum(ProductionTimeLog.quantity_produced).label('total_quantity'),
        func.count(ProductionTimeLog.id).label('completed_jobs')
    ).filter(
        ProductionTimeLog.ended_at >= today_start,
        ProductionTimeLog.ended_at.isnot(None)
    ).first()

    # Aktive Aufträge
    active_count = ProductionTimeLog.query.filter(
        ProductionTimeLog.ended_at.is_(None)
    ).count()

    # Diese Woche
    week_start = today_start - timedelta(days=today.weekday())
    week_stats = db.session.query(
        func.sum(ProductionTimeLog.duration_minutes).label('total_minutes'),
        func.sum(ProductionTimeLog.quantity_produced).label('total_quantity')
    ).filter(
        ProductionTimeLog.ended_at >= week_start,
        ProductionTimeLog.ended_at.isnot(None)
    ).first()

    return jsonify({
        'today': {
            'total_hours': round((today_stats.total_minutes or 0) / 60, 1),
            'total_quantity': today_stats.total_quantity or 0,
            'completed_jobs': today_stats.completed_jobs or 0
        },
        'week': {
            'total_hours': round((week_stats.total_minutes or 0) / 60, 1),
            'total_quantity': week_stats.total_quantity or 0
        },
        'active_jobs': active_count
    })


@production_time_bp.route('/update-estimates', methods=['POST'])
@login_required
def update_position_estimates():
    """Aktualisiert Zeitschätzungen basierend auf gesammelten Daten"""
    from sqlalchemy import func

    positions = PositionTimeEstimate.query.all()
    updated = 0

    for pos in positions:
        # Berechne Durchschnitte aus Logs
        stats = db.session.query(
            func.count(ProductionTimeLog.id).label('count'),
            func.avg(ProductionTimeLog.duration_minutes /
                    func.nullif(ProductionTimeLog.quantity_produced, 0)).label('avg_time_per_piece'),
            func.avg(ProductionTimeLog.stitch_count).label('avg_stitches')
        ).filter(
            ProductionTimeLog.embroidery_position == pos.position_name,
            ProductionTimeLog.ended_at.isnot(None),
            ProductionTimeLog.duration_minutes > 0,
            ProductionTimeLog.quantity_produced > 0
        ).first()

        if stats.count and stats.count >= 5:  # Mindestens 5 Datenpunkte
            pos.time_per_piece_minutes = round(stats.avg_time_per_piece, 2)
            pos.typical_stitch_count = int(stats.avg_stitches) if stats.avg_stitches else pos.typical_stitch_count
            pos.sample_count = stats.count
            pos.updated_at = datetime.utcnow()
            updated += 1

    db.session.commit()

    return jsonify({
        'success': True,
        'updated_positions': updated,
        'message': f'{updated} Positionen aktualisiert'
    })


# ═══════════════════════════════════════════════════════════════════════════════
# VERWALTUNG
# ═══════════════════════════════════════════════════════════════════════════════

@production_time_bp.route('/positions')
@login_required
def list_positions():
    """Listet alle konfigurierten Positionen"""
    positions = PositionTimeEstimate.query.order_by(PositionTimeEstimate.position_name).all()

    return jsonify({
        'positions': [{
            'id': p.id,
            'name': p.position_name,
            'display_name': p.display_name,
            'typical_stitches': p.typical_stitch_count,
            'setup_time': p.setup_time_minutes,
            'time_per_piece': p.time_per_piece_minutes,
            'sample_count': p.sample_count
        } for p in positions]
    })


@production_time_bp.route('/positions/<position_name>', methods=['PUT'])
@login_required
def update_position(position_name):
    """Aktualisiert Position-Einstellungen"""
    data = request.get_json()

    pos = PositionTimeEstimate.query.filter_by(position_name=position_name).first()
    if not pos:
        return jsonify({'success': False, 'error': 'Position nicht gefunden'}), 404

    if 'setup_time_minutes' in data:
        pos.setup_time_minutes = float(data['setup_time_minutes'])
    if 'time_per_piece_minutes' in data:
        pos.time_per_piece_minutes = float(data['time_per_piece_minutes'])
    if 'typical_stitch_count' in data:
        pos.typical_stitch_count = int(data['typical_stitch_count'])
    if 'complexity_multiplier' in data:
        pos.complexity_multiplier = float(data['complexity_multiplier'])

    pos.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True, 'message': 'Position aktualisiert'})


@production_time_bp.route('/delete/<int:log_id>', methods=['DELETE'])
@login_required
def delete_log(log_id):
    """Löscht einen Zeiteintrag"""
    log = ProductionTimeLog.query.get(log_id)

    if not log:
        return jsonify({'success': False, 'error': 'Eintrag nicht gefunden'}), 404

    db.session.delete(log)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Eintrag gelöscht'})
