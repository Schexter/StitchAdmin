# 🔐 Permission-System & Personalisierbares Dashboard

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Version:** 2.0.2  
**Datum:** 23.11.2025

---

## 📋 Übersicht

Das neue Permission-System ermöglicht:

### ✨ Features

1. **Modul-basierte Berechtigungen**
   - Admin legt fest: Wer hat Zugriff auf welches Modul
   - Feingranulare CRUD-Rechte (View, Create, Edit, Delete)
   - Admin-Only Module

2. **Personalisierbares Dashboard**
   - **Drag & Drop:** Reihenfolge der Module ändern
   - **Ein-/Ausblenden:** Module individuell sichtbar machen
   - **Auto-Save:** Änderungen werden automatisch gespeichert
   - **Pro User:** Jeder User hat sein eigenes Layout

3. **Sichtbarkeit in Navigation**
   - Module ohne Berechtigung werden ausgeblendet
   - Sowohl im Dashboard als auch in der Navbar

---

## 🚀 Installation & Setup

### Schritt 1: Datenbank-Tabellen erstellen

```bash
cd C:\SoftwareEntwicklung\StitchAdmin2.0
.venv\Scripts\activate
python scripts/setup_permissions.py
```

**Ausgabe:**
```
Permission-System Setup
========================================
[INFO] Erstelle Tabellen...
✅ Tabellen erfolgreich erstellt!

[OK] 3/3 Permission-Tabellen vorhanden:
  ✓ modules
  ✓ module_permissions
  ✓ dashboard_layouts
```

### Schritt 2: Basis-Module initialisieren

```bash
python scripts/init_modules.py
```

**Ausgabe:**
```
Modul-Initialisierung
========================================
[NEU]    CRM
[NEU]    Produktion
[NEU]    Kasse / POS
[NEU]    Buchhaltung
[NEU]    Dokumente & Post
[NEU]    Verwaltung
[NEU]    Lager & Artikel
[NEU]    Design-Archiv

✅ Erfolgreich: 8 erstellt, 0 aktualisiert
```

### Schritt 3: app.py aktualisieren

```bash
python scripts/update_app_for_permissions.py
```

**Was wird geändert:**
- ✅ Permission-Blueprints werden registriert
- ✅ Dashboard-Route wird aktualisiert
- ✅ Permission-Helper werden zum Context Processor hinzugefügt
- ✅ Backup wird automatisch erstellt

### Schritt 4: Server neu starten

```bash
start.bat
```

---

## 📁 Neue Dateien & Struktur

```
StitchAdmin2.0/
├── src/
│   ├── models/
│   │   └── user_permissions.py        # Neue Datenmodelle
│   ├── utils/
│   │   └── permissions.py             # Helper-Funktionen & Decorators
│   ├── controllers/
│   │   ├── permissions_controller.py  # Admin-Interface
│   │   └── dashboard_api_controller.py # Dashboard-API
│   └── templates/
│       ├── dashboard_personalized.html # Neues Dashboard mit Drag & Drop
│       └── permissions/
│           ├── index.html             # Berechtigungsverwaltung
│           └── user_permissions.html  # User-Berechtigungen bearbeiten
└── scripts/
    ├── setup_permissions.py           # Setup-Script
    ├── init_modules.py                # Module initialisieren
    └── update_app_for_permissions.py  # app.py auto-update
```

---

## 🎯 Verwendung

### Als Administrator

#### 1. Berechtigungsverwaltung öffnen

```
Dashboard → Einstellungen → Berechtigungsverwaltung
```

**Oder direkt:**
```
http://localhost:5000/admin/permissions
```

#### 2. Benutzer-Berechtigungen festlegen

1. **Tab "Benutzer-Berechtigungen"** öffnen
2. Bei gewünschtem User auf **"Berechtigungen"** klicken
3. Checkboxen für gewünschte Rechte setzen:
   - 👁️ **Ansehen:** Modul sehen und Daten anzeigen
   - ➕ **Erstellen:** Neue Einträge erstellen
   - ✏️ **Bearbeiten:** Bestehende Einträge ändern
   - 🗑️ **Löschen:** Einträge löschen

4. **"Berechtigungen speichern"** klicken

#### 3. Schnell-Zuweisung nutzen

Für schnelle Konfiguration:

- **"Alle: Nur Ansehen"** → User kann alle Module sehen
- **"Alle: Ansehen + Bearbeiten"** → User kann ansehen, erstellen und bearbeiten
- **"Alle: Voller Zugriff"** → User hat alle Rechte (inkl. Löschen)

#### 4. Module verwalten

