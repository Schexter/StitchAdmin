# Implementierungsplan: Workflow-Integration
## StitchAdmin 2.0 - Phase 1

**Erstellt:** 2025-11-24
**Basierend auf:** WORKFLOW_KONZEPT.md
**Zeitrahmen:** 5-7 Arbeitstage

---

## Phase 1: Basis-Integration (Tag 1-2)

### Tag 1 Vormittag: Datenbank-Models

#### Task 1.1: PackingList Model erstellen
**Datei:** `src/models/packing_list.py` (neu)
**Dauer:** 1h

```python
# Vollständiges PackingList Model mit:
- Basis-Felder (id, number, dates)
- Verknüpfungen (order, production, customer)
- Carton-Support (carton_number, total_cartons)
- Status-Tracking
- Artikel-JSON
- Gewicht/Maße
- QC-Felder
- Verpackungs-Felder
- Lagerbuchungs-Felder
- PDF-Pfad
```

**Checklist:**
- [ ] Model-Klasse erstellt
- [ ] Alle Felder definiert
- [ ] Relationships zu Order, Production, Customer
- [ ] Helper-Methods (carton_label, etc.)
- [ ] Nummerngenerierung (`generate_packing_list_number()`)
- [ ] Model in `__init__.py` exportiert

#### Task 1.2: DeliveryNote Model erstellen
**Datei:** `src/models/delivery_note.py` (neu)
**Dauer:** 1h

```python
# Vollständiges DeliveryNote Model mit:
- Basis-Felder
- Verknüpfungen (order, packing_list, customer, post_entry)
- Signatur-Felder (digital + gedruckt)
- Foto-Support
- Status
- PDF-Pfade (normal + mit Signatur)
```

**Checklist:**
- [ ] Model-Klasse erstellt
- [ ] Signatur-Felder (image, name, date, device, type)
- [ ] Foto-Array (JSON)
- [ ] Nummerngenerierung (`generate_delivery_note_number()`)
- [ ] is_signed Property
- [ ] Model exportiert

#### Task 1.3: Bestehende Models erweitern
**Dateien:** `src/models/models.py`, `src/models/company_settings.py`
**Dauer:** 1h

**Order erweitern:**
```python
workflow_status = db.Column(db.String(50))
packing_list_id = db.Column(db.Integer, db.ForeignKey('packing_lists.id'))
delivery_note_id = db.Column(db.Integer, db.ForeignKey('delivery_notes.id'))
auto_create_packing_list = db.Column(db.Boolean, default=True)
```

**Production erweitern:**
```python
packing_list_created = db.Column(db.Boolean, default=False)
packing_list_id = db.Column(db.Integer, db.ForeignKey('packing_lists.id'))
```

**PostEntry erweitern:**
```python
packing_list_id = db.Column(db.Integer, db.ForeignKey('packing_lists.id'))
delivery_note_id = db.Column(db.Integer, db.ForeignKey('delivery_notes.id'))
is_auto_created = db.Column(db.Boolean, default=False)
```

**CompanySettings erweitern:**
```python
invoice_creation_mode = db.Column(db.String(20), default='manual')
invoice_creation_delay_days = db.Column(db.Integer, default=0)
auto_create_packing_list = db.Column(db.Boolean, default=True)
auto_create_delivery_note = db.Column(db.Boolean, default=True)
auto_send_tracking_email = db.Column(db.Boolean, default=True)
require_qc_before_packing = db.Column(db.Boolean, default=False)
require_qc_photos = db.Column(db.Boolean, default=False)
auto_inventory_booking = db.Column(db.Boolean, default=True)
```

**Checklist:**
- [ ] Order erweitert
- [ ] Production erweitert
- [ ] PostEntry erweitert
- [ ] CompanySettings erweitert
- [ ] Relationships definiert

### Tag 1 Nachmittag: Datenbank-Migration

#### Task 1.4: Migration Script erstellen
**Datei:** `scripts/add_workflow_tables.py` (neu)
**Dauer:** 1h

```python
# Migration für:
1. CREATE TABLE packing_lists
2. CREATE TABLE delivery_notes
3. ALTER TABLE orders (neue Spalten)
4. ALTER TABLE productions (neue Spalten)
5. ALTER TABLE post_entries (neue Spalten)
6. ALTER TABLE company_settings (neue Spalten)
```

