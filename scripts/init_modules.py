"""
Module Initialization Script
Erstellt von Hans Hahn - Alle Rechte vorbehalten

Initialisiert die Basis-Module in der Datenbank
Führe dieses Script nach dem Erstellen der Tabellen aus
"""

from app import create_app
from src.models.models import db
from src.models.user_permissions import Module

# Module-Definitionen
INITIAL_MODULES = [
    {
        'name': 'crm',
        'display_name': 'CRM',
        'description': 'Kunden & Kontakte verwalten',
        'icon': 'bi-people-fill',
        'color': 'primary',
        'route': 'customers.index',
        'category': 'core',
        'requires_admin': False,
        'default_enabled': True,
        'sort_order': 1
    },
    {
        'name': 'production',
        'display_name': 'Produktion',
        'description': 'Aufträge & Fertigung',
        'icon': 'bi-gear-wide-connected',
        'color': 'success',
        'route': 'orders.index',
        'category': 'core',
        'requires_admin': False,
        'default_enabled': True,
        'sort_order': 2
    },
    {
        'name': 'pos',
        'display_name': 'Kasse / POS',
        'description': 'Barverkauf & Abrechnung',
        'icon': 'bi-cash-stack',
        'color': 'warning',
        'route': 'kasse.kassen_index',
        'category': 'finance',
        'requires_admin': False,
        'default_enabled': True,
        'sort_order': 3
    },
    {
        'name': 'accounting',
        'display_name': 'Buchhaltung',
        'description': 'Finanzen & Rechnungen',
        'icon': 'bi-calculator-fill',
        'color': 'info',
        'route': 'finanzen.index',
        'category': 'finance',
        'requires_admin': False,
        'default_enabled': True,
        'sort_order': 4
    },
    {
        'name': 'documents',
        'display_name': 'Dokumente & Post',
        'description': 'DMS, Postbuch & E-Mails',
        'icon': 'bi-folder2-open',
        'color': 'secondary',
        'route': 'documents.dashboard',
        'category': 'admin',
        'requires_admin': False,
        'default_enabled': True,
        'sort_order': 5
    },
    {
        'name': 'administration',
        'display_name': 'Verwaltung',
        'description': 'Einstellungen & System',
        'icon': 'bi-sliders',
        'color': 'dark',
        'route': 'settings.index',
        'category': 'admin',
        'requires_admin': True,
        'default_enabled': False,
        'sort_order': 6
    },
    {
        'name': 'warehouse',
        'display_name': 'Lager & Artikel',
        'description': 'Bestand & Verwaltung',
        'icon': 'bi-box-seam-fill',
        'color': 'primary',
        'route': 'articles.index',
        'category': 'core',
        'requires_admin': False,
        'default_enabled': True,
        'sort_order': 7
    },
    {
        'name': 'design',
        'display_name': 'Design-Archiv',
        'description': 'Motive & DST-Dateien',
        'icon': 'bi-palette-fill',
        'color': 'danger',
        'route': 'file_browser.browse',
        'category': 'production',
        'requires_admin': False,
        'default_enabled': True,
        'sort_order': 8
    },
    {
        'name': 'purchasing',
        'display_name': 'Einkauf & Bestellungen',
        'description': 'Lieferantenbestellungen & Wareneingang',
        'icon': 'bi-cart-plus-fill',
        'color': 'warning',
        'route': 'suppliers.order_suggestions',
        'category': 'core',
        'requires_admin': False,
        'default_enabled': True,
        'sort_order': 9
    }
]


def init_modules():
    """Initialisiert die Basis-Module in der Datenbank"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("Modul-Initialisierung")
        print("=" * 60)
        
        # Prüfe ob Tabelle existiert
        try:
            existing_count = Module.query.count()
            print(f"[INFO] {existing_count} Module bereits in Datenbank")
        except Exception as e:
            print(f"[FEHLER] Tabellen existieren nicht: {e}")
            print("[INFO] Führe erst 'python setup_database.py' aus!")
            return
        
        # Erstelle/Update Module
        created = 0
        updated = 0
        
        for module_data in INITIAL_MODULES:
            existing = Module.query.filter_by(name=module_data['name']).first()
            
            if existing:
                # Update bestehend
                for key, value in module_data.items():
                    setattr(existing, key, value)
                updated += 1
                print(f"[UPDATE] {module_data['display_name']}")
            else:
                # Neu erstellen
                module = Module(**module_data)
                db.session.add(module)
                created += 1
                print(f"[NEU]    {module_data['display_name']}")
        
        try:
            db.session.commit()
            print("\n" + "=" * 60)
            print(f"[OK] Erfolgreich: {created} erstellt, {updated} aktualisiert")
            print("=" * 60)
            
            # Zeige alle Module
            print("\nVerfügbare Module:")
            all_modules = Module.query.order_by(Module.sort_order).all()
            for m in all_modules:
                admin_marker = " [ADMIN]" if m.requires_admin else ""
                print(f"  {m.icon} {m.display_name}{admin_marker}")
        
        except Exception as e:
            db.session.rollback()
            print(f"\n[FEHLER] Fehler beim Speichern: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    init_modules()
