# Mobile Workflow & Foto-Dokumentation

**Erstellt von: Hans Hahn - Alle Rechte vorbehalten**
**Datum:** 24. November 2025
**Version:** 1.0

---

## 📱 Überblick

Diese Implementierung ermöglicht:
- **Mobile Webapp-Nutzung** im lokalen Netzwerk
- **Kamera-Zugriff** für QM-Fotos vom Smartphone
- **Automatische Workflows** von Produktion bis Versand
- **PDF-Generierung** für Packlisten & Lieferscheine

---

## 🎯 Implementierte Features

### 1. Foto-Management System

#### Order Model - Foto-Felder
```python
# Order.photos - JSON Array
[{
    "path": "photos/abc123.jpg",
    "type": "color|position|sample|qc|other",
    "description": "Fadenfarbe Rot",
    "timestamp": "2025-11-24T12:00:00"
}]
```

**Helper-Methoden:**
- `order.get_photos()` - Alle Fotos abrufen
- `order.add_photo(path, type, description)` - Foto hinzufügen
- `order.remove_photo(path)` - Foto löschen

#### PhotoService (`src/services/photo_service.py`)
- **Datei-Upload** mit Größenbeschränkung (10MB)
- **Base64-Upload** für Kamera-Fotos
- **Thumbnail-Generierung** (400×400px)
- **EXIF-Orientierung** automatisch korrigieren
- **Bildoptimierung** (max 1920px, 85% Qualität)

### 2. Kamera-Zugriff (JavaScript)

**Modul:** `src/static/js/camera-upload.js`

```javascript
// Initialisierung
const camera = new CameraUpload({
    targetElement: '#camera-container',
    uploadUrl: '/api/photos/upload/order/ORDER-123',
    photoType: 'qc',
    onSuccess: (result) => {
        console.log('Upload erfolgreich', result);
    }
});
```

**Features:**
- HTML5 getUserMedia API
- Rück-Kamera bevorzugen (facingMode: 'environment')
- Foto-Vorschau vor Upload
- Drag & Drop Alternative
- Progress-Anzeige

### 3. API-Endpunkte

#### Foto-Upload API (`/api/photos/*`)

**Upload für Auftrag:**
```http
POST /api/photos/upload/order/<order_id>
Content-Type: application/json

{
    "photo": "data:image/jpeg;base64,...",
    "type": "color",
    "description": "Fadenfarbe Rot"
}
```

**Upload für QC (Packliste):**
```http
POST /api/photos/upload/packing-list/<id>/qc
Content-Type: application/json

{
    "photo": "data:image/jpeg;base64,...",
    "description": "Stickqualität OK"
}
```

**Foto löschen:**
```http
DELETE /api/photos/delete/order/<order_id>/<photo_path>
```

**Upload-Informationen:**
```http
GET /api/photos/info
```

### 4. PDF-Generierung

#### Packliste PDF
**Service:** `src/services/pdf_service.py` - `create_packing_list_pdf()`

**Enthält:**
- Firmenlogo & Adresse
- Packlisten-Nummer & Datum
- Kunden-Info & Auftragsnummer
- Carton-Info (bei Teillieferungen)
- Artikelliste mit EAN/SKU
- Kundenvorgaben (gelbe Box)
- QK-Checkboxen
- Verpackungs-Felder (Gewicht, Maße)
- QR-Code für Tracking

#### Lieferschein PDF
**Service:** `src/services/pdf_service.py` - `create_delivery_note_pdf()`

**Enthält:**
- Firmenlogo & Adresse
- Lieferschein-Nummer & Datum
- Lieferadresse (Box)
- Auftragsnummer
- Versandart & Tracking-Nummer
- Artikelliste
- Paket-Info (Anzahl, Gewicht)
- Unterschriftenfeld
- Rechtlicher Hinweis

**Helper-Funktionen:** `src/utils/pdf_workflow_helpers.py`
- `generate_packing_list_pdf(packing_list)` - PDF erstellen & speichern
- `generate_delivery_note_pdf(delivery_note)` - PDF erstellen & speichern

### 5. Automatische Workflows

