# StitchAdmin 2.0 - Klassen-Übersicht

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Version:** 2.0.0  
**Stand:** 10. November 2025

---

## 📋 Inhaltsverzeichnis

1. [Model-Klassen (Datenbank)](#model-klassen-datenbank)
2. [Controller-Klassen (Blueprints)](#controller-klassen-blueprints)
3. [Service-Klassen (Business-Logic)](#service-klassen-business-logic)
4. [Utility-Klassen (Hilfsfunktionen)](#utility-klassen-hilfsfunktionen)
5. [Form-Klassen (WTForms)](#form-klassen-wtforms)

---

## 🗄️ Model-Klassen (Datenbank)

Alle Models befinden sich in `src/models/models.py` und weiteren Model-Dateien.

---

### 1. User (Benutzer)

**Datei:** `src/models/models.py`  
**Tabelle:** `users`  
**Zweck:** Authentifizierung und Benutzerverwaltung

#### Attribute

| Attribut | Typ | Nullable | Beschreibung |
|----------|-----|----------|--------------|
| `id` | Integer | Nein | Primary Key (auto-increment) |
| `username` | String(80) | Nein | Eindeutiger Benutzername |
| `email` | String(120) | Nein | Eindeutige E-Mail |
| `password_hash` | String(255) | Nein | Gehashtes Passwort |
| `is_active` | Boolean | Nein | Ist Benutzer aktiv? (default: True) |
| `is_admin` | Boolean | Nein | Ist Administrator? (default: False) |
| `created_at` | DateTime | Nein | Erstellungsdatum |
| `last_login` | DateTime | Ja | Letzter Login |

#### Methoden

```python
def set_password(password: str) -> None:
    """Hasht und speichert Passwort mit werkzeug.security"""
    pass

def check_password(password: str) -> bool:
    """Überprüft Passwort gegen gespeicherten Hash"""
    pass
```

#### Relationships

```python
activities = relationship('ActivityLog', backref='user_obj', lazy='dynamic')
```

#### Verwendung

```python
# Neuen Benutzer anlegen
user = User(username='hans', email='hans@example.com', is_admin=True)
user.set_password('geheim123')
db.session.add(user)
db.session.commit()

# Login prüfen
user = User.query.filter_by(username='hans').first()
if user and user.check_password('geheim123'):
    login_user(user)
```

---

### 2. Customer (Kunde)

**Datei:** `src/models/models.py`  
**Tabelle:** `customers`  
**Zweck:** Privat- und Geschäftskunden

#### Attribute

| Attribut | Typ | Beschreibung |
|----------|-----|--------------|
| **Identifikation** | | |
| `id` | String(50) | Primary Key (CUST-YYYYMMDD-XXXX) |
| `customer_type` | String(20) | 'private' oder 'business' |
| **Privatkunden** | | |
| `first_name` | String(100) | Vorname |
| `last_name` | String(100) | Nachname |
| `birth_date` | Date | Geburtsdatum |
| **Geschäftskunden** | | |
| `company_name` | String(200) | Firmenname |
| `contact_person` | String(100) | Ansprechpartner |
| `department` | String(100) | Abteilung |
| `position` | String(100) | Position |
| `tax_id` | String(50) | Steuernummer |
| `vat_id` | String(50) | Umsatzsteuer-ID |
| **Kontaktdaten** | | |
| `email` | String(120) | E-Mail-Adresse |
| `phone` | String(50) | Telefon |
| `mobile` | String(50) | Mobiltelefon |
| **Adresse** | | |
| `street` | String(200) | Straße |
| `house_number` | String(20) | Hausnummer |
| `postal_code` | String(20) | Postleitzahl |
| `city` | String(100) | Stadt |
| `country` | String(100) | Land (default: 'Deutschland') |
| **Sonstiges** | | |
| `newsletter` | Boolean | Newsletter-Anmeldung |
| `notes` | Text | Notizen |
| **Metadaten** | | |
| `created_at` | DateTime | Erstellungsdatum |
| `created_by` | String(80) | Erstellt von |
| `updated_at` | DateTime | Änderungsdatum |
| `updated_by` | String(80) | Geändert von |

#### Properties

```python
@property
def display_name(self) -> str:
    """
    Gibt formatierten Anzeigenamen zurück
    Privat: "Vorname Nachname"
    Geschäft: "Firmenname"
    """
    if self.customer_type == 'business':
        return self.company_name or 'Unbekannte Firma'
    else:
        return f"{self.first_name or ''} {self.last_name or ''}".strip() or 'Unbekannt'
```

#### Methoden

```python
def get(key: str, default=None):
    """Dictionary-kompatible Getter-Methode"""
    return getattr(self, key, default)
```

#### Relationships

```python
orders = relationship('Order', backref='customer', lazy='dynamic')
```

#### Beispiel

```python
# Privatkunden anlegen
customer = Customer(
    id='CUST-20251110-0001',
    customer_type='private',
    first_name='Max',
    last_name='Mustermann',
    email='max@example.com',
    phone='0123456789',
    street='Musterstraße',
    house_number='1',
    postal_code='12345',
    city='Musterstadt'
)

# Geschäftskunden anlegen
business = Customer(
    id='CUST-20251110-0002',
    customer_type='business',
    company_name='Mustermann GmbH',
    contact_person='Max Mustermann',
    email='info@mustermann-gmbh.de',
    tax_id='12345678',
    vat_id='DE123456789'
)
```

---

### 3. Article (Artikel)

**Datei:** `src/models/models.py`  
**Tabelle:** `articles`  
**Zweck:** Textil-Artikel mit Varianten und Preiskalkulation

#### Attribute

| Attribut | Typ | Beschreibung |
|----------|-----|--------------|
| **Identifikation** | | |
| `id` | String(50) | Primary Key |
| `article_number` | String(100) | L-Shop Artikelnummer (unique) |
| `name` | String(200) | Artikelname |
| `description` | Text | Beschreibung |
| **Kategorisierung** | | |
| `category_id` | Integer | FK → ProductCategory |
| `brand_id` | Integer | FK → Brand |
| `category` | String(100) | **Deprecated** - Legacy-Feld |
| `brand` | String(100) | **Deprecated** - Legacy-Feld |
| **Produktdetails** | | |
| `material` | String(100) | Material (z.B. "100% Baumwolle") |
| `weight` | Float | Gewicht in Gramm |
| `color` | String(50) | Farbe |
| `size` | String(50) | Größe |
| **Einkaufspreise (EK)** | | |
| `purchase_price_single` | Float | EK Einzelpreis |
| `purchase_price_carton` | Float | EK Kartonpreis |
| `purchase_price_10carton` | Float | EK 10-Karton-Preis |
| **Verkaufspreise (VK)** | | |
| `price` | Float | VK aktuell (kann manuell überschrieben werden) |
| `price_calculated` | Float | VK kalkuliert (EK × Faktor) |
| `price_recommended` | Float | VK empfohlen (EK × Faktor) |
| **Lager** | | |
| `stock` | Integer | Lagerbestand |
| `min_stock` | Integer | Mindestbestand |
| `location` | String(100) | Lagerort |
| **Lieferant** | | |
| `supplier` | String(100) | Lieferantenname |
| `supplier_article_number` | String(100) | Herstellernummer |
| **Status** | | |
| `active` | Boolean | Ist aktiv? |
| **L-Shop spezifisch** | | |
| `product_type` | String(100) | Produkttyp |
| `manufacturer_number` | String(100) | Herstellernummer |
| `has_variants` | Boolean | Hat Varianten? |
| `units_per_carton` | Integer | Stück pro Karton |
| `catalog_page_texstyles` | Integer | Katalogseite Texstyles |
| `catalog_page_corporate` | Integer | Katalogseite Corporate |
| `catalog_page_wahlbuch` | Integer | Katalogseite Wahlbuch |
| **Metadaten** | | |
| `created_at`, `created_by` | DateTime, String | Erstellung |
| `updated_at`, `updated_by` | DateTime, String | Änderung |

#### Methoden

```python
def calculate_prices(use_new_system=True) -> dict:
    """
    Berechnet VK-Preise basierend auf EK und Kalkulationsregeln
    
    Returns:
        dict: {
            'base_price': float,
            'calculated': float,
            'recommended': float,
            'calculated_with_tax': float,
            'recommended_with_tax': float,
            'tax_rate': float,
            'rule_used': str
        }
    """
    pass

def _get_best_purchase_price() -> float:
    """Ermittelt den besten (niedrigsten) EK-Preis"""
    if self.purchase_price_single > 0:
        return self.purchase_price_single
    elif self.purchase_price_carton > 0:
        return self.purchase_price_carton
    elif self.purchase_price_10carton > 0:
        return self.purchase_price_10carton
    return 0

def _calculate_prices_legacy() -> dict:
    """Fallback-Methode für Preiskalkulation"""
    pass

def get(key: str, default=None):
    """Dictionary-kompatibel"""
    return getattr(self, key, default)
```

#### Relationships

```python
order_items = relationship('OrderItem', backref='article', lazy='dynamic')
variants = relationship('ArticleVariant', back_populates='article', lazy='dynamic', cascade='all, delete-orphan')
category_obj = relationship('ProductCategory', backref='articles')
brand_obj = relationship('Brand', backref='articles')
```

#### Preiskalkulation-Beispiel

```python
# Artikel mit EK-Preisen
article = Article(
    article_number='TSH-001',
    name='T-Shirt Basic',
    purchase_price_single=5.50,  # EK Einzelpreis
    purchase_price_carton=4.80,  # EK Kartonpreis (20 Stück)
    purchase_price_10carton=4.20  # EK 10-Karton-Preis (200 Stück)
)

# Preise berechnen (mit neuer Regel-basierter Kalkulation)
result = article.calculate_prices(use_new_system=True)
# result = {
#     'base_price': 5.50,          # Niedrigster EK
#     'calculated': 9.85,          # EK × 1.5 × 1.19 (inkl. 19% MwSt)
#     'recommended': 13.09,        # EK × 2.0 × 1.19 (inkl. 19% MwSt)
#     'tax_rate': 19.0,
#     'rule_used': 'Standard Textilien'
# }

# VK-Preise wurden automatisch gesetzt
print(f"VK kalkuliert: {article.price_calculated}€")  # 9.85
print(f"VK empfohlen: {article.price_recommended}€")  # 13.09
```

---

### 4. ArticleVariant (Artikel-Variante)

**Datei:** `src/models/article_variant.py`  
**Tabelle:** `article_variants`  
**Zweck:** Größen- und Farb-Varianten von Artikeln

#### Attribute

| Attribut | Typ | Beschreibung |
|----------|-----|--------------|
| `id` | Integer | Primary Key |
| `article_id` | String(50) | FK → Article |
| `size` | String(20) | Größe (XS, S, M, L, XL, etc.) |
| `color` | String(50) | Farbe |
| `color_hex` | String(7) | Hex-Farbcode (#RRGGBB) |
| `ean` | String(20) | EAN-Barcode |
| `stock` | Integer | Lagerbestand dieser Variante |
| `price_modifier` | Float | Preisaufschlag (default 0.0) |
| `active` | Boolean | Ist aktiv? |

#### Relationships

```python
article = relationship('Article', back_populates='variants')
```

#### Beispiel

```python
# T-Shirt mit Varianten
tshirt = Article(article_number='TSH-001', name='T-Shirt Basic')

# Varianten hinzufügen
variant_s_red = ArticleVariant(
    article_id='TSH-001',
    size='S',
    color='Rot',
    color_hex='#FF0000',
    stock=50,
    ean='4012345678901'
)

variant_m_blue = ArticleVariant(
    article_id='TSH-001',
    size='M',
    color='Blau',
    color_hex='#0000FF',
    stock=30,
    ean='4012345678902'
)

tshirt.variants.append(variant_s_red)
tshirt.variants.append(variant_m_blue)
```

---

### 5. Order (Auftrag)

**Datei:** `src/models/models.py`  
**Tabelle:** `orders`  
**Zweck:** Stickerei- und Druck-Aufträge

#### Attribute

| Attribut | Typ | Beschreibung |
|----------|-----|--------------|
| **Identifikation** | | |
| `id` | String(50) | Primary Key |
| `customer_id` | String(50) | FK → Customer |
| `order_number` | String(50) | Auftragsnummer (unique) |
| `order_type` | String(20) | 'embroidery'/'printing'/'dtf'/'combined' |
| `status` | String(50) | Auftragsstatus (siehe unten) |
| **Allgemein** | | |
| `description` | Text | Beschreibung |
| `internal_notes` | Text | Interne Notizen |
| `customer_notes` | Text | Kunden-Notizen |
| **Stickerei-Details** | | |
| `stitch_count` | Integer | Stichzahl |
| `design_width_mm` | Float | Design-Breite (mm) |
| `design_height_mm` | Float | Design-Höhe (mm) |
| `embroidery_position` | String(100) | Position (Brust/Rücken/etc.) |
| `embroidery_size` | String(50) | Größe |
| `thread_colors` | Text | Farbenliste (komma-getrennt) |
| `selected_threads` | Text | Ausgewählte Garne (JSON) |
| **Druck-Details** | | |
| `print_width_cm` | Float | Druck-Breite (cm) |
| `print_height_cm` | Float | Druck-Höhe (cm) |
| `print_method` | String(50) | DTG/DTF/Siebdruck |
| `ink_coverage_percent` | Integer | Farbdeckung (%) |
| `print_colors` | Text | Farbenliste (JSON) |
| **Design-Workflow** | | |
| `design_status` | String(50) | Design-Status (siehe unten) |
| `design_supplier_id` | String(50) | FK → Supplier |
| `design_order_date` | Date | Bestelldatum Design |
| `design_expected_date` | Date | Erwartetes Lieferdatum |
| `design_received_date` | Date | Erhaltenes Datum |
| `design_order_notes` | Text | Notizen zur Design-Bestellung |
| **Dateien** | | |
| `design_file` | String(255) | **Deprecated** |
| `design_file_path` | String(255) | Vollständiger Pfad zur Design-Datei |
| `design_thumbnail_path` | String(255) | Pfad zum Thumbnail |
| `production_file` | String(255) | Produktionsdatei |
| **Preise** | | |
| `total_price` | Float | Gesamtpreis |
| `deposit_amount` | Float | Anzahlung |
| `discount_percent` | Float | Rabatt (%) |
| **Termine** | | |
| `due_date` | DateTime | Liefertermin |
| `rush_order` | Boolean | Eilauftrag? |
| **Produktion** | | |
| `assigned_machine_id` | String(50) | FK → Machine |
| `production_start` | DateTime | Produktionsstart |
| `production_end` | DateTime | Produktionsende |
| `production_minutes` | Integer | Produktionsdauer |
| **Metadaten** | | |
| `created_at`, `created_by` | DateTime, String | Erstellung |
| `updated_at`, `updated_by` | DateTime, String | Änderung |
| `completed_at`, `completed_by` | DateTime, String | Abschluss |

#### Status-Werte

**Auftragsstatus (`status`):**
- `new` - Neu erfasst
- `accepted` - Angenommen
- `in_progress` - In Bearbeitung
- `production` - In Produktion
- `ready` - Fertig (Abholbereit)
- `completed` - Abgeschlossen
- `cancelled` - Storniert

**Design-Status (`design_status`):**
- `none` - Kein Design
- `customer_provided` - Kunde hat geliefert
- `needs_order` - Muss bestellt werden
- `ordered` - Bei Lieferant bestellt
- `received` - Vom Lieferanten erhalten
- `ready` - Produktionsbereit

#### Methoden

```python
def get_selected_threads() -> list:
    """Gibt ausgewählte Garne als Liste zurück (JSON → Python)"""
    if self.selected_threads:
        return json.loads(self.selected_threads)
    return []

def set_selected_threads(threads_list: list) -> None:
    """Speichert Garne als JSON"""
    self.selected_threads = json.dumps(threads_list)

def can_start_production() -> tuple[bool, str]:
    """
    Prüft ob Produktion starten kann
    Returns: (can_start, reason)
    """
    if self.design_status not in ['customer_provided', 'ready']:
        return False, "Design nicht verfügbar"
    return True, "OK"

def get_design_status_display() -> str:
    """Benutzerfreundlicher Design-Status"""
    status_map = {
        'none': 'Kein Design',
        'customer_provided': 'Kunde bereitgestellt',
        'needs_order': 'Muss bestellt werden',
        'ordered': 'Bei Lieferant bestellt',
        'received': 'Vom Lieferanten erhalten',
        'ready': 'Produktionsbereit'
    }
    return status_map.get(self.design_status, self.design_status)

def get_design_status_badge_class() -> str:
    """Bootstrap-Badge-Klasse für Design-Status"""
    badge_map = {
        'none': 'bg-danger',
        'customer_provided': 'bg-success',
        'needs_order': 'bg-warning',
        'ordered': 'bg-info',
        'received': 'bg-primary',
        'ready': 'bg-success'
    }
    return badge_map.get(self.design_status, 'bg-secondary')

def has_design_file() -> bool:
    """Prüft ob Design-Datei vorhanden"""
    return bool(self.design_file_path or self.design_file)

def needs_design_order() -> bool:
    """Muss Design bestellt werden?"""
    return self.design_status == 'needs_order'

def is_design_in_progress() -> bool:
    """Design-Bestellung im Gange?"""
    return self.design_status == 'ordered'

def is_design_ready() -> bool:
    """Design produktionsbereit?"""
    return self.design_status in ['customer_provided', 'ready']
```

#### Relationships

```python
customer = relationship('Customer', backref='orders')
items = relationship('OrderItem', backref='order', lazy='dynamic', cascade='all, delete-orphan')
status_history = relationship('OrderStatusHistory', backref='order', lazy='dynamic', cascade='all, delete-orphan')
shipments = relationship('Shipment', backref='order', lazy='dynamic')
production_schedules = relationship('ProductionSchedule', backref='order')
assigned_machine = relationship('Machine', backref='orders', foreign_keys=[assigned_machine_id])
design_supplier = relationship('Supplier', backref='design_orders', foreign_keys=[design_supplier_id])
```

---

### 6. OrderItem (Auftragsposition)

**Datei:** `src/models/models.py`  
**Tabelle:** `order_items`  
**Zweck:** Textilien pro Auftrag

#### Attribute

| Attribut | Typ | Beschreibung |
|----------|-----|--------------|
| `id` | Integer | Primary Key |
| `order_id` | String(50) | FK → Order |
| `article_id` | String(50) | FK → Article |
| `quantity` | Integer | Menge |
| `unit_price` | Float | Stückpreis |
| `textile_size` | String(20) | Größe |
| `textile_color` | String(50) | Farbe |
| `position_details` | Text | Details |
| **Lieferanten-Bestellung** | | |
| `supplier_order_status` | String(50) | 'none'/'to_order'/'ordered'/'delivered' |
| `supplier_order_id` | String(50) | FK → SupplierOrder |
| `supplier_order_date` | Date | Bestelldatum |
| `supplier_expected_date` | Date | Erwartetes Datum |
| `supplier_delivered_date` | Date | Lieferdatum |
| `supplier_order_notes` | Text | Notizen |

#### Relationships

```python
order = relationship('Order', backref='items')
article = relationship('Article', backref='order_items')
supplier_order = relationship('SupplierOrder', backref='linked_order_items', foreign_keys=[supplier_order_id])
```

---

### 7. Thread (Stickgarn)

**Datei:** `src/models/models.py`  
**Tabelle:** `threads`  
**Zweck:** Stickgarn-Verwaltung mit Farben und Bestand

#### Attribute

| Attribut | Typ | Beschreibung |
|----------|-----|--------------|  
| `id` | String(50) | Primary Key |
| `brand` | String(100) | Marke (Madeira/Gütermann/etc.) |
| `article_number` | String(50) | Artikelnummer |
| `color_number` | String(20) | Farbnummer |
| `color_name` | String(100) | Farbname |
| `color_hex` | String(7) | Hex-Code (#RRGGBB) |
| `material` | String(50) | Material (Polyester/Rayon) |
| `thickness` | String(20) | Stärke (40wt/60wt) |
| `length_meters` | Integer | Länge in Meter pro Spule |
| `stock` | Integer | Lagerbestand (Spulen) |
| `min_stock` | Integer | Mindestbestand |
| `purchase_price` | Float | Einkaufspreis |
| `price` | Float | Verkaufspreis |
| `location` | String(100) | Lagerort |
| `active` | Boolean | Ist aktiv? |

#### Beispiel

```python
# Madeira Polyneon Garn
thread = Thread(
    id='THR-001',
    brand='Madeira',
    article_number='POLYNEON40',
    color_number='1800',
    color_name='Schneeweiß',
    color_hex='#FFFFFF',
    material='Polyester',
    thickness='40wt',
    length_meters=1000,
    stock=50,
    min_stock=10,
    purchase_price=2.50,
    price=4.99
)
```

---

### 8. Machine (Stickmaschine)

**Datei:** `src/models/models.py`  
**Tabelle:** `machines`  
**Zweck:** Stickmaschinen-Verwaltung mit Auslastung

#### Attribute

| Attribut | Typ | Beschreibung |
|----------|-----|--------------|  
| `id` | String(50) | Primary Key |
| `name` | String(100) | Maschinenname |
| `machine_type` | String(50) | 'embroidery'/'printing'/'dtf' |
| `brand` | String(100) | Hersteller |
| `model` | String(100) | Modellbezeichnung |
| `serial_number` | String(100) | Seriennummer |
| `heads` | Integer | Anzahl Köpfe |
| `needles_per_head` | Integer | Nadeln pro Kopf |
| `max_stitch_speed` | Integer | Max. Stichgeschwindigkeit |
| `max_embroidery_area_width` | Integer | Max. Breite (mm) |
| `max_embroidery_area_height` | Integer | Max. Höhe (mm) |
| `active` | Boolean | Ist aktiv? |
| `location` | String(100) | Standort |

---

### 9. Supplier (Lieferant)

**Datei:** `src/models/models.py`  
**Tabelle:** `suppliers`  
**Zweck:** Lieferanten (Textilien, Designs)

#### Attribute

| Attribut | Typ | Beschreibung |
|----------|-----|--------------|  
| `id` | String(50) | Primary Key |
| `supplier_type` | String(50) | 'textile'/'design'/'both' |
| `name` | String(200) | Name |
| `contact_person` | String(100) | Ansprechpartner |
| `email` | String(120) | E-Mail |
| `phone` | String(50) | Telefon |
| `website` | String(200) | Website |
| `street`, `city`, `postal_code` | String | Adresse |
| `payment_terms` | String(100) | Zahlungsbedingungen |
| `notes` | Text | Notizen |

---

### 10. ProductionSchedule (Produktionsplan)

**Datei:** `src/models/models.py`  
**Tabelle:** `production_schedules`  
**Zweck:** Kapazitätsplanung

#### Attribute

| Attribut | Typ | Beschreibung |
|----------|-----|--------------|  
| `id` | Integer | Primary Key |
| `order_id` | String(50) | FK → Order |
| `machine_id` | String(50) | FK → Machine |
| `scheduled_start` | DateTime | Geplanter Start |
| `scheduled_end` | DateTime | Geplantes Ende |
| `estimated_duration` | Integer | Geschätzte Dauer (min) |
| `status` | String(50) | 'planned'/'in_progress'/'completed'/'cancelled' |
| `priority` | Integer | Priorität (1-5) |

---

### 11. Invoice (Rechnung)

**Datei:** `src/models/models.py`  
**Tabelle:** `invoices`  
**Zweck:** Rechnungsstellung

#### Attribute

| Attribut | Typ | Beschreibung |
|----------|-----|--------------|  
| `id` | String(50) | Primary Key |
| `invoice_number` | String(50) | Rechnungsnummer (unique) |
| `customer_id` | String(50) | FK → Customer |
| `order_id` | String(50) | FK → Order |
| `invoice_type` | String(20) | 'invoice'/'credit_note'/'advance' |
| `invoice_date` | Date | Rechnungsdatum |
| `due_date` | Date | Fälligkeitsdatum |
| `status` | String(50) | 'draft'/'sent'/'paid'/'overdue'/'cancelled' |
| `subtotal` | Float | Nettosumme |
| `tax_amount` | Float | Steuerbetrag |
| `total_amount` | Float | Bruttosumme |
| `paid_amount` | Float | Gezahlter Betrag |
| `payment_date` | Date | Zahlungsdatum |
| `payment_method` | String(50) | Zahlungsmethode |
| `notes` | Text | Notizen |

---

### 12. Shipment (Versand)

**Datei:** `src/models/models.py`  
**Tabelle:** `shipments`  
**Zweck:** Versandmanagement

#### Attribute

| Attribut | Typ | Beschreibung |
|----------|-----|--------------|  
| `id` | String(50) | Primary Key |
| `shipment_number` | String(50) | Versandnummer |
| `order_id` | String(50) | FK → Order |
| `carrier` | String(100) | Versanddienstleister |
| `tracking_number` | String(100) | Sendungsnummer |
| `shipment_date` | Date | Versanddatum |
| `estimated_delivery` | Date | Geschätzte Zustellung |
| `actual_delivery` | Date | Tatsächliche Zustellung |
| `status` | String(50) | 'pending'/'shipped'/'in_transit'/'delivered'/'returned' |
| `shipping_cost` | Float | Versandkosten |
| `weight_kg` | Float | Gewicht (kg) |
| `notes` | Text | Notizen |

---

### 13. DesignFile (Design-Archiv)

**Datei:** `src/models/models.py`  
**Tabelle:** `design_files`  
**Zweck:** Zentrales Design-Archiv

#### Attribute

| Attribut | Typ | Beschreibung |
|----------|-----|--------------|  
| `id` | String(50) | Primary Key |
| `file_name` | String(255) | Dateiname |
| `file_path` | String(500) | Vollständiger Pfad |
| `file_type` | String(50) | Dateityp (DST/EMB/PES) |
| `file_size` | Integer | Dateigröße (bytes) |
| `thumbnail_path` | String(500) | Thumbnail-Pfad |
| `design_name` | String(200) | Design-Name |
| `design_number` | String(100) | Design-Nummer |
| `category` | String(100) | Kategorie |
| `tags` | String(500) | Tags (komma-getrennt) |
| `stitch_count` | Integer | Stichzahl |
| `width_mm` | Float | Breite (mm) |
| `height_mm` | Float | Höhe (mm) |
| `color_count` | Integer | Anzahl Farben |
| `notes` | Text | Notizen |
| `customer_id` | String(50) | FK → Customer (optional) |
| `created_at`, `created_by` | DateTime, String | Erstellung |

---

### 14. ActivityLog (Aktivitätsprotokoll)

**Datei:** `src/models/models.py`  
**Tabelle:** `activity_log`  
**Zweck:** Audit-Trail für alle Aktionen

#### Attribute

| Attribut | Typ | Beschreibung |
|----------|-----|--------------|  
| `id` | Integer | Primary Key |
| `timestamp` | DateTime | Zeitstempel |
| `user_id` | Integer | FK → User |
| `action` | String(100) | Aktion (created/updated/deleted) |
| `entity_type` | String(50) | Entitätstyp (customer/order/article) |
| `entity_id` | String(50) | Entitäts-ID |
| `description` | Text | Beschreibung |
| `changes` | Text | JSON mit Änderungen (vorher/nachher) |

---

### 15. Settings (Einstellungen)

**Datei:** `src/models/models.py`  
**Tabelle:** `settings`  
**Zweck:** Systemweite Einstellungen

#### Attribute

| Attribut | Typ | Beschreibung |
|----------|-----|--------------|  
| `id` | Integer | Primary Key |
| `key` | String(100) | Einstellungs-Schlüssel (unique) |
| `value` | Text | Wert (JSON-serialisiert) |
| `category` | String(50) | Kategorie (company/invoice/production) |
| `description` | String(255) | Beschreibung |
| `updated_at` | DateTime | Änderungsdatum |
| `updated_by` | String(80) | Geändert von |

#### Methoden

```python
@staticmethod
def get_setting(key: str, default=None):
    """Liest eine Einstellung aus der DB"""
    setting = Settings.query.filter_by(key=key).first()
    if setting:
        return json.loads(setting.value)
    return default

@staticmethod
def set_setting(key: str, value, category: str = 'general', description: str = '', user: str = 'system'):
    """Speichert eine Einstellung in der DB"""
    setting = Settings.query.filter_by(key=key).first()
    if setting:
        setting.value = json.dumps(value)
        setting.updated_at = datetime.now()
        setting.updated_by = user
    else:
        setting = Settings(
            key=key,
            value=json.dumps(value),
            category=category,
            description=description,
            updated_by=user
        )
        db.session.add(setting)
    db.session.commit()
```

---

## 🎮 Controller-Klassen (Blueprints)

Alle Controller sind Flask Blueprints in `src/controllers/`

### Blueprint-Struktur

```python
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from src.models.models import db, Customer

# Blueprint definieren
customer_bp = Blueprint('customers', __name__, url_prefix='/customers')

# Routen definieren
@customer_bp.route('/')
@login_required
def index():
    """Kundenliste"""
    customers = Customer.query.all()
    return render_template('customers/index.html', customers=customers)

@customer_bp.route('/<string:id>')
@login_required
def show(id):
    """Kunden-Details"""
    customer = Customer.query.get_or_404(id)
    return render_template('customers/show.html', customer=customer)

# Weitere Routen...
```

### Aktuelle Controller (DB-basiert)

| Controller | Blueprint-Name | URL-Prefix | Zweck |
|------------|----------------|------------|-------|
| `customer_controller_db.py` | `customers` | `/customers` | Kundenverwaltung |
| `article_controller_db.py` | `articles` | `/articles` | Artikelverwaltung |
| `order_controller_db.py` | `orders` | `/orders` | Auftragsverwaltung |
| `thread_controller_db.py` | `threads` | `/threads` | Garnverwaltung |
| `thread_controller_unified.py` | `threads_unified` | `/threads_unified` | Modernisierter Garn-Controller |
| `machine_controller_db.py` | `machines` | `/machines` | Maschinenverwaltung |
| `production_controller_db.py` | `production` | `/production` | Produktionsplanung |
| `shipping_controller_db.py` | `shipping` | `/shipping` | Versandverwaltung |
| `supplier_controller_db.py` | `suppliers` | `/suppliers` | Lieferantenverwaltung |
| `design_controller.py` | `design` | `/design` | Design-Archiv |
| `invoice_controller.py` | `invoices` | `/invoices` | Rechnungswesen |
| `settings_controller_unified.py` | `settings` | `/settings` | Einstellungen |

### Standard-Routen pro Controller

Jeder Controller implementiert üblicherweise:

| Route | Methode | Zweck |
|-------|---------|-------|
| `/` | GET | Liste/Index |
| `/new` | GET | Neues Formular |
| `/create` | POST | Datensatz erstellen |
| `/<id>` | GET | Details anzeigen |
| `/<id>/edit` | GET | Bearbeiten-Formular |
| `/<id>/update` | POST | Datensatz aktualisieren |
| `/<id>/delete` | POST | Datensatz löschen |

---

## 🔧 Service-Klassen (Business-Logic)

### DSTAnalyzer (DST-Datei-Analyse)

**Datei:** `src/services/dst_analyzer.py`  
**Zweck:** Stickdateien (DST) analysieren und auslesen

#### Methoden

```python
class DSTAnalyzer:
    
    @staticmethod
    def analyze_dst_file(file_path: str) -> dict:
        """
        Analysiert DST-Datei und extrahiert Metadaten
        
        Returns:
            dict: {
                'stitch_count': int,
                'color_count': int,
                'width_mm': float,
                'height_mm': float,
                'bounding_box': dict,
                'estimated_time_minutes': int
            }
        """
        pass
    
    @staticmethod
    def create_thumbnail(dst_path: str, output_path: str, size=(200, 200)):
        """Erstellt Thumbnail von DST-Datei"""
        pass
```

---

### PriceCalculator (Preiskalkulation)

**Datei:** `src/services/price_calculator.py`  
**Zweck:** Zentrale Preisberechnungen

#### Methoden

```python
class PriceCalculator:
    
    @staticmethod
    def calculate_article_price(article: Article, use_new_system: bool = True) -> dict:
        """Berechnet VK-Preis für Artikel"""
        pass
    
    @staticmethod
    def calculate_embroidery_price(stitch_count: int, color_count: int) -> float:
        """Berechnet Stickpreis basierend auf Stichen und Farben"""
        pass
    
    @staticmethod
    def calculate_order_total(order: Order) -> float:
        """Berechnet Gesamtsumme eines Auftrags"""
        pass
```

---

## 🛠️ Utility-Klassen (Hilfsfunktionen)

### ID-Generator

**Datei:** `src/utils/id_generator.py`

```python
from datetime import datetime

def generate_id(prefix: str) -> str:
    """
    Generiert eindeutige ID mit Prefix und Zeitstempel
    
    Beispiele:
        generate_id('CUST') → 'CUST-20251110-0001'
        generate_id('ORD') → 'ORD-20251110-0042'
    """
    timestamp = datetime.now().strftime('%Y%m%d')
    # Zähler aus DB oder Session holen
    counter = get_next_counter(prefix, timestamp)
    return f"{prefix}-{timestamp}-{counter:04d}"
```

---

### File-Handler

**Datei:** `src/utils/file_handler.py`

```python
class FileHandler:
    
    @staticmethod
    def save_upload(file, upload_type: str) -> str:
        """
        Speichert hochgeladene Datei
        
        Args:
            file: Werkzeug FileStorage
            upload_type: 'design', 'document', 'image'
        
        Returns:
            str: Relativer Pfad zur gespeicherten Datei
        """
        pass
    
    @staticmethod
    def delete_file(file_path: str) -> bool:
        """Löscht Datei vom Server"""
        pass
```

---

## 📝 Form-Klassen (WTForms)

**Datei:** `src/forms/customer_forms.py`

```python
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Email, Optional

class CustomerForm(FlaskForm):
    """Formular für Kunden (Privat & Geschäft)"""
    
    customer_type = SelectField(
        'Kundentyp',
        choices=[('private', 'Privatkunde'), ('business', 'Geschäftskunde')],
        validators=[DataRequired()]
    )
    
    # Privatkunde
    first_name = StringField('Vorname', validators=[Optional()])
    last_name = StringField('Nachname', validators=[Optional()])
    
    # Geschäftskunde
    company_name = StringField('Firmenname', validators=[Optional()])
    contact_person = StringField('Ansprechpartner', validators=[Optional()])
    
    # Kontakt
    email = StringField('E-Mail', validators=[Email(), Optional()])
    phone = StringField('Telefon', validators=[Optional()])
    
    # Adresse
    street = StringField('Straße', validators=[Optional()])
    house_number = StringField('Hausnummer', validators=[Optional()])
    postal_code = StringField('PLZ', validators=[Optional()])
    city = StringField('Stadt', validators=[Optional()])
    
    # Sonstiges
    newsletter = BooleanField('Newsletter')
    notes = TextAreaField('Notizen')
```

---

## 📊 Übersicht aller Klassen

### Models (17 Klassen)

1. ✅ User
2. ✅ Customer  
3. ✅ Article
4. ✅ ArticleVariant
5. ✅ Order
6. ✅ OrderItem
7. ✅ Thread
8. ✅ Machine
9. ✅ Supplier
10. ✅ ProductionSchedule
11. ✅ Invoice
12. ✅ Shipment
13. ✅ DesignFile
14. ✅ ActivityLog
15. ✅ Settings
16. ✅ Brand
17. ✅ ProductCategory

### Controllers (12 Blueprints)

1. ✅ customer_controller_db
2. ✅ article_controller_db
3. ✅ order_controller_db
4. ✅ thread_controller_db
5. ✅ thread_controller_unified
6. ✅ machine_controller_db
7. ✅ production_controller_db
8. ✅ shipping_controller_db
9. ✅ supplier_controller_db
10. ✅ design_controller
11. ✅ invoice_controller
12. ✅ settings_controller_unified

### Services (2 Klassen)

1. ✅ DSTAnalyzer
2. ✅ PriceCalculator

### Utils (2 Klassen)

1. ✅ ID-Generator
2. ✅ File-Handler

### Forms (10+ Forms)

1. ✅ CustomerForm
2. ✅ ArticleForm
3. ✅ OrderForm
4. ✅ ThreadForm
5. ✅ MachineForm
6. ✅ SupplierForm
7. ✅ InvoiceForm
8. ✅ ShipmentForm
9. ✅ DesignFileForm
10. ✅ SettingsForm

**Gesamt:** 43+ Klassen

---

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Stand:** 10. November 2025  
**Version:** 2.0.0 - Komplett
