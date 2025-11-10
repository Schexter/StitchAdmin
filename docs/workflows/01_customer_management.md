# Workflow: Kundenverwaltung

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**

---

## Prozess: Neuen Kunden anlegen

```mermaid
flowchart TD
    Start([Start: Neuer Kunde]) --> CheckType{Kundentyp?}
    
    CheckType -->|Privatkunde| FormPrivate[Formular: Privatkundenfelder<br/>- Vorname/Nachname<br/>- Geburtsdatum<br/>- Kontaktdaten<br/>- Adresse]
    CheckType -->|Geschäftskunde| FormBusiness[Formular: Geschäftskundenfelder<br/>- Firmenname<br/>- Kontaktperson<br/>- USt-IdNr./Steuernr.<br/>- Abteilung/Position]
    
    FormPrivate --> ValidateData{Daten<br/>valide?}
    FormBusiness --> ValidateData
    
    ValidateData -->|Nein| ShowErrors[Fehler anzeigen:<br/>- Pflichtfelder fehlen<br/>- E-Mail ungültig<br/>- etc.]
    ShowErrors --> CheckType
    
    ValidateData -->|Ja| GenerateID[Kunden-ID generieren<br/>Format: CUST-YYYYMMDD-XXXX]
    GenerateID --> SaveDB[(In Datenbank<br/>speichern)]
    SaveDB --> LogActivity[Aktivität protokollieren:<br/>User + Action + Timestamp]
    LogActivity --> ShowSuccess[✅ Erfolgsmeldung<br/>anzeigen]
    ShowSuccess --> End([Ende])
```

---

## Prozess: Kunde bearbeiten

```mermaid
flowchart TD
    Start([Start: Kunde bearbeiten]) --> LoadCustomer[(Kunde aus DB laden)]
    LoadCustomer --> CheckExists{Kunde<br/>existiert?}
    
    CheckExists -->|Nein| Error404[❌ 404 Fehler:<br/>Kunde nicht gefunden]
    Error404 --> End([Ende])
    
    CheckExists -->|Ja| DisplayForm[Formular mit<br/>vorausgefüllten Daten]
    DisplayForm --> UserEdits[Benutzer bearbeitet Felder]
    UserEdits --> ValidateChanges{Änderungen<br/>valide?}
    
    ValidateChanges -->|Nein| ShowErrors[Fehler anzeigen]
    ShowErrors --> DisplayForm
    
    ValidateChanges -->|Ja| SaveChanges[(Änderungen<br/>in DB speichern)]
    SaveChanges --> UpdateTimestamp[updated_at &<br/>updated_by aktualisieren]
    UpdateTimestamp --> LogActivity[Aktivität protokollieren:<br/>Customer updated]
    LogActivity --> ShowSuccess[✅ Erfolgsmeldung]
    ShowSuccess --> End
```

---

## Prozess: Kunde löschen

```mermaid
flowchart TD
    Start([Start: Kunde löschen]) --> LoadCustomer[(Kunde aus DB laden)]
    LoadCustomer --> CheckExists{Kunde<br/>existiert?}
    
    CheckExists -->|Nein| Error404[❌ 404 Fehler]
    Error404 --> End([Ende])
    
    CheckExists -->|Ja| CheckOrders{Hat Kunde<br/>Aufträge?}
    
    CheckOrders -->|Ja| ShowWarning[⚠️ Warnung anzeigen:<br/>Kunde hat X Aufträge!]
    ShowWarning --> ConfirmDelete{Löschen<br/>bestätigen?}
    
    CheckOrders -->|Nein| DirectConfirm{Löschen<br/>bestätigen?}
    
    ConfirmDelete -->|Nein| Cancel[Abbruch]
    DirectConfirm -->|Nein| Cancel
    Cancel --> End
    
    ConfirmDelete -->|Ja| DeleteCustomer[(Kunde aus DB<br/>löschen)]
    DirectConfirm -->|Ja| DeleteCustomer
    
    DeleteCustomer --> CascadeOrders{Aufträge<br/>vorhanden?}
    CascadeOrders -->|Ja| UpdateOrders[customer_id in Orders<br/>auf NULL setzen]
    CascadeOrders -->|Nein| LogDelete
    UpdateOrders --> LogDelete[Aktivität protokollieren:<br/>Customer deleted]
    LogDelete --> ShowSuccess[✅ Kunde gelöscht]
    ShowSuccess --> End
```

