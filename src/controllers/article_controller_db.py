"""
Article Controller - PostgreSQL-Version
Artikel-Verwaltung mit Datenbank
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from datetime import datetime
from src.models import db, Article, ArticleVariant, ActivityLog, Supplier, ProductCategory, Brand, PriceCalculationSettings
from src.services import LShopImportService
from src.utils.activity_logger import log_activity
from werkzeug.utils import secure_filename
import os
import tempfile
import json

# Blueprint erstellen
article_bp = Blueprint('articles', __name__, url_prefix='/articles')

def generate_article_id():
    """Generiere neue Artikel-ID - delegiert an IdGeneratorService"""
    from src.services.id_generator_service import IdGenerator
    return IdGenerator.article()

@article_bp.route('/')
@login_required
def index():
    """Artikel-Übersicht mit Smart-Filtern"""
    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '')
    brand_filter = request.args.get('brand', '')
    supplier_filter = request.args.get('supplier', '')
    material_filter = request.args.get('material', '')
    stock_filter = request.args.get('stock', '')

    query = Article.query

    if search_query:
        query = query.filter(
            db.or_(
                Article.name.ilike(f'%{search_query}%'),
                Article.article_number.ilike(f'%{search_query}%'),
                Article.description.ilike(f'%{search_query}%'),
                Article.supplier.ilike(f'%{search_query}%')
            )
        )

    if category_filter:
        query = query.filter_by(category=category_filter)
    if brand_filter:
        query = query.filter(Article.brand.ilike(f'%{brand_filter}%'))
    if supplier_filter:
        query = query.filter(Article.supplier.ilike(f'%{supplier_filter}%'))
    if material_filter:
        query = query.filter(Article.material == material_filter)
    if stock_filter == 'available':
        query = query.filter(Article.stock > 0)
    elif stock_filter == 'low':
        query = query.filter(Article.stock > 0, Article.stock <= 10)
    elif stock_filter == 'out':
        query = query.filter(db.or_(Article.stock == 0, Article.stock.is_(None)))

    articles_list = query.order_by(Article.name).all()

    articles = {}
    for article in articles_list:
        articles[article.id] = article

    # Filter-Optionen aus DB (distinct values)
    categories = [c[0] for c in db.session.query(Article.category).distinct().filter(
        Article.category.isnot(None), Article.category != '').order_by(Article.category).all()]
    brands = [b[0] for b in db.session.query(Article.brand).distinct().filter(
        Article.brand.isnot(None), Article.brand != '').order_by(Article.brand).all()]
    suppliers = [s[0] for s in db.session.query(Article.supplier).distinct().filter(
        Article.supplier.isnot(None), Article.supplier != '').order_by(Article.supplier).all()]
    materials = [m[0] for m in db.session.query(Article.material).distinct().filter(
        Article.material.isnot(None), Article.material != '').order_by(Article.material).all()]

    return render_template('articles/index.html',
                         articles=articles,
                         categories=categories,
                         brands=brands,
                         suppliers=suppliers,
                         materials=materials,
                         search_query=search_query,
                         category_filter=category_filter,
                         brand_filter=brand_filter,
                         supplier_filter=supplier_filter,
                         material_filter=material_filter,
                         stock_filter=stock_filter)

@article_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Neuen Artikel erstellen"""
    if request.method == 'POST':
        # Preis-Konvertierung (Komma zu Punkt)
        price_str = request.form.get('price', '0').replace(',', '.')

        # Neuen Artikel erstellen
        article = Article(
            id=generate_article_id(),
            article_number=request.form.get('article_number', '').strip() or None,
            name=request.form.get('name'),
            category=request.form.get('category', ''),
            description=request.form.get('description', ''),
            brand=request.form.get('brand', ''),
            material=request.form.get('material', ''),
            weight=float(request.form.get('weight', 0) or 0),
            color=request.form.get('color', ''),
            size=request.form.get('size', ''),
            price=float(price_str or 0),
            stock=int(request.form.get('stock', 0) or 0),
            min_stock=int(request.form.get('min_stock', 0) or 0),
            location=request.form.get('location', ''),
            supplier=request.form.get('supplier', ''),
            supplier_article_number=request.form.get('supplier_article_number', ''),
            active=request.form.get('active', False) == 'on',
            created_by=current_user.username,
            # Neue Felder
            product_type=request.form.get('product_type', ''),
            manufacturer_number=request.form.get('manufacturer_number', ''),
            purchase_price_single=float(request.form.get('purchase_price_single', '0').replace(',', '.') or 0),
            purchase_price_carton=float(request.form.get('purchase_price_carton', '0').replace(',', '.') or 0),
            purchase_price_10carton=float(request.form.get('purchase_price_10carton', '0').replace(',', '.') or 0)
        )
        
        # L-Shop erweiterte Felder
        article.units_per_carton = int(request.form.get('units_per_carton', 0) or 0)
        article.has_variants = request.form.get('has_variants') == 'on'
        article.catalog_page_texstyles = int(request.form.get('catalog_page_texstyles', 0) or 0)
        article.catalog_page_corporate = int(request.form.get('catalog_page_corporate', 0) or 0)
        article.catalog_page_wahlbuch = int(request.form.get('catalog_page_wahlbuch', 0) or 0)
        
        # Kategorie und Marke IDs
        category_id = request.form.get('category_id')
        if category_id:
            article.category_id = int(category_id)
        
        brand_id = request.form.get('brand_id')
        if brand_id:
            article.brand_id = int(brand_id)
        
        # Berechne kalkulierte Preise mit erweitertem System
        try:
            # Verwende den LShopImportService für die Preiskalkulation
            from src.services.lshop_import_service import LShopImportService
            import_service = LShopImportService()
            
            # Preise berechnen
            purchase_prices = {
                'single': article.purchase_price_single,
                'carton': article.purchase_price_carton,
                'ten_carton': article.purchase_price_10carton
            }
            
            price_result = import_service.calculate_selling_prices(purchase_prices, article)
            
            # VK-Preise setzen
            article.price_calculated = price_result['calculated']
            article.price_recommended = price_result['recommended']
            
            # Aktuellen Preis setzen wenn noch nicht gesetzt
            if not article.price:
                article.price = article.price_calculated
                
        except Exception:
            # Fallback auf alte Methode
            article.calculate_prices(use_new_system=False)
        
        # In Datenbank speichern
        try:
            db.session.add(article)
            db.session.commit()

            log_activity('article_created',
                        f'Artikel erstellt: {article.id} - {article.name}')

            flash(f'Artikel {article.name} wurde erstellt!', 'success')
            return redirect(url_for('articles.show', article_id=article.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Speichern: {str(e)}', 'danger')
    
    # Kategorien für Dropdown
    categories = db.session.query(Article.category).distinct().filter(Article.category.isnot(None)).all()
    categories = [c[0] for c in categories if c[0]]
    
    # Neue Kategorien aus ProductCategory
    product_categories = ProductCategory.query.filter_by(active=True).order_by(ProductCategory.sort_order, ProductCategory.name).all()
    
    # Marken für Dropdown
    brands = Brand.query.filter_by(active=True).order_by(Brand.name).all()
    
    # Lieferanten für Dropdown
    suppliers = Supplier.query.filter_by(active=True).order_by(Supplier.name).all()
    
    # Kalkulationsfaktoren (erweitert)
    try:
        from src.models.settings import PriceCalculationRule, TaxRate
        default_rule = PriceCalculationRule.get_default_rule()
        if default_rule:
            price_factors = {
                'calculated': default_rule.factor_calculated,
                'recommended': default_rule.factor_recommended,
                'tax_rate': default_rule.tax_rate.rate if default_rule.tax_rate else TaxRate.get_default_rate()
            }
        else:
            # Fallback auf Legacy
            price_factors = {
                'calculated': PriceCalculationSettings.get_setting('price_factor_calculated', 1.5),
                'recommended': PriceCalculationSettings.get_setting('price_factor_recommended', 2.0),
                'tax_rate': 19.0
            }
    except ImportError:
        # Legacy System
        price_factors = {
            'calculated': PriceCalculationSettings.get_setting('price_factor_calculated', 1.5),
            'recommended': PriceCalculationSettings.get_setting('price_factor_recommended', 2.0),
            'tax_rate': 19.0
        }
    
    return render_template('articles/new.html', 
                         categories=categories, 
                         product_categories=product_categories,
                         brands=brands,
                         suppliers=suppliers,
                         price_factors=price_factors)

@article_bp.route('/test/<article_id>')
@login_required
def test(article_id):
    """Test route for debugging"""
    article = Article.query.get_or_404(article_id)
    
    # Neue Kategorien aus ProductCategory
    product_categories = ProductCategory.query.filter_by(active=True).order_by(ProductCategory.sort_order, ProductCategory.name).all()
    
    # Marken für Dropdown
    brands = Brand.query.filter_by(active=True).order_by(Brand.name).all()
    
    # Kalkulationsfaktoren
    price_factors = {
        'calculated': PriceCalculationSettings.get_setting('price_factor_calculated', 1.5),
        'recommended': PriceCalculationSettings.get_setting('price_factor_recommended', 2.0)
    }
    
    return render_template('articles/test.html', 
                         article=article,
                         product_categories=product_categories,
                         brands=brands,
                         price_factors=price_factors)

@article_bp.route('/<article_id>')
@login_required
def show(article_id):
    """Artikel-Details anzeigen"""
    article = Article.query.get_or_404(article_id)
    
    # Preisberechnung entfernt (vermeidet Database Lock)
    # Stelle sicher, dass Preis-Attribute existieren
    if not hasattr(article, 'price_calculated') or article.price_calculated is None:
        article.price_calculated = article.price or 0
    if not hasattr(article, 'price_recommended') or article.price_recommended is None:
        article.price_recommended = article.price or 0
    
    # Lagerbestand-Status berechnen (mit None-Check)
    stock = article.stock or 0
    min_stock = article.min_stock or 0
    
    if stock <= 0:
        stock_status = 'danger'
        stock_text = 'Nicht auf Lager'
    elif stock <= min_stock:
        stock_status = 'warning'
        stock_text = 'Niedriger Bestand'
    else:
        stock_status = 'success'
        stock_text = 'Auf Lager'
    
    return render_template('articles/show.html',
                         article=article,
                         stock_status=stock_status,
                         stock_text=stock_text)

@article_bp.route('/<article_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(article_id):
    """Artikel bearbeiten"""
    article = Article.query.get_or_404(article_id)
    
    if request.method == 'POST':
        # Artikel aktualisieren
        article.article_number = request.form.get('article_number', '')
        article.name = request.form.get('name')
        article.category = request.form.get('category', '')
        article.description = request.form.get('description', '')
        article.brand = request.form.get('brand', '')
        article.material = request.form.get('material', '')
        article.weight = float(request.form.get('weight', 0) or 0)
        article.color = request.form.get('color', '')
        article.size = request.form.get('size', '')
        
        # Kategorie und Marke IDs
        category_id = request.form.get('category_id')
        if category_id:
            article.category_id = int(category_id)
        
        brand_id = request.form.get('brand_id')
        if brand_id:
            article.brand_id = int(brand_id)
        
        # Neue Preis-Felder (Komma zu Punkt)
        article.purchase_price_single = float(request.form.get('purchase_price_single', '0').replace(',', '.') or 0)
        article.purchase_price_carton = float(request.form.get('purchase_price_carton', '0').replace(',', '.') or 0)
        article.purchase_price_10carton = float(request.form.get('purchase_price_10carton', '0').replace(',', '.') or 0)
        
        # VK-Preis (manuell)
        article.price = float(request.form.get('price', '0').replace(',', '.') or 0)
        
        # Neue Felder
        article.product_type = request.form.get('product_type', '')
        article.manufacturer_number = request.form.get('manufacturer_number', '')
        
        # Berechne kalkulierte Preise
        article.calculate_prices()
        
        article.stock = int(request.form.get('stock', 0) or 0)
        article.min_stock = int(request.form.get('min_stock', 0) or 0)
        article.location = request.form.get('location', '')
        article.supplier = request.form.get('supplier', '')
        article.supplier_article_number = request.form.get('supplier_article_number', '')
        article.active = request.form.get('active', False) == 'on'
        article.updated_at = datetime.utcnow()
        article.updated_by = current_user.username
        
        # Änderungen speichern
        db.session.commit()
        
        # Aktivität protokollieren
        log_activity('article_updated', 
                    f'Artikel aktualisiert: {article.id} - {article.name}')
        
        flash(f'Artikel {article.name} wurde aktualisiert!', 'success')
        return redirect(url_for('articles.show', article_id=article.id))
    
    # Kategorien für Dropdown
    categories = db.session.query(Article.category).distinct().filter(Article.category.isnot(None)).all()
    categories = [c[0] for c in categories if c[0]]
    
    # Neue Kategorien aus ProductCategory
    product_categories = ProductCategory.query.filter_by(active=True).order_by(ProductCategory.sort_order, ProductCategory.name).all()
    
    # Marken für Dropdown
    brands = Brand.query.filter_by(active=True).order_by(Brand.name).all()
    
    # Lieferanten für Dropdown
    suppliers = Supplier.query.filter_by(active=True).order_by(Supplier.name).all()
    
    # Kalkulationsfaktoren
    price_factors = {
        'calculated': PriceCalculationSettings.get_setting('price_factor_calculated', 1.5),
        'recommended': PriceCalculationSettings.get_setting('price_factor_recommended', 2.0)
    }
    
    return render_template('articles/edit.html', 
                         article=article,
                         categories=categories,
                         product_categories=product_categories,
                         brands=brands,
                         suppliers=suppliers,
                         price_factors=price_factors)

@article_bp.route('/<article_id>/delete', methods=['POST'])
@login_required
def delete(article_id):
    """Artikel löschen"""
    article = Article.query.get_or_404(article_id)
    article_name = article.name
    
    # Prüfen ob Artikel in Aufträgen verwendet wird
    if article.order_items.count() > 0:
        flash(f'Artikel {article_name} kann nicht gelöscht werden, da er in Aufträgen verwendet wird!', 'danger')
        return redirect(url_for('articles.show', article_id=article_id))
    
    # Aktivität protokollieren bevor gelöscht wird
    log_activity('article_deleted', 
                f'Artikel gelöscht: {article.id} - {article_name}')
    
    # Artikel löschen
    db.session.delete(article)
    db.session.commit()
    
    flash(f'Artikel {article_name} wurde gelöscht!', 'success')
    return redirect(url_for('articles.index'))

@article_bp.route('/<article_id>/stock', methods=['POST'])
@login_required
def update_stock(article_id):
    """Lagerbestand aktualisieren mit erweiterter Historie"""
    article = Article.query.get_or_404(article_id)
    
    action = request.form.get('action')
    quantity = int(request.form.get('quantity', 0) or 0)
    order_number = request.form.get('order_number', '')
    reason = request.form.get('reason', '')
    
    # None-Check für aktuellen Bestand
    old_stock = article.stock or 0
    if article.stock is None:
        article.stock = 0
    
    # Bestandsänderung durchführen
    if action == 'add':
        article.stock += quantity
        log_detail = f'Wareneingang: +{quantity}'
    elif action == 'remove':
        article.stock = max(0, article.stock - quantity)
        log_detail = f'Entnahme: -{quantity}'
    elif action == 'inventory':
        article.stock = quantity
        log_detail = f'Inventur: Bestand auf {quantity} gesetzt'
    elif action == 'correction':
        if quantity >= 0:
            article.stock += quantity
            log_detail = f'Korrektur: +{quantity}'
        else:
            article.stock = max(0, article.stock + quantity)
            log_detail = f'Korrektur: {quantity}'
    else:
        article.stock = quantity
        log_detail = f'Bestand gesetzt auf {quantity}'
    
    article.updated_at = datetime.utcnow()
    article.updated_by = current_user.username
    
    # Erweiterte Log-Details erstellen
    log_details = [log_detail]
    log_details.append(f'Von {old_stock} auf {article.stock}')
    
    if order_number:
        # Erstelle Link zur Bestellung basierend auf dem Typ
        if order_number.startswith('PO') or order_number.startswith('SO'):
            # Lieferantenbestellung
            log_details.append(f'Lieferantenbestellung: {order_number}')
        elif order_number.startswith('A'):
            # Kundenauftrag
            log_details.append(f'Kundenauftrag: {order_number}')
        else:
            log_details.append(f'Bestellung: {order_number}')
    
    if reason:
        log_details.append(f'Grund: {reason}')
    
    log_details.append(f'Geändert von: {current_user.username}')
    
    db.session.commit()
    
    # Aktivität protokollieren mit allen Details
    log_activity('stock_updated', 
                f'Artikel {article.id} - {article.name}: ' + ' | '.join(log_details))
    
    flash(f'Lagerbestand von {article.name} wurde aktualisiert!', 'success')
    return redirect(url_for('articles.show', article_id=article_id))

# L-Shop Import Routes
@article_bp.route('/import/lshop', methods=['GET', 'POST'])
@login_required
def import_lshop():
    """L-Shop Excel Import"""
    if request.method == 'POST':
        # Excel-Upload verarbeiten
        if 'excel_file' not in request.files:
            flash('Keine Datei ausgewählt', 'error')
            return redirect(request.url)
        
        file = request.files['excel_file']
        if file.filename == '':
            flash('Keine Datei ausgewählt', 'error')
            return redirect(request.url)
        
        if file and file.filename.endswith('.xlsx'):
            # Temporäre Datei erstellen
            temp_dir = tempfile.gettempdir()
            filename = secure_filename(file.filename)
            filepath = os.path.join(temp_dir, filename)
            file.save(filepath)
            
            # Import-Service nutzen
            service = LShopImportService()
            
            # Analysiere Excel
            analysis = service.analyze_excel(filepath)
            if not analysis['success']:
                flash(f"Fehler beim Lesen der Excel-Datei: {analysis['error']}", 'error')
                os.remove(filepath)
                return redirect(request.url)
            
            # Validiere Daten
            validation = service.validate_data()
            if not validation['valid']:
                flash('Validierung fehlgeschlagen: ' + ', '.join(validation['errors']), 'error')
                os.remove(filepath)
                return redirect(request.url)
            
            # Import-Optionen
            options = {
                'update_existing': request.form.get('update_existing') == 'on',
                'create_variants': request.form.get('create_variants') == 'on',
                'supplier_id': request.form.get('supplier_id', 'L-SHOP'),
                'column_mapping': json.loads(request.form.get('column_mapping', '{}'))
            }
            
            # Führe Import durch
            result = service.import_articles(options['column_mapping'], options)
            
            # Aufräumen
            os.remove(filepath)
            
            if result['success']:
                message = f"Import erfolgreich! {result['imported_count']} neue Artikel, {result.get('updated_count', 0)} aktualisiert, {result['skipped_count']} übersprungen"
                if result.get('variant_count'):
                    message += f", {result['variant_count']} Varianten erstellt"
                if result['errors']:
                    message += f" ({len(result['errors'])} Fehler)"
                flash(message, 'success')
                
                # Aktivität protokollieren
                log_activity('lshop_import', 
                           f"L-Shop Import: {result['imported_count']} importiert, {result.get('updated_count', 0)} aktualisiert")
                
                return redirect(url_for('articles.index'))
            else:
                flash(f"Import fehlgeschlagen: {result['error']}", 'error')
        else:
            flash('Nur Excel-Dateien (.xlsx) werden unterstützt', 'error')
    
    # GET Request - zeige Import-Formular
    suppliers = Supplier.query.filter_by(active=True).order_by(Supplier.name).all()
    return render_template('articles/import_lshop.html', suppliers=suppliers)

@article_bp.route('/import/lshop/analyze', methods=['POST'])
@login_required
def import_lshop_analyze():
    """Analysiere Excel-Datei und zeige Spalten für Mapping"""
    if 'excel_file' not in request.files:
        return jsonify({'success': False, 'error': 'Keine Datei ausgewählt'})
    
    file = request.files['excel_file']
    if file.filename == '' or not file.filename.endswith('.xlsx'):
        return jsonify({'success': False, 'error': 'Ungültige Datei'})
    
    # Temporäre Datei
    temp_dir = tempfile.gettempdir()
    filename = secure_filename(file.filename)
    filepath = os.path.join(temp_dir, filename)
    file.save(filepath)
    
    # Analysiere mit Service
    service = LShopImportService()
    analysis = service.analyze_excel(filepath)
    
    if not analysis['success']:
        os.remove(filepath)
        return jsonify({'success': False, 'error': analysis['error']})
    
    # Hole Spalten-Mapping Preview
    service.get_column_mapping_preview()
    
    # Speichere Filepath in Session für späteren Import
    session['import_file_path'] = filepath
    session['import_file_name'] = filename
    
    return jsonify({
        'success': True,
        'mapping_preview': {
            'columns': [{
                'index': idx,
                'name': col_name
            } for idx, col_name in enumerate(analysis['columns'])],
            'preview_rows': [[
                {'value': str(row.get(col, '')) if row.get(col) is not None else ''}
                for col in analysis['columns']
            ] for row in analysis['preview_data'][:5]]
        },
        'total_rows': analysis['total_rows']
    })

@article_bp.route('/import/lshop/preview', methods=['POST'])
@login_required
def import_lshop_preview():
    """Vorschau der zu importierenden Artikel mit custom Mapping"""
    if 'excel_file' not in request.files:
        return jsonify({'success': False, 'error': 'Keine Datei ausgewählt'})
    
    file = request.files['excel_file']
    if file.filename == '' or not file.filename.endswith('.xlsx'):
        return jsonify({'success': False, 'error': 'Ungültige Datei'})
    
    # Temporäre Datei
    temp_dir = tempfile.gettempdir()
    filename = secure_filename(file.filename)
    filepath = os.path.join(temp_dir, filename)
    file.save(filepath)
    
    # Analysiere mit Service
    service = LShopImportService()
    analysis = service.analyze_excel(filepath)
    
    if not analysis['success']:
        os.remove(filepath)
        return jsonify({'success': False, 'error': analysis['error']})
    
    # Validierung
    validation = service.validate_data()
    
    # Vorschau erstellen
    preview = service.get_import_preview(limit=50)
    
    # Aufräumen
    os.remove(filepath)
    
    return jsonify({
        'success': True,
        'total_rows': analysis['total_rows'],
        'valid_rows': validation.get('valid_rows', 0),
        'warnings': validation.get('warnings', []),
        'preview': preview
    })

# Kompatibilitätsmethode für Templates
def get_article(article_id):
    """Artikel nach ID abrufen"""
    return Article.query.get(article_id)

@article_bp.route('/<string:article_id>/label')
@login_required
def print_label(article_id):
    """Etikett für Artikel drucken (62mm Endlos-Etikettendrucker)"""
    article = Article.query.get_or_404(article_id)
    
    # Füge aktuelles Datum für das Template hinzu
    from datetime import datetime
    now = datetime.now()
    
    # Aktivität protokollieren
    log_activity('article_label_printed', 
                f'Etikett gedruckt für Artikel: {article.name} ({article.article_number or article.id})')
    
    return render_template('articles/label.html', 
                         article=article,
                         now=now)

@article_bp.route('/<string:article_id>/label/multi')
@login_required
def print_label_multi(article_id):
    """Erweiterte Etiketten-Optionen für Artikel (mehrere Etiketten, verschiedene Formate)"""
    article = Article.query.get_or_404(article_id)
    
    # Füge aktuelles Datum für das Template hinzu
    from datetime import datetime
    now = datetime.now()
    
    # Aktivität protokollieren
    log_activity('article_label_multi_accessed', 
                f'Mehrfach-Etiketten geöffnet für Artikel: {article.name} ({article.article_number or article.id})')
    
    return render_template('articles/label_multi.html', 
                         article=article,
                         now=now)

@article_bp.route('/<string:article_id>/datasheet')
@login_required  
def print_datasheet(article_id):
    """DIN A4 Produktdatenblatt für Kunden"""
    article = Article.query.get_or_404(article_id)
    
    # Füge aktuelles Datum für das Template hinzu
    from datetime import datetime
    now = datetime.now()

    # Aktivität protokollieren
    log_activity('article_datasheet_printed',
                f'Produktdatenblatt gedruckt für Artikel: {article.name} ({article.article_number or article.id})')

    return render_template('articles/datasheet.html',
                         article=article,
                         now=now)


@article_bp.route('/<string:article_id>/image/search')
@login_required
def image_search(article_id):
    """Sucht Produktbilder per Artikelnummer/Bezeichnung"""
    article = Article.query.get_or_404(article_id)
    try:
        from src.services.article_image_service import ArticleImageSearchService
        from flask import current_app
        upload_dir = current_app.config.get('UPLOAD_FOLDER', 'instance/uploads')
        service = ArticleImageSearchService(upload_base_dir=upload_dir)
        images = service.search_images(article)
        return jsonify({'success': True, 'images': images})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@article_bp.route('/<string:article_id>/image/save', methods=['POST'])
@login_required
def image_save(article_id):
    """Laedt ein Bild herunter und speichert es zum Artikel"""
    article = Article.query.get_or_404(article_id)
    image_url = request.json.get('image_url', '').strip() if request.is_json else request.form.get('image_url', '').strip()
    if not image_url:
        return jsonify({'success': False, 'error': 'Keine Bild-URL angegeben'})

    try:
        from src.services.article_image_service import ArticleImageSearchService
        from flask import current_app
        upload_dir = current_app.config.get('UPLOAD_FOLDER', 'instance/uploads')
        service = ArticleImageSearchService(upload_base_dir=upload_dir)

        # Altes Bild loeschen falls vorhanden
        if article.image_path:
            service.delete_image(article.image_path, article.image_thumbnail_path)

        result = service.download_and_save(article.id, image_url)
        if result['success']:
            article.image_url = image_url
            article.image_path = result['image_path']
            article.image_thumbnail_path = result['thumbnail_path']
            article.updated_by = current_user.username
            article.updated_at = datetime.now()
            db.session.commit()
            log_activity('article_image_saved', f'Artikelbild gespeichert: {article.name}')
            return jsonify({
                'success': True,
                'image_path': f"/uploads/{result['image_path']}",
                'thumbnail_path': f"/uploads/{result['thumbnail_path']}",
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@article_bp.route('/<string:article_id>/image/delete', methods=['POST'])
@login_required
def image_delete(article_id):
    """Loescht das Artikelbild"""
    article = Article.query.get_or_404(article_id)
    try:
        if article.image_path:
            from src.services.article_image_service import ArticleImageSearchService
            from flask import current_app
            upload_dir = current_app.config.get('UPLOAD_FOLDER', 'instance/uploads')
            service = ArticleImageSearchService(upload_base_dir=upload_dir)
            service.delete_image(article.image_path, article.image_thumbnail_path)

        article.image_url = None
        article.image_path = None
        article.image_thumbnail_path = None
        article.updated_by = current_user.username
        article.updated_at = datetime.now()
        db.session.commit()
        log_activity('article_image_deleted', f'Artikelbild geloescht: {article.name}')
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@article_bp.route('/images/mass-import', methods=['POST'])
@login_required
def mass_image_import():
    """Massen-Bildimport: Sucht fuer alle Artikel ohne Bild ein Bild vom L-Shop"""
    import threading
    from flask import current_app

    app = current_app._get_current_object()
    upload_dir = current_app.config.get('UPLOAD_FOLDER', 'instance/uploads')

    def run_import(app_ctx, upload_dir):
        with app_ctx:
            from src.services.article_image_service import ArticleImageSearchService
            import time

            service = ArticleImageSearchService(upload_base_dir=upload_dir)
            articles = Article.query.filter(
                Article.supplier_article_number.isnot(None),
                Article.supplier_article_number != '',
                db.or_(
                    Article.image_path.is_(None),
                    Article.image_path == ''
                )
            ).all()

            total = len(articles)
            success_count = 0
            fail_count = 0
            logger.info(f"Massen-Bildimport gestartet: {total} Artikel ohne Bild")

            for idx, article in enumerate(articles):
                try:
                    # Priorität 1: Bereits gespeicherte Bild-URL (aus LShop-Import)
                    image_url_to_use = None
                    if article.image_url:
                        image_url_to_use = article.image_url
                    else:
                        # Priorität 2: L-Shop Suche (nur wenn keine URL gespeichert)
                        images = service._search_lshop(
                            article.supplier_article_number,
                            article.name or ''
                        )
                        if images:
                            image_url_to_use = images[0]['url']

                    if image_url_to_use:
                        result = service.download_and_save(article.id, image_url_to_use)
                        if result.get('success'):
                            article.image_url = image_url_to_use
                            article.image_path = result['image_path']
                            article.image_thumbnail_path = result['thumbnail_path']
                            db.session.commit()
                            success_count += 1
                        else:
                            fail_count += 1
                    else:
                        fail_count += 1

                    # Rate limiting - nicht den L-Shop ueberlasten
                    if idx % 10 == 0 and idx > 0:
                        time.sleep(2)
                        logger.info(f"Bildimport Fortschritt: {idx}/{total} ({success_count} OK, {fail_count} fehlgeschlagen)")

                except Exception as e:
                    fail_count += 1
                    logger.warning(f"Bildimport Fehler fuer {article.supplier_article_number}: {e}")
                    try:
                        db.session.rollback()
                    except Exception:
                        pass

            logger.info(f"Massen-Bildimport abgeschlossen: {success_count} OK, {fail_count} fehlgeschlagen von {total}")

    thread = threading.Thread(target=run_import, args=(app.app_context(), upload_dir))
    thread.daemon = True
    thread.start()

    # Zaehle Artikel ohne Bild
    count = Article.query.filter(
        Article.supplier_article_number.isnot(None),
        Article.supplier_article_number != '',
        db.or_(
            Article.image_path.is_(None),
            Article.image_path == ''
        )
    ).count()

    return jsonify({
        'success': True,
        'message': f'Bildimport fuer {count} Artikel gestartet (laeuft im Hintergrund)',
        'total': count
    })


@article_bp.route('/images/import-status')
@login_required
def image_import_status():
    """Status des Bildimports"""
    total = Article.query.filter(
        Article.supplier_article_number.isnot(None),
        Article.supplier_article_number != ''
    ).count()

    with_image = Article.query.filter(
        Article.image_path.isnot(None),
        Article.image_path != ''
    ).count()

    return jsonify({
        'success': True,
        'total': total,
        'with_image': with_image,
        'without_image': total - with_image,
        'percent': round((with_image / total * 100), 1) if total > 0 else 0
    })


@article_bp.route('/import/printequipment', methods=['POST'])
@login_required
def import_printequipment():
    """Importiert Sublimationsprodukte von Printequipment"""
    import threading
    from flask import current_app

    app = current_app._get_current_object()
    upload_dir = current_app.config.get('UPLOAD_FOLDER', 'instance/uploads')

    from src.services.printequipment_import_service import run_full_import

    thread = threading.Thread(
        target=run_full_import,
        args=(app.app_context(), upload_dir)
    )
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'message': 'Printequipment Sublimation-Import gestartet (laeuft im Hintergrund)'
    })


@article_bp.route('/api/filter-options')
@login_required
def api_filter_options():
    """Liefert alle verfuegbaren Filter-Werte aus der Artikeltabelle (auto-populated)."""
    filter_data = {}

    # Brands: aus Brand-Tabelle falls vorhanden, sonst aus article.brand
    brands_from_table = Brand.query.filter_by(active=True).order_by(Brand.name).all()
    if brands_from_table:
        filter_data['brands'] = [{'id': b.id, 'name': b.name} for b in brands_from_table]
    else:
        raw = db.session.query(Article.brand).filter(
            Article.active == True, Article.brand.isnot(None), Article.brand != ''
        ).distinct().order_by(Article.brand).all()
        filter_data['brands'] = [{'id': None, 'name': r[0]} for r in raw]

    # Kategorien: aus ProductCategory-Tabelle falls vorhanden
    cats = ProductCategory.query.filter_by(active=True).order_by(ProductCategory.name).all()
    if cats:
        filter_data['categories'] = [{'id': c.id, 'name': c.name} for c in cats]
    else:
        raw = db.session.query(Article.category).filter(
            Article.active == True, Article.category.isnot(None), Article.category != ''
        ).distinct().order_by(Article.category).all()
        filter_data['categories'] = [{'id': None, 'name': r[0]} for r in raw]

    # Lieferanten
    raw = db.session.query(Article.supplier).filter(
        Article.active == True, Article.supplier.isnot(None), Article.supplier != ''
    ).distinct().order_by(Article.supplier).all()
    filter_data['suppliers'] = [r[0] for r in raw]

    # Materialien
    raw = db.session.query(Article.material).filter(
        Article.active == True, Article.material.isnot(None), Article.material != ''
    ).distinct().order_by(Article.material).all()
    filter_data['materials'] = [r[0] for r in raw]

    # Farben
    raw = db.session.query(Article.color).filter(
        Article.active == True, Article.color.isnot(None), Article.color != ''
    ).distinct().order_by(Article.color).all()
    filter_data['colors'] = [r[0] for r in raw]

    # Produkttypen
    raw = db.session.query(Article.product_type).filter(
        Article.active == True, Article.product_type.isnot(None), Article.product_type != ''
    ).distinct().order_by(Article.product_type).all()
    filter_data['product_types'] = [r[0] for r in raw]

    return jsonify(filter_data)


@article_bp.route('/api/search')
@login_required
def api_search():
    """Unified Artikel-Suche mit Smart-Filtern."""
    query_text = request.args.get('q', '').strip()
    limit = min(request.args.get('limit', 50, type=int), 200)
    offset = request.args.get('offset', 0, type=int)

    q = Article.query.filter(Article.active == True)

    # Textsuche
    if query_text and len(query_text) >= 2:
        q = q.filter(db.or_(
            Article.name.ilike(f'%{query_text}%'),
            Article.article_number.ilike(f'%{query_text}%'),
            Article.description.ilike(f'%{query_text}%'),
            Article.supplier_article_number.ilike(f'%{query_text}%')
        ))

    # Brand-Filter
    brand_id = request.args.get('brand_id', type=int)
    if brand_id:
        q = q.filter(Article.brand_id == brand_id)
    else:
        brand_name = request.args.get('brand', '').strip()
        if brand_name:
            q = q.filter(Article.brand.ilike(f'%{brand_name}%'))

    # Kategorie-Filter
    category_id = request.args.get('category_id', type=int)
    if category_id:
        q = q.filter(Article.category_id == category_id)
    else:
        category_name = request.args.get('category', '').strip()
        if category_name:
            q = q.filter(Article.category.ilike(f'%{category_name}%'))

    # Lieferant-Filter
    supplier_name = request.args.get('supplier', '').strip()
    if supplier_name:
        q = q.filter(Article.supplier.ilike(f'%{supplier_name}%'))

    # Material-Filter
    material = request.args.get('material', '').strip()
    if material:
        q = q.filter(Article.material == material)

    # Farbe-Filter (Teilmatch fuer "Schwarz" -> "Schwarz/Rot")
    color = request.args.get('color', '').strip()
    if color:
        q = q.filter(Article.color.ilike(f'%{color}%'))

    # Produkttyp-Filter
    product_type = request.args.get('product_type', '').strip()
    if product_type:
        q = q.filter(Article.product_type == product_type)

    # Shop-Filter
    show_in_shop = request.args.get('show_in_shop')
    if show_in_shop == 'true':
        q = q.filter(Article.show_in_shop == True)

    # Lagerbestand-Filter
    stock_filter = request.args.get('stock', '').strip()
    if stock_filter == 'available':
        q = q.filter(Article.stock > 0)
    elif stock_filter == 'low':
        q = q.filter(Article.stock > 0, Article.stock <= 10)
    elif stock_filter == 'out':
        q = q.filter(db.or_(Article.stock == 0, Article.stock.is_(None)))

    total = q.count()
    articles = q.order_by(Article.name).offset(offset).limit(limit).all()

    return jsonify({
        'total': total,
        'articles': [{
            'id': a.id,
            'name': a.name,
            'article_number': a.article_number,
            'supplier_article_number': a.supplier_article_number,
            'description': a.description or '',
            'price': float(a.price or 0),
            'purchase_price': float(a.purchase_price_single or 0),
            'stock': a.stock or 0,
            'category': a.category,
            'category_id': a.category_id,
            'brand': a.brand,
            'brand_id': a.brand_id,
            'supplier': a.supplier or '',
            'material': a.material or '',
            'color': a.color or '',
            'size': a.size or '',
            'product_type': a.product_type or '',
            'weight': float(a.weight or 0)
        } for a in articles]
    })


# ============================================================
# VARIANTEN CRUD API
# ============================================================

@article_bp.route('/api/<article_id>/variants')
@login_required
def api_variants_list(article_id):
    """Liste aller Varianten eines Artikels"""
    article = Article.query.get_or_404(article_id)
    variants = article.get_all_variants()
    return jsonify([v.to_dict() for v in variants])


@article_bp.route('/api/<article_id>/variants', methods=['POST'])
@login_required
def api_variant_create(article_id):
    """Neue Variante erstellen"""
    article = Article.query.get_or_404(article_id)
    data = request.get_json() or {}

    color = data.get('color', '').strip() or None
    size = data.get('size', '').strip() or None

    if not color and not size:
        return jsonify({'success': False, 'error': 'Farbe oder Groesse erforderlich'}), 400

    # Duplikat-Check
    existing = ArticleVariant.query.filter_by(
        article_id=article_id, color=color, size=size
    ).first()
    if existing:
        return jsonify({'success': False, 'error': 'Diese Variante existiert bereits'}), 400

    vtype = 'color_size' if (color and size) else ('color' if color else 'size')

    variant = ArticleVariant(
        article_id=article_id,
        variant_type=vtype,
        color=color,
        size=size,
        ean=data.get('ean', '').strip() or None,
        single_price=float(data['single_price']) if data.get('single_price') else None,
        carton_price=float(data['carton_price']) if data.get('carton_price') else None,
        ten_carton_price=float(data['ten_carton_price']) if data.get('ten_carton_price') else None,
        units_per_carton=int(data['units_per_carton']) if data.get('units_per_carton') else None,
        stock=int(data.get('stock', 0)),
        min_stock=int(data.get('min_stock', 0)),
        active=True,
        created_by=current_user.username if current_user.is_authenticated else None,
    )
    db.session.add(variant)

    if not article.has_variants:
        article.has_variants = True

    db.session.commit()
    return jsonify({'success': True, 'variant': variant.to_dict()})


@article_bp.route('/api/variants/<int:variant_id>', methods=['PUT'])
@login_required
def api_variant_update(variant_id):
    """Variante aktualisieren"""
    variant = ArticleVariant.query.get_or_404(variant_id)
    data = request.get_json() or {}

    if 'color' in data:
        variant.color = data['color'].strip() or None
    if 'size' in data:
        variant.size = data['size'].strip() or None
    if 'ean' in data:
        variant.ean = data['ean'].strip() or None
    if 'single_price' in data:
        variant.single_price = float(data['single_price']) if data['single_price'] else None
    if 'carton_price' in data:
        variant.carton_price = float(data['carton_price']) if data['carton_price'] else None
    if 'ten_carton_price' in data:
        variant.ten_carton_price = float(data['ten_carton_price']) if data['ten_carton_price'] else None
    if 'units_per_carton' in data:
        variant.units_per_carton = int(data['units_per_carton']) if data['units_per_carton'] else None
    if 'stock' in data:
        variant.stock = int(data['stock'])
    if 'min_stock' in data:
        variant.min_stock = int(data['min_stock'])
    if 'active' in data:
        variant.active = bool(data['active'])

    # variant_type aktualisieren
    if variant.color and variant.size:
        variant.variant_type = 'color_size'
    elif variant.color:
        variant.variant_type = 'color'
    else:
        variant.variant_type = 'size'

    variant.updated_by = current_user.username if current_user.is_authenticated else None
    db.session.commit()
    return jsonify({'success': True, 'variant': variant.to_dict()})


@article_bp.route('/api/variants/<int:variant_id>', methods=['DELETE'])
@login_required
def api_variant_delete(variant_id):
    """Variante loeschen"""
    variant = ArticleVariant.query.get_or_404(variant_id)
    article_id = variant.article_id
    db.session.delete(variant)

    # Pruefen ob Artikel noch Varianten hat
    remaining = ArticleVariant.query.filter_by(article_id=article_id).count()
    if remaining <= 1:  # Die geloeschte wird noch gezaehlt bis commit
        article = Article.query.get(article_id)
        if article and remaining <= 1:
            article.has_variants = False

    db.session.commit()
    return jsonify({'success': True})


@article_bp.route('/api/<article_id>/convert-to-variants', methods=['POST'])
@login_required
def api_convert_to_variants(article_id):
    """Wandelt einen Einzel-Artikel in einen Varianten-Artikel um"""
    article = Article.query.get_or_404(article_id)

    if article.has_variants:
        return jsonify({'success': False, 'error': 'Artikel hat bereits Varianten'}), 400

    # Erste Variante aus den aktuellen Artikeldaten erstellen
    color = article.color or None
    size = article.size or None
    vtype = 'color_size' if (color and size) else ('color' if color else 'size')

    if color or size:
        variant = ArticleVariant(
            article_id=article.id,
            variant_type=vtype,
            color=color,
            size=size,
            single_price=article.purchase_price_single,
            carton_price=article.purchase_price_carton,
            ten_carton_price=getattr(article, 'purchase_price_10carton', None),
            units_per_carton=article.units_per_carton,
            stock=article.stock or 0,
            min_stock=article.min_stock or 0,
            active=True,
            created_by=current_user.username if current_user.is_authenticated else None,
        )
        db.session.add(variant)

    article.has_variants = True
    article.color = None
    article.size = None
    db.session.commit()

    return jsonify({'success': True})
