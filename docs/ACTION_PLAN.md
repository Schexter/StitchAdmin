# StitchAdmin 2.0 - Action Plan & Nächste Schritte

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Basiert auf:** IST-SOLL-Analyse  
**Start-Datum:** 11. November 2025  
**Ziel-Datum:** 28. Februar 2026 (Beta-Release)

---

## 🎯 Übersicht

Diese Dokument enthält **konkrete, umsetzbare Aufgaben** für die nächsten 13 Wochen, um StitchAdmin 2.0 von 40% auf 100% zu bringen.

---

## 📅 Sprint-Planung (2-Wochen-Sprints)

### Sprint 1: Cleanup & Foundation (11.11 - 24.11.2025)

**Ziel:** Legacy-Code entfernen, Testing aufsetzen  
**Aufwand:** 80 Stunden (10 Tage)  
**Priorität:** 🔴 KRITISCH

#### Woche 1: Code-Cleanup (11.11 - 17.11)

**Tag 1-2 (Mo-Di): Legacy-Controller entfernen** ✅ **ABGESCHLOSSEN (12.11.2025)**

```bash
# ✅ GELÖSCHT (12.11.2025)
# Insgesamt 5.593 Zeilen Code entfernt!
src/controllers/customer_controller.py          ✅ GELÖSCHT
src/controllers/article_controller.py           ✅ GELÖSCHT
src/controllers/order_controller.py             ✅ GELÖSCHT
src/controllers/machine_controller.py           ✅ GELÖSCHT
src/controllers/thread_controller.py            ✅ GELÖSCHT
src/controllers/production_controller.py        ✅ GELÖSCHT
src/controllers/shipping_controller.py          ✅ GELÖSCHT
src/controllers/supplier_controller.py          ✅ GELÖSCHT
src/controllers/settings_controller.py          ✅ GELÖSCHT
src/controllers/settings_controller_db.py       ✅ GELÖSCHT
src/controllers/thread_online_controller.py     ✅ GELÖSCHT
src/controllers/thread_online_controller_db.py  ✅ GELÖSCHT
```

**Aufgaben:**
- [x] Git-Branch erstellen: `claude/review-task-markdown-011CV3Yyuit8KH3NQFb5riuV`
- [x] Legacy-Controller entfernen (12 Dateien)
- [x] Doppelte Controller konsolidieren
- [x] Ungenutzte Imports in 13 Dateien bereinigen
- [x] Dokumentation aktualisiert

**Ergebnis:**
- ✅ 12 Legacy-Dateien gelöscht (5.593 Zeilen Code entfernt)
- ✅ 13 Dateien von ungenutzten Imports bereinigt
- ✅ Alle DB-Controller funktionieren
- ✅ Dokumentation aktualisiert

---

**Tag 3 (Mi): Doppelte Controller konsolidieren** ✅ **ABGESCHLOSSEN (12.11.2025)**

**Problem 1: Thread-Controller** ✅ GELÖST
```python
# ✅ Beide Dateien entfernt (wurden nicht verwendet)
# - thread_online_controller.py     → GELÖSCHT
# - thread_online_controller_db.py  → GELÖSCHT
```

**Problem 2: Settings-Controller** ✅ GELÖST
```python
# Dateien:
# - settings_controller_unified.py  ← BEHALTEN
# - settings_advanced_controller.py

# Aktion: Advanced in Unified integrieren
```

**Problem 3: Webshop-Automation**
```python
# Dateien:
# - webshop_automation_routes.py
# - webshop_automation_routes_complete.py

# Aktion: Complete-Version behalten, andere löschen
```

**Aufgaben:**
- [ ] Thread-Controller mergen
- [ ] Settings-Controller konsolidieren
- [ ] Webshop-Routes aufräumen
- [ ] Tests anpassen
- [ ] Commit: "refactor: consolidate duplicate controllers"

---

**Tag 4 (Do): Code-Review & Refactoring**

