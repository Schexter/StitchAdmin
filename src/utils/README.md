# Utils-Module

**Zentrale Hilfsfunktionen und Services für StitchAdmin 2.0**

## 📋 Übersicht

Dieses Verzeichnis enthält wiederverwendbare Utility-Module, die in der gesamten Anwendung verwendet werden. Die Module sind nach Funktionsbereichen organisiert und bieten zentrale Services für Logging, Sicherheit, Formulare, E-Mail und mehr.

## 🔧 Verfügbare Module

### 1. Logger (`logger.py`)

**Zentrales Logging-System für alle Module**

#### Features:
- Separate Logger für verschiedene Bereiche (Error, Activity, Production, Import, Debug)
- Automatische Log-Datei-Rotation
- Konfigurierbare Log-Level
- Console-Ausgabe im Debug-Modus
- Strukturierte Log-Formate

#### Verwendung:
```python
from src.utils.logger import logger

# Fehler protokollieren
logger.log_error("Datenbankverbindung fehlgeschlagen", exception=e, module="database")

# Aktivität protokollieren
logger.log_activity(user="admin", action="customer_created", details="Kunde KU001 angelegt")

# Produktion protokollieren
logger.log_production(order_id="AUF001", status="in_progress", machine="M1")

# Import protokollieren
logger.log_import(source="Excel", record_count=100, success_count=98, error_count=2)

# Debug-Informationen
logger.log_debug("API-Anfrage gesendet", module="api")
```

#### Log-Dateien:
- `logs/error.log` - Fehlermeldungen
- `logs/activity.log` - Benutzeraktivitäten
- `logs/production.log` - Produktionsprozesse
- `logs/import.log` - Datenimporte
- `logs/debug.log` - Debug-Informationen

#### Integration in App:
```python
# In app.py bereits integriert:
app.logger_instance = logger
```

---

### 2. Security (`security.py`)

**Erweiterte Sicherheitsfunktionen**

#### Features:
- Login-Versuch-Tracking und Account-Sperrung
- Passwort-Stärke-Validierung
- Passwort-Reset-Token-Management
- Sichere Passwort-Generierung

#### Funktionen:

##### Login-Schutz:
```python
from src.utils.security import check_login_attempts, record_login_attempt

# Vor Login prüfen
is_blocked, remaining_time = check_login_attempts("admin")
if is_blocked:
    flash(f"Account gesperrt für {remaining_time} Minuten")

# Nach Login protokollieren
record_login_attempt("admin", success=True)  # oder False
```

##### Passwort-Validierung:
```python
from src.utils.security import check_password_strength

is_valid, messages = check_password_strength("MeinPasswort123!")
if not is_valid:
    for msg in messages:
        flash(msg, 'warning')
```

##### Passwort-Reset:
```python
from src.utils.security import generate_password_reset_token, validate_password_reset_token

# Token generieren
token = generate_password_reset_token("admin")
reset_link = f"https://example.com/reset?token={token}"

# Token validieren
username = validate_password_reset_token(token)
if username:
    # Token ist gültig
    pass
```

#### Dateien:
- `login_attempts.json` - Login-Versuch-Tracking
- `password_reset_tokens.json` - Reset-Tokens (24h gültig)

---

### 3. Activity Logger (`activity_logger.py`)

**Audit-Trail für Benutzeraktivitäten**

#### Features:
- Detaillierte Protokollierung aller Benutzeraktionen
- IP-Adresse-Tracking
- Historie pro Benutzer
- Automatische Begrenzung auf 1000 Einträge

#### Verwendung:
```python
from src.utils.activity_logger import log_activity, get_user_activities, get_recent_activities

# Aktivität protokollieren
log_activity(
    username="admin",
    action="customer_created",
    details="Neuer Kunde: Max Mustermann (KU123)",
    ip_address=request.remote_addr
)

# Benutzer-Historie abrufen
activities = get_user_activities("admin", limit=50)

# Neueste Aktivitäten
recent = get_recent_activities(limit=100)
```

#### Unterstützte Aktionen:
- `login` / `logout`
- `create_user` / `edit_user` / `delete_user`
- `customer_created` / `customer_updated`
- `order_created` / `order_updated`
- `settings_changed`
- etc.

#### Datei:
- `activity_log.json` - Aktivitäts-Protokoll

---

### 4. Filters (`filters.py`)

**Custom Jinja2 Template-Filters**

#### Features:
- Deutsche Datums- und Zeitformatierung
- Relative Zeitangaben ("vor 2 Stunden")
- Altersberechnung
- Text-Formatierung

#### Verfügbare Filter:

