# ⚙️ IntelliJ IDEA Setup für StitchAdmin 2.0

**Letzte Aktualisierung:** 05.11.2025

---

## ✅ Status: KONFIGURIERT UND STARTBEREIT

Das Projekt ist bereits vollständig für IntelliJ IDEA konfiguriert!

---

## 📋 Was bereits konfiguriert ist:

✅ **Python SDK** - Python 3.13 mit Virtual Environment (.venv)
✅ **Flask-Unterstützung** - Flask-Plugin aktiviert
✅ **Jinja2-Templates** - Template-Ordner konfiguriert
✅ **Run-Configuration** - "StitchAdmin 2.0" fertig eingerichtet
✅ **Alle Dependencies** - Vollständig installiert (71 Pakete)

---

## 🚀 Starten in IntelliJ IDEA

### Option 1: Mit Run-Configuration (EMPFOHLEN)

1. **IntelliJ IDEA öffnen:**
   - Projekt öffnen: `C:\SoftwareEntwicklung\StitchAdmin2.0`

2. **Python Interpreter einrichten** (falls nötig):
   - `File` → `Project Structure` → `SDKs`
   - Klick auf `+` → `Python SDK` → `Existing environment`
   - Wähle: `.venv\Scripts\python.exe`
   - Name: `Python 3.13 (StitchAdmin2.0)`
   - Klick auf `OK`

3. **Run-Configuration auswählen:**
   - Oben rechts in der Toolbar: `StitchAdmin 2.0` auswählen
   - Klick auf den grünen **Play-Button** ▶️
   - **ODER** Drücke `Shift + F10`

4. **Browser öffnen:**
   ```
   http://localhost:5000
   ```

5. **Login:**
   ```
   Username: admin
   Password: admin
   ```

### Option 2: Terminal in IntelliJ

1. **Terminal öffnen** (Alt + F12)

2. **Virtual Environment aktivieren:**
   ```cmd
   .venv\Scripts\activate
   ```

3. **Anwendung starten:**
   ```cmd
   python app.py
   ```

4. **Browser öffnen:**
   ```
   http://localhost:5000
   ```

---

## 🛠️ IntelliJ IDEA Konfiguration (Details)

### Python Interpreter

- **Typ:** Virtual Environment (venv)
- **Pfad:** `.venv\Scripts\python.exe`
- **Python-Version:** 3.13
- **Installierte Pakete:** 71 (siehe unten)

### Flask-Konfiguration

- **Framework erkannt:** ✅ Ja
- **Template-Ordner:** `src/templates`
- **Static-Ordner:** `src/static`
- **App-Datei:** `app.py`

### Run-Configuration "StitchAdmin 2.0"

| Einstellung | Wert |
|-------------|------|
| **Script path** | `app.py` |
| **Python interpreter** | `.venv\Scripts\python.exe` |
| **Working directory** | Projekt-Root |
| **Environment variables** | `FLASK_DEBUG=True` |
| **Emulate terminal** | Nein |

---

## 📦 Installierte Pakete (71)

### Web-Framework
- Flask 3.0.3
- Flask-Login 0.6.3
- Flask-SQLAlchemy 3.1.1
- Flask-WTF 1.2.1
- Werkzeug 3.0.3
- Jinja2 3.1.6

### Datenbank
- SQLAlchemy 2.0.36+
- greenlet 3.2.4

### Formulare & Validierung
- WTForms 3.1.2
- email-validator 2.1.1

### Excel & Datenverarbeitung
- openpyxl 3.1.2
- pandas 2.3.3
- numpy 2.3.4
- xlrd 2.0.1

### PDF-Verarbeitung
- PyPDF2 3.0.1
- pdfplumber 0.10.3
- pdfminer.six 20221105
- pypdfium2 5.0.0

### Bildverarbeitung
- Pillow (via dependencies)

### Stickerei-spezifisch
- pyembroidery 1.5.1

### Sicherheit & Krypto
- cryptography 46.0.3
- cffi 2.0.0

