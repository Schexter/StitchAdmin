# 🎨 Design-Management System - Konzept & Spezifikation

**Erstellt:** 30.11.2025  
**Status:** Konzeptphase  
**Autor:** Hans Hahn - Alle Rechte vorbehalten

---

## 1. Übersicht & Zielsetzung

### 1.1 Problemstellung

Aktuell werden Designs nur als Anhang an Aufträge behandelt:
- Keine zentrale Design-Bibliothek
- Keine Versionierung
- Keine strukturierte Farbverwaltung (Garnfarben)
- Keine Historie (wann wurde Design wo eingesetzt)
- Design-Bestellungen nur rudimentär integriert
- Keine PDF-Beauftragung für externe Puncher/Druckdienstleister

### 1.2 Ziel

Ein **vollständiges Design-Management-System** mit:
- **Design-Archiv** (zentrale Bibliothek für Stick- und Druck-Designs)
- **Versionierung** (Änderungen nachvollziehbar)
- **Farbmanagement** (Garnfarben für Stick, CMYK/Pantone für Druck)
- **Vorschau-System** (Thumbnails, DST-Analyse)
- **Historie** (wo wurde Design eingesetzt)
- **Externe Beauftragung** (PDF-Beauftragung für Puncher/Druckerei)
- **Kategorisierung** (Stick vs. Druck vs. DTF)

---

## 2. Design-Typen

### 2.1 Stickerei-Designs (Embroidery)

| Aspekt | Details |
|--------|---------|
| **Dateiformate** | DST, EMB, PES, JEF, EXP, VP3, HUS |
| **Analyse** | pyembroidery (Stichzahl, Größe, Farbwechsel) |
| **Farben** | Garnfarben (Madeira, Polystar, etc.) |
| **Spezifikationen** | Stichzahl, Breite/Höhe, Stickzeit |
| **Externe Beauftragung** | Puncher/Digitizer |

### 2.2 Druck-Designs (Print)

| Aspekt | Details |
|--------|---------|
| **Dateiformate** | PDF, AI, EPS, SVG, PNG (hochauflösend), TIFF |
| **Farben** | CMYK, Pantone, RGB |
| **Spezifikationen** | DPI, Farbtiefe, Druckgröße |
| **Externe Beauftragung** | Grafik-Designer, Druckerei |

### 2.3 DTF-Designs (Direct to Film)

| Aspekt | Details |
|--------|---------|
| **Dateiformate** | PNG (transparent), PDF |
| **Farben** | CMYK + Weiß |
| **Spezifikationen** | DPI, Weißkanal |
| **Externe Beauftragung** | DTF-Dienstleister |

---

## 3. Datenmodell

### 3.1 Design (Stammdaten)

