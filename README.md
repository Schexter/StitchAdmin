
# StitchAdmin 2.0

**ERP-System für Stickerei- und Textilveredelungsbetriebe**

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Flask Version](https://img.shields.io/badge/flask-3.0.3-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-All%20Rights%20Reserved-red.svg)](LICENSE)

---

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**

**Version:** 2.0.5-alpha
**Stand:** 14. November 2025
**Status:** Alpha (ca. 50% fertig, Testing-Phase Sprint 2)

---

## 📋 Inhaltsverzeichnis

- [Über das Projekt](#über-das-projekt)
- [Hauptfunktionen](#hauptfunktionen)
- [Technologie-Stack](#technologie-stack)
- [Installation](#installation)
- [Schnellstart](#schnellstart)
- [Projektstruktur](#projektstruktur)
- [Module im Detail](#module-im-detail)
- [Konfiguration](#konfiguration)
- [Entwicklung](#entwicklung)
- [Testing](#testing)
- [Deployment](#deployment)
- [Bekannte Probleme](#bekannte-probleme)
- [Roadmap](#roadmap)
- [Support](#support)

---

## 🎯 Über das Projekt

**StitchAdmin 2.0** ist ein spezialisiertes ERP-System, das die kompletten Geschäftsprozesse von Stickerei- und Textilveredelungsbetrieben abbildet. Das System wurde entwickelt, um die besonderen Anforderungen der Branche zu erfüllen, die von Standard-ERP-Systemen nicht ausreichend abgedeckt werden.

### Warum StitchAdmin?

Standard-ERP-Systeme wie ERPNext bieten keine spezialisierten Funktionen für:
- 🧵 Stichzahl-Kalkulation und DST-Datei-Analyse
- 🎨 Design-Workflow mit Freigabeprozessen
- 🧶 Garnverwaltung mit Farbcodes und Lagerbestand
- 🏭 Maschinenplanung für Stickmaschinen
- 📦 Textile Artikel mit Varianten (Größe/Farbe)
- 💰 TSE-konforme Kassenfunktionen für Ladengeschäft

**StitchAdmin 2.0** schließt diese Lücke und bietet eine maßgeschneiderte Lösung.

### Entwicklungsphilosophie

Das Projekt befindet sich in der **schrittweisen Implementierung und Testphase**. Module werden vollständig implementiert und getestet, bevor zur nächsten Funktion übergegangen wird. 

⚠️ **WICHTIG:** Daten werden erst nach Nachfrage gespeichert oder geändert! Dies ermöglicht ausführliches Testing vor dem produktiven Einsatz.

---

## ✨ Hauptfunktionen

### 👥 Kundenverwaltung
- Privat- und Geschäftskunden
- Vollständige Adress- und Kontaktdaten
- Kundenhistorie und Notizen
- Newsletter-Verwaltung
- DSGVO-konforme Datenhaltung

### 📦 Artikelverwaltung
- **L-Shop Excel-Import** für Textilien (✅ 10.251 Artikel erfolgreich importiert)
- Artikel-Varianten (Farbe/Größe)
- Mehrstufige Preiskalkulation (EK → VK)
- Lagerbestandsverwaltung
- **137 Marken** automatisch aus Import generiert
- Lieferanten-Zuordnung mit Preishistorie

### 📋 Auftragsverwaltung
- **Stickerei-Aufträge** mit Stichzahl-Kalkulation
- **Druck-Aufträge** (DTG, DTF, Siebdruck)
- Kombinierte Aufträge möglich
- Design-Workflow (Upload → Bestellung → Freigabe)
- Status-Tracking mit vollständiger Historie
- Liefertermin-Verwaltung
- Textile-Bestellstatus pro Position

### 🏭 Produktionsverwaltung
- Maschinen-Kapazitätsplanung
- Produktionszeiten-Kalkulation
- Maschinenstatus-Überwachung
- Garnverbrauch-Tracking
- Priorisierung von Aufträgen

### 🧵 Garnverwaltung
- Garnfarben mit Herstellercodes
- Lagerbestandsverwaltung
- Verbrauchserfassung pro Auftrag
- Automatische Nachbestellvorschläge
- PDF-Import von Garnkarten

### 🏢 Lieferantenverwaltung
- Lieferanten-Stammdaten
- Ansprechpartner-Verwaltung
- Bestellungen mit Status-Tracking
- Webshop-Integration (automatische Links)
- Kommunikationsprotokoll
- Retouren-Adressen

### 💰 Rechnungsmodul (GoBD/TSE-konform)
- TSE-konforme Kassenbelege
- Rechnungserstellung mit Positionen
- ZUGFeRD-XML-Export
- Zahlungsverfolgung
- Tagesabschlüsse (Z-Berichte)
- Mehrwertsteuersätze
- Storno-Funktionen

### 🎨 Design-Workflow
- Sichere Datei-Uploads (DST, EMB, PES, etc.)
- **Automatische DST-Analyse** (Stichzahl, Größe, Farbwechsel)
- Thumbnail-Generierung für Vorschau
- Design-Status-Tracking
- Lieferanten-Bestellung von Designs
- Verknüpfung mit Aufträgen

### 📊 Dashboard & Statistiken
- Übersicht über aktuelle Aufträge
- Produktionsauslastung
- Umsatzstatistiken
- Offene Posten
- Lagerbestand-Warnungen

### 📱 Mobile Webapp & OCR Features ⭐ NEU!
- **Smartphone-Zugriff** - Nutzung im lokalen Netzwerk (Intranet)
- **Kamera-Integration** - Foto-Aufnahme für QM-Dokumentation
- **QM-Fotos** - Dokumentation von Farben, Positionen, Samples, Qualitätskontrolle
- **OCR-Texterkennung** - Tesseract-Integration für automatische Texterkennung
- **Smart-Extraction** - Automatische Erkennung von:
  - 💰 Geldbeträgen (€123,45)
  - 📅 Datumsangaben (25.11.2025, flexible Formate)
  - 📦 Tracking-Nummern (DHL, DPD, UPS, Hermes, GLS, FedEx)
  - 📄 Referenznummern (Rechnungs-Nr., Kunden-Nr., Auftrags-Nr.)
- **Auto-Fill** - Automatisches Ausfüllen von Feldern nach OCR-Erkennung
- **Workflow-Integration** - Produktion → Packliste → Lieferschein automatisch
- **PDF-Generierung** - Professionelle Dokumente mit Logo & QR-Code

**Dokumentation:**
- [Mobile Workflow Features](docs/MOBILE_WORKFLOW_FEATURES.md)
- [PostEntry OCR Features](docs/POSTENTRY_OCR_FEATURES.md)

---

## 🛠️ Technologie-Stack

### Backend
- **Framework:** Flask 3.0.3 (Python Web Framework)
- **Datenbank:** SQLite mit SQLAlchemy 2.0.36 ORM
- **Migrations:** Flask-Migrate 4.0.5 (Alembic-basiert)
- **Authentication:** Flask-Login
- **Forms:** Flask-WTF mit WTForms
- **Templating:** Jinja2
- **Logging:** Zentrales Logger-System mit strukturiertem Logging

### Frontend
- **HTML5** mit Jinja2-Templates
- **CSS3** (Custom Styling)
- **JavaScript** (Vanilla JS)
- **Bootstrap-kompatible** Komponenten

### Spezial-Libraries
- **pyembroidery 1.5.1** - DST-Datei-Analyse
- **Pillow ≥10.4.0** - Bildverarbeitung & Thumbnails
- **openpyxl 3.1.2** - L-Shop Excel-Import
- **pandas ≥2.2.0** - Datenverarbeitung
- **PyPDF2 / pdfplumber** - PDF-Analyse (Garnkarten, Rechnungen)
- **reportlab ≥4.0.0** - PDF-Generierung (Packlisten, Lieferscheine)
- **pytesseract ≥0.3.10** - OCR-Texterkennung ⭐ NEU!
- **qrcode[pil] ≥7.4.2** - QR-Code Generierung

### Development Tools
- **Python 3.11+** (getestet mit 3.11, 3.12, 3.13)
- **pip** - Package Management
- **venv** - Virtual Environment
- **Git** - Version Control

### Testing Framework ✅
- **pytest 8.3.3** - Testing Framework
- **pytest-cov 5.0.0** - Test Coverage (~20%, Ziel: >60%)
- **pytest-flask 1.3.0** - Flask-spezifische Tests
- **~400 Tests** implementiert (39 Model-Tests ✅, Integration-Tests ✅, Service-Tests ✅)

---

## 📥 Installation

### Systemanforderungen

- **Betriebssystem:** Windows 10/11, Linux, macOS
- **Python:** Version 3.11 oder höher
- **RAM:** Mindestens 4GB (8GB empfohlen)
- **Speicher:** 500MB für Anwendung + Speicher für Uploads
- **Tesseract OCR:** 4.0+ (für OCR-Features) ⭐ NEU!

### ⚡ Schnellinstallation (Empfohlen)

**Linux/macOS:**
```bash
cd StitchAdmin2.0
sudo bash scripts/install_dependencies.sh
python3 app.py
```

**Windows:**
```cmd
cd StitchAdmin2.0
REM Tesseract OCR installieren: https://github.com/UB-Mannheim/tesseract/wiki
scripts\install_dependencies.bat
python app.py
```

**Detaillierte Anleitung:** Siehe [INSTALLATION.md](INSTALLATION.md)

### Schritt-für-Schritt Installation (Manuell)

#### 1. Repository klonen oder herunterladen

```bash
# Falls Git verwendet wird
git clone <repository-url>
cd StitchAdmin2.0

# Oder ZIP herunterladen und entpacken
```

#### 2. Virtual Environment erstellen

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/macOS
python3 -m venv .venv
source .venv/bin/activate
```

#### 3. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

**Bei Python 3.13 Problemen:**
```bash
# SQLAlchemy-Fix ausführen
fix_sqlalchemy.bat

# Oder manuell
pip install --upgrade "SQLAlchemy>=2.0.36"
```

#### 4. Umgebungsvariablen konfigurieren

Erstellen Sie eine `.env` Datei im Projektverzeichnis:

```env
# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=ihre-geheime-schluessel-hier-aendern

# Database
DATABASE_URL=sqlite:///instance/stitchadmin.db

# Upload Configuration
UPLOAD_FOLDER=instance/uploads
MAX_CONTENT_LENGTH=16777216

# Email Configuration (optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=ihre-email@example.com
MAIL_PASSWORD=ihr-passwort
```

#### 5. Datenbank initialisieren

Die Datenbank wird beim ersten Start automatisch erstellt.

```bash
python app.py
```

---

## 🚀 Schnellstart

### Anwendung starten

```bash
# Virtual Environment aktivieren (falls nicht aktiv)
.venv\Scripts\activate   # Windows
source .venv/bin/activate  # Linux/macOS

# Anwendung starten
python app.py

# Oder mit Windows-Batch-Datei
start.bat
```

### Im Browser öffnen

```
http://localhost:5000
```

### Standard-Login

```
Benutzername: admin
Passwort: admin
```

⚠️ **WICHTIG:** Ändern Sie das Admin-Passwort sofort nach dem ersten Login!

### Erste Schritte nach dem Login

1. **Passwort ändern:** Einstellungen → Benutzer → Admin-Passwort ändern
2. **Grundeinstellungen konfigurieren:**
   - Mehrwertsteuersätze festlegen
   - Preiskalkulations-Faktoren einstellen
   - E-Mail-Konfiguration (optional)
3. **Stammdaten anlegen:**
   - Lieferanten erfassen
   - Produktkategorien erstellen
   - Marken/Hersteller erfassen
   - Maschinen registrieren
4. **Artikel importieren:**
   - L-Shop Excel-Datei importieren
   - Oder manuell Artikel anlegen
5. **Ersten Test-Auftrag erstellen**

---

## 📁 Projektstruktur

```
StitchAdmin2.0/
├── app.py                          # Haupt-Application (Flask Factory)
├── requirements.txt                # Python-Abhängigkeiten
├── .env                           # Umgebungsvariablen (nicht in Git!)
├── start.bat                      # Windows-Startskript
├── fix_sqlalchemy.bat             # SQLAlchemy-Reparatur
│
├── README.md                      # Diese Datei
├── TODO.md                        # Aufgaben und Meilensteine
├── CHANGELOG.md                   # Versions-Historie
├── error.log                      # Fehlerprotokoll
│
├── instance/                      # Flask Instance-Ordner
│   ├── stitchadmin.db            # SQLite-Datenbank
│   └── uploads/                  # Hochgeladene Dateien
│       ├── designs/              # Design-Dateien (DST, EMB, etc.)
│       ├── documents/            # Dokumente (PDF, etc.)
│       └── images/               # Bilder
│
├── src/                          # Quellcode-Hauptverzeichnis
│   ├── controllers/              # Flask Blueprints (38 Module)
│   │   ├── customer_controller_db.py
│   │   ├── article_controller_db.py
│   │   ├── order_controller_db.py
│   │   ├── rechnungsmodul/      # Rechnungs- und Kassenmodul
│   │   └── ...
│   │
│   ├── models/                   # SQLAlchemy Models (20+ Tabellen)
│   │   ├── models.py            # Haupt-Models
│   │   ├── article_variant.py
│   │   ├── rechnungsmodul.py
│   │   └── ...
│   │
│   ├── services/                 # Business-Logic-Services
│   │   ├── customer_service.py
│   │   ├── order_service.py
│   │   └── ...
│   │
│   ├── templates/                # Jinja2 HTML-Templates (126 Dateien)
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── customers/
│   │   ├── articles/
│   │   ├── orders/
│   │   └── ...
│   │
│   ├── static/                   # Statische Dateien
│   │   ├── css/
│   │   ├── js/
│   │   ├── images/
│   │   └── thumbnails/
│   │
│   └── utils/                    # Hilfsfunktionen (14 Module)
│       ├── dst_analyzer.py      # DST-Datei-Analyse
│       ├── design_upload.py     # Sichere Uploads
│       ├── pdf_analyzer.py      # PDF-Verarbeitung
│       ├── logger.py            # Logging
│       └── ...
│
├── config/                       # Konfigurationsdateien
├── scripts/                      # Hilfsskripte
├── docs/                         # Erweiterte Dokumentation
│   ├── PROJEKT_STRUKTUR.md      # Detaillierte Struktur-Dokumentation
│   ├── MIGRATION_GUIDE.md
│   └── ...
│
├── backups/                      # Datenbank-Backups
├── logs/                         # Anwendungs-Logs
└── tests/                        # Tests (in Entwicklung)
    ├── test_models.py
    ├── test_controllers.py
    └── conftest.py
```

---

## 📚 Module im Detail

### Kundenverwaltung (`/customers`)
- Erfassung von Privat- und Geschäftskunden
- Vollständige Kontakt- und Adressdaten
- Historie aller Interaktionen
- Notizen und Kommentare
- Newsletter-Verwaltung

### Artikelverwaltung (`/articles`)
- **L-Shop Import:** Excel-Dateien direkt importieren
- Artikel-Varianten für Größe/Farbe
- Preiskalkulation mit Aufschlagsfaktoren
- Lagerbestandsverwaltung
- Lieferanten-Zuordnung
- Kategorien und Marken

### Auftragsverwaltung (`/orders`)
- Auftragserstellung für Stickerei/Druck
- Design-Upload mit DST-Analyse
- Stichzahl-basierte Preiskalkulation
- Status-Tracking (Erfasst → In Produktion → Fertig → Ausgeliefert)
- Liefertermin-Planung
- Textile-Bestellung beim Lieferanten

### Produktionsverwaltung (`/production`)
- Maschinenzuordnung
- Kapazitätsplanung
- Reihenfolge-Optimierung
- Garnverbrauch-Erfassung
- Produktionszeit-Kalkulation

### Garnverwaltung (`/threads`)
- Garnfarben mit Herstellercodes
- Lagerbestand mit Min/Max-Grenzen
- Verbrauchserfassung
- Nachbestellvorschläge
- PDF-Import von Garnkarten

### Lieferantenverwaltung (`/suppliers`)
- Stammdaten mit Kontaktpersonen
- Webshop-Integration
- Bestellverwaltung
- Kommunikationsprotokoll
- Artikel-Lieferanten-Zuordnung

### Rechnungsmodul (`/kasse`, `/rechnung`)
- **TSE-konforme Kassenbelege**
- Rechnungserstellung
- ZUGFeRD-XML-Export
- Zahlungsverfolgung
- Z-Berichte (Tagesabschlüsse)

### Design-Workflow (`/design-workflow`)
- Datei-Upload mit Validierung
- **DST-Analyse:** Automatische Stichzahl-Erkennung
- Thumbnail-Generierung
- Status-Tracking
- Verknüpfung mit Aufträgen

---

## ⚙️ Konfiguration

### Preiskalkulation

Die Preiskalkulation erfolgt mehrstufig:

```
EK (Einkaufspreis)
↓ × Faktor 1 (Standard: 1.5)
= Zwischenpreis
↓ × Faktor 2 (Standard: 1.3)
= VK netto
↓ + MwSt (19% oder 7%)
= VK brutto
```

Faktoren können in **Einstellungen → Preiskalkulation** angepasst werden.

### Stickerei-Preise

Stickerei-Preise werden basierend auf Stichzahl berechnet:

```
Grundpreis + (Stichzahl ÷ 1000 × Preis pro 1000 Stiche)
```

Preise pro Position (Logo/Text) können in den Einstellungen definiert werden.

### E-Mail-Konfiguration

Für den E-Mail-Versand (z.B. Auftragsbestätigungen) in der `.env` konfigurieren:

```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=ihre-email@example.com
MAIL_PASSWORD=ihr-app-passwort
```

---

## 👨‍💻 Entwicklung

### Development Server starten

```bash
# Debug-Modus ist standardmäßig aktiviert
python app.py
```

Der Server läuft auf `http://localhost:5000` und lädt bei Code-Änderungen automatisch neu.

### Code-Standards

- **PEP 8** Python Style Guide
- **Type Hints** wo sinnvoll
- **Docstrings** für alle Funktionen und Klassen
- **Deutsche Kommentare** für Geschäftslogik
- **Englische Kommentare** für technische Details

### Neue Controller erstellen

```python
# src/controllers/mein_controller.py
from flask import Blueprint, render_template

mein_bp = Blueprint('mein', __name__, url_prefix='/mein')

@mein_bp.route('/')
def index():
    return render_template('mein/index.html')
```

In `app.py` registrieren:

```python
from src.controllers.mein_controller import mein_bp
app.register_blueprint(mein_bp)
```

### Neue Models erstellen

```python
# src/models/mein_model.py
from src.models.models import db

class MeinModel(db.Model):
    __tablename__ = 'mein_model'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
```

---

## 🧪 Testing

### Test-Setup ✅ (Sprint 1 & 2)

```bash
# Pytest bereits installiert in requirements.txt
# Tests ausführen
pytest

# Tests mit Coverage
pytest --cov=src --cov-report=html --cov-report=term

# Coverage-Report öffnen
# htmlcov/index.html im Browser öffnen
```

### Test-Struktur

```
tests/
├── conftest.py              # Pytest-Konfiguration & Fixtures
├── unit/                    # Unit-Tests
│   ├── models/              # Model-Tests (39 Tests ✅)
│   │   ├── test_customer_model.py
│   │   ├── test_article_model.py
│   │   ├── test_thread_model.py
│   │   └── test_order_model.py
│   └── utils/               # Utils-Tests (86 Tests ✅)
│       ├── test_form_helpers.py  (30 Tests, 100% Coverage)
│       ├── test_filters.py       (32 Tests, 87% Coverage)
│       └── test_security.py      (24 Tests, 92% Coverage)
├── integration/             # Integration-Tests (geplant)
└── htmlcov/                 # Coverage HTML-Reports
```

### Test-Statistiken (Stand: 14.11.2025)

- ✅ **~400 Tests** implementiert und bestehend
- ✅ **Model-Tests:** 39/39 (100%)
- ✅ **Integration-Tests:** 10/10 (100%)
- ✅ **L-Shop Import Tests:** 11/11 (100%)
- ✅ **Service-Tests:** ZugpferdService, PDFService getestet
- 🟡 **Test-Coverage:** ~20% (Ziel: >60% bis Ende Sprint 2)
- ✅ **10.251 L-Shop Artikel** erfolgreich importiert

---

## 🚀 Deployment

### Produktions-Setup

**1. Gunicorn installieren:**
```bash
pip install gunicorn
```

**2. Anwendung starten:**
```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

**3. Nginx als Reverse Proxy:**
```nginx
server {
    listen 80;
    server_name ihre-domain.de;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /static {
        alias /pfad/zu/StitchAdmin2.0/src/static;
    }
}
```

**4. Systemd Service erstellen:**
```ini
[Unit]
Description=StitchAdmin 2.0
After=network.target

[Service]
User=www-data
WorkingDirectory=/pfad/zu/StitchAdmin2.0
Environment="PATH=/pfad/zu/.venv/bin"
ExecStart=/pfad/zu/.venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app

[Install]
WantedBy=multi-user.target
```

### Sicherheits-Checkliste

- [ ] Starkes `SECRET_KEY` generieren
- [ ] Admin-Passwort ändern
- [ ] HTTPS aktivieren (Let's Encrypt)
- [ ] Firewall konfigurieren
- [ ] Regelmäßige Backups einrichten
- [ ] Log-Rotation konfigurieren
- [ ] Rate-Limiting aktivieren

---

## ⚠️ Bekannte Probleme

### Python 3.13 Kompatibilität

**Problem:** SQLAlchemy-Version zu alt für Python 3.13

**Lösung:**
```bash
fix_sqlalchemy.bat
# Oder
pip install --upgrade "SQLAlchemy>=2.0.36"
```

### L-Shop Import Encoding

**Problem:** Umlaute werden falsch dargestellt

**Lösung:** Excel-Datei mit UTF-8 Encoding speichern

### DST-Datei Upload

**Problem:** Große DST-Dateien (>10MB) werden abgelehnt

**Lösung:** `MAX_CONTENT_LENGTH` in `.env` erhöhen

---

## 🗺️ Roadmap

Siehe `TODO.md` für detaillierte Meilensteine und Aufgaben.

### Kurzfristig (Meilenstein 1-2)
- [x] Testing-Framework implementieren ✅ (12.11.2025)
- [x] Legacy-Controller bereinigen ✅ (12.11.2025 - 5.593 LOC entfernt)
- [x] Model-Tests implementieren ✅ (39 Tests, 100% bestanden)
- [x] Utils-Tests Basis ✅ (86 Tests, 93% Avg Coverage)
- [x] Migrations-System (Flask-Migrate) ✅ (installiert & konfiguriert)
- [ ] Test-Coverage auf >60% erhöhen (aktuell: 13.22%)
- [ ] Dokumentation vervollständigen (75% fertig)

### Mittelfristig (Meilenstein 3-4)
- [ ] REST-API erweitern
- [ ] Mobile-optimierte Oberfläche
- [ ] E-Mail-Benachrichtigungen
- [ ] Erweiterte Statistiken

### Langfristig (Meilenstein 5)
- [ ] Cloud-Synchronisation
- [ ] Multi-Mandanten-Fähigkeit
- [ ] Mobile-App (iOS/Android)
- [ ] Zahlungsintegration (SumUp/Stripe)

---

## 📞 Support

### Dokumentation
- **Projekt-Struktur:** `PROJEKT_STRUKTUR.md`
- **Schnellstart:** `QUICKSTART.md`
- **Migrations-Guide:** `docs/MIGRATION_GUIDE.md`

### Fehler melden
1. Prüfen Sie `error.log` auf Details
2. Prüfen Sie bekannte Probleme oben
3. Erstellen Sie einen detaillierten Bug-Report

### Entwickler
**Hans Hahn**  
**Projekt:** StitchAdmin 2.0  
**Lizenz:** Alle Rechte vorbehalten  
**Stand:** November 2025

---

## 📄 Lizenz

**Alle Rechte vorbehalten - Hans Hahn**

Diese Software ist urheberrechtlich geschützt. Die Nutzung, Vervielfältigung, Bearbeitung, Verbreitung und jede Art der Verwertung außerhalb der Grenzen des Urheberrechtes bedürfen der schriftlichen Zustimmung des Autors.

---

## 🙏 Danksagungen

- **Flask Community** - Für das exzellente Web-Framework
- **SQLAlchemy Team** - Für das mächtige ORM
- **pyembroidery** - Für die DST-Analyse-Library
- Alle Open-Source-Contributors der verwendeten Libraries

---

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**
**Letzte Aktualisierung:** 14.11.2025
**Version:** 2.0.5-alpha
