"""
User Controller - Benutzerverwaltung
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
from functools import wraps
import json
import os
from datetime import datetime

# Blueprint erstellen
user_bp = Blueprint('users', __name__, url_prefix='/users')

# Hilfsfunktionen
def load_users():
    """Lade Benutzer aus JSON-Datei"""
    if os.path.exists('users.json'):
        with open('users.json', 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    """Speichere Benutzer in JSON-Datei"""
    with open('users.json', 'w') as f:
        json.dump(users, f, indent=2)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Bitte melden Sie sich an.', 'info')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Bitte melden Sie sich an.', 'info')
            return redirect(url_for('auth.login'))
        if not session.get('is_admin', False):
            flash('Keine Berechtigung für diese Aktion.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@user_bp.route('/')
@admin_required
def index():
    """Liste aller Benutzer"""
    users = load_users()
    return render_template('users/index.html', users=users)

@user_bp.route('/new', methods=['GET', 'POST'])
@admin_required
def new():
    """Neuen Benutzer erstellen"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        is_admin = request.form.get('is_admin', False) == 'on'
        
        users = load_users()
        
        if username in users:
            flash('Benutzername bereits vergeben!', 'danger')
            return render_template('users/new.html')
        
        users[username] = {
            'username': username,
            'email': email,
            'password_hash': generate_password_hash(password),
            'is_admin': is_admin,
            'is_active': True,
            'created_at': datetime.now().isoformat()
        }
        
        save_users(users)
        
        # Aktivitäts-Log
        from src.utils.activity_logger import log_activity
        log_activity(session['username'], 'create_user', f'Benutzer {username} wurde erstellt')
        
        # Willkommens-E-Mail senden
        from src.utils.email_service import send_welcome_email
        if send_welcome_email(email, username):
            flash(f'Benutzer {username} wurde erstellt und Willkommens-E-Mail gesendet!', 'success')
        else:
            flash(f'Benutzer {username} wurde erstellt!', 'success')
        return redirect(url_for('users.index'))
    
    return render_template('users/new.html')

@user_bp.route('/<username>/edit', methods=['GET', 'POST'])
@admin_required
def edit(username):
    """Benutzer bearbeiten"""
    users = load_users()
    user = users.get(username)
    
    if not user:
        flash('Benutzer nicht gefunden!', 'danger')
        return redirect(url_for('users.index'))
    
    if request.method == 'POST':
        user['email'] = request.form.get('email', user['email'])
        user['is_admin'] = request.form.get('is_admin', False) == 'on'
        user['is_active'] = request.form.get('is_active', False) == 'on'
        
        if request.form.get('password'):
            user['password_hash'] = generate_password_hash(request.form.get('password'))
        
        save_users(users)
        
        # Aktivitäts-Log
        from src.utils.activity_logger import log_activity
        log_activity(session['username'], 'update_user', f'Benutzer {username} wurde aktualisiert')
        
        flash(f'Benutzer {username} wurde aktualisiert!', 'success')
        return redirect(url_for('users.index'))
    
    return render_template('users/edit.html', user=user)

@user_bp.route('/<username>/delete', methods=['POST'])
@admin_required
def delete(username):
    """Benutzer löschen"""
    if username == session.get('username'):
        flash('Sie können sich nicht selbst löschen!', 'danger')
        return redirect(url_for('users.index'))
    
    users = load_users()
    if username in users:
        del users[username]
        save_users(users)
        
        # Aktivitäts-Log
        from src.utils.activity_logger import log_activity
        log_activity(session['username'], 'delete_user', f'Benutzer {username} wurde gelöscht')
        
        flash(f'Benutzer {username} wurde gelöscht!', 'success')
    else:
        flash('Benutzer nicht gefunden!', 'danger')
    
    return redirect(url_for('users.index'))

@user_bp.route('/profile')
@login_required
def profile():
    """Benutzerprofil anzeigen"""
    users = load_users()
    user = users.get(session['username'])
    return render_template('users/profile.html', user=user)

@user_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Eigenes Profil bearbeiten"""
    users = load_users()
    user = users.get(session['username'])
    
    if request.method == 'POST':
        user['email'] = request.form.get('email', user['email'])
        
        # Passwort nur ändern wenn neues eingegeben wurde
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        
        if new_password:
            from werkzeug.security import check_password_hash
            if check_password_hash(user['password_hash'], old_password):
                user['password_hash'] = generate_password_hash(new_password)
                flash('Passwort wurde geändert!', 'success')
            else:
                flash('Altes Passwort ist falsch!', 'danger')
                return render_template('users/edit_profile.html', user=user)
        
        save_users(users)
        flash('Profil wurde aktualisiert!', 'success')
        return redirect(url_for('users.profile'))
    
    return render_template('users/edit_profile.html', user=user)