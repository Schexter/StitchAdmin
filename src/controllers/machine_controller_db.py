"""
Machine Controller - PostgreSQL-Version
Maschinen-Verwaltung mit Datenbank
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from src.models import db, Machine, Order, ProductionSchedule, ActivityLog
import json

# Blueprint erstellen
machine_bp = Blueprint('machines', __name__, url_prefix='/machines')

def log_activity(action, details):
    """Aktivität in Datenbank protokollieren"""
    activity = ActivityLog(
        username=current_user.username,  # Geändert von 'user' zu 'username'
        action=action,
        details=details,
        ip_address=request.remote_addr
    )
    db.session.add(activity)
    db.session.commit()

def generate_machine_id():
    """Generiere neue Maschinen-ID"""
    last_machine = Machine.query.filter(
        Machine.id.like('M%')
    ).order_by(Machine.id.desc()).first()

    if last_machine:
        try:
            last_num = int(last_machine.id[1:])
            return f"M{last_num + 1:03d}"
        except:
            return "M001"
    return "M001"

@machine_bp.route('/<machine_id>/threads')
@login_required
def machine_threads(machine_id):
    """Garn-Übersicht für eine Maschine"""
    from src.models import Thread, ThreadUsage
    from sqlalchemy import func

    machine = Machine.query.get_or_404(machine_id)

    # Zeitraum-Filter
    period = request.args.get('period', '30')
    days = int(period)
    start_date = datetime.utcnow() - timedelta(days=days)

    # Garnverbrauch dieser Maschine (historisch)
    thread_usage_stats = db.session.query(
        Thread.manufacturer,
        Thread.color_number,
        Thread.color_name_de,
        Thread.hex_color,
        func.sum(ThreadUsage.quantity_used).label('total_used'),
        func.count(ThreadUsage.id).label('usage_count'),
        func.max(ThreadUsage.used_at).label('last_used')
    ).join(ThreadUsage, Thread.id == ThreadUsage.thread_id)\
     .filter(ThreadUsage.machine_id == machine_id, ThreadUsage.used_at >= start_date)\
     .group_by(Thread.id)\
     .order_by(func.sum(ThreadUsage.quantity_used).desc())\
     .limit(50).all()

    # Aktuelle/geplante Aufträge für diese Maschine
    current_orders = Order.query.filter(
        Order.assigned_machine_id == machine_id,
        Order.status.in_(['accepted', 'in_progress'])
    ).order_by(Order.due_date).all()

    # Garnbedarf für aktuelle Aufträge
    required_threads = []
    for order in current_orders:
        if order.selected_threads:
            try:
                threads_data = json.loads(order.selected_threads)
                for thread_data in threads_data:
                    thread_id = thread_data.get('thread_id')
                    if thread_id:
                        thread = Thread.query.get(thread_id)
                        if thread:
                            # Berechne geschätzten Bedarf
                            estimated_usage = 0
                            if order.stitch_count:
                                estimated_usage = (order.stitch_count * 0.5 / 1000) * 1.1
                                estimated_usage /= len(threads_data)  # Verteilt auf alle Garne

                            required_threads.append({
                                'thread': thread,
                                'order': order,
                                'estimated_usage': estimated_usage
                            })
            except:
                pass

    # Gesamtstatistik
    total_usage = db.session.query(
        func.sum(ThreadUsage.quantity_used)
    ).filter(ThreadUsage.machine_id == machine_id, ThreadUsage.used_at >= start_date).scalar() or 0

    return render_template('machines/thread_overview.html',
                         machine=machine,
                         thread_stats=thread_usage_stats,
                         required_threads=required_threads,
                         current_orders=current_orders,
                         total_usage=total_usage,
                         period=period)

@machine_bp.route('/')
@login_required
def index():
    """Maschinen-Übersicht"""
    machine_type = request.args.get('type', '')
    
    # Query erstellen
    query = Machine.query
    
    if machine_type:
        query = query.filter_by(type=machine_type)
    
    # Nach Name sortieren
    machines_list = query.order_by(Machine.name).all()
    
    # In Dictionary umwandeln für Template-Kompatibilität
    machines = {}
    for machine in machines_list:
        machines[machine.id] = machine
    
    # Maschinentypen für Filter
    machine_types = db.session.query(Machine.type).distinct().filter(Machine.type.isnot(None)).all()
    machine_types = [t[0] for t in machine_types if t[0]]
    
    return render_template('machines/index.html',
                         machines=machines,
                         machine_types=machine_types,
                         selected_type=machine_type)

@machine_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Neue Maschine erstellen"""
    if request.method == 'POST':
        # Neue Maschine erstellen
        machine = Machine(
            id=generate_machine_id(),
            name=request.form.get('name'),
            type=request.form.get('type', 'embroidery'),
            manufacturer=request.form.get('manufacturer', ''),
            model=request.form.get('model', ''),
            serial_number=request.form.get('serial_number', ''),
            purchase_date=request.form.get('purchase_date') or None,
            status='active',
            created_by=current_user.username
        )
        
        # Type-spezifische Felder
        if machine.type == 'embroidery':
            machine.num_heads = int(request.form.get('num_heads', 1) or 1)
            machine.needles_per_head = int(request.form.get('needles_per_head', 15) or 15)
            machine.max_speed = int(request.form.get('max_speed', 1000) or 1000)
            machine.max_area_width = int(request.form.get('max_area_width', 0) or 0)
            machine.max_area_height = int(request.form.get('max_area_height', 0) or 0)
            machine.setup_time_minutes = int(request.form.get('setup_time_minutes', 15) or 15)
            machine.thread_change_time_minutes = int(request.form.get('thread_change_time_minutes', 3) or 3)
            machine.hoop_change_time_minutes = int(request.form.get('hoop_change_time_minutes', 5) or 5)
        
        # Wartungsintervall
        if request.form.get('maintenance_interval_days'):
            machine.maintenance_due = date.today() + timedelta(days=int(request.form.get('maintenance_interval_days')))
        
        # In Datenbank speichern
        db.session.add(machine)
        db.session.commit()
        
        # Aktivität protokollieren
        log_activity('machine_created', 
                    f'Maschine erstellt: {machine.id} - {machine.name}')
        
        flash(f'Maschine {machine.name} wurde erstellt!', 'success')
        return redirect(url_for('machines.show', machine_id=machine.id))
    
    return render_template('machines/new.html')

