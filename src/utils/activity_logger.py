"""
Aktivitäts-Logger für Audit-Trail
"""

import json
import os
from datetime import datetime
from pathlib import Path

ACTIVITY_LOG_FILE = 'activity_log.json'

def log_activity(username, action, details, ip_address=None):
    """
    Protokolliert Benutzeraktivitäten
    
    Args:
        username: Benutzername
        action: Aktion (login, logout, create_user, etc.)
        details: Detaillierte Beschreibung
        ip_address: IP-Adresse (optional)
    """
    # Lade existierende Logs
    logs = load_activity_logs()
    
    # Erstelle neuen Log-Eintrag
    log_entry = {
        'id': len(logs) + 1,
        'timestamp': datetime.now().isoformat(),
        'username': username,
        'action': action,
        'details': details,
        'ip_address': ip_address or 'N/A'
    }
    
    # Füge neuen Eintrag hinzu
    logs.append(log_entry)
    
    # Speichere Logs (behalte nur die letzten 1000 Einträge)
    if len(logs) > 1000:
        logs = logs[-1000:]
    
    save_activity_logs(logs)

def load_activity_logs():
    """Lade Aktivitäts-Logs aus Datei"""
    if os.path.exists(ACTIVITY_LOG_FILE):
        try:
            with open(ACTIVITY_LOG_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_activity_logs(logs):
    """Speichere Aktivitäts-Logs in Datei"""
    with open(ACTIVITY_LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=2)

def get_user_activities(username, limit=50):
    """Hole Aktivitäten eines bestimmten Benutzers"""
    logs = load_activity_logs()
    user_logs = [log for log in logs if log['username'] == username]
    return user_logs[-limit:]  # Neueste zuerst

def get_recent_activities(limit=50):
    """Hole die neuesten Aktivitäten"""
    logs = load_activity_logs()
    return logs[-limit:][::-1]  # Neueste zuerst

def get_activities_by_action(action, limit=50):
    """Hole Aktivitäten nach Aktionstyp"""
    logs = load_activity_logs()
    action_logs = [log for log in logs if log['action'] == action]
    return action_logs[-limit:][::-1]  # Neueste zuerst