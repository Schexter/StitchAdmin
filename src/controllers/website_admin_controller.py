# -*- coding: utf-8 -*-
"""
Website-CMS Admin Controller
Bearbeitung aller Website-Inhalte (Hero, Leistungen, Galerie, Über uns, Prozess)

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from src.models.models import db
from src.models.website_content import WebsiteContent

website_admin_bp = Blueprint('website_admin', __name__, url_prefix='/admin/website')

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}


def _allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def _upload_image(file, subfolder='website'):
    """Bild hochladen und relativen Pfad zurückgeben"""
    if not file or not file.filename or not _allowed_image(file.filename):
        return None
    filename = secure_filename(file.filename)
    upload_dir = os.path.join(current_app.static_folder, 'uploads', subfolder)
    os.makedirs(upload_dir, exist_ok=True)
    file.save(os.path.join(upload_dir, filename))
    return f'uploads/{subfolder}/{filename}'


@website_admin_bp.route('/')
@login_required
def dashboard():
    """Visueller CMS Page-Builder mit allen Sektionen"""
    sections = {
        'hero': WebsiteContent.get_section('hero'),
        'services': WebsiteContent.get_section('services'),
        'gallery': WebsiteContent.get_section('gallery'),
        'about': WebsiteContent.get_section('about'),
        'process': WebsiteContent.get_section('process'),
        'shop': WebsiteContent.get_section('shop'),
        'meta': {**WebsiteContent.get_section('meta'), **WebsiteContent.get_section('footer')},
    }
    return render_template('website_admin/dashboard.html', sections=sections)


@website_admin_bp.route('/hero', methods=['GET', 'POST'])
@login_required
def edit_hero():
    """Hero-Sektion bearbeiten"""
    if request.method == 'POST':
        for key in ['title', 'subtitle', 'badge_text', 'cta_text', 'cta_link']:
            WebsiteContent.set('hero', key, request.form.get(key, ''), updated_by=current_user.username)

        if 'bg_image' in request.files:
            path = _upload_image(request.files['bg_image'])
            if path:
                WebsiteContent.set('hero', 'bg_image', path, 'image', updated_by=current_user.username)

        db.session.commit()
        flash('Hero-Sektion gespeichert.', 'success')
        return redirect(url_for('website_admin.edit_hero'))

    content = WebsiteContent.get_section('hero')
    return render_template('website_admin/edit_hero.html', content=content)


@website_admin_bp.route('/services', methods=['GET', 'POST'])
@login_required
def edit_services():
    """Leistungen bearbeiten"""
    if request.method == 'POST':
        WebsiteContent.set('services', 'section_title', request.form.get('section_title', ''), updated_by=current_user.username)
        WebsiteContent.set('services', 'section_subtitle', request.form.get('section_subtitle', ''), updated_by=current_user.username)

        for i in range(1, 9):
            title = request.form.get(f'card_{i}_title', '')
            desc = request.form.get(f'card_{i}_description', '')
            if title:
                WebsiteContent.set('services', f'card_{i}_title', title, sort_order=i*10, updated_by=current_user.username)
                WebsiteContent.set('services', f'card_{i}_description', desc, 'textarea', sort_order=i*10+1, updated_by=current_user.username)

                img_key = f'card_{i}_image'
                if img_key in request.files:
                    path = _upload_image(request.files[img_key])
                    if path:
                        WebsiteContent.set('services', img_key, path, 'image', sort_order=i*10+2, updated_by=current_user.username)
            else:
                # Leere Karte entfernen
                WebsiteContent.delete_key('services', f'card_{i}_title')
                WebsiteContent.delete_key('services', f'card_{i}_description')
                WebsiteContent.delete_key('services', f'card_{i}_image')

        db.session.commit()
        flash('Leistungen gespeichert.', 'success')
        return redirect(url_for('website_admin.edit_services'))

    content = WebsiteContent.get_section('services')
    return render_template('website_admin/edit_services.html', content=content)


@website_admin_bp.route('/gallery', methods=['GET', 'POST'])
@login_required
def edit_gallery():
    """Galerie bearbeiten"""
    if request.method == 'POST':
        WebsiteContent.set('gallery', 'section_title', request.form.get('section_title', ''), updated_by=current_user.username)
        WebsiteContent.set('gallery', 'section_subtitle', request.form.get('section_subtitle', ''), updated_by=current_user.username)

        for i in range(1, 13):
            alt = request.form.get(f'image_{i}_alt', '')
            img_key = f'image_{i}'

            if img_key in request.files:
                path = _upload_image(request.files[img_key])
                if path:
                    WebsiteContent.set('gallery', img_key, path, 'image', sort_order=i*10, updated_by=current_user.username)

            if alt:
                WebsiteContent.set('gallery', f'{img_key}_alt', alt, sort_order=i*10+1, updated_by=current_user.username)

            # Bild löschen
            if request.form.get(f'delete_{img_key}'):
                WebsiteContent.delete_key('gallery', img_key)
                WebsiteContent.delete_key('gallery', f'{img_key}_alt')

        db.session.commit()
        flash('Galerie gespeichert.', 'success')
        return redirect(url_for('website_admin.edit_gallery'))

    content = WebsiteContent.get_section('gallery')
    return render_template('website_admin/edit_gallery.html', content=content)


@website_admin_bp.route('/about', methods=['GET', 'POST'])
@login_required
def edit_about():
    """Über-uns bearbeiten"""
    if request.method == 'POST':
        WebsiteContent.set('about', 'title', request.form.get('title', ''), updated_by=current_user.username)
        WebsiteContent.set('about', 'text', request.form.get('text', ''), 'textarea', updated_by=current_user.username)

        if 'image' in request.files:
            path = _upload_image(request.files['image'])
            if path:
                WebsiteContent.set('about', 'image', path, 'image', updated_by=current_user.username)

        for i in range(1, 7):
            val = request.form.get(f'checklist_{i}', '')
            if val:
                WebsiteContent.set('about', f'checklist_{i}', val, sort_order=10+i, updated_by=current_user.username)
            else:
                WebsiteContent.delete_key('about', f'checklist_{i}')

        db.session.commit()
        flash('Über uns gespeichert.', 'success')
        return redirect(url_for('website_admin.edit_about'))

    content = WebsiteContent.get_section('about')
    return render_template('website_admin/edit_about.html', content=content)


@website_admin_bp.route('/process', methods=['GET', 'POST'])
@login_required
def edit_process():
    """Prozess-Schritte bearbeiten"""
    if request.method == 'POST':
        WebsiteContent.set('process', 'section_title', request.form.get('section_title', ''), updated_by=current_user.username)

        for i in range(1, 7):
            title = request.form.get(f'step_{i}_title', '')
            if title:
                WebsiteContent.set('process', f'step_{i}_title', title, sort_order=i*10, updated_by=current_user.username)
                WebsiteContent.set('process', f'step_{i}_description', request.form.get(f'step_{i}_description', ''), 'textarea', sort_order=i*10+1, updated_by=current_user.username)
                WebsiteContent.set('process', f'step_{i}_icon', request.form.get(f'step_{i}_icon', 'bi-circle'), 'icon', sort_order=i*10+2, updated_by=current_user.username)
            else:
                WebsiteContent.delete_key('process', f'step_{i}_title')
                WebsiteContent.delete_key('process', f'step_{i}_description')
                WebsiteContent.delete_key('process', f'step_{i}_icon')

        db.session.commit()
        flash('Prozess-Schritte gespeichert.', 'success')
        return redirect(url_for('website_admin.edit_process'))

    content = WebsiteContent.get_section('process')
    return render_template('website_admin/edit_process.html', content=content)


@website_admin_bp.route('/shop', methods=['GET', 'POST'])
@login_required
def edit_shop():
    """Shop-Inhalte bearbeiten (Hero, Sektionen, Texte)"""
    if request.method == 'POST':
        fields = [
            'badge_text', 'title', 'subtitle',
            'finishing_badge', 'finishing_title', 'finishing_subtitle',
            'categories_badge', 'categories_title', 'categories_subtitle',
            'cta_title', 'cta_subtitle',
        ]
        for key in fields:
            WebsiteContent.set('shop', key, request.form.get(key, ''), updated_by=current_user.username)

        db.session.commit()
        flash('Shop-Inhalte gespeichert.', 'success')
        return redirect(url_for('website_admin.edit_shop'))

    content = WebsiteContent.get_section('shop')
    return render_template('website_admin/edit_shop.html', content=content)


@website_admin_bp.route('/meta', methods=['GET', 'POST'])
@login_required
def edit_meta():
    """SEO/Meta bearbeiten"""
    if request.method == 'POST':
        WebsiteContent.set('meta', 'seo_title', request.form.get('seo_title', ''), updated_by=current_user.username)
        WebsiteContent.set('meta', 'meta_description', request.form.get('meta_description', ''), updated_by=current_user.username)
        WebsiteContent.set('footer', 'impressum_link', request.form.get('impressum_link', ''), updated_by=current_user.username)
        WebsiteContent.set('footer', 'datenschutz_link', request.form.get('datenschutz_link', ''), updated_by=current_user.username)
        db.session.commit()
        flash('Meta-Daten gespeichert.', 'success')
        return redirect(url_for('website_admin.edit_meta'))

    content = {**WebsiteContent.get_section('meta'), **WebsiteContent.get_section('footer')}
    return render_template('website_admin/edit_meta.html', content=content)
