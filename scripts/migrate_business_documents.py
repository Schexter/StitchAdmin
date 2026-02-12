# -*- coding: utf-8 -*-
"""
Migration: Business Documents & Nummernkreise
=============================================
StitchAdmin 2.0

Erstellt alle Tabellen für:
- Nummernkreise (GoBD-konforme Belegnummern)
- Zahlungsbedingungen
- Business Documents (Angebote, AB, LS, Rechnungen)
- Document Positions
- Document Payments

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from flask import Flask
from src.models import db


def create_app():
    """Erstellt Flask-App für Migration"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/stitchadmin.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app


def run_migration():
    """Führt die Migration durch"""
    print("=" * 60)
    print("MIGRATION: Business Documents & Nummernkreise")
    print("=" * 60)
    
    # 1. Nummernkreise Tabelle
    print("\n[1/5] Erstelle Tabelle: nummernkreise...")
    try:
        db.session.execute("""
            CREATE TABLE IF NOT EXISTS nummernkreise (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                belegart VARCHAR(30) UNIQUE NOT NULL,
                bezeichnung VARCHAR(100) NOT NULL,
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
        """)
        db.session.commit()
        print("       ✓ Tabelle nummernkreise erstellt/existiert")
    except Exception as e:
        print(f"       ! Fehler: {e}")
    
    # 2. Zahlungsbedingungen Tabelle
    print("\n[2/5] Erstelle Tabelle: zahlungsbedingungen...")
    try:
        db.session.execute("""
            CREATE TABLE IF NOT EXISTS zahlungsbedingungen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bezeichnung VARCHAR(100) NOT NULL,
                kurztext VARCHAR(50),
                zahlungsziel_tage INTEGER DEFAULT 14,
                skonto_prozent INTEGER DEFAULT 0,
                skonto_tage INTEGER DEFAULT 0,
                anzahlung_erforderlich BOOLEAN DEFAULT 0,
                anzahlung_prozent INTEGER DEFAULT 0,
                anzahlung_text VARCHAR(200),
                text_rechnung TEXT,
                text_angebot TEXT,
                aktiv BOOLEAN DEFAULT 1,
                standard BOOLEAN DEFAULT 0,
                sortierung INTEGER DEFAULT 0,
                erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.session.commit()
        print("       ✓ Tabelle zahlungsbedingungen erstellt/existiert")
    except Exception as e:
        print(f"       ! Fehler: {e}")
    
    # 3. Business Documents Tabelle
    print("\n[3/5] Erstelle Tabelle: business_documents...")
    try:
        db.session.execute("""
            CREATE TABLE IF NOT EXISTS business_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Identifikation
                dokument_nummer VARCHAR(50) UNIQUE NOT NULL,
                dokument_typ VARCHAR(30) NOT NULL,
                
                -- Verkettung
                vorgaenger_id INTEGER REFERENCES business_documents(id),
                auftrag_id VARCHAR(50) REFERENCES orders(id),
                storno_von_id INTEGER REFERENCES business_documents(id),
                
                -- Kunde
                kunde_id VARCHAR(50) NOT NULL REFERENCES customers(id),
                rechnungsadresse JSON,
                lieferadresse JSON,
                
                -- Datum
                dokument_datum DATE DEFAULT CURRENT_DATE,
                gueltig_bis DATE,
                lieferdatum DATE,
                lieferdatum_bis DATE,
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
                kunden_referenz VARCHAR(100),
                
                -- Zahlungsbedingungen
                zahlungsbedingung_id INTEGER REFERENCES zahlungsbedingungen(id),
                zahlungsziel_tage INTEGER DEFAULT 14,
                skonto_prozent DECIMAL(5,2) DEFAULT 0,
                skonto_tage INTEGER DEFAULT 0,
                zahlungstext TEXT,
                
                -- Versand
                versandart VARCHAR(50),
                versandkosten DECIMAL(10,2) DEFAULT 0,
                sendungsnummer VARCHAR(100),
                
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
                angenommen_am TIMESTAMP,
                bezahlt_am TIMESTAMP,
                storniert_am TIMESTAMP,
                storno_grund VARCHAR(500)
            )
        """)
        db.session.commit()
        print("       ✓ Tabelle business_documents erstellt/existiert")
        
        # Indizes
        try:
            db.session.execute("CREATE INDEX IF NOT EXISTS idx_doc_nummer ON business_documents(dokument_nummer)")
            db.session.execute("CREATE INDEX IF NOT EXISTS idx_doc_kunde ON business_documents(kunde_id)")
            db.session.execute("CREATE INDEX IF NOT EXISTS idx_doc_typ ON business_documents(dokument_typ)")
            db.session.execute("CREATE INDEX IF NOT EXISTS idx_doc_status ON business_documents(status)")
            db.session.execute("CREATE INDEX IF NOT EXISTS idx_doc_datum ON business_documents(dokument_datum)")
            db.session.commit()
            print("       ✓ Indizes erstellt")
        except:
            pass
            
    except Exception as e:
        print(f"       ! Fehler: {e}")
    
    # 4. Document Positions Tabelle
    print("\n[4/5] Erstelle Tabelle: document_positions...")
    try:
        db.session.execute("""
            CREATE TABLE IF NOT EXISTS document_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dokument_id INTEGER NOT NULL REFERENCES business_documents(id),
                
                -- Sortierung
                position INTEGER NOT NULL,
                
                -- Typ
                typ VARCHAR(30) DEFAULT 'artikel',
                
                -- Referenzen
                artikel_id INTEGER REFERENCES articles(id),
                order_item_id INTEGER,
                
                -- Beschreibung
                artikelnummer VARCHAR(100),
                bezeichnung VARCHAR(500) NOT NULL,
                beschreibung TEXT,
                
                -- Mengen
                menge DECIMAL(10,3) NOT NULL DEFAULT 1,
                einheit VARCHAR(20) DEFAULT 'Stk.',
                
                -- Preise
                einzelpreis_netto DECIMAL(12,4) NOT NULL DEFAULT 0,
                rabatt_prozent DECIMAL(5,2) DEFAULT 0,
                
                -- MwSt
                mwst_satz DECIMAL(5,2) NOT NULL DEFAULT 19,
                mwst_kennzeichen VARCHAR(10) DEFAULT 'S',
                
                -- Berechnete Werte
                netto_gesamt DECIMAL(12,2) DEFAULT 0,
                mwst_betrag DECIMAL(12,2) DEFAULT 0,
                brutto_gesamt DECIMAL(12,2) DEFAULT 0,
                
                -- Optional
                kostenstelle VARCHAR(50)
            )
        """)
        db.session.commit()
        print("       ✓ Tabelle document_positions erstellt/existiert")
        
        # Index
        try:
            db.session.execute("CREATE INDEX IF NOT EXISTS idx_pos_dokument ON document_positions(dokument_id)")
            db.session.commit()
        except:
            pass
            
    except Exception as e:
        print(f"       ! Fehler: {e}")
    
    # 5. Document Payments Tabelle
    print("\n[5/5] Erstelle Tabelle: document_payments...")
    try:
        db.session.execute("""
            CREATE TABLE IF NOT EXISTS document_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dokument_id INTEGER NOT NULL REFERENCES business_documents(id),
                
                -- Zahlung
                zahlungsart VARCHAR(30) NOT NULL,
                betrag DECIMAL(12,2) NOT NULL,
                zahlung_datum DATE NOT NULL DEFAULT CURRENT_DATE,
                
                -- Referenzen
                transaktions_id VARCHAR(100),
                anzahlungs_rechnung_id INTEGER REFERENCES business_documents(id),
                
                -- Status
                bestaetigt BOOLEAN DEFAULT 0,
                bestaetigt_von VARCHAR(100),
                bestaetigt_am TIMESTAMP,
                
                notiz TEXT,
                
                -- Tracking
                erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                erstellt_von VARCHAR(100)
            )
        """)
        db.session.commit()
        print("       ✓ Tabelle document_payments erstellt/existiert")
        
    except Exception as e:
        print(f"       ! Fehler: {e}")
    
    print("\n" + "=" * 60)
    print("INITIALISIERUNG: Stammdaten")
    print("=" * 60)
    
    # Nummernkreise initialisieren
    print("\n[+] Initialisiere Nummernkreise...")
    try:
        from src.models.nummernkreise import init_nummernkreise
        anzahl = init_nummernkreise()
        print(f"    ✓ {anzahl} Nummernkreise erstellt")
    except Exception as e:
        print(f"    ! Fehler: {e}")
    
    # Zahlungsbedingungen initialisieren
    print("\n[+] Initialisiere Zahlungsbedingungen...")
    try:
        from src.models.nummernkreise import init_zahlungsbedingungen
        anzahl = init_zahlungsbedingungen()
        print(f"    ✓ {anzahl} Zahlungsbedingungen erstellt")
    except Exception as e:
        print(f"    ! Fehler: {e}")
    
    print("\n" + "=" * 60)
    print("✓ MIGRATION ABGESCHLOSSEN")
    print("=" * 60)


def show_status():
    """Zeigt aktuellen Status der Tabellen"""
    print("\n" + "=" * 60)
    print("STATUS: Business Documents Tabellen")
    print("=" * 60)
    
    tables = [
        'nummernkreise',
        'zahlungsbedingungen',
        'business_documents',
        'document_positions',
        'document_payments'
    ]
    
    for table in tables:
        try:
            result = db.session.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            count = result[0]
            print(f"  {table}: {count} Einträge")
        except Exception as e:
            print(f"  {table}: ✗ Nicht vorhanden")
    
    # Nummernkreise Details
    print("\n" + "-" * 40)
    print("Nummernkreise:")
    try:
        result = db.session.execute(
            "SELECT belegart, praefix, aktuelles_jahr, aktuelle_nummer FROM nummernkreise ORDER BY belegart"
        ).fetchall()
        for row in result:
            print(f"  {row[0]}: {row[1]}-{row[2]}-{str(row[3]).zfill(4)}")
    except:
        print("  (keine Daten)")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Migration: Business Documents')
    parser.add_argument('--status', action='store_true', help='Zeige Status der Tabellen')
    args = parser.parse_args()
    
    app = create_app()
    
    with app.app_context():
        if args.status:
            show_status()
        else:
            run_migration()
            show_status()
