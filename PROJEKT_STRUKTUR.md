# StitchAdmin 2.0 - Projekt-Struktur und Komponenten-Übersicht

**Erstellt von:** Hans Hahn - Alle Rechte vorbehalten
**Version:** 2.0.0
**Stand:** 05.11.2025
**Python-Version:** 3.11+ (getestet mit 3.11, 3.12, 3.13)

---

## 📊 Projekt-Statistiken

- **71 Python-Dateien** im src-Verzeichnis
- **38 Controller-Module** (inkl. Rechnungsmodul)
- **126 HTML-Templates**
- **14 Utility-Module**
- **Datenbank:** SQLite mit SQLAlchemy 2.0.36+
- **Framework:** Flask 3.0.3

---

## 📁 Verzeichnisstruktur

```
StitchAdmin2.0/
├── app.py                          # Haupt-Flask-Application (Factory Pattern)
├── requirements.txt                # Python-Abhängigkeiten
├── start.bat                       # Windows-Startskript
├── fix_sqlalchemy.bat             # SQLAlchemy-Reparatur-Skript
│
├── instance/                       # Flask Instance-Ordner
│   ├── stitchadmin.db             # SQLite-Datenbank
│   └── uploads/                   # Hochgeladene Dateien
│
├── src/                           # Quellcode-Hauptverzeichnis
│   ├── controllers/               # Flask Blueprints (MVC-Controller)
│   ├── models/                    # SQLAlchemy Datenbank-Models
│   ├── services/                  # Business-Logic-Services
│   ├── templates/                 # Jinja2 HTML-Templates
│   ├── static/                    # CSS, JavaScript, Bilder
│   └── utils/                     # Hilfsfunktionen und Tools
│
├── scripts/                       # Migrations- und Setup-Skripte
├── docs/                          # Dokumentation
├── logs/                          # Anwendungs-Logs
├── backups/                       # Datenbank-Backups
└── tests/                         # Unit- und Integration-Tests
```

---

## 🎮 Controllers (Flask Blueprints)

### Kern-Controller (Datenbank-basiert)

| Controller | Datei | Blueprint-Name | Beschreibung |
|-----------|-------|----------------|--------------|
| **Kunden** | `customer_controller_db.py` | `customer_bp` | Kundenverwaltung (Privat/Geschäftskunden) |
| **Artikel** | `article_controller_db.py` | `article_bp` | Artikelverwaltung, L-Shop Import, Preiskalkulation |
| **Aufträge** | `order_controller_db.py` | `order_bp` | Auftragsverwaltung (Stickerei/Druck/DTF) |
| **Maschinen** | `machine_controller_db.py` | `machine_bp` | Maschinen- und Equipment-Verwaltung |
| **Garne** | `thread_controller_db.py` | `thread_bp` | Garnverwaltung, Lagerbestand, Farben |
| **Produktion** | `production_controller_db.py` | `production_bp` | Produktionsplanung und -steuerung |
| **Versand** | `shipping_controller_db.py` | `shipping_bp` | Versandverwaltung, Tracking, Lieferscheine |
| **Lieferanten** | `supplier_controller_db.py` | `supplier_bp` | Lieferantenverwaltung, Bestellungen |
| **Einstellungen** | `settings_controller_unified.py` | `settings_bp` | System-Einstellungen, Konfiguration |
| **Aktivitäten** | `activity_controller_db.py` | `activity_bp` | Aktivitätsprotokoll, Änderungshistorie |

### Spezial-Controller

