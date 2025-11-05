"""
Erweiterte Sicherheitsfunktionen
"""

import json
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
import secrets
import string

LOGIN_ATTEMPTS_FILE = 'login_attempts.json'
PASSWORD_RESET_TOKENS_FILE = 'password_reset_tokens.json'

def load_login_attempts():
    """Lade Login-Versuche"""
    if os.path.exists(LOGIN_ATTEMPTS_FILE):
        with open(LOGIN_ATTEMPTS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_login_attempts(attempts):
    """Speichere Login-Versuche"""
    with open(LOGIN_ATTEMPTS_FILE, 'w') as f:
        json.dump(attempts, f, indent=2)

def check_login_attempts(username, max_attempts=5):
    """
    Prüfe ob Benutzer zu viele Login-Versuche hatte
    
    Returns:
        tuple: (is_blocked, remaining_time_minutes)
    """
    attempts = load_login_attempts()
    
    if username not in attempts:
        return False, 0
    
    user_attempts = attempts[username]
    
    # Prüfe ob Sperrzeit abgelaufen ist (15 Minuten)
    if 'blocked_until' in user_attempts:
        blocked_until = datetime.fromisoformat(user_attempts['blocked_until'])
        if datetime.now() < blocked_until:
            remaining = (blocked_until - datetime.now()).seconds // 60
            return True, remaining
        else:
            # Sperrzeit abgelaufen, zurücksetzen
            attempts[username] = {'count': 0}
            save_login_attempts(attempts)
            return False, 0
    
    # Prüfe Anzahl der Versuche
    if user_attempts.get('count', 0) >= max_attempts:
        # Blockiere für 15 Minuten
        user_attempts['blocked_until'] = (datetime.now() + timedelta(minutes=15)).isoformat()
        save_login_attempts(attempts)
        return True, 15
    
    return False, 0

def record_login_attempt(username, success=False):
    """Protokolliere Login-Versuch"""
    attempts = load_login_attempts()
    
    if success:
        # Bei erfolgreichem Login zurücksetzen
        if username in attempts:
            del attempts[username]
    else:
        # Fehlgeschlagener Versuch
        if username not in attempts:
            attempts[username] = {'count': 0}
        
        attempts[username]['count'] += 1
        attempts[username]['last_attempt'] = datetime.now().isoformat()
    
    save_login_attempts(attempts)

def generate_secure_password(length=12):
    """Generiere sicheres Passwort"""
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(characters) for _ in range(length))
    return password

def check_password_strength(password, min_length=8):
    """
    Prüfe Passwort-Stärke
    
    Returns:
        tuple: (is_valid, messages)
    """
    messages = []
    
    if len(password) < min_length:
        messages.append(f"Passwort muss mindestens {min_length} Zeichen lang sein")
    
    if not any(c.isupper() for c in password):
        messages.append("Passwort muss mindestens einen Großbuchstaben enthalten")
    
    if not any(c.islower() for c in password):
        messages.append("Passwort muss mindestens einen Kleinbuchstaben enthalten")
    
    if not any(c.isdigit() for c in password):
        messages.append("Passwort muss mindestens eine Zahl enthalten")
    
    if not any(c in string.punctuation for c in password):
        messages.append("Passwort muss mindestens ein Sonderzeichen enthalten")
    
    return len(messages) == 0, messages

def generate_password_reset_token(username):
    """Generiere Passwort-Reset-Token"""
    token = secrets.token_urlsafe(32)
    
    tokens = {}
    if os.path.exists(PASSWORD_RESET_TOKENS_FILE):
        with open(PASSWORD_RESET_TOKENS_FILE, 'r') as f:
            tokens = json.load(f)
    
    tokens[token] = {
        'username': username,
        'created_at': datetime.now().isoformat(),
        'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
    }
    
    with open(PASSWORD_RESET_TOKENS_FILE, 'w') as f:
        json.dump(tokens, f, indent=2)
    
    return token

def validate_password_reset_token(token):
    """
    Validiere Passwort-Reset-Token
    
    Returns:
        username oder None
    """
    if not os.path.exists(PASSWORD_RESET_TOKENS_FILE):
        return None
    
    with open(PASSWORD_RESET_TOKENS_FILE, 'r') as f:
        tokens = json.load(f)
    
    if token not in tokens:
        return None
    
    token_data = tokens[token]
    expires_at = datetime.fromisoformat(token_data['expires_at'])
    
    if datetime.now() > expires_at:
        # Token abgelaufen
        del tokens[token]
        with open(PASSWORD_RESET_TOKENS_FILE, 'w') as f:
            json.dump(tokens, f, indent=2)
        return None
    
    return token_data['username']

def invalidate_password_reset_token(token):
    """Token nach Verwendung löschen"""
    if not os.path.exists(PASSWORD_RESET_TOKENS_FILE):
        return
    
    with open(PASSWORD_RESET_TOKENS_FILE, 'r') as f:
        tokens = json.load(f)
    
    if token in tokens:
        del tokens[token]
        
    with open(PASSWORD_RESET_TOKENS_FILE, 'w') as f:
        json.dump(tokens, f, indent=2)

def cleanup_expired_tokens():
    """Aufräumen abgelaufener Tokens"""
    if not os.path.exists(PASSWORD_RESET_TOKENS_FILE):
        return
    
    with open(PASSWORD_RESET_TOKENS_FILE, 'r') as f:
        tokens = json.load(f)
    
    current_time = datetime.now()
    expired_tokens = []
    
    for token, data in tokens.items():
        if datetime.fromisoformat(data['expires_at']) < current_time:
            expired_tokens.append(token)
    
    for token in expired_tokens:
        del tokens[token]
    
    with open(PASSWORD_RESET_TOKENS_FILE, 'w') as f:
        json.dump(tokens, f, indent=2)