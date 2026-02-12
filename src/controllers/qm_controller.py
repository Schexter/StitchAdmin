# -*- coding: utf-8 -*-
"""
QM (Qualitätsmanagement) Controller
===================================
Vollständige QM-Verwaltung mit Checklisten, Prüfungen und Mängel-Tracking

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_, or_
import json
import os

from src.models import db
from src.models.models import Order, ActivityLog
from src.models.packing_list import PackingList
from src.models.qm import (
    QCChecklist, QCChecklistType, QCInspection, QCStatus,
    QCDefect, DefectCategory, DefectSeverity, QCRework, QCStatistics
)

# Blueprint erstellen
qm_bp = Blueprint('qm', __name__, url_prefix='/qm')


def log_activity(action, details):
    """Aktivität protokollieren"""
    activity = ActivityLog(
        username=current_user.username,
        action=action,
        details=details,
        ip_address=request.remote_addr
    )
    db.session.add(activity)
    db.session.commit()


# ==========================================
# DASHBOARD
# ==========================================

@qm_bp.route('/')
@login_required
def dashboard():
    """QM-Dashboard mit Übersicht"""
    
    # Offene Prüfungen
    pending_inspections = QCInspection.query.filter(
        QCInspection.status.in_([QCStatus.PENDING, QCStatus.IN_PROGRESS])
    ).order_by(QCInspection.created_at).all()
    
    # Fehlgeschlagene Prüfungen (Nacharbeit erforderlich)
    failed_inspections = QCInspection.query.filter_by(
        status=QCStatus.FAILED
    ).filter(
        QCInspection.requires_rework == True
    ).all()
    
    # Offene Nacharbeiten
    open_reworks = QCRework.query.filter(
        QCRework.status.in_(['pending', 'in_progress'])
    ).order_by(QCRework.priority.desc(), QCRework.created_at).all()
    
    # Statistiken heute
    today = date.today()
    today_stats = {
        'inspections_total': QCInspection.query.filter(
            func.date(QCInspection.created_at) == today
        ).count(),
        'inspections_passed': QCInspection.query.filter(
            func.date(QCInspection.completed_at) == today,
            QCInspection.status.in_([QCStatus.PASSED, QCStatus.PASSED_WITH_REMARKS])
        ).count(),
        'inspections_failed': QCInspection.query.filter(
            func.date(QCInspection.completed_at) == today,
            QCInspection.status == QCStatus.FAILED
        ).count(),
        'defects_found': QCDefect.query.filter(
            func.date(QCDefect.created_at) == today
        ).count(),
        'defects_resolved': QCDefect.query.filter(
            func.date(QCDefect.resolved_at) == today
        ).count()
    }
    
    # Letzte 7 Tage Statistiken für Chart
    week_stats = []
    for i in range(7):
        day = today - timedelta(days=6-i)
        day_passed = QCInspection.query.filter(
            func.date(QCInspection.completed_at) == day,
            QCInspection.status.in_([QCStatus.PASSED, QCStatus.PASSED_WITH_REMARKS])
        ).count()
        day_failed = QCInspection.query.filter(
            func.date(QCInspection.completed_at) == day,
            QCInspection.status == QCStatus.FAILED
        ).count()
        week_stats.append({
            'date': day.strftime('%d.%m.'),
            'passed': day_passed,
            'failed': day_failed
        })
    
    # Top-Mängelkategorien
    defect_categories = db.session.query(
        QCDefect.category,
        func.count(QCDefect.id).label('count')
    ).filter(
        QCDefect.created_at >= today - timedelta(days=30)
    ).group_by(QCDefect.category).order_by(func.count(QCDefect.id).desc()).limit(5).all()
    
    top_categories = [
        {'category': cat.value, 'label': _get_category_label(cat), 'count': count}
        for cat, count in defect_categories
    ]
    
    return render_template('qm/dashboard.html',
        pending_inspections=pending_inspections,
        failed_inspections=failed_inspections,
        open_reworks=open_reworks,
        today_stats=today_stats,
        week_stats=week_stats,
        top_categories=top_categories
    )


# ==========================================
# PRÜFUNGEN
# ==========================================

@qm_bp.route('/pruefungen')
@login_required
def inspections_list():
    """Liste aller Prüfungen"""
    
    status_filter = request.args.get('status', '')
    date_from = request.args.get('from', '')
    date_to = request.args.get('to', '')
    
    query = QCInspection.query
    
    if status_filter:
        query = query.filter_by(status=QCStatus(status_filter))
    
    if date_from:
        query = query.filter(QCInspection.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    
    if date_to:
        query = query.filter(QCInspection.created_at <= datetime.strptime(date_to, '%Y-%m-%d'))
    
    inspections = query.order_by(QCInspection.created_at.desc()).limit(100).all()
    
    return render_template('qm/inspections_list.html',
        inspections=inspections,
        status_filter=status_filter,
        qc_statuses=QCStatus
    )


@qm_bp.route('/pruefung/neu', methods=['GET', 'POST'])
@login_required
def new_inspection():
    """Neue Prüfung erstellen"""
    
    if request.method == 'POST':
        try:
            order_id = request.form.get('order_id')
            packing_list_id = request.form.get('packing_list_id')
            checklist_id = request.form.get('checklist_id')
            
            inspection = QCInspection(
                inspection_number=QCInspection.generate_inspection_number(),
                order_id=order_id if order_id else None,
                packing_list_id=int(packing_list_id) if packing_list_id else None,
                checklist_id=int(checklist_id) if checklist_id else None,
                status=QCStatus.PENDING,
                created_by=current_user.username
            )
            
            db.session.add(inspection)
            db.session.commit()
            
            log_activity('qc_inspection_created', 
                        f'Prüfung {inspection.inspection_number} erstellt')
            
            flash(f'Prüfung {inspection.inspection_number} wurde erstellt.', 'success')
            return redirect(url_for('qm.perform_inspection', inspection_id=inspection.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {str(e)}', 'danger')
    
    # GET: Formular anzeigen
    orders = Order.query.filter(
        Order.status.in_(['production_done', 'ready', 'qc_pending'])
    ).order_by(Order.created_at.desc()).limit(50).all()
    
    packing_lists = PackingList.query.filter_by(
        status='ready'
    ).order_by(PackingList.created_at.desc()).limit(50).all()
    
    checklists = QCChecklist.query.filter_by(is_active=True).all()
    
    # Vorauswahl
    order_id = request.args.get('order_id')
    packing_list_id = request.args.get('packing_list_id')
    
    return render_template('qm/new_inspection.html',
        orders=orders,
        packing_lists=packing_lists,
        checklists=checklists,
        preselected_order_id=order_id,
        preselected_packing_list_id=packing_list_id,
        checklist_types=QCChecklistType
    )


@qm_bp.route('/pruefung/<int:inspection_id>')
@login_required
def inspection_detail(inspection_id):
    """Prüfungs-Details anzeigen"""
    
    inspection = QCInspection.query.get_or_404(inspection_id)
    
    # Hole Checklisten-Items
    checklist_items = []
    if inspection.checklist:
        checklist_items = inspection.checklist.get_items()
    
    # Hole Ergebnisse
    results = inspection.get_results()
    
    # Merge Items mit Ergebnissen
    for item in checklist_items:
        item_result = results.get(str(item['id']), {})
        item['checked'] = bool(item_result)
        item['passed'] = item_result.get('passed', None)
        item['notes'] = item_result.get('notes', '')
        item['photo'] = item_result.get('photo', None)
    
    # Hole Mängel
    defects = inspection.defects.order_by(QCDefect.severity.desc()).all()
    
    return render_template('qm/inspection_detail.html',
        inspection=inspection,
        checklist_items=checklist_items,
        defects=defects,
        defect_categories=DefectCategory,
        defect_severities=DefectSeverity
    )


@qm_bp.route('/pruefung/<int:inspection_id>/durchfuehren', methods=['GET', 'POST'])
@login_required
def perform_inspection(inspection_id):
    """Prüfung durchführen (interaktiv)"""
    
    inspection = QCInspection.query.get_or_404(inspection_id)
    
    # Starte Prüfung falls noch nicht gestartet
    if inspection.status == QCStatus.PENDING:
        inspection.start_inspection(current_user.username)
        db.session.commit()
    
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            
            if action == 'save_item':
                # Einzelnen Prüfpunkt speichern
                item_id = request.form.get('item_id')
                passed = request.form.get('passed') == 'true'
                notes = request.form.get('notes', '')
                
                inspection.record_result(int(item_id), passed, notes)
                db.session.commit()
                
                return jsonify({'success': True})
            
            elif action == 'add_defect':
                # Mangel hinzufügen
                category = DefectCategory(request.form.get('category'))
                severity = DefectSeverity(request.form.get('severity'))
                description = request.form.get('description')
                item_id = request.form.get('item_id')
                
                defect = inspection.add_defect(
                    category=category,
                    severity=severity,
                    description=description,
                    item_id=int(item_id) if item_id else None
                )
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'defect_id': defect.id
                })
            
            elif action == 'complete':
                # Prüfung abschließen
                signature = request.form.get('signature')
                notes = request.form.get('notes', '')
                
                inspection.notes = notes
                inspection.complete_inspection(signature)
                db.session.commit()
                
                # Bei fehlgeschlagener Prüfung: Nacharbeit erstellen
                if inspection.status == QCStatus.FAILED and inspection.requires_rework:
                    rework = QCRework.create_from_inspection(inspection, current_user.username)
                    db.session.commit()
                    flash(f'Nacharbeits-Auftrag {rework.rework_number} wurde erstellt.', 'warning')
                
                log_activity('qc_inspection_completed',
                            f'Prüfung {inspection.inspection_number} abgeschlossen: {inspection.status.value}')
                
                flash(f'Prüfung abgeschlossen: {_get_status_label(inspection.status)}', 
                      'success' if inspection.status in [QCStatus.PASSED, QCStatus.PASSED_WITH_REMARKS] else 'warning')
                
                return redirect(url_for('qm.inspection_detail', inspection_id=inspection.id))
            
        except Exception as e:
            db.session.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': str(e)}), 400
            flash(f'Fehler: {str(e)}', 'danger')
    
    # GET: Prüfungs-Interface anzeigen
    checklist_items = []
    if inspection.checklist:
        checklist_items = inspection.checklist.get_items()
    
    results = inspection.get_results()
    
    # Merge Items mit Ergebnissen
    for item in checklist_items:
        item_result = results.get(str(item['id']), {})
        item['checked'] = bool(item_result)
        item['passed'] = item_result.get('passed', None)
        item['notes'] = item_result.get('notes', '')
    
    return render_template('qm/perform_inspection.html',
        inspection=inspection,
        checklist_items=checklist_items,
        defect_categories=DefectCategory,
        defect_severities=DefectSeverity
    )


@qm_bp.route('/pruefung/<int:inspection_id>/foto', methods=['POST'])
@login_required
def upload_inspection_photo(inspection_id):
    """Foto zur Prüfung hochladen"""
    
    inspection = QCInspection.query.get_or_404(inspection_id)
    
    if 'photo' not in request.files:
        return jsonify({'success': False, 'error': 'Keine Datei'}), 400
    
    file = request.files['photo']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Keine Datei ausgewählt'}), 400
    
    try:
        from werkzeug.utils import secure_filename
        
        # Speicherort
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'qc_photos')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Dateiname
        filename = f"{inspection.inspection_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(file.filename)}"
        filepath = os.path.join(upload_dir, filename)
        
        file.save(filepath)
        
        # Zur Inspektion hinzufügen
        item_id = request.form.get('item_id')
        description = request.form.get('description', '')
        
        inspection.add_photo(
            path=f"uploads/qc_photos/{filename}",
            description=description,
            item_id=int(item_id) if item_id else None
        )
        db.session.commit()
        
        return jsonify({
            'success': True,
            'photo_path': f"uploads/qc_photos/{filename}"
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==========================================
# CHECKLISTEN
# ==========================================

@qm_bp.route('/checklisten')
@login_required
def checklists_list():
    """Liste aller Checklisten"""
    
    checklists = QCChecklist.query.order_by(
        QCChecklist.checklist_type,
        QCChecklist.name
    ).all()
    
    # Gruppieren nach Typ
    by_type = {}
    for cl in checklists:
        type_name = cl.checklist_type.value
        if type_name not in by_type:
            by_type[type_name] = []
        by_type[type_name].append(cl)
    
    return render_template('qm/checklists_list.html',
        checklists_by_type=by_type,
        checklist_types=QCChecklistType
    )


@qm_bp.route('/checkliste/neu', methods=['GET', 'POST'])
@login_required
def new_checklist():
    """Neue Checkliste erstellen"""
    
    if request.method == 'POST':
        try:
            checklist = QCChecklist(
                name=request.form.get('name'),
                description=request.form.get('description', ''),
                checklist_type=QCChecklistType(request.form.get('checklist_type')),
                requires_photos=request.form.get('requires_photos') == 'on',
                requires_signature=request.form.get('requires_signature') == 'on',
                min_pass_percentage=float(request.form.get('min_pass_percentage', 100)),
                is_active=True,
                created_by=current_user.username
            )
            
            # Items aus JSON
            items_json = request.form.get('items', '[]')
            checklist.items = items_json
            
            db.session.add(checklist)
            db.session.commit()
            
            log_activity('qc_checklist_created',
                        f'Checkliste "{checklist.name}" erstellt')
            
            flash(f'Checkliste "{checklist.name}" wurde erstellt.', 'success')
            return redirect(url_for('qm.checklists_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {str(e)}', 'danger')
    
    return render_template('qm/edit_checklist.html',
        checklist=None,
        checklist_types=QCChecklistType,
        is_new=True
    )


@qm_bp.route('/checkliste/<int:checklist_id>/bearbeiten', methods=['GET', 'POST'])
@login_required
def edit_checklist(checklist_id):
    """Checkliste bearbeiten"""
    
    checklist = QCChecklist.query.get_or_404(checklist_id)
    
    if request.method == 'POST':
        try:
            checklist.name = request.form.get('name')
            checklist.description = request.form.get('description', '')
            checklist.checklist_type = QCChecklistType(request.form.get('checklist_type'))
            checklist.requires_photos = request.form.get('requires_photos') == 'on'
            checklist.requires_signature = request.form.get('requires_signature') == 'on'
            checklist.min_pass_percentage = float(request.form.get('min_pass_percentage', 100))
            checklist.is_active = request.form.get('is_active') == 'on'
            
            # Items aus JSON
            items_json = request.form.get('items', '[]')
            checklist.items = items_json
            
            db.session.commit()
            
            log_activity('qc_checklist_updated',
                        f'Checkliste "{checklist.name}" aktualisiert')
            
            flash(f'Checkliste wurde aktualisiert.', 'success')
            return redirect(url_for('qm.checklists_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {str(e)}', 'danger')
    
    return render_template('qm/edit_checklist.html',
        checklist=checklist,
        checklist_types=QCChecklistType,
        is_new=False
    )


@qm_bp.route('/checklisten/defaults')
@login_required
def create_default_checklists():
    """Erstellt Standard-Checklisten"""
    
    try:
        QCChecklist.create_default_checklists()
        flash('Standard-Checklisten wurden erstellt.', 'success')
    except Exception as e:
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('qm.checklists_list'))


# ==========================================
# MÄNGEL
# ==========================================

@qm_bp.route('/maengel')
@login_required
def defects_list():
    """Liste aller Mängel"""
    
    status_filter = request.args.get('status', '')  # open, resolved
    severity_filter = request.args.get('severity', '')
    category_filter = request.args.get('category', '')
    
    query = QCDefect.query
    
    if status_filter == 'open':
        query = query.filter_by(is_resolved=False)
    elif status_filter == 'resolved':
        query = query.filter_by(is_resolved=True)
    
    if severity_filter:
        query = query.filter_by(severity=DefectSeverity(severity_filter))
    
    if category_filter:
        query = query.filter_by(category=DefectCategory(category_filter))
    
    defects = query.order_by(QCDefect.created_at.desc()).limit(200).all()
    
    return render_template('qm/defects_list.html',
        defects=defects,
        status_filter=status_filter,
        severity_filter=severity_filter,
        category_filter=category_filter,
        defect_categories=DefectCategory,
        defect_severities=DefectSeverity
    )


@qm_bp.route('/mangel/<int:defect_id>/beheben', methods=['POST'])
@login_required
def resolve_defect(defect_id):
    """Mangel als behoben markieren"""
    
    defect = QCDefect.query.get_or_404(defect_id)
    
    try:
        resolution_notes = request.form.get('resolution_notes', '')
        defect.resolve(resolution_notes, current_user.username)
        db.session.commit()
        
        log_activity('qc_defect_resolved',
                    f'Mangel #{defect.id} behoben')
        
        flash('Mangel wurde als behoben markiert.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(request.referrer or url_for('qm.defects_list'))


# ==========================================
# NACHARBEITEN
# ==========================================

@qm_bp.route('/nacharbeiten')
@login_required
def reworks_list():
    """Liste aller Nacharbeiten"""
    
    status_filter = request.args.get('status', '')
    
    query = QCRework.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    reworks = query.order_by(
        QCRework.priority.desc(),
        QCRework.created_at.desc()
    ).all()
    
    return render_template('qm/reworks_list.html',
        reworks=reworks,
        status_filter=status_filter
    )


@qm_bp.route('/nacharbeit/<int:rework_id>')
@login_required
def rework_detail(rework_id):
    """Nacharbeits-Details"""
    
    rework = QCRework.query.get_or_404(rework_id)
    
    # Hole verknüpfte Mängel
    defect_ids = json.loads(rework.defects_to_fix) if rework.defects_to_fix else []
    defects = QCDefect.query.filter(QCDefect.id.in_(defect_ids)).all() if defect_ids else []
    
    return render_template('qm/rework_detail.html',
        rework=rework,
        defects=defects
    )


@qm_bp.route('/nacharbeit/<int:rework_id>/starten', methods=['POST'])
@login_required
def start_rework(rework_id):
    """Nacharbeit starten"""
    
    rework = QCRework.query.get_or_404(rework_id)
    
    try:
        rework.start(current_user.username)
        db.session.commit()
        
        log_activity('qc_rework_started',
                    f'Nacharbeit {rework.rework_number} gestartet')
        
        flash(f'Nacharbeit {rework.rework_number} wurde gestartet.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('qm.rework_detail', rework_id=rework.id))


@qm_bp.route('/nacharbeit/<int:rework_id>/abschliessen', methods=['POST'])
@login_required
def complete_rework(rework_id):
    """Nacharbeit abschließen"""
    
    rework = QCRework.query.get_or_404(rework_id)
    
    try:
        result_notes = request.form.get('result_notes', '')
        rework.complete(result_notes, current_user.username)
        
        # Verknüpfte Mängel als behoben markieren
        defect_ids = json.loads(rework.defects_to_fix) if rework.defects_to_fix else []
        for defect in QCDefect.query.filter(QCDefect.id.in_(defect_ids)).all():
            if not defect.is_resolved:
                defect.resolve(f"Behoben durch Nacharbeit {rework.rework_number}", current_user.username)
        
        # Erstelle neue Prüfung wenn erforderlich
        if rework.retest_required:
            retest = QCInspection(
                inspection_number=QCInspection.generate_inspection_number(),
                order_id=rework.order_id,
                checklist_id=rework.inspection.checklist_id if rework.inspection else None,
                status=QCStatus.PENDING,
                notes=f"Nachprüfung nach Nacharbeit {rework.rework_number}",
                created_by=current_user.username
            )
            db.session.add(retest)
            db.session.flush()
            
            rework.retest_inspection_id = retest.id
            
            flash(f'Nachprüfung {retest.inspection_number} wurde erstellt.', 'info')
        
        db.session.commit()
        
        log_activity('qc_rework_completed',
                    f'Nacharbeit {rework.rework_number} abgeschlossen')
        
        flash(f'Nacharbeit {rework.rework_number} wurde abgeschlossen.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('qm.rework_detail', rework_id=rework.id))


# ==========================================
# STATISTIKEN
# ==========================================

@qm_bp.route('/statistiken')
@login_required
def statistics():
    """QM-Statistiken"""
    
    # Zeitraum
    period = request.args.get('period', 'month')
    
    if period == 'week':
        start_date = date.today() - timedelta(days=7)
    elif period == 'month':
        start_date = date.today() - timedelta(days=30)
    elif period == 'quarter':
        start_date = date.today() - timedelta(days=90)
    else:
        start_date = date.today() - timedelta(days=365)
    
    # Gesamt-Statistiken
    total_inspections = QCInspection.query.filter(
        QCInspection.created_at >= start_date
    ).count()
    
    passed = QCInspection.query.filter(
        QCInspection.completed_at >= start_date,
        QCInspection.status.in_([QCStatus.PASSED, QCStatus.PASSED_WITH_REMARKS])
    ).count()
    
    failed = QCInspection.query.filter(
        QCInspection.completed_at >= start_date,
        QCInspection.status == QCStatus.FAILED
    ).count()
    
    pass_rate = (passed / total_inspections * 100) if total_inspections > 0 else 0
    
    # Mängel-Statistiken
    total_defects = QCDefect.query.filter(
        QCDefect.created_at >= start_date
    ).count()
    
    resolved_defects = QCDefect.query.filter(
        QCDefect.resolved_at >= start_date
    ).count()
    
    # Durchschnittliche Prüfzeit
    avg_time = db.session.query(
        func.avg(QCInspection.duration_minutes)
    ).filter(
        QCInspection.completed_at >= start_date,
        QCInspection.duration_minutes.isnot(None)
    ).scalar() or 0
    
    # Mängel nach Kategorie
    defects_by_category = db.session.query(
        QCDefect.category,
        func.count(QCDefect.id).label('count')
    ).filter(
        QCDefect.created_at >= start_date
    ).group_by(QCDefect.category).all()
    
    category_data = [
        {'category': cat.value, 'label': _get_category_label(cat), 'count': count}
        for cat, count in defects_by_category
    ]
    
    # Mängel nach Schweregrad
    defects_by_severity = db.session.query(
        QCDefect.severity,
        func.count(QCDefect.id).label('count')
    ).filter(
        QCDefect.created_at >= start_date
    ).group_by(QCDefect.severity).all()
    
    severity_data = [
        {'severity': sev.value, 'label': _get_severity_label(sev), 'count': count}
        for sev, count in defects_by_severity
    ]
    
    # Tages-Trend
    daily_stats = []
    for i in range(min(30, (date.today() - start_date).days + 1)):
        day = start_date + timedelta(days=i)
        day_passed = QCInspection.query.filter(
            func.date(QCInspection.completed_at) == day,
            QCInspection.status.in_([QCStatus.PASSED, QCStatus.PASSED_WITH_REMARKS])
        ).count()
        day_failed = QCInspection.query.filter(
            func.date(QCInspection.completed_at) == day,
            QCInspection.status == QCStatus.FAILED
        ).count()
        daily_stats.append({
            'date': day.strftime('%d.%m.'),
            'passed': day_passed,
            'failed': day_failed
        })
    
    return render_template('qm/statistics.html',
        period=period,
        total_inspections=total_inspections,
        passed=passed,
        failed=failed,
        pass_rate=pass_rate,
        total_defects=total_defects,
        resolved_defects=resolved_defects,
        avg_time=round(avg_time, 1),
        category_data=category_data,
        severity_data=severity_data,
        daily_stats=daily_stats
    )


# ==========================================
# API ENDPOINTS
# ==========================================

@qm_bp.route('/api/order/<order_id>/create-inspection', methods=['POST'])
@login_required
def api_create_inspection_for_order(order_id):
    """API: Erstellt Prüfung für Auftrag"""
    
    try:
        order = Order.query.get_or_404(order_id)
        
        # Bestimme Typ
        checklist_type = None
        if order.order_type == 'embroidery':
            checklist_type = QCChecklistType.EMBROIDERY
        elif order.order_type == 'printing':
            checklist_type = QCChecklistType.PRINTING
        
        inspection = QCInspection.create_for_order(order, checklist_type, current_user.username)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'inspection_id': inspection.id,
            'inspection_number': inspection.inspection_number
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@qm_bp.route('/api/inspection/<int:inspection_id>/status')
@login_required
def api_inspection_status(inspection_id):
    """API: Prüfungs-Status"""
    
    inspection = QCInspection.query.get_or_404(inspection_id)
    
    return jsonify({
        'status': inspection.status.value,
        'status_label': _get_status_label(inspection.status),
        'total_items': inspection.total_items,
        'passed_items': inspection.passed_items,
        'failed_items': inspection.failed_items,
        'pass_percentage': inspection.pass_percentage,
        'defects_count': inspection.defects.count()
    })


# ==========================================
# HILFSFUNKTIONEN
# ==========================================

def _get_status_label(status: QCStatus) -> str:
    """Gibt deutschen Label für Status zurück"""
    labels = {
        QCStatus.PENDING: 'Ausstehend',
        QCStatus.IN_PROGRESS: 'In Bearbeitung',
        QCStatus.PASSED: 'Bestanden',
        QCStatus.FAILED: 'Nicht bestanden',
        QCStatus.PASSED_WITH_REMARKS: 'Bestanden mit Anmerkungen',
        QCStatus.REWORK_REQUIRED: 'Nacharbeit erforderlich'
    }
    return labels.get(status, status.value)


def _get_category_label(category: DefectCategory) -> str:
    """Gibt deutschen Label für Kategorie zurück"""
    labels = {
        DefectCategory.THREAD_BREAK: 'Fadenbruch',
        DefectCategory.COLOR_DEVIATION: 'Farbabweichung',
        DefectCategory.POSITION_ERROR: 'Positionsfehler',
        DefectCategory.SIZE_ERROR: 'Größenfehler',
        DefectCategory.MATERIAL_DAMAGE: 'Materialschaden',
        DefectCategory.STITCH_ERROR: 'Stichfehler',
        DefectCategory.PRINT_DEFECT: 'Druckfehler',
        DefectCategory.WRONG_ARTICLE: 'Falscher Artikel',
        DefectCategory.MISSING_ITEM: 'Fehlender Artikel',
        DefectCategory.PACKAGING_DAMAGE: 'Verpackungsschaden',
        DefectCategory.OTHER: 'Sonstiges'
    }
    return labels.get(category, category.value)


def _get_severity_label(severity: DefectSeverity) -> str:
    """Gibt deutschen Label für Schweregrad zurück"""
    labels = {
        DefectSeverity.MINOR: 'Geringfügig',
        DefectSeverity.MAJOR: 'Erheblich',
        DefectSeverity.CRITICAL: 'Kritisch',
        DefectSeverity.COSMETIC: 'Optisch'
    }
    return labels.get(severity, severity.value)