##### Datumsformatierung:
```jinja2
{{ order.created_at|format_date }}           {# 15.11.2025 #}
{{ order.created_at|format_datetime }}       {# 15.11.2025 14:30 #}
{{ order.created_at|format_datetime_full }}  {# 15.11.2025 14:30:45 #}
{{ order.created_at|format_time }}           {# 14:30 #}
```

##### Relative Zeit:
```jinja2
{{ activity.timestamp|time_ago }}  {# vor 2 Stunden #}
```

##### Weitere Filter:
```jinja2
{{ customer.birth_date|calculate_age }}     {# 35 #}
{{ description|nl2br|safe }}                {# Newlines zu <br> #}
```

#### Integration:
```python
# In app.py bereits registriert:
from src.utils.filters import register_filters
register_filters(app)
```

---

### 5. Form Helpers (`form_helpers.py`)

**Utility-Funktionen für Formular-Verarbeitung**

#### Features:
- Sichere Datentyp-Konvertierung
- Deutsche Dezimalzahlen (Komma → Punkt)
- Validierung von Pflichtfeldern
- Fehlerbehandlung mit Flash-Messages

#### Funktionen:

##### Datums-Parsing:
```python
from src.utils.form_helpers import parse_date_from_form, parse_datetime_from_form

# Datum aus Formular
birth_date = parse_date_from_form(request.form.get('birth_date'), 'Geburtsdatum')

# DateTime aus Formular
delivery_date = parse_datetime_from_form(request.form.get('delivery'), 'Liefertermin')
```

##### Zahlen-Parsing:
```python
from src.utils.form_helpers import parse_float_from_form, parse_int_from_form

# Float mit deutscher Notation (12,50 → 12.50)
price = parse_float_from_form(request.form.get('price'), 'Preis', default=0.0)

# Integer
quantity = parse_int_from_form(request.form.get('quantity'), 'Menge', default=1)
```

##### Sichere Form-Daten:
```python
from src.utils.form_helpers import safe_get_form_value, validate_required_fields

# Wert mit Fallback
name = safe_get_form_value(request.form, 'name', default='Unbekannt')

# Pflichtfelder validieren
required = ['name', 'email', 'phone']
if not validate_required_fields(request.form, required):
    return redirect(url_for('customer.create'))
```

---

### 6. E-Mail Service (`email_service.py`)

**E-Mail-Benachrichtigungen und -Versand**

#### Features:
- SMTP-basierter E-Mail-Versand
- HTML und Text-Format
- Vorgefertigte Templates
- Konfigurierbar über system_settings.json

#### Verwendung:

##### Willkommens-E-Mail:
```python
from src.utils.email_service import send_welcome_email

send_welcome_email(
    user_email="neuer.user@example.com",
    username="neuer.user"
)
```

##### Passwort-Reset:
```python
from src.utils.email_service import send_password_reset_email

send_password_reset_email(
    user_email="user@example.com",
    username="testuser",
    reset_link="https://stitchadmin.local/reset?token=abc123"
)
```

##### Sicherheitswarnung:
```python
from src.utils.email_service import send_security_alert

send_security_alert(
    user_email="user@example.com",
    username="testuser",
    alert_type="Verdächtige Login-Aktivität",
    details="Login von unbekannter IP-Adresse"
)
```

##### Benutzerdefinierte E-Mail:
```python
from src.utils.email_service import send_email

send_email(
    to_email="kunde@example.com",
    subject="Ihre Bestellung ist fertig",
    body="Ihre Bestellung AUF001 ist abholbereit.",
    html_body="<p>Ihre Bestellung <strong>AUF001</strong> ist abholbereit.</p>"
)
```

#### Konfiguration:
E-Mail-Einstellungen werden in `system_settings.json` gespeichert:
```json
{
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_username": "your-email@gmail.com",
  "smtp_password": "your-password",
  "smtp_from_email": "noreply@stitchadmin.local",
  "enable_email_notifications": true
}
```

---

### 7. Customer History (`customer_history.py`)

**Kunden-Historie-Verwaltung**

#### Features:
- Chronologische Historie pro Kunde
- Automatische Begrenzung (100 Einträge/Kunde)
- Benutzer-Tracking

#### Verwendung:
```python
from src.utils.customer_history import add_customer_history, get_customer_history

# Historie hinzufügen
add_customer_history(
    customer_id="KU001",
    action="order_created",
    details="Neue Bestellung AUF123 erstellt",
    user="admin"
)

# Historie abrufen
history = get_customer_history("KU001", limit=20)
for entry in history:
    print(f"{entry['timestamp']}: {entry['action']} - {entry['details']}")
```

#### Datei:
- `customer_history.json` - Kunden-Historie

---

### 8. Design-Module

#### Design Upload (`design_upload.py`)
- Upload-Validierung für Design-Dateien
- Unterstützte Formate: DST, EMB, PES, etc.
- Automatische Metadaten-Extraktion