| Controller | Datei | Blueprint-Name | Beschreibung |
|-----------|-------|----------------|--------------|
| **Design-Workflow** | `design_workflow_controller.py` | `design_workflow_bp` | Design-Upload, DST-Analyse, Stichzahl |
| **Datei-Browser** | `file_browser_controller.py` | `file_browser_bp` | Dateiverwaltung, Upload, Thumbnails |
| **API** | `api_controller.py` | `api_bp` | REST-API für externe Integrationen |
| **Authentifizierung** | `auth_controller.py` | `auth_bp` | Login, Logout, Session-Management |
| **Dashboard** | `dashboard_controller.py` | - | Übersichts-Dashboard (in app.py integriert) |
| **Backup** | `backup_controller.py` | `backup_bp` | Datenbank-Backup und -Wiederherstellung |
| **Sicherheit** | `security_controller.py` | `security_bp` | Sicherheitseinstellungen, Zugriffskontrolle |

### Rechnungsmodul (TSE-konform)

| Controller | Datei | Blueprint-Name | Beschreibung |
|-----------|-------|----------------|--------------|
| **Kasse** | `rechnungsmodul/kasse_controller.py` | `kasse_bp` | TSE-konforme Kassenfunktionen, Belege |
| **Rechnungen** | `rechnungsmodul/rechnung_controller.py` | `rechnung_bp` | Rechnungserstellung, ZUGFeRD-Export |

### ~~Legacy-Controller (JSON-basiert)~~ ✅ ENTFERNT

**Status:** ✅ Alle Legacy JSON-Controller wurden am 12.11.2025 entfernt (5.593 Zeilen Code gelöscht)

Die folgenden Controller wurden bereinigt:
- ~~`customer_controller.py`~~ → Ersetzt durch `customer_controller_db.py`
- ~~`article_controller.py`~~ → Ersetzt durch `article_controller_db.py`
- ~~`order_controller.py`~~ → Ersetzt durch `order_controller_db.py`
- ~~`machine_controller.py`~~ → Ersetzt durch `machine_controller_db.py`
- ~~`thread_controller.py`~~ → Ersetzt durch `thread_controller_db.py`
- ~~`production_controller.py`~~ → Ersetzt durch `production_controller_db.py`
- ~~`shipping_controller.py`~~ → Ersetzt durch `shipping_controller_db.py`
- ~~`supplier_controller.py`~~ → Ersetzt durch `supplier_controller_db.py`
- ~~`settings_controller.py`~~ → Ersetzt durch `settings_controller_unified.py`
- ~~`settings_controller_db.py`~~ → Konsolidiert in `settings_controller_unified.py`
- ~~`thread_online_controller.py`~~ → Entfernt (nicht verwendet)
- ~~`thread_online_controller_db.py`~~ → Entfernt (nicht verwendet)

### Zusätzliche Controller

- `thread_web_search_routes.py` - Web-Suche für Garne
- `supplier_controller_db_extension.py` - Erweiterte Lieferanten-Funktionen
- `settings_advanced_controller.py` - Erweiterte Einstellungen

---

## 🗄️ Datenbank-Models

### Kern-Models (`src/models/models.py`)

| Model | Tabelle | Beschreibung |
|-------|---------|--------------|
| `User` | `users` | Benutzer mit Flask-Login Integration |
| `Customer` | `customers` | Kunden (Privat/Geschäft) |
| `Article` | `articles` | Artikel mit L-Shop Integration |
| `Order` | `orders` | Aufträge (Stickerei/Druck/DTF) |
| `OrderItem` | `order_items` | Auftragspositionen mit Lieferanten-Status |
| `OrderStatusHistory` | `order_status_history` | Status-Änderungsprotokoll |
| `Machine` | `machines` | Maschinen und Equipment |
| `ProductionSchedule` | `production_schedules` | Produktionsplanung |
| `Thread` | `threads` | Garne und Farben |
| `ThreadStock` | `thread_stock` | Garnbestand |
| `ThreadUsage` | `thread_usage` | Garnverbrauch |
| `Shipment` | `shipments` | Versendungen |
| `ShipmentItem` | `shipment_items` | Versandpositionen |
| `Supplier` | `suppliers` | Lieferanten mit Webshop-Integration |
| `SupplierOrder` | `supplier_orders` | Lieferanten-Bestellungen |
| `ActivityLog` | `activity_logs` | Aktivitätsprotokoll |
| `ProductCategory` | `product_categories` | Produktkategorien (hierarchisch) |
| `Brand` | `brands` | Marken/Hersteller |
| `PriceCalculationSettings` | `price_calculation_settings` | Preiskalkulations-Einstellungen |

