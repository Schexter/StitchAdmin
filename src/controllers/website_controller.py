# -*- coding: utf-8 -*-
"""
Oeffentliche Website - Startseite & Kontakt
Kein Login erforderlich.

Erstellt von: Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template

website_bp = Blueprint('website', __name__, url_prefix='/site')


@website_bp.route('/')
def home():
    """Oeffentliche Startseite"""
    from flask_login import current_user
    from flask import redirect, url_for, request

    # Eingeloggte User zum Dashboard - ausser bei Vorschau-Modus
    if current_user.is_authenticated and 'preview' not in request.args:
        return redirect(url_for('dashboard'))

    # Company-Daten laden
    company = None
    try:
        from src.models.company_settings import CompanySettings
        company = CompanySettings.get_settings()
    except Exception:
        pass

    # Statistiken fuer die Startseite
    stats = {'designs': 0, 'customers': 0, 'orders': 0}
    try:
        from src.models.models import Customer, Order
        stats['customers'] = Customer.query.count()
        stats['orders'] = Order.query.count()
    except Exception:
        pass
    try:
        from src.models.design import Design
        stats['designs'] = Design.query.count()
    except Exception:
        pass

    # Website-Inhalte aus CMS laden
    content = {}
    try:
        from src.models.website_content import WebsiteContent
        for section in ['hero', 'services', 'gallery', 'about', 'process', 'meta', 'footer']:
            content[section] = WebsiteContent.get_section(section)
    except Exception:
        pass

    return render_template('website/home.html',
                           company=company,
                           stats=stats,
                           content=content)


@website_bp.route('/impressum')
def impressum():
    """Impressum-Seite"""
    company = None
    try:
        from src.models.company_settings import CompanySettings
        company = CompanySettings.get_settings()
    except Exception:
        pass

    impressum_text = ''
    try:
        from src.models.website_content import WebsiteContent
        impressum_text = WebsiteContent.get('footer', 'impressum_link', '')
    except Exception:
        pass

    return render_template('website/impressum.html',
                           company=company, impressum_text=impressum_text)


@website_bp.route('/datenschutz')
def datenschutz():
    """Datenschutz-Seite"""
    company = None
    try:
        from src.models.company_settings import CompanySettings
        company = CompanySettings.get_settings()
    except Exception:
        pass

    datenschutz_text = ''
    try:
        from src.models.website_content import WebsiteContent
        datenschutz_text = WebsiteContent.get('footer', 'datenschutz_link', '')
    except Exception:
        pass

    return render_template('website/datenschutz.html',
                           company=company, datenschutz_text=datenschutz_text)


@website_bp.route('/agb')
def agb():
    """AGB-Seite"""
    company = _get_company()
    agb_text = ''
    try:
        from src.models.website_content import WebsiteContent
        agb_text = WebsiteContent.get('footer', 'agb_text', '')
    except Exception:
        pass
    return render_template('website/agb.html', company=company, page_text=agb_text)


@website_bp.route('/widerruf')
def widerruf():
    """Widerrufsbelehrung"""
    company = _get_company()
    widerruf_text = ''
    try:
        from src.models.website_content import WebsiteContent
        widerruf_text = WebsiteContent.get('footer', 'widerruf_text', '')
    except Exception:
        pass
    return render_template('website/widerruf.html', company=company, page_text=widerruf_text)


def _get_company():
    try:
        from src.models.company_settings import CompanySettings
        return CompanySettings.get_settings()
    except Exception:
        return None