### Utilities
- python-dotenv 1.0.1
- python-dateutil (via pandas)
- click 8.3.0
- blinker 1.9.0
- colorama 0.4.6
- charset-normalizer 3.4.4
- idna 3.11
- dnspython 2.8.0

### Server (Optional)
- gunicorn 22.0.0

---

## 🔧 Debugging in IntelliJ

### Debug-Modus starten

1. **Debug-Configuration verwenden:**
   - Run-Configuration `StitchAdmin 2.0` auswählen
   - Klick auf Debug-Button 🐞 (neben Play)
   - **ODER** Drücke `Shift + F9`

2. **Breakpoints setzen:**
   - Klick links neben die Zeilennummer
   - Roter Punkt erscheint

3. **Debug-Konsole nutzen:**
   - Variablen inspizieren
   - Expressions evaluieren
   - Call-Stack anzeigen

### Flask Debug-Modus

Der Flask Debug-Modus ist bereits aktiviert in der Run-Configuration:
```
FLASK_DEBUG=True
```

Features:
- ✅ Auto-Reload bei Code-Änderungen
- ✅ Detaillierte Fehlerseiten
- ✅ Interactive Debugger im Browser

---

## 🎨 IntelliJ IDEA Features für Flask

### Template-Unterstützung

✅ **Jinja2-Syntax-Highlighting**
✅ **Auto-Completion** für Template-Tags
✅ **Navigation** zu Template-Dateien (Ctrl+Click)
✅ **Template-Debugging**

### Code-Navigation

- **Ctrl + Click** auf Funktionen/Klassen → Springt zur Definition
- **Ctrl + Alt + Left/Right** → Navigation zurück/vor
- **Ctrl + N** → Klasse suchen
- **Ctrl + Shift + N** → Datei suchen
- **Ctrl + Shift + F** → In Dateien suchen

### Code-Completion

IntelliJ bietet intelligente Auto-Completion für:
- ✅ Flask-Funktionen
- ✅ SQLAlchemy-Models
- ✅ Jinja2-Template-Syntax
- ✅ WTForms-Felder
- ✅ Eigene Funktionen und Klassen

### Database Tools

1. **Database Tool Window öffnen:**
   - `View` → `Tool Windows` → `Database`

2. **SQLite-Datenbank verbinden:**
   - Klick auf `+` → `Data Source` → `SQLite`
   - **Pfad:** `instance/stitchadmin.db`
   - `Test Connection` → `OK`

3. **Datenbank durchsuchen:**
   - Tabellen anzeigen
   - SQL-Queries ausführen
   - Daten editieren

---

## 📁 Projekt-Struktur in IntelliJ

```
StitchAdmin2.0/
├── 📁 .idea/                     # IntelliJ IDEA Konfiguration
│   ├── runConfigurations/        # Run-Configurations
│   │   └── StitchAdmin_2_0.xml
│   ├── misc.xml                  # Python SDK Konfiguration
│   ├── StitchAdmin2.0.iml       # Modul-Konfiguration
│   └── workspace.xml             # Workspace-Einstellungen
│
├── 📁 .venv/                     # Virtual Environment (ausgegraut)
│   ├── Lib/
│   ├── Scripts/
│   │   └── python.exe
│   └── pyvenv.cfg
│
├── 📁 src/                       # Source-Ordner (BLAU markiert)
│   ├── 📁 controllers/           # Flask Blueprints
│   ├── 📁 models/                # SQLAlchemy Models
│   ├── 📁 templates/             # Jinja2 Templates
│   ├── 📁 static/                # CSS, JS, Images
│   ├── 📁 services/              # Business Logic
│   └── 📁 utils/                 # Hilfsfunktionen
│
├── 📁 instance/                  # Flask Instance (ausgegraut)
│   └── stitchadmin.db           # SQLite-Datenbank
│
├── 📄 app.py                     # ⭐ HAUPTDATEI
├── 📄 requirements.txt
└── 📄 README.md
```

### Ordner-Farben in IntelliJ:

