# StitchAdmin 2.0 - ProductionBlock Model
# Zeitblöcke für Pausen, Wartung, Büroarbeit, Telefonate, CRM-Aktivitäten etc.
# Erstellt von Hans Hahn - Alle Rechte vorbehalten

from datetime import datetime, time
from .models import db


class ProductionBlock(db.Model):
    """
    Universeller Kalender-Block für alle Aktivitäten
    
    Produktionsblöcke:
    - pause: Mittagspause, Kaffeepause
    - maintenance: Maschinenwartung
    - production: Produktion (alternativ zu ProductionSchedule)
    
    Büro/Verwaltung:
    - office: Allgemeine Büroarbeit
    - meeting: Besprechung intern
    - training: Schulung, Weiterbildung
    
    CRM/Kundenaktivitäten:
    - call_in: Eingehendes Telefonat
    - call_out: Ausgehendes Telefonat
    - customer_visit: Kundenbesuch (bei uns)
    - site_visit: Außentermin (beim Kunden)
    - email: Wichtige E-Mail-Korrespondenz
    - quote: Angebotserstellung
    - complaint: Reklamationsbearbeitung
    
    Personal:
    - vacation: Urlaub
    - sick: Krankheit
    - other: Sonstiges
    """
    __tablename__ = 'production_blocks'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Block-Typ und Bezeichnung
    block_type = db.Column(db.String(50), nullable=False, index=True)
    title = db.Column(db.String(200))
    
    # Zeitangaben - Start
    start_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    
    # Zeitangaben - Ende (kann anderer Tag sein für mehrtägige Blöcke)
    end_date = db.Column(db.Date, nullable=False, index=True)
    end_time = db.Column(db.Time, nullable=False)
    
    # =====================================================
    # VERKNÜPFUNGEN FÜR SCHNELLE SUCHE
    # =====================================================
    
    # Kundenbezug (für CRM-Aktivitäten)
    customer_id = db.Column(db.String(50), db.ForeignKey('customers.id'), nullable=True, index=True)
    customer = db.relationship('Customer', backref=db.backref('calendar_activities', lazy='dynamic'))
    
    # Auftragsbezug (optional)
    order_id = db.Column(db.String(50), db.ForeignKey('orders.id'), nullable=True, index=True)
    order = db.relationship('Order', backref=db.backref('calendar_activities', lazy='dynamic'))
    
    # Maschinenbezug (für Wartung, Produktion)
    machine_id = db.Column(db.Integer, db.ForeignKey('machines.id'), nullable=True)
    machine = db.relationship('Machine', backref=db.backref('production_blocks', lazy='dynamic'))
    
    # Mitarbeiterbezug
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user = db.relationship('User', backref=db.backref('production_blocks', lazy='dynamic'))
    
    # =====================================================
    # CRM-SPEZIFISCHE FELDER
    # =====================================================
    
    # Kontaktperson (bei Telefonaten/Besuchen)
    contact_person = db.Column(db.String(200))
    contact_phone = db.Column(db.String(50))
    contact_email = db.Column(db.String(200))
    
    # Inhalt/Zusammenfassung (durchsuchbar!)
    summary = db.Column(db.Text)  # Kurze Zusammenfassung
    content = db.Column(db.Text)  # Ausführlicher Inhalt/Gesprächsnotizen
    
    # Ergebnis/Outcome
    outcome = db.Column(db.String(50))  # z.B. 'successful', 'callback_needed', 'order_placed', 'complaint_resolved'
    follow_up_date = db.Column(db.Date)  # Wiedervorlage
    follow_up_notes = db.Column(db.Text)
    
    # Priorität/Wichtigkeit
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    
    # =====================================================
    # WIEDERKEHRENDE TERMINE
    # =====================================================
    
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_pattern = db.Column(db.String(50))  # daily, weekly, monthly, yearly
    recurrence_days = db.Column(db.String(50))  # z.B. "1,2,3,4,5" für Mo-Fr
    recurrence_end_date = db.Column(db.Date)
    parent_block_id = db.Column(db.Integer, db.ForeignKey('production_blocks.id'), nullable=True)
    
    # =====================================================
    # DARSTELLUNG
    # =====================================================
    
    # Farbe (optional, sonst wird Standard nach Typ verwendet)
    color = db.Column(db.String(20))
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_all_day = db.Column(db.Boolean, default=False)
    is_private = db.Column(db.Boolean, default=False)  # Nur für zugewiesenen User sichtbar
    
    # Allgemeine Notizen
    notes = db.Column(db.Text)
    
    # =====================================================
    # AUDIT
    # =====================================================
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(100))
    
    # =====================================================
    # KONSTANTEN
    # =====================================================
    
    # Standard-Farben nach Typ
    TYPE_COLORS = {
        # Produktion
        'pause': '#94a3b8',       # Grau
        'maintenance': '#f59e0b', # Orange
        'production': '#3b82f6',  # Blau
        
        # Büro
        'office': '#06b6d4',      # Cyan
        'meeting': '#6366f1',     # Indigo
        'training': '#8b5cf6',    # Violett
        
        # CRM - Telefonate
        'call_in': '#22c55e',     # Grün (eingehend)
        'call_out': '#14b8a6',    # Teal (ausgehend)
        
        # CRM - Besuche
        'customer_visit': '#0ea5e9',  # Hellblau
        'site_visit': '#0284c7',      # Dunkelblau
        
        # CRM - Korrespondenz
        'email': '#64748b',       # Slate
        'quote': '#a855f7',       # Lila
        'complaint': '#ef4444',   # Rot
        
        # Personal
        'vacation': '#ec4899',    # Pink
        'sick': '#f43f5e',        # Rose
        'other': '#78716c'        # Braun-Grau
    }
    
    TYPE_ICONS = {
        'pause': 'fa-coffee',
        'maintenance': 'fa-wrench',
        'production': 'fa-industry',
        'office': 'fa-briefcase',
        'meeting': 'fa-users',
        'training': 'fa-graduation-cap',
        'call_in': 'fa-phone-alt',
        'call_out': 'fa-phone',
        'customer_visit': 'fa-user-tie',
        'site_visit': 'fa-car',
        'email': 'fa-envelope',
        'quote': 'fa-file-invoice-dollar',
        'complaint': 'fa-exclamation-triangle',
        'vacation': 'fa-umbrella-beach',
        'sick': 'fa-thermometer-half',
        'other': 'fa-bookmark'
    }
    
    TYPE_LABELS = {
        'pause': 'Pause',
        'maintenance': 'Wartung',
        'production': 'Produktion',
        'office': 'Büroarbeit',
        'meeting': 'Meeting',
        'training': 'Schulung',
        'call_in': 'Anruf (eingehend)',
        'call_out': 'Anruf (ausgehend)',
        'customer_visit': 'Kundenbesuch',
        'site_visit': 'Außentermin',
        'email': 'E-Mail',
        'quote': 'Angebot',
        'complaint': 'Reklamation',
        'vacation': 'Urlaub',
        'sick': 'Krankheit',
        'other': 'Sonstiges'
    }
    
    TYPE_CATEGORIES = {
        'production': ['pause', 'maintenance', 'production'],
        'office': ['office', 'meeting', 'training'],
        'crm': ['call_in', 'call_out', 'customer_visit', 'site_visit', 'email', 'quote', 'complaint'],
        'personal': ['vacation', 'sick', 'other']
    }
    
    OUTCOME_LABELS = {
        'successful': 'Erfolgreich',
        'callback_needed': 'Rückruf erforderlich',
        'order_placed': 'Auftrag erteilt',
        'quote_sent': 'Angebot versendet',
        'quote_accepted': 'Angebot angenommen',
        'quote_rejected': 'Angebot abgelehnt',
        'complaint_resolved': 'Reklamation gelöst',
        'complaint_pending': 'Reklamation offen',
        'no_answer': 'Nicht erreicht',
        'voicemail': 'Mailbox',
        'cancelled': 'Abgesagt',
        'rescheduled': 'Verschoben'
    }
    
    # =====================================================
    # PROPERTIES
    # =====================================================
    
    @property
    def display_color(self):
        """Gibt die Anzeigefarbe zurück (eigene oder Standard)"""
        return self.color or self.TYPE_COLORS.get(self.block_type, '#78716c')
    
    @property
    def display_icon(self):
        """Gibt das passende Icon zurück"""
        return self.TYPE_ICONS.get(self.block_type, 'fa-bookmark')
    
    @property
    def type_label(self):
        """Gibt das deutsche Label für den Typ zurück"""
        return self.TYPE_LABELS.get(self.block_type, self.block_type.title())
    
    @property
    def outcome_label(self):
        """Gibt das deutsche Label für das Ergebnis zurück"""
        if self.outcome:
            return self.OUTCOME_LABELS.get(self.outcome, self.outcome)
        return None
    
    @property
    def is_crm_activity(self):
        """Prüft ob es eine CRM-Aktivität ist"""
        return self.block_type in self.TYPE_CATEGORIES.get('crm', [])
    
    @property
    def is_multiday(self):
        """Prüft ob der Block über mehrere Tage geht"""
        return self.start_date != self.end_date
    
    @property
    def duration_minutes(self):
        """Berechnet die Gesamtdauer in Minuten"""
        from datetime import datetime, timedelta
        
        start_dt = datetime.combine(self.start_date, self.start_time)
        end_dt = datetime.combine(self.end_date, self.end_time)
        
        delta = end_dt - start_dt
        return int(delta.total_seconds() / 60)
    
    @property
    def duration_hours(self):
        """Berechnet die Gesamtdauer in Stunden"""
        return round(self.duration_minutes / 60, 1)
    
    @property
    def needs_follow_up(self):
        """Prüft ob eine Wiedervorlage ansteht"""
        if self.follow_up_date:
            from datetime import date
            return self.follow_up_date <= date.today()
        return False
    
    # =====================================================
    # METHODEN
    # =====================================================
    
    def get_segments_for_week(self, week_start, week_end, work_start_hour=8, work_end_hour=17):
        """
        Teilt den Block in Tages-Segmente für die Kalenderansicht auf
        
        Returns: Liste von Dicts mit {date, start_time, end_time, is_start, is_end, is_continuation}
        """
        from datetime import timedelta
        
        segments = []
        current_date = max(self.start_date, week_start)
        end_date = min(self.end_date, week_end)
        
        while current_date <= end_date:
            segment = {
                'date': current_date,
                'block': self,
                'is_start': current_date == self.start_date,
                'is_end': current_date == self.end_date,
                'is_continuation': current_date != self.start_date and current_date != self.end_date
            }
            
            # Start-Zeit für dieses Segment
            if current_date == self.start_date:
                segment['start_time'] = self.start_time
            else:
                segment['start_time'] = time(work_start_hour, 0)
            
            # End-Zeit für dieses Segment
            if current_date == self.end_date:
                segment['end_time'] = self.end_time
            else:
                segment['end_time'] = time(work_end_hour, 0)
            
            segments.append(segment)
            current_date += timedelta(days=1)
        
        return segments
    
    def overlaps_with(self, other_start, other_end, machine_id=None):
        """Prüft ob dieser Block mit einem anderen Zeitraum überlappt"""
        from datetime import datetime
        
        self_start = datetime.combine(self.start_date, self.start_time)
        self_end = datetime.combine(self.end_date, self.end_time)
        
        # Keine Überlappung wenn Maschine unterschiedlich und beide definiert
        if machine_id and self.machine_id and machine_id != self.machine_id:
            return False
        
        # Zeitüberlappung prüfen
        return not (self_end <= other_start or self_start >= other_end)
    
    # =====================================================
    # KLASSENMETHODEN - ABFRAGEN
    # =====================================================
    
    @classmethod
    def get_blocks_for_date_range(cls, start_date, end_date, machine_id=None, 
                                   customer_id=None, block_types=None, include_inactive=False):
        """Holt alle Blöcke die in einen Datumsbereich fallen"""
        query = cls.query.filter(
            db.and_(
                cls.start_date <= end_date,
                cls.end_date >= start_date
            )
        )
        
        if not include_inactive:
            query = query.filter(cls.is_active == True)
        
        if machine_id:
            query = query.filter(
                db.or_(
                    cls.machine_id == machine_id,
                    cls.machine_id.is_(None)
                )
            )
        
        if customer_id:
            query = query.filter(cls.customer_id == customer_id)
        
        if block_types:
            query = query.filter(cls.block_type.in_(block_types))
        
        return query.order_by(cls.start_date, cls.start_time).all()
    
    @classmethod
    def get_customer_activities(cls, customer_id, limit=50):
        """Holt alle CRM-Aktivitäten für einen Kunden"""
        crm_types = cls.TYPE_CATEGORIES.get('crm', [])
        
        return cls.query.filter(
            cls.customer_id == customer_id,
            cls.block_type.in_(crm_types),
            cls.is_active == True
        ).order_by(cls.start_date.desc(), cls.start_time.desc()).limit(limit).all()
    
    @classmethod
    def get_pending_follow_ups(cls, user_id=None):
        """Holt alle fälligen Wiedervorlagen"""
        from datetime import date
        
        query = cls.query.filter(
            cls.follow_up_date <= date.today(),
            cls.is_active == True
        )
        
        if user_id:
            query = query.filter(cls.user_id == user_id)
        
        return query.order_by(cls.follow_up_date).all()
    
    @classmethod
    def search(cls, search_term, customer_id=None, block_types=None, 
               start_date=None, end_date=None, limit=100):
        """
        Durchsucht Kalendereinträge nach Stichworten
        
        Durchsucht: title, summary, content, contact_person, notes
        """
        search_pattern = f'%{search_term}%'
        
        query = cls.query.filter(
            cls.is_active == True,
            db.or_(
                cls.title.ilike(search_pattern),
                cls.summary.ilike(search_pattern),
                cls.content.ilike(search_pattern),
                cls.contact_person.ilike(search_pattern),
                cls.notes.ilike(search_pattern)
            )
        )
        
        if customer_id:
            query = query.filter(cls.customer_id == customer_id)
        
        if block_types:
            query = query.filter(cls.block_type.in_(block_types))
        
        if start_date:
            query = query.filter(cls.start_date >= start_date)
        
        if end_date:
            query = query.filter(cls.end_date <= end_date)
        
        return query.order_by(cls.start_date.desc()).limit(limit).all()
    
    @classmethod
    def get_statistics(cls, start_date, end_date, user_id=None):
        """Holt Statistiken für einen Zeitraum"""
        query = cls.query.filter(
            cls.start_date >= start_date,
            cls.end_date <= end_date,
            cls.is_active == True
        )
        
        if user_id:
            query = query.filter(cls.user_id == user_id)
        
        blocks = query.all()
        
        stats = {
            'total': len(blocks),
            'by_type': {},
            'by_outcome': {},
            'total_duration_hours': 0,
            'crm_activities': 0,
            'pending_follow_ups': 0
        }
        
        crm_types = cls.TYPE_CATEGORIES.get('crm', [])
        
        for block in blocks:
            # Nach Typ
            if block.block_type not in stats['by_type']:
                stats['by_type'][block.block_type] = 0
            stats['by_type'][block.block_type] += 1
            
            # Nach Ergebnis
            if block.outcome:
                if block.outcome not in stats['by_outcome']:
                    stats['by_outcome'][block.outcome] = 0
                stats['by_outcome'][block.outcome] += 1
            
            # Gesamtdauer
            stats['total_duration_hours'] += block.duration_hours
            
            # CRM-Aktivitäten
            if block.block_type in crm_types:
                stats['crm_activities'] += 1
            
            # Offene Wiedervorlagen
            if block.needs_follow_up:
                stats['pending_follow_ups'] += 1
        
        return stats
    
    @classmethod
    def create_recurring_instances(cls, parent_block, until_date):
        """Erstellt wiederkehrende Instanzen eines Blocks"""
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta
        
        if not parent_block.is_recurring or not parent_block.recurrence_pattern:
            return []
        
        instances = []
        current_start = parent_block.start_date
        duration = parent_block.end_date - parent_block.start_date
        
        while True:
            # Nächstes Datum berechnen
            if parent_block.recurrence_pattern == 'daily':
                current_start += timedelta(days=1)
            elif parent_block.recurrence_pattern == 'weekly':
                current_start += timedelta(weeks=1)
            elif parent_block.recurrence_pattern == 'monthly':
                current_start += relativedelta(months=1)
            elif parent_block.recurrence_pattern == 'yearly':
                current_start += relativedelta(years=1)
            else:
                break
            
            # Ende prüfen
            if current_start > until_date:
                break
            if parent_block.recurrence_end_date and current_start > parent_block.recurrence_end_date:
                break
            
            # Wochentag prüfen wenn definiert
            if parent_block.recurrence_days:
                allowed_days = [int(d) for d in parent_block.recurrence_days.split(',')]
                if current_start.weekday() not in allowed_days:
                    continue
            
            # Instanz erstellen
            instance = cls(
                block_type=parent_block.block_type,
                title=parent_block.title,
                start_date=current_start,
                start_time=parent_block.start_time,
                end_date=current_start + duration,
                end_time=parent_block.end_time,
                machine_id=parent_block.machine_id,
                user_id=parent_block.user_id,
                customer_id=parent_block.customer_id,
                color=parent_block.color,
                is_active=True,
                is_recurring=False,
                parent_block_id=parent_block.id,
                notes=parent_block.notes,
                created_by='system'
            )
            instances.append(instance)
        
        return instances
    
    def __repr__(self):
        return f'<ProductionBlock {self.block_type}: {self.title} ({self.start_date} - {self.end_date})>'
