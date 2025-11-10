# StitchAdmin 2.0 - Workflow-Diagramme Index

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Stand:** 10. November 2025

---

## 📋 Verfügbare Workflow-Dokumentationen

Dieser Ordner enthält detaillierte Workflow-Diagramme und Prozessbeschreibungen für alle wichtigen Anwendungsbereiche von StitchAdmin 2.0.

---

## ✅ Implementierte Workflows

### 1. Kundenverwaltung
**Datei:** [01_customer_management.md](./01_customer_management.md)

**Prozesse:**
- ✅ Neuen Kunden anlegen (Privat/Geschäft)
- ✅ Kunde bearbeiten
- ✅ Kunde löschen (mit Sicherheitsabfrage)
- ✅ Kunde suchen & filtern

**Diagramme:**
- Flowchart: Kunde anlegen
- Flowchart: Kunde bearbeiten
- Flowchart: Kunde löschen
- Flowchart: Kundensuche
- Datenfluss: Customer-Model

---

### 2. Auftragsverwaltung
**Datei:** [02_order_workflow.md](./02_order_workflow.md)

**Prozesse:**
- ✅ Gesamtprozess: Von Anfrage bis Auslieferung
- ✅ Stickerei-Auftrag erstellen
- ✅ Design-Workflow (Upload/Bestellen/Freigabe)
- ✅ Textilien bestellen
- ✅ Produktionsstart
- ✅ Qualitätsprüfung & Fertigstellung

**Diagramme:**
- Flowchart: Gesamtprozess
- Flowchart: Stickerei-Auftrag erstellen
- Flowchart: Design-Workflow
- Flowchart: Textilien bestellen
- Flowchart: Produktionsstart
- Flowchart: Qualitätsprüfung
- Datenfluss: Order-Model

---

### 3. Design-Workflow & DST-Analyse
**Datei:** [03_design_workflow.md](./03_design_workflow.md)

**Prozesse:**
- ✅ Gesamtprozess: Design-Workflow
- ✅ DST-Datei-Analyse (automatisch)
- ✅ Garn-Zuordnung
- ✅ Thumbnail-Generierung
- ✅ Upload-Sicherheit

**Diagramme:**
- Flowchart: Design-Workflow (komplett)
- Flowchart: DST-Datei-Analyse (detailliert)
- Flowchart: Garn-Zuordnung
- Flowchart: Thumbnail-Generierung
- Flowchart: Upload-Sicherheit

**Code-Beispiele:**
- DST-Analyzer (Python)
- Design-Upload Utility (Python)

---

## 🚧 Geplante Workflows (TODO)

### 4. Artikelverwaltung
**Geplante Datei:** `04_article_management.md`

**Geplante Prozesse:**
- [ ] Artikel manuell anlegen
- [ ] L-Shop Excel-Import
- [ ] Preiskalkulation
- [ ] Varianten verwalten
- [ ] Lagerbestand aktualisieren

---

### 5. Produktionsplanung
**Geplante Datei:** `05_production_planning.md`

**Geplante Prozesse:**
- [ ] Maschine zuweisen
- [ ] Produktionskalender
- [ ] Kapazitätsplanung
- [ ] Garnverbrauch erfassen

---

### 6. Garnverwaltung
**Geplante Datei:** `06_thread_management.md`

**Geplante Prozesse:**
- [ ] Garne anlegen
- [ ] PDF-Import (Garnkarten)
- [ ] Lagerbestand verwalten
- [ ] Nachbestellvorschläge
- [ ] Garnverbrauch buchen

---

### 7. Lieferantenverwaltung
**Geplante Datei:** `07_supplier_management.md`

**Geplante Prozesse:**
- [ ] Lieferant anlegen
- [ ] Bestellung erstellen
- [ ] Webshop-Integration
- [ ] Lieferstatus tracken

---

### 8. Rechnungsstellung
**Geplante Datei:** `08_invoicing_workflow.md`

**Geplante Prozesse:**
- [ ] Rechnung erstellen
- [ ] Kassenbeleg (TSE)
- [ ] ZUGFeRD-Export
- [ ] Zahlungsverfolgung
- [ ] Z-Bericht (Tagesabschluss)

---

### 9. Versandprozess
**Geplante Datei:** `09_shipping_workflow.md`

**Geplante Prozesse:**
- [ ] Versand erstellen
- [ ] Tracking-Nummer erfassen
- [ ] Lieferschein drucken
- [ ] Versandstatus tracken

---

### 10. Maschinenverwaltung
**Geplante Datei:** `10_machine_management.md`

**Geplante Prozesse:**
- [ ] Maschine anlegen
- [ ] Wartung planen
- [ ] Thread-Setup konfigurieren
- [ ] Maschinenstatus überwachen

---

## 📊 Diagramm-Typen

In den Workflow-Dokumentationen werden folgende Diagramm-Typen verwendet:

### Flowcharts (Ablaufdiagramme)
- **Zweck:** Schrittweise Prozessdarstellung
- **Tool:** Mermaid Flowchart
- **Verwendung:** Hauptprozesse, Entscheidungsbäume

### Sequence Diagrams (Sequenzdiagramme)
- **Zweck:** Interaktion zwischen Komponenten
- **Tool:** Mermaid Sequence Diagram
- **Verwendung:** API-Calls, Datenfluss

### Entity-Relationship Diagrams (ER-Diagramme)
- **Zweck:** Datenbank-Beziehungen
- **Tool:** Mermaid ER Diagram
- **Verwendung:** Model-Relationships

---

## 🔧 Verwendung der Diagramme

### In Markdown-Viewer
Die Diagramme sind in Mermaid-Syntax geschrieben und können in jedem Markdown-Viewer mit Mermaid-Support dargestellt werden:
- **GitHub** - Native Unterstützung
- **GitLab** - Native Unterstützung
- **VS Code** - Mit Mermaid-Extension
- **IntelliJ** - Mit Markdown-Plugin

### Als Bilder exportieren
```bash
# Mit Mermaid CLI
npm install -g @mermaid-js/mermaid-cli
mmdc -i 01_customer_management.md -o customer_workflow.png
```

### Online-Editor
Diagramme können auch online bearbeitet werden:
- https://mermaid.live/

---

## 📝 Dokumentations-Standards

Alle Workflow-Dokumente folgen diesem Format:

1. **Titel & Metadaten**
   - Dateiname
   - Erstelldatum
   - Version

2. **Gesamtprozess**
   - High-Level Flowchart
   - End-to-End Ablauf

3. **Detailprozesse**
   - Einzelne Schritte detailliert
   - Unterprozesse

4. **Datenfluss**
   - Controller → Model → DB
   - Request/Response-Zyklen

5. **Klassen & Methoden**
   - Relevante Models
   - Controller-Funktionen
   - Code-Beispiele

6. **Templates**
   - Verwendete HTML-Templates
   - Template-Variablen

7. **Fehlerbehandlung**
   - Häufige Fehler
   - Error-Handling
   - Validierung

---

## 🔄 Updates & Wartung

### Letzte Änderungen
- **10.11.2025:** Initiale Workflows erstellt
  - Customer Management
  - Order Workflow
  - Design Workflow

### Geplante Ergänzungen
- Artikelverwaltung (bis 15.11.2025)
- Produktionsplanung (bis 20.11.2025)
- Garnverwaltung (bis 25.11.2025)
- Restliche Workflows (bis 30.11.2025)

---

## 📞 Feedback & Fragen

Für Feedback oder Fragen zu den Workflows:
- **Entwickler:** Hans Hahn
- **Projekt:** StitchAdmin 2.0

---

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Letzte Aktualisierung:** 10. November 2025