- **BLAU** = Source Root (src/)
- **GRAU/AUSGEGRAUT** = Excluded (.venv, instance, logs)
- **NORMAL** = Regular Folders

---

## ⚡ Nützliche IntelliJ Shortcuts

### Allgemein
| Shortcut | Aktion |
|----------|--------|
| `Ctrl + Space` | Auto-Completion |
| `Ctrl + Q` | Quick Documentation |
| `Ctrl + P` | Parameter-Info |
| `Alt + Enter` | Quick Fix / Import |
| `Ctrl + Alt + L` | Code formatieren |

### Navigation
| Shortcut | Aktion |
|----------|--------|
| `Ctrl + N` | Klasse suchen |
| `Ctrl + Shift + N` | Datei suchen |
| `Ctrl + Shift + F` | In Dateien suchen |
| `Ctrl + B` | Gehe zu Definition |
| `Alt + F7` | Finde Verwendungen |

### Run & Debug
| Shortcut | Aktion |
|----------|--------|
| `Shift + F10` | Run |
| `Shift + F9` | Debug |
| `Ctrl + F2` | Stop |
| `F8` | Step Over (Debug) |
| `F7` | Step Into (Debug) |

### Terminal
| Shortcut | Aktion |
|----------|--------|
| `Alt + F12` | Terminal öffnen/schließen |

---

## 🔍 Troubleshooting

### Problem: "Python interpreter not configured"

**Lösung:**
1. `File` → `Project Structure` → `SDKs`
2. `+` → `Python SDK` → `Existing environment`
3. Wähle `.venv\Scripts\python.exe`

---

### Problem: "Module 'flask' not found"

**Lösung:**
```cmd
.venv\Scripts\activate
pip install -r requirements.txt
```

---

### Problem: Run-Configuration fehlt

**Lösung:**
1. `Run` → `Edit Configurations`
2. `+` → `Python`
3. Einstellungen:
   - Script: `app.py`
   - Python interpreter: `.venv\Scripts\python.exe`
   - Working directory: Projekt-Root
   - Environment: `FLASK_DEBUG=True`

---

### Problem: Port 5000 bereits belegt

**Lösung in app.py (Zeile 340):**
```python
# Ändere Port von 5000 auf z.B. 5001
app.run(host='0.0.0.0', port=5001, debug=app.config['DEBUG'])
```

---

### Problem: Templates nicht gefunden

**Lösung in .idea/StitchAdmin2.0.iml:**
Prüfe Template-Ordner:
```xml
<option name="TEMPLATE_FOLDERS">
  <list>
    <option value="$MODULE_DIR$/src/templates" />
  </list>
</option>
```

---

## 📚 Weitere Ressourcen

### IntelliJ IDEA Dokumentation
- [Flask Support](https://www.jetbrains.com/help/pycharm/flask.html)
- [Jinja2 Templates](https://www.jetbrains.com/help/pycharm/jinja2.html)
- [Database Tools](https://www.jetbrains.com/help/pycharm/database-tool-window.html)

### Projekt-Dokumentation
- `PROJEKT_STRUKTUR.md` - Vollständige Projekt-Übersicht
- `QUICKSTART.md` - Schnellstart-Anleitung
- `requirements.txt` - Dependencies

---

## ✅ Checkliste: Bereit zum Starten?

- [ ] IntelliJ IDEA installiert (oder PyCharm)
- [ ] Projekt geöffnet
- [ ] Python 3.13 Interpreter konfiguriert
- [ ] Virtual Environment (.venv) aktiviert
- [ ] Dependencies installiert (`pip list` zeigt 71 Pakete)
- [ ] Run-Configuration "StitchAdmin 2.0" vorhanden
- [ ] Datenbank erstellt (wird automatisch bei erstem Start)

**Wenn alle Punkte ✅ sind → Klick auf Play ▶️ und los geht's!**

---

**🚀 Viel Erfolg mit StitchAdmin 2.0 in IntelliJ IDEA!**

---

**Erstellt am:** 05.11.2025
**Für:** Hans Hahn
**Projekt:** StitchAdmin 2.0
