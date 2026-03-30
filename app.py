#!/usr/bin/env python3
"""
StitchAdmin 2.0 - Modernisierte ERP-Lösung für Stickerei-Betriebe
Erstellt von Hans Hahn - Alle Rechte vorbehalten

Hauptanwendung mit Flask Application Factory Pattern
"""

import os
import sys
from datetime import datetime, date, timedelta
from flask import Flask, render_template, redirect, url_for, flash, request, send_from_directory, g
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import logging

logger = logging.getLogger(__name__)

# UTF-8 Encoding für Windows
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# ==========================================
# EXE-MODUS ERKENNUNG
# ==========================================
def get_base_path():
    """
    Ermittelt den korrekten Basispfad für EXE oder Python-Modus
    Im EXE-Modus nutzt PyInstaller sys._MEIPASS
    """
    if getattr(sys, 'frozen', False):
        # Läuft als EXE (PyInstaller)
        return sys._MEIPASS
    else:
        # Läuft als Python-Script
        return os.path.dirname(os.path.abspath(__file__))

def get_data_path():
    """
    Ermittelt Pfad für persistente Daten (Datenbank, Uploads)
    Daten sollen im User-Verzeichnis gespeichert werden, nicht im EXE-Temp
    """
    if getattr(sys, 'frozen', False):
        # Im EXE-Modus: Nutze AppData/Local
        app_data = os.path.join(
            os.path.expanduser('~'),
            'AppData',
            'Local',
            'StitchAdmin'
        )
        os.makedirs(app_data, exist_ok=True)
        return app_data
    else:
        # Im Dev-Modus: Nutze Projekt-Verzeichnis
        return os.path.dirname(os.path.abspath(__file__))

