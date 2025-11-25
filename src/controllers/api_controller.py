from flask import Blueprint, jsonify, request, send_from_directory
from flask_login import login_required
from src.models.models import Article, Supplier, db
from flask_swagger_ui import get_swaggerui_blueprint
import json
import os

api_bp = Blueprint('api', __name__, url_prefix='/api')

# ==================== SWAGGER UI KONFIGURATION ====================
SWAGGER_URL = '/api/docs'  # URL für Swagger UI
API_URL = '/openapi.yaml'  # URL zur OpenAPI-Spezifikation

# Erstelle Swagger UI Blueprint
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "StitchAdmin 2.0 API",
        'docExpansion': 'list',
        'defaultModelsExpandDepth': 3,
        'displayRequestDuration': True,
        'filter': True,
        'tryItOutEnabled': True
    }
)

# Registriere Swagger UI Blueprint (wird in app.py eingebunden)
# HINWEIS: Dies muss in app.py mit app.register_blueprint(swaggerui_blueprint) registriert werden

@api_bp.route('/articles')
@login_required
def get_articles():
    """
    API-Endpunkt für Artikelsuche mit optionalem Lieferantenfilter
    Erstellt von Hans Hahn - Alle Rechte vorbehalten
    FIXED: L-Shop Import Problem behoben
    """
    try:
        # Hole Query-Parameter
        supplier_id = request.args.get('supplier_id')
        search = request.args.get('search', '')
        
        print(f"API: Suche Artikel - supplier_id: {supplier_id}, search: {search}")
        
        # Versuche zuerst Datenbank
        articles_data = []
        
        try:
            # Basis-Query - zeige nur aktive Artikel
            query = Article.query.filter_by(active=True)
            
            # CRITICAL FIX: Supplier-Filter BEFORE search to improve performance
            if supplier_id:
                # Hole Lieferant aus DB
                supplier = Supplier.query.get(supplier_id)
                if supplier:
                    print(f"API: Lieferant gefunden - ID: {supplier_id}, Name: {supplier.name}")
                    
                    # FIXED: Filtere sowohl nach supplier-Name ALS AUCH nach supplier_id
                    # Das löst das Hauptproblem: verschiedene Datenformate in DB
                    query = query.filter(
                        db.or_(
                            Article.supplier == supplier.name,
                            Article.supplier == supplier_id,
                            Article.supplier_id == supplier_id if hasattr(Article, 'supplier_id') else False
                        )
                    )
                else:
                    print(f"API: WARNUNG - Lieferant {supplier_id} nicht gefunden")
            
            # Suchfilter
            if search:
                query = query.filter(
                    db.or_(
                        Article.article_number.ilike(f'%{search}%'),
                        Article.name.ilike(f'%{search}%'),
                        Article.supplier_article_number.ilike(f'%{search}%')
                    )
                )
            
            # Sortierung
            articles = query.order_by(Article.article_number).all()
            
            print(f"API: Nach DB-Query gefundene Artikel: {len(articles)}")
            
            # NEUE LOGGING FÜR DEBUG
            if supplier_id and len(articles) == 0:
                # Debug: Zeige verfügbare Supplier-Werte
                sample_articles = Article.query.limit(5).all()
                print("API: DEBUG - Beispiel-Artikel-Supplier:")
                for art in sample_articles:
                    print(f"   Artikel {art.article_number}: supplier='{art.supplier}'")
                
                all_suppliers = Supplier.query.all()
                print("API: DEBUG - Verfügbare Supplier:")
                for sup in all_suppliers:
                    print(f"   Supplier ID: {sup.id}, Name: '{sup.name}'")
            
            # Konvertiere zu JSON
            for article in articles:
                article_dict = {
                    'id': article.id,
                    'article_number': article.article_number,
                    'name': article.name,
                    'supplier': article.supplier,
                    'supplier_article_number': article.supplier_article_number,
                    'purchase_price': float(article.purchase_price_single) if article.purchase_price_single else 0,
                    'stock': article.stock or 0
                }
                
                # Prüfe Multi-Lieferanten-Unterstützung
                if hasattr(article, 'article_suppliers'):
                    article_dict['suppliers'] = [as_rel.supplier_id for as_rel in article.article_suppliers.filter_by(active=True)]
                    
                    # Wenn ein spezifischer Lieferant angefragt wurde, hole dessen Preis
                    if supplier_id:
                        supplier_rel = article.article_suppliers.filter_by(supplier_id=supplier_id, active=True).first()
                        if supplier_rel:
                            article_dict['purchase_price'] = float(supplier_rel.purchase_price)
                            article_dict['supplier_article_number'] = supplier_rel.supplier_article_number
                
                articles_data.append(article_dict)
        
            # IMPROVED: Nur Fallback wenn wirklich keine Artikel UND kein Supplier-Filter
            if len(articles_data) == 0 and not supplier_id:
                raise Exception("No articles in DB, trying JSON")
                
            # FIXED: Auch bei Supplier-Filter, wenn 0 Artikel, versuche erweiterte Suche
            elif len(articles_data) == 0 and supplier_id:
                print("API: Erweiterte Supplier-Suche wegen 0 Ergebnissen")
                
                # Versuche mit LIKE-Pattern für Supplier-Namen
                supplier = Supplier.query.get(supplier_id)
                if supplier:
                    extended_query = Article.query.filter_by(active=True).filter(
                        db.or_(
                            Article.supplier.ilike(f'%{supplier.name}%'),
                            Article.supplier.ilike(f'%{supplier_id}%'),
                            Article.supplier.ilike(f'%L-Shop%'),  # Hardcoded für bekanntes Problem
                            Article.supplier.ilike(f'%LF001%')   # Hardcoded für bekanntes Problem
                        )
                    )
                    
                    extended_articles = extended_query.order_by(Article.article_number).all()
                    print(f"API: Erweiterte Suche gefunden: {len(extended_articles)} Artikel")
                    
                    # Konvertiere erweiterte Ergebnisse
                    for article in extended_articles:
                        article_dict = {
                            'id': article.id,
                            'article_number': article.article_number,
                            'name': article.name,
                            'supplier': article.supplier,
                            'supplier_article_number': article.supplier_article_number,
                            'purchase_price': float(article.purchase_price_single) if article.purchase_price_single else 0,
                            'stock': article.stock or 0
                        }
                        articles_data.append(article_dict)
                
                # Wenn immer noch nichts gefunden, probiere JSON-Fallback
                if len(articles_data) == 0:
                    print("API: Kein Ergebnis in erweiterter Suche, versuche JSON-Fallback")
                    raise Exception("Extended search failed, trying JSON")
                
        except Exception as db_error:
            print(f"API: DB-Fehler oder keine Artikel in DB: {db_error}")
            print("API: Fallback auf JSON-Datei")
            
            # Fallback auf JSON
            ARTICLES_FILE = 'articles.json'
            if os.path.exists(ARTICLES_FILE):
                with open(ARTICLES_FILE, 'r', encoding='utf-8') as f:
                    json_articles = json.load(f)
                    
                # Lade auch Lieferanten für Namen-Matching
                suppliers_by_name = {}
                suppliers_by_id = {}
                SUPPLIERS_FILE = 'suppliers.json'
                if os.path.exists(SUPPLIERS_FILE):
                    with open(SUPPLIERS_FILE, 'r', encoding='utf-8') as f:
                        suppliers = json.load(f)
                        for sid, supplier in suppliers.items():
                            name = supplier.get('name', '')
                            suppliers_by_name[name] = sid
                            suppliers_by_id[sid] = name
                    
                # Konvertiere JSON-Artikel
                for aid, article in json_articles.items():
                    # Supplier-Filter für JSON
                    if supplier_id:
                        article_supplier = article.get('supplier', '')
                        # Vergleiche sowohl mit ID als auch mit Namen
                        supplier_name = suppliers_by_id.get(supplier_id, '')
                        if not (article_supplier == supplier_id or 
                               article_supplier == supplier_name or
                               supplier_id in article_supplier or
                               supplier_name in article_supplier):
                            continue
                    
                    # Filter wenn Suche
                    if search:
                        search_lower = search.lower()
                        if not any([
                            search_lower in (article.get('article_number', '') or '').lower(),
                            search_lower in (article.get('name', '') or '').lower(),
                            search_lower in (article.get('supplier_article_number', '') or '').lower()
                        ]):
                            continue
                    
                    article_dict = {
                        'id': aid,
                        'article_number': article.get('article_number', ''),
                        'name': article.get('name', ''),
                        'supplier': article.get('supplier', ''),
                        'supplier_article_number': article.get('supplier_article_number', ''),
                        'purchase_price': float(article.get('purchase_price', 0)),
                        'stock': int(article.get('stock', 0))
                    }
                    
                    # Füge supplier_id hinzu wenn möglich
                    if article_dict['supplier'] in suppliers_by_name:
                        article_dict['supplier_id'] = suppliers_by_name[article_dict['supplier']]
                    
                    articles_data.append(article_dict)
                    
                print(f"API: {len(articles_data)} Artikel aus JSON geladen")
        
        print(f"API: FINAL RESULT - {len(articles_data)} Artikel für Request")
        
        return jsonify({
            'success': True,
            'articles': articles_data,
            'count': len(articles_data),
            'source': 'database' if not ('JSON' in str(db_error) if 'db_error' in locals() else False) else 'json_fallback'
        })
        
    except Exception as e:
        print(f"API CRITICAL ERROR: {e}")
        
        # Log Fehler für Analyse
        with open('logs/error_log.txt', 'a', encoding='utf-8') as f:
            from datetime import datetime
            f.write(f"\n================================================================================\n")
            f.write(f"{datetime.now().strftime('%d.%m.%Y %H:%M')} - API_ARTICLES_ERROR\n")
            f.write(f"================================================================================\n")
            f.write(f"ERROR: {str(e)}\n")
            f.write(f"SUPPLIER_ID: {supplier_id}\n")
            f.write(f"SEARCH: {search}\n")
            f.write(f"SEVERITY: CRITICAL\n")
            f.write(f"STATUS: LOGGED\n")
            f.write(f"DEVELOPER: Hans Hahn\n")
        
        return jsonify({
            'success': False,
            'error': str(e),
            'articles': [],
            'count': 0
        }), 500