**Checklist:**
- [ ] Script erstellt
- [ ] Alle Tabellen/Spalten abgedeckt
- [ ] Fehlerbehandlung
- [ ] Rollback-Logik
- [ ] Test auf Entwicklungs-DB

#### Task 1.5: Migration ausführen & testen
**Dauer:** 30min

**Checklist:**
- [ ] Backup der aktuellen DB erstellt
- [ ] Migration ausgeführt
- [ ] Keine Fehler
- [ ] Alle Tabellen vorhanden (`sqlite3 .browser`)
- [ ] Alle Spalten vorhanden

### Tag 1 Ende: Controller Basis

#### Task 1.6: Packing List Controller erstellen
**Datei:** `src/controllers/packing_list_controller.py` (neu)
**Dauer:** 2h

**Routes:**
```python
@packing_list_bp.route('/')                      # Liste
@packing_list_bp.route('/<int:id>')             # Detail
@packing_list_bp.route('/new')                   # Neu (manuell)
@packing_list_bp.route('/<int:id>/edit')        # Bearbeiten
@packing_list_bp.route('/<int:id>/qc')          # QC durchführen
@packing_list_bp.route('/<int:id>/pack')        # Verpacken
@packing_list_bp.route('/<int:id>/delete')      # Löschen
```

**Basis-Implementierung:**
- Liste mit Filtern (Status, Kunde)
- Detail-Ansicht
- CRUD-Operationen

**Checklist:**
- [ ] Blueprint erstellt
- [ ] Basis-Routes implementiert
- [ ] Controller in app.py registriert
- [ ] Imports korrekt

---

## Phase 1: Tag 2 - Templates & Basis-UI

### Tag 2 Vormittag: Templates erstellen

#### Task 2.1: Packlisten-Liste Template
**Datei:** `src/templates/packing_lists/list.html`
**Dauer:** 1h

**Features:**
- Tabs: Bereit (ready), In Verpackung (in_progress), Versandbereit (packed)
- Tabelle: Nummer, Kunde, Auftrag, Artikel-Anzahl, Status, Aktionen
- Filter: Kunde, Datum
- Buttons: "Neue Packliste", "QK", "Verpacken"

**Checklist:**
- [ ] Template erstellt
- [ ] Tabs funktionieren
- [ ] Tabelle zeigt Daten
- [ ] Filter implementiert
- [ ] Buttons verlinkt

#### Task 2.2: Packlisten-Detail Template
**Datei:** `src/templates/packing_lists/detail.html`
**Dauer:** 1.5h

**Sections:**
```
1. Header: Nummer, Status, Kunde, Auftrag
2. Carton-Info (bei Teillieferung)
3. Artikelliste (aus JSON)
4. Kundenvorgaben
5. QK-Bereich (Checkboxen, Fotos, Notizen)
6. Verpackung (Gewicht, Maße, Bestätigung)
7. Aktionen (QC, Verpacken, PDF, Bearbeiten)
```

**Checklist:**
- [ ] Template erstellt
- [ ] Alle Sections vorhanden
- [ ] Artikel-JSON wird angezeigt
- [ ] QC-Form funktioniert
- [ ] Verpackungs-Form funktioniert
- [ ] Carton-Label bei Teillieferungen

#### Task 2.3: Packlisten-Form Template
**Datei:** `src/templates/packing_lists/form.html`
**Dauer:** 1h

**Features:**
- Auftrag auswählen (Dropdown)
- Artikel automatisch laden
- Carton-Nummer bei Teillieferung
- Gewicht/Maße eingeben
- Kundenvorgaben anzeigen

**Checklist:**
- [ ] Template erstellt
- [ ] Auftrag-Dropdown funktioniert
- [ ] Artikel werden geladen (JS/AJAX)
- [ ] Carton-Felder conditional
- [ ] Validierung

### Tag 2 Nachmittag: Workflow-Integration Basis

#### Task 2.4: Produktions-Controller erweitern
**Datei:** `src/controllers/production_controller.py`
**Dauer:** 2h

