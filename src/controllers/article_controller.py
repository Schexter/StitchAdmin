"""
Article Controller - Artikel-Verwaltung
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
import json
import os
from datetime import datetime
from src.utils.activity_logger import log_activity

# Blueprint erstellen
article_bp = Blueprint('articles', __name__, url_prefix='/articles')

ARTICLES_FILE = 'articles.json'
CATEGORIES_FILE = 'article_categories.json'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Bitte melden Sie sich an.', 'info')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def load_articles():
    """Lade Artikel aus JSON-Datei"""
    if os.path.exists(ARTICLES_FILE):
        with open(ARTICLES_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_articles(articles):
    """Speichere Artikel in JSON-Datei"""
    with open(ARTICLES_FILE, 'w') as f:
        json.dump(articles, f, indent=2)

def load_categories():
    """Lade Kategorien aus JSON-Datei"""
    if os.path.exists(CATEGORIES_FILE):
        with open(CATEGORIES_FILE, 'r') as f:
            return json.load(f)
    return {
        "1": {"id": "1", "name": "Stoffe", "description": "Verschiedene Stoffarten"},
        "2": {"id": "2", "name": "Garne", "description": "Nähgarne und Stickgarne"},
        "3": {"id": "3", "name": "Kurzwaren", "description": "Knöpfe, Reißverschlüsse, etc."},
        "4": {"id": "4", "name": "Werkzeuge", "description": "Scheren, Nadeln, etc."},
        "5": {"id": "5", "name": "Zubehör", "description": "Sonstiges Nähzubehör"}
    }

def save_categories(categories):
    """Speichere Kategorien in JSON-Datei"""
    with open(CATEGORIES_FILE, 'w') as f:
        json.dump(categories, f, indent=2)

def generate_article_id():
    """Generiere neue Artikel-ID"""
    articles = load_articles()
    if not articles:
        return "ART001"
    
    # Finde höchste ID
    max_num = 0
    for article_id in articles.keys():
        if article_id.startswith("ART"):
            try:
                num = int(article_id[3:])
                max_num = max(max_num, num)
            except:
                pass
    
    return f"ART{max_num + 1:03d}"

@article_bp.route('/')
@login_required
def index():
    """Artikel-Übersicht"""
    articles = load_articles()
    categories = load_categories()
    
    # Filter
    category_filter = request.args.get('category', '')
    search_query = request.args.get('search', '').lower()
    stock_filter = request.args.get('stock', '')
    
    filtered_articles = {}
    
    for article_id, article in articles.items():
        # Kategorie-Filter
        if category_filter and article.get('category_id') != category_filter:
            continue
        
        # Such-Filter
        if search_query:
            if not (search_query in article.get('name', '').lower() or 
                    search_query in article.get('sku', '').lower() or
                    search_query in article.get('description', '').lower()):
                continue
        
        # Lagerbestand-Filter
        if stock_filter:
            stock = article.get('stock', 0)
            if stock_filter == 'out' and stock > 0:
                continue
            elif stock_filter == 'low' and stock > 10:
                continue
            elif stock_filter == 'available' and stock <= 0:
                continue
        
        filtered_articles[article_id] = article
    
    return render_template('articles/index.html', 
                         articles=filtered_articles,
                         categories=categories,
                         category_filter=category_filter,
                         search_query=search_query,
                         stock_filter=stock_filter)

@article_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Neuen Artikel erstellen"""
    categories = load_categories()
    
    # Lade Lieferanten
    from src.controllers.supplier_controller import load_suppliers
    suppliers = load_suppliers()
    
    if request.method == 'POST':
        articles = load_articles()
        
        article_id = generate_article_id()
        
        # Preis konvertieren
        try:
            price = float(request.form.get('price', '0').replace(',', '.'))
            purchase_price = float(request.form.get('purchase_price', '0').replace(',', '.'))
            stock = int(request.form.get('stock', '0'))
            min_stock = int(request.form.get('min_stock', '0'))
        except ValueError:
            flash('Ungültige Zahlenwerte!', 'danger')
            return render_template('articles/new.html', categories=categories, suppliers=suppliers)
        
        articles[article_id] = {
            'id': article_id,
            'sku': request.form.get('sku', ''),
            'name': request.form.get('name'),
            'description': request.form.get('description', ''),
            'category_id': request.form.get('category_id'),
            'price': price,
            'purchase_price': purchase_price,
            'stock': stock,
            'min_stock': min_stock,
            'unit': request.form.get('unit', 'Stück'),
            'location': request.form.get('location', ''),
            'supplier_id': request.form.get('supplier_id', ''),
            'supplier': request.form.get('supplier', ''),  # Für Abwärtskompatibilität
            'supplier_article_number': request.form.get('supplier_article_number', ''),
            'ean': request.form.get('ean', ''),
            'size': request.form.get('size', ''),
            'color': request.form.get('color', ''),
            'material': request.form.get('material', ''),
            'weight': request.form.get('weight', ''),
            'active': request.form.get('active', False) == 'on',
            'created_at': datetime.now().isoformat(),
            'created_by': session['username']
        }
        
        save_articles(articles)
        log_activity(session['username'], 'article_created', f'Artikel erstellt: {article_id} - {articles[article_id]["name"]}')
        
        flash(f'Artikel "{articles[article_id]["name"]}" wurde erstellt!', 'success')
        return redirect(url_for('articles.index'))
    
    # Vorausgewählter Lieferant aus URL-Parameter
    preselected_supplier_id = request.args.get('supplier_id', '')
    
    return render_template('articles/new.html', 
                         categories=categories, 
                         suppliers=suppliers,
                         preselected_supplier_id=preselected_supplier_id)

