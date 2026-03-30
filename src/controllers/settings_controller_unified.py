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


@settings_bp.route('/email', methods=['GET', 'POST'])
@login_required
def email():
    """E-Mail Einstellungen"""
    if not current_user.is_admin:
        flash('Nur Administratoren können E-Mail-Einstellungen ändern.', 'danger')
        return redirect(url_for('settings.index'))

    from src.models.company_settings import CompanySettings
    company_settings = CompanySettings.get_settings()

    if request.method == 'POST':
        # E-Mail-Methode - sicherstellen dass ein gültiger Wert gespeichert wird
        email_method = request.form.get('email_method', 'outlook')
        if email_method not in ['outlook', 'smtp', 'mailto']:
            email_method = 'outlook'
        company_settings.email_method = email_method

        # Outlook-Konto speichern
        company_settings.outlook_account = request.form.get('outlook_account', '')

        # SMTP-Einstellungen
        company_settings.smtp_server = request.form.get('smtp_server', '')
        company_settings.smtp_port = int(request.form.get('smtp_port', 587) or 587)
        company_settings.smtp_username = request.form.get('smtp_username', '')
        company_settings.smtp_use_tls = request.form.get('smtp_use_tls') == 'on'
        company_settings.smtp_from_email = request.form.get('smtp_from_email', '')
        company_settings.smtp_from_name = request.form.get('smtp_from_name', '')

        # Passwort nur aktualisieren wenn eingegeben
        smtp_password = request.form.get('smtp_password')
        if smtp_password:
            company_settings.smtp_password = smtp_password

        # E-Mail-Vorlagen
        company_settings.invoice_email_subject = request.form.get('invoice_email_subject', 'Rechnung {invoice_number}')
        company_settings.invoice_email_template = request.form.get('invoice_email_template', '')

        # E-Mail-Signatur
        company_settings.email_signature = request.form.get('email_signature', '')

        db.session.commit()

        flash('E-Mail Einstellungen wurden gespeichert!', 'success')
        return redirect(url_for('settings.email'))

    return render_template('settings/email.html', settings=company_settings)


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

    # Hole aktuellen Status
    token = None
    is_connected = False
    api_key_status = None

    settings = CompanySettings.get_settings() if COMPANY_SETTINGS_AVAILABLE else None

    # Pruefe API-Key Verbindung
    if settings and settings.sumup_api_key:
        try:
            check = sumup_service.check_connection()
            if check.get('success'):
                is_connected = True
                api_key_status = 'ok'
            else:
                api_key_status = check.get('error', 'Unbekannter Fehler')
        except Exception as e:
            api_key_status = str(e)

    # Fallback: OAuth Token
    if not is_connected:
        try:
            token = SumUpToken.get_current_token()
            if token and token.is_valid():
                is_connected = True
        except Exception as e:
            logger.error(f"Fehler beim Laden des SumUp Tokens: {e}")

    return render_template('settings/sumup.html',
                         is_connected=is_connected,
                         token=token,
                         settings=settings,
                         api_key_status=api_key_status)


@settings_bp.route('/integrations/sumup/save', methods=['POST'])
@login_required
def sumup_save_keys():
    """SumUp API Key und Merchant Code speichern"""
    if not current_user.is_admin:
        flash('Nur Administratoren können SumUp konfigurieren.', 'danger')
        return redirect(url_for('settings.index'))

    if not COMPANY_SETTINGS_AVAILABLE:
        flash('Firmeneinstellungen-Modul nicht verfügbar.', 'error')
        return redirect(url_for('settings.index'))

    settings = CompanySettings.get_settings()
    settings.sumup_api_key = request.form.get('sumup_api_key', '').strip()
    settings.sumup_merchant_code = request.form.get('sumup_merchant_code', '').strip()
    settings.updated_by = current_user.username

    try:
        db.session.commit()
        flash('SumUp-Zugangsdaten gespeichert.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Speichern: {e}', 'danger')

    return redirect(url_for('settings.sumup_integration'))


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
        result = sumup_service.exchange_code_for_token(
            code=code,
            redirect_uri=url_for('settings.sumup_callback', _external=True)
        )

        if result and result.get('success'):
            flash('SumUp erfolgreich verbunden! Kartenzahlungen sind jetzt aktiviert.', 'success')
        else:
            flash('Fehler beim Verbinden mit SumUp. Bitte versuchen Sie es erneut.', 'error')
    except Exception as e:
        flash(f'Fehler: {str(e)}', 'error')

    return redirect(url_for('settings.sumup_integration'))

