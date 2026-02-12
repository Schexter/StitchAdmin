# PostEntry Foto-Dokumentation & OCR

**Erstellt von: Hans Hahn - Alle Rechte vorbehalten**
**Datum:** 25. November 2025
**Version:** 1.0

---

## Überblick

Diese Erweiterung ermöglicht:
- **Mobile Dokument-Erfassung** via Smartphone-Kamera
- **OCR-Texterkennung** für Briefe und Rechnungen
- **Smart-Extraction** von Beträgen, Datum, Tracking-Nummern
- **Automatisches Ausfüllen** von PostEntry-Feldern

---

## Implementierte Features

### 1. PostEntry Model - Neue Felder

**Erweiterte Felder:**
```python
# PostEntry.photos - JSON Array
photos = db.Column(db.Text)
# Struktur: [{"path": "...", "type": "invoice|letter|package|other", "description": "...", "timestamp": "..."}]

# PostEntry.ocr_text - Volltext aus OCR
ocr_text = db.Column(db.Text)

# PostEntry.extracted_data - Smart-extrahierte Daten
extracted_data = db.Column(db.Text)
# Struktur: {"amount": 123.45, "date": "2025-11-25", "tracking": "...", "reference": "..."}
```

**Helper-Methoden:**
- `post_entry.get_photos()` - Alle Fotos abrufen
- `post_entry.add_photo(path, type, description)` - Foto hinzufügen
- `post_entry.remove_photo(path)` - Foto löschen
- `post_entry.get_extracted_data()` - Extrahierte Daten als Dict
- `post_entry.update_extracted_data(dict)` - Daten aktualisieren
- `post_entry.set_ocr_text(text)` - OCR-Text setzen

### 2. OCR Service (`src/services/ocr_service.py`)

**Features:**
- **Tesseract OCR Integration** für Texterkennung
- **Deutsch & Englisch** Sprachunterstützung
- **Bildvorverarbeitung** (Grayscale) für bessere Erkennung
- **Smart-Extraction** mit Regex-Patterns

**Unterstützte Extraktion:**

#### Beträge (Geldbeträge)
```python
# Erkennt:
- €123.45 oder € 123.45
- 123,45 € oder 123.45 EUR
- Summe: 123,45
- Gesamt: 123,45
- Rechnungsbetrag: 123,45
```

#### Datumsangaben
```python
# Erkennt:
- 25.11.2025 (DD.MM.YYYY)
- 25/11/2025 (DD/MM/YYYY)
- 2025-11-25 (ISO)
- 25. November 2025 (mit Monatsnamen)
```

#### Tracking-Nummern
```python
# Unterstützte Carrier:
- DHL: 12/20 Ziffern, JJD-Format
- DPD: 14 Ziffern
- UPS: 1Z Format
- Hermes: 16 Ziffern
- GLS: 11 Ziffern
- FedEx: 12/15 Ziffern
```

#### Referenznummern
```python
# Erkennt:
- Rechnung-Nr.: RE-2025-001
- Kunden-Nr.: K-12345
- Auftrag-Nr.: ORDER-123
- Liefer-Nr.: LS-2025-001
```

**Verwendung:**
```python
from src.services.ocr_service import OCRService

# OCR durchführen
ocr = OCRService()
result = ocr.process_document('path/to/scan.jpg', lang='deu')

# Ergebnis:
{
    'text': 'Vollständiger erkannter Text...',
    'extracted_data': {
        'amounts': [123.45, 10.00],
        'primary_amount': 123.45,
        'dates': ['2025-11-25T00:00:00'],
        'primary_date': '2025-11-25T00:00:00',
        'tracking': {'dhl': ['JJD123456789012345']},
        'primary_tracking': 'JJD123456789012345',
        'references': {'Rechnung-Nr.': 'RE-2025-001'}
    }
}
```

### 3. API-Endpunkte

#### Upload mit OCR
```http
POST /api/photos/upload/post-entry/<post_entry_id>
Content-Type: application/json

{
    "photo": "data:image/jpeg;base64,...",
    "type": "invoice",
    "description": "Rechnung DHL",
    "ocr_enabled": true
}

Response:
{
    "success": true,
    "message": "Foto erfolgreich hochgeladen",
    "photo": {
        "path": "photos/post_entry_123_abc.jpg",
        "type": "invoice",
        "url": "/uploads/photos/...",
        "thumbnail_url": "/uploads/thumbnails/..."
    },
    "ocr": {
        "text": "Erkannter Text...",
        "extracted_data": {
            "primary_amount": 123.45,
            "primary_tracking": "JJD...",
            ...
        }
    }
}
```

