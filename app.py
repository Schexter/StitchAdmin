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

# Füge Projekt-Root zum Python-Path hinzu
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def create_app():
    """
    Flask Application Factory
    Erstellt und konfiguriert die Flask-Anwendung
    """
    app = Flask(__name__,
                template_folder='src/templates',
                static_folder='src/static')

    # ==========================================
    # KONFIGURATION
    # ==========================================
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'True') == 'True'

    # Erstelle notwendige Verzeichnisse ZUERST
    instance_dir = os.path.join(BASE_DIR, 'instance')
    upload_dir = os.path.join(instance_dir, 'uploads')
    os.makedirs(instance_dir, exist_ok=True)
    os.makedirs(upload_dir, exist_ok=True)

    # Datenbank-Konfiguration mit absolutem Pfad
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
        print(f"[ERROR] FEHLER beim Importieren der Models: {e}")
        import traceback
        traceback.print_exc()
        return None

    # ==========================================
    # FLASK-MIGRATE (Datenbank-Migrationen)
    # ==========================================
    try:
        from flask_migrate import Migrate
        migrate = Migrate(app, db)
        print("[OK] Flask-Migrate erfolgreich initialisiert")
    except ImportError as e:
        print(f"[WARNING] Flask-Migrate nicht verfügbar: {e}")

    # ==========================================
    # LOGGER-SYSTEM
    # ==========================================
    try:
        from src.utils.logger import logger
        app.logger_instance = logger
        print("[OK] Logger-System erfolgreich initialisiert")
    except ImportError as e:
        print(f"[WARNING] Logger-System nicht verfügbar: {e}")

    # ==========================================
    # CUSTOM FILTERS
    # ==========================================
    try:
        from src.utils.filters import register_filters
        register_filters(app)
        print("[OK] Custom Template-Filters registriert")
    except ImportError as e:
        print(f"[WARNING] Custom Filters nicht verfügbar: {e}")

    # ==========================================
    # LOGIN MANAGER
    # ==========================================
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Bitte melden Sie sich an, um auf diese Seite zuzugreifen.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ==========================================
    # BASIS-ROUTEN
    # ==========================================
    @app.route('/favicon.ico')
    def favicon():
        return app.send_static_file('favicon.svg')

    @app.route('/openapi.yaml')
    def openapi_spec():
        """OpenAPI-Spezifikation bereitstellen"""
        from flask import send_file
        openapi_path = os.path.join(BASE_DIR, 'openapi.yaml')
        if os.path.exists(openapi_path):
            return send_file(openapi_path, mimetype='text/yaml')
        return "OpenAPI-Spezifikation nicht gefunden", 404

    @app.route('/')
    def index():
        """Startseite"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('auth.login'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Haupt-Dashboard mit Statistiken und Übersichten"""
        try:
            # Dashboard-Statistiken
            stats = {
                'open_orders': Order.query.filter(
                    Order.status.in_(['new', 'accepted'])
                ).count(),
                'in_production': Order.query.filter(
                    Order.status.in_(['in_progress', 'production'])
                ).count(),
                'ready_pickup': Order.query.filter(
                    Order.status.in_(['ready', 'completed'])
                ).count(),
                'today_revenue': 0,  # TODO: Implementieren
                'total_customers': Customer.query.count(),
                'total_articles': Article.query.count(),
                'active_machines': Machine.query.filter_by(active=True).count(),
            }
            
            # Letzte Bestellungen
            recent_orders = Order.query.order_by(
                Order.created_at.desc()
            ).limit(10).all()
            
            # Letzte Aktivitäten
            recent_activities = ActivityLog.query.order_by(
                ActivityLog.timestamp.desc()
            ).limit(10).all()
            
        except Exception as e:
            print(f"[ERROR] Fehler beim Laden der Dashboard-Statistiken: {e}")
            stats = {
                'open_orders': 0,
                'in_production': 0,
                'ready_pickup': 0,
                'today_revenue': 0,
                'total_customers': 0,
                'total_articles': 0,
                'active_machines': 0,
            }
            recent_orders = []
            recent_activities = []
        
        return render_template('dashboard.html',
                             stats=stats,
                             recent_orders=recent_orders,
                             recent_activities=recent_activities)

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
            print(f"[WARNING] {display_name} Blueprint nicht verfügbar: {e}")
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
    register_blueprint_safe('src.controllers.activity_controller_db', 'activity_bp', 'Aktivitäten')
    
    # Spezial-Module
    register_blueprint_safe('src.controllers.design_workflow_controller', 'design_workflow_bp', 'Design-Workflow')
    register_blueprint_safe('src.controllers.file_browser_controller', 'file_browser_bp', 'Datei-Browser')
    
    # API
    register_blueprint_safe('src.controllers.api_controller', 'api_bp', 'API')

    # Swagger UI für API-Dokumentation
    try:
        from src.controllers.api_controller import swaggerui_blueprint
        app.register_blueprint(swaggerui_blueprint)
        blueprints_registered.append('API-Docs (Swagger UI)')
        print("[OK] Swagger UI Blueprint registriert")
    except Exception as e:
        print(f"[WARNING] Swagger UI nicht verfügbar: {e}")
    
    # Rechnungsmodul
    try:
        from src.controllers.rechnungsmodul.kasse_controller import kasse_bp
        from src.controllers.rechnungsmodul.rechnung_controller import rechnung_bp
        app.register_blueprint(kasse_bp)
        app.register_blueprint(rechnung_bp)
        blueprints_registered.extend(['Kasse', 'Rechnungen'])
        print("[OK] Rechnungsmodul Blueprints registriert")
    except Exception as e:
        print(f"[WARNING] Rechnungsmodul nicht verfügbar: {e}")
        if app.config['DEBUG']:
            import traceback
            traceback.print_exc()

    # Auth Blueprint (wichtig!)
    try:
        # Erstelle Auth Blueprint für Login/Logout
        from flask import Blueprint
        auth_bp = Blueprint('auth', __name__)
        
        @auth_bp.route('/login', methods=['GET', 'POST'])
        def login():
            if current_user.is_authenticated:
                return redirect(url_for('dashboard'))
                
            if request.method == 'POST':
                username = request.form.get('username')
                password = request.form.get('password')
                
                user = User.query.filter_by(username=username).first()
                if user and user.check_password(password):
                    login_user(user, remember=True)
                    flash(f'Willkommen zurück, {user.username}!', 'success')
                    next_page = request.args.get('next')
                    return redirect(next_page if next_page else url_for('dashboard'))
                
                flash('Ungültiger Benutzername oder Passwort', 'danger')
            
            return render_template('login.html')
        
        @auth_bp.route('/logout')
        @login_required
        def logout():
            logout_user()
            flash('Sie wurden erfolgreich abgemeldet.', 'info')
            return redirect(url_for('auth.login'))
        
        app.register_blueprint(auth_bp)
        blueprints_registered.append('Auth')
        print("[OK] Auth Blueprint registriert")
    except Exception as e:
        print(f"[WARNING] Auth Blueprint Fehler: {e}")

    print(f"\n[INFO] Registrierte Module ({len(blueprints_registered)}): {', '.join(blueprints_registered)}\n")

    # ==========================================
    # CONTEXT PROCESSORS
    # ==========================================
    @app.context_processor
    def inject_globals():
        """Globale Template-Variablen"""
        return {
            'blueprints_available': blueprints_registered,
            'app_name': 'StitchAdmin 2.0',
            'app_version': '2.0.0',
        }

    # ==========================================
    # ERROR HANDLERS
    # ==========================================
    @app.errorhandler(404)
    def not_found_error(error):
        """404 - Seite nicht gefunden"""
        try:
            if hasattr(app, 'logger_instance'):
                app.logger_instance.log_debug(f"404 Error: {request.url}", "error_handler")
        except Exception:
            pass  # Logging sollte nie die Error-Behandlung blockieren
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        """500 - Interner Server-Fehler"""
        db.session.rollback()
        try:
            if hasattr(app, 'logger_instance'):
                app.logger_instance.log_error(f"500 Error: {str(error)}", "error_handler")
        except Exception:
            pass
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        """403 - Zugriff verweigert"""
        try:
            if hasattr(app, 'logger_instance'):
                app.logger_instance.log_warning(f"403 Error: {request.url}", "error_handler")
        except Exception:
            pass
        return render_template('errors/403.html'), 403

    @app.errorhandler(Exception)
    def handle_exception(error):
        """Globaler Exception Handler für unbehandelte Fehler"""
        try:
            if hasattr(app, 'logger_instance'):
                app.logger_instance.log_error(
                    f"Unhandled Exception: {type(error).__name__}: {str(error)}",
                    "error_handler"
                )
        except Exception:
            pass

        # Bei bekannten HTTP-Exceptions die richtige Seite anzeigen
        if hasattr(error, 'code'):
            if error.code == 404:
                return render_template('errors/404.html'), 404
            elif error.code == 403:
                return render_template('errors/403.html'), 403

        # Bei unbekannten Fehlern: 500
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app