**Änderungen:**
```python
@production_bp.route('/<int:id>/complete', methods=['POST'])
def complete_production(id):
    production = Production.query.get_or_404(id)

    # Status setzen
    production.status = 'completed'
    production.completed_at = datetime.now()

    # WORKFLOW TRIGGER
    if production.order and production.order.auto_create_packing_list:
        # Packliste erstellen
        packing_list = create_packing_list_from_production(production)

        # PostEntry erstellen
        post_entry = create_post_entry_from_packing_list(packing_list)

        # Status aktualisieren
        production.packing_list_created = True
        production.packing_list_id = packing_list.id

        flash(f'Packliste {packing_list.packing_list_number} erstellt', 'success')

    db.session.commit()
    return redirect(...)
```

**Helper-Funktionen erstellen:**
```python
def create_packing_list_from_production(production):
    """Erstellt Packliste aus Produktion"""
    # Artikel aus Order holen
    # PackingList erstellen
    # Items als JSON speichern
    # Kundenvorgaben kopieren
    return packing_list

def create_post_entry_from_packing_list(packing_list):
    """Erstellt PostEntry für Packliste"""
    # PostEntry erstellen (outbound)
    # Kunde als Empfänger
    # Firma als Absender
    # Status: open
    return post_entry
```

**Checklist:**
- [ ] complete_production erweitert
- [ ] create_packing_list_from_production() implementiert
- [ ] create_post_entry_from_packing_list() implementiert
- [ ] Fehlerbehandlung
- [ ] Flash-Messages
- [ ] Tests

---

## Phase 2: PDFs & Erweiterte UI (Tag 3-4)

### Tag 3: PDF-Generierung

#### Task 3.1: Packliste PDF Generator
**Datei:** `src/utils/pdf_generators.py` (erweitern)
**Dauer:** 3h

**Layout:**
```
┌─────────────────────────────────────┐
│ [LOGO]              PACKLISTE       │
│ Firma                               │
│ Adresse             PL-2024-001     │
│                     24.11.2024      │
├─────────────────────────────────────┤
│ Kunde: Musterfirma GmbH             │
│ Auftrag: AU-2024-123                │
│ Karton: 1 von 3  [falls Teillieferung]│
├─────────────────────────────────────┤
│ ARTIKELLISTE                        │
│ Pos | Artikel         | Menge | EAN│
│  1  | Poloshirt rot   |  10   |... │
│  2  | Baseballcap     |   5   |... │
├─────────────────────────────────────┤
│ KUNDENVORGABEN:                     │
│ "Einzeln in Folie verpacken"        │
├─────────────────────────────────────┤
│ QUALITÄTSKONTROLLE:                 │
│ [ ] Stickqualität geprüft           │
│ [ ] Farben korrekt                  │
│ [ ] Vollständigkeit                 │
│                                     │
│ Geprüft: ____________  Datum: _____ │
│                                     │
│ VERPACKUNG:                         │
│ Gewicht: _____ kg                   │
│ Maße: ___x___x___ cm                │
│                                     │
│ Verpackt: _________  Datum: _______ │
├─────────────────────────────────────┤
│ [QR-Code: PL-2024-001]              │
└─────────────────────────────────────┘
```

**Checklist:**
- [ ] PDF-Generator-Funktion erstellt
- [ ] Firmenlogo einbinden
- [ ] Artikeltabelle
- [ ] QK-Checkboxen
- [ ] Verpackungs-Felder
- [ ] QR-Code/Barcode
- [ ] Carton-Info bei Teillieferungen
- [ ] PDF speichern + Pfad in DB

#### Task 3.2: Lieferschein PDF Generator
**Datei:** `src/utils/pdf_generators.py` (erweitern)
**Dauer:** 2h

