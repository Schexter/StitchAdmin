# -*- coding: utf-8 -*-
"""
DESIGN-ERSTELLUNGS CONTROLLER
=============================
Workflow für Fremd- und Eigenerstellung von Designs

Routen:
- /design-creation/new/<order_id> - Neuen Erstellungsauftrag starten
- /design-creation/external - Fremderstellung (Lieferant)
- /design-creation/internal - Eigenerstellung (TODO)
- /design-creation/orders - Übersicht externe Bestellungen
- /design-creation/tasks - Übersicht interne Aufgaben

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
import os
import json
import logging

from src.models import db
from src.models.models import Order, Supplier, ActivityLog

logger = logging.getLogger(__name__)

design_creation_bp = Blueprint('design_creation', __name__, url_prefix='/design-creation')


# ==========================================
# WORKFLOW STARTEN
# ==========================================

@design_creation_bp.route('/new/<order_id>')
@login_required
def new_design_request(order_id):
    """Startet den Design-Erstellungs-Workflow für einen Auftrag"""
    
    order = Order.query.get_or_404(order_id)
    
    # Alle aktiven Lieferanten holen (für Fremderstellung)
    suppliers = Supplier.query.filter(Supplier.is_active == True).order_by(Supplier.name).all()
    
    # Vorhandene Design-Infos vom Auftrag
    existing_specs = {
        'design_type': order.order_type if order.order_type in ('embroidery', 'print', 'dtf') else 'embroidery',
        'width_mm': order.design_width_mm,
        'height_mm': order.design_height_mm,
        'position': order.embroidery_position,
        'stitch_count': order.stitch_count,
        'source_file_path': order.design_file_path,
        'source_file_name': os.path.basename(order.design_file_path) if order.design_file_path else None
    }
    
    return render_template('design_creation/new_request.html',
        order=order,
        suppliers=suppliers,
        existing_specs=existing_specs
    )


@design_creation_bp.route('/create-external/<order_id>', methods=['POST'])
@login_required
def create_external_order(order_id):
    """Erstellt externe Design-Bestellung (Fremderstellung)"""
    
    try:
        from src.services.design_creation_service import get_design_creation_service
        
        order = Order.query.get_or_404(order_id)
        
        # Formulardaten sammeln
        supplier_id = request.form.get('supplier_id')
        if not supplier_id:
            flash('Bitte Lieferant auswählen', 'danger')
            return redirect(url_for('design_creation.new_design_request', order_id=order_id))
        
        specs = {
            'design_type': request.form.get('design_type', 'embroidery'),
            'order_type': request.form.get('order_type', 'new_design'),
            'design_name': request.form.get('design_name', f"Design für {order.order_number}"),
            'description': request.form.get('description', ''),
            
            # Stickerei
            'width_mm': _parse_float(request.form.get('width_mm')),
            'height_mm': _parse_float(request.form.get('height_mm')),
            'max_stitch_count': _parse_int(request.form.get('max_stitch_count')),
            'max_colors': _parse_int(request.form.get('max_colors')),
            'stitch_density': request.form.get('stitch_density', 'normal'),
            'fabric_type': request.form.get('fabric_type', ''),
            
            # Druck
            'print_width_cm': _parse_float(request.form.get('print_width_cm')),
            'print_height_cm': _parse_float(request.form.get('print_height_cm')),
            'print_method': request.form.get('print_method'),
            'min_dpi': _parse_int(request.form.get('min_dpi', 300)),
            'needs_transparent_bg': request.form.get('needs_transparent_bg') == 'on',
            'needs_white_underbase': request.form.get('needs_white_underbase') == 'on',
            
            # Sonstiges
            'special_requirements': request.form.get('special_requirements', ''),
            'priority': request.form.get('priority', 'normal'),
            
            # Quelldatei vom Auftrag
            'source_file_path': order.design_file_path,
            'source_file_name': os.path.basename(order.design_file_path) if order.design_file_path else None
        }
        
        # Garnfarben parsen falls vorhanden
        thread_colors_json = request.form.get('thread_colors')
        if thread_colors_json:
            try:
                specs['thread_colors'] = json.loads(thread_colors_json)
            except:
                pass
        
        # Service aufrufen
        service = get_design_creation_service()
        send_email = request.form.get('send_email') == 'on'
        
        result = service.create_external_design_order(
            order=order,
            supplier_id=supplier_id,
            specs=specs,
            created_by=current_user.username,
            send_email=send_email
        )
        
        if result.get('success'):
            flash(f"✅ {result['message']}", 'success')
            if result.get('email_sent'):
                flash(f"📧 E-Mail gesendet: {result.get('email_message', '')}", 'info')
            return redirect(url_for('design_creation.external_orders'))
        else:
            flash(f"❌ Fehler: {result.get('error')}", 'danger')
            return redirect(url_for('design_creation.new_design_request', order_id=order_id))
            
    except Exception as e:
        logger.error(f"Error creating external order: {e}")
        flash(f'Fehler: {str(e)}', 'danger')
        return redirect(url_for('design_creation.new_design_request', order_id=order_id))


@design_creation_bp.route('/create-internal/<order_id>', methods=['POST'])
@login_required
def create_internal_task(order_id):
    """Erstellt interne Design-Aufgabe (Eigenerstellung)"""
    
    try:
        from src.services.design_creation_service import get_design_creation_service
        
        order = Order.query.get_or_404(order_id)
        
        specs = {
            'design_type': request.form.get('design_type', 'embroidery'),
            'design_name': request.form.get('design_name', f"Design für {order.order_number}"),
            
            # Spezifikationen
            'width_mm': _parse_float(request.form.get('width_mm')),
            'height_mm': _parse_float(request.form.get('height_mm')),
            'max_stitch_count': _parse_int(request.form.get('max_stitch_count')),
            'max_colors': _parse_int(request.form.get('max_colors')),
            'fabric_type': request.form.get('fabric_type', ''),
            'position': request.form.get('position', ''),
            
            # Sonstiges
            'special_requirements': request.form.get('special_requirements', ''),
            'notes': request.form.get('notes', ''),
            'priority': request.form.get('priority', 'normal'),
            
            # Quelldatei
            'source_file_path': order.design_file_path,
            'source_file_name': os.path.basename(order.design_file_path) if order.design_file_path else None,
            
            # Fälligkeit
            'due_date': _parse_date(request.form.get('due_date'))
        }
        
        # Garnfarben parsen
        thread_colors_json = request.form.get('thread_colors')
        if thread_colors_json:
            try:
                specs['thread_colors'] = json.loads(thread_colors_json)
            except:
                pass
        
        # Service aufrufen
        service = get_design_creation_service()
        generate_pdf = request.form.get('generate_pdf') != 'off'
        
        result = service.create_internal_design_task(
            order=order,
            specs=specs,
            created_by=current_user.username,
            generate_pdf=generate_pdf
        )
        
        if result.get('success'):
            flash(f"✅ {result['message']}", 'success')
            if result.get('pdf_generated'):
                flash('📄 Auftragszettel wurde erstellt', 'info')
            return redirect(url_for('design_creation.internal_tasks'))
        else:
            flash(f"❌ Fehler: {result.get('error')}", 'danger')
            return redirect(url_for('design_creation.new_design_request', order_id=order_id))
            
    except Exception as e:
        logger.error(f"Error creating internal task: {e}")
        flash(f'Fehler: {str(e)}', 'danger')
        return redirect(url_for('design_creation.new_design_request', order_id=order_id))


# ==========================================
# ÜBERSICHTEN
# ==========================================

@design_creation_bp.route('/orders')
@login_required
def external_orders():
    """Übersicht externe Design-Bestellungen"""
    
    from src.models.design import DesignOrder
    
    # Filter
    status_filter = request.args.get('status', '')
    
    query = DesignOrder.query
    
    if status_filter:
        query = query.filter(DesignOrder.status == status_filter)
    
    orders = query.order_by(DesignOrder.created_at.desc()).all()
    
    # Statistiken
    stats = {
        'draft': DesignOrder.query.filter_by(status='draft').count(),
        'sent': DesignOrder.query.filter_by(status='sent').count(),
        'in_progress': DesignOrder.query.filter_by(status='in_progress').count(),
        'delivered': DesignOrder.query.filter_by(status='delivered').count(),
        'completed': DesignOrder.query.filter_by(status='completed').count()
    }
    
    return render_template('design_creation/external_orders.html',
        orders=orders,
        stats=stats,
        status_filter=status_filter
    )


@design_creation_bp.route('/tasks')
@login_required
def internal_tasks():
    """Übersicht interne Design-Aufgaben (TODOs)"""
    
    from src.models.todo import Todo
    
    # Filter
    status_filter = request.args.get('status', '')
    assigned_filter = request.args.get('assigned', '')
    
    query = Todo.query.filter(Todo.todo_type == 'design_creation')
    
    if status_filter:
        query = query.filter(Todo.status == status_filter)
    
    if assigned_filter:
        query = query.filter(Todo.assigned_to == assigned_filter)
    
    tasks = query.order_by(Todo.due_date.asc(), Todo.priority.desc()).all()
    
    # Statistiken
    stats = {
        'open': Todo.query.filter_by(todo_type='design_creation', status='open').count(),
        'in_progress': Todo.query.filter_by(todo_type='design_creation', status='in_progress').count(),
        'completed': Todo.query.filter_by(todo_type='design_creation', status='completed').count(),
        'overdue': Todo.query.filter(
            Todo.todo_type == 'design_creation',
            Todo.status.in_(['open', 'in_progress']),
            Todo.due_date < date.today()
        ).count()
    }
    
    return render_template('design_creation/internal_tasks.html',
        tasks=tasks,
        stats=stats,
        status_filter=status_filter,
        today=date.today()
    )


# ==========================================
# EXTERNE BESTELLUNG: DETAIL & AKTIONEN
# ==========================================

@design_creation_bp.route('/order/<order_id>')
@login_required
def external_order_detail(order_id):
    """Detail-Ansicht einer externen Design-Bestellung"""
    
    from src.models.design import DesignOrder
    
    design_order = DesignOrder.query.get_or_404(order_id)
    
    return render_template('design_creation/external_order_detail.html',
        design_order=design_order
    )


@design_creation_bp.route('/order/<order_id>/send-email', methods=['POST'])
@login_required
def send_order_email(order_id):
    """Sendet/Erneut sendet E-Mail an Lieferant"""
    
    from src.models.design import DesignOrder
    from src.services.design_creation_service import get_design_creation_service
    
    design_order = DesignOrder.query.get_or_404(order_id)
    
    service = get_design_creation_service()
    result = service.send_design_order_email(design_order)
    
    if result.get('success'):
        return jsonify({'success': True, 'message': result['message']})
    else:
        return jsonify({'success': False, 'error': result.get('error')}), 500


@design_creation_bp.route('/order/<order_id>/update-status', methods=['POST'])
@login_required
def update_order_status(order_id):
    """Aktualisiert Status einer externen Bestellung"""

    from src.models.design import DesignOrder
    from src.services.design_creation_service import get_design_creation_service

    design_order = DesignOrder.query.get_or_404(order_id)

    new_status = request.form.get('status')
    notes = request.form.get('notes', '')

    if new_status:
        old_status = design_order.status
        design_order.status = new_status
        design_order.add_communication(
            f'Status geändert: {old_status} → {new_status}' + (f' - {notes}' if notes else ''),
            comm_type='note',
            sender=current_user.username
        )

        # Spezielle Aktionen je nach Status
        if new_status == 'delivered':
            design_order.delivered_at = datetime.utcnow()
        elif new_status == 'completed':
            design_order.completed_at = datetime.utcnow()

            # Design in Bibliothek erstellen wenn Datei vorhanden
            if design_order.delivered_file_path and os.path.exists(design_order.delivered_file_path):
                service = get_design_creation_service()
                result = service.create_design_from_external_order(
                    design_order=design_order,
                    delivered_file_path=design_order.delivered_file_path,
                    created_by=current_user.username
                )
                if result.get('success'):
                    flash(f"Design {result['design_number']} erstellt und mit Kunde verknüpft", 'success')
                else:
                    flash(f"Warnung: Design konnte nicht erstellt werden - {result.get('error')}", 'warning')

        db.session.commit()

        flash(f'Status geändert auf: {design_order.status_display}', 'success')

    return redirect(url_for('design_creation.external_order_detail', order_id=order_id))


# ==========================================
# INTERNE AUFGABE: DETAIL & AKTIONEN
# ==========================================

@design_creation_bp.route('/task/<int:task_id>')
@login_required
def internal_task_detail(task_id):
    """Detail-Ansicht einer internen Design-Aufgabe"""
    
    from src.models.todo import Todo
    
    task = Todo.query.get_or_404(task_id)
    
    return render_template('design_creation/internal_task_detail.html',
        task=task
    )


@design_creation_bp.route('/task/<int:task_id>/start', methods=['POST'])
@login_required
def start_task(task_id):
    """Startet Bearbeitung einer Aufgabe"""
    
    from src.models.todo import Todo
    
    task = Todo.query.get_or_404(task_id)
    task.start(current_user.username)
    task.assigned_to = current_user.username
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Bearbeitung gestartet'})


@design_creation_bp.route('/task/<int:task_id>/complete', methods=['POST'])
@login_required
def complete_task(task_id):
    """Markiert Aufgabe als erledigt und erstellt Design in Bibliothek"""

    from src.models.todo import Todo
    from src.services.design_creation_service import get_design_creation_service

    task = Todo.query.get_or_404(task_id)
    notes = request.form.get('notes', '')

    # Aufgabe abschließen
    task.complete(current_user.username, notes)
    db.session.commit()

    # Design in Bibliothek erstellen wenn Ergebnis-Datei vorhanden
    design_created = False
    if task.result_file_path and os.path.exists(task.result_file_path):
        service = get_design_creation_service()
        result = service.create_design_from_task(
            todo=task,
            result_file_path=task.result_file_path,
            created_by=current_user.username
        )
        if result.get('success'):
            design_created = True
            flash(f"Design {result['design_number']} erstellt und mit Kunde verknüpft", 'success')
        else:
            flash(f"Warnung: Design konnte nicht erstellt werden - {result.get('error')}", 'warning')

    flash('Aufgabe als erledigt markiert', 'success')

    if design_created and result.get('design'):
        # Zur Design-Detailseite weiterleiten
        return redirect(url_for('designs.show', design_id=result['design'].id))

    return redirect(url_for('design_creation.internal_tasks'))


@design_creation_bp.route('/task/<int:task_id>/download-pdf')
@login_required
def download_task_pdf(task_id):
    """Lädt Auftragszettel herunter"""

    from flask import send_file
    from src.models.todo import Todo

    task = Todo.query.get_or_404(task_id)

    if task.document_path and os.path.exists(task.document_path):
        return send_file(
            task.document_path,
            as_attachment=True,
            download_name=task.document_name or f'Auftragszettel_{task_id}.pdf'
        )
    else:
        flash('Auftragszettel nicht gefunden', 'danger')
        return redirect(url_for('design_creation.internal_task_detail', task_id=task_id))


@design_creation_bp.route('/task/<int:task_id>/update-progress', methods=['POST'])
@login_required
def update_task_progress(task_id):
    """Aktualisiert den Fortschritt einer Aufgabe"""

    from src.models.todo import Todo

    task = Todo.query.get_or_404(task_id)

    progress = request.form.get('progress', type=int)
    if progress is not None and 0 <= progress <= 100:
        task.progress = progress

        # Bei 100% automatisch auf erledigt setzen
        if progress == 100 and task.status != 'completed':
            task.complete(current_user.username, 'Fortschritt auf 100% gesetzt')
        # Bei Fortschritt > 0 automatisch starten falls noch offen
        elif progress > 0 and task.status == 'open':
            task.start(current_user.username)

        db.session.commit()

        return jsonify({
            'success': True,
            'progress': task.progress,
            'status': task.status,
            'message': f'Fortschritt aktualisiert: {progress}%'
        })

    return jsonify({'success': False, 'error': 'Ungültiger Fortschrittswert'}), 400


@design_creation_bp.route('/task/<int:task_id>/upload-result', methods=['POST'])
@login_required
def upload_task_result(task_id):
    """Lädt Ergebnis-Datei (fertiges Design) hoch"""

    from flask import send_file
    from src.models.todo import Todo
    from werkzeug.utils import secure_filename

    task = Todo.query.get_or_404(task_id)

    if 'result_file' not in request.files:
        flash('Keine Datei ausgewählt', 'danger')
        return redirect(url_for('design_creation.internal_task_detail', task_id=task_id))

    file = request.files['result_file']

    if file.filename == '':
        flash('Keine Datei ausgewählt', 'danger')
        return redirect(url_for('design_creation.internal_task_detail', task_id=task_id))

    try:
        # Upload-Verzeichnis
        upload_dir = os.path.join(current_app.instance_path, 'design_results')
        os.makedirs(upload_dir, exist_ok=True)

        # Dateiname sicher machen
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{task_id}_{timestamp}_{filename}"

        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)

        # Task aktualisieren
        task.result_file_path = file_path
        task.result_file_name = filename

        # Fortschritt auf mindestens 90% setzen
        if task.progress < 90:
            task.progress = 90

        # Kommentar hinzufügen
        task.add_comment(current_user.username, f'Ergebnis-Datei hochgeladen: {filename}')

        db.session.commit()

        flash(f'Datei "{filename}" erfolgreich hochgeladen', 'success')

    except Exception as e:
        logger.error(f"Error uploading result file: {e}")
        flash(f'Fehler beim Hochladen: {str(e)}', 'danger')

    return redirect(url_for('design_creation.internal_task_detail', task_id=task_id))


@design_creation_bp.route('/task/<int:task_id>/download-result')
@login_required
def download_task_result(task_id):
    """Lädt die Ergebnis-Datei herunter"""

    from flask import send_file
    from src.models.todo import Todo

    task = Todo.query.get_or_404(task_id)

    if task.result_file_path and os.path.exists(task.result_file_path):
        return send_file(
            task.result_file_path,
            as_attachment=True,
            download_name=task.result_file_name or f'Design_{task_id}'
        )
    else:
        flash('Ergebnis-Datei nicht gefunden', 'danger')
        return redirect(url_for('design_creation.internal_task_detail', task_id=task_id))


# ==========================================
# DASHBOARD
# ==========================================

@design_creation_bp.route('/')
@login_required
def dashboard():
    """Dashboard für Design-Erstellung"""
    
    from src.models.design import DesignOrder
    from src.models.todo import Todo
    
    # Externe Bestellungen
    pending_external = DesignOrder.query.filter(
        DesignOrder.status.in_(['draft', 'sent', 'quoted', 'in_progress'])
    ).order_by(DesignOrder.created_at.desc()).limit(10).all()
    
    # Interne Aufgaben
    pending_internal = Todo.query.filter(
        Todo.todo_type == 'design_creation',
        Todo.status.in_(['open', 'in_progress'])
    ).order_by(Todo.due_date.asc()).limit(10).all()
    
    # Überfällige
    overdue_tasks = Todo.query.filter(
        Todo.todo_type == 'design_creation',
        Todo.status.in_(['open', 'in_progress']),
        Todo.due_date < date.today()
    ).count()
    
    overdue_orders = DesignOrder.query.filter(
        DesignOrder.status.in_(['sent', 'in_progress']),
        DesignOrder.expected_delivery < date.today()
    ).count()
    
    return render_template('design_creation/dashboard.html',
        pending_external=pending_external,
        pending_internal=pending_internal,
        overdue_tasks=overdue_tasks,
        overdue_orders=overdue_orders
    )


# ==========================================
# HILFSFUNKTIONEN
# ==========================================

def _parse_float(value):
    """Parst Float-Wert oder gibt None zurück"""
    if value:
        try:
            return float(value.replace(',', '.'))
        except:
            pass
    return None

def _parse_int(value):
    """Parst Int-Wert oder gibt None zurück"""
    if value:
        try:
            return int(value)
        except:
            pass
    return None

def _parse_date(value):
    """Parst Datum oder gibt None zurück"""
    if value:
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except:
            pass
    return None
