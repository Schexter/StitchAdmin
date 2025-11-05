"""
Activity Controller - Aktivitäts-Logs anzeigen
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from src.utils.activity_logger import get_recent_activities, get_user_activities, get_activities_by_action

# Blueprint erstellen
activity_bp = Blueprint('activities', __name__, url_prefix='/activities')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Bitte melden Sie sich an.', 'info')
            return redirect(url_for('login'))
        if not session.get('is_admin', False):
            flash('Keine Berechtigung für diese Aktion.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@activity_bp.route('/')
@admin_required
def index():
    """Aktivitäts-Log Übersicht"""
    # Filter-Parameter
    filter_user = request.args.get('user', '')
    filter_action = request.args.get('action', '')
    
    if filter_user:
        activities = get_user_activities(filter_user, limit=100)
    elif filter_action:
        activities = get_activities_by_action(filter_action, limit=100)
    else:
        activities = get_recent_activities(limit=100)
    
    return render_template('activities/index.html', 
                         activities=activities,
                         filter_user=filter_user,
                         filter_action=filter_action)

@activity_bp.route('/api/recent')
@admin_required
def api_recent():
    """API Endpoint für neueste Aktivitäten"""
    activities = get_recent_activities(limit=10)
    return jsonify(activities)