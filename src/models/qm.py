# -*- coding: utf-8 -*-
"""
QM (Qualitätsmanagement) Models
===============================
Vollständiges QM-System mit Checklisten, Prüfungen und Mängelverwaltung

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime
from enum import Enum
import json
from src.models.models import db


class QCChecklistType(Enum):
    """Typen von QM-Checklisten"""
    EMBROIDERY = 'embroidery'
    PRINTING = 'printing'
    DTF = 'dtf'
    INCOMING_GOODS = 'incoming_goods'
    OUTGOING_GOODS = 'outgoing_goods'
    PRODUCTION = 'production'
    CUSTOM = 'custom'


class QCStatus(Enum):
    """QM-Prüfungsstatus"""
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    PASSED = 'passed'
    FAILED = 'failed'
    PASSED_WITH_REMARKS = 'passed_with_remarks'
    REWORK_REQUIRED = 'rework_required'


class DefectSeverity(Enum):
    """Schweregrad von Mängeln"""
    MINOR = 'minor'           # Kleiner Mangel, akzeptabel
    MAJOR = 'major'           # Größerer Mangel, muss dokumentiert werden
    CRITICAL = 'critical'     # Kritischer Mangel, nicht lieferbar
    COSMETIC = 'cosmetic'     # Nur optisch, Kunde entscheidet


class DefectCategory(Enum):
    """Mängelkategorien"""
    THREAD_BREAK = 'thread_break'
    COLOR_DEVIATION = 'color_deviation'
    POSITION_ERROR = 'position_error'
    SIZE_ERROR = 'size_error'
    MATERIAL_DAMAGE = 'material_damage'
    STITCH_ERROR = 'stitch_error'
    PRINT_DEFECT = 'print_defect'
    WRONG_ARTICLE = 'wrong_article'
    MISSING_ITEM = 'missing_item'
    PACKAGING_DAMAGE = 'packaging_damage'
    OTHER = 'other'


class QCChecklist(db.Model):
    """
    QM-Checklisten-Vorlagen
    
    Definiert die Prüfpunkte für verschiedene Prüfungstypen
    """
    __tablename__ = 'qc_checklists'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    checklist_type = db.Column(db.Enum(QCChecklistType), nullable=False)
    
    # Prüfpunkte als JSON
    # Format: [{"id": 1, "name": "...", "description": "...", "required": true, "category": "..."}]
    items = db.Column(db.Text, nullable=False, default='[]')
    
    # Einstellungen
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)
    requires_photos = db.Column(db.Boolean, default=False)
    requires_signature = db.Column(db.Boolean, default=False)
    min_pass_percentage = db.Column(db.Float, default=100.0)  # % der Punkte die bestanden werden müssen
    
    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    inspections = db.relationship('QCInspection', backref='checklist', lazy='dynamic')
    
    def get_items(self):
        """Gibt Prüfpunkte als Liste zurück"""
        try:
            return json.loads(self.items) if self.items else []
        except:
            return []
    
    def set_items(self, items_list):
        """Speichert Prüfpunkte als JSON"""
        self.items = json.dumps(items_list, ensure_ascii=False)
    
    def add_item(self, name, description='', required=True, category='general'):
        """Fügt einen Prüfpunkt hinzu"""
        items = self.get_items()
        new_id = max([i.get('id', 0) for i in items], default=0) + 1
        items.append({
            'id': new_id,
            'name': name,
            'description': description,
            'required': required,
            'category': category
        })
        self.set_items(items)
        return new_id
    
    @classmethod
    def get_default_for_type(cls, checklist_type: QCChecklistType):
        """Holt die Standard-Checkliste für einen Typ"""
        return cls.query.filter_by(
            checklist_type=checklist_type,
            is_default=True,
            is_active=True
        ).first()
    
    @classmethod
    def create_default_checklists(cls):
        """Erstellt Standard-Checklisten"""
        defaults = [
            {
                'name': 'Stickerei-Prüfung',
                'type': QCChecklistType.EMBROIDERY,
                'items': [
                    {'id': 1, 'name': 'Stichbild kontrollieren', 'description': 'Keine Fadenbrüche, gleichmäßige Stiche', 'required': True, 'category': 'quality'},
                    {'id': 2, 'name': 'Farbabgleich', 'description': 'Farben entsprechen Freigabe', 'required': True, 'category': 'color'},
                    {'id': 3, 'name': 'Position prüfen', 'description': 'Position wie in Freigabe definiert', 'required': True, 'category': 'position'},
                    {'id': 4, 'name': 'Größe messen', 'description': 'Maße entsprechen Vorgabe (±2mm)', 'required': True, 'category': 'size'},
                    {'id': 5, 'name': 'Vlies entfernen', 'description': 'Stickvlies sauber entfernt', 'required': True, 'category': 'finish'},
                    {'id': 6, 'name': 'Fäden abschneiden', 'description': 'Keine überstehenden Fäden', 'required': True, 'category': 'finish'},
                    {'id': 7, 'name': 'Rückseite kontrollieren', 'description': 'Rückseite sauber, keine Schlaufen', 'required': False, 'category': 'quality'},
                    {'id': 8, 'name': 'Textil unbeschädigt', 'description': 'Kein Loch, keine Flecken', 'required': True, 'category': 'material'},
                ]
            },
            {
                'name': 'Druck-Prüfung',
                'type': QCChecklistType.PRINTING,
                'items': [
                    {'id': 1, 'name': 'Druckbild scharf', 'description': 'Keine unscharfen Kanten', 'required': True, 'category': 'quality'},
                    {'id': 2, 'name': 'Farbdeckung', 'description': 'Vollständige Farbdeckung, keine Lücken', 'required': True, 'category': 'color'},
                    {'id': 3, 'name': 'Ausrichtung', 'description': 'Druck gerade und mittig', 'required': True, 'category': 'position'},
                    {'id': 4, 'name': 'Haftung prüfen', 'description': 'Druck löst sich nicht', 'required': True, 'category': 'quality'},
                    {'id': 5, 'name': 'Keine Farbspritzer', 'description': 'Keine ungewollten Farbpunkte', 'required': True, 'category': 'finish'},
                ]
            },
            {
                'name': 'Wareneingang',
                'type': QCChecklistType.INCOMING_GOODS,
                'items': [
                    {'id': 1, 'name': 'Lieferschein prüfen', 'description': 'Stimmt mit Bestellung überein', 'required': True, 'category': 'documentation'},
                    {'id': 2, 'name': 'Menge zählen', 'description': 'Stückzahl korrekt', 'required': True, 'category': 'quantity'},
                    {'id': 3, 'name': 'Artikelnummer prüfen', 'description': 'Richtige Artikel geliefert', 'required': True, 'category': 'article'},
                    {'id': 4, 'name': 'Farbe/Größe prüfen', 'description': 'Farbe und Größe wie bestellt', 'required': True, 'category': 'article'},
                    {'id': 5, 'name': 'Zustand prüfen', 'description': 'Keine Transportschäden', 'required': True, 'category': 'condition'},
                    {'id': 6, 'name': 'Sauberkeit', 'description': 'Keine Flecken oder Verunreinigungen', 'required': False, 'category': 'condition'},
                ]
            },
            {
                'name': 'Warenausgang',
                'type': QCChecklistType.OUTGOING_GOODS,
                'items': [
                    {'id': 1, 'name': 'Stückzahl prüfen', 'description': 'Alle Artikel vorhanden', 'required': True, 'category': 'quantity'},
                    {'id': 2, 'name': 'Qualität final prüfen', 'description': 'Nochmalige Sichtkontrolle', 'required': True, 'category': 'quality'},
                    {'id': 3, 'name': 'Lieferschein beilegen', 'description': 'Lieferschein im Paket', 'required': True, 'category': 'documentation'},
                    {'id': 4, 'name': 'Sauber verpackt', 'description': 'Ordentliche Verpackung', 'required': True, 'category': 'packaging'},
                    {'id': 5, 'name': 'Karton beschriftet', 'description': 'Adresse korrekt', 'required': True, 'category': 'packaging'},
                ]
            }
        ]
        
        for checklist_data in defaults:
            existing = cls.query.filter_by(
                name=checklist_data['name'],
                checklist_type=checklist_data['type']
            ).first()
            
            if not existing:
                checklist = cls(
                    name=checklist_data['name'],
                    checklist_type=checklist_data['type'],
                    is_default=True,
                    is_active=True,
                    created_by='system'
                )
                checklist.set_items(checklist_data['items'])
                db.session.add(checklist)
        
        db.session.commit()
    
    def __repr__(self):
        return f'<QCChecklist {self.name}>'


class QCInspection(db.Model):
    """
    QM-Prüfung
    
    Eine konkrete Prüfung eines Auftrags/Packliste/etc.
    """
    __tablename__ = 'qc_inspections'
    
    id = db.Column(db.Integer, primary_key=True)
    inspection_number = db.Column(db.String(50), unique=True)
    
    # Verknüpfungen
    order_id = db.Column(db.String(50), db.ForeignKey('orders.id'))
    packing_list_id = db.Column(db.Integer, db.ForeignKey('packing_lists.id'))
    checklist_id = db.Column(db.Integer, db.ForeignKey('qc_checklists.id'))
    
    # Status
    status = db.Column(db.Enum(QCStatus), default=QCStatus.PENDING)
    
    # Ergebnisse als JSON
    # Format: {"item_id": {"passed": true/false, "notes": "...", "photo": "..."}}
    results = db.Column(db.Text, default='{}')
    
    # Zusammenfassung
    total_items = db.Column(db.Integer, default=0)
    passed_items = db.Column(db.Integer, default=0)
    failed_items = db.Column(db.Integer, default=0)
    pass_percentage = db.Column(db.Float, default=0.0)
    
    # Prüfer-Info
    inspector_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    inspector_name = db.Column(db.String(100))
    inspector_signature = db.Column(db.Text)  # Base64
    
    # Zeiten
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Integer)
    
    # Fotos (JSON Array)
    photos = db.Column(db.Text, default='[]')
    
    # Notizen
    notes = db.Column(db.Text)
    internal_notes = db.Column(db.Text)
    
    # Bei Nacharbeit
    requires_rework = db.Column(db.Boolean, default=False)
    rework_description = db.Column(db.Text)
    rework_completed_at = db.Column(db.DateTime)
    rework_by = db.Column(db.String(80))
    
    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    
    # Relationships
    order = db.relationship('Order', backref=db.backref('qc_inspections', lazy='dynamic'))
    packing_list = db.relationship('PackingList', backref=db.backref('qc_inspections', lazy='dynamic'))
    defects = db.relationship('QCDefect', backref='inspection', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_results(self):
        """Gibt Prüfergebnisse als Dict zurück"""
        try:
            return json.loads(self.results) if self.results else {}
        except:
            return {}
    
    def set_results(self, results_dict):
        """Speichert Prüfergebnisse als JSON"""
        self.results = json.dumps(results_dict, ensure_ascii=False)
    
    def get_photos(self):
        """Gibt Fotos als Liste zurück"""
        try:
            return json.loads(self.photos) if self.photos else []
        except:
            return []
    
    def add_photo(self, path, description='', item_id=None):
        """Fügt ein Foto hinzu"""
        photos = self.get_photos()
        photos.append({
            'path': path,
            'description': description,
            'item_id': item_id,
            'timestamp': datetime.now().isoformat()
        })
        self.photos = json.dumps(photos, ensure_ascii=False)
    
    def record_result(self, item_id: int, passed: bool, notes: str = '', photo: str = None):
        """Erfasst das Ergebnis für einen Prüfpunkt"""
        results = self.get_results()
        results[str(item_id)] = {
            'passed': passed,
            'notes': notes,
            'photo': photo,
            'checked_at': datetime.now().isoformat()
        }
        self.set_results(results)
        
        # Aktualisiere Statistiken
        self._update_statistics()
    
    def _update_statistics(self):
        """Aktualisiert die Zusammenfassungs-Statistiken"""
        results = self.get_results()
        
        self.total_items = len(results)
        self.passed_items = sum(1 for r in results.values() if r.get('passed', False))
        self.failed_items = self.total_items - self.passed_items
        
        if self.total_items > 0:
            self.pass_percentage = (self.passed_items / self.total_items) * 100
        else:
            self.pass_percentage = 0.0
    
    def start_inspection(self, inspector_name: str):
        """Startet die Prüfung"""
        self.status = QCStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()
        self.inspector_name = inspector_name
    
    def complete_inspection(self, signature: str = None):
        """Schließt die Prüfung ab"""
        self._update_statistics()
        
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.duration_minutes = int((self.completed_at - self.started_at).total_seconds() / 60)
        
        if signature:
            self.inspector_signature = signature
        
        # Status basierend auf Ergebnis
        if self.checklist:
            min_pass = self.checklist.min_pass_percentage
        else:
            min_pass = 100.0
        
        # Prüfe auf kritische Mängel
        has_critical = self.defects.filter_by(severity=DefectSeverity.CRITICAL).count() > 0
        
        if has_critical:
            self.status = QCStatus.FAILED
            self.requires_rework = True
        elif self.pass_percentage >= min_pass:
            if self.failed_items > 0:
                self.status = QCStatus.PASSED_WITH_REMARKS
            else:
                self.status = QCStatus.PASSED
        else:
            self.status = QCStatus.FAILED
            self.requires_rework = True
    
    def add_defect(self, category: DefectCategory, severity: DefectSeverity,
                   description: str, item_id: int = None, photo: str = None):
        """Fügt einen Mangel hinzu"""
        defect = QCDefect(
            inspection_id=self.id,
            category=category,
            severity=severity,
            description=description,
            checklist_item_id=item_id,
            photo=photo,
            created_by=self.inspector_name
        )
        db.session.add(defect)
        return defect
    
    @classmethod
    def generate_inspection_number(cls):
        """Generiert eine eindeutige Prüfnummer"""
        today = datetime.now()
        prefix = f"QC{today.year}{today.month:02d}"
        
        count = cls.query.filter(
            cls.inspection_number.like(f"{prefix}%")
        ).count()
        
        return f"{prefix}-{count + 1:04d}"
    
    @classmethod
    def create_for_order(cls, order, checklist_type: QCChecklistType = None, created_by: str = 'system'):
        """Erstellt eine Prüfung für einen Auftrag"""
        # Bestimme Checklisten-Typ
        if not checklist_type:
            if order.order_type == 'embroidery':
                checklist_type = QCChecklistType.EMBROIDERY
            elif order.order_type == 'printing':
                checklist_type = QCChecklistType.PRINTING
            elif order.order_type == 'dtf':
                checklist_type = QCChecklistType.DTF
            else:
                checklist_type = QCChecklistType.PRODUCTION
        
        # Hole Standard-Checkliste
        checklist = QCChecklist.get_default_for_type(checklist_type)
        
        inspection = cls(
            inspection_number=cls.generate_inspection_number(),
            order_id=order.id,
            checklist_id=checklist.id if checklist else None,
            status=QCStatus.PENDING,
            created_by=created_by
        )
        
        db.session.add(inspection)
        return inspection
    
    def __repr__(self):
        return f'<QCInspection {self.inspection_number}>'


class QCDefect(db.Model):
    """
    QM-Mängel
    
    Dokumentiert gefundene Mängel bei Prüfungen
    """
    __tablename__ = 'qc_defects'
    
    id = db.Column(db.Integer, primary_key=True)
    inspection_id = db.Column(db.Integer, db.ForeignKey('qc_inspections.id'), nullable=False)
    
    # Kategorisierung
    category = db.Column(db.Enum(DefectCategory), nullable=False)
    severity = db.Column(db.Enum(DefectSeverity), nullable=False)
    
    # Details
    description = db.Column(db.Text, nullable=False)
    checklist_item_id = db.Column(db.Integer)  # Bezug zum Prüfpunkt
    photo = db.Column(db.String(255))  # Foto-Pfad
    
    # Position (falls relevant)
    position_description = db.Column(db.String(200))  # z.B. "Brust links, 3cm von Kante"
    article_number = db.Column(db.String(100))  # Betroffener Artikel
    quantity_affected = db.Column(db.Integer, default=1)  # Anzahl betroffener Stücke
    
    # Maßnahme
    action_taken = db.Column(db.Text)  # Was wurde unternommen
    action_by = db.Column(db.String(80))
    action_at = db.Column(db.DateTime)
    
    # Status
    is_resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime)
    resolved_by = db.Column(db.String(80))
    resolution_notes = db.Column(db.Text)
    
    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    
    def resolve(self, resolution_notes: str, resolved_by: str):
        """Markiert Mangel als behoben"""
        self.is_resolved = True
        self.resolved_at = datetime.utcnow()
        self.resolved_by = resolved_by
        self.resolution_notes = resolution_notes
    
    def get_severity_label(self):
        """Gibt Schweregrad als deutschen Text zurück"""
        labels = {
            DefectSeverity.MINOR: 'Geringfügig',
            DefectSeverity.MAJOR: 'Erheblich',
            DefectSeverity.CRITICAL: 'Kritisch',
            DefectSeverity.COSMETIC: 'Optisch'
        }
        return labels.get(self.severity, self.severity.value)
    
    def get_severity_color(self):
        """Gibt Bootstrap-Farbe für Schweregrad zurück"""
        colors = {
            DefectSeverity.MINOR: 'warning',
            DefectSeverity.MAJOR: 'orange',
            DefectSeverity.CRITICAL: 'danger',
            DefectSeverity.COSMETIC: 'info'
        }
        return colors.get(self.severity, 'secondary')
    
    def get_category_label(self):
        """Gibt Kategorie als deutschen Text zurück"""
        labels = {
            DefectCategory.THREAD_BREAK: 'Fadenbruch',
            DefectCategory.COLOR_DEVIATION: 'Farbabweichung',
            DefectCategory.POSITION_ERROR: 'Positionsfehler',
            DefectCategory.SIZE_ERROR: 'Größenfehler',
            DefectCategory.MATERIAL_DAMAGE: 'Materialschaden',
            DefectCategory.STITCH_ERROR: 'Stichfehler',
            DefectCategory.PRINT_DEFECT: 'Druckfehler',
            DefectCategory.WRONG_ARTICLE: 'Falscher Artikel',
            DefectCategory.MISSING_ITEM: 'Fehlender Artikel',
            DefectCategory.PACKAGING_DAMAGE: 'Verpackungsschaden',
            DefectCategory.OTHER: 'Sonstiges'
        }
        return labels.get(self.category, self.category.value)
    
    def __repr__(self):
        return f'<QCDefect {self.id}: {self.category.value} ({self.severity.value})>'


class QCRework(db.Model):
    """
    Nacharbeits-Aufträge
    
    Verwaltet Nacharbeiten nach fehlgeschlagener QM-Prüfung
    """
    __tablename__ = 'qc_reworks'
    
    id = db.Column(db.Integer, primary_key=True)
    rework_number = db.Column(db.String(50), unique=True)
    
    # Verknüpfungen
    inspection_id = db.Column(db.Integer, db.ForeignKey('qc_inspections.id'), nullable=False)
    order_id = db.Column(db.String(50), db.ForeignKey('orders.id'))
    
    # Status
    status = db.Column(db.String(50), default='pending')  # pending, in_progress, completed, cancelled
    
    # Beschreibung
    description = db.Column(db.Text, nullable=False)
    defects_to_fix = db.Column(db.Text)  # JSON: Liste der Mangel-IDs
    
    # Priorität
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    
    # Zuständigkeit
    assigned_to = db.Column(db.String(80))
    assigned_machine_id = db.Column(db.String(50), db.ForeignKey('machines.id'))
    
    # Zeiten
    due_date = db.Column(db.DateTime)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    estimated_minutes = db.Column(db.Integer)
    actual_minutes = db.Column(db.Integer)
    
    # Ergebnis
    result_notes = db.Column(db.Text)
    retest_required = db.Column(db.Boolean, default=True)
    retest_inspection_id = db.Column(db.Integer, db.ForeignKey('qc_inspections.id'))
    
    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    
    # Relationships
    inspection = db.relationship('QCInspection', backref='rework_orders', foreign_keys=[inspection_id])
    retest_inspection = db.relationship('QCInspection', foreign_keys=[retest_inspection_id])
    order = db.relationship('Order', backref='rework_orders')
    
    def start(self, worker: str):
        """Startet Nacharbeit"""
        self.status = 'in_progress'
        self.started_at = datetime.utcnow()
        self.assigned_to = worker
    
    def complete(self, result_notes: str, worker: str):
        """Schließt Nacharbeit ab"""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        self.result_notes = result_notes
        
        if self.started_at:
            self.actual_minutes = int((self.completed_at - self.started_at).total_seconds() / 60)
    
    @classmethod
    def generate_rework_number(cls):
        """Generiert eindeutige Nacharbeits-Nummer"""
        today = datetime.now()
        prefix = f"RW{today.year}{today.month:02d}"
        
        count = cls.query.filter(
            cls.rework_number.like(f"{prefix}%")
        ).count()
        
        return f"{prefix}-{count + 1:04d}"
    
    @classmethod
    def create_from_inspection(cls, inspection: QCInspection, created_by: str):
        """Erstellt Nacharbeits-Auftrag aus fehlgeschlagener Prüfung"""
        # Sammle fehlgeschlagene Mängel
        critical_defects = inspection.defects.filter(
            QCDefect.severity.in_([DefectSeverity.CRITICAL, DefectSeverity.MAJOR])
        ).all()
        
        defect_ids = [d.id for d in critical_defects]
        
        description_parts = ["Nacharbeit erforderlich aufgrund folgender Mängel:"]
        for defect in critical_defects:
            description_parts.append(f"- {defect.get_category_label()}: {defect.description}")
        
        rework = cls(
            rework_number=cls.generate_rework_number(),
            inspection_id=inspection.id,
            order_id=inspection.order_id,
            description='\n'.join(description_parts),
            defects_to_fix=json.dumps(defect_ids),
            priority='high' if any(d.severity == DefectSeverity.CRITICAL for d in critical_defects) else 'normal',
            created_by=created_by
        )
        
        db.session.add(rework)
        return rework
    
    def __repr__(self):
        return f'<QCRework {self.rework_number}>'


class QCStatistics(db.Model):
    """
    QM-Statistiken (täglich aggregiert)
    """
    __tablename__ = 'qc_statistics'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    
    # Prüfungen
    total_inspections = db.Column(db.Integer, default=0)
    passed_inspections = db.Column(db.Integer, default=0)
    failed_inspections = db.Column(db.Integer, default=0)
    pass_rate = db.Column(db.Float, default=0.0)
    
    # Mängel
    total_defects = db.Column(db.Integer, default=0)
    critical_defects = db.Column(db.Integer, default=0)
    resolved_defects = db.Column(db.Integer, default=0)
    
    # Nacharbeiten
    reworks_created = db.Column(db.Integer, default=0)
    reworks_completed = db.Column(db.Integer, default=0)
    avg_rework_time = db.Column(db.Float, default=0.0)
    
    # Prüfer-Zeit
    total_inspection_minutes = db.Column(db.Integer, default=0)
    avg_inspection_minutes = db.Column(db.Float, default=0.0)
    
    # Top-Mängelkategorien (JSON)
    top_defect_categories = db.Column(db.Text, default='{}')
    
    @classmethod
    def update_for_date(cls, date):
        """Aktualisiert Statistiken für ein Datum"""
        from sqlalchemy import func
        
        stats = cls.query.filter_by(date=date).first()
        if not stats:
            stats = cls(date=date)
            db.session.add(stats)
        
        # Prüfungen zählen
        inspections = QCInspection.query.filter(
            func.date(QCInspection.completed_at) == date
        ).all()
        
        stats.total_inspections = len(inspections)
        stats.passed_inspections = sum(1 for i in inspections if i.status in [QCStatus.PASSED, QCStatus.PASSED_WITH_REMARKS])
        stats.failed_inspections = sum(1 for i in inspections if i.status == QCStatus.FAILED)
        
        if stats.total_inspections > 0:
            stats.pass_rate = (stats.passed_inspections / stats.total_inspections) * 100
        
        # Mängel zählen
        defects = QCDefect.query.filter(
            func.date(QCDefect.created_at) == date
        ).all()
        
        stats.total_defects = len(defects)
        stats.critical_defects = sum(1 for d in defects if d.severity == DefectSeverity.CRITICAL)
        stats.resolved_defects = sum(1 for d in defects if d.is_resolved)
        
        # Prüfzeit
        inspection_minutes = [i.duration_minutes for i in inspections if i.duration_minutes]
        if inspection_minutes:
            stats.total_inspection_minutes = sum(inspection_minutes)
            stats.avg_inspection_minutes = sum(inspection_minutes) / len(inspection_minutes)
        
        # Top-Kategorien
        category_counts = {}
        for d in defects:
            cat = d.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Sortiere nach Häufigkeit
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        stats.top_defect_categories = json.dumps(dict(sorted_categories))
        
        db.session.commit()
        return stats
    
    def __repr__(self):
        return f'<QCStatistics {self.date}>'
