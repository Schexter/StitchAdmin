# -*- coding: utf-8 -*-
"""
Shop-Admin Controller für StitchAdmin
Verwaltung von Shop-Artikeln, Veredelungsarten, Motiven und Kategorien

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename
from src.models.models import db, Article, Order
from src.models.shop import ShopCategory, ShopFinishingType, ShopDesignTemplate
from src.models.design import Design

shop_admin_bp = Blueprint('shop_admin', __name__, url_prefix='/admin/shop')


# ============================================================
# DASHBOARD
# ============================================================

@shop_admin_bp.route('/')
@login_required
def dashboard():
    """Shop-Admin Dashboard"""
    stats = {
        'active_articles': Article.query.filter_by(show_in_shop=True, active=True).count(),
        'categories': ShopCategory.query.filter_by(is_active=True).count(),
        'finishing_types': ShopFinishingType.query.filter_by(is_active=True).count(),
        'design_templates': ShopDesignTemplate.query.filter_by(is_active=True).count(),
        'shop_orders': Order.query.filter_by(source='shop').count(),
    }
    # Letzte Shop-Bestellungen
    recent_orders = Order.query.filter_by(source='shop').order_by(
        Order.created_at.desc()
    ).limit(5).all()

    return render_template('shop_admin/dashboard.html', stats=stats, recent_orders=recent_orders)


# ============================================================
# ARTIKEL
# ============================================================

@shop_admin_bp.route('/artikel')
@login_required
def artikel_list():
    """Artikel für Shop verwalten"""
    # Alle aktiven Artikel laden
    articles = Article.query.filter_by(active=True).order_by(Article.name).all()
    categories = ShopCategory.query.filter_by(is_active=True).order_by(ShopCategory.sort_order).all()
    return render_template('shop_admin/artikel_list.html', articles=articles, categories=categories)


@shop_admin_bp.route('/artikel/toggle/<article_id>', methods=['POST'])
@login_required
def artikel_toggle(article_id):
    """Artikel für Shop aktivieren/deaktivieren"""
    article = Article.query.get_or_404(article_id)
    article.show_in_shop = not article.show_in_shop
    db.session.commit()
    status = 'aktiviert' if article.show_in_shop else 'deaktiviert'
    flash(f'Artikel "{article.name}" im Shop {status}.', 'success')
    return redirect(url_for('shop_admin.artikel_list'))


@shop_admin_bp.route('/artikel/<article_id>/edit', methods=['GET', 'POST'])
@login_required
def artikel_edit(article_id):
    """Shop-Details eines Artikels bearbeiten"""
    article = Article.query.get_or_404(article_id)
    categories = ShopCategory.query.filter_by(is_active=True).order_by(ShopCategory.sort_order).all()

    if request.method == 'POST':
        article.show_in_shop = 'show_in_shop' in request.form
        article.shop_description = request.form.get('shop_description', '')
        article.shop_category_id = request.form.get('shop_category_id') or None
        article.shop_sort_order = int(request.form.get('shop_sort_order', 0))
        article.shop_min_quantity = int(request.form.get('shop_min_quantity', 1))

        # Bild-Upload
        image = request.files.get('shop_image')
        if image and image.filename:
            filename = secure_filename(image.filename)
            upload_dir = os.path.join(current_app.static_folder, 'uploads', 'articles')
            os.makedirs(upload_dir, exist_ok=True)
            # Eindeutiger Name mit Artikel-ID
            ext = os.path.splitext(filename)[1].lower()
            save_name = f"article_{article.id}{ext}"
            image.save(os.path.join(upload_dir, save_name))
            article.shop_image_path = f"uploads/articles/{save_name}"

        # Bild löschen
        if 'delete_image' in request.form and article.shop_image_path:
            img_path = os.path.join(current_app.static_folder, article.shop_image_path)
            if os.path.exists(img_path):
                os.remove(img_path)
            article.shop_image_path = None

        db.session.commit()
        flash(f'Shop-Details für "{article.name}" gespeichert.', 'success')
        return redirect(url_for('shop_admin.artikel_list'))

    return render_template('shop_admin/artikel_edit.html', article=article, categories=categories)


# ============================================================
# KATEGORIEN
# ============================================================

@shop_admin_bp.route('/kategorien')
@login_required
def kategorien():
    """Shop-Kategorien verwalten"""
    categories = ShopCategory.query.order_by(ShopCategory.sort_order, ShopCategory.name).all()
    return render_template('shop_admin/kategorien.html', categories=categories)


@shop_admin_bp.route('/kategorien/neu', methods=['POST'])
@login_required
def kategorie_create():
    """Neue Kategorie erstellen"""
    name = request.form.get('name', '').strip()
    if not name:
        flash('Name ist erforderlich.', 'danger')
        return redirect(url_for('shop_admin.kategorien'))

    # Slug generieren
    slug = name.lower().replace(' ', '-').replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')

    category = ShopCategory(
        name=name,
        slug=slug,
        description=request.form.get('description', ''),
        parent_id=request.form.get('parent_id') or None,
        sort_order=int(request.form.get('sort_order', 0))
    )
    db.session.add(category)
    db.session.commit()
    flash(f'Kategorie "{name}" erstellt.', 'success')
    return redirect(url_for('shop_admin.kategorien'))


@shop_admin_bp.route('/kategorien/<int:cat_id>/edit', methods=['POST'])
@login_required
def kategorie_edit(cat_id):
    """Kategorie bearbeiten"""
    category = ShopCategory.query.get_or_404(cat_id)
    category.name = request.form.get('name', category.name)
    category.description = request.form.get('description', '')
    category.sort_order = int(request.form.get('sort_order', 0))
    category.is_active = 'is_active' in request.form
    db.session.commit()
    flash(f'Kategorie "{category.name}" aktualisiert.', 'success')
    return redirect(url_for('shop_admin.kategorien'))


@shop_admin_bp.route('/kategorien/<int:cat_id>/delete', methods=['POST'])
@login_required
def kategorie_delete(cat_id):
    """Kategorie löschen"""
    category = ShopCategory.query.get_or_404(cat_id)
    name = category.name
    db.session.delete(category)
    db.session.commit()
    flash(f'Kategorie "{name}" gelöscht.', 'success')
    return redirect(url_for('shop_admin.kategorien'))


# ============================================================
# VEREDELUNGSARTEN
# ============================================================

@shop_admin_bp.route('/veredelung')
@login_required
def veredelung_list():
    """Veredelungsarten verwalten"""
    types = ShopFinishingType.query.order_by(ShopFinishingType.sort_order).all()
    return render_template('shop_admin/veredelung_list.html', types=types)


@shop_admin_bp.route('/veredelung/neu', methods=['GET', 'POST'])
@login_required
def veredelung_create():
    """Neue Veredelungsart erstellen"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        slug = name.lower().replace(' ', '-').replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')

        finishing = ShopFinishingType(
            name=name,
            slug=slug,
            finishing_type=request.form.get('finishing_type', 'stick'),
            description=request.form.get('description', ''),
            icon=request.form.get('icon', 'bi-brush'),
            setup_price=float(request.form.get('setup_price', 0)),
            price_per_piece=float(request.form.get('price_per_piece', 0)),
            price_per_1000_stitches=float(request.form.get('price_per_1000_stitches', 0)),
            min_quantity=int(request.form.get('min_quantity', 1)),
            max_colors=int(request.form.get('max_colors', 0)) or None,
            max_width_mm=int(request.form.get('max_width_mm', 0)) or None,
            max_height_mm=int(request.form.get('max_height_mm', 0)) or None,
            sort_order=int(request.form.get('sort_order', 0))
        )

        # Positionen als JSON
        positions = request.form.getlist('positions')
        if positions:
            finishing.set_available_positions(positions)

        db.session.add(finishing)
        db.session.commit()
        flash(f'Veredelungsart "{name}" erstellt.', 'success')
        return redirect(url_for('shop_admin.veredelung_list'))

    return render_template('shop_admin/veredelung_edit.html', finishing=None)


