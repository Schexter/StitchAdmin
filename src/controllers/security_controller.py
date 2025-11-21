"""
Security Controller - Passwort-Reset und Sicherheitsfunktionen
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
import json
import os
from src.utils.security import (
    generate_password_reset_token, 
    validate_password_reset_token,
    invalidate_password_reset_token,
    check_password_strength,
    generate_secure_password
)
from src.utils.email_service import send_password_reset_email
from src.utils.activity_logger import log_activity

# Blueprint erstellen
security_bp = Blueprint('security', __name__)

USERS_FILE = 'users.json'

def load_users():
    """Lade Benutzer aus JSON-Datei"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    """Speichere Benutzer in JSON-Datei"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

@security_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Passwort vergessen"""
    if request.method == 'POST':
        email = request.form.get('email')
        users = load_users()
        
        # Finde Benutzer mit dieser E-Mail
        username = None
        for user, data in users.items():
            if data.get('email') == email:
                username = user
                break
        
        if username:
            # Token generieren
            token = generate_password_reset_token(username)
            reset_link = url_for('security.reset_password', token=token, _external=True)
            
            # E-Mail senden
            if send_password_reset_email(email, username, reset_link):
                flash('Eine E-Mail mit Anweisungen wurde gesendet.', 'success')
                log_activity(username, 'password_reset_request', 'Passwort-Reset angefordert')
            else:
                flash('E-Mail konnte nicht gesendet werden. Bitte kontaktieren Sie den Administrator.', 'danger')
        else:
            # Aus Sicherheitsgründen immer dieselbe Meldung
            flash('Eine E-Mail mit Anweisungen wurde gesendet.', 'success')
        
        return redirect(url_for('auth.login'))
    
    return render_template('security/forgot_password.html')

@security_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Passwort zurücksetzen"""
    username = validate_password_reset_token(token)
    
    if not username:
        flash('Ungültiger oder abgelaufener Link.', 'danger')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('Passwörter stimmen nicht überein!', 'danger')
            return render_template('security/reset_password.html', token=token)
        
        # Passwort-Stärke prüfen
        from src.controllers.settings_controller import load_settings
        settings = load_settings()
        min_length = settings.get('password_min_length', 8)
        
        is_valid, messages = check_password_strength(new_password, min_length)
        if not is_valid:
            for msg in messages:
                flash(msg, 'warning')
            return render_template('security/reset_password.html', token=token)
        
        # Passwort aktualisieren
        users = load_users()
        users[username]['password_hash'] = generate_password_hash(new_password)
        save_users(users)
        
        # Token ungültig machen
        invalidate_password_reset_token(token)
        
        log_activity(username, 'password_reset', 'Passwort wurde zurückgesetzt')
        flash('Ihr Passwort wurde erfolgreich geändert. Sie können sich jetzt anmelden.', 'success')
        
        return redirect(url_for('auth.login'))
    
    return render_template('security/reset_password.html', token=token)

@security_bp.route('/generate-password')
def generate_password():
    """API Endpoint für Passwort-Generator"""
    from flask import jsonify
    password = generate_secure_password()
    return jsonify({'password': password})