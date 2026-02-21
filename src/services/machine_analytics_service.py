# -*- coding: utf-8 -*-
"""
Maschinen-Analytics Service
=============================
Auslastung, Kapazitaet und Performance-Metriken fuer Maschinen.

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import logging
from datetime import datetime, date, timedelta
from collections import defaultdict

from src.models import db, Machine, ProductionSchedule

logger = logging.getLogger(__name__)


class MachineAnalyticsService:
    """Berechnet Auslastung und Kapazitaet"""

    WORK_HOURS_PER_DAY = 8  # Standard-Arbeitstag

    def get_machine_utilization(self, machine_id, start_date, end_date):
        """
        Berechnet Auslastung einer Maschine in einem Zeitraum.

        Returns:
            Dict mit scheduled_hours, available_hours, utilization_pct
        """
        schedules = ProductionSchedule.query.filter(
            ProductionSchedule.machine_id == machine_id,
            ProductionSchedule.status.in_(['scheduled', 'in_progress', 'completed']),
            ProductionSchedule.scheduled_start < end_date,
            ProductionSchedule.scheduled_end > start_date,
        ).all()

        scheduled_hours = 0
        actual_hours = 0

        for s in schedules:
            # Clip auf Zeitraum
            s_start = max(s.scheduled_start, datetime.combine(start_date, datetime.min.time()))
            s_end = min(s.scheduled_end, datetime.combine(end_date, datetime.max.time()))
            hours = max(0, (s_end - s_start).total_seconds() / 3600)
            scheduled_hours += hours

            # Actual (falls vorhanden)
            if s.actual_start and s.actual_end:
                a_start = max(s.actual_start, datetime.combine(start_date, datetime.min.time()))
                a_end = min(s.actual_end, datetime.combine(end_date, datetime.max.time()))
                actual_hours += max(0, (a_end - a_start).total_seconds() / 3600)

        # Arbeitstage im Zeitraum (Mo-Fr)
        work_days = self._count_workdays(start_date, end_date)
        available_hours = work_days * self.WORK_HOURS_PER_DAY

        utilization = (scheduled_hours / available_hours * 100) if available_hours > 0 else 0

        return {
            'scheduled_hours': round(scheduled_hours, 1),
            'actual_hours': round(actual_hours, 1),
            'available_hours': round(available_hours, 1),
            'utilization_pct': round(min(utilization, 100), 1),
            'idle_hours': round(max(0, available_hours - scheduled_hours), 1),
            'work_days': work_days,
        }

    def get_all_machines_utilization(self, start_date, end_date):
        """Auslastung aller aktiven Maschinen"""
        machines = Machine.query.filter_by(status='active').order_by(Machine.name).all()
        result = []

        for machine in machines:
            util = self.get_machine_utilization(machine.id, start_date, end_date)
            util['machine'] = machine
            result.append(util)

        # Sortierung: hoechste Auslastung zuerst
        result.sort(key=lambda x: x['utilization_pct'], reverse=True)
        return result

    def get_weekly_capacity(self, start_of_week):
        """
        Kapazitaets-Heatmap fuer eine Woche (Mo-Fr).

        Returns:
            Dict {machine_id: {day_index: {scheduled_hours, available_hours, pct}}}
        """
        machines = Machine.query.filter_by(status='active').order_by(Machine.name).all()
        end_of_week = start_of_week + timedelta(days=5)

        # Alle Schedules der Woche laden
        schedules = ProductionSchedule.query.filter(
            ProductionSchedule.status.in_(['scheduled', 'in_progress', 'completed']),
            ProductionSchedule.scheduled_start < datetime.combine(end_of_week, datetime.max.time()),
            ProductionSchedule.scheduled_end > datetime.combine(start_of_week, datetime.min.time()),
        ).all()

        # Pro Maschine & Tag aggregieren
        capacity = {}
        for machine in machines:
            days = {}
            for day_offset in range(5):  # Mo-Fr
                day = start_of_week + timedelta(days=day_offset)
                day_start = datetime.combine(day, datetime.min.time())
                day_end = datetime.combine(day, datetime.max.time())

                hours = 0
                jobs = 0
                for s in schedules:
                    if str(s.machine_id) != str(machine.id):
                        continue
                    s_start = max(s.scheduled_start, day_start)
                    s_end = min(s.scheduled_end, day_end)
                    h = max(0, (s_end - s_start).total_seconds() / 3600)
                    if h > 0:
                        hours += h
                        jobs += 1

                pct = (hours / self.WORK_HOURS_PER_DAY * 100) if self.WORK_HOURS_PER_DAY > 0 else 0

                days[day_offset] = {
                    'date': day,
                    'scheduled_hours': round(hours, 1),
                    'available_hours': self.WORK_HOURS_PER_DAY,
                    'pct': round(min(pct, 100), 1),
                    'jobs': jobs,
                    'overbooked': pct > 100,
                }

            capacity[machine.id] = {
                'machine': machine,
                'days': days,
                'week_total': round(sum(d['scheduled_hours'] for d in days.values()), 1),
                'week_available': self.WORK_HOURS_PER_DAY * 5,
                'week_pct': round(
                    sum(d['scheduled_hours'] for d in days.values()) / (self.WORK_HOURS_PER_DAY * 5) * 100, 1
                ) if self.WORK_HOURS_PER_DAY > 0 else 0,
            }

        return capacity

    def get_current_jobs(self):
        """Aktuelle Auftraege auf Maschinen"""
        now = datetime.utcnow()
        active = ProductionSchedule.query.filter(
            ProductionSchedule.status.in_(['scheduled', 'in_progress']),
            ProductionSchedule.scheduled_start <= now,
            ProductionSchedule.scheduled_end >= now,
        ).all()

        result = []
        for s in active:
            elapsed = (now - s.scheduled_start).total_seconds() / 3600
            total = (s.scheduled_end - s.scheduled_start).total_seconds() / 3600
            progress = (elapsed / total * 100) if total > 0 else 0

            result.append({
                'schedule': s,
                'machine': Machine.query.get(s.machine_id),
                'progress_pct': round(min(progress, 100), 1),
                'elapsed_hours': round(elapsed, 1),
                'total_hours': round(total, 1),
                'remaining_hours': round(max(0, total - elapsed), 1),
            })

        return result

    def get_queue_by_machine(self):
        """Warteschlange pro Maschine"""
        now = datetime.utcnow()
        upcoming = ProductionSchedule.query.filter(
            ProductionSchedule.status == 'scheduled',
            ProductionSchedule.scheduled_start > now,
        ).order_by(ProductionSchedule.scheduled_start).all()

        queues = defaultdict(list)
        for s in upcoming:
            queues[str(s.machine_id)].append(s)

        return dict(queues)

    def get_summary_stats(self):
        """Gesamtstatistiken"""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=5)
        month_start = today.replace(day=1)

        machines = Machine.query.filter_by(status='active').all()

        # Diese Woche
        week_util = []
        for m in machines:
            u = self.get_machine_utilization(m.id, week_start, week_end)
            week_util.append(u['utilization_pct'])

        # Heute aktive Jobs
        now = datetime.utcnow()
        active_jobs = ProductionSchedule.query.filter(
            ProductionSchedule.status.in_(['scheduled', 'in_progress']),
            ProductionSchedule.scheduled_start <= now,
            ProductionSchedule.scheduled_end >= now,
        ).count()

        # Anstehende Jobs
        pending_jobs = ProductionSchedule.query.filter(
            ProductionSchedule.status == 'scheduled',
            ProductionSchedule.scheduled_start > now,
        ).count()

        # Ueberbuchungen diese Woche
        capacity = self.get_weekly_capacity(week_start)
        overbooked = sum(
            1 for mc in capacity.values()
            for d in mc['days'].values()
            if d['overbooked']
        )

        return {
            'active_machines': len(machines),
            'avg_utilization': round(sum(week_util) / len(week_util), 1) if week_util else 0,
            'max_utilization': round(max(week_util), 1) if week_util else 0,
            'min_utilization': round(min(week_util), 1) if week_util else 0,
            'active_jobs': active_jobs,
            'pending_jobs': pending_jobs,
            'overbooked_slots': overbooked,
        }

    def _count_workdays(self, start_date, end_date):
        """Zaehlt Arbeitstage (Mo-Fr) im Zeitraum"""
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime):
            end_date = end_date.date()

        days = 0
        current = start_date
        while current < end_date:
            if current.weekday() < 5:
                days += 1
            current += timedelta(days=1)
        return days
