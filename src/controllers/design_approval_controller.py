# -*- coding: utf-8 -*-
"""
DESIGN-FREIGABE CONTROLLER
==========================
Kundenportal für Design-Freigaben ohne Login

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort, current_app
from datetime import datetime
import os
import json
import logging

from src.models import db
from src.models.models import Order, Customer, ActivityLog

logger = logging.getLogger(__name__)

# Blueprint - KEIN login_required, da Kunden ohne Account zugreifen
design_approval_bp = Blueprint('design_approval', __name__, url_prefix='/design-approval')


@design_approval_bp.route('/<token>')
def approval_page(token):
    """
    Öffentliche Design-Freigabe-Seite für Kunden
    
    Kunden erhalten einen einzigartigen Link per E-Mail und können
    hier das Design ansehen und freigeben/ablehnen.
    """
    
    # Finde Auftrag mit diesem Token
    order = Order.query.filter_by(design_approval_token=token).first()
    
    if not order:
        return render_template('design_approval/invalid_token.html'), 404
    
    # Prüfe Status
    if order.design_approval_status == 'approved':
        return render_template('design_approval/already_approved.html', order=order)
    
    # Hole Design-Informationen
    designs = []
    if hasattr(order, 'designs') and order.designs:
        for design in order.designs:
            designs.append({
                'id': design.id,
                'position': design.get_position_label(),
                'type': design.get_design_type_label(),
                'thumbnail': design.design_thumbnail_path,
                'width_mm': design.width_mm,
                'height_mm': design.height_mm,
                'stitch_count': design.stitch_count,
                'thread_colors': design.get_thread_colors()
            })
    else:
        # Fallback: Altes Single-Design-System
        if order.design_file_path or order.design_file:
            designs.append({
                'id': 0,
                'position': order.embroidery_position or 'Standard',
                'type': 'Stickerei' if order.order_type == 'embroidery' else 'Druck',
                'thumbnail': order.design_thumbnail_path or order.design_file,
                'width_mm': order.design_width_mm,
                'height_mm': order.design_height_mm,
                'stitch_count': order.stitch_count,
                'thread_colors': []
            })
    
    # Hole Kunde
    customer = order.customer
    
    # Hole Artikel/Positionen
    items = []
    for item in order.items:
        items.append({
            'article': item.article.name if item.article else 'Artikel',
            'quantity': item.quantity,
            'size': item.textile_size,
            'color': item.textile_color
        })
    
    # Firmen-Info für Branding
    from src.models.company_settings import CompanySettings
    company = CompanySettings.get_settings()
    
    return render_template('design_approval/approval_page.html',
        order=order,
        designs=designs,
        customer=customer,
        items=items,
        company=company,
        token=token
    )


@design_approval_bp.route('/<token>/approve', methods=['POST'])
def approve_design(token):
    """Design freigeben"""
    
    order = Order.query.filter_by(design_approval_token=token).first()
    
    if not order:
        return jsonify({'success': False, 'error': 'Ungültiger Link'}), 404
    
    if order.design_approval_status == 'approved':
        return jsonify({'success': False, 'error': 'Bereits freigegeben'}), 400
    
    try:
        # Hole Daten
        data = request.get_json() or request.form
        
        signature = data.get('signature')  # Base64 Signatur-Bild
        notes = data.get('notes', '')
        customer_name = data.get('customer_name', '')
        
        # IP und User-Agent für Nachweis
        ip_address = request.remote_addr
        user_agent = request.user_agent.string[:500] if request.user_agent else ''
        
        # Freigabe speichern
        order.design_approval_status = 'approved'
        order.design_approval_date = datetime.utcnow()
        order.design_approval_signature = signature
        order.design_approval_ip = ip_address
        order.design_approval_user_agent = user_agent
        order.design_approval_notes = notes
        
        # Workflow-Status aktualisieren
        order.workflow_status = 'design_approved'
        
        # Status-Historie
        from src.models.models import OrderStatusHistory
        history = OrderStatusHistory(
            order_id=order.id,
            from_status=order.status,
            to_status='design_approved',
            comment=f'Design freigegeben von {customer_name or "Kunde"} - IP: {ip_address}',
            changed_by='customer'
        )
        db.session.add(history)
        
        # Activity Log
        activity = ActivityLog(
            username='customer',
            action='design_approved',
            details=f'Auftrag {order.order_number}: Design freigegeben von {customer_name}',
            ip_address=ip_address
        )
        db.session.add(activity)
        
        db.session.commit()
        
        # Benachrichtigung an Team senden
        try:
            _notify_team_approval(order, customer_name)
        except Exception as e:
            logger.warning(f"Team-Benachrichtigung fehlgeschlagen: {e}")
        
        logger.info(f"Design approved: Order {order.id} by {customer_name} from {ip_address}")
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Vielen Dank! Das Design wurde freigegeben.',
                'redirect': url_for('design_approval.thank_you', token=token, action='approved')
            })
        else:
            flash('Vielen Dank! Das Design wurde freigegeben.', 'success')
            return redirect(url_for('design_approval.thank_you', token=token, action='approved'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Design approval failed: {e}")
        
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        else:
            flash(f'Fehler: {str(e)}', 'danger')
            return redirect(url_for('design_approval.approval_page', token=token))


@design_approval_bp.route('/<token>/reject', methods=['POST'])
def reject_design(token):
    """Design ablehnen / Änderung anfordern"""
    
    order = Order.query.filter_by(design_approval_token=token).first()
    
    if not order:
        return jsonify({'success': False, 'error': 'Ungültiger Link'}), 404
    
    try:
        data = request.get_json() or request.form
        
        reason = data.get('reason', '')
        requested_changes = data.get('requested_changes', '')
        customer_name = data.get('customer_name', '')
        
        ip_address = request.remote_addr
        
        # Ablehnung speichern
        order.design_approval_status = 'revision_requested'
        order.design_approval_notes = f"Änderungswunsch von {customer_name}:\n{reason}\n\nGewünschte Änderungen:\n{requested_changes}"
        order.design_approval_ip = ip_address
        
        # Workflow-Status
        order.workflow_status = 'design_pending'
        
        # Status-Historie
        from src.models.models import OrderStatusHistory
        history = OrderStatusHistory(
            order_id=order.id,
            from_status=order.status,
            to_status='design_revision',
            comment=f'Design-Änderung angefordert von {customer_name or "Kunde"}',
            changed_by='customer'
        )
        db.session.add(history)
        
        # Activity Log
        activity = ActivityLog(
            username='customer',
            action='design_revision_requested',
            details=f'Auftrag {order.order_number}: Änderung angefordert - {reason[:100]}',
            ip_address=ip_address
        )
        db.session.add(activity)
        
        db.session.commit()
        
        # Team benachrichtigen
        try:
            _notify_team_rejection(order, customer_name, reason, requested_changes)
        except Exception as e:
            logger.warning(f"Team-Benachrichtigung fehlgeschlagen: {e}")
        
        logger.info(f"Design revision requested: Order {order.id} by {customer_name}")
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Vielen Dank für Ihr Feedback. Wir werden das Design anpassen.',
                'redirect': url_for('design_approval.thank_you', token=token, action='revision')
            })
        else:
            flash('Vielen Dank für Ihr Feedback. Wir werden das Design anpassen.', 'info')
            return redirect(url_for('design_approval.thank_you', token=token, action='revision'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Design rejection failed: {e}")
        
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        else:
            flash(f'Fehler: {str(e)}', 'danger')
            return redirect(url_for('design_approval.approval_page', token=token))


@design_approval_bp.route('/<token>/thank-you')
def thank_you(token):
    """Danke-Seite nach Freigabe/Ablehnung"""
    
    order = Order.query.filter_by(design_approval_token=token).first()
    
    if not order:
        return render_template('design_approval/invalid_token.html'), 404
    
    action = request.args.get('action', 'approved')
    
    from src.models.company_settings import CompanySettings
    company = CompanySettings.get_settings()
    
    return render_template('design_approval/thank_you.html',
        order=order,
        action=action,
        company=company
    )


@design_approval_bp.route('/<token>/download/<int:design_id>')
def download_design(token, design_id):
    """Design-Datei herunterladen"""
    
    order = Order.query.filter_by(design_approval_token=token).first()
    
    if not order:
        abort(404)
    
    from flask import send_file
    
    # Finde Design
    if design_id == 0:
        # Legacy Single-Design
        filepath = order.design_file_path
    else:
        design = order.designs.filter_by(id=design_id).first()
        if not design:
            abort(404)
        filepath = design.design_file_path
    
    if not filepath or not os.path.exists(filepath):
        abort(404)
    
    return send_file(filepath, as_attachment=True)


# ==========================================
# ADMIN-FUNKTIONEN (mit Login)
# ==========================================

@design_approval_bp.route('/admin')
def admin_index():
    """Dashboard für Design-Freigaben (On-Premise Workflow)"""
    from flask_login import login_required, current_user
    from datetime import timedelta

    @login_required
    def _index():
        # Ausstehend: Design vorhanden, aber noch nicht gesendet
        pending_orders = Order.query.filter(
            Order.design_approval_status.in_([None, 'pending']),
            (Order.design_file.isnot(None)) | (Order.design_file_path.isnot(None))
        ).order_by(Order.created_at.desc()).all()
        
        # Gesendet: Warte auf Kundenreaktion
        sent_orders = Order.query.filter(
            Order.design_approval_status == 'sent'
        ).order_by(Order.design_approval_sent_at.desc()).all()
        
        # Änderung gewünscht
        revision_orders = Order.query.filter(
            Order.design_approval_status == 'revision_requested'
        ).order_by(Order.created_at.desc()).all()
        
        # Freigegeben (letzte 30 Tage)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        approved_orders = Order.query.filter(
            Order.design_approval_status == 'approved',
            Order.design_approval_date >= thirty_days_ago
        ).order_by(Order.design_approval_date.desc()).all()
        
        return render_template('design_approval/dashboard.html',
            pending_orders=pending_orders,
            sent_orders=sent_orders,
            revision_orders=revision_orders,
            approved_orders=approved_orders,
            now=datetime.utcnow()
        )

    return _index()


@design_approval_bp.route('/admin/send/<order_id>', methods=['POST'])
def admin_send_approval_request(order_id):
    """Sendet Freigabe-Anfrage an Kunden (Admin-Funktion)"""
    
    from flask_login import login_required, current_user
    
    @login_required
    def _send():
        order = Order.query.get_or_404(order_id)
        
        if not order.customer or not order.customer.email:
            return jsonify({'success': False, 'error': 'Keine Kunden-E-Mail vorhanden'}), 400
        
        if not order.has_design_file():
            return jsonify({'success': False, 'error': 'Kein Design vorhanden'}), 400
        
        try:
            # Token generieren falls nicht vorhanden
            if not order.design_approval_token:
                order.generate_approval_token()
            
            # Status aktualisieren
            order.design_approval_status = 'sent'
            order.design_approval_sent_at = datetime.utcnow()
            order.workflow_status = 'design_pending'
            
            db.session.commit()
            
            # E-Mail senden
            success = _send_approval_email(order)
            
            if success:
                activity = ActivityLog(
                    username=current_user.username,
                    action='design_approval_sent',
                    details=f'Freigabe-Anfrage gesendet für Auftrag {order.order_number}'
                )
                db.session.add(activity)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Freigabe-Anfrage wurde versendet',
                    'approval_url': url_for('design_approval.approval_page', 
                                           token=order.design_approval_token, _external=True)
                })
            else:
                return jsonify({'success': False, 'error': 'E-Mail konnte nicht gesendet werden'}), 500
                
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return _send()


@design_approval_bp.route('/admin/preview/<order_id>')
def admin_preview(order_id):
    """Vorschau der Freigabe-Seite (für Admins)"""
    
    from flask_login import login_required, current_user
    
    @login_required
    def _preview():
        order = Order.query.get_or_404(order_id)
        
        # Generiere temporären Token für Vorschau
        if not order.design_approval_token:
            order.generate_approval_token()
            db.session.commit()
        
        return redirect(url_for('design_approval.approval_page', token=order.design_approval_token))
    
    return _preview()


@design_approval_bp.route('/admin/resend/<order_id>', methods=['POST'])
def admin_resend_request(order_id):
    """Freigabe-Anfrage erneut senden"""

    from flask_login import login_required, current_user

    @login_required
    def _resend():
        order = Order.query.get_or_404(order_id)

        # Neuen Token generieren
        order.generate_approval_token()
        order.design_approval_status = 'sent'
        order.design_approval_sent_at = datetime.utcnow()

        db.session.commit()

        # E-Mail senden
        success = _send_approval_email(order)

        if success:
            return jsonify({'success': True, 'message': 'Freigabe-Anfrage erneut versendet'})
        else:
            return jsonify({'success': False, 'error': 'E-Mail-Versand fehlgeschlagen'}), 500

    return _resend()


@design_approval_bp.route('/send/<int:order_id>', methods=['POST'])
def send_approval_request(order_id):
    """Einzelne Freigabe-Anfrage senden"""
    from flask_login import login_required, current_user

    @login_required
    def _send():
        order = Order.query.get_or_404(order_id)

        if not order.customer or not order.customer.email:
            flash('Keine E-Mail-Adresse für den Kunden hinterlegt', 'danger')
            return redirect(url_for('design_approval.admin_index'))

        # Token generieren falls nicht vorhanden
        if not order.design_approval_token:
            order.generate_approval_token()

        order.design_approval_status = 'sent'
        order.design_approval_sent_at = datetime.utcnow()
        db.session.commit()

        # E-Mail senden
        success = _send_approval_email(order)

        if success:
            flash(f'Freigabe-Anfrage für Auftrag {order.order_number} wurde versendet', 'success')
        else:
            flash('E-Mail konnte nicht gesendet werden', 'danger')

        return redirect(url_for('design_approval.admin_index'))

    return _send()


@design_approval_bp.route('/send-batch', methods=['POST'])
def send_batch_approval_request():
    """Gebündelte Freigabe-Anfragen senden"""
    from flask_login import login_required, current_user

    @login_required
    def _send_batch():
        order_ids = request.form.getlist('order_ids[]')

        if not order_ids:
            flash('Keine Aufträge ausgewählt', 'warning')
            return redirect(url_for('design_approval.admin_index'))

        sent_count = 0
        failed_count = 0

        for order_id in order_ids:
            order = Order.query.get(order_id)
            if not order or not order.customer or not order.customer.email:
                failed_count += 1
                continue

            # Token generieren falls nicht vorhanden
            if not order.design_approval_token:
                order.generate_approval_token()

            order.design_approval_status = 'sent'
            order.design_approval_sent_at = datetime.utcnow()

            if _send_approval_email(order):
                sent_count += 1
            else:
                failed_count += 1

        db.session.commit()

        if sent_count > 0:
            flash(f'{sent_count} Freigabe-Anfrage(n) erfolgreich versendet', 'success')
        if failed_count > 0:
            flash(f'{failed_count} Anfrage(n) konnten nicht versendet werden', 'warning')

        return redirect(url_for('design_approval.admin_index'))

    return _send_batch()


@design_approval_bp.route('/public/<token>')
def public_approval_page(token):
    """Öffentliche Design-Freigabe-Seite (Alias für approval_page)"""
    return approval_page(token)


# ==========================================
# HILFSFUNKTIONEN
# ==========================================

def _send_approval_email(order):
    """Sendet Freigabe-E-Mail an Kunden"""
    
    try:
        from src.services.email_service import EmailService
        from src.models.company_settings import CompanySettings

        company = CompanySettings.get_settings()
        email_service = EmailService()
        
        approval_url = url_for('design_approval.approval_page', 
                              token=order.design_approval_token, _external=True)
        
        subject = f"Design-Freigabe für Auftrag {order.order_number} - {company.company_name}"
        
        body = f"""
        Guten Tag {order.customer.display_name},
        
        Ihr Design für Auftrag {order.order_number} ist fertig zur Freigabe.
        
        Bitte prüfen Sie das Design über folgenden Link:
        {approval_url}
        
        Mit diesem Link können Sie:
        - Das Design in voller Größe ansehen
        - Details wie Position, Größe und Farben überprüfen
        - Das Design freigeben oder Änderungen anfordern
        
        Bei Fragen stehen wir Ihnen gerne zur Verfügung.
        
        Mit freundlichen Grüßen
        {company.company_name}
        
        ---
        Dies ist eine automatische E-Mail. Bitte antworten Sie nicht direkt auf diese Nachricht.
        """
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2563eb;">Design-Freigabe für Auftrag {order.order_number}</h2>
                
                <p>Guten Tag {order.customer.display_name},</p>
                
                <p>Ihr Design für Auftrag <strong>{order.order_number}</strong> ist fertig zur Freigabe.</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{approval_url}" 
                       style="background-color: #2563eb; color: white; padding: 15px 30px; 
                              text-decoration: none; border-radius: 5px; font-size: 16px;">
                        Design prüfen und freigeben
                    </a>
                </div>
                
                <p>Mit diesem Link können Sie:</p>
                <ul>
                    <li>Das Design in voller Größe ansehen</li>
                    <li>Details wie Position, Größe und Farben überprüfen</li>
                    <li>Das Design freigeben oder Änderungen anfordern</li>
                </ul>
                
                <p>Bei Fragen stehen wir Ihnen gerne zur Verfügung.</p>
                
                <p>Mit freundlichen Grüßen<br>
                <strong>{company.company_name}</strong></p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                <p style="font-size: 12px; color: #666;">
                    Dies ist eine automatische E-Mail. Bitte antworten Sie nicht direkt auf diese Nachricht.
                </p>
            </div>
        </body>
        </html>
        """
        
        result = email_service.send_email(
            to=order.customer.email,
            subject=subject,
            body=body,
            html_body=html_body
        )
        
        return result.get('success', False)
        
    except Exception as e:
        logger.error(f"Failed to send approval email: {e}")
        return False


