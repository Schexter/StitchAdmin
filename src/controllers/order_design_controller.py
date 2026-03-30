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
            design.thread_colors = request.form.get('thread_colors') or None
        else:
            # Druck-Details
            design.print_width_cm = float(request.form.get('print_width_cm') or 0) or None
            design.print_height_cm = float(request.form.get('print_height_cm') or 0) or None
            # Druckfarben (Pantone / Hex) als JSON speichern
            design.thread_colors = request.form.get('print_colors_data') or None

        # Preise
        design.setup_price = float(request.form.get('setup_price') or 0)
        design.price_per_piece = float(request.form.get('price_per_piece') or 0)

        # Notizen
        design.notes = request.form.get('notes') or None

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
            'notes': design.notes,
            'sort_order': design.sort_order,
            'supplier_id': design.supplier_id,
            'supplier_order_status': design.supplier_order_status or 'none',
            'supplier_order_date': design.supplier_order_date.isoformat() if design.supplier_order_date else None,
            'supplier_expected_date': design.supplier_expected_date.isoformat() if design.supplier_expected_date else None,
            'supplier_delivered_date': design.supplier_delivered_date.isoformat() if design.supplier_delivered_date else None,
            'supplier_order_notes': design.supplier_order_notes,
            'supplier_cost': design.supplier_cost or 0,
            'supplier_reference': design.supplier_reference,
            'supplier_order_id': design.supplier_order_id,
            'print_file_path': design.print_file_path,
            'print_file_name': design.print_file_name,
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
            design.thread_colors = request.form.get('thread_colors') or None
        else:
            design.print_width_cm = float(request.form.get('print_width_cm') or 0) or None
            design.print_height_cm = float(request.form.get('print_height_cm') or 0) or None
            # Druckfarben (Pantone / Hex) als JSON speichern
            design.thread_colors = request.form.get('print_colors_data') or None

        # Preise
        design.setup_price = float(request.form.get('setup_price') or 0)
        design.price_per_piece = float(request.form.get('price_per_piece') or 0)

        # Notizen
        design.notes = request.form.get('notes') or None

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

        # Token in approval_notes speichern (einheitlich für alle Design-Typen)
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
Groesse: {f'{design.width_mm:.0f} x {design.height_mm:.0f} mm' if design.design_type == 'stick' and design.width_mm and design.height_mm else f'{design.print_width_cm:.1f} x {design.print_height_cm:.1f} cm' if design.print_width_cm and design.print_height_cm else 'Nicht angegeben'}

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
            <tr><td><strong>Gr&ouml;&szlig;e:</strong></td><td>{f'{design.width_mm:.0f} x {design.height_mm:.0f} mm' if design.design_type == 'stick' and design.width_mm and design.height_mm else f'{design.print_width_cm:.1f} x {design.print_height_cm:.1f} cm' if design.print_width_cm and design.print_height_cm else 'Nicht angegeben'}</td></tr>
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


