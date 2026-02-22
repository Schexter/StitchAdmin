# -*- coding: utf-8 -*-
"""
Öffentlicher Anfrage-Controller
Anfrage-Formular, Danke-Seite, Status-Tracking (kein Login nötig)

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from src.services.inquiry_service import (
    create_inquiry, get_inquiry_by_token, get_inquiry_by_number,
    find_inquiries_by_email, DSGVO_CONSENT_TEXT
)
from src.models.inquiry import INQUIRY_TYPE_LABELS

inquiry_bp = Blueprint('inquiry', __name__, url_prefix='/anfrage')


@inquiry_bp.route('/', methods=['GET', 'POST'], strict_slashes=False)
def form():
    """Anfrage-Formular anzeigen und verarbeiten"""
    company = _get_company()

    if request.method == 'POST':
        # Validierung
        errors = []
        if not request.form.get('first_name'):
            errors.append('Bitte geben Sie Ihren Vornamen an.')
        if not request.form.get('last_name'):
            errors.append('Bitte geben Sie Ihren Nachnamen an.')
        if not request.form.get('email'):
            errors.append('Bitte geben Sie Ihre E-Mail-Adresse an.')
        if not request.form.get('inquiry_type'):
            errors.append('Bitte wählen Sie eine Anfrageart.')
        if not request.form.get('description'):
            errors.append('Bitte beschreiben Sie Ihre Anfrage.')
        if not request.form.get('dsgvo_consent'):
            errors.append('Bitte stimmen Sie der Datenverarbeitung zu.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('inquiry/form.html',
                                 form_data=request.form,
                                 inquiry_types=INQUIRY_TYPE_LABELS,
                                 dsgvo_text=DSGVO_CONSENT_TEXT,
                                 company=company,
                                 cart_count=0)

        try:
            inquiry = create_inquiry(
                form_data=request.form,
                files=request.files,
                remote_ip=request.remote_addr
            )
            return redirect(url_for('inquiry.danke', token=inquiry.tracking_token))
        except Exception as e:
            flash(f'Fehler beim Absenden: {str(e)}', 'danger')

    return render_template('inquiry/form.html',
                         form_data={},
                         inquiry_types=INQUIRY_TYPE_LABELS,
                         dsgvo_text=DSGVO_CONSENT_TEXT,
                         company=company,
                         cart_count=0)


@inquiry_bp.route('/danke/<token>')
def danke(token):
    """Danke-Seite nach Absenden"""
    inquiry = get_inquiry_by_token(token)
    if not inquiry:
        flash('Anfrage nicht gefunden.', 'danger')
        return redirect(url_for('inquiry.form'))

    return render_template('inquiry/danke.html',
                         inquiry=inquiry,
                         company=_get_company(),
                         cart_count=0)


@inquiry_bp.route('/status/<token>')
def status(token):
    """Status-Seite für eine Anfrage"""
    inquiry = get_inquiry_by_token(token)
    if not inquiry:
        flash('Anfrage nicht gefunden.', 'danger')
        return redirect(url_for('inquiry.status_lookup'))

    return render_template('inquiry/status.html',
                         inquiry=inquiry,
                         company=_get_company(),
                         cart_count=0)


@inquiry_bp.route('/status', methods=['GET', 'POST'])
def status_lookup():
    """Status-Lookup per Anfragen-Nummer oder E-Mail"""
    inquiries = None

    if request.method == 'POST':
        search = request.form.get('search', '').strip()
        if not search:
            flash('Bitte geben Sie Ihre Anfragen-Nummer oder E-Mail ein.', 'warning')
        elif '@' in search:
            inquiries = find_inquiries_by_email(search)
            if not inquiries:
                flash('Keine Anfragen zu dieser E-Mail gefunden.', 'info')
        else:
            inquiry = get_inquiry_by_number(search.upper())
            if inquiry:
                return redirect(url_for('inquiry.status', token=inquiry.tracking_token))
            flash('Keine Anfrage mit dieser Nummer gefunden.', 'info')

    return render_template('inquiry/status_lookup.html',
                         inquiries=inquiries,
                         company=_get_company(),
                         cart_count=0)


def _get_company():
    """CompanySettings laden"""
    try:
        from src.models.company_settings import CompanySettings
        return CompanySettings.get_settings()
    except Exception:
        return None
