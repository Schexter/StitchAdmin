# StitchAdmin 2.0 - Dokumentations-Index

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Version:** 2.0.0-alpha  
**Stand:** November 2025

---

## 📚 Dokumentationsstruktur

Diese Dokumentation bietet eine vollständige technische Übersicht über StitchAdmin 2.0.

### Verfügbare Dokumente

1. **[README_KOMPLETT.md](./01_README_KOMPLETT.md)**
   - Projektübersicht
   - Systemarchitektur
   - Vollständige Datenbankstruktur (17 Haupt-Tabellen + 10 Rechnungsmodul-Tabellen)
   - Installation und Setup
   - Deployment-Anleitung

2. **[WORKFLOWS.md](./02_WORKFLOWS.md)**
   - Detaillierte Workflow-Diagramme (Mermaid)
   - 10 Haupt-Workflows:
     - Kundenverwaltung
     - Artikelverwaltung
     - Auftragsverwaltung
     - Design-Workflow
     - Produktions-Workflow
     - Lieferanten-Workflow
     - Kassen-Workflow
     - Rechnungs-Workflow
     - Versand-Workflow
     - Garnverwaltung

3. **[KLASSEN_BEZIEHUNGEN.md](./03_KLASSEN_BEZIEHUNGEN.md)**
   - Gesamt-Klassendiagramm
   - Detaillierte Klassen-Beschreibungen
   - Beziehungs-Matrix
   - Vererbungshierarchie
   - Model-Kategorien (Aggregate Roots, Entities, Value Objects)

4. **[FUNKTIONSUEBERSICHT.md](./04_FUNKTIONSUEBERSICHT.md)**
   - Alle Controller-Funktionen
   - Service-Funktionen
   - Util-Funktionen
   - Model-Methoden
   - API-Dokumentation

---

## 🔑 Schnellzugriff

### Kernmodule

#### 1. Kundenverwaltung
- **Controller:** `customer_controller_db.py`
- **Model:** `Customer`
- **Funktionen:** 
  - Privat-/Geschäftskunden
  - Vollständige Kontakt- und Adressdaten
  - Auftrags- und Rechnungshistorie