@settings_bp.route('/integrations/sumup/readers')
@login_required
def sumup_readers():
    """Liste aller registrierten SumUp-Terminals (AJAX)"""
    if not current_user.is_admin or not SUMUP_AVAILABLE:
        return jsonify({'success': False, 'error': 'Nicht berechtigt'})
    result = sumup_service.list_readers()
    return jsonify(result)


@settings_bp.route('/integrations/sumup/readers/pair', methods=['POST'])
@login_required
def sumup_pair_reader():
    """Neues SumUp-Terminal per Pairing-Code registrieren"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Nicht berechtigt'})
    if not SUMUP_AVAILABLE:
        return jsonify({'success': False, 'error': 'SumUp nicht verfuegbar'})

    name = request.form.get('reader_name', '').strip()
    pairing_code = request.form.get('pairing_code', '').strip()

    if not name or not pairing_code:
        return jsonify({'success': False, 'error': 'Name und Pairing-Code sind erforderlich'})

    result = sumup_service.create_reader(name, pairing_code)
    return jsonify(result)


@settings_bp.route('/integrations/sumup/readers/<reader_id>/delete', methods=['POST'])
@login_required
def sumup_delete_reader(reader_id):
    """Registriertes SumUp-Terminal entfernen"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Nicht berechtigt'})
    if not SUMUP_AVAILABLE:
        return jsonify({'success': False, 'error': 'SumUp nicht verfuegbar'})

    result = sumup_service.delete_reader(reader_id)
    return jsonify(result)


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

        # Besteuerungsart
        settings.steuerart = request.form.get('steuerart', 'soll')

        # Kleinunternehmer
        settings.small_business = request.form.get('small_business') == 'on'
        if settings.small_business:
            settings.small_business_text = request.form.get('small_business_text', '')

        # Express-Aufpreis
        settings.express_surcharge_percent = float(request.form.get('express_surcharge_percent', 0) or 0)
        settings.express_surcharge_fixed = float(request.form.get('express_surcharge_fixed', 0) or 0)
        settings.express_delivery_days = int(request.form.get('express_delivery_days', 1) or 1)

        # Rechtliche Texte
        settings.haftungsausschluss_kundenware = request.form.get('haftungsausschluss_kundenware', '')
        settings.agb_text = request.form.get('agb_text', '')

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

# ==================== SPEICHEREINSTELLUNGEN ====================

