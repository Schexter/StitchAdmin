# Swagger UI Setup für StitchAdmin 2.0

## Installation

Die Swagger UI-Integration ist bereits im Code vorbereitet. Um sie zu aktivieren, installieren Sie die benötigte Bibliothek:

```bash
# Installiere flask-swagger-ui
pip install flask-swagger-ui==4.11.1

# Oder installiere alle Requirements
pip install -r requirements.txt
```

## Zugriff auf die Dokumentation

Nach der Installation ist die interaktive API-Dokumentation verfügbar unter:

```
http://localhost:5000/api/docs
```

## Funktionen der Swagger UI

### Interaktive API-Exploration
- **Alle Endpunkte durchsuchen**: Strukturierte Übersicht aller API-Routen
- **Request/Response-Schemas**: Detaillierte Dokumentation aller Datenmodelle
- **Try it out**: API-Calls direkt aus dem Browser testen
- **Beispiele**: Vordefinierte Beispiele für alle Endpunkte

### Navigation
- **Tags**: Endpunkte sind nach Funktionsbereichen gruppiert
  - Authentifizierung
  - Kunden
  - Artikel
  - Aufträge
  - Produktion
  - Kasse
  - Rechnungen
  - etc.

- **Filter**: Suchen Sie nach spezifischen Endpunkten
- **Collapse/Expand**: Klappen Sie Bereiche auf und zu

### API-Tests durchführen

1. **Login erforderlich**: Die meisten Endpunkte erfordern Authentifizierung
   - Melden Sie sich zuerst über `/auth/login` in der Webanwendung an
   - Ihr Browser speichert automatisch den Session-Cookie

2. **Endpunkt auswählen**: Klicken Sie auf einen Endpunkt um Details zu sehen

3. **Try it out**: Klicken Sie auf "Try it out"

4. **Parameter eingeben**: Füllen Sie die benötigten Parameter aus

5. **Execute**: Klicken Sie auf "Execute" um den Request abzusenden

6. **Response prüfen**: Sehen Sie die Antwort inkl. Status-Code und Daten

## OpenAPI-Spezifikation

Die OpenAPI 3.0 Spezifikation ist verfügbar unter:

```
http://localhost:5000/openapi.yaml
```

Diese Datei kann in andere Tools importiert werden:
- Postman
- Insomnia
- curl-Generator
- Code-Generatoren

## Externe Tools

### Postman
1. Öffnen Sie Postman
2. Import → Link → `http://localhost:5000/openapi.yaml`
3. Collection wird automatisch erstellt

### curl-Befehle generieren
Die Swagger UI kann automatisch curl-Befehle für jeden Endpunkt generieren.
Klicken Sie auf "Execute" und kopieren Sie den curl-Befehl aus der Response.

## Troubleshooting

### Swagger UI lädt nicht

**Problem**: `/api/docs` zeigt 404-Fehler

**Lösung**:
```bash
# Überprüfen Sie ob flask-swagger-ui installiert ist
pip show flask-swagger-ui

# Falls nicht installiert
pip install flask-swagger-ui==4.11.1
```

### OpenAPI-Spec nicht gefunden

**Problem**: Swagger UI lädt, aber zeigt Fehler beim Laden der Spec

**Lösung**:
```bash
# Überprüfen Sie ob openapi.yaml existiert
ls -la openapi.yaml

# Route testen
curl http://localhost:5000/openapi.yaml
```

### Authentifizierung funktioniert nicht

**Problem**: API-Calls geben 401 Unauthorized zurück

**Lösung**:
1. Öffnen Sie `http://localhost:5000/auth/login` in einem neuen Tab
2. Melden Sie sich mit Ihren Credentials an
3. Kehren Sie zur Swagger UI zurück
4. Der Session-Cookie sollte jetzt gesetzt sein

## Produktions-Hinweise

### Sicherheit

In der Produktion sollten Sie:

1. **Zugriffsbeschränkung**: Swagger UI nur für authentifizierte Benutzer zugänglich machen
2. **API-Keys**: Erwägen Sie API-Key basierte Authentifizierung für externe Clients
3. **Rate Limiting**: Implementieren Sie Rate Limiting über Nginx
4. **HTTPS**: Nutzen Sie ausschließlich HTTPS in Produktion

### Beispiel: Zugriffsbeschränkung

Bearbeiten Sie `src/controllers/api_controller.py`:

```python
# Swagger UI nur für Admins
from flask_login import login_required, current_user
from functools import wraps

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# Dann in swaggerui_blueprint config:
# Oder erstellen Sie einen Wrapper-Blueprint mit @admin_required
```

## Weitere Ressourcen

- **OpenAPI-Spezifikation**: `/openapi.yaml`
- **API-Dokumentation**: `/API_DOCUMENTATION.md`
- **Deployment-Guide**: `/DEPLOYMENT.md`
- **Swagger UI Dokumentation**: https://swagger.io/tools/swagger-ui/

## Entwickler-Tipps

### API-Spec aktualisieren

Wenn Sie neue Endpunkte hinzufügen:

1. Bearbeiten Sie `openapi.yaml`
2. Fügen Sie den neuen Endpunkt unter `paths:` hinzu
3. Definieren Sie Schemas unter `components/schemas:` falls nötig
4. Swagger UI aktualisiert sich automatisch beim Reload

### Beispiel: Neuen Endpunkt hinzufügen

```yaml
paths:
  /api/mein-endpunkt:
    get:
      tags:
        - Mein Feature
      summary: Beschreibung
      parameters:
        - name: param1
          in: query
          schema:
            type: string
      responses:
        '200':
          description: Erfolg
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    type: array
```

### Schema-Validierung

Sie können die OpenAPI-Spec validieren mit:

```bash
# Installiere validator
npm install -g @apidevtools/swagger-cli

# Validiere Spec
swagger-cli validate openapi.yaml
```

## Support

Bei Fragen oder Problemen:
- Überprüfen Sie die Logs: `logs/app.log`
- Konsultieren Sie die API-Dokumentation: `API_DOCUMENTATION.md`
- Öffnen Sie ein GitHub Issue

---

Erstellt von Hans Hahn - Alle Rechte vorbehalten
StitchAdmin 2.0 - Version 2.0.0
