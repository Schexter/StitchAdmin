# Workflow: Auftragsverwaltung

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**

---

## Gesamtprozess: Von der Anfrage bis zur Auslieferung

```mermaid
flowchart TD
    Start([Kundenanfrage]) --> CreateOrder[Auftrag anlegen]
    CreateOrder --> SelectType{Auftragstyp?}
    
    SelectType -->|Stickerei| EmbroideryFlow[Stickerei-Details<br/>erfassen]
    SelectType -->|Druck| PrintFlow[Druck-Details<br/>erfassen]
    SelectType -->|Kombiniert| CombinedFlow[Stickerei + Druck<br/>Details erfassen]
    
    EmbroideryFlow --> AddTextiles[Textilien hinzufügen]
    PrintFlow --> AddTextiles
    CombinedFlow --> AddTextiles
    
    AddTextiles --> CheckDesign{Design<br/>vorhanden?}
    
    CheckDesign -->|Kunde liefert| UploadDesign[Design hochladen<br/>& analysieren]
    CheckDesign -->|Muss bestellt werden| OrderDesign[Design beim<br/>Lieferanten bestellen]
    
    UploadDesign --> DesignReady{Design<br/>OK?}
    OrderDesign --> WaitDesign[Warten auf<br/>Lieferant]
    WaitDesign --> DesignReady
    
    DesignReady -->|Nein| FixDesign[Design korrigieren]
    FixDesign --> DesignReady
    
    DesignReady -->|Ja| CheckTextiles{Textilien<br/>vorrätig?}
    
    CheckTextiles -->|Nein| OrderTextiles[Textilien bei<br/>Lieferant bestellen]
    OrderTextiles --> WaitTextiles[Warten auf<br/>Lieferung]
    WaitTextiles --> TextilesReady
    
    CheckTextiles -->|Ja| TextilesReady[Alle Materialien<br/>verfügbar]
    
    TextilesReady --> UpdateStatus1[Status: accepted]
    UpdateStatus1 --> ScheduleProduction[Produktion planen]
    ScheduleProduction --> UpdateStatus2[Status: in_progress]
    UpdateStatus2 --> StartProduction[Produktion starten]
    StartProduction --> UpdateStatus3[Status: production]
    UpdateStatus3 --> Production[Produktion durchführen]
    Production --> QualityCheck{Qualitätsprüfung<br/>OK?}
    
    QualityCheck -->|Nein| Rework[Nacharbeit/<br/>Neuproduktion]
    Rework --> Production
    
    QualityCheck -->|Ja| UpdateStatus4[Status: ready]
    UpdateStatus4 --> NotifyCustomer[Kunde benachrichtigen:<br/>Abholbereit]
    NotifyCustomer --> WaitPickup[Warten auf<br/>Abholung/Versand]
    WaitPickup --> CheckDelivery{Abholung oder<br/>Versand?}
    
    CheckDelivery -->|Abholung| Pickup[Kunde holt ab]
    CheckDelivery -->|Versand| Ship[Versand erstellen]
    
    Pickup --> UpdateStatus5[Status: completed]
    Ship --> UpdateStatus5
    UpdateStatus5 --> CreateInvoice[Rechnung erstellen]
    CreateInvoice --> End([Auftrag abgeschlossen])
```

---

## Detailprozess: Stickerei-Auftrag erstellen

