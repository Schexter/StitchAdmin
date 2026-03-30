"""
Quote Approval Controller - Angebots-Freigabe
==============================================
Oeffentliche Seiten (ohne Login) fuer Kunden-Freigabe per Token-Link.
Admin-Routen fuer Versand und Verwaltung.
"""

from flask import Blueprint, render_template, request, jsonify, url_for, redirect, flash
from flask_login import login_required, current_user
from datetime import datetime
from src.models import db
from src.models.angebot import Angebot, AngebotStatus
import logging

logger = logging.getLogger(__name__)

quote_approval_bp = Blueprint('quote_approval', __name__, url_prefix='/angebot-freigabe')


# ============================================================
# OEFFENTLICHE SEITEN (kein Login noetig)
# ============================================================

@quote_approval_bp.route('/<token>')
def approval_page(token):
    """Oeffentliche Freigabe-Seite fuer den Kunden"""
    angebot = Angebot.query.filter_by(approval_token=token).first()
    if not angebot:
        return render_template('quote_approval/invalid_token.html'), 404

    if angebot.approval_status == 'approved':
        return render_template('quote_approval/already_approved.html', angebot=angebot)

    company = None
    try:
        from src.models.company_settings import CompanySettings
        company = CompanySettings.get_settings()
    except Exception:
        pass

    return render_template('quote_approval/approval_page.html',
                         angebot=angebot, token=token, company=company)


@quote_approval_bp.route('/<token>/approve', methods=['POST'])
def approve(token):
    """Kunde nimmt Angebot an"""
    angebot = Angebot.query.filter_by(approval_token=token).first()
    if not angebot:
        return jsonify({'success': False, 'error': 'Ungueltiger Link'}), 404

    if angebot.approval_status == 'approved':
        return jsonify({'success': False, 'error': 'Angebot wurde bereits freigegeben'}), 400

    data = request.get_json() or {}

    angebot.approve_quote(
        signature=data.get('signature'),
        ip_address=request.remote_addr,
        user_agent=str(request.user_agent)[:500] if request.user_agent else '',
        notes=data.get('notes', ''),
        name=data.get('customer_name', '')
    )
    db.session.commit()

    # Auto-Auftrag erstellen (inkl. OrderDesign aus Veredelungs-Positionen)
    auftrag = None
    try:
        auftrag = angebot.in_auftrag_umwandeln(created_by='customer')
        db.session.commit()
        logger.info(f"Auto-Auftrag {auftrag.order_number} aus Angebot {angebot.angebotsnummer} erstellt")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Auto-Auftrag fuer Angebot {angebot.angebotsnummer} fehlgeschlagen: {e}")

    # Team-Benachrichtigung
    _notify_team(angebot, 'approved', data.get('customer_name', ''), auftrag=auftrag)

    # CRM-Aktivitaet
    try:
        from src.models.crm_activities import Activity, ActivityType
        Activity.create_activity(
            activity_type=ActivityType.NOTE,
            titel=f"Angebot {angebot.angebotsnummer} vom Kunden freigegeben",
            beschreibung=f"Freigegeben von {data.get('customer_name', 'Kunde')} (IP: {request.remote_addr})",
            kunde_id=angebot.kunde_id,
            angebot_id=angebot.id,
            created_by='customer'
        )
    except Exception as e:
        logger.warning(f"CRM-Aktivitaet konnte nicht erstellt werden: {e}")

    logger.info(f"Angebot {angebot.angebotsnummer} freigegeben von {data.get('customer_name')} (IP: {request.remote_addr})")

    return jsonify({
        'success': True,
        'message': 'Vielen Dank! Das Angebot wurde angenommen.',
        'redirect': url_for('quote_approval.thank_you', token=token, action='approved')
    })