@api_bp.route('/articles/<article_id>')
@login_required
def get_article_details(article_id):
    """
    Hole Details eines spezifischen Artikels
    Erstellt von Hans Hahn - Alle Rechte vorbehalten
    """
    try:
        article = Article.query.get_or_404(article_id)
        
        article_data = {
            'id': article.id,
            'article_number': article.article_number,
            'name': article.name,
            'description': article.description,
            'supplier': article.supplier,
            'supplier_article_number': article.supplier_article_number,
            'purchase_price': float(article.purchase_price) if article.purchase_price else 0,
            'selling_price': float(article.selling_price) if article.selling_price else 0,
            'stock': article.stock or 0,
            'min_stock': article.min_stock or 0,
            'unit': article.unit,
            'category': article.category
        }
        
        # Multi-Lieferanten-Informationen
        if hasattr(article, 'article_suppliers'):
            article_data['suppliers'] = []
            for as_rel in article.article_suppliers.filter_by(active=True):
                article_data['suppliers'].append({
                    'supplier_id': as_rel.supplier_id,
                    'supplier_name': as_rel.supplier.name,
                    'supplier_article_number': as_rel.supplier_article_number,
                    'purchase_price': float(as_rel.purchase_price),
                    'minimum_order_quantity': as_rel.minimum_order_quantity,
                    'delivery_time_days': as_rel.delivery_time_days,
                    'preferred': as_rel.preferred
                })
        
        return jsonify({
            'success': True,
            'article': article_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =============================================================================
# NEUE API-ENDPUNKTE FÜR DEBUGGING
# Erstellt von Hans Hahn - Alle Rechte vorbehalten
# =============================================================================

@api_bp.route('/debug/suppliers')
@login_required
def debug_suppliers():
    """Debug-Endpunkt: Zeige alle Supplier"""
    try:
        suppliers = Supplier.query.all()
        suppliers_data = []
        
        for supplier in suppliers:
            supplier_data = {
                'id': supplier.id,
                'name': supplier.name,
                'active': supplier.active,
                'article_count': Article.query.filter_by(supplier=supplier.name).count()
            }
            suppliers_data.append(supplier_data)
        
        return jsonify({
            'success': True,
            'suppliers': suppliers_data,
            'count': len(suppliers_data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/debug/articles-suppliers')
@login_required
def debug_articles_suppliers():
    """Debug-Endpunkt: Zeige Artikel-Supplier Mapping"""
    try:
        # Gruppiere Artikel nach Supplier
        from sqlalchemy import func
        supplier_stats = db.session.query(
            Article.supplier,
            func.count(Article.id).label('count')
        ).filter_by(active=True).group_by(Article.supplier).all()
        
        mapping_data = []
        for supplier_name, count in supplier_stats:
            mapping_data.append({
                'supplier_name': supplier_name,
                'article_count': count
            })
        
        return jsonify({
            'success': True,
            'supplier_mappings': mapping_data,
            'total_groups': len(mapping_data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Neue API-Endpunkte für Kassensystem
@api_bp.route('/articles/search')
@login_required
def search_articles():
    """Artikel-Suche für Kassensystem"""
    try:
        query = request.args.get('q', '')
        
        # Basis-Query
        articles_query = Article.query.filter_by(active=True)
        
        # Suche nach Artikelnummer, Name oder Barcode
        if query:
            articles_query = articles_query.filter(
                db.or_(
                    Article.article_number.ilike(f'%{query}%'),
                    Article.name.ilike(f'%{query}%'),
                    Article.barcode.ilike(f'%{query}%') if hasattr(Article, 'barcode') else False
                )
            )
        
        articles = articles_query.limit(50).all()
        
        # Konvertiere zu JSON-Format für Kasse
        result = []
        for article in articles:
            result.append({
                'id': article.id,
                'article_number': article.article_number,
                'name': article.name,
                'price': float(article.price or 0),
                'stock': article.stock or 0,
                'stock_quantity': article.stock or 0,
                'barcode': getattr(article, 'barcode', None),
                'category': article.category,
                'color': getattr(article, 'color', None),
                'size': getattr(article, 'size', None),
                'material': getattr(article, 'material', None),
                'weight': getattr(article, 'weight', 0.5)
            })
        
        return jsonify(result)
        
    except Exception as e:
        print(f"API Error in search_articles: {e}")
        return jsonify([])

@api_bp.route('/top-selling-articles')
@login_required
def top_selling_articles():
    """Häufig verkaufte Artikel für Schnellzugriff"""
    try:
        limit = int(request.args.get('limit', 6))
        
        # TODO: Implementiere echte Verkaufsstatistik
        # Vorerst: Zeige die ersten aktiven Artikel
        articles = Article.query.filter_by(active=True).limit(limit).all()
        
        result = []
        for article in articles:
            result.append({
                'id': article.id,
                'article_number': article.article_number,
                'name': article.name,
                'price': float(article.price or 0),
                'stock_quantity': article.stock or 0
            })
        
        return jsonify(result)
        
    except Exception as e:
        print(f"API Error in top_selling_articles: {e}")
        return jsonify([])
