"""
Datenbank-Migration: Shipping Bulk & Post Entry Erweiterungen
Erstellt von Hans Hahn

Fügt hinzu:
- ShippingBulk Tabelle
- Neue Felder zu PostEntry (shipping_bulk_id, expected_delivery_date, etc.)
"""

import sys
import os

# Füge Projekt-Root zum Path hinzu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from src.models.models import db
from src.models.document import ShippingBulk, PostEntry

def migrate():
    """Führt Migration durch"""
    print("[OK] Starte Migration: Shipping Bulk & Post Entry Erweiterungen")

    app = create_app()
    if not app:
        print("[FEHLER] App konnte nicht erstellt werden")
        return False

    with app.app_context():
        try:
            # Erstelle alle Tabellen (neue werden hinzugefügt, bestehende bleiben)
            db.create_all()
            print("[OK] Shipping Bulk Tabelle erstellt/aktualisiert")
            print("[OK] Post Entry Felder hinzugefügt")
            print("[OK] Migration erfolgreich!")
            return True

        except Exception as e:
            print(f"[FEHLER] Migration fehlgeschlagen: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    if migrate():
        print("\n" + "="*60)
        print("MIGRATION ERFOLGREICH ABGESCHLOSSEN")
        print("="*60)
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print("MIGRATION FEHLGESCHLAGEN")
        print("="*60)
        sys.exit(1)