**Aufgaben:**
- [ ] Imports bereinigen (ungenutztes entfernen)
- [ ] Docstrings vervollständigen
- [ ] Type Hints hinzufügen wo sinnvoll
- [ ] Code-Duplikation identifizieren
- [ ] TODOs im Code in TODO.md übertragen
- [ ] Commit: "refactor: clean up imports and docstrings"

---

**Tag 5 (Fr): Dokumentation aktualisieren**

**Aufgaben:**
- [ ] README.md aktualisieren (Controller-Liste)
- [ ] VOLLSTAENDIGE_DOKUMENTATION.md aktualisieren
- [ ] KLASSEN_UEBERSICHT.md aktualisieren
- [ ] Git-Tag erstellen: `v2.0.0-cleanup`

---

#### Woche 2: Testing-Setup (18.11 - 24.11)

**Tag 1 (Mo): pytest-Grundlagen**

**Aufgaben:**
- [ ] `pytest` und `pytest-flask` installieren
- [ ] `conftest.py` erstellen
- [ ] Test-Datenbank konfigurieren
- [ ] Erste fixtures definieren:
  - `app` - Test-App
  - `client` - Test-Client
  - `db` - Test-Datenbank
  - `test_user` - Test-User

**Code:**
```python
# tests/conftest.py
import pytest
from src.models.models import db as _db
from app import create_app

@pytest.fixture(scope='session')
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    return app

@pytest.fixture(scope='session')
def db(app):
    with app.app_context():
        _db.create_all()
        yield _db
        _db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def test_user(db):
    from src.models.models import User
    user = User(username='testuser', email='test@test.com', is_admin=True)
    user.set_password('test123')
    db.session.add(user)
    db.session.commit()
    return user
```

---

**Tag 2 (Di): Model-Tests**

**Aufgaben:**
- [ ] `test_customer_model.py` erstellen
- [ ] `test_article_model.py` erstellen
- [ ] `test_order_model.py` erstellen
- [ ] Mindestens 5 Tests pro Model

**Beispiel:**
```python
# tests/test_customer_model.py
def test_create_customer(db):
    from src.models.models import Customer
    
    customer = Customer(
        id='CUST-20251111-0001',
        customer_type='private',
        first_name='Max',
        last_name='Mustermann',
        email='max@test.com'
    )
    db.session.add(customer)
    db.session.commit()
    
    assert customer.display_name == 'Max Mustermann'
    assert customer.id == 'CUST-20251111-0001'
```

---

**Tag 3 (Mi): Controller-Tests**

**Aufgaben:**
- [ ] `test_customer_controller.py` erstellen
- [ ] `test_article_controller.py` erstellen
- [ ] Login-Tests
- [ ] CRUD-Tests

**Beispiel:**
```python
# tests/test_customer_controller.py
def test_customer_index(client, test_user):
    # Login
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'test123'
    })
    
    # Teste Customer-Liste
    response = client.get('/customers/')
    assert response.status_code == 200
    assert b'Kunden' in response.data
```

---

**Tag 4 (Do): Integration-Tests**

**Aufgaben:**
- [ ] End-to-End Test: Kunde anlegen
- [ ] End-to-End Test: Artikel importieren
- [ ] End-to-End Test: Auftrag erstellen
- [ ] Performance-Tests (optional)

---

**Tag 5 (Fr): Coverage & CI**

**Aufgaben:**
- [ ] pytest-cov installieren
- [ ] Coverage-Report generieren: `pytest --cov=src --cov-report=html`
- [ ] Ziel: >20% Coverage erreichen
- [ ] GitHub Actions einrichten (optional)

---

### Sprint 2: Produktionsplanung (25.11 - 08.12.2025)

**Ziel:** Vollständige Produktionsplanung implementieren  
**Aufwand:** 80 Stunden  
**Priorität:** 🔴 HOCH

#### Implementierungs-Schritte

**Woche 1: Backend (25.11 - 01.12)**
- [ ] Tag 1-2: `ThreadUsage` Model + Migration
- [ ] Tag 3: Produktionszeit-Kalkulation
- [ ] Tag 4: Kapazitätsplanung-Algorithmus
- [ ] Tag 5: API-Endpoints

