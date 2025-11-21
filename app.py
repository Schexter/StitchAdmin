#!/usr/bin/env python3
"""
StitchAdmin 2.0 - Modernisierte ERP-Lösung für Stickerei-Betriebe
Erstellt von Hans Hahn - Alle Rechte vorbehalten

Hauptanwendung mit Flask Application Factory Pattern
"""

import os
import sys
from datetime import timedelta
from flask import Flask, render_template, redirect, url_for, flash, request
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

    # Datenbank-Konfiguration mit absolutem Pfad im DATA_DIR
    db_path = os.path.join(instance_dir, 'stitchadmin.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    app.config['TEMPLATES_AUTO_RELOAD'] = True

    # Upload-Konfiguration
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
    app.config['UPLOAD_FOLDER'] = upload_dir

    # ==========================================
    # DATENBANK INITIALISIERUNG
    # ==========================================
    try:
        from src.models.models import db, User, Customer, Article, Order, Machine, Thread, ActivityLog, Supplier
        db.init_app(app)
        print("[OK] Datenbank-Models erfolgreich importiert")
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
    register_blueprint_safe('src.controllers.shipping_controller_db', 'shipping_bp', 'Versand')

    # Verwaltungs-Module
    register_blueprint_safe('src.controllers.supplier_controller_db', 'supplier_bp', 'Lieferanten')
    register_blueprint_safe('src.controllers.user_controller_db', 'user_bp', 'Benutzer')
    register_blueprint_safe('src.controllers.settings_controller_unified', 'settings_bp', 'Einstellungen')
    register_blueprint_safe('src.controllers.calculation_settings_controller', 'calc_settings_bp', 'Kalkulationseinstellungen')
    register_blueprint_safe('src.controllers.activity_controller_db', 'activity_bp', 'Aktivitäten')

    # Spezial-Module
    register_blueprint_safe('src.controllers.design_workflow_controller', 'design_workflow_bp', 'Design-Workflow')
    register_blueprint_safe('src.controllers.file_browser_controller', 'file_browser_bp', 'Datei-Browser')

    # API
    register_blueprint_safe('src.controllers.api_controller', 'api_bp', 'API')

    # Rechnungsmodul
    try:
        from src.controllers.rechnungsmodul.kasse_controller import kasse_bp
        from src.controllers.rechnungsmodul.rechnung_controller import rechnung_bp
        app.register_blueprint(kasse_bp)
        app.register_blueprint(rechnung_bp)
        blueprints_registered.append('Kasse')
        blueprints_registered.append('Rechnungen')
        print("[OK] Rechnungsmodul Blueprints registriert")
    except ImportError as e:
        print(f"[WARNUNG] Rechnungsmodul nicht verfuegbar: {e}")

    # Smart Home Integration
    register_blueprint_safe('src.controllers.shelly_controller', 'shelly_bp', 'Shelly-Geräte')

    # Auth und Dashboard
    register_blueprint_safe('src.controllers.auth_controller', 'auth_bp', 'Authentifizierung')

    # ==========================================
    # HAUPT-ROUTEN
    # ==========================================
    @app.route('/')
    def root():
        """Root-Route - Redirect zum Dashboard oder Login"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('auth.login'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Dashboard Hauptseite mit Statistiken"""
        from src.models.models import Order, db
        from datetime import datetime, date
        from sqlalchemy import func

        # Berechne Statistiken
        stats = {
            'open_orders': Order.query.filter(
                Order.status.in_(['pending', 'approved', 'in_progress'])
            ).count(),
            'in_production': Order.query.filter_by(status='in_progress').count(),
            'ready_pickup': Order.query.filter_by(status='ready_for_pickup').count(),
            'today_revenue': 0  # Placeholder - kann später erweitert werden
        }

        # Tagesumsatz berechnen (wenn Rechnungsmodul vorhanden)
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
        except (ImportError, Exception):
            pass

        return render_template('dashboard.html', stats=stats)

    # ==========================================
    # TEMPLATE FILTER
    # ==========================================
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

    # ==========================================
    # CONTEXT PROCESSORS
    # ==========================================
    @app.context_processor
    def inject_globals():
        """Globale Template-Variablen, inkl. Branding."""
        try:
            from src.models.branding_settings import BrandingSettings
            branding_settings = BrandingSettings.get_settings()
        except (ImportError, Exception):
            branding_settings = None

        return {
            'app_name': 'StitchAdmin 2.0',
            'app_version': '2.0.1',
            'branding': branding_settings
        }

    # ==========================================
    # ERROR HANDLERS
    # ==========================================
    # ... (unverändert)

    return app


# ==========================================
# HAUPTPROGRAMM
# ==========================================
if __name__ == '__main__':
    app = create_app()
    if app is None:
        sys.exit(1)
    
    with app.app_context():
        from src.models.models import db, User
        db.create_all()
        
        # Erstelle Admin-User falls nicht vorhanden
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@example.com', is_admin=True)
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
            print("[OK] Admin-User erstellt (admin/admin)")

    app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])
