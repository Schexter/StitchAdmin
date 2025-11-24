# Workflow-Integration Konzept
## StitchAdmin 2.0 - Durchgängiger ERP-Prozess

**Erstellt:** 2025-11-24
**Status:** Konzeptphase
**Ziel:** Vollständige Integration von Angebot → Produktion → Versand → Rechnung

---

## 1. Übersicht Workflow

```
┌─────────────┐
│   ANGEBOT   │
└──────┬──────┘
       │ akzeptiert
       ▼
┌─────────────┐
│   AUFTRAG   │
└──────┬──────┘
       │ Produktion starten
       ▼
┌─────────────┐
│ PRODUKTION  │
└──────┬──────┘
       │ Fertig
       ▼
┌─────────────┐     AUTOMATISCH ERSTELLT:
│  PACKLISTE  │ ◄── • PostEntry (Ausgang)
└──────┬──────┘     • Packliste PDF
       │             • Status: "Verpackung ausstehend"
       │ drucken + packen + "OK" markieren
       ▼
┌─────────────┐     AUTOMATISCH ERSTELLT:
│ LIEFERSCHEIN│ ◄── • Lieferschein PDF
└──────┬──────┘     • Status: "Versandbereit"
       │             • Optional: In Bulk legen
       │ Sendungsnummer erfassen
       ▼
┌─────────────┐     AUTOMATISCH:
│  VERSANDT   │ ◄── • Tracking Email an Kunde
└──────┬──────┘     • Lagerbuchung
       │             • Status: "Versendet"
       │ (manuell oder automatisch)
       ▼
┌─────────────┐     AUTOMATISCH/MANUELL:
│  RECHNUNG   │ ◄── • Rechnung aus Lieferschein
└─────────────┘     • Email an Kunde
                    • Status: "Abgeschlossen"
```

---

## 2. Datenbank-Erweiterungen

### 2.1 Neue Models

#### **PackingList** (Packliste)
```python
class PackingList(db.Model):
    __tablename__ = 'packing_lists'

    id = db.Column(db.Integer, primary_key=True)
    packing_list_number = db.Column(db.String(50), unique=True)  # PL-2024-001

    # Verknüpfungen
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    production_id = db.Column(db.Integer, db.ForeignKey('productions.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))

    # Teillieferungen (Cartons)
    carton_number = db.Column(db.Integer, default=1)  # Karton 1 von 3
    total_cartons = db.Column(db.Integer, default=1)  # Gesamt-Anzahl Kartons
    is_partial_delivery = db.Column(db.Boolean, default=False)

    # Status
    status = db.Column(db.String(20))  # draft, ready, packed, shipped

    # Inhalt (JSON)
    items = db.Column(db.Text)  # JSON Array der Artikel
    customer_notes = db.Column(db.Text)  # Kundenvorgaben
    packing_notes = db.Column(db.Text)  # Interne Notizen

    # Gewicht & Maße
    total_weight = db.Column(db.Float)  # kg
    package_length = db.Column(db.Float)  # cm
    package_width = db.Column(db.Float)
    package_height = db.Column(db.Float)

    # Qualitätskontrolle
    qc_performed = db.Column(db.Boolean, default=False)
    qc_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    qc_date = db.Column(db.DateTime)
    qc_notes = db.Column(db.Text)
    qc_photos = db.Column(db.Text)  # JSON Array mit Foto-Pfaden

    # Verpackung
    packed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    packed_at = db.Column(db.DateTime)
    packed_confirmed = db.Column(db.Boolean, default=False)

    # Lagerbuchung
    inventory_booked = db.Column(db.Boolean, default=False)
    inventory_booking_date = db.Column(db.DateTime)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # PDF
    pdf_path = db.Column(db.String(500))

    @property
    def carton_label(self):
        """Gibt 'Karton 1 von 3' zurück"""
        if self.total_cartons > 1:
            return f"Karton {self.carton_number} von {self.total_cartons}"
        return None
```