```python
class Design(db.Model):
    """
    Zentrale Design-Bibliothek
    Speichert alle Designs (Stick, Druck, DTF)
    """
    __tablename__ = 'designs'
    
    id = db.Column(db.String(50), primary_key=True)
    
    # Basis-Informationen
    design_number = db.Column(db.String(50), unique=True)  # D-2025-0001
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Kategorisierung
    design_type = db.Column(db.String(50), nullable=False)  # embroidery, print, dtf
    category = db.Column(db.String(100))  # Logo, Schrift, Motiv, etc.
    tags = db.Column(db.Text)  # JSON Array für Suche
    
    # Kunde (optional - kann auch Eigendesign sein)
    customer_id = db.Column(db.String(50), db.ForeignKey('customers.id'))
    is_customer_design = db.Column(db.Boolean, default=True)  # Kundendesign vs. Eigendesign
    
    # ═══════════════════════════════════════════════════════════════
    # DATEIEN & VORSCHAU
    # ═══════════════════════════════════════════════════════════════
    
    # Hauptdatei
    file_path = db.Column(db.String(500))  # Pfad zur Original-Datei
    file_type = db.Column(db.String(20))   # dst, emb, pdf, png, etc.
    file_size_kb = db.Column(db.Integer)
    file_hash = db.Column(db.String(64))   # SHA-256 für Duplikat-Erkennung
    
    # Vorschau
    thumbnail_path = db.Column(db.String(500))  # Kleines Vorschaubild
    preview_path = db.Column(db.String(500))    # Größere Vorschau
    preview_generated_at = db.Column(db.DateTime)
    
    # Produktionsdatei (falls abweichend)
    production_file_path = db.Column(db.String(500))
    production_file_type = db.Column(db.String(20))
    
    # ═══════════════════════════════════════════════════════════════
    # STICKEREI-SPEZIFISCH
    # ═══════════════════════════════════════════════════════════════
    
    # Maße
    width_mm = db.Column(db.Float)
    height_mm = db.Column(db.Float)
    
    # Stichzahl & Zeit
    stitch_count = db.Column(db.Integer)
    color_changes = db.Column(db.Integer)
    estimated_time_minutes = db.Column(db.Integer)
    
    # Garnfarben (JSON Array)
    # Format: [
    #   {"sequence": 1, "color_code": "1147", "color_name": "Madeira 1147", "rgb": "#FF0000", "thread_brand": "Madeira"},
    #   {"sequence": 2, "color_code": "1000", "color_name": "Schwarz", "rgb": "#000000", "thread_brand": "Madeira"}
    # ]
    thread_colors = db.Column(db.Text)
    
    # DST-Analyse Daten (JSON - komplette pyembroidery Analyse)
    dst_analysis = db.Column(db.Text)
    
    # ═══════════════════════════════════════════════════════════════
    # DRUCK-SPEZIFISCH
    # ═══════════════════════════════════════════════════════════════
    
    # Maße
    print_width_cm = db.Column(db.Float)
    print_height_cm = db.Column(db.Float)
    
    # Druckspezifikationen
    dpi = db.Column(db.Integer)
    color_mode = db.Column(db.String(20))  # cmyk, rgb, pantone
    
    # Farben (JSON Array)
    # Format: [
    #   {"type": "pantone", "code": "186 C", "name": "Rot"},
    #   {"type": "cmyk", "c": 0, "m": 100, "y": 100, "k": 0}
    # ]
    print_colors = db.Column(db.Text)
    
    # Druckmethode
    print_method = db.Column(db.String(50))  # dtf, sublimation, siebdruck, digital, transfer
    
    # ═══════════════════════════════════════════════════════════════
    # STATUS & WORKFLOW
    # ═══════════════════════════════════════════════════════════════
    
    status = db.Column(db.String(50), default='draft')
    # draft, active, archived, needs_revision
    
    # Qualität
    quality_rating = db.Column(db.Integer)  # 1-5 Sterne
    quality_notes = db.Column(db.Text)
    
    # Freigabe
    is_approved = db.Column(db.Boolean, default=False)
    approved_at = db.Column(db.DateTime)
    approved_by = db.Column(db.String(80))
    
    # ═══════════════════════════════════════════════════════════════
    # HERKUNFT & KOSTEN
    # ═══════════════════════════════════════════════════════════════
    
    # Woher kommt das Design?
    source = db.Column(db.String(50))  # customer, internal, external_order
    source_order_id = db.Column(db.String(50))  # Verknüpfung zur Design-Bestellung
    
    # Kosten
    creation_cost = db.Column(db.Float)  # Was hat das Design gekostet?
    supplier_id = db.Column(db.String(50), db.ForeignKey('suppliers.id'))  # Wer hat es erstellt?
    
    # ═══════════════════════════════════════════════════════════════
    # METADATEN
    # ═══════════════════════════════════════════════════════════════
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))
    
    # ═══════════════════════════════════════════════════════════════
    # RELATIONSHIPS
    # ═══════════════════════════════════════════════════════════════
    
    customer = db.relationship('Customer', backref='designs')
    supplier = db.relationship('Supplier', backref='created_designs')
    versions = db.relationship('DesignVersion', back_populates='design', cascade='all, delete-orphan')
    usage_history = db.relationship('DesignUsage', back_populates='design', cascade='all, delete-orphan')
    
    # ═══════════════════════════════════════════════════════════════
    # METHODEN
    # ═══════════════════════════════════════════════════════════════
    
    def get_thread_colors(self):
        """Gibt Garnfarben als Liste zurück"""
        if self.thread_colors:
            return json.loads(self.thread_colors)
        return []
    
    def set_thread_colors(self, colors):
        """Setzt Garnfarben aus Liste"""
        self.thread_colors = json.dumps(colors)
    
    def get_print_colors(self):
        """Gibt Druckfarben als Liste zurück"""
        if self.print_colors:
            return json.loads(self.print_colors)
        return []
    
    def analyze_dst_file(self):
        """Analysiert DST-Datei mit pyembroidery"""
        if self.design_type != 'embroidery' or not self.file_path:
            return None
        
        try:
            import pyembroidery
            pattern = pyembroidery.read(self.file_path)
            
            # Bounds berechnen
            bounds = pattern.bounds()
            width_mm = (bounds[2] - bounds[0]) / 10  # Einheiten zu mm
            height_mm = (bounds[3] - bounds[1]) / 10
            
            # Stichzahl
            stitch_count = len(pattern.stitches)
            
            # Farben
            colors = []
            for i, thread in enumerate(pattern.threadlist):
                colors.append({
                    'sequence': i + 1,
                    'color_code': thread.hex_color() if hasattr(thread, 'hex_color') else '',
                    'color_name': thread.description if hasattr(thread, 'description') else f'Farbe {i+1}',
                    'rgb': thread.hex_color() if hasattr(thread, 'hex_color') else '#000000'
                })
            
            # Farbwechsel zählen
            color_changes = sum(1 for s in pattern.stitches if s[2] == pyembroidery.COLOR_CHANGE)
            
            # Zeitschätzung (ca. 800 Stiche/Minute)
            estimated_time = round(stitch_count / 800)
            
            # Speichern
            self.width_mm = round(width_mm, 1)
            self.height_mm = round(height_mm, 1)
            self.stitch_count = stitch_count
            self.color_changes = color_changes
            self.estimated_time_minutes = estimated_time
            self.set_thread_colors(colors)
            
            # Vollständige Analyse als JSON
            self.dst_analysis = json.dumps({
                'bounds': bounds,
                'stitch_count': stitch_count,
                'color_changes': color_changes,
                'colors': colors,
                'estimated_time_minutes': estimated_time,
                'analyzed_at': datetime.utcnow().isoformat()
            })
            
            return True
            
        except Exception as e:
            print(f"DST-Analyse fehlgeschlagen: {e}")
            return False
    
    def get_usage_count(self):
        """Zählt wie oft das Design verwendet wurde"""
        return len(self.usage_history)
```