**Woche 2: Frontend (02.12 - 08.12)**
- [ ] Tag 1-2: Produktionskalender-UI
- [ ] Tag 3: Drag & Drop
- [ ] Tag 4-5: Tests & Bugfixes

**Details:** Siehe `docs/workflows/04_production_planning_workflow.md`

---

### Sprint 3: E-Mail-System (09.12 - 22.12.2025)

**Ziel:** Automatische Benachrichtigungen  
**Aufwand:** 80 Stunden  
**Priorität:** 🟡 MITTEL

#### Aufgaben

**Woche 1: Templates & Service (09.12 - 15.12)**
- [ ] E-Mail-Templates erstellen (HTML + Text)
  - Auftragsbestätigung
  - Lieferbenachrichtigung
  - Rechnung
  - Erinnerung
  - Newsletter
- [ ] EmailService erweitern
- [ ] SMTP-Konfiguration
- [ ] Versand-Queue (optional)

**Woche 2: Integration (16.12 - 22.12)**
- [ ] Trigger-Punkte identifizieren
- [ ] Automatische Benachrichtigungen
- [ ] Newsletter-System
- [ ] Tests

---

### Sprint 4: Reporting (07.01 - 19.01.2026)

**Ziel:** Dashboard mit Statistiken  
**Aufwand:** 60 Stunden  
**Priorität:** 🟡 MITTEL

#### Aufgaben
- [ ] Dashboard-Widgets
- [ ] Umsatz-Charts (Chart.js)
- [ ] Kunden-Statistiken
- [ ] Artikel-Statistiken
- [ ] Export-Funktionen (PDF/Excel)

---

### Sprint 5: Garnverwaltung (20.01 - 02.02.2026)

**Ziel:** PDF-Import & Vollständiges Tracking  
**Aufwand:** 80 Stunden  
**Priorität:** 🟡 MITTEL

#### Aufgaben
- [ ] PDF-Import (Garnkarten)
- [ ] Garnsuche nach Farbe
- [ ] Nachbestellvorschläge
- [ ] Lagerplatz-Verwaltung

---

### Sprint 6: Lieferantenverwaltung (03.02 - 16.02.2026)

**Ziel:** Webshop-Integration & Tracking  
**Aufwand:** 80 Stunden  
**Priorität:** 🟢 NIEDRIG

#### Aufgaben
- [ ] Webshop-API-Integration
- [ ] Automatische Bestellungen
- [ ] Lieferstatus-Tracking
- [ ] Retouren-Management

---

### Sprint 7: Testing & Deployment (17.02 - 28.02.2026)

**Ziel:** Beta-Release vorbereiten  
**Aufwand:** 60 Stunden  
**Priorität:** 🔴 HOCH

#### Aufgaben
- [ ] Test-Coverage auf 60% erhöhen
- [ ] End-to-End-Tests
- [ ] Performance-Optimierung
- [ ] Deployment-Setup (Nginx + Gunicorn)
- [ ] Backup-Strategie
- [ ] Monitoring
- [ ] Beta-Release 🎉

---

## 📋 Daily Checklist (Täglich)

### Morgens (30 Min)
- [ ] Git pull (Updates holen)
- [ ] TODO.md lesen (Tages-Aufgaben)
- [ ] error.log prüfen (Fehler vom Vortag)
- [ ] CHANGELOG.md updaten (gestriger Fortschritt)

### Während der Arbeit
- [ ] Commits nach jeder logischen Änderung
- [ ] Tests nach jeder Feature-Implementation
- [ ] Docstrings für neue Funktionen
- [ ] TODOs im Code vermeiden (in TODO.md schreiben)

### Abends (15 Min)
- [ ] Git push (Änderungen sichern)
- [ ] CHANGELOG.md aktualisieren (was heute gemacht wurde)
- [ ] TODO.md updaten (erledigte Tasks abhaken)
- [ ] Morgen-Plan erstellen (3-5 Aufgaben für nächsten Tag)

---

