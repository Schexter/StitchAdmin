"""
Zentraler Settings Controller für StitchAdmin
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from src.models import db
from src.models.models import PriceCalculationSettings, User, ProductCategory, Brand, Supplier

# Versuche erweiterte Settings zu importieren
try:
    from src.models.settings import TaxRate, PriceCalculationRule, ImportSettings
    ADVANCED_SETTINGS_AVAILABLE = True
except ImportError:
    ADVANCED_SETTINGS_AVAILABLE = False

# Import für SumUp Integration
try:
    from src.utils.sumup_service import sumup_service
    from src.models.sumup_token import SumUpToken
    SUMUP_AVAILABLE = True
except ImportError:
    SUMUP_AVAILABLE = False

# Blueprint für zentrale Einstellungen
settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/')
@login_required
def index():
    """Zentrale Einstellungen-Übersicht"""
    # ... (unverändert)
    pass

# ==================== SUMUP INTEGRATION ====================

@settings_bp.route('/integrations/sumup')
@login_required
def sumup_integration():
    """Seite für die SumUp-Integration."""
    if not SUMUP_AVAILABLE:
        flash('SumUp-Integrationsdateien nicht gefunden.', 'error')
        return redirect(url_for('settings.index'))

    # Prüfen, ob bereits ein Token für den Benutzer (oder global) existiert
    # Annahme: Wir verwenden eine globale Einstellung, daher user_id=None
    token = SumUpToken.get_token(user_id=None)
    is_connected = token is not None and not token.is_expired()

    return render_template('settings/sumup.html', is_connected=is_connected, token=token)

@settings_bp.route('/integrations/sumup/authorize', methods=['POST'])
@login_required
def sumup_authorize():
    """Leitet den Benutzer zur SumUp-Authentifizierung weiter."""
    if not SUMUP_AVAILABLE:
        return redirect(url_for('settings.index'))

    auth_url, error = sumup_service.get_authorization_url()
    if error:
        flash(f'Fehler beim Starten der SumUp-Verbindung: {error}', 'danger')
        return redirect(url_for('settings.sumup_integration'))

    return redirect(auth_url)

@settings_bp.route('/integrations/sumup/callback')
@login_required
def sumup_callback():
    """Callback-URL, die von SumUp nach der Authentifizierung aufgerufen wird."""
    if not SUMUP_AVAILABLE:
        return redirect(url_for('settings.index'))

    code = request.args.get('code')
    if not code:
        flash('Ungültige Antwort von SumUp erhalten.', 'danger')
        return redirect(url_for('settings.sumup_integration'))

    # Tausche den Code gegen einen Token
    token_data = sumup_service.exchange_code_for_token(code)

    if not token_data or not token_data.get('success'):
        flash(f"Fehler beim Abrufen des Tokens von SumUp: {token_data.get('error', 'Unbekannt')}", 'danger')
        return redirect(url_for('settings.sumup_integration'))

    # Speichere den Token in der Datenbank
    # Annahme: Globale Einstellung, kein spezifischer Benutzer
    SumUpToken.save_token(token_data, user_id=None)

    flash('SumUp-Konto erfolgreich verbunden!', 'success')
    return redirect(url_for('settings.sumup_integration'))

@settings_bp.route('/integrations/sumup/disconnect', methods=['POST'])
@login_required
def sumup_disconnect():
    """Trennt die Verbindung zum SumUp-Konto."""
    if not SUMUP_AVAILABLE:
        return redirect(url_for('settings.index'))

    token = SumUpToken.get_token(user_id=None)
    if token:
        db.session.delete(token)
        db.session.commit()
        flash('Die Verbindung zu SumUp wurde erfolgreich getrennt.', 'success')
    else:
        flash('Keine aktive SumUp-Verbindung gefunden.', 'warning')

    return redirect(url_for('settings.sumup_integration'))


# ==================== BENUTZER-VERWALTUNG ====================
# ... (Rest der Datei bleibt unverändert)
# (Hier aus Gründen der Kürze weggelassen)
@settings_bp.route('/users')
@login_required
def users():
    pass

@settings_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
def new_user():
    pass
