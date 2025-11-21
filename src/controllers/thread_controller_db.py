"""
Thread Controller - PostgreSQL-Version
Garn-/Farbverwaltung mit Datenbank
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from src.models import db, Thread, ThreadStock, ThreadUsage, ActivityLog
import csv
import io
import os
import sys
import tempfile
import subprocess
import glob

# Blueprint erstellen
thread_bp = Blueprint('thread', __name__, url_prefix='/thread')

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

@thread_bp.route('/dashboard')
@login_required
def dashboard():
    """Garn-Dashboard mit Statistiken"""
    from sqlalchemy import func

    # Bestandsstatistiken
    total_threads = Thread.query.count()
    threads_with_stock = db.session.query(func.count(ThreadStock.id)).filter(ThreadStock.quantity > 0).scalar() or 0
    threads_low_stock = db.session.query(func.count(ThreadStock.id)).filter(
        ThreadStock.quantity <= ThreadStock.min_stock,
        ThreadStock.quantity > 0
    ).scalar() or 0
    threads_out_of_stock = db.session.query(func.count(ThreadStock.id)).filter(ThreadStock.quantity == 0).scalar() or 0

    # Top 10 meist verwendete Garne (nach Verbrauch)
    top_threads = db.session.query(
        Thread.id,
        Thread.manufacturer,
        Thread.color_number,
        Thread.color_name_de,
        Thread.hex_color,
        func.sum(ThreadUsage.quantity_used).label('total_used')
    ).join(ThreadUsage, Thread.id == ThreadUsage.thread_id)\
     .group_by(Thread.id)\
     .order_by(func.sum(ThreadUsage.quantity_used).desc())\
     .limit(10).all()

    # Verbrauch nach Maschine (letzte 30 Tage)
    from datetime import timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    machine_usage = db.session.query(
        ThreadUsage.machine_id,
        func.count(ThreadUsage.id).label('usage_count'),
        func.sum(ThreadUsage.quantity_used).label('total_used')
    ).filter(ThreadUsage.used_at >= thirty_days_ago)\
     .group_by(ThreadUsage.machine_id)\
     .order_by(func.sum(ThreadUsage.quantity_used).desc())\
     .all()

    # Hersteller-Übersicht
    manufacturer_stats = db.session.query(
        Thread.manufacturer,
        func.count(Thread.id).label('thread_count'),
        func.sum(ThreadStock.quantity).label('total_stock')
    ).join(ThreadStock, Thread.id == ThreadStock.thread_id)\
     .group_by(Thread.manufacturer)\
     .order_by(func.count(Thread.id).desc())\
     .all()

    # Warnungen sammeln
    warnings = []
    if threads_out_of_stock > 0:
        warnings.append({
            'type': 'danger',
            'message': f'{threads_out_of_stock} Garne sind ausverkauft'
        })
    if threads_low_stock > 0:
        warnings.append({
            'type': 'warning',
            'message': f'{threads_low_stock} Garne haben niedrigen Bestand'
        })

    stats = {
        'total_threads': total_threads,
        'threads_with_stock': threads_with_stock,
        'threads_low_stock': threads_low_stock,
        'threads_out_of_stock': threads_out_of_stock,
        'top_threads': top_threads,
        'machine_usage': machine_usage,
        'manufacturer_stats': manufacturer_stats,
        'warnings': warnings
    }

    return render_template('threads/dashboard.html', stats=stats)

@thread_bp.route('/')
@login_required
def index():
    """Garn-Übersicht"""
    manufacturer_filter = request.args.get('manufacturer', '')
    category_filter = request.args.get('category', '')
    search_query = request.args.get('search', '').lower()
    stock_filter = request.args.get('stock', '')
    
    # Query erstellen
    query = Thread.query
    
    if manufacturer_filter:
        query = query.filter_by(manufacturer=manufacturer_filter)
    
    if category_filter:
        query = query.filter_by(category=category_filter)
    
    if search_query:
        query = query.filter(
            db.or_(
                Thread.color_number.ilike(f'%{search_query}%'),
                Thread.color_name_de.ilike(f'%{search_query}%'),
                Thread.color_name_en.ilike(f'%{search_query}%'),
                Thread.pantone.ilike(f'%{search_query}%')
            )
        )
    
    # Stock-Filter
    if stock_filter == 'out':
        query = query.join(ThreadStock).filter(ThreadStock.quantity == 0)
    elif stock_filter == 'low':
        query = query.join(ThreadStock).filter(
            ThreadStock.quantity <= ThreadStock.min_stock,
            ThreadStock.quantity > 0
        )
    
    # Nach Hersteller und Nummer sortieren
    threads_list = query.order_by(Thread.manufacturer, Thread.color_number).all()
    
    # In Dictionary umwandeln für Template-Kompatibilität
    threads = {}
    for thread in threads_list:
        threads[thread.id] = thread
    
    # Filter-Optionen laden
    manufacturers = db.session.query(Thread.manufacturer).distinct().filter(Thread.manufacturer.isnot(None)).all()
    manufacturers = [m[0] for m in manufacturers if m[0]]
    
    categories = db.session.query(Thread.category).distinct().filter(Thread.category.isnot(None)).all()
    categories = [c[0] for c in categories if c[0]]
    
    # Current filters als Dictionary für Template
    current_filters = {
        'manufacturer': manufacturer_filter,
        'category': category_filter,
        'search': search_query,
        'stock': stock_filter,
        'low_stock': stock_filter == 'low'
    }
    
    return render_template('threads/index.html',
                         threads=threads,
                         manufacturers=manufacturers,
                         categories=categories,
                         current_filters=current_filters,
                         manufacturer_filter=manufacturer_filter,
                         category_filter=category_filter,
                         search_query=search_query,
                         stock_filter=stock_filter)

@thread_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Neues Garn erstellen"""
    if request.method == 'POST':
        # Neues Garn erstellen
        thread = Thread(
            manufacturer=request.form.get('manufacturer'),
            thread_type=request.form.get('thread_type', ''),
            color_number=request.form.get('color_number'),
            color_name_de=request.form.get('color_name_de', ''),
            color_name_en=request.form.get('color_name_en', ''),
            hex_color=request.form.get('hex_color', ''),
            pantone=request.form.get('pantone', ''),
            category=request.form.get('category', 'Standard'),
            weight=int(request.form.get('weight', 40) or 40),
            material=request.form.get('material', ''),
            price=float(request.form.get('price', 0) or 0),
            supplier=request.form.get('supplier', ''),
            supplier_article_number=request.form.get('supplier_article_number', ''),
            active=request.form.get('active', False) == 'on',
            created_by=current_user.username
        )
        
        # RGB-Werte aus Hex berechnen
        if thread.hex_color and thread.hex_color.startswith('#'):
            try:
                hex_color = thread.hex_color.lstrip('#')
                thread.rgb_r = int(hex_color[0:2], 16)
                thread.rgb_g = int(hex_color[2:4], 16)
                thread.rgb_b = int(hex_color[4:6], 16)
            except:
                pass
        
        # ID generieren: Hersteller_Nummer
        thread.id = f"{thread.manufacturer}_{thread.color_number}".replace(' ', '_')
        
        # In Datenbank speichern
        db.session.add(thread)
        
        # Lagerbestand erstellen
        stock = ThreadStock(
            thread_id=thread.id,
            quantity=int(request.form.get('initial_stock', 0) or 0),
            min_stock=int(request.form.get('min_stock', 5) or 5),
            location=request.form.get('location', ''),
            updated_by=current_user.username
        )
        db.session.add(stock)
        
        db.session.commit()
        
        # Aktivität protokollieren
        log_activity('thread_created', 
                    f'Garn erstellt: {thread.manufacturer} {thread.color_number}')
        
        flash(f'Garn {thread.manufacturer} {thread.color_number} wurde erstellt!', 'success')
        return redirect(url_for('thread.show', thread_id=thread.id))
    
    return render_template('threads/new.html')

