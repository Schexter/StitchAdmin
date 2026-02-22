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
        import platform

        current_platform = platform.system()

        # Prüfe zuerst die Plattform
        if current_platform != 'Windows':
            logger.warning(f"Test-Outlook: Nicht-Windows Plattform: {current_platform}")
            return jsonify({
                'success': False,
                'message': f'Outlook-Integration ist nur unter Windows verfuegbar. Aktuelle Plattform: {current_platform}. Wenn Sie WSL nutzen, starten Sie StitchAdmin direkt unter Windows.'
            })

        if not OUTLOOK_AVAILABLE:
            return jsonify({
                'success': False,
                'message': 'win32com ist nicht installiert. Bitte fuehren Sie "pip install pywin32" aus und starten Sie die App unter Windows (nicht WSL).'
            })

        service = OutlookService()

        if not service.is_available():
            return jsonify({
                'success': False,
                'message': 'Outlook ist nicht verfuegbar. Stellen Sie sicher, dass Outlook installiert und geoeffnet ist.'
            })

        # Verbindung explizit herstellen
        if not service.connect():
            return jsonify({
                'success': False,
                'message': 'Konnte keine Verbindung zu Outlook herstellen. Bitte Outlook oeffnen und erneut versuchen.'
            })

        # Test-E-Mail erstellen (wird nur angezeigt, nicht gesendet)
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
        except Exception as create_error:
            logger.error(f"Test-Outlook create_email failed: {create_error}")
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
        return jsonify({
            'success': False,
            'message': f'Fehler: {str(e)}'
        })