#### **DeliveryNote** (Lieferschein)
```python
class DeliveryNote(db.Model):
    __tablename__ = 'delivery_notes'

    id = db.Column(db.Integer, primary_key=True)
    delivery_note_number = db.Column(db.String(50), unique=True)  # LS-2024-001

    # Verknüpfungen
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    packing_list_id = db.Column(db.Integer, db.ForeignKey('packing_lists.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    post_entry_id = db.Column(db.Integer, db.ForeignKey('post_entries.id'))

    # Datum
    delivery_date = db.Column(db.Date)

    # Inhalt
    items = db.Column(db.Text)  # JSON Array
    notes = db.Column(db.Text)

    # Unterschrift (digital + gedruckt)
    delivery_method = db.Column(db.String(20))  # 'pickup' oder 'shipping'
    signature_type = db.Column(db.String(20))  # 'digital' oder 'printed'
    signature_image = db.Column(db.String(500))  # Pfad zur digitalen Signatur (PNG)
    signature_name = db.Column(db.String(200))  # Name des Unterzeichners
    signature_date = db.Column(db.DateTime)
    signature_device = db.Column(db.String(100))  # z.B. "iPad Pro", "Desktop"

    # Fotos (z.B. verpacktes Paket)
    photos = db.Column(db.Text)  # JSON Array mit Foto-Pfaden

    # Status
    status = db.Column(db.String(20))  # draft, ready, sent, delivered, signed

    # PDF
    pdf_path = db.Column(db.String(500))
    pdf_with_signature_path = db.Column(db.String(500))  # PDF mit eingebetteter Unterschrift

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    @property
    def is_signed(self):
        """Prüft ob Lieferschein unterschrieben wurde"""
        return self.signature_image is not None or self.signature_name is not None
```

### 2.2 Erweiterte bestehende Models

#### **Order** (Auftrag)
```python
# Neue Felder hinzufügen:
workflow_status = db.Column(db.String(50))  # offer, ordered, in_production,
                                             # packing, ready_to_ship, shipped,
                                             # invoiced, completed
packing_list_id = db.Column(db.Integer, db.ForeignKey('packing_lists.id'))
delivery_note_id = db.Column(db.Integer, db.ForeignKey('delivery_notes.id'))
invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'))

# Automatisierung
auto_create_packing_list = db.Column(db.Boolean, default=True)
auto_create_delivery_note = db.Column(db.Boolean, default=True)
auto_create_invoice = db.Column(db.Boolean, default=False)  # Manuell standard
```

#### **Production** (Produktion)
```python
# Neue Felder:
packing_list_created = db.Column(db.Boolean, default=False)
packing_list_id = db.Column(db.Integer, db.ForeignKey('packing_lists.id'))
```

#### **PostEntry** (Postbuch)
```python
# Neue Felder:
packing_list_id = db.Column(db.Integer, db.ForeignKey('packing_lists.id'))
delivery_note_id = db.Column(db.Integer, db.ForeignKey('delivery_notes.id'))
is_auto_created = db.Column(db.Boolean, default=False)
```

#### **CompanySettings** (Firmeneinstellungen)
```python
# Neue Felder für Workflow-Automatisierung:
# Rechnungserstellung
invoice_creation_mode = db.Column(db.String(20), default='manual')
    # Optionen: 'manual', 'after_delivery', 'delayed'
invoice_creation_delay_days = db.Column(db.Integer, default=0)
    # Bei 'delayed': Anzahl Tage nach Versand

# Workflow-Automatisierung
auto_create_packing_list = db.Column(db.Boolean, default=True)
auto_create_delivery_note = db.Column(db.Boolean, default=True)
auto_send_tracking_email = db.Column(db.Boolean, default=True)

# Qualitätskontrolle
require_qc_before_packing = db.Column(db.Boolean, default=False)
require_qc_photos = db.Column(db.Boolean, default=False)

# Lagerbuchung
auto_inventory_booking = db.Column(db.Boolean, default=True)
```

#### **Article** (Artikel) - falls noch nicht vorhanden
```python
# Neue Felder für Lagerverwaltung:
in_stock = db.Column(db.Boolean, default=True)  # True = Lagerartikel, False = Fremdware
stock_quantity = db.Column(db.Integer, default=0)
min_stock_level = db.Column(db.Integer, default=0)
```