**Layout:**
```
┌─────────────────────────────────────┐
│ [LOGO]           LIEFERSCHEIN       │
│ Firmenname                          │
│ Straße + Nr.        LS-2024-001     │
│ PLZ + Ort           24.11.2024      │
├─────────────────────────────────────┤
│ LIEFERANSCHRIFT:                    │
│ Musterfirma GmbH                    │
│ Musterstraße 1                      │
│ 12345 Musterstadt                   │
├─────────────────────────────────────┤
│ Auftragsnummer: AU-2024-123         │
│ Lieferdatum: 24.11.2024             │
│ Versandart: DHL Paket               │
│ Sendungsnummer: 1234567890          │
├─────────────────────────────────────┤
│ GELIEFERTE ARTIKEL                  │
│ Pos | Bezeichnung     | Mge. | Einh│
│  1  | Poloshirt rot   |  10  | Stk │
│  2  | Baseballcap     |   5  | Stk │
├─────────────────────────────────────┤
│ Anzahl Pakete: 3                    │
│ Gesamtgewicht: 7.5 kg               │
├─────────────────────────────────────┤
│ UNTERSCHRIFT EMPFÄNGER:             │
│                                     │
│ ___________________________________ │
│ Name (Druckschrift)                 │
│                                     │
│ ___________________________________ │
│ Unterschrift          Datum         │
├─────────────────────────────────────┤
│ Dies ist kein steuerliches Dokument │
│ Die Rechnung folgt separat.         │
└─────────────────────────────────────┘
```

**Checklist:**
- [ ] PDF-Generator erstellt
- [ ] Firmenlogo + Adresse
- [ ] Lieferadresse
- [ ] Artikeltabelle
- [ ] Tracking-Info (falls vorhanden)
- [ ] Unterschriftenfeld
- [ ] Fußtext
- [ ] PDF speichern + Pfad in DB

#### Task 3.3: PDF-Download Routes
**Datei:** `src/controllers/packing_list_controller.py`
**Dauer:** 1h

```python
@packing_list_bp.route('/<int:id>/pdf')
def download_pdf(id):
    packing_list = PackingList.query.get_or_404(id)

    # PDF generieren falls nicht vorhanden
    if not packing_list.pdf_path or not os.path.exists(packing_list.pdf_path):
        pdf_path = generate_packing_list_pdf(packing_list)
        packing_list.pdf_path = pdf_path
        db.session.commit()

    return send_file(packing_list.pdf_path, as_attachment=True)
```

**Checklist:**
- [ ] PDF-Download Route für Packliste
- [ ] PDF-Download Route für Lieferschein
- [ ] Auto-Generierung bei fehlendem PDF
- [ ] Fehlerbehandlung

### Tag 4: QC & Verpackungs-Workflow

#### Task 4.1: QC-Workflow implementieren
**Datei:** `src/controllers/packing_list_controller.py`
**Dauer:** 2h

```python
@packing_list_bp.route('/<int:id>/qc', methods=['GET', 'POST'])
def perform_qc(id):
    packing_list = PackingList.query.get_or_404(id)

    if request.method == 'POST':
        # QC-Daten speichern
        packing_list.qc_performed = True
        packing_list.qc_by = current_user.id
        packing_list.qc_date = datetime.now()
        packing_list.qc_notes = request.form.get('qc_notes')

        # Fotos hochladen (optional)
        if 'qc_photos' in request.files:
            photos = save_qc_photos(request.files.getlist('qc_photos'))
            packing_list.qc_photos = json.dumps(photos)

        # Status aktualisieren
        if company_settings.require_qc_before_packing:
            packing_list.status = 'qc_passed'

        db.session.commit()
        flash('Qualitätskontrolle durchgeführt', 'success')
        return redirect(url_for('packing_list.detail', id=id))

    return render_template('packing_lists/qc_form.html', packing_list=packing_list)
```

**Checklist:**
- [ ] QC-Route implementiert
- [ ] QC-Form Template
- [ ] Foto-Upload
- [ ] Validierung (QC erforderlich?)
- [ ] Flash-Messages

#### Task 4.2: Verpackungs-Workflow
**Datei:** `src/controllers/packing_list_controller.py`
**Dauer:** 2h

```python
@packing_list_bp.route('/<int:id>/pack', methods=['GET', 'POST'])
def pack(id):
    packing_list = PackingList.query.get_or_404(id)

    # QC prüfen
    if company_settings.require_qc_before_packing and not packing_list.qc_performed:
        flash('Qualitätskontrolle muss zuerst durchgeführt werden', 'warning')
        return redirect(url_for('packing_list.qc', id=id))

    if request.method == 'POST':
        # Verpackungs-Daten
        packing_list.total_weight = request.form.get('weight')
        packing_list.package_length = request.form.get('length')
        packing_list.package_width = request.form.get('width')
        packing_list.package_height = request.form.get('height')
        packing_list.packing_notes = request.form.get('notes')

        packing_list.packed_by = current_user.id
        packing_list.packed_at = datetime.now()
        packing_list.packed_confirmed = True
        packing_list.status = 'packed'

        # WORKFLOW TRIGGER: Lieferschein erstellen
        if company_settings.auto_create_delivery_note:
            delivery_note = create_delivery_note_from_packing_list(packing_list)
            packing_list.delivery_note_id = delivery_note.id
            flash(f'Lieferschein {delivery_note.delivery_note_number} erstellt', 'success')

        db.session.commit()
        return redirect(url_for('packing_list.detail', id=id))

    return render_template('packing_lists/pack_form.html', packing_list=packing_list)
```

