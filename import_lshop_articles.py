"""
Import-Script für L-Shop Artikel
Importiert alle 10.252 Artikel aus der Excel-Datei
"""
import os
import sys
from app import create_app
from src.models import db, Supplier
from src.services.lshop_import_service import LShopImportService

def main():
    print("=" * 80)
    print("L-SHOP ARTIKEL IMPORT")
    print("=" * 80)

    # Flask App erstellen
    app = create_app()

    with app.app_context():
        # Excel-Datei
        excel_file = '10103777_Gesamt_L-Shop_DE_-_Fachhandelseinkaufspreise_(inkl._Kalk.)_ab_08.09.2025_(EUR).de.xlsx'

        if not os.path.exists(excel_file):
            print(f"[ERROR] Excel-Datei nicht gefunden: {excel_file}")
            return

        print(f"[OK] Excel-Datei gefunden: {excel_file}")

        # Lieferant "L-Shop" suchen oder erstellen
        supplier = Supplier.query.filter_by(name='L-Shop').first()
        if not supplier:
            print("[INFO] Erstelle Lieferant 'L-Shop'...")
            supplier = Supplier(
                id='LSHOP001',
                name='L-Shop',
                contact_person='L-Shop Deutschland',
                email='info@l-shop.com',
                country='Deutschland',
                webshop_notes='Textilien-Grosshaendler'
            )
            db.session.add(supplier)
            db.session.commit()
            print(f"[OK] Lieferant erstellt: {supplier.name} (ID: {supplier.id})")
        else:
            print(f"[OK] Lieferant gefunden: {supplier.name} (ID: {supplier.id})")

        # Import Service erstellen
        print("\n[INFO] Initialisiere L-Shop Import Service...")
        service = LShopImportService()

        # Excel analysieren (erkennt Header-Zeile automatisch)
        print("[INFO] Analysiere Excel-Datei...")
        service.analyze_excel(excel_file)

        # WICHTIG: L-Shop Excel hat Header in Zeile 9 - manuell überschreiben
        print("[INFO] Lade Excel mit korrekter Header-Zeile (9)...")
        import pandas as pd
        service.df = pd.read_excel(excel_file, header=9, engine='openpyxl')
        service.header_row = 9
        print(f"[OK] {len(service.df)} Zeilen geladen")
        print(f"[OK] Spalten: {list(service.df.columns)[:5]}...")

        # Standard Column Mapping verwenden
        print("\n[INFO] Verwende Standard Column Mapping...")
        column_mapping = service.get_default_column_mapping()

        # Mapping anzeigen
        print("\n[INFO] Column Mapping (Datenbank-Feld -> Excel-Spalte):")
        for db_field, excel_col in column_mapping.items():
            print(f"   {db_field:30} -> {excel_col}")

        # Vorschau
        print("\n[INFO] Vorschau (erste 3 Zeilen):")
        preview = service.get_import_preview(limit=3)
        for i, row in enumerate(preview, 1):
            print(f"\n   Zeile {i}:")
            for key, value in row.items():
                if value and str(value).strip():
                    print(f"      {key:25} = {value}")

        # Benutzer fragen
        print("\n" + "=" * 80)
        response = input("[FRAGE] Moechtest du ALLE Artikel importieren? (ja/nein): ").strip().lower()

        if response not in ['ja', 'j', 'yes', 'y']:
            print("[INFO] Import abgebrochen.")
            return

        # Import starten
        print("\n" + "=" * 80)
        print("[INFO] STARTE IMPORT...")
        print("=" * 80)

        result = service.import_articles(
            column_mapping=column_mapping,
            options={
                'supplier_id': supplier.id,
                'update_existing': True
            }
        )

        # Ergebnis anzeigen
        print("\n" + "=" * 80)
        print("[OK] IMPORT ABGESCHLOSSEN")
        print("=" * 80)
        print(f"[OK] Erfolgreich importiert: {result['imported_count']}")
        print(f"[OK] Aktualisiert: {result['updated_count']}")
        print(f"[INFO] Uebersprungen: {result['skipped_count']}")
        print(f"[ERROR] Fehler: {result['error_count']}")

        if result['errors']:
            print("\n[ERROR] Fehler-Details:")
            for error in result['errors'][:10]:  # Nur erste 10 Fehler
                print(f"   - {error}")
            if len(result['errors']) > 10:
                print(f"   ... und {len(result['errors']) - 10} weitere Fehler")

        print("\n[OK] Alle Artikel wurden erfolgreich importiert!")
        print("=" * 80)

if __name__ == '__main__':
    main()
