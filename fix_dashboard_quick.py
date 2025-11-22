"""
Quick-Fix Script: Registriert Documents Blueprint und aktualisiert Dashboard Stats
"""

import sys
import os

# 1. Blueprint in app.py registrieren
print("[1/2] Füge Documents-Blueprint hinzu...")

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Prüfen ob schon vorhanden
if 'documents_controller' not in content:
    # Finde die Stelle nach auth_controller
    search = "    register_blueprint_safe('src.controllers.auth_controller', 'auth_bp', 'Authentifizierung')"
    
    if search in content:
        replacement = search + "\n\n    # Dokumente & Post\n    register_blueprint_safe('src.controllers.documents.documents_controller', 'documents_bp', 'Dokumente & Post')"
        content = content.replace(search, replacement)
        
        # Backup erstellen
        with open('app.py.backup_docs', 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Neue Version schreiben
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("[OK] Documents-Blueprint hinzugefügt!")
    else:
        print("[FEHLER] Konnte auth_controller nicht finden!")
        sys.exit(1)
else:
    print("[INFO] Documents-Blueprint bereits vorhanden")

# 2. Dashboard-Statistiken erweitern
print("\n[2/2] Erweitere Dashboard-Statistiken...")

# Suche die Dashboard-Funktion
search_start = "@app.route('/dashboard')"
search_end = "return render_template('dashboard.html', stats=stats)"

if search_start in content and search_end in content:
    # Finde den stats Dict
    start_idx = content.find("stats = {", content.find(search_start))
    end_idx = content.find("}", start_idx) + 1
    
    if start_idx > 0 and end_idx > start_idx:
        # Neue Stats Definition
        new_stats = '''stats = {
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
        'document_count': 0,  # Wird später gefüllt
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
    }'''
        
        content = content[:start_idx] + new_stats + content[end_idx:]
        
        # Imports hinzufügen
        import_section = "from src.models.models import Order, db"
        new_import = "from src.models.models import Order, Customer, Article, Thread, db"
        content = content.replace(import_section, new_import)
        
        # Schreiben
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("[OK] Dashboard-Statistiken erweitert!")
    else:
        print("[WARNUNG] Konnte stats Dict nicht finden")
else:
    print("[WARNUNG] Konnte Dashboard-Route nicht finden")

print("\n" + "="*50)
print("FERTIG! Blueprint und Stats aktualisiert")
print("="*50)
print("\nNächste Schritte:")
print("1. Server neu starten: python app.py")
print("2. Im Browser: http://localhost:5000")
print("3. Neues Kachel-Dashboard sollte sichtbar sein!")
