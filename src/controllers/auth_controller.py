"""
Auth Controller - Authentifizierung und Benutzeranmeldung
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from src.models import db, User, ActivityLog

# Blueprint erstellen
auth_bp = Blueprint('auth', __name__)

def log_activity(action, details, username=None):
    """Aktivität in Datenbank protokollieren"""
    activity = ActivityLog(
        username=username or (current_user.username if current_user.is_authenticated else 'anonymous'),
        action=action,
        details=details,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', '')[:200]
    )
    db.session.add(activity)
    db.session.commit()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login-Seite und -Verarbeitung"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False) == 'on'
        
        # Benutzer suchen
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Ihr Konto ist deaktiviert. Bitte kontaktieren Sie den Administrator.', 'danger')
                log_activity('login_failed', f'Deaktiviertes Konto: {username}', username)
                return render_template('login.html')
            
            # Erfolgreiche Anmeldung
            login_user(user, remember=remember)
            user.last_login = db.session.query(db.func.now()).scalar()
            db.session.commit()
            
            log_activity('login', f'Erfolgreiche Anmeldung', user.username)
            
            # Weiterleitung zur gewünschten Seite oder Dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Ungültiger Benutzername oder Passwort', 'danger')
            log_activity('login_failed', f'Fehlgeschlagene Anmeldung für: {username}', username)
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Benutzer abmelden"""
    username = current_user.username
    logout_user()
    log_activity('logout', 'Benutzer abgemeldet', username)
    flash('Sie wurden erfolgreich abgemeldet.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    """Benutzerprofil anzeigen"""
    return render_template('users/profile.html', user=current_user)
