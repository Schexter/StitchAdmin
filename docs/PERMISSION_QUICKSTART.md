# 🚀 Permission-System - Quick Start

**5 Minuten Setup für das neue Permission-System & Dashboard**

---

## ⚡ Schnellinstallation

```bash
cd C:\SoftwareEntwicklung\StitchAdmin2.0
.venv\Scripts\activate

# 1. Tabellen erstellen
python scripts/setup_permissions.py

# 2. Module initialisieren
python scripts/init_modules.py

# 3. app.py automatisch updaten
python scripts/update_app_for_permissions.py

# 4. Server neu starten
start.bat
```

**Das war's!** 🎉

---

## 📱 Erste Schritte

### Als Admin

1. **Einloggen als admin/admin**

2. **Berechtigungen konfigurieren:**
   ```
   Dashboard → Einstellungen → Berechtigungsverwaltung
   ```
   
   Oder direkt: `http://localhost:5000/admin/permissions`

3. **User auswählen** und Berechtigungen setzen

4. **Schnell-Zuweisung nutzen** für schnelle Konfiguration

### Als User

1. **Einloggen**

2. **Dashboard anpassen:**
   - Klick auf "Dashboard anpassen"
   - Module per Drag & Drop verschieben
   - Module ein-/ausblenden mit 👁️ Symbol
   - Klick auf "Fertig" zum Speichern

---

## 🎯 Häufigste Anwendungsfälle

### Fall 1: Neuer Sticker-Mitarbeiter

```
Admin → Berechtigungen → User auswählen
→ Schnell-Zuweisung: "Alle: Ansehen + Bearbeiten"
→ Buchhaltung deaktivieren
→ Verwaltung deaktivieren
→ Speichern
```

### Fall 2: Verwaltungs-Mitarbeiter

```
Admin → Berechtigungen → User auswählen
→ CRM: Voll ✓
→ Kasse: Voll ✓
→ Buchhaltung: Voll ✓
→ Produktion: Nur ansehen ✓
→ Speichern
```

### Fall 3: Dashboard personalisieren

```
User → Dashboard
→ "Dashboard anpassen" klicken
→ Wichtigste Module nach oben ziehen
→ Unwichtige Module ausblenden
→ "Fertig" klicken
```

---

## 🔍 Troubleshooting

| Problem | Lösung |
|---------|--------|
| Tabelle nicht vorhanden | `python scripts/setup_permissions.py` |
| Module nicht sichtbar | `python scripts/init_modules.py` |
| Dashboard alt | Cache leeren: `Strg + Shift + R` |
| Blueprint-Fehler | `python scripts/update_app_for_permissions.py` |

---

## 📖 Vollständige Dokumentation

Für Details siehe: `docs/PERMISSION_SYSTEM.md`

---

**Version:** 2.0.2  
**Autor:** Hans Hahn
