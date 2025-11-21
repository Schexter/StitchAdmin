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
    return render_template('settings/sumup.html')

@settings_bp.route('/integrations/sumup/authorize', methods=['POST'])
@login_required
def sumup_authorize():
    """SumUp OAuth Autorisierung"""
    flash('SumUp Integration ist noch nicht implementiert.', 'info')
    return redirect(url_for('settings.index'))

@settings_bp.route('/integrations/sumup/callback')
@login_required
def sumup_callback():
    """SumUp OAuth Callback"""
    flash('SumUp Integration ist noch nicht implementiert.', 'info')
    return redirect(url_for('settings.index'))
@settings_bp.route('/integrations/sumup/disconnect', methods=['POST'])
@login_required
def sumup_disconnect():
    """SumUp Verbindung trennen"""
    flash('SumUp Integration ist noch nicht implementiert.', 'info')
    return redirect(url_for('settings.index'))

@settings_bp.route('/users')
@login_required
def users():
    """Benutzerverwaltung"""
    return redirect(url_for('user.index'))

@settings_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
def new_user():
    """Neuer Benutzer"""
    return redirect(url_for('user.new'))