---

## Prozess: Kunde suchen

```mermaid
flowchart TD
    Start([Start: Kundensuche]) --> DisplaySearch[Suchformular anzeigen]
    DisplaySearch --> UserInput[Benutzer gibt<br/>Suchbegriff ein]
    UserInput --> CheckInput{Eingabe<br/>vorhanden?}
    
    CheckInput -->|Nein| ShowAll[(Alle Kunden<br/>aus DB laden)]
    CheckInput -->|Ja| SearchDB[(Suche in DB:<br/>LIKE %term%)]
    
    SearchDB --> ApplyFilters{Filter<br/>aktiv?}
    ShowAll --> ApplyFilters
    
    ApplyFilters -->|Ja| FilterResults[Filter anwenden:<br/>- Kundentyp<br/>- Newsletter<br/>- PLZ-Bereich]
    ApplyFilters -->|Nein| SortResults
    
    FilterResults --> SortResults[Ergebnisse sortieren:<br/>- Nach Name<br/>- Nach Datum<br/>- Nach ID]
    
    SortResults --> Paginate[Paginierung:<br/>25 Kunden pro Seite]
    Paginate --> DisplayResults[Ergebnisse anzeigen]
    
    DisplayResults --> UserAction{Benutzer-<br/>Aktion?}
    UserAction -->|Details| ShowDetails[Kunden-Details]
    UserAction -->|Bearbeiten| EditCustomer[Kunde bearbeiten]
    UserAction -->|Neue Suche| DisplaySearch
    UserAction -->|Ende| End([Ende])
```

---

## Datenfluss: Customer-Model

```mermaid
flowchart LR
    User[Benutzer]
    Controller[customer_controller_db.py]
    Model[Customer Model]
    Database[(SQLite DB:<br/>customers Tabelle)]
    
    User -->|HTTP Request| Controller
    Controller -->|Query| Model
    Model -->|SQL| Database
    Database -->|Result| Model
    Model -->|Data| Controller
    Controller -->|Render| Template[Jinja2 Template]
    Template -->|HTML Response| User
    
    style Database fill:#f9f,stroke:#333,stroke-width:2px
    style Model fill:#bbf,stroke:#333,stroke-width:2px
    style Controller fill:#bfb,stroke:#333,stroke-width:2px
```

---

## Klassen & Methoden

### Customer Model (`src/models/models.py`)

**Hauptattribute:**
- `id`: Eindeutige Kunden-ID (CUST-YYYYMMDD-XXXX)
- `customer_type`: 'private' oder 'business'
- `first_name`, `last_name`: Name (Privatkunde)
- `company_name`: Firmenname (Geschäftskunde)
- `email`, `phone`, `mobile`: Kontaktdaten
- `street`, `house_number`, `postal_code`, `city`, `country`: Adresse
- `tax_id`, `vat_id`: Steuernummern (Geschäftskunde)
- `newsletter`: Boolean - Newsletter-Anmeldung
- `notes`: Freitext-Notizen

**Properties:**
- `display_name`: Gibt formattierten Namen zurück
  - Privatkunde: "Vorname Nachname"
  - Geschäftskunde: "Firmenname"

**Methods:**
- `get(key, default=None)`: Dictionary-kompatibel

**Relationships:**
- `orders`: 1:n zu Order

---

### Controller: `customer_controller_db.py`

**Blueprint:** `customer_bp`  
**URL-Prefix:** `/customers`

**Routen:**

| Route | Methode | Funktion | Beschreibung |
|-------|---------|----------|--------------|
| `/` | GET | `index()` | Kundenliste mit Suche/Filter |
| `/new` | GET | `new()` | Formular für neuen Kunden |
| `/create` | POST | `create()` | Kunden in DB anlegen |
| `/<id>` | GET | `show(id)` | Kunden-Details anzeigen |
| `/<id>/edit` | GET | `edit(id)` | Bearbeitungs-Formular |
| `/<id>/update` | POST | `update(id)` | Änderungen speichern |
| `/<id>/delete` | POST | `delete(id)` | Kunden löschen |

**Wichtige Funktionen:**

