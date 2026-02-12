"""
Schneller Test: Design-Modul Migration
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 50)
print("Design-Management Migration Test")
print("=" * 50)

try:
    from app import create_app
    print("[1] App-Factory erfolgreich importiert")
    
    app = create_app()
    print("[2] App erstellt")
    
    with app.app_context():
        from src.models.models import db
        from src.models.design import Design, ThreadBrand, ThreadColor, DesignOrder
        
        # Tabellen erstellen
        db.create_all()
        print("[3] Tabellen erstellt/geprueft")
        
        # Tabellen auflisten
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        design_tables = [t for t in tables if 'design' in t.lower() or 'thread' in t.lower()]
        print(f"[4] Design-Tabellen gefunden: {design_tables}")
        
        # Standard-Garnmarken pruefen/erstellen
        madeira = ThreadBrand.query.filter_by(name='Madeira').first()
        if not madeira:
            madeira = ThreadBrand(name='Madeira', short_code='MA', is_default=True, sort_order=1)
            db.session.add(madeira)
            db.session.commit()
            print("[5] Madeira Garnmarke erstellt")
        else:
            print("[5] Madeira Garnmarke existiert bereits")
        
        # Zaehle Eintraege
        brand_count = ThreadBrand.query.count()
        color_count = ThreadColor.query.count()
        design_count = Design.query.count()
        
        print(f"[6] Statistik:")
        print(f"    - Garnmarken: {brand_count}")
        print(f"    - Garnfarben: {color_count}")
        print(f"    - Designs: {design_count}")
        
        print("=" * 50)
        print("Migration erfolgreich!")
        print("=" * 50)

except Exception as e:
    print(f"[FEHLER] {e}")
    import traceback
    traceback.print_exc()
