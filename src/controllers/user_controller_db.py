"""
User Controller - PostgreSQL-Version
Benutzer-Verwaltung mit Datenbank
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from src.models import db, User, ActivityLog

# Blueprint erstellen
user_bp = Blueprint('users', __name__, url_prefix='/users')

def log_activity(action, details):
    """Aktivität in Datenbank protokollieren"""
    activity = ActivityLog(
        username=current_user.username,  # Geändert von 'user' zu 'username'
        action=action,
        details=details,
        ip_address=request.remote_addr
    )
    db.session.add(activity)
    db.session.commit()

@user_bp.route('/')
@login_required
def index():
    """Benutzer-Übersicht (nur für Admins)"""
    if not current_user.is_admin:
        flash('Keine Berechtigung für diese Seite!', 'danger')
        return redirect(url_for('dashboard'))
    
    # Alle Benutzer laden
    users_list = User.query.order_by(User.username).all()
    
    # In Dictionary umwandeln für Template-Kompatibilität
    users = {}
    for user in users_list:
        users[user.username] = user
    
    return render_template('users/index.html', users=users)

@user_bp.route('/profile')
@login_required
def profile():
    """Eigenes Profil anzeigen"""
    # Letzte Aktivitäten des Benutzers
    recent_activities = ActivityLog.query.filter_by(
        username=current_user.username  # Geändert von 'user' zu 'username'
    ).order_by(ActivityLog.timestamp.desc()).limit(10).all()
    
    return render_template('users/profile.html', 
                         user=current_user,
                         recent_activities=recent_activities)

@user_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Neuen Benutzer erstellen (nur für Admins)"""
    if not current_user.is_admin:
        flash('Keine Berechtigung!', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        is_admin = request.form.get('is_admin', False) == 'on'
        
        # Prüfen ob Benutzername bereits existiert
        if User.query.filter_by(username=username).first():
            flash('Benutzername bereits vergeben!', 'danger')
            return render_template('users/new.html')
        
        # Neuen Benutzer erstellen
        user = User(
            username=username,
            email=email,
            is_admin=is_admin,
            is_active=True
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Aktivität protokollieren
        log_activity('user_created', 
                    f'Benutzer erstellt: {username}')
        
        flash(f'Benutzer {username} wurde erstellt!', 'success')
        return redirect(url_for('users.index'))
    
    return render_template('users/new.html')

@user_bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(user_id):
    """Benutzer bearbeiten"""
    user = User.query.get_or_404(user_id)
    
    # Nur Admins oder der Benutzer selbst dürfen bearbeiten
    if not current_user.is_admin and current_user.id != user_id:
        flash('Keine Berechtigung!', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # Email aktualisieren
        user.email = request.form.get('email')
        
        # Passwort nur ändern wenn ausgefüllt
        new_password = request.form.get('new_password')
        if new_password:
            user.set_password(new_password)
        
        # Admin-Status nur von Admins änderbar
        if current_user.is_admin:
            user.is_admin = request.form.get('is_admin', False) == 'on'
            user.is_active = request.form.get('is_active', False) == 'on'
        
        db.session.commit()
        
        # Aktivität protokollieren
        log_activity('user_updated', 
                    f'Benutzer aktualisiert: {user.username}')
        
        flash('Benutzer wurde aktualisiert!', 'success')
        
        if current_user.id == user_id:
            return redirect(url_for('users.profile'))
        else:
            return redirect(url_for('users.index'))
    
    return render_template('users/edit.html', user=user)

@user_bp.route('/<int:user_id>/toggle-status', methods=['POST'])
@login_required
def toggle_status(user_id):
    """Benutzer aktivieren/deaktivieren"""
    if not current_user.is_admin:
        flash('Keine Berechtigung!', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    # Verhindere dass der Admin sich selbst deaktiviert
    if user.id == current_user.id:
        flash('Sie können sich nicht selbst deaktivieren!', 'danger')
        return redirect(url_for('users.index'))
    
    # Status umschalten
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'aktiviert' if user.is_active else 'deaktiviert'
    
    # Aktivität protokollieren
    log_activity('user_status_changed', 
                f'Benutzer {user.username} {status}')
    
    flash(f'Benutzer {user.username} wurde {status}!', 'success')
    return redirect(url_for('users.index'))

@user_bp.route('/<int:user_id>/delete', methods=['POST'])
@login_required
def delete(user_id):
    """Benutzer löschen"""
    if not current_user.is_admin:
        flash('Keine Berechtigung!', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    # Verhindere dass der Admin sich selbst löscht
    if user.id == current_user.id:
        flash('Sie können sich nicht selbst löschen!', 'danger')
        return redirect(url_for('users.index'))
    
    # Verhindere das Löschen des letzten Admins
    if user.is_admin:
        admin_count = User.query.filter_by(is_admin=True, is_active=True).count()
        if admin_count <= 1:
            flash('Der letzte Administrator kann nicht gelöscht werden!', 'danger')
            return redirect(url_for('users.index'))
    
    username = user.username
    
    # Aktivität protokollieren bevor gelöscht wird
    log_activity('user_deleted', 
                f'Benutzer gelöscht: {username}')
    
    # Benutzer löschen
    db.session.delete(user)
    db.session.commit()
    
    flash(f'Benutzer {username} wurde gelöscht!', 'success')
    return redirect(url_for('users.index'))

@user_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Eigenes Passwort ändern"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Aktuelles Passwort prüfen
        if not current_user.check_password(current_password):
            flash('Aktuelles Passwort ist falsch!', 'danger')
            return render_template('users/change_password.html')
        
        # Neue Passwörter prüfen
        if new_password != confirm_password:
            flash('Die neuen Passwörter stimmen nicht überein!', 'danger')
            return render_template('users/change_password.html')
        
        if len(new_password) < 6:
            flash('Das neue Passwort muss mindestens 6 Zeichen lang sein!', 'danger')
            return render_template('users/change_password.html')
        
        # Passwort ändern
        current_user.set_password(new_password)
        db.session.commit()
        
        # Aktivität protokollieren
        log_activity('password_changed', 
                    'Passwort geändert')
        
        flash('Ihr Passwort wurde erfolgreich geändert!', 'success')
        return redirect(url_for('users.profile'))
    
    return render_template('users/change_password.html')
