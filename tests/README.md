# StitchAdmin 2.0 - Testing

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**

## 🧪 Test-Infrastruktur

Dieses Verzeichnis enthält alle automatisierten Tests für StitchAdmin 2.0.

### Verzeichnis-Struktur

```
tests/
├── conftest.py                    # Zentrale Pytest-Fixtures
├── unit/                          # Unit Tests
│   ├── models/                    # Model Tests
│   │   ├── test_customer_model.py  # ✅ 12/12 Tests
│   │   ├── test_user_model.py      # ✅ 8/8 Tests
│   │   ├── test_article_model.py   # ⚠️ 7/11 Tests
│   │   └── test_thread_model.py    # ⚠️ 4/9 Tests
│   └── controllers/               # Controller Tests
│       ├── test_auth_controller.py       # 4 Tests
│       └── test_customer_controller.py   # 4 Tests
└── integration/                   # Integration Tests (TODO)
```

### Tests Ausführen

#### Alle Tests
```bash
pytest
```

#### Nur Model-Tests
```bash
pytest tests/unit/models/
```

#### Mit Coverage-Report
```bash
pytest --cov=src --cov-report=html
# Öffne htmlcov/index.html im Browser
```

#### Einzelne Test-Datei
```bash
pytest tests/unit/models/test_customer_model.py -v
```

## 📊 Test-Status

**Stand:** 12.11.2025
- **Gesamt:** 39 Tests
- **Bestanden:** 28 Tests ✅ (71.8%)
- **Fehlgeschlagen:** 11 Tests ⚠️ (28.2%)
- **Coverage:** ~11% (Target: >60%)

### Model-Tests

| Model | Tests | Status | Notizen |
|-------|-------|--------|---------|
| User | 8/8 | ✅ 100% | Authentifizierung funktioniert |
| Customer | 12/12 | ✅ 100% | Alle Szenarien abgedeckt |
| Article | 7/11 | ⚠️ 64% | Field-Mapping-Probleme |
| Thread | 4/9 | ⚠️ 44% | Field-Mapping-Probleme |

### Controller-Tests

| Controller | Tests | Status | Notizen |
|------------|-------|--------|---------|
| Auth | 4 | ✅ Basis | Login/Logout |
| Customer | 4 | ✅ Basis | CRUD-Routen |

## 🔧 Pytest-Konfiguration

Siehe `pytest.ini` im Projekt-Root für:
- Test-Discovery-Patterns
- Coverage-Einstellungen
- Custom Markers
- Output-Optionen

## 📝 Fixtures

Zentrale Fixtures in `conftest.py`:
- `app` - Flask App mit Test-Konfiguration
- `client` - Test Client für HTTP-Requests
- `db_session` - Datenbank-Session mit Rollback
- `test_user` - Standard-Test-User
- `test_admin` - Admin-User
- `authenticated_client` - Eingeloggter Client
- `test_customer` - Test-Kunde
- `test_article` - Test-Artikel
- `test_thread` - Test-Garn
- `test_machine` - Test-Maschine

## 🎯 Next Steps (Sprint 2)

1. **Verbleibende Tests fixen** (11 Tests)
   - Model-Field-Mapping korrigieren
   - Fixture-Konflikte auflösen

2. **Coverage erhöhen** (>60%)
   - Service-Tests implementieren
   - Integration-Tests für Workflows
   - Controller-Tests erweitern

3. **CI/CD Integration**
   - GitHub Actions für automatische Tests
   - Coverage-Badges

## 📚 Dokumentation

- [Pytest Docs](https://docs.pytest.org/)
- [Flask Testing](https://flask.palletsprojects.com/en/stable/testing/)
- [Coverage.py](https://coverage.readthedocs.io/)

---

**Version:** 1.0
**Letzte Aktualisierung:** 12.11.2025
