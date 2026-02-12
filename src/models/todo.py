# -*- coding: utf-8 -*-
"""
TODO / AUFGABEN Model für StitchAdmin
=====================================
Zentrale Aufgabenverwaltung für interne Workflows

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime, timedelta
from src.models.models import db
import json


class Todo(db.Model):
    """
    Zentrale Aufgaben-Tabelle
    Für: Design-Erstellung, Produktionsaufgaben, Allgemeine Aufgaben
    """
    __tablename__ = 'todos'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # ═══════════════════════════════════════════════════════════════
    # BASIS-INFORMATIONEN
    # ═══════════════════════════════════════════════════════════════
    
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Typ der Aufgabe
    todo_type = db.Column(db.String(50), default='general')
    # general, design_creation, production, quality_check, delivery, admin
    
    # Kategorie (frei wählbar)
    category = db.Column(db.String(100))
    
    # ═══════════════════════════════════════════════════════════════
    # VERKNÜPFUNGEN
    # ═══════════════════════════════════════════════════════════════
    
    # Verknüpfung zu Auftrag (optional)
    order_id = db.Column(db.String(50), db.ForeignKey('orders.id'))
    
    # Verknüpfung zu Design-Bestellung (optional)
    design_order_id = db.Column(db.String(50), db.ForeignKey('design_orders.id'))
    
    # Verknüpfung zu Kunde (optional)
    customer_id = db.Column(db.String(50), db.ForeignKey('customers.id'))
    
    # ═══════════════════════════════════════════════════════════════
    # ZUWEISUNG
    # ═══════════════════════════════════════════════════════════════
    
    # Wem ist die Aufgabe zugewiesen?
    assigned_to = db.Column(db.String(80))  # Username
    assigned_to_team = db.Column(db.String(100))  # Team/Abteilung (Grafik, Produktion, etc.)
    
    # Wer hat sie erstellt?
    created_by = db.Column(db.String(80))
    
    # ═══════════════════════════════════════════════════════════════
    # ZEITPLANUNG
    # ═══════════════════════════════════════════════════════════════
    
    # Fälligkeitsdatum
    due_date = db.Column(db.Date)
    due_time = db.Column(db.Time)
    
    # Erinnerung
    reminder_at = db.Column(db.DateTime)
    reminder_sent = db.Column(db.Boolean, default=False)
    
    # Geschätzte Dauer (Minuten)
    estimated_minutes = db.Column(db.Integer)
    
    # ═══════════════════════════════════════════════════════════════
    # STATUS & PRIORITÄT
    # ═══════════════════════════════════════════════════════════════
    
    status = db.Column(db.String(50), default='open')
    # open, in_progress, waiting, completed, cancelled
    
    priority = db.Column(db.String(20), default='normal')
    # low, normal, high, urgent
    
    # Fortschritt (0-100%)
    progress = db.Column(db.Integer, default=0)
    
    # ═══════════════════════════════════════════════════════════════
    # ANHÄNGE & DOKUMENTE
    # ═══════════════════════════════════════════════════════════════
    
    # Auftragszettel/Dokument (PDF-Pfad)
    document_path = db.Column(db.String(500))
    document_name = db.Column(db.String(255))
    
    # Zusätzliche Anhänge (JSON Array)
    attachments = db.Column(db.Text)  # [{"path": "...", "name": "...", "type": "..."}]
    
    # ═══════════════════════════════════════════════════════════════
    # DESIGN-SPEZIFISCH
    # ═══════════════════════════════════════════════════════════════
    
    # Für Design-Aufgaben: Spezifikationen
    design_type = db.Column(db.String(50))  # embroidery, print, dtf
    design_width_mm = db.Column(db.Float)
    design_height_mm = db.Column(db.Float)
    max_stitch_count = db.Column(db.Integer)
    max_colors = db.Column(db.Integer)
    fabric_type = db.Column(db.String(100))
    
    # Quell-Datei (Kundenvorlage)
    source_file_path = db.Column(db.String(500))
    source_file_name = db.Column(db.String(255))
    
    # Zusätzliche Design-Infos (JSON)
    design_specs = db.Column(db.Text)
    
    # ═══════════════════════════════════════════════════════════════
    # ABSCHLUSS
    # ═══════════════════════════════════════════════════════════════
    
    completed_at = db.Column(db.DateTime)
    completed_by = db.Column(db.String(80))
    completion_notes = db.Column(db.Text)
    
    # Ergebnis-Datei (bei Design-Aufgaben)
    result_file_path = db.Column(db.String(500))
    result_file_name = db.Column(db.String(255))
    
    # ═══════════════════════════════════════════════════════════════
    # NOTIZEN & KOMMENTARE
    # ═══════════════════════════════════════════════════════════════
    
    notes = db.Column(db.Text)
    
    # Kommentar-Verlauf (JSON Array)
    comments = db.Column(db.Text)
    # [{"user": "...", "text": "...", "timestamp": "..."}]
    
    # ═══════════════════════════════════════════════════════════════
    # METADATEN
    # ═══════════════════════════════════════════════════════════════
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # ═══════════════════════════════════════════════════════════════
    # RELATIONSHIPS
    # ═══════════════════════════════════════════════════════════════
    
    order = db.relationship('Order', backref='todos')
    design_order = db.relationship('DesignOrder', backref='todos')
    customer = db.relationship('Customer', backref='todos')
    
    # ═══════════════════════════════════════════════════════════════
    # METHODEN
    # ═══════════════════════════════════════════════════════════════
    
    def get_attachments(self):
        """Gibt Anhänge als Liste zurück"""
        if self.attachments:
            try:
                return json.loads(self.attachments)
            except:
                return []
        return []
    
    def add_attachment(self, path, name, file_type=''):
        """Fügt Anhang hinzu"""
        attachments = self.get_attachments()
        attachments.append({
            'path': path,
            'name': name,
            'type': file_type,
            'added_at': datetime.utcnow().isoformat()
        })
        self.attachments = json.dumps(attachments, ensure_ascii=False)
    
    def get_comments(self):
        """Gibt Kommentare als Liste zurück"""
        if self.comments:
            try:
                return json.loads(self.comments)
            except:
                return []
        return []
    
    def add_comment(self, user, text):
        """Fügt Kommentar hinzu"""
        comments = self.get_comments()
        comments.append({
            'user': user,
            'text': text,
            'timestamp': datetime.utcnow().isoformat()
        })
        self.comments = json.dumps(comments, ensure_ascii=False)
    
    def get_design_specs(self):
        """Gibt Design-Spezifikationen als Dict zurück"""
        if self.design_specs:
            try:
                return json.loads(self.design_specs)
            except:
                return {}
        return {}
    
    def set_design_specs(self, specs):
        """Setzt Design-Spezifikationen"""
        self.design_specs = json.dumps(specs, ensure_ascii=False)
    
    def complete(self, user, notes=''):
        """Markiert Aufgabe als erledigt"""
        self.status = 'completed'
        self.progress = 100
        self.completed_at = datetime.utcnow()
        self.completed_by = user
        if notes:
            self.completion_notes = notes
    
    def start(self, user):
        """Startet die Bearbeitung"""
        self.status = 'in_progress'
        if self.progress == 0:
            self.progress = 10
        self.add_comment(user, 'Bearbeitung gestartet')
    
    @property
    def is_overdue(self):
        """Prüft ob Aufgabe überfällig ist"""
        if self.due_date and self.status not in ('completed', 'cancelled'):
            from datetime import date
            return self.due_date < date.today()
        return False
    
    @property
    def is_due_soon(self):
        """Prüft ob Aufgabe bald fällig ist (innerhalb 2 Tage)"""
        if self.due_date and self.status not in ('completed', 'cancelled'):
            from datetime import date
            return self.due_date <= date.today() + timedelta(days=2)
        return False
    
    @property
    def status_display(self):
        """Gibt deutschen Status zurück"""
        statuses = {
            'open': 'Offen',
            'in_progress': 'In Bearbeitung',
            'waiting': 'Wartend',
            'completed': 'Erledigt',
            'cancelled': 'Abgebrochen'
        }
        return statuses.get(self.status, self.status)
    
    @property
    def status_color(self):
        """Gibt Bootstrap-Farbe für Status zurück"""
        colors = {
            'open': 'secondary',
            'in_progress': 'primary',
            'waiting': 'warning',
            'completed': 'success',
            'cancelled': 'dark'
        }
        return colors.get(self.status, 'secondary')
    
    @property
    def priority_display(self):
        """Gibt deutsche Priorität zurück"""
        priorities = {
            'low': 'Niedrig',
            'normal': 'Normal',
            'high': 'Hoch',
            'urgent': 'Dringend'
        }
        return priorities.get(self.priority, self.priority)
    
    @property
    def priority_color(self):
        """Gibt Bootstrap-Farbe für Priorität zurück"""
        colors = {
            'low': 'secondary',
            'normal': 'info',
            'high': 'warning',
            'urgent': 'danger'
        }
        return colors.get(self.priority, 'secondary')
    
    @property
    def type_icon(self):
        """Gibt Icon für Aufgabentyp zurück"""
        icons = {
            'general': '📋',
            'design_creation': '🎨',
            'production': '⚙️',
            'quality_check': '✅',
            'delivery': '📦',
            'admin': '⚙️'
        }
        return icons.get(self.todo_type, '📋')
    
    @property
    def type_display(self):
        """Gibt deutschen Aufgabentyp zurück"""
        types = {
            'general': 'Allgemein',
            'design_creation': 'Design-Erstellung',
            'production': 'Produktion',
            'quality_check': 'Qualitätsprüfung',
            'delivery': 'Lieferung',
            'admin': 'Verwaltung'
        }
        return types.get(self.todo_type, self.todo_type)
    
    @classmethod
    def create_design_todo(cls, order, specs, created_by):
        """
        Erstellt eine Design-Aufgabe für interne Erstellung
        
        Args:
            order: Der Auftrag
            specs: Dict mit Design-Spezifikationen
            created_by: Username des Erstellers
        """
        todo = cls(
            title=f"Design erstellen: {order.order_number}",
            description=f"Design für Auftrag {order.order_number} erstellen",
            todo_type='design_creation',
            category='Grafik',
            order_id=order.id,
            customer_id=order.customer_id,
            assigned_to_team='Grafik',
            created_by=created_by,
            priority=specs.get('priority', 'normal'),
            
            # Design-Spezifikationen
            design_type=specs.get('design_type', 'embroidery'),
            design_width_mm=specs.get('width_mm'),
            design_height_mm=specs.get('height_mm'),
            max_stitch_count=specs.get('max_stitch_count'),
            max_colors=specs.get('max_colors'),
            fabric_type=specs.get('fabric_type'),
            source_file_path=specs.get('source_file_path'),
            source_file_name=specs.get('source_file_name'),
        )
        
        # Zusätzliche Specs als JSON
        todo.set_design_specs(specs)
        
        # Fälligkeit setzen (Standard: 3 Werktage)
        if specs.get('due_date'):
            todo.due_date = specs['due_date']
        else:
            from datetime import date
            todo.due_date = date.today() + timedelta(days=3)
        
        return todo
    
    def __repr__(self):
        return f'<Todo {self.id}: {self.title[:50]}>'


class TodoTemplate(db.Model):
    """
    Vorlagen für wiederkehrende Aufgaben
    """
    __tablename__ = 'todo_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Vorlage
    todo_type = db.Column(db.String(50), default='general')
    category = db.Column(db.String(100))
    default_title = db.Column(db.String(200))
    default_description = db.Column(db.Text)
    default_priority = db.Column(db.String(20), default='normal')
    default_team = db.Column(db.String(100))
    default_duration_days = db.Column(db.Integer, default=3)
    estimated_minutes = db.Column(db.Integer)
    
    # Checkliste (JSON Array)
    checklist = db.Column(db.Text)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    
    def get_checklist(self):
        """Gibt Checkliste als Liste zurück"""
        if self.checklist:
            try:
                return json.loads(self.checklist)
            except:
                return []
        return []
    
    def create_todo(self, order=None, created_by=None, **kwargs):
        """Erstellt TODO aus Template"""
        from datetime import date
        
        todo = Todo(
            title=kwargs.get('title', self.default_title),
            description=kwargs.get('description', self.default_description),
            todo_type=self.todo_type,
            category=self.category,
            priority=kwargs.get('priority', self.default_priority),
            assigned_to_team=self.default_team,
            estimated_minutes=self.estimated_minutes,
            created_by=created_by,
            due_date=date.today() + timedelta(days=self.default_duration_days)
        )
        
        if order:
            todo.order_id = order.id
            todo.customer_id = order.customer_id
        
        return todo
    
    def __repr__(self):
        return f'<TodoTemplate {self.name}>'
