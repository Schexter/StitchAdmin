# 🚀 StitchAdmin 2.0 - Kachel-Dashboard Umbau

**Status:** ✅ Modelle fertig | ⏳ Templates in Arbeit | ⏳ Controller-Integration

---

## ✅ Was wurde erstellt:

### 1. Datenbank-Modelle (FERTIG)
📁 `src/models/document.py`
- ✅ `Document` - Zentrale Dokumentenverwaltung mit GoBD-Compliance
- ✅ `DocumentAccessLog` - Audit Trail (Wer, Wann, Was)
- ✅ `PostEntry` - Postbuch (Ein-/Ausgang)
- ✅ `EmailAccount` - E-Mail-Konten mit verschlüsselten Credentials
- ✅ `ArchivedEmail` - Archivierte E-Mails
- ✅ `EmailAttachment` - E-Mail-Anhänge

### 2. Verschlüsselung (FERTIG)
📁 `src/utils/encryption.py`
- ✅ Fernet-basierte symmetrische Verschlüsselung
- ✅ Automatische Key-Generierung
- ✅ Helper-Funktionen für E-Mail-Passwörter

### 3. Controller (FERTIG)
📁 `src/controllers/documents/documents_controller.py`
- ✅ Dashboard mit Statistiken
- ✅ Dokumenten-Liste mit Filtern
- ✅ Upload-Funktion
- ✅ Dokument-Ansicht mit Versionierung
- ✅ Download-Funktion
- ✅ Löschen mit Sicherheitsprüfung
- ✅ Volltextsuche
- ✅ Postbuch-Listen
- ✅ Post-Erfassung
- ✅ E-Mail-Archivierung

### 4. Neues Dashboard (FERTIG)
📁 `src/templates/dashboard.html`
- ✅ Modernes Kachel-Design
- ✅ 8 Hauptmodule:
  - CRM
  - Produktion
  - Kasse/POS
  - Buchhaltung
  - **Dokumente & Post** 🆕
  - Verwaltung
  - Lager
  - Design-Archiv
- ✅ Responsive Design
- ✅ Statistiken pro Modul
- ✅ Quick-Actions
- ✅ Farbliche Akzente

---

## ⏳ Was noch zu tun ist:

### 1. Blueprint in app.py registrieren
```python
# In app.py nach auth_controller hinzufügen:
register_blueprint_safe('src.controllers.documents.documents_controller', 'documents_bp', 'Dokumente & Post')
```

### 2. Templates für Dokumente-Modul erstellen
📁 `src/templates/documents/`
- [ ] `dashboard.html` - Dokumente-Übersicht
- [ ] `list.html` - Dokumenten-Liste
- [ ] `upload.html` - Upload-Formular
- [ ] `view.html` - Dokument-Ansicht
- [ ] `post_list.html` - Postbuch
- [ ] `post_new.html` - Post-Erfassung
- [ ] `email_accounts.html` - E-Mail-Konten
- [ ] `email_archived.html` - Archivierte E-Mails

### 3. Dashboard-Statistiken erweitern
```python
# In app.py @app.route('/dashboard') ergänzen:
stats = {
    # Bestehend
    'open_orders': ...,
    'in_production': ...,
    'ready_pickup': ...,
    'today_revenue': ...,
    
    # NEU für Dokumente
    'document_count': Document.query.filter_by(is_latest_version=True).count(),
    'open_post': PostEntry.query.filter_by(status='open').count(),
    'unread_emails': ArchivedEmail.query.filter_by(is_read=False).count(),
    
    # NEU für CRM
    'total_customers': Customer.query.count(),
    'open_leads': 0,  # Später mit Lead-System
    
    # NEU für Buchhaltung
    'open_invoices': 0,  # Aus Rechnungsmodul
    'overdue_payments': 0,
    
    # NEU für Lager
    'thread_count': Thread.query.count(),
    'low_stock': 0,
    
    # NEU für Design
    'design_count': 0,  # Später
    'dst_count': 0
}
```

