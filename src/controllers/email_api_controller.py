# -*- coding: utf-8 -*-
"""
E-Mail API Controller
StitchAdmin 2.0
Erstellt von Hans Hahn - Alle Rechte vorbehalten

API-Endpoints fuer E-Mail-Funktionen (Outlook, SMTP, etc.)
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
import logging

logger = logging.getLogger(__name__)

# Blueprint erstellen
email_api_bp = Blueprint('email_api', __name__, url_prefix='/api/email')


@email_api_bp.route('/check-outlook')
@login_required
def check_outlook():
    """
    Prueft ob Outlook verfuegbar ist und gibt Account-Info zurueck
    """
    try:
        import platform
        current_platform = platform.system()
        logger.info(f"Check-Outlook: Plattform = {current_platform}")

        from src.services.outlook_service import OutlookService, OUTLOOK_AVAILABLE
        logger.info(f"Check-Outlook: OUTLOOK_AVAILABLE = {OUTLOOK_AVAILABLE}")

        # Prüfe zuerst die Plattform
        if current_platform != 'Windows':
            logger.warning(f"Nicht-Windows Plattform erkannt: {current_platform}")
            return jsonify({
                'available': False,
                'message': f'Outlook-Integration nur unter Windows. Aktuelle Plattform: {current_platform}'
            })

        if not OUTLOOK_AVAILABLE:
            logger.warning("win32com nicht verfuegbar")
            return jsonify({
                'available': False,
                'message': 'win32com nicht installiert (pip install pywin32 unter Windows)'
            })

        service = OutlookService()
        is_avail = service.is_available()
        logger.info(f"Check-Outlook: service.is_available() = {is_avail}")

        if not is_avail:
            return jsonify({
                'available': False,
                'message': 'Outlook ist nicht installiert oder nicht erreichbar'
            })

        # Versuche Account-Info zu holen
        if service.connect():
            email = service.get_default_account_email()
            accounts = service.list_accounts()

            return jsonify({
                'available': True,
                'email': email,
                'accounts': accounts,
                'message': 'Outlook ist verfuegbar'
            })

        return jsonify({
            'available': False,
            'message': 'Outlook konnte nicht verbunden werden'
        })

    except ImportError:
        return jsonify({
            'available': False,
            'message': 'win32com nicht installiert (nur auf Windows verfuegbar)'
        })
    except Exception as e:
        logger.error(f"Outlook-Check fehlgeschlagen: {e}")
        return jsonify({
            'available': False,
            'message': str(e)
        })


@email_api_bp.route('/test-outlook', methods=['POST'])
@login_required
def test_outlook():
    """
    Erstellt eine Test-E-Mail in Outlook
    """
    try:
        from src.services.outlook_service import OutlookService, OUTLOOK_AVAILABLE
        import traceback
        import platform

        current_platform = platform.system()
        print(f"[TEST-OUTLOOK] Plattform = {current_platform}")

        # Prüfe zuerst die Plattform
        if current_platform != 'Windows':
            logger.warning(f"Test-Outlook: Nicht-Windows Plattform: {current_platform}")
            return jsonify({
                'success': False,
                'message': f'Outlook-Integration ist nur unter Windows verfuegbar. Aktuelle Plattform: {current_platform}. Wenn Sie WSL nutzen, starten Sie StitchAdmin direkt unter Windows.'
            })

        print(f"[TEST-OUTLOOK] OUTLOOK_AVAILABLE = {OUTLOOK_AVAILABLE}")
        if not OUTLOOK_AVAILABLE:
            return jsonify({
                'success': False,
                'message': 'win32com ist nicht installiert. Bitte fuehren Sie "pip install pywin32" aus und starten Sie die App unter Windows (nicht WSL).'
            })

        service = OutlookService()

        is_avail = service.is_available()
        print(f"[TEST-OUTLOOK] is_available = {is_avail}")
        if not is_avail:
            return jsonify({
                'success': False,
                'message': 'Outlook ist nicht verfuegbar. Stellen Sie sicher, dass Outlook installiert und geoeffnet ist.'
            })

        # Verbindung explizit herstellen
        connected = service.connect()
        print(f"[TEST-OUTLOOK] connected = {connected}")
        if not connected:
            return jsonify({
                'success': False,
                'message': 'Konnte keine Verbindung zu Outlook herstellen. Bitte Outlook oeffnen und erneut versuchen.'
            })

        # Test-E-Mail erstellen (wird nur angezeigt, nicht gesendet)
        print("[TEST-OUTLOOK] Erstelle Test-E-Mail...")
        try:
            success = service.create_email(
                to='test@example.com',  # Dummy-Adresse damit Outlook es akzeptiert
                subject='StitchAdmin Test-E-Mail',
                body='''<html>
<body style="font-family: Arial, sans-serif;">
<h2>StitchAdmin E-Mail-Test</h2>
<p>Diese Test-E-Mail wurde von StitchAdmin erstellt um die Outlook-Integration zu pruefen.</p>
<p>Wenn Sie diese E-Mail sehen, funktioniert die Outlook-Integration korrekt!</p>
<p><strong>Sie koennen diese E-Mail einfach schliessen oder den Empfaenger aendern und absenden.</strong></p>
<hr>
<p style="color: #666; font-size: 12px;">
Diese E-Mail wurde automatisch generiert.
</p>
</body>
</html>''',
                html_body=True,
                display_first=True  # Nur anzeigen, nicht senden
            )
            print(f"[TEST-OUTLOOK] create_email returned {success}")
        except Exception as create_error:
            print(f"[TEST-OUTLOOK] create_email Exception: {create_error}")
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'Fehler beim Erstellen der E-Mail: {str(create_error)}'
            })

        if success:
            return jsonify({
                'success': True,
                'message': 'Test-E-Mail wurde in Outlook geoeffnet. Schauen Sie in Ihre Taskleiste - das Outlook-Fenster sollte dort erscheinen.'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Fehler beim Erstellen der Test-E-Mail. Bitte pruefen Sie ob Outlook laeuft.'
            })

    except Exception as e:
        logger.error(f"Outlook-Test fehlgeschlagen: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Fehler: {str(e)}'
        })


@email_api_bp.route('/send-invoice/<int:rechnung_id>', methods=['POST'])
@login_required
def send_invoice_email(rechnung_id):
    """
    Versendet eine Rechnung per E-Mail
    """
    try:
        from src.models.rechnungsmodul import Rechnung
        from src.models.company_settings import CompanySettings
        from src.services.outlook_service import OutlookService
        import tempfile
        import os

        # Rechnung laden
        rechnung = Rechnung.query.get_or_404(rechnung_id)
        settings = CompanySettings.get_settings()

        # Empfaenger-E-Mail
        to_email = rechnung.kunde_email
        if not to_email:
            return jsonify({
                'success': False,
                'message': 'Keine E-Mail-Adresse fuer diesen Kunden hinterlegt'
            }), 400

        # PDF generieren
        from src.services.zugpferd_service import ZugpferdService
        zugpferd_service = ZugpferdService()
        pdf_content = zugpferd_service.create_invoice_from_rechnung(rechnung)

        # PDF temporaer speichern
        temp_dir = tempfile.mkdtemp()
        pdf_path = os.path.join(temp_dir, f'{rechnung.rechnungsnummer}.pdf')
        with open(pdf_path, 'wb') as f:
            f.write(pdf_content)

        # E-Mail-Methode bestimmen
        email_method = settings.email_method or 'outlook'

        if email_method == 'outlook':
            # Outlook-Versand
            service = OutlookService()

            if not service.is_available():
                return jsonify({
                    'success': False,
                    'message': 'Outlook ist nicht verfuegbar'
                })

            # Betreff mit Platzhaltern ersetzen
            subject = (settings.invoice_email_subject or 'Rechnung {invoice_number}').format(
                invoice_number=rechnung.rechnungsnummer,
                customer_name=rechnung.kunde_name,
                amount=f'{float(rechnung.brutto_gesamt or 0):,.2f}'
            )

            # Body mit Platzhaltern oder Standard
            if settings.invoice_email_template:
                body = settings.invoice_email_template.format(
                    invoice_number=rechnung.rechnungsnummer,
                    customer_name=rechnung.kunde_name,
                    amount=f'{float(rechnung.brutto_gesamt or 0):,.2f}'
                )
                html_body = False
            else:
                # Standard-HTML-Body
                body = f'''
<html>
<body style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
<p>Sehr geehrte Damen und Herren,</p>

<p>anbei erhalten Sie unsere Rechnung <strong>{rechnung.rechnungsnummer}</strong> ueber <strong>{float(rechnung.brutto_gesamt or 0):,.2f} EUR</strong>.</p>

<p>Bei Fragen stehen wir Ihnen gerne zur Verfuegung.</p>

<p>Mit freundlichen Gruessen</p>
</body>
</html>'''
                html_body = True

            # E-Mail erstellen (anzeigen, nicht direkt senden)
            display_first = request.json.get('display_first', True) if request.is_json else True

            success = service.create_email(
                to=to_email,
                subject=subject,
                body=body,
                attachments=[pdf_path],
                html_body=html_body,
                display_first=display_first
            )

            if success:
                return jsonify({
                    'success': True,
                    'message': 'E-Mail wurde in Outlook geoeffnet' if display_first else 'E-Mail wurde gesendet'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Fehler beim Erstellen der E-Mail'
                })

        elif email_method == 'mailto':
            # mailto-Link zurueckgeben
            import urllib.parse
            subject = (settings.invoice_email_subject or 'Rechnung {invoice_number}').format(
                invoice_number=rechnung.rechnungsnummer,
                customer_name=rechnung.kunde_name,
                amount=f'{float(rechnung.brutto_gesamt or 0):,.2f}'
            )
            body = f'Sehr geehrte Damen und Herren,\n\nanbei erhalten Sie unsere Rechnung {rechnung.rechnungsnummer}.\n\nMit freundlichen Gruessen'

            mailto_url = f"mailto:{to_email}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"

            return jsonify({
                'success': True,
                'mailto_url': mailto_url,
                'pdf_path': pdf_path,
                'message': 'Bitte fuegen Sie die PDF-Datei manuell als Anhang hinzu'
            })

        else:
            # SMTP-Versand (TODO: implementieren)
            return jsonify({
                'success': False,
                'message': 'SMTP-Versand noch nicht implementiert'
            })

    except Exception as e:
        logger.error(f"Rechnungsversand fehlgeschlagen: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@email_api_bp.route('/send-reminder/<int:rechnung_id>', methods=['POST'])
@login_required
def send_reminder_email(rechnung_id):
    """
    Versendet eine Zahlungserinnerung per E-Mail
    """
    try:
        from src.models.rechnungsmodul import Rechnung
        from src.models.company_settings import CompanySettings
        from src.services.outlook_service import OutlookService
        from datetime import date

        # Rechnung laden
        rechnung = Rechnung.query.get_or_404(rechnung_id)
        settings = CompanySettings.get_settings()

        # Empfaenger-E-Mail
        to_email = rechnung.kunde_email
        if not to_email:
            return jsonify({
                'success': False,
                'message': 'Keine E-Mail-Adresse fuer diesen Kunden hinterlegt'
            }), 400

        # Mahnstufe aus Request
        reminder_level = request.json.get('reminder_level', 1) if request.is_json else 1

        # Tage ueberfaellig berechnen
        days_overdue = 0
        if rechnung.faelligkeitsdatum:
            days_overdue = (date.today() - rechnung.faelligkeitsdatum).days

        # E-Mail-Methode
        email_method = settings.email_method or 'outlook'

        if email_method == 'outlook':
            service = OutlookService()

            if not service.is_available():
                return jsonify({
                    'success': False,
                    'message': 'Outlook ist nicht verfuegbar'
                })

            success = service.send_reminder_email(
                to=to_email,
                invoice_number=rechnung.rechnungsnummer,
                customer_name=rechnung.kunde_name,
                amount=float(rechnung.brutto_gesamt or 0),
                original_due_date=rechnung.faelligkeitsdatum.strftime('%d.%m.%Y') if rechnung.faelligkeitsdatum else '',
                days_overdue=days_overdue,
                reminder_level=reminder_level,
                display_first=True
            )

            if success:
                return jsonify({
                    'success': True,
                    'message': 'Zahlungserinnerung wurde in Outlook geoeffnet'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Fehler beim Erstellen der Zahlungserinnerung'
                })

        else:
            return jsonify({
                'success': False,
                'message': f'E-Mail-Methode {email_method} wird fuer Mahnungen noch nicht unterstuetzt'
            })

    except Exception as e:
        logger.error(f"Mahnungsversand fehlgeschlagen: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
