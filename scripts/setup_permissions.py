"""
Setup Script für Permission-System
Erstellt von Hans Hahn - Alle Rechte vorbehalten

Erstellt die neuen Tabellen für:
- Module
- ModulePermissions
- DashboardLayouts
"""

from app import create_app
from src.models.models import db
from src.models.user_permissions import Module, ModulePermission, DashboardLayout


def setup_permission_tables():
    """Erstellt die Permission-Tabellen"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("Permission-System Setup")
        print("=" * 60)
        
        try:
            # Erstelle Tabellen
            print("\n[INFO] Erstelle Tabellen...")
            db.create_all()
            print("[OK] Tabellen erfolgreich erstellt!")
            
            # Zeige erstellte Tabellen
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            permission_tables = ['modules', 'module_permissions', 'dashboard_layouts']
            existing = [t for t in permission_tables if t in tables]
            
            print(f"\n[OK] {len(existing)}/3 Permission-Tabellen vorhanden:")
            for table in existing:
                print(f"  + {table}")
            
            if len(existing) < 3:
                missing = [t for t in permission_tables if t not in tables]
                print(f"\n[WARNUNG] Fehlende Tabellen: {missing}")
            
            print("\n" + "=" * 60)
            print("Nächster Schritt:")
            print("  python scripts/init_modules.py")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n[FEHLER] Fehler beim Setup: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    setup_permission_tables()
