"""
Utility-Funktionen für Controller
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime
from flask import flash


def parse_date_from_form(date_string, field_name="Datum"):
    """
    Konvertiert einen Datums-String aus einem HTML-Formular zu einem Python date-Objekt
    
    Args:
        date_string (str): Datum im Format 'YYYY-MM-DD' oder leer/None
        field_name (str): Name des Feldes für Fehlermeldungen
        
    Returns:
        date|None: Python date-Objekt oder None wenn leer/ungültig
    """
    if not date_string or date_string.strip() == '':
        return None
    
    try:
        # Datum von 'YYYY-MM-DD' String zu Python date konvertieren
        return datetime.strptime(date_string.strip(), '%Y-%m-%d').date()
    except ValueError:
        # Bei ungültigem Datum: Warnung ausgeben und None zurückgeben
        flash(f'Ungültiges Datumsformat für {field_name}: {date_string}. Verwendung von YYYY-MM-DD erwartet.', 'warning')
        return None


def parse_datetime_from_form(datetime_string, field_name="Datum/Zeit"):
    """
    Konvertiert einen DateTime-String aus einem HTML-Formular zu einem Python datetime-Objekt
    
    Args:
        datetime_string (str): DateTime im Format 'YYYY-MM-DDTHH:MM' oder leer/None
        field_name (str): Name des Feldes für Fehlermeldungen
        
    Returns:
        datetime|None: Python datetime-Objekt oder None wenn leer/ungültig
    """
    if not datetime_string or datetime_string.strip() == '':
        return None
    
    try:
        # DateTime von HTML5 datetime-local Format konvertieren
        return datetime.strptime(datetime_string.strip(), '%Y-%m-%dT%H:%M')
    except ValueError:
        # Fallback: Versuche nur Datum ohne Zeit
        try:
            date_obj = datetime.strptime(datetime_string.strip(), '%Y-%m-%d')
            return date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
        except ValueError:
            flash(f'Ungültiges Datum/Zeit-Format für {field_name}: {datetime_string}', 'warning')
            return None


def parse_float_from_form(value_string, field_name="Wert", default=None):
    """
    Konvertiert einen String zu einem Float-Wert mit Fehlerbehandlung
    
    Args:
        value_string (str): Wert als String
        field_name (str): Name des Feldes für Fehlermeldungen
        default: Standardwert wenn Konvertierung fehlschlägt
        
    Returns:
        float|None: Konvertierter Wert oder default
    """
    if not value_string or value_string.strip() == '':
        return default
    
    try:
        # Deutsche Dezimalzahlen unterstützen (Komma zu Punkt)
        cleaned_value = value_string.strip().replace(',', '.')
        return float(cleaned_value)
    except ValueError:
        flash(f'Ungültiger Zahlenwert für {field_name}: {value_string}', 'warning')
        return default


def parse_int_from_form(value_string, field_name="Wert", default=None):
    """
    Konvertiert einen String zu einem Integer-Wert mit Fehlerbehandlung
    
    Args:
        value_string (str): Wert als String
        field_name (str): Name des Feldes für Fehlermeldungen
        default: Standardwert wenn Konvertierung fehlschlägt
        
    Returns:
        int|None: Konvertierter Wert oder default
    """
    if not value_string or value_string.strip() == '':
        return default
    
    try:
        return int(value_string.strip())
    except ValueError:
        flash(f'Ungültiger Ganzzahlwert für {field_name}: {value_string}', 'warning')
        return default


def safe_get_form_value(form_data, field_name, default='', strip=True):
    """
    Sichere Extraktion von Formulardaten mit Standardwerten
    
    Args:
        form_data: Flask request.form Objekt
        field_name (str): Name des Formularfeldes
        default: Standardwert wenn Feld nicht existiert
        strip (bool): Ob Whitespace entfernt werden soll
        
    Returns:
        str: Formulardaten oder Standardwert
    """
    value = form_data.get(field_name, default)
    if strip and isinstance(value, str):
        return value.strip()
    return value


def validate_required_fields(form_data, required_fields):
    """
    Validiert ob alle erforderlichen Felder ausgefüllt sind
    
    Args:
        form_data: Flask request.form Objekt
        required_fields (list): Liste der erforderlichen Feldnamen
        
    Returns:
        bool: True wenn alle Felder ausgefüllt, sonst False (mit Flash-Nachricht)
    """
    missing_fields = []
    
    for field in required_fields:
        value = form_data.get(field, '').strip()
        if not value:
            missing_fields.append(field)
    
    if missing_fields:
        field_names = ', '.join(missing_fields)
        flash(f'Folgende Pflichtfelder sind nicht ausgefüllt: {field_names}', 'error')
        return False
    
    return True


# Beispiel-Anwendung in Controllern:
"""
from src.utils.form_helpers import parse_date_from_form, safe_get_form_value

# In Controller-Funktion:
customer.birth_date = parse_date_from_form(request.form.get('birth_date'), 'Geburtsdatum')
customer.first_name = safe_get_form_value(request.form, 'first_name')
"""
