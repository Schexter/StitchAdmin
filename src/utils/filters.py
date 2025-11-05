"""
Custom Jinja2 Filters für StitchAdmin
"""

from datetime import datetime

def format_date(value):
    """Format a date value in German format DD.MM.YYYY"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.strftime('%d.%m.%Y')

def format_datetime(value):
    """Format a datetime value in German format DD.MM.YYYY HH:MM"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.strftime('%d.%m.%Y %H:%M')

def format_datetime_full(value):
    """Format a datetime value with seconds DD.MM.YYYY HH:MM:SS"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.strftime('%d.%m.%Y %H:%M:%S')

def format_time(value):
    """Format only time HH:MM"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.strftime('%H:%M')

def calculate_age(birth_date):
    """Calculate age from birth date"""
    if birth_date is None:
        return None
    today = datetime.today()
    age = today.year - birth_date.year
    # Überprüfe ob der Geburtstag dieses Jahr schon war
    if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
        age -= 1
    return age

def time_ago(value):
    """Convert datetime to relative time (e.g., '2 hours ago')"""
    if value is None:
        return ""
    
    if isinstance(value, str):
        return value
    
    now = datetime.now()
    diff = now - value
    
    if diff.days > 365:
        years = diff.days // 365
        return f"vor {years} Jahr{'en' if years > 1 else ''}"
    elif diff.days > 30:
        months = diff.days // 30
        return f"vor {months} Monat{'en' if months > 1 else ''}"
    elif diff.days > 0:
        return f"vor {diff.days} Tag{'en' if diff.days > 1 else ''}"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"vor {hours} Stunde{'n' if hours > 1 else ''}"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"vor {minutes} Minute{'n' if minutes > 1 else ''}"
    else:
        return "gerade eben"

def nl2br(value):
    """Convert newlines to HTML line breaks"""
    if value is None:
        return ""
    return value.replace('\n', '<br>')

def register_filters(app):
    """Register all custom filters with the Flask app"""
    app.jinja_env.filters['format_date'] = format_date
    app.jinja_env.filters['format_datetime'] = format_datetime
    app.jinja_env.filters['format_datetime_full'] = format_datetime_full
    app.jinja_env.filters['format_time'] = format_time
    app.jinja_env.filters['calculate_age'] = calculate_age
    app.jinja_env.filters['time_ago'] = time_ago
    app.jinja_env.filters['nl2br'] = nl2br