@quote_approval_bp.route('/<token>/reject', methods=['POST'])
def reject(token):
    """Kunde lehnt ab oder wuenscht Aenderungen"""
    angebot = Angebot.query.filter_by(approval_token=token).first()
    if not angebot:
        return jsonify({'success': False, 'error': 'Ungueltiger Link'}), 404

    data = request.get_json() or {}

    angebot.reject_quote(
        notes=data.get('reason', ''),
        ip_address=request.remote_addr,
        name=data.get('customer_name', '')
    )
    db.session.commit()

    _notify_team(angebot, 'rejected', data.get('customer_name', ''))

    logger.info(f"Angebot {angebot.angebotsnummer} abgelehnt von {data.get('customer_name')} (IP: {request.remote_addr})")

    return jsonify({
        'success': True,
        'message': 'Danke fuer Ihr Feedback. Wir passen das Angebot an.',
        'redirect': url_for('quote_approval.thank_you', token=token, action='revision')
    })


@quote_approval_bp.route('/<token>/pdf')
def download_pdf(token):
    """PDF-Download fuer Kunden per Freigabe-Token (oeffentlich, kein Login noetig)"""
    import io
    from flask import send_file
    angebot = Angebot.query.filter_by(approval_token=token).first()
    if not angebot:
        return "Ungueltiger Link", 404

    try:
        from src.controllers.angebote_controller import _build_angebot_pdf_bytes
        include_sig = bool(angebot.approval_signature)
        pdf_bytes = _build_angebot_pdf_bytes(angebot, include_signature=include_sig)
        safe_nr = angebot.angebotsnummer.replace('/', '-').replace('\\', '-')
        suffix = '_unterzeichnet' if include_sig else ''
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Angebot_{safe_nr}{suffix}.pdf'
        )
    except Exception as e:
        logger.error(f"PDF-Download Fehler fuer Token {token}: {e}")
        return "PDF konnte nicht generiert werden.", 500


@quote_approval_bp.route('/<token>/thank-you')
def thank_you(token):
    """Bestaetigung nach Freigabe/Ablehnung"""
    angebot = Angebot.query.filter_by(approval_token=token).first()
    if not angebot:
        return render_template('quote_approval/invalid_token.html'), 404

    company = None
    try:
        from src.models.company_settings import CompanySettings
        company = CompanySettings.get_settings()
    except Exception:
        pass

    action = request.args.get('action', 'approved')
    return render_template('quote_approval/thank_you.html',
                         angebot=angebot, action=action, company=company)


# ============================================================
# ADMIN-ROUTEN (Login erforderlich)
# ============================================================

@quote_approval_bp.route('/api/send/<int:angebot_id>', methods=['POST'])
@login_required
def api_send_approval(angebot_id):
    """Freigabe-Link per E-Mail versenden"""
    angebot = Angebot.query.get_or_404(angebot_id)

    if not angebot.kunde_email:
        return jsonify({'success': False, 'error': 'Keine E-Mail-Adresse vorhanden'}), 400

    # Token generieren und Status setzen
    angebot.send_approval_request()
    db.session.commit()

    # E-Mail senden
    approval_link = url_for('quote_approval.approval_page',
                           token=angebot.approval_token, _external=True)
    success = _send_approval_email(angebot, approval_link)

    if success:
        flash(f'Freigabe-Link an {angebot.kunde_email} versendet.', 'success')
        return jsonify({
            'success': True,
            'message': f'Freigabe-Link an {angebot.kunde_email} versendet',
            'approval_link': approval_link
        })
    else:
        return jsonify({
            'success': False,
            'error': 'E-Mail konnte nicht gesendet werden',
            'approval_link': approval_link
        }), 500


