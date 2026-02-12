"""
Production Controller - Kalender-Erweiterungen
Neue Routen für ressourcenübergreifenden Kalender mit Zeitblöcken und CRM

Diese Datei wird in production_controller_db.py importiert.

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta, time as dt_time
from src.models import db, Order, Machine, ProductionSchedule, ActivityLog, Customer
from sqlalchemy import and_, or_


def _get_schedule_segments_for_week(schedule, week_start, week_end, work_start_hour, work_end_hour):
    """
    Teilt einen Produktionsplan in Tages-Segmente für mehrtägige Aufträge
    """
    segments = []
    
    schedule_start_date = schedule.scheduled_start.date()
    schedule_end_date = schedule.scheduled_end.date()
    
    current_date = max(schedule_start_date, week_start)
    end_date = min(schedule_end_date, week_end)
    
    total_days = (schedule_end_date - schedule_start_date).days + 1
    is_multiday = total_days > 1
    
    while current_date <= end_date:
        segment = {
            'id': schedule.id,
            'schedule_id': schedule.id,
            'order_id': schedule.order_id,
            'order': schedule.order,
            'machine_id': schedule.machine_id,
            'machine': schedule.machine,
            'block_type': 'production',
            'title': f"Auftrag {schedule.order.id}" if schedule.order else 'Produktion',
            'notes': schedule.notes,
            'is_multiday': is_multiday,
            'total_days': total_days,
            'is_start': current_date == schedule_start_date,
            'is_end': current_date == schedule_end_date,
            'is_continuation': current_date != schedule_start_date and current_date != schedule_end_date,
            'color': getattr(schedule.machine, 'calendar_color', None) if schedule.machine else None
        }
        
        if current_date == schedule_start_date:
            segment['start_time'] = schedule.scheduled_start.time()
        else:
            segment['start_time'] = dt_time(work_start_hour, 0)
        
        if current_date == schedule_end_date:
            segment['end_time'] = schedule.scheduled_end.time()
        else:
            segment['end_time'] = dt_time(work_end_hour, 0)
        
        segments.append((current_date, segment))
        current_date += timedelta(days=1)
    
    return segments


def _get_block_segments_for_week(block, week_start, week_end, work_start_hour, work_end_hour):
    """
    Teilt einen Zeitblock in Tages-Segmente für mehrtägige Blöcke
    """
    segments = []
    
    current_date = max(block.start_date, week_start)
    end_date = min(block.end_date, week_end)
    
    total_days = (block.end_date - block.start_date).days + 1
    is_multiday = total_days > 1
    
    while current_date <= end_date:
        segment = {
            'id': f"block_{block.id}",
            'block_id': block.id,
            'schedule_id': None,
            'order_id': block.order_id,
            'order': block.order if hasattr(block, 'order') else None,
            'customer_id': block.customer_id,
            'customer': block.customer if hasattr(block, 'customer') else None,
            'machine_id': block.machine_id,
            'machine': block.machine,
            'block_type': block.block_type,
            'title': block.title or block.type_label,
            'summary': block.summary,
            'contact_person': block.contact_person,
            'notes': block.notes,
            'is_multiday': is_multiday,
            'total_days': total_days,
            'is_start': current_date == block.start_date,
            'is_end': current_date == block.end_date,
            'is_continuation': current_date != block.start_date and current_date != block.end_date,
            'color': block.display_color
        }
        
        if current_date == block.start_date:
            segment['start_time'] = block.start_time
        else:
            segment['start_time'] = dt_time(work_start_hour, 0)
        
        if current_date == block.end_date:
            segment['end_time'] = block.end_time
        else:
            segment['end_time'] = dt_time(work_end_hour, 0)
        
        segments.append((current_date, segment))
        current_date += timedelta(days=1)
    
    return segments


def register_calendar_routes(bp, load_production_settings, log_activity):
    """
    Registriert die neuen Kalender-Routen auf dem Blueprint
    """
    
    @bp.route('/calendar/new')
    @login_required
    def calendar_new():
        """
        NEUER Produktionskalender - Ressourcenübergreifend mit CRM
        """
        week_offset = request.args.get('week', 0, type=int)
        today = date.today()
        
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday) + timedelta(weeks=week_offset)
        week_end = week_start + timedelta(days=6)
        
        settings = load_production_settings()
        work_start_hour = settings.get('work_start', 8)
        work_end_hour = settings.get('work_end', 17)
        slot_height = 40
        
        machines = Machine.query.filter_by(status='active').order_by(Machine.type, Machine.name).all()
        
        machine_status = {}
        for machine in machines:
            current_order = Order.query.filter_by(
                assigned_machine_id=machine.id,
                status='in_progress'
            ).first()
            machine_status[machine.id] = {
                'machine': machine,
                'current_order': current_order,
                'is_busy': current_order is not None
            }
        
        schedules = ProductionSchedule.query.filter(
            and_(
                ProductionSchedule.scheduled_start <= datetime.combine(week_end, datetime.max.time()),
                ProductionSchedule.scheduled_end >= datetime.combine(week_start, datetime.min.time()),
                ProductionSchedule.status != 'cancelled'
            )
        ).all()
        
        blocks = []
        try:
            from src.models import ProductionBlock
            blocks = ProductionBlock.query.filter(
                and_(
                    ProductionBlock.start_date <= week_end,
                    ProductionBlock.end_date >= week_start,
                    ProductionBlock.is_active == True
                )
            ).all()
        except Exception as e:
            print(f"[INFO] ProductionBlock nicht verfügbar: {e}")
        
        calendar_data = {}
        for day_offset in range(7):
            current_date = week_start + timedelta(days=day_offset)
            calendar_data[current_date] = []
        
        for schedule in schedules:
            segments = _get_schedule_segments_for_week(
                schedule, week_start, week_end, work_start_hour, work_end_hour
            )
            for segment_date, segment in segments:
                if segment_date in calendar_data:
                    calendar_data[segment_date].append(segment)
        
        for block in blocks:
            segments = _get_block_segments_for_week(
                block, week_start, week_end, work_start_hour, work_end_hour
            )
            for segment_date, segment in segments:
                if segment_date in calendar_data:
                    calendar_data[segment_date].append(segment)
        
        for day in calendar_data:
            calendar_data[day].sort(key=lambda x: x['start_time'])
        
        waiting_orders = Order.query.filter_by(status='accepted').order_by(
            Order.rush_order.desc(), 
            Order.created_at
        ).all()
        
        # Kunden für CRM-Aktivitäten laden
        customers = Customer.query.order_by(Customer.last_name, Customer.first_name).all()
        
        return render_template('production/calendar_new.html',
                             week_start=week_start,
                             week_end=week_end,
                             week_offset=week_offset,
                             calendar_data=calendar_data,
                             machines=machines,
                             machine_status=machine_status,
                             waiting_orders=waiting_orders,
                             customers=customers,
                             settings=settings,
                             slot_height=slot_height,
                             today=today,
                             timedelta=timedelta)
    
    
    @bp.route('/block/add', methods=['POST'])
    @login_required
    def add_block():
        """
        Zeitblock/CRM-Aktivität hinzufügen
        
        Speichert ALLE Felder inkl. Kunde, Kontakt, Inhalt für spätere Suche
        """
        try:
            from src.models import ProductionBlock
        except ImportError:
            flash('ProductionBlock Model nicht verfügbar! Bitte Datenbank migrieren.', 'danger')
            return redirect(url_for('production.calendar_new'))
        
        # === BASIS-FELDER ===
        block_type = request.form.get('block_type', 'pause')
        title = request.form.get('title', '')
        start_date_str = request.form.get('start_date')
        start_time_str = request.form.get('start_time')
        end_date_str = request.form.get('end_date')
        end_time_str = request.form.get('end_time')
        machine_id = request.form.get('machine_id') or None
        notes = request.form.get('notes', '')
        
        # === CRM-FELDER ===
        customer_id = request.form.get('customer_id') or None
        order_id = request.form.get('order_id') or None
        contact_person = request.form.get('contact_person', '')
        contact_phone = request.form.get('contact_phone', '')
        contact_email = request.form.get('contact_email', '')
        summary = request.form.get('summary', '')
        content = request.form.get('content', '')
        outcome = request.form.get('outcome') or None
        follow_up_date_str = request.form.get('follow_up_date') or None
        follow_up_notes = request.form.get('follow_up_notes', '')
        priority = request.form.get('priority', 'normal')
        
        # === WIEDERKEHREND ===
        is_recurring = request.form.get('is_recurring') == 'on'
        recurrence_pattern = request.form.get('recurrence_pattern', 'weekly')
        
        # Datum/Zeit parsen
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
            end_time = datetime.strptime(end_time_str, '%H:%M').time()
            
            follow_up_date = None
            if follow_up_date_str:
                follow_up_date = datetime.strptime(follow_up_date_str, '%Y-%m-%d').date()
        except ValueError as e:
            flash(f'Ungültiges Datum oder Zeitformat: {e}', 'danger')
            return redirect(url_for('production.calendar_new'))
        
        # Validierung
        if end_date < start_date:
            flash('Enddatum kann nicht vor Startdatum liegen!', 'danger')
            return redirect(url_for('production.calendar_new'))
        
        if end_date == start_date and end_time <= start_time:
            flash('Endzeit muss nach Startzeit liegen!', 'danger')
            return redirect(url_for('production.calendar_new'))
        
        # Block erstellen mit ALLEN Feldern
        block = ProductionBlock(
            # Basis
            block_type=block_type,
            title=title or ProductionBlock.TYPE_LABELS.get(block_type, block_type.title()),
            start_date=start_date,
            start_time=start_time,
            end_date=end_date,
            end_time=end_time,
            machine_id=machine_id if machine_id else None,
            notes=notes,
            
            # CRM-Verknüpfungen (für schnelle Suche!)
            customer_id=customer_id,
            order_id=order_id,
            
            # CRM-Kontaktdaten
            contact_person=contact_person,
            contact_phone=contact_phone,
            contact_email=contact_email,
            
            # CRM-Inhalt (durchsuchbar!)
            summary=summary,
            content=content,
            outcome=outcome,
            
            # Wiedervorlage
            follow_up_date=follow_up_date,
            follow_up_notes=follow_up_notes,
            priority=priority,
            
            # Wiederkehrend
            is_recurring=is_recurring,
            recurrence_pattern=recurrence_pattern if is_recurring else None,
            
            # Meta
            user_id=current_user.id if hasattr(current_user, 'id') else None,
            created_by=current_user.username,
            is_active=True
        )
        
        db.session.add(block)
        db.session.commit()
        
        # Kundenname für Log ermitteln
        customer_name = ''
        if customer_id:
            customer = Customer.query.get(customer_id)
            if customer:
                customer_name = f" (Kunde: {customer.display_name})"
        
        log_activity('block_created', f'{block.type_label} erstellt: {block.title}{customer_name}')
        flash(f'{block.type_label} "{block.title}" wurde gespeichert!', 'success')
        
        return redirect(url_for('production.calendar_new'))
    
    
    @bp.route('/block/<int:block_id>/delete', methods=['POST'])
    @login_required
    def delete_block(block_id):
        """Zeitblock löschen (Soft Delete)"""
        try:
            from src.models import ProductionBlock
            block = ProductionBlock.query.get_or_404(block_id)
            
            block.is_active = False
            block.updated_by = current_user.username
            block.updated_at = datetime.utcnow()
            db.session.commit()
            
            log_activity('block_deleted', f'Eintrag gelöscht: {block.title}')
            flash('Eintrag wurde gelöscht!', 'success')
        except ImportError:
            flash('ProductionBlock Model nicht verfügbar!', 'danger')
        except Exception as e:
            flash(f'Fehler beim Löschen: {e}', 'danger')
        
        return redirect(url_for('production.calendar_new'))
    
    
    # =====================================================
    # CRM-SUCHE - Schnelles Finden von Telefonaten etc.
    # =====================================================
    
    @bp.route('/activities/search')
    @login_required
    def search_activities():
        """
        Durchsucht alle CRM-Aktivitäten (Telefonate, Besuche, E-Mails...)
        
        Durchsuchte Felder:
        - title (Betreff)
        - summary (Zusammenfassung)
        - content (Inhalt/Gesprächsnotizen)
        - contact_person (Ansprechpartner)
        - notes (Notizen)
        """
        try:
            from src.models import ProductionBlock
        except ImportError:
            return jsonify({'error': 'ProductionBlock nicht verfügbar'}), 500
        
        search_term = request.args.get('q', '').strip()
        customer_id = request.args.get('customer_id')
        block_type = request.args.get('type')
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        limit = request.args.get('limit', 50, type=int)
        
        # Basis-Query
        query = ProductionBlock.query.filter(ProductionBlock.is_active == True)
        
        # Volltextsuche
        if search_term:
            search_pattern = f'%{search_term}%'
            query = query.filter(
                or_(
                    ProductionBlock.title.ilike(search_pattern),
                    ProductionBlock.summary.ilike(search_pattern),
                    ProductionBlock.content.ilike(search_pattern),
                    ProductionBlock.contact_person.ilike(search_pattern),
                    ProductionBlock.notes.ilike(search_pattern)
                )
            )
        
        # Filter: Kunde
        if customer_id:
            query = query.filter(ProductionBlock.customer_id == customer_id)
        
        # Filter: Block-Typ
        if block_type:
            query = query.filter(ProductionBlock.block_type == block_type)
        
        # Filter: Datumsbereich
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                query = query.filter(ProductionBlock.start_date >= start_date)
            except:
                pass
        
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                query = query.filter(ProductionBlock.end_date <= end_date)
            except:
                pass
        
        # Sortieren und Limit
        blocks = query.order_by(ProductionBlock.start_date.desc(), ProductionBlock.start_time.desc()).limit(limit).all()
        
        # Ergebnisse formatieren
        results = []
        for block in blocks:
            results.append({
                'id': block.id,
                'type': block.block_type,
                'type_label': block.type_label,
                'icon': block.display_icon,
                'color': block.display_color,
                'title': block.title,
                'summary': block.summary[:200] if block.summary else None,
                'date': block.start_date.strftime('%d.%m.%Y'),
                'time': f"{block.start_time.strftime('%H:%M')} - {block.end_time.strftime('%H:%M')}",
                'customer_id': block.customer_id,
                'customer_name': block.customer.display_name if block.customer else None,
                'contact_person': block.contact_person,
                'outcome': block.outcome,
                'outcome_label': block.outcome_label,
                'has_follow_up': block.follow_up_date is not None,
                'needs_follow_up': block.needs_follow_up
            })
        
        return jsonify({
            'count': len(results),
            'results': results
        })
    
    
    @bp.route('/customer/<customer_id>/activities')
    @login_required
    def customer_activities(customer_id):
        """Alle Aktivitäten für einen bestimmten Kunden"""
        try:
            from src.models import ProductionBlock
        except ImportError:
            return jsonify({'error': 'ProductionBlock nicht verfügbar'}), 500
        
        customer = Customer.query.get_or_404(customer_id)
        
        # CRM-Typen
        crm_types = ProductionBlock.TYPE_CATEGORIES.get('crm', [])
        
        activities = ProductionBlock.query.filter(
            ProductionBlock.customer_id == customer_id,
            ProductionBlock.is_active == True
        ).order_by(
            ProductionBlock.start_date.desc(),
            ProductionBlock.start_time.desc()
        ).limit(100).all()
        
        results = []
        for act in activities:
            results.append({
                'id': act.id,
                'type': act.block_type,
                'type_label': act.type_label,
                'icon': act.display_icon,
                'title': act.title,
                'summary': act.summary,
                'date': act.start_date.strftime('%d.%m.%Y'),
                'time': act.start_time.strftime('%H:%M'),
                'contact_person': act.contact_person,
                'outcome': act.outcome_label,
                'needs_follow_up': act.needs_follow_up
            })
        
        return jsonify({
            'customer': {
                'id': customer.id,
                'name': customer.display_name
            },
            'count': len(results),
            'activities': results
        })
    
    
    @bp.route('/activities/follow-ups')
    @login_required
    def pending_follow_ups():
        """Alle fälligen Wiedervorlagen"""
        try:
            from src.models import ProductionBlock
        except ImportError:
            return jsonify({'error': 'ProductionBlock nicht verfügbar'}), 500
        
        today = date.today()
        
        follow_ups = ProductionBlock.query.filter(
            ProductionBlock.follow_up_date <= today,
            ProductionBlock.is_active == True
        ).order_by(ProductionBlock.follow_up_date).all()
        
        results = []
        for fu in follow_ups:
            days_overdue = (today - fu.follow_up_date).days
            
            results.append({
                'id': fu.id,
                'type': fu.block_type,
                'type_label': fu.type_label,
                'title': fu.title,
                'original_date': fu.start_date.strftime('%d.%m.%Y'),
                'follow_up_date': fu.follow_up_date.strftime('%d.%m.%Y'),
                'days_overdue': days_overdue,
                'customer_id': fu.customer_id,
                'customer_name': fu.customer.display_name if fu.customer else None,
                'contact_person': fu.contact_person,
                'follow_up_notes': fu.follow_up_notes
            })
        
        return jsonify({
            'count': len(results),
            'follow_ups': results
        })
    
    
    @bp.route('/api/suggest-machine')
    @login_required
    def api_suggest_machine():
        """Schlägt eine passende freie Maschine für einen Auftrag vor"""
        order_id = request.args.get('order_id')
        start_time_str = request.args.get('start_time')
        duration_hours = float(request.args.get('duration', 2))
        
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Auftrag nicht gefunden'}), 404
        
        try:
            start_dt = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M')
            end_dt = start_dt + timedelta(hours=duration_hours)
        except:
            return jsonify({'error': 'Ungültiges Zeitformat'}), 400
        
        machine_types = []
        if order.order_type in ['embroidery', 'combined']:
            machine_types.append('embroidery')
        if order.order_type in ['dtf', 'printing', 'combined']:
            machine_types.extend(['dtf', 'printing'])
        
        if not machine_types:
            machine_types = ['embroidery', 'dtf', 'printing']
        
        machines = Machine.query.filter(
            Machine.status == 'active',
            Machine.type.in_(machine_types)
        ).all()
        
        best_machine = None
        
        for machine in machines:
            conflict = ProductionSchedule.query.filter(
                and_(
                    ProductionSchedule.machine_id == machine.id,
                    ProductionSchedule.status != 'cancelled',
                    or_(
                        and_(
                            ProductionSchedule.scheduled_start <= start_dt,
                            ProductionSchedule.scheduled_end > start_dt
                        ),
                        and_(
                            ProductionSchedule.scheduled_start < end_dt,
                            ProductionSchedule.scheduled_end >= end_dt
                        ),
                        and_(
                            ProductionSchedule.scheduled_start >= start_dt,
                            ProductionSchedule.scheduled_end <= end_dt
                        )
                    )
                )
            ).first()
            
            if conflict:
                continue
            
            try:
                from src.models import ProductionBlock
                block_conflict = ProductionBlock.query.filter(
                    and_(
                        or_(
                            ProductionBlock.machine_id == machine.id,
                            ProductionBlock.machine_id.is_(None)
                        ),
                        ProductionBlock.start_date <= end_dt.date(),
                        ProductionBlock.end_date >= start_dt.date(),
                        ProductionBlock.is_active == True
                    )
                ).first()
                
                if block_conflict:
                    block_start = datetime.combine(block_conflict.start_date, block_conflict.start_time)
                    block_end = datetime.combine(block_conflict.end_date, block_conflict.end_time)
                    if not (end_dt <= block_start or start_dt >= block_end):
                        continue
            except:
                pass
            
            current_order = Order.query.filter_by(
                assigned_machine_id=machine.id,
                status='in_progress'
            ).first()
            
            if not current_order:
                best_machine = machine
                break
            elif best_machine is None:
                best_machine = machine
        
        if best_machine:
            return jsonify({
                'suggested_machine': {
                    'id': best_machine.id,
                    'name': best_machine.name,
                    'type': best_machine.type
                },
                'start_time': start_dt.isoformat(),
                'end_time': end_dt.isoformat()
            })
        else:
            return jsonify({
                'suggested_machine': None,
                'message': 'Keine passende freie Maschine gefunden'
            })
    
    
    @bp.route('/api/block/<block_id>')
    @login_required
    def api_block_details(block_id):
        """Details eines Kalender-Blocks abrufen (inkl. CRM-Daten)"""
        block_type = request.args.get('type', 'production')
        
        if block_type == 'production' or not str(block_id).startswith('block_'):
            try:
                schedule_id = int(str(block_id).replace('block_', ''))
            except:
                schedule_id = block_id
                
            schedule = ProductionSchedule.query.get(schedule_id)
            if schedule:
                is_multiday = schedule.scheduled_start.date() != schedule.scheduled_end.date()
                total_days = (schedule.scheduled_end.date() - schedule.scheduled_start.date()).days + 1
                
                return jsonify({
                    'id': schedule.id,
                    'schedule_id': schedule.id,
                    'block_type': 'production',
                    'order': {
                        'id': schedule.order.id if schedule.order else None,
                        'customer': schedule.order.customer.display_name if schedule.order and schedule.order.customer else None,
                        'type': schedule.order.order_type if schedule.order else None,
                        'stitch_count': schedule.order.stitch_count if schedule.order else None,
                        'rush': schedule.order.rush_order if schedule.order else False
                    } if schedule.order else None,
                    'machine': schedule.machine.name if schedule.machine else None,
                    'machine_id': schedule.machine_id,
                    'start': schedule.scheduled_start.strftime('%d.%m.%Y %H:%M'),
                    'end': schedule.scheduled_end.strftime('%d.%m.%Y %H:%M') if is_multiday else schedule.scheduled_end.strftime('%H:%M'),
                    'notes': schedule.notes,
                    'is_multiday': is_multiday,
                    'total_days': total_days
                })
        
        try:
            from src.models import ProductionBlock
            real_id = int(str(block_id).replace('block_', ''))
            block = ProductionBlock.query.get(real_id)
            if block:
                is_multiday = block.start_date != block.end_date
                
                return jsonify({
                    'id': block.id,
                    'block_type': block.block_type,
                    'type_label': block.type_label,
                    'title': block.title,
                    'icon': block.display_icon,
                    'color': block.display_color,
                    
                    # Zeitangaben
                    'start': f"{block.start_date.strftime('%d.%m.%Y')} {block.start_time.strftime('%H:%M')}",
                    'end': f"{block.end_date.strftime('%d.%m.%Y')} {block.end_time.strftime('%H:%M')}" if is_multiday else block.end_time.strftime('%H:%M'),
                    'is_multiday': is_multiday,
                    'duration_hours': block.duration_hours,
                    
                    # Verknüpfungen
                    'machine': block.machine.name if block.machine else None,
                    'customer_id': block.customer_id,
                    'customer_name': block.customer.display_name if block.customer else None,
                    'order_id': block.order_id,
                    
                    # CRM-Daten
                    'contact_person': block.contact_person,
                    'contact_phone': block.contact_phone,
                    'contact_email': block.contact_email,
                    'summary': block.summary,
                    'content': block.content,
                    'outcome': block.outcome,
                    'outcome_label': block.outcome_label,
                    
                    # Wiedervorlage
                    'follow_up_date': block.follow_up_date.strftime('%d.%m.%Y') if block.follow_up_date else None,
                    'follow_up_notes': block.follow_up_notes,
                    'needs_follow_up': block.needs_follow_up,
                    
                    # Sonstiges
                    'priority': block.priority,
                    'notes': block.notes,
                    'is_recurring': block.is_recurring,
                    'is_crm': block.is_crm_activity,
                    
                    # Audit
                    'created_at': block.created_at.strftime('%d.%m.%Y %H:%M') if block.created_at else None,
                    'created_by': block.created_by
                })
        except Exception as e:
            print(f"Fehler beim Laden des Blocks: {e}")
        
        return jsonify({'error': 'Block nicht gefunden'}), 404
