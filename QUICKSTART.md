# StitchAdmin 2.0 - Quick Start Guide

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**

---

## ✅ Migration erfolgreich abgeschlossen!

Alle Dateien wurden erfolgreich von `StitchAdmin` nach `StitchAdmin2.0` migriert.

---

## 🚀 Schnellstart (5 Schritte)

### Schritt 1: Virtual Environment erstellen
```bash
cd C:\SoftwareEntwicklung\StitchAdmin2.0
python -m venv .venv
```

### Schritt 2: Virtual Environment aktivieren
```bash
.venv\Scripts\activate
```

### Schritt 3: Requirements installieren
```bash
pip install -r requirements.txt
```

### Schritt 4: Anwendung starten
```bash
python app.py
```

### Schritt 5: Im Browser öffnen
```
http://localhost:5000
```

**Login-Daten:**
- Benutzername: `admin`
- Passwort: `admin`

---

## 📋 Was wurde migriert?

✅ **Models** - Alle Datenmodelle  
✅ **Controllers** - Alle Controller inkl. Rechnungsmodul  
✅ **Services** - Business-Services  
✅ **Utils** - Hilfsfunktionen  
✅ **Templates** - Alle HTML-Templates  
✅ **Static Files** - CSS, JS, Images  
✅ **Datenbank** - SQLite DB + Backup  
✅ **Uploads** - Design-Dateien, Dokumente, Bilder  

---

## 📁 Neue Struktur

```
StitchAdmin2.0/
├── app.py                    # Haupt-Anwendung
├── requirements.txt
├── .env
│
├── src/
│   ├── controllers/          # Geschäftslogik
│   ├── models/              # Datenmodelle
│   ├── services/            # Business-Services
│   ├── utils/               # Hilfsfunktionen
│   ├── templates/           # HTML-Templates
│   └── static/              # CSS, JS, Images
│
├── instance/
│   ├── stitchadmin.db       # Datenbank
│   └── uploads/             # Upload-Dateien
│
├── backups/                 # DB-Backups
├── config/                  # Konfiguration
├── docs/                    # Dokumentation
├── logs/                    # Logs
├── scripts/                 # Hilfsskripte
└── tests/                   # Tests (leer)
```

---

## ⚠️ Bekannte Punkte

### Import-Anpassungen erforderlich
Die Controller müssen ihre Imports eventuell anpassen:

**Alt (in den Controller-Dateien):**
```python
from models.models import Customer
from utils.logger import log_activity
```

**Neu (sollte sein):**
```python
from src.models.models import Customer
from src.utils.logger import log_activity
```

Die `app.py` importiert jetzt mit `src.` Präfix, aber die Controller-Dateien selbst könnten noch alte Imports haben.

### Erste Schritte nach dem Start:

1. **Prüfen, welche Module geladen wurden**  
   Beim Start zeigt die Konsole an, welche Blueprints erfolgreich registriert wurden.

2. **Dashboard testen**  
   Nach Login sollte das Dashboard mit Statistiken angezeigt werden.

3. **Module einzeln testen**  
   - Kunden → Funktioniert?
   - Artikel → Funktioniert?
   - Aufträge → Funktioniert?
   - etc.

---

## 🔧 Fehlerbehebung

### Fehler: "Module not found"
**Lösung:** Imports in den Controller-Dateien anpassen (siehe oben)

### Fehler: "Database locked"
**Lösung:** SQLite-DB im alten Verzeichnis könnte noch geöffnet sein. Schließen Sie alle Instanzen der alten Anwendung.

### Fehler: "Template not found"
**Lösung:** Template-Pfade prüfen - sollten relativ zu `src/templates/` sein

### Blueprints laden nicht
**Lösung:** 
1. Debug-Modus aktivieren (bereits aktiv)
2. Traceback in der Konsole ansehen
3. Imports im jeweiligen Controller prüfen

---

## 📚 Dokumentation

Weitere Informationen in:
- `docs/MIGRATION_COMPLETE.md` - Vollständiger Migrations-Bericht
- `docs/MIGRATION_GUIDE.md` - Migrations-Anleitung
- `docs/README_OLD.md` - Alte README als Referenz
- `app_old_reference.py` - Alte app.py als Vergleich

---

## 🔒 Backup-Hinweis

⚠️ **Wichtig:** Das alte Verzeichnis `C:\SoftwareEntwicklung\StitchAdmin` wurde **nicht gelöscht**.

Es dient als Backup und Referenz. Bitte erst löschen, wenn die Migration vollständig getestet wurde!

---

## 📞 Support

Bei Problemen:
1. Konsolen-Output prüfen
2. Debug-Modus ist aktiv - Fehler werden detailliert angezeigt
3. Alte Dateien im Original-Verzeichnis als Referenz nutzen

---

## ✨ Viel Erfolg!

Die Migration ist abgeschlossen. Alle Komponenten sind an ihrem Platz.  
Jetzt kann die Entwicklung in der neuen, sauberen Struktur weitergehen!

**Nächster Schritt:** Virtual Environment einrichten und die Anwendung starten! 🚀

---

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Datum:** 05.11.2025
