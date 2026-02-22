# -*- coding: utf-8 -*-
"""
Admin-Controller für Anfragen-Verwaltung
Liste, Detail, Status ändern, zuweisen, konvertieren

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from src.models.models import db, Order, User
from src.models.inquiry import Inquiry, INQUIRY_TYPE_LABELS
from src.services.inquiry_service import update_inquiry_status

inquiry_admin_bp = Blueprint('inquiry_admin', __name__, url_prefix='/admin/anfragen')


@inquiry_admin_bp.route('/')
@login_required
def list():
    """Alle Anfragen mit Filtern"""
    status_filter = request.args.get('status')
    type_filter = request.args.get('type')

    query = Inquiry.query

    if status_filter:
        query = query.filter_by(status=status_filter)
    if type_filter:
        query = query.filter_by(inquiry_type=type_filter)

    inquiries = query.order_by(Inquiry.created_at.desc()).all()

    # Statistiken
    stats = {
        'total': Inquiry.query.count(),
        'neu': Inquiry.query.filter_by(status='neu').count(),
        'in_bearbeitung': Inquiry.query.filter_by(status='in_bearbeitung').count(),
        'angebot_erstellt': Inquiry.query.filter_by(status='angebot_erstellt').count(),
    }

    return render_template('inquiry_admin/list.html',
                         inquiries=inquiries,
                         stats=stats,
                         inquiry_types=INQUIRY_TYPE_LABELS,
                         status_filter=status_filter,
                         type_filter=type_filter)


@inquiry_admin_bp.route('/<int:id>')
@login_required
def detail(id):
    """Anfrage-Detail"""
    inquiry = Inquiry.query.get_or_404(id)
    users = User.query.filter_by(is_active=True).all()

    return render_template('inquiry_admin/detail.html',
                         inquiry=inquiry,
                         users=users,
                         inquiry_types=INQUIRY_TYPE_LABELS)


@inquiry_admin_bp.route('/<int:id>/status', methods=['POST'])
@login_required
def change_status(id):
    """Status ändern"""
    new_status = request.form.get('status')
    if new_status:
        update_inquiry_status(id, new_status, updated_by=current_user.username)
        flash('Status aktualisiert.', 'success')
    return redirect(url_for('inquiry_admin.detail', id=id))


@inquiry_admin_bp.route('/<int:id>/assign', methods=['POST'])
@login_required
def assign(id):
    """Bearbeiter zuweisen"""
    inquiry = Inquiry.query.get_or_404(id)
    inquiry.assigned_to = request.form.get('assigned_to', '')
    if inquiry.status == 'neu':
        inquiry.status = 'in_bearbeitung'
    inquiry.updated_by = current_user.username
    db.session.commit()
    flash('Bearbeiter zugewiesen.', 'success')
    return redirect(url_for('inquiry_admin.detail', id=id))


@inquiry_admin_bp.route('/<int:id>/notes', methods=['POST'])
@login_required
def save_notes(id):
    """Interne Notizen speichern"""
    inquiry = Inquiry.query.get_or_404(id)
    inquiry.internal_notes = request.form.get('internal_notes', '')
    inquiry.updated_by = current_user.username
    db.session.commit()
    flash('Notizen gespeichert.', 'success')
    return redirect(url_for('inquiry_admin.detail', id=id))