```mermaid
flowchart TD
    Start([Start: Neuer<br/>Stickerei-Auftrag]) --> SelectCustomer[Kunde auswählen]
    SelectCustomer --> EnterBasics[Grunddaten:<br/>- Auftragsnummer<br/>- Liefertermin<br/>- Eilauftrag?]
    
    EnterBasics --> UploadDesign{Design-Datei<br/>hochladen?}
    
    UploadDesign -->|Ja| ValidateFile{Dateiformat<br/>OK?}
    ValidateFile -->|Nein| ShowError[❌ Fehler:<br/>Nur DST/EMB/PES/etc.]
    ShowError --> UploadDesign
    
    ValidateFile -->|Ja| AnalyzeDST[DST-Datei analysieren:<br/>- Stichzahl<br/>- Größe<br/>- Farbwechsel]
    
    AnalyzeDST --> ExtractColors[Farbliste extrahieren]
    ExtractColors --> MatchThreads[Garne zuordnen:<br/>- Madeira-Farben<br/>- Bestand prüfen]
    
    UploadDesign -->|Nein| SetDesignStatus[Design-Status:<br/>needs_order]
    SetDesignStatus --> MatchThreads
    
    MatchThreads --> EnterEmbroideryDetails[Stickerei-Details:<br/>- Position (Brust/Rücken/etc.)<br/>- Größe<br/>- Anzahl Positionen]
    
    EnterEmbroideryDetails --> CalculateStitchPrice[Preis berechnen:<br/>Grundpreis +<br/>Stichzahl × Preis/1000]
    
    CalculateStitchPrice --> AddTextileItems[Textilien hinzufügen]
    AddTextileItems --> SelectArticle[Artikel auswählen]
    SelectArticle --> SelectVariant[Variante wählen:<br/>- Größe<br/>- Farbe]
    SelectVariant --> EnterQuantity[Menge eingeben]
    EnterQuantity --> CalculateItemPrice[Position-Preis:<br/>Menge × VK-Preis]
    
    CalculateItemPrice --> CheckStock{Artikel<br/>vorrätig?}
    
    CheckStock -->|Nein| SetOrderStatus[Textile Status:<br/>to_order]
    CheckStock -->|Ja| SetOrderStatus2[Textile Status:<br/>none]
    
    SetOrderStatus --> AddMore{Weitere<br/>Positionen?}
    SetOrderStatus2 --> AddMore
    
    AddMore -->|Ja| AddTextileItems
    AddMore -->|Nein| CalculateTotal[Gesamtpreis:<br/>Stickerei + Textilien]
    
    CalculateTotal --> EnterDiscount[Rabatt eingeben?<br/>Optional]
    EnterDiscount --> EnterDeposit[Anzahlung?<br/>Optional]
    
    EnterDeposit --> AddNotes[Notizen hinzufügen:<br/>- Intern<br/>- Kunde]
    
    AddNotes --> SaveOrder[(Auftrag in DB<br/>speichern)]
    SaveOrder --> SetInitialStatus[Status: new]
    SetInitialStatus --> LogActivity[Aktivität<br/>protokollieren]
    LogActivity --> ShowSuccess[✅ Auftrag erstellt]
    ShowSuccess --> End([Ende])
```

---

## Prozess: Design-Workflow

```mermaid
flowchart TD
    Start([Design-Workflow starten]) --> CheckStatus{Design-<br/>Status?}
    
    CheckStatus -->|none| PromptUpload{Kunde hat<br/>Design?}
    PromptUpload -->|Ja| UploadForm[Upload-Formular<br/>anzeigen]
    PromptUpload -->|Nein| OrderForm[Lieferanten-<br/>Bestellung]
    
    UploadForm --> SelectFile[Datei auswählen:<br/>DST/EMB/PES/PNG/JPG]
    SelectFile --> Validate{Validierung<br/>OK?}
    
    Validate -->|Nein| ShowError[❌ Fehler anzeigen:<br/>- Falsches Format<br/>- Zu groß]
    ShowError --> UploadForm
    
    Validate -->|Ja| SaveFile[Datei sichern:<br/>uploads/designs/]
    SaveFile --> CheckDST{DST-Datei?}
    
    CheckDST -->|Ja| AnalyzeDST[Automatische Analyse:<br/>- Stichzahl<br/>- Größe<br/>- Farben]
    CheckDST -->|Nein| GenerateThumbnail[Thumbnail erstellen]
    
    AnalyzeDST --> UpdateOrder[(Order-Felder<br/>aktualisieren)]
    GenerateThumbnail --> UpdateOrder
    
    UpdateOrder --> SetStatusProvided[Design-Status:<br/>customer_provided]
    SetStatusProvided --> CheckReady{Produktions-<br/>bereit?}
    
    OrderForm --> SelectSupplier[Lieferant<br/>auswählen]
    SelectSupplier --> EnterOrderDetails[Bestelldetails:<br/>- Erwartetes Datum<br/>- Notizen]
    EnterOrderDetails --> SaveOrderRequest[(Design-Bestellung<br/>in Order speichern)]
    SaveOrderRequest --> SetStatusOrdered[Design-Status:<br/>ordered]
    SetStatusOrdered --> NotifyUser[👤 Benachrichtigung:<br/>Design bestellt]
    
    CheckReady -->|Ja| SetFinalStatus[Design-Status:<br/>ready]
    CheckReady -->|Nein| ReviewDesign[Design prüfen &<br/>ggf. anpassen]
    ReviewDesign --> CheckReady
    
    SetFinalStatus --> CanStartProduction[✅ Produktion<br/>kann starten]
    CanStartProduction --> End([Ende])
    
    NotifyUser --> WaitDelivery[Warten auf<br/>Lieferant]
    WaitDelivery --> ReceiveDesign[Design erhalten]
    ReceiveDesign --> SetStatusReceived[Design-Status:<br/>received]
    SetStatusReceived --> ReviewDesign
```

