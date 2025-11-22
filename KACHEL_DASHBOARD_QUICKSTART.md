# 🚀 StitchAdmin 2.0 - Kachel-Dashboard Aktivierung

## Schnellstart-Anleitung

### ✅ Was bereits erledigt ist:

1. ✅ Datenbank-Modelle erstellt (`src/models/document.py`)
2. ✅ Verschlüsselung implementiert (`src/utils/encryption.py`)
3. ✅ Controller erstellt (`src/controllers/documents/documents_controller.py`)
4. ✅ Neues Dashboard-Design (`src/templates/dashboard.html`)
5. ✅ Dokumente-Dashboard (`src/templates/documents/dashboard.html`)

---

## 🔧 Schritt-für-Schritt Aktivierung:

### Schritt 1: Dependencies installieren

```bash
cd C:\SoftwareEntwicklung\StitchAdmin2.0
.venv\Scripts\activate
pip install cryptography
```

### Schritt 2: Blueprint in app.py registrieren

Öffne `app.py` und füge nach der Zeile mit `auth_controller` folgendes hinzu:

```python
# Auth und Dashboard
register_blueprint_safe('src.controllers.auth_controller', 'auth_bp', 'Authentifizierung')

# Dokumente & Post  <-- NEU HINZUFÜGEN
register_blueprint_safe('src.controllers.documents.documents_controller', 'documents_bp', 'Dokumente & Post')
```

**Oder verwende dieses PowerShell-Script:**

```powershell
cd C:\SoftwareEntwicklung\StitchAdmin2.0

# Backup erstellen
Copy-Item app.py app.py.backup

# Blueprint hinzufügen
$content = Get-Content app.py -Raw
$search = "    register_blueprint_safe('src.controllers.auth_controller', 'auth_bp', 'Authentifizierung')"
$replace = @"
    register_blueprint_safe('src.controllers.auth_controller', 'auth_bp', 'Authentifizierung')
    
    # Dokumente & Post
    register_blueprint_safe('src.controllers.documents.documents_controller', 'documents_bp', 'Dokumente & Post')
"@

$content = $content -replace [regex]::Escape($search), $replace
$content | Set-Content app.py -Encoding UTF8

Write-Host "[OK] Blueprint hinzugefügt!" -ForegroundColor Green
```

### Schritt 3: Dashboard-Statistiken erweitern

In `app.py` bei der `@app.route('/dashboard')` Funktion ergänzen:

**VORHER:**
```python
@app.route('/dashboard')
@login_required
def dashboard():
    from src.models.models import Order, db
    from datetime import datetime, date
    from sqlalchemy import func

    stats = {
        'open_orders': Order.query.filter(...).count(),
        'in_production': Order.query.filter_by(status='in_progress').count(),
        'ready_pickup': Order.query.filter_by(status='ready_for_pickup').count(),
        'today_revenue': 0
    }
    
    # ... Tagesumsatz Berechnung ...
    
    return render_template('dashboard.html', stats=stats)
```

**NACHHER:**
```python
@app.route('/dashboard')
@login_required
def dashboard():
    from src.models.models import Order, Customer, Article, Thread, db
    from src.models.document import Document, PostEntry, ArchivedEmail
    from datetime import datetime, date
    from sqlalchemy import func

    stats = {
        # Produktion (bestehend)
        'open_orders': Order.query.filter(
            Order.status.in_(['pending', 'approved', 'in_progress'])
        ).count(),
        'in_production': Order.query.filter_by(status='in_progress').count(),
        'ready_pickup': Order.query.filter_by(status='ready_for_pickup').count(),
        'today_revenue': 0,
        
        # CRM
        'total_customers': Customer.query.count(),
        'open_leads': 0,  # Später mit Lead-System
        
        # Dokumente & Post
        'document_count': Document.query.filter_by(is_latest_version=True).count(),
        'open_post': PostEntry.query.filter_by(status='open').count(),
        'unread_emails': ArchivedEmail.query.filter_by(is_read=False).count(),
        
        # Buchhaltung
        'open_invoices': 0,  # Aus Rechnungsmodul
        'overdue_payments': 0,
        'today_transactions': 0,
        
        # Verwaltung
        'user_count': 0,  # User.query.count()
        'article_count': Article.query.count(),
        
        # Lager
        'thread_count': Thread.query.count(),
        'low_stock': 0,
        
        # Design
        'design_count': 0,
        'dst_count': 0
    }
    
    # Tagesumsatz berechnen (bestehend)
    try:
        from src.controllers.rechnungsmodul.models import KassenBeleg
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        today_sum = db.session.query(func.sum(KassenBeleg.summe_brutto)).filter(
            KassenBeleg.datum >= today_start,
            KassenBeleg.datum <= today_end
        ).scalar()

        stats['today_revenue'] = round(today_sum or 0, 2)
        stats['today_transactions'] = KassenBeleg.query.filter(
            KassenBeleg.datum >= today_start,
            KassenBeleg.datum <= today_end
        ).count()
    except (ImportError, Exception):
        pass
    
    return render_template('dashboard.html', stats=stats)
```

