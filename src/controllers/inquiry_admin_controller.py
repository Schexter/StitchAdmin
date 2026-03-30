# -*- coding: utf-8 -*-
"""
Admin-Controller für Anfragen-Verwaltung
Liste, Detail, Status ändern, zuweisen, konvertieren

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import uuid
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import func
from src.models.models import db, Order, Customer, User
from src.models.inquiry import Inquiry, INQUIRY_TYPE_LABELS
from src.services.inquiry_service import update_inquiry_status

inquiry_admin_bp = Blueprint('inquiry_admin', __name__, url_prefix='/admin/anfragen')


@inquiry_admin_bp.route('/neu', methods=['GET', 'POST'])
@login_required
def neue_anfrage():
    """Neue Anfrage händisch anlegen (Telefon, E-Mail, persönlich)"""
    if request.method == 'GET':
        kunde_id = request.args.get('kunde_id', '')
        kunden = Customer.query.order_by(Customer.company_name, Customer.last_name).all()
        vorselektierter_kunde = None
        if kunde_id:
            vorselektierter_kunde = Customer.query.get(kunde_id)

        return render_template('inquiry_admin/neue_anfrage.html',
                             kunden=kunden,
                             vorselektierter_kunde=vorselektierter_kunde,
                             inquiry_types=INQUIRY_TYPE_LABELS)

    # POST: Anfrage erstellen
    try:
        # Kundendaten ermitteln
        kunde_id = request.form.get('kunde_id')
        kunde = None
        if kunde_id:
            kunde = Customer.query.get(kunde_id)

        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        company_name = request.form.get('company_name', '')

        # Wenn Kunde gewählt, Daten übernehmen
        if kunde:
            first_name = first_name or kunde.first_name or ''
            last_name = last_name or kunde.last_name or ''
            email = email or kunde.email or ''
            phone = phone or kunde.phone or ''
            company_name = company_name or kunde.company_name or ''

        if not first_name or not last_name:
            flash('Vorname und Nachname sind erforderlich.', 'danger')
            return redirect(url_for('inquiry_admin.neue_anfrage'))

        # Nummer und Token generieren
        from src.services.inquiry_service import _generate_inquiry_number
        inquiry_number = _generate_inquiry_number()
        tracking_token = uuid.uuid4().hex

        # Wunschtermin parsen
        desired_date = None
        if request.form.get('desired_date'):
            try:
                desired_date = datetime.strptime(request.form['desired_date'], '%Y-%m-%d').date()
            except ValueError:
                pass

        inquiry = Inquiry(
            inquiry_number=inquiry_number,
            tracking_token=tracking_token,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            company_name=company_name,
            customer_id=kunde_id if kunde else None,
            inquiry_type=request.form.get('inquiry_type', 'sonstige'),
            description=request.form.get('description', ''),
            quantity=int(request.form.get('quantity', 0)) if request.form.get('quantity') else None,
            textile_type=request.form.get('textile_type', ''),
            desired_date=desired_date,
            internal_notes=request.form.get('internal_notes', ''),
            source='manual',
            dsgvo_consent=True,
            dsgvo_consent_at=datetime.utcnow(),
            assigned_to=current_user.username,
            status='in_bearbeitung',
        )

        db.session.add(inquiry)

        # Wenn kein Kunde verknüpft, nach E-Mail suchen oder neu anlegen
        if not kunde and email:
            existing = Customer.query.filter_by(email=email.strip().lower()).first()
            if existing:
                inquiry.customer_id = existing.id

        db.session.commit()

        flash(f'Anfrage {inquiry_number} erfolgreich angelegt.', 'success')
        return redirect(url_for('inquiry_admin.detail', id=inquiry.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Anlegen: {str(e)}', 'danger')
        return redirect(url_for('inquiry_admin.neue_anfrage'))


@inquiry_admin_bp.route('/')
@login_required
def list():
    """Alle Anfragen mit Filtern"""
    status_filter = request.args.get('status')
    type_filter = request.args.get('type')

    query = Inquiry.query

    if status_filter:
        query = query.filter_by(status=status_filter)
    else:
        # Standardmaessig stornierte Anfragen ausblenden (nur im CRM sichtbar)
        query = query.filter(Inquiry.status != 'storniert')
    if type_filter:
        query = query.filter_by(inquiry_type=type_filter)

    inquiries = query.order_by(Inquiry.created_at.desc()).all()

    # Statistiken (1 Query statt 4)
    status_counts = db.session.query(
        Inquiry.status, func.count(Inquiry.id)
    ).group_by(Inquiry.status).all()
    count_map = {s: c for s, c in status_counts}
    stats = {
        'total': sum(count_map.values()),
        'neu': count_map.get('neu', 0),
        'in_bearbeitung': count_map.get('in_bearbeitung', 0),
        'angebot_erstellt': count_map.get('angebot_erstellt', 0),
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


@inquiry_admin_bp.route('/<int:id>/bearbeiten', methods=['GET', 'POST'])
@login_required
def bearbeiten(id):
    """Anfrage bearbeiten"""
    inquiry = Inquiry.query.get_or_404(id)

    if request.method == 'POST':
        inquiry.first_name = request.form.get('first_name', inquiry.first_name)
        inquiry.last_name = request.form.get('last_name', inquiry.last_name)
        inquiry.email = request.form.get('email', '') or ''
        inquiry.phone = request.form.get('phone', '') or None
        inquiry.company_name = request.form.get('company_name', '') or None
        inquiry.inquiry_type = request.form.get('inquiry_type', inquiry.inquiry_type)
        inquiry.description = request.form.get('description', inquiry.description)
        qty = request.form.get('quantity', '')
        inquiry.quantity = int(qty) if qty else None
        inquiry.textile_type = request.form.get('textile_type', '') or None
        inquiry.textile_color = request.form.get('textile_color', '') or None
        dd = request.form.get('desired_date', '')
        inquiry.desired_date = datetime.strptime(dd, '%Y-%m-%d').date() if dd else None
        inquiry.internal_notes = request.form.get('internal_notes', '')
        inquiry.updated_by = current_user.username
        db.session.commit()
        flash('Anfrage aktualisiert.', 'success')
        return redirect(url_for('inquiry_admin.detail', id=id))

    return render_template('inquiry_admin/bearbeiten.html',
                         inquiry=inquiry,
                         inquiry_types=INQUIRY_TYPE_LABELS)


@inquiry_admin_bp.route('/<int:id>/kunde-anlegen', methods=['POST'])
@login_required
def kunde_anlegen(id):
    """Kunden aus Anfrage-Daten automatisch anlegen und verknuepfen"""
    inquiry = Inquiry.query.get_or_404(id)

    if inquiry.customer_id:
        flash('Anfrage ist bereits mit einem Kunden verknuepft.', 'info')
        return redirect(url_for('inquiry_admin.detail', id=id))

    try:
        from src.services.id_generator_service import IdGenerator
        generate_customer_id = IdGenerator.customer

        kunde = Customer(
            id=generate_customer_id(),
            first_name=inquiry.first_name,
            last_name=inquiry.last_name,
            email=inquiry.email or None,
            phone=inquiry.phone or None,
            company_name=inquiry.company_name or None,
            customer_type='business' if inquiry.company_name else 'private',
            is_active=True,
            created_by=current_user.username,
        )
        db.session.add(kunde)

        inquiry.customer_id = kunde.id
        inquiry.updated_by = current_user.username
        db.session.commit()

        flash(f'Kunde {kunde.display_name} ({kunde.id}) angelegt und verknuepft.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')

    return redirect(url_for('inquiry_admin.detail', id=id))


@inquiry_admin_bp.route('/<int:id>/kunde-verknuepfen')
@login_required
def kunde_verknuepfen(id):
    """Bestehenden Kunden mit Anfrage verknuepfen"""
    inquiry = Inquiry.query.get_or_404(id)
    kunde_id = request.args.get('kunde_id')

    if not kunde_id:
        flash('Keine Kunden-ID angegeben.', 'danger')
        return redirect(url_for('inquiry_admin.detail', id=id))

    kunde = Customer.query.get(kunde_id)
    if not kunde:
        flash('Kunde nicht gefunden.', 'danger')
        return redirect(url_for('inquiry_admin.detail', id=id))

    inquiry.customer_id = kunde_id
    inquiry.updated_by = current_user.username
    db.session.commit()

    flash(f'Anfrage mit Kunde {kunde.display_name} verknuepft.', 'success')
    return redirect(url_for('inquiry_admin.detail', id=id))


@inquiry_admin_bp.route('/<int:id>/als-auftrag', methods=['GET', 'POST'])
@login_required
def als_auftrag(id):
    """Anfrage direkt in Auftrag/Auftraege umwandeln (mit optionalem Split)"""
    from src.models.models import OrderItem
    from src.services.id_generator_service import IdGenerator
    generate_order_id = IdGenerator.order

    inquiry = Inquiry.query.get_or_404(id)

    if inquiry.order_id:
        flash('Anfrage wurde bereits in einen Auftrag umgewandelt.', 'warning')
        return redirect(url_for('inquiry_admin.detail', id=id))

    if not inquiry.customer_id:
        flash('Bitte zuerst einen Kunden verknuepfen.', 'danger')
        return redirect(url_for('inquiry_admin.detail', id=id))

    kunde = Customer.query.get(inquiry.customer_id)

    if request.method == 'POST':
        try:
            # Welche Auftraege sollen erstellt werden?
            split_types = request.form.getlist('auftrag_typ')
            if not split_types:
                split_types = [inquiry.inquiry_type or 'embroidery']

            created_orders = []
            for auftrag_typ in split_types:
                typ_labels = {
                    'design': 'Grafik/Design', 'embroidery': 'Bestickung',
                    'printing': 'Textildruck', 'dtf': 'DTF-Druck',
                    'sublimation': 'Sublimation', 'shipping': 'Versand'
                }
                typ_label = typ_labels.get(auftrag_typ, auftrag_typ)

                order = Order(
                    id=generate_order_id(),
                    customer_id=inquiry.customer_id,
                    order_type=auftrag_typ if auftrag_typ != 'design' else inquiry.inquiry_type,
                    auftrag_typ=auftrag_typ,
                    status='new',
                    description=f"{typ_label}: {inquiry.description}" if len(split_types) > 1 else inquiry.description,
                    internal_notes=inquiry.internal_notes or '',
                    is_kundenware=False,
                    total_price=0,
                    created_by=current_user.username,
                    created_at=datetime.utcnow(),
                )

                # Details aus Anfrage uebernehmen
                if auftrag_typ in ('embroidery', 'printing', 'dtf', 'sublimation'):
                    if inquiry.quantity:
                        item = OrderItem(
                            order_id=order.id,
                            quantity=inquiry.quantity,
                            unit_price=0,
                        )
                        db.session.add(item)
                    if inquiry.design_file_path:
                        order.design_file_path = inquiry.design_file_path

                if inquiry.desired_date:
                    order.due_date = datetime.combine(inquiry.desired_date, datetime.min.time())

                db.session.add(order)
                created_orders.append(order)

            # Anfrage als umgewandelt markieren
            if created_orders:
                inquiry.order_id = created_orders[0].id
                inquiry.status = 'auftrag_erstellt'
                inquiry.updated_by = current_user.username

            db.session.commit()

            if len(created_orders) == 1:
                flash(f'Auftrag {created_orders[0].id} aus Anfrage {inquiry.inquiry_number} erstellt.', 'success')
                return redirect(url_for('orders.show', order_id=created_orders[0].id))
            else:
                nummern = ', '.join(o.id for o in created_orders)
                flash(f'{len(created_orders)} Auftraege erstellt: {nummern}', 'success')
                return redirect(url_for('orders.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {str(e)}', 'danger')
            return redirect(url_for('inquiry_admin.detail', id=id))

    # GET: Split-Dialog anzeigen
    # Moegliche Auftragstypen basierend auf Anfrage-Typ
    typ_options = []
    it = inquiry.inquiry_type or 'embroidery'

    # Design/Grafik ist fast immer noetig
    if it in ('embroidery', 'printing', 'dtf', 'sublimation', 'combined', 'design'):
        typ_options.append({'key': 'design', 'label': 'Grafik / Design erstellen', 'icon': 'bi-palette', 'checked': True})

    # Produktionstypen je nach Anfrage
    if it in ('embroidery', 'combined'):
        typ_options.append({'key': 'embroidery', 'label': 'Bestickung', 'icon': 'bi-brush', 'checked': True})
    if it in ('printing', 'combined'):
        typ_options.append({'key': 'printing', 'label': 'Textildruck', 'icon': 'bi-printer', 'checked': True})
    if it == 'dtf':
        typ_options.append({'key': 'dtf', 'label': 'DTF-Druck', 'icon': 'bi-layers', 'checked': True})
    if it == 'sublimation':
        typ_options.append({'key': 'sublimation', 'label': 'Sublimation', 'icon': 'bi-droplet', 'checked': True})

    # Immer Versand als Option
    typ_options.append({'key': 'shipping', 'label': 'Versand / Logistik', 'icon': 'bi-truck', 'checked': False})

    # Fallback falls gar nichts passt
    if len(typ_options) <= 1:
        typ_options.insert(0, {'key': it, 'label': INQUIRY_TYPE_LABELS.get(it, it), 'icon': 'bi-gear', 'checked': True})

    return render_template('inquiry_admin/als_auftrag.html',
                         inquiry=inquiry,
                         kunde=kunde,
                         typ_options=typ_options)


@inquiry_admin_bp.route('/<int:id>/status', methods=['POST'])
@login_required
def change_status(id):
    """Status ändern"""
    new_status = request.form.get('status')
    if new_status:
        update_inquiry_status(id, new_status, updated_by=current_user.username)
        flash('Status aktualisiert.', 'success')
    return redirect(url_for('inquiry_admin.detail', id=id))


@inquiry_admin_bp.route('/<int:id>/stornieren', methods=['POST'])
@login_required
def stornieren(id):
    """Anfrage stornieren mit optionalem Grund"""
    grund = request.form.get('grund', '').strip()
    update_inquiry_status(id, 'storniert', updated_by=current_user.username)
    if grund:
        inquiry = Inquiry.query.get(id)
        if inquiry:
            prefix = '\n\nStornierung: '
            inquiry.internal_notes = (inquiry.internal_notes or '') + prefix + grund
            db.session.commit()
    flash('Anfrage wurde storniert.', 'warning')
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


@inquiry_admin_bp.route('/<int:id>/reply', methods=['POST'])
@login_required
def reply(id):
    """Anfrage per E-Mail beantworten"""
    inquiry = Inquiry.query.get_or_404(id)

    subject = request.form.get('subject', '')
    body = request.form.get('body', '')

    if not subject or not body:
        flash('Betreff und Nachricht sind erforderlich.', 'warning')
        return redirect(url_for('inquiry_admin.detail', id=id))

    # Status-Link anhängen falls Tracking-Token vorhanden
    status_footer = ''
    if hasattr(inquiry, 'tracking_token') and inquiry.tracking_token:
        try:
            status_url = url_for('inquiry.status', token=inquiry.tracking_token, _external=True)
            status_footer = f'\n\n---\nStatus Ihrer Anfrage verfolgen: {status_url}'
            body = body + status_footer
        except Exception:
            pass

    # E-Mail senden
    try:
        from src.services.email_service_new import EmailService
        service = EmailService()
        html_body = f'<p>{body.replace(chr(10), "<br>")}</p>'
        result = service.send_email(
            to=inquiry.email,
            subject=subject,
            body=body,
            html_body=html_body,
        )
        if not result.get('success'):
            flash(f'E-Mail-Versand fehlgeschlagen: {result.get("error", "Unbekannt")}', 'danger')
            return redirect(url_for('inquiry_admin.detail', id=id))
    except Exception as e:
        flash(f'Fehler beim E-Mail-Versand: {e}', 'danger')
        return redirect(url_for('inquiry_admin.detail', id=id))

    # CRM-Kontakt anlegen
    if inquiry.customer_id:
        try:
            from src.models.crm_contact import CustomerContact, ContactType, ContactStatus
            contact = CustomerContact(
                customer_id=inquiry.customer_id,
                contact_type=ContactType.EMAIL_AUSGANG,
                status=ContactStatus.ERLEDIGT,
                subject=subject,
                body_html=f'<p>{body.replace(chr(10), "<br>")}</p>',
                body_text=body,
                email_to=inquiry.email,
                contact_date=datetime.utcnow(),
                created_at=datetime.utcnow(),
                created_by=current_user.username,
            )
            db.session.add(contact)
        except Exception:
            pass

    # Status auf "in_bearbeitung" setzen falls noch "neu"
    if inquiry.status == 'neu':
        inquiry.status = 'in_bearbeitung'
    inquiry.updated_by = current_user.username
    inquiry.updated_at = datetime.utcnow()
    db.session.commit()

    flash(f'Antwort an {inquiry.email} gesendet!', 'success')
    return redirect(url_for('inquiry_admin.detail', id=id))


@inquiry_admin_bp.route('/<int:id>/update-customer', methods=['POST'])
@login_required
def update_customer_name(id):
    """Kundendaten aus Anfrage aktualisieren"""
    inquiry = Inquiry.query.get_or_404(id)
    if not inquiry.customer_id:
        flash('Kein Kunde verknüpft.', 'warning')
        return redirect(url_for('inquiry_admin.detail', id=id))

    from src.models.models import Customer
    customer = Customer.query.get(inquiry.customer_id)
    if not customer:
        flash('Kunde nicht gefunden.', 'danger')
        return redirect(url_for('inquiry_admin.detail', id=id))

    customer.first_name = inquiry.first_name
    customer.last_name = inquiry.last_name
    if inquiry.phone and not customer.phone:
        customer.phone = inquiry.phone
    if inquiry.company_name and not customer.company_name:
        customer.company_name = inquiry.company_name

    db.session.commit()
    flash(f'Kundendaten auf "{inquiry.full_name}" aktualisiert.', 'success')
    return redirect(url_for('inquiry_admin.detail', id=id))
