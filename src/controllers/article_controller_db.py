"""
Article Controller - PostgreSQL-Version
Artikel-Verwaltung mit Datenbank
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from datetime import datetime
from src.models import db, Article, ActivityLog, Supplier, ProductCategory, Brand, PriceCalculationSettings
from src.services import LShopImportService
from werkzeug.utils import secure_filename
import os
import tempfile
import json

# Blueprint erstellen
article_bp = Blueprint('articles', __name__, url_prefix='/articles')

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

def generate_article_id():
    """Generiere neue Artikel-ID"""
    last_article = Article.query.filter(
        Article.id.like('ART%')
    ).order_by(Article.id.desc()).first()
    
    if last_article:
        try:
            last_num = int(last_article.id[3:])
            return f"ART{last_num + 1:03d}"
        except:
            return "ART001"
    return "ART001"

@article_bp.route('/')
@login_required
def index():
    """Artikel-Übersicht"""
    search_query = request.args.get('search', '').lower()
    category_filter = request.args.get('category', '')
    
    # Query erstellen
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
    
    # Nach Name sortieren
    articles_list = query.order_by(Article.name).all()
    
    # In Dictionary umwandeln für Template-Kompatibilität
    articles = {}
    for article in articles_list:
        # Preisberechnung beim Laden entfernt (vermeidet Database Lock)
        # Verwende existierende Preise aus der Datenbank
        articles[article.id] = article
    
    # Kategorien für Filter
    categories = db.session.query(Article.category).distinct().filter(Article.category.isnot(None)).all()
    categories = [c[0] for c in categories if c[0]]
    
    return render_template('articles/index.html',
                         articles=articles,
                         categories=categories,
                         search_query=search_query,
                         category_filter=category_filter)

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
            article_number=request.form.get('article_number', ''),
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
        db.session.add(article)
        db.session.commit()
        
        # Aktivität protokollieren
        log_activity('article_created', 
                    f'Artikel erstellt: {article.id} - {article.name}')
        
        flash(f'Artikel {article.name} wurde erstellt!', 'success')
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


@article_bp.route('/api/search')
@login_required
def api_search():
    """
    API-Endpunkt für Artikel-Suche (für Rechnungen, Aufträge etc.)
    """
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 20, type=int)

    if len(query) < 2:
        return jsonify({'articles': []})

    # Suche in Name, Artikelnummer, Beschreibung
    from sqlalchemy import or_

    articles = Article.query.filter(
        or_(
            Article.name.ilike(f'%{query}%'),
            Article.article_number.ilike(f'%{query}%'),
            Article.description.ilike(f'%{query}%'),
            Article.supplier_article_number.ilike(f'%{query}%')
        ),
        Article.active == True
    ).limit(limit).all()

    return jsonify({
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
            'brand': a.brand
        } for a in articles]
    })

