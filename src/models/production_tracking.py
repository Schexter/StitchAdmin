"""
Produktionszeit-Tracking für lernende Kalkulation
Erfasst detaillierte Zeitdaten pro Auftrag und Position

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime, timedelta
from src.models.models import db
import json


class ProductionTimeLog(db.Model):
    """
    Detailliertes Zeitprotokoll für Produktionsschritte
    Ermöglicht lernende Kalkulation basierend auf historischen Daten
    """
    __tablename__ = 'production_time_logs'

    id = db.Column(db.Integer, primary_key=True)

    # Verknüpfungen
    order_id = db.Column(db.String(50), db.ForeignKey('orders.id'), nullable=False)
    order_item_id = db.Column(db.Integer, db.ForeignKey('order_items.id'))

    # Arbeitsschritt
    work_type = db.Column(db.String(50), nullable=False)
    # embroidery_setup, embroidery_run, print_setup, print_run,
    # dtf_setup, dtf_run, design_creation, quality_check, packing

    # Zeiterfassung
    started_at = db.Column(db.DateTime, nullable=False)
    ended_at = db.Column(db.DateTime)
    paused_duration_minutes = db.Column(db.Integer, default=0)  # Pausenzeit

    # Berechnete Dauer in Minuten
    duration_minutes = db.Column(db.Float)

    # Mitarbeiter
    started_by = db.Column(db.String(80))
    ended_by = db.Column(db.String(80))

    # Maschine (falls relevant)
    machine_id = db.Column(db.String(50), db.ForeignKey('machines.id'))

    # ═══════════════════════════════════════════════════════════════
    # PRODUKTIONSDETAILS (für Lernalgorithmus)
    # ═══════════════════════════════════════════════════════════════

    # Stickerei
    stitch_count = db.Column(db.Integer)  # Tatsächliche Stichzahl
    color_changes = db.Column(db.Integer)  # Anzahl Farbwechsel
    embroidery_position = db.Column(db.String(100))  # Brust, Rücken, Ärmel, etc.
    embroidery_size_mm2 = db.Column(db.Float)  # Fläche in mm²

    # Mengen
    quantity_planned = db.Column(db.Integer)  # Geplante Stückzahl
    quantity_produced = db.Column(db.Integer)  # Tatsächlich produziert
    quantity_rejected = db.Column(db.Integer, default=0)  # Ausschuss

    # Material
    fabric_type = db.Column(db.String(100))  # Stoffart
    fabric_difficulty = db.Column(db.Integer)  # 1-5 Schwierigkeit

    # Komplexität
    complexity_rating = db.Column(db.Integer)  # 1-5 Komplexität des Designs
    is_new_design = db.Column(db.Boolean, default=False)  # Erstmalige Produktion?

    # Notizen
    notes = db.Column(db.Text)
    issues = db.Column(db.Text)  # Probleme während Produktion

    # ═══════════════════════════════════════════════════════════════
    # METADATEN
    # ═══════════════════════════════════════════════════════════════

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    order = db.relationship('Order', backref='production_logs')
    order_item = db.relationship('OrderItem', backref='production_logs')
    machine = db.relationship('Machine', backref='production_logs')

    # ═══════════════════════════════════════════════════════════════
    # METHODEN
    # ═══════════════════════════════════════════════════════════════

    def stop(self, ended_by: str = None):
        """Stoppt die Zeiterfassung und berechnet Dauer"""
        self.ended_at = datetime.utcnow()
        self.ended_by = ended_by

        if self.started_at:
            total_minutes = (self.ended_at - self.started_at).total_seconds() / 60
            self.duration_minutes = total_minutes - (self.paused_duration_minutes or 0)

    def add_pause(self, minutes: int):
        """Fügt Pausenzeit hinzu"""
        self.paused_duration_minutes = (self.paused_duration_minutes or 0) + minutes

    @property
    def is_running(self):
        """Prüft ob Timer läuft"""
        return self.started_at is not None and self.ended_at is None

    @property
    def effective_duration(self):
        """Effektive Arbeitszeit in Minuten"""
        if self.duration_minutes:
            return self.duration_minutes
        if self.started_at:
            if self.ended_at:
                total = (self.ended_at - self.started_at).total_seconds() / 60
            else:
                total = (datetime.utcnow() - self.started_at).total_seconds() / 60
            return total - (self.paused_duration_minutes or 0)
        return 0

    @property
    def time_per_piece(self):
        """Zeit pro Stück in Minuten"""
        if self.quantity_produced and self.quantity_produced > 0 and self.duration_minutes:
            return self.duration_minutes / self.quantity_produced
        return None

    @property
    def stitches_per_minute(self):
        """Stiche pro Minute (für Stickerei)"""
        if self.stitch_count and self.duration_minutes and self.duration_minutes > 0:
            return self.stitch_count / self.duration_minutes
        return None

    @property
    def work_type_display(self):
        """Deutscher Name für Arbeitstyp"""
        types = {
            'embroidery_setup': 'Stickerei Einrichtung',
            'embroidery_run': 'Stickerei Produktion',
            'print_setup': 'Druck Einrichtung',
            'print_run': 'Druck Produktion',
            'dtf_setup': 'DTF Einrichtung',
            'dtf_run': 'DTF Produktion',
            'design_creation': 'Design-Erstellung',
            'quality_check': 'Qualitätskontrolle',
            'packing': 'Verpackung',
            'other': 'Sonstiges'
        }
        return types.get(self.work_type, self.work_type)

    @classmethod
    def start_tracking(cls, order_id: str, work_type: str, started_by: str,
                       order_item_id: int = None, machine_id: str = None,
                       **kwargs):
        """Startet neue Zeiterfassung"""
        log = cls(
            order_id=order_id,
            order_item_id=order_item_id,
            work_type=work_type,
            started_at=datetime.utcnow(),
            started_by=started_by,
            machine_id=machine_id,
            **kwargs
        )
        db.session.add(log)
        db.session.commit()
        return log

    @classmethod
    def get_active_for_order(cls, order_id: str):
        """Holt aktive Zeiterfassung für Auftrag"""
        return cls.query.filter_by(
            order_id=order_id,
            ended_at=None
        ).first()

    def __repr__(self):
        return f'<ProductionTimeLog {self.order_id} {self.work_type}>'


class ProductionStatistics(db.Model):
    """
    Aggregierte Statistiken für Kalkulation
    Wird regelmäßig aus ProductionTimeLog berechnet
    """
    __tablename__ = 'production_statistics'

    id = db.Column(db.Integer, primary_key=True)

    # Kategorisierung
    work_type = db.Column(db.String(50), nullable=False)
    embroidery_position = db.Column(db.String(100))  # Brust, Rücken, etc.
    fabric_type = db.Column(db.String(100))
    stitch_range_min = db.Column(db.Integer)  # Stichzahl-Bereich
    stitch_range_max = db.Column(db.Integer)

    # Statistiken
    sample_count = db.Column(db.Integer, default=0)  # Anzahl Datenpunkte
    avg_duration_minutes = db.Column(db.Float)
    min_duration_minutes = db.Column(db.Float)
    max_duration_minutes = db.Column(db.Float)
    std_deviation = db.Column(db.Float)

    # Pro Stück
    avg_time_per_piece = db.Column(db.Float)
    avg_stitches_per_minute = db.Column(db.Float)

    # Einrichtungszeit
    avg_setup_time = db.Column(db.Float)

    # Letzte Aktualisierung
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def calculate_for_embroidery(cls, position: str = None, stitch_min: int = None,
                                  stitch_max: int = None):
        """
        Berechnet Statistiken für Stickerei basierend auf historischen Daten
        """
        from sqlalchemy import func

        query = ProductionTimeLog.query.filter(
            ProductionTimeLog.work_type.in_(['embroidery_setup', 'embroidery_run']),
            ProductionTimeLog.ended_at.isnot(None),
            ProductionTimeLog.duration_minutes > 0
        )

        if position:
            query = query.filter_by(embroidery_position=position)

        if stitch_min is not None:
            query = query.filter(ProductionTimeLog.stitch_count >= stitch_min)

        if stitch_max is not None:
            query = query.filter(ProductionTimeLog.stitch_count <= stitch_max)

        logs = query.all()

        if not logs:
            return None

        durations = [log.duration_minutes for log in logs if log.duration_minutes]
        times_per_piece = [log.time_per_piece for log in logs if log.time_per_piece]
        stitches_per_min = [log.stitches_per_minute for log in logs if log.stitches_per_minute]

        import statistics

        stats = {
            'sample_count': len(logs),
            'avg_duration': statistics.mean(durations) if durations else 0,
            'min_duration': min(durations) if durations else 0,
            'max_duration': max(durations) if durations else 0,
            'std_deviation': statistics.stdev(durations) if len(durations) > 1 else 0,
            'avg_time_per_piece': statistics.mean(times_per_piece) if times_per_piece else 0,
            'avg_stitches_per_minute': statistics.mean(stitches_per_min) if stitches_per_min else 0
        }

        return stats

    @classmethod
    def estimate_time(cls, work_type: str, stitch_count: int = None,
                      position: str = None, quantity: int = 1,
                      fabric_type: str = None) -> dict:
        """
        Schätzt Produktionszeit basierend auf historischen Daten

        Returns:
            Dict mit geschätzter Zeit und Konfidenz
        """
        # Basis-Query
        query = ProductionTimeLog.query.filter(
            ProductionTimeLog.work_type == work_type,
            ProductionTimeLog.ended_at.isnot(None),
            ProductionTimeLog.duration_minutes > 0
        )

        # Filter anwenden
        if position:
            query = query.filter_by(embroidery_position=position)

        if fabric_type:
            query = query.filter_by(fabric_type=fabric_type)

        # Stichzahl-Bereich (±20%)
        if stitch_count:
            min_stitch = int(stitch_count * 0.8)
            max_stitch = int(stitch_count * 1.2)
            query = query.filter(
                ProductionTimeLog.stitch_count.between(min_stitch, max_stitch)
            )

        logs = query.order_by(ProductionTimeLog.created_at.desc()).limit(50).all()

        if not logs:
            # Fallback: Standardwerte
            return {
                'estimated_minutes': _default_estimate(work_type, stitch_count, quantity),
                'confidence': 'low',
                'sample_count': 0,
                'message': 'Keine historischen Daten verfügbar'
            }

        import statistics

        # Zeit pro Stück berechnen
        times_per_piece = [log.time_per_piece for log in logs if log.time_per_piece]

        if times_per_piece:
            avg_time = statistics.mean(times_per_piece)
            estimated = avg_time * quantity

            # Konfidenz basierend auf Datenmenge
            if len(logs) >= 20:
                confidence = 'high'
            elif len(logs) >= 10:
                confidence = 'medium'
            else:
                confidence = 'low'

            return {
                'estimated_minutes': round(estimated, 1),
                'confidence': confidence,
                'sample_count': len(logs),
                'avg_time_per_piece': round(avg_time, 2),
                'min_time': round(min(times_per_piece), 2),
                'max_time': round(max(times_per_piece), 2)
            }

        return {
            'estimated_minutes': _default_estimate(work_type, stitch_count, quantity),
            'confidence': 'low',
            'sample_count': len(logs),
            'message': 'Unvollständige Daten'
        }


def _default_estimate(work_type: str, stitch_count: int = None, quantity: int = 1) -> float:
    """Standard-Schätzung wenn keine historischen Daten verfügbar"""

    # Basis-Zeiten in Minuten
    base_times = {
        'embroidery_setup': 15,  # Einrichtung
        'embroidery_run': 5,     # Pro Stück (wird mit Stichzahl angepasst)
        'print_setup': 10,
        'print_run': 2,
        'dtf_setup': 8,
        'dtf_run': 3,
        'design_creation': 30,
        'quality_check': 2,
        'packing': 3
    }

    base = base_times.get(work_type, 10)

    # Stickerei: Zeit basierend auf Stichzahl anpassen
    if work_type == 'embroidery_run' and stitch_count:
        # ~800 Stiche/Minute als Basis
        base = stitch_count / 800

    return round(base * quantity, 1)


class PositionTimeEstimate(db.Model):
    """
    Gespeicherte Zeitschätzungen pro Position (Brust, Rücken, etc.)
    Wird aus historischen Daten berechnet und für schnelle Kalkulation verwendet
    """
    __tablename__ = 'position_time_estimates'

    id = db.Column(db.Integer, primary_key=True)

    # Position
    position_name = db.Column(db.String(100), unique=True, nullable=False)
    # brust_links, brust_rechts, ruecken_gross, ruecken_klein,
    # aermel_links, aermel_rechts, kragen, etc.

    # Typische Werte
    typical_stitch_count = db.Column(db.Integer)
    typical_size_mm2 = db.Column(db.Float)

    # Einrichtungszeit (fix)
    setup_time_minutes = db.Column(db.Float, default=5)

    # Zeit pro Stück
    time_per_piece_minutes = db.Column(db.Float)

    # Aufschläge
    complexity_multiplier = db.Column(db.Float, default=1.0)  # Für komplexe Designs
    fabric_difficulty_multiplier = db.Column(db.Float, default=1.0)  # Für schwierige Stoffe

    # Basierend auf X Datenpunkten
    sample_count = db.Column(db.Integer, default=0)

    # Letzte Aktualisierung
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def get_estimate(cls, position: str, quantity: int = 1,
                     stitch_count: int = None, complexity: int = 1) -> float:
        """
        Holt Zeitschätzung für Position

        Args:
            position: Position (brust_links, ruecken, etc.)
            quantity: Stückzahl
            stitch_count: Stichzahl (optional, überschreibt Standard)
            complexity: Komplexität 1-5

        Returns:
            Geschätzte Zeit in Minuten
        """
        estimate = cls.query.filter_by(position_name=position).first()

        if not estimate:
            # Fallback
            return _default_estimate('embroidery_run', stitch_count, quantity)

        base_time = estimate.time_per_piece_minutes or 5

        # Stichzahl anpassen wenn abweichend
        if stitch_count and estimate.typical_stitch_count:
            ratio = stitch_count / estimate.typical_stitch_count
            base_time *= ratio

        # Komplexität anwenden
        if complexity > 1:
            base_time *= (1 + (complexity - 1) * 0.1)  # +10% pro Stufe

        total = estimate.setup_time_minutes + (base_time * quantity)

        return round(total, 1)

    @property
    def display_name(self):
        """Deutscher Name"""
        names = {
            'brust_links': 'Brust links',
            'brust_rechts': 'Brust rechts',
            'brust_mitte': 'Brust Mitte',
            'ruecken_gross': 'Rücken groß',
            'ruecken_klein': 'Rücken klein',
            'aermel_links': 'Ärmel links',
            'aermel_rechts': 'Ärmel rechts',
            'kragen': 'Kragen',
            'kappe_vorne': 'Kappe vorne',
            'kappe_seite': 'Kappe Seite'
        }
        return names.get(self.position_name, self.position_name)

    def __repr__(self):
        return f'<PositionTimeEstimate {self.position_name}>'
