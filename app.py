#!/usr/bin/env python3
"""
StitchAdmin 2.0 - Modernisierte ERP-Lösung für Stickerei-Betriebe
Erstellt von Hans Hahn - Alle Rechte vorbehalten

Hauptanwendung mit Flask Application Factory Pattern
"""

import os
import sys
from datetime import timedelta
from flask import Flask, render_template, redirect, url_for, flash, request, send_from_directory, g
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

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
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
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

    @login_manager.user_loader
    def load_user(user_id):
        """Lädt Benutzer für Flask-Login"""
        from src.models.models import User, db
        return db.session.get(User, user_id)

    # ==========================================
    # GLOBALER LOGIN-SCHUTZ (Vorgelagerte Loginseite)
    # ==========================================
    @app.before_request
    def require_login():
        """Alle Seiten erfordern Login - kein Zugang ohne Anmeldung"""
        # Erlaubte Endpunkte ohne Login
        if request.endpoint and (
            request.endpoint == 'auth.login' or
            request.endpoint == 'static' or
            request.endpoint == 'root' or
            (hasattr(request, 'endpoint') and request.endpoint and request.endpoint.startswith('setup.')) or
            (hasattr(request, 'endpoint') and request.endpoint and request.endpoint.startswith('website.')) or
            (hasattr(request, 'endpoint') and request.endpoint and request.endpoint.startswith('shop.')) or
            (hasattr(request, 'endpoint') and request.endpoint and request.endpoint.startswith('inquiry.')) or
            request.endpoint == 'calendar_sync.callback_microsoft' or
            request.endpoint == 'social_media.callback_facebook'
        ):
            return
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        # Tenant-Kontext setzen (Phase 1: Default-Tenant fuer alle User)
        if app.config.get('MULTI_TENANT_ENABLED'):
            from src.models.tenant import Tenant
            default_tenant = Tenant.query.filter_by(slug='default').first()
            if default_tenant:
                g.current_tenant_id = default_tenant.id
                g.current_tenant = default_tenant

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

    # Banking
    register_blueprint_safe('src.controllers.banking_controller', 'banking_bp', 'Bankkonten')

    # E-Mail-Sync
    register_blueprint_safe('src.controllers.email_sync_controller', 'email_sync_bp', 'E-Mail-Sync')

    # Kalender-Sync
    register_blueprint_safe('src.controllers.calendar_sync_controller', 'calendar_sync_bp', 'Kalender-Sync')

    # Social Media
    register_blueprint_safe('src.controllers.social_media_controller', 'social_media_bp', 'Social Media')

    # ==========================================
    # HAUPT-ROUTEN
    # ==========================================
    @app.route('/app')
    def root():
        """App-Einstieg - Redirect zum Dashboard, Login oder Setup"""
        # Setup-Check: Erstinstallation?
        try:
            from src.controllers.setup_wizard_controller import is_setup_complete
            if not is_setup_complete():
                return redirect(url_for('setup.welcome'))
        except Exception as e:
            print(f"[WARNUNG] Setup-Check fehlgeschlagen: {e}")

        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('auth.login'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Dashboard Hauptseite mit personalisierten Modulen"""
        from src.models.models import Order, Customer, Article, Thread, db
        from src.utils.permissions import get_user_dashboard_modules
        from datetime import datetime, date
        from sqlalchemy import func

        # Hole Module basierend auf Berechtigungen & Layout
        try:
            user_modules = get_user_dashboard_modules(current_user)
        except Exception as e:
            print(f"[FEHLER] Dashboard Module konnten nicht geladen werden: {e}")
            import traceback
            traceback.print_exc()
            user_modules = []

        # Berechne Statistiken
        stats = {
            # Produktion
            'open_orders': Order.query.filter(
                Order.status.in_(['pending', 'approved', 'in_progress'])
            ).count(),
            'in_production': Order.query.filter_by(status='in_progress').count(),
            'ready_pickup': Order.query.filter_by(status='ready_for_pickup').count(),
            'today_revenue': 0,

            # CRM
            'total_customers': Customer.query.count(),
            'open_leads': 0,

            # Dokumente & Post
            'document_count': 0,
            'open_post': 0,
            'unread_emails': 0,

            # Buchhaltung
            'open_invoices': 0,
            'overdue_payments': 0,
            'today_transactions': 0,

            # Verwaltung
            'user_count': 0,
            'article_count': Article.query.count(),

            # Lager
            'thread_count': Thread.query.count(),
            'low_stock': 0,

            # Design
            'design_count': 0,
            'dst_count': 0,

            # Einkauf/Bestellungen
            'pending_supplier_orders': 0,
            'items_to_order': 0
        }

        # Einkauf-Statistiken berechnen
        try:
            from src.models.models import SupplierOrder, OrderItem
            stats['pending_supplier_orders'] = SupplierOrder.query.filter(
                SupplierOrder.status.in_(['draft', 'ordered'])
            ).count()
            # Items die bestellt werden müssen (Bestand < Auftragsmenge)
            stats['items_to_order'] = OrderItem.query.filter(
                OrderItem.supplier_order_status.in_(['none', 'to_order'])
            ).join(Article).filter(
                OrderItem.quantity > Article.stock
            ).count()
        except Exception:
            pass

        # Tagesumsatz berechnen
        try:
            from src.controllers.rechnungsmodul.models import KassenBeleg
            today = date.today()
            today_start = datetime.combine(today, datetime.min.time())
            today_end = datetime.combine(today, datetime.max.time())

            today_sum = db.session.query(func.sum(KassenBeleg.summe_brutto)).filter(
                KassenBeleg.datum >= today_start,
                KassenBeleg.datum <= today_end
            ).scalar()

            stats['today_revenue'] = round(today_sum or 0, 2)
            stats['today_transactions'] = KassenBeleg.query.filter(
                KassenBeleg.datum >= today_start,
                KassenBeleg.datum <= today_end
            ).count()
        except (ImportError, Exception):
            pass

        # Dokumente-Statistiken
        try:
            from src.models.document import Document, PostEntry, ArchivedEmail
            stats['document_count'] = Document.query.filter_by(is_latest_version=True).count()
            stats['open_post'] = PostEntry.query.filter_by(status='open').count()
            stats['unread_emails'] = ArchivedEmail.query.filter_by(is_read=False).count()
        except (ImportError, Exception):
            pass

        # Online-Statistiken (Website-CMS, Shop, Anfragen)
        try:
            from src.models.website_content import WebsiteContent
            stats['website_content_count'] = WebsiteContent.query.count()
        except (ImportError, Exception):
            pass
        try:
            from src.models.inquiry import Inquiry
            stats['new_inquiries'] = Inquiry.query.filter_by(status='NEU').count()
        except (ImportError, Exception):
            pass
        try:
            stats['shop_orders'] = Order.query.filter_by(source='shop').count()
        except Exception:
            pass

        return render_template('dashboard_personalized.html',
                             user_modules=user_modules,
                             stats=stats)

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
                from datetime import datetime
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
                from datetime import datetime
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
            from datetime import date
            if isinstance(birth_date, str):
                from datetime import datetime
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

        return {
            'app_name': 'StitchAdmin 2.0',
            'app_version': '2.0.2',
            'branding': branding_settings,
            'today': date.today()
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
        from src.models.tenant import Tenant, UserTenant  # noqa: F401
        from src.models.csv_import import CSVImportJob  # noqa: F401
        from src.models.contracts import Contract, ContractContact, ContractCommunication  # noqa: F401
        from src.models.email_automation import EmailAutomationRule, EmailAutomationLog  # noqa: F401
        from src.models.banking import BankAccount, BankTransaction  # noqa: F401
        from src.models.calendar_sync import CalendarConnection, CalendarSyncMapping  # noqa: F401
        from src.models.social_media import SocialMediaAccount, SocialMediaPost  # noqa: F401
        try:
            _db.create_all()
        except Exception as e:
            _db.session.rollback()
            print(f"[WARN] create_all() Worker-Race-Condition: {e}")

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
            logger.info("customers.is_active Spalte hinzugefuegt")
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
            admin = User(username='admin', email='admin@example.com', is_admin=True)
            admin.set_password('admin')
            _db.session.add(admin)
            _db.session.commit()

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