@shop_admin_bp.route('/veredelung/<int:ft_id>/edit', methods=['GET', 'POST'])
@login_required
def veredelung_edit(ft_id):
    """Veredelungsart bearbeiten"""
    finishing = ShopFinishingType.query.get_or_404(ft_id)

    if request.method == 'POST':
        finishing.name = request.form.get('name', finishing.name)
        finishing.finishing_type = request.form.get('finishing_type', finishing.finishing_type)
        finishing.description = request.form.get('description', '')
        finishing.icon = request.form.get('icon', 'bi-brush')
        finishing.setup_price = float(request.form.get('setup_price', 0))
        finishing.price_per_piece = float(request.form.get('price_per_piece', 0))
        finishing.price_per_1000_stitches = float(request.form.get('price_per_1000_stitches', 0))
        finishing.min_quantity = int(request.form.get('min_quantity', 1))
        finishing.max_colors = int(request.form.get('max_colors', 0)) or None
        finishing.max_width_mm = int(request.form.get('max_width_mm', 0)) or None
        finishing.max_height_mm = int(request.form.get('max_height_mm', 0)) or None
        finishing.sort_order = int(request.form.get('sort_order', 0))
        finishing.is_active = 'is_active' in request.form

        positions = request.form.getlist('positions')
        if positions:
            finishing.set_available_positions(positions)

        db.session.commit()
        flash(f'Veredelungsart "{finishing.name}" aktualisiert.', 'success')
        return redirect(url_for('shop_admin.veredelung_list'))

    return render_template('shop_admin/veredelung_edit.html', finishing=finishing)


