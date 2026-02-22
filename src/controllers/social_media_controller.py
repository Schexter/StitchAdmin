# -*- coding: utf-8 -*-
"""
Social Media Controller
=======================
Facebook + Instagram: Konten verbinden, Posts erstellen, Kalender

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime

from src.models import db
from src.models.social_media import SocialMediaAccount, SocialMediaPost

import logging
logger = logging.getLogger(__name__)

social_media_bp = Blueprint('social_media', __name__, url_prefix='/social-media')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Nur Administratoren haben Zugriff.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@social_media_bp.route('/')
@login_required
@admin_required
def index():
    """Social Media Dashboard"""
    accounts = SocialMediaAccount.query.filter_by(is_active=True).all()
    scheduled = SocialMediaPost.query.filter_by(status='scheduled').order_by(SocialMediaPost.scheduled_at).limit(10).all()
    recent = SocialMediaPost.query.filter_by(status='published').order_by(SocialMediaPost.published_at.desc()).limit(10).all()
    failed = SocialMediaPost.query.filter_by(status='failed').count()

    return render_template('social_media/index.html',
                         accounts=accounts,
                         scheduled=scheduled,
                         recent=recent,
                         failed_count=failed)


@social_media_bp.route('/accounts')
@login_required
@admin_required
def accounts():
    """Account-Liste"""
    from src.services.social_media_service import MetaGraphService

    all_accounts = SocialMediaAccount.query.order_by(SocialMediaAccount.platform).all()
    service = MetaGraphService()

    return render_template('social_media/accounts.html',
                         accounts=all_accounts,
                         is_configured=service.is_configured())


@social_media_bp.route('/connect/facebook')
@login_required
@admin_required
def connect_facebook():
    """Facebook OAuth starten"""
    from src.services.social_media_service import MetaGraphService

    service = MetaGraphService()
    if not service.is_configured():
        flash('Meta App nicht konfiguriert. Bitte App-ID und Secret in den Einstellungen hinterlegen.', 'warning')
        return redirect(url_for('social_media.accounts'))

    redirect_uri = url_for('social_media.callback_facebook', _external=True)
    auth_url = service.get_auth_url(redirect_uri)
    return redirect(auth_url)


@social_media_bp.route('/callback/facebook')
def callback_facebook():
    """Facebook OAuth Callback"""
    from src.services.social_media_service import MetaGraphService

    code = request.args.get('code')
    error = request.args.get('error')

    if error:
        flash(f'Facebook-Verbindung abgelehnt: {error}', 'danger')
        return redirect(url_for('social_media.accounts'))

    if not code:
        flash('Kein Authorization-Code erhalten.', 'danger')
        return redirect(url_for('social_media.accounts'))

    service = MetaGraphService()
    redirect_uri = url_for('social_media.callback_facebook', _external=True)

    # Short-lived Token
    tokens = service.exchange_code(code, redirect_uri)
    if not tokens:
        flash('Token-Austausch fehlgeschlagen.', 'danger')
        return redirect(url_for('social_media.accounts'))

    short_token = tokens.get('access_token')

    # Long-lived Token
    long_data = service.exchange_for_long_token(short_token)
    user_token = long_data.get('access_token', short_token) if long_data else short_token

    # Seiten abrufen
    pages = service.get_pages(user_token)

    if not pages:
        flash('Keine Facebook-Seiten gefunden. Stellen Sie sicher, dass Sie eine Seite verwalten.', 'warning')
        return redirect(url_for('social_media.accounts'))

    # Jede Seite als Account speichern
    for page in pages:
        existing = SocialMediaAccount.query.filter_by(
            platform='facebook', page_id=page['id']
        ).first()

        if existing:
            existing.access_token_encrypted = page.get('access_token', user_token)
            existing.account_name = page.get('name', 'Facebook-Seite')
            existing.is_active = True
        else:
            account = SocialMediaAccount(
                platform='facebook',
                account_name=page.get('name', 'Facebook-Seite'),
                page_id=page['id'],
                access_token_encrypted=page.get('access_token', user_token),
                connected_by=current_user.id if current_user.is_authenticated else None,
            )
            db.session.add(account)

        # Instagram Business Account?
        ig_data = page.get('instagram_business_account')
        if ig_data:
            ig_id = ig_data.get('id')
            ig_existing = SocialMediaAccount.query.filter_by(
                platform='instagram', page_id=ig_id
            ).first()

            if not ig_existing:
                ig_account = SocialMediaAccount(
                    platform='instagram',
                    account_name=f'{page.get("name", "Instagram")} (Instagram)',
                    page_id=ig_id,
                    access_token_encrypted=page.get('access_token', user_token),
                    connected_by=current_user.id if current_user.is_authenticated else None,
                )
                db.session.add(ig_account)

    db.session.commit()
    flash(f'{len(pages)} Facebook-Seite(n) verbunden!', 'success')
    return redirect(url_for('social_media.accounts'))


@social_media_bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_post():
    """Post erstellen"""
    accounts = SocialMediaAccount.query.filter_by(is_active=True).all()

    if request.method == 'POST':
        account_id = request.form.get('account_id', type=int)
        text = request.form.get('text', '')
        hashtags = request.form.get('hashtags', '')
        link_url = request.form.get('link_url', '')
        scheduled_str = request.form.get('scheduled_at', '')
        action = request.form.get('action', 'draft')  # draft, schedule, publish

        post = SocialMediaPost(
            account_id=account_id,
            text=text,
            hashtags=hashtags,
            link_url=link_url if link_url else None,
            source_type='manual',
            created_by=current_user.id,
        )

        # Bild hochladen
        image = request.files.get('image')
        if image and image.filename:
            import os
            upload_dir = os.path.join('src', 'static', 'uploads', 'social')
            os.makedirs(upload_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{timestamp}_{image.filename}'
            filepath = os.path.join(upload_dir, filename)
            image.save(filepath)
            post.image_path = filepath

        if action == 'publish':
            # Sofort veroeffentlichen
            post.status = 'scheduled'
            db.session.add(post)
            db.session.commit()

            from src.services.social_media_service import MetaGraphService
            service = MetaGraphService()
            if service.publish_post(post):
                flash('Post veroeffentlicht!', 'success')
            else:
                flash(f'Post fehlgeschlagen: {post.error_message}', 'danger')

        elif action == 'schedule' and scheduled_str:
            post.scheduled_at = datetime.strptime(scheduled_str, '%Y-%m-%dT%H:%M')
            post.status = 'scheduled'
            db.session.add(post)
            db.session.commit()

            from src.services.social_media_service import MetaGraphService
            service = MetaGraphService()
            service.schedule_post(post.id)
            flash(f'Post geplant fuer {post.scheduled_at.strftime("%d.%m.%Y %H:%M")}', 'success')

        else:
            post.status = 'draft'
            db.session.add(post)
            db.session.commit()
            flash('Entwurf gespeichert.', 'success')

        return redirect(url_for('social_media.index'))

    return render_template('social_media/create_post.html', accounts=accounts)


@social_media_bp.route('/from-article/<int:article_id>', methods=['POST'])
@login_required
@admin_required
def from_article(article_id):
    """Auto-Post aus Artikel"""
    from src.services.social_media_service import AutoPostService

    account_ids = request.form.getlist('account_ids', type=int)
    custom_text = request.form.get('custom_text', '')

    service = AutoPostService()
    posts = service.create_from_article(article_id, account_ids, custom_text or None)

    if posts:
        flash(f'{len(posts)} Post-Entwuerfe erstellt.', 'success')
    else:
        flash('Keine Posts erstellt.', 'warning')

    return redirect(url_for('social_media.index'))


@social_media_bp.route('/calendar')
@login_required
@admin_required
def calendar():
    """Post-Kalender"""
    posts = SocialMediaPost.query.filter(
        SocialMediaPost.status.in_(['scheduled', 'published'])
    ).order_by(SocialMediaPost.scheduled_at).all()

    return render_template('social_media/calendar.html', posts=posts)


@social_media_bp.route('/post/<int:post_id>')
@login_required
@admin_required
def post_detail(post_id):
    """Post-Detail"""
    post = SocialMediaPost.query.get_or_404(post_id)
    return render_template('social_media/post_detail.html', post=post)


@social_media_bp.route('/post/<int:post_id>/publish', methods=['POST'])
@login_required
@admin_required
def publish_post(post_id):
    """Sofort veroeffentlichen"""
    from src.services.social_media_service import MetaGraphService

    post = SocialMediaPost.query.get_or_404(post_id)
    service = MetaGraphService()

    if service.publish_post(post):
        flash('Post veroeffentlicht!', 'success')
    else:
        flash(f'Fehler: {post.error_message}', 'danger')

    return redirect(url_for('social_media.post_detail', post_id=post_id))


@social_media_bp.route('/post/<int:post_id>/cancel', methods=['POST'])
@login_required
@admin_required
def cancel_post(post_id):
    """Geplanten Post abbrechen"""
    post = SocialMediaPost.query.get_or_404(post_id)

    if post.status == 'scheduled':
        post.status = 'draft'
        db.session.commit()

        # Scheduler-Job entfernen
        try:
            from src.services.scheduler_service import remove_job
            remove_job(f'social_post_{post_id}')
        except Exception:
            pass

        flash('Post abgebrochen.', 'info')
    else:
        flash('Nur geplante Posts koennen abgebrochen werden.', 'warning')

    return redirect(url_for('social_media.post_detail', post_id=post_id))
