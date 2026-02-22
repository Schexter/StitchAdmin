# -*- coding: utf-8 -*-
"""
Landing Page & Registrierung Controller
Oeffentliche Seiten fuer SaaS-Landing, Registrierung neuer Tenants
Erstellt von: Hans Hahn - Alle Rechte vorbehalten
"""

import re
import secrets
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_user
from src.models.models import db, User
from src.models.tenant import Tenant, UserTenant
import logging

logger = logging.getLogger(__name__)

landing_bp = Blueprint('landing', __name__)

# Reservierte Subdomains die nicht vergeben werden duerfen
RESERVED_SUBDOMAINS = {
    'app', 'api', 'www', 'mail', 'ftp', 'admin', 'root', 'system',
    'default', 'test', 'demo', 'staging', 'dev', 'localhost',
    'support', 'help', 'docs', 'status', 'blog', 'shop',
}


@landing_bp.route('/')
def index():
    """Landing Page - Startseite fuer nicht angemeldete Benutzer"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing/index.html')


@landing_bp.route('/register', methods=['POST'])
def register():
    """Neuen Tenant + Admin-User registrieren"""
    company_name = request.form.get('company_name', '').strip()
    subdomain = request.form.get('subdomain', '').strip().lower()
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    password_confirm = request.form.get('password_confirm', '')
    phone = request.form.get('phone', '').strip()
    plan = request.form.get('plan', 'starter')

    # Validierung
    errors = []

    if not company_name:
        errors.append('Firmenname ist erforderlich.')
    if not subdomain:
        errors.append('Subdomain ist erforderlich.')
    elif not re.match(r'^[a-z0-9][a-z0-9\-]{1,30}[a-z0-9]$', subdomain):
        errors.append('Subdomain: Nur Kleinbuchstaben, Zahlen und Bindestriche (3-32 Zeichen).')
    elif subdomain in RESERVED_SUBDOMAINS:
        errors.append('Diese Subdomain ist reserviert. Bitte waehlen Sie eine andere.')
    elif Tenant.query.filter_by(subdomain=subdomain).first():
        errors.append('Diese Subdomain ist bereits vergeben.')

    if not full_name:
        errors.append('Ihr Name ist erforderlich.')
    if not email:
        errors.append('E-Mail ist erforderlich.')
    elif User.query.filter_by(email=email).first():
        errors.append('Diese E-Mail-Adresse wird bereits verwendet.')

    if not password or len(password) < 8:
        errors.append('Passwort muss mindestens 8 Zeichen lang sein.')
    elif password != password_confirm:
        errors.append('Passwoerter stimmen nicht ueberein.')

    if plan not in ('starter', 'professional', 'enterprise'):
        plan = 'starter'

    if errors:
        for err in errors:
            flash(err, 'danger')
        return redirect(url_for('landing.index') + '#registrierung')

    try:
        # Slug aus Subdomain generieren
        slug = subdomain

        # Username aus E-Mail generieren
        username = email.split('@')[0]
        # Sicherstellen dass Username einzigartig ist
        base_username = username
        counter = 1
        while User.query.filter_by(username=username).first():
            username = f"{base_username}{counter}"
            counter += 1

        # Vornamen und Nachnamen aus full_name extrahieren
        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        # Tenant erstellen
        tenant = Tenant(
            slug=slug,
            name=company_name,
            subdomain=subdomain,
            contact_email=email,
            contact_phone=phone,
            is_active=True,
            plan_tier='trial',
            trial_ends_at=datetime.utcnow() + timedelta(days=14),
        )
        db.session.add(tenant)
        db.session.flush()  # ID generieren

        # Admin-User erstellen
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_admin=True,
            is_active=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        # User dem Tenant zuweisen
        user_tenant = UserTenant(
            user_id=user.id,
            tenant_id=tenant.id,
            role='tenant_admin',
            is_active=True,
            is_primary=True,
        )
        db.session.add(user_tenant)

        db.session.commit()

        logger.info(f"Neuer Tenant registriert: {company_name} ({subdomain}), User: {username}")

        # Direkt einloggen
        login_user(user)

        flash(f'Willkommen bei StitchAdmin, {first_name}! Ihr Account wurde erfolgreich erstellt. '
              f'Ihre Testphase laeuft bis zum {tenant.trial_ends_at.strftime("%d.%m.%Y")}.', 'success')
        return redirect(url_for('dashboard'))

    except Exception as e:
        db.session.rollback()
        logger.error(f"Registrierung fehlgeschlagen: {e}")
        flash('Bei der Registrierung ist ein Fehler aufgetreten. Bitte versuchen Sie es erneut.', 'danger')
        return redirect(url_for('landing.index') + '#registrierung')


@landing_bp.route('/check-subdomain')
def check_subdomain():
    """API: Pruefen ob Subdomain verfuegbar ist"""
    from flask import jsonify
    subdomain = request.args.get('subdomain', '').strip().lower()

    if not subdomain or len(subdomain) < 3:
        return jsonify({'available': False, 'message': 'Mindestens 3 Zeichen'})

    if not re.match(r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$', subdomain):
        return jsonify({'available': False, 'message': 'Nur Kleinbuchstaben, Zahlen, Bindestriche'})

    if subdomain in RESERVED_SUBDOMAINS:
        return jsonify({'available': False, 'message': 'Reserviert'})

    if Tenant.query.filter_by(subdomain=subdomain).first():
        return jsonify({'available': False, 'message': 'Bereits vergeben'})

    return jsonify({'available': True, 'message': 'Verfuegbar'})
