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


@landing_bp.route('/demo')
def demo_login():
    """Demo-Account: Readonly-Zugang zum Anschauen"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    # Demo-User finden oder erstellen
    demo_user = User.query.filter_by(username='demo').first()
    if not demo_user:
        demo_user = User(
            username='demo',
            email='demo@stitchadmin.de',
            first_name='Demo',
            last_name='Benutzer',
            is_active=True,
            is_admin=False,
            is_demo=True,
        )
        demo_user.set_password('demo-readonly-2026')
        db.session.add(demo_user)
        db.session.commit()
        logger.info("Demo-User erstellt")

    # Sicherstellen dass is_demo gesetzt ist
    if not demo_user.is_demo:
        demo_user.is_demo = True
        db.session.commit()

    login_user(demo_user, remember=False)
    demo_user.last_login = db.session.query(db.func.now()).scalar()
    db.session.commit()

    flash('Demo-Modus: Sie koennen sich umschauen, aber nichts aendern.', 'info')
    return redirect(url_for('dashboard'))


def _seed_demo_data():
    """Erstellt Fantasie-Demodaten wenn noch nicht vorhanden"""
    from src.models.models import Customer, Article, Order, OrderItem
    from src.models.inquiry import Inquiry
    import uuid

    # Nur seeden wenn keine Demo-Kunden existieren
    if Customer.query.filter(Customer.company_name.ilike('%Muster%Stickerei%')).first():
        return

    try:
        # Demo-Kunden
        kunden = [
            Customer(id=f'DEMO-K{i+1:03d}', first_name=fn, last_name=ln, company_name=cn,
                     email=em, phone=ph, city=ct, postal_code=plz, street=st)
            for i, (fn, ln, cn, em, ph, ct, plz, st) in enumerate([
                ('Stefan', 'Weber', 'Weber Sportswear GmbH', 'info@weber-sport.de', '0202-555100', 'Wuppertal', '42103', 'Hofkamp 12'),
                ('Maria', 'Schneider', 'FC Bergisch Lions e.V.', 'vorstand@bergisch-lions.de', '0202-555200', 'Solingen', '42651', 'Klingenstr. 8'),
                ('Thomas', 'Fischer', 'Fischer Workwear AG', 'tf@fischer-workwear.de', '0211-555300', 'Duesseldorf', '40213', 'Koenigsallee 55'),
                ('Anna', 'Mueller', 'Gasthaus Zur Linde', 'kontakt@gasthaus-linde.de', '0202-555400', 'Wuppertal', '42275', 'Berliner Str. 20'),
                ('Klaus', 'Berger', 'Berger Dachdecker OHG', 'buero@berger-dach.de', '0212-555500', 'Remscheid', '42853', 'Alleestr. 3'),
            ])
        ]
        for k in kunden:
            db.session.add(k)

        # Demo-Artikel
        artikel = [
            Article(id=f'DEMO-A{i+1:03d}', name=n, article_number=sku, category=cat)
            for i, (n, sku, cat) in enumerate([
                ('Polo-Shirt Premium Weiss', 'POLO-W-001', 'Textilien'),
                ('T-Shirt Baumwolle Schwarz', 'TS-BK-001', 'Textilien'),
                ('Softshell-Jacke Navy', 'SJ-NV-001', 'Textilien'),
                ('Arbeits-Latzhose Grau', 'ALH-GR-001', 'Textilien'),
                ('Cap mit Klettverschluss', 'CAP-001', 'Accessoires'),
            ])
        ]
        for a in artikel:
            db.session.add(a)

        db.session.flush()

        # Demo-Auftraege
        from datetime import date, timedelta
        today = date.today()

        auftraege = [
            ('DEMO-2026-001', 'DEMO-K001', 'in_progress', today - timedelta(days=5), '50x Polo bestickt Brust links'),
            ('DEMO-2026-002', 'DEMO-K002', 'pending', today - timedelta(days=2), '30x Trikot-Set Ruecken + Brust'),
            ('DEMO-2026-003', 'DEMO-K003', 'approved', today - timedelta(days=8), '100x Arbeits-Shirts mit Flex'),
            ('DEMO-2026-004', 'DEMO-K004', 'completed', today - timedelta(days=15), '20x Schuerzen Gasthaus Linde'),
            ('DEMO-2026-005', 'DEMO-K005', 'ready', today - timedelta(days=3), '15x Softshell bestickt'),
        ]
        for oid, kid, status, created, desc in auftraege:
            order = Order(
                id=oid, order_number=oid, customer_id=kid,
                status=status, description=desc,
                created_at=datetime.combine(created, datetime.min.time()),
            )
            db.session.add(order)

        # Demo-Anfragen
        for i, (fn, ln, em, desc, st) in enumerate([
            ('Laura', 'Klein', 'laura@example.de', '80 Vereins-Shirts mit Logo vorne + Ruecken', 'neu'),
            ('Markus', 'Braun', 'mb@example.de', 'Angebot fuer 200 Poloshirts bestickt', 'in_bearbeitung'),
            ('Petra', 'Hoffmann', 'ph@example.de', 'Muster fuer Workwear mit DTF-Transfer', 'angebot_erstellt'),
        ]):
            inq = Inquiry(
                inquiry_number=f'DEMO-ANF-{i+1:03d}',
                tracking_token=uuid.uuid4().hex,
                first_name=fn, last_name=ln, email=em,
                description=desc, status=st,
                inquiry_type='stickerei' if i < 2 else 'druck',
                source='manual',
                dsgvo_consent=True,
                dsgvo_consent_at=datetime.utcnow(),
            )
            db.session.add(inq)

        db.session.commit()
        logger.info("Demo-Daten erfolgreich erstellt")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Demo-Daten konnten nicht erstellt werden: {e}")


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


@landing_bp.route('/impressum')
def impressum():
    """Impressum"""
    return render_template('landing/impressum.html')


@landing_bp.route('/datenschutz')
def datenschutz():
    """Datenschutzerklaerung"""
    return render_template('landing/datenschutz.html')


@landing_bp.route('/agb')
def agb():
    """Allgemeine Geschaeftsbedingungen"""
    return render_template('landing/agb.html')
