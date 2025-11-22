# -*- coding: utf-8 -*-
"""
Angebote-Controller
==================

Erstellt von: StitchAdmin
Zweck: Angebots-Verwaltung mit CRM-Tracking
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import func, and_, or_
from src.models import db
from src.models.models import Order, Customer
from src.models.angebot import Angebot, AngebotStatus
from src.models.crm_activities import AngebotTracking, Activity, ActivityType

angebote_bp = Blueprint('angebote', __name__, url_prefix='/angebote')


@angebote_bp.route('/')
@login_required
def index():
    """Angebots-Übersicht"""

    # Filter-Parameter
    status_filter = request.args.get('status', 'alle')
    kunde_filter = request.args.get('kunde', '')
    sortierung = request.args.get('sort', 'datum')  # datum, nummer, kunde

    query = Angebot.query

    # Status filtern
    if status_filter != 'alle':
        query = query.filter_by(status=status_filter)

    # Kunde filtern
    if kunde_filter:
        query = query.filter(
            or_(
                Angebot.kunde_name.ilike(f'%{kunde_filter}%'),
                Angebot.angebotsnummer.ilike(f'%{kunde_filter}%')
            )
        )

    # Sortierung
    if sortierung == 'nummer':
        query = query.order_by(Angebot.angebotsnummer.desc())
    elif sortierung == 'kunde':
        query = query.order_by(Angebot.kunde_name)
    else:  # datum
        query = query.order_by(Angebot.angebotsdatum.desc())

    angebote = query.all()

    # Statistiken
    stats = {
        'gesamt': Angebot.query.count(),
        'entwurf': Angebot.query.filter_by(status=AngebotStatus.ENTWURF).count(),
        'verschickt': Angebot.query.filter_by(status=AngebotStatus.VERSCHICKT).count(),
        'angenommen': Angebot.query.filter_by(status=AngebotStatus.ANGENOMMEN).count(),
        'abgelehnt': Angebot.query.filter_by(status=AngebotStatus.ABGELEHNT).count(),
        'abgelaufen': Angebot.query.filter_by(status=AngebotStatus.ABGELAUFEN).count()
    }

    # Angebote mit Follow-up
    heute = date.today()
    follow_up_needed = AngebotTracking.query.filter(
        or_(
            AngebotTracking.naechster_kontakt_geplant <= heute,
            and_(
                AngebotTracking.letzter_kontakt.isnot(None),
                AngebotTracking.naechster_kontakt_geplant.is_(None)
            )
        )
    ).all()

    return render_template('angebote/index.html',
                         angebote=angebote,
                         stats=stats,
                         follow_up_needed=follow_up_needed,
                         status_filter=status_filter,
                         kunde_filter=kunde_filter,
                         sortierung=sortierung)


@angebote_bp.route('/<int:angebot_id>')
@login_required
def show(angebot_id):
    """Angebots-Details anzeigen"""

    angebot = Angebot.query.get_or_404(angebot_id)

    # Hole Tracking-Daten falls vorhanden
    tracking = AngebotTracking.query.filter_by(angebot_id=angebot_id).first()

    # Hole alle Aktivitäten zu diesem Angebot
    aktivitaeten = Activity.query.filter_by(angebot_id=angebot_id).order_by(Activity.created_at.desc()).all()

    return render_template('angebote/show.html',
                         angebot=angebot,
                         tracking=tracking,
                         aktivitaeten=aktivitaeten)


@angebote_bp.route('/neu', methods=['GET', 'POST'])
@login_required
def neu():
    """Neues Angebot erstellen"""

    if request.method == 'GET':
        # Hole Auftrag-ID falls vorhanden (von Auftrag erstellen)
        auftrag_id = request.args.get('auftrag_id')
        auftrag = None

        if auftrag_id:
            auftrag = Order.query.get_or_404(auftrag_id)

        # Hole alle Kunden für Dropdown
        kunden = Customer.query.order_by(Customer.display_name).all()

        return render_template('angebote/neu.html',
                             auftrag=auftrag,
                             kunden=kunden)

    # POST: Angebot erstellen
    try:
        auftrag_id = request.form.get('auftrag_id')

        if auftrag_id:
            # Aus Auftrag erstellen
            auftrag = Order.query.get_or_404(auftrag_id)

            angebot = Angebot.von_auftrag_erstellen(
                auftrag=auftrag,
                created_by=current_user.username,
                gueltig_tage=int(request.form.get('gueltig_tage', 30))
            )

            flash(f'Angebot {angebot.angebotsnummer} aus Auftrag {auftrag.id} erstellt.', 'success')
        else:
            # Neues Angebot ohne Auftrag
            kunde = Customer.query.get_or_404(request.form.get('kunde_id'))

            angebot = Angebot(
                kunde_id=kunde.id,
                kunde_name=kunde.display_name,
                kunde_adresse=kunde.full_address if hasattr(kunde, 'full_address') else '',
                kunde_email=kunde.email,
                titel=request.form.get('titel', ''),
                beschreibung=request.form.get('beschreibung', ''),
                gueltig_tage=int(request.form.get('gueltig_tage', 30)),
                created_by=current_user.username
            )

            db.session.add(angebot)
            db.session.flush()  # ID generieren

            # Positionen manuell hinzufügen
            # TODO: Implementieren Sie hier die Positionseingabe

            flash(f'Angebot {angebot.angebotsnummer} erstellt.', 'success')

        db.session.commit()
        return redirect(url_for('angebote.show', angebot_id=angebot.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Erstellen des Angebots: {str(e)}', 'danger')
        return redirect(url_for('angebote.index'))


@angebote_bp.route('/<int:angebot_id>/bearbeiten', methods=['GET', 'POST'])
@login_required
def bearbeiten(angebot_id):
    """Angebot bearbeiten"""

    angebot = Angebot.query.get_or_404(angebot_id)

    # Nur Entwürfe können bearbeitet werden
    if angebot.status != AngebotStatus.ENTWURF:
        flash('Nur Angebots-Entwürfe können bearbeitet werden.', 'warning')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))

    if request.method == 'GET':
        kunden = Customer.query.order_by(Customer.display_name).all()
        return render_template('angebote/bearbeiten.html',
                             angebot=angebot,
                             kunden=kunden)

    # POST: Änderungen speichern
    try:
        angebot.titel = request.form.get('titel', '')
        angebot.beschreibung = request.form.get('beschreibung', '')
        angebot.bemerkungen = request.form.get('bemerkungen', '')
        angebot.gueltig_tage = int(request.form.get('gueltig_tage', 30))
        angebot.updated_by = current_user.username
        angebot.updated_at = datetime.utcnow()

        # TODO: Positionen aktualisieren

        db.session.commit()
        flash(f'Angebot {angebot.angebotsnummer} aktualisiert.', 'success')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Aktualisieren: {str(e)}', 'danger')
        return redirect(url_for('angebote.bearbeiten', angebot_id=angebot_id))


@angebote_bp.route('/<int:angebot_id>/versenden', methods=['POST'])
@login_required
def versenden(angebot_id):
    """Angebot versenden und Tracking aktivieren"""

    angebot = Angebot.query.get_or_404(angebot_id)

    if angebot.status != AngebotStatus.ENTWURF:
        flash('Angebot wurde bereits versendet.', 'warning')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))

    try:
        # Follow-up Tage aus Form
        follow_up_tage = int(request.form.get('follow_up_tage', 7))
        verkaufschance = int(request.form.get('verkaufschance', 50))

        # Angebot versenden mit Tracking
        tracking = angebot.versenden_und_tracken(
            created_by=current_user.username,
            naechster_kontakt_tage=follow_up_tage
        )

        # Verkaufschance setzen
        tracking.verkaufschance_prozent = verkaufschance

        db.session.commit()

        flash(f'Angebot {angebot.angebotsnummer} versendet. Nächster Follow-up in {follow_up_tage} Tagen.', 'success')

        # TODO: PDF generieren und per E-Mail versenden

        return redirect(url_for('angebote.show', angebot_id=angebot_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Versenden: {str(e)}', 'danger')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))


@angebote_bp.route('/<int:angebot_id>/annehmen', methods=['POST'])
@login_required
def annehmen(angebot_id):
    """Angebot als angenommen markieren"""

    angebot = Angebot.query.get_or_404(angebot_id)

    try:
        angebot.annehmen(created_by=current_user.username)
        db.session.commit()

        flash(f'Angebot {angebot.angebotsnummer} wurde angenommen!', 'success')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))


@angebote_bp.route('/<int:angebot_id>/ablehnen', methods=['POST'])
@login_required
def ablehnen(angebot_id):
    """Angebot als abgelehnt markieren"""

    angebot = Angebot.query.get_or_404(angebot_id)

    try:
        grund = request.form.get('grund', '')

        angebot.ablehnen(
            grund=grund,
            created_by=current_user.username
        )

        db.session.commit()

        flash(f'Angebot {angebot.angebotsnummer} wurde abgelehnt.', 'info')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))


@angebote_bp.route('/<int:angebot_id>/in-auftrag-umwandeln', methods=['POST'])
@login_required
def in_auftrag_umwandeln(angebot_id):
    """Angebot in Produktionsauftrag umwandeln"""

    angebot = Angebot.query.get_or_404(angebot_id)

    if angebot.status != AngebotStatus.ANGENOMMEN:
        flash('Nur angenommene Angebote können in Aufträge umgewandelt werden.', 'warning')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))

    try:
        auftrag = angebot.in_auftrag_umwandeln(created_by=current_user.username)
        db.session.commit()

        flash(f'Angebot {angebot.angebotsnummer} in Auftrag {auftrag.id} umgewandelt!', 'success')
        return redirect(url_for('orders.view_order', order_id=auftrag.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Fehler bei der Umwandlung: {str(e)}', 'danger')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))


@angebote_bp.route('/<int:angebot_id>/kontakt', methods=['POST'])
@login_required
def kontakt_durchgefuehrt(angebot_id):
    """Registriere einen durchgeführten Kontakt (Follow-up)"""

    angebot = Angebot.query.get_or_404(angebot_id)
    tracking = AngebotTracking.query.filter_by(angebot_id=angebot_id).first()

    if not tracking:
        flash('Kein Tracking für dieses Angebot gefunden.', 'warning')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))

    try:
        ergebnis = request.form.get('ergebnis', '')
        verkaufschance = request.form.get('verkaufschance', None)
        naechster_kontakt_tage = request.form.get('naechster_kontakt_tage', None)

        # Kontakt registrieren
        tracking.kontakt_durchgefuehrt(
            ergebnis=ergebnis,
            created_by=current_user.username
        )

        # Verkaufschance aktualisieren
        if verkaufschance:
            tracking.verkaufschance_aktualisieren(
                prozent=int(verkaufschance),
                begruendung=ergebnis
            )

        # Nächsten Kontakt planen
        if naechster_kontakt_tage:
            tracking.naechsten_kontakt_planen(
                tage_bis_kontakt=int(naechster_kontakt_tage)
            )

        db.session.commit()

        flash(f'Kontakt für Angebot {angebot.angebotsnummer} registriert.', 'success')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))


@angebote_bp.route('/<int:angebot_id>/loeschen', methods=['POST'])
@login_required
def loeschen(angebot_id):
    """Angebot löschen"""

    if not current_user.is_admin:
        flash('Nur Administratoren können Angebote löschen.', 'danger')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))

    angebot = Angebot.query.get_or_404(angebot_id)

    # Nur Entwürfe können gelöscht werden
    if angebot.status != AngebotStatus.ENTWURF:
        flash('Nur Angebots-Entwürfe können gelöscht werden.', 'warning')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))

    try:
        nummer = angebot.angebotsnummer
        db.session.delete(angebot)
        db.session.commit()

        flash(f'Angebot {nummer} wurde gelöscht.', 'success')
        return redirect(url_for('angebote.index'))

    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Löschen: {str(e)}', 'danger')
        return redirect(url_for('angebote.show', angebot_id=angebot_id))


@angebote_bp.route('/<int:angebot_id>/pdf')
@login_required
def pdf_generieren(angebot_id):
    """PDF für Angebot generieren"""

    angebot = Angebot.query.get_or_404(angebot_id)

    # TODO: PDF-Generierung implementieren
    flash('PDF-Generierung ist noch nicht implementiert.', 'info')
    return redirect(url_for('angebote.show', angebot_id=angebot_id))
