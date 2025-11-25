"""
Zentraler Settings Controller für StitchAdmin
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, date
from src.models import db
from src.models.models import PriceCalculationSettings, User, ProductCategory, Brand, Supplier

# Import für Branding
try:
    from src.models.branding_settings import BrandingSettings
    BRANDING_AVAILABLE = True
except ImportError:
    BRANDING_AVAILABLE = False

# Import für SumUp Integration
try:
    from src.utils.sumup_service import sumup_service
    from src.models.sumup_token import SumUpToken
    SUMUP_AVAILABLE = True
except ImportError:
    SUMUP_AVAILABLE = False

# Import für Firmeneinstellungen
try:
    from src.models.company_settings import CompanySettings
    COMPANY_SETTINGS_AVAILABLE = True
except ImportError:
    COMPANY_SETTINGS_AVAILABLE = False

# Blueprint für zentrale Einstellungen
settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

# ... (bestehende Routen wie index, sumup, users etc. bleiben unverändert) ...

# ==================== BRANDING EINSTELLUNGEN ====================

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@settings_bp.route('/branding', methods=['GET', 'POST'])
@login_required
def branding():
    """Seite für die Branding-Einstellungen."""
    if not current_user.is_admin:
        flash('Nur Administratoren können das Erscheinungsbild anpassen.', 'danger')
        return redirect(url_for('dashboard'))

    if not BRANDING_AVAILABLE:
        flash('Branding-Funktion ist nicht verfügbar.', 'error')
        return redirect(url_for('settings.index'))

    settings = BrandingSettings.get_settings()

    if request.method == 'POST':
        # Farben aktualisieren
        settings.primary_color = request.form.get('primary_color', '#0d6efd')
        settings.secondary_color = request.form.get('secondary_color', '#6c757d')

        # Logo-Upload
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Pfad zum Speichern des Logos im static-Ordner
                upload_path = os.path.join(current_app.static_folder, 'uploads', filename)
                os.makedirs(os.path.dirname(upload_path), exist_ok=True)
                
                file.save(upload_path)
                
                # Relativen Pfad für die Verwendung in Templates speichern
                settings.logo_path = os.path.join('uploads', filename).replace('\\', '/')
                flash('Neues Logo erfolgreich hochgeladen.', 'success')

        try:
            db.session.commit()
            flash('Branding-Einstellungen erfolgreich gespeichert.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Speichern der Einstellungen: {e}', 'danger')

        return redirect(url_for('settings.branding'))

    return render_template('settings/branding.html', settings=settings)

# ... (Rest der Datei bleibt unverändert)
# (Hier aus Gründen der Kürze weggelassen)
@settings_bp.route('/')
@login_required
def index():
    """Einstellungen Hauptseite"""
    # Übersichts-Daten sammeln
    user_count = User.query.count()
    admin_count = User.query.filter_by(is_admin=True).count()
    category_count = ProductCategory.query.count()
    brand_count = Brand.query.count()

    # Preis-Kalkulation Einstellungen (Key-Value Store)
    price_factor_calculated = PriceCalculationSettings.get_setting('price_factor_calculated', 2.5)
    price_factor_recommended = PriceCalculationSettings.get_setting('price_factor_recommended', 2.5)

    settings_overview = {
        'user_count': user_count,
        'admin_count': admin_count,
        'category_count': category_count,
        'brand_count': brand_count,
        'advanced_available': False  # Erweiterte Einstellungen noch nicht verfügbar
    }

    legacy_settings = {
        'price_factor_calculated': price_factor_calculated,
        'price_factor_recommended': price_factor_recommended
    }

    advanced_settings = {
        'tax_rates': 0,
        'calculation_rules': 0,
        'default_tax_rate': None,
        'default_calculation_rule': None,
        'import_settings_configured': False
    }

    return render_template('settings/index.html',
                         settings_overview=settings_overview,
                         legacy_settings=legacy_settings,
                         advanced_settings=advanced_settings)
@settings_bp.route('/integrations/sumup')
@login_required
def sumup_integration():
    """SumUp Integration Einstellungen"""
    if not current_user.is_admin:
        flash('Nur Administratoren können SumUp konfigurieren.', 'danger')
        return redirect(url_for('settings.index'))

    # Prüfe ob SumUp verfügbar ist
    if not SUMUP_AVAILABLE:
        flash('SumUp-Modul ist nicht verfügbar. Bitte prüfen Sie die Installation.', 'error')
        return redirect(url_for('settings.index'))

    # Hole aktuellen Token-Status
    token = None
    is_connected = False

    try:
        token = SumUpToken.get_current_token()
        if token and token.is_valid():
            is_connected = True
    except Exception as e:
        print(f"Fehler beim Laden des SumUp Tokens: {e}")

    return render_template('settings/sumup.html',
                         is_connected=is_connected,
                         token=token)

@settings_bp.route('/integrations/sumup/authorize', methods=['POST'])
@login_required
def sumup_authorize():
    """SumUp OAuth Autorisierung starten"""
    if not current_user.is_admin:
        flash('Nur Administratoren können SumUp konfigurieren.', 'danger')
        return redirect(url_for('settings.index'))

    if not SUMUP_AVAILABLE:
        flash('SumUp-Modul ist nicht verfügbar.', 'error')
        return redirect(url_for('settings.sumup_integration'))

    try:
        # Starte OAuth Flow
        auth_url = sumup_service.get_authorization_url(
            redirect_uri=url_for('settings.sumup_callback', _external=True)
        )

        if auth_url:
            return redirect(auth_url)
        else:
            flash('Fehler beim Starten der Autorisierung. Bitte prüfen Sie die SumUp Client ID.', 'error')
            return redirect(url_for('settings.sumup_integration'))
    except Exception as e:
        flash(f'Fehler: {str(e)}', 'error')
        return redirect(url_for('settings.sumup_integration'))

@settings_bp.route('/integrations/sumup/callback')
@login_required
def sumup_callback():
    """SumUp OAuth Callback"""
    if not current_user.is_admin:
        flash('Nur Administratoren können SumUp konfigurieren.', 'danger')
        return redirect(url_for('settings.index'))

    if not SUMUP_AVAILABLE:
        flash('SumUp-Modul ist nicht verfügbar.', 'error')
        return redirect(url_for('settings.sumup_integration'))

    code = request.args.get('code')
    if not code:
        flash('Keine Autorisierung erhalten. Bitte versuchen Sie es erneut.', 'warning')
        return redirect(url_for('settings.sumup_integration'))

    try:
        # Tausche Code gegen Access Token
        success = sumup_service.exchange_code_for_token(
            code=code,
            redirect_uri=url_for('settings.sumup_callback', _external=True)
        )

        if success:
            flash('SumUp erfolgreich verbunden! Kartenzahlungen sind jetzt aktiviert.', 'success')
        else:
            flash('Fehler beim Verbinden mit SumUp. Bitte versuchen Sie es erneut.', 'error')
    except Exception as e:
        flash(f'Fehler: {str(e)}', 'error')

    return redirect(url_for('settings.sumup_integration'))

@settings_bp.route('/integrations/sumup/disconnect', methods=['POST'])
@login_required
def sumup_disconnect():
    """SumUp Verbindung trennen"""
    if not current_user.is_admin:
        flash('Nur Administratoren können SumUp konfigurieren.', 'danger')
        return redirect(url_for('settings.index'))

    if not SUMUP_AVAILABLE:
        flash('SumUp-Modul ist nicht verfügbar.', 'error')
        return redirect(url_for('settings.sumup_integration'))

    try:
        # Lösche Token aus der Datenbank
        token = SumUpToken.get_current_token()
        if token:
            db.session.delete(token)
            db.session.commit()
            flash('Verbindung zu SumUp wurde getrennt.', 'success')
        else:
            flash('Keine aktive SumUp-Verbindung gefunden.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Trennen: {str(e)}', 'error')

    return redirect(url_for('settings.sumup_integration'))

@settings_bp.route('/company', methods=['GET', 'POST'])
@login_required
def company_settings():
    """Firmeneinstellungen für Rechnungen"""
    if not current_user.is_admin:
        flash('Nur Administratoren können Firmeneinstellungen ändern.', 'danger')
        return redirect(url_for('settings.index'))

    if not COMPANY_SETTINGS_AVAILABLE:
        flash('Firmeneinstellungen-Modul ist nicht verfügbar.', 'error')
        return redirect(url_for('settings.index'))

    settings = CompanySettings.get_settings()

    if request.method == 'POST':
        # Aktualisiere alle Felder
        settings.company_name = request.form.get('company_name', '')
        settings.company_addition = request.form.get('company_addition', '')
        settings.owner_name = request.form.get('owner_name', '')

        # Adresse
        settings.street = request.form.get('street', '')
        settings.house_number = request.form.get('house_number', '')
        settings.postal_code = request.form.get('postal_code', '')
        settings.city = request.form.get('city', '')
        settings.country = request.form.get('country', 'Deutschland')

        # Kontakt
        settings.phone = request.form.get('phone', '')
        settings.fax = request.form.get('fax', '')
        settings.email = request.form.get('email', '')
        settings.website = request.form.get('website', '')

        # Steuern
        settings.tax_id = request.form.get('tax_id', '')
        settings.vat_id = request.form.get('vat_id', '')
        settings.tax_office = request.form.get('tax_office', '')

        # Bank
        settings.bank_name = request.form.get('bank_name', '')
        settings.iban = request.form.get('iban', '')
        settings.bic = request.form.get('bic', '')
        settings.account_holder = request.form.get('account_holder', '')

        # Handelsregister
        settings.commercial_register = request.form.get('commercial_register', '')

        # Rechnungseinstellungen
        settings.invoice_prefix = request.form.get('invoice_prefix', 'RE')
        settings.payment_terms_days = int(request.form.get('payment_terms_days', 14))
        settings.default_tax_rate = float(request.form.get('default_tax_rate', 19.0))
        settings.invoice_footer_text = request.form.get('invoice_footer_text', '')

        # Kleinunternehmer
        settings.small_business = request.form.get('small_business') == 'on'
        if settings.small_business:
            settings.small_business_text = request.form.get('small_business_text', '')

        settings.updated_by = current_user.username
        settings.updated_at = datetime.now()

        try:
            db.session.commit()
            flash('Firmeneinstellungen erfolgreich gespeichert.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Speichern: {e}', 'danger')

        return redirect(url_for('settings.company_settings'))

    return render_template('settings/company.html', settings=settings)

@settings_bp.route('/users')
@login_required
def users():
    """Benutzerverwaltung"""
    return redirect(url_for('users.index'))

@settings_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
def new_user():
    """Neuer Benutzer"""
    return redirect(url_for('users.new'))
