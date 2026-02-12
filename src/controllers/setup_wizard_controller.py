# -*- coding: utf-8 -*-
"""
SETUP WIZARD CONTROLLER
=======================
Erstinstallations-Assistent für StitchAdmin 2.0

Führt durch:
1. Willkommen & Lizenzvereinbarung
2. Firmendaten
3. Logo & Branding
4. Speicherpfade
5. Bankverbindung
6. E-Mail-Einstellungen
7. Administrator-Konto
8. Zusammenfassung & Abschluss

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from datetime import datetime

from src.models import db

import logging
logger = logging.getLogger(__name__)

# Blueprint
setup_bp = Blueprint('setup', __name__, url_prefix='/setup')

# Erlaubte Bildformate
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def is_setup_complete():
    """Prüft ob Setup bereits abgeschlossen wurde"""
    try:
        from src.models.company_settings import CompanySettings
        settings = CompanySettings.query.first()
        if settings and settings.company_name and settings.company_name != 'Ihre Firma':
            return True
    except:
        pass
    return False


def setup_required(f):
    """Decorator: Leitet zum Setup wenn nicht abgeschlossen"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_setup_complete():
            return redirect(url_for('setup.welcome'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# SCHRITT 1: WILLKOMMEN
# ============================================================================

@setup_bp.route('/')
@setup_bp.route('/welcome')
def welcome():
    """Willkommensseite des Setup-Wizards"""
    if is_setup_complete():
        return redirect(url_for('dashboard'))
    
    return render_template('setup/welcome.html', step=1, total_steps=8)


@setup_bp.route('/license', methods=['GET', 'POST'])
def license():
    """Lizenzvereinbarung"""
    if is_setup_complete():
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        if request.form.get('accept_license'):
            session['setup_license_accepted'] = True
            return redirect(url_for('setup.company'))
        else:
            flash('Bitte akzeptieren Sie die Lizenzvereinbarung um fortzufahren.', 'warning')
    
    return render_template('setup/license.html', step=1, total_steps=8)


# ============================================================================
# SCHRITT 2: FIRMENDATEN
# ============================================================================

@setup_bp.route('/company', methods=['GET', 'POST'])
def company():
    """Firmendaten eingeben"""
    if is_setup_complete():
        return redirect(url_for('dashboard'))
    
    from src.models.company_settings import CompanySettings
    settings = CompanySettings.get_settings()
    
    if request.method == 'POST':
        # Firmendaten speichern
        settings.company_name = request.form.get('company_name', '').strip()
        settings.company_addition = request.form.get('company_addition', '').strip()
        settings.owner_name = request.form.get('owner_name', '').strip()
        
        # Adresse
        settings.street = request.form.get('street', '').strip()
        settings.house_number = request.form.get('house_number', '').strip()
        settings.postal_code = request.form.get('postal_code', '').strip()
        settings.city = request.form.get('city', '').strip()
        settings.country = request.form.get('country', 'Deutschland').strip()
        
        # Kontakt
        settings.phone = request.form.get('phone', '').strip()
        settings.email = request.form.get('email', '').strip()
        settings.website = request.form.get('website', '').strip()
        
        # Steuerdaten
        settings.tax_id = request.form.get('tax_id', '').strip()
        settings.vat_id = request.form.get('vat_id', '').strip()
        
        # Kleinunternehmer
        settings.small_business = request.form.get('small_business') == 'on'
        
        try:
            db.session.commit()
            flash('Firmendaten gespeichert!', 'success')
            return redirect(url_for('setup.branding'))
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Speichern: {e}', 'danger')
    
    return render_template('setup/company.html', step=2, total_steps=8, settings=settings)


# ============================================================================
# SCHRITT 3: LOGO & BRANDING
# ============================================================================

@setup_bp.route('/branding', methods=['GET', 'POST'])
def branding():
    """Logo und Farben konfigurieren"""
    if is_setup_complete():
        return redirect(url_for('dashboard'))
    
    try:
        from src.models.branding_settings import BrandingSettings
        branding = BrandingSettings.get_settings()
    except:
        branding = None
    
    from src.models.company_settings import CompanySettings
    company = CompanySettings.get_settings()
    
    if request.method == 'POST':
        # Logo hochladen
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Einheitlicher Name
                ext = filename.rsplit('.', 1)[1].lower()
                logo_filename = f"company_logo.{ext}"
                
                upload_dir = os.path.join(current_app.static_folder, 'uploads', 'logos')
                os.makedirs(upload_dir, exist_ok=True)
                
                filepath = os.path.join(upload_dir, logo_filename)
                file.save(filepath)
                
                # Pfad speichern
                company.logo_path = f"uploads/logos/{logo_filename}"
                
                if branding:
                    branding.logo_path = company.logo_path
        
        # Farben
        if branding:
            branding.primary_color = request.form.get('primary_color', '#0d6efd')
            branding.secondary_color = request.form.get('secondary_color', '#6c757d')
        
        try:
            db.session.commit()
            flash('Branding gespeichert!', 'success')
            return redirect(url_for('setup.storage'))
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {e}', 'danger')
    
    return render_template('setup/branding.html', step=3, total_steps=8, 
                         branding=branding, company=company)


# ============================================================================
# SCHRITT 4: SPEICHERPFADE
# ============================================================================

@setup_bp.route('/storage', methods=['GET', 'POST'])
def storage():
    """Speicherpfade konfigurieren"""
    if is_setup_complete():
        return redirect(url_for('dashboard'))
    
    try:
        from src.models.storage_settings import StorageSettings
        settings = StorageSettings.get_settings()
    except Exception as e:
        logger.error(f"StorageSettings nicht verfügbar: {e}")
        flash('Speichereinstellungen nicht verfügbar. Bitte Migration ausführen.', 'warning')
        return redirect(url_for('setup.bank'))
    
    # Standard-Basispfad vorschlagen
    default_base = os.path.join(os.path.expanduser('~'), 'StitchAdmin', 'Dokumente')
    
    if request.method == 'POST':
        # Basispfad
        base_path = request.form.get('base_path', '').strip()
        if not base_path:
            base_path = default_base
        
        settings.base_path = base_path
        
        # Ordnerstruktur
        settings.folder_structure = request.form.get('folder_structure', 'year_month')
        settings.include_customer_in_filename = request.form.get('include_customer') == 'on'
        settings.include_date_in_filename = request.form.get('include_date') == 'on'
        
        # Pfade validieren
        errors = settings.validate_paths()
        if errors:
            for error in errors:
                flash(error, 'danger')
        else:
            # Ordnerstruktur erstellen
            if settings.create_folder_structure():
                try:
                    db.session.commit()
                    flash('Speicherpfade konfiguriert und Ordner erstellt!', 'success')
                    return redirect(url_for('setup.bank'))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Fehler: {e}', 'danger')
            else:
                flash('Ordnerstruktur konnte nicht erstellt werden.', 'danger')
    
    return render_template('setup/storage.html', step=4, total_steps=8,
                         settings=settings, default_base=default_base)


# ============================================================================
# SCHRITT 5: BANKVERBINDUNG
# ============================================================================

@setup_bp.route('/bank', methods=['GET', 'POST'])
def bank():
    """Bankverbindung konfigurieren"""
    if is_setup_complete():
        return redirect(url_for('dashboard'))
    
    from src.models.company_settings import CompanySettings
    settings = CompanySettings.get_settings()
    
    if request.method == 'POST':
        settings.bank_name = request.form.get('bank_name', '').strip()
        settings.iban = request.form.get('iban', '').strip().upper().replace(' ', '')
        settings.bic = request.form.get('bic', '').strip().upper()
        settings.account_holder = request.form.get('account_holder', '').strip()
        
        # Zahlungsziel
        try:
            settings.payment_terms_days = int(request.form.get('payment_terms_days', 14))
        except:
            settings.payment_terms_days = 14
        
        try:
            db.session.commit()
            flash('Bankverbindung gespeichert!', 'success')
            return redirect(url_for('setup.email'))
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {e}', 'danger')
    
    return render_template('setup/bank.html', step=5, total_steps=8, settings=settings)


# ============================================================================
# SCHRITT 6: E-MAIL-EINSTELLUNGEN
# ============================================================================

@setup_bp.route('/email', methods=['GET', 'POST'])
def email():
    """E-Mail-Versand konfigurieren"""
    if is_setup_complete():
        return redirect(url_for('dashboard'))
    
    from src.models.company_settings import CompanySettings
    settings = CompanySettings.get_settings()
    
    if request.method == 'POST':
        settings.email_method = request.form.get('email_method', 'outlook')
        
        if settings.email_method == 'smtp':
            settings.smtp_server = request.form.get('smtp_server', '').strip()
            settings.smtp_port = int(request.form.get('smtp_port', 587))
            settings.smtp_username = request.form.get('smtp_username', '').strip()
            settings.smtp_password = request.form.get('smtp_password', '').strip()
            settings.smtp_use_tls = request.form.get('smtp_use_tls') == 'on'
            settings.smtp_from_email = request.form.get('smtp_from_email', '').strip()
            settings.smtp_from_name = request.form.get('smtp_from_name', '').strip()
        
        try:
            db.session.commit()
            flash('E-Mail-Einstellungen gespeichert!', 'success')
            return redirect(url_for('setup.admin'))
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {e}', 'danger')
    
    return render_template('setup/email.html', step=6, total_steps=8, settings=settings)


# ============================================================================
# SCHRITT 7: ADMINISTRATOR-KONTO
# ============================================================================

@setup_bp.route('/admin', methods=['GET', 'POST'])
def admin():
    """Administrator-Konto erstellen"""
    if is_setup_complete():
        return redirect(url_for('dashboard'))
    
    from src.models.models import User
    
    # Prüfen ob bereits ein Admin existiert
    existing_admin = User.query.filter_by(is_admin=True).first()
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        # Validierung
        errors = []
        if not username or len(username) < 3:
            errors.append('Benutzername muss mindestens 3 Zeichen haben.')
        if not email or '@' not in email:
            errors.append('Bitte gültige E-Mail-Adresse eingeben.')
        if not password or len(password) < 8:
            errors.append('Passwort muss mindestens 8 Zeichen haben.')
        if password != password_confirm:
            errors.append('Passwörter stimmen nicht überein.')
        
        # Prüfen ob Benutzer existiert
        if User.query.filter_by(username=username).first():
            errors.append('Benutzername bereits vergeben.')
        if User.query.filter_by(email=email).first():
            errors.append('E-Mail-Adresse bereits registriert.')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
        else:
            try:
                admin_user = User(
                    username=username,
                    email=email,
                    password_hash=generate_password_hash(password),
                    is_admin=True,
                    is_active=True
                )
                db.session.add(admin_user)
                db.session.commit()
                
                flash('Administrator-Konto erstellt!', 'success')
                return redirect(url_for('setup.finish'))
            except Exception as e:
                db.session.rollback()
                flash(f'Fehler: {e}', 'danger')
    
    return render_template('setup/admin.html', step=7, total_steps=8, 
                         existing_admin=existing_admin)


# ============================================================================
# SCHRITT 8: ZUSAMMENFASSUNG & ABSCHLUSS
# ============================================================================

@setup_bp.route('/finish', methods=['GET', 'POST'])
def finish():
    """Setup abschließen"""
    from src.models.company_settings import CompanySettings
    company = CompanySettings.get_settings()
    
    try:
        from src.models.storage_settings import StorageSettings
        storage = StorageSettings.get_settings()
    except:
        storage = None
    
    try:
        from src.models.branding_settings import BrandingSettings
        branding = BrandingSettings.get_settings()
    except:
        branding = None
    
    from src.models.models import User
    admin = User.query.filter_by(is_admin=True).first()
    
    if request.method == 'POST':
        # Setup als abgeschlossen markieren
        # (wird implizit durch vorhandene Firmendaten erkannt)
        flash('🎉 Setup erfolgreich abgeschlossen! Willkommen bei StitchAdmin!', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('setup/finish.html', step=8, total_steps=8,
                         company=company, storage=storage, branding=branding, admin=admin)


# ============================================================================
# HILFSFUNKTIONEN
# ============================================================================

@setup_bp.route('/skip')
def skip():
    """Setup überspringen (für Entwicklung)"""
    if current_app.debug:
        from src.models.company_settings import CompanySettings
        settings = CompanySettings.get_settings()
        settings.company_name = 'StitchAdmin Demo GmbH'
        db.session.commit()
        flash('Setup übersprungen (Demo-Modus).', 'info')
        return redirect(url_for('dashboard'))
    return redirect(url_for('setup.welcome'))


@setup_bp.route('/reset')
def reset():
    """Setup zurücksetzen (für Entwicklung)"""
    if current_app.debug:
        from src.models.company_settings import CompanySettings
        settings = CompanySettings.query.first()
        if settings:
            settings.company_name = 'Ihre Firma'
            db.session.commit()
        session.clear()
        flash('Setup zurückgesetzt.', 'info')
        return redirect(url_for('setup.welcome'))
    return redirect(url_for('dashboard'))
