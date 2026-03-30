"""
Auth Controller - Authentifizierung und Benutzeranmeldung
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, g
from flask_login import login_user, logout_user, login_required, current_user
from src.models import db, User, ActivityLog
from src.utils.activity_logger import log_activity
from urllib.parse import urlparse, urljoin
from datetime import datetime, timedelta
from collections import defaultdict
import threading
import logging

logger = logging.getLogger(__name__)

# Blueprint erstellen
auth_bp = Blueprint('auth', __name__)

# Einfaches In-Memory Rate-Limiting (IP-basiert)
_login_attempts = defaultdict(list)
_lock = threading.Lock()
MAX_ATTEMPTS = 10
LOCKOUT_MINUTES = 15

def _is_rate_limited(ip: str) -> bool:
    """Prüft ob IP zu viele Login-Versuche hatte."""
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=LOCKOUT_MINUTES)
    with _lock:
        _login_attempts[ip] = [t for t in _login_attempts[ip] if t > cutoff]
        if len(_login_attempts[ip]) >= MAX_ATTEMPTS:
            return True
        _login_attempts[ip].append(now)
    return False

def _is_safe_url(target: str) -> bool:
    """Verhindert Open-Redirect auf externe Seiten."""
    if not target:
        return False
    ref = urlparse(request.host_url)
    test = urlparse(urljoin(request.host_url, target))
    return test.scheme in ('http', 'https') and ref.netloc == test.netloc

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login-Seite und -Verarbeitung"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        ip = request.remote_addr
        if _is_rate_limited(ip):
            flash(f'Zu viele Versuche. Bitte {LOCKOUT_MINUTES} Minuten warten.', 'danger')
            return render_template('login.html')

        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False) == 'on'

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('Ihr Konto ist deaktiviert. Bitte kontaktieren Sie den Administrator.', 'danger')
                log_activity('login_failed', f'Deaktiviertes Konto: {username}', username)
                return render_template('login.html')

            # Tenant-Scoping: Auf Subdomain nur Tenant-Mitglieder einloggen
            tenant = g.get('current_tenant')
            if tenant and not user.is_system_admin:
                try:
                    from src.models.tenant import UserTenant
                    membership = UserTenant.query.filter_by(
                        user_id=user.id, tenant_id=tenant.id, is_active=True
                    ).first()
                    if not membership:
                        flash('Sie haben keinen Zugang zu diesem Bereich.', 'danger')
                        log_activity('login_failed', f'Kein Tenant-Zugang: {username} fuer {tenant.name}', username)
                        return render_template('login.html')
                except Exception as e:
                    logger.warning(f"Tenant-Check fehlgeschlagen: {e}")

            # 2FA aktiv? → Zwischenschritt
            if user.totp_enabled:
                session['_2fa_user_id'] = user.id
                session['_2fa_remember'] = remember
                session['_2fa_next'] = request.args.get('next', '')
                return redirect(url_for('auth.verify_2fa'))

            # Kein 2FA → direkt einloggen
            login_user(user, remember=remember)
            user.last_login = db.session.query(db.func.now()).scalar()
            db.session.commit()
            log_activity('login', 'Erfolgreiche Anmeldung', user.username)

            next_page = request.args.get('next')
            if next_page and _is_safe_url(next_page):
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Ungültiger Benutzername oder Passwort', 'danger')
            log_activity('login_failed', f'Fehlgeschlagene Anmeldung für: {username}', username)

    return render_template('login.html')

@auth_bp.route('/verify-2fa', methods=['GET', 'POST'])
def verify_2fa():
    """2FA-Code Eingabe nach Passwort-Pruefung"""
    user_id = session.get('_2fa_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user:
        session.pop('_2fa_user_id', None)
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip().replace(' ', '')
        remember = session.get('_2fa_remember', False)
        next_page = session.get('_2fa_next', '')

        # TOTP-Code oder Backup-Code pruefen
        if user.verify_totp(code) or user.verify_backup_code(code):
            # Session-Daten aufraeumen
            session.pop('_2fa_user_id', None)
            session.pop('_2fa_remember', None)
            session.pop('_2fa_next', None)

            login_user(user, remember=remember)
            user.last_login = db.session.query(db.func.now()).scalar()
            db.session.commit()
            log_activity('login', 'Anmeldung mit 2FA', user.username)

            if next_page and _is_safe_url(next_page):
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Ungueltiger Code. Versuchen Sie es erneut.', 'danger')
            log_activity('login_failed', f'2FA fehlgeschlagen fuer: {user.username}', user.username)

    return render_template('auth/verify_2fa.html', username=user.username)


@auth_bp.route('/logout')
@login_required
def logout():
    """Benutzer abmelden"""
    username = current_user.username
    logout_user()
    log_activity('logout', 'Benutzer abgemeldet', username)
    flash('Sie wurden erfolgreich abgemeldet.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    """Benutzerprofil anzeigen"""
    return render_template('users/profile.html', user=current_user)


# ============================================================
# 2FA SETUP
# ============================================================

@auth_bp.route('/2fa/setup', methods=['GET', 'POST'])
@login_required
def setup_2fa():
    """2FA aktivieren — zeigt QR-Code + Backup-Codes"""
    if current_user.totp_enabled:
        flash('2FA ist bereits aktiviert.', 'info')
        return redirect(url_for('auth.profile'))

    if request.method == 'POST':
        # Verifizierung: User muss einen gueltigen Code eingeben um zu aktivieren
        code = request.form.get('code', '').strip()
        secret = session.get('_2fa_setup_secret')

        if not secret:
            flash('Sitzung abgelaufen. Bitte erneut versuchen.', 'warning')
            return redirect(url_for('auth.setup_2fa'))

        import pyotp
        totp = pyotp.TOTP(secret)
        if totp.verify(code, valid_window=1):
            current_user.totp_secret = secret
            current_user.totp_enabled = True
            backup_codes = current_user.generate_backup_codes()
            db.session.commit()
            session.pop('_2fa_setup_secret', None)
            log_activity('2fa_enabled', '2FA aktiviert', current_user.username)
            return render_template('auth/2fa_backup_codes.html', backup_codes=backup_codes)
        else:
            flash('Ungueltiger Code. Bitte scannen Sie den QR-Code erneut und geben den aktuellen Code ein.', 'danger')

    # Neues Secret generieren
    import pyotp
    secret = pyotp.random_base32()
    session['_2fa_setup_secret'] = secret
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=current_user.email or current_user.username, issuer_name='StitchAdmin')

    # QR-Code als Data-URI generieren
    qr_data_uri = _generate_qr_data_uri(uri)

    return render_template('auth/setup_2fa.html', qr_data_uri=qr_data_uri, secret=secret)


@auth_bp.route('/2fa/disable', methods=['POST'])
@login_required
def disable_2fa():
    """2FA deaktivieren — erfordert Passwort-Bestaetigung"""
    password = request.form.get('password', '')
    if not current_user.check_password(password):
        flash('Falsches Passwort.', 'danger')
        return redirect(url_for('auth.profile'))

    current_user.totp_enabled = False
    current_user.totp_secret = None
    current_user.backup_codes = None
    db.session.commit()
    log_activity('2fa_disabled', '2FA deaktiviert', current_user.username)
    flash('Zwei-Faktor-Authentifizierung wurde deaktiviert.', 'success')
    return redirect(url_for('auth.profile'))


def _generate_qr_data_uri(data):
    """Generiert QR-Code als base64 Data-URI"""
    import qrcode
    import io
    import base64
    qr = qrcode.QRCode(version=1, box_size=6, border=2,
                        error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f'data:image/png;base64,{b64}'
