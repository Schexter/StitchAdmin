# -*- coding: utf-8 -*-
"""
Website-CMS Admin Controller
Bearbeitung aller Website-Inhalte (Hero, Leistungen, Galerie, Über uns, Prozess)

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
import subprocess
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from src.models.models import db
from src.models.website_content import WebsiteContent

logger = logging.getLogger(__name__)

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
    # Custom Domain aus WebsiteContent laden
    custom_domain = WebsiteContent.get('domain', 'custom_domain')
    return render_template('website_admin/dashboard.html', sections=sections, custom_domain=custom_domain)


@website_admin_bp.route('/custom-domain', methods=['POST'])
@login_required
def save_custom_domain():
    """Eigene Domain fuer Website speichern + Auto-SSL"""
    domain = request.form.get('custom_domain', '').strip().lower()
    # Domain bereinigen (https://, trailing slash entfernen)
    domain = domain.replace('https://', '').replace('http://', '').rstrip('/')

    if domain:
        WebsiteContent.set('domain', 'custom_domain', domain,
                          updated_by=current_user.username)

        # Auto-SSL Provisioning versuchen
        ssl_result = _provision_ssl(domain)
        if ssl_result:
            flash(f'Domain "{domain}" gespeichert und SSL-Zertifikat erstellt!', 'success')
        else:
            flash(f'Domain "{domain}" gespeichert. SSL konnte noch nicht erstellt werden - '
                  f'bitte erst den A-Eintrag bei Ihrem Domain-Anbieter auf unseren Server richten, '
                  f'dann "SSL erstellen" klicken.', 'warning')
    else:
        flash('Bitte geben Sie eine Domain ein.', 'warning')

    return redirect(url_for('website_admin.dashboard'))


@website_admin_bp.route('/custom-domain/provision-ssl', methods=['POST'])
@login_required
def provision_ssl():
    """SSL-Zertifikat fuer Custom Domain manuell anfordern"""
    domain = WebsiteContent.get('domain', 'custom_domain')
    if not domain:
        flash('Keine Custom Domain hinterlegt.', 'warning')
        return redirect(url_for('website_admin.dashboard'))

    if _provision_ssl(domain):
        flash(f'SSL-Zertifikat fuer {domain} erfolgreich erstellt!', 'success')
    else:
        flash(f'SSL-Erstellung fehlgeschlagen. Bitte pruefen Sie, dass der '
              f'A-Eintrag fuer {domain} auf unseren Server zeigt.', 'danger')

    return redirect(url_for('website_admin.dashboard'))


def _provision_ssl(domain):
    """SSL-Provisioning via Script ausfuehren"""
    script = '/opt/stitchadmin/provision-ssl.sh'
    if not os.path.exists(script):
        logger.warning(f'SSL-Script nicht gefunden: {script}')
        return False
    try:
        result = subprocess.run(
            ['sudo', script, domain],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            logger.info(f'SSL provisioniert fuer {domain}: {result.stdout}')
            return True
        else:
            logger.warning(f'SSL-Provisioning fehlgeschlagen fuer {domain}: {result.stderr}')
            return False
    except Exception as e:
        logger.error(f'SSL-Provisioning Fehler: {e}')
        return False


@website_admin_bp.route('/custom-domain/remove')
@login_required
def remove_custom_domain():
    """Eigene Domain entfernen"""
    entry = WebsiteContent.query.filter_by(section='domain', key='custom_domain').first()
    if entry:
        db.session.delete(entry)
        db.session.commit()
        flash('Domain-Zuordnung entfernt.', 'info')
    return redirect(url_for('website_admin.dashboard'))


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
    """Rechtliche Seiten & SEO bearbeiten"""
    if request.method == 'POST':
        WebsiteContent.set('meta', 'seo_title', request.form.get('seo_title', ''), updated_by=current_user.username)
        WebsiteContent.set('meta', 'meta_description', request.form.get('meta_description', ''), updated_by=current_user.username)
        WebsiteContent.set('footer', 'impressum_link', request.form.get('impressum_link', ''), updated_by=current_user.username)
        WebsiteContent.set('footer', 'datenschutz_link', request.form.get('datenschutz_link', ''), updated_by=current_user.username)
        WebsiteContent.set('footer', 'agb_text', request.form.get('agb_text', ''), updated_by=current_user.username)
        WebsiteContent.set('footer', 'widerruf_text', request.form.get('widerruf_text', ''), updated_by=current_user.username)
        db.session.commit()
        flash('Rechtliche Seiten gespeichert.', 'success')
        return redirect(url_for('website_admin.edit_meta'))

    content = {**WebsiteContent.get_section('meta'), **WebsiteContent.get_section('footer')}
    return render_template('website_admin/edit_meta.html', content=content)