### 3.2 DesignVersion (Versionierung)

```python
class DesignVersion(db.Model):
    """
    Versionierung von Designs
    Speichert alle Änderungen/Revisionen
    """
    __tablename__ = 'design_versions'
    
    id = db.Column(db.Integer, primary_key=True)
    design_id = db.Column(db.String(50), db.ForeignKey('designs.id'), nullable=False)
    
    # Version
    version_number = db.Column(db.Integer, nullable=False)  # 1, 2, 3, ...
    version_name = db.Column(db.String(100))  # "Original", "Revision 1", etc.
    
    # Änderungen
    change_description = db.Column(db.Text)  # Was wurde geändert?
    change_reason = db.Column(db.String(200))  # Warum?
    
    # Dateien
    file_path = db.Column(db.String(500))
    thumbnail_path = db.Column(db.String(500))
    
    # Technische Daten (Snapshot der Design-Daten bei dieser Version)
    technical_data = db.Column(db.Text)  # JSON: stitch_count, colors, etc.
    
    # Wer hat geändert?
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    
    # Ist dies die aktive Version?
    is_active = db.Column(db.Boolean, default=False)
    
    # Relationships
    design = db.relationship('Design', back_populates='versions')
```

### 3.3 DesignUsage (Historie)

```python
class DesignUsage(db.Model):
    """
    Verwendungs-Historie
    Trackt wo ein Design eingesetzt wurde
    """
    __tablename__ = 'design_usage'
    
    id = db.Column(db.Integer, primary_key=True)
    design_id = db.Column(db.String(50), db.ForeignKey('designs.id'), nullable=False)
    
    # Wo wurde es verwendet?
    order_id = db.Column(db.String(50), db.ForeignKey('orders.id'))
    order_item_id = db.Column(db.Integer, db.ForeignKey('order_items.id'))
    
    # Verwendungsdetails
    position = db.Column(db.String(100))  # Brust links, Rücken, etc.
    quantity = db.Column(db.Integer, default=1)  # Wie oft bestickt/bedruckt
    
    # Anpassungen (falls abweichend vom Original)
    size_adjustment = db.Column(db.String(50))  # "90%", "110%", etc.
    color_adjustments = db.Column(db.Text)  # JSON: welche Farben geändert
    
    # Ergebnis
    quality_feedback = db.Column(db.Integer)  # 1-5 Sterne
    feedback_notes = db.Column(db.Text)
    
    # Zeitstempel
    used_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_by = db.Column(db.String(80))
    
    # Relationships
    design = db.relationship('Design', back_populates='usage_history')
    order = db.relationship('Order', backref='design_usages')
```

