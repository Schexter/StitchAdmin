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
from src.models.rechnungsmodul.models import Rechnung, RechnungsStatus, RechnungsRichtung
from src.models.mahnwesen import Mahnung, MahnStatus, Ratenzahlung, Rate
from src.models.angebot import Angebot, AngebotStatus
from src.models.crm_activities import AngebotTracking, Activity

finanzen_bp = Blueprint('finanzen', __name__, url_prefix='/finanzen')


def _buchhaltung_required(f):
    """Dekorator: Nur Admin oder Buchhaltungs-Berechtigung"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if not current_user.is_admin:
            # Prüfe ModulePermission für 'finanzen'
            try:
                from src.models.user_permissions import ModulePermission
                perm = ModulePermission.query.filter_by(
                    user_id=current_user.id, module_name='finanzen', revoked_at=None
                ).first()
                if not perm or not perm.can_view:
                    flash('Zugriff verweigert. Nur Buchhaltung/Admin.', 'danger')
                    return redirect(url_for('dashboard'))
            except Exception:
                flash('Zugriff verweigert. Nur Admin.', 'danger')
                return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


def _berechne_offene_posten(rechnungen_query, heute, in_7_tagen, in_30_tagen):
    """Hilfsfunktion: Berechnet offene Posten für eine Rechnungsliste"""
    rechnungen = rechnungen_query.all()
    gesamt = Decimal('0.0')
    ueberfaellig = Decimal('0.0')
    faellig_7 = Decimal('0.0')
    faellig_30 = Decimal('0.0')
    ueberfaellige = []

    for r in rechnungen:
        betrag = Decimal(str(r.offener_betrag or 0))
        gesamt += betrag
        if not r.faelligkeitsdatum:
            continue
        if r.faelligkeitsdatum < heute:
            ueberfaellig += betrag
            ueberfaellige.append(r)
        elif r.faelligkeitsdatum <= in_7_tagen:
            faellig_7 += betrag
        elif r.faelligkeitsdatum <= in_30_tagen:
            faellig_30 += betrag

    return {
        'gesamt': gesamt, 'ueberfaellig': ueberfaellig,
        'faellig_7': faellig_7, 'faellig_30': faellig_30,
        'ueberfaellige': ueberfaellige, 'alle': rechnungen,
    }


@finanzen_bp.route('/')
@login_required
@_buchhaltung_required
def index():
    """Finanzen-Hauptübersicht"""

    heute = date.today()
    in_7_tagen = heute + timedelta(days=7)
    in_30_tagen = heute + timedelta(days=30)

    # ========== FORDERUNGEN (Ausgangsrechnungen = Kunden schulden uns) ==========
    forderungen = _berechne_offene_posten(
        Rechnung.query.filter(
            Rechnung.status.in_([RechnungsStatus.OFFEN, RechnungsStatus.TEILBEZAHLT]),
            Rechnung.richtung == RechnungsRichtung.AUSGANG
        ), heute, in_7_tagen, in_30_tagen
    )

    # ========== VERBINDLICHKEITEN (Eingangsrechnungen = Wir schulden Lieferanten) ==========
    verbindlichkeiten = _berechne_offene_posten(
        Rechnung.query.filter(
            Rechnung.status.in_([RechnungsStatus.OFFEN, RechnungsStatus.TEILBEZAHLT]),
            Rechnung.richtung == RechnungsRichtung.EINGANG
        ), heute, in_7_tagen, in_30_tagen
    )

    # ========== MAHNWESEN ==========
    mahnungen_1 = Mahnung.query.filter_by(mahnstufe=1, status=MahnStatus.VERSENDET).count()
    mahnungen_2 = Mahnung.query.filter_by(mahnstufe=2, status=MahnStatus.VERSENDET).count()
    mahnungen_3 = Mahnung.query.filter_by(mahnstufe=3, status=MahnStatus.VERSENDET).count()

    mahnungen_gesamt = Mahnung.query.filter_by(status=MahnStatus.VERSENDET).all()
    mahngebuehren_gesamt = sum(Decimal(str(m.mahngebuehr or 0)) for m in mahnungen_gesamt)
    verzugszinsen_gesamt = sum(Decimal(str(m.verzugszinsen or 0)) for m in mahnungen_gesamt)

    # Inkasso-Fälle
    inkasso_count = Mahnung.query.filter(
        Mahnung.status.in_([MahnStatus.INKASSO, MahnStatus.GERICHTLICH])
    ).count()
    inkasso_faelle = Mahnung.query.filter(
        Mahnung.status.in_([MahnStatus.INKASSO, MahnStatus.GERICHTLICH])
    ).order_by(Mahnung.mahndatum.desc()).limit(10).all()

    # Nächste Mahnungen (automatischer Mahnlauf)
    naechste_mahnungen = []
    for rechnung in forderungen['ueberfaellige']:
        tage_ueberfaellig = (heute - rechnung.faelligkeitsdatum).days

        letzte_mahnung = Mahnung.query.filter_by(
            rechnung_id=rechnung.id
        ).order_by(Mahnung.mahnstufe.desc()).first()

        if not letzte_mahnung and tage_ueberfaellig >= 7:
            naechste_mahnungen.append({
                'rechnung': rechnung,
                'mahnstufe': 1,
                'grund': f'{tage_ueberfaellig} Tage überfällig'
            })
        elif letzte_mahnung and letzte_mahnung.status == MahnStatus.VERSENDET:
            tage_seit_mahnung = (heute - letzte_mahnung.versanddatum).days if letzte_mahnung.versanddatum else 0
            if tage_seit_mahnung >= 14 and letzte_mahnung.mahnstufe < 3:
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
    raten_ueberfaellig = []

    for rz in ratenzahlungen_aktiv:
        raten_gesamt_offen += Decimal(str(rz.offener_betrag))

        for rate in rz.raten:
            if rate.status == 'offen':
                if rate.faelligkeitsdatum < heute:
                    raten_ueberfaellig.append(rate)
                elif rate.faelligkeitsdatum == heute:
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
        if hasattr(angebot, 'tracking') and angebot.tracking:
            chance = Decimal(str(angebot.tracking.verkaufschance_prozent or 50)) / Decimal('100')
            gewichteter_umsatz += Decimal(str(angebot.brutto_gesamt or 0)) * chance
        else:
            gewichteter_umsatz += Decimal(str(angebot.brutto_gesamt or 0)) * Decimal('0.5')

    # ========== UMSATZ (letzten 30 Tage) ==========
    vor_30_tagen = heute - timedelta(days=30)

    ausgang_30_tage = Rechnung.query.filter(
        Rechnung.rechnungsdatum >= vor_30_tagen,
        Rechnung.richtung == RechnungsRichtung.AUSGANG
    ).all()
    umsatz_30_tage = sum(Decimal(str(r.brutto_gesamt or 0)) for r in ausgang_30_tage)
    zahlungseingang_30_tage = sum(Decimal(str(r.bezahlt_betrag or 0)) for r in ausgang_30_tage)

    eingang_30_tage = Rechnung.query.filter(
        Rechnung.rechnungsdatum >= vor_30_tagen,
        Rechnung.richtung == RechnungsRichtung.EINGANG
    ).all()
    ausgaben_30_tage = sum(Decimal(str(r.brutto_gesamt or 0)) for r in eingang_30_tage)

    # ========== LIQUIDITÄT ==========
    liquiditaet = {
        'liquide_mittel': float(zahlungseingang_30_tage),
        'forderungen': float(forderungen['gesamt']),
        'verbindlichkeiten': float(verbindlichkeiten['gesamt']),
        'liquiditaetsgrad': float(
            (zahlungseingang_30_tage / verbindlichkeiten['gesamt'] * 100)
            if verbindlichkeiten['gesamt'] > 0 else 0
        )
    }

    # ========== WIEDERKEHRENDE KOSTEN (Verträge) ==========
    vertrag_monatlich = Decimal('0.0')
    vertrag_jaehrlich = Decimal('0.0')
    vertraege_bald_faellig = []
    vertraege_kuendigung = []
    try:
        from src.models.contracts import Contract
        aktive_vertraege = Contract.query.filter_by(status='active').all()
        for v in aktive_vertraege:
            vertrag_monatlich += Decimal(str(v.monthly_cost or 0))
            vertrag_jaehrlich += Decimal(str(v.yearly_cost or 0))
            if v.is_expiring_soon:
                vertraege_bald_faellig.append(v)
            if v.is_renewal_due:
                vertraege_kuendigung.append(v)
    except Exception:
        aktive_vertraege = []

    # ========== NEUESTE AKTIVITÄTEN ==========
    neueste_aktivitaeten = Activity.query.filter(
        Activity.activity_type.in_(['angebot_versendet', 'angebot_nachfrage', 'angebot_angenommen', 'angebot_abgelehnt'])
    ).order_by(Activity.created_at.desc()).limit(10).all()

    return render_template('finanzen/index.html',
                         # Forderungen (Ausgang)
                         forderungen_gesamt=float(forderungen['gesamt']),
                         forderungen_ueberfaellig=float(forderungen['ueberfaellig']),
                         forderungen_faellig_7_tage=float(forderungen['faellig_7']),
                         forderungen_faellig_30_tage=float(forderungen['faellig_30']),
                         ueberfaellige_rechnungen=forderungen['ueberfaellige'][:10],
                         # Verbindlichkeiten (Eingang)
                         verbindlichkeiten_gesamt=float(verbindlichkeiten['gesamt']),
                         verbindlichkeiten_ueberfaellig=float(verbindlichkeiten['ueberfaellig']),
                         verbindlichkeiten_faellig_7=float(verbindlichkeiten['faellig_7']),
                         verbindlichkeiten_faellig_30=float(verbindlichkeiten['faellig_30']),
                         ueberfaellige_eingangsrechnungen=verbindlichkeiten['ueberfaellige'][:10],
                         # Mahnwesen
                         mahnungen_1=mahnungen_1,
                         mahnungen_2=mahnungen_2,
                         mahnungen_3=mahnungen_3,
                         mahngebuehren_gesamt=float(mahngebuehren_gesamt),
                         verzugszinsen_gesamt=float(verzugszinsen_gesamt),
                         naechste_mahnungen=naechste_mahnungen[:10],
                         # Inkasso
                         inkasso_count=inkasso_count,
                         inkasso_faelle=inkasso_faelle,
                         # Ratenzahlungen
                         ratenzahlungen_aktiv_count=len(ratenzahlungen_aktiv),
                         raten_gesamt_offen=float(raten_gesamt_offen),
                         raten_faellig_heute=raten_faellig_heute,
                         raten_faellig_woche=raten_faellig_woche,
                         raten_ueberfaellig=raten_ueberfaellig,
                         # Angebote
                         angebote_offen_count=len(angebote_offen),
                         angebote_follow_up_count=len(angebote_follow_up),
                         erwarteter_umsatz=float(erwarteter_umsatz),
                         gewichteter_umsatz=float(gewichteter_umsatz),
                         # Umsatz
                         umsatz_30_tage=float(umsatz_30_tage),
                         zahlungseingang_30_tage=float(zahlungseingang_30_tage),
                         ausgaben_30_tage=float(ausgaben_30_tage),
                         # Liquidität
                         liquiditaet=liquiditaet,
                         # Wiederkehrende Kosten (Verträge)
                         vertrag_monatlich=float(vertrag_monatlich),
                         vertrag_jaehrlich=float(vertrag_jaehrlich),
                         aktive_vertraege_count=len(aktive_vertraege) if aktive_vertraege else 0,
                         vertraege_bald_faellig=vertraege_bald_faellig,
                         vertraege_kuendigung=vertraege_kuendigung,
                         # Aktivitäten
                         neueste_aktivitaeten=neueste_aktivitaeten)


@finanzen_bp.route('/offene-posten')
@login_required
@_buchhaltung_required
def offene_posten():
    """Detaillierte Liste aller offenen Posten"""

    filter_status = request.args.get('status', 'alle')
    filter_kunde = request.args.get('kunde', '')
    filter_richtung = request.args.get('richtung', 'alle')
    sortierung = request.args.get('sort', 'faelligkeit')

    query = Rechnung.query.filter(
        Rechnung.status.in_([RechnungsStatus.OFFEN, RechnungsStatus.TEILBEZAHLT])
    )

    # Richtung filtern
    if filter_richtung == 'ausgang':
        query = query.filter(Rechnung.richtung == RechnungsRichtung.AUSGANG)
    elif filter_richtung == 'eingang':
        query = query.filter(Rechnung.richtung == RechnungsRichtung.EINGANG)

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
        query = query.filter(and_(
            Rechnung.faelligkeitsdatum >= heute,
            Rechnung.faelligkeitsdatum <= heute + timedelta(days=7)
        ))
    elif filter_status == 'faellig_30_tage':
        query = query.filter(and_(
            Rechnung.faelligkeitsdatum > heute + timedelta(days=7),
            Rechnung.faelligkeitsdatum <= heute + timedelta(days=30)
        ))

    # Sortierung
    if sortierung == 'betrag':
        query = query.order_by(Rechnung.brutto_gesamt.desc())
    elif sortierung == 'kunde':
        query = query.order_by(Rechnung.kunde_name)
    else:
        query = query.order_by(Rechnung.faelligkeitsdatum)

    rechnungen = query.all()
    gesamt_forderung = sum(Decimal(str(r.offener_betrag or 0)) for r in rechnungen)

    return render_template('finanzen/offene_posten.html',
                         rechnungen=rechnungen,
                         gesamt_forderung=float(gesamt_forderung),
                         filter_status=filter_status,
                         filter_kunde=filter_kunde,
                         filter_richtung=filter_richtung,
                         sortierung=sortierung)


@finanzen_bp.route('/mahnungen')
@login_required
@_buchhaltung_required
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


@finanzen_bp.route('/mahnung/wizard')
@finanzen_bp.route('/mahnung/wizard/<int:rechnung_id>')
@login_required
@_buchhaltung_required
def mahnung_wizard(rechnung_id=None):
    """Mahnungs-Wizard: Ueberfaellige Rechnung waehlen -> Mahnstufe -> Erstellen"""
    from src.models.rechnungsmodul import RechnungsStatus

    # Alle ueberfaelligen Rechnungen laden
    today = date.today()
    ueberfaellige = Rechnung.query.filter(
        Rechnung.richtung == 'ausgang',
        Rechnung.status.in_([RechnungsStatus.VERSENDET, RechnungsStatus.UEBERFAELLIG, RechnungsStatus.TEILBEZAHLT]),
        Rechnung.faelligkeitsdatum < today
    ).order_by(Rechnung.faelligkeitsdatum).all()

    selected_rechnung = None
    letzte_mahnung_obj = None
    naechste_stufe = 1
    vorschau = {}

    if rechnung_id:
        selected_rechnung = Rechnung.query.get_or_404(rechnung_id)

        # Letzte Mahnung fuer diese Rechnung
        letzte_mahnung_obj = Mahnung.query.filter_by(
            rechnung_id=rechnung_id
        ).order_by(Mahnung.mahnstufe.desc()).first()

        naechste_stufe = 1 if not letzte_mahnung_obj else letzte_mahnung_obj.mahnstufe + 1

        # Vorschau berechnen
        tage_ueberfaellig = (today - selected_rechnung.faelligkeitsdatum).days if selected_rechnung.faelligkeitsdatum else 0
        offener_betrag = float(selected_rechnung.brutto_gesamt or 0)

        gebuehren_staffel = {1: 5.0, 2: 10.0, 3: 15.0}
        mahngebuehr = gebuehren_staffel.get(naechste_stufe, 15.0)

        # Verzugszinsen (5% p.a. Privat, 9% p.a. Geschaeft)
        zinssatz = 0.09 if getattr(selected_rechnung, 'kunde_ust_id', None) else 0.05
        verzugszinsen = round(offener_betrag * zinssatz * tage_ueberfaellig / 365, 2)

        vorschau = {
            'tage_ueberfaellig': tage_ueberfaellig,
            'offener_betrag': offener_betrag,
            'mahngebuehr': mahngebuehr,
            'verzugszinsen': verzugszinsen,
            'gesamtforderung': round(offener_betrag + mahngebuehr + verzugszinsen, 2),
            'zahlungsfrist_tage': 7 if naechste_stufe <= 2 else 5,
        }

    return render_template('finanzen/mahnung_wizard.html',
        ueberfaellige=ueberfaellige,
        selected_rechnung=selected_rechnung,
        letzte_mahnung=letzte_mahnung_obj,
        naechste_stufe=naechste_stufe,
        vorschau=vorschau,
        today=today)


@finanzen_bp.route('/mahnung/erstellen/<int:rechnung_id>', methods=['POST'])
@login_required
@_buchhaltung_required
def mahnung_erstellen(rechnung_id):
    """Erstellt eine neue Mahnung"""

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


@finanzen_bp.route('/inkasso/<int:mahnung_id>', methods=['POST'])
@login_required
@_buchhaltung_required
def inkasso_einleiten(mahnung_id):
    """Mahnung an Inkasso übergeben"""
    mahnung = Mahnung.query.get_or_404(mahnung_id)

    if mahnung.mahnstufe < 3:
        flash('Inkasso erst nach 3. Mahnung möglich.', 'warning')
        return redirect(url_for('finanzen.mahnungen'))

    mahnung.status = MahnStatus.INKASSO
    mahnung.bemerkungen = (mahnung.bemerkungen or '') + f'\n[{date.today()}] An Inkasso übergeben von {current_user.username}'
    db.session.commit()

    flash(f'Rechnung {mahnung.rechnung.rechnungsnummer} an Inkasso übergeben.', 'info')
    return redirect(url_for('finanzen.mahnungen'))


@finanzen_bp.route('/ratenzahlungen')
@login_required
@_buchhaltung_required
def ratenzahlungen():
    """Ratenzahlungs-Übersicht"""

    ratenzahlungen = Ratenzahlung.query.filter_by(status='aktiv').all()

    return render_template('finanzen/ratenzahlungen.html',
                         ratenzahlungen=ratenzahlungen)


@finanzen_bp.route('/bwa')
@login_required
@_buchhaltung_required
def bwa():
    """Betriebswirtschaftliche Auswertung (BWA) - Monatsübersicht"""
    import calendar

    heute = date.today()
    jahr = int(request.args.get('jahr', heute.year))

    monate_labels = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun',
                     'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']

    monate = []
    umsatz_gesamt = Decimal('0')
    kosten_gesamt = Decimal('0')

    for monat in range(1, 13):
        _, letzter_tag = calendar.monthrange(jahr, monat)
        start = date(jahr, monat, 1)
        ende = date(jahr, monat, letzter_tag)

        umsatz_rechnungen = Rechnung.query.filter(
            Rechnung.richtung == RechnungsRichtung.AUSGANG,
            Rechnung.status.notin_([RechnungsStatus.ENTWURF]),
            Rechnung.rechnungsdatum >= start,
            Rechnung.rechnungsdatum <= ende
        ).all()
        umsatz_netto = sum(Decimal(str(r.netto_gesamt or 0)) for r in umsatz_rechnungen)
        umsatz_brutto = sum(Decimal(str(r.brutto_gesamt or 0)) for r in umsatz_rechnungen)
        umsatz_mwst = umsatz_brutto - umsatz_netto

        eingang_rechnungen = Rechnung.query.filter(
            Rechnung.richtung == RechnungsRichtung.EINGANG,
            Rechnung.status.notin_([RechnungsStatus.ENTWURF]),
            Rechnung.rechnungsdatum >= start,
            Rechnung.rechnungsdatum <= ende
        ).all()
        kosten_netto = sum(Decimal(str(r.netto_gesamt or 0)) for r in eingang_rechnungen)

        rohertrag = umsatz_netto - kosten_netto

        monate.append({
            'monat': monat,
            'label': monate_labels[monat - 1],
            'umsatz_netto': float(umsatz_netto),
            'umsatz_brutto': float(umsatz_brutto),
            'umsatz_mwst': float(umsatz_mwst),
            'kosten_netto': float(kosten_netto),
            'rohertrag': float(rohertrag),
            'anzahl_rechnungen': len(umsatz_rechnungen),
            'anzahl_eingang': len(eingang_rechnungen),
            'ist_leer': umsatz_netto == 0 and kosten_netto == 0,
        })
        umsatz_gesamt += umsatz_netto
        kosten_gesamt += kosten_netto

    erste_rechnung = Rechnung.query.order_by(Rechnung.rechnungsdatum).first()
    start_jahr = erste_rechnung.rechnungsdatum.year if erste_rechnung else heute.year
    verfuegbare_jahre = list(range(start_jahr, heute.year + 1))

    return render_template('finanzen/bwa.html',
                         jahr=jahr,
                         monate=monate,
                         monate_labels=monate_labels,
                         umsatz_gesamt=float(umsatz_gesamt),
                         kosten_gesamt=float(kosten_gesamt),
                         rohertrag_gesamt=float(umsatz_gesamt - kosten_gesamt),
                         verfuegbare_jahre=verfuegbare_jahre)


@finanzen_bp.route('/liquiditaet')
@login_required
@_buchhaltung_required
def liquiditaet():
    """Liquiditäts-Übersicht"""

    return render_template('finanzen/liquiditaet.html')
