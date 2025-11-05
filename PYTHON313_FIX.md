# 🔧 Python 3.13 Kompatibilitätsproblem - GELÖST

**Problem:** SQLAlchemy 2.0.30 ist nicht kompatibel mit Python 3.13

## ✅ Schnelle Lösung

### Option 1: Automatisches Fix-Script (EMPFOHLEN)

**Einfach Doppelklick auf:**
```
fix_sqlalchemy.bat
```

Das Script:
1. Aktiviert das Virtual Environment
2. Upgraded SQLAlchemy auf Version ≥ 2.0.36
3. Zeigt die installierte Version an

**Danach:**
```
start.bat
```

---

### Option 2: Manuell

```bash
cd C:\SoftwareEntwicklung\StitchAdmin2.0

# Virtual Environment aktivieren
.venv\Scripts\activate

# SQLAlchemy upgraden
pip install --upgrade "SQLAlchemy>=2.0.36"

# Anwendung starten
python app.py
```

---

## 🔍 Was war das Problem?

**Fehler:**
```
TypeError: Can't replace canonical symbol for '__firstlineno__' with new int value 615
```

**Ursache:**
- Python 3.13 hat neue interne Strukturen
- SQLAlchemy 2.0.30 nutzt veraltete Mechanismen
- SQLAlchemy ≥ 2.0.36 behebt dieses Problem

---

## ✅ Nach dem Fix

Die Anwendung sollte starten mit:
```
✅ Datenbank-Models erfolgreich importiert
✅ Custom Template-Filters registriert
✅ Kunden Blueprint registriert
✅ Artikel Blueprint registriert
... (weitere Blueprints)

🚀 StitchAdmin 2.0 gestartet!
📍 URL: http://localhost:5000
👤 Login: admin / admin
```

---

## 🎯 Zusammenfassung

1. **fix_sqlalchemy.bat** ausführen
2. Warten bis Update abgeschlossen
3. **start.bat** ausführen
4. Im Browser öffnen: http://localhost:5000

Fertig! 🎉

---

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**