### Erweiterte Models

#### Artikel-Varianten (`src/models/article_variant.py`)
- `ArticleVariant` - Artikel-Varianten (Farbe/Größe) für L-Shop

#### Artikel-Lieferanten (`src/models/article_supplier.py`)
- `ArticleSupplier` - Verknüpfung Artikel ↔ Lieferant mit Preisen
- `ArticleSupplierPriceHistory` - Preisverlaufs-Historie

#### Einstellungen (`src/models/settings.py`)
- `TaxRate` - Mehrwertsteuersätze
- `PriceCalculationRule` - Erweiterte Kalkulationsregeln
- `ImportSettings` - L-Shop Import-Einstellungen

#### Lieferanten-Kontakte (`src/models/supplier_contact.py`)
- `SupplierContact` - Ansprechpartner bei Lieferanten
- `SupplierCommunicationLog` - Kommunikationsprotokoll

#### Rechnungsmodul (`src/models/rechnungsmodul.py`)
- `MwStSatz` - Mehrwertsteuersätze für Rechnungen
- `Rechnung` - Rechnungen mit ZUGFeRD-Support
- `RechnungsPosition` - Rechnungspositionen
- `RechnungsZahlung` - Zahlungen zu Rechnungen
- `TSEKonfiguration` - TSE-Konfiguration (Technische Sicherheitseinrichtung)
- `KassenBeleg` - TSE-konforme Kassenbelege
- `BelegPosition` - Positionen auf Kassenbelegen
- `KassenTransaktion` - Zahlungstransaktionen
- `Tagesabschluss` - Z-Berichte für Kassensystem

---

## 🛠️ Utilities (`src/utils/`)

| Modul | Datei | Beschreibung |
|-------|-------|--------------|
| **Aktivitätsprotokoll** | `activity_logger.py` | Logging aller Benutzeraktionen |
| **Kundenhistorie** | `customer_history.py` | Änderungshistorie für Kunden |
| **Design-Verwaltung** | `design_link_manager.py` | Design-Datei-Verknüpfungen |
| **Design-Upload** | `design_upload.py` | Sichere Datei-Uploads mit Validierung |
| **DST-Analyse** | `dst_analyzer.py` | DST-Stickdatei-Analyse (Stichzahl, Größe) |
| **E-Mail-Service** | `email_service.py` | E-Mail-Versand (SMTP) |
| **Datei-Analyse** | `file_analysis.py` | Dateiformat-Erkennung und Validierung |
| **Template-Filter** | `filters.py` | Custom Jinja2-Filter (Datum, Währung, etc.) |
| **Formular-Helfer** | `form_helpers.py` | WTForms-Hilfsfunktionen |
| **Logger** | `logger.py` | Zentrales Logging-System |
| **PDF-Analyse** | `pdf_analyzer.py` | PDF-Parsing für Rechnungen/Lieferscheine |
| **PDF-Analyse Lite** | `pdf_analyzer_lite.py` | Leichtgewichtige PDF-Verarbeitung |
| **Sicherheit** | `security.py` | Sicherheitsfunktionen, Input-Validierung |

---

## 🎨 Templates (`src/templates/`)

### Basis-Templates

- `base.html` - Haupt-Layout mit Navigation
- `base_clean.html` - Minimalistisches Layout
- `base_simple.html` - Vereinfachtes Layout
- `base_switch.html` - Layout-Umschalter
- `login.html` - Login-Seite
- `dashboard.html` - Dashboard mit Statistiken
- `index.html` - Startseite

### Template-Bereiche