---

## 3. Workflow-Automatisierung

### Phase 1: Produktion → Packliste
**Trigger:** Produktionsstatus → "completed"

**Automatische Aktionen:**
1. PackingList erstellen
   - Nummer generieren (PL-2024-001)
   - Artikel aus Auftrag übernehmen
   - Kundenvorgaben kopieren
   - Status: "ready"

2. PostEntry erstellen
   - Richtung: "outbound"
   - Verknüpfung zu Order + PackingList
   - Empfänger: Kundenadresse
   - Absender: Firmendaten
   - Status: "open"
   - is_auto_created: true

3. Packliste PDF generieren
   - Stückliste mit Artikeln
   - Kundenvorgaben
   - QK-Checkbox
   - Barcode/QR-Code für Tracking

4. Benachrichtigung
   - Toast-Message: "Packliste erstellt"
   - Optional: Email an Lager-Mitarbeiter

### Phase 2: Packliste → Lieferschein
**Trigger:** PackingList.packed_confirmed = True

**Automatische Aktionen:**
1. Qualitätskontrolle prüfen
   - Wenn qc_required: Erst nach QC fortfahren
   - Sonst: Direkt weiter

2. DeliveryNote erstellen
   - Nummer generieren (LS-2024-001)
   - Daten aus PackingList
   - Lieferdatum: heute
   - Status: "ready"

3. Lieferschein PDF generieren
   - Firmenlogo
   - Kundenadresse
   - Artikelliste
   - Unterschriftenfeld

4. PostEntry aktualisieren
   - delivery_note_id setzen
   - Status: "in_progress" (versandbereit)

5. Optional: Bulk zuordnen
   - Wenn mehrere Sendungen: In Bulk legen
   - Für Sammelversand

### Phase 3: Lieferschein → Versand
**Trigger:** PostEntry Tracking-Nummer erfasst

**Automatische Aktionen:**
1. PostEntry aktualisieren
   - Status: "completed"
   - shipped_at: jetzt

2. DeliveryNote aktualisieren
   - Status: "sent"

3. Order aktualisieren
   - workflow_status: "shipped"

4. Tracking-Email versenden
   - An Kunde
   - Mit Tracking-Link
   - Lieferschein als PDF anhängen

5. Optional: Lagerbuchung
   - Endprodukte ausbuchen
   - Wenn Lagerverwaltung aktiv

### Phase 4: Versand → Rechnung (optional automatisch)
**Trigger:** Manuell ODER X Tage nach Versand

**Automatische Aktionen:**
1. Rechnung erstellen
   - Aus Order/DeliveryNote
   - Artikel + Preise
   - Versandkosten
   - Zahlungsziel

2. Rechnung PDF generieren

3. Email an Kunde
   - Rechnung als PDF
   - Zahlungsinformationen

4. Order aktualisieren
   - workflow_status: "invoiced"

---

## 4. UI/UX Konzept

### 4.1 Produktions-Detailansicht
**Neu hinzufügen:**
```
┌─────────────────────────────────────┐
│ Produktion: PR-2024-123             │
│ Status: Fertig ✓                    │
├─────────────────────────────────────┤
│ 📦 Versandvorbereitung              │
│                                     │
│ [✓] Packliste erstellt: PL-2024-045│
│     → PDF anzeigen | Neu drucken   │
│                                     │
│ [ ] Qualitätskontrolle durchgeführt│
│     Geprüft von: ___________       │
│                                     │
│ [ ] Verpackung abgeschlossen       │
│     [Button: Als verpackt markieren]│
│                                     │
│ Status: Warte auf Verpackung       │
└─────────────────────────────────────┘
```

### 4.2 Packlisten-Übersicht (neu)
**Route:** `/shipping/packing-lists`

