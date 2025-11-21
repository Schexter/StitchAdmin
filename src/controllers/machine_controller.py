"""
Machine Controller - Maschinen-Verwaltung für Stickerei & Textildruck
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
import json
import os
from datetime import datetime, timedelta
from src.utils.activity_logger import log_activity

# Blueprint erstellen
machine_bp = Blueprint('machines', __name__, url_prefix='/machines')

MACHINES_FILE = 'machines.json'
MACHINE_SCHEDULE_FILE = 'machine_schedule.json'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Bitte melden Sie sich an.', 'info')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def load_machines():
    """Lade Maschinen aus JSON-Datei"""
    if os.path.exists(MACHINES_FILE):
        with open(MACHINES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_machines(machines):
    """Speichere Maschinen in JSON-Datei"""
    with open(MACHINES_FILE, 'w', encoding='utf-8') as f:
        json.dump(machines, f, indent=2, ensure_ascii=False)

def load_machine_schedule():
    """Lade Maschinenbelegungsplan"""
    if os.path.exists(MACHINE_SCHEDULE_FILE):
        with open(MACHINE_SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_machine_schedule(schedule):
    """Speichere Maschinenbelegungsplan"""
    with open(MACHINE_SCHEDULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(schedule, f, indent=2, ensure_ascii=False)

def generate_machine_id():
    """Generiere neue Maschinen-ID"""
    machines = load_machines()
    if not machines:
        return "M001"
    
    # Finde höchste ID
    max_num = 0
    for machine_id in machines.keys():
        if machine_id.startswith('M'):
            try:
                num = int(machine_id[1:])
                max_num = max(max_num, num)
            except:
                pass
    
    return f"M{max_num + 1:03d}"

@machine_bp.route('/')
@login_required
def index():
    """Maschinen-Übersicht"""
    machines = load_machines()
    schedule = load_machine_schedule()
    
    # Aktueller Status der Maschinen
    current_time = datetime.now()
    for machine_id, machine in machines.items():
        # Prüfe aktuelle Belegung
        machine_schedule = schedule.get(machine_id, [])
        machine['current_status'] = 'available'
        machine['current_job'] = None
        
        for job in machine_schedule:
            start_time = datetime.fromisoformat(job['start_time'])
            end_time = datetime.fromisoformat(job['end_time'])
            
            if start_time <= current_time <= end_time:
                machine['current_status'] = 'busy'
                machine['current_job'] = job
                break
    
    return render_template('machines/index.html', machines=machines)

@machine_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Neue Maschine anlegen"""
    if request.method == 'POST':
        machines = load_machines()
        machine_id = generate_machine_id()
        
        machine = {
            'id': machine_id,
            'name': request.form.get('name', ''),
            'type': request.form.get('type', 'embroidery'),  # embroidery, dtf, dtg, vinyl, sublimation
            'manufacturer': request.form.get('manufacturer', ''),
            'model': request.form.get('model', ''),
            'serial_number': request.form.get('serial_number', ''),
            'purchase_date': request.form.get('purchase_date', ''),
            'status': 'active',  # active, inactive, maintenance
            'location': request.form.get('location', ''),
            'notes': request.form.get('notes', ''),
            # Technische Spezifikationen
            'max_embroidery_area_width': int(request.form.get('max_embroidery_area_width', 400)),  # mm
            'max_embroidery_area_height': int(request.form.get('max_embroidery_area_height', 400)),  # mm
            'max_speed': int(request.form.get('max_speed', 1000)),  # Stiche/min
            'num_heads': int(request.form.get('num_heads', 1)),  # Anzahl Stickköpfe
            'needles_per_head': int(request.form.get('needles_per_head', 15)),  # Nadeln pro Kopf
            'num_needles': int(request.form.get('num_heads', 1)) * int(request.form.get('needles_per_head', 15)),  # Gesamt-Nadeln
            'hoop_sizes': request.form.get('hoop_sizes', '').split(','),  # Liste der verfügbaren Rahmengrößen
            # Garnkonfiguration pro Kopf
            'thread_setup': [],  # Wird später gefüllt
            # Rüstzeiten
            'setup_time_minutes': int(request.form.get('setup_time_minutes', 15)),  # Standard-Rüstzeit
            'thread_change_time_minutes': int(request.form.get('thread_change_time_minutes', 3)),  # Zeit pro Garnwechsel
            'hoop_change_time_minutes': int(request.form.get('hoop_change_time_minutes', 5)),  # Zeit für Rahmenwechsel
            # DTF-spezifische Einstellungen
            'max_print_width': int(request.form.get('max_print_width', 600)) if request.form.get('type') == 'dtf' else 0,  # mm
            'print_resolution': request.form.get('print_resolution', '1200x1200') if request.form.get('type') == 'dtf' else '',
            # Betriebszeiten
            'operating_hours_start': request.form.get('operating_hours_start', '08:00'),
            'operating_hours_end': request.form.get('operating_hours_end', '18:00'),
            'working_days': request.form.getlist('working_days[]'),  # Mo-So
            # Wartung
            'last_maintenance': request.form.get('last_maintenance', ''),
            'next_maintenance': request.form.get('next_maintenance', ''),
            'maintenance_interval_days': int(request.form.get('maintenance_interval_days', 90)),
            'created_at': datetime.now().isoformat(),
            'created_by': session['username']
        }
        
        machines[machine_id] = machine
        save_machines(machines)
        log_activity(session['username'], 'create_machine', f'Maschine {machine_id} ({machine["name"]}) wurde angelegt')
        
        flash(f'Maschine {machine_id} wurde angelegt!', 'success')
        return redirect(url_for('machines.show', machine_id=machine_id))
    
    return render_template('machines/new.html')

