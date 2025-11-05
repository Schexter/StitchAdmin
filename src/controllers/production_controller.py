"""
Production Controller - Produktionsplanung für Stickerei & Textildruck
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

# Blueprint erstellen
production_bp = Blueprint('production', __name__, url_prefix='/production')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Bitte melden Sie sich an.', 'info')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def load_orders():
    """Lade Kundenaufträge"""
    from src.controllers.order_controller import load_orders
    return load_orders()

def get_production_orders(exclude_assigned=False):
    """Hole alle Aufträge die produziert werden müssen
    
    Args:
        exclude_assigned: Wenn True, werden bereits zugewiesene Aufträge ausgeschlossen
    """
    orders = load_orders()
    
    # Nur Aufträge die in Produktion sind oder bereit für Produktion
    production_orders = {
        oid: order for oid, order in orders.items() 
        if order.get('status') in ['accepted', 'in_progress']
    }
    
    if exclude_assigned:
        # Lade Maschinenbelegungen um zugewiesene Aufträge zu identifizieren
        try:
            with open('machine_schedule.json', 'r', encoding='utf-8') as f:
                schedule = json.load(f)
            
            # Sammle alle zugewiesenen Auftragsnummern
            assigned_orders = set()
            for machine_id, jobs in schedule.items():
                for job in jobs:
                    if job.get('order_id') and job.get('status') != 'cancelled':
                        assigned_orders.add(job.get('order_id'))
            
            # Filtere zugewiesene Aufträge aus
            production_orders = {
                oid: order for oid, order in production_orders.items()
                if oid not in assigned_orders
            }
        except (FileNotFoundError, json.JSONDecodeError):
            # Wenn keine Schedule-Datei existiert, sind keine Aufträge zugewiesen
            pass
    
    return production_orders

def group_orders_by_type(orders):
    """Gruppiere Aufträge nach Produktionstyp"""
    grouped = {
        'embroidery': [],
        'printing': [],
        'combined': []
    }
    
    for order_id, order in orders.items():
        order_type = order.get('order_type', 'embroidery')
        if order_type in grouped:
            grouped[order_type].append(order)
    
    return grouped

def predict_production_time_ai(order, machine=None):
    """KI-basierte Vorhersage der Produktionszeit basierend auf historischen Daten
    
    Diese Funktion analysiert abgeschlossene Aufträge mit ähnlichen Eigenschaften
    und berechnet eine realistischere Zeitschätzung.
    """
    try:
        # Lade historische Daten
        if not os.path.exists('production_history.json'):
            return None
            
        with open('production_history.json', 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        order_type = order.get('order_type', 'embroidery')
        
        # Sammle relevante historische Aufträge
        relevant_orders = []
        
        for hist_order in history:
            # Filtere nach Auftragstyp
            if hist_order.get('order_type') != order_type:
                continue
                
            # Filtere nach Maschine wenn angegeben
            if machine and hist_order.get('machine_id') != machine.get('id'):
                continue
            
            # Berechne Ähnlichkeit für Stickerei
            if order_type == 'embroidery':
                stitch_diff = abs(hist_order.get('stitch_count', 0) - order.get('stitch_count', 0))
                quantity_diff = abs(hist_order.get('quantity', 0) - order.get('quantity', 0))
                
                # Ähnlichkeitsscore (je niedriger desto ähnlicher)
                similarity = stitch_diff / 1000 + quantity_diff * 10
                
                if similarity < 100:  # Threshold für Ähnlichkeit
                    relevant_orders.append({
                        'order': hist_order,
                        'similarity': similarity,
                        'actual_time': hist_order.get('actual_production_time', 0)
                    })
            
            # Für Druckaufträge
            elif order_type in ['printing', 'dtf']:
                size_diff = abs(
                    (hist_order.get('print_width_cm', 0) * hist_order.get('print_height_cm', 0)) -
                    (order.get('print_width_cm', 0) * order.get('print_height_cm', 0))
                )
                quantity_diff = abs(hist_order.get('quantity', 0) - order.get('quantity', 0))
                
                similarity = size_diff / 100 + quantity_diff * 5
                
                if similarity < 50:
                    relevant_orders.append({
                        'order': hist_order,
                        'similarity': similarity,
                        'actual_time': hist_order.get('actual_production_time', 0)
                    })
        
        if not relevant_orders:
            return None
        
        # Sortiere nach Ähnlichkeit
        relevant_orders.sort(key=lambda x: x['similarity'])
        
        # Gewichteter Durchschnitt der Top 5 ähnlichsten Aufträge
        top_orders = relevant_orders[:5]
        total_weight = 0
        weighted_time = 0
        
        for item in top_orders:
            # Gewicht ist invers zur Ähnlichkeit
            weight = 1 / (1 + item['similarity'])
            weighted_time += item['actual_time'] * weight
            total_weight += weight
        
        if total_weight > 0:
            predicted_time = weighted_time / total_weight
            
            # Adjustiere für Lernkurve (neuere Aufträge sind meist schneller)
            learning_factor = 0.95  # 5% Verbesserung über Zeit
            predicted_time *= learning_factor
            
            return round(predicted_time)
        
    except Exception as e:
        # Bei Fehler einfach None zurückgeben
        print(f"KI-Vorhersage Fehler: {e}")
        
    return None

def calculate_production_time(order, machine=None, use_ai_prediction=True):
    """Berechne geschätzte Produktionszeit mit Maschinenberücksichtigung und optionaler KI-Vorhersage"""
    order_type = order.get('order_type', 'embroidery')
    quantity = order.get('quantity', 1)
    
    # Versuche KI-basierte Vorhersage wenn aktiviert
    if use_ai_prediction:
        ai_prediction = predict_production_time_ai(order, machine)
        if ai_prediction:
            return ai_prediction
    
    if order_type == 'embroidery':
        # Verwende maschinenspezifische Berechnung wenn verfügbar
        if machine and machine.get('type') == 'embroidery':
            try:
                from src.controllers.machine_controller import calculate_embroidery_production_time
                time_breakdown = calculate_embroidery_production_time(machine, order)
                return time_breakdown['total_minutes']
            except ImportError:
                pass
        
        # Fallback: Vereinfachte Berechnung
        stitch_count = order.get('stitch_count', 5000)
        base_time = 5 + (stitch_count / 1000) * 2  # Min pro Stück
        setup_time = 30  # Setup-Zeit in Minuten
        
        total_minutes = (base_time * quantity) + setup_time
        
    elif order_type in ['printing', 'dtf']:
        # Druck: 2-5 Min pro Stück + Setup
        base_time = 3  # Min pro Stück
        setup_time = 20
        
        total_minutes = (base_time * quantity) + setup_time
        
    elif order_type == 'combined':
        # Kombination: Beide Zeiten
        embroidery_time = (8 * quantity) + 30
        printing_time = (3 * quantity) + 20
        total_minutes = embroidery_time + printing_time
    
    else:
        total_minutes = quantity * 5  # Fallback
    
    return round(total_minutes)

def get_machine_capacity():
    """Hole verfügbare Maschinenkapazität aus Maschinenverwaltung"""
    try:
        from src.controllers.machine_controller import load_machines
        machines = load_machines()
        
        capacity = {
            'embroidery_machines': {},
            'printing_stations': {},
            'dtf_stations': {},
            'other_machines': {}
        }
        
        for machine_id, machine in machines.items():
            if machine.get('status') != 'active':
                continue
                
            machine_info = {
                'name': machine.get('name', 'Unbenannte Maschine'),
                'location': machine.get('location', ''),
                'available': True,  # TODO: Mit Belegungsplan abgleichen
                'specs': {}
            }
            
            if machine.get('type') == 'embroidery':
                machine_info['specs'] = {
                    'needles': machine.get('num_needles', 1),
                    'max_speed': machine.get('max_speed', 1000),
                    'max_area': f"{machine.get('max_embroidery_area_width', 400)}x{machine.get('max_embroidery_area_height', 400)}mm"
                }
                capacity['embroidery_machines'][machine_id] = machine_info
                
            elif machine.get('type') == 'dtf':
                machine_info['specs'] = {
                    'max_width': f"{machine.get('max_print_width', 600)}mm",
                    'resolution': machine.get('print_resolution', '1200x1200')
                }
                capacity['dtf_stations'][machine_id] = machine_info
                
            elif machine.get('type') in ['dtg', 'vinyl', 'sublimation']:
                capacity['printing_stations'][machine_id] = machine_info
                
            else:
                capacity['other_machines'][machine_id] = machine_info
        
        return capacity
        
    except ImportError:
        # Fallback wenn Maschinenverwaltung nicht verfügbar
        return {
            'embroidery_machines': {
                'machine_1': {'name': 'Stickmaschine 1', 'available': True, 'specs': {'needles': 6}}
            },
            'printing_stations': {
                'dtf_station': {'name': 'DTF-Drucker', 'available': True, 'specs': {}}
            }
        }

@production_bp.route('/')
@login_required
def index():
    """Produktionsplanung Übersicht"""
    orders = get_production_orders()
    grouped_orders = group_orders_by_type(orders)
    machines = get_machine_capacity()
    
    # Produktionsstatistiken
    stats = {
        'total_orders': len(orders),
        'embroidery_orders': len(grouped_orders['embroidery']),
        'printing_orders': len(grouped_orders['printing']),
        'combined_orders': len(grouped_orders['combined']),
        'urgent_orders': len([o for o in orders.values() if o.get('priority') == 'urgent']),
        'overdue_orders': 0  # TODO: Implementieren
    }
    
    # Berechne Gesamtproduktionszeit
    total_production_time = 0
    for order in orders.values():
        total_production_time += calculate_production_time(order)
    
    stats['total_production_hours'] = round(total_production_time / 60, 1)
    
    return render_template('production/index.html', 
                         orders=orders,
                         grouped_orders=grouped_orders,
                         machines=machines,
                         stats=stats)

@production_bp.route('/schedule')
@login_required
def schedule():
    """Produktionszeitplan"""
    orders = get_production_orders()
    
    # Sortiere nach Priorität und Abholdatum
    scheduled_orders = []
    for order in orders.values():
        production_time = calculate_production_time(order)
        priority_weight = {
            'urgent': 1,
            'high': 2, 
            'normal': 3,
            'low': 4
        }.get(order.get('priority', 'normal'), 3)
        
        scheduled_orders.append({
            'order': order,
            'production_time_minutes': production_time,
            'production_time_hours': round(production_time / 60, 1),
            'priority_weight': priority_weight,
            'pickup_date': order.get('pickup_date', ''),
            'days_until_pickup': 0  # TODO: Berechnen
        })
    
    # Sortiere nach Priorität und Datum
    scheduled_orders.sort(key=lambda x: (x['priority_weight'], x['pickup_date'] or '9999-12-31'))
    
    return render_template('production/schedule.html', scheduled_orders=scheduled_orders)

@production_bp.route('/worklist/<machine_type>')
@login_required  
def worklist(machine_type):
    """Arbeitsliste für spezifische Maschine/Station"""
    orders = get_production_orders()
    
    # Filtere nach Maschinentyp
    filtered_orders = []
    for order in orders.values():
        order_type = order.get('order_type', '')
        
        if machine_type == 'embroidery' and order_type in ['embroidery', 'combined']:
            filtered_orders.append(order)
        elif machine_type == 'printing' and order_type in ['printing', 'combined']:
            filtered_orders.append(order)
    
    # Sortiere nach Priorität
    filtered_orders.sort(key=lambda x: {
        'urgent': 1, 'high': 2, 'normal': 3, 'low': 4
    }.get(x.get('priority', 'normal'), 3))
    
    machine_name = {
        'embroidery': 'Stickerei-Arbeitsplatz',
        'printing': 'Druck-Arbeitsplatz'
    }.get(machine_type, machine_type)
    
    return render_template('production/worklist.html', 
                         orders=filtered_orders,
                         machine_type=machine_type,
                         machine_name=machine_name)

@production_bp.route('/start_production/<order_id>', methods=['POST'])
@login_required
def start_production(order_id):
    """Startet Produktion für einen Auftrag"""
    from src.controllers.order_controller import load_orders, save_orders
    
    orders = load_orders()
    order = orders.get(order_id)
    
    if not order:
        flash('Auftrag nicht gefunden!', 'danger')
        return redirect(url_for('production.index'))
    
    if order.get('status') != 'accepted':
        flash('Auftrag ist nicht bereit für Produktion!', 'warning')
        return redirect(url_for('production.index'))
    
    # Status auf "in_progress" setzen
    order['status'] = 'in_progress'
    order['production_started_at'] = datetime.now().isoformat()
    order['production_started_by'] = session['username']
    
    save_orders(orders)
    
    flash(f'Produktion für Auftrag {order_id} gestartet!', 'success')
    return redirect(url_for('production.index'))

@production_bp.route('/complete_production/<order_id>', methods=['POST'])
@login_required
def complete_production(order_id):
    """Markiert Produktion als abgeschlossen"""
    from src.controllers.order_controller import load_orders, save_orders
    
    orders = load_orders()
    order = orders.get(order_id)
    
    if not order:
        flash('Auftrag nicht gefunden!', 'danger')
        return redirect(url_for('production.index'))
    
    if order.get('status') != 'in_progress':
        flash('Auftrag ist nicht in Produktion!', 'warning')
        return redirect(url_for('production.index'))
    
    # Berechne tatsächliche Produktionszeit
    if order.get('production_started_at'):
        start_time = datetime.fromisoformat(order['production_started_at'])
        end_time = datetime.now()
        actual_time_minutes = round((end_time - start_time).total_seconds() / 60)
        
        # Speichere für KI-Lernen
        save_production_history(order, actual_time_minutes)
    
    # Status auf "ready" setzen (bereit zur Abholung)
    order['status'] = 'ready'
    order['production_completed_at'] = datetime.now().isoformat()
    order['production_completed_by'] = session['username']
    
    save_orders(orders)
    
    flash(f'Produktion für Auftrag {order_id} abgeschlossen! Bereit zur Abholung.', 'success')
    return redirect(url_for('production.index'))

def save_production_history(order, actual_time_minutes):
    """Speichert abgeschlossene Produktionsaufträge für KI-Lernen"""
    try:
        # Lade existierende Historie
        if os.path.exists('production_history.json'):
            with open('production_history.json', 'r', encoding='utf-8') as f:
                history = json.load(f)
        else:
            history = []
        
        # Füge relevante Daten hinzu
        history_entry = {
            'order_id': order.get('id'),
            'order_type': order.get('order_type'),
            'quantity': order.get('quantity'),
            'stitch_count': order.get('stitch_count', 0),
            'print_width_cm': order.get('print_width_cm', 0),
            'print_height_cm': order.get('print_height_cm', 0),
            'textile_type': order.get('textile_type'),
            'actual_production_time': actual_time_minutes,
            'completed_at': datetime.now().isoformat(),
            'machine_id': order.get('assigned_machine_id')  # Falls zugewiesen
        }
        
        history.append(history_entry)
        
        # Behalte nur die letzten 1000 Einträge
        if len(history) > 1000:
            history = history[-1000:]
        
        # Speichere
        with open('production_history.json', 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        print(f"Fehler beim Speichern der Produktionshistorie: {e}")

@production_bp.route('/api/stats')
@login_required
def api_stats():
    """API für Produktionsstatistiken"""
    orders = get_production_orders()
    grouped_orders = group_orders_by_type(orders)
    
    # Berechne Workload pro Typ
    embroidery_time = sum(calculate_production_time(order) for order in grouped_orders['embroidery'])
    printing_time = sum(calculate_production_time(order) for order in grouped_orders['printing'])
    combined_time = sum(calculate_production_time(order) for order in grouped_orders['combined'])
    
    return jsonify({
        'total_orders': len(orders),
        'embroidery': {
            'orders': len(grouped_orders['embroidery']),
            'time_hours': round(embroidery_time / 60, 1)
        },
        'printing': {
            'orders': len(grouped_orders['printing']),
            'time_hours': round(printing_time / 60, 1)
        },
        'combined': {
            'orders': len(grouped_orders['combined']),
            'time_hours': round(combined_time / 60, 1)
        },
        'total_time_hours': round((embroidery_time + printing_time + combined_time) / 60, 1)
    })

@production_bp.route('/planning')
@login_required
def planning():
    """Erweiterte Produktionsplanung mit Maschinen- und Garnzuteilung"""
    # Zeige nur nicht zugewiesene Aufträge in der Planungsansicht
    orders = get_production_orders(exclude_assigned=True)
    machines = get_machine_capacity()
    
    # Lade Thread-Informationen
    try:
        from src.controllers.thread_controller import load_threads, load_thread_stock, calculate_thread_usage
        threads = load_threads()
        thread_stock = load_thread_stock()
        
        # Berechne Garnbedarf für alle Aufträge
        thread_requirements = {}
        low_stock_warnings = []
        
        for order_id, order in orders.items():
            if order.get('order_type') in ['embroidery', 'combined']:
                stitch_count = order.get('stitch_count', 5000)
                thread_colors = order.get('thread_colors', '').split(',')
                
                order_thread_usage = []
                for color in thread_colors:
                    color = color.strip()
                    if color:
                        # Suche passenden Thread
                        matching_threads = [
                            tid for tid, thread in threads.items()
                            if color.lower() in thread.get('color_name', '').lower()
                        ]
                        
                        if matching_threads:
                            thread_id = matching_threads[0]  # Nimm ersten Treffer
                            usage_meters = calculate_thread_usage(stitch_count, 1)
                            
                            order_thread_usage.append({
                                'thread_id': thread_id,
                                'color_name': threads[thread_id].get('color_name', ''),
                                'usage_meters': usage_meters,
                                'stock_available': thread_stock.get(thread_id, {}).get('quantity', 0)
                            })
                            
                            # Bestand-Warnung
                            current_stock = thread_stock.get(thread_id, {}).get('quantity', 0)
                            min_stock = thread_stock.get(thread_id, {}).get('min_stock', 5)
                            if current_stock <= min_stock:
                                low_stock_warnings.append({
                                    'thread_id': thread_id,
                                    'color_name': threads[thread_id].get('color_name', ''),
                                    'current_stock': current_stock,
                                    'min_stock': min_stock
                                })
                
                if order_thread_usage:
                    thread_requirements[order_id] = order_thread_usage
        
    except ImportError:
        threads = {}
        thread_stock = {}
        thread_requirements = {}
        low_stock_warnings = []
    
    # Gruppiere Aufträge nach Maschinentyp und Priorität
    production_queue = {
        'embroidery': [],
        'dtf': [],
        'printing': []
    }
    
    for order in orders.values():
        order_type = order.get('order_type', 'embroidery')
        priority = order.get('priority', 'normal')
        production_time = calculate_production_time(order)
        
        queue_item = {
            'order': order,
            'production_time_hours': round(production_time / 60, 1),
            'priority_weight': {'urgent': 1, 'high': 2, 'normal': 3, 'low': 4}.get(priority, 3),
            'thread_requirements': thread_requirements.get(order['id'], [])
        }
        
        if order_type in ['embroidery', 'combined']:
            production_queue['embroidery'].append(queue_item)
        if order_type in ['printing', 'dtf', 'combined']:
            production_queue['dtf'].append(queue_item)
    
    # Sortiere Queues nach Priorität
    for queue in production_queue.values():
        queue.sort(key=lambda x: x['priority_weight'])
    
    return render_template('production/planning.html',
                         production_queue=production_queue,
                         machines=machines,
                         thread_requirements=thread_requirements,
                         low_stock_warnings=low_stock_warnings,
                         total_orders=len(orders))

@production_bp.route('/assign_machine', methods=['POST'])
@login_required
def assign_machine():
    """Auftrag einer Maschine zuweisen"""
    order_id = request.form.get('order_id')
    machine_id = request.form.get('machine_id')
    start_time = request.form.get('start_time')
    
    if not all([order_id, machine_id, start_time]):
        flash('Alle Felder sind erforderlich!', 'danger')
        return redirect(url_for('production.planning'))
    
    try:
        from src.controllers.machine_controller import load_machine_schedule, save_machine_schedule
        from src.controllers.order_controller import load_orders
        
        # Lade Daten
        orders = load_orders()
        order = orders.get(order_id)
        schedule = load_machine_schedule()
        
        if not order:
            flash('Auftrag nicht gefunden!', 'danger')
            return redirect(url_for('production.planning'))
        
        # Berechne Endzeit
        production_time = calculate_production_time(order)
        start_datetime = datetime.fromisoformat(start_time)
        end_datetime = start_datetime + timedelta(minutes=production_time)
        
        # Füge Job zur Maschinenbelegung hinzu
        if machine_id not in schedule:
            schedule[machine_id] = []
        
        job = {
            'id': len(schedule[machine_id]) + 1,
            'order_id': order_id,
            'job_title': f"Auftrag {order_id} - {order.get('description', '')}",
            'start_time': start_datetime.isoformat(),
            'end_time': end_datetime.isoformat(),
            'estimated_duration_minutes': production_time,
            'priority': order.get('priority', 'normal'),
            'notes': f"Automatisch zugewiesen via Produktionsplanung",
            'status': 'scheduled',
            'created_at': datetime.now().isoformat(),
            'created_by': session['username']
        }
        
        schedule[machine_id].append(job)
        save_machine_schedule(schedule)
        
        flash(f'Auftrag {order_id} wurde Maschine {machine_id} zugewiesen!', 'success')
        
    except ImportError:
        flash('Maschinenverwaltung nicht verfügbar!', 'danger')
    except Exception as e:
        flash(f'Fehler beim Zuweisen: {str(e)}', 'danger')
    
    return redirect(url_for('production.planning'))

@production_bp.route('/api/time_prediction/<order_id>')
@login_required
def api_time_prediction(order_id):
    """API-Endpoint für KI-basierte Zeitvorhersage"""
    from src.controllers.order_controller import load_orders
    
    orders = load_orders()
    order = orders.get(order_id)
    
    if not order:
        return jsonify({'error': 'Auftrag nicht gefunden'}), 404
    
    # Berechne beide Zeiten
    standard_time = calculate_production_time(order, use_ai_prediction=False)
    ai_time = predict_production_time_ai(order)
    
    response = {
        'standard_time_minutes': standard_time,
        'standard_time_hours': round(standard_time / 60, 1),
        'ai_prediction_available': ai_time is not None
    }
    
    if ai_time:
        response['ai_time_minutes'] = ai_time
        response['ai_time_hours'] = round(ai_time / 60, 1)
        response['confidence'] = 'high' if os.path.exists('production_history.json') else 'low'
        
        # Berechne Abweichung
        difference = ai_time - standard_time
        response['difference_minutes'] = difference
        response['difference_percent'] = round((difference / standard_time) * 100) if standard_time > 0 else 0
    
    return jsonify(response)