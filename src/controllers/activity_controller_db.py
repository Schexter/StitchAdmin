"""
Activity Controller - PostgreSQL-Version
Aktivitätsprotokoll mit Datenbank
"""

from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from src.models import db, ActivityLog

# Blueprint erstellen
activity_bp = Blueprint('activities', __name__, url_prefix='/activities')

@activity_bp.route('/')
@login_required
def index():
    """Aktivitäts-Übersicht"""
    # Nur Admins dürfen alle Aktivitäten sehen
    if not current_user.is_admin:
        # Normale Benutzer sehen nur ihre eigenen
        user_filter = current_user.username
    else:
        user_filter = request.args.get('user', '')
    
    action_filter = request.args.get('action', '')
    date_filter = request.args.get('date', '')
    
    # Query erstellen
    query = ActivityLog.query
    
    if user_filter:
        query = query.filter_by(user=user_filter)
    
    if action_filter:
        query = query.filter_by(action=action_filter)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d')
            start_date = filter_date
            end_date = filter_date + timedelta(days=1)
            query = query.filter(
                ActivityLog.timestamp >= start_date,
                ActivityLog.timestamp < end_date
            )
        except:
            pass
    
    # Nach Zeitstempel sortieren (neueste zuerst)
    activities = query.order_by(ActivityLog.timestamp.desc()).limit(500).all()
    
    # Verfügbare Filter-Optionen
    if current_user.is_admin:
        users = db.session.query(ActivityLog.user).distinct().filter(ActivityLog.user.isnot(None)).all()
        users = [u[0] for u in users if u[0]]
    else:
        users = [current_user.username]
    
    actions = db.session.query(ActivityLog.action).distinct().filter(ActivityLog.action.isnot(None)).all()
    actions = [a[0] for a in actions if a[0]]
    
    # Statistiken berechnen
    today = datetime.now().date()
    stats = {
        'today': ActivityLog.query.filter(
            db.func.date(ActivityLog.timestamp) == today
        ).count(),
        'week': ActivityLog.query.filter(
            ActivityLog.timestamp >= datetime.now() - timedelta(days=7)
        ).count(),
        'month': ActivityLog.query.filter(
            ActivityLog.timestamp >= datetime.now() - timedelta(days=30)
        ).count()
    }
    
    return render_template('activities/index.html',
                         activities=activities,
                         users=users,
                         actions=actions,
                         user_filter=user_filter,
                         action_filter=action_filter,
                         date_filter=date_filter,
                         stats=stats)

@activity_bp.route('/export')
@login_required
def export():
    """Aktivitäten exportieren (CSV)"""
    if not current_user.is_admin:
        flash('Keine Berechtigung!', 'danger')
        return redirect(url_for('activities.index'))
    
    # Filter anwenden
    user_filter = request.args.get('user', '')
    action_filter = request.args.get('action', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    query = ActivityLog.query
    
    if user_filter:
        query = query.filter_by(user=user_filter)
    
    if action_filter:
        query = query.filter_by(action=action_filter)
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(ActivityLog.timestamp >= from_date)
        except:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(ActivityLog.timestamp < to_date)
        except:
            pass
    
    activities = query.order_by(ActivityLog.timestamp.desc()).all()
    
    # CSV generieren
    import csv
    from io import StringIO
    from flask import make_response
    
    si = StringIO()
    cw = csv.writer(si)
    
    # Header
    cw.writerow(['Zeitstempel', 'Benutzer', 'Aktion', 'Details', 'IP-Adresse'])
    
    # Daten
    for activity in activities:
        cw.writerow([
            activity.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            activity.user,
            activity.action,
            activity.details,
            activity.ip_address
        ])
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=aktivitaeten_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    output.headers["Content-type"] = "text/csv"
    
    return output

@activity_bp.route('/cleanup', methods=['POST'])
@login_required
def cleanup():
    """Alte Aktivitäten löschen"""
    if not current_user.is_admin:
        flash('Keine Berechtigung!', 'danger')
        return redirect(url_for('activities.index'))
    
    days = int(request.form.get('days', 90))
    cutoff_date = datetime.now() - timedelta(days=days)
    
    # Alte Einträge löschen
    deleted = ActivityLog.query.filter(
        ActivityLog.timestamp < cutoff_date
    ).delete()
    
    db.session.commit()
    
    # Protokollieren
    from flask import flash
    activity = ActivityLog(
        user=current_user.username,
        action='activities_cleanup',
        details=f'{deleted} Aktivitäten älter als {days} Tage gelöscht',
        ip_address=request.remote_addr
    )
    db.session.add(activity)
    db.session.commit()
    
    flash(f'{deleted} alte Aktivitäten wurden gelöscht!', 'success')
    return redirect(url_for('activities.index'))

# Hilfsfunktionen für andere Module
def log_activity(user, action, details, ip_address=None):
    """Aktivität protokollieren (für andere Module)"""
    activity = ActivityLog(
        user=user,
        action=action,
        details=details,
        ip_address=ip_address or request.remote_addr
    )
    db.session.add(activity)
    db.session.commit()