**Helper-Funktion:**
```python
def create_delivery_note_from_packing_list(packing_list):
    """Erstellt Lieferschein aus Packliste"""
    delivery_note = DeliveryNote(
        delivery_note_number=generate_delivery_note_number(),
        order_id=packing_list.order_id,
        packing_list_id=packing_list.id,
        customer_id=packing_list.customer_id,
        post_entry_id=packing_list.post_entry_id,
        delivery_date=date.today(),
        items=packing_list.items,
        status='ready',
        created_by=current_user.id
    )
    db.session.add(delivery_note)

    # Lieferschein PDF generieren
    pdf_path = generate_delivery_note_pdf(delivery_note)
    delivery_note.pdf_path = pdf_path

    # PostEntry aktualisieren
    if packing_list.post_entry:
        packing_list.post_entry.delivery_note_id = delivery_note.id
        packing_list.post_entry.status = 'in_progress'

    return delivery_note
```

**Checklist:**
- [ ] Pack-Route implementiert
- [ ] QC-Prüfung
- [ ] Gewicht/Maße-Felder
- [ ] Auto-Lieferschein-Erstellung
- [ ] PostEntry-Update
- [ ] Flash-Messages

---

## Phase 3: Digitale Unterschrift & Email (Tag 5)

### Tag 5 Vormittag: Digitale Unterschrift

#### Task 5.1: Unterschrift-Capture UI
**Datei:** `src/templates/delivery_notes/signature.html`
**Dauer:** 2h

**Features:**
- Canvas-Element für Signatur
- JavaScript: Maus/Touch-Events
- "Löschen" Button
- "Speichern" Button
- Vorschau
- Name-Eingabefeld

**JavaScript:**
```javascript
const canvas = document.getElementById('signature-canvas');
const ctx = canvas.getContext('2d');
let drawing = false;

// Touch & Mouse Events
canvas.addEventListener('mousedown', startDrawing);
canvas.addEventListener('mousemove', draw);
canvas.addEventListener('mouseup', stopDrawing);
canvas.addEventListener('touchstart', startDrawing);
canvas.addEventListener('touchmove', draw);
canvas.addEventListener('touchend', stopDrawing);

function saveSignature() {
    const dataURL = canvas.toDataURL('image/png');
    // AJAX POST zu Server
    fetch('/delivery-notes/{{ delivery_note.id }}/signature', {
        method: 'POST',
        body: JSON.stringify({
            signature: dataURL,
            name: document.getElementById('signer-name').value
        })
    });
}
```

**Checklist:**
- [ ] Canvas implementiert
- [ ] Zeichnen funktioniert (Maus + Touch)
- [ ] Löschen-Button
- [ ] Speichern-Button
- [ ] Name-Feld
- [ ] Responsive Design (Tablet-optimiert)

#### Task 5.2: Unterschrift-Backend
**Datei:** `src/controllers/delivery_note_controller.py` (neu)
**Dauer:** 2h

```python
@delivery_note_bp.route('/<int:id>/signature', methods=['POST'])
def save_signature(id):
    delivery_note = DeliveryNote.query.get_or_404(id)

    data = request.get_json()
    signature_data = data.get('signature')  # base64 PNG
    signer_name = data.get('name')

    # Base64 zu Bild
    import base64
    signature_bytes = base64.b64decode(signature_data.split(',')[1])

    # Speichern
    filename = f"signature_{delivery_note.id}_{int(datetime.now().timestamp())}.png"
    signature_path = os.path.join('static/uploads/signatures', filename)

    with open(signature_path, 'wb') as f:
        f.write(signature_bytes)

    # DB aktualisieren
    delivery_note.signature_image = signature_path
    delivery_note.signature_name = signer_name
    delivery_note.signature_date = datetime.now()
    delivery_note.signature_type = 'digital'
    delivery_note.signature_device = request.user_agent.string
    delivery_note.status = 'signed'

    # PDF mit Unterschrift generieren
    pdf_with_sig = generate_delivery_note_pdf_with_signature(delivery_note)
    delivery_note.pdf_with_signature_path = pdf_with_sig

    db.session.commit()

    return jsonify({'success': True, 'message': 'Unterschrift gespeichert'})
```