## 🎯 Kritische Erfolgsfaktoren

### 1. Fokus bewahren
- ✅ **Ein Modul nach dem anderen** abschließen
- ❌ **NICHT** zwischen Modulen springen
- ❌ **KEINE** neuen Features während Cleanup

### 2. Testing-Disziplin
- ✅ **Jeden Tag Tests schreiben**
- ✅ **Tests vor Commit laufen lassen**
- ✅ **Coverage-Report wöchentlich prüfen**

### 3. Dokumentation laufend
- ✅ **CHANGELOG.md täglich** aktualisieren
- ✅ **Docstrings sofort** schreiben
- ✅ **Workflows dokumentieren** während Implementierung

### 4. Code-Qualität
- ✅ **Code-Reviews** (selbst nach 2 Tagen nochmal anschauen)
- ✅ **PEP 8** einhalten
- ✅ **Refactoring** nicht auf später verschieben

---

## 📈 Fortschritts-Tracking

### Wöchentliches Review (Jeden Freitag)

**Fragen:**
1. Was wurde diese Woche erreicht?
2. Was hat nicht funktioniert?
3. Welche Blocker gab es?
4. Was ist der Plan für nächste Woche?

**Metriken:**
- Sprint-Fortschritt (%)
- Test-Coverage (%)
- Gelöste Issues
- Neue Issues

### Update TODO.md
```markdown
## Sprint-Review: KW XX

### Erreicht:
- [ ] Aufgabe 1
- [ ] Aufgabe 2

### Probleme:
- Problem X

### Nächste Woche:
- Aufgabe A
- Aufgabe B
```

---

## 🚨 Notfall-Plan

### Wenn der Zeitplan nicht eingehalten wird

**Plan B: Minimale Beta-Version**

Fokus nur auf:
1. ✅ Cleanup (Sprint 1) - **PFLICHT**
2. ✅ Testing Basics (Sprint 1) - **PFLICHT**
3. ✅ Produktionsplanung (Sprint 2) - **PFLICHT**
4. ⚠️ E-Mail-System (Sprint 3) - **Optional → v2.1**
5. ⚠️ Reporting (Sprint 4) - **Minimal → v2.1**
6. ❌ Garnverwaltung (Sprint 5) - **→ v2.2**
7. ❌ Lieferanten (Sprint 6) - **→ v2.2**

**Neue Timeline:**
- Beta-Release: Ende Januar 2026 (statt Februar)
- v2.1 (Full): Ende März 2026
- v2.2 (Complete): Ende Mai 2026

---

## 📞 Support & Ressourcen

### Bei technischen Problemen

1. **error.log prüfen**
2. **Google/StackOverflow**
3. **SQLAlchemy Docs:** https://docs.sqlalchemy.org
4. **Flask Docs:** https://flask.palletsprojects.com
5. **pytest Docs:** https://docs.pytest.org

### Code-Vorlagen

**Verzeichnis:** `docs/code_templates/`
- Controller-Template
- Model-Template
- Test-Template
- Service-Template

---

## ✅ Start-Checklist (Montag, 11.11.2025)

Bevor du beginnst:

- [ ] Dieses Dokument komplett gelesen
- [ ] IST_SOLL_ANALYSE.md gelesen
- [ ] Git-Branch erstellt: `sprint-1/cleanup`
- [ ] Backup-Ordner erstellt: `backups/pre_cleanup/`
- [ ] Virtual Environment aktiviert
- [ ] Kaffee ☕ geholt
- [ ] **LOS GEHT'S!** 🚀

---

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Letzte Aktualisierung:** 10. November 2025  
**Nächstes Review:** 15. November 2025

---

## 🎉 Motivations-Tracker

```
┌─────────────────────────────────────────┐
│  "The journey of a thousand miles       │
│   begins with a single step."           │
│                        - Lao Tzu        │
└─────────────────────────────────────────┘

Fortschritt bis Beta-Release:
[████░░░░░░░░░░░░░░░░] 40%

Noch 60% zu gehen!
Du schaffst das! 💪
```