@machine_bp.route('/<machine_id>')
@login_required
def show(machine_id):
    """Maschinen-Details anzeigen"""
    machine = Machine.query.get_or_404(machine_id)
    
    # Aktuelle Aufträge für diese Maschine
    current_orders = Order.query.filter_by(
        assigned_machine_id=machine_id,
        status='in_progress'
    ).all()
    
    # Geplante Aufträge
    scheduled_orders = ProductionSchedule.query.filter_by(
        machine_id=machine_id,
        status='scheduled'
    ).filter(
        ProductionSchedule.scheduled_start >= datetime.now()
    ).order_by(ProductionSchedule.scheduled_start).limit(5).all()
    
    # Wartungsstatus berechnen
    if machine.maintenance_due:
        days_until_maintenance = (machine.maintenance_due - date.today()).days
        if days_until_maintenance < 0:
            maintenance_status = 'danger'
            maintenance_text = 'Überfällig!'
        elif days_until_maintenance <= 7:
            maintenance_status = 'warning'
            maintenance_text = f'In {days_until_maintenance} Tagen fällig'
        else:
            maintenance_status = 'success'
            maintenance_text = f'In {days_until_maintenance} Tagen fällig'
    else:
        maintenance_status = 'info'
        maintenance_text = 'Nicht geplant'
    
    return render_template('machines/show.html',
                         machine=machine,
                         current_orders=current_orders,
                         scheduled_orders=scheduled_orders,
                         maintenance_status=maintenance_status,
                         maintenance_text=maintenance_text)

