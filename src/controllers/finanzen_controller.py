# -*- coding: utf-8 -*-
"""
Finanzen-Controller
===================

Erstellt von: StitchAdmin
Zweck: Finanzen-Übersicht, Offene Posten, Mahnwesen, Liquidität
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import func, and_, or_
from src.models import db
from src.models.rechnungsmodul.models import Rechnung, RechnungsStatus
from src.models.mahnwesen import Mahnung, MahnStatus, Ratenzahlung, Rate
from src.models.angebot import Angebot, AngebotStatus
from src.models.crm_activities import AngebotTracking, Activity

finanzen_bp = Blueprint('finanzen', __name__, url_prefix='/finanzen')


@finanzen_bp.route('/')
@login_required
def index():
    """Finanzen-Hauptübersicht"""

    # ========== OFFENE FORDERUNGEN ==========
    offene_rechnungen = Rechnung.query.filter_by(status=RechnungsStatus.OFFEN).all()

    forderungen_gesamt = Decimal('0.0')
    forderungen_ueberfaellig = Decimal('0.0')
    forderungen_faellig_7_tage = Decimal('0.0')
    forderungen_faellig_30_tage = Decimal('0.0')

    heute = date.today()
    in_7_tagen = heute + timedelta(days=7)
    in_30_tagen = heute + timedelta(days=30)

    ueberfaellige_rechnungen = []

    for rechnung in offene_rechnungen:
        offener_betrag = Decimal(str(rechnung.offener_betrag))
        forderungen_gesamt += offener_betrag

        if rechnung.faelligkeitsdatum < heute:
            forderungen_ueberfaellig += offener_betrag
            ueberfaellige_rechnungen.append(rechnung)
        elif rechnung.faelligkeitsdatum <= in_7_tagen:
            forderungen_faellig_7_tage += offener_betrag
        elif rechnung.faelligkeitsdatum <= in_30_tagen:
            forderungen_faellig_30_tage += offener_betrag

    # ========== MAHNWESEN ==========
    mahnungen_1 = Mahnung.query.filter_by(mahnstufe=1, status=MahnStatus.VERSENDET).count()
    mahnungen_2 = Mahnung.query.filter_by(mahnstufe=2, status=MahnStatus.VERSENDET).count()
    mahnungen_3 = Mahnung.query.filter_by(mahnstufe=3, status=MahnStatus.VERSENDET).count()

    mahnungen_gesamt = Mahnung.query.filter_by(status=MahnStatus.VERSENDET).all()
    mahngebuehren_gesamt = sum(Decimal(str(m.mahngebuehr or 0)) for m in mahnungen_gesamt)
    verzugszinsen_gesamt = sum(Decimal(str(m.verzugszinsen or 0)) for m in mahnungen_gesamt)

    # Nächste Mahnungen (automatischer Mahnlauf)
    naechste_mahnungen = []
    for rechnung in ueberfaellige_rechnungen:
        tage_ueberfaellig = (heute - rechnung.faelligkeitsdatum).days

        # Letzte Mahnung prüfen
        letzte_mahnung = Mahnung.query.filter_by(
            rechnung_id=rechnung.id
        ).order_by(Mahnung.mahnstufe.desc()).first()

        if not letzte_mahnung and tage_ueberfaellig >= 7:
            # 1. Mahnung fällig
            naechste_mahnungen.append({
                'rechnung': rechnung,
                'mahnstufe': 1,
                'grund': f'{tage_ueberfaellig} Tage überfällig'
            })
        elif letzte_mahnung and letzte_mahnung.status == MahnStatus.VERSENDET:
            tage_seit_mahnung = (heute - letzte_mahnung.versanddatum).days if letzte_mahnung.versanddatum else 0

            if tage_seit_mahnung >= 14 and letzte_mahnung.mahnstufe < 3:
                # Nächste Mahnstufe
                naechste_mahnungen.append({
                    'rechnung': rechnung,
                    'mahnstufe': letzte_mahnung.mahnstufe + 1,
                    'grund': f'{tage_seit_mahnung} Tage seit letzter Mahnung'
                })

    # ========== RATENZAHLUNGEN ==========
    ratenzahlungen_aktiv = Ratenzahlung.query.filter_by(status='aktiv').all()

    raten_gesamt_offen = Decimal('0.0')
    raten_faellig_heute = []
    raten_faellig_woche = []

    for rz in ratenzahlungen_aktiv:
        raten_gesamt_offen += Decimal(str(rz.offener_betrag))

        for rate in rz.raten:
            if rate.status == 'offen':
                if rate.faelligkeitsdatum <= heute:
                    raten_faellig_heute.append(rate)
                elif rate.faelligkeitsdatum <= in_7_tagen:
                    raten_faellig_woche.append(rate)

    # ========== ANGEBOTE (VERKAUFSCHANCEN) ==========
    angebote_offen = Angebot.query.filter(
        Angebot.status.in_([AngebotStatus.VERSCHICKT])
    ).all()

    angebote_follow_up = AngebotTracking.query.filter(
        or_(
            AngebotTracking.naechster_kontakt_geplant <= heute,
            and_(
                AngebotTracking.letzter_kontakt.isnot(None),
                AngebotTracking.naechster_kontakt_geplant.is_(None)
            )
        )
    ).all()

    erwarteter_umsatz = Decimal('0.0')
    gewichteter_umsatz = Decimal('0.0')

    for angebot in angebote_offen:
        erwarteter_umsatz += Decimal(str(angebot.brutto_gesamt or 0))

        # Gewichteter Umsatz (mit Verkaufschance)
        if hasattr(angebot, 'tracking') and angebot.tracking:
            chance = Decimal(str(angebot.tracking.verkaufschance_prozent or 50)) / Decimal('100')
            gewichteter_umsatz += Decimal(str(angebot.brutto_gesamt or 0)) * chance
        else:
            gewichteter_umsatz += Decimal(str(angebot.brutto_gesamt or 0)) * Decimal('0.5')

    # ========== UMSATZ (letzten 30 Tage) ==========
    vor_30_tagen = heute - timedelta(days=30)

    rechnungen_30_tage = Rechnung.query.filter(
        Rechnung.rechnungsdatum >= vor_30_tagen
    ).all()

    umsatz_30_tage = sum(Decimal(str(r.brutto_gesamt or 0)) for r in rechnungen_30_tage)
    zahlungseingang_30_tage = sum(Decimal(str(r.bezahlt_betrag or 0)) for r in rechnungen_30_tage)

    # ========== LIQUIDITÄT ==========
    # Vereinfachte Liquiditätsberechnung
    liquide_mittel = zahlungseingang_30_tage  # Sollte aus Banking-API kommen
    verbindlichkeiten = forderungen_gesamt

    liquiditaet = {
        'liquide_mittel': float(liquide_mittel),
        'forderungen': float(forderungen_gesamt),
        'verbindlichkeiten': float(verbindlichkeiten),
        'liquiditaetsgrad': float((liquide_mittel / verbindlichkeiten * 100) if verbindlichkeiten > 0 else 0)
    }

    # ========== NEUESTE AKTIVITÄTEN ==========
    neueste_aktivitaeten = Activity.query.filter(
        Activity.activity_type.in_(['angebot_versendet', 'angebot_nachfrage', 'angebot_angenommen', 'angebot_abgelehnt'])
    ).order_by(Activity.created_at.desc()).limit(10).all()

    return render_template('finanzen/index.html',
                         # Forderungen
                         forderungen_gesamt=float(forderungen_gesamt),
                         forderungen_ueberfaellig=float(forderungen_ueberfaellig),
                         forderungen_faellig_7_tage=float(forderungen_faellig_7_tage),
                         forderungen_faellig_30_tage=float(forderungen_faellig_30_tage),
                         ueberfaellige_rechnungen=ueberfaellige_rechnungen[:10],  # Top 10
                         # Mahnwesen
                         mahnungen_1=mahnungen_1,
                         mahnungen_2=mahnungen_2,
                         mahnungen_3=mahnungen_3,
                         mahngebuehren_gesamt=float(mahngebuehren_gesamt),
                         verzugszinsen_gesamt=float(verzugszinsen_gesamt),
                         naechste_mahnungen=naechste_mahnungen[:10],
                         # Ratenzahlungen
                         ratenzahlungen_aktiv_count=len(ratenzahlungen_aktiv),
                         raten_gesamt_offen=float(raten_gesamt_offen),
                         raten_faellig_heute=raten_faellig_heute,
                         raten_faellig_woche=raten_faellig_woche,
                         # Angebote
                         angebote_offen_count=len(angebote_offen),
                         angebote_follow_up_count=len(angebote_follow_up),
                         erwarteter_umsatz=float(erwarteter_umsatz),
                         gewichteter_umsatz=float(gewichteter_umsatz),
                         # Umsatz
                         umsatz_30_tage=float(umsatz_30_tage),
                         zahlungseingang_30_tage=float(zahlungseingang_30_tage),
                         # Liquidität
                         liquiditaet=liquiditaet,
                         # Aktivitäten
                         neueste_aktivitaeten=neueste_aktivitaeten)


@finanzen_bp.route('/offene-posten')
@login_required
def offene_posten():
    """Detaillierte Liste aller offenen Posten"""

    # Filter-Parameter
    filter_status = request.args.get('status', 'alle')
    filter_kunde = request.args.get('kunde', '')
    sortierung = request.args.get('sort', 'faelligkeit')  # faelligkeit, betrag, kunde

    query = Rechnung.query.filter_by(status=RechnungsStatus.OFFEN)

    # Kunde filtern
    if filter_kunde:
        query = query.filter(
            or_(
                Rechnung.kunde_name.ilike(f'%{filter_kunde}%'),
                Rechnung.rechnungsnummer.ilike(f'%{filter_kunde}%')
            )
        )

    # Status filtern
    heute = date.today()

    if filter_status == 'ueberfaellig':
        query = query.filter(Rechnung.faelligkeitsdatum < heute)
    elif filter_status == 'faellig_7_tage':
        in_7_tagen = heute + timedelta(days=7)
        query = query.filter(
            and_(
                Rechnung.faelligkeitsdatum >= heute,
                Rechnung.faelligkeitsdatum <= in_7_tagen
            )
        )
    elif filter_status == 'faellig_30_tage':
        in_7_tagen = heute + timedelta(days=7)
        in_30_tagen = heute + timedelta(days=30)
        query = query.filter(
            and_(
                Rechnung.faelligkeitsdatum > in_7_tagen,
                Rechnung.faelligkeitsdatum <= in_30_tagen
            )
        )

    # Sortierung
    if sortierung == 'betrag':
        query = query.order_by(Rechnung.brutto_gesamt.desc())
    elif sortierung == 'kunde':
        query = query.order_by(Rechnung.kunde_name)
    else:  # faelligkeit
        query = query.order_by(Rechnung.faelligkeitsdatum)

    rechnungen = query.all()

    # Gesamtsummen berechnen
    gesamt_forderung = sum(Decimal(str(r.offener_betrag)) for r in rechnungen)

    return render_template('finanzen/offene_posten.html',
                         rechnungen=rechnungen,
                         gesamt_forderung=float(gesamt_forderung),
                         filter_status=filter_status,
                         filter_kunde=filter_kunde,
                         sortierung=sortierung)


@finanzen_bp.route('/mahnungen')
@login_required
def mahnungen():
    """Mahnwesen-Übersicht"""

    status_filter = request.args.get('status', 'versendet')

    query = Mahnung.query

    if status_filter != 'alle':
        query = query.filter_by(status=status_filter)

    mahnungen = query.order_by(Mahnung.mahndatum.desc()).all()

    return render_template('finanzen/mahnungen.html',
                         mahnungen=mahnungen,
                         status_filter=status_filter)


@finanzen_bp.route('/mahnung/erstellen/<int:rechnung_id>', methods=['POST'])
@login_required
def mahnung_erstellen(rechnung_id):
    """Erstellt eine neue Mahnung"""

    if not current_user.is_admin:
        flash('Nur Administratoren können Mahnungen erstellen.', 'danger')
        return redirect(url_for('finanzen.index'))

    rechnung = Rechnung.query.get_or_404(rechnung_id)

    # Prüfe letzte Mahnung
    letzte_mahnung = Mahnung.query.filter_by(
        rechnung_id=rechnung_id
    ).order_by(Mahnung.mahnstufe.desc()).first()

    mahnstufe = 1 if not letzte_mahnung else letzte_mahnung.mahnstufe + 1

    if mahnstufe > 3:
        flash('Maximale Mahnstufe (3) bereits erreicht. Bitte Inkasso einleiten.', 'warning')
        return redirect(url_for('finanzen.mahnungen'))

    try:
        # Kunde ist Geschäftskunde?
        ist_geschaeftskunde = hasattr(rechnung.kunde, 'is_business') and rechnung.kunde.is_business

        mahnung = Mahnung.erstelle_mahnung(
            rechnung=rechnung,
            mahnstufe=mahnstufe,
            ist_geschaeftskunde=ist_geschaeftskunde,
            created_by=current_user.username
        )

        flash(f'Mahnung {mahnung.mahnungsnummer} (Stufe {mahnstufe}) erfolgreich erstellt.', 'success')

    except Exception as e:
        flash(f'Fehler beim Erstellen der Mahnung: {str(e)}', 'danger')

    return redirect(url_for('finanzen.mahnungen'))


@finanzen_bp.route('/ratenzahlungen')
@login_required
def ratenzahlungen():
    """Ratenzahlungs-Übersicht"""

    ratenzahlungen = Ratenzahlung.query.filter_by(status='aktiv').all()

    return render_template('finanzen/ratenzahlungen.html',
                         ratenzahlungen=ratenzahlungen)


@finanzen_bp.route('/liquiditaet')
@login_required
def liquiditaet():
    """Liquiditäts-Übersicht"""

    if not current_user.is_admin:
        flash('Nur Administratoren können die Liquidität einsehen.', 'danger')
        return redirect(url_for('finanzen.index'))

    # TODO: Integration mit Banking-API
    # Aktuell nur Dummy-Daten

    return render_template('finanzen/liquiditaet.html')