| Bereich | Ordner | Anzahl | Beschreibung |
|---------|--------|--------|--------------|
| **Aktivitäten** | `activities/` | 3 | Aktivitätsprotokolle |
| **Artikel** | `articles/` | 15+ | Artikelverwaltung, L-Shop Import |
| **Kunden** | `customers/` | 6 | Kundenverwaltung |
| **Design-Workflow** | `design_workflow/` | 4 | Design-Upload und -Verwaltung |
| **Fehlerseiten** | `errors/` | 3 | 403, 404, 500 |
| **Datei-Browser** | `file_browser/` | 2 | Dateimanagement |
| **Includes** | `includes/` | 10+ | Wiederverwendbare Komponenten |
| **Kasse** | `kasse/` | 8 | Kassensystem (TSE-konform) |
| **Maschinen** | `machines/` | 6 | Maschinenverwaltung |
| **Aufträge** | `orders/` | 12+ | Auftragsverwaltung |
| **Produktion** | `production/` | 8 | Produktionsplanung |
| **Rechnungen** | `rechnung/`, `rechnungen/` | 10+ | Rechnungserstellung |
| **Sicherheit** | `security/` | 2 | Sicherheitseinstellungen |
| **Einstellungen** | `settings/` | 15+ | System-Einstellungen |
| **Versand** | `shipping/` | 6 | Versandverwaltung |
| **Lieferanten** | `suppliers/` | 8+ | Lieferantenverwaltung |
| **Garne** | `thread/`, `threads/` | 10+ | Garnverwaltung |
| **Benutzer** | `users/` | 3 | Benutzerverwaltung |

### Includes (Wiederverwendbare Komponenten)

- `_navbar.html` - Hauptnavigation
- `_sidebar.html` - Seitenleiste
- `_flash_messages.html` - Flash-Nachrichten
- `_pagination.html` - Paginierung
- `_form_macros.html` - Formular-Makros
- `_table_actions.html` - Tabellen-Aktions-Buttons
- `_delete_modal.html` - Lösch-Bestätigungs-Modal
- `_search_bar.html` - Suchleiste
- `_filters.html` - Filter-Komponenten
- `_breadcrumbs.html` - Breadcrumb-Navigation

---

## 🎨 Static-Dateien (`src/static/`)

### CSS (`static/css/`)
- `style.css` - Haupt-Stylesheet
- `dashboard.css` - Dashboard-spezifisch
- `forms.css` - Formular-Styling
- `tables.css` - Tabellen-Styling
- `print.css` - Druckansicht

### JavaScript (`static/js/`)
- `main.js` - Haupt-JavaScript
- `api.js` - API-Client
- `forms.js` - Formular-Validierung
- `tables.js` - Dynamische Tabellen
- `search.js` - Such-Funktionen
- `notifications.js` - Toast-Benachrichtigungen

### Bilder (`static/images/`)
- Logo, Icons, Platzhalter-Bilder

### Thumbnails (`static/thumbnails/`)
- `designs/` - Design-Vorschaubilder

---

## 🔧 Hauptfunktionen nach Modul

### Kundenverwaltung
- ✅ Privat- und Geschäftskunden
- ✅ Vollständige Adress- und Kontaktdaten
- ✅ Kundenhistorie und Notizen
- ✅ Newsletter-Verwaltung
- ✅ DSGVO-konforme Datenhaltung

### Artikelverwaltung
- ✅ L-Shop Excel-Import
- ✅ Artikel-Varianten (Farbe/Größe)
- ✅ Mehrstufige Preiskalkulation (EK → VK)
- ✅ Lagerbestandsverwaltung
- ✅ Kategorien und Marken
- ✅ Lieferanten-Zuordnung mit Preishistorie

### Auftragsverwaltung
- ✅ Stickerei-Aufträge (Stichzahl, Position, Garne)
- ✅ Druck-Aufträge (DTG, DTF, Siebdruck)
- ✅ Kombinierte Aufträge
- ✅ Design-Workflow (Upload, Bestellung, Freigabe)
- ✅ Status-Tracking mit Historie
- ✅ Liefertermin-Verwaltung
- ✅ Textile-Bestellstatus pro Position

