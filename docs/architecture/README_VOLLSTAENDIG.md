# StitchAdmin 2.0 - Vollständige Architektur-Dokumentation

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**

**Version:** 2.0.0-alpha  
**Stand:** 10.11.2025  
**Status:** Umfassende Dokumentation aller Module, Klassen und Workflows

---

## 📋 Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Architektur-Überblick](#architektur-überblick)
3. [Datenbank-Schema](#datenbank-schema)
4. [Module und Komponenten](#module-und-komponenten)
5. [Workflows](#workflows)
6. [API-Referenz](#api-referenz)
7. [Deployment](#deployment)

---

## 🎯 Übersicht

StitchAdmin 2.0 ist ein vollständiges ERP-System für Stickerei- und Textilveredelungsbetriebe, entwickelt mit Flask und SQLAlchemy. Das System basiert auf einer modernen MVC-Architektur mit klarer Trennung von Datenmodellen, Geschäftslogik und Präsentationsschicht.

### Technologie-Stack

```
┌─────────────────────────────────────────────┐
│           Frontend (Browser)                │
│  HTML5 + Jinja2 + CSS3 + Vanilla JS        │
└────────────────┬────────────────────────────┘
                 │ HTTP/HTTPS
┌────────────────┴────────────────────────────┐
│         Flask Application (Python)          │
│  ┌──────────────────────────────────────┐  │
│  │   Controllers (Blueprints)           │  │
│  │   - 38+ Module für verschiedene      │  │
│  │     Geschäftsbereiche                │  │
│  └──────────────┬───────────────────────┘  │
│                 │                            │
│  ┌──────────────┴───────────────────────┐  │
│  │   Services (Business Logic)          │  │
│  │   - Komplexe Geschäftslogik          │  │
│  │   - Datenvalidierung                 │  │
│  └──────────────┬───────────────────────┘  │
│                 │                            │
│  ┌──────────────┴───────────────────────┐  │
│  │   Models (SQLAlchemy ORM)            │  │
│  │   - 20+ Datenbank-Tabellen           │  │
│  │   - Relationships                    │  │
│  └──────────────┬───────────────────────┘  │
└─────────────────┴─────────────────────────┘
                  │
┌─────────────────┴─────────────────────────┐
│      SQLite Database                      │
│  (PostgreSQL-kompatibel für Produktion)   │
└───────────────────────────────────────────┘
```

### Projektstruktur

```
StitchAdmin2.0/
│
├── app.py                          # Flask Application Factory
├── requirements.txt                # Python-Abhängigkeiten
├── .env                           # Umgebungsvariablen
│
├── instance/                      # Daten (nicht in Git)
│   ├── stitchadmin.db            # SQLite-Datenbank
│   └── uploads/                  # Hochgeladene Dateien
│
├── src/
│   ├── controllers/              # 38 Blueprint-Module
│   ├── models/                   # 8 Model-Dateien
│   ├── services/                 # Business-Logic
│   ├── templates/                # 126 Jinja2-Templates
│   ├── static/                   # CSS, JS, Images
│   └── utils/                    # 14 Utility-Module
│
├── docs/                         # Dokumentation
│   └── architecture/            # Diese Datei
│
├── tests/                        # Tests (pytest)
├── scripts/                      # Hilfsskripte
├── backups/                      # DB-Backups
└── logs/                         # Anwendungs-Logs
```

---

## 🏗️ Architektur-Überblick

### MVC-Pattern

StitchAdmin folgt dem Model-View-Controller Pattern mit Flask-spezifischen Erweiterungen:

```
┌─────────────────────────────────────────────────────────┐
│                      USER REQUEST                        │
│                    (HTTP/Browser)                        │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   FLASK ROUTING                          │
│              (@app.route decorators)                     │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    CONTROLLER                            │
│                  (Blueprint-Modul)                       │
│                                                          │
│  Aufgaben:                                              │
│  • Request-Validierung                                  │
│  • Session-Management                                   │
│  • Service-Aufrufe                                      │
│  • Response-Generierung                                 │
│                                                          │
│  Beispiel: customer_controller_db.py                    │
│  @customer_bp.route('/add', methods=['GET', 'POST'])    │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                     SERVICE                              │
│                (Business Logic)                          │
│                                                          │
│  Aufgaben:                                              │
│  • Geschäftsregeln prüfen                              │
│  • Datenvalidierung                                     │
│  • Komplexe Berechnungen                               │
│  • Mehrere Models koordinieren                          │
│  • Transaktionen verwalten                             │
│                                                          │
│  Beispiel: customer_service.py                          │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                      MODEL                               │
│                (SQLAlchemy ORM)                          │
│                                                          │
│  Aufgaben:                                              │
│  • Datenstruktur definieren                            │
│  • Relationships festlegen                             │
│  • Basis-Validierung                                   │
│  • Datenbank-Queries                                   │
│                                                          │
│  Beispiel: models.py - Customer                         │
│  class Customer(db.Model):                              │
│      id = db.Column(db.Integer, primary_key=True)       │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    DATABASE                              │
│                   (SQLite/PostgreSQL)                    │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                      VIEW                                │
│                 (Jinja2 Template)                        │
│                                                          │
│  Aufgaben:                                              │
│  • HTML-Generierung                                     │
│  • Daten-Präsentation                                  │
│  • Formular-Rendering                                  │
│  • Template-Vererbung                                  │
│                                                          │
│  Beispiel: customers/list.html                          │
└─────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   HTTP RESPONSE                          │
│                  (HTML/JSON/Redirect)                    │
└─────────────────────────────────────────────────────────┘
```

### Schichtenarchitektur

```
┌──────────────────────────────────────────────────────┐
│  Presentation Layer (Templates + Static Files)       │
│  • Jinja2-Templates                                  │
│  • CSS/JavaScript                                    │
│  • Statische Assets                                  │
└────────────────────────┬─────────────────────────────┘
                         │
┌────────────────────────┴─────────────────────────────┐
│  Controller Layer (Flask Blueprints)                 │
│  • Route-Definitionen                                │
│  • Request-Handling                                  │
│  • Response-Formatierung                            │
│  • Session-Management                                │
└────────────────────────┬─────────────────────────────┘
                         │
┌────────────────────────┴─────────────────────────────┐
│  Service Layer (Business Logic)                      │
│  • Geschäftsregeln                                   │
│  • Komplexe Operationen                             │
│  • Datenvalidierung                                  │
│  • Transaktionsmanagement                           │
└────────────────────────┬─────────────────────────────┘
                         │
┌────────────────────────┴─────────────────────────────┐
│  Data Access Layer (SQLAlchemy Models)               │
│  • Datenbank-Models                                  │
│  • Relationships                                     │
│  • Query-Methoden                                    │
│  • Migrations                                        │
└────────────────────────┬─────────────────────────────┘
                         │
┌────────────────────────┴─────────────────────────────┐
│  Database Layer (SQLite/PostgreSQL)                  │
│  • Datenpersistenz                                   │
│  • ACID-Transaktionen                               │
│  • Indizes                                           │
│  • Constraints                                       │
└──────────────────────────────────────────────────────┘
```

### Application Factory Pattern

```python
# app.py
from flask import Flask
from src.models.models import db
from src.controllers import register_blueprints

def create_app():
    """
    Flask Application Factory
    Erstellt und konfiguriert die Flask-App
    """
    app = Flask(__name__)
    
    # Konfiguration laden
    app.config.from_object('config.Config')
    
    # Datenbank initialisieren
    db.init_app(app)
    
    # Blueprints registrieren
    register_blueprints(app)
    
    # Context Processors
    register_context_processors(app)
    
    # Error Handlers
    register_error_handlers(app)
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

---

## Fortsetzung folgt in separaten Dateien...

Diese Datei wird in spezialisierte Dokumentations-Dateien aufgeteilt:

1. **DATENBANK_SCHEMA.md** - Alle Tabellen und Beziehungen
2. **CONTROLLER_REFERENZ.md** - Alle Controller mit Routen
3. **WORKFLOWS.md** - Alle Geschäftsprozesse
4. **KLASSEN_DIAGRAMME.md** - Visualisierung der Klassenstruktur
5. **API_DOKUMENTATION.md** - REST-API Endpunkte

---

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Letzte Aktualisierung:** 10.11.2025
