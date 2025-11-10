# Quick-Start Guide: Sprint 1 Tag 1

**Montag, 11. November 2025**  
**Erstellt von Hans Hahn - Alle Rechte vorbehalten**

---

## ⏰ Zeitplan für heute (8 Stunden)

```
09:00-09:30  ☕ Vorbereitung & Setup
09:30-12:00  🗑️  Legacy-Controller löschen (Teil 1)
12:00-13:00  🍽️  Mittagspause
13:00-16:00  🗑️  Legacy-Controller löschen (Teil 2)
16:00-17:00  ✅ Tests & Abschluss
```

---

## 🎯 Ziel heute

**10 Legacy-Controller-Dateien löschen**

Jede Datei einzeln:
1. Löschen
2. App testen
3. Commit machen
4. Weiter zur nächsten

---

## 📋 Step-by-Step Anleitung

### Schritt 1: Vorbereitung (09:00-09:30)

#### Terminal öffnen & ins Projektverzeichnis
```bash
cd C:\SoftwareEntwicklung\StitchAdmin2.0
```

#### Virtual Environment aktivieren
```bash
.venv\Scripts\activate
```

#### Git-Status prüfen
```bash
git status
git pull  # Falls es Updates gibt
```

#### Backup erstellen
```bash
mkdir backups\pre_cleanup_20251111
xcopy src\controllers backups\pre_cleanup_20251111\controllers\ /E /I
```

#### Neuen Branch erstellen
```bash
git checkout -b sprint-1/cleanup
```

✅ **Checkpoint:** Du bist jetzt auf Branch `sprint-1/cleanup`

---

### Schritt 2: Legacy-Controller löschen (09:30-12:00)

**WICHTIG:** Nach JEDER Löschung testen!

#### Controller 1: customer_controller.py

```bash
# Löschen
del src\controllers\customer_controller.py

# App testen
python app.py
# → App sollte starten ohne Fehler
# → Drücke Ctrl+C zum Stoppen

# Commit
git add -A
git commit -m "refactor: remove legacy customer_controller.py (JSON-based)"
```

✅ **Funktioniert?** Weiter zu Controller 2!  
❌ **Fehler?** Siehe Troubleshooting unten

---

#### Controller 2: article_controller.py

```bash
del src\controllers\article_controller.py
python app.py  # Test
git add -A
git commit -m "refactor: remove legacy article_controller.py (JSON-based)"
```

---

#### Controller 3: order_controller.py

```bash
del src\controllers\order_controller.py
python app.py  # Test
git add -A
git commit -m "refactor: remove legacy order_controller.py (JSON-based)"
```

---

#### Controller 4: machine_controller.py

```bash
del src\controllers\machine_controller.py
python app.py  # Test
git add -A
git commit -m "refactor: remove legacy machine_controller.py (JSON-based)"
```

---

#### Controller 5: thread_controller.py

```bash
del src\controllers\thread_controller.py
python app.py  # Test
git add -A
git commit -m "refactor: remove legacy thread_controller.py (JSON-based)"
```

---

### 🍽️ Mittagspause (12:00-13:00)

✅ **5 von 10 Controllern gelöscht!**  
Pause verdient! 🎉

---

### Schritt 3: Restliche Controller (13:00-16:00)

#### Controller 6: production_controller.py

```bash
del src\controllers\production_controller.py
python app.py  # Test
git add -A
git commit -m "refactor: remove legacy production_controller.py (JSON-based)"
```

---

#### Controller 7: shipping_controller.py

```bash
del src\controllers\shipping_controller.py
python app.py  # Test
git add -A
git commit -m "refactor: remove legacy shipping_controller.py (JSON-based)"
```

---

#### Controller 8: supplier_controller.py

```bash
del src\controllers\supplier_controller.py
python app.py  # Test
git add -A
git commit -m "refactor: remove legacy supplier_controller.py (JSON-based)"
```

---

#### Controller 9: settings_controller.py

```bash
del src\controllers\settings_controller.py
python app.py  # Test
git add -A
git commit -m "refactor: remove legacy settings_controller.py (JSON-based)"
```

---

#### Controller 10: settings_controller_db.py

```bash
# Dieser wird auch gelöscht, da wir settings_controller_unified.py haben
del src\controllers\settings_controller_db.py
python app.py  # Test
git add -A
git commit -m "refactor: remove settings_controller_db.py (superseded by unified)"
```

---

### Schritt 4: Finale Tests (16:00-16:30)

#### Kompletten Funktionstest durchführen

```bash
# App starten
python app.py
```

**Im Browser testen:**
1. ✅ http://localhost:5000 → Login funktioniert?
2. ✅ Dashboard wird angezeigt?
3. ✅ Kunden-Liste öffnen → Funktioniert?
4. ✅ Artikel-Liste öffnen → Funktioniert?
5. ✅ Auftrags-Liste öffnen → Funktioniert?

**Alle funktionieren?** ✅ Perfekt!  
**Fehler?** Siehe Troubleshooting

---

### Schritt 5: Push & Dokumentation (16:30-17:00)

