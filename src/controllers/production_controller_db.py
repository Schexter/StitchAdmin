"""
Production Controller - PostgreSQL-Version
Produktions-Verwaltung mit Datenbank
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from src.models import db, Order, Machine, ProductionSchedule, ActivityLog, PackingList, PostEntry, CompanySettings
from sqlalchemy import and_
import json
import os

# Blueprint erstellen
production_bp = Blueprint('production', __name__, url_prefix='/production')

def load_production_settings():
    """Lade Produktions-Einstellungen aus JSON-Datei"""
    settings_file = 'production_settings.json'
    default_settings = {
        'work_start': 8,
        'work_end': 17,
        'lunch_start': 12,
        'lunch_end': 13,
        'distraction_factor': 0.85
    }
    
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)
                # Konvertiere zu einfacherer Struktur für Template
                return {
                    'work_start': 8,
                    'work_end': 17,
                    'lunch_start': 12,
                    'lunch_end': 13,
                    'distraction_factor': settings_data.get('production_factors', {}).get('distraction_factor', 0.85),
                    'color_scheme': settings_data.get('calendar_settings', {}).get('color_scheme', {})
                }
        except Exception as e:
            print(f"Fehler beim Laden der Produktions-Einstellungen: {e}")
    
    return default_settings

def calculate_thread_requirements(order):
    """Berechne Garnbedarf für einen Auftrag"""
    thread_requirements = []
    
    if not order.stitch_count or order.stitch_count == 0:
        return thread_requirements
    
    # Standard: 5.5 Meter Garn pro 1000 Stiche
    THREAD_PER_1000_STITCHES = 5.5
    
    # Berechne Gesamtgarnbedarf
    total_thread_meters = (order.stitch_count / 1000) * THREAD_PER_1000_STITCHES
    
    # Sicherheitsfaktor 15% für Verschnitt, Fadenbruch etc.
    total_thread_meters *= 1.15
    
    # Wenn Farbinformationen vorhanden sind
    if order.selected_threads:
        try:
            selected_threads = json.loads(order.selected_threads) if isinstance(order.selected_threads, str) else order.selected_threads
            num_colors = len(selected_threads)
            
            for thread_id in selected_threads:
                from src.models import Thread, ThreadStock
                thread = Thread.query.get(thread_id)
                if thread:
                    # Anteiliger Garnbedarf pro Farbe (vereinfacht)
                    thread_meters_per_color = total_thread_meters / num_colors
                    
                    # Hole Lagerbestand
                    stock = ThreadStock.query.filter_by(thread_id=thread_id).first()
                    current_stock = stock.quantity if stock else 0
                    min_stock = stock.min_stock if stock else 5
                    
                    # Prüfe ob genug auf Lager
                    is_sufficient = current_stock >= (thread_meters_per_color / 5000)  # Umrechnung in Konen (5000m pro Kone)
                    
                    thread_requirements.append({
                        'thread': thread,
                        'meters_needed': round(thread_meters_per_color, 1),
                        'cones_needed': round(thread_meters_per_color / 5000, 2),  # Standard: 5000m pro Kone
                        'current_stock': current_stock,
                        'min_stock': min_stock,
                        'is_sufficient': is_sufficient,
                        'is_low_stock': current_stock <= min_stock
                    })
        except Exception as e:
            print(f"Fehler bei Garnbedarfsberechnung: {e}")
    
    return thread_requirements

def log_activity(action, details):
    """Aktivität in Datenbank protokollieren"""
    activity = ActivityLog(
        username=current_user.username,
        action=action,
        details=details,
        ip_address=request.remote_addr
    )
    db.session.add(activity)
    db.session.commit()

def _record_automatic_thread_usage(order):
    """
    Erfasst automatisch Garnverbrauch beim Produktionsabschluss

    Basierend auf:
    - order.selected_threads (JSON mit ausgewählten Garnen)
    - order.stitch_count (Anzahl Stiche)
    - order.assigned_machine_id (Zugewiesene Maschine)
    """
    from src.models import Thread, ThreadStock, ThreadUsage

    # Nur für Stickerei-Aufträge
    if order.order_type not in ['embroidery', 'combined']:
        return

    # Prüfe ob Stichanzahl vorhanden
    if not order.stitch_count or order.stitch_count == 0:
        print(f"[INFO] Kein stitch_count für Auftrag {order.id}, überspringe Garnverbrauchserfassung")
        return

    # Parse selected_threads JSON
    selected_threads = []
    if order.selected_threads:
        try:
            selected_threads = json.loads(order.selected_threads)
        except:
            # Fallback: Verwende thread_colors als Komma-getrennte Liste
            if order.thread_colors:
                thread_colors = [c.strip() for c in order.thread_colors.split(',')]
                # Versuche Threads zu finden
                for color in thread_colors:
                    threads = Thread.query.filter(
                        db.or_(
                            Thread.color_number == color,
                            Thread.color_name_de.ilike(f'%{color}%')
                        )
                    ).all()
                    if threads:
                        selected_threads.append({'thread_id': threads[0].id})

    if not selected_threads:
        print(f"[INFO] Keine Garne für Auftrag {order.id}, überspringe Garnverbrauchserfassung")
        return

    # Berechne Garnverbrauch pro Garn
    # Formel: (Stichanzahl * 0.5mm pro Stich) / 1000 = Meter
    # + 10% Puffer für Faden wechsel und Verschnitt
    total_usage_meters = (order.stitch_count * 0.5 / 1000) * 1.1
    usage_per_thread = total_usage_meters / len(selected_threads)

    print(f"[INFO] Erfasse Garnverbrauch für Auftrag {order.id}: {len(selected_threads)} Garne, gesamt {total_usage_meters:.1f}m")

    # Erstelle ThreadUsage-Einträge
    for thread_data in selected_threads:
        thread_id = thread_data.get('thread_id')
        if not thread_id:
            continue

        # Prüfe ob Thread existiert
        thread = Thread.query.get(thread_id)
        if not thread:
            print(f"[WARNUNG] Garn {thread_id} nicht gefunden")
            continue

        # Erstelle ThreadUsage-Eintrag
        usage = ThreadUsage(
            thread_id=thread_id,
            order_id=order.id,
            machine_id=order.assigned_machine_id,
            quantity_used=usage_per_thread,
            usage_type='production',
            recorded_by='system',
            notes=f'Automatisch erfasst bei Produktionsabschluss (geschätzt)',
            used_at=datetime.utcnow()
        )
        db.session.add(usage)

        # Aktualisiere Lagerbestand
        stock = ThreadStock.query.filter_by(thread_id=thread_id).first()
        if stock and stock.quantity > 0:
            stock.quantity = max(0, stock.quantity - usage_per_thread)
            stock.last_updated = datetime.utcnow()
            print(f"[INFO] Lagerbestand aktualisiert: {thread.color_name_de} -{usage_per_thread:.1f}m")
        else:
            print(f"[WARNUNG] Kein Lagerbestand für Garn {thread.color_name_de}")

    # Commit alle Änderungen
    db.session.commit()
    print(f"[OK] Garnverbrauch für Auftrag {order.id} erfolgreich erfasst")

@production_bp.route('/')
@login_required
def index():
    """Produktions-Übersicht"""
    # Aktuelle Produktionen (Status: in_progress)
    current_productions = Order.query.filter_by(
        status='in_progress'
    ).order_by(Order.production_start.desc()).all()
    
    # Wartende Aufträge (Status: accepted)
    waiting_orders = Order.query.filter_by(
        status='accepted'
    ).order_by(Order.rush_order.desc(), Order.created_at).all()
    
    # Maschinen-Status
    machines = Machine.query.filter_by(status='active').all()
    machine_status = {}
    
    for machine in machines:
        # Aktueller Auftrag auf der Maschine
        current_order = Order.query.filter_by(
            assigned_machine_id=machine.id,
            status='in_progress'
        ).first()
        
        machine_status[machine.id] = {
            'machine': machine,
            'current_order': current_order,
            'is_busy': current_order is not None
        }
    
    # Produktionsstatistiken für heute
    today = date.today()
    stats = {
        'completed_today': Order.query.filter(
            and_(
                Order.status == 'ready',
                db.func.date(Order.production_end) == today
            )
        ).count(),
        'in_progress': len(current_productions),
        'waiting': len(waiting_orders),
        'rush_orders': Order.query.filter_by(
            status='accepted',
            rush_order=True
        ).count()
    }
    
    return render_template('production/index.html',
                         current_productions=current_productions,
                         waiting_orders=waiting_orders,
                         machine_status=machine_status,
                         stats=stats)

@production_bp.route('/planning')
@login_required
def planning():
    """Produktionsplanung"""
    # Datum-Filter
    start_date = request.args.get('start_date', date.today().isoformat())
    end_date = request.args.get('end_date', (date.today() + timedelta(days=7)).isoformat())
    
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
    except:
        start = date.today()
        end = date.today() + timedelta(days=7)
    
    # Geplante Produktionen laden
    schedules = ProductionSchedule.query.filter(
        and_(
            ProductionSchedule.scheduled_start >= start,
            ProductionSchedule.scheduled_start <= end
        )
    ).order_by(ProductionSchedule.scheduled_start).all()
    
    # Nach Maschine gruppieren
    schedule_by_machine = {}
    for schedule in schedules:
        if schedule.machine_id not in schedule_by_machine:
            schedule_by_machine[schedule.machine_id] = []
        schedule_by_machine[schedule.machine_id].append(schedule)
    
    # Verfügbare Maschinen
    machines_list = Machine.query.filter_by(status='active').all()
    
    # Maschinen nach Typ gruppieren
    machines = {
        'embroidery_machines': {},
        'printing_machines': {},
        'dtf_machines': {}
    }
    
    for machine in machines_list:
        if machine.type == 'embroidery':
            machines['embroidery_machines'][machine.id] = machine
        elif machine.type == 'printing':
            machines['printing_machines'][machine.id] = machine
        elif machine.type == 'dtf':
            machines['dtf_machines'][machine.id] = machine
    
    # Produktions-Queue erstellen
    production_queue = {
        'embroidery': [],
        'printing': [],
        'dtf': []
    }
    
    # Wartende Aufträge nach Typ gruppieren
    waiting_orders = Order.query.filter_by(status='accepted').all()
    
    for order in waiting_orders:
        priority_weight = 1 if order.rush_order else 3
        
        # Produktionszeit schätzen (vereinfacht)
        production_time_hours = 2  # Standard: 2 Stunden
        if order.stitch_count:
            # Geschätzt: 10000 Stiche pro Stunde
            production_time_hours = round(order.stitch_count / 10000, 1)
        
        # Garnbedarf berechnen für Stickaufträge
        thread_requirements = []
        if order.order_type in ['embroidery', 'combined']:
            thread_requirements = calculate_thread_requirements(order)
        
        queue_item = {
            'order': order,
            'priority_weight': priority_weight,
            'production_time_hours': production_time_hours,
            'thread_requirements': thread_requirements
        }
        
        if order.order_type == 'embroidery':
            production_queue['embroidery'].append(queue_item)
        elif order.order_type == 'printing':
            production_queue['printing'].append(queue_item)
        elif order.order_type == 'dtf':
            production_queue['dtf'].append(queue_item)
        elif order.order_type == 'combined':
            # Kombinierte Aufträge in beide Queues
            production_queue['embroidery'].append(queue_item)
            production_queue['printing'].append(queue_item)
    
    # Nach Priorität sortieren
    for queue_type in production_queue:
        production_queue[queue_type].sort(key=lambda x: (x['priority_weight'], x['order'].created_at))
    
    # Warnungen für niedrigen Garnbestand sammeln
    low_stock_warnings = []
    from src.models import ThreadStock
    
    # Prüfe alle aktiven Garnbestände
    low_stocks = db.session.query(ThreadStock).filter(
        ThreadStock.quantity <= ThreadStock.min_stock
    ).all()
    
    for stock in low_stocks:
        if stock.thread:
            low_stock_warnings.append({
                'thread': stock.thread,
                'current_stock': stock.quantity,
                'min_stock': stock.min_stock,
                'location': stock.location
            })
    
    return render_template('production/planning.html',
                         schedules=schedules,
                         schedule_by_machine=schedule_by_machine,
                         machines=machines,
                         production_queue=production_queue,
                         low_stock_warnings=low_stock_warnings,
                         start_date=start_date,
                         end_date=end_date)

@production_bp.route('/schedule')
@login_required
def schedule():
    """Produktionszeitplan - Aufträge nach Priorität sortiert"""
    # Hole alle akzeptierten und in Arbeit befindlichen Aufträge
    orders = Order.query.filter(
        Order.status.in_(['accepted', 'in_progress'])
    ).all()
    
    # Berechne Prioritäten und Produktionszeiten
    scheduled_orders = []
    for order in orders:
        # Prioritätsgewichtung
        priority_weight = 0
        if order.priority == 'urgent':
            priority_weight = 1000
        elif order.priority == 'high':
            priority_weight = 500
        elif order.priority == 'normal':
            priority_weight = 100
        else:  # low
            priority_weight = 10
            
        # Express-Aufträge bekommen extra Gewicht
        if order.rush_order:
            priority_weight += 1500
            
        # Abholdatum berücksichtigen
        if order.pickup_date:
            days_until_pickup = (order.pickup_date - date.today()).days
            if days_until_pickup <= 1:
                priority_weight += 2000
            elif days_until_pickup <= 3:
                priority_weight += 1000
            elif days_until_pickup <= 7:
                priority_weight += 500
        
        # Produktionszeit schätzen
        production_time_hours = 2.0  # Standard
        if order.order_type == 'embroidery' and order.total_stitches:
            # 10.000 Stiche pro Stunde
            production_time_hours = order.total_stitches / 10000
        elif order.order_type == 'printing':
            # DTF/Textildruck: 30 Stück pro Stunde
            production_time_hours = order.quantity / 30
        elif order.order_type == 'combined':
            # Kombiniert: längere Zeit
            production_time_hours = 3.0
            
        production_time_minutes = int(production_time_hours * 60)
        
        scheduled_orders.append({
            'order': order,
            'priority_weight': priority_weight,
            'production_time_hours': production_time_hours,
            'production_time_minutes': production_time_minutes
        })
    
    # Nach Priorität sortieren (höchste zuerst)
    scheduled_orders.sort(key=lambda x: (-x['priority_weight'], x['order'].created_at))
    
    return render_template('production/schedule.html',
                         scheduled_orders=scheduled_orders)

@production_bp.route('/worklist')
@login_required
def worklist():
    """Arbeitsliste für Maschinen - gefiltert nach Maschinentyp"""
    # Maschinentyp aus Query-Parameter holen
    machine_type = request.args.get('type', 'embroidery')
    machine_id = request.args.get('machine_id')
    
    # Maschineninformationen
    machine_name = "Alle Maschinen"
    if machine_id:
        machine = Machine.query.get(machine_id)
        if machine:
            machine_name = machine.name
            machine_type = machine.machine_type
    
    # Aufträge filtern
    query = Order.query.filter(
        Order.status.in_(['accepted', 'in_progress'])
    )
    
    # Nach Maschinentyp filtern
    if machine_type == 'embroidery':
        query = query.filter(
            Order.order_type.in_(['embroidery', 'combined'])
        )
    else:  # printing/dtf
        query = query.filter(
            Order.order_type.in_(['printing', 'dtf', 'combined'])
        )
    
    # Nach spezifischer Maschine filtern, wenn angegeben
    if machine_id:
        query = query.filter(Order.assigned_machine_id == machine_id)
    
    # Sortierung: Dringende zuerst, dann nach Erstelldatum
    orders = query.order_by(
        db.case(
            (Order.priority == 'urgent', 1),
            (Order.priority == 'high', 2),
            (Order.priority == 'normal', 3),
            (Order.priority == 'low', 4),
            else_=5
        ),
        Order.rush_order.desc(),
        Order.created_at.asc()
    ).all()
    
    return render_template('production/worklist.html',
                         orders=orders,
                         machine_type=machine_type,
                         machine_name=machine_name)

@production_bp.route('/order/<order_id>/start', methods=['POST'])
@login_required
def start_production(order_id):
    """Produktion starten"""
    order = Order.query.get_or_404(order_id)
    
    if order.status != 'accepted':
        flash('Nur angenommene Aufträge können gestartet werden!', 'danger')
        return redirect(url_for('production.index'))
    
    # Maschine zuweisen
    machine_id = request.form.get('machine_id')
    if machine_id:
        # Prüfen ob Maschine frei ist
        busy_order = Order.query.filter_by(
            assigned_machine_id=machine_id,
            status='in_progress'
        ).first()
        
        if busy_order:
            flash(f'Maschine ist bereits belegt mit Auftrag {busy_order.id}!', 'danger')
            return redirect(url_for('production.index'))
        
        order.assigned_machine_id = machine_id
    
    # Status aktualisieren
    order.status = 'in_progress'
    order.production_start = datetime.utcnow()
    
    # Status-Historie
    from src.models import OrderStatusHistory
    history = OrderStatusHistory(
        order_id=order_id,
        from_status='accepted',
        to_status='in_progress',
        comment=f'Produktion gestartet auf Maschine {machine_id}' if machine_id else 'Produktion gestartet',
        changed_by=current_user.username
    )
    db.session.add(history)
    
    db.session.commit()
    
    # Aktivität protokollieren
    log_activity('production_started', 
                f'Produktion gestartet: Auftrag {order.id}')
    
    flash(f'Produktion für Auftrag {order.id} wurde gestartet!', 'success')
    return redirect(url_for('production.index'))

@production_bp.route('/order/<order_id>/complete', methods=['POST'])
@login_required
def complete_production(order_id):
    """Produktion abschließen"""
    order = Order.query.get_or_404(order_id)

    if order.status != 'in_progress':
        flash('Nur laufende Produktionen können abgeschlossen werden!', 'danger')
        return redirect(url_for('production.index'))

    # Status aktualisieren
    order.status = 'ready'
    order.production_end = datetime.utcnow()

    # Produktionszeit berechnen
    if order.production_start:
        duration = order.production_end - order.production_start
        order.production_minutes = int(duration.total_seconds() / 60)

    # AUTOMATISCHE GARNVERBRAUCH-ERFASSUNG
    try:
        _record_automatic_thread_usage(order)
    except Exception as e:
        print(f"[WARNUNG] Automatische Garnverbrauchserfassung fehlgeschlagen: {e}")
        # Nicht kritisch - Produktion kann trotzdem abgeschlossen werden

    # Status-Historie
    from src.models import OrderStatusHistory
    history = OrderStatusHistory(
        order_id=order_id,
        from_status='in_progress',
        to_status='ready',
        comment=request.form.get('comment', ''),
        changed_by=current_user.username
    )
    db.session.add(history)

    db.session.commit()

    # Aktivität protokollieren
    log_activity('production_completed',
                f'Produktion abgeschlossen: Auftrag {order.id}')

    # WORKFLOW-AUTOMATISIERUNG: Packliste & Post-Eintrag erstellen
    try:
        settings = CompanySettings.get_settings()

        # 1. Packliste erstellen (wenn aktiviert)
        if settings.auto_create_packing_list and order.auto_create_packing_list:
            # Prüfe ob bereits eine Packliste existiert
            existing_pl = PackingList.query.filter_by(order_id=order.id).first()
            if not existing_pl:
                # Erstelle Packliste
                packing_list = PackingList(
                    packing_list_number=PackingList.generate_packing_list_number(),
                    order_id=order.id,
                    customer_id=order.customer_id,
                    status='ready',
                    customer_notes=order.customer_notes or '',
                    created_by=current_user.id
                )

                # Items aus Auftrag übernehmen
                items = []
                if order.order_items:
                    for order_item in order.order_items:
                        items.append({
                            'article_id': order_item.article_id,
                            'name': order_item.article.name if order_item.article else 'Unbekannt',
                            'quantity': order_item.quantity,
                            'ean': order_item.article.ean if order_item.article else ''
                        })
                packing_list.set_items_list(items)

                db.session.add(packing_list)
                db.session.flush()  # Um ID zu erhalten

                # Verknüpfe mit Auftrag
                order.packing_list_id = packing_list.id

                # 2. Post-Eintrag erstellen (wenn Packliste erstellt wurde)
                post_entry = PostEntry(
                    type='outgoing',
                    customer_id=order.customer_id,
                    status='draft',
                    packing_list_id=packing_list.id,
                    is_auto_created=True,
                    created_by=current_user.id,
                    created_at=datetime.utcnow()
                )
                db.session.add(post_entry)
                db.session.flush()

                # Verknüpfe Post-Eintrag mit Packliste
                packing_list.post_entry_id = post_entry.id

                db.session.commit()

                log_activity('packing_list_auto_created',
                           f'Packliste {packing_list.packing_list_number} automatisch erstellt für Auftrag {order.id}')

                flash(f'Packliste {packing_list.packing_list_number} und Post-Eintrag wurden automatisch erstellt.', 'info')
    except Exception as e:
        print(f"[WARNUNG] Workflow-Automatisierung fehlgeschlagen: {e}")
        import traceback
        traceback.print_exc()
        # Nicht kritisch - Produktion wurde erfolgreich abgeschlossen

    flash(f'Produktion für Auftrag {order.id} wurde abgeschlossen!', 'success')
    return redirect(url_for('production.index'))

@production_bp.route('/schedule/new', methods=['POST'])
@login_required
def schedule_production():
    """Produktion einplanen"""
    order_id = request.form.get('order_id')
    machine_id = request.form.get('machine_id')
    scheduled_date = request.form.get('scheduled_date')
    scheduled_time = request.form.get('scheduled_time')
    duration_minutes = int(request.form.get('duration_minutes', 60))
    
    # Zeitpunkt berechnen
    try:
        scheduled_start = datetime.strptime(
            f"{scheduled_date} {scheduled_time}", 
            '%Y-%m-%d %H:%M'
        )
    except:
        flash('Ungültiges Datum/Zeit Format!', 'danger')
        return redirect(url_for('production.planning'))
    
    scheduled_end = scheduled_start + timedelta(minutes=duration_minutes)
    
    # Prüfen ob Zeitslot frei ist
    conflict = ProductionSchedule.query.filter(
        and_(
            ProductionSchedule.machine_id == machine_id,
            ProductionSchedule.status != 'cancelled',
            db.or_(
                and_(
                    ProductionSchedule.scheduled_start <= scheduled_start,
                    ProductionSchedule.scheduled_end > scheduled_start
                ),
                and_(
                    ProductionSchedule.scheduled_start < scheduled_end,
                    ProductionSchedule.scheduled_end >= scheduled_end
                )
            )
        )
    ).first()
    
    if conflict:
        flash('Maschine ist zu diesem Zeitpunkt bereits belegt!', 'danger')
        return redirect(url_for('production.planning'))
    
    # Planung erstellen
    schedule = ProductionSchedule(
        machine_id=machine_id,
        order_id=order_id,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        status='scheduled',
        priority=5,
        notes=request.form.get('notes', ''),
        created_by=current_user.username
    )
    
    db.session.add(schedule)
    db.session.commit()
    
    # Aktivität protokollieren
    log_activity('production_scheduled', 
                f'Produktion eingeplant: Auftrag {order_id} auf Maschine {machine_id}')
    
    flash('Produktion wurde eingeplant!', 'success')
    return redirect(url_for('production.planning'))

@production_bp.route('/schedule/<int:schedule_id>/cancel', methods=['POST'])
@login_required
def cancel_schedule(schedule_id):
    """Geplante Produktion stornieren"""
    schedule = ProductionSchedule.query.get_or_404(schedule_id)
    
    schedule.status = 'cancelled'
    schedule.updated_at = datetime.utcnow()
    schedule.updated_by = current_user.username
    
    db.session.commit()
    
    # Aktivität protokollieren
    log_activity('production_schedule_cancelled', 
                f'Produktionsplanung storniert: ID {schedule_id}')
    
    flash('Produktionsplanung wurde storniert!', 'success')
    return redirect(url_for('production.planning'))

# API-Endpoints
@production_bp.route('/calendar')
@login_required
def calendar():
    """Produktionskalender mit visueller Ansicht"""
    # Woche auswählen
    week_offset = request.args.get('week', 0, type=int)
    today = date.today()
    
    # Wochenstart (Montag)
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday) + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)
    
    # Bürozeiten und Pausen aus Settings laden
    settings = load_production_settings()
    
    # Maschinen laden
    machines = Machine.query.filter_by(status='active').order_by(Machine.type, Machine.name).all()
    
    # Produktionspläne für die Woche laden
    schedules = ProductionSchedule.query.filter(
        and_(
            ProductionSchedule.scheduled_start >= week_start,
            ProductionSchedule.scheduled_start <= week_end,
            ProductionSchedule.status != 'cancelled'
        )
    ).all()
    
    # Nach Tag und Maschine gruppieren
    calendar_data = {}
    for day_offset in range(7):
        current_date = week_start + timedelta(days=day_offset)
        calendar_data[current_date] = {}
        
        for machine in machines:
            day_schedules = [s for s in schedules 
                           if s.machine_id == machine.id 
                           and s.scheduled_start.date() == current_date]
            calendar_data[current_date][machine.id] = day_schedules
    
    # Wartende Aufträge für Drag & Drop
    waiting_orders = Order.query.filter_by(status='accepted').order_by(
        Order.rush_order.desc(), 
        Order.created_at
    ).all()
    
    return render_template('production/calendar.html',
                         week_start=week_start,
                         week_end=week_end,
                         week_offset=week_offset,
                         calendar_data=calendar_data,
                         machines=machines,
                         waiting_orders=waiting_orders,
                         settings=settings,
                         today=today,
                         timedelta=timedelta)  # Für Template-Nutzung

@production_bp.route('/api/machine/<machine_id>/availability')
@login_required
def api_machine_availability(machine_id):
    """Maschinen-Verfügbarkeit für Kalender"""
    date_str = request.args.get('date')
    
    try:
        check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        return jsonify({'error': 'Invalid date format'}), 400
    
    # Geplante Zeiten für diese Maschine und Tag
    schedules = ProductionSchedule.query.filter(
        and_(
            ProductionSchedule.machine_id == machine_id,
            db.func.date(ProductionSchedule.scheduled_start) == check_date,
            ProductionSchedule.status != 'cancelled'
        )
    ).all()
    
    busy_slots = []
    for schedule in schedules:
        busy_slots.append({
            'start': schedule.scheduled_start.strftime('%H:%M'),
            'end': schedule.scheduled_end.strftime('%H:%M'),
            'order_id': schedule.order_id
        })
    
    return jsonify({
        'machine_id': machine_id,
        'date': date_str,
        'busy_slots': busy_slots
    })

@production_bp.route('/api/schedule/move', methods=['POST'])
@login_required
def api_move_schedule():
    """Produktionsplanung verschieben (Drag & Drop)"""
    data = request.get_json()
    schedule_id = data.get('schedule_id')
    new_start = data.get('new_start')
    new_machine_id = data.get('machine_id')
    
    schedule = ProductionSchedule.query.get_or_404(schedule_id)
    
    # Neue Zeit berechnen
    try:
        new_start_dt = datetime.strptime(new_start, '%Y-%m-%d %H:%M')
        duration = schedule.scheduled_end - schedule.scheduled_start
        new_end_dt = new_start_dt + duration
    except:
        return jsonify({'error': 'Invalid datetime format'}), 400
    
    # Konfliktprüfung
    conflict = ProductionSchedule.query.filter(
        and_(
            ProductionSchedule.machine_id == new_machine_id,
            ProductionSchedule.id != schedule_id,
            ProductionSchedule.status != 'cancelled',
            db.or_(
                and_(
                    ProductionSchedule.scheduled_start <= new_start_dt,
                    ProductionSchedule.scheduled_end > new_start_dt
                ),
                and_(
                    ProductionSchedule.scheduled_start < new_end_dt,
                    ProductionSchedule.scheduled_end >= new_end_dt
                )
            )
        )
    ).first()
    
    if conflict:
        return jsonify({'error': 'Time slot is already occupied'}), 409
    
    # Update schedule
    schedule.machine_id = new_machine_id
    schedule.scheduled_start = new_start_dt
    schedule.scheduled_end = new_end_dt
    schedule.updated_at = datetime.utcnow()
    schedule.updated_by = current_user.username
    
    db.session.commit()
    
    return jsonify({'success': True, 'schedule_id': schedule_id})

@production_bp.route('/api/order/schedule', methods=['POST'])
@login_required
def api_schedule_order():
    """Auftrag einplanen (Drag & Drop aus Warteschlange)"""
    data = request.get_json()
    order_id = data.get('order_id')
    machine_id = data.get('machine_id')
    start_time = data.get('start_time')
    duration_hours = data.get('duration_hours', 2)
    
    order = Order.query.get_or_404(order_id)
    
    if order.status != 'accepted':
        return jsonify({'error': 'Order must be in accepted status'}), 400
    
    # Zeit berechnen
    try:
        start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
        end_dt = start_dt + timedelta(hours=duration_hours)
    except:
        return jsonify({'error': 'Invalid datetime format'}), 400
    
    # Konfliktprüfung
    conflict = ProductionSchedule.query.filter(
        and_(
            ProductionSchedule.machine_id == machine_id,
            ProductionSchedule.status != 'cancelled',
            db.or_(
                and_(
                    ProductionSchedule.scheduled_start <= start_dt,
                    ProductionSchedule.scheduled_end > start_dt
                ),
                and_(
                    ProductionSchedule.scheduled_start < end_dt,
                    ProductionSchedule.scheduled_end >= end_dt
                )
            )
        )
    ).first()
    
    if conflict:
        return jsonify({'error': 'Time slot is already occupied'}), 409
    
    # Neue Planung erstellen
    schedule = ProductionSchedule(
        machine_id=machine_id,
        order_id=order_id,
        scheduled_start=start_dt,
        scheduled_end=end_dt,
        status='scheduled',
        priority=1 if order.rush_order else 3,
        created_by=current_user.username
    )
    
    db.session.add(schedule)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'schedule_id': schedule.id,
        'order': {
            'id': order.id,
            'customer_name': order.customer.display_name if order.customer else 'Unbekannt',
            'description': order.description or 'Keine Beschreibung'
        }
    })