# Füge Projekt-Root zum Python-Path hinzu
BASE_DIR = get_base_path()
DATA_DIR = get_data_path()

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def create_app():
    """
    Flask Application Factory
    Erstellt und konfiguriert die Flask-Anwendung
    """
    # Template und Static Pfade (EXE-kompatibel)
    template_path = os.path.join(BASE_DIR, 'src', 'templates')
    static_path = os.path.join(BASE_DIR, 'src', 'static')

    app = Flask(__name__,
                template_folder=template_path,
                static_folder=static_path)

    # ==========================================
    # KONFIGURATION
    # ==========================================
    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        # Persistenten Key aus Datei laden oder erzeugen
        key_file = os.path.join(DATA_DIR, '.secret_key')
        if os.path.exists(key_file):
            with open(key_file, 'r') as f:
                secret_key = f.read().strip()
        else:
            import secrets
            secret_key = secrets.token_hex(32)
            with open(key_file, 'w') as f:
                f.write(secret_key)
    app.config['SECRET_KEY'] = secret_key
    app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'False') == 'True'  # Default: False im EXE

    # Erstelle notwendige Verzeichnisse im DATA_DIR (persistent)
    instance_dir = os.path.join(DATA_DIR, 'instance')
    upload_dir = os.path.join(DATA_DIR, 'uploads')  # Uploads im User-Verzeichnis
    os.makedirs(instance_dir, exist_ok=True)
    os.makedirs(upload_dir, exist_ok=True)

    # Datenbank-Konfiguration (PostgreSQL via DATABASE_URL oder SQLite als Fallback)
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    else:
        db_path = os.path.join(instance_dir, 'stitchadmin.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    # Session-Cookie Sicherheit
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = not app.config.get('DEBUG', False)
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    app.config['REMEMBER_COOKIE_SECURE'] = not app.config.get('DEBUG', False)

    # Upload-Konfiguration
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
    app.config['UPLOAD_FOLDER'] = upload_dir

    # Multi-Tenant (Phase 1: deaktiviert, wird in Phase 2 aktiviert)
    app.config['MULTI_TENANT_ENABLED'] = os.environ.get('MULTI_TENANT_ENABLED', 'False') == 'True'

    # ==========================================
    # DATENBANK INITIALISIERUNG
    # ==========================================
    try:
        from src.models.models import db, User, Customer, Article, Order, Machine, Thread, ActivityLog, Supplier
        db.init_app(app)
        print("[OK] Datenbank-Models erfolgreich importiert")

        # Flask-Migrate fuer Schema-Migrationen
        try:
            from flask_migrate import Migrate
            migrate = Migrate(app, db)
            print("[OK] Flask-Migrate initialisiert")
        except ImportError:
            print("[INFO] Flask-Migrate nicht installiert - nutze db.create_all()")

        # Tenant-Filtering (nur aktiv wenn MULTI_TENANT_ENABLED=True)
        from src.models.tenant_filter import init_tenant_filtering
        init_tenant_filtering(app)

    except ImportError as e:
        print(f"[FEHLER] FEHLER beim Importieren der Models: {e}")
        import traceback
        traceback.print_exc()
        return None

    # ==========================================
    # LOGIN MANAGER
    # ==========================================
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Bitte melden Sie sich an, um auf diese Seite zuzugreifen.'
    login_manager.login_message_category = 'info'

    # ==========================================
    # CSRF-SCHUTZ
    # ==========================================
    from flask_wtf.csrf import CSRFProtect
    csrf = CSRFProtect(app)
    app.config['WTF_CSRF_CHECK_DEFAULT'] = True

    @login_manager.user_loader
    def load_user(user_id):
        """Lädt Benutzer für Flask-Login"""
        from src.models.models import User, db
        return db.session.get(User, user_id)

    # ==========================================
    # GLOBALER LOGIN-SCHUTZ (Vorgelagerte Loginseite)
    # ==========================================
    @app.before_request
    def block_demo_writes():
        """Demo-User duerfen nichts aendern — nur GET-Requests erlaubt"""
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH') and current_user.is_authenticated:
            if getattr(current_user, 'is_demo', False):
                # Logout erlauben
                if request.endpoint == 'auth.logout':
                    return
                from flask import jsonify as jr
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jr({'success': False, 'error': 'Demo-Modus: Aenderungen sind nicht moeglich.'}), 403
                flash('Demo-Modus: Aenderungen sind nicht moeglich. Registrieren Sie sich fuer einen eigenen Account.', 'warning')
                return redirect(request.referrer or url_for('dashboard'))

    @app.after_request
    def set_security_headers(response):
        """Sicherheits-HTTP-Header fuer alle Antworten"""
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        return response

    @app.before_request
    def resolve_tenant():
        """Tenant aus Subdomain oder Custom-Domain ermitteln"""
        g.current_tenant = None
        g.current_tenant_id = None

        main_domain = app.config.get('MAIN_DOMAIN', 'stitchadmin.hahn-it-wuppertal.de')
        host = request.host.split(':')[0]  # Port ignorieren

        if host in ('localhost', '127.0.0.1'):
            return  # Lokal: kein Tenant-Routing

        # Subdomain erkennen: tenant-slug.stitchadmin.hahn-it-wuppertal.de
        if host.endswith('.' + main_domain):
            subdomain = host.replace('.' + main_domain, '')
            if subdomain and subdomain not in ('www', 'api'):
                try:
                    from src.models.tenant import Tenant
                    tenant = Tenant.query.filter_by(subdomain=subdomain, is_active=True).first()
                    if tenant:
                        g.current_tenant = tenant
                        g.current_tenant_id = tenant.id
                except Exception:
                    pass
                # Root auf Tenant-Website weiterleiten
                if request.path == '/' and g.current_tenant:
                    return redirect('/site/', code=302)
            return

        # Custom-Domain erkennen
        if host != main_domain:
            try:
                from src.models.tenant import Tenant
                tenant = Tenant.query.filter_by(custom_domain=host, is_active=True).first()
                if tenant:
                    g.current_tenant = tenant
                    g.current_tenant_id = tenant.id
            except Exception:
                pass
            if request.path == '/':
                return redirect('/site/', code=302)

    @app.before_request
    def require_login():
        """Alle Seiten erfordern Login - kein Zugang ohne Anmeldung"""
        # Erlaubte Endpunkte ohne Login
        public_prefixes = (
            'setup.', 'landing.', 'website.', 'shop.', 'inquiry.', 'tracking.',
        )
        if request.endpoint and (
            request.endpoint in ('auth.login', 'auth.verify_2fa', 'static', 'root',
                                 'favicon', 'manifest', 'apple_touch_icon',
                                 'calendar_sync.callback_microsoft',
                                 'social_media.callback_facebook') or
            any(request.endpoint.startswith(p) for p in public_prefixes) or
            (request.endpoint.startswith('design_approval.') and
             not request.endpoint.startswith('design_approval.admin') and
             not request.endpoint.startswith('design_approval.api_') and
             request.endpoint not in ('design_approval.freigabe_pdf', 'design_approval.download_generated_pdf', 'design_approval.scan_incoming_emails')) or
            (request.endpoint.startswith('quote_approval.') and
             not request.endpoint.startswith('quote_approval.api_'))
        ):
            return

        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        # Tenant-Zugehoerigkeit pruefen: User darf nur in seinem Tenant arbeiten
        if g.get('current_tenant'):
            try:
                from src.models.tenant import UserTenant
                membership = UserTenant.query.filter_by(
                    user_id=current_user.id,
                    tenant_id=g.current_tenant.id,
                    is_active=True
                ).first()
                if not membership and not current_user.is_system_admin:
                    from flask_login import logout_user
                    logout_user()
                    flash('Sie haben keinen Zugang zu diesem Bereich.', 'danger')
                    return redirect(url_for('auth.login'))
            except Exception:
                pass

    # ==========================================
    # BLUEPRINT REGISTRIERUNG
    # ==========================================
    blueprints_registered = []

    def register_blueprint_safe(import_path, blueprint_name, display_name):
        """
        Sichere Blueprint-Registrierung mit Fehlerbehandlung
        """
        try:
            module = __import__(import_path, fromlist=[blueprint_name])
            blueprint = getattr(module, blueprint_name)
            app.register_blueprint(blueprint)
            blueprints_registered.append(display_name)
            print(f"[OK] {display_name} Blueprint registriert")
            return True
        except Exception as e:
            print(f"[WARNUNG] {display_name} Blueprint nicht verfuegbar: {e}")
            import traceback
            if app.config['DEBUG']:
                traceback.print_exc()
            return False

    # Kern-Module
    register_blueprint_safe('src.controllers.customer_controller_db', 'customer_bp', 'Kunden')
    register_blueprint_safe('src.controllers.article_controller_db', 'article_bp', 'Artikel')
    register_blueprint_safe('src.controllers.order_controller_db', 'order_bp', 'Aufträge')
    register_blueprint_safe('src.controllers.machine_controller_db', 'machine_bp', 'Maschinen')
    register_blueprint_safe('src.controllers.thread_controller_db', 'thread_bp', 'Garne')
    register_blueprint_safe('src.controllers.production_controller_db', 'production_bp', 'Produktion')
    register_blueprint_safe('src.controllers.production_time_controller', 'production_time_bp', 'Produktionszeit-Tracking')
    register_blueprint_safe('src.controllers.shipping_controller_db', 'shipping_bp', 'Versand')
    register_blueprint_safe('src.controllers.packing_list_controller', 'packing_list_bp', 'Packlisten')

    # Verwaltungs-Module
    register_blueprint_safe('src.controllers.supplier_controller_db', 'supplier_bp', 'Lieferanten')
    register_blueprint_safe('src.controllers.purchasing_controller', 'purchasing_bp', 'Einkauf')
    register_blueprint_safe('src.controllers.user_controller_db', 'user_bp', 'Benutzer')
    register_blueprint_safe('src.controllers.settings_controller_unified', 'settings_bp', 'Einstellungen')
    register_blueprint_safe('src.controllers.calculation_settings_controller', 'calc_settings_bp', 'Kalkulationseinstellungen')
    register_blueprint_safe('src.controllers.activity_controller_db', 'activity_bp', 'Aktivitäten')

    # Spezial-Module
    register_blueprint_safe('src.controllers.design_workflow_controller', 'design_workflow_bp', 'Design-Workflow')
    register_blueprint_safe('src.controllers.file_browser_controller', 'file_browser_bp', 'Datei-Browser')

    # API
    register_blueprint_safe('src.controllers.api_controller', 'api_bp', 'API')
    register_blueprint_safe('src.controllers.photo_upload_controller', 'photo_upload_bp', 'Foto-Upload')

    # Rechnungsmodul
    try:
        from src.controllers.rechnungsmodul.kasse_controller import kasse_bp
        from src.controllers.rechnungsmodul.rechnung_controller import rechnung_bp
        from src.controllers.buchungen_controller import buchungen_bp
        app.register_blueprint(kasse_bp)
        app.register_blueprint(rechnung_bp)
        app.register_blueprint(buchungen_bp)
        blueprints_registered.append('Kasse')
        blueprints_registered.append('Rechnungen')
        blueprints_registered.append('Buchungsjournal')
        print("[OK] Rechnungsmodul Blueprints registriert")
    except ImportError as e:
        print(f"[WARNUNG] Rechnungsmodul nicht verfuegbar: {e}")

    # Design-Freigabe System
    register_blueprint_safe('src.controllers.design_approval_controller', 'design_approval_bp', 'Design-Freigabe')

    # Design-Archiv & Bestellungen
    register_blueprint_safe('src.controllers.design_controller', 'designs_bp', 'Design-Archiv')

    # Multi-Position-Design API
    register_blueprint_safe('src.controllers.order_design_controller', 'order_design_bp', 'Design-Positionen API')

    # Smart Home Integration
    register_blueprint_safe('src.controllers.shelly_controller', 'shelly_bp', 'Shelly-Geräte')

    # Finanzen-Modul
    register_blueprint_safe('src.controllers.finanzen_controller', 'finanzen_bp', 'Finanzen')
    register_blueprint_safe('src.controllers.angebote_controller', 'angebote_bp', 'Angebote')

    # Auth und Dashboard
    register_blueprint_safe('src.controllers.auth_controller', 'auth_bp', 'Authentifizierung')

    # Dokumente & Post
    register_blueprint_safe('src.controllers.documents.documents_controller', 'documents_bp', 'Dokumente & Post')
    register_blueprint_safe('src.controllers.shipping_bulk_controller', 'shipping_bulk_bp', 'Versand-Bulk')

    # E-Mail Integration
    register_blueprint_safe('src.controllers.email_controller', 'email_bp', 'E-Mail Integration')
    register_blueprint_safe('src.controllers.email_api_controller', 'email_api_bp', 'E-Mail API')

    # CRM - Kundenkontakt-Management
    register_blueprint_safe('src.controllers.crm_controller', 'crm_bp', 'CRM')

    # Dokument-Workflow Admin (Nummernkreise, Zahlungsbedingungen)
    register_blueprint_safe('src.controllers.document_admin_controller', 'document_admin_bp', 'Dokument-Admin')

    # Update & Backup System
    register_blueprint_safe('src.controllers.update_controller', 'update_bp', 'Updates & Backups')

    # Permission-System
    register_blueprint_safe('src.controllers.permissions_controller', 'permissions_bp', 'Berechtigungsverwaltung')
    register_blueprint_safe('src.controllers.dashboard_api_controller', 'dashboard_api_bp', 'Dashboard-API')

    # Design-Erstellung (Fremd- und Eigenerstellung)
    register_blueprint_safe('src.controllers.design_creation_controller', 'design_creation_bp', 'Design-Erstellung')

    # Auftrags-Wizard (Step-by-Step Auftragserfassung)
    register_blueprint_safe('src.controllers.order_wizard_controller', 'wizard_bp', 'Auftrags-Wizard')

    # Angebote-Workflow (Document-Workflow Integration)
    register_blueprint_safe('src.controllers.angebote_workflow_controller', 'angebote_workflow_bp', 'Angebote-Workflow')

    # Auftragsbestätigungen (Document-Workflow Integration)
    register_blueprint_safe('src.controllers.auftraege_controller', 'auftraege_bp', 'Auftragsbestätigungen')

    # Lieferscheine (Document-Workflow Integration)
    register_blueprint_safe('src.controllers.lieferscheine_controller', 'lieferscheine_bp', 'Lieferscheine')

    # Rechnungen (Document-Workflow Integration)
    register_blueprint_safe('src.controllers.rechnungen_controller', 'rechnungen_bp', 'Rechnungen')

    # Setup-Wizard (Erstinstallation)
    register_blueprint_safe('src.controllers.setup_wizard_controller', 'setup_bp', 'Setup-Wizard')
    
    # Buchhaltung & Controlling
    register_blueprint_safe('src.controllers.buchhaltung_controller', 'buchhaltung_bp', 'Buchhaltung')
    
    # Kalender (Outlook-Style)
    register_blueprint_safe('src.controllers.kalender_controller', 'kalender_bp', 'Kalender')

    # Oeffentliche Website (Startseite ohne Login)
    register_blueprint_safe('src.controllers.website_controller', 'website_bp', 'Website')

    # Oeffentlicher Shop (Konfigurator, Warenkorb, Checkout - ohne Login)
    register_blueprint_safe('src.controllers.shop_controller', 'shop_bp', 'Shop')

    # Shop-Verwaltung (Admin-Bereich, Login erforderlich)
    register_blueprint_safe('src.controllers.shop_admin_controller', 'shop_admin_bp', 'Shop-Verwaltung')

    # Oeffentliches Anfrage-Formular (ohne Login)
    register_blueprint_safe('src.controllers.inquiry_controller', 'inquiry_bp', 'Anfragen (öffentlich)')

    # Einheitliches Tracking (öffentlich)
    register_blueprint_safe('src.controllers.inquiry_controller', 'tracking_bp', 'Auftrags-Tracking (öffentlich)')

    # Anfragen-Verwaltung (Admin-Bereich, Login erforderlich)
    register_blueprint_safe('src.controllers.inquiry_admin_controller', 'inquiry_admin_bp', 'Anfragen-Verwaltung')

    # Website-CMS (Admin-Bereich, Login erforderlich)
    register_blueprint_safe('src.controllers.website_admin_controller', 'website_admin_bp', 'Website-CMS')

    # CSV-Import
    register_blueprint_safe('src.controllers.csv_import_controller', 'csv_import_bp', 'CSV-Import')

    # Vertraege & Policen
    register_blueprint_safe('src.controllers.contracts_controller', 'contracts_bp', 'Vertraege')

    # E-Mail Automation
    register_blueprint_safe('src.controllers.email_automation_controller', 'email_automation_bp', 'E-Mail-Automation')

    # Landing Page & Registrierung (oeffentlich)
    register_blueprint_safe('src.controllers.landing_controller', 'landing_bp', 'Landing Page')

    # Plattform-Administration (SaaS Tenant-Verwaltung)
    register_blueprint_safe('src.controllers.platform_admin_controller', 'platform_admin_bp', 'Plattform-Admin')

    # Billing Dashboard (Tenant-seitig: Plan, Nutzung, Zahlungen)
    register_blueprint_safe('src.controllers.billing_controller', 'billing_bp', 'Billing')

    # Banking
    register_blueprint_safe('src.controllers.banking_controller', 'banking_bp', 'Bankkonten')

    # E-Mail-Sync
    register_blueprint_safe('src.controllers.email_sync_controller', 'email_sync_bp', 'E-Mail-Sync')

    # Kalender-Sync
    register_blueprint_safe('src.controllers.calendar_sync_controller', 'calendar_sync_bp', 'Kalender-Sync')

    # Social Media
    register_blueprint_safe('src.controllers.social_media_controller', 'social_media_bp', 'Social Media')

    # Aufgaben-Board (Zentrale Aufgabenverwaltung)
    register_blueprint_safe('src.controllers.taskboard_controller', 'taskboard_bp', 'Aufgaben-Board')

    # Angebots-Freigabe (oeffentlich + Admin)
    register_blueprint_safe('src.controllers.quote_approval_controller', 'quote_approval_bp', 'Angebots-Freigabe')

    # Veredelungsverfahren (Einstellungen + API)
    register_blueprint_safe('src.controllers.veredelung_controller', 'veredelung_bp', 'Veredelung')

    # Energie / Stromzähler
    register_blueprint_safe('src.controllers.energie_controller', 'energie_bp', 'Stromzähler')

    # Feedback / Bug-Melder
    register_blueprint_safe('src.controllers.feedback_controller', 'feedback_bp', 'Feedback')

    # Dashboard ist als Thin-Wrapper in app.py, Logik in src/controllers/dashboard_controller.py

    # CSRF-Ausnahmen fuer oeffentliche Blueprints und JSON-APIs
    for bp_name in ['shop', 'inquiry', 'tracking', 'website', 'design_approval', 'quote_approval', 'production_time', 'kasse', 'rechnung']:
        bp = app.blueprints.get(bp_name)
        if bp:
            csrf.exempt(bp)

    # Einzelne externe Routen von CSRF ausnehmen (Token-basierte Auth / JSON-APIs)
    for view_name in ['shipping.abholung_unterschrift_extern_speichern',
                      'customers.api_search', 'customers.api_quick_create',
                      'customers.api_customers', 'settings.test_cloud_connection',
                      'wizard.api_artikel_suche', 'wizard.api_artikel_varianten',
                      'feedback.submit', 'feedback.update_status']:
        if view_name in app.view_functions:
            csrf.exempt(app.view_functions[view_name])

    # ==========================================
    # FAVICON - Dynamisch aus Firmenlogo
    # ==========================================
    @app.route('/favicon.ico')
    def favicon():
        """Favicon aus Branding-Logo oder Default"""
        try:
            from src.models.branding_settings import BrandingSettings
            branding = BrandingSettings.get_settings()
            if branding and branding.logo_path:
                logo_dir = os.path.dirname(branding.logo_path)
                logo_file = os.path.basename(branding.logo_path)
                return send_from_directory(
                    os.path.join(app.static_folder, logo_dir),
                    logo_file, max_age=86400
                )
        except Exception:
            pass
        return send_from_directory(app.static_folder, 'favicon.ico', max_age=86400)

    @app.route('/manifest.json')
    def manifest():
        """PWA Web App Manifest - dynamisch aus Branding"""
        from flask import jsonify as json_response
        try:
            from src.models.branding_settings import BrandingSettings
            from src.models.company_settings import CompanySettings
            branding = BrandingSettings.get_settings()
            company = CompanySettings.get_settings()
            name = company.company_name if company and company.company_name else 'StitchAdmin'
            color = branding.primary_color if branding and branding.primary_color else '#1a6b5a'
            icons = []
            if branding and branding.logo_path:
                logo_url = url_for('static', filename=branding.logo_path, _external=True)
                icons = [
                    {'src': logo_url, 'sizes': '192x192', 'type': 'image/png'},
                    {'src': logo_url, 'sizes': '512x512', 'type': 'image/png'},
                ]
        except Exception:
            name = 'StitchAdmin'
            color = '#1a6b5a'
            icons = []

        manifest_data = {
            'name': name,
            'short_name': name[:12],
            'start_url': '/',
            'display': 'standalone',
            'background_color': '#ffffff',
            'theme_color': color,
            'icons': icons,
        }
        response = json_response(manifest_data)
        response.headers['Cache-Control'] = 'public, max-age=86400'
        return response

    @app.route('/apple-touch-icon.png')
    def apple_touch_icon():
        """Apple Touch Icon aus Branding-Logo"""
        try:
            from src.models.branding_settings import BrandingSettings
            branding = BrandingSettings.get_settings()
            if branding and branding.logo_path:
                logo_dir = os.path.dirname(branding.logo_path)
                logo_file = os.path.basename(branding.logo_path)
                return send_from_directory(
                    os.path.join(app.static_folder, logo_dir),
                    logo_file, max_age=86400
                )
        except Exception:
            pass
        return send_from_directory(app.static_folder, 'favicon.ico', max_age=86400)

    # ==========================================
    # HAUPT-ROUTEN
    # ==========================================
    @app.route('/app')
    def root():
        """App-Einstieg - Redirect zum Dashboard oder Landing"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('landing.index'))

    # Dashboard-Route: Weiterleitung zum ausgelagerten Blueprint
    @app.route('/dashboard', endpoint='dashboard')
    @login_required
    def dashboard():
        from src.controllers.dashboard_controller import dashboard as _dashboard_view
        return _dashboard_view()

    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        """
        Stellt Upload-Dateien bereit (Fotos, Thumbnails, etc.)
        """
        upload_folder = app.config.get('UPLOAD_FOLDER', 'instance/uploads')
        return send_from_directory(upload_folder, filename)

    @app.template_filter('format_date')
    def format_date_filter(date_obj, format_string='%d.%m.%Y'):
        """Formatiert Datum für Templates"""
        if date_obj is None:
            return '-'
        try:
            if isinstance(date_obj, str):
                date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
            return date_obj.strftime(format_string)
        except (AttributeError, ValueError):
            return str(date_obj)

    @app.template_filter('format_datetime')
    def format_datetime_filter(date_obj, format_string='%d.%m.%Y %H:%M'):
        """Formatiert Datum+Zeit für Templates"""
        if date_obj is None:
            return '-'
        try:
            if isinstance(date_obj, str):
                date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
            return date_obj.strftime(format_string)
        except (AttributeError, ValueError):
            return str(date_obj)

    @app.template_filter('format_currency')
    def format_currency_filter(value):
        """Formatiert Währung für Templates"""
        try:
            return f"{float(value):.2f} €"
        except (TypeError, ValueError):
            return "0.00 €"

    @app.template_filter('calculate_age')
    def calculate_age_filter(birth_date):
        """Berechnet Alter aus Geburtsdatum"""
        if not birth_date:
            return None
        try:
            if isinstance(birth_date, str):
                birth_date = datetime.fromisoformat(birth_date.replace('Z', '+00:00')).date()
            today = date.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            return age
        except (AttributeError, ValueError, TypeError):
            return None

    @app.template_filter('format_number')
    def format_number_filter(value, decimals=0):
        """Formatiert Zahlen"""
        try:
            if decimals == 0:
                return f"{int(value):,}".replace(',', '.')
            else:
                return f"{float(value):,.{decimals}f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        except (TypeError, ValueError):
            return value

    @app.template_filter('format_percent')
    def format_percent_filter(value):
        """Formatiert Prozent"""
        try:
            return f"{float(value):.1f}%"
        except (TypeError, ValueError):
            return "0%"

    @app.template_filter('is_design_link')
    def is_design_link_filter(value):
        """Prüft ob der Wert ein Link (URL) ist"""
        if not value:
            return False
        value_str = str(value)
        return value_str.startswith('http://') or value_str.startswith('https://') or value_str.startswith('link:')

    @app.template_filter('show_graphics_manager')
    def show_graphics_manager_filter(order_id):
        """Prüft ob der Grafikmanager-Button angezeigt werden soll (nur wenn kein Design vorhanden)"""
        try:
            from src.models.models import Order
            order = Order.query.get(order_id)
            if not order:
                return False
            # Zeige Grafikmanager nur wenn KEIN Design vorhanden ist
            return not (order.design_file_path or order.design_file)
        except Exception as e:
            # Bei Fehler: Grafikmanager NICHT anzeigen
            return False

    @app.template_filter('basename')
    def basename_filter(value):
        """Gibt den Dateinamen aus einem Pfad zurück"""
        if not value:
            return ''
        return os.path.basename(str(value))

    @app.template_filter('file_url')
    def file_url_filter(relative_path):
        """Generiert file:// URL aus relativem DB-Pfad fuer Hyperlinks"""
        if not relative_path:
            return '#'
        try:
            from src.services.file_storage_service import FileStorageService
            return FileStorageService().get_file_url(relative_path)
        except Exception:
            return '#'

    @app.template_filter('file_open_url')
    def file_open_url_filter(relative_path):
        """Generiert /file_browser/open?path=... URL zum Oeffnen via Server"""
        if not relative_path:
            return '#'
        from urllib.parse import quote
        return f"/file_browser/open?path={quote(str(relative_path))}"

    @app.template_filter('file_exists')
    def file_exists_filter(relative_path):
        """Prueft ob eine Datei existiert (fuer bedingte Anzeige)"""
        if not relative_path:
            return False
        try:
            from src.services.file_storage_service import FileStorageService
            return FileStorageService().file_exists(relative_path)
        except Exception:
            return False

    # ==========================================
    # CONTEXT PROCESSORS
    # ==========================================
    @app.context_processor
    def inject_globals():
        """Globale Template-Variablen, inkl. Branding."""
        from datetime import date
        
        try:
            from src.models.branding_settings import BrandingSettings
            branding_settings = BrandingSettings.get_settings()
        except (ImportError, Exception):
            branding_settings = None

        
        # Permission-Helper registrieren
        try:
            from src.utils.permissions import register_permission_helpers
            register_permission_helpers(app)
        except (ImportError, Exception):
            pass

        # Tenant-Plan-Info fuer Templates (Trial-Banner, etc.)
        tenant_plan = None
        try:
            from src.utils.plan_gate import get_tenant_plan_info
            tenant_plan = get_tenant_plan_info()
        except (ImportError, Exception):
            pass

        # Dynamische Position/Veredelungs-Choices
        position_choices = []
        design_type_choices = []
        try:
            from src.models.order_workflow import OrderDesign
            position_choices = OrderDesign.get_position_choices_dynamic()
            design_type_choices = OrderDesign.get_design_type_choices_dynamic()
        except Exception:
            pass

        # Demo-Modus: Branding ueberschreiben
        if current_user.is_authenticated and getattr(current_user, 'is_demo', False):
            class DemoBranding:
                company_name = 'Muster Stickerei GmbH'
                logo_path = None
                primary_color = '#1a6b5a'
                secondary_color = '#6c757d'
            branding_settings = DemoBranding()

        return {
            'app_name': 'StitchAdmin 2.0',
            'app_version': '2.0.2',
            'branding': branding_settings,
            'today': date.today(),
            'tenant_plan': tenant_plan,
            'position_choices': position_choices,
            'design_type_choices': design_type_choices,
        }

    # ==========================================
    # ERROR HANDLERS
    # ==========================================
    # ... (unverändert)

    # ==========================================
    # DATENBANK-TABELLEN ERSTELLEN (auch für Gunicorn)
    # ==========================================
    with app.app_context():
        from src.models.models import db as _db, User
        # Tenant-Models importieren damit create_all() die Tabellen kennt
        from src.models.tenant import Tenant, UserTenant, TenantPayment  # noqa: F401
        from src.models.csv_import import CSVImportJob  # noqa: F401
        from src.models.contracts import Contract, ContractContact, ContractCommunication  # noqa: F401
        from src.models.email_automation import EmailAutomationRule, EmailAutomationLog  # noqa: F401
        from src.models.banking import BankAccount, BankTransaction  # noqa: F401
        from src.models.calendar_sync import CalendarConnection, CalendarSyncMapping  # noqa: F401
        from src.models.social_media import SocialMediaAccount, SocialMediaPost  # noqa: F401
        from src.models.order_workflow import VeredelungsArt, PositionTyp  # noqa: F401
        from src.models.veredelung import VeredelungsVerfahren, VeredelungsPosition, VeredelungsParameter, ArtikelVeredelung  # noqa: F401
        from src.models.production_job import ProductionJob  # noqa: F401
        from src.models.energie import StromAblesung, StromTarif  # noqa: F401
        try:
            _db.create_all()
        except Exception as e:
            _db.session.rollback()
            print(f"[WARN] create_all() Worker-Race-Condition: {e}")

        # Standard-Veredelungsarten und Positionstypen erstellen
        try:
            VeredelungsArt.ensure_defaults()
            PositionTyp.ensure_defaults()
        except Exception as e:
            _db.session.rollback()
            print(f"[INFO] ensure_defaults: {e}")

        # APScheduler fuer Hintergrund-Jobs (Social Media, E-Mail, Bank-Sync)
        try:
            from src.services.scheduler_service import init_scheduler
            init_scheduler(app)
        except ImportError:
            print("[INFO] APScheduler nicht installiert - Hintergrund-Jobs deaktiviert")

        # Migriere neue Spalte: customers.is_active
        try:
            _db.session.execute(_db.text(
                "ALTER TABLE customers ADD COLUMN is_active BOOLEAN DEFAULT TRUE"
            ))
            _db.session.commit()
            print("[OK] customers.is_active Spalte hinzugefuegt")
        except Exception:
            _db.session.rollback()

        # Migriere neue Spalte: users.is_system_admin
        try:
            _db.session.execute(_db.text(
                "ALTER TABLE users ADD COLUMN is_system_admin BOOLEAN DEFAULT FALSE"
            ))
            _db.session.commit()
            print("[OK] users.is_system_admin Spalte hinzugefuegt")
        except Exception:
            _db.session.rollback()  # Spalte existiert bereits

        # Migriere Billing-Spalten fuer Tenants
        billing_columns = [
            ("tenants", "billing_status", "VARCHAR(30) DEFAULT 'active'"),
            ("tenants", "billing_cycle", "VARCHAR(20) DEFAULT 'monthly'"),
            ("tenants", "next_billing_date", "DATE"),
            ("tenants", "last_payment_date", "DATE"),
            ("tenants", "last_payment_amount", "NUMERIC(10,2)"),
            ("tenants", "stripe_customer_id", "VARCHAR(100)"),
            ("tenants", "stripe_subscription_id", "VARCHAR(100)"),
            ("tenants", "tax_id", "VARCHAR(50)"),
        ]
        for table, col, col_type in billing_columns:
            try:
                _db.session.execute(_db.text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                _db.session.commit()
            except Exception:
                _db.session.rollback()

        # Migriere Auftrags-Feature-Spalten (Rechnungsempfaenger, Sublimation etc.)
        feature_columns = [
            ("orders", "billing_customer_id", "VARCHAR(50)"),
            ("order_items", "sublimation_position", "VARCHAR(50)"),
            ("order_items", "is_non_textile", "BOOLEAN DEFAULT FALSE"),
            ("order_items", "non_textile_type", "VARCHAR(100)"),
        ]
        for table, col, col_type in feature_columns:
            try:
                _db.session.execute(_db.text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                _db.session.commit()
            except Exception:
                _db.session.rollback()

        # Migriere neue Spalten fuer Shop + Anfragen
        shop_columns = [
            ("orders", "source", "VARCHAR(20)"),
            ("orders", "tracking_token", "VARCHAR(64)"),
            ("orders", "customer_email_for_tracking", "VARCHAR(200)"),
            ("orders", "archived_at", "DATETIME"),
            ("orders", "archived_by", "VARCHAR(80)"),
            ("orders", "archive_reason", "VARCHAR(200)"),
            ("articles", "show_in_shop", "BOOLEAN DEFAULT FALSE"),
            ("articles", "shop_description", "TEXT"),
            ("articles", "shop_image_path", "VARCHAR(255)"),
            ("articles", "shop_category_id", "INTEGER"),
            ("articles", "shop_sort_order", "INTEGER DEFAULT 0"),
            ("articles", "shop_min_quantity", "INTEGER DEFAULT 1"),
        ]
        for table, col, col_type in shop_columns:
            try:
                _db.session.execute(_db.text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                _db.session.commit()
            except Exception:
                _db.session.rollback()

        # Migriere OrderDesign: Notizen + Externe Bestellung + Druckdatei
        design_supplier_columns = [
            ("order_designs", "notes", "TEXT"),
            ("order_designs", "supplier_id", "VARCHAR(50)"),
            ("order_designs", "supplier_order_status", "VARCHAR(50) DEFAULT 'none'"),
            ("order_designs", "supplier_order_date", "DATE"),
            ("order_designs", "supplier_expected_date", "DATE"),
            ("order_designs", "supplier_delivered_date", "DATE"),
            ("order_designs", "supplier_order_notes", "TEXT"),
            ("order_designs", "supplier_cost", "FLOAT"),
            ("order_designs", "supplier_order_id", "VARCHAR(50)"),
            ("order_designs", "supplier_reference", "VARCHAR(100)"),
            ("order_designs", "print_file_path", "VARCHAR(255)"),
            ("order_designs", "print_file_name", "VARCHAR(255)"),
        ]
        for table, col, col_type in design_supplier_columns:
            try:
                _db.session.execute(_db.text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                _db.session.commit()
            except Exception:
                _db.session.rollback()

        # SumUp-Felder in CompanySettings
        sumup_columns = [
            ("company_settings", "sumup_api_key", "VARCHAR(500)"),
            ("company_settings", "sumup_merchant_code", "VARCHAR(100)"),
        ]
        for table, col, col_type in sumup_columns:
            try:
                _db.session.execute(_db.text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                _db.session.commit()
            except Exception:
                _db.session.rollback()

        # Artikelbild-Felder + Google API Keys
        image_columns = [
            ("articles", "image_url", "VARCHAR(500)"),
            ("articles", "image_path", "VARCHAR(255)"),
            ("articles", "image_thumbnail_path", "VARCHAR(255)"),
            ("company_settings", "google_api_key", "VARCHAR(200)"),
            ("company_settings", "google_search_cx", "VARCHAR(100)"),
        ]
        for table, col, col_type in image_columns:
            try:
                _db.session.execute(_db.text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                _db.session.commit()
            except Exception:
                _db.session.rollback()

        # Lieferantenbestellungen: Wareneingang-Felder
        so_columns = [
            ("supplier_orders", "delivery_note_photo", "VARCHAR(500)"),
            ("supplier_orders", "actual_delivery_date", "DATE"),
            ("supplier_orders", "receiving_notes", "TEXT"),
        ]
        for table, col, col_type in so_columns:
            try:
                _db.session.execute(_db.text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                _db.session.commit()
            except Exception:
                _db.session.rollback()

        # Performance-Indexes fuer haeufig gefilterte Spalten
        order_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_order_workflow_status ON orders (workflow_status)",
            "CREATE INDEX IF NOT EXISTS idx_order_design_approval_status ON orders (design_approval_status)",
            "CREATE INDEX IF NOT EXISTS idx_order_payment_status ON orders (payment_status)",
            "CREATE INDEX IF NOT EXISTS idx_order_archived_at ON orders (archived_at)",
            "CREATE INDEX IF NOT EXISTS idx_order_active ON orders (archived_at, workflow_status)",
            "CREATE INDEX IF NOT EXISTS idx_order_customer_created ON orders (customer_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_inquiry_status ON inquiries (status)",
            "CREATE INDEX IF NOT EXISTS idx_inquiry_created ON inquiries (created_at)",
            "CREATE INDEX IF NOT EXISTS idx_supplier_order_status ON supplier_orders (status)",
            "CREATE INDEX IF NOT EXISTS idx_supplier_order_delivery ON supplier_orders (delivery_date)",
        ]
        for idx_sql in order_indexes:
            try:
                _db.session.execute(_db.text(idx_sql))
                _db.session.commit()
            except Exception:
                _db.session.rollback()

        # scan_foto Spalte fuer Rechnungs-Scanner
        try:
            _db.session.execute(_db.text("ALTER TABLE rechnungen ADD COLUMN scan_foto VARCHAR(500)"))
            _db.session.commit()
        except Exception:
            _db.session.rollback()

        # DPD-Kundennummer in CompanySettings
        try:
            _db.session.execute(_db.text("ALTER TABLE company_settings ADD COLUMN dpd_customer_number VARCHAR(20)"))
            _db.session.commit()
        except Exception:
            _db.session.rollback()

        # Angebots-Verknüpfung in Inquiries
        try:
            _db.session.execute(_db.text("ALTER TABLE inquiries ADD COLUMN angebot_id INTEGER REFERENCES angebote(id)"))
            _db.session.commit()
        except Exception:
            _db.session.rollback()

        # Aufgaben: Privat/Öffentlich Sichtbarkeit
        try:
            _db.session.execute(_db.text("ALTER TABLE todos ADD COLUMN is_private BOOLEAN DEFAULT TRUE"))
            _db.session.commit()
        except Exception:
            _db.session.rollback()

        # Tracking-Token für Angebote (einheitliches Tracking)
        try:
            _db.session.execute(_db.text("ALTER TABLE angebote ADD COLUMN tracking_token VARCHAR(64) UNIQUE"))
            _db.session.execute(_db.text("CREATE INDEX idx_angebote_tracking_token ON angebote(tracking_token)"))
            _db.session.commit()
        except Exception:
            _db.session.rollback()

        # Bestehende Angebote ohne Token mit Token versehen
        try:
            import uuid as _uuid
            result = _db.session.execute(_db.text("SELECT id FROM angebote WHERE tracking_token IS NULL"))
            for row in result.fetchall():
                _db.session.execute(_db.text("UPDATE angebote SET tracking_token = :token WHERE id = :id"),
                                    {'token': _uuid.uuid4().hex, 'id': row[0]})
            _db.session.commit()
        except Exception:
            _db.session.rollback()

        # Kundenware-Felder
        try:
            _db.session.execute(_db.text("ALTER TABLE orders ADD COLUMN is_kundenware BOOLEAN DEFAULT FALSE"))
            _db.session.commit()
        except Exception:
            _db.session.rollback()

        try:
            _db.session.execute(_db.text("ALTER TABLE angebote ADD COLUMN is_kundenware BOOLEAN DEFAULT FALSE"))
            _db.session.commit()
        except Exception:
            _db.session.rollback()

        # Auftragstyp fuer Angebote (wird bei Umwandlung an Auftrag uebergeben)
        try:
            _db.session.execute(_db.text("ALTER TABLE angebote ADD COLUMN auftragstyp VARCHAR(20) DEFAULT 'embroidery'"))
            _db.session.commit()
        except Exception:
            _db.session.rollback()

        # Rechtliche Texte in Firmeneinstellungen
        try:
            _db.session.execute(_db.text("ALTER TABLE company_settings ADD COLUMN haftungsausschluss_kundenware TEXT DEFAULT ''"))
            _db.session.execute(_db.text("ALTER TABLE company_settings ADD COLUMN agb_text TEXT DEFAULT ''"))
            _db.session.commit()
        except Exception:
            _db.session.rollback()

        # Textbausteine-Tabelle fuer Angebote (wiederverwendbare Textbloecke)
        try:
            _db.session.execute(_db.text("""
                CREATE TABLE IF NOT EXISTS textbausteine (
                    id SERIAL PRIMARY KEY,
                    titel VARCHAR(200) NOT NULL,
                    inhalt TEXT NOT NULL,
                    kategorie VARCHAR(50) DEFAULT 'sonstiges',
                    sort_order INTEGER DEFAULT 0,
                    aktiv BOOLEAN DEFAULT TRUE,
                    ist_standard BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(80),
                    updated_at TIMESTAMP
                )
            """))
            _db.session.commit()
            print('[OK] Textbausteine-Tabelle erstellt')
        except Exception:
            _db.session.rollback()

        # Textbausteine-Feld im Angebot (JSON mit ausgewaehlten IDs)
        try:
            _db.session.execute(_db.text("ALTER TABLE angebote ADD COLUMN textbausteine_ids TEXT DEFAULT ''"))
            _db.session.execute(_db.text("ALTER TABLE angebote ADD COLUMN textbausteine_text TEXT DEFAULT ''"))
            _db.session.commit()
        except Exception:
            _db.session.rollback()

        # Standard-Textbausteine anlegen
        try:
            from src.models.textbaustein import Textbaustein
            Textbaustein.ensure_defaults()
        except Exception as e:
            _db.session.rollback()
            print(f'[WARN] Textbausteine defaults: {e}')

        # Angebots-Freigabe Felder
        for col in [
            "approval_token VARCHAR(100) UNIQUE",
            "approval_status VARCHAR(50)",
            "approval_sent_at TIMESTAMP",
            "approval_date TIMESTAMP",
            "approval_signature TEXT",
            "approval_ip VARCHAR(50)",
            "approval_user_agent VARCHAR(500)",
            "approval_notes TEXT",
            "approved_by_name VARCHAR(200)"
        ]:
            try:
                _db.session.execute(_db.text(f"ALTER TABLE angebote ADD COLUMN {col}"))
                _db.session.commit()
            except Exception:
                _db.session.rollback()

        # Standard E-Mail-Templates fuer Kunden-Benachrichtigungen
        try:
            from src.models.crm_contact import EmailTemplate, EmailTemplateCategory
            from src.models.email_automation import EmailAutomationRule

            if EmailTemplate.query.filter_by(category=EmailTemplateCategory.AUFTRAG_BESTAETIGUNG).count() == 0:
                _templates = [
                    (EmailTemplateCategory.AUFTRAG_BESTAETIGUNG, 'Auftragsbestaetigung',
                     'Ihr Auftrag {auftragsnummer} wurde angenommen',
                     'Guten Tag {anrede} {kunde_name},\n\nvielen Dank fuer Ihren Auftrag {auftragsnummer}.\nWir haben Ihren Auftrag erhalten und werden ihn schnellstmoeglich bearbeiten.\n\nMit freundlichen Gruessen\n{firmenname}',
                     '<p>Guten Tag {anrede} {kunde_name},</p><p>vielen Dank fuer Ihren Auftrag <strong>{auftragsnummer}</strong>.</p><p>Wir haben Ihren Auftrag erhalten und werden ihn schnellstmoeglich bearbeiten.</p><p>Mit freundlichen Gruessen<br>{firmenname}</p>',
                     'order_status', 'accepted'),

                    (EmailTemplateCategory.PRODUKTION_GEPLANT, 'Ware im Zulauf',
                     'Material fuer Ihren Auftrag {auftragsnummer} ist bestellt',
                     'Guten Tag {anrede} {kunde_name},\n\ndie Materialien fuer Ihren Auftrag {auftragsnummer} sind bestellt.\nSobald alles eingetroffen ist, starten wir mit der Produktion.\n\nMit freundlichen Gruessen\n{firmenname}',
                     '<p>Guten Tag {anrede} {kunde_name},</p><p>die Materialien fuer Ihren Auftrag <strong>{auftragsnummer}</strong> sind bestellt.</p><p>Sobald alles eingetroffen ist, starten wir mit der Produktion.</p><p>Mit freundlichen Gruessen<br>{firmenname}</p>',
                     'workflow_status', 'confirmed'),

                    (EmailTemplateCategory.PRODUKTION_GEPLANT, 'Produktion gestartet',
                     'Ihr Auftrag {auftragsnummer} ist in Produktion',
                     'Guten Tag {anrede} {kunde_name},\n\nIhr Auftrag {auftragsnummer} befindet sich jetzt in der Produktion.\nWir informieren Sie, sobald Ihr Auftrag fertiggestellt ist.\n\nMit freundlichen Gruessen\n{firmenname}',
                     '<p>Guten Tag {anrede} {kunde_name},</p><p>Ihr Auftrag <strong>{auftragsnummer}</strong> befindet sich jetzt in der Produktion.</p><p>Wir informieren Sie, sobald Ihr Auftrag fertiggestellt ist.</p><p>Mit freundlichen Gruessen<br>{firmenname}</p>',
                     'order_status', 'in_progress'),

                    (EmailTemplateCategory.QM_ABNAHME, 'Auftrag fertig',
                     'Ihr Auftrag {auftragsnummer} ist fertig!',
                     'Guten Tag {anrede} {kunde_name},\n\nIhr Auftrag {auftragsnummer} ist fertiggestellt und bereit zur Abholung bzw. zum Versand.\n\nMit freundlichen Gruessen\n{firmenname}',
                     '<p>Guten Tag {anrede} {kunde_name},</p><p>Ihr Auftrag <strong>{auftragsnummer}</strong> ist fertiggestellt und bereit zur Abholung bzw. zum Versand.</p><p>Mit freundlichen Gruessen<br>{firmenname}</p>',
                     'order_status', 'ready'),

                    (EmailTemplateCategory.VERSAND_INFO, 'Versendet mit Tracking',
                     'Ihr Auftrag {auftragsnummer} wurde versendet',
                     'Guten Tag {anrede} {kunde_name},\n\nIhr Auftrag {auftragsnummer} wurde versendet.\nVersanddienstleister: {versanddienstleister}\nSendungsnummer: {sendungsnummer}\n\nMit freundlichen Gruessen\n{firmenname}',
                     '<p>Guten Tag {anrede} {kunde_name},</p><p>Ihr Auftrag <strong>{auftragsnummer}</strong> wurde versendet.</p><table style="background:#f8f9fa;padding:15px;border-radius:8px;margin:15px 0;width:100%"><tr><td><strong>Versand:</strong></td><td>{versanddienstleister}</td></tr><tr><td><strong>Sendungsnr.:</strong></td><td>{sendungsnummer}</td></tr></table><p>Mit freundlichen Gruessen<br>{firmenname}</p>',
                     'workflow_status', 'shipped'),
                ]

                for cat, name, subj, text, html, trigger_evt, trigger_val in _templates:
                    tpl = EmailTemplate(
                        name=name, category=cat, subject=subj,
                        body_text=text, body_html=html, is_active=True,
                        created_by='System'
                    )
                    _db.session.add(tpl)
                    _db.session.flush()

                    rule = EmailAutomationRule(
                        name=f'Auto: {name}',
                        description=f'Sendet "{name}" bei {trigger_evt}={trigger_val}',
                        trigger_event=trigger_evt,
                        trigger_value=trigger_val,
                        template_id=tpl.id,
                        is_enabled=True,
                        created_by='System'
                    )
                    _db.session.add(rule)

                _db.session.commit()
                print('[OK] Standard E-Mail-Templates und Automation-Regeln erstellt')
        except Exception as e:
            _db.session.rollback()
            print(f'[WARN] E-Mail-Templates Migration: {e}')

        # Migriere Modul-Icons von Emojis/Text auf Bootstrap Icons
        try:
            from src.models.user_permissions import Module
            icon_mapping = {
                'CRM': 'bi-people-fill', '👥': 'bi-people-fill',
                'PROD': 'bi-gear-wide-connected', '🏭': 'bi-gear-wide-connected',
                'POS': 'bi-cash-stack', '💰': 'bi-cash-stack',
                'ACC': 'bi-calculator-fill', '📈': 'bi-calculator-fill',
                'DOC': 'bi-folder2-open', '📁': 'bi-folder2-open',
                'ADM': 'bi-sliders', '⚙️': 'bi-sliders',
                'WH': 'bi-box-seam-fill', '📦': 'bi-box-seam-fill',
                'DSN': 'bi-palette-fill', '🎨': 'bi-palette-fill',
                'EK': 'bi-cart-plus-fill', '🛒': 'bi-cart-plus-fill',
                'palette': 'bi-palette-fill',
            }
            modules = Module.query.all()
            updated = False
            for m in modules:
                if m.icon in icon_mapping:
                    m.icon = icon_mapping[m.icon]
                    updated = True
                elif m.icon and not m.icon.startswith('bi-'):
                    m.icon = 'bi-grid-fill'
                    updated = True
            if updated:
                _db.session.commit()
        except Exception:
            pass

        # Online-Module (Website-CMS, Shop, Anfragen) anlegen
        try:
            from src.models.user_permissions import Module
            online_modules = [
                {
                    'name': 'website_cms',
                    'display_name': 'Website-CMS',
                    'description': 'Website-Inhalte bearbeiten',
                    'icon': 'bi-globe',
                    'color': 'info',
                    'route': 'website_admin.dashboard',
                    'category': 'online',
                    'requires_admin': True,
                    'default_enabled': True,
                    'sort_order': 10,
                },
                {
                    'name': 'shop_admin',
                    'display_name': 'Online-Shop',
                    'description': 'Shop & Konfigurator verwalten',
                    'icon': 'bi-shop',
                    'color': 'success',
                    'route': 'shop_admin.dashboard',
                    'category': 'online',
                    'requires_admin': True,
                    'default_enabled': True,
                    'sort_order': 11,
                },
                {
                    'name': 'inquiry_admin',
                    'display_name': 'Anfragen',
                    'description': 'Website-Anfragen bearbeiten',
                    'icon': 'bi-envelope-paper-fill',
                    'color': 'warning',
                    'route': 'inquiry_admin.list',
                    'category': 'online',
                    'requires_admin': True,
                    'default_enabled': True,
                    'sort_order': 12,
                },
            ]
            for mod_data in online_modules:
                if not Module.query.filter_by(name=mod_data['name']).first():
                    _db.session.add(Module(**mod_data))
            _db.session.commit()
        except Exception:
            _db.session.rollback()

        # CSV-Import Modul anlegen
        try:
            from src.models.user_permissions import Module
            if not Module.query.filter_by(name='csv_import').first():
                _db.session.add(Module(
                    name='csv_import',
                    display_name='CSV-Import',
                    description='Kunden, Artikel & Buchungen importieren',
                    icon='bi-file-earmark-arrow-up',
                    color='secondary',
                    route='csv_import.index',
                    category='admin',
                    requires_admin=True,
                    default_enabled=True,
                    sort_order=15,
                ))
                _db.session.commit()
        except Exception:
            _db.session.rollback()

        # Vertraege-Modul anlegen
        try:
            from src.models.user_permissions import Module
            if not Module.query.filter_by(name='contracts').first():
                _db.session.add(Module(
                    name='contracts',
                    display_name='Vertraege & Policen',
                    description='Vertraege, Versicherungen & Wartung verwalten',
                    icon='bi-file-earmark-text',
                    color='primary',
                    route='contracts.index',
                    category='admin',
                    requires_admin=False,
                    default_enabled=True,
                    sort_order=14,
                ))
                _db.session.commit()
        except Exception:
            _db.session.rollback()

        # Aufgaben-Board Modul anlegen
        try:
            from src.models.user_permissions import Module
            if not Module.query.filter_by(name='taskboard').first():
                _db.session.add(Module(
                    name='taskboard',
                    display_name='Aufgaben-Board',
                    description='Zentrale Aufgabenverwaltung mit Kanban-Board',
                    icon='bi-kanban',
                    color='info',
                    route='taskboard.index',
                    category='core',
                    requires_admin=False,
                    default_enabled=True,
                    sort_order=2,
                ))
                _db.session.commit()
        except Exception:
            _db.session.rollback()

        # Website-CMS Standard-Inhalte setzen (nur bei leerer Tabelle)
        try:
            from src.models.website_content import WebsiteContent
            if WebsiteContent.query.count() == 0:
                WebsiteContent.seed_defaults()
                print("[OK] Website Standard-Inhalte erstellt")
        except Exception:
            _db.session.rollback()

        # Erstelle Admin-User falls nicht vorhanden
        if not User.query.filter_by(username='admin').first():
            import secrets
            initial_pw = secrets.token_urlsafe(12)
            admin = User(username='admin', email='admin@example.com', is_admin=True)
            admin.set_password(initial_pw)
            _db.session.add(admin)
            _db.session.commit()
            print(f"[WICHTIG] Admin-User erstellt. Passwort: {initial_pw}")
            print("[WICHTIG] Bitte sofort aendern unter Einstellungen > Benutzer!")

        # Default-Tenant erstellen falls nicht vorhanden
        try:
            if not Tenant.query.filter_by(slug='default').first():
                default_tenant = Tenant(
                    slug='default',
                    name='StitchAdmin',
                    subdomain='app',
                    contact_email='admin@example.com',
                    is_active=True,
                    plan_tier='enterprise',
                )
                _db.session.add(default_tenant)
                _db.session.flush()

                # Alle bestehenden User dem Default-Tenant zuweisen
                users = User.query.all()
                for user in users:
                    if not UserTenant.query.filter_by(user_id=user.id, tenant_id=default_tenant.id).first():
                        ut = UserTenant(
                            user_id=user.id,
                            tenant_id=default_tenant.id,
                            role='tenant_admin' if user.is_admin else 'user',
                            is_active=True,
                            is_primary=True,
                        )
                        _db.session.add(ut)

                # Admin als System-Admin markieren
                admin_user = User.query.filter_by(username='admin').first()
                if admin_user and hasattr(admin_user, 'is_system_admin'):
                    admin_user.is_system_admin = True

                _db.session.commit()
                print(f"[OK] Default-Tenant erstellt, {len(users)} User zugewiesen")
        except Exception as e:
            print(f"[INFO] Default-Tenant Setup: {e}")
            _db.session.rollback()

    return app


# ==========================================
# HAUPTPROGRAMM
# ==========================================
if __name__ == '__main__':
    app = create_app()
    if app is None:
        sys.exit(1)

    app.run(host='0.0.0.0', port=5000, debug=True)