@thread_bp.route('/<thread_id>')
@login_required
def show(thread_id):
    """Garn-Details anzeigen"""
    thread = Thread.query.get_or_404(thread_id)
    
    # Verbrauchshistorie laden (letzte 10)
    usage_history = ThreadUsage.query.filter_by(
        thread_id=thread_id
    ).order_by(ThreadUsage.used_at.desc()).limit(10).all()
    
    # Lagerbestand-Status
    if thread.stock:
        if thread.stock.quantity == 0:
            stock_status = 'danger'
            stock_text = 'Nicht auf Lager'
        elif thread.stock.quantity <= thread.stock.min_stock:
            stock_status = 'warning'
            stock_text = 'Niedriger Bestand'
        else:
            stock_status = 'success'
            stock_text = 'Auf Lager'
    else:
        stock_status = 'info'
        stock_text = 'Kein Bestand definiert'
    
    return render_template('threads/show.html',
                         thread=thread,
                         usage_history=usage_history,
                         stock_status=stock_status,
                         stock_text=stock_text)

@thread_bp.route('/<thread_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(thread_id):
    """Garn bearbeiten"""
    thread = Thread.query.get_or_404(thread_id)
    
    if request.method == 'POST':
        # Garn aktualisieren
        thread.thread_type = request.form.get('thread_type', '')
        thread.color_name_de = request.form.get('color_name_de', '')
        thread.color_name_en = request.form.get('color_name_en', '')
        thread.hex_color = request.form.get('hex_color', '')
        thread.pantone = request.form.get('pantone', '')
        thread.category = request.form.get('category', 'Standard')
        thread.weight = int(request.form.get('weight', 40) or 40)
        thread.material = request.form.get('material', '')
        thread.price = float(request.form.get('price', 0) or 0)
        thread.supplier = request.form.get('supplier', '')
        thread.supplier_article_number = request.form.get('supplier_article_number', '')
        thread.active = request.form.get('active', False) == 'on'
        thread.discontinued = request.form.get('discontinued', False) == 'on'
        thread.updated_at = datetime.utcnow()
        thread.updated_by = current_user.username
        
        # RGB-Werte aktualisieren
        if thread.hex_color and thread.hex_color.startswith('#'):
            try:
                hex_color = thread.hex_color.lstrip('#')
                thread.rgb_r = int(hex_color[0:2], 16)
                thread.rgb_g = int(hex_color[2:4], 16)
                thread.rgb_b = int(hex_color[4:6], 16)
            except:
                pass
        
        # Lagerbestand aktualisieren
        if thread.stock:
            thread.stock.min_stock = int(request.form.get('min_stock', 5) or 5)
            thread.stock.location = request.form.get('location', '')
            thread.stock.updated_by = current_user.username
        
        # Änderungen speichern
        db.session.commit()
        
        # Aktivität protokollieren
        log_activity('thread_updated', 
                    f'Garn aktualisiert: {thread.manufacturer} {thread.color_number}')
        
        flash(f'Garn {thread.manufacturer} {thread.color_number} wurde aktualisiert!', 'success')
        return redirect(url_for('thread.show', thread_id=thread.id))
    
    return render_template('threads/edit.html', thread=thread)

@thread_bp.route('/<thread_id>/stock', methods=['POST'])
@login_required
def update_stock(thread_id):
    """Lagerbestand aktualisieren"""
    thread = Thread.query.get_or_404(thread_id)
    
    if not thread.stock:
        # Stock erstellen falls nicht vorhanden
        thread.stock = ThreadStock(thread_id=thread_id)
        db.session.add(thread.stock)
    
    action = request.form.get('action')
    quantity = int(request.form.get('quantity', 0) or 0)
    
    old_stock = thread.stock.quantity
    
    if action == 'add':
        thread.stock.quantity += quantity
        log_detail = f'Bestand erhöht um {quantity}'
    elif action == 'remove':
        thread.stock.quantity = max(0, thread.stock.quantity - quantity)
        log_detail = f'Bestand reduziert um {quantity}'
    else:
        thread.stock.quantity = quantity
        log_detail = f'Bestand gesetzt auf {quantity}'
    
    thread.stock.updated_at = datetime.utcnow()
    thread.stock.updated_by = current_user.username
    
    db.session.commit()
    
    # Aktivität protokollieren
    log_activity('thread_stock_updated', 
                f'{thread.manufacturer} {thread.color_number}: {log_detail} (alt: {old_stock}, neu: {thread.stock.quantity})')
    
    flash(f'Lagerbestand wurde aktualisiert!', 'success')
    return redirect(url_for('thread.show', thread_id=thread_id))

@thread_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_threads():
    """Garne aus CSV oder PDF importieren"""
    if not current_user.is_admin:
        flash('Keine Berechtigung!', 'danger')
        return redirect(url_for('thread.index'))
    
    if request.method == 'POST':
        import_type = request.form.get('import_type', 'csv')
        
        if 'file' not in request.files:
            flash('Keine Datei ausgewählt!', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('Keine Datei ausgewählt!', 'danger')
            return redirect(request.url)
        
        # CSV Import
        if import_type == 'csv' and file.filename.endswith('.csv'):
            # CSV verarbeiten
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.DictReader(stream)
            
            imported = 0
            errors = []
            
            for row in csv_reader:
                try:
                    # Thread erstellen oder aktualisieren
                    manufacturer = row.get('manufacturer', '').strip()
                    color_number = row.get('color_number', '').strip()
                    
                    if not manufacturer or not color_number:
                        errors.append(f"Zeile {csv_reader.line_num}: Hersteller oder Farbnummer fehlt")
                        continue
                    
                    thread_id = f"{manufacturer}_{color_number}".replace(' ', '_')
                    
                    thread = Thread.query.get(thread_id)
                    if not thread:
                        thread = Thread(id=thread_id)
                        db.session.add(thread)
                    
                    # Felder zuweisen
                    thread.manufacturer = manufacturer
                    thread.color_number = color_number
                    thread.thread_type = row.get('thread_type', '')
                    thread.color_name_de = row.get('color_name_de', '')
                    thread.color_name_en = row.get('color_name_en', '')
                    thread.hex_color = row.get('hex_color', '')
                    thread.pantone = row.get('pantone', '')
                    thread.category = row.get('category', 'Standard')
                    thread.material = row.get('material', '')
                    
                    # RGB aus Hex berechnen
                    if thread.hex_color and thread.hex_color.startswith('#'):
                        try:
                            hex_color = thread.hex_color.lstrip('#')
                            thread.rgb_r = int(hex_color[0:2], 16)
                            thread.rgb_g = int(hex_color[2:4], 16)
                            thread.rgb_b = int(hex_color[4:6], 16)
                        except:
                            pass
                    
                    if row.get('price'):
                        try:
                            thread.price = float(row['price'])
                        except:
                            pass
                    
                    thread.updated_by = current_user.username
                    thread.active = True
                    
                    imported += 1
                    
                except Exception as e:
                    errors.append(f"Zeile {csv_reader.line_num}: {str(e)}")
            
            db.session.commit()
            
            # Aktivität protokollieren
            log_activity('threads_imported_csv', 
                        f'{imported} Garne aus CSV importiert')
            
            if errors:
                flash(f'{imported} Garne importiert. {len(errors)} Fehler aufgetreten.', 'warning')
                for error in errors[:5]:  # Zeige max 5 Fehler
                    flash(error, 'danger')
            else:
                flash(f'{imported} Garne erfolgreich aus CSV importiert!', 'success')
            
            return redirect(url_for('thread.index'))
            
        # PDF Import
        elif import_type == 'pdf' and file.filename.endswith('.pdf'):
            # PDF-Datei temporär speichern
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                file.save(tmp_file.name)
                temp_path = tmp_file.name
            
            try:
                # Verwende den Universal Thread Analyzer
                # Versuche verschiedene Pfade
                possible_paths = [
                    # Universal Thread Analyzer V2 - Ein Analyzer für alle!
                    'Universal_Thread_Analyzer.py',
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Universal_Thread_Analyzer.py'),
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'Universal_Thread_Analyzer.py'),
                    # Fallback auf alte Analyzer (falls noch benötigt)
                    'Universal_Thread_Analyzer_V2.py',
                    'thread_analyzer_wrapper.py'
                ]
                
                analyzer_path = None
                for path in possible_paths:
                    if os.path.exists(path):
                        analyzer_path = path
                        print(f"Verwende Analyzer: {path}")
                        break
                
                if analyzer_path:
                    # Führe Analyzer aus
                    # Setze Umgebungsvariablen für korrektes Encoding
                    env = os.environ.copy()
                    env['PYTHONIOENCODING'] = 'utf-8'
                    
                    result = subprocess.run([
                        sys.executable, '-u', analyzer_path, temp_path
                    ], capture_output=True, text=True, encoding='utf-8', 
                       errors='replace', env=env)
                    
                    if result.returncode == 0:
                        # Suche nach generierter CSV
                        csv_files = glob.glob('*_Farben_*.csv')
                        
                        if csv_files:
                            # Neueste CSV-Datei nehmen
                            latest_csv = max(csv_files, key=os.path.getctime)
                            
                            # CSV importieren
                            with open(latest_csv, 'r', encoding='utf-8') as csv_file:
                                csv_reader = csv.DictReader(csv_file)
                                
                                imported = 0
                                for row in csv_reader:
                                    try:
                                        manufacturer = row.get('Hersteller', '').strip()
                                        color_number = row.get('Farbnummer', '').strip()
                                        
                                        if manufacturer and color_number:
                                            thread_id = f"{manufacturer}_{color_number}".replace(' ', '_')
                                            
                                            thread = Thread.query.get(thread_id)
                                            if not thread:
                                                thread = Thread(id=thread_id)
                                                db.session.add(thread)
                                            
                                            thread.manufacturer = manufacturer
                                            thread.color_number = color_number
                                            thread.color_name_de = row.get('Farbname_DE', '')
                                            thread.color_name_en = row.get('Farbname_EN', '')
                                            thread.hex_color = row.get('Hex', '')
                                            thread.pantone = row.get('Pantone', '')
                                            
                                            # RGB-Werte
                                            if row.get('RGB_R'):
                                                thread.rgb_r = int(row.get('RGB_R', 0))
                                                thread.rgb_g = int(row.get('RGB_G', 0))
                                                thread.rgb_b = int(row.get('RGB_B', 0))
                                            
                                            thread.category = 'Standard'
                                            thread.updated_by = current_user.username
                                            thread.active = True
                                            
                                            imported += 1
                                    except Exception as e:
                                        print(f"Fehler beim Import: {e}")
                                
                                db.session.commit()
                                
                                # Aktivität protokollieren
                                log_activity('threads_imported_pdf', 
                                            f'{imported} Garne aus PDF importiert')
                                
                                flash(f'{imported} Garne erfolgreich aus PDF extrahiert und importiert!', 'success')
                                
                            # Lösche temporäre CSV
                            os.remove(latest_csv)
                        else:
                            flash('Keine Farben konnten aus der PDF extrahiert werden.', 'warning')
                    else:
                        flash(f'PDF-Analyse fehlgeschlagen: {result.stderr}', 'danger')
                else:
                    flash('PDF-Analyzer nicht gefunden. Bitte stellen Sie sicher, dass Universal_Thread_Analyzer.py existiert.', 'danger')
                    
            except Exception as e:
                flash(f'Fehler beim PDF-Import: {str(e)}', 'danger')
            finally:
                # Temporäre Datei löschen
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            
            return redirect(url_for('thread.index'))
        else:
            flash(f'Ungültiges Dateiformat für {import_type}-Import!', 'danger')
            return redirect(request.url)
    
    return render_template('threads/import.html')

@thread_bp.route('/api/search')
@login_required
def api_search():
    """Garn-Suche für Autocomplete"""
    query = request.args.get('q', '')
    
    if len(query) < 2:
        return jsonify([])
    
    threads = Thread.query.filter(
        db.or_(
            Thread.color_number.ilike(f'%{query}%'),
            Thread.color_name_de.ilike(f'%{query}%'),
            Thread.color_name_en.ilike(f'%{query}%')
        )
    ).filter_by(active=True).limit(20).all()
    
    results = []
    for thread in threads:
        results.append({
            'id': thread.id,
            'text': f"{thread.manufacturer} {thread.color_number} - {thread.color_name_de or thread.color_name_en}",
            'color': thread.hex_color
        })
    
    return jsonify(results)

@thread_bp.route('/usage')
@login_required
def usage_overview():
    """Übersicht über Garnverbrauch"""
    from sqlalchemy import func
    from datetime import timedelta

    # Zeiträume für Filter
    period = request.args.get('period', '30')  # 7, 30, 90 Tage
    days = int(period)
    start_date = datetime.utcnow() - timedelta(days=days)

    # Gesamtverbrauch nach Thread
    thread_usage_stats = db.session.query(
        Thread.manufacturer,
        Thread.color_number,
        Thread.color_name_de,
        Thread.hex_color,
        func.sum(ThreadUsage.quantity_used).label('total_used'),
        func.count(ThreadUsage.id).label('usage_count')
    ).join(ThreadUsage, Thread.id == ThreadUsage.thread_id)\
     .filter(ThreadUsage.used_at >= start_date)\
     .group_by(Thread.id)\
     .order_by(func.sum(ThreadUsage.quantity_used).desc())\
     .limit(50).all()

    # Verbrauch nach Maschine
    machine_usage_stats = db.session.query(
        ThreadUsage.machine_id,
        func.count(ThreadUsage.id).label('usage_count'),
        func.sum(ThreadUsage.quantity_used).label('total_used')
    ).filter(ThreadUsage.used_at >= start_date, ThreadUsage.machine_id.isnot(None))\
     .group_by(ThreadUsage.machine_id)\
     .order_by(func.sum(ThreadUsage.quantity_used).desc())\
     .all()

    # Verbrauch nach Auftrag
    order_usage_stats = db.session.query(
        ThreadUsage.order_id,
        func.count(ThreadUsage.id).label('usage_count'),
        func.sum(ThreadUsage.quantity_used).label('total_used')
    ).filter(ThreadUsage.used_at >= start_date, ThreadUsage.order_id.isnot(None))\
     .group_by(ThreadUsage.order_id)\
     .order_by(func.sum(ThreadUsage.quantity_used).desc())\
     .limit(20).all()

    # Letzte Erfassungen
    recent_usage = ThreadUsage.query\
        .order_by(ThreadUsage.used_at.desc())\
        .limit(50).all()

    return render_template('threads/usage_overview.html',
                         thread_stats=thread_usage_stats,
                         machine_stats=machine_usage_stats,
                         order_stats=order_usage_stats,
                         recent_usage=recent_usage,
                         period=period)

@thread_bp.route('/usage/record', methods=['GET', 'POST'])
@login_required
def record_usage():
    """Garnverbrauch erfassen"""
    from src.models import Machine, Order

    if request.method == 'POST':
        try:
            # Hole Formulardaten
            thread_id = request.form.get('thread_id')
            quantity_used = float(request.form.get('quantity_used', 0))
            machine_id = request.form.get('machine_id')
            order_id = request.form.get('order_id')
            usage_type = request.form.get('usage_type', 'production')
            notes = request.form.get('notes', '')

            # Validierung
            if not thread_id or quantity_used <= 0:
                flash('Bitte Garn und Menge angeben', 'danger')
                return redirect(url_for('thread.record_usage'))

            # Prüfe ob Thread existiert
            thread = Thread.query.get(thread_id)
            if not thread:
                flash('Garn nicht gefunden', 'danger')
                return redirect(url_for('thread.record_usage'))

            # Erstelle ThreadUsage Eintrag
            usage = ThreadUsage(
                thread_id=thread_id,
                quantity_used=quantity_used,
                machine_id=machine_id if machine_id else None,
                order_id=order_id if order_id else None,
                usage_type=usage_type,
                recorded_by=current_user.username,
                notes=notes,
                used_at=datetime.utcnow()
            )

            db.session.add(usage)

            # Aktualisiere Lagerbestand
            stock = ThreadStock.query.filter_by(thread_id=thread_id).first()
            if stock:
                stock.quantity = max(0, stock.quantity - quantity_used)
                stock.last_updated = datetime.utcnow()

            db.session.commit()

            log_activity('thread_usage_recorded',
                        f'Garnverbrauch erfasst: {thread.color_name_de} ({quantity_used}m)')

            flash(f'Garnverbrauch erfasst: {quantity_used}m von {thread.color_name_de}', 'success')
            return redirect(url_for('thread.usage_overview'))

        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Erfassen: {str(e)}', 'danger')
            return redirect(url_for('thread.record_usage'))

    # GET - Zeige Formular
    threads = Thread.query.order_by(Thread.manufacturer, Thread.color_number).all()
    machines = Machine.query.order_by(Machine.name).all()
    orders = Order.query.filter(Order.status.in_(['accepted', 'in_progress']))\
        .order_by(Order.created_at.desc()).limit(50).all()

    return render_template('threads/record_usage.html',
                         threads=threads,
                         machines=machines,
                         orders=orders)

# Hilfsfunktionen
def get_thread_by_id(thread_id):
    """Garn nach ID abrufen"""
    return Thread.query.get(thread_id)