@email_api_bp.route('/test-smtp', methods=['POST'])
@login_required
def test_smtp():
    """
    Testet die SMTP-Verbindung und sendet optional eine Test-E-Mail
    """
    try:
        from src.models.company_settings import CompanySettings
        settings = CompanySettings.get_settings()

        if not settings.smtp_server:
            return jsonify({
                'success': False,
                'message': 'Kein SMTP-Server konfiguriert. Bitte zuerst die Einstellungen speichern.'
            })

        if not settings.smtp_from_email:
            return jsonify({
                'success': False,
                'message': 'Keine Absender-E-Mail konfiguriert.'
            })

        # Test-Empfaenger aus Request oder Absender-Adresse
        test_to = None
        if request.is_json:
            test_to = request.json.get('test_email')
        if not test_to:
            test_to = settings.smtp_from_email

        from src.services.email_service_new import EmailService
        service = EmailService()

        # Zuerst nur Verbindung testen
        conn_result = service.test_connection()
        if not conn_result.get('success'):
            return jsonify({
                'success': False,
                'message': f'SMTP-Verbindung fehlgeschlagen: {conn_result.get("error", "Unbekannter Fehler")}'
            })

        # Verbindung OK - Test-E-Mail senden
        result = service.send_email(
            to=test_to,
            subject='StitchAdmin - SMTP Test',
            body='Diese Test-E-Mail wurde von StitchAdmin gesendet.\n\nWenn Sie diese E-Mail erhalten, funktioniert der SMTP-Versand korrekt.',
            html_body='''<html><body style="font-family: Arial, sans-serif;">
<h2>StitchAdmin SMTP-Test</h2>
<p>Diese Test-E-Mail wurde von StitchAdmin gesendet.</p>
<p style="color: green; font-weight: bold;">Wenn Sie diese E-Mail sehen, funktioniert der SMTP-Versand korrekt!</p>
<hr>
<p style="color: #666; font-size: 12px;">Automatisch generiert von StitchAdmin.</p>
</body></html>''',
            track=True
        )

        if result.get('success'):
            return jsonify({
                'success': True,
                'message': f'Test-E-Mail erfolgreich an {test_to} gesendet!'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'SMTP-Verbindung OK, aber Versand fehlgeschlagen: {result.get("error", "Unbekannter Fehler")}'
            })

    except Exception as e:
        logger.error(f"SMTP-Test fehlgeschlagen: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@email_api_bp.route('/send-invoice/<int:rechnung_id>', methods=['POST'])
@login_required
def send_invoice_email(rechnung_id):
    """
    Versendet eine Rechnung per E-Mail
    """
    try:
        from src.models.rechnungsmodul import Rechnung
        from src.models.company_settings import CompanySettings
        import tempfile
        import os

        # OutlookService nur importieren wenn noetig (Windows-only)
        OutlookService = None
        try:
            from src.services.outlook_service import OutlookService
        except ImportError:
            pass

        # Rechnung laden
        rechnung = Rechnung.query.get_or_404(rechnung_id)
        settings = CompanySettings.get_settings()

        # Empfaenger-E-Mail (kunde_email Snapshot oder Kunde-Relationship)
        to_email = getattr(rechnung, 'kunde_email', None)
        if not to_email and rechnung.kunde:
            to_email = rechnung.kunde.email
        if not to_email:
            return jsonify({
                'success': False,
                'message': 'Keine E-Mail-Adresse fuer diesen Kunden hinterlegt'
            }), 400

        # Betrag ermitteln (neues Model: brutto_gesamt, altes: summe_brutto)
        betrag = float(getattr(rechnung, 'brutto_gesamt', None) or getattr(rechnung, 'summe_brutto', 0) or 0)
        kunde_name = rechnung.kunde.display_name if rechnung.kunde else (getattr(rechnung, 'kunde_name', None) or 'Kunde')

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
        email_method = settings.email_method or 'smtp'

        if email_method == 'outlook':
            # Outlook-Versand
            if not OutlookService:
                return jsonify({
                    'success': False,
                    'message': 'Outlook ist auf diesem System nicht verfuegbar (nur Windows)'
                })

            service = OutlookService()

            if not service.is_available():
                return jsonify({
                    'success': False,
                    'message': 'Outlook ist nicht verfuegbar'
                })

            # Betreff mit Platzhaltern ersetzen
            subject = (settings.invoice_email_subject or 'Rechnung {invoice_number}').format(
                invoice_number=rechnung.rechnungsnummer,
                customer_name=kunde_name,
                amount=f'{betrag:,.2f}'
            )

            # Body mit Platzhaltern oder Standard
            if settings.invoice_email_template:
                body = settings.invoice_email_template.format(
                    invoice_number=rechnung.rechnungsnummer,
                    customer_name=kunde_name,
                    amount=f'{betrag:,.2f}'
                )
                html_body = False
            else:
                # Standard-HTML-Body
                body = f'''
<html>
<body style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
<p>Sehr geehrte Damen und Herren,</p>

<p>anbei erhalten Sie unsere Rechnung <strong>{rechnung.rechnungsnummer}</strong> ueber <strong>{betrag:,.2f} EUR</strong>.</p>

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
                customer_name=kunde_name,
                amount=f'{betrag:,.2f}'
            )
            body = f'Sehr geehrte Damen und Herren,\n\nanbei erhalten Sie unsere Rechnung {rechnung.rechnungsnummer}.\n\nMit freundlichen Gruessen'

            mailto_url = f"mailto:{to_email}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"

            return jsonify({
                'success': True,
                'mailto_url': mailto_url,
                'pdf_path': pdf_path,
                'message': 'Bitte fuegen Sie die PDF-Datei manuell als Anhang hinzu'
            })

        elif email_method == 'smtp':
            # SMTP-Versand
            from src.services.email_service_new import EmailService
            service = EmailService()

            # Betreff mit Platzhaltern
            subject = (settings.invoice_email_subject or 'Rechnung {invoice_number}').format(
                invoice_number=rechnung.rechnungsnummer,
                customer_name=kunde_name,
                amount=f'{betrag:,.2f}'
            )

            # Body
            if settings.invoice_email_template:
                body = settings.invoice_email_template.format(
                    invoice_number=rechnung.rechnungsnummer,
                    customer_name=kunde_name,
                    amount=f'{betrag:,.2f}'
                )
                html_body = None
            else:
                body = f'Sehr geehrte Damen und Herren,\n\nanbei erhalten Sie unsere Rechnung {rechnung.rechnungsnummer} ueber {betrag:,.2f} EUR.\n\nBei Fragen stehen wir Ihnen gerne zur Verfuegung.\n\nMit freundlichen Gruessen'
                html_body = f'''<html><body style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
<p>Sehr geehrte Damen und Herren,</p>
<p>anbei erhalten Sie unsere Rechnung <strong>{rechnung.rechnungsnummer}</strong> ueber <strong>{betrag:,.2f} EUR</strong>.</p>
<p>Bei Fragen stehen wir Ihnen gerne zur Verfuegung.</p>
<p>Mit freundlichen Gruessen</p>'''

                # Signatur anhaengen
                if settings.email_signature:
                    html_body += f'<hr><div style="font-size: 12px; color: #666;">{settings.email_signature}</div>'

                html_body += '</body></html>'

            result = service.send_email(
                to=to_email,
                subject=subject,
                body=body,
                html_body=html_body,
                attachments=[pdf_path]
            )

            if result.get('success'):
                return jsonify({
                    'success': True,
                    'message': f'Rechnung per E-Mail an {to_email} gesendet'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'Versand fehlgeschlagen: {result.get("error", "Unbekannter Fehler")}'
                })

        else:
            return jsonify({
                'success': False,
                'message': f'Unbekannte E-Mail-Methode: {email_method}'
            })

    except Exception as e:
        logger.error(f"Rechnungsversand fehlgeschlagen: {e}")
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
        from datetime import date

        # OutlookService nur importieren wenn noetig (Windows-only)
        OutlookService = None
        try:
            from src.services.outlook_service import OutlookService
        except ImportError:
            pass

        # Rechnung laden
        rechnung = Rechnung.query.get_or_404(rechnung_id)
        settings = CompanySettings.get_settings()

        # Empfaenger-E-Mail (kunde_email Snapshot oder Kunde-Relationship)
        to_email = getattr(rechnung, 'kunde_email', None)
        if not to_email and rechnung.kunde:
            to_email = rechnung.kunde.email
        if not to_email:
            return jsonify({
                'success': False,
                'message': 'Keine E-Mail-Adresse fuer diesen Kunden hinterlegt'
            }), 400

        # Betrag und Kundenname ermitteln
        betrag = float(getattr(rechnung, 'brutto_gesamt', None) or getattr(rechnung, 'summe_brutto', 0) or 0)
        kunde_name = rechnung.kunde.display_name if rechnung.kunde else (getattr(rechnung, 'kunde_name', None) or 'Kunde')

        # Mahnstufe aus Request
        reminder_level = request.json.get('reminder_level', 1) if request.is_json else 1

        # Tage ueberfaellig berechnen
        days_overdue = 0
        if rechnung.faelligkeitsdatum:
            days_overdue = (date.today() - rechnung.faelligkeitsdatum).days

        # E-Mail-Methode
        email_method = settings.email_method or 'smtp'

        if email_method == 'outlook':
            if not OutlookService:
                return jsonify({
                    'success': False,
                    'message': 'Outlook ist auf diesem System nicht verfuegbar (nur Windows)'
                })

            service = OutlookService()

            if not service.is_available():
                return jsonify({
                    'success': False,
                    'message': 'Outlook ist nicht verfuegbar'
                })

            success = service.send_reminder_email(
                to=to_email,
                invoice_number=rechnung.rechnungsnummer,
                customer_name=kunde_name,
                amount=betrag,
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

        elif email_method == 'smtp':
            from src.services.email_service_new import EmailService
            service = EmailService()

            result = service.send_payment_reminder(
                to=to_email,
                customer_name=kunde_name,
                invoice_number=rechnung.rechnungsnummer,
                due_date=rechnung.faelligkeitsdatum.strftime('%d.%m.%Y') if rechnung.faelligkeitsdatum else '',
                amount=betrag,
                reminder_level=reminder_level
            )

            if result.get('success'):
                return jsonify({
                    'success': True,
                    'message': f'Zahlungserinnerung per E-Mail an {to_email} gesendet'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'Versand fehlgeschlagen: {result.get("error", "Unbekannter Fehler")}'
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
