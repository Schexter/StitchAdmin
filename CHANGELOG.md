# StitchAdmin 2.0 - Changelog

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**

Dieses Dokument protokolliert alle wesentlichen Änderungen am StitchAdmin 2.0 Projekt.

---

## [2.0.3-beta.7] - 2025-01-07

### 📊 Buchhaltung & Controlling Modul

#### Added - Buchhaltungsmodul
- **Buchungsjournal** mit Kontenrahmen (SKR03)
- **BWA** (Betriebswirtschaftliche Auswertung)
  - Monats-/Quartals-/Jahresauswertung
  - Vorjahresvergleich
  - Rohertrag-Marge
- **USt-Voranmeldung**
  - Automatische Berechnung
  - ELSTER-kompatibler CSV-Export
- **Liquiditätsplanung**
  - Offene Forderungen
  - Cashflow-Berechnung
  - Prognose

#### Added - Export-Funktionen
- **DATEV-Export** - Buchungsstapel für Steuerberater
- **GoBD-Export** - Revisionssicheres ZIP-Archiv mit Prüfsummen
- **ELSTER-CSV** - USt-Voranmeldung
- **Excel-Export** - BWA, Journal

#### Added - Kalkulationen (Stickerei-spezifisch)
- **Stundensatz-Kalkulation** - Vollkostenbasis
- **Stickpreis-Kalkulation** - Pro 1000 Stiche, Farbwechsel, Mindestpreis
- **Deckungsbeitragsrechnung** - DB I, DB II, Break-Even

### 👕 Textildruck-Kalkulation (NEU)

#### Added - Verfahrens-Kalkulationen
- **Siebdruck**
  - Sieb-/Film-/Einrichtekosten
  - Farbkosten pro Druck
  - Staffelrabatte (5-30%)
  - Reserve/Ausschuss

- **DTG-Druck** (Direct-to-Garment)
  - Tintenkosten pro cm²
  - Vorbehandlung (dunkle Textilien)
  - Keine Mindestmenge

- **Flex/Flock-Druck**
  - Materialkosten pro cm²
  - Schnittdaten-Kosten
  - Entgitterung

#### Added - Wettbewerbsvergleich
- Manuelle Preiseingabe von Wettbewerbern
- Referenzpreise (Marktdurchschnitt)
- Automatischer Vergleich bei Kalkulation
- Preispositions-Empfehlung

### 📋 Kontenrahmen-Auswahl

#### Added - Automatische Kontenrahmen-Initialisierung
- **SKR03** vollständig (Standard)
- **SKR04** vorbereitet
- **Branchen-Vorlagen**:
  - Textildruck & Stickerei (mit speziellen Konten)
  - Handel
  - Handwerk
  - Dienstleistung

#### Branchenspezifische Konten (Textil)
- 0410-0440: Maschinen (Stick, Druck, Presse, Plotter)
- 3200-3240: Wareneingang Textilien
- 3500-3560: Material (Garne, Folien, Farben)
- 8500-8570: Erlöse nach Verfahren

#### Neue Dateien
- `src/services/textildruck_kalkulation.py`
- `src/services/wettbewerb_preise.py`
- `src/services/kontenrahmen_service.py`
- `src/templates/buchhaltung/kalkulation_textildruck.html`
- `src/templates/buchhaltung/kontenplan_setup.html`

### 📅 Kalender-System (Outlook-Style) - NEU

#### Neuer Produktionskalender
- **Ressourcen-Timeline** - Maschinen als Spalten nebeneinander
- **Ansichten**: Tag/Woche/Monat + Listenansicht
- **Drag & Drop** Terminplanung
- **Echtzeit-Auslastung** pro Maschine
- **FullCalendar 6** Integration

#### Termin-Typen
- 🟢 Produktion | 🔴 Ratenzahlung | 🔵 Kundentermin | 🟡 Wartung

#### Ratenzahlungen
- Automatische Kalendertermine für jede Rate
- Übersicht fälliger/überfälliger Raten
- 3-Tage-Vorab-Erinnerung

#### Ressourcen-Verwaltung
- Standard-Maschinen (Stick, Druck, Presse, Plotter)
- Verfügbarkeitszeiten & Auslastung

### 👥 CRM-Finanz-Verknüpfung - NEU

#### Kunden-Finanzdaten
- Umsatz gesamt & aktuelles Jahr
- Offene Posten & Überfällige
- Zahlungsmoral-Score (0-100)
- Top-Kunden nach Umsatz

#### Neue Dateien
- `src/models/kalender.py`
- `src/services/crm_finanz_service.py`
- `src/controllers/kalender_controller.py`
- `src/templates/kalender/*.html`

---

