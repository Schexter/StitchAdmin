"""
Order Design Controller
API-Endpunkte für Multi-Position-Design-Verwaltung
"""

from flask import Blueprint, request, jsonify, current_app, url_for, render_template
from flask_login import login_required, current_user
from datetime import datetime
from src.models import db, Order, OrderItem, OrderDesign, OrderItemPersonalization, OrderDesignNameList
from src.models.company_settings import CompanySettings
from werkzeug.utils import secure_filename
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Blueprint erstellen
order_design_bp = Blueprint('order_designs', __name__, url_prefix='/orders/api')


@order_design_bp.route('/design', methods=['POST'])
@login_required
def create_design():
    """Neue Design-Position erstellen"""
    try:
        order_id = request.form.get('order_id')
        if not order_id:
            return jsonify({'success': False, 'error': 'Auftrags-ID fehlt'})

        order = Order.query.get(order_id)
        if not order:
            return jsonify({'success': False, 'error': 'Auftrag nicht gefunden'})

        # Neues Design erstellen
        design = OrderDesign(
            order_id=order_id,
            position=request.form.get('position'),
            position_label=get_position_label(request.form.get('position')),
            design_type=request.form.get('design_type', 'stick'),
            is_personalized=request.form.get('is_personalized') == 'on',
            design_name=request.form.get('design_name'),
            created_by=current_user.username
        )

        # Design-Datei verarbeiten
        design_file = request.files.get('design_file')
        if design_file and design_file.filename:
            filename = secure_filename(design_file.filename)
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'designs')
            os.makedirs(upload_folder, exist_ok=True)

            filepath = os.path.join(upload_folder, f"{order_id}_{design.position}_{filename}")
            design_file.save(filepath)
            design.design_file_path = os.path.relpath(filepath, os.path.join(current_app.root_path, 'static', 'uploads'))
        elif request.form.get('design_file_path'):
            design.design_file_path = request.form.get('design_file_path')

        # Stickerei-Details
        if design.design_type == 'stick':
            design.stitch_count = int(request.form.get('stitch_count') or 0) or None
            design.width_mm = float(request.form.get('width_mm') or 0) or None
            design.height_mm = float(request.form.get('height_mm') or 0) or None
            design.thread_colors = request.form.get('thread_colors')
        else:
            # Druck-Details
            design.print_width_cm = float(request.form.get('print_width_cm') or 0) or None
            design.print_height_cm = float(request.form.get('print_height_cm') or 0) or None
            design.print_colors = int(request.form.get('print_colors') or 1)

        # Preise
        design.setup_price = float(request.form.get('setup_price') or 0)
        design.price_per_piece = float(request.form.get('price_per_piece') or 0)

        # Sortierung
        existing_count = OrderDesign.query.filter_by(order_id=order_id).count()
        design.sort_order = existing_count

        db.session.add(design)
        db.session.commit()

        return jsonify({
            'success': True,
            'design_id': design.id,
            'message': 'Design-Position erfolgreich erstellt'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Erstellen des Designs: {e}")
        return jsonify({'success': False, 'error': str(e)})


@order_design_bp.route('/design/<int:design_id>', methods=['GET'])
@login_required
def get_design(design_id):
    """Design-Position abrufen"""
    design = OrderDesign.query.get(design_id)
    if not design:
        return jsonify({'success': False, 'error': 'Design nicht gefunden'})

    return jsonify({
        'success': True,
        'design': {
            'id': design.id,
            'order_id': design.order_id,
            'position': design.position,
            'position_label': design.get_position_label(),
            'design_type': design.design_type,
            'is_personalized': design.is_personalized,
            'design_name': design.design_name,
            'design_file_path': design.design_file_path,
            'design_thumbnail_path': design.design_thumbnail_path,
            'stitch_count': design.stitch_count,
            'width_mm': design.width_mm,
            'height_mm': design.height_mm,
            'thread_colors': design.thread_colors,
            'print_width_cm': design.print_width_cm,
            'print_height_cm': design.print_height_cm,
            'print_colors': design.print_colors,
            'approval_status': design.approval_status,
            'setup_price': design.setup_price,
            'price_per_piece': design.price_per_piece,
            'sort_order': design.sort_order
        }
    })


@order_design_bp.route('/design/<int:design_id>', methods=['PUT'])
@login_required
def update_design(design_id):
    """Design-Position aktualisieren"""
    try:
        design = OrderDesign.query.get(design_id)
        if not design:
            return jsonify({'success': False, 'error': 'Design nicht gefunden'})

        # Grunddaten
        design.position = request.form.get('position', design.position)
        design.position_label = get_position_label(design.position)
        design.design_type = request.form.get('design_type', design.design_type)
        design.is_personalized = request.form.get('is_personalized') == 'on'
        design.design_name = request.form.get('design_name')

        # Design-Datei
        design_file = request.files.get('design_file')
        if design_file and design_file.filename:
            filename = secure_filename(design_file.filename)
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'designs')
            os.makedirs(upload_folder, exist_ok=True)

            filepath = os.path.join(upload_folder, f"{design.order_id}_{design.position}_{filename}")
            design_file.save(filepath)
            design.design_file_path = os.path.relpath(filepath, os.path.join(current_app.root_path, 'static', 'uploads'))
        elif request.form.get('design_file_path'):
            design.design_file_path = request.form.get('design_file_path')

        # Typ-spezifische Details
        if design.design_type == 'stick':
            design.stitch_count = int(request.form.get('stitch_count') or 0) or None
            design.width_mm = float(request.form.get('width_mm') or 0) or None
            design.height_mm = float(request.form.get('height_mm') or 0) or None
            design.thread_colors = request.form.get('thread_colors')
        else:
            design.print_width_cm = float(request.form.get('print_width_cm') or 0) or None
            design.print_height_cm = float(request.form.get('print_height_cm') or 0) or None
            design.print_colors = int(request.form.get('print_colors') or 1)

        # Preise
        design.setup_price = float(request.form.get('setup_price') or 0)
        design.price_per_piece = float(request.form.get('price_per_piece') or 0)

        design.updated_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Design-Position aktualisiert'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Aktualisieren des Designs: {e}")
        return jsonify({'success': False, 'error': str(e)})


@order_design_bp.route('/design/<int:design_id>', methods=['DELETE'])
@login_required
def delete_design(design_id):
    """Design-Position löschen"""
    try:
        design = OrderDesign.query.get(design_id)
        if not design:
            return jsonify({'success': False, 'error': 'Design nicht gefunden'})

        # Lösche auch zugehörige Personalisierungen
        OrderItemPersonalization.query.filter_by(order_design_id=design_id).delete()

        # Lösche Namen-Listen (für Sammeldesigns)
        OrderDesignNameList.query.filter_by(order_design_id=design_id).delete()

        db.session.delete(design)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Design-Position gelöscht'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Löschen des Designs: {e}")
        return jsonify({'success': False, 'error': str(e)})


@order_design_bp.route('/design/<int:design_id>/personalizations', methods=['GET'])
@login_required
def get_personalizations(design_id):
    """Personalisierungen für ein Design abrufen"""
    design = OrderDesign.query.get(design_id)
    if not design:
        return jsonify({'success': False, 'error': 'Design nicht gefunden'})

    # Hole Order-Items
    order = Order.query.get(design.order_id)
    if not order:
        return jsonify({'success': False, 'error': 'Auftrag nicht gefunden'})

    order_items = []
    for item in order.items:
        article = item.article
        order_items.append({
            'id': item.id,
            'article_id': item.article_id,
            'article_name': article.name if article else None,
            'quantity': item.quantity,
            'textile_size': item.textile_size,
            'textile_color': item.textile_color
        })

    # Hole bestehende Personalisierungen
    personalizations = []
    for pers in design.personalizations:
        personalizations.append({
            'id': pers.id,
            'order_item_id': pers.order_item_id,
            'text_line_1': pers.text_line_1,
            'text_line_2': pers.text_line_2,
            'text_line_3': pers.text_line_3,
            'sequence_number': pers.sequence_number,
            'is_produced': pers.is_produced
        })

    return jsonify({
        'success': True,
        'order_items': order_items,
        'personalizations': personalizations
    })


@order_design_bp.route('/design/<int:design_id>/personalizations', methods=['POST'])
@login_required
def save_personalizations(design_id):
    """Personalisierungen speichern"""
    try:
        design = OrderDesign.query.get(design_id)
        if not design:
            return jsonify({'success': False, 'error': 'Design nicht gefunden'})

        data = request.get_json()
        personalizations_data = data.get('personalizations', [])

        # Lösche bestehende Personalisierungen für dieses Design
        OrderItemPersonalization.query.filter_by(order_design_id=design_id).delete()

        # Erstelle neue Personalisierungen
        for pers_data in personalizations_data:
            pers = OrderItemPersonalization(
                order_item_id=int(pers_data['order_item_id']),
                order_design_id=design_id,
                text_line_1=pers_data.get('text_line_1', '').strip() or None,
                text_line_2=pers_data.get('text_line_2', '').strip() or None,
                sequence_number=pers_data.get('sequence_number'),
                is_produced=pers_data.get('is_produced', False)
            )
            db.session.add(pers)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{len(personalizations_data)} Personalisierungen gespeichert'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Speichern der Personalisierungen: {e}")
        return jsonify({'success': False, 'error': str(e)})


@order_design_bp.route('/design/<int:design_id>/name-list', methods=['GET'])
@login_required
def get_name_list(design_id):
    """Namen-Liste für Sammeldesign abrufen"""
    design = OrderDesign.query.get(design_id)
    if not design:
        return jsonify({'success': False, 'error': 'Design nicht gefunden'})

    names = []
    for name_entry in design.name_list.order_by(OrderDesignNameList.sort_order):
        names.append({
            'id': name_entry.id,
            'name': name_entry.name,
            'subtitle': name_entry.subtitle,
            'sort_order': name_entry.sort_order
        })

    return jsonify({
        'success': True,
        'names': names
    })


@order_design_bp.route('/design/<int:design_id>/name-list', methods=['POST'])
@login_required
def save_name_list(design_id):
    """Namen-Liste für Sammeldesign speichern"""
    try:
        design = OrderDesign.query.get(design_id)
        if not design:
            return jsonify({'success': False, 'error': 'Design nicht gefunden'})

        data = request.get_json()
        names_data = data.get('names', [])

        # Lösche bestehende Namen
        OrderDesignNameList.query.filter_by(order_design_id=design_id).delete()

        # Erstelle neue Namen-Einträge
        for i, name_data in enumerate(names_data):
            name_entry = OrderDesignNameList(
                order_design_id=design_id,
                name=name_data.get('name', '').strip(),
                subtitle=name_data.get('subtitle', '').strip() or None,
                sort_order=i
            )
            db.session.add(name_entry)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{len(names_data)} Namen gespeichert'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Speichern der Namen-Liste: {e}")
        return jsonify({'success': False, 'error': str(e)})


@order_design_bp.route('/design/<int:design_id>/approve', methods=['POST'])
@login_required
def approve_design(design_id):
    """Design-Position freigeben (intern)"""
    try:
        design = OrderDesign.query.get(design_id)
        if not design:
            return jsonify({'success': False, 'error': 'Design nicht gefunden'})

        design.approval_status = 'approved'
        design.approved_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Design freigegeben'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@order_design_bp.route('/designs/<int:design_id>/send-approval', methods=['POST'])
@login_required
def send_design_approval(design_id):
    """Design zur Kundenfreigabe senden"""
    try:
        design = OrderDesign.query.get(design_id)
        if not design:
            return jsonify({'success': False, 'error': 'Design nicht gefunden'})

        order = Order.query.get(design.order_id)
        if not order:
            return jsonify({'success': False, 'error': 'Auftrag nicht gefunden'})

        # Prüfe ob Kunde vorhanden und E-Mail hat
        if not order.customer:
            return jsonify({'success': False, 'error': 'Kein Kunde für diesen Auftrag hinterlegt'})

        if not order.customer.email:
            return jsonify({'success': False, 'error': 'Keine E-Mail-Adresse für den Kunden hinterlegt'})

        # Generiere Freigabe-Token
        import secrets
        approval_token = secrets.token_urlsafe(32)

        # Speichere Token im Design selbst (als JSON in approval_notes temporär)
        token_data = {
            'token': approval_token,
            'created_at': datetime.utcnow().isoformat(),
            'sent_to': order.customer.email
        }

        # Token in thread_colors speichern (als JSON, wird nicht für Druck-Designs verwendet)
        if design.design_type != 'stick':
            design.thread_colors = json.dumps({'approval_token': token_data})
        else:
            existing_notes = design.approval_notes or ''
            design.approval_notes = f"{existing_notes}\n[TOKEN:{approval_token}]".strip()

        # Auch Order-Token setzen falls nicht vorhanden
        if not order.design_approval_token:
            order.design_approval_token = approval_token

        # Status auf "gesendet" setzen
        design.approval_status = 'sent'
        order.design_approval_status = 'sent'
        order.design_approval_sent_at = datetime.utcnow()

        db.session.commit()

        # Freigabe-URL erstellen
        approval_url = url_for('design_approval.public_approval_page',
                               token=order.design_approval_token,
                               _external=True)

        # E-Mail senden - je nach konfigurierter Methode
        email_sent = False
        email_error_msg = None

        settings = CompanySettings.query.first()
        if not settings:
            email_error_msg = "Keine Firmeneinstellungen gefunden"
        else:
            company_name = settings.company_name or "StitchAdmin"
            email_method = settings.email_method or 'outlook'

            # E-Mail-Inhalte vorbereiten
            subject = f"Design-Freigabe für Auftrag {order.order_number} - {design.get_position_label()}"

            text_body = f"""
Guten Tag {order.customer.display_name},

bitte prüfen und genehmigen Sie das Design für Ihren Auftrag {order.order_number}.

Position: {design.get_position_label()}
Typ: {'Stickerei' if design.design_type == 'stick' else 'Druck'}

Im Anhang finden Sie das Freigabeformular mit der Design-Vorschau.
Bitte prüfen Sie das Design sorgfältig und senden Sie uns das unterschriebene
Formular per E-Mail, Fax oder WhatsApp zurück.

Bei Fragen stehen wir Ihnen gerne zur Verfügung.

Mit freundlichen Grüßen
{company_name}
            """

            html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 8px 8px 0 0; text-align: center;">
        <h1 style="color: white; margin: 0;">Design-Freigabe</h1>
    </div>
    <div style="background: #f8f9fa; padding: 20px; border-radius: 0 0 8px 8px;">
        <p>Guten Tag <strong>{order.customer.display_name}</strong>,</p>
        <p>bitte prüfen und genehmigen Sie das Design für Ihren Auftrag <strong>{order.order_number}</strong>.</p>
        <table style="width: 100%; background: white; padding: 15px; border-radius: 8px; margin: 15px 0;">
            <tr><td><strong>Position:</strong></td><td>{design.get_position_label()}</td></tr>
            <tr><td><strong>Typ:</strong></td><td>{'Stickerei' if design.design_type == 'stick' else 'Druck'}</td></tr>
        </table>
        <div style="background: #e8f5e9; border-left: 4px solid #4caf50; padding: 15px; margin: 20px 0;">
            <p style="margin: 0;"><strong>📎 Freigabeformular im Anhang</strong></p>
            <p style="margin: 10px 0 0 0; font-size: 14px;">
                Bitte prüfen Sie das Design im angehängten PDF und senden Sie uns das
                unterschriebene Formular per E-Mail, Fax oder WhatsApp zurück.
            </p>
        </div>
        <p style="color: #666; font-size: 12px;">
            <strong>Hinweis:</strong> Nach Ihrer Freigabe beginnen wir mit der Produktion.
            Änderungen sind danach nicht mehr möglich.
        </p>
    </div>
    <p style="color: #999; font-size: 11px; text-align: center; margin-top: 20px;">
        {company_name}
    </p>
</body>
</html>
            """

            # PDF-Freigabeformular erstellen
            pdf_path = None
            try:
                from src.services.design_approval_pdf import create_design_approval_pdf, get_design_image_path
                import tempfile

                # Design-Bild finden
                design_image = get_design_image_path(order, design, current_app.root_path)

                # PDF in temp-Datei erstellen
                pdf_filename = f"Freigabe_{order.order_number}_{design.position}.pdf"
                pdf_path = os.path.join(tempfile.gettempdir(), pdf_filename)

                create_design_approval_pdf(
                    order=order,
                    design=design,
                    company_settings=settings,
                    design_image_path=design_image,
                    output_path=pdf_path
                )
                current_app.logger.info(f"Freigabe-PDF erstellt: {pdf_path}")

            except Exception as pdf_error:
                current_app.logger.error(f"Fehler bei PDF-Erstellung: {pdf_error}")
                pdf_path = None

            # Versand je nach Methode
            if email_method == 'outlook':
                # Outlook-Versand - Prüfe erst ob wir unter Windows laufen
                import sys
                if sys.platform != 'win32':
                    email_error_msg = (
                        "OUTLOOK NICHT VERFÜGBAR: Die App läuft unter Linux/WSL. "
                        "Outlook-Integration funktioniert nur unter Windows. "
                        "Bitte starte die App in PowerShell/CMD mit 'python app.py' "
                        "ODER wechsle in Einstellungen → E-Mail auf SMTP."
                    )
                    current_app.logger.warning(f"Outlook-Versand fehlgeschlagen: App läuft unter {sys.platform}")
                else:
                    try:
                        from src.services.outlook_service import OutlookService
                        outlook = OutlookService()

                        if outlook.is_available():
                            # Anhänge vorbereiten
                            attachments = [pdf_path] if pdf_path and os.path.exists(pdf_path) else None

                            success = outlook.create_email(
                                to=order.customer.email,
                                subject=subject,
                                body=html_body,
                                html_body=True,
                                attachments=attachments,
                                display_first=True  # E-Mail in Outlook anzeigen zum Überprüfen
                            )
                            if success:
                                email_sent = True
                                current_app.logger.info(f"Design-Freigabe via Outlook erstellt für {order.customer.email}")
                            else:
                                email_error_msg = "Outlook konnte E-Mail nicht erstellen - ist Outlook geöffnet?"
                        else:
                            email_error_msg = "Outlook ist nicht verfügbar oder nicht gestartet. Bitte Outlook öffnen und erneut versuchen."

                    except ImportError:
                        email_error_msg = "Outlook-Integration fehlt (pywin32 nicht installiert). Bitte 'pip install pywin32' ausführen oder SMTP verwenden."
                    except Exception as e:
                        email_error_msg = f"Outlook-Fehler: {str(e)}"
                        current_app.logger.error(f"Outlook-Fehler: {e}")

            elif email_method == 'smtp':
                # SMTP-Versand
                if not settings.smtp_server or not settings.smtp_username:
                    email_error_msg = "SMTP nicht konfiguriert - bitte in Einstellungen einrichten"
                else:
                    try:
                        msg = MIMEMultipart('alternative')
                        msg['Subject'] = subject
                        msg['From'] = f"{settings.smtp_from_name or company_name} <{settings.smtp_from_email or settings.smtp_username}>"
                        msg['To'] = order.customer.email

                        msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
                        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

                        if settings.smtp_use_tls:
                            server = smtplib.SMTP(settings.smtp_server, settings.smtp_port or 587)
                            server.starttls()
                        else:
                            server = smtplib.SMTP_SSL(settings.smtp_server, settings.smtp_port or 465)

                        server.login(settings.smtp_username, settings.smtp_password)
                        server.send_message(msg)
                        server.quit()

                        email_sent = True
                        current_app.logger.info(f"Design-Freigabe via SMTP an {order.customer.email} gesendet")

                    except smtplib.SMTPAuthenticationError:
                        email_error_msg = "SMTP-Authentifizierung fehlgeschlagen"
                    except smtplib.SMTPConnectError:
                        email_error_msg = f"Verbindung zu {settings.smtp_server} fehlgeschlagen"
                    except Exception as e:
                        email_error_msg = str(e)
                        current_app.logger.error(f"SMTP-Fehler: {e}")

            else:  # mailto oder andere
                email_error_msg = f"E-Mail-Methode '{email_method}' unterstützt keinen automatischen Versand. Bitte Outlook oder SMTP verwenden."

        # Antwort
        if email_sent:
            message = f'Design-Freigabe wurde an {order.customer.email} gesendet!'
        else:
            message = f'Freigabe-Status gesetzt, aber E-Mail nicht gesendet: {email_error_msg}'

        return jsonify({
            'success': True,
            'message': message,
            'approval_url': approval_url,
            'email_sent': email_sent,
            'email_error': email_error_msg
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Senden der Freigabe: {e}")
        return jsonify({'success': False, 'error': str(e)})


@order_design_bp.route('/designs/<int:design_id>/approval-status', methods=['POST'])
@login_required
def update_approval_status(design_id):
    """Freigabe-Status manuell aktualisieren"""
    try:
        design = OrderDesign.query.get(design_id)
        if not design:
            return jsonify({'success': False, 'error': 'Design nicht gefunden'})

        data = request.get_json()
        new_status = data.get('status')

        if new_status not in ['pending', 'sent', 'approved', 'rejected', 'revision_requested']:
            return jsonify({'success': False, 'error': 'Ungültiger Status'})

        design.approval_status = new_status

        if new_status == 'approved':
            design.approved_at = datetime.utcnow()

        if data.get('notes'):
            design.approval_notes = data.get('notes')

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Status auf "{new_status}" gesetzt'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@order_design_bp.route('/designs/<int:design_id>/image')
def get_design_image(design_id):
    """Liefert das Design-Bild für die Vorschau"""
    from flask import send_file, abort

    design = OrderDesign.query.get(design_id)
    if not design or not design.design_file_path:
        abort(404)

    # Pfad normalisieren (Windows/Linux kompatibel)
    file_path = design.design_file_path.replace('\\', '/')

    # Vollständigen Pfad erstellen
    full_path = os.path.join(current_app.root_path, 'static', 'uploads', file_path)

    # Fallback: direkt im uploads-Ordner
    if not os.path.exists(full_path):
        full_path = os.path.join(current_app.root_path, 'static', 'uploads', os.path.basename(file_path))

    # Fallback: im src/static/uploads Ordner
    if not os.path.exists(full_path):
        full_path = os.path.join(current_app.root_path, 'src', 'static', 'uploads', file_path)

    if os.path.exists(full_path):
        return send_file(full_path)

    current_app.logger.error(f"Design-Bild nicht gefunden: {design.design_file_path}")
    abort(404)


def get_position_label(position_code):
    """Gibt das Label für einen Position-Code zurück"""
    position_map = {
        'brust_links': 'Brust links',
        'brust_rechts': 'Brust rechts',
        'brust_mitte': 'Brust Mitte',
        'aermel_links': 'Ärmel links',
        'aermel_rechts': 'Ärmel rechts',
        'ruecken': 'Rücken',
        'ruecken_oben': 'Rücken oben',
        'ruecken_unten': 'Rücken unten',
        'kragen': 'Kragen/Nacken',
        'bauch': 'Bauch',
        'hosenbein_links': 'Hosenbein links',
        'hosenbein_rechts': 'Hosenbein rechts',
        'kappe_vorne': 'Kappe vorne',
        'kappe_seite': 'Kappe Seite',
        'andere': 'Andere Position'
    }
    return position_map.get(position_code, position_code)
