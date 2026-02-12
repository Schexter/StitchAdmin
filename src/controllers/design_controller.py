"""
Design-Management Controller
Zentrale Verwaltung für Stick-, Druck- und DTF-Designs

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_file, current_app
from flask_login import login_required, current_user
from datetime import datetime, date
from werkzeug.utils import secure_filename
import uuid
import os
import json
import hashlib

from src.models.models import db, Customer, Supplier, Order
from src.models.design import (
    Design, DesignVersion, DesignUsage,
    ThreadBrand, ThreadColor, DesignOrder
)
from src.models.nummernkreis import NumberSequenceService, DocumentType

# Blueprint
designs_bp = Blueprint('designs', __name__, url_prefix='/designs')


# ═══════════════════════════════════════════════════════════════════════════════
# HILFSFUNKTIONEN
# ═══════════════════════════════════════════════════════════════════════════════

def generate_design_number():
    """Generiert eine neue Design-Nummer (D-2025-0001)"""
    try:
        return NumberSequenceService.generate_number(DocumentType.DESIGN)
    except:
        # Fallback
        from datetime import datetime
        count = Design.query.count() + 1
        return f"D-{datetime.now().year}-{count:04d}"


def generate_design_order_number():
    """Generiert eine neue Design-Bestellnummer (DO-2025-0001)"""
    try:
        return NumberSequenceService.generate_number(DocumentType.DESIGN_ORDER)
    except:
        # Fallback
        from datetime import datetime
        count = DesignOrder.query.count() + 1
        return f"DO-{datetime.now().year}-{count:04d}"


def allowed_file(filename, design_type='embroidery'):
    """Prüft ob Dateiendung erlaubt ist"""
    embroidery_extensions = {'dst', 'emb', 'pes', 'jef', 'exp', 'vp3', 'hus', 'xxx', 'sew'}
    print_extensions = {'pdf', 'ai', 'eps', 'svg', 'png', 'jpg', 'jpeg', 'tiff', 'tif', 'psd'}
    
    if '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    
    if design_type == 'embroidery':
        return ext in embroidery_extensions or ext in print_extensions  # Source kann auch Bild sein
    else:
        return ext in print_extensions


def get_file_hash(filepath):
    """Berechnet SHA-256 Hash einer Datei"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_design_upload_path():
    """Gibt den Upload-Pfad für Designs zurück"""
    upload_path = os.path.join(current_app.root_path, '..', 'uploads', 'designs')
    os.makedirs(upload_path, exist_ok=True)
    return upload_path


def get_design_thumbnail_path():
    """Gibt den Thumbnail-Pfad zurück"""
    thumb_path = os.path.join(current_app.root_path, 'static', 'thumbnails', 'designs')
    os.makedirs(thumb_path, exist_ok=True)
    return thumb_path


# ═══════════════════════════════════════════════════════════════════════════════
# DESIGN-ARCHIV ROUTEN
# ═══════════════════════════════════════════════════════════════════════════════

@designs_bp.route('/')
def index():
    """Design-Archiv Übersicht"""
    # Filter aus Request
    design_type = request.args.get('type', '')
    status = request.args.get('status', '')
    customer_id = request.args.get('customer', '')
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 24  # Grid-Ansicht
    
    # Query aufbauen
    query = Design.query
    
    if design_type:
        query = query.filter(Design.design_type == design_type)
    
    if status:
        query = query.filter(Design.status == status)
    
    if customer_id:
        query = query.filter(Design.customer_id == customer_id)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            db.or_(
                Design.name.ilike(search_term),
                Design.design_number.ilike(search_term),
                Design.description.ilike(search_term),
                Design.tags.ilike(search_term)
            )
        )
    
    # Sortierung
    query = query.order_by(Design.created_at.desc())
    
    # Pagination
    designs = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Kunden für Filter
    customers = Customer.query.order_by(Customer.company_name, Customer.last_name).all()
    
    # Statistiken
    stats = {
        'total': Design.query.count(),
        'embroidery': Design.query.filter_by(design_type='embroidery').count(),
        'print': Design.query.filter_by(design_type='print').count(),
        'dtf': Design.query.filter_by(design_type='dtf').count(),
        'active': Design.query.filter_by(status='active').count()
    }
    
    return render_template('designs/index.html',
                          designs=designs,
                          customers=customers,
                          stats=stats,
                          filters={
                              'type': design_type,
                              'status': status,
                              'customer': customer_id,
                              'search': search
                          })