### Schritt 4: Datenbank-Tabellen anlegen

```bash
cd C:\SoftwareEntwicklung\StitchAdmin2.0
.venv\Scripts\activate
python
```

```python
from app import create_app
app = create_app()

with app.app_context():
    from src.models.models import db
    from src.models.document import Document, DocumentAccessLog, PostEntry, EmailAccount, ArchivedEmail, EmailAttachment
    
    # Tabellen anlegen
    db.create_all()
    print("[OK] Alle Tabellen wurden erstellt!")
    
    # Prüfen
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"[OK] {len(tables)} Tabellen in Datenbank:")
    for table in tables:
        print(f"  - {table}")
```

### Schritt 5: Starten und Testen

```bash
cd C:\SoftwareEntwicklung\StitchAdmin2.0
start.bat
```

**Browser öffnen:**
```
http://localhost:5000
```

**Login:**
```
Username: admin
Password: admin
```

---

## 📋 Checkliste

- [ ] Dependencies installiert (`cryptography`)
- [ ] Blueprint in app.py registriert
- [ ] Dashboard-Statistiken erweitert
- [ ] Datenbank-Tabellen angelegt
- [ ] Server gestartet
- [ ] Neues Dashboard sichtbar mit 8 Kacheln
- [ ] "Dokumente & Post" Kachel funktioniert
- [ ] Upload-Funktion getestet
- [ ] Postbuch getestet

---

## 🎯 Was die Kacheln machen:

### 1. CRM 👥
- Kunden verwalten
- Kontakthistorie
- Ansprechpartner
- *(Später: Leads, Sales Pipeline)*

### 2. Produktion 🏭
- Aufträge verwalten
- Produktionsplanung
- Maschinensteuerung
- Design-Workflow

### 3. Kasse 💰
- Barverkauf (POS)
- TSE-Integration
- Tagesabschluss
- Kassenbuch

### 4. Buchhaltung 📈
- Rechnungen
- Mahnwesen
- Finanzen
- DATEV-Export

### 5. **Dokumente & Post 📁** ✨ NEU
- Dokumentenmanagement (DMS)
- Postbuch (Ein-/Ausgang)
- E-Mail-Archivierung
- OCR & Volltextsuche

### 6. Verwaltung ⚙️
- Einstellungen
- Benutzer & Rechte
- Artikel & Preise
- Lieferanten

### 7. Lager 📦
- Garnverwaltung
- Artikelbestand
- Thread-Matching
- Inventur

### 8. Design-Archiv 🎨
- DST-Dateien
- Motive-Bibliothek
- Automatische Analyse
- Kategorisierung

---

## 🐛 Troubleshooting

### Problem: "ModuleNotFoundError: No module named 'cryptography'"
**Lösung:**
```bash
pip install cryptography
```

### Problem: "Blueprint 'documents' not found"
**Lösung:**
- Prüfe ob Blueprint in app.py registriert ist
- Stelle sicher dass `__init__.py` im documents-Ordner existiert

### Problem: "Table 'documents' doesn't exist"
**Lösung:**
```python
from app import create_app
app = create_app()
with app.app_context():
    from src.models.models import db
    db.create_all()
```

### Problem: Dashboard zeigt alte Version
**Lösung:**
- Browser-Cache leeren (Strg + Shift + R)
- Prüfe ob `dashboard.html` im templates-Ordner überschrieben wurde

---

## 📁 Datei-Struktur nach Umbau:

```
StitchAdmin2.0/
├── app.py (✏️ GEÄNDERT - Blueprint hinzugefügt)
├── src/
│   ├── models/
│   │   ├── document.py (✨ NEU)
│   │   └── ...
│   ├── controllers/
│   │   ├── documents/ (✨ NEU)
│   │   │   ├── __init__.py
│   │   │   └── documents_controller.py
│   │   └── ...
│   ├── templates/
│   │   ├── dashboard.html (✏️ KOMPLETT NEU - Kachel-Design)
│   │   ├── documents/ (✨ NEU)
│   │   │   ├── dashboard.html
│   │   │   ├── list.html (TODO)
│   │   │   ├── upload.html (TODO)
│   │   │   └── ...
│   │   └── ...
│   └── utils/
│       ├── encryption.py (✨ NEU)
│       └── ...
└── instance/
    ├── stitchadmin.db
    └── encryption.key (✨ AUTO-GENERIERT)
```

---

## 🎉 Erfolg!

Wenn alles funktioniert, siehst du:

1. **Neues Dashboard** mit 8 bunten Kacheln
2. **Dokumente & Post Kachel** mit Statistiken
3. **Smooth Hover-Effekte** bei Kacheln
4. **Responsive Design** (funktioniert auch auf Tablet)
5. **Quick-Actions** auf Dokumente-Kachel

---

## 📞 Support

Bei Problemen:
1. Prüfe Logs in `error.log`
2. Prüfe Terminal-Output
3. Checke Browser-Konsole (F12)

---

**Erstellt:** 22.11.2025  
**Version:** 2.0.1  
**Autor:** Hans Hahn - Alle Rechte vorbehalten