@order_design_bp.route('/price-suggestion', methods=['GET'])
@login_required
def get_price_suggestion():
    """Kalkulierter Preis-Vorschlag basierend auf Design-Parametern"""
    try:
        from src.services.textildruck_kalkulation import StickKalkulator, TextildruckKalkulator
        from decimal import Decimal

        design_type = request.args.get('design_type', 'stick')
        menge = max(int(request.args.get('menge') or 1), 1)

        if design_type == 'stick':
            stichzahl = int(request.args.get('stichzahl') or 0)
            farbwechsel = int(request.args.get('farbwechsel') or 0)

            if stichzahl <= 0:
                return jsonify({'success': False, 'error': 'Stichzahl erforderlich'})

            kalk = StickKalkulator()
            result = kalk.berechne_komplett(
                stichzahl=stichzahl,
                farbwechsel=farbwechsel,
                menge=menge
            )

            return jsonify({
                'success': True,
                'verfahren': result['verfahren'],
                'setup_price': float(result['einrichtekosten']),
                'price_per_piece': float(result['vk_pro_stueck_netto']),
                'breakdown': {
                    'stickpreis': float(result['stickpreis']),
                    'einrichtekosten': float(result['einrichtekosten']),
                    'selbstkosten': float(result['selbstkosten']),
                    'vk_netto': float(result['vk_pro_stueck_netto']),
                    'vk_brutto': float(result['vk_pro_stueck_brutto']),
                }
            })

        else:
            # Druckverfahren (dtg, flex, siebdruck, sublimation)
            print_method = request.args.get('print_method', design_type)
            width_cm = float(request.args.get('width_cm') or 0)
            height_cm = float(request.args.get('height_cm') or 0)
            flaeche_cm2 = max(width_cm * height_cm, 1.0)
            anzahl_farben = int(request.args.get('anzahl_farben') or 1)

            kalk = TextildruckKalkulator()

            if print_method in ('flex', 'flock'):
                result = kalk.berechne_flex_flock(
                    menge=menge,
                    flaeche_cm2=flaeche_cm2,
                    ist_flock=(print_method == 'flock')
                )
                setup = float(result.get('schnitt_kosten', 0))
            elif print_method in ('dtg', 'dtf', 'sublimation', 'printing'):
                result = kalk.berechne_dtg(
                    menge=menge,
                    druckgroesse_cm2=flaeche_cm2
                )
                setup = float(result.get('einrichtung', 0))
            else:
                # Siebdruck (Standard)
                result = kalk.berechne_siebdruck(
                    menge=menge,
                    anzahl_farben=anzahl_farben,
                    druckgroesse_cm2=flaeche_cm2
                )
                setup = float(result.get('fixkosten_gesamt', 0))

            return jsonify({
                'success': True,
                'verfahren': result['verfahren'],
                'setup_price': setup,
                'price_per_piece': float(result['vk_pro_stueck_netto']),
                'breakdown': {
                    'selbstkosten': float(result.get('selbstkosten_pro_stueck', 0)),
                    'vk_netto': float(result['vk_pro_stueck_netto']),
                    'vk_brutto': float(result['vk_pro_stueck_brutto']),
                }
            })

    except Exception as e:
        current_app.logger.error(f"Fehler bei Preisberechnung: {e}")
        return jsonify({'success': False, 'error': str(e)})