Im Tab **"Module verwalten"**:
- Module **aktivieren/deaktivieren**
- **Nur-Admin** Markierung setzen
- **Standard aktiv** für neue User festlegen
- **Reihenfolge** anpassen

### Als normaler User

#### Dashboard personalisieren

1. **"Dashboard anpassen"** klicken
2. **Drag & Drop:** Kacheln ziehen und neu anordnen
3. **Ein-/Ausblenden:** Auf Augen-Symbol klicken
4. **"Fertig"** klicken → Änderungen werden gespeichert

#### Funktionen im Edit-Mode:

- **Ziehen:** Kachel anfassen und verschieben
- **Ausblenden:** 👁️ Symbol → wird zu 👁️‍🗨️
- **Zurücksetzen:** "Zurücksetzen" Button → Standard-Layout

---

## 🔧 API-Endpunkte

### Dashboard-Layout API

#### Layout laden
```
GET /api/dashboard/layout
```

**Response:**
```json
{
  "success": true,
  "layout": {
    "id": 1,
    "user_id": 1,
    "layout_config": {
      "modules": [
        {"module_id": 1, "order": 1, "visible": true, "size": "normal"},
        {"module_id": 2, "order": 2, "visible": false, "size": "normal"}
      ],
      "theme": "light",
      "compact_mode": false
    }
  }
}
```

#### Layout speichern
```
POST /api/dashboard/layout
Content-Type: application/json

{
  "modules": [
    {"module_id": 1, "order": 1, "visible": true, "size": "normal"}
  ],
  "theme": "light"
}
```

#### Modul-Sichtbarkeit umschalten
```
POST /api/dashboard/module/<module_id>/toggle
```

#### Dashboard zurücksetzen
```
POST /api/dashboard/reset
```

### Permissions API

#### Modul aktivieren/deaktivieren
```
POST /admin/permissions/module/<module_id>/toggle
```

#### Schnell-Zuweisung
```
POST /admin/permissions/quick-assign
Content-Type: application/json

{
  "user_id": 2,
  "level": "view"  # view, edit, full
}
```

---

## 💻 Entwickler: Permission-System nutzen

### In Python-Code

#### Decorator für Routen

```python
from src.utils.permissions import module_required

@app.route('/customers')
@login_required
@module_required('crm', 'view')  # Berechtigung prüfen
def customer_index():
    return render_template('customers/index.html')
```

#### Programmatisch prüfen

```python
from src.utils.permissions import has_module_permission

if has_module_permission(current_user, 'crm', 'edit'):
    # User darf Kunden bearbeiten
    pass
```

#### Module eines Users abrufen

```python
from src.utils.permissions import get_user_modules

modules = get_user_modules(current_user)
for module in modules:
    print(f"User kann {module.display_name} nutzen")
```

### In Templates

#### Berechtigung prüfen

```jinja2
{% if has_permission('crm', 'edit') %}
    <button>Bearbeiten</button>
{% endif %}
```

#### User-Module auflisten

```jinja2
{% for module in get_user_modules() %}
    <a href="{{ url_for(module.route) }}">
        {{ module.icon }} {{ module.display_name }}
    </a>
{% endfor %}
```

---

## 🗄️ Datenbank-Schema

### Tabelle: `modules`

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | Integer | Primary Key |
| name | String(100) | Eindeutiger Name (z.B. "crm") |
| display_name | String(100) | Anzeigename |
| description | String(255) | Beschreibung |
| icon | String(50) | Emoji oder Icon-Klasse |
| color | String(50) | Bootstrap-Farbe |
| route | String(200) | Flask-Route |
| category | String(50) | Kategorie (core, finance, admin) |
| is_active | Boolean | Modul aktiv? |
| requires_admin | Boolean | Nur für Admins? |
| default_enabled | Boolean | Standard für neue User? |
| sort_order | Integer | Sortierung |

### Tabelle: `module_permissions`

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | Integer | Primary Key |
| user_id | Integer | Foreign Key → users.id |
| module_id | Integer | Foreign Key → modules.id |
| can_view | Boolean | Ansehen erlaubt |
| can_create | Boolean | Erstellen erlaubt |
| can_edit | Boolean | Bearbeiten erlaubt |
| can_delete | Boolean | Löschen erlaubt |
| granted_by | Integer | Welcher Admin hat Recht vergeben |
| granted_at | DateTime | Zeitpunkt der Vergabe |

### Tabelle: `dashboard_layouts`

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | Integer | Primary Key |
| user_id | Integer | Foreign Key → users.id (unique) |
| layout_config | JSON | Dashboard-Konfiguration |
| created_at | DateTime | Erstellt am |
| updated_at | DateTime | Aktualisiert am |