---

## Prozess: Textilien bestellen

```mermaid
flowchart TD
    Start([Textilien für<br/>Auftrag bestellen]) --> CheckItems[(OrderItems<br/>mit Status to_order)]
    
    CheckItems --> HasItems{Items<br/>vorhanden?}
    HasItems -->|Nein| NoItems[ℹ️ Keine Bestellung<br/>erforderlich]
    NoItems --> End([Ende])
    
    HasItems -->|Ja| GroupBySupplier[Items nach<br/>Lieferant gruppieren]
    GroupBySupplier --> ForEachSupplier{Für jeden<br/>Lieferant}
    
    ForEachSupplier --> CreateSupplierOrder[SupplierOrder<br/>erstellen]
    CreateSupplierOrder --> AddItemsToOrder[Items zur<br/>Bestellung hinzufügen]
    AddItemsToOrder --> CalculateSubtotal[Zwischensumme<br/>berechnen]
    CalculateSubtotal --> AddShipping[Versandkosten<br/>hinzufügen]
    AddShipping --> CalculateTotal[Gesamtbetrag<br/>berechnen]
    
    CalculateTotal --> SaveSupplierOrder[(SupplierOrder<br/>in DB speichern)]
    SaveSupplierOrder --> LinkOrderItems[OrderItems mit<br/>SupplierOrder verknüpfen]
    LinkOrderItems --> UpdateItemStatus[Item-Status:<br/>ordered]
    
    UpdateItemStatus --> CheckWebshop{Webshop-<br/>Integration?}
    
    CheckWebshop -->|Ja| AutoOrder[Automatische<br/>Bestellung]
    CheckWebshop -->|Nein| ManualOrder[Manuelle<br/>Bestellung]
    
    AutoOrder --> GenerateOrderURL[Webshop-URL<br/>generieren]
    GenerateOrderURL --> SubmitOrder[API-Call:<br/>Bestellung absenden]
    SubmitOrder --> CheckResponse{Erfolgreich?}
    
    CheckResponse -->|Nein| LogError[Fehler protokollieren]
    LogError --> ManualOrder
    
    CheckResponse -->|Ja| SaveTrackingInfo[Tracking-Info<br/>speichern]
    SaveTrackingInfo --> NotifySuccess[✅ Bestellung<br/>erfolgreich]
    
    ManualOrder --> OpenWebshopURL[Webshop-Link<br/>öffnen]
    OpenWebshopURL --> ManualEntry[👤 Benutzer bestellt<br/>manuell]
    ManualEntry --> EnterTrackingManual[Tracking-Info<br/>manuell eingeben]
    EnterTrackingManual --> NotifySuccess
    
    NotifySuccess --> MoreSuppliers{Weitere<br/>Lieferanten?}
    MoreSuppliers -->|Ja| ForEachSupplier
    MoreSuppliers -->|Nein| AllOrdered[Alle Textilien<br/>bestellt]
    AllOrdered --> End
```

---

## Prozess: Produktionsstart

```mermaid
flowchart TD
    Start([Produktion starten]) --> LoadOrder[(Order laden)]
    LoadOrder --> CheckReadiness{Kann Produktion<br/>starten?}
    
    CheckReadiness --> CheckDesign{Design<br/>bereit?}
    CheckDesign -->|Nein| Error1[❌ Fehler:<br/>Design fehlt]
    Error1 --> End([Ende])
    
    CheckDesign -->|Ja| CheckTextiles{Textilien<br/>vorhanden?}
    CheckTextiles -->|Nein| Error2[❌ Fehler:<br/>Textilien fehlen]
    Error2 --> End
    
    CheckTextiles -->|Ja| CheckThreads{Garne<br/>vorrätig?}
    CheckThreads -->|Nein| Error3[❌ Fehler:<br/>Garne fehlen]
    Error3 --> End
    
    CheckThreads -->|Ja| SelectMachine[Maschine<br/>auswählen]
    SelectMachine --> CheckCapacity{Maschinen-<br/>Kapazität?}
    
    CheckCapacity -->|Belegt| ShowAlternatives[Alternative<br/>Maschinen anzeigen]
    ShowAlternatives --> SelectMachine
    
    CheckCapacity -->|Frei| AssignMachine[Maschine zuweisen]
    AssignMachine --> CalculateTime[Produktionszeit<br/>schätzen:<br/>Setup + Stickzeit]
    
    CalculateTime --> CreateSchedule[(ProductionSchedule<br/>erstellen)]
    CreateSchedule --> UpdateOrderStatus[Order-Status:<br/>in_progress]
    UpdateOrderStatus --> SetProductionStart[production_start:<br/>timestamp]
    
    SetProductionStart --> StartMachine[🏭 Maschine starten]
    StartMachine --> MonitorProduction[Produktion<br/>überwachen]
    
    MonitorProduction --> CheckProgress{Fortschritt?}
    CheckProgress -->|In Arbeit| MonitorProduction
    CheckProgress -->|Problem| HandleIssue[Problem behandeln:<br/>- Fadenbruch<br/>- Maschine stoppt]
    HandleIssue --> MonitorProduction
    
    CheckProgress -->|Fertig| CompleteProduction[Produktion<br/>abschließen]
    CompleteProduction --> RecordThreadUsage[Garnverbrauch<br/>erfassen]
    RecordThreadUsage --> UpdateStock[(Thread-Stock<br/>aktualisieren)]
    UpdateStock --> SetProductionEnd[production_end:<br/>timestamp]
    SetProductionEnd --> UpdateOrderStatus2[Order-Status:<br/>production]
    UpdateOrderStatus2 --> End
```