**Checklist:**
- [ ] Route implementiert
- [ ] Base64 → PNG Konvertierung
- [ ] Datei speichern
- [ ] DB aktualisieren
- [ ] PDF mit Signatur generieren
- [ ] Fehlerbehandlung

### Tag 5 Nachmittag: Email-Integration

#### Task 5.3: Tracking-Email versenden
**Datei:** `src/controllers/documents/documents_controller.py` (erweitern)
**Dauer:** 2h

```python
# Bereits vorhanden, aber erweitern:
@documents_bp.route('/post/<int:id>/send_notification', methods=['POST'])
def send_shipping_notification(id):
    entry = PostEntry.query.get_or_404(id)

    # Lieferschein als Anhang
    attachments = []
    if entry.delivery_note and entry.delivery_note.pdf_path:
        attachments.append({
            'path': entry.delivery_note.pdf_path,
            'filename': f'Lieferschein_{entry.delivery_note.delivery_note_number}.pdf'
        })

    # Email senden (bereits implementiert)
    service = EmailIntegrationService(email_account.id)
    success = service.send_email(
        to_address=customer_email,
        subject=f'Ihre Bestellung wurde versendet - Tracking: {entry.tracking_number}',
        body=render_template('emails/shipping_notification.html', entry=entry),
        attachments=attachments
    )

    # PostEntry aktualisieren
    entry.email_notification_sent = True
    entry.email_notification_date = datetime.now()
    entry.status = 'completed'

    db.session.commit()
```

**Checklist:**
- [ ] Lieferschein-Anhang
- [ ] Email-Template
- [ ] Status-Update
- [ ] Fehlerbehandlung

---

## Phase 4: Dashboard & Statistiken (Tag 6)

### Tag 6: Dashboard-Integration

#### Task 6.1: Workflow-Status Widget
**Datei:** `src/templates/dashboard_simple.html` (erweitern)
**Dauer:** 2h

**Widget:**
```html
<div class="card">
    <div class="card-header">
        <h5>🔄 Workflow-Status</h5>
    </div>
    <div class="card-body">
        <div class="row">
            <div class="col-md-6">
                <a href="{{ url_for('packing_list.list', status='ready') }}" class="text-decoration-none">
                    <div class="alert alert-warning">
                        <strong>{{ stats.packing_lists_ready }}</strong>
                        Warte auf Verpackung
                    </div>
                </a>
            </div>
            <div class="col-md-6">
                <a href="{{ url_for('packing_list.list', status='packed') }}" class="text-decoration-none">
                    <div class="alert alert-info">
                        <strong>{{ stats.packing_lists_packed }}</strong>
                        Versandbereit
                    </div>
                </a>
            </div>
        </div>
        <div class="row">
            <div class="col-md-6">
                <a href="{{ url_for('documents.post_list', status='open') }}" class="text-decoration-none">
                    <div class="alert alert-primary">
                        <strong>{{ stats.shipments_today }}</strong>
                        Heute versenden
                    </div>
                </a>
            </div>
            <div class="col-md-6">
                <a href="{{ url_for('invoices.list', status='open') }}" class="text-decoration-none">
                    <div class="alert alert-danger">
                        <strong>{{ stats.invoices_open }}</strong>
                        Rechnung offen
                    </div>
                </a>
            </div>
        </div>
    </div>
</div>
```

**Controller-Änderung:**
```python
@dashboard_bp.route('/')
def index():
    stats = {
        'packing_lists_ready': PackingList.query.filter_by(status='ready').count(),
        'packing_lists_packed': PackingList.query.filter_by(status='packed').count(),
        'shipments_today': PostEntry.query.filter(
            PostEntry.direction == 'outbound',
            PostEntry.status == 'in_progress',
            PostEntry.planned_ship_date == date.today()
        ).count(),
        'invoices_open': Invoice.query.filter_by(status='open').count()
    }
    return render_template('dashboard_simple.html', stats=stats, ...)
```

