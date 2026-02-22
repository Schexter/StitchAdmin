# -*- coding: utf-8 -*-
"""
Kalender-Sync Controller
========================
Microsoft Graph OAuth + Kalender-Synchronisation

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta

from src.models import db
from src.models.calendar_sync import CalendarConnection, CalendarSyncMapping

import logging
logger = logging.getLogger(__name__)

calendar_sync_bp = Blueprint('calendar_sync', __name__, url_prefix='/calendar-sync')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Nur Administratoren haben Zugriff.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@calendar_sync_bp.route('/')
@login_required
@admin_required
def index():
    """Kalender-Sync Status"""
    from src.services.calendar_sync_service import MicrosoftGraphCalendarService

    connections = CalendarConnection.query.filter_by(user_id=current_user.id).all()
    service = MicrosoftGraphCalendarService()

    return render_template('calendar_sync/connect.html',
                         connections=connections,
                         is_configured=service.is_configured())


@calendar_sync_bp.route('/connect/microsoft')
@login_required
@admin_required
def connect_microsoft():
    """OAuth starten - Redirect zu Microsoft"""
    from src.services.calendar_sync_service import MicrosoftGraphCalendarService

    service = MicrosoftGraphCalendarService()
    if not service.is_configured():
        flash('Microsoft Graph ist nicht konfiguriert. Bitte Client-ID und Secret in den Einstellungen hinterlegen.', 'warning')
        return redirect(url_for('calendar_sync.index'))

    redirect_uri = url_for('calendar_sync.callback_microsoft', _external=True)
    auth_url = service.get_auth_url(redirect_uri)

    return redirect(auth_url)


@calendar_sync_bp.route('/callback/microsoft')
def callback_microsoft():
    """OAuth Callback - Token speichern"""
    from src.services.calendar_sync_service import MicrosoftGraphCalendarService

    code = request.args.get('code')
    error = request.args.get('error')

    if error:
        flash(f'Microsoft-Verbindung fehlgeschlagen: {error}', 'danger')
        return redirect(url_for('calendar_sync.index'))

    if not code:
        flash('Kein Authorization-Code erhalten.', 'danger')
        return redirect(url_for('calendar_sync.index'))

    service = MicrosoftGraphCalendarService()
    redirect_uri = url_for('calendar_sync.callback_microsoft', _external=True)
    tokens = service.exchange_code(code, redirect_uri)

    if not tokens:
        flash('Token-Austausch fehlgeschlagen.', 'danger')
        return redirect(url_for('calendar_sync.index'))

    # Verbindung speichern
    connection = CalendarConnection(
        provider='microsoft',
        user_id=current_user.id if current_user.is_authenticated else None,
        access_token_encrypted=tokens['access_token'],
        refresh_token_encrypted=tokens.get('refresh_token', ''),
        token_expiry=datetime.utcnow() + timedelta(seconds=tokens.get('expires_in', 3600)),
        sync_direction='bidirectional',
        is_active=True,
    )
    db.session.add(connection)
    db.session.commit()

    # Kalender auflisten
    calendars = service.list_calendars(connection)
    if calendars:
        connection.calendar_id = calendars[0]['id']
        connection.calendar_name = calendars[0].get('name', 'Kalender')
        db.session.commit()

    flash('Microsoft-Kalender erfolgreich verbunden!', 'success')
    return redirect(url_for('calendar_sync.index'))


@calendar_sync_bp.route('/<int:conn_id>/sync', methods=['POST'])
@login_required
@admin_required
def sync(conn_id):
    """Manueller Sync"""
    from src.services.calendar_sync_service import MicrosoftGraphCalendarService

    service = MicrosoftGraphCalendarService()
    result = service.sync_to_outlook(conn_id)

    if 'error' in result:
        flash(f'Sync-Fehler: {result["error"]}', 'danger')
    else:
        flash(f'Sync erfolgreich: {result["created"]} erstellt, {result["updated"]} aktualisiert.', 'success')

    return redirect(url_for('calendar_sync.index'))


@calendar_sync_bp.route('/<int:conn_id>/disconnect', methods=['POST'])
@login_required
@admin_required
def disconnect(conn_id):
    """Verbindung trennen"""
    connection = CalendarConnection.query.get_or_404(conn_id)
    connection.is_active = False
    connection.access_token_encrypted = None
    connection.refresh_token_encrypted = None
    db.session.commit()
    flash('Kalender-Verbindung getrennt.', 'success')
    return redirect(url_for('calendar_sync.index'))


@calendar_sync_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    """Sync-Einstellungen"""
    connections = CalendarConnection.query.filter_by(user_id=current_user.id, is_active=True).all()

    if request.method == 'POST':
        conn_id = request.form.get('connection_id', type=int)
        conn = CalendarConnection.query.get(conn_id)
        if conn:
            conn.sync_direction = request.form.get('sync_direction', 'bidirectional')
            conn.calendar_id = request.form.get('calendar_id', conn.calendar_id)
            db.session.commit()
            flash('Einstellungen gespeichert.', 'success')

    return render_template('calendar_sync/settings.html', connections=connections)