---

## Prozess: Qualitätsprüfung & Fertigstellung

```mermaid
flowchart TD
    Start([Produktion fertig]) --> QualityCheck[Qualitätsprüfung<br/>durchführen]
    QualityCheck --> CheckStitching{Stickerei<br/>OK?}
    
    CheckStitching -->|Nein| IdentifyIssue[Problem identifizieren:<br/>- Fadenbruch<br/>- Versatz<br/>- Qualität]
    IdentifyIssue --> CanRework{Nacharbeit<br/>möglich?}
    
    CanRework -->|Ja| Rework[Nacharbeit<br/>durchführen]
    Rework --> QualityCheck
    
    CanRework -->|Nein| RestartProduction[Neuproduktion<br/>erforderlich]
    RestartProduction --> LogWaste[Ausschuss<br/>dokumentieren]
    LogWaste --> Start
    
    CheckStitching -->|Ja| CheckTextile{Textil<br/>OK?}
    
    CheckTextile -->|Nein| IdentifyTextileIssue[Problem:<br/>- Beschädigung<br/>- Verschmutzung]
    IdentifyTextileIssue --> ReplaceTextile{Ersatz<br/>möglich?}
    
    ReplaceTextile -->|Ja| OrderNewTextile[Neues Textil<br/>bestellen]
    OrderNewTextile --> RestartProduction
    
    ReplaceTextile -->|Nein| ContactCustomer[Kunde kontaktieren:<br/>Alternativen besprechen]
    ContactCustomer --> End([Ende])
    
    CheckTextile -->|Ja| FinalCheck[Endkontrolle:<br/>- Sauberkeit<br/>- Vollständigkeit]
    
    FinalCheck --> Package[Verpacken &<br/>Kennzeichnen]
    Package --> UpdateStatus[Order-Status:<br/>ready]
    UpdateStatus --> SetCompletedBy[completed_at +<br/>completed_by]
    SetCompletedBy --> NotifyCustomer[📧 Kunde benachrichtigen:<br/>Abholbereit]
    NotifyCustomer --> PrintDocuments[Dokumente drucken:<br/>- Lieferschein<br/>- Rechnung]
    PrintDocuments --> StoreReady[Im Lager<br/>bereitstellen]
    StoreReady --> End
```

---

## Datenfluss: Order-Model

```mermaid
flowchart LR
    User[Benutzer]
    Controller[order_controller_db.py]
    OrderModel[Order Model]
    ItemModel[OrderItem Model]
    StatusModel[OrderStatusHistory]
    Database[(SQLite DB)]
    
    User -->|Create Order| Controller
    Controller -->|new Order| OrderModel
    OrderModel -->|SQL INSERT| Database
    
    User -->|Add Item| Controller
    Controller -->|new OrderItem| ItemModel
    ItemModel -->|SQL INSERT| Database
    ItemModel -->|FK order_id| OrderModel
    
    User -->|Change Status| Controller
    Controller -->|update Order.status| OrderModel
    Controller -->|new History| StatusModel
    StatusModel -->|SQL INSERT| Database
    StatusModel -->|FK order_id| OrderModel
    
    style Database fill:#f9f,stroke:#333,stroke-width:2px
    style OrderModel fill:#bbf,stroke:#333,stroke-width:2px
    style Controller fill:#bfb,stroke:#333,stroke-width:2px
```

---

## Klassen & Methoden

### Order Model (`src/models/models.py`)