@order_design_bp.route('/design/<int:design_id>/supplier-status', methods=['POST'])
@login_required
def update_supplier_status(design_id):
    """Lieferanten-Bestellstatus aktualisieren"""
    try:
        design = OrderDesign.query.get(design_id)
        if not design:
            return jsonify({'success': False, 'error': 'Design nicht gefunden'})

        data = request.get_json() or request.form

        design.supplier_order_status = data.get('supplier_order_status', design.supplier_order_status)
        design.supplier_id = data.get('supplier_id') or None
        design.supplier_order_notes = data.get('supplier_order_notes') or None
        design.supplier_cost = float(data.get('supplier_cost') or 0)
        design.supplier_reference = data.get('supplier_reference') or None

        # Datum-Felder
        if data.get('supplier_order_date'):
            from datetime import date as dt_date
            design.supplier_order_date = datetime.strptime(data['supplier_order_date'], '%Y-%m-%d').date()
        if data.get('supplier_expected_date'):
            design.supplier_expected_date = datetime.strptime(data['supplier_expected_date'], '%Y-%m-%d').date()
        if data.get('supplier_delivered_date'):
            design.supplier_delivered_date = datetime.strptime(data['supplier_delivered_date'], '%Y-%m-%d').date()

        # Auto-Datum setzen
        if design.supplier_order_status == 'ordered' and not design.supplier_order_date:
            design.supplier_order_date = datetime.utcnow().date()
        if design.supplier_order_status == 'delivered' and not design.supplier_delivered_date:
            design.supplier_delivered_date = datetime.utcnow().date()

        # Auto SupplierOrder erstellen wenn bestellt aber noch keine Bestellung existiert
        if design.supplier_order_status == 'ordered' and not design.supplier_order_id and design.supplier_id:
            try:
                from src.models.models import SupplierOrder, Supplier, Order
                from datetime import date as dt_date

                supplier = Supplier.query.get(design.supplier_id)
                order = Order.query.get(design.order_id)

                order_id_str = f"SDO{datetime.now().strftime('%Y%m%d%H%M%S')}"
                try:
                    from src.controllers.purchasing_controller import generate_purchase_order_number
                    order_number = generate_purchase_order_number(created_by=current_user.username)
                except Exception:
                    order_number = f"PO-{datetime.now().strftime('%Y%m%d-%H%M')}"

                delivery_days = supplier.delivery_time_days or 7 if supplier else 7
                expected_delivery = dt_date.today() + __import__('datetime').timedelta(days=delivery_days)

                type_labels = {'stick': 'Stickerei', 'druck': 'Druck', 'dtf': 'DTF-Transfer',
                               'flex': 'Flex', 'flock': 'Flock', 'sublimation': 'Sublimation'}

                items_list = [{
                    'design_id': design.id,
                    'design_name': design.design_name or design.get_position_label(),
                    'design_type': type_labels.get(design.design_type, design.design_type or ''),
                    'position': design.get_position_label(),
                    'order_number': order.order_number if order else design.order_id,
                    'quantity': 1,
                    'unit_price': float(design.supplier_cost or 0),
                    'total': float(design.supplier_cost or 0),
                }]

                new_so = SupplierOrder(
                    id=order_id_str,
                    supplier_id=str(design.supplier_id),
                    order_number=order_number,
                    supplier_order_number=design.supplier_reference or '',
                    status='ordered',
                    order_date=dt_date.today(),
                    delivery_date=expected_delivery,
                    created_by=current_user.username,
                    linked_customer_orders=design.order_id,
                    notes=f"Design-Bestellung fuer Auftrag {order.order_number if order else design.order_id}",
                )
                new_so.set_items(items_list)
                new_so.subtotal = design.supplier_cost or 0
                new_so.total_amount = design.supplier_cost or 0

                db.session.add(new_so)
                design.supplier_order_id = new_so.id

                current_app.logger.info(f"Auto-SupplierOrder {order_number} fuer Design #{design.id} erstellt")
            except Exception as e:
                current_app.logger.warning(f"Auto-SupplierOrder fehlgeschlagen: {e}")

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Bestellstatus aktualisiert',
            'status': design.supplier_order_status,
            'status_label': design.get_supplier_status_label(),
            'badge_class': design.get_supplier_status_badge()
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Aktualisieren des Supplier-Status: {e}")
        return jsonify({'success': False, 'error': str(e)})


@order_design_bp.route('/design/<int:design_id>/print-file', methods=['POST'])
@login_required
def upload_print_file(design_id):
    """Druckdatei für externen Lieferanten hochladen"""
    try:
        design = OrderDesign.query.get(design_id)
        if not design:
            return jsonify({'success': False, 'error': 'Design nicht gefunden'})

        print_file = request.files.get('print_file')
        if not print_file or not print_file.filename:
            return jsonify({'success': False, 'error': 'Keine Datei ausgewählt'})

        filename = secure_filename(print_file.filename)
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'designs', 'print')
        os.makedirs(upload_folder, exist_ok=True)

        filepath = os.path.join(upload_folder, f"{design.order_id}_{design.position}_{filename}")
        print_file.save(filepath)

        design.print_file_path = f"designs/print/{design.order_id}_{design.position}_{filename}"
        design.print_file_name = print_file.filename
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Druckdatei hochgeladen',
            'file_name': design.print_file_name,
            'file_path': design.print_file_path
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Upload der Druckdatei: {e}")
        return jsonify({'success': False, 'error': str(e)})


