"""
Automatisches Update-Script für app.py
Erstellt von Hans Hahn - Alle Rechte vorbehalten

Führt folgende Updates durch:
1. Registriert Permission-Blueprints
2. Aktualisiert Dashboard-Route
3. Fügt Permission-Helper zum Context Processor hinzu
"""

import os
import sys
import shutil
from datetime import datetime

def backup_file(filepath):
    """Erstellt ein Backup der Datei"""
    backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(filepath, backup_path)
    print(f"[OK] Backup erstellt: {backup_path}")
    return backup_path

def update_app_py():
    """Aktualisiert app.py mit Permission-System"""
    app_py_path = 'C:\\SoftwareEntwicklung\\StitchAdmin2.0\\app.py'
    
    if not os.path.exists(app_py_path):
        print(f"[FEHLER] app.py nicht gefunden: {app_py_path}")
        return False
    
    # Backup erstellen
    backup_path = backup_file(app_py_path)
    
    try:
        with open(app_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("\n" + "=" * 60)
        print("Aktualisiere app.py...")
        print("=" * 60)
        
        # 1. Blueprint-Registrierung hinzufügen
        if 'permissions_controller' not in content:
            email_line = "    register_blueprint_safe('src.controllers.email_controller', 'email_bp', 'E-Mail Integration')"
            new_blueprints = """    register_blueprint_safe('src.controllers.email_controller', 'email_bp', 'E-Mail Integration')

    # Permission-System
    register_blueprint_safe('src.controllers.permissions_controller', 'permissions_bp', 'Berechtigungsverwaltung')
    register_blueprint_safe('src.controllers.dashboard_api_controller', 'dashboard_api_bp', 'Dashboard-API')"""
            
            content = content.replace(email_line, new_blueprints)
            print("[OK] Blueprint-Registrierung hinzugefügt")
        else:
            print("[SKIP] Blueprints bereits registriert")
        
        # 2. Dashboard-Route aktualisieren
        if 'get_user_dashboard_modules' not in content:
            # Finde Dashboard-Route
            dashboard_start = content.find('@app.route(\'/dashboard\')')
            if dashboard_start != -1:
                # Finde Ende der Funktion (nächste @app.route oder @app.template_filter)
                next_decorator = content.find('@app.', dashboard_start + 50)
                
                new_dashboard = '''@app.route('/dashboard')
    @login_required
    def dashboard():
        """Dashboard Hauptseite mit personalisierten Modulen"""
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

    '''
                
                content = content[:dashboard_start] + new_dashboard + content[next_decorator:]
                print("[OK] Dashboard-Route aktualisiert")
            else:
                print("[WARNUNG] Dashboard-Route nicht gefunden")
        else:
            print("[SKIP] Dashboard bereits aktualisiert")
        
        # 3. Context Processor erweitern
        if 'register_permission_helpers' not in content:
            # Finde inject_globals Funktion
            inject_start = content.find('def inject_globals():')
            if inject_start != -1:
                # Finde return Statement
                return_pos = content.find('return {', inject_start)
                if return_pos != -1:
                    # Füge vor return ein
                    helper_code = '''
        # Permission-Helper registrieren
        try:
            from src.utils.permissions import register_permission_helpers
            register_permission_helpers(app)
        except (ImportError, Exception):
            pass

        '''
                    content = content[:return_pos] + helper_code + content[return_pos:]
                    
                    # Update Version
                    content = content.replace("'app_version': '2.0.1'", "'app_version': '2.0.2'")
                    
                    print("[OK] Context Processor erweitert")
            else:
                print("[WARNUNG] inject_globals nicht gefunden")
        else:
            print("[SKIP] Context Processor bereits erweitert")
        
        # Schreibe aktualisierte Datei
        with open(app_py_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("\n" + "=" * 60)
        print("[OK] app.py erfolgreich aktualisiert!")
        print("=" * 60)
        print(f"\nBackup: {backup_path}")
        print("\nNächste Schritte:")
        print("1. python scripts/setup_permissions.py")
        print("2. python scripts/init_modules.py")
        print("3. Server neu starten")
        
        return True
    
    except Exception as e:
        print(f"\n[FEHLER] Fehler beim Update: {e}")
        print(f"Backup wiederherstellen: {backup_path}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    update_app_py()
