# -*- coding: utf-8 -*-
"""
ProductionJob Model
Ermoeglicht das Aufteilen eines Auftrags in mehrere Produktionsjobs
(z.B. Stickerei, DTF, Sublimation, Druck, Laser)
"""

from datetime import datetime
from src.models import db


class ProductionJob(db.Model):
    """Einzelner Produktionsjob innerhalb eines Auftrags"""
    __tablename__ = 'production_jobs'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50), db.ForeignKey('orders.id'), nullable=False, index=True)
    job_number = db.Column(db.String(20), unique=True)
    job_type = db.Column(db.String(50), nullable=False)  # embroidery, dtf, sublimation, printing, laser
    status = db.Column(db.String(20), default='pending', index=True)  # pending, in_progress, completed, cancelled
    description = db.Column(db.Text)

    # Maschine + Zuordnung
    assigned_machine_id = db.Column(db.String(50), db.ForeignKey('machines.id'))
    assigned_to = db.Column(db.String(100))

    # Zeiterfassung
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Integer)

    # Sortierung
    sort_order = db.Column(db.Integer, default=0)

    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    notes = db.Column(db.Text)

    # Relationships
    order = db.relationship('Order', backref=db.backref('production_jobs', lazy='dynamic', cascade='all, delete-orphan'))
    machine = db.relationship('Machine')

    JOB_TYPE_LABELS = {
        'embroidery': 'Stickerei',
        'dtf': 'DTF-Druck',
        'sublimation': 'Sublimation',
        'printing': 'Druck',
        'laser': 'Laser',
        'engraving': 'Gravur',
        'cutting': 'Zuschnitt',
        'other': 'Sonstiges'
    }

    @property
    def type_label(self):
        return self.JOB_TYPE_LABELS.get(self.job_type, self.job_type)

    @property
    def status_label(self):
        labels = {
            'pending': 'Ausstehend',
            'in_progress': 'In Arbeit',
            'completed': 'Abgeschlossen',
            'cancelled': 'Abgebrochen'
        }
        return labels.get(self.status, self.status)

    @property
    def status_badge_class(self):
        classes = {
            'pending': 'bg-secondary',
            'in_progress': 'bg-warning text-dark',
            'completed': 'bg-success',
            'cancelled': 'bg-danger'
        }
        return classes.get(self.status, 'bg-secondary')

    @property
    def type_icon(self):
        icons = {
            'embroidery': 'bi-needle',
            'dtf': 'bi-printer',
            'sublimation': 'bi-thermometer-high',
            'printing': 'bi-printer-fill',
            'laser': 'bi-lightning',
            'engraving': 'bi-pencil',
            'cutting': 'bi-scissors',
            'other': 'bi-gear'
        }
        return icons.get(self.job_type, 'bi-gear')

    def start(self):
        self.status = 'in_progress'
        self.started_at = datetime.utcnow()

    def complete(self):
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_minutes = int(delta.total_seconds() / 60)

    @classmethod
    def generate_job_number(cls):
        last = cls.query.order_by(cls.id.desc()).first()
        if last and last.job_number:
            try:
                num = int(last.job_number.split('-')[1]) + 1
            except (IndexError, ValueError):
                num = 1
        else:
            num = 1
        return f'PJ-{num:04d}'