@designs_bp.route('/new', methods=['GET', 'POST'])
def new():
    """Neues Design anlegen"""
    if request.method == 'POST':
        try:
            # Basis-Daten
            design_id = str(uuid.uuid4())
            design_number = generate_design_number()
            
            design = Design(
                id=design_id,
                design_number=design_number,
                name=request.form.get('name', '').strip(),
                description=request.form.get('description', '').strip(),
                design_type=request.form.get('design_type', 'embroidery'),
                category=request.form.get('category', '').strip(),
                customer_id=request.form.get('customer_id') or None,
                is_customer_design=request.form.get('is_customer_design') == 'on',
                source=request.form.get('source', 'customer'),
                status='active',
                created_by=session.get('username', 'System')
            )
            
            # Tags verarbeiten
            tags_str = request.form.get('tags', '').strip()
            if tags_str:
                tags = [t.strip() for t in tags_str.split(',') if t.strip()]
                design.set_tags(tags)
            
            # Datei hochladen
            if 'design_file' in request.files:
                file = request.files['design_file']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    
                    # Eindeutigen Dateinamen erstellen
                    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                    new_filename = f"{design_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
                    
                    # Speichern
                    upload_path = get_design_upload_path()
                    filepath = os.path.join(upload_path, new_filename)
                    file.save(filepath)
                    
                    design.file_path = filepath
                    design.file_name = filename
                    design.file_type = ext
                    design.file_size_kb = os.path.getsize(filepath) // 1024
                    design.file_hash = get_file_hash(filepath)
                    
                    # Stickdatei analysieren
                    if design.design_type == 'embroidery' and ext in ('dst', 'emb', 'pes', 'jef', 'exp'):
                        design.analyze_embroidery_file()
            
            # Maße (falls manuell eingegeben)
            if request.form.get('width_mm'):
                design.width_mm = float(request.form.get('width_mm'))
            if request.form.get('height_mm'):
                design.height_mm = float(request.form.get('height_mm'))
            
            # Stickerei-spezifisch
            if design.design_type == 'embroidery':
                if request.form.get('stitch_count'):
                    design.stitch_count = int(request.form.get('stitch_count'))
                if request.form.get('color_changes'):
                    design.color_changes = int(request.form.get('color_changes'))
            
            # Druck-spezifisch
            if design.design_type in ('print', 'dtf'):
                if request.form.get('print_width_cm'):
                    design.print_width_cm = float(request.form.get('print_width_cm'))
                if request.form.get('print_height_cm'):
                    design.print_height_cm = float(request.form.get('print_height_cm'))
                if request.form.get('dpi'):
                    design.dpi = int(request.form.get('dpi'))
                design.color_mode = request.form.get('color_mode', 'cmyk')
                design.print_method = request.form.get('print_method', '')
            
            db.session.add(design)
            
            # Initiale Version erstellen
            version = DesignVersion(
                design_id=design_id,
                version_number=1,
                version_name='Original',
                change_description='Erstversion',
                file_path=design.file_path,
                file_name=design.file_name,
                is_active=True,
                created_by=session.get('username', 'System')
            )
            
            # Technische Daten als Snapshot speichern
            tech_data = {
                'stitch_count': design.stitch_count,
                'width_mm': design.width_mm,
                'height_mm': design.height_mm,
                'color_changes': design.color_changes,
                'thread_colors': design.get_thread_colors()
            }
            version.set_technical_data(tech_data)
            
            db.session.add(version)
            db.session.commit()
            
            flash(f'Design {design_number} erfolgreich angelegt!', 'success')
            return redirect(url_for('designs.show', design_id=design_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Anlegen: {str(e)}', 'danger')
    
    # GET: Formular anzeigen
    customers = Customer.query.order_by(Customer.company_name, Customer.last_name).all()
    thread_brands = ThreadBrand.query.order_by(ThreadBrand.sort_order).all()
    
    return render_template('designs/form.html',
                          design=None,
                          customers=customers,
                          thread_brands=thread_brands,
                          mode='new')


@designs_bp.route('/<design_id>')
def show(design_id):
    """Design-Details anzeigen"""
    design = Design.query.get_or_404(design_id)
    
    # Letzte Verwendungen
    recent_usage = DesignUsage.query.filter_by(design_id=design_id)\
        .order_by(DesignUsage.used_at.desc())\
        .limit(10).all()
    
    # Versionen
    versions = DesignVersion.query.filter_by(design_id=design_id)\
        .order_by(DesignVersion.version_number.desc()).all()
    
    # Garnfarben-Details laden
    thread_colors_detailed = []
    for color in design.get_thread_colors():
        # Versuche passende Farbe aus DB zu finden
        db_color = None
        if color.get('color_code'):
            db_color = ThreadColor.query.filter_by(color_code=color['color_code']).first()
        
        thread_colors_detailed.append({
            **color,
            'db_color': db_color
        })
    
    return render_template('designs/show.html',
                          design=design,
                          recent_usage=recent_usage,
                          versions=versions,
                          thread_colors=thread_colors_detailed)


@designs_bp.route('/<design_id>/edit', methods=['GET', 'POST'])
def edit(design_id):
    """Design bearbeiten"""
    design = Design.query.get_or_404(design_id)
    
    if request.method == 'POST':
        try:
            # Basis-Daten aktualisieren
            design.name = request.form.get('name', '').strip()
            design.description = request.form.get('description', '').strip()
            design.category = request.form.get('category', '').strip()
            design.customer_id = request.form.get('customer_id') or None
            design.is_customer_design = request.form.get('is_customer_design') == 'on'
            design.status = request.form.get('status', 'active')
            
            # Tags
            tags_str = request.form.get('tags', '').strip()
            if tags_str:
                tags = [t.strip() for t in tags_str.split(',') if t.strip()]
                design.set_tags(tags)
            else:
                design.tags = None
            
            # Maße
            if request.form.get('width_mm'):
                design.width_mm = float(request.form.get('width_mm'))
            if request.form.get('height_mm'):
                design.height_mm = float(request.form.get('height_mm'))
            
            # Typ-spezifische Daten
            if design.design_type == 'embroidery':
                if request.form.get('stitch_count'):
                    design.stitch_count = int(request.form.get('stitch_count'))
                if request.form.get('color_changes'):
                    design.color_changes = int(request.form.get('color_changes'))
            
            if design.design_type in ('print', 'dtf'):
                if request.form.get('print_width_cm'):
                    design.print_width_cm = float(request.form.get('print_width_cm'))
                if request.form.get('print_height_cm'):
                    design.print_height_cm = float(request.form.get('print_height_cm'))
                if request.form.get('dpi'):
                    design.dpi = int(request.form.get('dpi'))
                design.color_mode = request.form.get('color_mode', 'cmyk')
                design.print_method = request.form.get('print_method', '')
            
            # Qualität
            if request.form.get('quality_rating'):
                design.quality_rating = int(request.form.get('quality_rating'))
            design.quality_notes = request.form.get('quality_notes', '').strip()
            
            design.updated_by = session.get('username', 'System')
            
            db.session.commit()
            flash('Design erfolgreich aktualisiert!', 'success')
            return redirect(url_for('designs.show', design_id=design_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Speichern: {str(e)}', 'danger')
    
    # GET: Formular mit Daten
    customers = Customer.query.order_by(Customer.company_name, Customer.last_name).all()
    thread_brands = ThreadBrand.query.order_by(ThreadBrand.sort_order).all()
    
    return render_template('designs/form.html',
                          design=design,
                          customers=customers,
                          thread_brands=thread_brands,
                          mode='edit')


@designs_bp.route('/<design_id>/delete', methods=['POST'])
def delete(design_id):
    """Design löschen"""
    design = Design.query.get_or_404(design_id)
    
    try:
        design_number = design.design_number
        db.session.delete(design)
        db.session.commit()
        flash(f'Design {design_number} gelöscht!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Löschen: {str(e)}', 'danger')
    
    return redirect(url_for('designs.index'))


@designs_bp.route('/<design_id>/analyze', methods=['POST'])
def analyze(design_id):
    """Stickdatei neu analysieren"""
    design = Design.query.get_or_404(design_id)
    
    if design.design_type != 'embroidery':
        flash('Nur Stickerei-Designs können analysiert werden!', 'warning')
        return redirect(url_for('designs.show', design_id=design_id))
    
    if not design.file_path or not os.path.exists(design.file_path):
        flash('Design-Datei nicht gefunden!', 'danger')
        return redirect(url_for('designs.show', design_id=design_id))
    
    try:
        if design.analyze_embroidery_file():
            db.session.commit()
            flash('Design erfolgreich analysiert!', 'success')
        else:
            flash('Analyse fehlgeschlagen - Dateiformat möglicherweise nicht unterstützt.', 'warning')
    except Exception as e:
        flash(f'Analysefehler: {str(e)}', 'danger')
    
    return redirect(url_for('designs.show', design_id=design_id))


@designs_bp.route('/<design_id>/duplicate', methods=['POST'])
def duplicate(design_id):
    """Design duplizieren"""
    original = Design.query.get_or_404(design_id)
    
    try:
        new_id = str(uuid.uuid4())
        new_number = generate_design_number()
        
        # Kopiere alle Felder
        new_design = Design(
            id=new_id,
            design_number=new_number,
            name=f"{original.name} (Kopie)",
            description=original.description,
            design_type=original.design_type,
            category=original.category,
            tags=original.tags,
            customer_id=original.customer_id,
            is_customer_design=original.is_customer_design,
            file_path=original.file_path,  # Gleiche Datei referenzieren
            file_name=original.file_name,
            file_type=original.file_type,
            file_size_kb=original.file_size_kb,
            file_hash=original.file_hash,
            thumbnail_path=original.thumbnail_path,
            width_mm=original.width_mm,
            height_mm=original.height_mm,
            stitch_count=original.stitch_count,
            color_changes=original.color_changes,
            estimated_time_minutes=original.estimated_time_minutes,
            thread_colors=original.thread_colors,
            dst_analysis=original.dst_analysis,
            print_width_cm=original.print_width_cm,
            print_height_cm=original.print_height_cm,
            dpi=original.dpi,
            color_mode=original.color_mode,
            print_colors=original.print_colors,
            print_method=original.print_method,
            status='draft',
            source='internal',
            created_by=session.get('username', 'System')
        )
        
        db.session.add(new_design)
        db.session.commit()
        
        flash(f'Design dupliziert als {new_number}!', 'success')
        return redirect(url_for('designs.edit', design_id=new_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Duplizieren: {str(e)}', 'danger')
        return redirect(url_for('designs.show', design_id=design_id))


# ═══════════════════════════════════════════════════════════════════════════════
# GARNFARBEN-ROUTEN
# ═══════════════════════════════════════════════════════════════════════════════

@designs_bp.route('/colors')
def colors():
    """Garnfarben-Bibliothek"""
    brand_id = request.args.get('brand', type=int)
    family = request.args.get('family', '')
    search = request.args.get('search', '')
    
    # Query aufbauen
    query = ThreadColor.query.join(ThreadBrand)
    
    if brand_id:
        query = query.filter(ThreadColor.brand_id == brand_id)
    
    if family:
        query = query.filter(ThreadColor.color_family == family)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            db.or_(
                ThreadColor.color_code.ilike(search_term),
                ThreadColor.color_name.ilike(search_term)
            )
        )
    
    colors = query.order_by(ThreadBrand.sort_order, ThreadColor.color_code).all()
    
    # Marken für Filter
    brands = ThreadBrand.query.order_by(ThreadBrand.sort_order).all()
    
    # Farbfamilien
    families = db.session.query(ThreadColor.color_family)\
        .filter(ThreadColor.color_family.isnot(None))\
        .distinct().all()
    families = [f[0] for f in families if f[0]]
    
    return render_template('designs/colors.html',
                          colors=colors,
                          brands=brands,
                          families=families,
                          filters={
                              'brand': brand_id,
                              'family': family,
                              'search': search
                          })


@designs_bp.route('/colors/new', methods=['GET', 'POST'])
def new_color():
    """Neue Garnfarbe anlegen"""
    if request.method == 'POST':
        try:
            color = ThreadColor(
                brand_id=int(request.form.get('brand_id')),
                color_code=request.form.get('color_code', '').strip(),
                color_name=request.form.get('color_name', '').strip(),
                color_family=request.form.get('color_family', '').strip() or None,
                is_metallic=request.form.get('is_metallic') == 'on',
                is_glow=request.form.get('is_glow') == 'on',
                is_neon=request.form.get('is_neon') == 'on',
                stock_quantity=int(request.form.get('stock_quantity', 0)),
                min_stock=int(request.form.get('min_stock', 1)),
                location=request.form.get('location', '').strip() or None
            )
            
            # RGB aus Hex setzen
            rgb_hex = request.form.get('rgb_hex', '').strip()
            if rgb_hex:
                color.set_rgb_from_hex(rgb_hex)
            
            db.session.add(color)
            db.session.commit()
            
            flash(f'Farbe {color.full_name} angelegt!', 'success')
            return redirect(url_for('designs.colors'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {str(e)}', 'danger')
    
    brands = ThreadBrand.query.order_by(ThreadBrand.sort_order).all()
    return render_template('designs/color_form.html', color=None, brands=brands, mode='new')


@designs_bp.route('/colors/<int:color_id>/edit', methods=['GET', 'POST'])
def edit_color(color_id):
    """Garnfarbe bearbeiten"""
    color = ThreadColor.query.get_or_404(color_id)
    
    if request.method == 'POST':
        try:
            color.brand_id = int(request.form.get('brand_id'))
            color.color_code = request.form.get('color_code', '').strip()
            color.color_name = request.form.get('color_name', '').strip()
            color.color_family = request.form.get('color_family', '').strip() or None
            color.is_metallic = request.form.get('is_metallic') == 'on'
            color.is_glow = request.form.get('is_glow') == 'on'
            color.is_neon = request.form.get('is_neon') == 'on'
            color.stock_quantity = int(request.form.get('stock_quantity', 0))
            color.min_stock = int(request.form.get('min_stock', 1))
            color.location = request.form.get('location', '').strip() or None
            
            rgb_hex = request.form.get('rgb_hex', '').strip()
            if rgb_hex:
                color.set_rgb_from_hex(rgb_hex)
            
            db.session.commit()
            flash('Farbe aktualisiert!', 'success')
            return redirect(url_for('designs.colors'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {str(e)}', 'danger')
    
    brands = ThreadBrand.query.order_by(ThreadBrand.sort_order).all()
    return render_template('designs/color_form.html', color=color, brands=brands, mode='edit')


# ═══════════════════════════════════════════════════════════════════════════════
# DESIGN-BESTELLUNGEN
# ═══════════════════════════════════════════════════════════════════════════════

@designs_bp.route('/orders')
def design_orders():
    """Design-Bestellungen Übersicht"""
    status = request.args.get('status', '')
    design_type = request.args.get('type', '')
    page = request.args.get('page', 1, type=int)
    
    query = DesignOrder.query
    
    if status:
        query = query.filter(DesignOrder.status == status)
    
    if design_type:
        query = query.filter(DesignOrder.design_type == design_type)
    
    query = query.order_by(DesignOrder.created_at.desc())
    
    orders = query.paginate(page=page, per_page=20, error_out=False)
    
    # Statistiken
    stats = {
        'total': DesignOrder.query.count(),
        'pending': DesignOrder.query.filter(DesignOrder.status.in_(['draft', 'sent', 'quoted'])).count(),
        'in_progress': DesignOrder.query.filter(DesignOrder.status.in_(['accepted', 'deposit_paid', 'in_progress'])).count(),
        'completed': DesignOrder.query.filter_by(status='completed').count()
    }
    
    return render_template('designs/orders/index.html',
                          orders=orders,
                          stats=stats,
                          filters={'status': status, 'type': design_type})


@designs_bp.route('/orders/new', methods=['GET', 'POST'])
def new_design_order():
    """Neue Design-Bestellung anlegen"""
    if request.method == 'POST':
        try:
            order_id = str(uuid.uuid4())
            order_number = generate_design_order_number()
            
            order = DesignOrder(
                id=order_id,
                design_order_number=order_number,
                design_type=request.form.get('design_type', 'embroidery'),
                order_type=request.form.get('order_type', 'new_design'),
                design_name=request.form.get('design_name', '').strip(),
                design_description=request.form.get('design_description', '').strip(),
                supplier_id=request.form.get('supplier_id') or None,
                customer_id=request.form.get('customer_id') or None,
                order_id=request.form.get('order_id') or None,
                priority=request.form.get('priority', 'normal'),
                status='draft',
                created_by=session.get('username', 'System')
            )
            
            # Stickerei-Spezifikation
            if order.design_type == 'embroidery':
                if request.form.get('target_width_mm'):
                    order.target_width_mm = float(request.form.get('target_width_mm'))
                if request.form.get('target_height_mm'):
                    order.target_height_mm = float(request.form.get('target_height_mm'))
                if request.form.get('max_stitch_count'):
                    order.max_stitch_count = int(request.form.get('max_stitch_count'))
                if request.form.get('max_colors'):
                    order.max_colors = int(request.form.get('max_colors'))
                order.stitch_density = request.form.get('stitch_density', 'normal')
                order.underlay_type = request.form.get('underlay_type', 'standard')
                order.fabric_type = request.form.get('fabric_type', '').strip()
            
            # Druck-Spezifikation
            if order.design_type in ('print', 'dtf'):
                if request.form.get('target_print_width_cm'):
                    order.target_print_width_cm = float(request.form.get('target_print_width_cm'))
                if request.form.get('target_print_height_cm'):
                    order.target_print_height_cm = float(request.form.get('target_print_height_cm'))
                order.print_method = request.form.get('print_method', '')
                if request.form.get('min_dpi'):
                    order.min_dpi = int(request.form.get('min_dpi'))
                order.color_mode = request.form.get('color_mode', 'cmyk')
                order.needs_transparent_bg = request.form.get('needs_transparent_bg') == 'on'
                order.needs_white_underbase = request.form.get('needs_white_underbase') == 'on'
            
            # Besondere Anforderungen
            order.special_requirements = request.form.get('special_requirements', '').strip()
            
            # Liefertermin
            if request.form.get('expected_delivery'):
                order.expected_delivery = datetime.strptime(
                    request.form.get('expected_delivery'), '%Y-%m-%d'
                ).date()
            
            # Vorlage-Datei
            if 'source_file' in request.files:
                file = request.files['source_file']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                    new_filename = f"{order_number}_source.{ext}"
                    
                    upload_path = os.path.join(get_design_upload_path(), 'orders')
                    os.makedirs(upload_path, exist_ok=True)
                    filepath = os.path.join(upload_path, new_filename)
                    file.save(filepath)
                    
                    order.source_file_path = filepath
                    order.source_file_name = filename
                    order.source_file_type = ext
            
            db.session.add(order)
            db.session.commit()
            
            flash(f'Design-Bestellung {order_number} angelegt!', 'success')
            return redirect(url_for('designs.show_design_order', order_id=order_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {str(e)}', 'danger')
    
    # GET: Formular
    suppliers = Supplier.query.filter(
        db.or_(
            Supplier.supplier_type == 'puncher',
            Supplier.supplier_type == 'digitizer',
            Supplier.supplier_type == 'designer',
            Supplier.notes.ilike('%design%'),
            Supplier.notes.ilike('%punch%'),
            Supplier.notes.ilike('%digitiz%')
        )
    ).order_by(Supplier.name).all()
    
    # Falls keine spezialisierten Lieferanten, alle anzeigen
    if not suppliers:
        suppliers = Supplier.query.order_by(Supplier.name).all()
    
    customers = Customer.query.order_by(Customer.company_name, Customer.last_name).all()
    orders = Order.query.filter(Order.status.in_(['new', 'in_progress', 'pending_design']))\
        .order_by(Order.created_at.desc()).limit(50).all()
    
    return render_template('designs/orders/form.html',
                          order=None,
                          suppliers=suppliers,
                          customers=customers,
                          related_orders=orders,
                          mode='new')


@designs_bp.route('/orders/<order_id>')
def show_design_order(order_id):
    """Design-Bestellung Details"""
    order = DesignOrder.query.get_or_404(order_id)
    
    return render_template('designs/orders/show.html', order=order)


@designs_bp.route('/orders/<order_id>/pdf')
def design_order_pdf(order_id):
    """PDF-Beauftragung generieren"""
    order = DesignOrder.query.get_or_404(order_id)
    
    try:
        from src.services.design_order_pdf import DesignOrderPDFGenerator
        
        generator = DesignOrderPDFGenerator(order)
        pdf_path = generator.generate()
        
        # Pfad speichern
        order.order_pdf_path = pdf_path
        order.order_pdf_generated_at = datetime.utcnow()
        db.session.commit()
        
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"Design-Beauftragung_{order.design_order_number}.pdf"
        )
        
    except Exception as e:
        flash(f'PDF-Generierung fehlgeschlagen: {str(e)}', 'danger')
        return redirect(url_for('designs.show_design_order', order_id=order_id))


@designs_bp.route('/orders/<order_id>/status', methods=['POST'])
def update_design_order_status(order_id):
    """Status einer Design-Bestellung aktualisieren"""
    order = DesignOrder.query.get_or_404(order_id)
    
    new_status = request.form.get('status')
    if new_status:
        order.status = new_status
        order.updated_by = session.get('username', 'System')
        
        # Status-spezifische Aktionen
        if new_status == 'sent':
            order.request_sent_at = datetime.utcnow()
        elif new_status == 'delivered':
            order.delivered_at = datetime.utcnow()
        elif new_status == 'completed':
            order.completed_at = datetime.utcnow()
        
        # Kommunikationslog
        order.add_communication(
            f"Status geändert zu: {order.status_display}",
            'status_change',
            session.get('username', 'System')
        )
        
        db.session.commit()
        flash(f'Status auf "{order.status_display}" geändert!', 'success')
    
    return redirect(url_for('designs.show_design_order', order_id=order_id))


# ═══════════════════════════════════════════════════════════════════════════════
# API ENDPUNKTE
# ═══════════════════════════════════════════════════════════════════════════════

@designs_bp.route('/api/search')
def api_search():
    """API: Design-Suche für Autocomplete"""
    q = request.args.get('q', '')
    limit = request.args.get('limit', 10, type=int)
    
    if len(q) < 2:
        return jsonify([])
    
    designs = Design.query.filter(
        db.or_(
            Design.name.ilike(f'%{q}%'),
            Design.design_number.ilike(f'%{q}%')
        ),
        Design.status == 'active'
    ).limit(limit).all()
    
    return jsonify([{
        'id': d.id,
        'design_number': d.design_number,
        'name': d.name,
        'type': d.design_type,
        'type_icon': d.type_icon,
        'customer': d.customer.display_name if d.customer else None,
        'stitch_count': d.stitch_count,
        'thumbnail': d.thumbnail_path
    } for d in designs])


@designs_bp.route('/api/colors')
def api_colors():
    """API: Garnfarben für Dropdown"""
    brand_id = request.args.get('brand_id', type=int)
    
    query = ThreadColor.query.filter_by(is_active=True)
    
    if brand_id:
        query = query.filter_by(brand_id=brand_id)
    
    colors = query.order_by(ThreadColor.color_code).all()
    
    return jsonify([{
        'id': c.id,
        'code': c.color_code,
        'name': c.color_name,
        'full_name': c.full_name,
        'rgb_hex': c.rgb_hex,
        'family': c.color_family,
        'is_metallic': c.is_metallic
    } for c in colors])


# ============================================
# KUNDEN-DESIGNS
# ============================================

@designs_bp.route('/customer/<customer_id>')
@login_required
def customer_designs(customer_id):
    """Alle Designs eines Kunden anzeigen"""
    from src.models.models import Customer

    customer = Customer.query.get_or_404(customer_id)

    # Alle Designs des Kunden
    designs = Design.query.filter_by(customer_id=customer_id)\
        .order_by(Design.created_at.desc()).all()

    # Statistiken
    stats = {
        'total': len(designs),
        'embroidery': len([d for d in designs if d.design_type == 'embroidery']),
        'print': len([d for d in designs if d.design_type == 'print']),
        'dtf': len([d for d in designs if d.design_type == 'dtf']),
        'approved': len([d for d in designs if d.is_approved]),
        'pending_approval': len([d for d in designs if not d.is_approved])
    }

    return render_template('designs/customer_designs.html',
        customer=customer,
        designs=designs,
        stats=stats
    )


@designs_bp.route('/<design_id>/approve', methods=['POST'])
@login_required
def approve_design(design_id):
    """Design genehmigen"""
    design = Design.query.get_or_404(design_id)

    design.is_approved = True
    design.approved_at = datetime.utcnow()
    design.approved_by = current_user.username

    db.session.commit()

    flash(f'Design {design.design_number} wurde genehmigt', 'success')

    # Zurück zur vorherigen Seite oder Design-Detail
    next_url = request.referrer or url_for('designs.show', design_id=design_id)
    return redirect(next_url)