### Produktionsverwaltung
- ✅ Maschinen-Planung
- ✅ Kapazitätsplanung
- ✅ Produktionszeiten-Kalkulation
- ✅ Maschinenstatus-Überwachung
- ✅ Garnverbrauch-Tracking

### Lieferantenverwaltung
- ✅ Lieferanten-Stammdaten
- ✅ Ansprechpartner-Verwaltung
- ✅ Bestellungen mit Status-Tracking
- ✅ Webshop-Integration (URL-Patterns)
- ✅ Kommunikationsprotokoll
- ✅ Retouren-Adressen

### Rechnungsmodul (GoBD/TSE-konform)
- ✅ TSE-konforme Kassenbelege
- ✅ Rechnungserstellung mit Positionen
- ✅ ZUGFeRD-XML-Export
- ✅ Zahlungsverfolgung
- ✅ Tagesabschlüsse (Z-Berichte)
- ✅ Mehrwertsteuersätze
- ✅ Storno-Funktionen

### Design-Workflow
- ✅ Sichere Datei-Uploads (DST, EMB, etc.)
- ✅ Automatische DST-Analyse (Stichzahl, Größe)
- ✅ Thumbnail-Generierung
- ✅ Design-Status-Tracking
- ✅ Lieferanten-Bestellung von Designs

### Einstellungen
- ✅ Preiskalkulations-Regeln
- ✅ Mehrwertsteuersätze
- ✅ Import-Konfigurationen
- ✅ E-Mail-Konfiguration
- ✅ Backup-Einstellungen
- ✅ Benutzer- und Rechteverwaltung

---

## 🚀 Start und Installation

### Voraussetzungen
```bash
Python 3.11+ (empfohlen: 3.11, 3.12, 3.13)
pip (Python Package Manager)
```

### Installation

1. **Virtual Environment erstellen:**
```bash
python -m venv .venv
```

2. **Virtual Environment aktivieren:**
```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

3. **Abhängigkeiten installieren:**
```bash
pip install -r requirements.txt
```

4. **Anwendung starten:**
```bash
# Direkt mit Python
python app.py

