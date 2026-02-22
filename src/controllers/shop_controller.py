# -*- coding: utf-8 -*-
"""
Öffentlicher Shop Controller für StitchAdmin
Textil-Katalog, Konfigurator, Warenkorb und Checkout (kein Login nötig)

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from src.models.models import db, Article, Order
from src.models.shop import ShopCategory, ShopFinishingType, ShopDesignTemplate
from src.models.design import Design
from src.models.website_content import WebsiteContent
from src.services.shop_service import (
    get_cart, add_to_cart, update_cart_item, remove_from_cart,
    clear_cart, get_cart_count, calculate_item_total, calculate_cart_total,
    calculate_finishing_price, create_order_from_cart, get_order_by_tracking_token
)

shop_bp = Blueprint('shop', __name__, url_prefix='/shop')


def _get_shop_content():
    """CMS-Inhalte für den Shop laden"""
    try:
        return WebsiteContent.get_section('shop')
    except Exception:
        return {}


# ============================================================
# SHOP-STARTSEITE / KONFIGURATOR
# ============================================================

@shop_bp.route('/')
def index():
    """Shop-Startseite mit Konfigurator-Übersicht"""
    finishing_types = ShopFinishingType.query.filter_by(is_active=True).order_by(
        ShopFinishingType.sort_order
    ).all()
    categories = ShopCategory.query.filter_by(is_active=True, parent_id=None).order_by(
        ShopCategory.sort_order
    ).all()

    # Company-Daten für Branding
    company = None
    try:
        from src.models.company_settings import CompanySettings
        company = CompanySettings.get_settings()
    except Exception:
        pass

    return render_template('shop/index.html',
                         finishing_types=finishing_types,
                         categories=categories,
                         company=company,
                         content=_get_shop_content(),
                         cart_count=get_cart_count())


# ============================================================
# TEXTIL-KATALOG
# ============================================================

@shop_bp.route('/textilien')
def textilien():
    """Textil-Katalog mit Filtern"""
    category_id = request.args.get('kategorie', type=int)

    query = Article.query.filter_by(show_in_shop=True, active=True)
    if category_id:
        query = query.filter_by(shop_category_id=category_id)

    articles = query.order_by(Article.shop_sort_order, Article.name).all()
    categories = ShopCategory.query.filter_by(is_active=True).order_by(ShopCategory.sort_order).all()

    company = None
    try:
        from src.models.company_settings import CompanySettings
        company = CompanySettings.get_settings()
    except Exception:
        pass

    return render_template('shop/textilien.html',
                         articles=articles,
                         categories=categories,
                         selected_category=category_id,
                         company=company,
                         cart_count=get_cart_count())


@shop_bp.route('/textilien/<article_id>')
def artikel_detail(article_id):
    """Artikel-Detailseite mit Varianten"""
    article = Article.query.filter_by(id=article_id, show_in_shop=True, active=True).first_or_404()
    variants = article.variants.filter_by(active=True).all() if article.has_variants else []
    finishing_types = ShopFinishingType.query.filter_by(is_active=True).order_by(ShopFinishingType.sort_order).all()

    company = None
    try:
        from src.models.company_settings import CompanySettings
        company = CompanySettings.get_settings()
    except Exception:
        pass

    return render_template('shop/artikel_detail.html',
                         article=article,
                         variants=variants,
                         finishing_types=finishing_types,
                         company=company,
                         cart_count=get_cart_count())


# ============================================================
# MOTIVE
# ============================================================

@shop_bp.route('/motive')
def motive():
    """Design-Galerie für den Konfigurator"""
    category = request.args.get('kategorie')
    query = ShopDesignTemplate.query.filter_by(is_active=True)
    if category:
        query = query.filter_by(category=category)
    templates = query.order_by(ShopDesignTemplate.sort_order).all()

    company = None
    try:
        from src.models.company_settings import CompanySettings
        company = CompanySettings.get_settings()
    except Exception:
        pass

    return render_template('shop/motive.html',
                         templates=templates,
                         selected_category=category,
                         company=company,
                         cart_count=get_cart_count())


# ============================================================
# API ENDPOINTS (AJAX)
# ============================================================

@shop_bp.route('/api/varianten/<article_id>')
def api_varianten(article_id):
    """Varianten eines Artikels laden (AJAX)"""
    article = Article.query.get_or_404(article_id)
    variants = []
    if article.has_variants:
        for v in article.variants.filter_by(active=True).all():
            variants.append({
                'id': v.id,
                'color': v.color,
                'size': v.size,
                'price': v.single_price or article.price or 0,
                'stock': v.stock or 0
            })
    return jsonify(variants)


@shop_bp.route('/api/preis', methods=['POST'])
def api_preis():
    """Preis berechnen (AJAX)"""
    data = request.get_json()
    finishing_type_id = data.get('finishing_type_id')
    stitch_count = data.get('stitch_count', 0)
    quantity = data.get('quantity', 1)
    width_mm = data.get('width_mm')
    height_mm = data.get('height_mm')

    finishing_type = ShopFinishingType.query.get(finishing_type_id)
    if not finishing_type:
        return jsonify({'error': 'Veredelungsart nicht gefunden'}), 404

    result = calculate_finishing_price(
        finishing_type, stitch_count, quantity, width_mm, height_mm
    )
    return jsonify(result)


@shop_bp.route('/api/warenkorb', methods=['POST'])
def api_warenkorb_add():
    """Artikel zum Warenkorb hinzufügen (AJAX)"""
    data = request.get_json()

    # Artikel validieren
    article = Article.query.get(data.get('article_id'))
    if not article or not article.show_in_shop:
        return jsonify({'error': 'Artikel nicht verfügbar'}), 404

    item = {
        'article_id': article.id,
        'article_name': article.name,
        'variant_id': data.get('variant_id'),
        'variant_info': data.get('variant_info', ''),
        'quantity': max(1, int(data.get('quantity', 1))),
        'unit_price': float(data.get('unit_price', article.price or 0)),
        'finishings': data.get('finishings', []),
        'notes': data.get('notes', '')
    }

    count = add_to_cart(item)
    return jsonify({'success': True, 'cart_count': count})


@shop_bp.route('/api/warenkorb/<int:index>', methods=['PUT'])
def api_warenkorb_update(index):
    """Warenkorb-Artikel aktualisieren (AJAX)"""
    data = request.get_json()
    quantity = int(data.get('quantity', 1))
    cart = update_cart_item(index, quantity)
    totals = calculate_cart_total()
    return jsonify({'success': True, 'cart': cart, 'totals': totals})


@shop_bp.route('/api/warenkorb/<int:index>', methods=['DELETE'])
def api_warenkorb_delete(index):
    """Warenkorb-Artikel entfernen (AJAX)"""
    cart = remove_from_cart(index)
    totals = calculate_cart_total()
    return jsonify({'success': True, 'cart': cart, 'totals': totals})


# ============================================================
# WARENKORB
# ============================================================

@shop_bp.route('/warenkorb')
def warenkorb():
    """Warenkorb-Seite"""
    cart = get_cart()
    totals = calculate_cart_total()

    # Artikeldaten nachladen
    cart_items = []
    for item in cart:
        article = Article.query.get(item.get('article_id'))
        cart_items.append({
            **item,
            'article': article,
            'item_total': calculate_item_total(item)
        })

    company = None
    try:
        from src.models.company_settings import CompanySettings
        company = CompanySettings.get_settings()
    except Exception:
        pass

    return render_template('shop/warenkorb.html',
                         cart_items=cart_items,
                         totals=totals,
                         company=company,
                         cart_count=get_cart_count())


# ============================================================
# CHECKOUT
# ============================================================

@shop_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    """Checkout-Formular und Bestellaufgabe"""
    cart = get_cart()
    if not cart:
        flash('Ihr Warenkorb ist leer.', 'info')
        return redirect(url_for('shop.index'))

    if request.method == 'POST':
        customer_data = {
            'first_name': request.form.get('first_name', ''),
            'last_name': request.form.get('last_name', ''),
            'email': request.form.get('email', ''),
            'phone': request.form.get('phone', ''),
            'company_name': request.form.get('company_name', ''),
            'street': request.form.get('street', ''),
            'house_number': request.form.get('house_number', ''),
            'postal_code': request.form.get('postal_code', ''),
            'city': request.form.get('city', ''),
            'notes': request.form.get('notes', '')
        }

        # Validierung
        if not customer_data['email']:
            flash('Bitte geben Sie eine E-Mail-Adresse an.', 'danger')
            return render_template('shop/checkout.html',
                                 cart=cart,
                                 totals=calculate_cart_total(),
                                 form_data=customer_data,
                                 company=None,
                                 cart_count=get_cart_count())

        try:
            order = create_order_from_cart(customer_data)
            return redirect(url_for('shop.bestaetigung', token=order.tracking_token))
        except Exception as e:
            flash(f'Fehler bei der Bestellung: {str(e)}', 'danger')

    totals = calculate_cart_total()

    company = None
    try:
        from src.models.company_settings import CompanySettings
        company = CompanySettings.get_settings()
    except Exception:
        pass

    return render_template('shop/checkout.html',
                         cart=cart,
                         totals=totals,
                         form_data={},
                         company=company,
                         cart_count=get_cart_count())


# ============================================================
# BESTÄTIGUNG & STATUS
# ============================================================

@shop_bp.route('/bestaetigung/<token>')
def bestaetigung(token):
    """Bestellbestätigung"""
    order = get_order_by_tracking_token(token)
    if not order:
        flash('Bestellung nicht gefunden.', 'danger')
        return redirect(url_for('shop.index'))

    company = None
    try:
        from src.models.company_settings import CompanySettings
        company = CompanySettings.get_settings()
    except Exception:
        pass

    return render_template('shop/bestaetigung.html',
                         order=order,
                         company=company,
                         cart_count=0)


@shop_bp.route('/status/<token>')
def status(token):
    """Auftragsstatus prüfen"""
    order = get_order_by_tracking_token(token)
    if not order:
        flash('Bestellung nicht gefunden.', 'danger')
        return redirect(url_for('shop.index'))

    company = None
    try:
        from src.models.company_settings import CompanySettings
        company = CompanySettings.get_settings()
    except Exception:
        pass

    return render_template('shop/bestaetigung.html',
                         order=order,
                         company=company,
                         cart_count=0)