**Checklist:**
- [ ] Widget im Dashboard
- [ ] Statistiken berechnen
- [ ] Links zu gefilterten Listen
- [ ] Farb-Codierung

#### Task 6.2: Workflow-Übersicht Seite
**Datei:** `src/templates/workflow/overview.html` (neu)
**Dauer:** 2h

**Features:**
- Kanban-Board-Style
- Spalten: In Produktion → Verpackung → Versandbereit → Versendet
- Drag & Drop (optional)
- Aufträge in jeweiliger Phase
- Quick-Actions

**Checklist:**
- [ ] Template erstellt
- [ ] Controller-Route
- [ ] Aufträge gruppiert
- [ ] Quick-Actions (QC, Verpacken, Versenden)

---

## Phase 5: Lagerbuchung & Feinschliff (Tag 7)

### Tag 7 Vormittag: Lagerbuchung

#### Task 7.1: Lagerbuchungs-Logik
**Datei:** `src/utils/inventory_manager.py` (neu)
**Dauer:** 2h

```python
def book_inventory_for_production(production):
    """Bucht Artikel aus Lager für Produktion"""
    order = production.order

    for order_item in order.items:
        article = order_item.article

        # Nur Lagerartikel ausbuchen
        if article.in_stock:
            if article.stock_quantity >= order_item.quantity:
                article.stock_quantity -= order_item.quantity

                # Lagerbewegung protokollieren
                inventory_log = InventoryLog(
                    article_id=article.id,
                    type='production',
                    quantity=-order_item.quantity,
                    reference_id=production.id,
                    reference_type='production',
                    created_by=current_user.id
                )
                db.session.add(inventory_log)
            else:
                # Warnung: Nicht genug auf Lager
                flash(f'Warnung: {article.name} - nur {article.stock_quantity} auf Lager', 'warning')
        else:
            # Fremdware: In Stückliste übernehmen
            pass

    db.session.commit()
```

**Checklist:**
- [ ] Inventory-Manager erstellt
- [ ] Ausbuchungs-Logik
- [ ] Lagerbewegungen protokollieren
- [ ] Warnungen bei fehlendem Lager
- [ ] Integration in Produktions-Workflow

#### Task 7.2: Teillieferungen-UI
**Datei:** `src/templates/packing_lists/split_order.html` (neu)
**Dauer:** 2h

**Features:**
- Auftrag in mehrere Cartons aufteilen
- Artikel auf Cartons verteilen
- Automatisch Packlisten generieren

**UI:**
```html
<form method="POST">
    <h4>Auftrag AU-2024-123 aufteilen</h4>

    <label>Anzahl Cartons:</label>
    <input type="number" name="carton_count" min="2" max="10" value="3">

    <h5>Artikel verteilen:</h5>
    <table>
        <tr>
            <th>Artikel</th>
            <th>Gesamt</th>
            <th>Carton 1</th>
            <th>Carton 2</th>
            <th>Carton 3</th>
        </tr>
        <tr>
            <td>Poloshirt rot</td>
            <td>10</td>
            <td><input type="number" name="item_1_carton_1" max="10"></td>
            <td><input type="number" name="item_1_carton_2" max="10"></td>
            <td><input type="number" name="item_1_carton_3" max="10"></td>
        </tr>
    </table>

    <button type="submit">Packlisten erstellen</button>
</form>
```

**Checklist:**
- [ ] Template erstellt
- [ ] Artikel-Verteilungs-Logik
- [ ] Validierung (Summe muss stimmen)
- [ ] Mehrere Packlisten erstellen
- [ ] Carton-Nummern setzen

### Tag 7 Nachmittag: Testing & Polieren

#### Task 7.3: End-to-End Testing
**Dauer:** 2h

**Test-Szenarien:**
1. Produktion abschließen → Packliste erstellt
2. QC durchführen → Fotos hochladen
3. Verpacken → Lieferschein erstellt
4. Tracking erfassen → Email versendet
5. Teillieferung erstellen
6. Digitale Unterschrift auf Tablet
7. Lagerbuchung prüfen

