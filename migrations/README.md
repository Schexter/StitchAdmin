# Datenbank-Migrationen

**Flask-Migrate** - Alembic-basierte Datenbank-Migrationen für StitchAdmin 2.0

## 📋 Übersicht

Dieses Verzeichnis enthält alle Datenbank-Migrationen für StitchAdmin. Migrationen ermöglichen es, Änderungen am Datenbankschema versioniert und nachvollziehbar durchzuführen.

## 🚀 Befehle

### Migration erstellen
```bash
flask --app app:create_app db migrate -m "Beschreibung der Änderung"
```

### Migration anwenden
```bash
flask --app app:create_app db upgrade
```

### Migration rückgängig machen
```bash
flask --app app:create_app db downgrade
```

### Aktuellen Status anzeigen
```bash
flask --app app:create_app db current
```

### Migrations-Historie anzeigen
```bash
flask --app app:create_app db history
```

## 📁 Struktur

```
migrations/
├── alembic.ini          # Alembic-Konfiguration
├── env.py               # Migration-Environment-Setup
├── script.py.mako       # Template für neue Migrations
└── versions/            # Migrations-Dateien
    └── xxx_description.py
```

## ⚠️ Wichtige Hinweise

1. **Vor Produktions-Deployment:** Immer Backup der Datenbank erstellen!
2. **Testing:** Migrations erst in Entwicklung/Test-Umgebung testen
3. **Versionskontrolle:** Alle Migration-Files in Git committen
4. **Reihenfolge:** Migrations werden in chronologischer Reihenfolge angewendet

## 📝 Workflow

1. Models in `src/models/` ändern
2. Migration erstellen: `flask db migrate -m "Add new field"`
3. Migration überprüfen in `migrations/versions/`
4. Migration anwenden: `flask db upgrade`
5. Migration testen
6. Migration committen

## 🔄 Bestehende Datenbank

Falls bereits eine Datenbank existiert:
```bash
flask --app app:create_app db stamp head
```

Dies markiert die aktuelle Datenbank als "up-to-date" mit den Migrationen.

---

**Version:** 1.0
**Erstellt:** 12.11.2025
**Erstellt von:** Hans Hahn - Alle Rechte vorbehalten
