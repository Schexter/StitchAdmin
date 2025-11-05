"""
E-Mail Service für Benachrichtigungen
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os
from datetime import datetime

SETTINGS_FILE = 'system_settings.json'

def load_email_settings():
    """Lade E-Mail Einstellungen"""
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
            return {
                'smtp_server': settings.get('smtp_server', ''),
                'smtp_port': settings.get('smtp_port', 587),
                'smtp_username': settings.get('smtp_username', ''),
                'smtp_password': settings.get('smtp_password', ''),
                'smtp_from_email': settings.get('smtp_from_email', ''),
                'enable_email_notifications': settings.get('enable_email_notifications', False)
            }
    return None

def send_email(to_email, subject, body, html_body=None):
    """
    Sendet eine E-Mail
    
    Args:
        to_email: Empfänger E-Mail
        subject: Betreff
        body: Text-Inhalt
        html_body: HTML-Inhalt (optional)
    
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    settings = load_email_settings()
    
    if not settings or not settings['enable_email_notifications']:
        return False
    
    if not all([settings['smtp_server'], settings['smtp_username'], settings['smtp_password']]):
        print("E-Mail-Einstellungen unvollständig")
        return False
    
    try:
        # E-Mail erstellen
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = settings['smtp_from_email'] or settings['smtp_username']
        msg['To'] = to_email
        
        # Text-Teil
        text_part = MIMEText(body, 'plain')
        msg.attach(text_part)
        
        # HTML-Teil (falls vorhanden)
        if html_body:
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
        
        # SMTP-Verbindung
        with smtplib.SMTP(settings['smtp_server'], settings['smtp_port']) as server:
            server.starttls()
            server.login(settings['smtp_username'], settings['smtp_password'])
            server.send_message(msg)
        
        return True
        
    except Exception as e:
        print(f"E-Mail-Fehler: {e}")
        return False

def send_welcome_email(user_email, username):
    """Willkommens-E-Mail an neuen Benutzer"""
    subject = "Willkommen bei StitchAdmin"
    
    body = f"""
Hallo {username},

willkommen bei StitchAdmin! Ihr Konto wurde erfolgreich erstellt.

Sie können sich jetzt mit Ihrem Benutzernamen anmelden.

Mit freundlichen Grüßen
Ihr StitchAdmin Team
"""
    
    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif;">
    <h2>Willkommen bei StitchAdmin!</h2>
    <p>Hallo <strong>{username}</strong>,</p>
    <p>Ihr Konto wurde erfolgreich erstellt.</p>
    <p>Sie können sich jetzt mit Ihrem Benutzernamen anmelden.</p>
    <hr>
    <p><small>Diese E-Mail wurde automatisch generiert.</small></p>
</body>
</html>
"""
    
    return send_email(user_email, subject, body, html_body)

def send_password_reset_email(user_email, username, reset_link):
    """Passwort-Reset E-Mail"""
    subject = "Passwort zurücksetzen - StitchAdmin"
    
    body = f"""
Hallo {username},

Sie haben eine Passwort-Zurücksetzung angefordert.

Klicken Sie auf folgenden Link um Ihr Passwort zurückzusetzen:
{reset_link}

Dieser Link ist 24 Stunden gültig.

Falls Sie diese Anfrage nicht gestellt haben, ignorieren Sie diese E-Mail.

Mit freundlichen Grüßen
Ihr StitchAdmin Team
"""
    
    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif;">
    <h2>Passwort zurücksetzen</h2>
    <p>Hallo <strong>{username}</strong>,</p>
    <p>Sie haben eine Passwort-Zurücksetzung angefordert.</p>
    <p><a href="{reset_link}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Passwort zurücksetzen</a></p>
    <p><small>Dieser Link ist 24 Stunden gültig.</small></p>
    <hr>
    <p><small>Falls Sie diese Anfrage nicht gestellt haben, ignorieren Sie diese E-Mail.</small></p>
</body>
</html>
"""
    
    return send_email(user_email, subject, body, html_body)

def send_security_alert(user_email, username, alert_type, details):
    """Sicherheitswarnung senden"""
    subject = f"Sicherheitswarnung - {alert_type}"
    
    body = f"""
Hallo {username},

Wir haben eine ungewöhnliche Aktivität in Ihrem Konto festgestellt:

{alert_type}: {details}
Zeitpunkt: {datetime.now().strftime('%d.%m.%Y %H:%M')}

Falls Sie diese Aktion nicht durchgeführt haben, ändern Sie bitte umgehend Ihr Passwort.

Mit freundlichen Grüßen
Ihr StitchAdmin Team
"""
    
    return send_email(user_email, subject, body)

def send_admin_notification(subject, message):
    """Benachrichtigung an alle Admins"""
    from src.controllers.user_controller import load_users
    users = load_users()
    
    admin_emails = [user['email'] for user in users.values() 
                   if user.get('is_admin') and user.get('email')]
    
    success_count = 0
    for email in admin_emails:
        if send_email(email, f"[Admin] {subject}", message):
            success_count += 1
    
    return success_count