**Checklist:**
- [ ] Alle Workflows getestet
- [ ] PDFs korrekt generiert
- [ ] Emails versendet
- [ ] Lagerbuchungen korrekt
- [ ] Keine Fehler in Console

#### Task 7.4: Settings-UI
**Datei:** `src/templates/settings/workflow.html` (neu)
**Dauer:** 1h

**Settings:**
```html
<form method="POST">
    <h4>Workflow-Automatisierung</h4>

    <div class="form-check">
        <input type="checkbox" name="auto_create_packing_list" checked>
        <label>Packliste nach Produktion automatisch erstellen</label>
    </div>

    <div class="form-check">
        <input type="checkbox" name="auto_create_delivery_note" checked>
        <label>Lieferschein nach Verpackung automatisch erstellen</label>
    </div>

    <h5>Rechnungserstellung</h5>
    <select name="invoice_creation_mode">
        <option value="manual" selected>Manuell</option>
        <option value="after_delivery">Nach Lieferung</option>
        <option value="delayed">Verzögert</option>
    </select>

    <div id="delay-field" style="display: none;">
        <label>Tage nach Versand:</label>
        <input type="number" name="invoice_creation_delay_days" value="7">
    </div>

    <h5>Qualitätskontrolle</h5>
    <div class="form-check">
        <input type="checkbox" name="require_qc_before_packing">
        <label>QC vor Verpackung erforderlich</label>
    </div>

    <button type="submit">Speichern</button>
</form>
```

**Checklist:**
- [ ] Settings-Template
- [ ] Controller-Route
- [ ] Speichern funktioniert
- [ ] Settings werden angewendet

---

## Fertigstellung & Deployment

### Finale Checklist:

**Datenbank:**
- [ ] Alle Tabellen erstellt
- [ ] Alle Felder vorhanden
- [ ] Relationships funktionieren
- [ ] Migration dokumentiert

**Backend:**
- [ ] Alle Controller implementiert
- [ ] Alle Helper-Funktionen
- [ ] Fehlerbehandlung überall
- [ ] Logging aktiviert

**Frontend:**
- [ ] Alle Templates erstellt
- [ ] UI/UX getestet
- [ ] Responsive Design
- [ ] Tablet-optimiert (Signatur)

**PDFs:**
- [ ] Packliste PDF korrekt
- [ ] Lieferschein PDF korrekt
- [ ] Logos eingebunden
- [ ] QR-Codes funktionieren

**Workflows:**
- [ ] Produktion → Packliste funktioniert
- [ ] Packliste → Lieferschein funktioniert
- [ ] Tracking → Email funktioniert
- [ ] Teillieferungen funktionieren

**Features:**
- [ ] Digitale Unterschrift funktioniert
- [ ] QC-Workflow funktioniert
- [ ] Lagerbuchung funktioniert
- [ ] Dashboard-Widget funktioniert

**Dokumentation:**
- [ ] User-Guide erstellt
- [ ] Admin-Dokumentation
- [ ] Changelog aktualisiert

---

## Zeitplan-Zusammenfassung

| Tag | Phase | Aufgaben | Stunden |
|-----|-------|----------|---------|
| 1   | DB & Basis | Models, Migration, Controller-Basis | 8h |
| 2   | Templates | Liste, Detail, Forms, Workflow-Trigger | 8h |
| 3   | PDFs | Packliste-PDF, Lieferschein-PDF | 6h |
| 4   | Workflows | QC, Verpackung, Lieferschein-Erstellung | 6h |
| 5   | Signatur & Email | Canvas-Signatur, Email-Integration | 6h |
| 6   | Dashboard | Workflow-Widget, Übersichts-Seite | 6h |
| 7   | Lager & Finish | Lagerbuchung, Teillieferungen, Testing | 8h |

**Gesamt:** ~48 Stunden / 6-7 Arbeitstage

---

## Nächster Schritt

**Bereit zum Start?**

Wenn ja:
1. Backup der aktuellen Datenbank erstellen
2. Branch erstellen: `git checkout -b feature/workflow-integration`
3. Mit Task 1.1 beginnen (PackingList Model)

**Oder willst du noch etwas am Plan ändern?**