#### Fotos abrufen
```http
GET /api/photos/post-entry/<post_entry_id>/photos

Response:
{
    "success": true,
    "photos": [...],
    "ocr_text": "Vollständiger OCR-Text",
    "extracted_data": {...}
}
```

#### Foto löschen
```http
DELETE /api/photos/delete/post-entry/<post_entry_id>/<photo_path>

Response:
{
    "success": true,
    "message": "Foto erfolgreich gelöscht"
}
```

### 4. Auto-Fill Features

**Automatisches Ausfüllen beim Upload:**

Wenn OCR aktiviert ist und Daten erkannt werden, werden PostEntry-Felder automatisch ausgefüllt:

```python
# Tracking-Nummer (wenn leer)
if 'primary_tracking' in extracted_data and not post_entry.tracking_number:
    post_entry.tracking_number = extracted_data['primary_tracking']

# Versandkosten (wenn leer)
if 'primary_amount' in extracted_data and not post_entry.shipping_cost:
    post_entry.shipping_cost = extracted_data['primary_amount']
```

Dies spart Zeit beim manuellen Eintippen von Tracking-Nummern und Beträgen!

### 5. Mobile Template (`src/templates/documents/post_scan.html`)

**Features:**
- **Kamera-Integration** über camera-upload.js
- **Live OCR-Status** während Verarbeitung
- **Ergebnis-Anzeige** der erkannten Daten
- **Foto-Galerie** aller hochgeladenen Dokumente
- **Touch-optimiert** für Smartphone-Nutzung

**Zugriff:**
```
http://your-server:5000/documents/post/<POST_ENTRY_ID>/scan
```

---

## Installation & Setup

### 1. Tesseract OCR installieren

**Windows:**
```bash
# Download von: https://github.com/UB-Mannheim/tesseract/wiki
# Installieren und Pfad merken (z.B. C:\Program Files\Tesseract-OCR\tesseract.exe)
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-deu
```

**macOS:**
```bash
brew install tesseract tesseract-lang
```

### 2. Python-Packages installieren

```bash
pip install pytesseract pillow
```

### 3. Tesseract-Pfad konfigurieren (optional)

Wenn Tesseract nicht im PATH ist:

```python
# In src/services/ocr_service.py oder app.py
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

### 4. Migration ausführen

```bash
python3 scripts/add_post_entry_photos_fields.py
```

---

## Verwendung

### Workflow: Brief/Rechnung scannen

1. **PostEntry öffnen** im Browser
2. **Scan-Button** klicken oder `/documents/post/<ID>/scan` aufrufen
3. **Dokument fotografieren** mit Smartphone-Kamera
4. **OCR läuft automatisch** - erkannte Daten werden angezeigt
5. **Felder werden ausgefüllt** (Tracking, Betrag, etc.)
6. **Fertig!** Text ist gespeichert, Daten extrahiert

### Beispiel: Paket-Eingang erfassen

1. DHL-Lieferschein mit Smartphone scannen
2. **Tracking-Nummer** wird automatisch erkannt
3. **Versandkosten** werden extrahiert
4. **Datum** wird erkannt
5. Alles wird in PostEntry gespeichert

### Beispiel: Rechnung archivieren

1. Rechnung vom Lieferanten scannen
2. **Rechnungsnummer** wird erkannt
3. **Betrag** wird extrahiert
4. **Rechnungsdatum** wird erkannt
5. Volltext wird für Suche gespeichert

---

## Konfiguration

### OCR aktivieren/deaktivieren

```python
# Beim Upload:
data = {
    'photo': base64_image,
    'ocr_enabled': True  # oder False
}
```

### Sprache ändern

```python
# Deutsch (Standard)
ocr_result = ocr_service.process_document(image_path, lang='deu')

# Englisch
ocr_result = ocr_service.process_document(image_path, lang='eng')

