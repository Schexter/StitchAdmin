from flask import Blueprint, jsonify, request
from flask_login import login_required
from src.models.models import Article, Supplier, db
import logging

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/articles')
@login_required
def get_articles():
    """API-Endpunkt für Artikelsuche mit optionalem Lieferantenfilter"""
    try:
        supplier_id = request.args.get('supplier_id')
        search = request.args.get('search', '')

        query = Article.query.filter_by(active=True)

        # Supplier-Filter
        if supplier_id:
            supplier = Supplier.query.get(supplier_id)
            if supplier:
                query = query.filter(
                    db.or_(
                        Article.supplier == supplier.name,
                        Article.supplier == supplier_id,
                        Article.supplier_id == supplier_id if hasattr(Article, 'supplier_id') else False
                    )
                )

        # Suchfilter
        if search:
            query = query.filter(
                db.or_(
                    Article.article_number.ilike(f'%{search}%'),
                    Article.name.ilike(f'%{search}%'),
                    Article.supplier_article_number.ilike(f'%{search}%')
                )
            )

        articles = query.order_by(Article.article_number).all()

        # Konvertiere zu JSON
        articles_data = []
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

            # Multi-Lieferanten-Unterstützung
            if hasattr(article, 'article_suppliers'):
                article_dict['suppliers'] = [
                    as_rel.supplier_id for as_rel in article.article_suppliers.filter_by(active=True)
                ]
                if supplier_id:
                    supplier_rel = article.article_suppliers.filter_by(
                        supplier_id=supplier_id, active=True
                    ).first()
                    if supplier_rel:
                        article_dict['purchase_price'] = float(supplier_rel.purchase_price)
                        article_dict['supplier_article_number'] = supplier_rel.supplier_article_number

            articles_data.append(article_dict)

        return jsonify({
            'success': True,
            'articles': articles_data,
            'count': len(articles_data),
            'source': 'database'
        })

    except Exception as e:
        logger.error(f"API articles error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'articles': [],
            'count': 0
        }), 500


@api_bp.route('/articles/<article_id>')
@login_required
def get_article_details(article_id):
    """Hole Details eines spezifischen Artikels"""
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


@api_bp.route('/articles/search')
@login_required
def search_articles():
    """Artikel-Suche für Kassensystem"""
    try:
        query = request.args.get('q', '')
        articles_query = Article.query.filter_by(active=True)

        if query:
            articles_query = articles_query.filter(
                db.or_(
                    Article.article_number.ilike(f'%{query}%'),
                    Article.name.ilike(f'%{query}%'),
                    Article.barcode.ilike(f'%{query}%') if hasattr(Article, 'barcode') else False
                )
            )

        articles = articles_query.limit(50).all()

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
        logger.error(f"search_articles error: {e}")
        return jsonify([])


@api_bp.route('/top-selling-articles')
@login_required
def top_selling_articles():
    """Häufig verkaufte Artikel für Schnellzugriff"""
    try:
        limit = int(request.args.get('limit', 6))
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
        logger.error(f"top_selling_articles error: {e}")
        return jsonify([])