@order_design_bp.route('/design/<int:design_id>/print-file', methods=['DELETE'])
@login_required
def delete_print_file(design_id):
    """Druckdatei löschen"""
    try:
        design = OrderDesign.query.get(design_id)
        if not design:
            return jsonify({'success': False, 'error': 'Design nicht gefunden'})

        if design.print_file_path:
            full_path = os.path.join(current_app.root_path, 'static', 'uploads', design.print_file_path)
            if os.path.exists(full_path):
                os.remove(full_path)

        design.print_file_path = None
        design.print_file_name = None
        db.session.commit()

        return jsonify({'success': True, 'message': 'Druckdatei gelöscht'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@order_design_bp.route('/design/<int:design_id>/create-supplier-order', methods=['POST'])
@login_required
def create_supplier_order_for_design(design_id):
    """Erstellt eine Lieferantenbestellung aus einer Design-Position"""
    try:
        design = OrderDesign.query.get(design_id)
        if not design:
            return jsonify({'success': False, 'error': 'Design nicht gefunden'})

        if not design.supplier_id:
            return jsonify({'success': False, 'error': 'Kein Lieferant ausgewählt'})

        from src.models.models import Supplier, SupplierOrder
        supplier = Supplier.query.get(design.supplier_id)
        if not supplier:
            return jsonify({'success': False, 'error': 'Lieferant nicht gefunden'})

        order = Order.query.get(design.order_id)

        # Bestellnummer generieren
        from datetime import date as dt_date
        from src.controllers.purchasing_controller import generate_purchase_order_number
        order_id_str = f"SDO{datetime.now().strftime('%Y%m%d%H%M%S')}"
        order_number = generate_purchase_order_number(created_by=current_user.username)

        # Lieferzeit berechnen
        delivery_days = supplier.delivery_time_days or 7
        expected_delivery = dt_date.today() + __import__('datetime').timedelta(days=delivery_days)

        # SupplierOrder erstellen
        type_labels = {'stick': 'Stickerei', 'druck': 'Druck', 'dtf': 'DTF-Transfer',
                       'flex': 'Flex', 'flock': 'Flock', 'sublimation': 'Sublimation'}

        items_list = [{
            'design_id': design.id,
            'design_name': design.design_name or design.get_position_label(),
            'design_type': type_labels.get(design.design_type, design.design_type),
            'position': design.get_position_label(),
            'order_number': order.order_number if order else design.order_id,
            'quantity': 1,
            'unit_price': float(design.supplier_cost or 0),
            'total': float(design.supplier_cost or 0),
        }]

        new_order = SupplierOrder(
            id=order_id_str,
            supplier_id=str(design.supplier_id),
            order_number=order_number,
            status='draft',
            order_date=dt_date.today(),
            delivery_date=expected_delivery,
            created_by=current_user.username,
            notes=f"Design-Bestellung für Auftrag {order.order_number if order else design.order_id}",
        )
        new_order.set_items(items_list)
        new_order.subtotal = design.supplier_cost or 0
        new_order.total_amount = design.supplier_cost or 0

        db.session.add(new_order)

        # Design mit Bestellung verknüpfen
        design.supplier_order_id = new_order.id
        design.supplier_order_status = 'ordered'
        if not design.supplier_order_date:
            design.supplier_order_date = dt_date.today()
        design.supplier_expected_date = expected_delivery

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Bestellung {order_number} erstellt',
            'order_id': new_order.id,
            'order_number': order_number,
            'supplier_name': supplier.name
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Erstellen der Lieferantenbestellung: {e}")
        return jsonify({'success': False, 'error': str(e)})


def get_position_label(position_code):
    """Gibt das Label für einen Position-Code zurück (dynamisch aus DB)"""
    try:
        from src.models.order_workflow import OrderDesign
        for code, label in OrderDesign.get_position_choices_dynamic():
            if code == position_code:
                return label
    except Exception:
        pass
    return position_code