### 4. Datenbank-Tabellen anlegen
```bash
python
>>> from app import create_app
>>> app = create_app()
>>> with app.app_context():
...     from src.models.models import db
...     db.create_all()
...     print("Tabellen erstellt!")
```

### 5. Dependencies installieren
```bash
pip install cryptography  # Für Verschlüsselung
pip install pytesseract   # Für OCR (optional)
pip install pdf2image     # Für PDF-OCR (optional)
```

### 6. Navigation anpassen
- [ ] base.html: Neuen Menüpunkt "Dokumente & Post" hinzufügen
- [ ] Sidebar: Icon + Link

---

## 🎨 Design-Features

### Kachel-Farben:
- **CRM:** Blau-Gradient (#4facfe → #00f2fe)
- **Marketing:** Pink-Gelb (#fa709a → #fee140)
- **Produktion:** Türkis-Lila (#30cfd0 → #330867)
- **Kasse:** Pastell (#a8edea → #fed6e3)
- **Buchhaltung:** Rosa (#ff9a9e → #fecfef)
- **Dokumente:** Pfirsich (#ffecd2 → #fcb69f) 🆕
- **Verwaltung:** Gelb-Cyan (#fddb92 → #d1fdff)
- **Lager:** Blau (#89f7fe → #66a6ff)

### Interaktionen:
- Hover-Effekt: Karte hebt sich ab (-10px)
- Box-Shadow wird größer
- Smooth Transitions (0.3s)
- Quick-Actions für häufige Aufgaben

---

## 🔐 Sicherheit

### Verschlüsselung:
- E-Mail-Passwörter werden mit Fernet verschlüsselt
- Key wird in `instance/encryption.key` gespeichert
- **WICHTIG:** `encryption.key` NIEMALS in Git committen!
- Dateirechte: Nur Owner kann lesen (0o600)

### GoBD-Compliance:
- Dokumente können gesperrt werden (unveränderbar)
- Vollständiger Audit Trail
- Aufbewahrungsfristen werden gespeichert
- SHA-256 Hash für Integrität

---

## 📊 Neue Module im Überblick

### Dokumente & Post:
1. **Dokumentenmanagement (DMS)**
   - Zentrale Ablage
   - Versionierung
   - Volltextsuche
   - Automatische Klassifizierung

2. **Postbuch**
   - Ein-/Ausgang erfassen
   - Tracking-Nummern
   - Fristen & Wiedervorlagen
   - Verknüpfung zu Kunden/Aufträgen

3. **E-Mail-Integration**
   - IMAP-Anbindung
   - Automatische Archivierung
   - Anhänge als separate Dokumente
   - Kunde-Zuordnung

4. **OCR (Optional)**
   - Automatische Texterkennung
   - Rechnungsdaten extrahieren
   - Volltext-Index für Suche

---

## 🚀 Nächste Schritte (Priorisiert):

1. **Sofort:**
   - Blueprint in app.py registrieren
   - Datenbank-Tabellen anlegen
   - Templates erstellen
   - Statistiken im Dashboard implementieren

2. **Diese Woche:**
   - Upload-Funktion testen
   - Postbuch testen
   - Navigation anpassen

3. **Nächste Woche:**
   - E-Mail-Integration (IMAP)
   - OCR mit Tesseract
   - Automatische Klassifizierung

4. **Später:**
   - Marketing-Modul ausarbeiten
   - CRM-Erweiterungen (Leads, Pipeline)
   - Workflow-System (Freigaben)

---

## 💡 Marketing-Modul (Zukünftig)

### Geplante Features:
- Newsletter-Verwaltung
- Social Media Planer
- Kampagnen-Tracking
- ROI-Analysen
- Event-Management (Messen)
- Referenz-Galerie
- Testimonials

---

**Erstellt:** 22.11.2025
**Status:** 60% komplett
**Autor:** Hans Hahn - Alle Rechte vorbehalten