# ============================================================
# MOTIVE / DESIGN-TEMPLATES
# ============================================================

@shop_admin_bp.route('/motive')
@login_required
def motive_list():
    """Shop-Motive verwalten"""
    templates = ShopDesignTemplate.query.order_by(ShopDesignTemplate.sort_order).all()
    return render_template('shop_admin/motive_list.html', templates=templates)


@shop_admin_bp.route('/motive/neu', methods=['GET', 'POST'])
@login_required
def motiv_create():
    """Neues Shop-Motiv erstellen"""
    if request.method == 'POST':
        template = ShopDesignTemplate(
            name=request.form.get('name', ''),
            description=request.form.get('description', ''),
            design_id=request.form.get('design_id') or None,
            category=request.form.get('category', 'motiv'),
            stitch_count=int(request.form.get('stitch_count', 0)) or None,
            color_count=int(request.form.get('color_count', 0)) or None,
            width_mm=int(request.form.get('width_mm', 0)) or None,
            height_mm=int(request.form.get('height_mm', 0)) or None,
            sort_order=int(request.form.get('sort_order', 0))
        )

        types = request.form.getlist('available_for_types')
        if types:
            template.set_available_for_types(types)

        db.session.add(template)
        db.session.commit()
        flash(f'Motiv "{template.name}" erstellt.', 'success')
        return redirect(url_for('shop_admin.motive_list'))

    # Designs aus Bibliothek für Verknüpfung laden
    designs = Design.query.filter_by(status='active').order_by(Design.name).all()
    return render_template('shop_admin/motiv_edit.html', template=None, designs=designs)


@shop_admin_bp.route('/motive/<int:tmpl_id>/edit', methods=['GET', 'POST'])
@login_required
def motiv_edit(tmpl_id):
    """Shop-Motiv bearbeiten"""
    template = ShopDesignTemplate.query.get_or_404(tmpl_id)

    if request.method == 'POST':
        template.name = request.form.get('name', template.name)
        template.description = request.form.get('description', '')
        template.design_id = request.form.get('design_id') or None
        template.category = request.form.get('category', 'motiv')
        template.stitch_count = int(request.form.get('stitch_count', 0)) or None
        template.color_count = int(request.form.get('color_count', 0)) or None
        template.width_mm = int(request.form.get('width_mm', 0)) or None
        template.height_mm = int(request.form.get('height_mm', 0)) or None
        template.sort_order = int(request.form.get('sort_order', 0))
        template.is_active = 'is_active' in request.form

        types = request.form.getlist('available_for_types')
        if types:
            template.set_available_for_types(types)

        db.session.commit()
        flash(f'Motiv "{template.name}" aktualisiert.', 'success')
        return redirect(url_for('shop_admin.motive_list'))

    designs = Design.query.filter_by(status='active').order_by(Design.name).all()
    return render_template('shop_admin/motiv_edit.html', template=template, designs=designs)


# ============================================================
# SHOP-BESTELLUNGEN
# ============================================================

@shop_admin_bp.route('/bestellungen')
@login_required
def bestellungen():
    """Shop-Bestellungen anzeigen"""
    orders = Order.query.filter_by(source='shop').order_by(
        Order.created_at.desc()
    ).all()
    return render_template('shop_admin/bestellungen.html', orders=orders)
