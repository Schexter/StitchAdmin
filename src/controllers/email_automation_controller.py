# -*- coding: utf-8 -*-
"""
E-Mail Automation Controller
==============================
Verwaltung von Automation-Regeln und Einsicht in Logs.

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user

from src.models import db
from src.models.email_automation import EmailAutomationRule, EmailAutomationLog
from src.models.crm_contact import EmailTemplate

import logging
logger = logging.getLogger(__name__)

email_automation_bp = Blueprint('email_automation', __name__, url_prefix='/crm/automation')


@email_automation_bp.route('/')
@login_required
def index():
    """Uebersicht aller Automation-Regeln"""
    rules = EmailAutomationRule.query.order_by(EmailAutomationRule.trigger_event, EmailAutomationRule.name).all()

    # Letzte Logs
    recent_logs = EmailAutomationLog.query.order_by(
        EmailAutomationLog.sent_at.desc()
    ).limit(20).all()

    # Statistiken
    stats = {
        'active_rules': EmailAutomationRule.query.filter_by(is_enabled=True).count(),
        'total_sent': db.session.query(db.func.sum(EmailAutomationRule.send_count)).scalar() or 0,
        'recent_errors': EmailAutomationLog.query.filter_by(status='failed').limit(5).count(),
    }

    return render_template('email_automation/index.html',
                         rules=rules,
                         recent_logs=recent_logs,
                         stats=stats)


@email_automation_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_rule():
    """Neue Automation-Regel erstellen"""
    if request.method == 'POST':
        try:
            rule = EmailAutomationRule(
                name=request.form.get('name', '').strip(),
                description=request.form.get('description', '').strip() or None,
                trigger_event=request.form.get('trigger_event'),
                trigger_value=request.form.get('trigger_value'),
                is_enabled=request.form.get('is_enabled') == 'on',
                send_copy_to=request.form.get('send_copy_to', '').strip() or None,
                created_by=current_user.username,
            )

            template_id = request.form.get('template_id')
            if template_id:
                rule.template_id = int(template_id)

            db.session.add(rule)
            db.session.commit()

            flash(f'Regel "{rule.name}" erstellt.', 'success')
            return redirect(url_for('email_automation.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {e}', 'danger')

    templates = EmailTemplate.query.filter_by(is_active=True).order_by(EmailTemplate.name).all()

    return render_template('email_automation/form.html',
                         rule=None,
                         templates=templates,
                         trigger_events=EmailAutomationRule.TRIGGER_EVENTS,
                         trigger_values=EmailAutomationRule.TRIGGER_VALUES)


@email_automation_bp.route('/<int:rule_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_rule(rule_id):
    """Regel bearbeiten"""
    rule = EmailAutomationRule.query.get_or_404(rule_id)

    if request.method == 'POST':
        try:
            rule.name = request.form.get('name', '').strip()
            rule.description = request.form.get('description', '').strip() or None
            rule.trigger_event = request.form.get('trigger_event')
            rule.trigger_value = request.form.get('trigger_value')
            rule.is_enabled = request.form.get('is_enabled') == 'on'
            rule.send_copy_to = request.form.get('send_copy_to', '').strip() or None

            template_id = request.form.get('template_id')
            rule.template_id = int(template_id) if template_id else None

            db.session.commit()
            flash(f'Regel "{rule.name}" aktualisiert.', 'success')
            return redirect(url_for('email_automation.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {e}', 'danger')

    templates = EmailTemplate.query.filter_by(is_active=True).order_by(EmailTemplate.name).all()

    return render_template('email_automation/form.html',
                         rule=rule,
                         templates=templates,
                         trigger_events=EmailAutomationRule.TRIGGER_EVENTS,
                         trigger_values=EmailAutomationRule.TRIGGER_VALUES)


@email_automation_bp.route('/<int:rule_id>/toggle', methods=['POST'])
@login_required
def toggle_rule(rule_id):
    """Regel aktivieren/deaktivieren"""
    rule = EmailAutomationRule.query.get_or_404(rule_id)
    rule.is_enabled = not rule.is_enabled
    db.session.commit()
    status = 'aktiviert' if rule.is_enabled else 'deaktiviert'
    flash(f'Regel "{rule.name}" {status}.', 'success')
    return redirect(url_for('email_automation.index'))


@email_automation_bp.route('/<int:rule_id>/delete', methods=['POST'])
@login_required
def delete_rule(rule_id):
    """Regel loeschen"""
    rule = EmailAutomationRule.query.get_or_404(rule_id)
    name = rule.name
    try:
        db.session.delete(rule)
        db.session.commit()
        flash(f'Regel "{name}" geloescht.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {e}', 'danger')
    return redirect(url_for('email_automation.index'))


@email_automation_bp.route('/logs')
@login_required
def logs():
    """Automation-Logs anzeigen"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')

    query = EmailAutomationLog.query

    if status_filter:
        query = query.filter_by(status=status_filter)

    logs = query.order_by(EmailAutomationLog.sent_at.desc()).limit(100).all()

    return render_template('email_automation/logs.html',
                         logs=logs,
                         status_filter=status_filter)


@email_automation_bp.route('/api/trigger-values/<trigger_event>')
@login_required
def api_trigger_values(trigger_event):
    """API: Gibt verfuegbare Trigger-Werte fuer ein Event zurueck"""
    values = EmailAutomationRule.TRIGGER_VALUES.get(trigger_event, {})
    return jsonify(values)