# ==========================================
# HAUPTPROGRAMM
# ==========================================
if __name__ == '__main__':
    # Erstelle App-Instanz
    app = create_app()
    
    if app is None:
        print("[ERROR] FEHLER: App konnte nicht erstellt werden!")
        print("Bitte prüfen Sie die Fehlermeldungen oben.")
        sys.exit(1)
    
    # Datenbank-Initialisierung
    with app.app_context():
        from src.models.models import db, User
        
        # Erstelle alle Tabellen
        print("[INFO] Erstelle Datenbank-Tabellen...")
        db.create_all()
        print("[OK] Datenbank-Tabellen erstellt")
        
        # Führe Migrationen aus (falls vorhanden)
        try:
            from scripts.db_migration import migrate_database
            migrate_database(db)
            print("[OK] Datenbank-Migrationen erfolgreich")
        except ImportError:
            print("[INFO] Keine Migrationen gefunden")
        except Exception as e:
            print(f"[WARNING] Migration fehlgeschlagen: {e}")
        
        # Erstelle Admin-User falls nicht vorhanden
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@stitchadmin.local',
                is_admin=True,
                is_active=True
            )
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
            print("[OK] Admin-User erstellt (admin/admin)")
        else:
            print("[INFO] Admin-User existiert bereits")

    # Starte Server
    print("\n" + "="*60)
    print(">>> StitchAdmin 2.0 gestartet!")
    print("="*60)
    print(f"[*] URL:         http://localhost:5000")
    print(f"[*] Login:       admin / admin")
    print(f"[*] Debug-Modus: {'Aktiv' if app.config['DEBUG'] else 'Inaktiv'}")
    print(f"[*] Blueprints:  {len([x for x in app.blueprints])} registriert")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])
