# -*- coding: utf-8 -*-
"""
Migration: Dokument-Workflow System
===================================
Erstellt Tabellen für:
- Nummernkreise
- Zahlungsbedingungen
- BusinessDocuments
- DocumentPositions
- DocumentPayments

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import sys
import os

# Projektpfad hinzufügen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from decimal import Decimal


def run_migration():
    """Führt die Migration durch"""
    from app import create_app
    from src.models import db
    
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("Migration: Dokument-Workflow System")
        print("=" * 60)
        
        # Prüfen ob Tabellen existieren
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        tables_to_create = [
            'nummernkreise',
            'zahlungsbedingungen', 
            'business_documents',
            'document_positions',
            'document_payments'
        ]
        
        # ============================================================
        # TABELLE: nummernkreise
        # ============================================================
        if 'nummernkreise' not in existing_tables:
            print("\n[1/5] Erstelle Tabelle 'nummernkreise'...")
            db.session.execute(db.text("""
                CREATE TABLE nummernkreise (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    belegart VARCHAR(30) UNIQUE NOT NULL,
                    bezeichnung VARCHAR(100),
                    praefix VARCHAR(10) NOT NULL,
                    aktuelles_jahr INTEGER NOT NULL,
                    aktuelle_nummer INTEGER DEFAULT 0,
                    stellen INTEGER DEFAULT 4,
                    trennzeichen VARCHAR(5) DEFAULT '-',
                    jahr_format VARCHAR(10) DEFAULT 'YYYY',
                    jahreswechsel_reset BOOLEAN DEFAULT 1,
                    aktiv BOOLEAN DEFAULT 1,
                    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    geaendert_am TIMESTAMP
                )
            """))
            print("      ✓ Tabelle erstellt")
        else:
            print("\n[1/5] Tabelle 'nummernkreise' existiert bereits")
        
        # ============================================================
        # TABELLE: zahlungsbedingungen
        # ============================================================
        if 'zahlungsbedingungen' not in existing_tables:
            print("\n[2/5] Erstelle Tabelle 'zahlungsbedingungen'...")
            db.session.execute(db.text("""
                CREATE TABLE zahlungsbedingungen (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bezeichnung VARCHAR(100) NOT NULL,
                    kurztext VARCHAR(50),
                    zahlungsziel_tage INTEGER DEFAULT 14,
                    skonto_prozent DECIMAL(5,2) DEFAULT 0,
                    skonto_tage INTEGER DEFAULT 0,
                    anzahlung_erforderlich BOOLEAN DEFAULT 0,
                    anzahlung_prozent DECIMAL(5,2) DEFAULT 0,
                    anzahlung_festbetrag DECIMAL(12,2) DEFAULT 0,
                    anzahlung_text VARCHAR(200),
                    text_rechnung TEXT,
                    text_rechnung_skonto TEXT,
                    aktiv BOOLEAN DEFAULT 1,
                    standard BOOLEAN DEFAULT 0,
                    sortierung INTEGER DEFAULT 0,
                    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    geaendert_am TIMESTAMP
                )
            """))
            print("      ✓ Tabelle erstellt")
        else:
            print("\n[2/5] Tabelle 'zahlungsbedingungen' existiert bereits")
        
        # ============================================================
        # TABELLE: business_documents
        # ============================================================
        if 'business_documents' not in existing_tables:
            print("\n[3/5] Erstelle Tabelle 'business_documents'...")
            db.session.execute(db.text("""
                CREATE TABLE business_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    
                    -- Identifikation
                    dokument_nummer VARCHAR(50) UNIQUE NOT NULL,
                    dokument_typ VARCHAR(30) NOT NULL,
                    
                    -- Verkettung
                    vorgaenger_id INTEGER REFERENCES business_documents(id),
                    auftrag_id VARCHAR(50) REFERENCES orders(id),
                    
                    -- Kunde
                    kunde_id VARCHAR(50) NOT NULL REFERENCES customers(id),
                    rechnungsadresse TEXT,  -- JSON
                    lieferadresse TEXT,     -- JSON
                    ansprechpartner VARCHAR(200),
                    
                    -- Datum
                    dokument_datum DATE NOT NULL,
                    gueltig_bis DATE,
                    lieferdatum DATE,
                    leistungsdatum DATE,
                    leistungszeitraum_bis DATE,
                    faelligkeitsdatum DATE,
                    
                    -- Beträge
                    summe_netto DECIMAL(12,2) DEFAULT 0,
                    summe_mwst DECIMAL(12,2) DEFAULT 0,
                    summe_brutto DECIMAL(12,2) DEFAULT 0,
                    rabatt_prozent DECIMAL(5,2) DEFAULT 0,
                    rabatt_betrag DECIMAL(12,2) DEFAULT 0,
                    bereits_gezahlt DECIMAL(12,2) DEFAULT 0,
                    restbetrag DECIMAL(12,2) DEFAULT 0,
                    
                    -- Status
                    status VARCHAR(30) DEFAULT 'entwurf',
                    
                    -- Texte
                    betreff VARCHAR(500),
                    einleitung TEXT,
                    schlussbemerkung TEXT,
                    interne_notiz TEXT,
                    kunden_referenz VARCHAR(200),
                    kunden_bestellnummer VARCHAR(100),
                    
                    -- Zahlungsbedingungen
                    zahlungsbedingung_id INTEGER REFERENCES zahlungsbedingungen(id),
                    zahlungsziel_tage INTEGER DEFAULT 14,
                    skonto_prozent DECIMAL(5,2) DEFAULT 0,
                    skonto_tage INTEGER DEFAULT 0,
                    skonto_betrag DECIMAL(12,2) DEFAULT 0,
                    zahlungstext TEXT,
                    
                    -- Versand
                    versandart VARCHAR(50),
                    versandkosten DECIMAL(10,2) DEFAULT 0,
                    tracking_nummer VARCHAR(100),
                    
                    -- PDF
                    pdf_pfad VARCHAR(500),
                    pdf_erstellt_am TIMESTAMP,
                    pdf_hash VARCHAR(64),
                    
                    -- Tracking
                    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    erstellt_von VARCHAR(100),
                    geaendert_am TIMESTAMP,
                    geaendert_von VARCHAR(100),
                    versendet_am TIMESTAMP,
                    versendet_per VARCHAR(50),
                    versendet_an VARCHAR(200),
                    
                    -- Angebots-spezifisch
                    angenommen_am TIMESTAMP,
                    abgelehnt_am TIMESTAMP,
                    ablehnungsgrund TEXT,
                    
                    -- Rechnungs-spezifisch
                    bezahlt_am DATE,
                    letzte_mahnung_am DATE,
                    mahnstufe INTEGER DEFAULT 0
                )
            """))
            
            # Indexes erstellen
            db.session.execute(db.text("""
                CREATE INDEX idx_doc_nummer ON business_documents(dokument_nummer)
            """))
            db.session.execute(db.text("""
                CREATE INDEX idx_doc_typ ON business_documents(dokument_typ)
            """))
            db.session.execute(db.text("""
                CREATE INDEX idx_doc_kunde ON business_documents(kunde_id)
            """))
            db.session.execute(db.text("""
                CREATE INDEX idx_doc_status ON business_documents(status)
            """))
            db.session.execute(db.text("""
                CREATE INDEX idx_doc_datum ON business_documents(dokument_datum)
            """))
            
            print("      ✓ Tabelle und Indexes erstellt")
        else:
            print("\n[3/5] Tabelle 'business_documents' existiert bereits")
        
        # ============================================================
        # TABELLE: document_positions
        # ============================================================
        if 'document_positions' not in existing_tables:
            print("\n[4/5] Erstelle Tabelle 'document_positions'...")
            db.session.execute(db.text("""
                CREATE TABLE document_positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dokument_id INTEGER NOT NULL REFERENCES business_documents(id),
                    position INTEGER NOT NULL,
                    
                    -- Typ
                    typ VARCHAR(30) DEFAULT 'artikel',
                    
                    -- Referenzen
                    artikel_id INTEGER REFERENCES articles(id),
                    order_item_id INTEGER,
                    anzahlung_dokument_id INTEGER REFERENCES business_documents(id),
                    
                    -- Beschreibung
                    artikelnummer VARCHAR(100),
                    bezeichnung VARCHAR(500) NOT NULL,
                    beschreibung TEXT,
                    veredelung_position VARCHAR(50),
                    veredelung_details TEXT,  -- JSON
                    
                    -- Mengen
                    menge DECIMAL(10,3) NOT NULL DEFAULT 1,
                    einheit VARCHAR(20) DEFAULT 'Stk.',
                    
                    -- Preise
                    einzelpreis_netto DECIMAL(12,4) NOT NULL DEFAULT 0,
                    einzelpreis_brutto DECIMAL(12,4) DEFAULT 0,
                    rabatt_prozent DECIMAL(5,2) DEFAULT 0,
                    rabatt_betrag DECIMAL(12,2) DEFAULT 0,
                    
                    -- MwSt
                    mwst_satz DECIMAL(5,2) NOT NULL DEFAULT 19.00,
                    mwst_kennzeichen VARCHAR(10) DEFAULT 'S',
                    
                    -- Berechnete Werte
                    netto_gesamt DECIMAL(12,2) NOT NULL DEFAULT 0,
                    mwst_betrag DECIMAL(12,2) NOT NULL DEFAULT 0,
                    brutto_gesamt DECIMAL(12,2) NOT NULL DEFAULT 0,
                    
                    -- Optional
                    kostenstelle VARCHAR(50),
                    notiz TEXT,
                    
                    UNIQUE(dokument_id, position)
                )
            """))
            
            db.session.execute(db.text("""
                CREATE INDEX idx_pos_dokument ON document_positions(dokument_id)
            """))
            
            print("      ✓ Tabelle erstellt")
        else:
            print("\n[4/5] Tabelle 'document_positions' existiert bereits")
        
        # ============================================================
        # TABELLE: document_payments
        # ============================================================
        if 'document_payments' not in existing_tables:
            print("\n[5/5] Erstelle Tabelle 'document_payments'...")
            db.session.execute(db.text("""
                CREATE TABLE document_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dokument_id INTEGER NOT NULL REFERENCES business_documents(id),
                    
                    -- Zahlung
                    zahlungsart VARCHAR(30) NOT NULL,
                    betrag DECIMAL(12,2) NOT NULL,
                    zahlung_datum DATE NOT NULL,
                    
                    -- Referenzen
                    transaktions_id VARCHAR(100),
                    verrechnungs_dokument_id INTEGER REFERENCES business_documents(id),
                    bank_referenz VARCHAR(200),
                    kontoauszug_datum DATE,
                    
                    -- Status
                    bestaetigt BOOLEAN DEFAULT 0,
                    bestaetigt_von VARCHAR(100),
                    bestaetigt_am TIMESTAMP,
                    
                    -- Notizen
                    notiz TEXT,
                    
                    -- Tracking
                    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    erstellt_von VARCHAR(100)
                )
            """))
            
            db.session.execute(db.text("""
                CREATE INDEX idx_pay_dokument ON document_payments(dokument_id)
            """))
            db.session.execute(db.text("""
                CREATE INDEX idx_pay_datum ON document_payments(zahlung_datum)
            """))
            
            print("      ✓ Tabelle erstellt")
        else:
            print("\n[5/5] Tabelle 'document_payments' existiert bereits")
        
        db.session.commit()
        
        # ============================================================
        # STAMMDATEN INITIALISIEREN
        # ============================================================
        print("\n" + "-" * 60)
        print("Initialisiere Stammdaten...")
        
        # Nummernkreise
        from src.models.document_workflow import initialisiere_nummernkreise, initialisiere_zahlungsbedingungen
        
        print("\n  → Nummernkreise...")
        initialisiere_nummernkreise()
        print("    ✓ Nummernkreise initialisiert")
        
        print("\n  → Zahlungsbedingungen...")
        initialisiere_zahlungsbedingungen()
        print("    ✓ Zahlungsbedingungen initialisiert")
        
        # ============================================================
        # ZUSAMMENFASSUNG
        # ============================================================
        print("\n" + "=" * 60)
        print("Migration erfolgreich abgeschlossen!")
        print("=" * 60)
        
        # Statistik
        from src.models.document_workflow import Nummernkreis, Zahlungsbedingung
        
        nk_count = Nummernkreis.query.count()
        zb_count = Zahlungsbedingung.query.count()
        
        print(f"\nStatistik:")
        print(f"  • Nummernkreise: {nk_count}")
        print(f"  • Zahlungsbedingungen: {zb_count}")
        
        # Nummernkreise anzeigen
        print(f"\nNummernkreise (Vorschau nächste Nummer):")
        for nk in Nummernkreis.query.order_by(Nummernkreis.belegart).all():
            print(f"  • {nk.bezeichnung}: {nk.vorschau_naechste()}")
        
        return True


def rollback_migration():
    """Macht die Migration rückgängig (VORSICHT!)"""
    from app import create_app
    from src.models import db
    
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("ROLLBACK: Dokument-Workflow System")
        print("ACHTUNG: Alle Daten werden gelöscht!")
        print("=" * 60)
        
        confirm = input("\nWirklich fortfahren? (ja/nein): ")
        if confirm.lower() != 'ja':
            print("Abgebrochen.")
            return False
        
        tables = [
            'document_payments',
            'document_positions', 
            'business_documents',
            'zahlungsbedingungen',
            'nummernkreise'
        ]
        
        for table in tables:
            try:
                db.session.execute(db.text(f"DROP TABLE IF EXISTS {table}"))
                print(f"  ✓ Tabelle '{table}' gelöscht")
            except Exception as e:
                print(f"  ✗ Fehler bei '{table}': {e}")
        
        db.session.commit()
        print("\nRollback abgeschlossen.")
        return True


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Dokument-Workflow Migration')
    parser.add_argument('--rollback', action='store_true', help='Migration rückgängig machen')
    
    args = parser.parse_args()
    
    if args.rollback:
        rollback_migration()
    else:
        run_migration()