# Oder mit Windows-Batch
start.bat
```

5. **Browser öffnen:**
```
http://localhost:5000
```

6. **Standard-Login:**
```
Benutzername: admin
Passwort: admin
```

### Erste Schritte nach Installation

1. **Admin-Passwort ändern** (Einstellungen → Benutzer)
2. **Einstellungen konfigurieren:**
   - Preiskalkulations-Faktoren
   - Mehrwertsteuersätze
   - E-Mail-Konfiguration
3. **Stammdaten anlegen:**
   - Lieferanten
   - Kategorien
   - Marken
   - Maschinen
4. **Artikel importieren** (L-Shop Excel-Import)

---

## 🔗 Wichtige Routen

### Hauptbereiche
- `/` - Dashboard
- `/customers` - Kunden
- `/articles` - Artikel
- `/orders` - Aufträge
- `/production` - Produktion
- `/machines` - Maschinen
- `/threads` - Garne
- `/suppliers` - Lieferanten
- `/shipping` - Versand
- `/settings` - Einstellungen

### Rechnungsmodul
- `/kasse` - Kassensystem
- `/rechnung` - Rechnungen
- `/rechnung/tagesabschluss` - Z-Bericht

### Spezialfunktionen
- `/design-workflow` - Design-Upload und -Verwaltung
- `/file-browser` - Dateiverwaltung
- `/api` - REST-API
- `/activities` - Aktivitätsprotokoll

---

## 📦 Abhängigkeiten (requirements.txt)

### Web-Framework
- Flask 3.0.3
- Flask-Login 0.6.3
- Flask-SQLAlchemy 3.1.1
- Flask-WTF 1.2.1
- Werkzeug 3.0.3

### Datenbank
- SQLAlchemy ≥ 2.0.36 (Python 3.13 kompatibel)

### Formulare & Validierung
- WTForms 3.1.2
- email-validator 2.1.1

### Bildverarbeitung
- Pillow ≥ 10.4.0

### Excel & Dokumente
- openpyxl 3.1.2
- pandas ≥ 2.2.0
- xlrd 2.0.1

### PDF-Verarbeitung
- PyPDF2 3.0.1
- pdfplumber 0.10.3

### Stickerei-spezifisch
- pyembroidery 1.5.1

### Sonstiges
- python-dotenv 1.0.1
- python-dateutil ≥ 2.8.2
- gunicorn 22.0.0 (Produktions-Server)

---

## 🔒 Sicherheit

### Implementierte Sicherheitsfeatures
- ✅ Flask-Login Session-Management
- ✅ Password-Hashing (Werkzeug)
- ✅ CSRF-Schutz (Flask-WTF)
- ✅ Input-Validierung (WTForms)
- ✅ SQL-Injection-Schutz (SQLAlchemy ORM)
- ✅ Sichere Datei-Uploads mit Whitelist
- ✅ Aktivitätsprotokoll für Audit-Trail

### Best Practices
- Verwenden Sie starke Passwörter
- Ändern Sie Standard-Credentials sofort
- Aktivieren Sie HTTPS in Produktion
- Führen Sie regelmäßige Backups durch
- Halten Sie Dependencies aktuell

---

## 📝 Entwickler-Notizen

### Architektur-Muster
- **MVC-Pattern** mit Flask Blueprints
- **Application Factory Pattern** für Flask
- **Repository Pattern** für Datenbank-Zugriffe
- **Service Layer** für Business-Logik

### Code-Konventionen
- **PEP 8** Python Style Guide
- **Type Hints** wo sinnvoll
- **Docstrings** für alle Module und Funktionen
- **Deutsche Kommentare** für Geschäftslogik

### Datenbank-Migrations
- Models werden bei Start automatisch erstellt (`db.create_all()`)
- Für Produktivumgebung empfohlen: Flask-Migrate/Alembic

### Testing
- Unit-Tests im `tests/`-Verzeichnis
- Integration-Tests für Controller
- Datenbank-Tests mit in-memory SQLite

---

## 🐛 Bekannte Probleme und Lösungen

### SQLAlchemy 2.0 Kompatibilität
**Problem:** Python 3.13 erfordert SQLAlchemy ≥ 2.0.36
**Lösung:** `fix_sqlalchemy.bat` ausführen oder manuell aktualisieren

### L-Shop Import
**Problem:** Excel-Dateien mit Umlauten
**Lösung:** Encoding UTF-8 verwenden, openpyxl-Engine

### TSE-Konfiguration
**Problem:** TSE-Hardware nicht verfügbar
**Lösung:** Mock-Modus für Entwicklung aktivieren

---

## 📞 Support und Kontakt

**Entwickler:** Hans Hahn
**Projekt:** StitchAdmin 2.0 - ERP für Stickerei-Betriebe
**Lizenz:** Alle Rechte vorbehalten
**Stand:** November 2025

---

## 🎯 Roadmap / Zukünftige Features

- [ ] REST-API-Erweiterung (vollständig)
- [ ] Mobile-App (iOS/Android)
- [ ] Cloud-Synchronisation
- [ ] Multi-Mandanten-Fähigkeit
- [ ] Erweiterte Statistiken und Dashboards
- [ ] Automatische Backups in Cloud
- [ ] E-Mail-Benachrichtigungen
- [ ] Barcode-Scanner-Integration
- [ ] Tablet-optimierte Produktions-UI
- [ ] SumUp/Stripe-Zahlungsintegration

---

**📌 Diese Dokumentation wurde automatisch generiert am 05.11.2025**
