"""
Settings Controller - PostgreSQL-Version
System-Einstellungen (wird später erweitert)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from src.models import db, ActivityLog, PriceCalculationSettings

# Blueprint erstellen
settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

def log_activity(action, details):
    """Aktivität in Datenbank protokollieren"""
    activity = ActivityLog(
        username=current_user.username,  # Geändert von 'user' zu 'username'
        action=action,
        details=details,
        ip_address=request.remote_addr
    )
    db.session.add(activity)
    db.session.commit()

@settings_bp.route('/')
@login_required
def index():
    """Einstellungen-Übersicht"""
    if not current_user.is_admin:
        flash('Keine Berechtigung für diese Seite!', 'danger')
        return redirect(url_for('dashboard'))
    
    # TODO: Einstellungen aus Datenbank laden
    settings = {
        # Allgemeine Einstellungen
        'site_name': 'StitchAdmin',
        'maintenance_mode': False,
        'session_timeout': 30,
        'allow_registration': False,
        
        # Sicherheit
        'enable_2fa': False,
        'enable_email_notifications': True,
        
        # Firma
        'company_name': 'StitchAdmin GmbH',
        'company_address': 'Musterstraße 123, 12345 Musterstadt',
        'company_email': 'info@stitchadmin.de',
        'company_phone': '+49 123 456789',
        'tax_rate': 19,
        'currency': 'EUR',
        
        # E-Mail
        'smtp_server': '',
        'smtp_port': 587,
        'smtp_user': ''
    }
    
    return render_template('settings/index.html', settings=settings)

@settings_bp.route('/company', methods=['GET', 'POST'])
@login_required
def company():
    """Firmen-Einstellungen"""
    if not current_user.is_admin:
        flash('Keine Berechtigung!', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # TODO: In Datenbank speichern
        log_activity('settings_updated', 'Firmen-Einstellungen aktualisiert')
        flash('Einstellungen wurden gespeichert!', 'success')
        return redirect(url_for('settings.index'))
    
    return render_template('settings/company.html')

@settings_bp.route('/email', methods=['GET', 'POST'])
@login_required
def email():
    """E-Mail-Einstellungen"""
    if not current_user.is_admin:
        flash('Keine Berechtigung!', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # TODO: In Datenbank speichern
        log_activity('settings_updated', 'E-Mail-Einstellungen aktualisiert')
        flash('E-Mail-Einstellungen wurden gespeichert!', 'success')
        return redirect(url_for('settings.index'))
    
    return render_template('settings/email.html')

@settings_bp.route('/system', methods=['GET', 'POST'])
@login_required
def system():
    """System-Einstellungen"""
    if not current_user.is_admin:
        flash('Keine Berechtigung!', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # TODO: In Datenbank speichern
        log_activity('settings_updated', 'System-Einstellungen aktualisiert')
        flash('System-Einstellungen wurden gespeichert!', 'success')
        return redirect(url_for('settings.index'))
    
    # System-Informationen
    import sys
    import platform
    from flask import current_app
    
    system_info = {
        'python_version': sys.version,
        'platform': platform.platform(),
        'flask_version': current_app.extensions.get('sqlalchemy').db.engine.dialect.name,
        'database': current_app.config['SQLALCHEMY_DATABASE_URI'].split('@')[1] if '@' in current_app.config['SQLALCHEMY_DATABASE_URI'] else 'SQLite'
    }
    
    return render_template('settings/system.html', system_info=system_info)

@settings_bp.route('/backup')
@login_required
def backup():
    """Backup-Einstellungen"""
    if not current_user.is_admin:
        flash('Keine Berechtigung!', 'danger')
        return redirect(url_for('dashboard'))
    
    # TODO: Backup-Konfiguration implementieren
    return render_template('settings/backup.html')

@settings_bp.route('/general', methods=['GET', 'POST'])
@login_required
def general():
    """Allgemeine Einstellungen"""
    if not current_user.is_admin:
        flash('Keine Berechtigung!', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # TODO: In Datenbank speichern
        site_name = request.form.get('site_name')
        maintenance_mode = request.form.get('maintenance_mode', False) == 'on'
        session_timeout = request.form.get('session_timeout', 30)
        
        log_activity('settings_updated', 'Allgemeine Einstellungen aktualisiert')
        flash('Allgemeine Einstellungen wurden gespeichert!', 'success')
        return redirect(url_for('settings.index'))
    
    # TODO: Aus Datenbank laden
    settings = {
        'site_name': 'StitchAdmin',
        'maintenance_mode': False,
        'session_timeout': 30,
        'allow_registration': False
    }
    
    return render_template('settings/general.html', settings=settings)

@settings_bp.route('/security', methods=['GET', 'POST'])
@login_required
def security():
    """Sicherheits-Einstellungen"""
    if not current_user.is_admin:
        flash('Keine Berechtigung!', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # TODO: In Datenbank speichern
        enable_2fa = request.form.get('enable_2fa', False) == 'on'
        max_login_attempts = request.form.get('max_login_attempts', 5)
        password_min_length = request.form.get('password_min_length', 8)
        
        log_activity('settings_updated', 'Sicherheits-Einstellungen aktualisiert')
        flash('Sicherheits-Einstellungen wurden gespeichert!', 'success')
        return redirect(url_for('settings.index'))
    
    # TODO: Aus Datenbank laden
    settings = {
        'enable_2fa': False,
        'max_login_attempts': 5,
        'password_min_length': 8,
        'require_special_chars': True
    }
    
    return render_template('settings/security.html', settings=settings)

@settings_bp.route('/pricing', methods=['GET', 'POST'])
@login_required
def pricing():
    """Preis-Einstellungen"""
    if not current_user.is_admin:
        flash('Keine Berechtigung!', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # Artikel-Kalkulationsfaktoren speichern
        try:
            factor_calculated = float(request.form.get('price_factor_calculated', 1.5))
            factor_recommended = float(request.form.get('price_factor_recommended', 2.0))
            
            PriceCalculationSettings.set_setting('price_factor_calculated', factor_calculated, 
                                               'Faktor für kalkulierten VK-Preis (EK x Faktor)', 
                                               current_user.username)
            PriceCalculationSettings.set_setting('price_factor_recommended', factor_recommended,
                                               'Faktor für empfohlenen VK-Preis (EK x Faktor)',
                                               current_user.username)
            
            # Stickerei-Preise
            stitch_price_per_1000 = float(request.form.get('stitch_price_per_1000', 1.50))
            setup_fee = float(request.form.get('setup_fee', 15.00))
            digitizing_per_1000 = float(request.form.get('digitizing_per_1000', 5.00))
            
            PriceCalculationSettings.set_setting('stitch_price_per_1000', stitch_price_per_1000,
                                               'Preis pro 1000 Stiche', current_user.username)
            PriceCalculationSettings.set_setting('setup_fee', setup_fee,
                                               'Einrichtungsgebühr', current_user.username)
            PriceCalculationSettings.set_setting('digitizing_per_1000', digitizing_per_1000,
                                               'Digitalisierung pro 1000 Stiche', current_user.username)
            
            log_activity('settings_updated', 'Preis-Einstellungen aktualisiert')
            flash('Preis-Einstellungen wurden gespeichert!', 'success')
        except ValueError:
            flash('Ungültige Werte eingegeben!', 'danger')
        
        return redirect(url_for('settings.pricing'))
    
    # Aus Datenbank laden
    settings = {
        'price_factor_calculated': PriceCalculationSettings.get_setting('price_factor_calculated', 1.5),
        'price_factor_recommended': PriceCalculationSettings.get_setting('price_factor_recommended', 2.0),
        'stitch_price_per_1000': PriceCalculationSettings.get_setting('stitch_price_per_1000', 1.50),
        'setup_fee': PriceCalculationSettings.get_setting('setup_fee', 15.00),
        'digitizing_per_1000': PriceCalculationSettings.get_setting('digitizing_per_1000', 5.00),
        'minimum_order_value': 25.00,
        'tax_rate': 19
    }
    
    return render_template('settings/pricing.html', settings=settings)

@settings_bp.route('/shipping', methods=['GET', 'POST'])
@login_required
def shipping():
    """Versand-Einstellungen"""
    if not current_user.is_admin:
        flash('Keine Berechtigung!', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # TODO: In Datenbank speichern
        default_shipping_cost = request.form.get('default_shipping_cost', 5.90)
        free_shipping_threshold = request.form.get('free_shipping_threshold', 50.00)
        
        log_activity('settings_updated', 'Versand-Einstellungen aktualisiert')
        flash('Versand-Einstellungen wurden gespeichert!', 'success')
        return redirect(url_for('settings.index'))
    
    # TODO: Aus Datenbank laden
    settings = {
        'default_shipping_cost': 5.90,
        'free_shipping_threshold': 50.00,
        'express_shipping_cost': 12.90,
        'international_shipping_cost': 15.90
    }
    
    return render_template('settings/shipping.html', settings=settings)
