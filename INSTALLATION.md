# StitchAdmin 2.0 - Installation

**Erstellt von: Hans Hahn - Alle Rechte vorbehalten**

---

## Schnellstart

### Linux/macOS

```bash
# 1. Repository klonen oder entpacken
cd StitchAdmin2.0

# 2. Installation ausführen (benötigt sudo)
sudo bash scripts/install_dependencies.sh

# 3. Konfiguration anpassen
cp .env.example .env
# Bearbeite .env mit deinen Einstellungen

# 4. Server starten
python3 app.py
```

### Windows

```cmd
REM 1. Repository entpacken
cd StitchAdmin2.0

REM 2. Tesseract OCR manuell installieren
REM Download: https://github.com/UB-Mannheim/tesseract/wiki
REM Wichtig: Deutsche Sprache auswählen!

REM 3. Installation ausführen
scripts\install_dependencies.bat

REM 4. Konfiguration anpassen
copy .env.example .env
REM Bearbeite .env mit deinen Einstellungen

REM 5. Server starten
python app.py
```

---

## Manuelle Installation

### 1. Voraussetzungen

#### System-Requirements

- **Python:** 3.11 oder höher (getestet mit 3.11, 3.12, 3.13)
- **Tesseract OCR:** 4.0 oder höher (für OCR-Funktionen)
- **Betriebssystem:** Linux, macOS, Windows (WSL2 empfohlen)
- **RAM:** Mindestens 2 GB
- **Festplatte:** 500 MB (+ Platz für Datenbank und Uploads)

#### Python installieren

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv
```

**macOS:**
```bash
brew install python@3.11
```

**Windows:**
- Download: https://www.python.org/downloads/
- Wichtig: "Add Python to PATH" aktivieren!

### 2. Tesseract OCR installieren

#### Linux (Ubuntu/Debian)

```bash
sudo apt-get install tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng
```

#### macOS

```bash
brew install tesseract tesseract-lang
```

#### Windows

1. Download: https://github.com/UB-Mannheim/tesseract/wiki
2. Installiere `tesseract-ocr-w64-setup-5.x.x.exe`
3. Wähle bei der Installation **"Deutsche Sprache"** aus
4. Füge Tesseract zum PATH hinzu (Option während Installation)

**Tesseract-Pfad konfigurieren (falls nicht im PATH):**

Erstelle/bearbeite `src/config/tesseract_config.py`:
```python
import pytesseract

# Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# macOS (Homebrew)
# pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
```

### 3. Python-Dependencies installieren

```bash
# Im Projekt-Verzeichnis
cd StitchAdmin2.0

# Virtual Environment erstellen (empfohlen)
python3 -m venv venv

# Virtual Environment aktivieren
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Dependencies installieren
pip install -r requirements.txt
```

### 4. Datenbank initialisieren

```bash
# Datenbank-Struktur erstellen (beim ersten Start)
python3 app.py

# Server beenden (Strg+C)

# Migrationen ausführen (für Foto & OCR Features)
python3 scripts/add_order_photos_field.py
python3 scripts/add_post_entry_photos_fields.py
```

### 5. Konfiguration

```bash
# .env Datei erstellen
cp .env.example .env

# Bearbeite .env mit deinen Einstellungen
nano .env  # oder ein anderer Editor
```

**Wichtige Einstellungen in .env:**

```env
# Geheimschlüssel (WICHTIG: Ändern!)
SECRET_KEY=your-secret-key-here

# Datenbank (Standard: SQLite)
DATABASE_URL=sqlite:///instance/stitchadmin.db

# Upload-Ordner
UPLOAD_FOLDER=instance/uploads

# Flask-Umgebung
FLASK_ENV=production  # oder 'development' für Debug-Modus
```

### 6. Server starten

```bash
# Entwicklungs-Server
python3 app.py

# Zugriff im Browser:
# http://localhost:5000

# Von anderen Geräten im Netzwerk:
# http://<DEINE-IP>:5000
```

**IP-Adresse herausfinden:**

```bash
# Linux/macOS
hostname -I | awk '{print $1}'