---

## 🐛 Troubleshooting

### Problem: "Table 'modules' doesn't exist"

**Lösung:**
```bash
python scripts/setup_permissions.py
```

### Problem: "ModuleNotFoundError: No module named 'src.models.user_permissions'"

**Lösung:**
Stelle sicher, dass die Datei existiert:
```
C:\SoftwareEntwicklung\StitchAdmin2.0\src\models\user_permissions.py
```

### Problem: Dashboard zeigt alte Version ohne Drag & Drop

**Lösung:**
1. Browser-Cache leeren (Strg + Shift + R)
2. Prüfe ob Template korrekt ist:
```bash
dir C:\SoftwareEntwicklung\StitchAdmin2.0\src\templates\dashboard_personalized.html
```

### Problem: Permission-Blueprint nicht registriert

**Lösung:**
```bash
python scripts/update_app_for_permissions.py
```

Dann Server neu starten.

### Problem: Module werden nicht angezeigt

**Lösung:**
1. Module initialisieren:
```bash
python scripts/init_modules.py
```

2. Berechtigungen prüfen:
```
http://localhost:5000/admin/permissions
```

---

## 📊 Beispiel-Workflows

### Workflow 1: Neuer Mitarbeiter (Sticker)

1. **Admin:** Neuen User anlegen
2. **Admin:** Berechtigungen → User auswählen
3. **Admin:** Schnell-Zuweisung: "Alle: Ansehen + Bearbeiten"
4. **Admin:** Module deaktivieren:
   - ❌ Buchhaltung
   - ❌ Verwaltung
   - ❌ Dokumente & Post
5. **User:** Beim Login: Sieht nur relevante Module
6. **User:** Dashboard anpassen: Reihenfolge ändern

### Workflow 2: Verwaltungs-Mitarbeiter

1. **Admin:** Berechtigungen → User auswählen
2. **Admin:** Aktiviere:
   - ✅ CRM (Voll)
   - ✅ Kasse (Voll)
   - ✅ Buchhaltung (Voll)
   - ✅ Dokumente & Post (Voll)
   - ❌ Produktion (nur ansehen)
3. **User:** Dashboard personalisieren

---

## 🔄 Migration von bestehenden Usern

Bei bestehenden Installationen:

1. **Tabellen erstellen:**
```bash
python scripts/setup_permissions.py
```

2. **Module initialisieren:**
```bash
python scripts/init_modules.py
```

3. **Alle User bekommen Standard-Zugriff:**
   - Neue User: Alle Module mit `default_enabled=True`
   - Admin: Automatisch alle Module
   - Normale User: Müssen von Admin konfiguriert werden

4. **Optional: Massen-Zuweisung**

Python-Script in Flask-Shell:
```python
from app import create_app
app = create_app()

with app.app_context():
    from src.models.models import User, db
    from src.models.user_permissions import Module, ModulePermission
    
    # Alle normalen User
    users = User.query.filter_by(is_admin=False).all()
    modules = Module.query.all()
    
    for user in users:
        for module in modules:
            if not module.requires_admin:
                perm = ModulePermission(
                    user_id=user.id,
                    module_id=module.id,
                    can_view=True,
                    can_create=True,
                    can_edit=True,
                    can_delete=False
                )
                db.session.add(perm)
    
    db.session.commit()
    print(f"[OK] {len(users)} User konfiguriert")
```

---

## 📈 Zukünftige Erweiterungen

Geplante Features:

1. **Rollen-System**
   - Vordefinierte Rollen (z.B. "Sticker", "Verwaltung")
   - User zu Rollen zuweisen statt einzelne Berechtigungen

2. **Kachelgrößen**
   - Klein (1x1), Mittel (2x1), Groß (2x2)
   - Anpassbar per Drag & Drop

3. **Dashboard-Vorlagen**
   - Admin erstellt Vorlagen
   - User können Vorlage wählen

4. **Zeitlich begrenzte Berechtigungen**
   - Temporärer Zugriff
   - Automatisches Ablaufen

5. **Audit-Log**
   - Wer hat wann welche Berechtigung geändert
   - Nachvollziehbarkeit

---

## 📞 Support

Bei Problemen:

1. **Logs prüfen:** `error.log`
2. **Terminal-Output:** Beim Server-Start
3. **Browser-Konsole:** F12 → Console

---

**Version:** 2.0.2  
**Letztes Update:** 23.11.2025  
**Autor:** Hans Hahn - Alle Rechte vorbehalten