@quote_approval_bp.route('/api/mark-approved/<int:angebot_id>', methods=['POST'])
@login_required
def api_mark_approved(angebot_id):
    """Manuell als freigegeben markieren (Telefon/E-Mail/PDF-Upload)"""
    angebot = Angebot.query.get_or_404(angebot_id)

    data = request.get_json() or {}
    method = data.get('method', 'manual')

    angebot.approval_status = 'approved'
    angebot.approval_date = datetime.utcnow()
    angebot.approved_by_name = data.get('name', f'Manuell von {current_user.username}')
    angebot.approval_notes = f"Manuell freigegeben ({method}) von {current_user.username}"
    angebot.status = AngebotStatus.ANGENOMMEN
    db.session.commit()

    # Auto-Auftrag erstellen wenn gewuenscht
    auftrag_info = ''
    if data.get('create_order', True):
        try:
            auftrag = angebot.in_auftrag_umwandeln(created_by=current_user.username)
            db.session.commit()
            auftrag_info = f' Auftrag {auftrag.order_number} erstellt.'
            logger.info(f"Auto-Auftrag {auftrag.order_number} aus Angebot {angebot.angebotsnummer} erstellt")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Auto-Auftrag fehlgeschlagen: {e}")
            auftrag_info = f' Auto-Auftrag fehlgeschlagen: {e}'

    flash(f'Angebot {angebot.angebotsnummer} als freigegeben markiert.{auftrag_info}', 'success')
    return jsonify({'success': True})


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def _send_approval_email(angebot, approval_link):
    """Sendet die Freigabe-Email an den Kunden"""
    try:
        from src.services.email_service_new import EmailService

        company = None
        try:
            from src.models.company_settings import CompanySettings
            company = CompanySettings.get_settings()
        except Exception:
            pass

        company_name = company.company_name if company else 'StitchAdmin'

        subject = f"Angebots-Freigabe - {angebot.angebotsnummer} - {company_name}"

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
                        color: white; padding: 25px; text-align: center; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0; font-size: 24px;">Angebots-Freigabe</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">Angebot {angebot.angebotsnummer}</p>
            </div>

            <div style="padding: 30px; background: #f8f9fa; border-radius: 0 0 8px 8px;">
                <p>Guten Tag {angebot.kunde_name},</p>

                <p>Ihr Angebot <strong>{angebot.angebotsnummer}</strong> liegt zur Freigabe bereit.</p>

                <div style="background: white; padding: 20px; border-radius: 8px; margin: 25px 0;">
                    <h3 style="margin-top: 0; color: #2563eb;">Angebots-Details:</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 8px; font-weight: bold;">Angebotsnummer:</td>
                            <td style="padding: 8px;">{angebot.angebotsnummer}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 8px; font-weight: bold;">Gueltig bis:</td>
                            <td style="padding: 8px;">{angebot.gueltig_bis.strftime('%d.%m.%Y') if angebot.gueltig_bis else '-'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Gesamtbetrag (brutto):</td>
                            <td style="padding: 8px; font-weight: bold; color: #2563eb;">{angebot.brutto_gesamt:.2f} EUR</td>
                        </tr>
                    </table>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{approval_link}"
                       style="display: inline-block; background: #28a745; color: white; padding: 14px 35px;
                              text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px;">
                        Angebot ansehen &amp; freigeben
                    </a>
                </div>

                <div style="text-align: center; margin: 10px 0 25px 0;">
                    <a href="{approval_link}/pdf"
                       style="display: inline-block; background: #6c757d; color: white; padding: 10px 25px;
                              text-decoration: none; border-radius: 6px; font-size: 14px;">
                        Angebot als PDF herunterladen
                    </a>
                </div>

                <p style="color: #666; font-size: 14px;">
                    <strong>Aenderungen gewuenscht?</strong><br>
                    Auf der Freigabe-Seite koennen Sie auch Aenderungswuensche mitteilen.
                    Alternativ koennen Sie das PDF ausdrucken, unterschreiben und per Post oder E-Mail zuruecksenden.
                </p>

                <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 25px 0;">

                <p>Mit freundlichen Gruessen<br><strong>{company_name}</strong></p>
                {f'<p style="color: #999; font-size: 12px;">{company.phone or ""}</p>' if company and company.phone else ''}
            </div>
        </body>
        </html>
        """

        # PDF als Anhang generieren
        pdf_attachment = None
        try:
            import tempfile, os
            from src.controllers.angebote_controller import _build_angebot_pdf_bytes
            pdf_bytes = _build_angebot_pdf_bytes(angebot, include_signature=False)
            safe_nr = angebot.angebotsnummer.replace('/', '-').replace('\\', '-')
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf',
                                              prefix=f'Angebot_{safe_nr}_')
            tmp.write(pdf_bytes)
            tmp.close()
            pdf_attachment = tmp.name
        except Exception as pe:
            logger.warning(f"PDF-Anhang konnte nicht erstellt werden: {pe}")

        email_service = EmailService()
        email_service.send_email(
            to=angebot.kunde_email,
            subject=subject,
            body=f"Angebot {angebot.angebotsnummer} zur Freigabe: {approval_link}\n\nPDF herunterladen: {approval_link}/pdf",
            html_body=html_body,
            attachments=[pdf_attachment] if pdf_attachment else None
        )

        # Temp-Datei aufräumen
        if pdf_attachment:
            try:
                os.unlink(pdf_attachment)
            except Exception:
                pass

        logger.info(f"Freigabe-Email fuer {angebot.angebotsnummer} an {angebot.kunde_email} gesendet")
        return True
    except Exception as e:
        logger.error(f"Fehler beim E-Mail-Versand: {e}")
        return False


def _notify_team(angebot, action, customer_name, auftrag=None):
    """Benachrichtigt das Team ueber Kundenreaktion"""
    try:
        from src.services.email_service_new import EmailService
        from src.models.company_settings import CompanySettings

        company = CompanySettings.get_settings()
        notify_email = getattr(company, 'notification_email', None) or (company.email if company else None)
        if not notify_email:
            return

        if action == 'approved':
            subject = f"Angebot {angebot.angebotsnummer} FREIGEGEBEN von {customer_name}"
            if auftrag:
                subject += f" - Auftrag {auftrag.order_number} erstellt"
            body = f"Kunde {customer_name} hat das Angebot {angebot.angebotsnummer} freigegeben.\n\n"
            if auftrag:
                body += f"Auftrag {auftrag.order_number} wurde automatisch erstellt (inkl. Design-Freigabe).\n\n"
            else:
                body += "Das Angebot kann jetzt in einen Auftrag umgewandelt werden.\n\n"
            body += "Signiertes PDF im Anhang."
        else:
            subject = f"Angebot {angebot.angebotsnummer} - Aenderung gewuenscht"
            body = f"Kunde {customer_name} hat Aenderungen am Angebot {angebot.angebotsnummer} gewuenscht.\n\nKommentar: {angebot.approval_notes or '-'}"

        # Signiertes PDF anhängen wenn freigegeben
        pdf_attachment = None
        if action == 'approved' and angebot.approval_signature:
            try:
                import tempfile, os
                from src.controllers.angebote_controller import _build_angebot_pdf_bytes
                pdf_bytes = _build_angebot_pdf_bytes(angebot, include_signature=True)
                safe_nr = angebot.angebotsnummer.replace('/', '-').replace('\\', '-')
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf',
                                                  prefix=f'Angebot_{safe_nr}_unterzeichnet_')
                tmp.write(pdf_bytes)
                tmp.close()
                pdf_attachment = tmp.name
            except Exception as pe:
                logger.warning(f"Signiertes PDF fuer Team-Email konnte nicht erstellt werden: {pe}")

        email_service = EmailService()
        email_service.send_email(
            to=notify_email,
            subject=subject,
            body=body,
            attachments=[pdf_attachment] if pdf_attachment else None
        )

        if pdf_attachment:
            try:
                import os
                os.unlink(pdf_attachment)
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Team-Benachrichtigung fehlgeschlagen: {e}")