# Windows
ipconfig | findstr IPv4
```

---

## Features & Module

Nach erfolgreicher Installation sind folgende Features verfügbar:

### 1. Mobile Foto-Dokumentation

**Für Aufträge:**
- `/orders/<ORDER_ID>/photos` - Fotos mit Smartphone-Kamera aufnehmen
- Dokumentation von Farben, Positionen, Samples, QC

**Für Posteingang (mit OCR):**
- `/documents/post/<POST_ENTRY_ID>/scan` - Dokumente scannen
- Automatische Texterkennung
- Smart-Extraction: Beträge, Datum, Tracking-Nummern

Dokumentation: `docs/MOBILE_WORKFLOW_FEATURES.md`

### 2. Workflow-Automatisierung

- Produktion → Packliste → Lieferschein
- Automatische PDF-Generierung
- QC-Workflows mit Foto-Dokumentation

Dokumentation: `docs/WORKFLOWS.md`

### 3. OCR & Smart-Extraction

- Rechnungen: Betrag & Rechnungsnummer extrahieren
- Briefe: Volltext-Erkennung
- Pakete: Tracking-Nummer automatisch erkennen

Dokumentation: `docs/POSTENTRY_OCR_FEATURES.md`

---

## Troubleshooting

### Python nicht gefunden

**Problem:** `python: command not found`

**Lösung:**
```bash
# Versuche python3
python3 --version

# Oder installiere Python
sudo apt-get install python3
```

### Tesseract nicht gefunden

**Problem:** `pytesseract.TesseractNotFoundError`

**Lösung:**
1. Installiere Tesseract (siehe Abschnitt 2)
2. Konfiguriere Pfad in `src/config/tesseract_config.py`
3. Prüfe Installation: `tesseract --version`

### Port bereits belegt

**Problem:** `Address already in use: Port 5000`

**Lösung:**
```bash
# Port ändern in app.py:
app.run(host='0.0.0.0', port=5001)

# Oder laufenden Prozess beenden:
# Linux/macOS:
lsof -ti:5000 | xargs kill -9

# Windows:
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### Datenbank-Fehler

**Problem:** `OperationalError: no such table`

**Lösung:**
```bash
# Datenbank neu initialisieren
rm instance/stitchadmin.db
python3 app.py

# Migrationen ausführen
python3 scripts/add_order_photos_field.py
python3 scripts/add_post_entry_photos_fields.py
```

### OCR erkennt keinen Text

**Problem:** OCR liefert leeren Text

**Lösung:**
1. **Bessere Beleuchtung** beim Scannen
2. **Dokument glatt legen** (keine Falten)
3. **Höhere Auflösung** verwenden
4. **Sprache prüfen:** Deutsch (`deu`) ausgewählt?

### Permission Denied (Linux)

**Problem:** `Permission denied: 'instance/uploads'`

**Lösung:**
```bash
# Upload-Ordner Berechtigungen setzen
sudo chown -R $USER:$USER instance/
chmod -R 755 instance/
```

---

## Produktions-Deployment

### Mit Gunicorn (empfohlen)

```bash
# Gunicorn ist bereits in requirements.txt enthalten

# Server starten
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Mit Logs
gunicorn -w 4 -b 0.0.0.0:5000 --access-logfile - --error-logfile - app:app
```

### Mit Systemd (Linux)

Erstelle `/etc/systemd/system/stitchadmin.service`:

```ini
[Unit]
Description=StitchAdmin 2.0
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/StitchAdmin2.0
Environment="PATH=/var/www/StitchAdmin2.0/venv/bin"
ExecStart=/var/www/StitchAdmin2.0/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Service aktivieren
sudo systemctl enable stitchadmin
sudo systemctl start stitchadmin
sudo systemctl status stitchadmin
```

### Mit Nginx (Reverse Proxy)

```nginx
server {
    listen 80;
    server_name stitchadmin.example.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /uploads {
        alias /var/www/StitchAdmin2.0/instance/uploads;
    }
}
```

---

## Deinstallation

```bash
# Virtual Environment entfernen (falls verwendet)
rm -rf venv/

# Datenbank löschen
rm instance/stitchadmin.db

# Uploads löschen
rm -rf instance/uploads/

# Python-Packages entfernen
pip uninstall -r requirements.txt -y

# Tesseract deinstallieren (optional)
# Ubuntu/Debian:
sudo apt-get remove tesseract-ocr
```

---

## Support & Dokumentation

- **Workflow-Features:** `docs/MOBILE_WORKFLOW_FEATURES.md`
- **OCR-Features:** `docs/POSTENTRY_OCR_FEATURES.md`
- **Workflows:** `docs/WORKFLOWS.md`
- **API-Dokumentation:** `docs/API.md` (falls vorhanden)

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**
