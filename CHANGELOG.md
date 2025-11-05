# StitchAdmin 2.0 - Changelog

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**

Dieses Dokument protokolliert alle wesentlichen Änderungen am StitchAdmin 2.0 Projekt.

Format basierend auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/)  
Versionierung folgt [Semantic Versioning](https://semver.org/lang/de/)

---

## [Unreleased]

### In Arbeit
- Testing-Framework mit Pytest
- Legacy-Controller-Bereinigung
- Flask-Migrate Integration
- API-Dokumentation

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
