# StitchAdmin 2.0 - IST-SOLL-Analyse & Gap-Analyse

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Analyse-Datum:** 10. November 2025  
**Projekt-Status:** Alpha (~40% fertig)

---

## 📋 Inhaltsverzeichnis

1. [Executive Summary](#executive-summary)
2. [IST-Zustand (Aktuell)](#ist-zustand-aktuell)
3. [SOLL-Zustand (Ziel)](#soll-zustand-ziel)
4. [Gap-Analyse](#gap-analyse)
5. [Priorisierte Maßnahmen](#priorisierte-maßnahmen)
6. [Detaillierte Module-Analyse](#detaillierte-module-analyse)

---

## 🎯 Executive Summary

### Projekt-Status

| Bereich | IST | SOLL | Gap | Priorität |
|---------|-----|------|-----|-----------|
| **Core Features** | 60% | 100% | 40% | 🔴 HOCH |
| **Datenbank-Models** | 90% | 100% | 10% | 🟡 MITTEL |
| **Controller (DB)** | 70% | 100% | 30% | 🔴 HOCH |
| **Controller (Legacy)** | 100% | 0% | -100% | 🔴 CLEANUP |
| **Templates** | 65% | 100% | 35% | 🟡 MITTEL |
| **Workflows** | 30% | 100% | 70% | 🟢 NIEDRIG |
| **Testing** | 5% | 60% | 55% | 🔴 HOCH |
| **Dokumentation** | 50% | 100% | 50% | 🟡 MITTEL |
| **API** | 10% | 80% | 70% | 🟢 NIEDRIG |

**Gesamtstatus:** ~40% vollständig

---

## 📊 IST-Zustand (Aktuell)

### ✅ Was funktioniert gut

#### 1. Datenbank-Schema (90% fertig)
- ✅ **20+ Tabellen implementiert**
- ✅ Relationships korrekt definiert
- ✅ SQLAlchemy 2.0.36 (aktuell)
- ✅ Migrations-System funktioniert
- ✅ Erweiterte Models:
  - `ArticleVariant` - Größe/Farbe-Varianten
  - `ArticleSupplier` - Lieferanten-Zuordnung mit Preishistorie
  - `SupplierContact` - Ansprechpartner
  - `SupplierCommunicationLog` - Kommunikationsprotokoll
  - `TaxRate`, `PriceCalculationRule` - Erweiterte Preiskalkulation
  - `ImportSettings` - L-Shop Import-Konfiguration

**Fehlende Tabellen:**
- ⚠️ `ProductionSchedule` - Existiert im Model, aber nicht voll genutzt
- ⚠️ `ThreadUsage` - Garnverbrauch-Tracking fehlt teilweise

---

#### 2. Kundenverwaltung (85% fertig)
✅ **Vollständig implementiert:**
- Customer-Model (Privat/Geschäft)
- CRUD-Operationen (Create, Read, Update, Delete)
- Suche & Filter
- Aktivitäts-Historie
- Newsletter-Verwaltung

⚠️ **Verbesserungspotential:**
- Kunden-Statistiken (Umsatz, Aufträge)
- Export-Funktionen (CSV, Excel)
- Duplikat-Erkennung

---

#### 3. Artikelverwaltung (75% fertig)
✅ **Gut implementiert:**
- Article-Model mit erweiterten Feldern
- L-Shop Excel-Import (vollständig)
- Varianten-Verwaltung (Farbe/Größe)
- Preiskalkulation (alt + neu)
- Lagerbestandsverwaltung
- Lieferanten-Zuordnung

⚠️ **Gaps:**
- Varianten-UI noch nicht vollständig
- Barcode-Druck (implementiert, aber nicht getestet)
- Produktdatenblatt (Template vorhanden, aber nicht fertig)
- Massen-Bearbeitung fehlt
- Artikel-Import-Historie fehlt

---

#### 4. Auftragsverwaltung (70% fertig)
✅ **Kernfunktionen:**
- Order-Model (Stickerei/Druck/Kombiniert)
- CRUD-Operationen
- Status-Tracking (7 Status)
- Design-Workflow (90% fertig)
- OrderItem-Verwaltung
- Textile-Bestellung

⚠️ **Wichtige Gaps:**
- Produktionsplanung nicht vollständig integriert
- Qualitätsprüfungs-Workflow fehlt
- Automatische Benachrichtigungen fehlen
- Liefertermin-Tracking inkomplett

---

#### 5. Design-Workflow (90% fertig)
✅ **Sehr gut implementiert:**
- DST-Datei-Upload
- Automatische DST-Analyse (pyembroidery)
- Thumbnail-Generierung
- Design-Status-Tracking
- Lieferanten-Bestellung
- Sichere Uploads

⚠️ **Minor Gaps:**
- Batch-Upload fehlt
- Design-Archiv-Suche inkomplett
- Automatische Garn-Zuordnung teilweise manuell

---

#### 6. Garnverwaltung (65% fertig)
✅ **Basis vorhanden:**
- Thread-Model
- ThreadStock-Model
- CRUD-Operationen
- Farbverwaltung (Hex, RGB, Pantone)

⚠️ **Major Gaps:**
- PDF-Import (Garnkarten) nicht implementiert
- Garnverbrauch-Tracking fehlt (`ThreadUsage`)
- Nachbestellvorschläge nicht automatisiert
- Garnsuche nach Farbe inkomplett

---

#### 7. Lieferantenverwaltung (70% fertig)
✅ **Gut implementiert:**
- Supplier-Model
- SupplierOrder-Model
- SupplierContact-Model
- Kommunikationsprotokoll
- Webshop-Integration (Links)

⚠️ **Gaps:**
- Automatische Webshop-Bestellung fehlt
- Lieferstatus-Tracking inkomplett
- Retouren-Management fehlt
- Lieferanten-Bewertung fehlt

---

#### 8. Produktionsverwaltung (50% fertig)
✅ **Teilweise vorhanden:**
- Machine-Model
- ProductionSchedule-Model (existiert)
- Maschinenzuordnung

⚠️ **Major Gaps:**
- Produktionskalender-UI fehlt
- Kapazitätsplanung nicht implementiert
- Garnverbrauch-Erfassung fehlt
- Maschinen-Status-Überwachung inkomplett
- Zeiterfassung fehlt

---

#### 9. Rechnungsmodul (60% fertig)
✅ **Basis vorhanden:**
- Kassenbeleg-Model
- Rechnung-Model
- TSE-Vorbereitung
- Z-Berichte (Basis)

⚠️ **Gaps:**
- ZUGFeRD-Export nicht implementiert
- Zahlungsverfolgung inkomplett
- Mahnwesen fehlt
- DATEV-Export fehlt

---

#### 10. Versandverwaltung (40% fertig)
✅ **Minimal vorhanden:**
- Shipment-Model
- ShipmentItem-Model
- Tracking-Nummer-Erfassung

⚠️ **Major Gaps:**
- DHL/DPD/UPS-Integration fehlt
- Versandetiketten-Druck fehlt
- Lieferschein-Generierung inkomplett
- Tracking-Status-Updates fehlen

---

### ❌ Was fehlt komplett

1. **Testing-Framework** (5% vorhanden)
   - Keine Unit-Tests
   - Keine Integration-Tests
   - Keine End-to-End-Tests
   - pytest-Setup fehlt

2. **REST-API** (10% vorhanden)
   - Nur Basis-API-Controller
   - Keine Swagger/OpenAPI-Dokumentation
   - Keine API-Authentication
   - Keine Rate-Limiting

3. **E-Mail-System** (20% vorhanden)
   - email_service.py existiert
   - Aber keine Templates
   - Keine automatischen Benachrichtigungen
   - Keine Newsletter-Funktion

4. **Reporting** (0% vorhanden)
   - Keine Statistiken
   - Keine Dashboards (außer Basic)
   - Keine Exports (PDF/Excel)
   - Keine Diagramme

5. **Barcode-Integration** (0% vorhanden)
   - Keine Scanner-Integration
   - Keine Barcode-Generierung
   - Keine Lagerbestand-Updates per Scan

---

### 🐛 Legacy-Code (Technische Schulden)

**Problem:** Doppelte Controller-Dateien

| Legacy (JSON) | Aktuell (DB) | Status |
|---------------|--------------|--------|
| `customer_controller.py` | `customer_controller_db.py` | ✅ DB-Version vollständig |
| `article_controller.py` | `article_controller_db.py` | ✅ DB-Version vollständig |
| `order_controller.py` | `order_controller_db.py` | ✅ DB-Version vollständig |
| `machine_controller.py` | `machine_controller_db.py` | ✅ DB-Version vollständig |
| `thread_controller.py` | `thread_controller_db.py` | ⚠️ Thread-Online-Controller dupliziert |
| `production_controller.py` | `production_controller_db.py` | ⚠️ Nicht vollständig migriert |
| `shipping_controller.py` | `shipping_controller_db.py` | ✅ DB-Version vollständig |
| `supplier_controller.py` | `supplier_controller_db.py` | ✅ DB-Version vollständig |
| `settings_controller.py` | `settings_controller_unified.py` | ⚠️ 3 Versionen! |

**Aktion erforderlich:**
- 🔴 Legacy-Controller löschen (nach Backup)
- 🔴 Doppelte Thread-Controller konsolidieren
- 🔴 Settings-Controller auf EINE Version reduzieren

---

## 🎯 SOLL-Zustand (Ziel)

### Vision für StitchAdmin 2.0

**Mission:** Vollständiges, produktionsreifes ERP-System für Stickerei- und Textilveredelungsbetriebe mit:
- ✅ 100% funktionsfähige Kernmodule
- ✅ Testing-Coverage > 60%
- ✅ API-First Architecture
- ✅ Mobile-optimierte UI
- ✅ Cloud-Sync-Fähigkeit
- ✅ TSE/GoBD-Compliance

---

### Ziel-Features pro Modul

#### 1. Kundenverwaltung (SOLL: 100%)
- ✅ Alle IST-Features behalten
- ➕ Kunden-Statistiken (Umsatz-Charts)
- ➕ CSV/Excel-Export
- ➕ Duplikat-Erkennung (automatisch)
- ➕ Kunden-Tags/Labels
- ➕ E-Mail-Integration (Historie)

#### 2. Artikelverwaltung (SOLL: 100%)
- ✅ Alle IST-Features behalten
- ➕ Vollständige Varianten-UI
- ➕ Barcode-Scanner-Integration
- ➕ Massen-Bearbeitung (Bulk-Edit)
- ➕ Artikel-Bundles/Sets
- ➕ Preishistorie-Diagramm
- ➕ Automatische Nachbestellung
- ➕ Artikel-Bewertungen

#### 3. Auftragsverwaltung (SOLL: 100%)
- ✅ Alle IST-Features behalten
- ➕ Vollständige Produktionsplanung
- ➕ Qualitätsprüfungs-Workflow
- ➕ Automatische E-Mail-Benachrichtigungen
- ➕ Liefertermin-Tracking (mit Alerts)
- ➕ Auftrags-Templates
- ➕ Wiederkehrende Aufträge
- ➕ Kundenfeedback-System

#### 4. Design-Workflow (SOLL: 100%)
- ✅ Alle IST-Features behalten
- ➕ Batch-Upload (mehrere Dateien)
- ➕ Design-Archiv-Suche (Tags, Datum, Größe)
- ➕ Automatische Garn-Zuordnung (100% KI-gestützt)
- ➕ Design-Vorschau (3D-Rendering)
- ➕ Versionshistorie

#### 5. Garnverwaltung (SOLL: 100%)
- ✅ Alle IST-Features behalten
- ➕ PDF-Import (Madeira, Isacord, etc.)
- ➕ Vollständiges Garnverbrauch-Tracking
- ➕ Automatische Nachbestellvorschläge
- ➕ Garnsuche nach Farbe (Hex-Input)
- ➕ Garnkarten-Verwaltung
- ➕ Lagerplatz-Optimierung

#### 6. Lieferantenverwaltung (SOLL: 100%)
- ✅ Alle IST-Features behalten
- ➕ Automatische Webshop-Bestellung (API)
- ➕ Vollständiges Lieferstatus-Tracking
- ➕ Retouren-Management
- ➕ Lieferanten-Bewertung (1-5 Sterne)
- ➕ Preisvergleich-Tool
- ➕ Automatische Lieferanten-Auswahl

#### 7. Produktionsverwaltung (SOLL: 100%)
- ✅ Erweiterte Basis
- ➕ Produktionskalender-UI (Drag & Drop)
- ➕ Kapazitätsplanung (Algorithmus)
- ➕ Garnverbrauch-Erfassung (automatisch)
- ➕ Maschinen-Status-Dashboard
- ➕ Zeiterfassung pro Auftrag
- ➕ Produktivitäts-Statistiken
- ➕ Wartungsplanung

#### 8. Rechnungsmodul (SOLL: 100%)
- ✅ Alle IST-Features behalten
- ➕ ZUGFeRD-Export (vollständig)
- ➕ Vollständige Zahlungsverfolgung
- ➕ Mahnwesen (3 Mahnstufen)
- ➕ DATEV-Export
- ➕ Rechnungs-Templates
- ➕ Wiederkehrende Rechnungen

#### 9. Versandverwaltung (SOLL: 100%)
- ✅ Erweiterte Basis
- ➕ DHL/DPD/UPS-API-Integration
- ➕ Versandetiketten-Druck
- ➕ Lieferschein-Generierung
- ➕ Automatische Tracking-Updates
- ➕ Versandkosten-Kalkulation
- ➕ Packstationen-Support

#### 10. Reporting & Statistiken (NEU - 0% → 100%)
- ➕ Dashboard mit Widgets
- ➕ Umsatz-Charts (täglich/wöchentlich/monatlich)
- ➕ Produktivitäts-Statistiken
- ➕ Lagerbestand-Warnungen
- ➕ Kunden-Analyse (Top-Kunden)
- ➕ Artikel-Analyse (Top-Artikel)
- ➕ Export-Funktionen (PDF/Excel)

---

## 🔍 Gap-Analyse

### Kritische Gaps (Muss vor Release behoben werden)

| Gap | IST | SOLL | Impact | Aufwand | Priorität |
|-----|-----|------|--------|---------|-----------|
| **Testing-Framework** | 5% | 60% | HOCH | 2 Wochen | 🔴 P1 |
| **Legacy-Code-Cleanup** | 100% | 0% | HOCH | 1 Woche | 🔴 P1 |
| **Produktionsplanung** | 50% | 100% | HOCH | 2 Wochen | 🔴 P1 |
| **Garnverbrauch-Tracking** | 0% | 100% | HOCH | 1 Woche | 🔴 P1 |
| **E-Mail-Benachrichtigungen** | 20% | 100% | MITTEL | 1 Woche | 🟡 P2 |
| **API-Dokumentation** | 10% | 80% | MITTEL | 1 Woche | 🟡 P2 |
| **Reporting/Dashboard** | 10% | 100% | MITTEL | 2 Wochen | 🟡 P2 |
| **Versandintegration** | 40% | 100% | NIEDRIG | 2 Wochen | 🟢 P3 |
| **Mobile-UI** | 30% | 100% | NIEDRIG | 3 Wochen | 🟢 P3 |

---

### Funktionale Gaps

#### Modul: Kundenverwaltung
| Feature | IST | SOLL | Gap | Aufwand |
|---------|-----|------|-----|---------|
| CRUD-Operationen | ✅ 100% | 100% | - | - |
| Suche & Filter | ✅ 90% | 100% | 10% | 2h |
| Kunden-Statistiken | ❌ 0% | 100% | 100% | 1 Tag |
| CSV/Excel-Export | ❌ 0% | 100% | 100% | 4h |
| Duplikat-Erkennung | ❌ 0% | 100% | 100% | 1 Tag |
| E-Mail-Historie | ❌ 0% | 100% | 100% | 1 Tag |

**Gesamt-Gap:** 15%  
**Geschätzter Aufwand:** 4 Tage

---

#### Modul: Artikelverwaltung
| Feature | IST | SOLL | Gap | Aufwand |
|---------|-----|------|-----|---------|
| CRUD-Operationen | ✅ 100% | 100% | - | - |
| L-Shop Import | ✅ 100% | 100% | - | - |
| Varianten-Verwaltung | ⚠️ 70% | 100% | 30% | 2 Tage |
| Preiskalkulation | ✅ 100% | 100% | - | - |
| Barcode-Integration | ❌ 0% | 100% | 100% | 2 Tage |
| Massen-Bearbeitung | ❌ 0% | 100% | 100% | 1 Tag |
| Artikel-Bundles | ❌ 0% | 100% | 100% | 2 Tage |
| Nachbestellung | ⚠️ 30% | 100% | 70% | 1 Tag |

**Gesamt-Gap:** 25%  
**Geschätzter Aufwand:** 9 Tage

---

#### Modul: Auftragsverwaltung
| Feature | IST | SOLL | Gap | Aufwand |
|---------|-----|------|-----|---------|
| CRUD-Operationen | ✅ 100% | 100% | - | - |
| Status-Tracking | ✅ 100% | 100% | - | - |
| Design-Workflow | ✅ 90% | 100% | 10% | 1 Tag |
| Produktionsplanung | ⚠️ 50% | 100% | 50% | 5 Tage |
| Qualitätsprüfung | ❌ 0% | 100% | 100% | 2 Tage |
| E-Mail-Benachrichtigungen | ❌ 0% | 100% | 100% | 2 Tage |
| Auftrags-Templates | ❌ 0% | 100% | 100% | 1 Tag |
| Wiederkehrende Aufträge | ❌ 0% | 100% | 100% | 2 Tage |

**Gesamt-Gap:** 30%  
**Geschätzter Aufwand:** 13 Tage

---

## 📋 Priorisierte Maßnahmen

### Phase 1: Cleanup & Stabilisierung (Woche 1-2)

**Ziel:** Legacy-Code entfernen, Testing aufsetzen

#### Woche 1: Cleanup
- [ ] **Tag 1-2:** Legacy-Controller entfernen
  - customer_controller.py
  - article_controller.py
  - order_controller.py
  - machine_controller.py
  - thread_controller.py (alt)
  - production_controller.py
  - shipping_controller.py
  - supplier_controller.py
  - settings_controller.py + settings_controller_db.py

- [ ] **Tag 3-4:** Doppelte Controller konsolidieren
  - thread_online_controller.py + thread_online_controller_db.py → EINE Version
  - settings_controller_unified.py optimieren
  - webshop_automation_routes.py + webshop_automation_routes_complete.py → EINE Version

- [ ] **Tag 5:** Code-Review & Refactoring
  - Imports bereinigen
  - Ungenutzten Code entfernen
  - Docstrings vervollständigen

#### Woche 2: Testing
- [ ] **Tag 1-2:** pytest-Setup
  - conftest.py erstellen
  - Test-Fixtures definieren
  - Test-Datenbank Setup

- [ ] **Tag 3-5:** Erste Tests schreiben
  - test_models.py (Customer, Article, Order)
  - test_customer_controller.py
  - test_article_controller.py
  - Ziel: 20% Coverage

**Deliverables:**
- ✅ Keine Legacy-Controller mehr
- ✅ pytest funktioniert
- ✅ 20% Test-Coverage
- ✅ Sauberer Code

---

### Phase 2: Kernfunktionen vervollständigen (Woche 3-5)

#### Woche 3: Produktionsverwaltung
- [ ] **Tag 1-2:** Produktionskalender-UI
  - Drag & Drop für Aufträge
  - Maschinenauslastung visualisieren
  - Zeitslots verwalten

- [ ] **Tag 3-4:** Kapazitätsplanung
  - Algorithmus für automatische Zuordnung
  - Priorisierung berücksichtigen
  - Eilaufträge

- [ ] **Tag 5:** Garnverbrauch-Erfassung
  - ThreadUsage-Tracking implementieren
  - Automatische Verbrauchserfassung
  - Lagerbestand-Updates

#### Woche 4: E-Mail-System
- [ ] **Tag 1-2:** E-Mail-Templates
  - Auftragsbestätigung
  - Lieferbenachrichtigung
  - Rechnung
  - Erinnerungen

- [ ] **Tag 3-4:** Automatische Benachrichtigungen
  - Status-Änderungen
  - Liefertermine
  - Lagerbestand-Warnungen

- [ ] **Tag 5:** Newsletter-System
  - Template-Editor
  - Empfänger-Verwaltung
  - Versand-Historie

#### Woche 5: Reporting
- [ ] **Tag 1-2:** Dashboard-Widgets
  - Umsatz-Charts
  - Offene Aufträge
  - Produktivität
  - Lagerbestand-Warnungen

- [ ] **Tag 3-4:** Statistiken
  - Kunden-Analyse
  - Artikel-Analyse
  - Zeitraum-Filter

- [ ] **Tag 5:** Export-Funktionen
  - PDF-Reports
  - Excel-Export
  - CSV-Export

**Deliverables:**
- ✅ Produktionsplanung vollständig
- ✅ E-Mail-Benachrichtigungen funktionieren
- ✅ Dashboard mit Statistiken
- ✅ Export-Funktionen

---

### Phase 3: Erweiterte Features (Woche 6-8)

#### Woche 6: Garnverwaltung
- [ ] PDF-Import (Garnkarten)
- [ ] Garnsuche nach Farbe
- [ ] Lagerplatz-Optimierung
- [ ] Nachbestellvorschläge (automatisch)

#### Woche 7: Lieferantenverwaltung
- [ ] Webshop-API-Integration
- [ ] Lieferstatus-Tracking
- [ ] Retouren-Management
- [ ] Lieferanten-Bewertung

#### Woche 8: Versandintegration
- [ ] DHL/DPD/UPS-API
- [ ] Versandetiketten-Druck
- [ ] Lieferschein-Generierung
- [ ] Tracking-Updates

---

### Phase 4: API & Mobile (Woche 9-11)

#### Woche 9-10: REST-API
- [ ] Flask-RESTX Setup
- [ ] API-Endpoints für alle Module
- [ ] Swagger-Dokumentation
- [ ] API-Authentication (JWT)
- [ ] Rate-Limiting

#### Woche 11: Mobile-UI
- [ ] Responsive Design
- [ ] Touch-Optimierung
- [ ] PWA-Setup
- [ ] Offline-Modus

---

### Phase 5: Testing & Deployment (Woche 12-13)

#### Woche 12: Testing
- [ ] Test-Coverage auf 60% erhöhen
- [ ] Integration-Tests
- [ ] End-to-End-Tests
- [ ] Performance-Tests

#### Woche 13: Deployment
- [ ] Produktions-Setup (Nginx + Gunicorn)
- [ ] Backup-Strategie
- [ ] Monitoring
- [ ] Dokumentation finalisieren

---

## 📈 Detaillierte Module-Analyse

*(Fortsetzung mit detaillierten Workflows pro Modul folgt in separaten Dokumenten)*

Siehe:
- [04_article_management_workflow.md](./workflows/04_article_management_workflow.md) - Artikelverwaltung
- [05_production_planning_workflow.md](./workflows/05_production_planning_workflow.md) - Produktionsplanung
- [06_thread_management_workflow.md](./workflows/06_thread_management_workflow.md) - Garnverwaltung
- [07_supplier_management_workflow.md](./workflows/07_supplier_management_workflow.md) - Lieferantenverwaltung
- [08_reporting_workflow.md](./workflows/08_reporting_workflow.md) - Reporting & Statistiken

---

## 📊 Zeitplan-Übersicht

```
Woche 1-2:   Cleanup & Testing-Setup        [Phase 1]
Woche 3-5:   Kernfunktionen                 [Phase 2]
Woche 6-8:   Erweiterte Features            [Phase 3]
Woche 9-11:  API & Mobile                   [Phase 4]
Woche 12-13: Testing & Deployment           [Phase 5]

Total: ~13 Wochen (3 Monate)
```

**Target Release:** Ende Februar 2026 (Beta)

---

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Letzte Aktualisierung:** 10. November 2025  
**Nächstes Review:** 15. November 2025