### 3.4 ThreadColor (Garnfarben-Bibliothek)

```python
class ThreadBrand(db.Model):
    """Garn-Marken (Madeira, Polystar, etc.)"""
    __tablename__ = 'thread_brands'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    short_code = db.Column(db.String(10))  # MA, PO, etc.
    website = db.Column(db.String(200))
    is_default = db.Column(db.Boolean, default=False)
    
    colors = db.relationship('ThreadColor', back_populates='brand')


class ThreadColor(db.Model):
    """
    Garnfarben-Bibliothek
    Zentrale Sammlung aller Garnfarben für Stickerei
    """
    __tablename__ = 'thread_colors'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Marke & Code
    brand_id = db.Column(db.Integer, db.ForeignKey('thread_brands.id'), nullable=False)
    color_code = db.Column(db.String(20), nullable=False)  # z.B. "1147"
    color_name = db.Column(db.String(100))  # "Weihnachtsrot"
    
    # Farbe
    rgb_hex = db.Column(db.String(7))  # "#FF0000"
    rgb_r = db.Column(db.Integer)
    rgb_g = db.Column(db.Integer)
    rgb_b = db.Column(db.Integer)
    
    # Kategorisierung
    color_family = db.Column(db.String(50))  # rot, blau, grün, etc.
    is_metallic = db.Column(db.Boolean, default=False)
    is_glow = db.Column(db.Boolean, default=False)
    
    # Lagerbestand (optional)
    stock_quantity = db.Column(db.Integer, default=0)
    min_stock = db.Column(db.Integer, default=1)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_favorite = db.Column(db.Boolean, default=False)
    
    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    brand = db.relationship('ThreadBrand', back_populates='colors')
    
    # Unique Constraint
    __table_args__ = (
        db.UniqueConstraint('brand_id', 'color_code', name='unique_brand_color'),
    )
    
    @property
    def full_name(self):
        return f"{self.brand.short_code} {self.color_code}" if self.brand else self.color_code
```

---

## 4. Design-Bestellung (Externe Beauftragung)

### 4.1 DesignOrder (bereits im Einkauf-Modul Konzept)

Erweitert um **Druck-Support**:

