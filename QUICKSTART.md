# StitchAdmin 2.0 - Quick Start Guide

**Von 0 auf produktiv in 10 Minuten! ⚡**

Erstellt von: **Hans Hahn** - Alle Rechte vorbehalten

---

## 🎯 Was du bekommst

- ✅ Vollständiges ERP-System für Stickerei-Betriebe
- ✅ Mobile Zugriff vom Smartphone
- ✅ Foto-Dokumentation mit Kamera
- ✅ OCR-Texterkennung für Rechnungen & Briefe
- ✅ Automatische Workflows

---

## 📦 Installation

### Linux/Ubuntu/Debian

```bash
# 1. Terminal öffnen
cd /pfad/zu/StitchAdmin2.0

# 2. Automatische Installation
sudo bash scripts/install_dependencies.sh

# 3. Server starten
python3 app.py

# 4. Browser öffnen
# http://localhost:5000
```

### Windows

```cmd
REM 1. CMD öffnen (als Administrator)
cd C:\pfad\zu\StitchAdmin2.0

REM 2. Tesseract OCR installieren
REM https://github.com/UB-Mannheim/tesseract/wiki
REM -> tesseract-ocr-w64-setup-5.x.x.exe herunterladen
REM -> Installieren mit "Deutsche Sprache" auswählen!

REM 3. Dependencies installieren
scripts\install_dependencies.bat

REM 4. Server starten
python app.py

REM 5. Browser öffnen
REM http://localhost:5000
```

---

## 🚀 Erste Schritte

### 1. Einloggen

**Standard-Zugangsdaten:**
- Benutzername: `admin`
- Passwort: `admin`

⚠️ **WICHTIG:** Passwort nach dem ersten Login ändern!

### 2. Grundeinstellungen konfigurieren

```
Menü → Einstellungen → Firma
```

**Pflichtfelder:**
- Firmenname
- Adresse
- Steuernummer
- Logo hochladen (optional)

### 3. Ersten Kunden anlegen

```
Menü → Kunden → Neu
```

**Mindestangaben:**
- Vorname & Nachname (oder Firma)
- Email oder Telefon
- Adresse

### 4. Ersten Auftrag erstellen

```
Menü → Aufträge → Neu
```

**Workflow:**
1. Kunde auswählen
2. Artikel hinzufügen
3. Liefertermin festlegen
4. Speichern

---

## 📱 Mobile Features nutzen

### IP-Adresse herausfinden

**Linux/macOS:**
```bash
hostname -I | awk '{print $1}'
# Beispiel-Ausgabe: 192.168.1.100
```

**Windows:**
```cmd
ipconfig | findstr IPv4
# Beispiel-Ausgabe: IPv4-Adresse . . . . . . . . . . : 192.168.1.100
```

### Vom Smartphone zugreifen

1. **Smartphone und PC im gleichen WLAN**
2. **Browser auf Smartphone öffnen**
3. **Eingeben:** `http://192.168.1.100:5000`
   (Ersetze die IP mit deiner tatsächlichen IP!)

### Fotos mit Smartphone aufnehmen

**Für Aufträge (Farben, Samples, QC):**
```
Im Browser: /orders/<AUFTRAG_ID>/photos
```

**Für Posteingang (mit OCR):**
```
Im Browser: /documents/post/<POST_ID>/scan
```

---

## 🎨 Workflow-Beispiel: Stickauftrag

### Start bis Versand in 6 Schritten

**1. Auftrag erstellen**
```
Aufträge → Neu → Kunde wählen → Artikel hinzufügen
```

**2. Design hochladen**
```
Auftrag öffnen → Design-Tab → DST-Datei hochladen
→ Stichzahl wird automatisch erkannt!
```

**3. Produktion starten**
```
Auftrag öffnen → Produktion → Maschine zuweisen → Starten
```

**4. Produktion abschließen + QC**
```
Produktion abschließen → Packliste wird automatisch erstellt
→ Mit Smartphone: QC-Fotos aufnehmen
→ QC bestätigen
```

**5. Verpacken**
```
Packliste → Als verpackt markieren
→ Lieferschein wird automatisch erstellt
→ Mit Smartphone: Versandlabel scannen
→ Tracking-Nummer wird automatisch erkannt!
```

**6. Rechnung erstellen**
```
Auftrag → Rechnung erstellen → PDF generieren → Email senden
```

**Fertig! 🎉**

---

## 🔍 OCR-Features testen

### Rechnung scannen

1. **PostEntry erstellen:**
   ```
   Dokumente → Postbuch → Neu → Typ: "Eingehend"
   ```

