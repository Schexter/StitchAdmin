"""
Kunden-Historie Verwaltung
"""

import json
import os
from datetime import datetime

CUSTOMER_HISTORY_FILE = 'customer_history.json'

def load_customer_history():
    """Lade Kunden-Historie aus JSON-Datei"""
    if os.path.exists(CUSTOMER_HISTORY_FILE):
        with open(CUSTOMER_HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_customer_history(history):
    """Speichere Kunden-Historie in JSON-Datei"""
    with open(CUSTOMER_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def add_customer_history(customer_id, action, details, user='system'):
    """Füge einen Eintrag zur Kunden-Historie hinzu"""
    history = load_customer_history()
    
    # Initialisiere Historie für Kunde falls nicht vorhanden
    if customer_id not in history:
        history[customer_id] = []
    
    # Erstelle Historie-Eintrag
    entry = {
        'timestamp': datetime.now().isoformat(),
        'action': action,
        'details': details,
        'user': user
    }
    
    # Füge Eintrag hinzu (neueste zuerst)
    history[customer_id].insert(0, entry)
    
    # Begrenze Historie auf 100 Einträge pro Kunde
    if len(history[customer_id]) > 100:
        history[customer_id] = history[customer_id][:100]
    
    save_customer_history(history)

def get_customer_history(customer_id, limit=20):
    """Hole Historie eines Kunden"""
    history = load_customer_history()
    
    if customer_id in history:
        return history[customer_id][:limit]
    
    return []

def clear_customer_history(customer_id):
    """Lösche Historie eines Kunden"""
    history = load_customer_history()
    
    if customer_id in history:
        del history[customer_id]
        save_customer_history(history)