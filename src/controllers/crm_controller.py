# -*- coding: utf-8 -*-
"""
CRM Controller - Kundenkontakt-Management
StitchAdmin 2.0
Erstellt von Hans Hahn - Alle Rechte vorbehalten

Funktionen:
- Kontakthistorie (E-Mails, Telefonate, Notizen)
- E-Mail senden an Kunden
- Telefon-Notizen erfassen
- E-Mail-Vorlagen verwalten
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, date
import logging

from src.models import db
from src.models.models import Customer, Order
from src.models.crm_contact import (
    CustomerContact, ContactType, ContactStatus,
    EmailTemplate, EmailTemplateCategory
)

logger = logging.getLogger(__name__)

crm_bp = Blueprint('crm', __name__, url_prefix='/crm')


# ==========================================
# CRM DASHBOARD - Kunden-Rankings
# ==========================================

@crm_bp.route('/dashboard')
@login_required
def dashboard():
    """
    CRM Dashboard mit Kunden-Rankings
    
    Zeigt:
    - VIP-Kunden (gewichteter Score)
    - Top-Umsatz (gesamt & Jahr)
    - Zahlungsmoral (beste & schlechteste)
    - Kontakt-Alerts (kein Kontakt, fällige Wiedervorlagen)
    - Neue Kunden
    """
    from src.utils.customer_analytics import CustomerAnalytics
    
    # Summary für Header-Karten
    summary = CustomerAnalytics.get_dashboard_summary()
    
    # Alle Rankings laden
    rankings = CustomerAnalytics.get_all_rankings(limit=20)
    
    return render_template('crm/dashboard.html',
                         summary=summary,
                         rankings=rankings)


@crm_bp.route('/api/customer/<customer_id>/stats')
@login_required
def api_customer_stats(customer_id):
    """
    API: Detaillierte Statistiken für einen Kunden
    
    Liefert Scores, Umsatz, Zahlungsmoral, Engagement
    """
    from src.utils.customer_analytics import CustomerAnalytics
    
    stats = CustomerAnalytics.get_customer_detail_stats(customer_id)
    
    if not stats:
        return jsonify({'error': 'Kunde nicht gefunden'}), 404
    
    # Datumswerte in Strings umwandeln
    if stats.get('customer_since'):
        stats['customer_since'] = stats['customer_since'].strftime('%d.%m.%Y')
    if stats['engagement'].get('last_contact'):
        stats['engagement']['last_contact'] = stats['engagement']['last_contact'].strftime('%d.%m.%Y')
    
    return jsonify(stats)


# ==========================================
# KONTAKTHISTORIE
# ==========================================

@crm_bp.route('/kunde/<customer_id>/kontakte')
@login_required
def customer_contacts(customer_id):
    """Zeigt Kontakthistorie eines Kunden"""
    customer = Customer.query.get_or_404(customer_id)

    # Filter
    contact_type = request.args.get('type', '')
    date_from = request.args.get('from', '')
    date_to = request.args.get('to', '')

    query = CustomerContact.query.filter_by(customer_id=customer_id)

    if contact_type:
        query = query.filter_by(contact_type=ContactType(contact_type))

    if date_from:
        query = query.filter(CustomerContact.contact_date >= datetime.strptime(date_from, '%Y-%m-%d'))

    if date_to:
        query = query.filter(CustomerContact.contact_date <= datetime.strptime(date_to, '%Y-%m-%d'))

    contacts = query.order_by(CustomerContact.contact_date.desc()).all()

    return render_template('crm/customer_contacts.html',
        customer=customer,
        contacts=contacts,
        contact_types=ContactType
    )


@crm_bp.route('/kunde/<customer_id>/kontakt/neu', methods=['GET', 'POST'])
@login_required
def new_contact(customer_id):
    """Neuen Kontakt erstellen (E-Mail, Telefonat, Notiz)"""
    customer = Customer.query.get_or_404(customer_id)
    contact_type = request.args.get('type', 'notiz')

    if request.method == 'POST':
        try:
            contact = CustomerContact(
                customer_id=customer_id,
                contact_type=ContactType(request.form.get('contact_type', 'notiz')),
                subject=request.form.get('subject', ''),
                body_text=request.form.get('body_text', ''),
                contact_date=datetime.strptime(request.form.get('contact_date'), '%Y-%m-%dT%H:%M') if request.form.get('contact_date') else datetime.now(),
                created_by=current_user.username,
                status=ContactStatus(request.form.get('status', 'erledigt'))
            )

            # Telefon-spezifisch
            if contact.contact_type in [ContactType.TELEFON_EINGANG, ContactType.TELEFON_AUSGANG]:
                contact.phone_number = request.form.get('phone_number', '')
                contact.callback_required = request.form.get('callback_required') == 'on'
                if contact.callback_required and request.form.get('callback_date'):
                    contact.callback_date = datetime.strptime(request.form.get('callback_date'), '%Y-%m-%dT%H:%M')

            # Auftragsbezug
            order_id = request.form.get('order_id')
            if order_id:
                contact.order_id = int(order_id)

            # Wiedervorlage
            if request.form.get('follow_up_date'):
                contact.follow_up_date = datetime.strptime(request.form.get('follow_up_date'), '%Y-%m-%dT%H:%M')
                contact.follow_up_note = request.form.get('follow_up_note', '')

            db.session.add(contact)
            db.session.commit()

            flash('Kontakt erfolgreich gespeichert!', 'success')
            return redirect(url_for('crm.customer_contacts', customer_id=customer_id))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler beim Erstellen des Kontakts: {e}")
            flash(f'Fehler: {str(e)}', 'error')

    # Auftraege des Kunden laden
    orders = Order.query.filter_by(customer_id=customer_id).order_by(Order.created_at.desc()).limit(20).all()

    return render_template('crm/new_contact.html',
        customer=customer,
        contact_type=contact_type,
        contact_types=ContactType,
        orders=orders,
        now=datetime.now()
    )


# ==========================================
# E-MAIL SENDEN
# ==========================================

@crm_bp.route('/kunde/<customer_id>/email', methods=['GET', 'POST'])
@login_required
def send_email(customer_id):
    """E-Mail an Kunden senden"""
    customer = Customer.query.get_or_404(customer_id)

    if request.method == 'POST':
        try:
            from src.models.company_settings import CompanySettings
            from src.services.outlook_service import OutlookService

            settings = CompanySettings.get_settings()

            to_email = request.form.get('to_email', customer.email)
            subject = request.form.get('subject', '')
            body = request.form.get('body', '')
            save_contact = request.form.get('save_contact') == 'on'

            if not to_email:
                flash('Keine E-Mail-Adresse angegeben!', 'error')
                return redirect(url_for('crm.send_email', customer_id=customer_id))

            email_method = settings.email_method or 'outlook'
            success = False

            if email_method == 'outlook':
                service = OutlookService()
                if service.is_available():
                    success = service.create_email(
                        to=to_email,
                        subject=subject,
                        body=body,
                        html_body=True,
                        display_first=True  # Erst anzeigen
                    )
            elif email_method == 'mailto':
                import urllib.parse
                mailto_url = f"mailto:{to_email}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
                return redirect(mailto_url)

            # Kontakt speichern
            if save_contact:
                contact = CustomerContact(
                    customer_id=customer_id,
                    contact_type=ContactType.EMAIL_AUSGANG,
                    subject=subject,
                    body_html=body,
                    email_to=to_email,
                    contact_date=datetime.now(),
                    created_by=current_user.username,
                    status=ContactStatus.GESENDET if success else ContactStatus.ENTWURF
                )
                db.session.add(contact)
                db.session.commit()

            if success:
                flash('E-Mail wurde in Outlook geoeffnet!', 'success')
            else:
                flash('E-Mail konnte nicht geoeffnet werden.', 'warning')

            return redirect(url_for('crm.customer_contacts', customer_id=customer_id))

        except Exception as e:
            logger.error(f"Fehler beim E-Mail-Versand: {e}")
            flash(f'Fehler: {str(e)}', 'error')

    # E-Mail-Vorlagen laden
    templates = EmailTemplate.query.filter_by(is_active=True).order_by(EmailTemplate.category, EmailTemplate.name).all()

    # Vorlage aus URL?
    template_id = request.args.get('template')
    selected_template = None
    if template_id:
        selected_template = EmailTemplate.query.get(template_id)

    # Auftraege des Kunden
    orders = Order.query.filter_by(customer_id=customer_id).order_by(Order.created_at.desc()).limit(10).all()

    return render_template('crm/send_email.html',
        customer=customer,
        templates=templates,
        selected_template=selected_template,
        orders=orders
    )


@crm_bp.route('/api/template/<int:template_id>/render', methods=['POST'])
@login_required
def render_template_api(template_id):
    """Rendert eine E-Mail-Vorlage mit Kontext"""
    try:
        template = EmailTemplate.query.get_or_404(template_id)
        context = request.json or {}

        subject, body_text, body_html = template.render(context)

        return jsonify({
            'success': True,
            'subject': subject,
            'body_text': body_text,
            'body_html': body_html
        })

    except Exception as e:
        logger.error(f"Fehler beim Rendern der Vorlage: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==========================================
# TELEFON-NOTIZEN
# ==========================================

@crm_bp.route('/kunde/<customer_id>/telefonat', methods=['GET', 'POST'])
@login_required
def phone_note(customer_id):
    """Telefon-Notiz erfassen"""
    customer = Customer.query.get_or_404(customer_id)

    if request.method == 'POST':
        try:
            direction = request.form.get('direction', 'ausgang')
            contact_type = ContactType.TELEFON_AUSGANG if direction == 'ausgang' else ContactType.TELEFON_EINGANG

            contact = CustomerContact(
                customer_id=customer_id,
                contact_type=contact_type,
                subject=request.form.get('subject', 'Telefonat'),
                body_text=request.form.get('notes', ''),
                phone_number=request.form.get('phone_number', customer.phone),
                contact_date=datetime.now(),
                created_by=current_user.username,
                status=ContactStatus.ERLEDIGT,
                callback_required=request.form.get('callback_required') == 'on'
            )

            if contact.callback_required and request.form.get('callback_date'):
                contact.callback_date = datetime.strptime(request.form.get('callback_date'), '%Y-%m-%dT%H:%M')

            # Auftragsbezug
            order_id = request.form.get('order_id')
            if order_id:
                contact.order_id = int(order_id)

            db.session.add(contact)
            db.session.commit()

            flash('Telefon-Notiz gespeichert!', 'success')
            return redirect(url_for('crm.customer_contacts', customer_id=customer_id))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler beim Speichern der Telefon-Notiz: {e}")
            flash(f'Fehler: {str(e)}', 'error')

    # Auftraege des Kunden
    orders = Order.query.filter_by(customer_id=customer_id).order_by(Order.created_at.desc()).limit(10).all()

    return render_template('crm/phone_note.html',
        customer=customer,
        orders=orders,
        now=datetime.now()
    )


# ==========================================
# AUFTRAGS-E-MAILS
# ==========================================

@crm_bp.route('/auftrag/<int:order_id>/email/<category>')
@login_required
def order_email(order_id, category):
    """E-Mail zu einem Auftrag senden (Bestaetigung, Freigabe, Versand, etc.)"""
    order = Order.query.get_or_404(order_id)
    customer = order.customer

    if not customer or not customer.email:
        flash('Kunde hat keine E-Mail-Adresse!', 'error')
        return redirect(url_for('orders.show', order_id=order_id))

    try:
        cat = EmailTemplateCategory(category)
    except ValueError:
        flash('Unbekannte E-Mail-Kategorie!', 'error')
        return redirect(url_for('orders.show', order_id=order_id))

    # Standard-Vorlage fuer diese Kategorie
    template = EmailTemplate.get_default_for_category(cat)
    if not template:
        flash(f'Keine Vorlage fuer Kategorie "{category}" gefunden!', 'warning')
        return redirect(url_for('crm.send_email', customer_id=customer.id))

    # Kontext aufbauen
    context = {
        'anrede': 'Frau' if customer.gender == 'female' else 'Herr' if customer.gender == 'male' else '',
        'kunde_name': customer.display_name,
        'firma': customer.company_name or '',
        'auftragsnummer': order.order_number,
        'auftragsdatum': order.created_at.strftime('%d.%m.%Y') if order.created_at else '',
        'gesamtbetrag': f'{order.total_price:.2f} EUR' if order.total_price else '',
    }

    # Zusaetzliche Kontext-Variablen je nach Kategorie
    if cat == EmailTemplateCategory.VERSAND_INFO:
        context['versanddienstleister'] = order.shipping_carrier or 'DHL'
        context['sendungsnummer'] = order.tracking_number or ''
        context['tracking_link'] = order.tracking_url or ''
        context['lieferzeit'] = '1-3 Werktage'

    if cat == EmailTemplateCategory.GRAFIK_FREIGABE:
        # Freigabe-Link generieren (falls Design-Approval-System vorhanden)
        context['freigabe_link'] = url_for('design_approval.approval_page',
                                          order_id=order.id, _external=True) if order.approval_token else '#'

    # Vorlage rendern
    subject, body_text, body_html = template.render(context)

    return render_template('crm/send_email.html',
        customer=customer,
        order=order,
        templates=EmailTemplate.query.filter_by(is_active=True).all(),
        selected_template=template,
        prefilled_subject=subject,
        prefilled_body=body_html or body_text
    )


# ==========================================
# E-MAIL-VORLAGEN VERWALTUNG
# ==========================================

@crm_bp.route('/vorlagen')
@login_required
def email_templates():
    """E-Mail-Vorlagen verwalten"""
    templates = EmailTemplate.query.order_by(EmailTemplate.category, EmailTemplate.sort_order, EmailTemplate.name).all()

    # Nach Kategorie gruppieren
    templates_by_category = {}
    for template in templates:
        cat = template.category
        if cat not in templates_by_category:
            templates_by_category[cat] = []
        templates_by_category[cat].append(template)

    return render_template('crm/email_templates.html',
        templates_by_category=templates_by_category,
        categories=EmailTemplateCategory
    )


@crm_bp.route('/vorlagen/neu', methods=['GET', 'POST'])
@login_required
def new_email_template():
    """Neue E-Mail-Vorlage erstellen"""
    if request.method == 'POST':
        try:
            template = EmailTemplate(
                name=request.form.get('name'),
                description=request.form.get('description', ''),
                category=EmailTemplateCategory(request.form.get('category')),
                subject=request.form.get('subject'),
                body_text=request.form.get('body_text', ''),
                body_html=request.form.get('body_html', ''),
                is_active=request.form.get('is_active') == 'on',
                is_default=request.form.get('is_default') == 'on',
                created_by=current_user.username
            )

            # Platzhalter
            placeholders = request.form.get('placeholders', '').split(',')
            placeholders = [p.strip() for p in placeholders if p.strip()]
            template.set_placeholders(placeholders)

            db.session.add(template)
            db.session.commit()

            flash('Vorlage erfolgreich erstellt!', 'success')
            return redirect(url_for('crm.email_templates'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler beim Erstellen der Vorlage: {e}")
            flash(f'Fehler: {str(e)}', 'error')

    return render_template('crm/edit_template.html',
        template=None,
        categories=EmailTemplateCategory,
        is_new=True
    )


@crm_bp.route('/vorlagen/<int:template_id>/bearbeiten', methods=['GET', 'POST'])
@login_required
def edit_email_template(template_id):
    """E-Mail-Vorlage bearbeiten"""
    template = EmailTemplate.query.get_or_404(template_id)

    if request.method == 'POST':
        try:
            template.name = request.form.get('name')
            template.description = request.form.get('description', '')
            template.category = EmailTemplateCategory(request.form.get('category'))
            template.subject = request.form.get('subject')
            template.body_text = request.form.get('body_text', '')
            template.body_html = request.form.get('body_html', '')
            template.is_active = request.form.get('is_active') == 'on'
            template.is_default = request.form.get('is_default') == 'on'
            template.updated_by = current_user.username

            # Platzhalter
            placeholders = request.form.get('placeholders', '').split(',')
            placeholders = [p.strip() for p in placeholders if p.strip()]
            template.set_placeholders(placeholders)

            db.session.commit()

            flash('Vorlage erfolgreich aktualisiert!', 'success')
            return redirect(url_for('crm.email_templates'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler beim Bearbeiten der Vorlage: {e}")
            flash(f'Fehler: {str(e)}', 'error')

    return render_template('crm/edit_template.html',
        template=template,
        categories=EmailTemplateCategory,
        is_new=False
    )


@crm_bp.route('/vorlagen/<int:template_id>/loeschen', methods=['POST'])
@login_required
def delete_email_template(template_id):
    """E-Mail-Vorlage loeschen"""
    try:
        template = EmailTemplate.query.get_or_404(template_id)
        db.session.delete(template)
        db.session.commit()
        flash('Vorlage geloescht!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Fehler beim Loeschen der Vorlage: {e}")
        flash(f'Fehler: {str(e)}', 'error')

    return redirect(url_for('crm.email_templates'))


@crm_bp.route('/vorlagen/init')
@login_required
def init_default_templates():
    """Initialisiert Standard-Vorlagen"""
    try:
        EmailTemplate.create_default_templates()
        flash('Standard-Vorlagen wurden erstellt!', 'success')
    except Exception as e:
        logger.error(f"Fehler beim Erstellen der Standard-Vorlagen: {e}")
        flash(f'Fehler: {str(e)}', 'error')

    return redirect(url_for('crm.email_templates'))


# ==========================================
# WIEDERVORLAGEN / FOLLOW-UPS
# ==========================================

@crm_bp.route('/wiedervorlagen')
@login_required
def follow_ups():
    """Zeigt alle faelligen Wiedervorlagen"""
    today = datetime.now()

    follow_ups = CustomerContact.query.filter(
        CustomerContact.follow_up_date <= today,
        CustomerContact.status != ContactStatus.ERLEDIGT
    ).order_by(CustomerContact.follow_up_date).all()

    callbacks = CustomerContact.query.filter(
        CustomerContact.callback_required == True,
        CustomerContact.callback_date <= today,
        CustomerContact.status != ContactStatus.ERLEDIGT
    ).order_by(CustomerContact.callback_date).all()

    return render_template('crm/follow_ups.html',
        follow_ups=follow_ups,
        callbacks=callbacks
    )


# ==========================================
# API ENDPOINTS
# ==========================================

@crm_bp.route('/api/kunde/<customer_id>/kontakte')
@login_required
def api_customer_contacts(customer_id):
    """API: Kontakte eines Kunden als JSON"""
    contacts = CustomerContact.query.filter_by(customer_id=customer_id)\
        .order_by(CustomerContact.contact_date.desc())\
        .limit(50).all()

    return jsonify({
        'success': True,
        'contacts': [{
            'id': c.id,
            'type': c.contact_type.value,
            'type_label': c.type_label,
            'type_icon': c.type_icon,
            'type_color': c.type_color,
            'subject': c.subject,
            'body_text': c.body_text[:200] + '...' if c.body_text and len(c.body_text) > 200 else c.body_text,
            'contact_date': c.contact_date.isoformat() if c.contact_date else None,
            'created_by': c.created_by
        } for c in contacts]
    })


@crm_bp.route('/api/kontakt/<int:contact_id>')
@login_required
def api_contact_detail(contact_id):
    """API: Einzelner Kontakt als JSON"""
    contact = CustomerContact.query.get_or_404(contact_id)

    return jsonify({
        'success': True,
        'contact': {
            'id': contact.id,
            'type': contact.contact_type.value,
            'type_label': contact.type_label,
            'subject': contact.subject,
            'body_text': contact.body_text,
            'body_html': contact.body_html,
            'email_to': contact.email_to,
            'phone_number': contact.phone_number,
            'contact_date': contact.contact_date.isoformat() if contact.contact_date else None,
            'created_by': contact.created_by,
            'attachments': contact.get_attachments()
        }
    })


# ==========================================
# CRM AKTIVITÄTEN (aus Produktionskalender)
# Integration mit ProductionBlock für Telefonate, Besuche, etc.
# ==========================================

@crm_bp.route('/activities')
@login_required
def activities_search():
    """
    Zentrale CRM-Aktivitäten Suche
    
    Durchsucht alle Kalender-Aktivitäten (Telefonate, Besuche, E-Mails...)
    Verknüpft mit Kunden und Aufträgen für schnelles Finden
    """
    from datetime import timedelta
    from sqlalchemy import or_
    
    # Versuche ProductionBlock zu laden
    try:
        from src.models import ProductionBlock
    except ImportError:
        flash('Aktivitäten-Modul nicht verfügbar. Bitte Datenbank migrieren.', 'warning')
        return redirect(url_for('dashboard.index'))
    
    # Suchparameter
    search_term = request.args.get('q', '').strip()
    customer_id = request.args.get('customer_id', '')
    order_id = request.args.get('order_id', '')
    block_type = request.args.get('type', '')
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    quick_filter = request.args.get('filter', '')
    
    today = date.today()
    
    # Basis-Query: Nur CRM-relevante Typen
    crm_types = ProductionBlock.TYPE_CATEGORIES.get('crm', [])
    query = ProductionBlock.query.filter(
        ProductionBlock.is_active == True,
        ProductionBlock.block_type.in_(crm_types)
    )
    
    # Quick Filter
    if quick_filter == 'today':
        query = query.filter(ProductionBlock.start_date == today)
    elif quick_filter == 'week':
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        query = query.filter(
            ProductionBlock.start_date >= week_start,
            ProductionBlock.start_date <= week_end
        )
    elif quick_filter == 'follow_ups':
        query = query.filter(
            ProductionBlock.follow_up_date <= today,
            ProductionBlock.follow_up_date.isnot(None)
        )
    
    # Volltextsuche
    if search_term:
        search_pattern = f'%{search_term}%'
        query = query.filter(
            or_(
                ProductionBlock.title.ilike(search_pattern),
                ProductionBlock.summary.ilike(search_pattern),
                ProductionBlock.content.ilike(search_pattern),
                ProductionBlock.contact_person.ilike(search_pattern),
                ProductionBlock.notes.ilike(search_pattern)
            )
        )
    
    # Filter: Kunde
    if customer_id:
        query = query.filter(ProductionBlock.customer_id == customer_id)
    
    # Filter: Auftrag
    if order_id:
        query = query.filter(ProductionBlock.order_id == order_id)
    
    # Filter: Typ
    if block_type:
        query = query.filter(ProductionBlock.block_type == block_type)
    
    # Filter: Datum
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            query = query.filter(ProductionBlock.start_date >= start_date)
        except:
            pass
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            query = query.filter(ProductionBlock.start_date <= end_date)
        except:
            pass
    
    # Sortieren und Limit
    activities = query.order_by(
        ProductionBlock.start_date.desc(),
        ProductionBlock.start_time.desc()
    ).limit(50).all()
    
    # Statistiken (letzte 30 Tage)
    stats_start = today - timedelta(days=30)
    stats_query = ProductionBlock.query.filter(
        ProductionBlock.is_active == True,
        ProductionBlock.start_date >= stats_start
    )
    
    stats = {
        'calls': stats_query.filter(
            ProductionBlock.block_type.in_(['call_in', 'call_out'])
        ).count(),
        'visits': stats_query.filter(
            ProductionBlock.block_type.in_(['customer_visit', 'site_visit'])
        ).count(),
        'emails': stats_query.filter(
            ProductionBlock.block_type == 'email'
        ).count(),
        'follow_ups': ProductionBlock.query.filter(
            ProductionBlock.is_active == True,
            ProductionBlock.follow_up_date <= today,
            ProductionBlock.follow_up_date.isnot(None)
        ).count()
    }
    
    # Kunden für Filter-Dropdown
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.display_name).all()
    
    return render_template('crm/activities_search.html',
                         activities=activities,
                         stats=stats,
                         customers=customers)


@crm_bp.route('/kunde/<customer_id>/aktivitaeten')
@login_required
def customer_activities(customer_id):
    """
    Alle CRM-Aktivitäten für einen Kunden
    
    Zeigt Telefonate, Besuche, E-Mails etc. chronologisch
    """
    customer = Customer.query.get_or_404(customer_id)
    
    try:
        from src.models import ProductionBlock
        
        activities = ProductionBlock.query.filter(
            ProductionBlock.customer_id == customer_id,
            ProductionBlock.is_active == True
        ).order_by(
            ProductionBlock.start_date.desc(),
            ProductionBlock.start_time.desc()
        ).limit(100).all()
    except:
        activities = []
    
    return render_template('crm/customer_activities.html',
                         customer=customer,
                         activities=activities)


@crm_bp.route('/api/kunde/<customer_id>/aktivitaeten')
@login_required
def api_customer_activities(customer_id):
    """
    API: CRM-Aktivitäten eines Kunden als JSON
    
    Für AJAX-Laden in Kundendetailseite
    """
    try:
        from src.models import ProductionBlock
        
        activities = ProductionBlock.query.filter(
            ProductionBlock.customer_id == customer_id,
            ProductionBlock.is_active == True
        ).order_by(
            ProductionBlock.start_date.desc(),
            ProductionBlock.start_time.desc()
        ).limit(50).all()
        
        return jsonify({
            'success': True,
            'count': len(activities),
            'activities': [{
                'id': a.id,
                'type': a.block_type,
                'type_label': a.type_label,
                'icon': a.display_icon,
                'color': a.display_color,
                'title': a.title,
                'summary': a.summary[:150] + '...' if a.summary and len(a.summary) > 150 else a.summary,
                'date': a.start_date.strftime('%d.%m.%Y'),
                'time': a.start_time.strftime('%H:%M'),
                'contact_person': a.contact_person,
                'outcome': a.outcome_label,
                'order_id': a.order_id,
                'has_follow_up': a.follow_up_date is not None,
                'needs_follow_up': a.needs_follow_up
            } for a in activities]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_bp.route('/api/auftrag/<order_id>/aktivitaeten')
@login_required
def api_order_activities(order_id):
    """
    API: CRM-Aktivitäten eines Auftrags als JSON
    
    Für AJAX-Laden in Auftragsdetailseite
    """
    try:
        from src.models import ProductionBlock
        
        activities = ProductionBlock.query.filter(
            ProductionBlock.order_id == order_id,
            ProductionBlock.is_active == True
        ).order_by(
            ProductionBlock.start_date.desc(),
            ProductionBlock.start_time.desc()
        ).all()
        
        return jsonify({
            'success': True,
            'count': len(activities),
            'activities': [{
                'id': a.id,
                'type': a.block_type,
                'type_label': a.type_label,
                'icon': a.display_icon,
                'title': a.title,
                'summary': a.summary,
                'date': a.start_date.strftime('%d.%m.%Y'),
                'time': a.start_time.strftime('%H:%M'),
                'contact_person': a.contact_person,
                'outcome': a.outcome_label,
                'customer_name': a.customer.display_name if a.customer else None
            } for a in activities]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_bp.route('/api/wiedervorlagen')
@login_required
def api_pending_follow_ups():
    """
    API: Alle fälligen Wiedervorlagen
    
    Für Dashboard-Widget oder Benachrichtigungen
    """
    try:
        from src.models import ProductionBlock
        
        today = date.today()
        
        follow_ups = ProductionBlock.query.filter(
            ProductionBlock.follow_up_date <= today,
            ProductionBlock.is_active == True,
            ProductionBlock.follow_up_date.isnot(None)
        ).order_by(ProductionBlock.follow_up_date).all()
        
        return jsonify({
            'success': True,
            'count': len(follow_ups),
            'follow_ups': [{
                'id': fu.id,
                'type': fu.block_type,
                'type_label': fu.type_label,
                'title': fu.title,
                'original_date': fu.start_date.strftime('%d.%m.%Y'),
                'follow_up_date': fu.follow_up_date.strftime('%d.%m.%Y'),
                'days_overdue': (today - fu.follow_up_date).days,
                'customer_id': fu.customer_id,
                'customer_name': fu.customer.display_name if fu.customer else None,
                'contact_person': fu.contact_person,
                'follow_up_notes': fu.follow_up_notes
            } for fu in follow_ups]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