@article_bp.route('/<article_id>')
@login_required
def show(article_id):
    """Artikel-Details anzeigen"""
    articles = load_articles()
    article = articles.get(article_id)
    
    if not article:
        flash('Artikel nicht gefunden!', 'danger')
        return redirect(url_for('articles.index'))
    
    categories = load_categories()
    category = categories.get(article.get('category_id', ''), {})
    
    # Lade Lieferant falls vorhanden
    supplier = None
    if article.get('supplier_id'):
        from src.controllers.supplier_controller import load_suppliers
        suppliers = load_suppliers()
        supplier = suppliers.get(article['supplier_id'])
    
    return render_template('articles/show.html', article=article, category=category, supplier=supplier)

@article_bp.route('/<article_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(article_id):
    """Artikel bearbeiten"""
    articles = load_articles()
    article = articles.get(article_id)
    
    if not article:
        flash('Artikel nicht gefunden!', 'danger')
        return redirect(url_for('articles.index'))
    
    categories = load_categories()
    
    # Lade Lieferanten
    from src.controllers.supplier_controller import load_suppliers
    suppliers = load_suppliers()
    
    if request.method == 'POST':
        # Preis konvertieren
        try:
            price = float(request.form.get('price', '0').replace(',', '.'))
            purchase_price = float(request.form.get('purchase_price', '0').replace(',', '.'))
            stock = int(request.form.get('stock', '0'))
            min_stock = int(request.form.get('min_stock', '0'))
        except ValueError:
            flash('Ungültige Zahlenwerte!', 'danger')
            return render_template('articles/edit.html', article=article, categories=categories, suppliers=suppliers)
        
        # Artikel aktualisieren
        article['sku'] = request.form.get('sku', '')
        article['name'] = request.form.get('name')
        article['description'] = request.form.get('description', '')
        article['category_id'] = request.form.get('category_id')
        article['price'] = price
        article['purchase_price'] = purchase_price
        article['stock'] = stock
        article['min_stock'] = min_stock
        article['unit'] = request.form.get('unit', 'Stück')
        article['location'] = request.form.get('location', '')
        article['supplier_id'] = request.form.get('supplier_id', '')
        article['supplier'] = request.form.get('supplier', '')  # Für Abwärtskompatibilität
        article['supplier_article_number'] = request.form.get('supplier_article_number', '')
        article['ean'] = request.form.get('ean', '')
        article['size'] = request.form.get('size', '')
        article['color'] = request.form.get('color', '')
        article['material'] = request.form.get('material', '')
        article['weight'] = request.form.get('weight', '')
        article['active'] = request.form.get('active', False) == 'on'
        article['updated_at'] = datetime.now().isoformat()
        article['updated_by'] = session['username']
        
        save_articles(articles)
        log_activity(session['username'], 'article_updated', f'Artikel aktualisiert: {article_id} - {article["name"]}')
        
        flash(f'Artikel "{article["name"]}" wurde aktualisiert!', 'success')
        return redirect(url_for('articles.show', article_id=article_id))
    
    return render_template('articles/edit.html', article=article, categories=categories, suppliers=suppliers)

@article_bp.route('/<article_id>/delete', methods=['POST'])
@login_required
def delete(article_id):
    """Artikel löschen"""
    articles = load_articles()
    
    if article_id in articles:
        article_name = articles[article_id]['name']
        del articles[article_id]
        save_articles(articles)
        
        log_activity(session['username'], 'article_deleted', f'Artikel gelöscht: {article_id} - {article_name}')
        flash(f'Artikel "{article_name}" wurde gelöscht!', 'success')
    else:
        flash('Artikel nicht gefunden!', 'danger')
    
    return redirect(url_for('articles.index'))

@article_bp.route('/<article_id>/stock', methods=['POST'])
@login_required
def update_stock(article_id):
    """Lagerbestand aktualisieren (AJAX)"""
    articles = load_articles()
    article = articles.get(article_id)
    
    if not article:
        return jsonify({'success': False, 'message': 'Artikel nicht gefunden'}), 404
    
    data = request.get_json()
    change = int(data.get('change', 0))
    reason = data.get('reason', 'Manuelle Anpassung')
    
    old_stock = article['stock']
    article['stock'] = max(0, article['stock'] + change)
    
    save_articles(articles)
    
    log_activity(
        session['username'], 
        'stock_updated', 
        f'Lagerbestand {article["name"]}: {old_stock} → {article["stock"]} ({reason})'
    )
    
    return jsonify({
        'success': True,
        'new_stock': article['stock'],
        'low_stock': article['stock'] <= article.get('min_stock', 0)
    })

@article_bp.route('/<article_id>/duplicate', methods=['POST'])
@login_required
def duplicate(article_id):
    """Artikel duplizieren"""
    articles = load_articles()
    article = articles.get(article_id)
    
    if not article:
        return jsonify({'success': False, 'message': 'Artikel nicht gefunden'}), 404
    
    # Erstelle neue ID
    new_article_id = generate_article_id()
    
    # Kopiere Artikel mit neuen Werten
    new_article = article.copy()
    new_article['id'] = new_article_id
    new_article['name'] = f"{article['name']} (Kopie)"
    new_article['sku'] = f"{article.get('sku', '')}_COPY" if article.get('sku') else ''
    new_article['stock'] = 0  # Neue Artikel starten mit 0 Bestand
    new_article['created_at'] = datetime.now().isoformat()
    new_article['created_by'] = session['username']
    new_article['updated_at'] = datetime.now().isoformat()
    new_article['updated_by'] = session['username']
    
    # Entferne IDs aus Kopie für saubere Duplikation
    if 'updated_at' in article:
        new_article.pop('updated_at', None)
    if 'updated_by' in article:
        new_article.pop('updated_by', None)
    
    articles[new_article_id] = new_article
    save_articles(articles)
    
    log_activity(
        session['username'], 
        'article_duplicated', 
        f'Artikel dupliziert: {article_id} → {new_article_id} ({new_article["name"]})'
    )
    
    return jsonify({
        'success': True,
        'new_id': new_article_id,
        'new_name': new_article['name']
    })