#### Workflow-Helper (`src/utils/workflow_helpers.py`)

**Produktion → Packliste → PostEntry:**
```python
result = complete_production_workflow(
    production=production,
    order=order,
    current_user=current_user
)

# Erstellt automatisch:
# 1. PackingList (mit PDF)
# 2. PostEntry (Postbuch-Eintrag)
# 3. Verknüpfungen aktualisieren
```

**Packliste → Lieferschein:**
```python
delivery_note = create_delivery_note_from_packing_list(packing_list)
# Erstellt automatisch:
# 1. DeliveryNote (mit PDF)
# 2. PostEntry aktualisieren
```

#### Integration in Controller

**Production Controller** (`complete_production`):
```python
# Nach Produktionsabschluss:
workflow_result = complete_production_workflow(
    production=production_mock,
    order=order,
    current_user=current_user
)

if workflow_result['success']:
    # Packliste & PostEntry erstellt ✅
    flash(f"Packliste {pl.packing_list_number} erstellt!", 'success')
```

**Packing List Controller** (`pack`):
```python
# Nach Verpackung:
if settings.auto_create_delivery_note:
    delivery_note = create_delivery_note_from_packing_list(packing_list)
    flash(f"Lieferschein {dn.delivery_note_number} erstellt!", 'info')
```

---

## 🚀 Verwendung

### Mobile Webapp-Zugriff

1. **Server starten:**
   ```bash
   python app.py
   ```

2. **IP-Adresse ermitteln:**
   ```bash
   ipconfig  # Windows
   ifconfig  # Linux/Mac
   ```

3. **Vom Smartphone zugreifen:**
   ```
   http://<IP-ADRESSE>:5000
   ```
   Beispiel: `http://192.168.1.100:5000`

### QM-Fotos mit Smartphone aufnehmen

1. **Auftrag öffnen** im Browser
2. **"Foto hinzufügen"** Button klicken
3. **Kamera öffnen** wählen
4. **Foto aufnehmen**
5. **Beschreibung** eingeben (z.B. "Fadenfarbe Rot")
6. **Hochladen** bestätigen

### Workflow: Produktion abschließen

1. **Produktion beenden** → Button "Produktion abschließen"
2. **Automatisch erstellt:**
   - ✅ Packliste (PL-2025-0001)
   - ✅ Postbuch-Eintrag (POST-2025-000123)
   - ✅ PDFs generiert
3. **Status:** Auftrag → "Packing"

### Workflow: QC durchführen

1. **Packliste öffnen** → "QC durchführen"
2. **Fotos aufnehmen** (optional, vom Smartphone)
3. **Checkboxen** ausfüllen
4. **QC bestanden** bestätigen
5. **Status:** Packliste → "QC bestanden"

### Workflow: Verpacken

1. **Packliste öffnen** → "Als verpackt markieren"
2. **Gewicht & Maße** eingeben
3. **Bestätigen**
4. **Automatisch erstellt:**
   - ✅ Lieferschein (LS-2025-0001)
   - ✅ PDF generiert
   - ✅ PostEntry aktualisiert
5. **Status:** Packliste → "Verpackt"

---

## ⚙️ Einstellungen

### Company Settings

**Workflow-Automatisierung:**
```python
# Packliste nach Produktion automatisch erstellen
auto_create_packing_list = True

# Lieferschein nach Verpackung automatisch erstellen
auto_create_delivery_note = True

# Tracking-Email automatisch senden
auto_send_tracking_email = True

# QC vor Verpackung erforderlich
require_qc_before_packing = False

# QC-Fotos erforderlich
require_qc_photos = False

# Automatische Lagerbuchung
auto_inventory_booking = True
```

**Rechnungserstellung:**
```python
# manual = Manuell
# after_delivery = Nach Lieferung
# delayed = Verzögert (X Tage)
invoice_creation_mode = 'manual'
invoice_creation_delay_days = 7
```

### Order-spezifische Einstellung

```python
order.auto_create_packing_list = True  # Pro Auftrag deaktivierbar
```

---

## 📂 Datei-Struktur

