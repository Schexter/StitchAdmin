# -*- coding: utf-8 -*-
"""
MASTER MIGRATION SCRIPT
=======================
Führt alle ausstehenden Migrationen aus

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
import sys
import sqlite3
from datetime import datetime

# Projekt-Root zum Path hinzufügen
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def get_db_path():
    """Ermittelt Datenbankpfad"""
    # Standard-Pfade
    paths = [
        os.path.join(BASE_DIR, 'instance', 'stitchadmin.db'),
        os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'StitchAdmin', 'instance', 'stitchadmin.db'),
    ]
    
    for path in paths:
        if os.path.exists(path):
            return path
    
    # Fallback
    return paths[0]


def table_exists(cursor, table_name):
    """Prüft ob Tabelle existiert"""
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None


def column_exists(cursor, table_name, column_name):
    """Prüft ob Spalte existiert"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def run_migration(db_path=None):
    """Führt alle Migrationen aus"""
    
    if db_path is None:
        db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"⚠ Datenbank nicht gefunden: {db_path}")
        print("  Erstelle neue Datenbank...")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    print(f"Migriere: {db_path}")
    print("=" * 60)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    migrations_applied = []
    
    # ==========================================================================
    # MIGRATION 1: StorageSettings
    # ==========================================================================
    if not table_exists(cursor, 'storage_settings'):
        print("Erstelle: storage_settings")
        cursor.execute("""
            CREATE TABLE storage_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Basispfade
                base_path VARCHAR(500) DEFAULT '',
                
                -- Separate Archive (NAS/Netzlaufwerk)
                design_archiv_path VARCHAR(500) DEFAULT '',
                design_archiv_aktiv BOOLEAN DEFAULT 0,
                stickdateien_path VARCHAR(500) DEFAULT '',
                stickdateien_aktiv BOOLEAN DEFAULT 0,
                freigaben_archiv_path VARCHAR(500) DEFAULT '',
                freigaben_archiv_aktiv BOOLEAN DEFAULT 0,
                motiv_archiv_path VARCHAR(500) DEFAULT '',
                motiv_archiv_aktiv BOOLEAN DEFAULT 0,
                
                -- Dokument-Pfade
                angebote_path VARCHAR(200) DEFAULT 'Angebote',
                auftraege_path VARCHAR(200) DEFAULT 'Auftragsbestätigungen',
                lieferscheine_path VARCHAR(200) DEFAULT 'Lieferscheine',
                rechnungen_ausgang_path VARCHAR(200) DEFAULT 'Rechnungen\\Ausgang',
                rechnungen_eingang_path VARCHAR(200) DEFAULT 'Rechnungen\\Eingang',
                gutschriften_path VARCHAR(200) DEFAULT 'Gutschriften',
                mahnungen_path VARCHAR(200) DEFAULT 'Mahnungen',
                
                -- Design-Pfade
                designs_path VARCHAR(200) DEFAULT 'Designs',
                design_freigaben_path VARCHAR(200) DEFAULT 'Design-Freigaben',
                
                -- Sonstige Pfade
                backup_path VARCHAR(200) DEFAULT 'Backups',
                temp_path VARCHAR(200) DEFAULT 'Temp',
                import_path VARCHAR(200) DEFAULT 'Importe',
                export_path VARCHAR(200) DEFAULT 'Exporte',
                
                -- Ordnerstruktur-Optionen
                folder_structure VARCHAR(50) DEFAULT 'year_month',
                include_customer_in_filename BOOLEAN DEFAULT 1,
                include_date_in_filename BOOLEAN DEFAULT 1,
                
                -- Archivierung
                auto_archive BOOLEAN DEFAULT 0,
                archive_after_years INTEGER DEFAULT 10,
                archive_path VARCHAR(200) DEFAULT 'Archiv',
                
                -- Metadaten
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        cursor.execute("INSERT INTO storage_settings (base_path) VALUES ('')")
        migrations_applied.append("storage_settings")
    else:
        print("✓ storage_settings existiert bereits")
        # Erweitere bestehende Tabelle um NAS-Felder
        nas_columns = [
            ("design_archiv_path", "VARCHAR(500) DEFAULT ''"),
            ("design_archiv_aktiv", "BOOLEAN DEFAULT 0"),
            ("stickdateien_path", "VARCHAR(500) DEFAULT ''"),
            ("stickdateien_aktiv", "BOOLEAN DEFAULT 0"),
            ("freigaben_archiv_path", "VARCHAR(500) DEFAULT ''"),
            ("freigaben_archiv_aktiv", "BOOLEAN DEFAULT 0"),
            ("motiv_archiv_path", "VARCHAR(500) DEFAULT ''"),
            ("motiv_archiv_aktiv", "BOOLEAN DEFAULT 0"),
        ]
        for col_name, col_type in nas_columns:
            if not column_exists(cursor, 'storage_settings', col_name):
                try:
                    cursor.execute(f"ALTER TABLE storage_settings ADD COLUMN {col_name} {col_type}")
                    print(f"  + Spalte storage_settings.{col_name}")
                    migrations_applied.append(f"storage_settings.{col_name}")
                except Exception as e:
                    print(f"  ⚠ {col_name}: {e}")
    
    # ==========================================================================
    # MIGRATION 2: BusinessDocument Erweiterungen
    # ==========================================================================
    if table_exists(cursor, 'business_documents'):
        new_columns = [
            ("pdf_pfad", "VARCHAR(500)"),
            ("pdf_erstellt_am", "TIMESTAMP"),
            ("xml_pfad", "VARCHAR(500)"),
            ("zugpferd_profil", "VARCHAR(50)"),
        ]
        
        for col_name, col_type in new_columns:
            if not column_exists(cursor, 'business_documents', col_name):
                try:
                    cursor.execute(f"ALTER TABLE business_documents ADD COLUMN {col_name} {col_type}")
                    print(f"  + Spalte business_documents.{col_name}")
                    migrations_applied.append(f"business_documents.{col_name}")
                except Exception as e:
                    print(f"  ⚠ {col_name}: {e}")
    
    # ==========================================================================
    # MIGRATION 3: CompanySettings Erweiterungen (falls nicht vorhanden)
    # ==========================================================================
    if table_exists(cursor, 'company_settings'):
        settings_columns = [
            ("small_business", "BOOLEAN DEFAULT 0"),
            ("small_business_text", "TEXT DEFAULT 'Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.'"),
            ("logo_path", "VARCHAR(500)"),
            ("invoice_email_subject", "VARCHAR(500)"),
            ("invoice_email_template", "TEXT"),
        ]
        
        for col_name, col_def in settings_columns:
            if not column_exists(cursor, 'company_settings', col_name):
                try:
                    cursor.execute(f"ALTER TABLE company_settings ADD COLUMN {col_name} {col_def}")
                    print(f"  + Spalte company_settings.{col_name}")
                    migrations_applied.append(f"company_settings.{col_name}")
                except Exception as e:
                    print(f"  ⚠ {col_name}: {e}")
    
    # ==========================================================================
    # MIGRATION 4: Nummernkreise (falls nicht vorhanden)
    # ==========================================================================
    if not table_exists(cursor, 'nummernkreis'):
        print("Erstelle: nummernkreis")
        cursor.execute("""
            CREATE TABLE nummernkreis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prefix VARCHAR(20) NOT NULL,
                name VARCHAR(100) NOT NULL,
                beschreibung TEXT,
                format VARCHAR(50) DEFAULT '{PREFIX}-{JAHR}-{NR}',
                aktuelle_nummer INTEGER DEFAULT 0,
                min_stellen INTEGER DEFAULT 4,
                jahreswechsel_reset BOOLEAN DEFAULT 1,
                letztes_reset_jahr INTEGER,
                aktiv BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                UNIQUE(prefix)
            )
        """)
        
        # Standard-Nummernkreise
        nummernkreise = [
            ('ANG', 'Angebote', 'Nummernkreis für Angebote'),
            ('AB', 'Auftragsbestätigungen', 'Nummernkreis für Auftragsbestätigungen'),
            ('LS', 'Lieferscheine', 'Nummernkreis für Lieferscheine'),
            ('RE', 'Rechnungen', 'Nummernkreis für Ausgangsrechnungen'),
            ('GS', 'Gutschriften', 'Nummernkreis für Gutschriften'),
        ]
        
        for prefix, name, beschreibung in nummernkreise:
            cursor.execute("""
                INSERT INTO nummernkreis (prefix, name, beschreibung)
                VALUES (?, ?, ?)
            """, (prefix, name, beschreibung))
        
        migrations_applied.append("nummernkreis")
    
    # ==========================================================================
    # MIGRATION 5: Zahlungsbedingungen (falls nicht vorhanden)
    # ==========================================================================
    if not table_exists(cursor, 'zahlungsbedingung'):
        print("Erstelle: zahlungsbedingung")
        cursor.execute("""
            CREATE TABLE zahlungsbedingung (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                tage_netto INTEGER DEFAULT 14,
                tage_skonto INTEGER,
                skonto_prozent REAL,
                text_vorlage TEXT,
                ist_standard BOOLEAN DEFAULT 0,
                aktiv BOOLEAN DEFAULT 1,
                sortierung INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        
        # Standard-Zahlungsbedingungen
        bedingungen = [
            ('14 Tage netto', 14, None, None, 'Zahlbar innerhalb von 14 Tagen ohne Abzug.', 1),
            ('30 Tage netto', 30, None, None, 'Zahlbar innerhalb von 30 Tagen ohne Abzug.', 0),
            ('Sofort', 0, None, None, 'Zahlbar sofort ohne Abzug.', 0),
            ('14 Tage 2% Skonto', 30, 14, 2.0, 'Zahlbar innerhalb von 14 Tagen mit 2% Skonto oder 30 Tage netto.', 0),
        ]
        
        for name, netto, skonto_tage, skonto_proz, text, standard in bedingungen:
            cursor.execute("""
                INSERT INTO zahlungsbedingung (name, tage_netto, tage_skonto, skonto_prozent, text_vorlage, ist_standard)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, netto, skonto_tage, skonto_proz, text, standard))
        
        migrations_applied.append("zahlungsbedingung")
    
    # ==========================================================================
    # MIGRATION 6: DocumentPosition Erweiterungen
    # ==========================================================================
    if table_exists(cursor, 'document_positions'):
        pos_columns = [
            ("artikel_nummer", "VARCHAR(50)"),
            ("beschreibung", "TEXT"),
            ("rabatt_prozent", "REAL DEFAULT 0"),
            ("rabatt_betrag", "REAL DEFAULT 0"),
        ]
        
        for col_name, col_type in pos_columns:
            if not column_exists(cursor, 'document_positions', col_name):
                try:
                    cursor.execute(f"ALTER TABLE document_positions ADD COLUMN {col_name} {col_type}")
                    print(f"  + Spalte document_positions.{col_name}")
                    migrations_applied.append(f"document_positions.{col_name}")
                except Exception as e:
                    print(f"  ⚠ {col_name}: {e}")
    
    # ==========================================================================
    # MIGRATION 7: Buchhaltung Tabellen
    # ==========================================================================
    
    # Kontenplan
    if not table_exists(cursor, 'buchhaltung_konten'):
        print("Erstelle: buchhaltung_konten")
        cursor.execute("""
            CREATE TABLE buchhaltung_konten (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kontonummer VARCHAR(10) NOT NULL UNIQUE,
                bezeichnung VARCHAR(200) NOT NULL,
                kontenrahmen VARCHAR(10) DEFAULT 'SKR03',
                kontenklasse INTEGER,
                ist_aktiv BOOLEAN DEFAULT 1,
                ist_ertragskonto BOOLEAN DEFAULT 0,
                ist_aufwandskonto BOOLEAN DEFAULT 0,
                ist_bestandskonto BOOLEAN DEFAULT 0,
                standard_mwst_satz REAL DEFAULT 19.0,
                datev_kontonummer VARCHAR(10),
                parent_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        migrations_applied.append("buchhaltung_konten")
    
    # Buchungen
    if not table_exists(cursor, 'buchhaltung_buchungen'):
        print("Erstelle: buchhaltung_buchungen")
        cursor.execute("""
            CREATE TABLE buchhaltung_buchungen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                buchungsdatum DATE NOT NULL,
                erfassungsdatum TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                belegnummer VARCHAR(50),
                beleg_art VARCHAR(50),
                buchungstext VARCHAR(500) NOT NULL,
                soll_konto_id INTEGER,
                haben_konto_id INTEGER,
                konto_id INTEGER,
                gegenkonto_id INTEGER,
                betrag_netto REAL NOT NULL,
                betrag_brutto REAL,
                mwst_satz REAL DEFAULT 19.0,
                mwst_betrag REAL,
                buchungs_art VARCHAR(20),
                rechnung_id INTEGER,
                kunde_id INTEGER,
                lieferant_id INTEGER,
                kostenstelle_id INTEGER,
                ist_storniert BOOLEAN DEFAULT 0,
                storno_buchung_id INTEGER,
                datev_exportiert BOOLEAN DEFAULT 0,
                datev_export_datum TIMESTAMP,
                erstellt_von VARCHAR(100)
            )
        """)
        migrations_applied.append("buchhaltung_buchungen")
    
    # Kostenstellen
    if not table_exists(cursor, 'buchhaltung_kostenstellen'):
        print("Erstelle: buchhaltung_kostenstellen")
        cursor.execute("""
            CREATE TABLE buchhaltung_kostenstellen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nummer VARCHAR(20) NOT NULL UNIQUE,
                bezeichnung VARCHAR(200) NOT NULL,
                beschreibung TEXT,
                verantwortlicher VARCHAR(100),
                budget_jahr REAL,
                budget_monat REAL,
                parent_id INTEGER,
                ist_aktiv BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        migrations_applied.append("buchhaltung_kostenstellen")
    
    # USt-Voranmeldung
    if not table_exists(cursor, 'buchhaltung_ust_voranmeldung'):
        print("Erstelle: buchhaltung_ust_voranmeldung")
        cursor.execute("""
            CREATE TABLE buchhaltung_ust_voranmeldung (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jahr INTEGER NOT NULL,
                monat INTEGER,
                quartal INTEGER,
                zeitraum_von DATE NOT NULL,
                zeitraum_bis DATE NOT NULL,
                umsatz_19_netto REAL DEFAULT 0,
                ust_19 REAL DEFAULT 0,
                umsatz_7_netto REAL DEFAULT 0,
                ust_7 REAL DEFAULT 0,
                ig_erwerbe_netto REAL DEFAULT 0,
                ust_ig_erwerbe REAL DEFAULT 0,
                vorsteuer_19 REAL DEFAULT 0,
                vorsteuer_7 REAL DEFAULT 0,
                vorsteuer_ig REAL DEFAULT 0,
                vorsteuer_gesamt REAL DEFAULT 0,
                ust_zahllast REAL DEFAULT 0,
                status VARCHAR(20) DEFAULT 'entwurf',
                elster_xml_pfad VARCHAR(500),
                export_datum TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        migrations_applied.append("buchhaltung_ust_voranmeldung")
    
    # Finanzplan
    if not table_exists(cursor, 'buchhaltung_finanzplan'):
        print("Erstelle: buchhaltung_finanzplan")
        cursor.execute("""
            CREATE TABLE buchhaltung_finanzplan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jahr INTEGER NOT NULL,
                monat INTEGER,
                name VARCHAR(100) NOT NULL,
                beschreibung TEXT,
                umsatz_plan REAL DEFAULT 0,
                sonstige_einnahmen_plan REAL DEFAULT 0,
                wareneinkauf_plan REAL DEFAULT 0,
                personalkosten_plan REAL DEFAULT 0,
                miete_plan REAL DEFAULT 0,
                marketing_plan REAL DEFAULT 0,
                sonstige_kosten_plan REAL DEFAULT 0,
                investitionen_plan REAL DEFAULT 0,
                umsatz_ist REAL DEFAULT 0,
                kosten_ist REAL DEFAULT 0,
                ist_freigegeben BOOLEAN DEFAULT 0,
                freigabe_datum TIMESTAMP,
                freigabe_von VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        migrations_applied.append("buchhaltung_finanzplan")
    
    # Kalkulationen
    if not table_exists(cursor, 'buchhaltung_kalkulationen'):
        print("Erstelle: buchhaltung_kalkulationen")
        cursor.execute("""
            CREATE TABLE buchhaltung_kalkulationen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                typ VARCHAR(50),
                beschreibung TEXT,
                gueltig_ab DATE,
                gueltig_bis DATE,
                basis_stundensatz REAL,
                basis_maschinenkosten REAL,
                preis_pro_1000_stiche REAL,
                preis_farbwechsel REAL,
                mindestpreis REAL,
                einrichtekosten REAL,
                material_aufschlag_prozent REAL DEFAULT 0,
                gewinn_aufschlag_prozent REAL DEFAULT 0,
                risiko_aufschlag_prozent REAL DEFAULT 0,
                kalkulation_details TEXT,
                ist_aktiv BOOLEAN DEFAULT 1,
                ist_standard BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                erstellt_von VARCHAR(100)
            )
        """)
        migrations_applied.append("buchhaltung_kalkulationen")
    
    # Wettbewerbs-Preise
    if not table_exists(cursor, 'wettbewerb_preise'):
        print("Erstelle: wettbewerb_preise")
        cursor.execute("""
            CREATE TABLE wettbewerb_preise (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anbieter VARCHAR(100) NOT NULL,
                produkt VARCHAR(200),
                verfahren VARCHAR(50),
                menge INTEGER NOT NULL,
                stueckpreis_netto REAL,
                stueckpreis_brutto REAL,
                gesamtpreis_netto REAL,
                gesamtpreis_brutto REAL,
                lieferzeit_tage INTEGER DEFAULT 0,
                mindestmenge INTEGER DEFAULT 1,
                quelle_url VARCHAR(500),
                ist_manuell BOOLEAN DEFAULT 1,
                erfasst_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                gueltig_bis TIMESTAMP,
                preis_hash VARCHAR(64) UNIQUE
            )
        """)
        migrations_applied.append("wettbewerb_preise")
    
    # ==========================================================================
    # MIGRATION 8: Kalender-System
    # ==========================================================================
    
    # Kalender-Ressourcen (Maschinen, Räume)
    if not table_exists(cursor, 'kalender_ressourcen'):
        print("Erstelle: kalender_ressourcen")
        cursor.execute("""
            CREATE TABLE kalender_ressourcen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                typ VARCHAR(50),
                beschreibung TEXT,
                maschinen_typ VARCHAR(50),
                kapazitaet VARCHAR(100),
                farbe VARCHAR(20) DEFAULT '#3788d8',
                icon VARCHAR(50),
                reihenfolge INTEGER DEFAULT 0,
                ist_aktiv BOOLEAN DEFAULT 1,
                verfuegbar_von TIME DEFAULT '08:00:00',
                verfuegbar_bis TIME DEFAULT '17:00:00',
                arbeitstage VARCHAR(50) DEFAULT '[1,2,3,4,5]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        migrations_applied.append("kalender_ressourcen")
    
    # Kalender-Termine
    if not table_exists(cursor, 'kalender_termine'):
        print("Erstelle: kalender_termine")
        cursor.execute("""
            CREATE TABLE kalender_termine (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titel VARCHAR(200) NOT NULL,
                beschreibung TEXT,
                start_datum DATE NOT NULL,
                start_zeit TIME,
                ende_datum DATE,
                ende_zeit TIME,
                ganztaegig BOOLEAN DEFAULT 0,
                termin_typ VARCHAR(30) DEFAULT 'intern',
                status VARCHAR(30) DEFAULT 'geplant',
                prioritaet INTEGER DEFAULT 2,
                farbe VARCHAR(20) DEFAULT '#3788d8',
                kunde_id INTEGER,
                auftrag_id INTEGER,
                dokument_id INTEGER,
                maschine_id INTEGER,
                mitarbeiter_id INTEGER,
                ratenzahlung_id INTEGER,
                ressource_id INTEGER,
                wiederholung VARCHAR(20) DEFAULT 'keine',
                wiederholung_ende DATE,
                parent_termin_id INTEGER,
                erinnerung_minuten INTEGER,
                erinnerung_gesendet BOOLEAN DEFAULT 0,
                notizen TEXT,
                tags VARCHAR(500),
                betrag REAL,
                erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                erstellt_von VARCHAR(100),
                aktualisiert_am TIMESTAMP,
                FOREIGN KEY (ressource_id) REFERENCES kalender_ressourcen(id),
                FOREIGN KEY (kunde_id) REFERENCES customers(id)
            )
        """)
        migrations_applied.append("kalender_termine")
    
    # Ratenzahlungen
    if not table_exists(cursor, 'ratenzahlungen'):
        print("Erstelle: ratenzahlungen")
        cursor.execute("""
            CREATE TABLE ratenzahlungen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kunde_id INTEGER NOT NULL,
                dokument_id INTEGER,
                gesamtbetrag REAL NOT NULL,
                anzahl_raten INTEGER NOT NULL,
                rate_betrag REAL NOT NULL,
                erste_rate DATE NOT NULL,
                intervall_tage INTEGER DEFAULT 30,
                bezahlte_raten INTEGER DEFAULT 0,
                restbetrag REAL,
                ist_abgeschlossen BOOLEAN DEFAULT 0,
                notizen TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (kunde_id) REFERENCES customers(id)
            )
        """)
        migrations_applied.append("ratenzahlungen")
    
    # Commit
    conn.commit()
    conn.close()
    
    # Zusammenfassung
    print("=" * 60)
    if migrations_applied:
        print(f"✓ {len(migrations_applied)} Migration(en) angewendet:")
        for m in migrations_applied:
            print(f"  - {m}")
    else:
        print("✓ Datenbank ist aktuell, keine Migrationen nötig.")
    
    return True


if __name__ == '__main__':
    run_migration()