@settings_bp.route('/storage', methods=['GET', 'POST'])
@login_required
def storage():
    """Speicherpfad-Einstellungen"""
    if not current_user.is_admin:
        flash('Nur Administratoren können Speichereinstellungen ändern.', 'danger')
        return redirect(url_for('settings.index'))
    
    try:
        from src.models.storage_settings import StorageSettings
        settings = StorageSettings.get_settings()
    except ImportError:
        flash('StorageSettings nicht verfügbar. Bitte Migration ausführen.', 'warning')
        return redirect(url_for('settings.index'))
    
    import os
    default_base = os.path.join(os.path.expanduser('~'), 'StitchAdmin', 'Dokumente')
    validation_errors = []
    
    if request.method == 'POST':
        # Basispfad
        settings.base_path = request.form.get('base_path', '').strip() or default_base
        
        # === SEPARATE ARCHIVE (NAS/Netzlaufwerk) ===
        # Design-Archiv
        settings.design_archiv_aktiv = request.form.get('design_archiv_aktiv') == 'on'
        settings.design_archiv_path = request.form.get('design_archiv_path', '').strip()
        
        # Stickdateien
        settings.stickdateien_aktiv = request.form.get('stickdateien_aktiv') == 'on'
        settings.stickdateien_path = request.form.get('stickdateien_path', '').strip()
        
        # Freigaben-Archiv
        settings.freigaben_archiv_aktiv = request.form.get('freigaben_archiv_aktiv') == 'on'
        settings.freigaben_archiv_path = request.form.get('freigaben_archiv_path', '').strip()
        
        # Motiv-Archiv
        settings.motiv_archiv_aktiv = request.form.get('motiv_archiv_aktiv') == 'on'
        settings.motiv_archiv_path = request.form.get('motiv_archiv_path', '').strip()
        
        # Ordnerstruktur
        settings.folder_structure = request.form.get('folder_structure', 'year_month')
        settings.include_customer_in_filename = request.form.get('include_customer') == 'on'
        settings.include_date_in_filename = request.form.get('include_date') == 'on'
        
        # === CLOUD-SPEICHER (Nextcloud / WebDAV) ===
        settings.cloud_enabled = request.form.get('cloud_enabled') == 'on'
        settings.cloud_type = request.form.get('cloud_type', 'nextcloud')
        settings.cloud_url = request.form.get('cloud_url', '').strip()
        settings.cloud_username = request.form.get('cloud_username', '').strip()
        cloud_pw = request.form.get('cloud_password', '').strip()
        if cloud_pw:
            settings.cloud_password = cloud_pw
        settings.cloud_base_path = request.form.get('cloud_base_path', '/StitchAdmin/Dokumente').strip()
        settings.cloud_sync_rechnungen = request.form.get('cloud_sync_rechnungen') == 'on'
        settings.cloud_sync_angebote = request.form.get('cloud_sync_angebote') == 'on'
        settings.cloud_sync_lieferscheine = request.form.get('cloud_sync_lieferscheine') == 'on'
        settings.cloud_sync_auftraege = request.form.get('cloud_sync_auftraege') == 'on'
        settings.cloud_sync_freigaben = request.form.get('cloud_sync_freigaben') == 'on'
        settings.cloud_sync_mahnungen = request.form.get('cloud_sync_mahnungen') == 'on'
        settings.cloud_sync_backups = request.form.get('cloud_sync_backups') == 'on'

        # Dokumentpfade (relativ)
        settings.angebote_path = request.form.get('angebote_path', 'Angebote')
        settings.auftraege_path = request.form.get('auftraege_path', 'Auftragsbestätigungen')
        settings.lieferscheine_path = request.form.get('lieferscheine_path', 'Lieferscheine')
        settings.rechnungen_ausgang_path = request.form.get('rechnungen_ausgang_path', 'Rechnungen\\Ausgang')
        settings.rechnungen_eingang_path = request.form.get('rechnungen_eingang_path', 'Rechnungen\\Eingang')
        settings.gutschriften_path = request.form.get('gutschriften_path', 'Gutschriften')
        settings.designs_path = request.form.get('designs_path', 'Designs')
        settings.backup_path = request.form.get('backup_path', 'Backups')
        
        # Pfade validieren
        validation_errors = settings.validate_paths()
        
        if not validation_errors:
            # Ordner erstellen falls gewünscht
            if request.form.get('create_folders'):
                if settings.create_folder_structure():
                    flash('Ordnerstruktur erfolgreich erstellt!', 'success')
                else:
                    flash('Ordner konnten nicht erstellt werden.', 'warning')
            
            try:
                db.session.commit()
                flash('Speichereinstellungen gespeichert.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Fehler: {e}', 'danger')
        else:
            for error in validation_errors:
                flash(error, 'danger')
    
    return render_template('settings/storage.html', 
                         settings=settings, 
                         default_base=default_base,
                         validation_errors=validation_errors)


@settings_bp.route('/test-cloud', methods=['POST'])
@login_required
def test_cloud_connection():
    """API: Cloud-Verbindung testen (Nextcloud/WebDAV)"""
    from flask import jsonify

    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Nur Admins'}), 403

    data = request.json or {}

    # Temporaeres Settings-Objekt fuer den Test
    from src.models.storage_settings import StorageSettings
    test_settings = StorageSettings()
    test_settings.cloud_enabled = True
    test_settings.cloud_type = data.get('cloud_type', 'nextcloud')
    test_settings.cloud_url = data.get('cloud_url', '')
    test_settings.cloud_username = data.get('cloud_username', '')
    test_settings.cloud_password = data.get('cloud_password', '')
    test_settings.cloud_base_path = data.get('cloud_base_path', '/StitchAdmin/Dokumente')

    try:
        from src.services.webdav_service import WebDAVService
        service = WebDAVService(settings=test_settings)
        result = service.test_connection()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Fehler: {str(e)}'})