@machine_bp.route('/<machine_id>')
@login_required
def show(machine_id):
    """Maschinendetails anzeigen"""
    machines = load_machines()
    machine = machines.get(machine_id)
    
    if not machine:
        flash('Maschine nicht gefunden!', 'danger')
        return redirect(url_for('machines.index'))
    
    # Lade Belegungsplan für die nächsten 7 Tage
    schedule = load_machine_schedule()
    machine_schedule = schedule.get(machine_id, [])
    
    # Filtere zukünftige Jobs
    current_time = datetime.now()
    upcoming_jobs = []
    for job in machine_schedule:
        if datetime.fromisoformat(job['start_time']) >= current_time:
            upcoming_jobs.append(job)
    
    # Sortiere nach Startzeit
    upcoming_jobs.sort(key=lambda x: x['start_time'])
    
    # Berechne nächstes Wartungsdatum
    next_maintenance_calculated = None
    if machine.get('last_maintenance') and machine.get('maintenance_interval_days'):
        try:
            last_maintenance = datetime.strptime(machine['last_maintenance'], '%Y-%m-%d')
            next_maintenance_calculated = (last_maintenance + timedelta(days=machine['maintenance_interval_days'])).strftime('%Y-%m-%d')
        except:
            pass
    
    return render_template('machines/show.html', 
                         machine=machine, 
                         upcoming_jobs=upcoming_jobs[:10],  # Zeige nur nächste 10 Jobs
                         next_maintenance_calculated=next_maintenance_calculated)

