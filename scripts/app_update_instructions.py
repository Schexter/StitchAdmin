"""
Update-Script für app.py - Permission-System Integration
Erstellt von Hans Hahn - Alle Rechte vorbehalten

Fügt hinzu:
1. Permission-Blueprints (Admin-Interface & API)
2. Permission-Helper in Context Processor
3. Aktualisierte Dashboard-Route mit Permission-System
"""

# Dieser Code muss in app.py an den richtigen Stellen eingefügt werden

# ==========================================
# 1. NACH DEN BLUEPRINT-REGISTRIERUNGEN (Zeile ~195)
# ==========================================
"""
    # E-Mail Integration
    register_blueprint_safe('src.controllers.email_controller', 'email_bp', 'E-Mail Integration')

    # ===== NEU: Permission-System =====
    register_blueprint_safe('src.controllers.permissions_controller', 'permissions_bp', 'Berechtigungsverwaltung')
    register_blueprint_safe('src.controllers.dashboard_api_controller', 'dashboard_api_bp', 'Dashboard-API')
    # ===== ENDE NEU =====

    # ==========================================
    # HAUPT-ROUTEN
"""

# ==========================================
# 2. DASHBOARD-ROUTE ERSETZEN (Zeile ~205-280)
# ==========================================
"""
    @app.route('/dashboard')
    @login_required
    def dashboard():
        \"\"\"Dashboard Hauptseite mit personalisierten Modulen\"\"\"
        from src.models.models import Order, Customer, Article, Thread, db
        from src.utils.permissions import get_user_dashboard_modules
        from datetime import datetime, date
        from sqlalchemy import func

        # Hole Module basierend auf Berechtigungen & Layout
        user_modules = get_user_dashboard_modules(current_user)

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
            'dst_count': 0
        }

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

        return render_template('dashboard_personalized.html', 
                             user_modules=user_modules, 
                             stats=stats)
"""

# ==========================================
# 3. CONTEXT PROCESSOR ERWEITERN (Zeile ~375)
# ==========================================
"""
    @app.context_processor
    def inject_globals():
        \"\"\"Globale Template-Variablen, inkl. Branding & Permissions.\"\"\"
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
            'app_version': '2.0.2',  # Version erhöht
            'branding': branding_settings
        }
"""

print("""
╔══════════════════════════════════════════════════════════════╗
║  UPDATE-ANLEITUNG FÜR app.py                                  ║
╠══════════════════════════════════════════════════════════════╣
║                                                                ║
║  SCHRITT 1: Blueprint-Registrierung                           ║
║  ----------------------------------                           ║
║  Füge nach Zeile ~195 (nach E-Mail Integration) ein:         ║
║                                                                ║
║  # Permission-System                                          ║
║  register_blueprint_safe('src.controllers.permissions_controller',║
║                         'permissions_bp', 'Berechtigungen')   ║
║  register_blueprint_safe('src.controllers.dashboard_api_controller',║
║                         'dashboard_api_bp', 'Dashboard-API')  ║
║                                                                ║
║  SCHRITT 2: Dashboard-Route ersetzen                          ║
║  ----------------------------------                           ║
║  Ersetze die komplette @app.route('/dashboard') Funktion      ║
║  (Zeilen ~205-280) mit dem Code oben                          ║
║                                                                ║
║  SCHRITT 3: Context Processor erweitern                       ║
║  ----------------------------------                           ║
║  Füge in inject_globals() die Permission-Helper Registrierung║
║  hinzu (siehe Code oben)                                      ║
║                                                                ║
╚══════════════════════════════════════════════════════════════╝

ODER: Nutze das automatische Update-Script:
    python scripts/update_app_for_permissions.py
""")