@settings_bp.route('/storage/migrate-paths', methods=['POST'])
@login_required
def migrate_paths():
    """Migriert absolute Dateipfade in der DB zu relativen Pfaden"""
    from flask import jsonify

    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Nur Admins'}), 403

    dry_run = request.json.get('dry_run', True) if request.json else True

    try:
        from src.services.file_storage_service import FileStorageService
        storage = FileStorageService()

        # Alle Models mit Dateipfad-Feldern
        migration_targets = []

        # Design
        try:
            from src.models.design import Design, DesignVersion
            migration_targets.extend([
                (Design, 'file_path'),
                (Design, 'thumbnail_path'),
                (Design, 'preview_path'),
                (Design, 'production_file_path'),
                (DesignVersion, 'file_path'),
                (DesignVersion, 'thumbnail_path'),
            ])
        except ImportError:
            pass

        # Document
        try:
            from src.models.document import Document, EmailAttachment
            migration_targets.extend([
                (Document, 'file_path'),
                (EmailAttachment, 'file_path'),
            ])
        except ImportError:
            pass

        # Order-Workflow
        try:
            from src.models.order_workflow import OrderDesign
            migration_targets.extend([
                (OrderDesign, 'design_file_path'),
                (OrderDesign, 'design_thumbnail_path'),
                (OrderDesign, 'print_file_path'),
            ])
        except ImportError:
            pass

        # Angebot
        try:
            from src.models.angebot import Angebot, AngebotsPosition
            migration_targets.extend([
                (Angebot, 'pdf_path'),
                (AngebotsPosition, 'design_file_path'),
                (AngebotsPosition, 'design_thumbnail_path'),
            ])
        except ImportError:
            pass

        # Inquiry
        try:
            from src.models.inquiry import Inquiry
            migration_targets.append((Inquiry, 'design_file_path'))
        except ImportError:
            pass

        # Contracts
        try:
            from src.models.contracts import Contract
            migration_targets.append((Contract, 'document_path'))
        except ImportError:
            pass

        # Models (Article, LogoDesign)
        try:
            from src.models.models import Article
            migration_targets.extend([
                (Article, 'image_path'),
                (Article, 'image_thumbnail_path'),
            ])
        except ImportError:
            pass

        # Company / Branding / Tenant
        try:
            from src.models.company_settings import CompanySettings
            migration_targets.append((CompanySettings, 'logo_path'))
        except ImportError:
            pass

        try:
            from src.models.tenant import Tenant
            migration_targets.append((Tenant, 'logo_path'))
        except ImportError:
            pass

        # Feedback
        try:
            from src.models.feedback import FeedbackReport
            migration_targets.append((FeedbackReport, 'screenshot_path'))
        except ImportError:
            pass

        # Todo
        try:
            from src.models.todo import Todo
            migration_targets.extend([
                (Todo, 'document_path'),
                (Todo, 'source_file_path'),
                (Todo, 'result_file_path'),
            ])
        except ImportError:
            pass

        all_results = []
        total_migrated = 0
        total_skipped = 0

        for model_class, field_name in migration_targets:
            try:
                result = storage.migrate_absolute_paths(model_class, field_name, dry_run=dry_run)
                if result['migrated'] > 0:
                    all_results.append({
                        'model': model_class.__name__,
                        'field': field_name,
                        'migrated': result['migrated'],
                        'skipped': result['skipped'],
                        'details': result.get('details', [])[:10]  # Max 10 Details
                    })
                total_migrated += result['migrated']
                total_skipped += result['skipped']
            except Exception as e:
                all_results.append({
                    'model': model_class.__name__,
                    'field': field_name,
                    'error': str(e)
                })

        return jsonify({
            'success': True,
            'dry_run': dry_run,
            'total_migrated': total_migrated,
            'total_skipped': total_skipped,
            'results': all_results,
            'message': f"{'Vorschau' if dry_run else 'Migration'}: {total_migrated} Pfade konvertiert, {total_skipped} uebersprungen"
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Fehler: {str(e)}'})


@settings_bp.route('/storage/stats')
@login_required
def storage_stats():
    """Statistiken ueber Dateispeicher"""
    from flask import jsonify

    if not current_user.is_admin:
        return jsonify({'success': False}), 403

    try:
        from src.services.file_storage_service import FileStorageService
        storage = FileStorageService()

        roots = storage.get_storage_roots()
        stats = {
            'base_path': storage.base_path,
            'base_exists': os.path.exists(storage.base_path),
            'roots': roots,
        }

        # Speicherplatz pruefen
        try:
            import shutil
            usage = shutil.disk_usage(storage.base_path)
            stats['disk_total_gb'] = round(usage.total / (1024**3), 1)
            stats['disk_used_gb'] = round(usage.used / (1024**3), 1)
            stats['disk_free_gb'] = round(usage.free / (1024**3), 1)
            stats['disk_percent'] = round(usage.used / usage.total * 100, 1)
        except Exception:
            pass

        # Dateien zaehlen pro Dokumenttyp
        doc_types = ['angebot', 'auftrag', 'rechnung_ausgang', 'rechnung_eingang',
                     'lieferschein', 'design', 'design_freigabe', 'backup']
        type_stats = []
        for dt in doc_types:
            path = storage.settings.get_full_path(dt)
            count = 0
            total_size = 0
            if os.path.exists(path):
                for root, dirs, files in os.walk(path):
                    count += len(files)
                    for f in files:
                        try:
                            total_size += os.path.getsize(os.path.join(root, f))
                        except OSError:
                            pass
            type_stats.append({
                'type': dt,
                'path': path,
                'exists': os.path.exists(path),
                'file_count': count,
                'total_size_mb': round(total_size / (1024*1024), 1) if total_size else 0
            })
        stats['doc_types'] = type_stats

        return jsonify(stats)

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


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


# ==================== VEREDELUNGSARTEN & POSITIONEN ====================

@settings_bp.route('/positionen')
@login_required
def positionen():
    """Veredelungsarten und Positionstypen verwalten"""
    if not current_user.is_admin:
        flash('Nur Administratoren können Positionen verwalten.', 'danger')
        return redirect(url_for('settings.index'))

    from src.models.order_workflow import VeredelungsArt, PositionTyp
    arten = VeredelungsArt.query.order_by(VeredelungsArt.sort_order, VeredelungsArt.name).all()
    typen = PositionTyp.query.order_by(PositionTyp.sort_order, PositionTyp.name).all()
    return render_template('settings/positionen.html', arten=arten, typen=typen)


@settings_bp.route('/positionen/veredelungsart', methods=['POST'])
@login_required
def veredelungsart_save():
    """Veredelungsart erstellen oder bearbeiten"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Keine Berechtigung'}), 403

    from src.models.order_workflow import VeredelungsArt
    art_id = request.form.get('id')
    code = request.form.get('code', '').strip().lower()
    name = request.form.get('name', '').strip()

    if not code or not name:
        flash('Code und Name sind Pflichtfelder.', 'danger')
        return redirect(url_for('settings.positionen'))

    if art_id:
        art = VeredelungsArt.query.get(int(art_id))
        if not art:
            flash('Veredelungsart nicht gefunden.', 'danger')
            return redirect(url_for('settings.positionen'))
    else:
        existing = VeredelungsArt.query.filter_by(code=code).first()
        if existing:
            flash(f'Code "{code}" existiert bereits.', 'danger')
            return redirect(url_for('settings.positionen'))
        art = VeredelungsArt(code=code)
        db.session.add(art)

    art.name = name
    art.beschreibung = request.form.get('beschreibung', '').strip()
    art.icon = request.form.get('icon', 'bi-brush').strip()
    art.farbe = request.form.get('farbe', 'primary').strip()
    art.sort_order = int(request.form.get('sort_order', 0))
    art.aktiv = request.form.get('aktiv') == 'on'

    db.session.commit()
    flash(f'Veredelungsart "{name}" gespeichert.', 'success')
    return redirect(url_for('settings.positionen'))


@settings_bp.route('/positionen/veredelungsart/<int:art_id>/delete', methods=['POST'])
@login_required
def veredelungsart_delete(art_id):
    """Veredelungsart löschen"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Keine Berechtigung'}), 403

    from src.models.order_workflow import VeredelungsArt
    art = VeredelungsArt.query.get_or_404(art_id)
    db.session.delete(art)
    db.session.commit()
    flash(f'Veredelungsart "{art.name}" gelöscht.', 'success')
    return redirect(url_for('settings.positionen'))


@settings_bp.route('/positionen/typ', methods=['POST'])
@login_required
def positiontyp_save():
    """Positionstyp erstellen oder bearbeiten"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Keine Berechtigung'}), 403

    from src.models.order_workflow import PositionTyp
    typ_id = request.form.get('id')
    code = request.form.get('code', '').strip().lower()
    name = request.form.get('name', '').strip()

    if not code or not name:
        flash('Code und Name sind Pflichtfelder.', 'danger')
        return redirect(url_for('settings.positionen'))

    if typ_id:
        typ = PositionTyp.query.get(int(typ_id))
        if not typ:
            flash('Positionstyp nicht gefunden.', 'danger')
            return redirect(url_for('settings.positionen'))
    else:
        existing = PositionTyp.query.filter_by(code=code).first()
        if existing:
            flash(f'Code "{code}" existiert bereits.', 'danger')
            return redirect(url_for('settings.positionen'))
        typ = PositionTyp(code=code)
        db.session.add(typ)

    typ.name = name
    # Mehrfachauswahl: Liste der gewählten Veredelungsart-IDs
    art_ids = request.form.getlist('veredelungsart_ids')
    art_ids = [x for x in art_ids if x.strip().isdigit()]
    typ.veredelungsart_ids = ','.join(art_ids) if art_ids else None
    typ.veredelungsart_id = int(art_ids[0]) if art_ids else None  # Rückwärtskompatibilität
    typ.sort_order = int(request.form.get('sort_order', 0))
    typ.aktiv = request.form.get('aktiv') == 'on'

    db.session.commit()
    flash(f'Positionstyp "{name}" gespeichert.', 'success')
    return redirect(url_for('settings.positionen'))


@settings_bp.route('/positionen/typ/<int:typ_id>/delete', methods=['POST'])
@login_required
def positiontyp_delete(typ_id):
    """Positionstyp löschen"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Keine Berechtigung'}), 403

    from src.models.order_workflow import PositionTyp
    typ = PositionTyp.query.get_or_404(typ_id)
    db.session.delete(typ)
    db.session.commit()
    flash(f'Positionstyp "{typ.name}" gelöscht.', 'success')
    return redirect(url_for('settings.positionen'))


# ==================== TEXTBAUSTEINE ====================

@settings_bp.route('/textbausteine')
@login_required
def textbausteine():
    """Textbausteine für Angebote verwalten"""
    if not current_user.is_admin:
        flash('Nur Administratoren können Textbausteine verwalten.', 'danger')
        return redirect(url_for('settings.index'))

    from src.models.textbaustein import Textbaustein, TEXTBAUSTEIN_CATEGORIES
    bausteine = Textbaustein.query.order_by(Textbaustein.kategorie, Textbaustein.sort_order, Textbaustein.titel).all()
    return render_template('settings/textbausteine.html',
                         bausteine=bausteine,
                         kategorien=TEXTBAUSTEIN_CATEGORIES)


@settings_bp.route('/textbausteine/save', methods=['POST'])
@login_required
def textbaustein_save():
    """Textbaustein erstellen oder bearbeiten"""
    if not current_user.is_admin:
        flash('Keine Berechtigung.', 'danger')
        return redirect(url_for('settings.textbausteine'))

    from src.models.textbaustein import Textbaustein
    tb_id = request.form.get('id')
    titel = request.form.get('titel', '').strip()
    inhalt = request.form.get('inhalt', '').strip()

    if not titel or not inhalt:
        flash('Titel und Inhalt sind Pflichtfelder.', 'danger')
        return redirect(url_for('settings.textbausteine'))

    if tb_id:
        tb = Textbaustein.query.get(int(tb_id))
        if not tb:
            flash('Textbaustein nicht gefunden.', 'danger')
            return redirect(url_for('settings.textbausteine'))
    else:
        tb = Textbaustein(created_by=current_user.username)
        db.session.add(tb)

    tb.titel = titel
    tb.inhalt = inhalt
    tb.kategorie = request.form.get('kategorie', 'sonstiges')
    tb.sort_order = int(request.form.get('sort_order', 0))
    tb.aktiv = request.form.get('aktiv') == 'on'
    tb.ist_standard = request.form.get('ist_standard') == 'on'

    db.session.commit()
    flash(f'Textbaustein "{titel}" gespeichert.', 'success')
    return redirect(url_for('settings.textbausteine'))


@settings_bp.route('/textbausteine/<int:tb_id>/delete', methods=['POST'])
@login_required
def textbaustein_delete(tb_id):
    """Textbaustein löschen"""
    if not current_user.is_admin:
        flash('Keine Berechtigung.', 'danger')
        return redirect(url_for('settings.textbausteine'))

    from src.models.textbaustein import Textbaustein
    tb = Textbaustein.query.get_or_404(tb_id)
    name = tb.titel
    db.session.delete(tb)
    db.session.commit()
    flash(f'Textbaustein "{name}" gelöscht.', 'success')
    return redirect(url_for('settings.textbausteine'))