```
src/
├── models/
│   ├── models.py                    # Order.photos Feld
│   ├── packing_list.py              # PackingList Model
│   └── delivery_note.py             # DeliveryNote Model
│
├── services/
│   ├── photo_service.py             # Foto-Upload & Thumbnails
│   └── pdf_service.py               # PDF-Generierung
│
├── utils/
│   ├── workflow_helpers.py          # Workflow-Automatisierung
│   └── pdf_workflow_helpers.py      # PDF-Helper
│
├── controllers/
│   ├── photo_upload_controller.py   # API für Foto-Upload
│   ├── packing_list_controller.py   # QC & Verpackung
│   └── production_controller_db.py  # Workflow-Integration
│
└── static/js/
    └── camera-upload.js             # Kamera-Modul

scripts/
└── add_order_photos_field.py        # Migration

instance/uploads/
├── photos/                          # Original-Fotos
└── thumbnails/                      # Thumbnails (400×400)
```

---

## 🧪 Testing

### 1. Backend-Tests

```bash
# Photo Service testen
python -c "from src.services.photo_service import PhotoService; ps = PhotoService(); print('OK')"

# Workflow Helper testen
python -c "from src.utils.workflow_helpers import *; print('OK')"
```

### 2. API-Tests (mit cURL)

```bash
# Upload Info abrufen
curl -X GET http://localhost:5000/api/photos/info

# Foto hochladen (Base64)
curl -X POST http://localhost:5000/api/photos/upload/order/ORDER-123 \
  -H "Content-Type: application/json" \
  -d '{"photo": "data:image/jpeg;base64,/9j/4AAQ...", "type": "qc", "description": "Test"}'
```

### 3. Mobile Tests

1. **Kamera-Zugriff:**
   - Android Chrome: ✅
   - iOS Safari: ✅
   - Desktop Chrome: ✅ (Webcam)

2. **Foto-Upload:**
   - Datei-Upload: ✅
   - Kamera-Capture: ✅
   - Base64-Encoding: ✅

3. **Responsive Design:**
   - Touch-Navigation: ✅
   - Formulare mobile-optimiert: ✅

---

## 📋 Nächste Schritte (Optional)

### UI-Templates erstellen

1. **QC-Form Template** (`src/templates/packing_lists/qc.html`)
   - Foto-Upload-Integration
   - Kamera-Button
   - Vorschau-Galerie

2. **Packlisten-Übersicht** (`src/templates/packing_lists/list.html`)
   - Status-Tabs
   - Foto-Thumbnails
   - Quick-Actions

### Erweiterte Features

1. **Barcode-Scanner** (Smartphone-Kamera)
2. **Offline-Modus** (Service Worker)
3. **Push-Notifications** (Neue Aufträge)
4. **GPS-Tracking** (Versand-Status)
5. **Digitale Unterschrift** (Lieferschein)

---

## 🐛 Troubleshooting

### Kamera funktioniert nicht

**Problem:** Browser blockiert Kamera-Zugriff

**Lösung:**
1. HTTPS verwenden (oder localhost)
2. Browser-Berechtigungen prüfen
3. Fallback auf Datei-Upload

### Upload schlägt fehl

**Problem:** Datei zu groß oder falsches Format

**Lösung:**
```python
# In photo_service.py anpassen:
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'heic'}
```

### PDF-Generierung fehlschlägt

**Problem:** ReportLab nicht installiert

**Lösung:**
```bash
pip install reportlab pillow
```

---

## 📝 Changelog

### Version 1.0 (24.11.2025)
- ✅ Foto-Management System (Order.photos)
- ✅ PhotoService mit Thumbnail-Generierung
- ✅ Kamera-Upload JavaScript-Modul
- ✅ API-Endpunkte für Foto-Upload
- ✅ PDF-Generierung (Packliste & Lieferschein)
- ✅ Workflow-Helper (Produktion → Versand)
- ✅ Controller-Integration (Production & Packing List)
- ✅ Migration (photos Feld)
- ✅ Dokumentation

---

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**
**Bei Fragen: siehe WORKFLOW_KONZEPT.md für Details**
