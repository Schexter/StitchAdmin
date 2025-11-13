# StitchAdmin 2.0 API-Dokumentation

## Übersicht

Diese Dokumentation beschreibt die REST-API von StitchAdmin 2.0, einer modernen ERP-Lösung für Stickerei-Betriebe.

## OpenAPI-Spezifikation

Die vollständige API-Dokumentation ist in der Datei `openapi.yaml` im OpenAPI 3.0 Format verfügbar.

## Swagger UI

Die interaktive API-Dokumentation ist über Swagger UI erreichbar:

```
http://localhost:5000/api/docs
```

Dort können Sie:
- Alle verfügbaren Endpunkte durchsuchen
- Request/Response-Schemas einsehen
- API-Calls direkt aus dem Browser testen
- Beispiele für alle Endpunkte sehen

## Authentifizierung

StitchAdmin 2.0 verwendet Session-basierte Authentifizierung über Flask-Login.

### Login-Flow

1. **Login**: POST an `/auth/login` mit Username und Passwort
2. **Session-Cookie**: Bei erfolgreicher Anmeldung erhalten Sie einen Session-Cookie
3. **API-Calls**: Verwenden Sie den Cookie für alle weiteren API-Anfragen
4. **Logout**: GET an `/auth/logout` um die Session zu beenden

### Beispiel mit cURL

```bash
# Login
curl -X POST http://localhost:5000/auth/login \
  -d "username=admin&password=admin" \
  -c cookies.txt

# API-Call mit Session
curl http://localhost:5000/api/articles \
  -b cookies.txt

# Logout
curl http://localhost:5000/auth/logout \
  -b cookies.txt
```

### Beispiel mit Python

```python
import requests

# Session erstellen
session = requests.Session()

# Login
login_data = {
    'username': 'admin',
    'password': 'admin'
}
session.post('http://localhost:5000/auth/login', data=login_data)

# API-Call
response = session.get('http://localhost:5000/api/articles')
articles = response.json()

print(f"Gefundene Artikel: {articles['count']}")
```

## Haupt-Endpunkte

### Artikel-API

#### Alle Artikel abrufen
```http
GET /api/articles?supplier_id=SUP001&search=shirt
```

**Response:**
```json
{
  "success": true,
  "articles": [
    {
      "id": "ART001",
      "article_number": "A-2025-001",
      "name": "T-Shirt Basic Weiß",
      "price": 15.99,
      "stock": 50
    }
  ],
  "count": 1,
  "source": "database"
}
```

#### Artikel-Details
```http
GET /api/articles/ART001
```

**Response:**
```json
{
  "success": true,
  "article": {
    "id": "ART001",
    "article_number": "A-2025-001",
    "name": "T-Shirt Basic Weiß",
    "description": "Hochwertiges Baumwoll-T-Shirt",
    "price": 15.99,
    "purchase_price": 8.50,
    "stock": 50,
    "category": "Textilien"
  }
}
```

#### Artikel-Suche für Kasse
```http
GET /api/articles/search?q=shirt
```

**Response:**
```json
[
  {
    "id": "ART001",
    "article_number": "A-2025-001",
    "name": "T-Shirt Basic Weiß",
    "price": 15.99,
    "stock_quantity": 50,
    "barcode": "4260123456789",
    "category": "Textilien"
  }
]
```

### Debug-Endpunkte

Für Entwicklung und Debugging stehen zusätzliche Endpunkte zur Verfügung:

#### Alle Lieferanten
```http
GET /api/debug/suppliers
```

#### Artikel-Lieferanten-Mapping
```http
GET /api/debug/articles-suppliers
```

## Web-API-Endpunkte (HTML)

Zusätzlich zu den JSON-API-Endpunkten unter `/api` gibt es zahlreiche Web-Endpunkte, die HTML zurückgeben:

### Kunden
- `GET /customers` - Kunden-Übersicht
- `GET /customers/new` - Neuer Kunde (Formular)
- `POST /customers/new` - Neuen Kunden erstellen
- `GET /customers/{id}` - Kunden-Details
- `POST /customers/{id}/edit` - Kunde bearbeiten
- `POST /customers/{id}/delete` - Kunde löschen

### Artikel
- `GET /articles` - Artikel-Übersicht
- `GET /articles/new` - Neuer Artikel (Formular)
- `POST /articles/new` - Neuen Artikel erstellen
- `GET /articles/{id}` - Artikel-Details
- `POST /articles/{id}/edit` - Artikel bearbeiten
- `POST /articles/{id}/stock` - Lagerbestand aktualisieren
- `POST /articles/import/lshop` - L-Shop Excel-Import

### Aufträge
- `GET /orders` - Auftrags-Übersicht
- `POST /orders/new` - Neuen Auftrag erstellen
- `GET /orders/{id}` - Auftrags-Details
- `POST /orders/{id}/status` - Status aktualisieren
- `POST /orders/{id}/add-item` - Artikel hinzufügen

