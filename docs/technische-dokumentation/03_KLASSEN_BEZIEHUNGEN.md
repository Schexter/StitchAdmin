# StitchAdmin 2.0 - Klassen und Beziehungen

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Version:** 2.0.0-alpha  
**Stand:** November 2025

---

## 📋 Inhaltsverzeichnis

1. [Gesamt-Klassendiagramm](#1-gesamt-klassendiagramm)
2. [Kern-Module Detailliert](#2-kern-module-detailliert)
3. [Rechnungsmodul Detailliert](#3-rechnungsmodul-detailliert)
4. [Beziehungs-Matrix](#4-beziehungs-matrix)
5. [Vererbungshierarchie](#5-vererbungshierarchie)

---

## 1. Gesamt-Klassendiagramm

### Vollständiges UML-Klassendiagramm

```mermaid
classDiagram
    %% Benutzer und Authentifizierung
    class User {
        +Integer id PK
        +String username UNIQUE
        +String email UNIQUE
        +String password_hash
        +Boolean is_active
        +Boolean is_admin
        +DateTime created_at
        +DateTime last_login
        +set_password(password)
        +check_password(password)
    }
    
    %% Kundenverwaltung
    class Customer {
        +String id PK
        +String customer_type
        +String first_name
        +String last_name
        +Date birth_date
        +String company_name
        +String contact_person
        +String email
        +String phone
        +String street
        +String postal_code
        +String city
        +String country
        +Boolean newsletter
        +Text notes
        +DateTime created_at
        +String created_by
        +display_name()
        +get(key, default)
    }
    
    %% Artikelverwaltung
    class Article {
        +String id PK
        +String article_number UNIQUE
        +String name
        +Text description
        +Integer category_id FK
        +Integer brand_id FK
        +String material
        +Float weight
        +Float purchase_price_single
        +Float purchase_price_carton
        +Float price
        +Float price_calculated
        +Integer stock
        +Integer min_stock
        +Boolean active
        +DateTime created_at
        +calculate_prices()
        +get(key, default)
    }
    
    class ArticleVariant {
        +Integer id PK
        +String article_id FK
        +String sku UNIQUE
        +String color
        +String size
        +String variant_name
        +Float purchase_price_single
        +Float price
        +Integer stock
        +Boolean active
        +DateTime created_at
    }
    
    class ProductCategory {
        +Integer id PK
        +String name UNIQUE
        +Text description
        +Integer parent_id FK
        +Boolean active
        +Integer sort_order
        +DateTime created_at
    }
    
    class Brand {
        +Integer id PK
        +String name UNIQUE
        +Text description
        +String logo_url
        +String website
        +Boolean active
        +DateTime created_at
    }
    
    %% Auftragsverwaltung
    class Order {
        +String id PK
        +String customer_id FK
        +String order_number UNIQUE
        +String order_type
        +String status
        +Integer stitch_count
        +Float design_width_mm
        +String embroidery_position
        +Text selected_threads
        +String design_status
        +String design_supplier_id FK
        +String design_file_path
        +Float total_price
        +DateTime due_date
        +Boolean rush_order
        +String assigned_machine_id FK
        +DateTime created_at
        +get_selected_threads()
        +can_start_production()
        +has_design_file()
    }
    
    class OrderItem {
        +Integer id PK
        +String order_id FK
        +String article_id FK
        +Integer quantity
        +Float unit_price
        +String textile_size
        +String textile_color
        +String supplier_order_status
        +String supplier_order_id FK
        +DateTime created_at
    }
    
    class OrderStatusHistory {
        +Integer id PK
        +String order_id FK
        +String from_status
        +String to_status
        +Text comment
        +DateTime changed_at
        +String changed_by
    }
    
    %% Maschinenverwaltung
    class Machine {
        +String id PK
        +String name
        +String type
        +String manufacturer
        +String model
        +Integer num_heads
        +Integer needles_per_head
        +Integer max_speed
        +Text thread_setup
        +String status
        +Date maintenance_due
        +DateTime created_at
        +get_thread_setup()
        +set_thread_setup(setup)
    }
    
    class ProductionSchedule {
        +Integer id PK
        +String machine_id FK
        +String order_id FK
        +DateTime scheduled_start
        +DateTime scheduled_end
        +DateTime actual_start
        +DateTime actual_end
        +String status
        +Integer priority
        +DateTime created_at
    }
    
    %% Garnverwaltung
    class Thread {
        +String id PK
        +String manufacturer
        +String thread_type
        +String color_number
        +String color_name_de
        +String hex_color
        +String pantone
        +Integer rgb_r
        +Integer rgb_g
        +Integer rgb_b
        +String category
        +Float price
        +Boolean active
        +DateTime created_at
    }
    
    class ThreadStock {
        +Integer id PK
        +String thread_id FK
        +Integer quantity
        +Integer min_stock
        +String location
        +Date last_order_date
        +DateTime updated_at
    }
    
    class ThreadUsage {
        +Integer id PK
        +String thread_id FK
        +String order_id FK
        +Float quantity_used
        +String usage_type
        +DateTime used_at
    }
    
    %% Lieferantenverwaltung
    class Supplier {
        +String id PK
        +String name
        +String contact_person
        +String email
        +String phone
        +String street
        +String city
        +String webshop_url
        +String webshop_type
        +Boolean auto_order_enabled
        +Boolean active
        +DateTime created_at
    }
    
    class SupplierOrder {
        +String id PK
        +String supplier_id FK
        +String order_number
        +String supplier_order_number
        +Date order_date
        +String status
        +Float total_amount
        +Text items
        +DateTime created_at
        +get_items()
        +set_items(items_list)
        +calculate_total()
    }
    
    %% Versandverwaltung
    class Shipment {
        +String id PK
        +String order_id FK
        +String tracking_number
        +String carrier
        +Float weight
        +String status
        +DateTime shipped_date
        +String recipient_name
        +String recipient_city
        +DateTime created_at
    }
    
    class ShipmentItem {
        +Integer id PK
        +String shipment_id FK
        +Integer order_item_id FK
        +Integer quantity
        +String description
    }
    
    %% Aktivitätsprotokoll
    class ActivityLog {
        +Integer id PK
        +String username
        +String action
        +Text details
        +String ip_address
        +DateTime timestamp
    }
    
    %% Beziehungen - Kunden
    User "1" --> "*" Order : creates
    User "1" --> "*" ActivityLog : performs
    Customer "1" --> "*" Order : has
    
    %% Beziehungen - Artikel
    Article "1" --> "*" ArticleVariant : has
    Article "*" --> "1" ProductCategory : belongs_to
    Article "*" --> "1" Brand : belongs_to
    Article "1" --> "*" OrderItem : used_in
    
    %% Beziehungen - Aufträge
    Order "1" --> "*" OrderItem : contains
    Order "1" --> "*" OrderStatusHistory : tracks
    Order "1" --> "*" Shipment : ships
    Order "*" --> "0..1" Machine : assigned_to
    Order "*" --> "0..1" Supplier : design_from
    Order "1" --> "*" ThreadUsage : uses
    
    %% Beziehungen - OrderItems
    OrderItem "*" --> "1" Article : references
    OrderItem "*" --> "0..1" SupplierOrder : ordered_in
    
    %% Beziehungen - Maschinen
    Machine "1" --> "*" ProductionSchedule : has
    Machine "1" --> "*" Order : produces
    
    %% Beziehungen - Garne
    Thread "1" --> "1" ThreadStock : has
    Thread "1" --> "*" ThreadUsage : tracks
    
    %% Beziehungen - Lieferanten
    Supplier "1" --> "*" SupplierOrder : receives
    Supplier "1" --> "*" Order : supplies_design
    
    %% Beziehungen - Versand
    Shipment "1" --> "*" ShipmentItem : contains
    ShipmentItem "*" --> "1" OrderItem : ships
```

---

## 2. Kern-Module Detailliert

### 2.1 Kundenverwaltung

```mermaid
classDiagram
    class Customer {
        <<Entity>>
        +String id PK
        +String customer_type
        +PersonalData: first_name, last_name, birth_date
        +BusinessData: company_name, contact_person, tax_id
        +ContactData: email, phone, mobile
        +AddressData: street, postal_code, city, country
        +Boolean newsletter
        +Text notes
        +Metadata: created_at, created_by, updated_at
        +display_name() String
        +get(key, default) Any
    }
    
    class Order {
        +String customer_id FK
    }
    
    class Rechnung {
        +String kunde_id FK
    }
    
    Customer "1" --> "*" Order : places
    Customer "1" --> "*" Rechnung : receives
    
    note for Customer "Unterstützt Privat- und\nGeschäftskunden mit\nunterschiedlichen Feldern"
```

**Methoden:**

```python
@property
def display_name(self):
    """
    Gibt den Anzeigenamen zurück
    - Geschäftskunde: company_name
    - Privatkunde: first_name + last_name
    """
```

### 2.2 Artikelverwaltung

```mermaid
classDiagram
    class Article {
        <<Entity>>
        +String id PK
        +String article_number UNIQUE
        +String name
        +Text description
        +PriceData: purchase_price_*, price*
        +StockData: stock, min_stock, location
        +SupplierData: supplier, supplier_article_number
        +LShopData: product_type, manufacturer_number
        +Boolean has_variants
        +Metadata: created_at, updated_at
        +calculate_prices() Dict
        +_get_best_purchase_price() Float
    }
    
    class ArticleVariant {
        <<Entity>>
        +Integer id PK
        +String article_id FK
        +String sku UNIQUE
        +String color
        +String size
        +Float price
        +Integer stock
        +Boolean active
    }
    
    class ProductCategory {
        <<LookupTable>>
        +Integer id PK
        +String name UNIQUE
        +Integer parent_id FK
        +Boolean active
        +Integer sort_order
    }
    
    class Brand {
        <<LookupTable>>
        +Integer id PK
        +String name UNIQUE
        +String logo_url
        +String website
        +Boolean active
    }
    
    class ArticleSupplier {
        <<JoinTable>>
        +Integer id PK
        +String article_id FK
        +String supplier_id FK
        +String supplier_article_number
        +Float price
        +Boolean is_preferred
        +Date last_order_date
    }
    
    Article "1" --> "*" ArticleVariant : has
    Article "*" --> "1" ProductCategory : categorized_by
    Article "*" --> "1" Brand : manufactured_by
    Article "*" --> "*" Supplier : supplied_by
    ArticleSupplier --|> Article
    ArticleSupplier --|> Supplier
    
    ProductCategory "1" --> "*" ProductCategory : contains
```

**Preiskalkulation:**

```python
def calculate_prices(self, use_new_system=True):
    """
    Berechnet VK-Preise basierend auf EK und Einstellungen
    
    Methoden:
    1. Neue Methode (PriceCalculationRule):
       - Regelbasierte Kalkulation nach Kategorie/Marke
       - Verschiedene Faktoren pro Regel
       - Steuersätze pro Regel
    
    2. Legacy-Methode (Fallback):
       - Globale Faktoren aus PriceCalculationSettings
       - Standard-Steuersatz
    
    Formel:
    VK = EK × Faktor × (1 + MwSt/100)
    
    Returns:
        Dict: {
            'base_price': Float,
            'calculated': Float,
            'recommended': Float,
            'tax_rate': Float,
            'rule_used': String
        }
    """
```

### 2.3 Auftragsverwaltung

```mermaid
classDiagram
    class Order {
        <<AggregateRoot>>
        +String id PK
        +String customer_id FK
        +String order_number UNIQUE
        +Enum order_type
        +String status
        +EmbroideryData: stitch_count, design_*
        +PrintData: print_*, ink_coverage
        +DesignWorkflow: design_status, design_supplier_id
        +ProductionData: assigned_machine_id, production_*
        +PriceData: total_price, deposit, discount
        +DateTime due_date
        +Boolean rush_order
        +get_selected_threads() List
        +can_start_production() Tuple[Bool, String]
        +is_design_ready() Bool
    }
    
    class OrderItem {
        <<ValueObject>>
        +Integer id PK
        +String order_id FK
        +String article_id FK
        +Integer quantity
        +Float unit_price
        +TextileData: size, color
        +SupplierOrderData: status, order_id, dates
    }
    
    class OrderStatusHistory {
        <<EventLog>>
        +Integer id PK
        +String order_id FK
        +String from_status
        +String to_status
        +Text comment
        +DateTime changed_at
        +String changed_by
    }
    
    Order "1" *-- "*" OrderItem : contains
    Order "1" --> "*" OrderStatusHistory : logs
    Order "*" --> "1" Customer : belongs_to
    Order "*" --> "0..1" Machine : assigned_to
    Order "*" --> "0..1" Supplier : design_ordered_from
    
    OrderItem "*" --> "1" Article : references
    OrderItem "*" --> "0..1" SupplierOrder : part_of
```

**Status-Übergänge:**

```
new → in_production → completed → shipped → delivered
  ↓         ↓            ↓
cancelled  paused    cancelled
```

**Design-Status-Übergänge:**

```
none → customer_provided → ready
  ↓                          ↑
needs_order → ordered → received
```

### 2.4 Produktionsverwaltung

```mermaid
classDiagram
    class Machine {
        <<Entity>>
        +String id PK
        +String name
        +Enum type
        +MachineSpecs: manufacturer, model, serial
        +EmbroiderySpecs: num_heads, needles_per_head, max_speed
        +CapacityData: max_area_*
        +ConfigData: thread_setup, default_settings
        +String status
        +TimeData: setup_time, thread_change_time
        +Date maintenance_due
        +get_thread_setup() List
        +set_thread_setup(setup) void
    }
    
    class ProductionSchedule {
        <<Entity>>
        +Integer id PK
        +String machine_id FK
        +String order_id FK
        +DateTime scheduled_start
        +DateTime scheduled_end
        +DateTime actual_start
        +DateTime actual_end
        +String status
        +Integer priority
        +Text notes
    }
    
    Machine "1" --> "*" ProductionSchedule : schedules
    Machine "1" --> "*" Order : produces
    ProductionSchedule "*" --> "1" Order : produces
```

**Machine Thread Setup (JSON):**

```json
[
    {
        "position": 1,
        "thread_id": "THR-001",
        "color": "Schwarz",
        "manufacturer": "Madeira"
    },
    {
        "position": 2,
        "thread_id": "THR-002",
        "color": "Weiß",
        "manufacturer": "Madeira"
    }
]
```

### 2.5 Garnverwaltung

```mermaid
classDiagram
    class Thread {
        <<Entity>>
        +String id PK
        +String manufacturer
        +String thread_type
        +String color_number
        +ColorData: color_name_*, hex, pantone, rgb_*
        +ThreadSpecs: category, weight, material
        +PriceData: price, supplier, supplier_article_number
        +Boolean active
        +Boolean discontinued
        +Metadata: created_at, updated_at
    }
    
    class ThreadStock {
        <<ValueObject>>
        +Integer id PK
        +String thread_id FK
        +Integer quantity
        +Integer min_stock
        +String location
        +Date last_order_date
        +String supplier_order_number
        +DateTime updated_at
    }
    
    class ThreadUsage {
        <<EventLog>>
        +Integer id PK
        +String thread_id FK
        +String order_id FK
        +Float quantity_used
        +Enum usage_type
        +String machine_id
        +DateTime used_at
        +String recorded_by
    }
    
    Thread "1" -- "1" ThreadStock : has
    Thread "1" --> "*" ThreadUsage : tracks
    ThreadUsage "*" --> "1" Order : for
```

**Garnkategorien:**

- **Standard** - Normale Stickgarne
- **Metallic** - Metallicgarne
- **Rayon** - Rayongarne  
- **Polyester** - Polyestergarne
- **Spezial** - Spezialgarne (Glow-in-dark, etc.)

---

## 3. Rechnungsmodul Detailliert

### 3.1 Kassensystem

```mermaid
classDiagram
    class KassenBeleg {
        <<AggregateRoot>>
        +Integer id PK
        +String belegnummer UNIQUE
        +Enum beleg_typ
        +String kunde_id FK
        +CustomerSnapshot: kunde_name, kunde_adresse
        +MoneyData: netto_gesamt, mwst_gesamt, brutto_gesamt
        +PaymentData: zahlungsart, gegeben, rueckgeld
        +TSEData: tse_transaktion_id
        +CashRegister: kassen_id, kassierer_id
        +StornoData: storniert, storno_grund
        +DateTime erstellt_am
        +generate_belegnummer() String
        +calculate_totals() void
        +to_dict() Dict
    }
    
    class BelegPosition {
        <<ValueObject>>
        +Integer id PK
        +Integer beleg_id FK
        +Integer position
        +ArtikelSnapshot: artikel_id, artikel_nummer, artikel_name
        +QuantityData: menge, einzelpreis_netto/brutto
        +TaxData: mwst_satz, mwst_betrag
        +DiscountData: rabatt_prozent, rabatt_betrag
        +MoneyData: netto_betrag, brutto_betrag
        +calculate_amounts() void
    }
    
    class KassenTransaktion {
        <<ValueObject TSE>>
        +Integer id PK
        +String tse_serial
        +String tse_transaktion_nummer UNIQUE
        +DateTime tse_start
        +DateTime tse_ende
        +TSESignature: signatur_zaehler, algorithmus, signatur
        +ProcessData: prozess_typ, prozess_daten
        +String tse_client_id
        +get_prozess_daten() Dict
        +set_prozess_daten(data) void
    }
    
    KassenBeleg "1" *-- "*" BelegPosition : contains
    KassenBeleg "*" --> "0..1" KassenTransaktion : signed_by
    KassenBeleg "*" --> "1" User : created_by
    KassenBeleg "*" --> "0..1" Customer : for
    KassenBeleg "1" --> "0..1" KassenBeleg : storniert
```

**Beleg-Typen (Enum):**

```python
class BelegTyp(Enum):
    RECHNUNG = "RECHNUNG"      # Normaler Kassenbeleg
    GUTSCHRIFT = "GUTSCHRIFT"  # Gutschrift/Rückerstattung
    TRAINING = "TRAINING"       # Trainings-Beleg
    STORNO = "STORNO"           # Storno-Beleg
```

**Zahlungsarten (Enum):**

```python
class ZahlungsArt(Enum):
    BAR = "BAR"
    EC_KARTE = "EC_KARTE"
    KREDITKARTE = "KREDITKARTE"
    RECHNUNG = "RECHNUNG"
    UEBERWEISUNG = "UEBERWEISUNG"
    PAYPAL = "PAYPAL"
    LASTSCHRIFT = "LASTSCHRIFT"
```

### 3.2 TSE-System

```mermaid
classDiagram
    class TSEKonfiguration {
        <<Entity>>
        +Integer id PK
        +String tse_seriennummer UNIQUE
        +String tse_hersteller
        +String tse_modell
        +CertificateData: zertifikat_*, gueltig_von/bis
        +ConfigData: kassen_id, client_id
        +Enum status
        +Boolean aktiv
        +MaintenanceData: letzte_wartung, naechste_wartung
        +DateTime erstellt_am
    }
    
    class MwStSatz {
        <<LookupTable>>
        +Integer id PK
        +String bezeichnung
        +Decimal satz
        +Date gueltig_von
        +Date gueltig_bis
        +Boolean aktiv
        +Boolean standard
        +String verwendung
        +get_standard_satz() MwStSatz
        +get_aktuelle_saetze() List[MwStSatz]
    }
    
    class TagesAbschluss {
        <<AggregateRoot>>
        +Integer id PK
        +Date datum
        +String kassen_id
        +Statistics: anzahl_belege, anzahl_stornos
        +UmsatzByPayment: umsatz_bar, umsatz_ec, ...
        +TotalRevenue: umsatz_netto, umsatz_mwst, umsatz_brutto
        +CashBalance: kassenstand_anfang, kassenstand_ende
        +TSERange: tse_von, tse_bis
        +Boolean abgeschlossen
        +Boolean geprueft
        +DateTime erstellt_am
    }
    
    KassenTransaktion "*" --> "1" TSEKonfiguration : uses
    BelegPosition "*" --> "1" MwStSatz : applies
    TagesAbschluss "1" --> "*" KassenBeleg : summarizes
```

**TSE-Status (Enum):**

```python
class TSEStatus(Enum):
    AKTIV = "AKTIV"
    INAKTIV = "INAKTIV"
    DEFEKT = "DEFEKT"
    WARTUNG = "WARTUNG"
```

### 3.3 Rechnungssystem

```mermaid
classDiagram
    class Rechnung {
        <<AggregateRoot>>
        +Integer id PK
        +String rechnungsnummer UNIQUE
        +String kunde_id FK
        +CustomerSnapshot: kunde_name, kunde_adresse, kunde_*
        +DateData: rechnungsdatum, leistungsdatum, faelligkeitsdatum
        +MoneyData: netto_gesamt, mwst_gesamt, brutto_gesamt
        +DiscountData: rabatt_*, skonto_*
        +Enum status
        +ZUGPFERDData: profil, xml
        +FileData: pdf_datei, xml_datei
        +SendData: versendet_am, versand_email
        +PaymentTerms: zahlungsbedingungen, mahnstufe
        +PaymentData: bezahlt_am, bezahlt_betrag
        +Metadata: erstellt_am, bearbeitet_am
        +generate_rechnungsnummer() String
        +calculate_totals() void
        +is_overdue() Bool
        +get_open_amount() Decimal
    }
    
    class RechnungsPosition {
        <<ValueObject>>
        +Integer id PK
        +Integer rechnung_id FK
        +Integer position
        +ArtikelSnapshot: artikel_*, beschreibung
        +QuantityData: menge, einheit, einzelpreis
        +TaxData: mwst_satz, mwst_betrag
        +DiscountData: rabatt_*
        +MoneyData: netto_betrag, brutto_betrag
        +calculate_amounts() void
    }
    
    class RechnungsZahlung {
        <<ValueObject>>
        +Integer id PK
        +Integer rechnung_id FK
        +Decimal betrag
        +Enum zahlungsart
        +Date zahlungsdatum
        +PaymentDetails: referenz, bank_name, verwendungszweck
        +SkontoData: skonto_prozent, skonto_betrag
        +String status
        +Text bemerkungen
        +DateTime erfasst_am
    }
    
    class ZugpferdKonfiguration {
        <<Configuration>>
        +Integer id PK
        +CompanyData: unternehmen_*, adresse_*
        +TaxData: steuernummer, ust_id, handelsregisternummer
        +ContactData: telefon, email, website
        +BankData: bank_name, iban, bic
        +ZUGPFERDSettings: standard_profil, xml_validierung
        +Boolean aktiv
        +DateTime erstellt_am
    }
    
    Rechnung "1" *-- "*" RechnungsPosition : contains
    Rechnung "1" --> "*" RechnungsZahlung : paid_by
    Rechnung "*" --> "1" Customer : for
    Rechnung "*" --> "1" ZugpferdKonfiguration : uses
```

**Rechnungs-Status (Enum):**

```python
class RechnungsStatus(Enum):
    ENTWURF = "ENTWURF"           # Noch nicht versendet
    OFFEN = "OFFEN"               # Versendet, unbezahlt
    TEILBEZAHLT = "TEILBEZAHLT"   # Teilweise bezahlt
    BEZAHLT = "BEZAHLT"           # Vollständig bezahlt
    UEBERFAELLIG = "UEBERFAELLIG" # Fälligkeitsdatum überschritten
    STORNIERT = "STORNIERT"       # Storniert
    GUTSCHRIFT = "GUTSCHRIFT"     # Gutschrift erstellt
```

**ZUGPFERD-Profile (Enum):**

```python
class ZugpferdProfil(Enum):
    MINIMUM = "MINIMUM"       # Mindestanforderungen
    BASIC = "BASIC"           # Standard-Profil
    COMFORT = "COMFORT"       # Erweiterte Informationen
    EXTENDED = "EXTENDED"     # Maximale Informationen
```

---

## 4. Beziehungs-Matrix

### Direkte Beziehungen

| Von → Nach | Typ | Kardinalität | FK-Spalte | Beschreibung |
|------------|-----|--------------|-----------|--------------|
| **User → ActivityLog** | Composition | 1:N | username | Benutzer-Aktivitäten |
| **User → Order** | Association | 1:N | created_by | Auftrag-Ersteller |
| **User → KassenBeleg** | Association | 1:N | kassierer_id | Kassierer |
| **Customer → Order** | Composition | 1:N | customer_id | Kunden-Aufträge |
| **Customer → Rechnung** | Composition | 1:N | kunde_id | Kunden-Rechnungen |
| **Article → ArticleVariant** | Composition | 1:N | article_id | Artikel-Varianten |
| **Article → OrderItem** | Association | 1:N | article_id | Artikel in Aufträgen |
| **Article → ProductCategory** | Association | N:1 | category_id | Artikel-Kategorie |
| **Article → Brand** | Association | N:1 | brand_id | Artikel-Marke |
| **Order → OrderItem** | Composition | 1:N | order_id | Auftragspositionen |
| **Order → OrderStatusHistory** | Composition | 1:N | order_id | Status-Historie |
| **Order → Shipment** | Composition | 1:N | order_id | Versendungen |
| **Order → Machine** | Association | N:0..1 | assigned_machine_id | Maschinen-Zuweisung |
| **Order → Supplier** | Association | N:0..1 | design_supplier_id | Design-Lieferant |
| **OrderItem → Article** | Association | N:1 | article_id | Artikel-Referenz |
| **OrderItem → SupplierOrder** | Association | N:0..1 | supplier_order_id | Lieferantenbestellung |
| **Machine → ProductionSchedule** | Composition | 1:N | machine_id | Maschinen-Plan |
| **Machine → Order** | Association | 1:N | assigned_machine_id | Zugewiesene Aufträge |
| **Thread → ThreadStock** | Composition | 1:1 | thread_id | Garn-Bestand |
| **Thread → ThreadUsage** | Composition | 1:N | thread_id | Garn-Verbrauch |
| **ThreadUsage → Order** | Association | N:1 | order_id | Verbrauch für Auftrag |
| **Supplier → SupplierOrder** | Composition | 1:N | supplier_id | Lieferanten-Bestellungen |
| **Supplier → Order** | Association | 1:N | design_supplier_id | Design-Bestellungen |
| **Shipment → ShipmentItem** | Composition | 1:N | shipment_id | Versand-Positionen |
| **ShipmentItem → OrderItem** | Association | N:1 | order_item_id | Versendete Positionen |
| **KassenBeleg → BelegPosition** | Composition | 1:N | beleg_id | Beleg-Positionen |
| **KassenBeleg → KassenTransaktion** | Association | N:0..1 | tse_transaktion_id | TSE-Signatur |
| **KassenBeleg → Customer** | Association | N:0..1 | kunde_id | Kunde (optional) |
| **Rechnung → RechnungsPosition** | Composition | 1:N | rechnung_id | Rechnungs-Positionen |
| **Rechnung → RechnungsZahlung** | Composition | 1:N | rechnung_id | Zahlungen |
| **Rechnung → Customer** | Association | N:1 | kunde_id | Rechnungs-Kunde |

### Indirekte Beziehungen (über Join-Tables)

| Tabelle A | Join-Table | Tabelle B | Beschreibung |
|-----------|------------|-----------|--------------|
| **Article** | ArticleSupplier | **Supplier** | Artikel ↔ Lieferanten |
| **Supplier** | SupplierContact | *Contact-Info* | Lieferanten ↔ Ansprechpartner |

---

## 5. Vererbungshierarchie

### SQLAlchemy Base Classes

```mermaid
classDiagram
    class db.Model {
        <<SQLAlchemy Base>>
        +__tablename__
        +query
    }
    
    class UserMixin {
        <<Flask-Login>>
        +is_authenticated
        +is_active
        +is_anonymous
        +get_id()
    }
    
    db.Model <|-- User
    db.Model <|-- Customer
    db.Model <|-- Article
    db.Model <|-- Order
    db.Model <|-- Machine
    db.Model <|-- Thread
    db.Model <|-- Supplier
    db.Model <|-- KassenBeleg
    db.Model <|-- Rechnung
    
    UserMixin <|-- User
    
    note for db.Model "Alle Models erben von\nSQLAlchemy's db.Model"
    note for UserMixin "User erbt zusätzlich von\nFlask-Login's UserMixin"
```

### Model-Kategorien

**Aggregate Roots:**
- `Customer` - Kunden-Aggregate
- `Order` - Auftrags-Aggregate
- `KassenBeleg` - Kassen-Aggregate
- `Rechnung` - Rechnungs-Aggregate
- `TagesAbschluss` - Tagesabschluss-Aggregate

**Entities:**
- `User`, `Article`, `Machine`, `Thread`, `Supplier`, `Shipment`

**Value Objects:**
- `OrderItem`, `BelegPosition`, `RechnungsPosition`
- `ArticleVariant`, `ThreadStock`, `ShipmentItem`

**Event Logs:**
- `OrderStatusHistory`, `ThreadUsage`, `ActivityLog`

**Lookup Tables:**
- `ProductCategory`, `Brand`, `MwStSatz`

**Join Tables:**
- `ArticleSupplier`, `SupplierContact`

**Configuration:**
- `TSEKonfiguration`, `ZugpferdKonfiguration`
- `PriceCalculationSettings`

---

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**