```python
class DesignOrder(db.Model):
    """
    Design-Bestellungen bei externen Dienstleistern
    Für: Puncher (Stick), Grafiker (Druck), DTF-Dienstleister
    """
    __tablename__ = 'design_orders'
    
    id = db.Column(db.String(50), primary_key=True)
    design_order_number = db.Column(db.String(50), unique=True)  # DO-2025-0001
    
    # Verknüpfungen
    order_id = db.Column(db.String(50), db.ForeignKey('orders.id'))
    design_id = db.Column(db.String(50), db.ForeignKey('designs.id'))  # Falls existierendes Design überarbeitet wird
    supplier_id = db.Column(db.String(50), db.ForeignKey('suppliers.id'))
    
    # ═══════════════════════════════════════════════════════════════
    # TYP & SPEZIFIKATION
    # ═══════════════════════════════════════════════════════════════
    
    # Art der Bestellung
    design_type = db.Column(db.String(50), nullable=False)  # embroidery, print, dtf
    order_type = db.Column(db.String(50))  # new_design, revision, conversion
    
    # Allgemeine Spezifikation
    design_name = db.Column(db.String(200))
    design_description = db.Column(db.Text)
    
    # ═══════════════════════════════════════════════════════════════
    # STICKEREI-SPEZIFIKATION
    # ═══════════════════════════════════════════════════════════════
    
    # Maße
    target_width_mm = db.Column(db.Float)
    target_height_mm = db.Column(db.Float)
    
    # Stick-Vorgaben
    max_stitch_count = db.Column(db.Integer)
    max_colors = db.Column(db.Integer)
    stitch_density = db.Column(db.String(50))  # normal, dicht, locker
    
    # Garnfarben (JSON)
    requested_thread_colors = db.Column(db.Text)  # Gewünschte Farben
    
    # Unterlage/Backing
    underlay_type = db.Column(db.String(50))  # keine, leicht, standard, stark
    
    # Stoffart (wichtig für Puncher)
    fabric_type = db.Column(db.String(100))  # Baumwolle, Fleece, Leder, etc.
    
    # ═══════════════════════════════════════════════════════════════
    # DRUCK-SPEZIFIKATION
    # ═══════════════════════════════════════════════════════════════
    
    # Maße
    target_print_width_cm = db.Column(db.Float)
    target_print_height_cm = db.Column(db.Float)
    
    # Druck-Vorgaben
    print_method = db.Column(db.String(50))  # dtf, sublimation, siebdruck, digital, transfer
    min_dpi = db.Column(db.Integer, default=300)
    color_mode = db.Column(db.String(20))  # cmyk, pantone, rgb
    
    # Farbvorgaben (JSON)
    requested_print_colors = db.Column(db.Text)  # Pantone-Codes, CMYK-Werte
    
    # Transparenz/Hintergrund
    needs_transparent_bg = db.Column(db.Boolean, default=False)
    needs_white_underbase = db.Column(db.Boolean, default=False)  # Für DTF/dunkle Stoffe
    
    # ═══════════════════════════════════════════════════════════════
    # VORLAGE & REFERENZ
    # ═══════════════════════════════════════════════════════════════
    
    # Kundenvorlage
    source_file_path = db.Column(db.String(500))
    source_file_type = db.Column(db.String(50))  # jpg, png, pdf, ai, sketch
    
    # Referenz-Bilder (JSON Array)
    reference_images = db.Column(db.Text)
    
    # Textuelle Beschreibung
    special_requirements = db.Column(db.Text)
    
    # ═══════════════════════════════════════════════════════════════
    # STATUS & WORKFLOW
    # ═══════════════════════════════════════════════════════════════
    
    status = db.Column(db.String(50), default='draft')
    # draft, sent, quoted, deposit_pending, deposit_paid, 
    # ordered, in_progress, delivered, received, reviewed, 
    # approved, revision_requested, completed
    
    # Anfrage
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    request_sent_at = db.Column(db.DateTime)
    request_sent_to = db.Column(db.String(200))
    
    # Angebot
    quote_received_date = db.Column(db.DateTime)
    quote_price = db.Column(db.Float)
    quote_delivery_days = db.Column(db.Integer)
    quote_notes = db.Column(db.Text)
    quote_file_path = db.Column(db.String(500))
    
    # Anzahlung
    deposit_required = db.Column(db.Boolean, default=False)
    deposit_percent = db.Column(db.Float)
    deposit_amount = db.Column(db.Float)
    deposit_status = db.Column(db.String(50))
    deposit_paid_date = db.Column(db.DateTime)
    
    # Bestellung
    order_date = db.Column(db.DateTime)
    expected_delivery = db.Column(db.Date)
    
    # Lieferung
    delivered_date = db.Column(db.DateTime)
    delivered_file_path = db.Column(db.String(500))
    delivered_preview_path = db.Column(db.String(500))
    
    # Qualitätsprüfung
    review_status = db.Column(db.String(50))
    review_date = db.Column(db.DateTime)
    review_notes = db.Column(db.Text)
    revision_count = db.Column(db.Integer, default=0)
    
    # Kosten
    total_price = db.Column(db.Float)
    payment_status = db.Column(db.String(50))
    
    # ═══════════════════════════════════════════════════════════════
    # PDF-BEAUFTRAGUNG
    # ═══════════════════════════════════════════════════════════════
    
    # Generierte PDF
    order_pdf_path = db.Column(db.String(500))
    order_pdf_generated_at = db.Column(db.DateTime)
    
    # ═══════════════════════════════════════════════════════════════
    # METADATEN
    # ═══════════════════════════════════════════════════════════════
    
    priority = db.Column(db.String(20), default='normal')
    internal_notes = db.Column(db.Text)
    communication_log = db.Column(db.Text)  # JSON Array
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    order = db.relationship('Order', backref='design_orders')
    design = db.relationship('Design', backref='orders_for_design')
    supplier = db.relationship('Supplier', backref='design_orders_received')
```