@machine_bp.route('/<machine_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(machine_id):
    """Maschine bearbeiten"""
    machine = Machine.query.get_or_404(machine_id)
    
    if request.method == 'POST':
        # Maschine aktualisieren
        machine.name = request.form.get('name')
        machine.manufacturer = request.form.get('manufacturer', '')
        machine.model = request.form.get('model', '')
        machine.serial_number = request.form.get('serial_number', '')
        machine.purchase_date = request.form.get('purchase_date') or None
        machine.status = request.form.get('status', 'active')
        machine.updated_at = datetime.utcnow()
        machine.updated_by = current_user.username
        
        # Type-spezifische Felder
        if machine.type == 'embroidery':
            machine.num_heads = int(request.form.get('num_heads', 1) or 1)
            machine.needles_per_head = int(request.form.get('needles_per_head', 15) or 15)
            machine.max_speed = int(request.form.get('max_speed', 1000) or 1000)
            machine.max_area_width = int(request.form.get('max_area_width', 0) or 0)
            machine.max_area_height = int(request.form.get('max_area_height', 0) or 0)
            machine.setup_time_minutes = int(request.form.get('setup_time_minutes', 15) or 15)
            machine.thread_change_time_minutes = int(request.form.get('thread_change_time_minutes', 3) or 3)
            machine.hoop_change_time_minutes = int(request.form.get('hoop_change_time_minutes', 5) or 5)
        
        # Änderungen speichern
        db.session.commit()
        
        # Aktivität protokollieren
        log_activity('machine_updated', 
                    f'Maschine aktualisiert: {machine.id} - {machine.name}')
        
        flash(f'Maschine {machine.name} wurde aktualisiert!', 'success')
        return redirect(url_for('machines.show', machine_id=machine.id))
    
    return render_template('machines/edit.html', machine=machine)

@machine_bp.route('/<machine_id>/delete', methods=['POST'])
@login_required
def delete(machine_id):
    """Maschine löschen"""
    machine = Machine.query.get_or_404(machine_id)
    machine_name = machine.name
    
    # Prüfen ob Maschine aktive Aufträge hat
    active_orders = Order.query.filter_by(
        assigned_machine_id=machine_id
    ).filter(
        Order.status.in_(['accepted', 'in_progress'])
    ).count()
    
    if active_orders > 0:
        flash(f'Maschine {machine_name} kann nicht gelöscht werden, da noch aktive Aufträge vorhanden sind!', 'danger')
        return redirect(url_for('machines.show', machine_id=machine_id))
    
    # Aktivität protokollieren bevor gelöscht wird
    log_activity('machine_deleted', 
                f'Maschine gelöscht: {machine.id} - {machine_name}')
    
    # Maschine löschen
    db.session.delete(machine)
    db.session.commit()
    
    flash(f'Maschine {machine_name} wurde gelöscht!', 'success')
    return redirect(url_for('machines.index'))

@machine_bp.route('/<machine_id>/maintenance', methods=['POST'])
@login_required
def record_maintenance(machine_id):
    """Wartung durchgeführt"""
    machine = Machine.query.get_or_404(machine_id)
    
    machine.last_maintenance = date.today()
    
    # Nächste Wartung berechnen
    interval = int(request.form.get('interval_days', 90))
    machine.maintenance_due = date.today() + timedelta(days=interval)
    
    machine.updated_at = datetime.utcnow()
    machine.updated_by = current_user.username
    
    db.session.commit()
    
    # Aktivität protokollieren
    log_activity('machine_maintenance', 
                f'Wartung durchgeführt: {machine.id} - {machine.name}')
    
    flash(f'Wartung für {machine.name} wurde dokumentiert!', 'success')
    return redirect(url_for('machines.show', machine_id=machine_id))

@machine_bp.route('/<machine_id>/schedule')
@login_required
def schedule(machine_id):
    """Planungsansicht für Maschine"""
    machine = Machine.query.get_or_404(machine_id)
    
    # Geplante Aufträge für die nächsten 7 Tage
    start_date = datetime.now()
    end_date = start_date + timedelta(days=7)
    
    scheduled_items = ProductionSchedule.query.filter(
        ProductionSchedule.machine_id == machine_id,
        ProductionSchedule.scheduled_start >= start_date,
        ProductionSchedule.scheduled_start <= end_date
    ).order_by(ProductionSchedule.scheduled_start).all()
    
    # Verfügbare Zeitslots berechnen
    available_slots = []
    work_start = 8  # 8:00 Uhr
    work_end = 17   # 17:00 Uhr
    
    for day_offset in range(7):
        check_date = start_date.date() + timedelta(days=day_offset)
        
        # Prüfe ob Wochenende
        if check_date.weekday() < 5:  # Montag-Freitag
            # Finde belegte Zeiten für diesen Tag
            day_schedules = [s for s in scheduled_items 
                           if s.scheduled_start.date() == check_date]
            
            # Berechne freie Slots
            current_time = datetime.combine(check_date, datetime.min.time().replace(hour=work_start))
            end_time = datetime.combine(check_date, datetime.min.time().replace(hour=work_end))
            
            for schedule in sorted(day_schedules, key=lambda x: x.scheduled_start):
                if current_time < schedule.scheduled_start:
                    available_slots.append({
                        'date': check_date,
                        'start': current_time.time(),
                        'end': schedule.scheduled_start.time(),
                        'duration_hours': (schedule.scheduled_start - current_time).total_seconds() / 3600
                    })
                current_time = schedule.scheduled_end
            
            # Slot bis Arbeitsende
            if current_time < end_time:
                available_slots.append({
                    'date': check_date,
                    'start': current_time.time(),
                    'end': end_time.time(),
                    'duration_hours': (end_time - current_time).total_seconds() / 3600
                })
    
    return render_template('machines/schedule.html',
                         machine=machine,
                         jobs=scheduled_items,  # Template erwartet 'jobs'
                         scheduled_items=scheduled_items,
                         available_slots=available_slots,
                         start_date=start_date,
                         end_date=end_date)

@machine_bp.route('/<machine_id>/thread-setup', methods=['GET', 'POST'])
@login_required
def thread_setup(machine_id):
    """Garn-Setup für Maschine"""
    machine = Machine.query.get_or_404(machine_id)
    
    if request.method == 'POST':
        # Thread-Setup speichern
        setup_data = []
        
        # Strukturiere die Daten wie das Template es erwartet
        for head_num in range(machine.num_heads or 1):
            head_threads = []
            for needle_num in range(machine.needles_per_head or 15):
                thread_id = request.form.get(f'head_{head_num}_needle_{needle_num}_thread')
                if thread_id:
                    head_threads.append({
                        'needle_position': needle_num + 1,
                        'thread_id': thread_id
                    })
            
            if head_threads:
                setup_data.append({
                    'head_number': head_num + 1,
                    'threads': head_threads
                })
        
        machine.set_thread_setup(setup_data)
        machine.updated_at = datetime.utcnow()
        machine.updated_by = current_user.username
        
        db.session.commit()
        
        # Aktivität protokollieren
        log_activity('machine_thread_setup', 
                    f'Garn-Setup aktualisiert: {machine.id} - {machine.name}')
        
        flash(f'Garn-Setup für {machine.name} wurde gespeichert!', 'success')
        return redirect(url_for('machines.show', machine_id=machine_id))
    
    # Verfügbare Garne laden
    from src.models import Thread
    threads = Thread.query.filter_by(active=True).order_by(Thread.manufacturer, Thread.color_number).all()
    
    # In Dictionary umwandeln für Template-Kompatibilität
    available_threads = {}
    for thread in threads:
        available_threads[thread.id] = {
            'brand': thread.manufacturer,
            'color_code': thread.color_number,
            'color_name': thread.color_name_de or thread.color_name_en,
            'color_hex': thread.hex_color or '#cccccc',
            'stock': getattr(thread.stock, 'quantity', 0) if thread.stock else 0
        }
    
    return render_template('machines/thread_setup.html',
                         machine=machine,
                         available_threads=available_threads,
                         current_setup=machine.get_thread_setup())

# API-Endpoints
@machine_bp.route('/api/status')
@login_required
def api_machine_status():
    """Maschinen-Status für Dashboard"""
    machines = Machine.query.all()
    
    status_data = []
    for machine in machines:
        # Aktueller Auftrag
        current_order = Order.query.filter_by(
            assigned_machine_id=machine.id,
            status='in_progress'
        ).first()
        
        status_data.append({
            'id': machine.id,
            'name': machine.name,
            'type': machine.type,
            'status': machine.status,
            'current_order': current_order.id if current_order else None,
            'current_order_progress': 0  # TODO: Fortschritt berechnen
        })
    
    return jsonify(status_data)

# Hilfsfunktionen
def get_machine_by_id(machine_id):
    """Maschine nach ID abrufen"""
    return Machine.query.get(machine_id)