#### Design Link Manager (`design_link_manager.py`)
- Verknüpfung von Design-Dateien mit Aufträgen
- Versionsverwaltung von Designs
- Design-Bibliothek-Verwaltung

#### DST Analyzer (`dst_analyzer.py`)
- Analyse von DST-Stickdateien
- Stichzahl-Berechnung
- Farbwechsel-Erkennung
- Maschinenzeit-Schätzung

#### File Analysis (`file_analysis.py`)
- Allgemeine Datei-Analyse
- MIME-Type-Erkennung
- Datei-Validierung

---

### 9. PDF-Module

#### PDF Analyzer (`pdf_analyzer.py`)
- Vollständige PDF-Analyse
- Text-Extraktion
- Metadaten-Auslesen

#### PDF Analyzer Lite (`pdf_analyzer_lite.py`)
- Lightweight PDF-Verarbeitung
- Schnelle Text-Extraktion
- Geringerer Speicherbedarf

---

## 🔄 Best Practices

### 1. Fehlerbehandlung
Alle Utils-Funktionen haben eingebaute Fehlerbehandlung. Kritische Fehler werden über das Logger-System protokolliert:

```python
try:
    result = some_util_function()
except Exception as e:
    logger.log_error("Fehler in Utility-Funktion", exception=e, module="utils")
```

### 2. Import-Konventionen
```python
# Einzelne Funktionen importieren
from src.utils.logger import log_error, log_activity

# Ganzes Modul importieren
from src.utils import security
from src.utils import form_helpers
```

### 3. Testing
Beim Testen von Utils-Modulen:
```python
import pytest
from src.utils.form_helpers import parse_float_from_form

def test_parse_float_german():
    result = parse_float_from_form("12,50", "test")
    assert result == 12.5
```

---

## 📝 Wartung

### Log-Rotation
Logs sollten regelmäßig rotiert werden:
```python
from src.utils.logger import logger
logger.clear_old_logs(days=30)
```

### Token-Cleanup
Abgelaufene Tokens sollten regelmäßig gelöscht werden:
```python
from src.utils.security import cleanup_expired_tokens
cleanup_expired_tokens()
```

---

## 🔒 Sicherheit

### Sensible Daten
- Passwort-Hashes niemals in Logs ausgeben
- E-Mail-Credentials sicher speichern
- Login-Attempt-Dateien schützen

### Validierung
Alle Benutzereingaben sollten durch Form Helpers validiert werden:
```python
from src.utils.form_helpers import validate_required_fields, safe_get_form_value

if validate_required_fields(request.form, ['name', 'email']):
    name = safe_get_form_value(request.form, 'name')
    # ... weiter verarbeiten
```

---

## 📊 Integration in Controller

Beispiel für einen typischen Controller mit Utils-Integration:

```python
from flask import Blueprint, request, flash, redirect, url_for
from src.utils.logger import logger
from src.utils.form_helpers import parse_date_from_form, validate_required_fields
from src.utils.activity_logger import log_activity
from src.utils.security import check_login_attempts

customer_bp = Blueprint('customer', __name__)

@customer_bp.route('/customer/create', methods=['POST'])
def create_customer():
    # Validierung
    required = ['first_name', 'last_name', 'email']
    if not validate_required_fields(request.form, required):
        return redirect(url_for('customer.new'))

    try:
        # Daten parsen
        birth_date = parse_date_from_form(request.form.get('birth_date'))

        # Kunde erstellen
        customer = Customer(...)
        db.session.add(customer)
        db.session.commit()

        # Aktivität protokollieren
        log_activity(
            username=current_user.username,
            action="customer_created",
            details=f"Kunde {customer.id} erstellt"
        )

        flash('Kunde erfolgreich erstellt', 'success')
        return redirect(url_for('customer.detail', customer_id=customer.id))

    except Exception as e:
        logger.log_error("Fehler beim Erstellen des Kunden", exception=e, module="customer")
        flash('Fehler beim Erstellen', 'error')
        return redirect(url_for('customer.new'))
```

---

## 🆕 Neues Utility-Modul hinzufügen

1. **Datei erstellen**: `src/utils/new_module.py`
2. **Docstring hinzufügen**: Dokumentiere Zweck und Verwendung
3. **Tests schreiben**: `tests/unit/utils/test_new_module.py`
4. **README aktualisieren**: Füge Dokumentation hinzu
5. **Integration testen**: Teste in relevanten Controllern

---

**Version:** 1.0
**Erstellt:** 12.11.2025
**Letzte Aktualisierung:** 12.11.2025
**Erstellt von:** Hans Hahn - Alle Rechte vorbehalten