---

## 5. PDF-Beauftragung

### 5.1 Struktur der PDF

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  [FIRMENLOGO]                              DESIGN-BEAUFTRAGUNG           │
│  Mustermann Stickerei GmbH                 DO-2025-0042                  │
│  Musterstraße 1                            Datum: 30.11.2025             │
│  12345 Musterstadt                                                       │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  AN:                                       AUFTRAGSART:                  │
│  PunchPro Digitizing                       ☑ Stickprogramm (DST)        │
│  Herr Max Puncher                          ☐ Druckdatei                  │
│  puncher@example.com                       ☐ DTF-Design                  │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  DESIGN-SPEZIFIKATION                                                    │
│  ════════════════════════════════════════════════════════════════════    │
│                                                                          │
│  Name:           Firmenlogo XY GmbH                                      │
│  Typ:            Logo-Stickerei                                          │
│                                                                          │
│  MASSE:                                                                  │
│  ┌─────────────────┐                                                     │
│  │   80 x 40 mm    │  Breite: 80 mm                                     │
│  │                 │  Höhe:   40 mm                                      │
│  └─────────────────┘                                                     │
│                                                                          │
│  STICK-VORGABEN:                                                         │
│  • Max. Stichzahl:    15.000                                            │
│  • Max. Farben:       4                                                  │
│  • Stoffart:          Baumwoll-Poloshirt                                │
│  • Unterlage:         Standard                                           │
│                                                                          │
│  FARBVORGABEN:                                                           │
│  ┌────┬──────────────┬─────────────┬─────────┐                          │
│  │ Nr │ Farbe        │ Madeira Nr. │ Muster  │                          │
│  ├────┼──────────────┼─────────────┼─────────┤                          │
│  │ 1  │ Dunkelblau   │ 1042        │ ███     │                          │
│  │ 2  │ Weiß         │ 1001        │ ███     │                          │
│  │ 3  │ Rot          │ 1147        │ ███     │                          │
│  │ 4  │ Schwarz      │ 1000        │ ███     │                          │
│  └────┴──────────────┴─────────────┴─────────┘                          │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  KUNDENVORLAGE                                                           │
│  ════════════════════════════════════════════════════════════════════    │
│                                                                          │
│  ┌────────────────────────────────────────┐                              │
│  │                                        │                              │
│  │         [VORSCHAUBILD]                 │                              │
│  │                                        │                              │
│  │         Logo_XY_GmbH.pdf               │                              │
│  │                                        │                              │
│  └────────────────────────────────────────┘                              │
│                                                                          │
│  Originaldatei im Anhang: Logo_XY_GmbH.pdf                              │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  BESONDERE ANFORDERUNGEN                                                 │
│  ════════════════════════════════════════════════════════════════════    │
│                                                                          │
│  • Schrift "XY GmbH" muss gut lesbar sein                               │
│  • Feine Details im Logo beibehalten                                     │
│  • Für Poloshirt-Veredelung optimieren                                   │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  LIEFERUNG                                                               │
│  ════════════════════════════════════════════════════════════════════    │
│                                                                          │
│  Gewünschte Lieferung:  05.12.2025                                      │
│  Priorität:             ☑ Normal  ☐ Eilig (+25%)                        │
│                                                                          │
│  Lieferformat:          DST (Tajima)                                     │
│  Lieferung per:         E-Mail an bestellung@mustermann.de               │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ZAHLUNGSBEDINGUNGEN                                                     │
│  ════════════════════════════════════════════════════════════════════    │
│                                                                          │
│  ☑ 50% Anzahlung vor Beginn                                             │
│  ☐ Vollständige Zahlung nach Lieferung                                  │
│                                                                          │
│  Verwendungszweck: DO-2025-0042                                          │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Kontakt bei Rückfragen:                                                 │
│  Hans Hahn | Tel: 0123/456789 | bestellung@mustermann.de                 │
│                                                                          │
│  ────────────────────────────────────────────────────────────────────    │
│                                                                          │
│  Datum: ____________    Unterschrift: _______________________________    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 5.2 PDF-Generator Service

