"""
Order Controller - PostgreSQL-Version
Auftrags-Verwaltung mit Datenbank
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
from src.models import db, Order, Customer, Article, OrderItem, ActivityLog, Supplier, CompanySettings
from sqlalchemy import text
from src.utils.activity_logger import log_activity
from src.utils.dst_analyzer import analyze_dst_file_robust
from werkzeug.utils import secure_filename
import json
import os

# Blueprint erstellen
order_bp = Blueprint('orders', __name__, url_prefix='/orders')

def generate_order_id():
    """Generiere neue Auftrags-ID - delegiert an IdGeneratorService"""
    from src.services.id_generator_service import IdGenerator
    return IdGenerator.order()

@order_bp.route('/')
@login_required
def index():
    """Auftrags-Übersicht"""
    status_filter = request.args.get('status', '')
    search_query = request.args.get('search', '').lower()
    show_archived = request.args.get('show_archived', '0') == '1'

    # Query erstellen
    query = Order.query

    # Standardmäßig: Stornierte und bereits abgerechnete (invoiced) ausblenden
    HIDDEN_STATUSES = ['cancelled', 'invoiced']
    if not show_archived:
        query = query.filter(Order.archived_at == None)
        if not status_filter:
            # Kein expliziter Filter → verstecke abgeschlossene
            query = query.filter(Order.status.notin_(HIDDEN_STATUSES))
            query = query.filter(db.or_(
                Order.workflow_status == None,
                Order.workflow_status.notin_(['invoiced', 'completed'])
            ))

    if status_filter:
        query = query.filter_by(status=status_filter)

    if search_query:
        query = query.join(Customer).filter(
            db.or_(
                Order.id.ilike(f'%{search_query}%'),
                Order.order_number.ilike(f'%{search_query}%'),
                Customer.company_name.ilike(f'%{search_query}%'),
                Customer.first_name.ilike(f'%{search_query}%'),
                Customer.last_name.ilike(f'%{search_query}%'),
                Order.description.ilike(f'%{search_query}%')
            )
        )

    # Nach Datum sortieren (neueste zuerst)
    orders = query.order_by(Order.created_at.desc()).all()

    return render_template('orders/index.html',
                         orders=orders,
                         status_filter=status_filter,
                         search_query=search_query,
                         show_archived=show_archived)

@order_bp.route('/new')
@login_required
def new():
    """Weiterleitung zum Auftrags-Wizard (Step-by-Step)"""
    customer_id = request.args.get('customer_id')
    if customer_id:
        return redirect(url_for('wizard.step1', customer_id=customer_id))
    return redirect(url_for('wizard.start', reset=1))


@order_bp.route('/new-classic', methods=['GET', 'POST'])
@login_required
def new_classic():
    """Klassisches Auftragsformular (Fallback)"""
    if request.method == 'POST':
        # Hilfsfunktion zum Parsen von Datumsfeldern
        def parse_date(date_str):
            """Parst Datumsstring zu date-Objekt oder None (für Date-Spalten)"""
            if not date_str or date_str.strip() == '':
                return None
            try:
                return datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
            except (ValueError, AttributeError):
                return None

        def parse_datetime(date_str):
            """Parst Datumsstring zu datetime-Objekt oder None (für DateTime-Spalten)"""
            if not date_str or date_str.strip() == '':
                return None
            try:
                return datetime.strptime(date_str.strip(), '%Y-%m-%d')
            except (ValueError, AttributeError):
                return None

        # Abweichender Rechnungsempfaenger
        billing_customer_id = None
        if request.form.get('has_billing_customer') == 'on':
            billing_customer_id = request.form.get('billing_customer_id') or None

        # Neuen Auftrag erstellen
        order = Order(
            id=generate_order_id(),
            order_number=generate_order_id(),  # Gleich wie ID
            customer_id=request.form.get('customer_id'),
            billing_customer_id=billing_customer_id,
            order_type=request.form.get('order_type', 'embroidery'),
            status='accepted',
            description=request.form.get('description', ''),
            internal_notes=request.form.get('notes', ''),
            customer_notes=request.form.get('customer_notes', ''),
            total_price=float(request.form.get('price', 0) or 0),
            due_date=parse_datetime(request.form.get('pickup_date')),
            rush_order=request.form.get('rush_order', False) == 'on',
            is_kundenware=request.form.get('is_kundenware', False) == 'on',
            created_by=current_user.username
        )
        
        # Order-Type spezifische Felder
        if order.order_type in ['embroidery', 'combined']:
            order.stitch_count = int(request.form.get('stitch_count', 0) or 0)
            order.design_width_mm = float(request.form.get('design_width_mm', 0) or 0)
            order.design_height_mm = float(request.form.get('design_height_mm', 0) or 0)
            order.embroidery_position = request.form.get('embroidery_position', '')
            order.embroidery_size = request.form.get('embroidery_size', '')
            order.thread_colors = request.form.get('thread_colors', '')
        
        if order.order_type in ['printing', 'dtf', 'combined']:
            order.print_width_cm = float(request.form.get('print_width_cm', 0) or 0)
            order.print_height_cm = float(request.form.get('print_height_cm', 0) or 0)
            order.print_method = request.form.get('print_method', '')
            order.ink_coverage_percent = int(request.form.get('ink_coverage_percent', 50) or 50)
            order.print_colors = request.form.get('selected_print_colors') or None

        # Design-Workflow-Felder (NEU)
        design_status = request.form.get('design_status', 'none')
        order.design_status = design_status
        
        if design_status == 'needs_order':
            order.design_supplier_id = request.form.get('design_supplier_id') or None
            order.design_order_notes = request.form.get('design_order_notes')
            order.design_expected_date = parse_date(request.form.get('design_expected_date'))
        
        elif design_status == 'customer_provided':
            # Wenn Kunde Design bereitstellt, aber keine Datei hochgeladen wurde
            if not ('design_file' in request.files and request.files['design_file'].filename):
                order.design_status = 'none'  # Zurücksetzen auf "none" wenn keine Datei
        
        # Design-Datei hochladen (wenn vorhanden)
        design_file_processed = False

        if 'design_file' in request.files:
            file = request.files['design_file']
            if file and file.filename:
                # Sichere Dateiname generieren
                filename = f"{order.id}_{secure_filename(file.filename)}"
                upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'designs')
                os.makedirs(upload_dir, exist_ok=True)
                upload_path = os.path.join(upload_dir, filename)
                file.save(upload_path)
                order.design_file_path = upload_path
                order.design_file = f"uploads/designs/{filename}"
                design_file_processed = True

                # Status auf "customer_provided" setzen wenn Datei hochgeladen
                if order.design_status == 'none':
                    order.design_status = 'customer_provided'

        # NEU: Wenn ein Dateipfad über den File-Browser ausgewählt wurde
        design_file_path_input = request.form.get('design_file_path', '').strip()
        if design_file_path_input and not design_file_processed:
            # Prüfe ob die Datei existiert
            if os.path.exists(design_file_path_input):
                # Kopiere die Datei in den Upload-Ordner
                original_filename = os.path.basename(design_file_path_input)
                filename = f"{order.id}_{secure_filename(original_filename)}"
                upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'designs')
                os.makedirs(upload_dir, exist_ok=True)
                upload_path = os.path.join(upload_dir, filename)

                # Datei kopieren
                import shutil
                shutil.copy2(design_file_path_input, upload_path)

                order.design_file_path = upload_path
                order.design_file = f"uploads/designs/{filename}"
                design_file_processed = True

                # Status auf "customer_provided" setzen
                if order.design_status == 'none':
                    order.design_status = 'customer_provided'

        # NEU: DST-Datei analysieren wenn vorhanden
        if design_file_processed and order.design_file_path:
            file_ext = os.path.splitext(order.design_file_path)[1].lower()
            if file_ext in ['.dst', '.pes', '.jef', '.exp']:
                try:
                    analysis = analyze_dst_file_robust(order.design_file_path)
                    if analysis.get('success'):
                        # Nur überschreiben wenn nicht manuell eingegeben
                        if not order.stitch_count or order.stitch_count == 0:
                            order.stitch_count = analysis.get('stitch_count', 0)
                        if not order.design_width_mm or order.design_width_mm == 0:
                            order.design_width_mm = analysis.get('width_mm', 0)
                        if not order.design_height_mm or order.design_height_mm == 0:
                            order.design_height_mm = analysis.get('height_mm', 0)
                        # Speichere komplette Analyse als JSON
                        order.file_analysis = json.dumps(analysis)
                except Exception as e:
                    current_app.logger.error(f"Fehler bei DST-Analyse: {e}")
        
        # In Datenbank speichern
        db.session.add(order)
        db.session.commit()
        
        # Artikel hinzufügen
        article_ids = request.form.getlist('article_id[]')
        quantities = request.form.getlist('quantity[]')
        sizes = request.form.getlist('size[]')
        colors = request.form.getlist('color[]')
        
        # Sublimation-Felder (global für den Auftrag)
        sublimation_position = request.form.get('sublimation_position', '')
        is_non_textile = request.form.get('is_non_textile') == 'on'
        non_textile_type = request.form.get('non_textile_type', '')

        for i, article_id in enumerate(article_ids):
            if article_id:
                item = OrderItem(
                    order_id=order.id,
                    article_id=article_id,
                    quantity=int(quantities[i]) if i < len(quantities) else 1,
                    textile_size=sizes[i] if i < len(sizes) else '',
                    textile_color=colors[i] if i < len(colors) else ''
                )

                # Sublimation-Felder auf Item setzen
                if order.order_type in ['printing', 'dtf', 'combined'] and order.print_method == 'sublimation':
                    item.sublimation_position = sublimation_position
                    item.is_non_textile = is_non_textile
                    item.non_textile_type = non_textile_type if is_non_textile else ''

                # Preis aus Artikel übernehmen
                article = Article.query.get(article_id)
                if article:
                    item.unit_price = article.price

                db.session.add(item)
        
        db.session.commit()

        # Auto-Berechnung: Wenn Preis 0, aus Komponenten berechnen (zentral ueber OrderService)
        from src.services.order_service import OrderService
        OrderService.aktualisiere_preis_wenn_noetig(order)
        db.session.commit()

        # Aktivität protokollieren
        log_activity('order_created',
                    f'Auftrag erstellt: {order.id} für {order.customer.display_name if order.customer else "Unbekannt"}')

        flash(f'Auftrag {order.id} wurde erstellt! Sie können jetzt mehrere Design-Positionen hinzufügen.', 'success')
        # Zur Edit-Seite weiterleiten, damit Multi-Designs hinzugefügt werden können
        return redirect(url_for('orders.edit', order_id=order.id))
    
    # Kunden und Artikel für Formular laden
    customers_list = Customer.query.order_by(Customer.company_name, Customer.last_name).all()
    articles_list = Article.query.filter_by(active=True).order_by(Article.name).all()
    suppliers_list = Supplier.query.filter_by(active=True).order_by(Supplier.name).all()
    
    # In Dictionary umwandeln für Template-Kompatibilität
    customers = {}
    for customer in customers_list:
        customers[customer.id] = customer
    
    articles = {}
    for article in articles_list:
        articles[article.id] = article
        
    suppliers = {}
    for supplier in suppliers_list:
        suppliers[supplier.id] = supplier
    
    # Vorauswahl wenn customer_id übergeben wurde
    selected_customer_id = request.args.get('customer_id')
    
    return render_template('orders/new.html',
                         customers=customers,
                         articles=articles,
                         suppliers=suppliers,
                         selected_customer_id=selected_customer_id)

@order_bp.route('/<order_id>')
@login_required
def show(order_id):
    """Auftrags-Details anzeigen"""
    order = Order.query.get_or_404(order_id)
    
    # Lieferanten für Design-Workflow laden
    suppliers = Supplier.query.filter_by(active=True).order_by(Supplier.name).all()
    
    # Status-Historie laden
    status_history = order.status_history.order_by(text('changed_at desc')).all()
    
    # Berechne Bestell-Statistiken
    items_to_order = 0
    items_ordered = 0
    items_delivered = 0
    
    for item in order.items:
        if item.supplier_order_status == 'none':
            # Prüfe ob Lagerbestand ausreicht
            if item.article and (item.article.stock or 0) < item.quantity:
                items_to_order += 1
        elif item.supplier_order_status == 'ordered':
            items_ordered += 1
        elif item.supplier_order_status == 'delivered':
            items_delivered += 1

    # Maschinen für Produktionsplanung laden
    from src.models.models import Machine
    machines = Machine.query.filter_by(status='active').order_by(Machine.name).all()
    
    # CRM-Aktivitäten laden (Telefonate, Besuche, E-Mails aus ProductionBlock)
    activities = []
    try:
        from src.models import ProductionBlock
        activities = ProductionBlock.query.filter(
            ProductionBlock.order_id == order_id,
            ProductionBlock.is_active == True
        ).order_by(
            ProductionBlock.start_date.desc(),
            ProductionBlock.start_time.desc()
        ).limit(10).all()
    except Exception as e:
        # ProductionBlock noch nicht migriert - ignorieren
        pass

    # Letzte Kunden-Benachrichtigungen laden
    notification_logs = []
    try:
        from src.models.email_automation import EmailAutomationLog
        notification_logs = EmailAutomationLog.query.filter_by(
            order_id=order_id
        ).order_by(EmailAutomationLog.created_at.desc()).limit(5).all()
    except Exception:
        pass

    # Workflow-Timeline
    timeline = order.get_workflow_timeline()

    # Design-Positionen und -Typen für Multi-Position-Management
    from src.models.order_workflow import OrderDesign
    position_choices = OrderDesign.get_position_choices_dynamic()
    design_type_choices = OrderDesign.get_design_type_choices_dynamic()

    return render_template('orders/show.html',
                         order=order,
                         suppliers=suppliers,
                         status_history=status_history,
                         items_to_order=items_to_order,
                         items_ordered=items_ordered,
                         items_delivered=items_delivered,
                         machines=machines,
                         activities=activities,
                         notification_logs=notification_logs,
                         timeline=timeline,
                         position_choices=position_choices,
                         design_type_choices=design_type_choices)


@order_bp.route('/<order_id>/manual-design-approval', methods=['POST'])
@login_required
def manual_design_approval(order_id):
    """Design manuell freigeben (ohne E-Mail-Versand, z.B. telefonische Zusage)"""
    order = Order.query.get_or_404(order_id)

    reason = request.form.get('approval_reason', 'telefon')
    notes = request.form.get('approval_notes', '')
    reason_labels = {
        'telefon': 'Telefonische Zusage',
        'persoenlich': 'Persoenliche Absprache',
        'email': 'E-Mail Bestaetigung',
        'stammkunde': 'Stammkunde',
        'intern': 'Intern freigegeben',
    }

    order.design_approval_status = 'approved'
    order.design_approval_date = datetime.utcnow()
    order.design_approval_notes = f"[Manuell] {reason_labels.get(reason, reason)}: {notes}".strip()

    # Auch order_designs als approved markieren
    try:
        from src.models.order_workflow import OrderDesign
        designs = OrderDesign.query.filter_by(order_id=order_id).all()
        for d in designs:
            d.approval_status = 'approved'
            d.approved_at = datetime.utcnow()
    except Exception:
        pass

    db.session.commit()

    log_activity('design_approved_manual',
                f'Design manuell freigegeben: Auftrag {order_id} ({reason_labels.get(reason, reason)})')

    flash(f'Design fuer Auftrag {order_id} manuell freigegeben ({reason_labels.get(reason, reason)}).', 'success')
    return redirect(url_for('orders.show', order_id=order_id))


@order_bp.route('/<order_id>/photos')
@login_required
def photos(order_id):
    """Foto-Seite für Auftrag (Mobile-optimiert)"""
    order = Order.query.get_or_404(order_id)
    return render_template('orders/photos.html', order=order)

@order_bp.route('/<order_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(order_id):
    """Auftrag bearbeiten"""
    order = Order.query.get_or_404(order_id)

    if request.method == 'POST':
        # Hilfsfunktion zum Parsen von Datumsfeldern
        def parse_datetime(date_str):
            """Parst Datumsstring zu datetime-Objekt oder None (für DateTime-Spalten)"""
            if not date_str or date_str.strip() == '':
                return None
            try:
                return datetime.strptime(date_str.strip(), '%Y-%m-%d')
            except (ValueError, AttributeError):
                return None

        # Auftrag aktualisieren
        order.customer_id = request.form.get('customer_id')

        # Abweichender Rechnungsempfaenger
        if request.form.get('has_billing_customer') == 'on':
            order.billing_customer_id = request.form.get('billing_customer_id') or None
        else:
            order.billing_customer_id = None

        order.order_type = request.form.get('order_type', 'embroidery')
        order.description = request.form.get('description', '')
        order.internal_notes = request.form.get('notes', '')
        order.customer_notes = request.form.get('customer_notes', '')
        order.total_price = float(request.form.get('price', 0) or 0)
        order.due_date = parse_datetime(request.form.get('pickup_date'))
        order.rush_order = request.form.get('rush_order', False) == 'on'
        order.is_kundenware = request.form.get('is_kundenware', False) == 'on'
        order.updated_at = datetime.utcnow()
        order.updated_by = current_user.username
        
        # Order-Type spezifische Felder
        if order.order_type in ['embroidery', 'combined']:
            order.stitch_count = int(request.form.get('stitch_count', 0) or 0)
            order.design_width_mm = float(request.form.get('design_width_mm', 0) or 0)
            order.design_height_mm = float(request.form.get('design_height_mm', 0) or 0)
            order.embroidery_position = request.form.get('embroidery_position', '')
            order.embroidery_size = request.form.get('embroidery_size', '')
            order.thread_colors = request.form.get('thread_colors', '')
        
        if order.order_type in ['printing', 'dtf', 'combined']:
            order.print_width_cm = float(request.form.get('print_width_cm', 0) or 0)
            order.print_height_cm = float(request.form.get('print_height_cm', 0) or 0)
            order.print_method = request.form.get('print_method', '')
            order.ink_coverage_percent = int(request.form.get('ink_coverage_percent', 50) or 50)
            order.print_colors = request.form.get('selected_print_colors') or None

        # Design-Workflow Felder
        design_status = request.form.get('design_status', '').strip()
        if design_status:
            order.design_status = design_status
        else:
            order.design_status = 'none'

        if design_status == 'logo_needs_creation':
            order.designer_id = request.form.get('designer_id') or None
            order.design_expected_date = parse_datetime(request.form.get('design_expected_date'))
            order.design_requirements = request.form.get('design_requirements', '').strip() or None
            order.design_priority = request.form.get('design_priority', 'normal')
            order.design_cost = float(request.form.get('design_cost', 0) or 0)

        elif design_status == 'logo_needs_adaptation':
            order.original_logo_path = request.form.get('original_logo_path', '').strip() or None
            order.adaptation_days = int(request.form.get('adaptation_days', 0) or 0) or None
            order.adaptation_details = request.form.get('adaptation_details', '').strip() or None
            order.target_format = request.form.get('target_format', '').strip() or None
            order.adaptation_cost = float(request.form.get('adaptation_cost', 0) or 0)

        elif design_status == 'logo_available':
            # Design-Datei Upload
            design_file_processed = False
            if 'design_file' in request.files:
                file = request.files['design_file']
                if file and file.filename:
                    filename = f"{order.id}_{secure_filename(file.filename)}"
                    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'designs')
                    os.makedirs(upload_dir, exist_ok=True)
                    upload_path = os.path.join(upload_dir, filename)
                    file.save(upload_path)
                    order.design_file_path = upload_path
                    order.design_file = f"uploads/designs/{filename}"
                    design_file_processed = True
                    order.design_status = 'customer_provided'

            # Dateipfad ueber File-Browser
            design_file_path_input = request.form.get('design_file_path', '').strip()
            if design_file_path_input and not design_file_processed:
                if os.path.exists(design_file_path_input):
                    import shutil
                    original_filename = os.path.basename(design_file_path_input)
                    filename = f"{order.id}_{secure_filename(original_filename)}"
                    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'designs')
                    os.makedirs(upload_dir, exist_ok=True)
                    upload_path = os.path.join(upload_dir, filename)
                    shutil.copy2(design_file_path_input, upload_path)
                    order.design_file_path = upload_path
                    order.design_file = f"uploads/designs/{filename}"
                    order.design_status = 'customer_provided'

        # Bestehende Artikel aktualisieren
        existing_ids = request.form.getlist('existing_item_id[]')
        existing_quantities = request.form.getlist('existing_quantity[]')
        existing_unit_prices = request.form.getlist('existing_unit_price[]')
        existing_sizes = request.form.getlist('existing_size[]')
        existing_colors = request.form.getlist('existing_color[]')
        delete_ids = [x for x in request.form.getlist('delete_item[]') if x]

        for i, item_id_str in enumerate(existing_ids):
            item_id = int(item_id_str)
            if str(item_id) in delete_ids:
                item = OrderItem.query.get(item_id)
                if item:
                    db.session.delete(item)
            else:
                item = OrderItem.query.get(item_id)
                if item:
                    item.quantity = int(existing_quantities[i]) if i < len(existing_quantities) else item.quantity
                    if i < len(existing_unit_prices):
                        item.unit_price = float(existing_unit_prices[i] or 0)
                    item.textile_size = existing_sizes[i] if i < len(existing_sizes) else item.textile_size
                    item.textile_color = existing_colors[i] if i < len(existing_colors) else item.textile_color

        # Neue Artikel hinzufuegen
        new_article_ids = request.form.getlist('new_article_id[]')
        new_quantities = request.form.getlist('new_quantity[]')
        new_unit_prices = request.form.getlist('new_unit_price[]')
        new_sizes = request.form.getlist('new_size[]')
        new_colors = request.form.getlist('new_color[]')

        for i, article_id in enumerate(new_article_ids):
            if article_id:
                article = Article.query.get(article_id)
                # Benutzer-Preis hat Vorrang, sonst Artikel-Preis
                user_price = float(new_unit_prices[i] or 0) if i < len(new_unit_prices) else 0
                if user_price == 0 and article and article.price:
                    user_price = article.price
                new_item = OrderItem(
                    order_id=order.id,
                    article_id=article_id,
                    quantity=int(new_quantities[i]) if i < len(new_quantities) else 1,
                    textile_size=new_sizes[i] if i < len(new_sizes) else '',
                    textile_color=new_colors[i] if i < len(new_colors) else '',
                    unit_price=user_price
                )
                db.session.add(new_item)

        # Auto-Berechnung: Wenn Preis 0, aus Komponenten berechnen (zentral ueber OrderService)
        db.session.flush()
        from src.services.order_service import OrderService
        OrderService.aktualisiere_preis_wenn_noetig(order)

        # Aenderungen speichern
        db.session.commit()

        # Aktivität protokollieren
        log_activity('order_updated',
                    f'Auftrag aktualisiert: {order.id}')

        flash(f'Auftrag {order.id} wurde aktualisiert!', 'success')
        return redirect(url_for('orders.show', order_id=order.id))
    
    # Kunden und Artikel für Formular laden
    customers_list = Customer.query.order_by(Customer.company_name, Customer.last_name).all()
    articles_list = Article.query.filter_by(active=True).order_by(Article.name).all()

    # Maschinen für Produktionsplanung laden
    from src.models.models import Machine
    machines = Machine.query.filter_by(status='active').order_by(Machine.name).all()

    # Lieferanten für externe Design-Bestellung
    suppliers = Supplier.query.filter_by(active=True).order_by(Supplier.name).all()

    # In Dictionary umwandeln für Template-Kompatibilität
    customers = {}
    for customer in customers_list:
        customers[customer.id] = customer

    articles = {}
    for article in articles_list:
        articles[article.id] = article

    # Design-Positionen und -Typen für Multi-Position-Management
    from src.models.order_workflow import OrderDesign
    position_choices = OrderDesign.get_position_choices_dynamic()
    design_type_choices = OrderDesign.get_design_type_choices_dynamic()

    return render_template('orders/edit.html',
                         order=order,
                         customers=customers,
                         articles=articles,
                         machines=machines,
                         suppliers=suppliers,
                         position_choices=position_choices,
                         design_type_choices=design_type_choices)

@order_bp.route('/<order_id>/status', methods=['POST'])
@login_required
def update_status(order_id):
    """Auftragsstatus aktualisieren - zentral ueber OrderService"""
    from src.services.order_service import OrderService

    new_status = request.form.get('status')
    comment = request.form.get('comment', '')

    if not new_status:
        flash('Kein Status angegeben.', 'warning')
        return redirect(url_for('orders.show', order_id=order_id))

    ok, msg = OrderService.update_status(order_id, new_status, comment)
    if ok:
        log_activity('order_status_changed', f'Auftrag {order_id}: {msg}')
        flash(msg, 'success')
    else:
        flash(msg, 'danger')

    return redirect(url_for('orders.show', order_id=order_id))


@order_bp.route('/<order_id>/notify', methods=['POST'])
@login_required
def send_customer_notification(order_id):
    """Manuelle Kunden-Benachrichtigung senden"""
    order = Order.query.get_or_404(order_id)

    if not order.customer or not order.customer.email:
        flash('Keine Kunden-E-Mail hinterlegt!', 'danger')
        return redirect(url_for('orders.show', order_id=order_id))

    notification_type = request.form.get('type', '')

    # Vordefinierte Benachrichtigungstypen
    type_map = {
        'accepted': ('order_status', 'accepted'),
        'confirmed': ('workflow_status', 'confirmed'),
        'in_progress': ('order_status', 'in_progress'),
        'ready': ('order_status', 'ready'),
        'shipped': ('workflow_status', 'shipped'),
    }

    if notification_type in type_map:
        trigger_event, trigger_value = type_map[notification_type]
        try:
            from src.services.email_automation_service import EmailAutomationService
            automation = EmailAutomationService()
            automation.check_and_send(order, trigger_event, trigger_value)
            flash(f'Benachrichtigung an {order.customer.email} gesendet!', 'success')
        except Exception as e:
            flash(f'Fehler beim Senden: {e}', 'danger')

    elif notification_type == 'custom':
        # Freitext-Nachricht
        subject = request.form.get('subject', '')
        body = request.form.get('body', '')
        if subject and body:
            try:
                from src.services.email_service_new import EmailService
                service = EmailService()
                html_body = f'<p>{body.replace(chr(10), "<br>")}</p>'
                result = service.send_email(
                    to=order.customer.email,
                    subject=subject,
                    body_html=html_body,
                    body_text=body,
                )
                if result.get('success'):
                    # CRM-Kontakthistorie
                    try:
                        from src.models.crm_contact import CustomerContact
                        contact = CustomerContact(
                            customer_id=order.customer.id,
                            contact_type='email_ausgang',
                            subject=subject,
                            body_html=html_body,
                            email_to=order.customer.email,
                            status='gesendet',
                            order_id=order.id,
                            created_by=current_user.username,
                        )
                        db.session.add(contact)
                        db.session.commit()
                    except Exception:
                        pass
                    flash(f'Nachricht an {order.customer.email} gesendet!', 'success')
                else:
                    flash(f'E-Mail-Versand fehlgeschlagen: {result.get("error", "Unbekannter Fehler")}', 'danger')
            except Exception as e:
                flash(f'Fehler: {e}', 'danger')
        else:
            flash('Betreff und Nachricht erforderlich!', 'warning')
    else:
        flash('Unbekannter Benachrichtigungstyp.', 'warning')

    return redirect(url_for('orders.show', order_id=order_id))


@order_bp.route('/<order_id>/delete', methods=['POST'])
@login_required
def delete(order_id):
    """Auftrag löschen"""
    order = Order.query.get_or_404(order_id)
    
    # Nur Aufträge im Status 'cancelled' können gelöscht werden
    if order.status != 'cancelled':
        flash('Nur stornierte Aufträge können gelöscht werden!', 'danger')
        return redirect(url_for('orders.show', order_id=order_id))
    
    # Aktivität protokollieren bevor gelöscht wird
    log_activity('order_deleted', 
                f'Auftrag gelöscht: {order.id}')
    
    # Auftrag und zugehörige Items löschen (cascade)
    db.session.delete(order)
    db.session.commit()
    
    flash(f'Auftrag {order_id} wurde gelöscht!', 'success')
    return redirect(url_for('orders.index'))

# API-Endpoints für AJAX
@order_bp.route('/api/customer/<customer_id>')
@login_required
def api_customer_details(customer_id):
    """Kunden-Details für AJAX abrufen"""
    customer = Customer.query.get_or_404(customer_id)
    return jsonify({
        'id': customer.id,
        'name': customer.display_name,
        'email': customer.email,
        'phone': customer.phone or customer.mobile,
        'address': f"{customer.street} {customer.house_number}, {customer.postal_code} {customer.city}".strip()
    })

@order_bp.route('/api/article/<article_id>')
@login_required
def api_article_details(article_id):
    """Artikel-Details für AJAX abrufen"""
    article = Article.query.get_or_404(article_id)
    return jsonify({
        'id': article.id,
        'name': article.name,
        'price': article.price,
        'stock': article.stock,
        'color': article.color,
        'size': article.size
    })

@order_bp.route('/api/articles/search')
@login_required
def api_article_search():
    """Artikel-Suche für AJAX (Artikelnummer, Name)"""
    search_term = request.args.get('q', '').strip()

    if not search_term:
        return jsonify([])

    # Suche nach Artikelnummer oder Name (Case-insensitive)
    articles = Article.query.filter(
        Article.active == True,
        db.or_(
            Article.article_number.ilike(f'%{search_term}%'),
            Article.name.ilike(f'%{search_term}%')
        )
    ).order_by(Article.name).limit(20).all()

    results = []
    for article in articles:
        results.append({
            'id': article.id,
            'article_number': article.article_number or '',
            'name': article.name,
            'price': float(article.price) if article.price else 0.0,
            'stock': article.stock or 0,
            'color': article.color or '',
            'size': article.size or '',
            'material': article.material or '',
            'weight': float(article.weight) if article.weight else 0.5,
            'display': f"{article.article_number or 'N/A'} - {article.name} - {article.price:.2f}€"
        })

    return jsonify(results)

# Hilfsfunktionen für Templates
def get_customer_display_name(customer):
    """Kunden-Anzeigename generieren"""
    if customer:
        return customer.display_name
    return "Unbekannt"

@order_bp.route('/analyze_file', methods=['POST'])
@login_required
def analyze_file():
    """Design-Datei analysieren (DST, PES, etc.)"""
    if 'design_file' not in request.files:
        return jsonify({'success': False, 'error': 'Keine Datei hochgeladen'})
    
    file = request.files['design_file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Keine Datei ausgewählt'})
    
    # Dateierweiterung prüfen
    filename = file.filename.lower()
    file_ext = os.path.splitext(filename)[1]
    
    # Temporäre Datei speichern
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
        file.save(tmp_file.name)
        tmp_path = tmp_file.name
    
    try:
        if file_ext == '.dst':
            # DST-Datei analysieren mit robustem Analyzer
            try:
                result = analyze_dst_file_robust(tmp_path)
                if result.get('success'):
                    return jsonify({
                        'success': True,
                        'stitch_count': result.get('stitch_count', result.get('total_stitches', 0)),
                        'width_mm': result.get('width_mm', 0),
                        'height_mm': result.get('height_mm', 0),
                        'color_count': result.get('color_count', result.get('estimated_colors', 1)),
                        'analysis_details': {
                            'total_stitches': result.get('total_stitches', 0),
                            'normal_stitches': result.get('normal_stitches', 0),
                            'jump_stitches': result.get('jump_stitches', 0),
                            'color_changes': result.get('color_changes', 0),
                            'density_per_cm2': result.get('density_per_cm2', 0),
                            'estimated_time_minutes': result.get('estimated_time_minutes', 0)
                        }
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': result.get('error', 'Unbekannter Fehler beim Analysieren der DST-Datei')
                    })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Fehler beim Analysieren der DST-Datei: {str(e)}'
                })
        
        elif file_ext in ['.png', '.jpg', '.jpeg']:
            # Bilddatei analysieren
            from PIL import Image
            img = Image.open(tmp_path)
            
            # DPI ermitteln (Standard: 72)
            dpi = img.info.get('dpi', (72, 72))
            if isinstance(dpi, int):
                dpi = (dpi, dpi)
            
            # Größe in cm berechnen
            width_cm = (img.width / dpi[0]) * 2.54
            height_cm = (img.height / dpi[1]) * 2.54
            
            return jsonify({
                'success': True,
                'width_px': img.width,
                'height_px': img.height,
                'width_cm': round(width_cm, 1),
                'height_cm': round(height_cm, 1),
                'dpi': dpi
            })
        
        else:
            return jsonify({
                'success': False,
                'error': f'Dateityp {file_ext} wird noch nicht unterstützt'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Fehler beim Analysieren der Datei: {str(e)}',
            'filename': filename,
            'file_ext': file_ext
        })
    
    finally:
        # Temporäre Datei löschen
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

def analyze_dst_file(filepath):
    """DST-Stickdatei analysieren"""
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
        
        # DST Header lesen (512 Bytes)
        if len(data) < 512:
            raise ValueError("Datei zu klein für DST-Format")
        
        # Koordinaten für Bounding Box
        min_x = max_x = min_y = max_y = 0
        x = y = 0
        stitch_count = 0
        color_changes = 0
        
        # DST-Befehle beginnen nach dem 512-Byte Header
        i = 512
        
        while i < len(data) - 2:
            b1 = data[i]
            b2 = data[i + 1]
            b3 = data[i + 2]
            
            # Prüfe auf Spezial-Befehle
            if b3 & 0xF0 == 0xF0:
                # Farbwechsel
                if b3 == 0xFE and b2 == 0xB0:
                    color_changes += 1
                    i += 3
                    continue
                # Ende der Datei
                elif b3 == 0xF3:
                    break
                # Andere Befehle überspringen
                else:
                    i += 3
                    continue
            
            # Normale Stiche
            # X-Koordinate (b1 und untere 2 Bits von b3)
            dx = b1
            if b3 & 0x01:
                dx = -dx
            
            # Y-Koordinate (b2 und Bits 2-3 von b3)
            dy = b2
            if b3 & 0x02:
                dy = -dy
            
            # 0.1mm Einheiten
            x += dx
            y += dy
            
            # Bounding Box aktualisieren
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)
            
            stitch_count += 1
            i += 3
        
        # Berechne Größe in mm (DST verwendet 0.1mm Einheiten)
        width_mm = (max_x - min_x) / 10.0
        height_mm = (max_y - min_y) / 10.0
        
        return {
            'stitch_count': stitch_count,
            'width_mm': abs(width_mm),
            'height_mm': abs(height_mm),
            'color_count': color_changes + 1  # +1 für die Startfarbe
        }
    
    except Exception as e:
        raise ValueError(f"Fehler beim Lesen der DST-Datei: {str(e)}")

@order_bp.route('/calculate_price', methods=['POST'])
@login_required
def calculate_price():
    """Preis für Auftrag kalkulieren"""
    data = request.get_json()
    
    order_type = data.get('order_type', 'embroidery')
    quantity = int(data.get('quantity', 1))
    textile_items = data.get('textile_items', [])
    
    # Basis-Textilkosten
    textile_cost = 0
    for item in textile_items:
        textile_cost += item['price'] * item['quantity']
    
    # Produktionskosten
    production_cost = 0
    
    # Preise aus Kalkulationseinstellungen laden
    try:
        from src.models.models import PriceCalculationSettings
        calc = PriceCalculationSettings.query.first()
        price_per_1000 = float(calc.price_per_1000_stitches) if calc and calc.price_per_1000_stitches else 1.50
        price_per_cm2 = float(calc.price_per_cm2) if calc and calc.price_per_cm2 else 0.05
        setup_fee = float(calc.setup_fee) if calc and calc.setup_fee else 15.00
    except Exception:
        price_per_1000 = 1.50
        price_per_cm2 = 0.05
        setup_fee = 15.00

    if order_type in ['embroidery', 'combined']:
        stitch_count = int(data.get('stitch_count', 0))
        if stitch_count > 0:
            production_cost += (stitch_count / 1000) * price_per_1000 * quantity

    if order_type in ['printing', 'dtf', 'combined']:
        width_cm = float(data.get('print_width_cm', 0))
        height_cm = float(data.get('print_height_cm', 0))
        if width_cm > 0 and height_cm > 0:
            area_cm2 = width_cm * height_cm
            production_cost += area_cm2 * price_per_cm2 * quantity
    
    # Mengenrabatt
    discount_percent = 0
    if quantity >= 50:
        discount_percent = 5
    elif quantity >= 100:
        discount_percent = 10
    elif quantity >= 250:
        discount_percent = 15
    
    # Gesamtpreis berechnen
    subtotal = textile_cost + production_cost
    discount_amount = subtotal * (discount_percent / 100)
    total = subtotal - discount_amount + setup_fee
    
    return jsonify({
        'textile_cost': round(textile_cost, 2),
        'production_cost': round(production_cost, 2),
        'subtotal': round(subtotal, 2),
        'setup_fee': round(setup_fee, 2),
        'discount_percent': discount_percent,
        'discount_amount': round(discount_amount, 2),
        'total': round(total, 2)
    })


@order_bp.route('/items/<int:item_id>/mark-for-order', methods=['POST'])
@login_required
def mark_item_for_order(item_id):
    """Markiere eine Auftragsposition zur Bestellung"""
    item = OrderItem.query.get_or_404(item_id)
    
    # Prüfe Berechtigung
    if not current_user.is_admin:
        order = Order.query.get(item.order_id)
        if order.created_by != current_user.username:
            return jsonify({'error': 'Keine Berechtigung'}), 403
    
    # Markiere zur Bestellung
    item.supplier_order_status = 'to_order'
    item.supplier_order_notes = f"Markiert zur Bestellung am {datetime.now().strftime('%d.%m.%Y %H:%M')} von {current_user.username}"
    
    db.session.commit()
    
    log_activity('order_item_marked_for_order', 
                f'Position {item_id} zur Bestellung markiert')
    
    return jsonify({'success': True})


@order_bp.route('/<order_id>/design-ordered', methods=['POST'])
@login_required
def mark_design_ordered(order_id):
    """Markiere Design als bestellt"""
    order = Order.query.get_or_404(order_id)

    # Design-Status aktualisieren
    if order.design_status == 'needs_order':
        order.design_status = 'ordered'
        order.design_order_date = datetime.now()
        db.session.commit()

        log_activity('design_marked_ordered',
                    f'Design für Auftrag {order_id} als bestellt markiert')

        return jsonify({'success': True})

    return jsonify({'success': False, 'error': 'Design ist nicht im Status "needs_order"'}), 400


@order_bp.route('/create-quick', methods=['POST'])
@login_required
def create_quick_order():
    """Erstelle schnell eine neue Bestellung ohne Kunde"""
    try:
        # Generiere neue Auftrags-ID
        order_id = generate_order_id()
        
        # Erstelle neue Bestellung
        order = Order(
            id=order_id,
            order_number=order_id,
            status='new',
            created_by=current_user.username,
            order_type='combined'
        )
        
        db.session.add(order)
        db.session.commit()
        
        log_activity('order_created_quick', 
                    f'Schnellbestellung {order_id} erstellt')
        
        return jsonify({
            'success': True,
            'order_id': order_id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@order_bp.route('/current')
@login_required  
def current_order():
    """Aktuelle offene Bestellung für den aktuellen Benutzer"""
    # Suche nach einer offenen Bestellung (Status: new)
    current_order = Order.query.filter_by(
        status='new',
        created_by=current_user.username
    ).order_by(Order.created_at.desc()).first()
    
    if current_order:
        return jsonify({
            'exists': True,
            'order_id': current_order.id,
            'customer': current_order.customer.display_name if current_order.customer else 'Unbekannt',
            'item_count': current_order.items.count()
        })
    else:
        return jsonify({
            'exists': False
        })


@order_bp.route('/<order_id>/add-item', methods=['POST'])
@login_required
def add_item_to_order(order_id):
    """Füge Artikel zu einer Bestellung hinzu"""
    try:
        data = request.get_json()
        article_id = data.get('article_id')
        quantity = data.get('quantity', 1)
        
        # Hole Bestellung und Artikel
        order = Order.query.get_or_404(order_id)
        article = Article.query.get_or_404(article_id)
        
        # Prüfe Berechtigung
        if order.created_by != current_user.username and not current_user.is_admin:
            return jsonify({'error': 'Keine Berechtigung'}), 403
        
        # Erstelle neue Auftragsposition
        order_item = OrderItem(
            order_id=order_id,
            article_id=article_id,
            quantity=quantity,
            unit_price=article.price or 0
        )
        
        db.session.add(order_item)
        db.session.commit()
        
        log_activity('order_item_added', 
                    f'Artikel {article.name} zu Auftrag {order_id} hinzugefügt')
        
        return jsonify({
            'success': True,
            'item_id': order_item.id,
            'message': f'{article.name} wurde zur Bestellung hinzugefügt'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@order_bp.route('/items/<int:item_id>/mark-delivered', methods=['POST'])
@login_required
def mark_item_delivered(item_id):
    """Markiere eine Auftragsposition als geliefert"""
    item = OrderItem.query.get_or_404(item_id)
    
    # Prüfe Berechtigung
    if not current_user.is_admin:
        return jsonify({'error': 'Nur Admins können Lieferungen bestätigen'}), 403
    
    # Markiere als geliefert
    item.supplier_order_status = 'delivered'
    item.supplier_delivered_date = datetime.now().date()
    
    # Aktualisiere Bestand wenn Artikel vorhanden
    if item.article:
        if not item.article.stock:
            item.article.stock = 0
        item.article.stock += item.quantity
        
        # Notiz hinzufügen
        existing_notes = item.supplier_order_notes or ''
        new_note = f"\nGeliefert am {datetime.now().strftime('%d.%m.%Y %H:%M')} von {current_user.username}. Bestand erhöht um {item.quantity}."
        item.supplier_order_notes = (existing_notes + new_note).strip()
    
    db.session.commit()
    
    log_activity(current_user.username, 'order_item_delivered', 
                f'Position {item_id} als geliefert markiert')
    
    # Prüfe ob alle Positionen des Auftrags geliefert sind
    order = Order.query.get(item.order_id)
    all_delivered = all(i.supplier_order_status == 'delivered' or 
                       (i.article and i.article.stock >= i.quantity) 
                       for i in order.items)
    
    return jsonify({
        'success': True,
        'all_delivered': all_delivered,
        'new_stock': item.article.stock if item.article else None
    })


@order_bp.route('/create-quick', methods=['POST'])
@login_required
def create_quick():
    """Schnell-Erstellung einer neuen Bestellung (für interne Zwecke)"""
    data = request.get_json()
    
    try:
        # Generiere neue Order ID
        order_id = generate_order_id()
        
        # Erstelle minimale Bestellung
        order = Order(
            id=order_id,
            order_number=order_id,
            customer_id=data.get('customer_id'),  # Optional
            order_type=data.get('order_type', 'internal'),
            status='new',
            description=data.get('description', 'Schnellbestellung'),
            internal_notes=data.get('notes', 'Erstellt über Artikel-Übersicht'),
            customer_notes='',
            total_price=0,
            created_by=current_user.username
        )
        
        # Falls kein Kunde angegeben, suche oder erstelle internen Kunden
        if not order.customer_id:
            from src.models import Customer
            internal_customer = Customer.query.filter_by(
                company_name='Interner Bedarf'
            ).first()
            
            if not internal_customer:
                # Erstelle internen Kunden
                internal_customer = Customer(
                    id='INTERNAL',
                    customer_type='business',
                    company_name='Interner Bedarf',
                    email='intern@stitchadmin.local',
                    created_by=current_user.username
                )
                db.session.add(internal_customer)
                db.session.flush()
            
            order.customer_id = internal_customer.id
        
        db.session.add(order)
        db.session.commit()
        
        log_activity('quick_order_created', 
                    f'Schnellbestellung {order_id} erstellt')
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'order_number': order.order_number
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@order_bp.route('/<string:order_id>/print/order_sheet')
@login_required
def print_order_sheet(order_id):
    """Vollständiges A4 Auftragsblatt drucken"""
    order = Order.query.get_or_404(order_id)

    # Füge aktuelles Datum für das Template hinzu
    from datetime import datetime
    now = datetime.now()

    # Firmendaten laden
    company = CompanySettings.query.first()

    # Aktivität protokollieren
    log_activity('order_sheet_printed',
                f'Auftragsblatt gedruckt für Bestellung: {order.id}')

    no_prices = request.args.get('production') == '1'

    return render_template('orders/order_sheet.html',
                         order=order,
                         company=company,
                         now=now,
                         no_prices=no_prices)

@order_bp.route('/<string:order_id>/stammblatt')
@login_required
def stammblatt_pdf(order_id):
    """Stammblatt (Design-Datenblatt) als PDF generieren"""
    order = Order.query.get_or_404(order_id)
    company = CompanySettings.query.first()

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        import io as _io

        buf = _io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
                                leftMargin=20*mm, rightMargin=20*mm,
                                topMargin=20*mm, bottomMargin=20*mm)

        styles = getSampleStyleSheet()
        green = colors.HexColor('#1a6b5a')
        light_green = colors.HexColor('#e8f5f0')

        title_style = ParagraphStyle('Title', parent=styles['Heading1'],
                                     textColor=green, fontSize=18, spaceAfter=4)
        label_style = ParagraphStyle('Label', parent=styles['Normal'],
                                     textColor=colors.grey, fontSize=8, spaceAfter=2)
        value_style = ParagraphStyle('Value', parent=styles['Normal'],
                                     fontSize=10, spaceAfter=6, fontName='Helvetica-Bold')

        story = []

        # Header
        company_name = company.company_name if company else 'StitchAdmin'
        story.append(Paragraph(company_name, ParagraphStyle('Co', parent=styles['Normal'],
                                                             fontSize=10, textColor=green)))
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph(f'STAMMBLATT - Auftrag {order.order_number or order.id}', title_style))
        story.append(HRFlowable(width='100%', thickness=2, color=green))
        story.append(Spacer(1, 4*mm))

        def row(label, value):
            return [Paragraph(label, label_style), Paragraph(str(value or '-'), value_style)]

        # Kundendaten
        customer = order.get_billing_customer() if hasattr(order, 'get_billing_customer') else order.customer
        customer_name = customer.display_name if customer else '-'

        data = [
            row('Auftragnummer', order.order_number or order.id),
            row('Kunde / Auftraggeber', order.customer.display_name if order.customer else '-'),
            row('Rechnungsempfaenger', customer_name if customer != order.customer else '-'),
            row('Auftragstyp', {'embroidery': 'Bestickung', 'printing': 'Textildruck',
                                'dtf': 'DTF', 'combined': 'Kombi', 'sublimation': 'Sublimation'
                                }.get(order.order_type, order.order_type or '-')),
            row('Status', order.status or '-'),
            row('Freigabestatus', {'pending': 'Ausstehend', 'approved': 'Freigegeben',
                                   'revision_requested': 'Änderung gewünscht', 'none': '-'
                                   }.get(order.design_approval_status or 'none', '-')),
        ]

        if order.design_approval_date:
            data.append(row('Freigabe am', order.design_approval_date.strftime('%d.%m.%Y %H:%M')))

        # Design-Spezifikationen
        if order.order_type in ('embroidery', 'combined'):
            data += [
                row('Stichzahl', f"{order.stitch_count:,}".replace(',', '.') if order.stitch_count else '-'),
                row('Design-Breite', f"{order.design_width_mm} mm" if order.design_width_mm else '-'),
                row('Design-Hoehe', f"{order.design_height_mm} mm" if order.design_height_mm else '-'),
                row('Stickposition', order.embroidery_position or '-'),
                row('Garnfarben', order.thread_colors or '-'),
            ]
        if order.order_type in ('printing', 'dtf', 'combined'):
            data += [
                row('Druckbreite', f"{order.print_width_cm} cm" if order.print_width_cm else '-'),
                row('Druckhoehe', f"{order.print_height_cm} cm" if order.print_height_cm else '-'),
                row('Druckverfahren', order.print_method or '-'),
                row('Druckposition', order.embroidery_position or '-'),
            ]

        data += [
            row('Beschreibung', order.description or '-'),
            row('Interne Notizen', order.internal_notes or '-'),
            row('Faelligkeitsdatum', order.due_date.strftime('%d.%m.%Y') if order.due_date else '-'),
        ]

        t = Table(data, colWidths=[55*mm, 115*mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), light_green),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f9fcfb')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ccddda')),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
        ]))
        story.append(t)

        # Artikel-Positionen
        if order.items.count() > 0:
            story.append(Spacer(1, 6*mm))
            story.append(Paragraph('Artikel / Textilien', ParagraphStyle('Sec', parent=styles['Heading2'],
                                                                          textColor=green, fontSize=12)))
            story.append(HRFlowable(width='100%', thickness=1, color=green))
            story.append(Spacer(1, 2*mm))

            item_data = [['Artikel', 'Art.Nr.', 'Menge', 'Groesse', 'Farbe', 'Position']]
            for item in order.items:
                item_data.append([
                    item.article.name if item.article else '-',
                    item.article.article_number if item.article else '-',
                    str(item.quantity),
                    item.textile_size or '-',
                    item.textile_color or '-',
                    item.sublimation_position if hasattr(item, 'sublimation_position') and item.sublimation_position else '-'
                ])

            it = Table(item_data, colWidths=[55*mm, 25*mm, 15*mm, 18*mm, 30*mm, 27*mm])
            it.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), green),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ccddda')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fcfb')]),
            ]))
            story.append(it)

        # Footer
        story.append(Spacer(1, 10*mm))
        story.append(HRFlowable(width='100%', thickness=0.5, color=colors.grey))
        from datetime import datetime as _dt
        story.append(Paragraph(
            f'Erstellt am {_dt.now().strftime("%d.%m.%Y %H:%M")} von {current_user.username} | StitchAdmin',
            ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7, textColor=colors.grey, alignment=TA_CENTER)
        ))

        doc.build(story)
        buf.seek(0)

        from flask import send_file as _send_file
        return _send_file(buf, mimetype='application/pdf',
                          download_name=f'Stammblatt_{order.order_number or order.id}.pdf',
                          as_attachment=False)

    except Exception as e:
        current_app.logger.error(f"Stammblatt-Fehler: {e}")
        flash(f'Fehler beim Erstellen des Stammblatts: {str(e)}', 'danger')
        return redirect(url_for('orders.show', order_id=order_id))


@order_bp.route('/<string:order_id>/print/production_labels')
@login_required
def print_production_labels(order_id):
    """Produktions-Etiketten für Zebra-Drucker"""
    order = Order.query.get_or_404(order_id)
    
    # Füge aktuelles Datum für das Template hinzu
    from datetime import datetime
    now = datetime.now()
    
    # Aktivität protokollieren
    log_activity('production_labels_printed', 
                f'Produktions-Etiketten gedruckt für Bestellung: {order.id}')
    
    return render_template('orders/production_labels.html', 
                         order=order,
                         now=now)

@order_bp.route('/create_logo_order', methods=['GET', 'POST'])
@login_required
def create_logo_order():
    """Logo/Design-Bestellung erstellen"""
    if request.method == 'POST':
        try:
            # TODO: Implementiere Logo-Order-Erstellung
            # Erstelle Eintrag in logo_orders Tabelle
            flash('Logo-Bestellung wurde erstellt', 'success')
            
            # Wenn order_id vorhanden, zurück zur Bestellung
            order_id = request.form.get('order_id')
            if order_id:
                return redirect(url_for('orders.show', order_id=order_id))
            return redirect(url_for('orders.index'))
            
        except Exception as e:
            flash(f'Fehler beim Erstellen der Logo-Bestellung: {str(e)}', 'error')
            return redirect(request.url)
    
    # GET Request - Zeige Formular
    order_id = request.args.get('order_id')
    order = None
    description = ''
    
    if order_id:
        order = Order.query.get(order_id)
        if order:
            description = f"Logo/Design für Auftrag {order.order_number or order.id}"
            if order.design_description:
                description += f"\n{order.design_description}"
    
    # Hole aktive Lieferanten
    suppliers = Supplier.query.filter_by(active=True).order_by(Supplier.name).all()
    
    return render_template('orders/create_logo_order.html',
                         order=order,
                         description=description,
                         suppliers=suppliers)

@order_bp.route('/<string:order_id>/upload_design', methods=['POST'])
@login_required
def upload_design(order_id):
    """Design-Datei für Auftrag hochladen"""
    order = Order.query.get_or_404(order_id)
    
    if 'design_file' not in request.files:
        flash('Keine Datei ausgewählt', 'error')
        return redirect(url_for('orders.show', order_id=order_id))
    
    file = request.files['design_file']
    if file.filename == '':
        flash('Keine Datei ausgewählt', 'error')
        return redirect(url_for('orders.show', order_id=order_id))
    
    if file:
        # Sichere Dateiname generieren
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{order.order_number or order.id}_{timestamp}_{filename}"
        
        # Upload-Verzeichnis erstellen falls nicht vorhanden
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'designs')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Datei speichern
        filepath = os.path.join(upload_dir, unique_filename)
        file.save(filepath)
        
        # Order aktualisieren
        order.design_file = f"uploads/designs/{unique_filename}"
        order.design_file_path = filepath
        order.updated_at = datetime.utcnow()
        order.updated_by = current_user.username
        
        # Optional: Beschreibung hinzufügen
        file_description = request.form.get('file_description')
        if file_description:
            if order.design_description:
                order.design_description += f"\n\nDatei-Info: {file_description}"
            else:
                order.design_description = f"Datei-Info: {file_description}"
        
        db.session.commit()
        
        # Aktivität protokollieren
        log_activity('design_uploaded', 
                    f'Design-Datei hochgeladen für Auftrag {order.order_number or order.id}: {filename}')
        
        flash('Design-Datei erfolgreich hochgeladen', 'success')
        
        # Optional: Datei analysieren
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext in ['.dst', '.pes', '.jef', '.exp']:
            # Stickdatei analysieren
            try:
                analysis = analyze_dst_file_robust(filepath)
                if analysis['success']:
                    order.stitch_count = analysis.get('stitch_count', 0)
                    order.file_analysis = json.dumps(analysis)
                    db.session.commit()
            except Exception:
                pass

    return redirect(url_for('orders.show', order_id=order_id))


# ==========================================
# WORKFLOW API ENDPUNKTE
# ==========================================

@order_bp.route('/<order_id>/confirm-pickup', methods=['POST'])
@login_required
def confirm_pickup(order_id):
    """Bestätigt Abholung durch Kunden"""
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'success': False, 'error': 'Auftrag nicht gefunden'})

    try:
        data = request.get_json()

        order.pickup_signature_name = data.get('pickup_name')
        order.pickup_signature = data.get('signature')
        order.pickup_confirmed_at = datetime.utcnow()
        order.workflow_status = 'completed'

        # Zahlung verarbeiten
        payment_method = data.get('payment_method')
        if payment_method:
            order.record_final_payment(method=payment_method)

        db.session.commit()

        log_activity('pickup_confirmed',
                    f'Abholung bestätigt für Auftrag {order.order_number} durch {order.pickup_signature_name}')

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@order_bp.route('/<order_id>/confirm-shipping', methods=['POST'])
@login_required
def confirm_shipping(order_id):
    """Markiert Auftrag als versendet"""
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'success': False, 'error': 'Auftrag nicht gefunden'})

    try:
        data = request.get_json()

        # Shipment erstellen falls Model existiert
        order.workflow_status = 'shipped'
        order.pickup_confirmed_at = datetime.utcnow()  # Wiederverwendung für Versanddatum

        # Tracking-Info in Notizen speichern
        tracking_info = f"Versand: {data.get('carrier', '-')}"
        if data.get('tracking_numbers'):
            tracking_info += f"\nTracking: {data.get('tracking_numbers')}"
        if data.get('notes'):
            tracking_info += f"\nNotizen: {data.get('notes')}"

        if order.notes:
            order.notes += f"\n\n--- Versandinfo ---\n{tracking_info}"
        else:
            order.notes = f"--- Versandinfo ---\n{tracking_info}"

        db.session.commit()

        log_activity('shipping_confirmed',
                    f'Versand bestätigt für Auftrag {order.order_number}')

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@order_bp.route('/<order_id>/archive', methods=['POST'])
@login_required
def archive_order(order_id):
    """Archiviert den Auftrag"""
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'success': False, 'error': 'Auftrag nicht gefunden'})

    try:
        can_archive, message = order.can_archive()
        if not can_archive:
            return jsonify({'success': False, 'error': message})

        data = request.get_json()
        reason = data.get('reason', 'completed')

        order.archive(user=current_user.username, reason=reason)
        db.session.commit()

        log_activity('order_archived',
                    f'Auftrag {order.order_number} archiviert: {reason}')

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@order_bp.route('/<order_id>/unarchive', methods=['POST'])
@login_required
def unarchive_order(order_id):
    """Stellt Auftrag aus Archiv wieder her"""
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'success': False, 'error': 'Auftrag nicht gefunden'})

    try:
        order.unarchive()
        db.session.commit()

        log_activity('order_unarchived',
                    f'Auftrag {order.order_number} aus Archiv wiederhergestellt')

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@order_bp.route('/<order_id>/mark-paid', methods=['POST'])
@login_required
def mark_paid(order_id):
    """Markiert Auftrag als bezahlt"""
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'success': False, 'error': 'Auftrag nicht gefunden'})

    try:
        order.record_final_payment(method='manual')
        db.session.commit()

        log_activity('payment_confirmed',
                    f'Zahlung bestätigt für Auftrag {order.order_number}')

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@order_bp.route('/<order_id>/start-production', methods=['POST'])
@login_required
def start_production(order_id):
    """Startet die Produktion"""
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'success': False, 'error': 'Auftrag nicht gefunden'})

    try:
        order.workflow_status = 'in_production'
        order.production_start = datetime.utcnow()
        db.session.commit()

        log_activity('production_started',
                    f'Produktion gestartet für Auftrag {order.order_number}')

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@order_bp.route('/<order_id>/save-packing', methods=['POST'])
@login_required
def save_packing(order_id):
    """Speichert Verpackungs-Status"""
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'success': False, 'error': 'Auftrag nicht gefunden'})

    try:
        data = request.get_json()

        # Delivery-Type aktualisieren
        if data.get('delivery_type'):
            order.delivery_type = data.get('delivery_type')

        # TODO: PackingList-Einträge erstellen/aktualisieren

        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@order_bp.route('/<order_id>/complete-packing', methods=['POST'])
@login_required
def complete_packing(order_id):
    """Schließt Verpackung ab"""
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'success': False, 'error': 'Auftrag nicht gefunden'})

    try:
        order.workflow_status = 'ready_to_ship'
        db.session.commit()

        log_activity('packing_completed',
                    f'Verpackung abgeschlossen für Auftrag {order.order_number}')

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@order_bp.route('/api/calculate-total', methods=['GET'])
@login_required
def api_calculate_total():
    """Berechnet Gesamtpreis aus Artikeln + Druckpositionen"""
    order_id = request.args.get('order_id')
    if not order_id:
        return jsonify({'success': False, 'error': 'order_id fehlt'})

    order = Order.query.get(order_id)
    if not order:
        return jsonify({'success': False, 'error': 'Auftrag nicht gefunden'})

    try:
        # Artikel-Summe
        artikel_total = 0.0
        items = OrderItem.query.filter_by(order_id=order_id).all()
        for item in items:
            price = item.unit_price or 0
            if not price and item.article_id:
                article = Article.query.get(item.article_id)
                if article and hasattr(article, 'price') and article.price:
                    price = article.price
            artikel_total += (item.quantity or 0) * price

        # Gesamt-Stückzahl für Druck/Stick-Kalkulation
        total_qty = sum((item.quantity or 0) for item in items) or 1

        # Design-Positionen-Summe
        from src.models.order_workflow import OrderDesign
        design_total = 0.0
        erstellkosten = 0.0
        designs = OrderDesign.query.filter_by(order_id=order_id).all()
        for design in designs:
            design_total += (design.setup_price or 0) + (design.price_per_piece or 0) * total_qty
            erstellkosten += float(design.supplier_cost or 0)  # Design-Erstellkosten

        # Design-Kosten vom Order
        design_kosten = float(order.design_cost or 0) + float(order.adaptation_cost or 0)

        total = artikel_total + design_total + erstellkosten + design_kosten

        return jsonify({
            'success': True,
            'artikel_total': round(artikel_total, 2),
            'design_total': round(design_total, 2),
            'erstellkosten': round(erstellkosten, 2),
            'design_kosten': round(design_kosten, 2),
            'total': round(total, 2)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
