"""
Settings Controller - Systemeinstellungen verwalten
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
import json
import os
from src.utils.activity_logger import log_activity

# Blueprint erstellen
settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

SETTINGS_FILE = 'system_settings.json'

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Bitte melden Sie sich an.', 'info')
            return redirect(url_for('login'))
        if not session.get('is_admin', False):
            flash('Keine Berechtigung für diese Aktion.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def load_settings():
    """Lade Systemeinstellungen"""
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    
    # Standard-Einstellungen
    return {
        'site_name': 'StitchAdmin',
        'site_description': 'Administrations-Dashboard',
        'maintenance_mode': False,
        'allow_registration': False,
        'session_timeout': 30,
        'max_login_attempts': 5,
        'password_min_length': 8,
        'require_password_change': False,
        'days_until_password_expires': 90,
        'enable_2fa': False,
        'smtp_server': '',
        'smtp_port': 587,
        'smtp_username': '',
        'smtp_from_email': '',
        'enable_email_notifications': False
    }

def save_settings(settings):
    """Speichere Systemeinstellungen"""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

@settings_bp.route('/')
@admin_required
def index():
    """Einstellungen anzeigen"""
    settings = load_settings()
    return render_template('settings/index.html', settings=settings)

@settings_bp.route('/general', methods=['GET', 'POST'])
@admin_required
def general():
    """Allgemeine Einstellungen"""
    settings = load_settings()
    
    if request.method == 'POST':
        settings['site_name'] = request.form.get('site_name', settings['site_name'])
        settings['site_description'] = request.form.get('site_description', settings['site_description'])
        settings['maintenance_mode'] = request.form.get('maintenance_mode', False) == 'on'
        settings['allow_registration'] = request.form.get('allow_registration', False) == 'on'
        settings['session_timeout'] = int(request.form.get('session_timeout', 30))
        
        save_settings(settings)
        log_activity(session['username'], 'update_settings', 'Allgemeine Einstellungen wurden aktualisiert')
        
        flash('Einstellungen wurden gespeichert!', 'success')
        return redirect(url_for('settings.general'))
    
    return render_template('settings/general.html', settings=settings)

@settings_bp.route('/security', methods=['GET', 'POST'])
@admin_required
def security():
    """Sicherheitseinstellungen"""
    settings = load_settings()
    
    if request.method == 'POST':
        settings['max_login_attempts'] = int(request.form.get('max_login_attempts', 5))
        settings['password_min_length'] = int(request.form.get('password_min_length', 8))
        settings['require_password_change'] = request.form.get('require_password_change', False) == 'on'
        settings['days_until_password_expires'] = int(request.form.get('days_until_password_expires', 90))
        settings['enable_2fa'] = request.form.get('enable_2fa', False) == 'on'
        
        save_settings(settings)
        log_activity(session['username'], 'update_settings', 'Sicherheitseinstellungen wurden aktualisiert')
        
        flash('Sicherheitseinstellungen wurden gespeichert!', 'success')
        return redirect(url_for('settings.security'))
    
    return render_template('settings/security.html', settings=settings)

@settings_bp.route('/email', methods=['GET', 'POST'])
@admin_required
def email():
    """E-Mail Einstellungen"""
    settings = load_settings()
    
    if request.method == 'POST':
        settings['smtp_server'] = request.form.get('smtp_server', '')
        settings['smtp_port'] = int(request.form.get('smtp_port', 587))
        settings['smtp_username'] = request.form.get('smtp_username', '')
        settings['smtp_from_email'] = request.form.get('smtp_from_email', '')
        settings['enable_email_notifications'] = request.form.get('enable_email_notifications', False) == 'on'
        
        # Passwort nur aktualisieren wenn eingegeben
        smtp_password = request.form.get('smtp_password')
        if smtp_password:
            settings['smtp_password'] = smtp_password  # In Produktion verschlüsseln!
        
        save_settings(settings)
        log_activity(session['username'], 'update_settings', 'E-Mail Einstellungen wurden aktualisiert')
        
        flash('E-Mail Einstellungen wurden gespeichert!', 'success')
        return redirect(url_for('settings.email'))
    
    return render_template('settings/email.html', settings=settings)

@settings_bp.route('/shipping', methods=['GET', 'POST'])
@admin_required
def shipping():
    """Versandkosten-Einstellungen"""
    # Lade Versandeinstellungen aus shipping_controller
    from src.controllers.shipping_controller import load_shipping_settings, SHIPPING_SETTINGS_FILE
    import json
    
    settings = load_shipping_settings()
    
    if request.method == 'POST':
        # Basis-Einstellungen
        settings['free_shipping_threshold'] = float(request.form.get('free_shipping_threshold', 50.00))
        settings['default_package_weight'] = float(request.form.get('default_package_weight', 0.5))
        
        # Carrier-Einstellungen aktualisieren
        for carrier_id in settings['carriers']:
            enabled = request.form.get(f'carrier_{carrier_id}_enabled') == 'on'
            cost_domestic = float(request.form.get(f'carrier_{carrier_id}_cost_domestic', 0))
            cost_eu = float(request.form.get(f'carrier_{carrier_id}_cost_eu', 0))
            cost_international = float(request.form.get(f'carrier_{carrier_id}_cost_international', 0))
            
            settings['carriers'][carrier_id]['enabled'] = enabled
            settings['carriers'][carrier_id]['cost_domestic'] = cost_domestic
            settings['carriers'][carrier_id]['cost_eu'] = cost_eu
            settings['carriers'][carrier_id]['cost_international'] = cost_international
        
        # Gewichtsstufen
        weight_tiers = []
        tier_index = 0
        while f'weight_tier_{tier_index}_max' in request.form:
            tier = {
                'max_weight': float(request.form.get(f'weight_tier_{tier_index}_max', 0)),
                'multiplier': float(request.form.get(f'weight_tier_{tier_index}_multiplier', 1.0))
            }
            weight_tiers.append(tier)
            tier_index += 1
        
        if weight_tiers:
            settings['weight_tiers'] = weight_tiers
        
        # Speichern
        with open(SHIPPING_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        
        log_activity(session['username'], 'update_settings', 'Versandeinstellungen wurden aktualisiert')
        flash('Versandeinstellungen wurden gespeichert!', 'success')
        return redirect(url_for('settings.shipping'))
    
    return render_template('settings/shipping.html', settings=settings)

@settings_bp.route('/pricing', methods=['GET', 'POST'])
@admin_required
def pricing():
    """Kostenkalkulations-Einstellungen"""
    # Lade Preiseinstellungen aus dem order_controller
    from src.controllers.order_controller import load_material_prices, MATERIAL_PRICES_FILE
    import json
    
    pricing = load_material_prices()
    
    if request.method == 'POST':
        # Stickerei-Preise
        pricing['embroidery']['price_per_1000_stitches'] = float(request.form.get('embroidery_price_per_1000', 1.50))
        pricing['embroidery']['setup_fee'] = float(request.form.get('embroidery_setup_fee', 15.00))
        pricing['embroidery']['thread_price_per_cone'] = float(request.form.get('thread_price_per_cone', 3.50))
        
        # DTF-Preise
        pricing['dtf']['film_price_per_meter'] = float(request.form.get('dtf_film_price', 12.00))
        pricing['dtf']['powder_price_per_kg'] = float(request.form.get('dtf_powder_price', 18.00))
        pricing['dtf']['ink_price_per_liter'] = float(request.form.get('dtf_ink_price', 45.00))
        pricing['dtf']['powder_usage_per_m2'] = float(request.form.get('dtf_powder_usage', 0.08))
        pricing['dtf']['ink_coverage'] = float(request.form.get('dtf_ink_coverage', 0.012))
        pricing['dtf']['waste_factor'] = float(request.form.get('dtf_waste_factor', 1.15))
        pricing['dtf']['energy_cost_per_m2'] = float(request.form.get('dtf_energy_cost', 0.50))
        pricing['dtf']['labor_cost_per_print'] = float(request.form.get('dtf_labor_cost', 2.00))
        
        # Mengenstaffeln
        if 'discounts' not in pricing:
            pricing['discounts'] = {}
        
        pricing['discounts']['qty_10'] = int(request.form.get('discount_10', 5))
        pricing['discounts']['qty_25'] = int(request.form.get('discount_25', 10))
        pricing['discounts']['qty_50'] = int(request.form.get('discount_50', 15))
        pricing['discounts']['qty_100'] = int(request.form.get('discount_100', 20))
        pricing['discounts']['qty_250'] = int(request.form.get('discount_250', 25))
        pricing['discounts']['qty_500'] = int(request.form.get('discount_500', 30))
        
        # Standard-Textilpreise
        pricing['textile_prices']['t-shirt'] = float(request.form.get('textile_tshirt', 5.00))
        pricing['textile_prices']['polo'] = float(request.form.get('textile_polo', 8.00))
        pricing['textile_prices']['hoodie'] = float(request.form.get('textile_hoodie', 15.00))
        pricing['textile_prices']['pullover'] = float(request.form.get('textile_pullover', 12.00))
        pricing['textile_prices']['jacket'] = float(request.form.get('textile_jacket', 20.00))
        pricing['textile_prices']['cap'] = float(request.form.get('textile_cap', 4.00))
        pricing['textile_prices']['bag'] = float(request.form.get('textile_bag', 6.00))
        pricing['textile_prices']['other'] = float(request.form.get('textile_other', 10.00))
        
        # Speichern
        with open(MATERIAL_PRICES_FILE, 'w', encoding='utf-8') as f:
            json.dump(pricing, f, indent=2, ensure_ascii=False)
        
        log_activity(session['username'], 'update_settings', 'Kostenkalkulations-Einstellungen wurden aktualisiert')
        flash('Kostenkalkulations-Einstellungen wurden gespeichert!', 'success')
        return redirect(url_for('settings.pricing'))
    
    return render_template('settings/pricing.html', pricing=pricing)