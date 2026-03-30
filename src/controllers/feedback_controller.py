# -*- coding: utf-8 -*-
"""
Feedback / Bug-Report Controller
=================================
Widget-basierter Bug-Melder (unten rechts in der App).

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from src.models import db
from src.models.feedback import FeedbackReport
import logging

logger = logging.getLogger(__name__)

feedback_bp = Blueprint('feedback', __name__, url_prefix='/feedback')


@feedback_bp.route('/submit', methods=['POST'])
@login_required
def submit():
    """Bug-Report oder Feedback einreichen (AJAX)"""
    try:
        data = request.json or {}
        titel = data.get('titel', '').strip()
        if not titel:
            return jsonify({'success': False, 'error': 'Titel ist erforderlich'}), 400

        report = FeedbackReport(
            typ=data.get('typ', 'bug'),
            titel=titel,
            beschreibung=data.get('beschreibung', ''),
            seite_url=data.get('seite_url', ''),
            browser_info=data.get('browser_info', ''),
            prioritaet=data.get('prioritaet', 'normal'),
            erstellt_von=current_user.username,
        )
        db.session.add(report)
        db.session.flush()

        # Screenshot speichern (Base64 -> Datei)
        screenshot = data.get('screenshot', '')
        if screenshot and screenshot.startswith('data:image/'):
            try:
                import base64, os
                header, b64data = screenshot.split(',', 1)
                img_bytes = base64.b64decode(b64data)
                upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'instance', 'feedback')
                os.makedirs(upload_dir, exist_ok=True)
                filename = f"feedback_{report.id}.jpg"
                filepath = os.path.join(upload_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(img_bytes)
                report.screenshot_path = f"feedback/{filename}"
            except Exception as e:
                logger.warning(f"Screenshot speichern fehlgeschlagen: {e}")

        db.session.commit()

        logger.info(f"Feedback #{report.id} von {current_user.username}: {titel}")

        return jsonify({
            'success': True,
            'message': 'Feedback gesendet!',
            'id': report.id
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Feedback-Fehler: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@feedback_bp.route('/liste')
@login_required
def liste():
    """Alle Feedback-Reports (nur fuer Admins)"""
    if not current_user.is_admin:
        flash('Nur Admins koennen Feedback verwalten.', 'danger')
        return redirect(url_for('dashboard'))

    reports = FeedbackReport.query.order_by(FeedbackReport.created_at.desc()).all()

    stats = {
        'neu': FeedbackReport.query.filter_by(status='neu').count(),
        'in_arbeit': FeedbackReport.query.filter_by(status='in_arbeit').count(),
        'erledigt': FeedbackReport.query.filter_by(status='erledigt').count(),
        'gesamt': FeedbackReport.query.count(),
    }

    return render_template('feedback/liste.html', reports=reports, stats=stats)


@feedback_bp.route('/<int:report_id>/status', methods=['POST'])
@login_required
def update_status(report_id):
    """Status aendern + Antwort"""
    if not current_user.is_admin:
        return jsonify({'success': False}), 403

    report = FeedbackReport.query.get_or_404(report_id)
    data = request.json or request.form

    if data.get('status'):
        report.status = data['status']
    if data.get('antwort'):
        report.antwort = data['antwort']
    report.bearbeitet_von = current_user.username
    report.bearbeitet_am = datetime.utcnow()
    db.session.commit()

    if request.is_json:
        return jsonify({'success': True})
    flash('Status aktualisiert.', 'success')
    return redirect(url_for('feedback.liste'))