**Hauptattribute:**
- `id`: Order-ID (ORD-YYYYMMDD-XXXX)
- `customer_id`: FK → Customer
- `order_number`: Eindeutige Auftragsnummer
- `order_type`: 'embroidery'/'printing'/'dtf'/'combined'
- `status`: Auftragsstatus (siehe Status-Übersicht)
- `stitch_count`: Stichzahl (Stickerei)
- `design_file_path`: Pfad zur Design-Datei
- `total_price`: Gesamtpreis
- `due_date`: Liefertermin
- `assigned_machine_id`: FK → Machine

**Design-Workflow-Felder:**
- `design_status`: 'none'/'customer_provided'/'needs_order'/'ordered'/'received'/'ready'
- `design_supplier_id`: FK → Supplier
- `design_order_date`, `design_expected_date`, `design_received_date`

**Methods:**
- `can_start_production()` → (bool, reason)
- `get_design_status_display()` → String
- `has_design_file()` → bool
- `needs_design_order()` → bool
- `is_design_ready()` → bool

**Relationships:**
- `customer`: n:1 → Customer
- `items`: 1:n → OrderItem
- `status_history`: 1:n → OrderStatusHistory
- `shipments`: 1:n → Shipment
- `production_schedules`: 1:n → ProductionSchedule
- `assigned_machine`: n:1 → Machine
- `design_supplier`: n:1 → Supplier

---

### OrderItem Model

**Attribute:**
- `id`: Item-ID (auto-increment)
- `order_id`: FK → Order
- `article_id`: FK → Article
- `quantity`: Menge
- `unit_price`: Stückpreis
- `textile_size`, `textile_color`: Variante
- **Lieferanten-Bestellung:**
  - `supplier_order_status`: 'none'/'to_order'/'ordered'/'delivered'
  - `supplier_order_id`: FK → SupplierOrder
  - `supplier_order_date`, `supplier_expected_date`, `supplier_delivered_date`

---

### Controller: `order_controller_db.py`

**Blueprint:** `order_bp`  
**URL-Prefix:** `/orders`

**Hauptrouten:**

| Route | Methode | Funktion | Beschreibung |
|-------|---------|----------|--------------|
| `/` | GET | `index()` | Auftragsliste |
| `/new` | GET | `new()` | Neuer Auftrag |
| `/create` | POST | `create()` | Auftrag anlegen |
| `/<id>` | GET | `show(id)` | Auftrags-Details |
| `/<id>/edit` | GET | `edit(id)` | Bearbeiten |
| `/<id>/update` | POST | `update(id)` | Speichern |
| `/<id>/status` | POST | `update_status(id)` | Status ändern |
| `/<id>/items/add` | POST | `add_item(id)` | Position hinzufügen |
| `/<id>/design` | GET | `design_workflow(id)` | Design-Workflow |

---

## Status-Übersicht

### Auftragsstatus

1. **new** - Neu erfasst
   - Auftrag angelegt
   - Noch nicht bestätigt

2. **accepted** - Angenommen
   - Auftrag bestätigt
   - Design & Materialien geprüft
   - Produktionsplanung möglich

3. **in_progress** - In Bearbeitung
   - Materialien beschafft
   - Produktion geplant
   - Wartet auf freie Maschine

4. **production** - In Produktion
   - Aktiv an Maschine
   - Wird produziert

5. **ready** - Fertig
   - Produktion abgeschlossen
   - Qualitätsprüfung bestanden
   - Abholbereit

6. **completed** - Abgeschlossen
   - Übergeben/Versendet
   - Rechnung erstellt
   - Bezahlt

7. **cancelled** - Storniert
   - Auftrag abgebrochen

### Design-Status

1. **none** - Kein Design
2. **customer_provided** - Kunde hat geliefert
3. **needs_order** - Muss bestellt werden
4. **ordered** - Bei Lieferant bestellt
5. **received** - Vom Lieferanten erhalten
6. **ready** - Produktionsbereit

### Textile-Status (OrderItem)

1. **none** - Keine Bestellung nötig
2. **to_order** - Muss bestellt werden
3. **ordered** - Bestellt
4. **delivered** - Geliefert

---

## Templates

**Verzeichnis:** `src/templates/orders/`

- `index.html` - Auftragsliste mit Filtern
- `new.html` - Neuer Auftrag (Formular)
- `show.html` - Auftrags-Details
- `edit.html` - Auftrag bearbeiten
- `design_workflow.html` - Design-Verwaltung
- `items_manage.html` - Positionen verwalten

---

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Stand:** 10. November 2025