Format basierend auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/)  
Versionierung folgt [Semantic Versioning](https://semver.org/lang/de/)

---

## [Unreleased]

### In Arbeit
- Testing-Framework mit Pytest
- Legacy-Controller-Bereinigung
- Flask-Migrate Integration

---

## [2.0.3] - 2025-01-07

### 📋 Dokument-Workflow & Auftrags-Wizard (Phase 1 + 2)

#### Added - Phase 1: Basis-Implementation
- **Nummernkreise (GoBD-konform)**
  - Automatische Belegnummern-Generierung
  - Jahreswechsel-Reset
  - Konfigurierbares Format (Präfix, Stellen, Trennzeichen)
  - Admin-Interface unter `/admin/dokumente/nummernkreise`

- **Zahlungsbedingungen**
  - Verwaltung unter `/admin/dokumente/zahlungsbedingungen`
  - Skonto-Berechnung
  - Anzahlungs-Optionen (% oder Festbetrag)
  - Standard-Bedingung für neue Kunden

- **Document-Workflow Models**
  - `BusinessDocument` - Einheitliches Dokumenten-Model
  - `DocumentPosition` - Positionen mit automatischer MwSt-Berechnung
  - `DocumentPayment` - Zahlungsverfolgung
  - Enums für DokumentTyp, DokumentStatus, PositionsTyp

#### Added - Phase 2: Auftrags-Wizard
- **5-Step Wizard für Auftragserfassung**
  - Step 1: Kunde & Grunddaten (Kundensuche, Dokumenttyp, Auftragsart)
  - Step 2: Textilien auswählen (Artikelsuche, Größenstaffel)
  - Step 3: Veredelung definieren (Stickerei/Druck, DST-Upload-Analyse)
  - Step 4: Kalkulation (automatische Preisberechnung, Mengenrabatt)
  - Step 5: Zusammenfassung & Abschluss

- **API-Endpoints für AJAX**
  - `/wizard/api/kunden/suche` - Kundensuche
  - `/wizard/api/artikel/suche` - Artikelsuche mit Filter
  - `/wizard/api/artikel/<id>/varianten` - Varianten laden
  - `/wizard/api/design/analyse` - DST-Datei analysieren (pyembroidery)
  - `/wizard/api/kalkulation/berechnen` - Live-Kalkulation

- **Kalkulations-Engine**
  - Automatische Textil-Preisberechnung
  - Stickerei-Kalkulation (Stiche × Preis/1000)
  - Druck-Kalkulation (Fläche × Preis/cm²)
  - Einrichtungspauschalen
  - Mengenrabatt-Staffel (5-20%)

#### Neue Dateien
- `src/controllers/order_wizard_controller.py` - Wizard-Controller
- `src/templates/wizard/step1.html` - Kunde & Grunddaten
- `src/templates/wizard/step2.html` - Textilien auswählen
- `src/templates/wizard/step3.html` - Veredelung definieren
- `src/templates/wizard/step4.html` - Kalkulation
- `src/templates/wizard/step5.html` - Zusammenfassung

#### Geänderte Dateien
- `app.py` - Wizard-Blueprint und Angebote-Workflow-Blueprint registriert

---

## [2.0.3-beta.2] - 2025-01-07

### 📄 Phase 3: Angebote-Modul (Document-Workflow Integration)

#### Added - Angebote CRUD
- **Angebote-Übersicht** (`/angebote-v2/`)
  - Filterfunktion nach Status und Kunde
  - Statistik-Karten (Gesamt, Entwurf, Versendet, Angenommen, Abgelehnt, Überfällig)
  - Tabellen-Ansicht mit Schnellaktionen

- **Angebot erstellen** (`/angebote-v2/neu`)
  - Kundenauswahl mit Details
  - Betreff & Texte (Einleitung, Schlussbemerkung)
  - Dynamische Positionseingabe mit Artikelsuche
  - Zahlungsbedingungen & Gültigkeit
  - Live-Summenberechnung

- **Angebot bearbeiten** (`/angebote-v2/<id>/bearbeiten`)
  - Nur für Entwürfe möglich
  - Positionen hinzufügen/ändern/löschen
  - Rabatt anpassen

- **Status-Workflow**
  - Versenden (als versendet markieren)
  - Annehmen (Kunde hat angenommen)
  - Ablehnen (mit Begründung)
  - Stornieren
  - In Auftragsbestätigung umwandeln

#### Added - PDF-Generierung
- **ReportLab Integration**
  - Professionelles PDF-Layout mit Kopfbereich
  - Empfänger-Adressblock
  - Dokumentinfo (Nummer, Datum, Gültigkeit)
  - Positionen-Tabelle mit Formatierung
  - Summen-Block (Netto, MwSt, Brutto)
  - Fußbereich mit Zahlungsbedingungen

- **PDF-Routen**
  - `/angebote-v2/<id>/pdf` - Download
  - `/angebote-v2/<id>/pdf/vorschau` - Browser-Vorschau

#### Added - E-Mail-Versand
- **E-Mail-Formular** (`/angebote-v2/<id>/email`)
  - Empfänger (vorausgefüllt aus Kundendaten)
  - Betreff (automatisch generiert)
  - Nachrichtentext (editierbar)
  - PDF automatisch als Anhang

- **SMTP-Integration**
  - Konfiguration über Umgebungsvariablen
  - Status-Update nach Versand

#### Neue Dateien
- `src/controllers/angebote_workflow_controller.py` - Controller mit CRUD, PDF, E-Mail
- `src/templates/angebote_v2/index.html` - Übersicht
- `src/templates/angebote_v2/show.html` - Detailansicht
- `src/templates/angebote_v2/neu.html` - Neues Angebot
- `src/templates/angebote_v2/bearbeiten.html` - Bearbeiten
- `src/templates/angebote_v2/email.html` - E-Mail senden

---

## [2.0.3-beta.3] - 2025-01-07

### 📝 Phase 4: Auftragsbestätigungen (Document-Workflow Integration)

#### Added - AB CRUD
- **AB-Übersicht** (`/auftraege/`)
  - Filterfunktion nach Status und Kunde
  - Statistik-Karten (Gesamt, Entwurf, Versendet, In Bearbeitung, Geliefert)
  - Tabellen-Ansicht mit Schnellaktionen

- **AB erstellen** (`/auftraege/neu`)
  - Manuelle Erstellung mit Kundenauswahl
  - Kundenreferenz & Bestellnummer
  - Dynamische Positionseingabe
  - Lieferdatum & Zahlungsbedingungen

- **AB aus Angebot** (`/auftraege/aus-angebot/<id>`)
  - Automatische Konvertierung angenommener Angebote
  - Übernahme aller Positionen und Daten
  - Verknüpfung zum Vorgänger-Angebot

- **AB bearbeiten** (`/auftraege/<id>/bearbeiten`)
  - Nur für Entwürfe möglich
  - Positionen hinzufügen/ändern/löschen

#### Added - Status-Workflow
- `Entwurf` → `Versendet` → `In Bearbeitung` → `Geliefert`
- Stornieren möglich
- Verknüpfte Dokumente anzeigen (Lieferscheine, Rechnungen)

#### Added - Folgedokumente
- **Lieferschein erstellen** (`/auftraege/<id>/lieferschein`)
  - Automatische Positionskopie (ohne Dienstleistungen)
  - Auftrag wird als "Geliefert" markiert
  - Verweis auf Vorgänger-AB

- **Rechnung erstellen** (`/auftraege/<id>/rechnung`)
  - Unterstützt: Rechnung, Anzahlung, Teilrechnung
  - Automatische Fälligkeitsberechnung
  - Zahlungstext aus Zahlungsbedingung

#### Added - PDF-Generierung
- **ReportLab Integration**
  - Professionelles AB-Layout
  - Dokumentinfo inkl. Lieferdatum, Kundenreferenz
  - Positionstabelle mit Formatierung
  - Summenblock

- **PDF-Routen**
  - `/auftraege/<id>/pdf` - Download
  - `/auftraege/<id>/pdf/vorschau` - Browser-Vorschau

#### Neue Dateien
- `src/controllers/auftraege_controller.py` - Controller mit CRUD, PDF, Folgedokumente
- `src/templates/auftraege/index.html` - Übersicht
- `src/templates/auftraege/show.html` - Detailansicht mit Aktionen
- `src/templates/auftraege/neu.html` - Neuer Auftrag
- `src/templates/auftraege/bearbeiten.html` - Bearbeiten

#### Geänderte Dateien
- `app.py` - auftraege_bp Blueprint registriert

---

## [2.0.3-beta.4] - 2025-01-07

### 🚚 Phase 5: Lieferscheine (Document-Workflow Integration)

#### Added - Lieferschein CRUD
- **Lieferschein-Übersicht** (`/lieferscheine/`)
  - Filterfunktion nach Status und Kunde
  - Statistik-Karten (Gesamt, Offen, Heute zu liefern, Ausgeliefert)
  - Tabellen-Ansicht mit Schnellaktionen

- **Lieferschein manuell erstellen** (`/lieferscheine/neu`)
  - Kundenauswahl mit Lieferadresse
  - Versandart (Versand, Abholung, Spedition)
  - Sendungsnummer/Tracking
  - Dynamische Positionseingabe

- **Lieferschein aus Auftrag** (`/lieferscheine/aus-auftrag/<id>`)
  - Positionsauswahl mit Liefermengen
  - Teillieferung unterstützt
  - Auftrag wird entsprechend aktualisiert

- **Lieferschein bearbeiten** (`/lieferscheine/<id>/bearbeiten`)
  - Nur für offene Lieferscheine
  - Positionen ändern

#### Added - Status-Workflow
- `Entwurf/Offen` → `Ausgeliefert`
- Teillieferung: Auftrag wird "Teilgeliefert"
- Volllieferung: Auftrag wird "Geliefert"
- Stornieren möglich

#### Added - Folgedokumente
- **Rechnung aus Lieferschein** (`/lieferscheine/<id>/rechnung`)
  - Preise werden aus Vorgänger-Auftrag geholt
  - Automatische Verknüpfung

#### Added - PDF-Generierung
- **Lieferschein-PDF ohne Preise!**
  - Lieferadresse prominent
  - Versandart & Tracking
  - Positionen mit Artikelnummer & Menge
  - Empfangsbestätigung (Unterschriftsfeld)

#### Neue Dateien
- `src/controllers/lieferscheine_controller.py` - Controller mit CRUD, PDF
- `src/templates/lieferscheine/index.html` - Übersicht
- `src/templates/lieferscheine/show.html` - Detailansicht
- `src/templates/lieferscheine/neu.html` - Neuer Lieferschein
- `src/templates/lieferscheine/aus_auftrag.html` - Aus Auftrag erstellen
- `src/templates/lieferscheine/bearbeiten.html` - Bearbeiten

#### Geänderte Dateien
- `app.py` - lieferscheine_bp Blueprint registriert

---

## [2.0.3-beta.5] - 2025-01-07

### 💰 Phase 6: Rechnungen & Zahlungen (Document-Workflow Integration)

#### Added - Rechnungs-CRUD
- **Rechnungs-Übersicht** (`/rechnungen/`)
  - Filterfunktion nach Status und Kunde
  - Statistik-Karten (Gesamt, Offen, Teilbezahlt, Überfällig, Bezahlt, Offene Summe)
  - Farbliche Markierung überfälliger Rechnungen

- **Rechnung erstellen** (`/rechnungen/neu`)
  - Manuell mit Kundenauswahl
  - Rechnungstyp: Normal, Anzahlung, Teilrechnung
  - Zahlungsbedingung mit automatischer Fälligkeitsberechnung
  - Dynamische Positionseingabe

- **Rechnung bearbeiten** (`/rechnungen/<id>/bearbeiten`)
  - Nur wenn noch offen und keine Zahlungen

#### Added - Zahlungsverwaltung
- **Zahlung erfassen** (`/rechnungen/<id>/zahlung`)
  - Zahlungsarten: Überweisung, Bar, EC-Karte, Kreditkarte, PayPal, Lastschrift
  - Transaktions-ID und Bank-Referenz
  - Automatische Status-Aktualisierung (Offen → Teilbezahlt → Bezahlt)
  - Schnellauswahl für Vollbetrag und Skonto

- **Zahlung löschen** (`/rechnungen/<id>/zahlung/<zahlung_id>/loeschen`)
  - Status wird automatisch neu berechnet

#### Added - Status-Workflow
- `Offen` → `Teilbezahlt` → `Bezahlt`
- Überfälligkeits-Tracking mit Tageberechnung
- Mahnstufen (1, 2, 3, ...)
- Stornieren möglich (außer bezahlte Rechnungen)

#### Added - Gutschriften
- **Gutschrift erstellen** (`/rechnungen/<id>/gutschrift`)
  - Automatische Kopie aller Positionen mit negativen Beträgen
  - Verknüpfung zur Original-Rechnung

#### Added - PDF-Generierung
- **Professionelles Rechnungs-PDF**
  - Rechnungsadresse
  - Leistungsdatum und Fälligkeitsdatum
  - Positionstabelle mit Summen
  - Zahlungstext aus Zahlungsbedingung
  - Bankverbindung

#### Neue Dateien
- `src/controllers/rechnungen_controller.py` - Controller mit CRUD, Zahlungen, PDF
- `src/templates/rechnungen/index.html` - Übersicht mit Statistiken
- `src/templates/rechnungen/show.html` - Detailansicht mit Zahlungen
- `src/templates/rechnungen/neu.html` - Neue Rechnung
- `src/templates/rechnungen/bearbeiten.html` - Bearbeiten
- `src/templates/rechnungen/zahlung.html` - Zahlung erfassen

#### Geänderte Dateien
- `app.py` - rechnungen_bp Blueprint registriert

---

## [2.0.3-beta.6] - 2025-01-07

### 🛠️ Setup-Wizard & Speicherpfad-Konfiguration

#### Added - Installations-Assistent
- **8-Schritte Setup-Wizard** (`/setup/`)
  1. Willkommen & Feature-Übersicht
  2. Lizenzvereinbarung
  3. Firmendaten (Name, Adresse, Steuern)
  4. Logo & Branding (Farben)
  5. Speicherpfade konfigurieren
  6. Bankverbindung
  7. E-Mail-Einstellungen
  8. Administrator-Konto & Abschluss

- **Automatische Erkennung** ob Setup bereits abgeschlossen
- **Demo-Modus** zum Überspringen (nur im Debug)

#### Added - StorageSettings Model
- **Konfigurierbare Speicherpfade** für:
  - Angebote, Auftragsbestätigungen, Lieferscheine
  - Rechnungen (Ausgang + Eingang)
  - Gutschriften, Mahnungen
  - Designs, Design-Freigaben
  - Backups, Importe, Exporte

- **Ordnerstruktur-Optionen:**
  - Jahr/Monat (empfohlen)
  - Nur Jahr
  - Nach Kunde
  - Flach

- **Dateinamen-Optionen:**
  - Kundenname in Dateinamen
  - Datum in Dateinamen

- **Hilfsfunktionen:**
  - `get_full_path()` - Vollständiger Pfad für Dokumenttyp
  - `get_filename()` - Dateiname nach Einstellungen
  - `ensure_path_exists()` - Ordner erstellen
  - `validate_paths()` - Pfade prüfen
  - `create_folder_structure()` - Alle Ordner anlegen

#### Neue Dateien
- `src/models/storage_settings.py` - Speicherpfad-Model
- `src/controllers/setup_wizard_controller.py` - Setup-Controller
- `src/templates/setup/base_setup.html` - Basis-Template
- `src/templates/setup/welcome.html` - Willkommen
- `src/templates/setup/license.html` - Lizenz
- `src/templates/setup/company.html` - Firmendaten
- `src/templates/setup/branding.html` - Logo & Farben
- `src/templates/setup/storage.html` - Speicherpfade
- `src/templates/setup/bank.html` - Bankverbindung
- `src/templates/setup/email.html` - E-Mail
- `src/templates/setup/admin.html` - Administrator
- `src/templates/setup/finish.html` - Abschluss

#### Geänderte Dateien
- `app.py` - setup_bp Blueprint registriert, Setup-Check bei Root-Route

### 🔗 ZugPferd-Integration & PDF-Service

#### Added - Document PDF Service
- **Zentraler PDF-Service** (`src/services/document_pdf_service.py`)
  - Einheitliche PDF-Generierung für alle Dokumenttypen
  - Automatische Speicherpfad-Ermittlung via StorageSettings
  - ZugPferd-Integration für Rechnungen
  - Firmenlogo aus CompanySettings
  - Deutsche Zahlenformatierung

- **Methoden:**
  - `get_save_path()` - Ermittelt Speicherpfad basierend auf Einstellungen
  - `save_pdf()` - Speichert PDF am konfigurierten Ort
  - `generate_document_pdf()` - Generisches PDF für alle Dokumenttypen
  - `generate_rechnung_pdf()` - Rechnung mit optionalem ZugPferd-XML
  - `get_company_header_data()` - Lädt Firmendaten für PDF-Header

#### Changed - Rechnungs-Controller
- PDF-Generierung nutzt jetzt neuen DocumentPDFService
- Automatische ZugPferd-XML-Einbettung (PDF/A-3)
- Konfigurierbare Speicherpfade
- Neue Route `/rechnungen/<id>/pdf/zugpferd` für explizite E-Rechnung

#### Added - Master-Migrations-Script
- `migrations/run_all_migrations.py`
  - Prüft und erstellt storage_settings
  - Erweitert business_documents um PDF/XML-Felder
  - Erstellt nummernkreis und zahlungsbedingung falls fehlend
  - Erweitert company_settings
  - Kann mehrfach ausgeführt werden (idempotent)

#### Neue/Geänderte Dateien
- `src/services/document_pdf_service.py` - Zentraler PDF-Service
- `src/controllers/rechnungen_controller.py` - ZugPferd-Integration
- `migrations/run_all_migrations.py` - Master-Migration

### 📂 NAS/Netzlaufwerk-Unterstützung für Archive

#### Added - Separate Archive auf NAS
- **Design-Archiv** - DST, EMB, PES Stickdateien
  - Separates Verzeichnis aktivierbar
  - UNC-Pfade unterstützt: `\\NAS\Designs`
  - Netzlaufwerke: `Z:\Stickdateien`

- **Stickdateien-Archiv** - Produktionsfertige Dateien
  - Für Maschinen-Output
  - Separater Speicherort möglich

- **Freigaben-Archiv** - Kundenfreigabe-PDFs
  - Bestätigungen und Genehmigungen
  - Kann auf NAS liegen

- **Motiv-Archiv** - Grafiken & Vorlagen
  - AI, PSD, Vektor-Dateien
  - Separates Verzeichnis

#### Changed - StorageSettings Model
- Neue Felder für separate Archive:
  - `design_archiv_path`, `design_archiv_aktiv`
  - `stickdateien_path`, `stickdateien_aktiv`
  - `freigaben_archiv_path`, `freigaben_archiv_aktiv`
  - `motiv_archiv_path`, `motiv_archiv_aktiv`

- Erweiterte Pfad-Validierung:
  - UNC-Pfade (\\\server\share)
  - Netzlaufwerke (Z:\)
  - Schreibrechte-Prüfung
  - Erreichbarkeits-Test

- Neue Hilfsmethode `_apply_subfolders()`
- Erweiterte `_check_path_access()` für Netzlaufwerke

#### Changed - UI
- Neue Sektion "Separate Archive (NAS/Netzlaufwerk)"
- Toggle-Switches zum Aktivieren/Deaktivieren
- NAS-Hinweise und Beispiel-Pfade
- Pfad-Test-Funktion

---

## [2.0.2] - 2025-11-23

### 🔐 Permission-System & Personalisierbares Dashboard

#### Added - Neue Features
- **Permission-System**
  - Modul-basierte Berechtigungen (View, Create, Edit, Delete)
  - Admin-Interface für Berechtigungsverwaltung
  - User-spezifische Modul-Zugriffe
  - Admin-Only Module
  - Schnell-Zuweisung für Berechtigungen

- **Personalisierbares Dashboard**
  - Drag & Drop Funktionalität (SortableJS)
  - Module ein-/ausblenden per User
  - Individuelle Reihenfolge pro User
  - Auto-Save der Dashboard-Konfiguration
  - Edit-Mode mit visueller Rückmeldung

- **Neue Datenmodelle**
  - `Module` - Systemmodule definieren
  - `ModulePermission` - Berechtigungen pro User & Modul
  - `DashboardLayout` - Persönliche Dashboard-Layouts

- **API-Endpunkte**
  - `/api/dashboard/layout` - Layout laden/speichern
  - `/api/dashboard/module/<id>/toggle` - Sichtbarkeit umschalten
  - `/api/dashboard/reset` - Dashboard zurücksetzen
  - `/admin/permissions/*` - Berechtigungsverwaltung

- **Helper-Funktionen**
  - `has_module_permission()` - Berechtigungsprüfung
  - `@module_required` - Route-Decorator
  - `get_user_modules()` - User-Module abrufen
  - `get_user_dashboard_modules()` - Dashboard-Module mit Layout

- **Templates**
  - `dashboard_personalized.html` - Neues Dashboard mit Drag & Drop
  - `permissions/index.html` - Berechtigungsverwaltung
  - `permissions/user_permissions.html` - User-Berechtigungen bearbeiten

- **Setup-Scripts**
  - `scripts/setup_permissions.py` - Tabellen erstellen
  - `scripts/init_modules.py` - Basis-Module initialisieren
  - `scripts/update_app_for_permissions.py` - app.py automatisch updaten

#### Changed - Änderungen
- Dashboard-Route aktualisiert:
  - Nutzt jetzt `get_user_dashboard_modules()`
  - Rendert `dashboard_personalized.html`
  - Berücksichtigt Berechtigungen & Layouts

- Context Processor erweitert:
  - Permission-Helper in Templates verfügbar
  - `has_permission()` Template-Funktion
  - `get_user_modules()` Template-Funktion

- App-Version erhöht: 2.0.1 → 2.0.2

#### Documentation
- `docs/PERMISSION_SYSTEM.md` - Vollständige Dokumentation
  - Installation & Setup
  - Verwendung (Admin & User)
  - API-Dokumentation
  - Entwickler-Guide
  - Troubleshooting
  - Beispiel-Workflows

#### Technical Details
- 8 Basis-Module initialisiert:
  - CRM (Kundenverwaltung)
  - Production (Aufträge & Fertigung)
  - POS (Kasse)
  - Accounting (Buchhaltung)
  - Documents (Dokumente & Post)
  - Administration (Verwaltung) - Admin-Only
  - Warehouse (Lager)
  - Design Archive (Design-Archiv)

- SortableJS 1.15.0 für Drag & Drop
- Bootstrap 5 Toast für Benachrichtigungen
- JSON-Speicherung für Dashboard-Layouts

#### Migration Notes
- Bestehende User: Müssen Berechtigungen vom Admin erhalten
- Admin-User: Haben automatisch Vollzugriff
- Neue User: Bekommen Standard-Berechtigungen (default_enabled)
- Backup der app.py wird automatisch erstellt

---

## [2.0.0-alpha] - 2025-11-05

### 🎉 Projekt-Initialisierung & Migration

#### Added - Neue Features
- **Projekt-Dokumentation erstellt**
  - `README.md` - Umfassende Projekt-Dokumentation
  - `TODO.md` - Meilensteine und Aufgabenplanung
  - `CHANGELOG.md` - Diese Datei
  - `error.log` - Fehlerprotokoll initialisiert
  - `PROJEKT_STRUKTUR.md` - Detaillierte Struktur-Dokumentation
  - `QUICKSTART.md` - Schnellstart-Anleitung

- **Kern-Module implementiert (40% Projektfortschritt)**
  - ✅ Kundenverwaltung (Privat/Geschäftskunden)
  - ✅ Artikelverwaltung mit L-Shop Excel-Import
  - ✅ Auftragsverwaltung (Stickerei/Druck/DTF)
  - ✅ Produktionsverwaltung mit Maschinenzuordnung
  - ✅ Garnverwaltung mit Lagerbestand
  - ✅ Lieferantenverwaltung mit Bestellsystem
  - ✅ Versandverwaltung mit Tracking
  - ✅ Rechnungsmodul (TSE-konform, GoBD)
  - ✅ Design-Workflow mit DST-Analyse
  - ✅ Einstellungsverwaltung

- **Datenbank-Models (SQLAlchemy 2.0)**
  - `User` - Benutzer mit Flask-Login
  - `Customer` - Kunden (Privat/Geschäft)
  - `Article` - Artikel mit Varianten
  - `Order` / `OrderItem` - Aufträge mit Positionen
  - `OrderStatusHistory` - Status-Tracking
  - `Machine` - Maschinen und Equipment
  - `ProductionSchedule` - Produktionsplanung
  - `Thread` / `ThreadStock` / `ThreadUsage` - Garnverwaltung
  - `Shipment` / `ShipmentItem` - Versendungen
  - `Supplier` / `SupplierOrder` - Lieferanten und Bestellungen
  - `ActivityLog` - Aktivitätsprotokoll
  - `ProductCategory` / `Brand` - Kategorien und Marken
  - `ArticleVariant` - Artikel-Varianten (Farbe/Größe)
  - `ArticleSupplier` - Artikel-Lieferanten-Zuordnung
  - Rechnungsmodul-Models: `Rechnung`, `KassenBeleg`, `TSEKonfiguration`, etc.

- **Controller-Struktur (Flask Blueprints)**
  - 38 Controller-Module implementiert
  - DB-basierte Controller für alle Kern-Module
  - Rechnungsmodul mit TSE-Konformität
  - Design-Workflow-Controller
  - API-Controller (Basis)
  - Auth-Controller mit Flask-Login
  - Backup-Controller

- **Utilities**
  - `dst_analyzer.py` - DST-Stickdatei-Analyse (Stichzahl, Größe)
  - `design_upload.py` - Sichere Datei-Uploads
  - `pdf_analyzer.py` / `pdf_analyzer_lite.py` - PDF-Verarbeitung
  - `activity_logger.py` - Aktivitätsprotokollierung
  - `email_service.py` - E-Mail-Versand
  - `logger.py` - Zentrales Logging
  - `security.py` - Sicherheitsfunktionen
  - `filters.py` - Custom Jinja2-Filter

- **Frontend**
  - 126 Jinja2-Templates
  - Base-Templates mit verschiedenen Layouts
  - Wiederverwendbare Includes (_navbar, _sidebar, etc.)
  - Responsive CSS
  - JavaScript für Interaktivität

- **Features**
  - L-Shop Excel-Import für Textilien
  - DST-Datei-Analyse mit automatischer Stichzahl-Erkennung
  - Thumbnail-Generierung für Designs
  - TSE-konforme Kassenbelege
  - ZUGFeRD-XML-Export für Rechnungen
  - Preiskalkulation mit mehrstufigen Faktoren
  - Status-Tracking für Aufträge mit Historie
  - Textile-Bestellstatus beim Lieferanten
  - Garnverbrauch-Erfassung
  - Aktivitätsprotokoll für Audit-Trail

#### Changed - Änderungen
- **Migration von StitchAdmin zu StitchAdmin2.0**
  - Projektverzeichnis umstrukturiert
  - Alle Dateien nach `C:\SoftwareEntwicklung\StitchAdmin2.0` verschoben
  - `src/`-Verzeichnis für bessere Code-Organisation
  - Datenbank und Uploads migriert

- **Architektur-Umstellung**
  - Von JSON-basierter zu Datenbank-basierter Datenhaltung
  - SQLAlchemy 2.0 als ORM
  - Flask Application Factory Pattern
  - Blueprint-basierte Modulstruktur

- **Python 3.13 Kompatibilität**
  - SQLAlchemy auf Version ≥2.0.36 aktualisiert
  - `fix_sqlalchemy.bat` für automatische Reparatur

#### Fixed - Behobene Fehler
- SQLAlchemy-Kompatibilitätsprobleme mit Python 3.13
- Import-Pfade nach Migration korrigiert
- Template-Pfade angepasst
- Datenbank-Initialisierung verbessert

#### Deprecated - Veraltet (wird entfernt)
- JSON-basierte Legacy-Controller (werden in v2.1.0 entfernt)
  - `customer_controller.py` (nicht DB-basiert)
  - `article_controller.py` (nicht DB-basiert)
  - `order_controller.py` (nicht DB-basiert)
  - `machine_controller.py` (nicht DB-basiert)
  - `thread_controller.py` (nicht DB-basiert)
  - `production_controller.py` (nicht DB-basiert)
  - `shipping_controller.py` (nicht DB-basiert)
  - `supplier_controller.py` (nicht DB-basiert)

#### Security - Sicherheit
- ✅ Flask-Login Session-Management implementiert
- ✅ CSRF-Schutz aktiviert (Flask-WTF)
- ✅ Password-Hashing mit Werkzeug
- ✅ SQL-Injection-Schutz durch SQLAlchemy ORM
- ✅ Sichere Datei-Uploads mit Whitelist
- ✅ Input-Validierung mit WTForms
- ✅ Aktivitätsprotokoll für Audit-Trail

---

## [1.0.0] - Entwicklungshistorie (vor Migration)

### Kontext
StitchAdmin 1.0 wurde ursprünglich als Monolith mit JSON-basierter Datenhaltung entwickelt. Die Migration zu Version 2.0 erfolgte aufgrund folgender Faktoren:

- Bessere Datenkonsistenz durch relationale Datenbank
- Skalierbarkeit und Performance
- Einfacheres Querying mit SQLAlchemy
- Professionellere Architektur
- Vorbereitung auf Multi-User-Betrieb

### Hauptfeatures (v1.0)
- Basis-Kundenverwaltung (JSON)
- Artikel-Import aus Excel
- Einfache Auftragsverwaltung
- Grundlegende Garnverwaltung
- Statische HTML-Templates

### Lessons Learned
- JSON-Dateien ungeeignet für komplexe Beziehungen
- Manuelle Datenintegrität fehleranfällig
- Concurrent Access problematisch
- Backup & Recovery kompliziert

→ **Entscheidung für Datenbank-basierte Lösung in v2.0**

---

## Entwicklungsnotizen

### Architektur-Entscheidungen

#### 2025-11-05: Projekt-Strukturierung
**Problem:** Fehlende Pflichtdateien (README, TODO, CHANGELOG, error.log)  
**Lösung:** Alle Pflichtdateien gemäß Custom Instructions erstellt  
**Begründung:** Nachhaltige Entwicklung erfordert vollständige Dokumentation

**Entscheidung:** Legacy-Controller werden in Meilenstein 1 entfernt  
**Begründung:** DB-basierte Controller sind vollständig funktional  
**Risiko:** Minimal, da keine Funktionsverluste

#### 2025-11-05: Testing-Strategie
**Entscheidung:** Fokus auf Integration-Tests statt Unit-Tests  
**Begründung:** Mehr Wert für weniger Aufwand bei kleineren Projekten  
**Ziel:** 60% Coverage mit Integration-Tests

#### 2025-11-05: SQLAlchemy 2.0 Migration
**Problem:** Python 3.13 erfordert neuere SQLAlchemy-Version  
**Lösung:** Update auf SQLAlchemy ≥2.0.36  
**Script:** `fix_sqlalchemy.bat` für automatische Aktualisierung  
**Impact:** Breaking Changes in Query-API, aber bessere Performance

### Bekannte Probleme (Stand: 05.11.2025)

1. **Tests-Verzeichnis leer**
   - Status: In Arbeit
   - Geplant: Meilenstein 1
   - Pytest-Framework wird aufgesetzt

2. **Legacy-Controller noch vorhanden**
   - Status: Zur Entfernung vorgesehen
   - Geplant: Meilenstein 1
   - Keine Funktionsverluste erwartet

3. **Keine Datenbank-Migrations**
   - Status: Geplant
   - Lösung: Flask-Migrate Integration
   - Geplant: Meilenstein 1

4. **API-Dokumentation fehlt**
   - Status: Geplant
   - Lösung: OpenAPI/Swagger
   - Geplant: Meilenstein 3

### Performance-Optimierungen

#### Geplant
- [ ] Datenbank-Indexes für häufig genutzte Felder
- [ ] Lazy-Loading für große Listen
- [ ] Redis-Caching für Sessions
- [ ] Query-Optimierung (N+1 Probleme)
- [ ] Thumbnail-Cache optimieren

### Sicherheits-Verbesserungen

#### Geplant
- [ ] HTTPS-Konfiguration für Produktion
- [ ] Rate-Limiting implementieren
- [ ] Security-Headers erweitern
- [ ] Content Security Policy (CSP)
- [ ] Input-Sanitization verschärfen
- [ ] Audit-Log erweitern

---

## Version History - Zusammenfassung

| Version | Datum | Status | Beschreibung |
|---------|-------|--------|--------------|
| **2.0.0-alpha** | 05.11.2025 | 🟡 Alpha | Erste öffentliche Version, ~40% fertig |
| 1.0.0 | 2024 | ⚫ Veraltet | JSON-basierte Version (vor Migration) |

---

## Upgrade-Hinweise

### Von 1.0 zu 2.0

**Wichtig:** Version 2.0 ist **nicht** rückwärtskompatibel mit 1.0!

#### Daten-Migration
Die Daten aus JSON-Dateien müssen manuell in die neue Datenbank importiert werden:

1. Backup der JSON-Dateien erstellen
2. Datenbank initialisieren (`python app.py`)
3. Migrations-Skript ausführen (in Entwicklung)
4. Daten validieren
5. JSON-Dateien als Backup aufbewahren

#### Konfiguration
- `.env`-Datei erstellen (siehe README.md)
- `SECRET_KEY` setzen
- E-Mail-Konfiguration anpassen (optional)

#### Breaking Changes
- Alle API-Endpunkte geändert
- JSON-basierte Controller entfernt
- Datenstruktur komplett neu
- Template-Struktur umorganisiert

---

## Contributors

**Hauptentwickler:** Hans Hahn

---

## Support & Feedback

Bei Fragen oder Problemen:
1. `error.log` prüfen
2. `README.md` konsultieren
3. `PROJEKT_STRUKTUR.md` für Details

---

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Letzte Aktualisierung:** 05.11.2025  
**Version:** 2.0.0-alpha
