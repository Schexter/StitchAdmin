# StitchAdmin 2.0 - Migration Guide

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**

## Übersicht

Dieser Guide beschreibt die Migration von StitchAdmin 1.x zu StitchAdmin 2.0 mit verbesserter Projektstruktur.

## Neue Struktur

```
StitchAdmin2.0/
├── app.py                      # Haupt-Anwendung (neu strukturiert)
├── requirements.txt            # Python-Abhängigkeiten
├── .env                        # Umgebungsvariablen
│
├── src/                        # Quellcode
│   ├── models/                 # Datenbank-Models
│   ├── controllers/            # Business Logic & Routes
│   ├── services/               # Geschäftslogik-Services
│   ├── utils/                  # Hilfsfunktionen
│   ├── templates/              # Jinja2 Templates
│   └── static/                 # CSS, JS, Bilder
│
├── instance/                   # Datenbank & Uploads
│   ├── stitchadmin.db         # SQLite Datenbank
│   └── uploads/               # Hochgeladene Dateien
│       ├── designs/           # Design-Dateien (DST, etc.)
│       ├── documents/         # PDF-Dokumente
│       └── images/            # Bilder
│
├── config/                     # Konfigurationsdateien
├── scripts/                    # Hilfsskripte
├── tests/                      # Unit Tests
├── docs/                       # Dokumentation
├── logs/                       # Log-Dateien
└── backups/                    # Datenbank-Backups
```

## Migration durchführen

### Schritt 1: Migration vorbereiten

**WICHTIG:** Erstelle ein Backup des alten Systems!

```powershell
# Backup erstellen
Copy-Item "C:\SoftwareEntwicklung\StitchAdmin\instance" `
          "C:\SoftwareEntwicklung\StitchAdmin\BACKUP_$(Get-Date -Format 'yyyyMMdd_HHmmss')" `
          -Recurse
```

### Schritt 2: Migration ausführen

```powershell
# Wechsle ins neue Verzeichnis
cd C:\SoftwareEntwicklung\StitchAdmin2.0

# Führe Migrations-Script aus
.\scripts\migrate_from_old.ps1
```

Das Script kopiert automatisch:
- ✅ Konfigurationsdateien (.env, requirements)
- ✅ Models (Datenbank-Struktur)
- ✅ Controllers (alle _db.py Versionen)
- ✅ Services & Utils
- ✅ Templates & Static Files
- ✅ Datenbank & Upload-Dateien
- ✅ Wichtige Dokumentation

### Schritt 3: Virtual Environment einrichten

```powershell
# Erstelle Virtual Environment
python -m venv .venv

# Aktiviere Virtual Environment
.\.venv\Scripts\Activate.ps1

# Installiere Abhängigkeiten
pip install -r requirements.txt
```

### Schritt 4: Anwendung starten

```powershell
# Starte StitchAdmin 2.0
python app.py
```

Die Anwendung läuft dann auf: **http://localhost:5000**

Standard-Login: **admin / admin**

## Was ist neu in 2.0?

### Verbesserte Architektur
- ✨ Klarere Projektstruktur
- 🔧 Modernisierte app.py mit Application Factory Pattern
- 📦 Bessere Trennung von Code und Daten
- 🛡️ Verbesserte Fehlerbehandlung

### Aufgeräumte Codebasis
- 🧹 Nur noch _db.py Controller (funktionierende Versionen)
- 📝 Konsistente Blueprint-Registrierung
- 🔒 Verbessertes Auth-System
- 📊 Zentralisiertes Error-Handling

### Neue Features (geplant)
- 🎨 Modernes UI-Design
- 📱 Responsive Design
- 🔔 Benachrichtigungssystem
- 📈 Erweiterte Reports

## Wichtige Änderungen

### Controller-Konsolidierung
- Alte doppelte Controller entfernt (z.B. `customer_controller.py`)
- Nur noch `*_controller_db.py` Versionen im Einsatz
- Konsistente Namensgebung

### Blueprint-Struktur
- Auth-Blueprint integriert (Login/Logout)
- Sichere Blueprint-Registrierung mit Fehlerbehandlung
- Alle Module optional ladbar

### Konfiguration
- `.env` für Umgebungsvariablen
- Zentralisierte App-Konfiguration in `app.py`
- Einfachere Anpassung für Produktion

## Troubleshooting

### Problem: Module nicht gefunden
```
❌ FEHLER beim Importieren der Models
```

**Lösung:** Prüfe ob alle Dateien korrekt kopiert wurden:
```powershell
dir C:\SoftwareEntwicklung\StitchAdmin2.0\src\models
```

### Problem: Datenbank-Fehler
```
❌ Fehler beim Laden der Dashboard-Statistiken
```

**Lösung:** Führe Datenbank-Migration aus:
```powershell
python scripts\db_migration.py
```

### Problem: Template nicht gefunden
```
❌ Template 'dashboard.html' nicht gefunden
```

**Lösung:** Prüfe Template-Pfade:
```powershell
dir C:\SoftwareEntwicklung\StitchAdmin2.0\src\templates
```

## Weitere Schritte

Nach erfolgreicher Migration:

1. **Teste alle Module**
   - Kunden ✓
   - Artikel ✓
   - Aufträge ✓
   - Maschinen ✓
   - Garne ✓
   - Produktion ✓
   - Kassensystem ✓

2. **Erstelle neuen Admin-User**
   ```python
   # Falls benötigt, erstelle einen neuen Admin
   python
   >>> from app import create_app
   >>> from src.models import db, User
   >>> app = create_app()
   >>> with app.app_context():
   ...     user = User(username='neuer_admin', email='admin@firma.de', is_admin=True)
   ...     user.set_password('sicheres_passwort')
   ...     db.session.add(user)
   ...     db.session.commit()
   ```

3. **Passe Konfiguration an**
   - Ändere `SECRET_KEY` in `.env`
   - Konfiguriere Backup-Pfade
   - Setze Produktions-Einstellungen

4. **Dokumentiere Änderungen**
   - Aktualisiere `docs/CHANGELOG.md`
   - Dokumentiere Custom-Anpassungen
   - Erstelle User-Guide

## Support

Bei Problemen oder Fragen:
1. Prüfe `logs/` Verzeichnis
2. Konsultiere `docs/` Dokumentation
3. Checke alte Protokolle in `docs/`

## Nächste Entwicklungsschritte

Siehe: `docs/TODO_FAHRPLAN.md`

---

**Stand:** 2025-11-05
**Version:** 2.0.0
**Status:** Migration abgeschlossen, Tests ausstehend