2. **Mit Smartphone öffnen:**
   ```
   /documents/post/<ID>/scan
   ```

3. **Rechnung fotografieren:**
   - Kamera-Button drücken
   - Rechnung fotografieren
   - Upload bestätigen

4. **Automatisch erkannt:**
   - ✅ Rechnungsbetrag
   - ✅ Rechnungsnummer
   - ✅ Rechnungsdatum
   - ✅ Volltext für Suche

### Paket-Tracking scannen

1. **PostEntry für Versand erstellen**

2. **DHL-Label fotografieren:**
   - Tracking-Nummer wird automatisch erkannt
   - Versandkosten werden extrahiert
   - Felder werden automatisch ausgefüllt

---

## ⚙️ Wichtige Einstellungen

### Workflows automatisieren

```
Einstellungen → Workflows
```

**Empfohlene Einstellungen:**
- ✅ Packliste nach Produktion automatisch erstellen
- ✅ Lieferschein nach Verpackung automatisch erstellen
- ✅ Tracking-Email automatisch senden
- ✅ OCR bei Upload aktivieren

### Firmen-Branding

```
Einstellungen → Branding
```

**Anpassen:**
- Logo hochladen
- Farben anpassen
- Email-Signatur
- PDF-Layout

---

## 🆘 Häufige Probleme

### Server nicht erreichbar

**Problem:** `Connection refused` vom Smartphone

**Lösung:**
```bash
# 1. Firewall-Port öffnen (Linux)
sudo ufw allow 5000

# 2. Windows: Firewall-Regel hinzufügen
# Systemsteuerung → Firewall → Neue Regel → Port 5000 zulassen
```

### OCR erkennt nichts

**Problem:** Leerer Text nach Scan

**Lösung:**
- ✅ Bessere Beleuchtung beim Fotografieren
- ✅ Dokument glatt legen (keine Falten)
- ✅ Kamera stabilisieren (nicht verwackeln)
- ✅ Höhere Auflösung verwenden
- ✅ Tesseract korrekt installiert? `tesseract --version`

### Fotos werden nicht hochgeladen

**Problem:** Upload schlägt fehl

**Lösung:**
```bash
# Upload-Ordner erstellen
mkdir -p instance/uploads/photos
mkdir -p instance/uploads/thumbnails
chmod -R 755 instance/uploads
```

### Python-Fehler beim Start

**Problem:** `ModuleNotFoundError`

**Lösung:**
```bash
# Dependencies neu installieren
pip install -r requirements.txt

# Oder Installations-Skript verwenden
sudo bash scripts/install_dependencies.sh
```

---

## 📚 Nächste Schritte

**Nach dem Quick Start:**

1. **Dokumentation lesen:**
   - [INSTALLATION.md](INSTALLATION.md) - Detaillierte Installation
   - [MOBILE_WORKFLOW_FEATURES.md](docs/MOBILE_WORKFLOW_FEATURES.md) - Mobile Features
   - [POSTENTRY_OCR_FEATURES.md](docs/POSTENTRY_OCR_FEATURES.md) - OCR-Features

2. **Daten importieren:**
   - Kunden aus Excel importieren
   - Artikel aus L-Shop importieren
   - Garnfarben hochladen

3. **Team einrichten:**
   - Benutzer anlegen
   - Rollen vergeben
   - Rechte anpassen

4. **Backup einrichten:**
   ```bash
   # Automatisches Backup einrichten
   cp scripts/backup.sh /etc/cron.daily/
   ```

5. **Produktion vorbereiten:**
   - Für SSL/TLS konfigurieren
   - Reverse Proxy einrichten (Nginx)
   - Systemd Service erstellen

---

## 💡 Tipps & Tricks

### Tastatur-Shortcuts

- `Strg + S` - Speichern (in Formularen)
- `Strg + N` - Neu (auf Listen-Seiten)
- `Strg + F` - Suche

### Mobile-Optimierung

- **Kamera-Qualität:** Für OCR reichen 5MP
- **Beleuchtung:** Tageslicht oder LED (kein Blitz)
- **Hintergrund:** Dunkler Untergrund für bessere Kontraste

### Performance

- **Datenbank:** Für >1000 Aufträge PostgreSQL verwenden
- **Uploads:** Alte Fotos regelmäßig archivieren
- **Cache:** Browser-Cache leeren bei Problemen

---

## 🎉 Geschafft!

Du bist jetzt bereit, StitchAdmin 2.0 produktiv zu nutzen!

**Viel Erfolg mit deinem Stickerei-Betrieb! 🧵✨**

---

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**