```
┌─────────────────────────────────────────────┐
│ 📦 Packlisten                              │
├─────────────────────────────────────────────┤
│                                             │
│ [Tabs]                                      │
│  • Bereit zur Verpackung (5)               │
│  • In Verpackung (2)                       │
│  • Versandbereit (12)                      │
│  • Alle                                     │
│                                             │
├─────────────────────────────────────────────┤
│ PL-2024-045  | Kunde A | 3 Artikel | Offen│
│              Auftrag: AU-2024-123          │
│              [QK durchführen] [Verpacken]  │
├─────────────────────────────────────────────┤
│ PL-2024-046  | Kunde B | 1 Artikel | QK OK│
│              Auftrag: AU-2024-125          │
│              [Verpackung abschließen]      │
└─────────────────────────────────────────────┘
```

### 4.3 Packlisten-Detailansicht
```
┌─────────────────────────────────────────┐
│ Packliste PL-2024-045                  │
│ Auftrag: AU-2024-123 | Kunde: Firma A │
├─────────────────────────────────────────┤
│ 📋 Artikelliste:                        │
│  1. Besticktes Poloshirt (10x)         │
│  2. Baseballcap mit Logo (5x)          │
│                                         │
│ 📝 Kundenvorgaben:                      │
│  "Bitte einzeln in Folie verpacken"    │
│                                         │
│ ✓ Qualitätskontrolle:                  │
│  [x] Stickqualität geprüft             │
│  [x] Farben korrekt                    │
│  [x] Vollständigkeit                   │
│  Geprüft von: Max M. am 24.11.2024    │
│                                         │
│ 📦 Verpackung:                          │
│  Gewicht: 2.5 kg                       │
│  Maße: 40x30x20 cm                     │
│  Verpackt von: ___________             │
│                                         │
│ [Button: Packliste drucken]            │
│ [Button: Als verpackt bestätigen] ✓    │
└─────────────────────────────────────────┘
```

### 4.4 Workflow-Status Widget
**Auf Dashboard anzeigen:**
```
┌─────────────────────────────────┐
│ 🔄 Workflow-Status              │
├─────────────────────────────────┤
│ Warte auf Verpackung:      5    │
│ Versandbereit:            12    │
│ Heute versenden:           3    │
│ Rechnung offen:            7    │
└─────────────────────────────────┘
```

---

## 5. PDF-Generierung

### 5.1 Packliste PDF
**Elemente:**
- Firmenlogo + Adresse
- "PACKLISTE" Überschrift
- Packlisten-Nummer + Datum
- Kundenname + Auftragsnummer
- Tabelle: Artikel, Menge, EAN/SKU
- Kundenvorgaben (hervorgehoben)
- QK-Checkliste mit Checkboxen
- Unterschriftenfeld Verpacker
- Barcode/QR-Code (für Scan-Workflow)

### 5.2 Lieferschein PDF
**Elemente:**
- Firmenlogo + Firmenadresse
- "LIEFERSCHEIN" Überschrift
- Lieferschein-Nummer + Datum
- Kundenadresse (Empfänger)
- Tabelle: Pos., Artikel, Menge, Einheit
- Gewicht + Anzahl Pakete
- Versandart + Tracking (falls vorhanden)
- Lieferbedingungen
- Unterschriftenfeld Empfänger
- Fußtext: "Dies ist kein steuerliches Dokument"

---

## 6. API/Integration-Punkte

### 6.1 Interne Workflows
```python
# Produktions-Controller
@production_bp.route('/<int:id>/complete', methods=['POST'])
def complete_production(id):
    production = Production.query.get_or_404(id)
    production.status = 'completed'

    # WORKFLOW TRIGGER
    if production.order and production.order.auto_create_packing_list:
        packing_list = create_packing_list_from_production(production)
        post_entry = create_post_entry_from_packing_list(packing_list)
        generate_packing_list_pdf(packing_list)

        flash(f'Packliste {packing_list.packing_list_number} erstellt', 'success')

    db.session.commit()
    return redirect(...)
```

### 6.2 Versanddienstleister API (später)
- **DHL Geschäftskundenversand API**
  - Versandlabel generieren
  - Tracking-Nummer abrufen
  - Abholung beauftragen

- **DPD Cloud API**
  - Label erstellen
  - Parcel Status abrufen