#### Git push
```bash
git push origin sprint-1/cleanup
```

#### CHANGELOG.md updaten
```bash
notepad CHANGELOG.md
```

**Hinzufügen:**
```markdown
## [Datum: 2025-11-11]
### Durchgeführt:
- Legacy-Controller entfernt (10 Dateien)
- JSON-basierte Controller gelöscht
- Git-Branch: sprint-1/cleanup erstellt

### Funktioniert:
- Alle DB-basierten Controller arbeiten
- App startet ohne Fehler
- Alle Hauptfunktionen getestet

### Nächste Schritte:
- Doppelte Controller konsolidieren (Dienstag)
- Code-Review & Refactoring (Mittwoch)
```

#### TODO.md updaten
```bash
notepad TODO.md
```

**Abhaken:**
```markdown
- [x] customer_controller.py (JSON-basiert) → Gelöscht ✅
- [x] article_controller.py (JSON-basiert) → Gelöscht ✅
- [x] order_controller.py (JSON-basiert) → Gelöscht ✅
- [x] machine_controller.py (JSON-basiert) → Gelöscht ✅
- [x] thread_controller.py (JSON-basiert) → Gelöscht ✅
- [x] production_controller.py (JSON-basiert) → Gelöscht ✅
- [x] shipping_controller.py (JSON-basiert) → Gelöscht ✅
- [x] supplier_controller.py (JSON-basiert) → Gelöscht ✅
- [x] settings_controller.py (JSON-basiert) → Gelöscht ✅
- [x] settings_controller_db.py → Gelöscht ✅
```

---

## 🎉 Feierabend!

**Geschafft heute:**
- ✅ 10 Legacy-Controller gelöscht
- ✅ 10 Git-Commits gemacht
- ✅ App funktioniert weiterhin
- ✅ CHANGELOG & TODO aktualisiert
- ✅ Branch gepusht

**Morgen (Dienstag):**
- Doppelte Controller konsolidieren
- Thread-Controller mergen
- Settings-Controller aufräumen

---

## 🆘 Troubleshooting

### Problem: App startet nicht nach Löschen

**Fehlermeldung:** `ImportError: No module named 'src.controllers.customer_controller'`

**Lösung:**
```bash
# Prüfe app.py - Blueprint-Registrierung
notepad app.py

# Suche nach:
# from src.controllers.customer_controller import customer_bp
# Diese Zeile sollte NICHT mehr da sein!
# Falls doch: Löschen und speichern
```

---

### Problem: "Blueprint already registered"

**Fehlermeldung:** `AssertionError: A blueprint with the name 'customer' is already registered`

**Ursache:** Doppelte Blueprint-Registrierung in app.py

**Lösung:**
```bash
# app.py öffnen
notepad app.py

# Suche nach doppelten Zeilen wie:
# app.register_blueprint(customer_bp)
# app.register_blueprint(customer_bp)  ← Duplikat!

# Eine löschen, speichern
```

---

### Problem: Seite zeigt 404-Fehler

**Symptom:** Route `/customers` nicht gefunden

**Ursache:** Blueprint nicht korrekt registriert

**Lösung:**
```python
# Prüfe in app.py:
from src.controllers.customer_controller_db import customer_bp
app.register_blueprint(customer_bp)

# URL-Prefix prüfen im Controller:
customer_bp = Blueprint('customers', __name__, url_prefix='/customers')
```

---

### Problem: Datenbank-Fehler

**Fehlermeldung:** `sqlalchemy.exc.OperationalError: no such table`

**Lösung:**
```bash
# Datenbank neu initialisieren
python
>>> from app import create_app
>>> from src.models.models import db
>>> app = create_app()
>>> with app.app_context():
...     db.create_all()
>>> exit()

# App neu starten
python app.py
```

---

## 📞 Notfall-Kontakte

### Falls gar nichts funktioniert

**Option 1: Backup wiederherstellen**
```bash
# Zum Main-Branch zurück
git checkout main

# Oder: Backup-Dateien zurückkopieren
xcopy backups\pre_cleanup_20251111\controllers\*.* src\controllers\ /E /Y
```

**Option 2: Branch verwerfen und neu starten**
```bash
git checkout main
git branch -D sprint-1/cleanup
# Morgen nochmal versuchen
```

---

## ✅ End-of-Day Checklist

- [ ] Alle 10 Controller gelöscht
- [ ] App startet ohne Fehler
- [ ] Hauptfunktionen getestet (Login, Dashboard, Listen)
- [ ] 10 Git-Commits gemacht
- [ ] Branch gepusht (sprint-1/cleanup)
- [ ] CHANGELOG.md aktualisiert
- [ ] TODO.md aktualisiert
- [ ] Plan für morgen erstellt

**Alles erledigt?** 🎉 **SUPER GEMACHT!**

---

## 📝 Notizen für morgen

**Was lief gut:**
- (hier notieren)

**Was war schwierig:**
- (hier notieren)

**Ideen/Verbesserungen:**
- (hier notieren)

---

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Viel Erfolg heute!** 💪🚀
