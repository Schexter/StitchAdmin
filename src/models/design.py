"""
Design Management Models für StitchAdmin
Zentrale Bibliothek für Stick-, Druck- und DTF-Designs

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime
from src.models.models import db
import json


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
    file_name = db.Column(db.String(255))  # Original-Dateiname
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
    print_method = db.Column(db.String(50))  # siebdruck, digital, transfer, dtf
    
    # DTF spezifisch
    has_white_underbase = db.Column(db.Boolean, default=False)
    has_transparent_bg = db.Column(db.Boolean, default=False)
    
    # ═══════════════════════════════════════════════════════════════
    # STATUS & WORKFLOW
    # ═══════════════════════════════════════════════════════════════
    
    status = db.Column(db.String(50), default='active')
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
    # STATISTIK
    # ═══════════════════════════════════════════════════════════════
    
    usage_count = db.Column(db.Integer, default=0)  # Wie oft verwendet
    last_used_at = db.Column(db.DateTime)
    
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
    supplier = db.relationship('Supplier', backref='created_designs', foreign_keys=[supplier_id])
    versions = db.relationship('DesignVersion', back_populates='design', cascade='all, delete-orphan', order_by='DesignVersion.version_number.desc()')
    usage_history = db.relationship('DesignUsage', back_populates='design', cascade='all, delete-orphan', order_by='DesignUsage.used_at.desc()')
    
    # ═══════════════════════════════════════════════════════════════
    # METHODEN
    # ═══════════════════════════════════════════════════════════════
    
    def get_thread_colors(self):
        """Gibt Garnfarben als Liste zurück"""
        if self.thread_colors:
            try:
                return json.loads(self.thread_colors)
            except:
                return []
        return []
    
    def set_thread_colors(self, colors):
        """Setzt Garnfarben aus Liste"""
        self.thread_colors = json.dumps(colors, ensure_ascii=False)
    
    def get_print_colors(self):
        """Gibt Druckfarben als Liste zurück"""
        if self.print_colors:
            try:
                return json.loads(self.print_colors)
            except:
                return []
        return []
    
    def set_print_colors(self, colors):
        """Setzt Druckfarben aus Liste"""
        self.print_colors = json.dumps(colors, ensure_ascii=False)
    
    def get_tags(self):
        """Gibt Tags als Liste zurück"""
        if self.tags:
            try:
                return json.loads(self.tags)
            except:
                return []
        return []
    
    def set_tags(self, tags):
        """Setzt Tags aus Liste"""
        self.tags = json.dumps(tags, ensure_ascii=False)
    
    def get_dst_analysis(self):
        """Gibt DST-Analyse als Dict zurück"""
        if self.dst_analysis:
            try:
                return json.loads(self.dst_analysis)
            except:
                return {}
        return {}
    
    def analyze_embroidery_file(self):
        """Analysiert Stickdatei mit pyembroidery"""
        if self.design_type != 'embroidery' or not self.file_path:
            return False
        
        try:
            import pyembroidery
            import os
            
            if not os.path.exists(self.file_path):
                return False
            
            pattern = pyembroidery.read(self.file_path)
            if not pattern:
                return False
            
            # Bounds berechnen
            bounds = pattern.bounds()
            if bounds:
                self.width_mm = round((bounds[2] - bounds[0]) / 10, 1)
                self.height_mm = round((bounds[3] - bounds[1]) / 10, 1)
            
            # Stichzahl
            self.stitch_count = len([s for s in pattern.stitches if s[2] in (0, 1)])  # Nur echte Stiche
            
            # Farben extrahieren
            colors = []
            for i, thread in enumerate(pattern.threadlist):
                color_data = {
                    'sequence': i + 1,
                    'color_code': '',
                    'color_name': '',
                    'rgb': '#000000',
                    'thread_brand': ''
                }
                
                if hasattr(thread, 'hex_color'):
                    color_data['rgb'] = thread.hex_color()
                if hasattr(thread, 'description'):
                    color_data['color_name'] = thread.description or f'Farbe {i+1}'
                if hasattr(thread, 'catalog_number'):
                    color_data['color_code'] = thread.catalog_number or ''
                if hasattr(thread, 'brand'):
                    color_data['thread_brand'] = thread.brand or ''
                
                colors.append(color_data)
            
            # Farbwechsel zählen
            self.color_changes = sum(1 for s in pattern.stitches if s[2] == pyembroidery.COLOR_CHANGE)
            
            # Zeitschätzung (ca. 800 Stiche/Minute)
            if self.stitch_count:
                self.estimated_time_minutes = max(1, round(self.stitch_count / 800))
            
            # Farben speichern
            self.set_thread_colors(colors)
            
            # Vollständige Analyse als JSON
            self.dst_analysis = json.dumps({
                'bounds': bounds,
                'stitch_count': self.stitch_count,
                'color_changes': self.color_changes,
                'colors': colors,
                'estimated_time_minutes': self.estimated_time_minutes,
                'width_mm': self.width_mm,
                'height_mm': self.height_mm,
                'analyzed_at': datetime.utcnow().isoformat()
            }, ensure_ascii=False)
            
            self.preview_generated_at = datetime.utcnow()
            
            return True
            
        except Exception as e:
            print(f"Stickdatei-Analyse fehlgeschlagen: {e}")
            return False
    
    def increment_usage(self):
        """Erhöht den Verwendungszähler"""
        self.usage_count = (self.usage_count or 0) + 1
        self.last_used_at = datetime.utcnow()
    
    @property
    def type_icon(self):
        """Gibt passendes Icon für Design-Typ zurück"""
        icons = {
            'embroidery': '🧵',
            'print': '🖨️',
            'dtf': '🎨'
        }
        return icons.get(self.design_type, '📄')
    
    @property
    def type_display(self):
        """Gibt deutschen Namen für Design-Typ zurück"""
        types = {
            'embroidery': 'Stickerei',
            'print': 'Druck',
            'dtf': 'DTF'
        }
        return types.get(self.design_type, self.design_type)
    
    @property
    def status_display(self):
        """Gibt deutschen Namen für Status zurück"""
        statuses = {
            'draft': 'Entwurf',
            'active': 'Aktiv',
            'archived': 'Archiviert',
            'needs_revision': 'Überarbeitung nötig'
        }
        return statuses.get(self.status, self.status)
    
    @property
    def status_color(self):
        """Gibt Bootstrap-Farbe für Status zurück"""
        colors = {
            'draft': 'secondary',
            'active': 'success',
            'archived': 'dark',
            'needs_revision': 'warning'
        }
        return colors.get(self.status, 'secondary')
    
    def __repr__(self):
        return f'<Design {self.design_number}: {self.name}>'


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
    file_name = db.Column(db.String(255))
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
    
    def get_technical_data(self):
        """Gibt technische Daten als Dict zurück"""
        if self.technical_data:
            try:
                return json.loads(self.technical_data)
            except:
                return {}
        return {}
    
    def set_technical_data(self, data):
        """Setzt technische Daten aus Dict"""
        self.technical_data = json.dumps(data, ensure_ascii=False)
    
    def __repr__(self):
        return f'<DesignVersion {self.design_id} v{self.version_number}>'


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
    order_item = db.relationship('OrderItem', backref='design_usages')
    
    def get_color_adjustments(self):
        """Gibt Farbanpassungen als Liste zurück"""
        if self.color_adjustments:
            try:
                return json.loads(self.color_adjustments)
            except:
                return []
        return []
    
    def __repr__(self):
        return f'<DesignUsage {self.design_id} -> {self.order_id}>'


class ThreadBrand(db.Model):
    """Garn-Marken (Madeira, Polystar, etc.)"""
    __tablename__ = 'thread_brands'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    short_code = db.Column(db.String(10))  # MA, PO, etc.
    website = db.Column(db.String(200))
    notes = db.Column(db.Text)
    is_default = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    colors = db.relationship('ThreadColor', back_populates='brand', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<ThreadBrand {self.name}>'


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
    is_neon = db.Column(db.Boolean, default=False)
    
    # Lagerbestand (optional)
    stock_quantity = db.Column(db.Integer, default=0)
    min_stock = db.Column(db.Integer, default=1)
    location = db.Column(db.String(100))  # Lagerort
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_favorite = db.Column(db.Boolean, default=False)
    
    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    brand = db.relationship('ThreadBrand', back_populates='colors')
    
    # Unique Constraint
    __table_args__ = (
        db.UniqueConstraint('brand_id', 'color_code', name='unique_brand_color'),
    )
    
    @property
    def full_name(self):
        """Voller Name mit Marke"""
        if self.brand:
            return f"{self.brand.short_code or self.brand.name} {self.color_code}"
        return self.color_code
    
    @property
    def display_name(self):
        """Anzeigename"""
        if self.color_name:
            return f"{self.full_name} - {self.color_name}"
        return self.full_name
    
    @property
    def is_low_stock(self):
        """Prüft ob Bestand niedrig ist"""
        return self.stock_quantity < self.min_stock
    
    def set_rgb_from_hex(self, hex_color):
        """Setzt RGB-Werte aus Hex-Code"""
        if hex_color and hex_color.startswith('#') and len(hex_color) == 7:
            self.rgb_hex = hex_color
            self.rgb_r = int(hex_color[1:3], 16)
            self.rgb_g = int(hex_color[3:5], 16)
            self.rgb_b = int(hex_color[5:7], 16)
    
    def __repr__(self):
        return f'<ThreadColor {self.full_name}>'


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
    customer_id = db.Column(db.String(50), db.ForeignKey('customers.id'))  # Für wen ist das Design
    
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
    print_method = db.Column(db.String(50))  # siebdruck, digital, transfer, dtf
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
    source_file_name = db.Column(db.String(255))
    source_file_type = db.Column(db.String(50))  # jpg, png, pdf, ai, sketch
    
    # Referenz-Bilder (JSON Array)
    reference_images = db.Column(db.Text)
    
    # Textuelle Beschreibung
    special_requirements = db.Column(db.Text)
    
    # ═══════════════════════════════════════════════════════════════
    # STATUS & WORKFLOW
    # ═══════════════════════════════════════════════════════════════
    
    status = db.Column(db.String(50), default='draft')
    # draft, sent, quoted, accepted, deposit_pending, deposit_paid, 
    # in_progress, delivered, received, revision_requested, completed, cancelled
    
    # Anfrage
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    request_sent_at = db.Column(db.DateTime)
    request_sent_to = db.Column(db.String(200))  # E-Mail-Adresse
    
    # Angebot
    quote_received_at = db.Column(db.DateTime)
    quote_price = db.Column(db.Float)
    quote_delivery_days = db.Column(db.Integer)
    quote_notes = db.Column(db.Text)
    quote_valid_until = db.Column(db.Date)
    quote_accepted_at = db.Column(db.DateTime)
    
    # Anzahlung
    deposit_required = db.Column(db.Boolean, default=False)
    deposit_percent = db.Column(db.Float)
    deposit_amount = db.Column(db.Float)
    deposit_status = db.Column(db.String(50))  # pending, paid
    deposit_paid_at = db.Column(db.DateTime)
    
    # Bestellung
    ordered_at = db.Column(db.DateTime)
    expected_delivery = db.Column(db.Date)
    
    # Lieferung
    delivered_at = db.Column(db.DateTime)
    delivered_file_path = db.Column(db.String(500))
    delivered_file_name = db.Column(db.String(255))
    delivered_preview_path = db.Column(db.String(500))
    
    # Qualitätsprüfung
    review_status = db.Column(db.String(50))  # pending, approved, revision_needed
    review_date = db.Column(db.DateTime)
    review_notes = db.Column(db.Text)
    revision_count = db.Column(db.Integer, default=0)
    
    # Abschluss
    completed_at = db.Column(db.DateTime)
    final_design_id = db.Column(db.String(50))  # Verknüpfung zum erstellten Design
    
    # Kosten
    total_price = db.Column(db.Float)
    payment_status = db.Column(db.String(50))  # pending, partial, paid
    paid_at = db.Column(db.DateTime)
    
    # ═══════════════════════════════════════════════════════════════
    # PDF-BEAUFTRAGUNG
    # ═══════════════════════════════════════════════════════════════
    
    # Generierte PDF
    order_pdf_path = db.Column(db.String(500))
    order_pdf_generated_at = db.Column(db.DateTime)
    
    # ═══════════════════════════════════════════════════════════════
    # SONSTIGES
    # ═══════════════════════════════════════════════════════════════
    
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    internal_notes = db.Column(db.Text)
    communication_log = db.Column(db.Text)  # JSON Array
    
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
    
    order = db.relationship('Order', backref='external_design_orders')
    design = db.relationship('Design', backref='revision_orders', foreign_keys=[design_id])
    supplier = db.relationship('Supplier', backref='design_orders_received')
    customer = db.relationship('Customer', backref='design_orders')
    
    # ═══════════════════════════════════════════════════════════════
    # METHODEN
    # ═══════════════════════════════════════════════════════════════
    
    def get_requested_thread_colors(self):
        """Gibt angeforderte Garnfarben als Liste zurück"""
        if self.requested_thread_colors:
            try:
                return json.loads(self.requested_thread_colors)
            except:
                return []
        return []
    
    def set_requested_thread_colors(self, colors):
        """Setzt angeforderte Garnfarben"""
        self.requested_thread_colors = json.dumps(colors, ensure_ascii=False)
    
    def get_requested_print_colors(self):
        """Gibt angeforderte Druckfarben als Liste zurück"""
        if self.requested_print_colors:
            try:
                return json.loads(self.requested_print_colors)
            except:
                return []
        return []
    
    def set_requested_print_colors(self, colors):
        """Setzt angeforderte Druckfarben"""
        self.requested_print_colors = json.dumps(colors, ensure_ascii=False)
    
    def get_reference_images(self):
        """Gibt Referenzbilder als Liste zurück"""
        if self.reference_images:
            try:
                return json.loads(self.reference_images)
            except:
                return []
        return []
    
    def add_reference_image(self, path, description=''):
        """Fügt Referenzbild hinzu"""
        images = self.get_reference_images()
        images.append({
            'path': path,
            'description': description,
            'added_at': datetime.utcnow().isoformat()
        })
        self.reference_images = json.dumps(images, ensure_ascii=False)
    
    def get_communication_log(self):
        """Gibt Kommunikationslog als Liste zurück"""
        if self.communication_log:
            try:
                return json.loads(self.communication_log)
            except:
                return []
        return []
    
    def add_communication(self, message, comm_type='note', sender='system'):
        """Fügt Kommunikationseintrag hinzu"""
        log = self.get_communication_log()
        log.append({
            'type': comm_type,  # note, email_sent, email_received, call, etc.
            'message': message,
            'sender': sender,
            'timestamp': datetime.utcnow().isoformat()
        })
        self.communication_log = json.dumps(log, ensure_ascii=False)
    
    @property
    def type_icon(self):
        """Gibt passendes Icon für Design-Typ zurück"""
        icons = {
            'embroidery': '🧵',
            'print': '🖨️',
            'dtf': '🎨'
        }
        return icons.get(self.design_type, '📄')
    
    @property
    def type_display(self):
        """Gibt deutschen Namen für Design-Typ zurück"""
        types = {
            'embroidery': 'Stickprogramm',
            'print': 'Druckdatei',
            'dtf': 'DTF-Design'
        }
        return types.get(self.design_type, self.design_type)
    
    @property
    def status_display(self):
        """Gibt deutschen Namen für Status zurück"""
        statuses = {
            'draft': 'Entwurf',
            'sent': 'Angefragt',
            'quoted': 'Angebot erhalten',
            'accepted': 'Angenommen',
            'deposit_pending': 'Warte auf Anzahlung',
            'deposit_paid': 'Anzahlung bezahlt',
            'in_progress': 'In Bearbeitung',
            'delivered': 'Geliefert',
            'received': 'Eingegangen',
            'revision_requested': 'Überarbeitung angefordert',
            'completed': 'Abgeschlossen',
            'cancelled': 'Storniert'
        }
        return statuses.get(self.status, self.status)
    
    @property
    def status_color(self):
        """Gibt Bootstrap-Farbe für Status zurück"""
        colors = {
            'draft': 'secondary',
            'sent': 'info',
            'quoted': 'primary',
            'accepted': 'primary',
            'deposit_pending': 'warning',
            'deposit_paid': 'info',
            'in_progress': 'info',
            'delivered': 'success',
            'received': 'success',
            'revision_requested': 'warning',
            'completed': 'success',
            'cancelled': 'danger'
        }
        return colors.get(self.status, 'secondary')
    
    @property
    def priority_display(self):
        """Gibt deutschen Namen für Priorität zurück"""
        priorities = {
            'low': 'Niedrig',
            'normal': 'Normal',
            'high': 'Hoch',
            'urgent': 'Eilig'
        }
        return priorities.get(self.priority, self.priority)
    
    @property
    def priority_color(self):
        """Gibt Bootstrap-Farbe für Priorität zurück"""
        colors = {
            'low': 'secondary',
            'normal': 'primary',
            'high': 'warning',
            'urgent': 'danger'
        }
        return colors.get(self.priority, 'secondary')
    
    @property
    def is_overdue(self):
        """Prüft ob Lieferung überfällig ist"""
        if self.expected_delivery and self.status not in ('delivered', 'received', 'completed', 'cancelled'):
            from datetime import date
            return self.expected_delivery < date.today()
        return False
    
    def __repr__(self):
        return f'<DesignOrder {self.design_order_number}: {self.design_name}>'