### 6.3 Webhooks/Events (später)
```python
# Event-System für Benachrichtigungen
emit_event('production.completed', production_id=id)
emit_event('packing_list.created', packing_list_id=pl.id)
emit_event('order.shipped', order_id=order.id)
```

---

## 7. Implementierungs-Phasen

### **Phase 1: Basis-Integration** (2-3 Tage)
- [ ] Datenbank-Models erstellen (PackingList, DeliveryNote)
- [ ] Migration-Script für neue Felder
- [ ] Packlisten-Controller + Routes
- [ ] Basis-Templates (Liste, Detail, Bearbeiten)
- [ ] Workflow: Produktion → Packliste (ohne PDF)
- [ ] PostEntry automatisch erstellen

### **Phase 2: PDFs + UI** (2-3 Tage)
- [ ] Packliste PDF Generator
- [ ] Lieferschein PDF Generator
- [ ] Druckansicht optimieren
- [ ] QK-Workflow implementieren
- [ ] Verpackungs-Workflow
- [ ] Status-Widget auf Dashboard

### **Phase 3: Automatisierung** (2-3 Tage)
- [ ] Workflow: Packliste → Lieferschein
- [ ] Workflow: Lieferschein → Versand
- [ ] Email-Benachrichtigungen
- [ ] Tracking-Email an Kunde
- [ ] Bulk-Integration

### **Phase 4: Rechnung-Integration** (2-3 Tage)
- [ ] Rechnung aus Lieferschein generieren
- [ ] Automatische/Manuelle Rechnungserstellung
- [ ] Rechnungs-Email
- [ ] Workflow-Status vollständig
- [ ] Übersichts-Dashboard

### **Phase 5: Erweitert** (optional, später)
- [ ] Lagerbuchungen automatisch
- [ ] Teillieferungen
- [ ] Retourenmanagement
- [ ] Versanddienstleister-API
- [ ] Digitale Unterschrift (Tablet)
- [ ] Barcode-Scanner-Integration
- [ ] Produktionszeiten-Tracking
- [ ] Statistiken + Reports

---

## 8. Technische Details

### 8.1 Nummerngenerierung
```python
def generate_packing_list_number():
    """Generiert PL-2024-001 Format"""
    year = datetime.now().year
    prefix = f"PL-{year}-"

    last = PackingList.query.filter(
        PackingList.packing_list_number.like(f"{prefix}%")
    ).order_by(PackingList.id.desc()).first()

    if last:
        last_num = int(last.packing_list_number.split('-')[-1])
        new_num = last_num + 1
    else:
        new_num = 1

    return f"{prefix}{new_num:04d}"
```

### 8.2 Workflow-Status-Maschine
```python
WORKFLOW_STATES = {
    'offer': {
        'next': ['ordered', 'rejected'],
        'label': 'Angebot',
        'color': 'info'
    },
    'ordered': {
        'next': ['in_production'],
        'label': 'Bestellt',
        'color': 'primary'
    },
    'in_production': {
        'next': ['packing'],
        'label': 'In Produktion',
        'color': 'warning'
    },
    'packing': {
        'next': ['ready_to_ship'],
        'label': 'Verpackung',
        'color': 'warning'
    },
    'ready_to_ship': {
        'next': ['shipped'],
        'label': 'Versandbereit',
        'color': 'info'
    },
    'shipped': {
        'next': ['invoiced'],
        'label': 'Versendet',
        'color': 'success'
    },
    'invoiced': {
        'next': ['completed'],
        'label': 'Rechnung erstellt',
        'color': 'success'
    },
    'completed': {
        'next': [],
        'label': 'Abgeschlossen',
        'color': 'secondary'
    }
}
```

### 8.3 Email-Templates
**Template: shipping_notification.html**
```html
Hallo {{ customer.name }},

Ihre Bestellung {{ order.order_number }} wurde heute versendet!

Sendungsnummer: {{ tracking_number }}
Versanddienstleister: {{ carrier }}
Voraussichtliche Zustellung: {{ expected_delivery }}

Tracking-Link: {{ tracking_url }}

Im Anhang finden Sie Ihren Lieferschein.

Mit freundlichen Grüßen
{{ company.name }}
```