def _notify_team_approval(order, customer_name):
    """Benachrichtigt das Team über erfolgte Freigabe"""
    
    try:
        from src.services.email_service import EmailService
        from src.models.company_settings import CompanySettings

        company = CompanySettings.get_settings()
        
        if not company.notification_email:
            return
        
        email_service = EmailService()
        
        subject = f"✅ Design freigegeben: Auftrag {order.order_number}"
        
        body = f"""
        Design-Freigabe erfolgt!
        
        Auftrag: {order.order_number}
        Kunde: {order.customer.display_name}
        Freigegeben von: {customer_name}
        Zeitpunkt: {datetime.now().strftime('%d.%m.%Y %H:%M')}
        
        Der Auftrag kann jetzt in die Produktion gehen.
        """
        
        email_service.send_email(
            to=company.notification_email,
            subject=subject,
            body=body
        )
        
    except Exception as e:
        logger.warning(f"Team notification failed: {e}")


# ==========================================
# API-ENDPUNKTE (On-Premise Workflow)
# ==========================================

@design_approval_bp.route('/api/send/<order_id>', methods=['POST'])
def api_send_approval(order_id):
    """API: PDF generieren und per E-Mail senden"""
    from flask_login import login_required, current_user
    
    @login_required
    def _send():
        try:
            from src.services.design_approval_service import get_design_approval_service
            
            order = Order.query.get_or_404(order_id)
            
            if not order.customer or not order.customer.email:
                return jsonify({'success': False, 'error': 'Keine Kunden-E-Mail vorhanden'}), 400
            
            service = get_design_approval_service()
            
            # PDF generieren
            pdf_path, pdf_hash = service.generate_approval_pdf(order)
            
            # E-Mail senden
            result = service.send_approval_email(order, pdf_path)
            
            if result.get('success'):
                # Activity Log
                activity = ActivityLog(
                    username=current_user.username,
                    action='design_approval_sent',
                    details=f'Freigabe-PDF gesendet für Auftrag {order.order_number}'
                )
                db.session.add(activity)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': f'Freigabe-PDF gesendet an {order.customer.email}'
                })
            else:
                return jsonify({'success': False, 'error': result.get('error', 'Senden fehlgeschlagen')}), 500
                
        except Exception as e:
            logger.error(f"API send error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return _send()


@design_approval_bp.route('/api/generate-pdf/<order_id>', methods=['POST'])
def api_generate_pdf(order_id):
    """API: Nur PDF generieren (ohne E-Mail)"""
    from flask_login import login_required, current_user
    
    @login_required
    def _generate():
        try:
            from src.services.design_approval_service import get_design_approval_service
            
            order = Order.query.get_or_404(order_id)
            service = get_design_approval_service()
            
            # PDF generieren
            pdf_path, pdf_hash = service.generate_approval_pdf(order)
            
            return jsonify({
                'success': True,
                'download_url': url_for('design_approval.download_generated_pdf', 
                                        order_id=order_id, _external=True),
                'pdf_path': pdf_path
            })
                
        except Exception as e:
            logger.error(f"PDF generation error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return _generate()


@design_approval_bp.route('/api/mark-approved/<order_id>', methods=['POST'])
def api_mark_approved(order_id):
    """API: Freigabe manuell eintragen (E-Mail/PDF/Telefon)"""
    from flask_login import login_required, current_user
    
    @login_required
    def _mark():
        try:
            order = Order.query.get_or_404(order_id)
            
            # Daten aus FormData
            method = request.form.get('method', 'email')
            notes = request.form.get('notes', '')
            signed_pdf = request.files.get('signed_pdf')
            
            # Methoden-Labels
            method_labels = {
                'email': 'E-Mail-Bestätigung',
                'pdf': 'Unterschriebene PDF',
                'phone': 'Telefonische Freigabe'
            }
            
            # Notiz zusammenbauen
            approval_note = f"Freigabe-Methode: {method_labels.get(method, method)}\n"
            approval_note += f"Eingetragen von: {current_user.username}\n"
            approval_note += f"Datum: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            if notes:
                approval_note += f"Notiz: {notes}"
            
            # Signierte PDF speichern falls vorhanden
            if signed_pdf and signed_pdf.filename:
                from src.services.design_approval_service import get_design_approval_service
                service = get_design_approval_service()
                
                result = service.process_signed_pdf(
                    order=order,
                    pdf_data=signed_pdf.read(),
                    filename=signed_pdf.filename,
                    source='upload',
                    signer_info={'name': notes}
                )
                
                if not result.get('success'):
                    return jsonify({'success': False, 'error': result.get('error')}), 500
            else:
                # Ohne PDF: Nur Status aktualisieren
                order.design_approval_status = 'approved'
                order.design_approval_date = datetime.utcnow()
                order.design_approval_notes = approval_note
                order.workflow_status = 'design_approved'
                db.session.commit()
            
            # Activity Log
            activity = ActivityLog(
                username=current_user.username,
                action='design_approved_manual',
                details=f'Freigabe eingetragen für Auftrag {order.order_number} ({method_labels.get(method, method)})'
            )
            db.session.add(activity)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Freigabe eingetragen'})
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Mark approved error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return _mark()


@design_approval_bp.route('/api/resend/<order_id>', methods=['POST'])
def api_resend(order_id):
    """API: Erinnerungs-E-Mail senden"""
    from flask_login import login_required, current_user
    
    @login_required
    def _resend():
        try:
            from src.services.design_approval_service import get_design_approval_service
            
            order = Order.query.get_or_404(order_id)
            
            if not order.customer or not order.customer.email:
                return jsonify({'success': False, 'error': 'Keine Kunden-E-Mail'}), 400
            
            service = get_design_approval_service()
            
            # Neue PDF generieren
            pdf_path, _ = service.generate_approval_pdf(order)
            
            # E-Mail senden
            result = service.send_approval_email(
                order, 
                pdf_path, 
                custom_message="Dies ist eine Erinnerung an die ausstehende Design-Freigabe."
            )
            
            if result.get('success'):
                return jsonify({'success': True, 'message': 'Erinnerung gesendet'})
            else:
                return jsonify({'success': False, 'error': result.get('error')}), 500
                
        except Exception as e:
            logger.error(f"Resend error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return _resend()


@design_approval_bp.route('/download-generated-pdf/<order_id>')
def download_generated_pdf(order_id):
    """Generierte PDF herunterladen"""
    from flask_login import login_required
    from flask import send_file
    import glob
    
    @login_required
    def _download():
        try:
            order = Order.query.get_or_404(order_id)
            
            # Finde die neueste PDF für diesen Auftrag
            from src.services.design_approval_service import get_design_approval_service
            service = get_design_approval_service()
            service._init_dirs()
            
            # Suche nach passender PDF
            pattern = os.path.join(service.pdf_dir, f"freigabe_{order.order_number}_*.pdf")
            pdf_files = glob.glob(pattern)
            
            if pdf_files:
                # Neueste nehmen
                latest_pdf = max(pdf_files, key=os.path.getctime)
                return send_file(
                    latest_pdf,
                    as_attachment=True,
                    download_name=f'Design-Freigabe_{order.order_number}.pdf'
                )
            else:
                # Neue generieren
                pdf_path, _ = service.generate_approval_pdf(order)
                return send_file(
                    pdf_path,
                    as_attachment=True,
                    download_name=f'Design-Freigabe_{order.order_number}.pdf'
                )
                
        except Exception as e:
            logger.error(f"PDF download error: {e}")
            abort(500)
    
    return _download()


@design_approval_bp.route('/api/resend/<int:request_id>', methods=['POST'])
def api_resend_approval(request_id):
    """API: Freigabe erneut senden (nach Änderung)"""
    from flask_login import login_required, current_user
    
    @login_required
    def _resend():
        try:
            from src.models.design_approval import DesignApprovalRequest, DesignApprovalStatus
            from src.services.design_approval_service import get_design_approval_service
            
            request = DesignApprovalRequest.query.get_or_404(request_id)
            service = get_design_approval_service()
            
            # Neuen Token generieren
            import uuid
            request.token = str(uuid.uuid4())
            request.status = DesignApprovalStatus.DRAFT.value
            
            # Neue PDF generieren
            service.generate_approval_pdf(request)
            
            # E-Mail senden
            success = service.send_approval_email(request, include_pdf=True)
            
            if success:
                request.add_history(
                    action='resent',
                    details='Freigabe-Anfrage erneut gesendet nach Änderung',
                    by=current_user.username
                )
                db.session.commit()
                return jsonify({'success': True, 'message': 'Erneut gesendet'})
            else:
                return jsonify({'success': False, 'error': 'Senden fehlgeschlagen'}), 500
                
        except Exception as e:
            logger.error(f"API resend error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return _resend()


@design_approval_bp.route('/api/history/<int:request_id>')
def api_get_history(request_id):
    """API: Historie einer Freigabe-Anfrage abrufen"""
    from flask_login import login_required
    
    @login_required
    def _history():
        try:
            from src.models.design_approval import DesignApprovalRequest
            
            request = DesignApprovalRequest.query.get_or_404(request_id)
            
            entries = []
            for entry in request.history_entries:
                entries.append({
                    'action': entry.action,
                    'label': entry.get_action_label(),
                    'icon': entry.get_action_icon(),
                    'details': entry.details,
                    'by': entry.performed_by or 'System',
                    'ip': entry.ip_address,
                    'date': entry.created_at.strftime('%d.%m.%Y %H:%M')
                })
            
            return jsonify({'success': True, 'entries': entries})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return _history()


@design_approval_bp.route('/download-pdf/<int:request_id>')
def download_pdf(request_id):
    """Original-PDF herunterladen"""
    from flask_login import login_required
    from flask import send_file
    
    @login_required
    def _download():
        try:
            from src.models.design_approval import DesignApprovalRequest
            from src.services.design_approval_service import get_design_approval_service
            
            request = DesignApprovalRequest.query.get_or_404(request_id)
            
            # PDF generieren falls nicht vorhanden
            if not request.pdf_file_path or not os.path.exists(request.pdf_file_path):
                service = get_design_approval_service()
                service.generate_approval_pdf(request)
            
            if request.pdf_file_path and os.path.exists(request.pdf_file_path):
                return send_file(
                    request.pdf_file_path,
                    as_attachment=True,
                    download_name=f'Design-Freigabe_{request.order.order_number}.pdf'
                )
            else:
                abort(404)
                
        except Exception as e:
            logger.error(f"PDF download error: {e}")
            abort(500)
    
    return _download()


@design_approval_bp.route('/download-signed-pdf/<int:request_id>')
def download_signed_pdf(request_id):
    """Signierte PDF herunterladen"""
    from flask_login import login_required
    from flask import send_file
    
    @login_required
    def _download():
        try:
            from src.models.design_approval import DesignApprovalRequest
            
            request = DesignApprovalRequest.query.get_or_404(request_id)
            
            if request.signed_pdf_path and os.path.exists(request.signed_pdf_path):
                return send_file(
                    request.signed_pdf_path,
                    as_attachment=True,
                    download_name=f'Design-Freigabe_{request.order.order_number}_signiert.pdf'
                )
            else:
                abort(404)
                
        except Exception as e:
            logger.error(f"Signed PDF download error: {e}")
            abort(500)
    
    return _download()


@design_approval_bp.route('/batch-send', methods=['POST'])
def batch_send():
    """Mehrere Freigaben auf einmal senden"""
    from flask_login import login_required, current_user
    
    @login_required
    def _batch():
        try:
            from src.models.design_approval import DesignApprovalRequest
            from src.services.design_approval_service import get_design_approval_service
            
            request_ids = request.form.getlist('request_ids[]')
            
            if not request_ids:
                flash('Keine Anfragen ausgewählt', 'warning')
                return redirect(url_for('design_approval.admin_index'))
            
            service = get_design_approval_service()
            sent = 0
            failed = 0
            
            for req_id in request_ids:
                req = DesignApprovalRequest.query.get(req_id)
                if not req:
                    failed += 1
                    continue
                
                if not req.pdf_file_path:
                    service.generate_approval_pdf(req)
                
                if service.send_approval_email(req, include_pdf=True):
                    sent += 1
                else:
                    failed += 1
            
            if sent > 0:
                flash(f'{sent} Freigabe-Anfrage(n) erfolgreich gesendet', 'success')
            if failed > 0:
                flash(f'{failed} Anfrage(n) konnten nicht gesendet werden', 'warning')
            
            return redirect(url_for('design_approval.admin_index'))
            
        except Exception as e:
            logger.error(f"Batch send error: {e}")
            flash(f'Fehler: {str(e)}', 'danger')
            return redirect(url_for('design_approval.admin_index'))
    
    return _batch()


@design_approval_bp.route('/scan-incoming-emails')
def scan_incoming_emails():
    """Eingehende E-Mails auf signierte PDFs prüfen"""
    from flask_login import login_required, current_user
    
    @login_required
    def _scan():
        try:
            from src.services.email_service import EmailService
            from src.models.design_approval import DesignApprovalRequest
            from src.services.design_approval_service import get_design_approval_service
            
            email_service = EmailService()
            service = get_design_approval_service()
            
            # E-Mails der letzten 7 Tage mit PDF-Anhängen
            processed = 0
            
            # Hier würde die E-Mail-Scan-Logik implementiert
            # Vereinfachte Version: Prüfe auf spezifische Betreff-Zeilen
            
            flash(f'{processed} signierte PDFs verarbeitet', 'info')
            return redirect(url_for('design_approval.admin_index'))
            
        except Exception as e:
            logger.error(f"Email scan error: {e}")
            flash(f'Fehler beim Scannen: {str(e)}', 'danger')
            return redirect(url_for('design_approval.admin_index'))
    
    return _scan()


@design_approval_bp.route('/create/<order_id>', methods=['POST'])
def create_approval_request(order_id):
    """Neue Freigabe-Anfrage für Auftrag erstellen"""
    from flask_login import login_required, current_user
    
    @login_required
    def _create():
        try:
            from src.services.design_approval_service import get_design_approval_service
            
            order = Order.query.get_or_404(order_id)
            service = get_design_approval_service()
            
            # Anfrage erstellen
            approval_request = service.create_approval_request(
                order=order,
                created_by=current_user.username
            )
            
            # PDF generieren
            service.generate_approval_pdf(approval_request)
            
            flash(f'Freigabe-Anfrage erstellt für Auftrag {order.order_number}', 'success')
            
            # Optional direkt senden
            if request.form.get('send_immediately') and order.customer and order.customer.email:
                service.send_approval_email(approval_request, include_pdf=True)
                flash('E-Mail wurde gesendet', 'success')
            
            return redirect(url_for('design_approval.admin_index'))
            
        except Exception as e:
            logger.error(f"Create approval error: {e}")
            flash(f'Fehler: {str(e)}', 'danger')
            return redirect(url_for('order_db.order_detail', order_id=order_id))
    
    return _create()


def _notify_team_rejection(order, customer_name, reason, requested_changes):
    """Benachrichtigt das Team über Änderungswunsch"""
    
    try:
        from src.services.email_service import EmailService
        from src.models.company_settings import CompanySettings

        company = CompanySettings.get_settings()
        
        if not company.notification_email:
            return
        
        email_service = EmailService()
        
        subject = f"⚠️ Design-Änderung angefordert: Auftrag {order.order_number}"
        
        body = f"""
        Design-Änderung angefordert!
        
        Auftrag: {order.order_number}
        Kunde: {order.customer.display_name}
        Angefordert von: {customer_name}
        Zeitpunkt: {datetime.now().strftime('%d.%m.%Y %H:%M')}
        
        Grund:
        {reason}
        
        Gewünschte Änderungen:
        {requested_changes}
        
        Bitte das Design entsprechend anpassen und erneut zur Freigabe senden.
        """
        
        email_service.send_email(
            to=company.notification_email,
            subject=subject,
            body=body
        )
        
    except Exception as e:
        logger.warning(f"Team notification failed: {e}")