```python
# src/services/design_order_pdf.py

class DesignOrderPDFGenerator:
    """Generiert PDF-Beauftragungen für Design-Bestellungen"""
    
    def __init__(self, design_order):
        self.order = design_order
        self.pdf = None
    
    def generate(self):
        """Erstellt die PDF"""
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        
        # ... Implementation
        
    def _add_header(self):
        """Fügt Kopfzeile mit Logo und Bestellnummer hinzu"""
        pass
    
    def _add_recipient(self):
        """Fügt Empfänger-Block hinzu"""
        pass
    
    def _add_specification(self):
        """Fügt Design-Spezifikation hinzu"""
        pass
    
    def _add_color_table(self):
        """Fügt Farbtabelle hinzu"""
        pass
    
    def _add_preview_image(self):
        """Fügt Vorschaubild hinzu"""
        pass
    
    def _add_requirements(self):
        """Fügt besondere Anforderungen hinzu"""
        pass
    
    def _add_delivery_info(self):
        """Fügt Lieferinformationen hinzu"""
        pass
    
    def _add_payment_terms(self):
        """Fügt Zahlungsbedingungen hinzu"""
        pass
```

---

## 6. Routing-Struktur

### 6.1 Design-Archiv

```
/designs/                           → Übersicht (Liste)
/designs/new                        → Neues Design anlegen
/designs/<id>                       → Design-Details
/designs/<id>/edit                  → Design bearbeiten
/designs/<id>/versions              → Versionsverlauf
/designs/<id>/history               → Verwendungs-Historie
/designs/<id>/analyze               → DST neu analysieren
/designs/<id>/duplicate             → Design duplizieren
/designs/search                     → Suche
/designs/colors                     → Garnfarben-Bibliothek
```

### 6.2 Design-Bestellungen (im Einkauf-Modul)

```
/purchasing/design-orders/          → Übersicht
/purchasing/design-orders/new       → Neue Bestellung
/purchasing/design-orders/<id>      → Details
/purchasing/design-orders/<id>/pdf  → PDF generieren
/purchasing/design-orders/<id>/send → E-Mail senden
/purchasing/design-orders/<id>/receive → Eingang erfassen
```

---

## 7. UI-Konzept

### 7.1 Design-Archiv Übersicht