- **Workflow:** Siehe [WORKFLOWS.md - Abschnitt 1](./02_WORKFLOWS.md#1-kundenverwaltung-workflow)

#### 2. Artikelverwaltung
- **Controller:** `article_controller_db.py`
- **Models:** `Article`, `ArticleVariant`, `ProductCategory`, `Brand`
- **Services:** `lshop_import_service.py`
- **Funktionen:**
  - L-Shop Excel-Import
  - Varianten-Management (Farbe/Größe)
  - Automatische Preiskalkulation
  - Lagerbestandsverwaltung
- **Workflow:** Siehe [WORKFLOWS.md - Abschnitt 2](./02_WORKFLOWS.md#2-artikelverwaltung-workflow)

#### 3. Auftragsverwaltung
- **Controller:** `order_controller_db.py`
- **Models:** `Order`, `OrderItem`, `OrderStatusHistory`
- **Utils:** `dst_analyzer.py`, `design_upload.py`
- **Funktionen:**
  - Stickerei-/Druck-/Kombinierte Aufträge
  - Design-Upload mit DST-Analyse
  - Stichzahl-basierte Preiskalkulation
  - Status-Tracking
  - Textilien-Bestellung
- **Workflow:** Siehe [WORKFLOWS.md - Abschnitt 3](./02_WORKFLOWS.md#3-auftrags-workflow)

#### 4. Design-Workflow
- **Controller:** `design_workflow_controller.py`
- **Funktionen:**
  - Design-Upload (DST, EMB, PES, etc.)
  - Automatische DST-Analyse
  - Lieferanten-Bestellung
  - Status-Tracking (none → ordered → received → ready)
  - Thumbnail-Generierung
- **Workflow:** Siehe [WORKFLOWS.md - Abschnitt 4](./02_WORKFLOWS.md#4-design-workflow)

#### 5. Produktionsverwaltung
- **Controller:** `production_controller_db.py`
- **Models:** `Machine`, `ProductionSchedule`
- **Funktionen:**
  - Maschinenkapazitäts-Planung
  - Auftrags-Zuweisung
  - Produktionszeit-Kalkulation
  - Garnverbrauch-Tracking
- **Workflow:** Siehe WORKFLOWS.md - Abschnitt 5

#### 6. Garnverwaltung
- **Controller:** `thread_controller_db.py`
- **Models:** `Thread`, `ThreadStock`, `ThreadUsage`
- **Funktionen:**
  - Garnfarben mit Herstellercodes
  - Lagerbestandsverwaltung
  - Verbrauchserfassung
  - Nachbestellvorschläge
  - PDF-Import von Garnkarten
- **Workflow:** Siehe WORKFLOWS.md - Abschnitt 10

#### 7. Lieferantenverwaltung
- **Controller:** `supplier_controller_db.py`
- **Models:** `Supplier`, `SupplierOrder`, `SupplierContact`
- **Funktionen:**
  - Lieferanten-Stammdaten
  - Webshop-Integration
  - Bestellverwaltung
  - Kommunikationsprotokoll
- **Workflow:** Siehe WORKFLOWS.md - Abschnitt 6

#### 8. Kassensystem (TSE-konform)
- **Controller:** `rechnungsmodul/kasse_controller.py`
- **Models:** `KassenBeleg`, `BelegPosition`, `KassenTransaktion`, `TSEKonfiguration`
- **Funktionen:**
  - TSE-konforme Kassenbelege
  - Zahlungserfassung (Bar, EC, Kreditkarte, etc.)
  - Tagesabschlüsse (Z-Berichte)
  - Storno-Funktionen
- **Workflow:** Siehe WORKFLOWS.md - Abschnitt 7

#### 9. Rechnungssystem (ZUGPFERD-konform)
- **Controller:** `rechnungsmodul/rechnung_controller.py`
- **Models:** `Rechnung`, `RechnungsPosition`, `RechnungsZahlung`, `ZugpferdKonfiguration`
- **Services:** `zugpferd_service.py`
- **Funktionen:**
  - Rechnungserstellung
  - ZUGFeRD-XML-Export
  - Zahlungsverfolgung
  - Mahnwesen
- **Workflow:** Siehe WORKFLOWS.md - Abschnitt 8

#### 10. Versandverwaltung
- **Controller:** `shipping_controller_db.py`
- **Models:** `Shipment`, `ShipmentItem`
- **Funktionen:**
  - Versandvorbereitung
  - Tracking-Nummer-Verwaltung
  - Packlisten
  - Versandetiketten
- **Workflow:** Siehe WORKFLOWS.md - Abschnitt 9

---

## 📊 Datenbank-Übersicht

### Haupt-Tabellen (17)

1. **users** - Benutzerverwaltung
2. **customers** - Kundenverwaltung
3. **articles** - Artikelverwaltung
4. **article_variants** - Artikel-Varianten
5. **orders** - Auftragsverwaltung
6. **order_items** - Auftragspositionen
7. **order_status_history** - Status-Historie
8. **machines** - Maschinenverzeichnis
9. **production_schedules** - Produktionsplanung
10. **threads** - Garnverwaltung
11. **thread_stock** - Garnbestand
12. **thread_usage** - Garnverbrauch
13. **suppliers** - Lieferantenverwaltung
14. **supplier_orders** - Lieferantenbestellungen
15. **shipments** - Versandverwaltung
16. **shipment_items** - Versandpositionen
17. **activity_logs** - Aktivitätsprotokoll

### Rechnungsmodul-Tabellen (10)

1. **kassen_belege** - Kassenbuchungen
2. **beleg_positionen** - Belegpositionen
3. **kassen_transaktionen** - TSE-Transaktionen
4. **mwst_saetze** - Mehrwertsteuersätze
5. **tse_konfigurationen** - TSE-Konfiguration
6. **rechnungen** - Rechnungen
7. **rechnungs_positionen** - Rechnungspositionen
8. **rechnungs_zahlungen** - Zahlungen
9. **tagesabschluesse** - Tagesabschlüsse
10. **zugpferd_konfigurationen** - ZUGPFERD-Einstellungen

### Hilfs-Tabellen (6)

1. **product_categories** - Produktkategorien
2. **brands** - Marken/Hersteller
3. **article_supplier** - Artikel-Lieferanten-Zuordnung
4. **supplier_contact** - Lieferanten-Ansprechpartner
5. **price_calculation_settings** - Preiskalkulationseinstellungen
6. **settings** (TaxRate, PriceCalculationRule) - Erweiterte Einstellungen

**Gesamt: 33 Tabellen**

---

## 🔧 Technologie-Stack

### Backend
- **Flask 3.0.3** - Web Framework
- **SQLAlchemy 2.0.36** - ORM
- **SQLite / PostgreSQL** - Datenbank
- **Flask-Login** - Authentifizierung
- **Flask-WTF** - Formulare
- **Jinja2** - Templating

### Spezial-Libraries
- **pyembroidery 1.5.1** - DST-Datei-Analyse
- **Pillow ≥10.4.0** - Bildverarbeitung & Thumbnails
- **openpyxl 3.1.2** - L-Shop Excel-Import
- **pandas ≥2.2.0** - Datenverarbeitung
- **PyPDF2 / pdfplumber** - PDF-Analyse

### Frontend
- **HTML5 / CSS3** - UI
- **JavaScript (Vanilla)** - Interaktivität
- **Bootstrap-kompatibel** - Styling

---

## 🎯 Entwicklungsstatus

**Gesamtfortschritt: ~40% fertig**

### ✅ Fertiggestellt
- Datenbankstruktur (100%)
- Kundenverwaltung (100%)
- Artikelverwaltung mit L-Shop Import (100%)
- Auftragsverwaltung Kern (90%)
- Design-Workflow (85%)
- Garnverwaltung (90%)
- Lieferantenverwaltung (85%)
- Kassensystem Struktur (80%)
- Rechnungssystem Struktur (75%)

### 🚧 In Arbeit
- Produktionsplanung (60%)
- Versandverwaltung (70%)
- TSE-Integration (50%)
- ZUGPFERD-Export (40%)
- Dashboard & Statistiken (50%)

### ⏳ Geplant (Meilenstein 1-2)
- Testing-Framework
- API-Dokumentation
- Mobile-Optimierung
- E-Mail-Benachrichtigungen
- Erweiterte Statistiken

---

## 📝 Wichtige Dateien

### Konfiguration
- `app.py` - Flask Application Factory
- `.env` - Umgebungsvariablen
- `requirements.txt` - Python-Abhängigkeiten

### Datenbank
- `src/models/models.py` - Haupt-Models (17 Tabellen)
- `src/models/rechnungsmodul/models.py` - Rechnungs-Models (10 Tabellen)
- `src/models/article_variant.py` - Artikel-Varianten
- `src/models/settings.py` - Einstellungen

### Controller (38 Module)
- `src/controllers/customer_controller_db.py`
- `src/controllers/article_controller_db.py`
- `src/controllers/order_controller_db.py`
- `src/controllers/design_workflow_controller.py`
- `src/controllers/production_controller_db.py`
- `src/controllers/machine_controller_db.py`
- `src/controllers/thread_controller_db.py`
- `src/controllers/supplier_controller_db.py`
- `src/controllers/shipping_controller_db.py`
- `src/controllers/rechnungsmodul/kasse_controller.py`
- `src/controllers/rechnungsmodul/rechnung_controller.py`
- ... (weitere 27 Controller)

### Services (6 Module)
- `src/services/lshop_import_service.py` - L-Shop Excel-Import
- `src/services/pdf_service.py` - PDF-Verarbeitung
- `src/services/zugpferd_service.py` - ZUGPFERD-Export
- `src/services/webshop_automation_service.py` - Webshop-Integration
- `src/services/thread_web_search_service.py` - Garn-Suche
- ... (weitere Services)

### Utils (14 Module)
- `src/utils/dst_analyzer.py` - DST-Datei-Analyse
- `src/utils/design_upload.py` - Design-Upload
- `src/utils/pdf_analyzer.py` - PDF-Analyse
- `src/utils/activity_logger.py` - Aktivitäts-Logging
- `src/utils/logger.py` - Allgemeines Logging
- ... (weitere Utils)

---

## 🚀 Schnellstart

### Installation
```bash
# Repository klonen
git clone https://github.com/Schexter/StitchAdmin.git
cd StitchAdmin2.0

# Virtual Environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# Abhängigkeiten installieren
pip install -r requirements.txt

# Anwendung starten
python app.py
```

### Zugriff
```
http://localhost:5000
```

**Standard-Login:**
- Benutzername: `admin`
- Passwort: `admin`

⚠️ **WICHTIG:** Passwort nach erstem Login ändern!

---

## 📞 Support & Kontakt

### Entwickler
**Hans Hahn**

### Repository
**GitHub:** https://github.com/Schexter/StitchAdmin.git

### Lizenz
**Alle Rechte vorbehalten - Hans Hahn**

---

## 📖 Weitere Dokumentation

### Projektmanagement
- `TODO.md` - Aufgaben und Meilensteine
- `CHANGELOG.md` - Versions-Historie
- `error.log` - Fehlerprotokoll

### Spezifische Guides
- `docs/MIGRATION_GUIDE.md` - Migrations-Anleitung
- `docs/PROJEKT_STRUKTUR.md` - Detaillierte Struktur-Doku
- `docs/QUICKSTART.md` - Schnellstart-Guide

---

## 🔄 Aktualisierungen

Diese Dokumentation wird kontinuierlich aktualisiert. Letzte Aktualisierung: **10. November 2025**

---

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**