```python
def create():
    # 1. Formulardaten validieren
    # 2. Kunden-ID generieren
    # 3. Customer-Objekt erstellen
    # 4. In DB speichern (db.session.add + commit)
    # 5. Aktivität protokollieren
    # 6. Erfolgsmeldung & Redirect
    pass

def update(id):
    # 1. Customer aus DB laden
    # 2. Formulardaten validieren
    # 3. Attribute aktualisieren
    # 4. updated_at, updated_by setzen
    # 5. Änderungen speichern (db.session.commit)
    # 6. Aktivität protokollieren
    # 7. Erfolgsmeldung & Redirect
    pass

def delete(id):
    # 1. Customer aus DB laden
    # 2. Prüfen ob Aufträge vorhanden
    # 3. Warnung anzeigen wenn Aufträge
    # 4. Nach Bestätigung: db.session.delete
    # 5. Commit
    # 6. Aktivität protokollieren
    # 7. Erfolgsmeldung & Redirect
    pass
```

---

## Templates

**Verzeichnis:** `src/templates/customers/`

### `index.html` - Kundenliste
- Suchformular (Name, E-Mail, ID)
- Filter (Kundentyp, Newsletter, PLZ-Bereich)
- Ergebnis-Tabelle mit Sortierung
- Paginierung (25 pro Seite)
- Aktionen: Details, Bearbeiten, Löschen

### `new.html` - Neuer Kunde
- Kundentyp-Auswahl (Radio: Privat/Geschäft)
- Dynamisches Formular (JS: Felder ein-/ausblenden)
- Validierung (HTML5 + JavaScript)
- Speichern → POST /customers/create

### `show.html` - Kunden-Details
- Alle Kundendaten anzeigen
- Verknüpfte Aufträge (Tabelle)
- Aktivitäts-Historie
- Aktionen: Bearbeiten, Löschen, Neuer Auftrag

### `edit.html` - Kunde bearbeiten
- Vorausgefülltes Formular
- Gleiche Validierung wie new.html
- Speichern → POST /customers/<id>/update

---

## Validierungsregeln

### Pflichtfelder (Privatkunde)
- ✅ Vorname
- ✅ Nachname
- ✅ E-Mail ODER Telefon

### Pflichtfelder (Geschäftskunde)
- ✅ Firmenname
- ✅ Kontaktperson
- ✅ E-Mail ODER Telefon

### Optionale Felder
- Geburtsdatum (Privatkunde)
- Adresse (Straße, PLZ, Ort)
- USt-IdNr., Steuernr. (Geschäftskunde)
- Abteilung, Position (Geschäftskunde)
- Notizen
- Newsletter-Anmeldung

### Format-Validierung
- **E-Mail:** Regex-Validierung
- **Telefon/Mobil:** Nur Zahlen, Leerzeichen, +, -, ()
- **PLZ:** 5 Ziffern (Deutschland)
- **USt-IdNr.:** DE + 9 Ziffern

---

## Sicherheit & Berechtigungen

### Zugriffskontrolle
- Alle Routen: `@login_required`
- Nur eingeloggte Benutzer dürfen Kunden verwalten

### Aktivitäts-Protokollierung
Alle Aktionen werden in `activity_logs` protokolliert:
- `customer_created` - Kunde angelegt
- `customer_updated` - Kunde bearbeitet
- `customer_deleted` - Kunde gelöscht

Format:
```python
ActivityLog(
    username=current_user.username,
    action='customer_created',
    details=f'Customer {customer.id} - {customer.display_name}',
    timestamp=datetime.utcnow()
)
```

---

## Fehlerbehandlung

### Häufige Fehler

**404 - Kunde nicht gefunden:**
```python
customer = Customer.query.get(id)
if not customer:
    flash('Kunde nicht gefunden!', 'danger')
    return redirect(url_for('customer.index'))
```

**Duplikate E-Mail:**
```python
existing = Customer.query.filter_by(email=email).first()
if existing:
    flash('E-Mail bereits vergeben!', 'warning')
    return redirect(url_for('customer.new'))
```

**Datenbankfehler:**
```python
try:
    db.session.commit()
except Exception as e:
    db.session.rollback()
    flash(f'Fehler beim Speichern: {str(e)}', 'danger')
    return redirect(url_for('customer.new'))
```

---

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Stand:** 10. November 2025