@machine_bp.route('/<machine_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(machine_id):
    """Maschine bearbeiten"""
    machines = load_machines()
    machine = machines.get(machine_id)
    
    if not machine:
        flash('Maschine nicht gefunden!', 'danger')
        return redirect(url_for('machines.index'))
    
    if request.method == 'POST':
        # Update machine details
        machine['name'] = request.form.get('name', machine['name'])
        machine['type'] = request.form.get('type', machine['type'])
        machine['manufacturer'] = request.form.get('manufacturer', machine['manufacturer'])
        machine['model'] = request.form.get('model', machine['model'])
        machine['serial_number'] = request.form.get('serial_number', machine['serial_number'])
        machine['purchase_date'] = request.form.get('purchase_date', machine['purchase_date'])
        machine['status'] = request.form.get('status', machine['status'])
        machine['location'] = request.form.get('location', machine['location'])
        machine['notes'] = request.form.get('notes', machine['notes'])
        
        # Technische Daten
        machine['max_embroidery_area_width'] = int(request.form.get('max_embroidery_area_width', machine.get('max_embroidery_area_width', 400)))
        machine['max_embroidery_area_height'] = int(request.form.get('max_embroidery_area_height', machine.get('max_embroidery_area_height', 400)))
        machine['max_speed'] = int(request.form.get('max_speed', machine.get('max_speed', 1000)))
        machine['num_needles'] = int(request.form.get('num_needles', machine.get('num_needles', 15)))
        machine['hoop_sizes'] = request.form.get('hoop_sizes', '').split(',')
        
        if machine['type'] == 'dtf':
            machine['max_print_width'] = int(request.form.get('max_print_width', machine.get('max_print_width', 600)))
            machine['print_resolution'] = request.form.get('print_resolution', machine.get('print_resolution', '1200x1200'))
        
        # Betriebszeiten
        machine['operating_hours_start'] = request.form.get('operating_hours_start', machine.get('operating_hours_start', '08:00'))
        machine['operating_hours_end'] = request.form.get('operating_hours_end', machine.get('operating_hours_end', '18:00'))
        machine['working_days'] = request.form.getlist('working_days[]')
        
        # Wartung
        machine['last_maintenance'] = request.form.get('last_maintenance', machine.get('last_maintenance', ''))
        machine['next_maintenance'] = request.form.get('next_maintenance', machine.get('next_maintenance', ''))
        machine['maintenance_interval_days'] = int(request.form.get('maintenance_interval_days', machine.get('maintenance_interval_days', 90)))
        
        machine['updated_at'] = datetime.now().isoformat()
        machine['updated_by'] = session['username']
        
        save_machines(machines)
        log_activity(session['username'], 'update_machine', f'Maschine {machine_id} wurde aktualisiert')
        
        flash('Maschine wurde aktualisiert!', 'success')
        return redirect(url_for('machines.show', machine_id=machine_id))
    
    return render_template('machines/edit.html', machine=machine)

@machine_bp.route('/<machine_id>/schedule', methods=['GET', 'POST'])
@login_required
def schedule(machine_id):
    """Maschinenbelegung planen"""
    machines = load_machines()
    machine = machines.get(machine_id)
    
    if not machine:
        flash('Maschine nicht gefunden!', 'danger')
        return redirect(url_for('machines.index'))
    
    if request.method == 'POST':
        schedule_data = load_machine_schedule()
        if machine_id not in schedule_data:
            schedule_data[machine_id] = []
        
        # Neuen Job hinzufügen
        job = {
            'id': len(schedule_data[machine_id]) + 1,
            'order_id': request.form.get('order_id', ''),
            'job_title': request.form.get('job_title', ''),
            'start_time': request.form.get('start_time', ''),
            'end_time': request.form.get('end_time', ''),
            'estimated_duration_minutes': int(request.form.get('estimated_duration_minutes', 60)),
            'priority': request.form.get('priority', 'normal'),
            'notes': request.form.get('notes', ''),
            'status': 'scheduled',  # scheduled, in_progress, completed, cancelled
            'created_at': datetime.now().isoformat(),
            'created_by': session['username']
        }
        
        schedule_data[machine_id].append(job)
        save_machine_schedule(schedule_data)
        
        flash('Job wurde eingeplant!', 'success')
        return redirect(url_for('machines.schedule', machine_id=machine_id))
    
    # Lade aktuelle Belegung
    schedule_data = load_machine_schedule()
    machine_jobs = schedule_data.get(machine_id, [])
    
    # Sortiere nach Startzeit
    machine_jobs.sort(key=lambda x: x['start_time'])
    
    return render_template('machines/schedule.html', 
                         machine=machine, 
                         jobs=machine_jobs)

@machine_bp.route('/api/availability')
@login_required
def api_availability():
    """API-Endpoint für Maschinenverfügbarkeit"""
    machine_type = request.args.get('type', 'embroidery')
    start_date = request.args.get('start_date', datetime.now().date().isoformat())
    
    machines = load_machines()
    schedule = load_machine_schedule()
    
    available_machines = []
    for machine_id, machine in machines.items():
        if machine['type'] == machine_type and machine['status'] == 'active':
            # Berechne freie Slots für den Tag
            machine_schedule = schedule.get(machine_id, [])
            # Vereinfachte Verfügbarkeit (kann erweitert werden)
            available_machines.append({
                'id': machine_id,
                'name': machine['name'],
                'location': machine['location'],
                'available_hours': 8  # Beispielwert
            })
    
    return jsonify(available_machines)

@machine_bp.route('/<machine_id>/thread_setup', methods=['GET', 'POST'])
@login_required
def thread_setup(machine_id):
    """Garnkonfiguration für Stickmaschine verwalten"""
    machines = load_machines()
    machine = machines.get(machine_id)
    
    if not machine:
        flash('Maschine nicht gefunden!', 'danger')
        return redirect(url_for('machines.index'))
    
    if machine.get('type') != 'embroidery':
        flash('Garnkonfiguration nur für Stickmaschinen verfügbar!', 'warning')
        return redirect(url_for('machines.show', machine_id=machine_id))
    
    if request.method == 'POST':
        # Garnkonfiguration verarbeiten
        thread_setup = []
        num_heads = machine.get('num_heads', 1)
        needles_per_head = machine.get('needles_per_head', 15)
        
        for head in range(num_heads):
            head_setup = {
                'head_number': head + 1,
                'threads': []
            }
            
            for needle in range(needles_per_head):
                thread_id = request.form.get(f'head_{head}_needle_{needle}_thread')
                if thread_id:
                    head_setup['threads'].append({
                        'needle_position': needle + 1,
                        'thread_id': thread_id
                    })
            
            thread_setup.append(head_setup)
        
        machine['thread_setup'] = thread_setup
        machine['thread_setup_updated'] = datetime.now().isoformat()
        machine['thread_setup_updated_by'] = session['username']
        
        save_machines(machines)
        log_activity(session['username'], 'update_machine_threads', f'Garnkonfiguration für Maschine {machine_id} aktualisiert')
        
        flash('Garnkonfiguration wurde gespeichert!', 'success')
        return redirect(url_for('machines.thread_setup', machine_id=machine_id))
    
    # Lade verfügbare Garne
    try:
        from src.controllers.thread_controller import load_threads_dict, load_thread_stock
        threads = load_threads_dict()
        thread_stock = load_thread_stock()
        
        # Alle Garne mit Bestandsinformation
        available_threads = {}
        for thread_id, thread in threads.items():
            stock = thread_stock.get(thread_id, {}).get('quantity', 0)
            thread_data = thread.copy()
            thread_data['stock'] = stock
            available_threads[thread_id] = thread_data
                
    except ImportError as e:
        print(f"Import error: {e}")
        available_threads = {}
    except Exception as e:
        print(f"Error loading threads: {e}")
        available_threads = {}
    
    return render_template('machines/thread_setup.html', 
                         machine=machine,
                         available_threads=available_threads)

def calculate_embroidery_production_time(machine, order):
    """Berechnet realistische Produktionszeit für Stickauftrag"""
    stitch_count = order.get('stitch_count', 5000)
    quantity = order.get('quantity', 1)
    
    # Maschinengeschwindigkeit berücksichtigen
    machine_speed = machine.get('max_speed', 1000)  # Stiche/min
    practical_speed = machine_speed * 0.7  # 70% der max. Geschwindigkeit in der Praxis
    
    # Grundzeit pro Stück (reine Stickzeit)
    embroidery_time_per_piece = stitch_count / practical_speed  # Minuten
    
    # Rüstzeit einmalig
    setup_time = machine.get('setup_time_minutes', 15)
    
    # Garnwechselzeit - ermitteln aus Auftrag
    thread_colors = order.get('thread_colors', '').split(',')
    color_changes = max(1, len([c for c in thread_colors if c.strip()]))
    thread_change_time = color_changes * machine.get('thread_change_time_minutes', 3)
    
    # Rahmenwechselzeit zwischen Stücken (bei mehr als 1 Stück)
    hoop_changes = max(0, quantity - 1)
    hoop_change_time = hoop_changes * machine.get('hoop_change_time_minutes', 5)
    
    # Gesamtzeit
    total_time = setup_time + (embroidery_time_per_piece * quantity) + thread_change_time + hoop_change_time
    
    # Pufferzeit (10% für unvorhergesehene Unterbrechungen)
    total_time *= 1.1
    
    return {
        'total_minutes': round(total_time),
        'embroidery_time': round(embroidery_time_per_piece * quantity),
        'setup_time': setup_time,
        'thread_change_time': thread_change_time,
        'hoop_change_time': hoop_change_time,
        'machine_speed_used': practical_speed,
        'efficiency_factor': 0.7
    }