---

## 9. Konfiguration

### 9.1 Einstellungen (Settings)
**Neue Settings-Sektion: Workflow-Automatisierung**

```
┌─────────────────────────────────────┐
│ Workflow-Automatisierung            │
├─────────────────────────────────────┤
│ [x] Packliste nach Produktion       │
│ [x] Lieferschein nach Verpackung    │
│ [ ] Rechnung nach Versand           │
│ [ ] Rechnung X Tage nach Versand: [7]│
│                                     │
│ Qualitätskontrolle:                 │
│ [x] QK vor Verpackung erforderlich  │
│ [ ] QK-Fotos erforderlich           │
│                                     │
│ Email-Benachrichtigungen:           │
│ [x] Tracking-Email an Kunde         │
│ [x] Packliste-Email an Lager        │
│ [ ] Tägliche Zusammenfassung        │
└─────────────────────────────────────┘
```

---

## 10. Testing-Checkliste

### Manuelle Tests:
- [ ] Produktion abschließen → Packliste wird erstellt
- [ ] Packliste anzeigen + drucken
- [ ] QK durchführen + bestätigen
- [ ] Verpackung bestätigen → Lieferschein wird erstellt
- [ ] Lieferschein anzeigen + drucken
- [ ] Tracking erfassen → Email wird versendet
- [ ] Rechnung manuell erstellen
- [ ] Kompletter Workflow: Angebot bis Rechnung

### Edge Cases:
- [ ] Produktion ohne Auftrag
- [ ] Mehrere Produktionen pro Auftrag (Teillieferungen)
- [ ] Kunde ohne Email-Adresse
- [ ] Versand ohne Tracking
- [ ] Abholung statt Versand

---

## 11. Entscheidungen (beantwortet 2025-11-24)

1. **Teillieferungen:** ✅ JA
   - Eigene Packliste pro Karton (Carton) generieren können
   - Ein Auftrag kann mehrere Packlisten haben
   - Jede Packliste → eigener Lieferschein
   - Implementierung: `carton_number` Feld in PackingList

2. **Rechnung:** ✅ Manuell als Standard
   - Immer manuell erstellen (Standard)
   - ABER: In Einstellungen konfigurierbar
   - Optionen: "Manuell", "Nach Lieferung", "X Tage nach Lieferung"
   - Implementierung: Settings-Feld `invoice_creation_mode`

3. **Lagerbuchung:** ✅ Jetzt implementieren
   - Lagerartikel: Ausbuchung bei Produktion
   - Fremdware (nicht auf Lager): In Stückliste aus Arbeitsauftrag übernehmen
   - Prüfung: Artikel hat `in_stock` Flag
   - Implementierung: Inventory-Modul erweitern

4. **Abholung:** ✅ Beides
   - Lieferschein zum Ausdrucken (PDF)
   - Digitale Unterschrift auf Tablet in der Anwendung
   - Implementierung: Canvas-basierte Signatur + Speichern als Bild
   - Unterschrift-Feld in DeliveryNote

5. **Retouren:** 🔜 Später (nicht Phase 1)
   - Gutschrift + Lager-Einbuchung
   - Separate Implementierung nach Basis-Workflow

6. **Priorität:** ✅ ALLES ist wichtig
   - PDF-Generierung: Hoch
   - Email-Automatisierung: Hoch
   - Status-Übersicht: Hoch
   - Digitale Unterschrift: Hoch
   - Lagerbuchung: Hoch

---

## 12. Nächste Schritte

**Diskutieren:**
1. Offene Fragen klären
2. Prioritäten festlegen
3. Phase 1 Umfang final definieren

**Danach:**
- Detailliertes Task-Board erstellen
- Datenbank-Schema final festlegen
- Mit Implementierung Phase 1 starten

---

**Notizen:**
- Dieses Dokument ist "living document" - wird während Entwicklung aktualisiert
- Bei Änderungen: Datum + Änderung dokumentieren
