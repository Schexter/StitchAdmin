# StitchAdmin 2.0 - Funktionsübersicht

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Version:** 2.0.0-alpha  
**Stand:** November 2025

---

## 📋 Inhaltsverzeichnis

1. [Controller-Funktionen](#1-controller-funktionen)
2. [Service-Funktionen](#2-service-funktionen)
3. [Util-Funktionen](#3-util-funktionen)
4. [Model-Methoden](#4-model-methoden)

---

## 1. Controller-Funktionen

### 1.1 Kundenverwaltung (`customer_controller_db.py`)

#### **GET /customers**
```python
def index():
    """
    Kundenliste anzeigen
    
    Query-Parameter:
        - search: String - Suche nach Name/Firma/Email
        - type: String - Filter nach Kundentyp (private/business)
        - sort: String - Sortierung (name/created_at)
    
    Returns:
        Template: customers/index.html
        Context:
            - customers: List[Customer]
            - search_query: String
            - customer_type_filter: String
    """
```

#### **GET /customers/new**
```python
def new():
    """
    Neukunden-Formular anzeigen
    
    Returns:
        Template: customers/new.html
        Context:
            - customer_types: List[String]
    """
```

#### **POST /customers/new**
```python
def create():
    """
    Neuen Kunden anlegen
    
    Form-Data:
        - customer_type: String (required)
        - first_name: String (required if private)
        - last_name: String (required if private)
        - company_name: String (required if business)
        - email: String
        - phone: String
        - street: String
        - postal_code: String
        - city: String
        - country: String
        - newsletter: Boolean
        - notes: Text
    
    Process:
        1. Validierung der Eingaben
        2. Kunden-ID generieren (Format: C-YYYYMMDD-XXXX)
        3. Customer-Objekt erstellen
        4. In DB speichern
        5. Aktivität protokollieren
    
    Returns:
        Redirect: /customers/show/<id>
        Flash: Success-Message
    
    Errors:
        - ValidationError: Zurück zu /customers/new mit Fehlermeldungen
        - DatabaseError: 500 Error
    """
```

#### **GET /customers/show/<id>**
```python
def show(id):
    """
    Kundendetails anzeigen
    
    URL-Parameter:
        - id: String - Kunden-ID
    
    Process:
        1. Kunde aus DB laden
        2. Auftragshistorie laden (Order.query.filter_by(customer_id))
        3. Rechnungshistorie laden (Rechnung.query.filter_by(kunde_id))
        4. Aktivitäten laden (ActivityLog.query.filter)
    
    Returns:
        Template: customers/show.html
        Context:
            - customer: Customer
            - orders: List[Order]
            - rechnungen: List[Rechnung]
            - activities: List[ActivityLog]
            - order_count: Integer
            - total_revenue: Float
    
    Errors:
        - NotFound: 404 wenn Kunde nicht existiert
    """
```

#### **GET /customers/edit/<id>**
```python
def edit(id):
    """
    Kunden-Bearbeitungsformular anzeigen
    
    URL-Parameter:
        - id: String - Kunden-ID
    
    Returns:
        Template: customers/edit.html
        Context:
            - customer: Customer
            - customer_types: List[String]
    
    Errors:
        - NotFound: 404 wenn Kunde nicht existiert
    """
```

#### **POST /customers/edit/<id>**
```python
def update(id):
    """
    Kunde aktualisieren
    
    URL-Parameter:
        - id: String - Kunden-ID
    
    Form-Data:
        [Gleiche Felder wie bei create()]
    
    Process:
        1. Kunde aus DB laden
        2. Validierung der Eingaben
        3. Kunde aktualisieren
        4. Metadaten aktualisieren (updated_at, updated_by)
        5. In DB speichern
        6. Aktivität protokollieren
    
    Returns:
        Redirect: /customers/show/<id>
        Flash: Success-Message
    
    Errors:
        - ValidationError: Zurück zu /customers/edit/<id>
        - NotFound: 404 wenn Kunde nicht existiert
    """
```

---

### 1.2 Artikelverwaltung (`article_controller_db.py`)

#### **GET /articles**
```python
def index():
    """
    Artikelliste anzeigen
    
    Query-Parameter:
        - search: String - Suche nach Name/Nummer
        - category: Integer - Filter nach Kategorie-ID
        - brand: Integer - Filter nach Marken-ID
        - stock_warning: Boolean - Nur Artikel mit niedrigem Bestand
        - sort: String - Sortierung (name/price/stock)
    
    Process:
        1. Artikel aus DB laden
        2. Filter anwenden
        3. Sortierung anwenden
        4. Lagerbestand-Warnungen prüfen
        5. Kategorien/Marken für Filter laden
    
    Returns:
        Template: articles/index.html
        Context:
            - articles: List[Article]
            - categories: List[ProductCategory]
            - brands: List[Brand]
            - search_query: String
            - filters: Dict
            - stock_warnings: Integer
    """
```

#### **GET /articles/import-lshop**
```python
def import_lshop():
    """
    L-Shop Import-Formular anzeigen
    
    Returns:
        Template: articles/lshop/import.html
        Context:
            - supported_formats: List[String]
            - max_file_size: Integer (MB)
    """
```

#### **POST /articles/import-lshop**
```python
def process_lshop_import():
    """
    L-Shop Excel-Import durchführen
    
    Form-Data:
        - file: FileUpload (Excel .xlsx)
        - update_existing: Boolean - Existierende Artikel aktualisieren
        - create_variants: Boolean - Varianten automatisch anlegen
    
    Process:
        1. Excel-Datei hochladen
        2. Excel parsen (lshop_import_service.parse_lshop_excel)
        3. Artikel extrahieren
        4. Vorschau anzeigen (GET mit Daten)
        5. Import bestätigen (POST)
        6. Für jeden Artikel:
           a. Prüfen ob existiert (article_number)
           b. Artikel anlegen oder aktualisieren
           c. Preise kalkulieren (calculate_prices)
           d. Varianten anlegen (falls has_variants=True)
        7. Import-Statistik erstellen
    
    Returns:
        Template: articles/lshop/import.html
        Context:
            - preview_data: List[Dict] (bei GET nach Parse)
            - import_stats: Dict (bei POST)
              - total: Integer
              - created: Integer
              - updated: Integer
              - variants_created: Integer
              - errors: List[String]
    
    Errors:
        - ValidationError: Ungültiges Excel-Format
        - ParseError: Fehler beim Parsen
    """
```

#### **GET /articles/new**
```python
def new():
    """
    Neuer Artikel-Formular anzeigen
    
    Returns:
        Template: articles/new.html
        Context:
            - categories: List[ProductCategory]
            - brands: List[Brand]
            - suppliers: List[Supplier]
            - price_factors: Dict
    """
```

#### **POST /articles/new**
```python
def create():
    """
    Neuen Artikel anlegen
    
    Form-Data:
        - article_number: String (unique, required)
        - name: String (required)
        - description: Text
        - category_id: Integer
        - brand_id: Integer
        - material: String
        - weight: Float
        - purchase_price_single: Float (required)
        - purchase_price_carton: Float
        - purchase_price_10carton: Float
        - stock: Integer
        - min_stock: Integer
        - location: String
        - supplier: String
        - supplier_article_number: String
        - active: Boolean
    
    Process:
        1. Validierung
        2. Artikel-ID generieren
        3. Preise kalkulieren (calculate_prices)
        4. Article-Objekt erstellen
        5. In DB speichern
        6. Aktivität protokollieren
    
    Returns:
        Redirect: /articles/show/<id>
        Flash: Success-Message
    
    Errors:
        - ValidationError: Zurück zu /articles/new
        - DuplicateError: article_number bereits vorhanden
    """
```

#### **GET /articles/show/<id>**
```python
def show(id):
    """
    Artikeldetails anzeigen
    
    URL-Parameter:
        - id: String - Artikel-ID
    
    Process:
        1. Artikel aus DB laden
        2. Varianten laden (ArticleVariant.query.filter_by)
        3. Lieferanten laden (ArticleSupplier.query.filter_by)
        4. Lagerbestand prüfen
        5. Verwendung in Aufträgen laden
        6. Kalkulierte Preise anzeigen
    
    Returns:
        Template: articles/show.html
        Context:
            - article: Article
            - variants: List[ArticleVariant]
            - suppliers: List[ArticleSupplier]
            - stock_status: Dict
            - order_usage: List[Order]
            - price_calculation: Dict
    
    Errors:
        - NotFound: 404 wenn Artikel nicht existiert
    """
```

#### **GET /articles/edit/<id>**
```python
def edit(id):
    """
    Artikel-Bearbeitungsformular anzeigen
    
    URL-Parameter:
        - id: String - Artikel-ID
    
    Returns:
        Template: articles/edit.html
        Context:
            - article: Article
            - categories: List[ProductCategory]
            - brands: List[Brand]
            - suppliers: List[Supplier]
            - price_calculation: Dict
    
    Errors:
        - NotFound: 404 wenn Artikel nicht existiert
    """
```

#### **POST /articles/edit/<id>**
```python
def update(id):
    """
    Artikel aktualisieren
    
    URL-Parameter:
        - id: String - Artikel-ID
    
    Form-Data:
        [Gleiche Felder wie bei create()]
    
    Process:
        1. Artikel aus DB laden
        2. Validierung
        3. Preise neu kalkulieren bei EK-Änderung
        4. Artikel aktualisieren
        5. Metadaten aktualisieren
        6. In DB speichern
        7. Aktivität protokollieren
    
    Returns:
        Redirect: /articles/show/<id>
        Flash: Success-Message
    
    Errors:
        - ValidationError: Zurück zu /articles/edit/<id>
        - NotFound: 404
    """
```

#### **GET /articles/variants/<article_id>**
```python
def manage_variants(article_id):
    """
    Varianten-Management anzeigen
    
    URL-Parameter:
        - article_id: String - Artikel-ID
    
    Returns:
        Template: articles/variants_section.html
        Context:
            - article: Article
            - variants: List[ArticleVariant]
            - available_colors: List[String]
            - available_sizes: List[String]
    """
```

#### **POST /articles/variants/<article_id>/new**
```python
def create_variant(article_id):
    """
    Neue Variante anlegen
    
    URL-Parameter:
        - article_id: String - Artikel-ID
    
    Form-Data:
        - color: String (required)
        - size: String (required)
        - sku: String (unique, auto-generated if empty)
        - purchase_price_single: Float
        - price: Float (auto-calculated from article)
        - stock: Integer
        - active: Boolean
    
    Process:
        1. Artikel laden
        2. Validierung (color + size Kombination unique)
        3. SKU generieren falls leer
        4. Variante erstellen
        5. In DB speichern
    
    Returns:
        Redirect: /articles/variants/<article_id>
        Flash: Success-Message
    
    Errors:
        - ValidationError: Variante existiert bereits
        - NotFound: Artikel nicht gefunden
    """
```

#### **GET /articles/label/<id>**
```python
def print_label(id):
    """
    Artikel-Etikett drucken
    
    URL-Parameter:
        - id: String - Artikel-ID
    
    Query-Parameter:
        - quantity: Integer - Anzahl Etiketten (default: 1)
        - size: String - Etiketten-Größe (default: 40x30mm)
    
    Returns:
        Template: articles/label.html (Druckansicht)
        Context:
            - article: Article
            - quantity: Integer
            - barcode: String (EAN-13 oder ähnlich)
    """
```

#### **GET /articles/datasheet/<id>**
```python
def datasheet(id):
    """
    Artikel-Datenblatt anzeigen
    
    URL-Parameter:
        - id: String - Artikel-ID
    
    Returns:
        Template: articles/datasheet.html (PDF-ready)
        Context:
            - article: Article
            - variants: List[ArticleVariant]
            - suppliers: List[ArticleSupplier]
            - technical_data: Dict
            - price_history: List[Dict]
    """
```

---

### 1.3 Auftragsverwaltung (`order_controller_db.py`)

#### **GET /orders**
```python
def index():
    """
    Auftragsliste anzeigen
    
    Query-Parameter:
        - search: String - Suche nach Auftragsnummer/Kunde
        - status: String - Filter nach Status
        - type: String - Filter nach Typ (embroidery/printing/combined)
        - date_from: Date - Datum von
        - date_to: Date - Datum bis
        - rush: Boolean - Nur Eilaufträge
        - sort: String - Sortierung (date/due_date/status)
    
    Process:
        1. Aufträge aus DB laden
        2. Filter anwenden
        3. Sortierung anwenden
        4. Status-Statistiken berechnen
        5. Design-Status aggregieren
    
    Returns:
        Template: orders/index.html
        Context:
            - orders: List[Order]
            - status_stats: Dict[String, Integer]
            - design_status_stats: Dict[String, Integer]
            - filters: Dict
            - total_count: Integer
            - rush_count: Integer
    """
```

#### **GET /orders/new**
```python
def new():
    """
    Neuer Auftrag-Formular anzeigen
    
    Query-Parameter:
        - customer_id: String - Vorausgewählter Kunde (optional)
    
    Returns:
        Template: orders/new.html
        Context:
            - customers: List[Customer]
            - order_types: List[String]
            - machines: List[Machine]
            - threads: List[Thread]
            - articles: List[Article]
            - selected_customer: Customer (optional)
    """
```

#### **POST /orders/new**
```python
def create():
    """
    Neuen Auftrag anlegen
    
    Form-Data:
        - customer_id: String (required)
        - order_type: String (required)
        - description: Text
        - internal_notes: Text
        - customer_notes: Text
        
        # Stickerei-Felder (wenn order_type = embroidery/combined)
        - embroidery_position: String
        - embroidery_size: String
        - design_file: FileUpload (optional)
        - selected_threads: List[String] (JSON)
        
        # Druck-Felder (wenn order_type = printing/combined)
        - print_method: String
        - print_width_cm: Float
        - print_height_cm: Float
        - print_colors: List[Dict] (JSON)
        
        # Design-Workflow
        - design_status: String
        - design_supplier_id: String (optional)
        - design_order_date: Date (optional)
        - design_expected_date: Date (optional)
        
        # OrderItems
        - items: List[Dict] (JSON)
          [
            {
              article_id: String,
              quantity: Integer,
              textile_size: String,
              textile_color: String,
              supplier_order_status: String
            }
          ]
        
        # Preise
        - total_price: Float
        - deposit_amount: Float
        - discount_percent: Float
        
        # Termine
        - due_date: DateTime
        - rush_order: Boolean
    
    Process:
        1. Validierung
        2. Kunde laden und validieren
        
        # Design-Upload
        3. Falls design_file vorhanden:
           a. Datei speichern (design_upload.save_design_file)
           b. Falls DST: Analysieren (dst_analyzer.analyze_dst_file)
           c. Thumbnail erstellen
           d. Pfade speichern
           e. design_status = 'customer_provided'
        
        4. Falls design_supplier_id:
           - design_status = 'needs_order'
        
        # Auftragsnummer generieren
        5. order_number = generate_order_number()
           Format: ORD-YYYYMMDD-XXXX
        
        # Preisberechnung
        6. Preis berechnen:
           a. Falls Stickerei: Stichzahl × Preis pro 1000 Stiche
           b. Falls Druck: Fläche × Preis pro cm²
           c. Textil-Preise addieren (aus OrderItems)
        
        # Order erstellen
        7. Order-Objekt erstellen
        8. In DB speichern
        
        # OrderItems erstellen
        9. Für jedes Item:
           a. OrderItem erstellen
           b. Prüfen ob Artikel auf Lager
           c. Falls nicht: supplier_order_status = 'to_order'
           d. In DB speichern
        
        # Status-Historie
        10. OrderStatusHistory erstellen (status = 'new')
        
        # Lieferantenbestellungen
        11. Falls OrderItems mit status='to_order':
            - Lieferantenbestellungen erstellen
            - → supplier_controller.create_order_from_order_items()
        
        12. Aktivität protokollieren
    
    Returns:
        Redirect: /orders/show/<id>
        Flash: Success-Message
    
    Errors:
        - ValidationError: Zurück zu /orders/new
        - FileUploadError: Fehler beim Design-Upload
    """
```

#### **GET /orders/show/<id>**
```python
def show(id):
    """
    Auftragsdetails anzeigen
    
    URL-Parameter:
        - id: String - Auftrags-ID
    
    Process:
        1. Auftrag aus DB laden
        2. Kunde laden
        3. OrderItems laden mit Artikel-Daten
        4. Status-Historie laden
        5. Design-Dateien laden
        6. Produktionsstatus laden
        7. Versandstatus laden
        8. Maschinen-Zuweisung laden
    
    Returns:
        Template: orders/show.html
        Context:
            - order: Order
            - customer: Customer
            - items: List[OrderItem]
            - status_history: List[OrderStatusHistory]
            - design_file_url: String (optional)
            - design_thumbnail_url: String (optional)
            - machine: Machine (optional)
            - shipments: List[Shipment]
            - can_start_production: Boolean
            - production_ready_message: String
    
    Errors:
        - NotFound: 404 wenn Auftrag nicht existiert
    """
```

#### **POST /orders/change-status/<id>**
```python
def change_status(id):
    """
    Status ändern
    
    URL-Parameter:
        - id: String - Auftrags-ID
    
    Form-Data:
        - new_status: String (required)
        - comment: Text (optional)
        - assigned_machine_id: String (optional, bei 'in_production')
    
    Process:
        1. Auftrag laden
        2. Validierung (Status-Übergang erlaubt?)
        3. Falls new_status = 'in_production':
           a. Prüfen ob Design bereit
           b. Maschine zuweisen
           c. ProductionSchedule erstellen
           d. production_start setzen
        
        4. Falls new_status = 'completed':
           a. completed_at = now
           b. production_end = now
           c. production_minutes berechnen
        
        5. Status aktualisieren
        6. OrderStatusHistory erstellen
        7. In DB speichern
        8. Aktivität protokollieren
    
    Returns:
        Redirect: /orders/show/<id>
        Flash: Success-Message
    
    Errors:
        - ValidationError: Ungültiger Status-Übergang
        - BusinessRuleError: Design nicht bereit für Produktion
    """
```

#### **GET /orders/edit/<id>**
```python
def edit(id):
    """
    Auftrag bearbeiten
    
    URL-Parameter:
        - id: String - Auftrags-ID
    
    Returns:
        Template: orders/edit.html
        Context:
            - order: Order
            - customer: Customer
            - items: List[OrderItem]
            - customers: List[Customer]
            - machines: List[Machine]
            - threads: List[Thread]
            - articles: List[Article]
    
    Errors:
        - NotFound: 404
        - BusinessRuleError: Auftrag kann nicht bearbeitet werden (z.B. bereits in Produktion)
    """
```

#### **POST /orders/edit/<id>**
```python
def update(id):
    """
    Auftrag aktualisieren
    
    URL-Parameter:
        - id: String - Auftrags-ID
    
    Form-Data:
        [Ähnliche Felder wie bei create()]
    
    Process:
        1. Auftrag laden
        2. Validierung
        3. Design aktualisieren (falls neue Datei)
        4. OrderItems aktualisieren (löschen/hinzufügen/ändern)
        5. Preise neu berechnen
        6. Metadaten aktualisieren
        7. In DB speichern
        8. Aktivität protokollieren
    
    Returns:
        Redirect: /orders/show/<id>
        Flash: Success-Message
    """
```

#### **GET /orders/order-sheet/<id>**
```python
def order_sheet(id):
    """
    Auftragsblatt drucken
    
    URL-Parameter:
        - id: String - Auftrags-ID
    
    Returns:
        Template: orders/order_sheet.html (Druckansicht)
        Context:
            - order: Order
            - customer: Customer
            - items: List[OrderItem]
            - design_thumbnail: String (Base64)
            - production_instructions: String
    """
```

#### **GET /orders/production-labels/<id>**
```python
def production_labels(id):
    """
    Produktions-Etiketten drucken
    
    URL-Parameter:
        - id: String - Auftrags-ID
    
    Returns:
        Template: orders/production_labels.html (Druckansicht)
        Context:
            - order: Order
            - items: List[OrderItem]
            - labels: List[Dict]
              [
                {
                  article: Article,
                  quantity: Integer,
                  size: String,
                  color: String,
                  barcode: String
                }
              ]
    """
```

---

*Fortsetzung mit weiteren Controllern in nächster Datei...*

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**