```
┌──────────────────────────────────────────────────────────────────────────┐
│  🎨 Design-Archiv                               [+ Neues Design] [Suche] │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Filter: [Alle Typen ▼] [Alle Kunden ▼] [Alle Status ▼]                 │
│                                                                          │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐             │
│  │   [Vorschau]    │ │   [Vorschau]    │ │   [Vorschau]    │             │
│  │                 │ │                 │ │                 │             │
│  │ D-2025-0042     │ │ D-2025-0041     │ │ D-2025-0040     │             │
│  │ Müller Logo     │ │ Sport AG        │ │ Restaurant XY   │             │
│  │ 🧵 Stick        │ │ 🖨️ Druck       │ │ 🧵 Stick        │             │
│  │ 12.500 Stiche   │ │ CMYK, 300dpi    │ │ 8.200 Stiche    │             │
│  │ 4 Farben        │ │ 3 Farben        │ │ 2 Farben        │             │
│  │ ⭐⭐⭐⭐⭐      │ │ ⭐⭐⭐⭐        │ │ ⭐⭐⭐⭐⭐      │             │
│  │ 12x verwendet   │ │ 3x verwendet    │ │ 28x verwendet   │             │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘             │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Design-Detail Ansicht

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ← Zurück                                        [Bearbeiten] [Löschen]  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  D-2025-0042 - Müller GmbH Logo                                         │
│  ═══════════════════════════════════════════════════════════════════     │
│                                                                          │
│  ┌────────────────────────┐  ┌─────────────────────────────────────┐     │
│  │                        │  │ DETAILS                              │     │
│  │                        │  ├─────────────────────────────────────┤     │
│  │     [VORSCHAU]         │  │ Typ:      🧵 Stickerei              │     │
│  │                        │  │ Status:   ✅ Aktiv                  │     │
│  │                        │  │ Kunde:    Müller GmbH               │     │
│  │                        │  │ Erstellt: 15.10.2025                │     │
│  └────────────────────────┘  └─────────────────────────────────────┘     │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │ TECHNISCHE DATEN                                                 │     │
│  ├─────────────────────────────────────────────────────────────────┤     │
│  │ Größe:        80 x 45 mm                                        │     │
│  │ Stichzahl:    12.500                                            │     │
│  │ Farbwechsel:  3                                                 │     │
│  │ Geschätzte Zeit: 16 min                                         │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │ GARNFARBEN                                              [Edit]   │     │
│  ├─────────────────────────────────────────────────────────────────┤     │
│  │ 1. ███ Madeira 1042 - Dunkelblau                               │     │
│  │ 2. ███ Madeira 1001 - Weiß                                     │     │
│  │ 3. ███ Madeira 1147 - Rot                                      │     │
│  │ 4. ███ Madeira 1000 - Schwarz                                  │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │ VERWENDUNGS-HISTORIE                              [Alle anzeigen]│     │
│  ├─────────────────────────────────────────────────────────────────┤     │
│  │ • AU-2025-0234 - Müller GmbH - 15.11.2025 - 50 Stk.            │     │
│  │ • AU-2025-0198 - Müller GmbH - 02.10.2025 - 25 Stk.            │     │
│  │ • AU-2025-0156 - Müller GmbH - 18.08.2025 - 100 Stk.           │     │
│  │ ... insgesamt 12x verwendet                                     │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │ VERSIONEN                                           [Neue Version]│     │
│  ├─────────────────────────────────────────────────────────────────┤     │
│  │ v2 (aktiv) - 20.10.2025 - "Schriftgröße angepasst"             │     │
│  │ v1         - 15.10.2025 - "Original"                            │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Phasenplan

### Phase 1: Design-Model & Basis (Sprint 1)
- [ ] Design Model erstellen
- [ ] DesignVersion Model
- [ ] DesignUsage Model
- [ ] Migration Script
- [ ] Basis-Controller

### Phase 2: Design-Archiv UI (Sprint 1-2)
- [ ] Übersicht (Grid/Liste)
- [ ] Detail-Ansicht
- [ ] Anlegen/Bearbeiten
- [ ] DST-Analyse Integration
- [ ] Thumbnail-Generierung

### Phase 3: Garnfarben-Bibliothek (Sprint 2)
- [ ] ThreadBrand Model
- [ ] ThreadColor Model
- [ ] Import (Madeira, Polystar CSV)
- [ ] Farbauswahl-UI

### Phase 4: Design-Bestellungen (Sprint 2-3)
- [ ] DesignOrder Model (erweitert)
- [ ] PDF-Generator
- [ ] E-Mail-Versand
- [ ] Stickerei-Workflow
- [ ] Druck-Workflow

### Phase 5: Integration (Sprint 3-4)
- [ ] Order-Integration (Design aus Archiv wählen)
- [ ] Dashboard-Kachel "Design-Archiv"
- [ ] Statistiken
- [ ] Suche & Filter

---

## 9. Nächste Schritte

**Nach Konzept-Freigabe:**
1. Models erstellen (`design.py`, `design_version.py`, `design_usage.py`)
2. Migration ausführen
3. Basis-Controller + Templates
4. DST-Analyse aktivieren
5. PDF-Generator implementieren

---

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**