# Mehrsprachig
ocr_result = ocr_service.process_document(image_path, lang='deu+eng')
```

### Tracking-Pattern erweitern

```python
# In src/services/ocr_service.py
TRACKING_PATTERNS = {
    'custom_carrier': [
        r'\bCUSTOM-\d{10}\b',  # Custom Pattern
    ]
}
```

---

## Datei-Struktur

```
src/
├── models/
│   └── document.py                    # PostEntry mit photos/ocr_text/extracted_data
│
├── services/
│   ├── photo_service.py              # Foto-Upload (bereits vorhanden)
│   └── ocr_service.py                # NEU: OCR & Smart-Extraction
│
├── controllers/
│   ├── photo_upload_controller.py    # ERWEITERT: PostEntry Upload-Routes
│   └── documents/
│       └── documents_controller.py   # ERWEITERT: post_scan Route
│
└── templates/
    └── documents/
        └── post_scan.html            # NEU: Scan-Interface

scripts/
└── add_post_entry_photos_fields.py   # NEU: Migration

docs/
└── POSTENTRY_OCR_FEATURES.md         # Diese Datei
```

---

## Troubleshooting

### OCR funktioniert nicht

**Problem:** `pytesseract.TesseractNotFoundError`

**Lösung:**
1. Tesseract installieren (siehe Installation)
2. Pfad konfigurieren:
   ```python
   pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   ```

### Texterkennung ungenau

**Problem:** Schlechte OCR-Qualität

**Lösung:**
1. **Bessere Beleuchtung** beim Fotografieren
2. **Dokument glatt legen** (keine Falten)
3. **Kamera stabilisieren** (nicht verwackeln)
4. **Höhere Auflösung** verwenden
5. **Bildvorverarbeitung** erweitern (Kontrast, Schärfe)

### Tracking-Nummer nicht erkannt

**Problem:** Carrier-spezifisches Format nicht unterstützt

**Lösung:**
1. Pattern in `TRACKING_PATTERNS` erweitern
2. Eigenes Regex-Pattern hinzufügen
3. Service neu starten

---

## Performance

### OCR-Geschwindigkeit

- **Kleines Dokument (A5):** ~2-3 Sekunden
- **Großes Dokument (A4):** ~5-7 Sekunden
- **Mehrere Seiten:** Pro Seite ~3-5 Sekunden

### Optimierungen

```python
# Bild verkleinern für schnellere OCR
from PIL import Image

image = Image.open(path)
image.thumbnail((1920, 1920))  # Max 1920px
```

---

## Sicherheit

### Datenschutz

- OCR-Text wird **nur lokal** verarbeitet (kein Cloud-Service)
- Tesseract läuft **auf dem Server** (keine Daten-Übertragung)
- Fotos werden **verschlüsselt gespeichert** (optional: Dateisystem-Verschlüsselung)

### Best Practices

1. **Sensible Daten:** OCR-Text kann sensible Informationen enthalten
2. **Zugriffsrechte:** Nur autorisierte Benutzer können Scans sehen
3. **Archivierung:** Alte Scans regelmäßig archivieren/löschen
4. **DSGVO:** OCR-Texte unterliegen Datenschutz-Anforderungen

---

## Erweiterungen (Optional)

### 1. Barcode-Scanner

```python
# pyzbar installieren
pip install pyzbar

# In ocr_service.py
from pyzbar import pyzbar

def scan_barcodes(image_path):
    image = Image.open(image_path)
    barcodes = pyzbar.decode(image)
    return [b.data.decode('utf-8') for b in barcodes]
```

### 2. Mehrseiten-PDF OCR

```python
# pdf2image installieren
pip install pdf2image

# In ocr_service.py
from pdf2image import convert_from_path

def process_pdf(pdf_path):
    images = convert_from_path(pdf_path)
    texts = []
    for image in images:
        text = pytesseract.image_to_string(image, lang='deu')
        texts.append(text)
    return '\n\n--- Seite ---\n\n'.join(texts)
```

### 3. Handschrifterkennung

```python
# Tesseract 4.0+ mit LSTM
# Bessere Handschrifterkennung
pytesseract.image_to_string(image, lang='deu', config='--oem 1 --psm 6')
```

---

## Changelog

### Version 1.0 (25.11.2025)
- PostEntry Model erweitert (photos, ocr_text, extracted_data)
- OCRService mit Smart-Extraction implementiert
- API-Endpunkte für PostEntry-Upload mit OCR
- Mobile Scan-Template erstellt
- Migration ausgeführt
- Auto-Fill für Tracking & Betrag
- Dokumentation erstellt

---

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**
**Bei Fragen: siehe MOBILE_WORKFLOW_FEATURES.md für ähnliche Features**