### Produktion
- `GET /production` - Produktions-Übersicht
- `GET /production/planning` - Produktionsplanung
- `POST /production/order/{id}/start` - Produktion starten
- `POST /production/api/order/schedule` - Auftrag einplanen

### Kasse (TSE-Integration)
- `GET /kasse` - Kassensystem
- `GET /kasse/verkauf` - Verkaufs-Interface
- `POST /kasse/verkauf/abschliessen` - Verkauf abschließen
- `GET /kasse/tagesabschluss` - Tagesabschluss

### Rechnungen (ZUGFeRD)
- `GET /rechnung` - Rechnungs-Übersicht
- `POST /rechnung/neu` - Neue Rechnung
- `GET /rechnung/{id}/pdf` - Rechnung als PDF
- `GET /rechnung/{id}/download` - ZUGFeRD-PDF herunterladen

## Datenmodelle

### Customer (Kunde)
```json
{
  "id": "CUST001",
  "customer_number": "K-2025-001",
  "company_name": "Musterfirma GmbH",
  "first_name": "Max",
  "last_name": "Mustermann",
  "email": "max@example.com",
  "phone": "+49 123 456789",
  "street": "Musterstraße 1",
  "postal_code": "12345",
  "city": "Musterstadt",
  "country": "Deutschland",
  "customer_type": "business",
  "tax_id": "DE123456789",
  "payment_terms": 14,
  "discount": 5.0,
  "active": true
}
```

### Article (Artikel)
```json
{
  "id": "ART001",
  "article_number": "A-2025-001",
  "name": "T-Shirt Basic Weiß",
  "description": "Hochwertiges Baumwoll-T-Shirt",
  "supplier": "L-Shop",
  "supplier_article_number": "TS-001-W",
  "category": "Textilien",
  "brand": "Fruit of the Loom",
  "price": 15.99,
  "purchase_price_single": 8.50,
  "purchase_price_carton": 7.20,
  "purchase_price_10carton": 6.80,
  "stock": 50,
  "min_stock": 10,
  "unit": "Stück",
  "barcode": "4260123456789",
  "active": true
}
```

### Order (Auftrag)
```json
{
  "id": "ORD001",
  "order_number": "A-2025-001",
  "customer_id": "CUST001",
  "customer_name": "Max Mustermann",
  "order_date": "2025-01-15",
  "delivery_date": "2025-01-22",
  "status": "new",
  "order_type": "stickerei",
  "total_price": 350.00,
  "items": [
    {
      "article_id": "ART001",
      "article_name": "T-Shirt Basic Weiß",
      "quantity": 10,
      "unit_price": 15.99,
      "total_price": 159.90
    }
  ]
}
```

## Status-Codes

Die API verwendet Standard-HTTP-Status-Codes:

- `200 OK` - Anfrage erfolgreich
- `201 Created` - Ressource erfolgreich erstellt
- `302 Found` - Redirect (bei Web-Endpunkten)
- `400 Bad Request` - Ungültige Anfrage
- `401 Unauthorized` - Nicht authentifiziert
- `403 Forbidden` - Keine Berechtigung
- `404 Not Found` - Ressource nicht gefunden
- `500 Internal Server Error` - Serverfehler

## Fehlerbehandlung

Fehler werden im folgenden Format zurückgegeben:

```json
{
  "success": false,
  "error": "Fehlerbeschreibung"
}
```

### Beispiel

```json
{
  "success": false,
  "error": "Artikel ART999 nicht gefunden"
}
```

## Rate Limiting

Aktuell gibt es kein Rate Limiting. In Produktionsumgebungen sollte dies über einen Reverse Proxy (z.B. Nginx) implementiert werden.

## CORS

Cross-Origin Resource Sharing (CORS) ist standardmäßig nicht aktiviert. Für externe Clients muss dies in der Konfiguration aktiviert werden.

## Versionierung

Die aktuelle API-Version ist **2.0.0**. Die Versionierung folgt Semantic Versioning.

## Weitere Ressourcen

- **OpenAPI-Spezifikation**: `openapi.yaml` (vollständige Dokumentation)
- **Swagger UI**: `http://localhost:5000/api/docs` (interaktive Dokumentation)
- **Deployment-Guide**: `DEPLOYMENT.md`
- **Entwickler-Dokumentation**: `TODO.md`

## Support

Bei Fragen oder Problemen:
- GitHub Issues: https://github.com/yourusername/stitchadmin2.0/issues
- Email: admin@stitchadmin.local

## Änderungshistorie

### Version 2.0.0 (2025-01-13)
- Initiale OpenAPI-Dokumentation
- Swagger UI Integration
- Vollständige API-Endpunkt-Dokumentation
- Kassen-API mit TSE-Integration
- Rechnungs-API mit ZUGFeRD-Unterstützung
