# -*- coding: utf-8 -*-
"""
RECHNUNGS-CONTROLLER - ZUGPFERD-konforme Rechnungserstellung
===========================================================

Erstellt von: Hans Hahn - Alle Rechte vorbehalten
Datum: 09. Juli 2025
Zweck: Flask-Controller für ZUGPFERD-Rechnungssystem

Features:
- ZUGPFERD-Rechnungserstellung
- PDF/XML-Hybrid-Download
- E-Mail-Versand
- Rechnungsübersicht
- Zahlungserfassung
"""

import json
from datetime import datetime, date, timedelta
from decimal import Decimal
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file
import io

# Imports für Models und Services
try:
    from src.models import db
    from src.models.models import Customer, Order
    from src.models.rechnungsmodul import (
        Rechnung, RechnungsPosition, RechnungsStatus, ZugpferdProfil, RechnungsRichtung
    )
    from src.services.zugpferd_service import ZugpferdService
    from src.services.pdf_service import PDFService
    from flask_login import current_user

    # Utility-Klasse für Rechnungen
    class RechnungsUtils:
        @staticmethod
        def get_next_draft_number():
            """Arbeitsnummer für Entwürfe (ENT-YYYYMM-XXXX) - wird bei Versenden ersetzt"""
            now = datetime.now()
            pattern = f"ENT-{now.year:04d}{now.month:02d}-%"
            existing = Rechnung.query.filter(
                Rechnung.rechnungsnummer.like(pattern)
            ).order_by(Rechnung.rechnungsnummer.desc()).first()
            last_num = 0
            if existing:
                try:
                    last_num = int(existing.rechnungsnummer.rsplit('-', 1)[-1])
                except (ValueError, IndexError):
                    pass
            return f"ENT-{now.year:04d}{now.month:02d}-{last_num + 1:04d}"

        @staticmethod
        def get_next_invoice_number():
            """Echte Rechnungsnummer (RE-YYYYMM-XXXX) - nur für finalisierte Rechnungen"""
            now = datetime.now()
            pattern = f"RE-{now.year:04d}{now.month:02d}-%"
            existing = Rechnung.query.filter(
                Rechnung.rechnungsnummer.like(pattern)
            ).order_by(Rechnung.rechnungsnummer.desc()).first()
            last_num = 0
            if existing:
                try:
                    last_num = int(existing.rechnungsnummer.rsplit('-', 1)[-1])
                except (ValueError, IndexError):
                    pass
            return f"RE-{now.year:04d}{now.month:02d}-{last_num + 1:04d}"

except ImportError as e:
    print(f"Import-Fehler: {e}")
    db = None
    Customer = None
    Order = None
    Rechnung = None

import logging
logger = logging.getLogger(__name__)

# Blueprint erstellen
rechnung_bp = Blueprint('rechnung', __name__, url_prefix='/rechnung')

@rechnung_bp.route('/')
def rechnungs_index():
    """
    Rechnungsübersicht
    Zeigt alle Rechnungen mit Filter- und Suchfunktionen, getrennt nach Eingang/Ausgang
    """
    try:
        from datetime import date

        # Filter-Parameter
        status_filter = request.args.get('status', '')
        customer_filter = request.args.get('customer', '')
        period_filter = request.args.get('period', '')
        tab = request.args.get('tab', 'ausgang')  # Standard: Ausgangsrechnungen

        # Basis-Query für Ausgangsrechnungen
        ausgangsrechnungen = []
        eingangsrechnungen = []

        if db:
            try:
                # Ausgangsrechnungen (an Kunden)
                ausgang_query = Rechnung.query.filter(
                    db.or_(
                        Rechnung.richtung == RechnungsRichtung.AUSGANG,
                        Rechnung.richtung == None  # Alte Rechnungen ohne Richtung
                    )
                )

                # Eingangsrechnungen (von Lieferanten)
                eingang_query = Rechnung.query.filter(
                    Rechnung.richtung == RechnungsRichtung.EINGANG
                )

                # Standard: nur offene Rechnungen; bei Filter: gefiltert
                if status_filter:
                    ausgang_query = ausgang_query.filter_by(status=status_filter)
                    eingang_query = eingang_query.filter_by(status=status_filter)
                else:
                    ausgang_query = ausgang_query.filter(
                        Rechnung.status.in_([RechnungsStatus.OFFEN, RechnungsStatus.TEILBEZAHLT])
                    )
                    eingang_query = eingang_query.filter(
                        Rechnung.status.in_([RechnungsStatus.OFFEN, RechnungsStatus.TEILBEZAHLT])
                    )

                # Zeitraum-Filter anwenden
                if period_filter:
                    today = date.today()
                    date_filter = None
                    if period_filter == 'today':
                        date_filter = db.func.date(Rechnung.rechnungsdatum) == today
                    elif period_filter == 'week':
                        week_start = today - timedelta(days=today.weekday())
                        date_filter = Rechnung.rechnungsdatum >= week_start
                    elif period_filter == 'month':
                        month_start = today.replace(day=1)
                        date_filter = Rechnung.rechnungsdatum >= month_start
                    elif period_filter == 'year':
                        year_start = today.replace(month=1, day=1)
                        date_filter = Rechnung.rechnungsdatum >= year_start

                    if date_filter is not None:
                        ausgang_query = ausgang_query.filter(date_filter)
                        eingang_query = eingang_query.filter(date_filter)

                ausgangsrechnungen = ausgang_query.order_by(Rechnung.rechnungsdatum.desc()).all()
                eingangsrechnungen = eingang_query.order_by(Rechnung.rechnungsdatum.desc()).all()
            except Exception as db_error:
                logger.error(f"Datenbankfehler: {db_error}")

        # Statistiken für Ausgangsrechnungen berechnen
        today = date.today()
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)

        # Offene Ausgangsrechnungen
        ausgang_offen = [r for r in ausgangsrechnungen if r.status in [RechnungsStatus.OFFEN, RechnungsStatus.ENTWURF]]
        ausgang_offen_count = len(ausgang_offen)
        ausgang_offen_total = sum(float(r.brutto_gesamt or 0) for r in ausgang_offen)

        # Überfällige Ausgangsrechnungen
        ausgang_ueberfaellig = [r for r in ausgangsrechnungen
                               if r.status == RechnungsStatus.OFFEN
                               and r.faelligkeitsdatum
                               and r.faelligkeitsdatum < today]
        ausgang_ueberfaellig_count = len(ausgang_ueberfaellig)
        ausgang_ueberfaellig_total = sum(float(r.brutto_gesamt or 0) for r in ausgang_ueberfaellig)

        # Bezahlte diesen Monat
        ausgang_bezahlt = [r for r in ausgangsrechnungen
                          if r.status == RechnungsStatus.BEZAHLT
                          and r.bezahlt_am
                          and r.bezahlt_am >= month_start]
        ausgang_bezahlt_count = len(ausgang_bezahlt)
        ausgang_bezahlt_total = sum(float(r.brutto_gesamt or 0) for r in ausgang_bezahlt)

        # Statistiken für Eingangsrechnungen
        eingang_offen = [r for r in eingangsrechnungen if r.status in [RechnungsStatus.OFFEN, RechnungsStatus.ENTWURF]]
        eingang_offen_count = len(eingang_offen)
        eingang_offen_total = sum(float(r.brutto_gesamt or 0) for r in eingang_offen)

        return render_template('rechnung/index.html',
            ausgangsrechnungen=ausgangsrechnungen,
            eingangsrechnungen=eingangsrechnungen,
            tab=tab,
            # Statistiken Ausgang
            ausgang_offen_count=ausgang_offen_count,
            ausgang_offen_total=ausgang_offen_total,
            ausgang_ueberfaellig_count=ausgang_ueberfaellig_count,
            ausgang_ueberfaellig_total=ausgang_ueberfaellig_total,
            ausgang_bezahlt_count=ausgang_bezahlt_count,
            ausgang_bezahlt_total=ausgang_bezahlt_total,
            ausgang_total_count=len(ausgangsrechnungen),
            # Statistiken Eingang
            eingang_offen_count=eingang_offen_count,
            eingang_offen_total=eingang_offen_total,
            eingang_total_count=len(eingangsrechnungen),
            # Alte Variablen für Kompatibilität
            rechnungen=ausgangsrechnungen if tab == 'ausgang' else eingangsrechnungen,
            open_invoices_count=ausgang_offen_count,
            open_invoices_total=ausgang_offen_total,
            overdue_invoices_count=ausgang_ueberfaellig_count,
            overdue_invoices_total=ausgang_ueberfaellig_total,
            paid_this_month_count=ausgang_bezahlt_count,
            paid_this_month_total=ausgang_bezahlt_total,
            year_total_count=len(ausgangsrechnungen),
            year_total_amount=sum(float(r.brutto_gesamt or 0) for r in ausgangsrechnungen)
        )

    except Exception as e:
        logger.error(f"Fehler in rechnungs_index: {str(e)}")
        flash(f"Fehler beim Laden der Rechnungsübersicht: {str(e)}", "error")
        return render_template('rechnung/index.html',
            ausgangsrechnungen=[],
            eingangsrechnungen=[],
            rechnungen=[],
            tab='ausgang',
            ausgang_offen_count=0,
            ausgang_offen_total=0,
            ausgang_ueberfaellig_count=0,
            ausgang_ueberfaellig_total=0,
            ausgang_bezahlt_count=0,
            ausgang_bezahlt_total=0,
            ausgang_total_count=0,
            eingang_offen_count=0,
            eingang_offen_total=0,
            eingang_total_count=0,
            open_invoices_count=0,
            open_invoices_total=0,
            overdue_invoices_count=0,
            overdue_invoices_total=0,
            paid_this_month_count=0,
            paid_this_month_total=0,
            year_total_count=0,
            year_total_amount=0
        )

@rechnung_bp.route('/neu')
def neue_rechnung():
    """
    Formular für neue Rechnung anzeigen
    """
    try:
        # Nächste Rechnungsnummer generieren
        naechste_nummer = RechnungsUtils.get_next_invoice_number()
        
        # ZUGPFERD-Profile
        zugpferd_profile = [
            {'value': 'MINIMUM', 'label': 'Minimum (nur Grunddaten)'},
            {'value': 'BASIC', 'label': 'Basic (Standard)'},
            {'value': 'COMFORT', 'label': 'Comfort (erweitert)'},
            {'value': 'EXTENDED', 'label': 'Extended (vollständig)'}
        ]
        
        # MwSt-Sätze (temporär)
        mwst_saetze = [
            {'id': 1, 'bezeichnung': 'Normalsteuersatz', 'satz': 19.0},
            {'id': 2, 'bezeichnung': 'Ermäßigter Steuersatz', 'satz': 7.0},
            {'id': 3, 'bezeichnung': 'Steuerfreie Lieferung', 'satz': 0.0}
        ]
        
        # Kunde vorausfuellen wenn ?kunde_id= angegeben
        pre_kunde = None
        pre_kunde_id = request.args.get('kunde_id')
        if pre_kunde_id:
            pre_kunde = Customer.query.get(pre_kunde_id)

        return render_template('rechnung/neue_rechnung.html',
            naechste_nummer=naechste_nummer,
            zugpferd_profile=zugpferd_profile,
            mwst_saetze=mwst_saetze,
            page_title="Neue Rechnung erstellen",
            today=date.today().isoformat(),
            pre_kunde=pre_kunde
        )
        
    except Exception as e:
        logger.error(f"Fehler beim Anzeigen des Rechnungsformulars: {str(e)}")
        flash(f"Fehler beim Laden des Formulars: {str(e)}", "error")
        return redirect(url_for('rechnung.rechnungs_index'))

@rechnung_bp.route('/neu', methods=['POST'])
def rechnung_erstellen():
    """
    Neue Rechnung erstellen
    """
    try:
        # Formulardaten auslesen
        kunde_id = request.form.get('kunde_id')
        rechnungsdatum = datetime.strptime(request.form.get('rechnungsdatum'), '%Y-%m-%d').date() if request.form.get('rechnungsdatum') else date.today()
        leistungsdatum = datetime.strptime(request.form.get('leistungsdatum'), '%Y-%m-%d').date() if request.form.get('leistungsdatum') else rechnungsdatum
        zahlungsbedingungen = request.form.get('zahlungsbedingungen', 'Zahlbar innerhalb 14 Tagen')
        zugpferd_profil = request.form.get('zugpferd_profil', 'BASIC')
        bemerkungen = request.form.get('bemerkungen', '')

        # Kunde laden
        kunde = Customer.query.get(kunde_id)
        if not kunde:
            flash("Kunde nicht gefunden!", "error")
            return redirect(url_for('rechnung.neue_rechnung'))

        # Rechnung erstellen
        rechnung = Rechnung(
            richtung=RechnungsRichtung.AUSGANG,
            kunde_id=kunde_id,
            kunde_name=kunde.display_name,
            kunde_adresse=f"{kunde.street} {kunde.house_number}\n{kunde.postal_code} {kunde.city}".strip(),
            kunde_email=kunde.email,
            kunde_steuernummer=kunde.tax_id,
            kunde_ust_id=kunde.vat_id,
            rechnungsdatum=rechnungsdatum,
            leistungsdatum=leistungsdatum,
            zahlungsbedingungen=zahlungsbedingungen,
            zugpferd_profil=ZugpferdProfil[zugpferd_profil],
            bemerkungen=bemerkungen,
            status=RechnungsStatus.ENTWURF,
            erstellt_von=current_user.username if current_user.is_authenticated else 'System'
        )

        # Positionen verarbeiten (is_header Zeilen überspringen)
        positionen_data = json.loads(request.form.get('positionen', '[]'))
        pos_idx = 1
        for pos_data in positionen_data:
            if pos_data.get('is_header'):
                continue
            ep = pos_data.get('einzelpreis_netto') or pos_data.get('einzelpreis', 0)
            position = RechnungsPosition(
                position=pos_idx,
                artikel_name=pos_data.get('artikel_name', ''),
                beschreibung=pos_data.get('beschreibung', ''),
                menge=Decimal(str(pos_data.get('menge', 1))),
                einheit=pos_data.get('einheit', 'Stück'),
                einzelpreis=Decimal(str(ep)),
                mwst_satz=Decimal(str(pos_data.get('mwst_satz', 19))),
                rabatt_prozent=Decimal(str(pos_data.get('rabatt_prozent', 0)))
            )
            position.calculate_amounts()
            rechnung.positionen.append(position)
            pos_idx += 1

        # Gesamtsummen berechnen
        rechnung.calculate_totals()

        # In DB speichern
        db.session.add(rechnung)
        db.session.flush()  # ID vergeben ohne commit

        # Aufträge verknüpfen (aus aus_auftrag_erstellen.html)
        auftrag_ids = request.form.getlist('auftrag_id')
        if auftrag_ids:
            linked_orders = Order.query.filter(Order.id.in_(auftrag_ids)).all()
            for o in linked_orders:
                o.invoice_id = rechnung.id
                o.workflow_status = 'invoiced'

        db.session.commit()

        logger.info(f"Rechnung {rechnung.rechnungsnummer} erfolgreich erstellt")
        flash(f"Rechnung {rechnung.rechnungsnummer} wurde erfolgreich erstellt!", "success")
        return redirect(url_for('rechnung.rechnung_detail', rechnung_id=rechnung.id))

    except Exception as e:
        db.session.rollback()
        logger.error(f"Fehler beim Erstellen der Rechnung: {str(e)}")
        flash(f"Fehler beim Erstellen der Rechnung: {str(e)}", "error")
        return redirect(url_for('rechnung.neue_rechnung'))

@rechnung_bp.route('/<int:rechnung_id>')
def rechnung_detail(rechnung_id):
    """
    Einzelne Rechnung anzeigen
    """
    try:
        rechnung = Rechnung.query.get_or_404(rechnung_id)

        # Alle verknüpften Aufträge (über Order.invoice_id)
        verknuepfte_auftraege = Order.query.filter_by(invoice_id=rechnung_id).all()

        from datetime import date as date_cls
        return render_template('rechnung/detail.html',
            rechnung=rechnung,
            verknuepfte_auftraege=verknuepfte_auftraege,
            today=date_cls.today(),
            page_title=f"Rechnung {rechnung.rechnungsnummer}"
        )

    except Exception as e:
        logger.error(f"Fehler beim Anzeigen der Rechnung: {str(e)}")
        flash(f"Fehler beim Laden der Rechnung: {str(e)}", "error")
        return redirect(url_for('rechnung.rechnungs_index'))

def _build_rechnung_positionen(orders):
    """Baut Rechnungspositionen aus einer Liste von Auftraegen.
    Enthaelt: Artikel (OrderItems), Veredelung (OrderDesign), design_cost, adaptation_cost.
    Returns: (positionen, netto_gesamt, mwst_gesamt)
    """
    from src.models.order_workflow import OrderDesign
    VEREDELUNG_LABELS = {
        'embroidery': 'Stickerei', 'printing': 'Druck', 'dtf': 'DTF-Druck',
        'sublimation': 'Sublimation', 'combined': 'Kombi-Veredelung'
    }
    positionen = []
    netto_gesamt = Decimal('0')
    mwst_gesamt = Decimal('0')
    pos_idx = 1

    for order in orders:
        # Bei mehreren Auftraegen: Kopfzeile pro Auftrag
        if len(orders) > 1:
            positionen.append({
                'position': pos_idx,
                'artikel_name': f'Auftrag {order.order_number or order.id}',
                'beschreibung': order.description or '',
                'menge': 1, 'einheit': 'pauschal',
                'einzelpreis_netto': 0, 'mwst_satz': 0,
                'netto_betrag': 0, 'mwst_betrag': 0, 'brutto_betrag': 0,
                'is_header': True, 'order_id': order.id
            })
            pos_idx += 1

        total_qty = 0
        # 1. Artikel / OrderItems
        items = order.items.all() if hasattr(order.items, 'all') else list(order.items)
        for item in items:
            einzelpreis = Decimal(str(item.unit_price or 0))
            menge = Decimal(str(item.quantity or 1))
            total_qty += int(item.quantity or 1)
            netto = einzelpreis * menge
            mwst = netto * Decimal('0.19')
            netto_gesamt += netto
            mwst_gesamt += mwst
            positionen.append({
                'position': pos_idx,
                'artikel_id': item.article_id,
                'artikel_name': item.article.name if item.article else f'Position {pos_idx}',
                'beschreibung': item.position_details or '',
                'menge': float(menge), 'einheit': 'Stück',
                'einzelpreis_netto': float(einzelpreis), 'mwst_satz': 19,
                'netto_betrag': float(netto), 'mwst_betrag': float(mwst),
                'brutto_betrag': float(netto + mwst), 'is_header': False
            })
            pos_idx += 1

        total_qty = max(total_qty, 1)

        # 2. Veredelung aus OrderDesign
        designs = OrderDesign.query.filter_by(order_id=order.id).all()
        for design in designs:
            setup = Decimal(str(design.setup_price or 0))
            per_piece = Decimal(str(design.price_per_piece or 0)) * total_qty
            veredelung_total = setup + per_piece
            if veredelung_total > 0:
                label = VEREDELUNG_LABELS.get(order.order_type, 'Veredelung')
                netto = veredelung_total
                mwst = netto * Decimal('0.19')
                netto_gesamt += netto
                mwst_gesamt += mwst
                desc_parts = []
                if float(setup) > 0:
                    desc_parts.append(f'Einrichtung {float(setup):.2f}€')
                if float(design.price_per_piece or 0) > 0:
                    desc_parts.append(f'{float(design.price_per_piece):.2f}€ × {total_qty} Stück')
                positionen.append({
                    'position': pos_idx, 'artikel_name': label,
                    'beschreibung': ', '.join(desc_parts),
                    'menge': 1, 'einheit': 'pauschal',
                    'einzelpreis_netto': float(netto), 'mwst_satz': 19,
                    'netto_betrag': float(netto), 'mwst_betrag': float(mwst),
                    'brutto_betrag': float(netto + mwst), 'is_header': False
                })
                pos_idx += 1
            # Design-Erstellkosten (Lieferant)
            if design.supplier_cost and float(design.supplier_cost) > 0:
                netto = Decimal(str(design.supplier_cost))
                mwst = netto * Decimal('0.19')
                netto_gesamt += netto
                mwst_gesamt += mwst
                positionen.append({
                    'position': pos_idx, 'artikel_name': 'Design-Erstellung',
                    'beschreibung': '', 'menge': 1, 'einheit': 'pauschal',
                    'einzelpreis_netto': float(netto), 'mwst_satz': 19,
                    'netto_betrag': float(netto), 'mwst_betrag': float(mwst),
                    'brutto_betrag': float(netto + mwst), 'is_header': False
                })
                pos_idx += 1

        # 3. Design-Kosten / Anpassungskosten direkt am Auftrag
        for cost_field, label in [('design_cost', 'Design-Kosten'), ('adaptation_cost', 'Design-Anpassung')]:
            val = float(getattr(order, cost_field, None) or 0)
            if val > 0:
                netto = Decimal(str(val))
                mwst = netto * Decimal('0.19')
                netto_gesamt += netto
                mwst_gesamt += mwst
                positionen.append({
                    'position': pos_idx, 'artikel_name': label,
                    'beschreibung': '', 'menge': 1, 'einheit': 'pauschal',
                    'einzelpreis_netto': float(netto), 'mwst_satz': 19,
                    'netto_betrag': float(netto), 'mwst_betrag': float(mwst),
                    'brutto_betrag': float(netto + mwst), 'is_header': False
                })
                pos_idx += 1

    # 4. Proforma-Verrechnung: Bereits bezahlte Anzahlungen abziehen
    # Suche Proformas ueber Angebot-Verknuepfung
    angebot_ids = set()
    for order in orders:
        if hasattr(order, 'angebot_id') and order.angebot_id:
            angebot_ids.add(order.angebot_id)
        # Auch ueber Angebot.auftrag_id suchen
        try:
            from src.models.angebot import Angebot
            linked = Angebot.query.filter_by(auftrag_id=order.id).all()
            for a in linked:
                angebot_ids.add(a.id)
        except Exception:
            pass

    if angebot_ids:
        proformas = Rechnung.query.filter(
            Rechnung.rechnung_typ == 'proforma',
            Rechnung.angebot_id.in_(list(angebot_ids)),
            Rechnung.status.in_([RechnungsStatus.VERSENDET, RechnungsStatus.BEZAHLT])
        ).all()

        for prf in proformas:
            prf_betrag = Decimal(str(float(prf.brutto_gesamt or 0)))
            if prf_betrag > 0:
                prf_netto = Decimal(str(float(prf.netto_gesamt or 0)))
                prf_mwst = Decimal(str(float(prf.mwst_gesamt or 0)))
                netto_gesamt -= prf_netto
                mwst_gesamt -= prf_mwst
                positionen.append({
                    'position': pos_idx,
                    'artikel_name': f'abzgl. Anzahlung ({prf.rechnungsnummer})',
                    'beschreibung': f'Proforma-Rechnung vom {prf.rechnungsdatum.strftime("%d.%m.%Y") if prf.rechnungsdatum else ""}',
                    'menge': 1, 'einheit': 'pauschal',
                    'einzelpreis_netto': float(-prf_netto), 'mwst_satz': 19,
                    'netto_betrag': float(-prf_netto), 'mwst_betrag': float(-prf_mwst),
                    'brutto_betrag': float(-(prf_netto + prf_mwst)),
                    'is_header': False, 'is_proforma_abzug': True
                })
                pos_idx += 1

    return positionen, netto_gesamt, mwst_gesamt


ZUGPFERD_PROFILE = [
    {'value': 'MINIMUM', 'label': 'Minimum (einfachste Stufe)'},
    {'value': 'BASIC', 'label': 'Basic (Standard)'},
    {'value': 'COMFORT', 'label': 'Comfort (erweitert)'},
    {'value': 'EXTENDED', 'label': 'Extended (vollständig)'},
]


@rechnung_bp.route('/wizard')
@rechnung_bp.route('/wizard/<order_id>')
def rechnung_wizard(order_id=None):
    """Rechnungs-Wizard: Auftrag waehlen -> Positionen pruefen -> Rechnung erstellen"""
    try:
        # Alle abrechenbaren Auftraege laden
        abrechnbare = Order.query.filter(
            Order.status.in_(['accepted', 'in_progress', 'ready', 'completed'])
        ).order_by(Order.created_at.desc()).all()

        # Wenn order_id uebergeben: direkt Positionen bauen
        selected_order = None
        positionen = []
        netto_gesamt = 0
        mwst_gesamt = 0
        kunde = None

        if order_id:
            selected_order = Order.query.get_or_404(order_id)
            kunde = selected_order.get_billing_customer() if hasattr(selected_order, 'get_billing_customer') else None
            if not kunde and selected_order.customer_id:
                kunde = Customer.query.get(selected_order.customer_id)
            pos_data, ng, mg = _build_rechnung_positionen([selected_order])
            positionen = pos_data
            netto_gesamt = float(ng)
            mwst_gesamt = float(mg)

        return render_template('rechnung/wizard.html',
            auftraege=abrechnbare,
            selected_order=selected_order,
            kunde=kunde,
            positionen=positionen,
            netto_gesamt=netto_gesamt,
            mwst_gesamt=mwst_gesamt,
            brutto_gesamt=netto_gesamt + mwst_gesamt,
            naechste_nummer=RechnungsUtils.get_next_invoice_number(),
            zugpferd_profile=ZUGPFERD_PROFILE,
            today=date.today().isoformat()
        )
    except Exception as e:
        logger.error(f"Rechnungs-Wizard Fehler: {e}")
        flash(f"Fehler: {str(e)}", "error")
        return redirect(url_for('rechnung.rechnungs_index'))


# ==========================================
# PROFORMA-RECHNUNG (Anzahlung aus Angebot)
# ==========================================

@rechnung_bp.route('/proforma/angebot/<int:angebot_id>', methods=['GET', 'POST'])
def proforma_aus_angebot(angebot_id):
    """Proforma-Rechnung (Anzahlung) aus einem Angebot erstellen"""
    try:
        from src.models.angebot import Angebot
        angebot = Angebot.query.get_or_404(angebot_id)
        kunde = Customer.query.get(angebot.kunde_id) if angebot.kunde_id else None

        if request.method == 'POST':
            anzahlung_prozent = float(request.form.get('anzahlung_prozent', 50))
            netto = float(angebot.netto_gesamt or 0)
            anzahlung_netto = round(netto * anzahlung_prozent / 100, 2)
            anzahlung_mwst = round(anzahlung_netto * 0.19, 2)
            anzahlung_brutto = anzahlung_netto + anzahlung_mwst

            rechnungsdatum = date.today()
            zahlungsziel = int(request.form.get('zahlungsziel_tage', 7))
            faellig = rechnungsdatum + timedelta(days=zahlungsziel)

            # Proforma-Nummernkreis: PRF-YYYYMM-XXXX
            now = datetime.now()
            pattern = f"PRF-{now.year:04d}{now.month:02d}-%"
            existing = Rechnung.query.filter(
                Rechnung.rechnungsnummer.like(pattern)
            ).order_by(Rechnung.rechnungsnummer.desc()).first()
            last_num = 0
            if existing:
                try:
                    last_num = int(existing.rechnungsnummer.rsplit('-', 1)[-1])
                except (ValueError, IndexError):
                    pass
            proforma_nr = f"PRF-{now.year:04d}{now.month:02d}-{last_num + 1:04d}"

            rechnung = Rechnung(
                rechnungsnummer=proforma_nr,
                richtung=RechnungsRichtung.AUSGANG,
                rechnung_typ='proforma',
                angebot_id=angebot_id,
                kunde_id=angebot.kunde_id,
                kunde_name=angebot.kunde_name,
                kunde_adresse=angebot.kunde_adresse,
                kunde_email=angebot.kunde_email,
                rechnungsdatum=rechnungsdatum,
                leistungsdatum=rechnungsdatum,
                faelligkeitsdatum=faellig,
                netto_gesamt=anzahlung_netto,
                mwst_gesamt=anzahlung_mwst,
                brutto_gesamt=anzahlung_brutto,
                zahlungsbedingungen=f'Anzahlung zahlbar innerhalb {zahlungsziel} Tagen bis {faellig.strftime("%d.%m.%Y")}',
                bemerkungen=f'Proforma/Anzahlung ({anzahlung_prozent:.0f}%) zu Angebot {angebot.angebotsnummer}',
                status=RechnungsStatus.ENTWURF,
                erstellt_von=current_user.username if current_user.is_authenticated else 'System'
            )
            db.session.add(rechnung)
            db.session.flush()

            # Eine Position: Anzahlung
            pos = RechnungsPosition(
                rechnung_id=rechnung.id,
                position=1,
                artikel_name=f'Anzahlung ({anzahlung_prozent:.0f}%) zu Angebot {angebot.angebotsnummer}',
                beschreibung=angebot.titel or '',
                menge=Decimal('1'),
                einheit='pauschal',
                einzelpreis_netto=Decimal(str(anzahlung_netto)),
                mwst_satz=Decimal('19'),
                netto_betrag=Decimal(str(anzahlung_netto)),
                mwst_betrag=Decimal(str(anzahlung_mwst)),
                brutto_betrag=Decimal(str(anzahlung_brutto)),
            )
            db.session.add(pos)
            db.session.commit()

            flash(f'Proforma-Rechnung {proforma_nr} erstellt (Anzahlung {anzahlung_prozent:.0f}% = {anzahlung_brutto:.2f} EUR).', 'success')
            return redirect(url_for('rechnung.rechnung_detail', rechnung_id=rechnung.id))

        # GET: Formular anzeigen
        return render_template('rechnung/proforma.html',
            angebot=angebot,
            kunde=kunde,
            naechste_nummer='PRF-...',
            today=date.today().isoformat()
        )

    except Exception as e:
        logger.error(f"Proforma-Fehler: {e}")
        flash(f"Fehler: {str(e)}", "error")
        return redirect(url_for('angebote.show', angebot_id=angebot_id))


@rechnung_bp.route('/neue_rechnung_aus_auftrag')
def neue_rechnung_aus_auftrag():
    """
    Formular zur Erstellung einer Rechnung aus einem Auftrag - zeigt Liste der abrechenbaren Aufträge
    """
    try:
        from src.models.models import Order, Customer

        # Lade Aufträge die noch nicht abgerechnet wurden (Status: completed, delivered oder in_production)
        auftraege = Order.query.filter(
            Order.status.in_(['completed', 'delivered', 'in_production', 'ready'])
        ).order_by(Order.created_at.desc()).limit(50).all()

        return render_template('rechnung/aus_auftrag.html',
            auftraege=auftraege
        )

    except Exception as e:
        logger.error(f"Fehler beim Laden der Aufträge: {str(e)}")
        flash(f"Fehler beim Laden der Aufträge: {str(e)}", "error")
        return redirect(url_for('rechnung.rechnungs_index'))


@rechnung_bp.route('/neue_rechnung_aus_auftrag/<order_id>')
def rechnung_aus_auftrag_erstellen(order_id):
    """Rechnung aus einem einzelnen Auftrag erstellen"""
    try:
        from src.models.models import Order, Customer
        order = Order.query.get_or_404(order_id)
        kunde = order.get_billing_customer() if hasattr(order, 'get_billing_customer') else None
        if not kunde and order.customer_id:
            kunde = Customer.query.get(order.customer_id)

        positionen, netto_gesamt, mwst_gesamt = _build_rechnung_positionen([order])

        return render_template('rechnung/aus_auftrag_erstellen.html',
            orders=[order],
            kunde=kunde,
            positionen=positionen,
            netto_gesamt=float(netto_gesamt),
            mwst_gesamt=float(mwst_gesamt),
            brutto_gesamt=float(netto_gesamt + mwst_gesamt),
            naechste_nummer=RechnungsUtils.get_next_invoice_number(),
            zugpferd_profile=ZUGPFERD_PROFILE,
            today=date.today().isoformat()
        )
    except Exception as e:
        logger.error(f"Fehler beim Erstellen der Rechnung aus Auftrag: {str(e)}")
        flash(f"Fehler: {str(e)}", "error")
        return redirect(url_for('rechnung.neue_rechnung_aus_auftrag'))

@rechnung_bp.route('/sammelrechnung/neu', methods=['GET'])
def neue_sammelrechnung():
    """
    Formular fuer Sammelrechnung - mehrere Auftraege zusammenfassen
    """
    try:
        # Alle offenen/abgeschlossenen Auftraege ohne Rechnung laden
        orders = Order.query.filter(
            Order.status.in_(['accepted', 'in_progress', 'ready', 'completed'])
        ).order_by(Order.customer_id, Order.created_at.desc()).all()

        # Nach Kunden gruppieren fuer bessere UX
        customer_orders = {}
        for order in orders:
            customer_key = order.customer_id or 'unknown'
            if customer_key not in customer_orders:
                customer_orders[customer_key] = {
                    'customer': order.customer,
                    'orders': []
                }
            customer_orders[customer_key]['orders'].append(order)

        return render_template('rechnung/sammelrechnung_neu.html',
            customer_orders=customer_orders,
            naechste_nummer=RechnungsUtils.get_next_invoice_number(),
            today=date.today().isoformat()
        )
    except Exception as e:
        logger.error(f"Fehler Sammelrechnung-Formular: {e}")
        flash(f"Fehler: {e}", "error")
        return redirect(url_for('rechnung.rechnungs_index'))


@rechnung_bp.route('/sammelrechnung/erstellen', methods=['POST'])
def sammelrechnung_erstellen():
    """Sammelrechnung aus mehreren Auftraegen - auch von aus_auftrag.html aus"""
    try:
        # Akzeptiere order_ids[] (aus_auftrag.html) oder auftrag_id[] (sammelrechnung_neu.html)
        order_ids = request.form.getlist('order_ids[]') or request.form.getlist('auftrag_id')
        if not order_ids:
            flash('Bitte mindestens einen Auftrag auswaehlen.', 'warning')
            return redirect(url_for('rechnung.neue_rechnung_aus_auftrag'))

        orders = Order.query.filter(Order.id.in_(order_ids)).all()
        if not orders:
            flash('Keine gueltigen Auftraege gefunden.', 'danger')
            return redirect(url_for('rechnung.neue_rechnung_aus_auftrag'))

        # Wenn nur ein Auftrag ausgewaehlt: Einzelrechnung erstellen
        if len(orders) == 1:
            return redirect(url_for('rechnung.rechnung_aus_auftrag_erstellen', order_id=orders[0].id))

        # Alle Auftraege muessen vom gleichen Rechnungsempfaenger sein
        billing_ids = set()
        for o in orders:
            bc = o.get_billing_customer() if hasattr(o, 'get_billing_customer') else o.customer
            billing_ids.add(bc.id if bc else None)
        if len(billing_ids) > 1:
            flash('Alle ausgewaehlten Auftraege muessen zum gleichen Kunden gehoeren.', 'danger')
            return redirect(url_for('rechnung.neue_rechnung_aus_auftrag'))

        first_order = orders[0]
        kunde = first_order.get_billing_customer() if hasattr(first_order, 'get_billing_customer') else first_order.customer

        positionen, netto_gesamt, mwst_gesamt = _build_rechnung_positionen(orders)

        return render_template('rechnung/aus_auftrag_erstellen.html',
            orders=orders,
            kunde=kunde,
            positionen=positionen,
            netto_gesamt=float(netto_gesamt),
            mwst_gesamt=float(mwst_gesamt),
            brutto_gesamt=float(netto_gesamt + mwst_gesamt),
            naechste_nummer=RechnungsUtils.get_next_invoice_number(),
            zugpferd_profile=ZUGPFERD_PROFILE,
            today=date.today().isoformat()
        )

    except Exception as e:
        logger.error(f"Fehler beim Erstellen der Sammelrechnung: {e}")
        flash(f"Fehler: {e}", "error")
        return redirect(url_for('rechnung.neue_sammelrechnung'))


@rechnung_bp.route('/sammelrechnung/finalisieren', methods=['POST'])
def sammelrechnung_finalisieren():
    """
    Sammelrechnung final erstellen (speichert Rechnung + Positionen)
    """
    try:
        kunde_id = request.form.get('kunde_id')
        rechnungsdatum_str = request.form.get('rechnungsdatum')
        zahlungsziel = int(request.form.get('zahlungsziel_tage', 14))
        interne_notiz = request.form.get('interne_notiz', '')
        order_ids = request.form.getlist('auftrag_id')

        rechnungsdatum = datetime.strptime(rechnungsdatum_str, '%Y-%m-%d').date() if rechnungsdatum_str else date.today()
        faellig = date.fromordinal(rechnungsdatum.toordinal() + zahlungsziel)

        kunde = Customer.query.get(kunde_id)
        if not kunde:
            flash('Rechnungsempfaenger nicht gefunden.', 'danger')
            return redirect(url_for('rechnung.neue_sammelrechnung'))

        orders = Order.query.filter(Order.id.in_(order_ids)).all()
        if not orders:
            flash('Keine gueltigen Auftraege.', 'danger')
            return redirect(url_for('rechnung.neue_sammelrechnung'))

        rechnung = Rechnung(
            richtung=RechnungsRichtung.AUSGANG,
            kunde_id=kunde_id,
            kunde_name=kunde.display_name,
            kunde_adresse=f"{kunde.street or ''} {kunde.house_number or ''}\n{kunde.postal_code or ''} {kunde.city or ''}".strip(),
            kunde_email=kunde.email,
            kunde_steuernummer=getattr(kunde, 'tax_id', None),
            kunde_ust_id=getattr(kunde, 'vat_id', None),
            rechnungsdatum=rechnungsdatum,
            leistungsdatum=rechnungsdatum,
            zahlungsbedingungen=f'Zahlbar innerhalb {zahlungsziel} Tagen bis {faellig.strftime("%d.%m.%Y")}',
            bemerkungen=interne_notiz or f'Sammelrechnung fuer {len(orders)} Auftraege',
            status=RechnungsStatus.ENTWURF,
            erstellt_von=current_user.username if current_user.is_authenticated else 'System'
        )

        pos_idx = 1
        for order in orders:
            for item in order.items:
                einzelpreis = Decimal(str(item.unit_price or 0))
                menge = Decimal(str(item.quantity or 1))
                mwst_satz = Decimal('19')

                beschreibung = f"Auftrag {order.order_number or order.id}"
                if item.position_details:
                    beschreibung += f" - {item.position_details}"

                pos = RechnungsPosition(
                    position=pos_idx,
                    artikel_name=item.article.name if item.article else f'Position {pos_idx}',
                    beschreibung=beschreibung,
                    menge=menge,
                    einheit='Stck',
                    einzelpreis=einzelpreis,
                    mwst_satz=mwst_satz,
                    rabatt_prozent=Decimal('0')
                )
                pos.calculate_amounts()
                rechnung.positionen.append(pos)
                pos_idx += 1

        rechnung.calculate_totals()
        db.session.add(rechnung)
        db.session.commit()

        # Auftraege mit Rechnung verknuepfen
        for order in orders:
            order.invoice_id = rechnung.id
            order.workflow_status = 'invoiced'
        db.session.commit()

        logger.info(f"Sammelrechnung {rechnung.rechnungsnummer} erstellt ({len(orders)} Auftraege)")
        flash(f'Sammelrechnung {rechnung.rechnungsnummer} erfolgreich erstellt!', 'success')
        return redirect(url_for('rechnung.rechnung_detail', rechnung_id=rechnung.id))

    except Exception as e:
        db.session.rollback()
        logger.error(f"Fehler beim Erstellen der Sammelrechnung: {e}")
        flash(f'Fehler: {e}', 'danger')
        return redirect(url_for('rechnung.neue_sammelrechnung'))


@rechnung_bp.route('/eingang/neu')
def neue_eingangsrechnung():
    """
    Formular für neue Eingangsrechnung (von Lieferanten)
    """
    try:
        from src.models.models import Supplier

        # Lieferanten laden
        lieferanten = Supplier.query.order_by(Supplier.name).all()

        return render_template('rechnung/eingang_neu.html',
            lieferanten=lieferanten,
            heute=date.today()
        )

    except Exception as e:
        logger.error(f"Fehler beim Laden des Eingangsrechnungs-Formulars: {str(e)}")
        flash(f"Fehler beim Laden des Formulars: {str(e)}", "error")
        return redirect(url_for('rechnung.rechnungs_index', tab='eingang'))

@rechnung_bp.route('/eingang/neu', methods=['POST'])
def eingangsrechnung_erstellen():
    """Neue Eingangsrechnung erfassen + automatisch buchen"""
    from src.services.rechnung_service import RechnungService
    from src.models.models import Supplier

    try:
        lieferant_id = request.form.get('lieferant_id')
        rechnungsnummer = request.form.get('rechnungsnummer', '')
        rechnungsdatum = datetime.strptime(request.form.get('rechnungsdatum'), '%Y-%m-%d').date() if request.form.get('rechnungsdatum') else date.today()
        faelligkeitsdatum = datetime.strptime(request.form.get('faelligkeitsdatum'), '%Y-%m-%d').date() if request.form.get('faelligkeitsdatum') else None
        netto_gesamt = Decimal(request.form.get('netto_gesamt', '0').replace(',', '.'))
        mwst_gesamt = Decimal(request.form.get('mwst_gesamt', '0').replace(',', '.'))
        mwst_satz = int(request.form.get('mwst_satz', 19))
        bemerkungen = request.form.get('bemerkungen', '')
        kategorie = request.form.get('kategorie', 'sonstiges')

        lieferant = Supplier.query.get(lieferant_id) if lieferant_id else None
        lieferant_name = lieferant.name if lieferant else request.form.get('lieferant_name', 'Unbekannt')

        rechnung, fehler = RechnungService.erfasse_eingangsrechnung(
            lieferant_name=lieferant_name,
            rechnungsnummer=rechnungsnummer,
            rechnungsdatum=rechnungsdatum,
            netto=netto_gesamt,
            mwst_betrag=mwst_gesamt,
            mwst_satz=mwst_satz,
            kategorie=kategorie,
            bemerkungen=bemerkungen,
            lieferant_id=lieferant_id,
            faelligkeitsdatum=faelligkeitsdatum,
            auto_buchen=True
        )

        if rechnung:
            flash(f"Eingangsrechnung {rechnung.rechnungsnummer} erfasst und gebucht!", "success")
            return redirect(url_for('rechnung.rechnungs_index', tab='eingang'))
        else:
            flash(f"Fehler: {fehler}", "error")
            return redirect(url_for('rechnung.neue_eingangsrechnung'))

    except Exception as e:
        logger.error(f"Fehler beim Erfassen der Eingangsrechnung: {str(e)}")
        flash(f"Fehler beim Erfassen: {str(e)}", "error")
        return redirect(url_for('rechnung.neue_eingangsrechnung'))

@rechnung_bp.route('/<int:rechnung_id>/bearbeiten')
def rechnung_bearbeiten(rechnung_id):
    """Rechnung bearbeiten (nur ENTWURF)"""
    rechnung = Rechnung.query.get_or_404(rechnung_id)
    if rechnung.status != RechnungsStatus.ENTWURF:
        flash("Nur Entwürfe können bearbeitet werden.", "warning")
        return redirect(url_for('rechnung.rechnung_detail', rechnung_id=rechnung_id))
    return render_template('rechnung/bearbeiten.html', rechnung=rechnung)


@rechnung_bp.route('/<int:rechnung_id>/versenden', methods=['POST'])
def rechnung_versenden(rechnung_id):
    """Entwurf finalisieren: echte RE-Nummer vergeben + Status OFFEN + Buchung"""
    from src.services.rechnung_service import RechnungService

    ok, msg = RechnungService.versende_rechnung(rechnung_id)
    if ok:
        flash(msg, "success")
    else:
        flash(msg, "error")
    return redirect(url_for('rechnung.rechnung_detail', rechnung_id=rechnung_id))


@rechnung_bp.route('/<int:rechnung_id>/loeschen', methods=['POST'])
def rechnung_loeschen(rechnung_id):
    """Entwurf-Rechnung komplett löschen"""
    rechnung = Rechnung.query.get_or_404(rechnung_id)
    if rechnung.status != RechnungsStatus.ENTWURF:
        flash("Nur Entwürfe können gelöscht werden.", "warning")
        return redirect(url_for('rechnung.rechnung_detail', rechnung_id=rechnung_id))
    try:
        nummer = rechnung.rechnungsnummer
        # Verknüpfte Aufträge entkoppeln (Foreign Key)
        from src.models.models import Order
        linked_orders = Order.query.filter_by(invoice_id=rechnung_id).all()
        for order in linked_orders:
            order.invoice_id = None
            if order.status in ('invoiced', 'completed'):
                order.status = 'ready'
        # Positionen löschen
        for pos in rechnung.positionen:
            db.session.delete(pos)
        db.session.delete(rechnung)
        db.session.commit()
        flash(f"Rechnung {nummer} wurde gelöscht.", "info")
        return redirect(url_for('rechnung.rechnungs_index'))
    except Exception as e:
        db.session.rollback()
        flash(f"Fehler beim Löschen: {e}", "error")
        return redirect(url_for('rechnung.rechnung_detail', rechnung_id=rechnung_id))

@rechnung_bp.route('/<int:rechnung_id>/pdf')
def rechnung_pdf(rechnung_id):
    """
    Rechnung als PDF anzeigen
    """
    try:
        rechnung = Rechnung.query.get_or_404(rechnung_id)

        # PDF-Service nutzen (ohne ZUGFeRD-XML)
        pdf_service = PDFService()
        zugpferd_service = ZugpferdService()

        # Daten aufbereiten
        invoice_data = zugpferd_service._convert_rechnung_to_invoice_data(rechnung)

        # PDF generieren
        pdf_content = pdf_service.create_invoice_pdf(invoice_data)

        # Als Response zurückgeben
        return send_file(
            io.BytesIO(pdf_content),
            mimetype='application/pdf',
            as_attachment=False,  # Im Browser anzeigen
            download_name=f'{rechnung.rechnungsnummer}.pdf'
        )

    except Exception as e:
        logger.error(f"Fehler beim Generieren des PDFs: {str(e)}")
        flash(f"Fehler beim Generieren des PDFs: {str(e)}", "error")
        return redirect(url_for('rechnung.rechnung_detail', rechnung_id=rechnung_id))

@rechnung_bp.route('/<int:rechnung_id>/download')
def rechnung_download(rechnung_id):
    """
    Rechnung herunterladen (ZUGPFERD PDF/A-3 mit eingebettetem XML)
    """
    try:
        rechnung = Rechnung.query.get_or_404(rechnung_id)

        # ZUGFeRD-Service nutzen
        zugpferd_service = ZugpferdService()

        # Vollständiges ZUGFeRD-PDF erstellen (PDF/A-3 + XML)
        zugferd_pdf = zugpferd_service.create_invoice_from_rechnung(rechnung)

        # Als Download zurückgeben
        return send_file(
            io.BytesIO(zugferd_pdf),
            mimetype='application/pdf',
            as_attachment=True,  # Download erzwingen
            download_name=f'{rechnung.rechnungsnummer}_ZUGFeRD.pdf'
        )

    except Exception as e:
        logger.error(f"Fehler beim ZUGFeRD-Download: {str(e)}")
        flash(f"Fehler beim Download: {str(e)}", "error")
        return redirect(url_for('rechnung.rechnung_detail', rechnung_id=rechnung_id))

# API-Endpoints
@rechnung_bp.route('/api/<int:rechnung_id>/bezahlt', methods=['POST'])
def api_rechnung_bezahlt(rechnung_id):
    """Rechnung als bezahlt oder teilbezahlt markieren"""
    from src.services.rechnung_service import RechnungService

    try:
        data = request.get_json() or {}
        rechnung = Rechnung.query.get_or_404(rechnung_id)

        zahlungsart = data.get('zahlungsart', 'ueberweisung')
        betrag = float(data.get('betrag') or rechnung.brutto_gesamt or 0)

        ok, msg = RechnungService.zahlung_erfassen(rechnung_id, betrag, zahlungsart)
        if ok:
            return jsonify({'success': True, 'message': msg})
        else:
            return jsonify({'success': False, 'message': msg}), 400

    except Exception as e:
        logger.error(f"Fehler beim Markieren als bezahlt: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@rechnung_bp.route('/api/<int:rechnung_id>/mahnung', methods=['POST'])
def api_rechnung_mahnung(rechnung_id):
    """
    Zahlungserinnerung versenden
    """
    try:
        # TODO: Mahnung versenden implementieren
        return jsonify({
            'success': True,
            'message': 'Zahlungserinnerung wurde versendet'
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Versenden der Mahnung: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@rechnung_bp.route('/api/<int:rechnung_id>/stornieren', methods=['POST'])
def api_rechnung_stornieren(rechnung_id):
    """
    Rechnung stornieren - erstellt eine Stornorechnung
    """
    try:
        rechnung = Rechnung.query.get_or_404(rechnung_id)

        # Prüfen ob Rechnung bereits storniert
        if rechnung.status == RechnungsStatus.STORNIERT:
            return jsonify({
                'success': False,
                'message': 'Rechnung ist bereits storniert'
            }), 400

        # Storno-Grund aus Request holen
        data = request.get_json() or {}
        storno_grund = data.get('grund', 'Storniert durch Benutzer')

        # Stornorechnung erstellen (negative Beträge)
        storno_nummer = f"ST-{rechnung.rechnungsnummer}"

        # Prüfen ob Stornorechnung bereits existiert
        existing_storno = Rechnung.query.filter_by(rechnungsnummer=storno_nummer).first()
        if existing_storno:
            return jsonify({
                'success': False,
                'message': 'Stornorechnung existiert bereits'
            }), 400

        # Neue Stornorechnung mit negativen Beträgen
        stornorechnung = Rechnung(
            rechnungsnummer=storno_nummer,
            richtung=rechnung.richtung,
            kunde_id=rechnung.kunde_id,
            kunde_name=rechnung.kunde_name,
            kunde_adresse=rechnung.kunde_adresse,
            kunde_email=rechnung.kunde_email,
            kunde_steuernummer=rechnung.kunde_steuernummer,
            kunde_ust_id=rechnung.kunde_ust_id,
            rechnungsdatum=date.today(),
            leistungsdatum=rechnung.leistungsdatum,
            faelligkeitsdatum=date.today(),
            netto_gesamt=-rechnung.netto_gesamt,
            mwst_gesamt=-rechnung.mwst_gesamt,
            brutto_gesamt=-rechnung.brutto_gesamt,
            status=RechnungsStatus.STORNIERT,
            zugpferd_profil=rechnung.zugpferd_profil,
            bemerkungen=f"Stornorechnung zu {rechnung.rechnungsnummer}\nGrund: {storno_grund}",
            erstellt_von=current_user.username if current_user.is_authenticated else 'System'
        )

        # Storno-Positionen erstellen (negative Beträge)
        for pos in rechnung.positionen:
            storno_pos = RechnungsPosition(
                position=pos.position,
                artikel_id=pos.artikel_id,
                artikel_nummer=pos.artikel_nummer,
                artikel_name=f"STORNO: {pos.artikel_name}",
                beschreibung=pos.beschreibung,
                menge=-pos.menge,
                einheit=pos.einheit,
                einzelpreis=pos.einzelpreis,
                mwst_satz=pos.mwst_satz,
                mwst_betrag=-pos.mwst_betrag,
                rabatt_prozent=pos.rabatt_prozent,
                rabatt_betrag=-pos.rabatt_betrag if pos.rabatt_betrag else 0,
                netto_betrag=-pos.netto_betrag,
                brutto_betrag=-pos.brutto_betrag
            )
            stornorechnung.positionen.append(storno_pos)

        # Originalrechnung als storniert markieren
        rechnung.status = RechnungsStatus.STORNIERT
        rechnung.bemerkungen = (rechnung.bemerkungen or '') + f"\n\n--- STORNIERT am {date.today().strftime('%d.%m.%Y')} ---\nGrund: {storno_grund}\nStornorechnung: {storno_nummer}"
        rechnung.bearbeitet_am = datetime.utcnow()
        rechnung.bearbeitet_von = current_user.username if current_user.is_authenticated else 'System'

        db.session.add(stornorechnung)
        db.session.commit()

        logger.info(f"Rechnung {rechnung.rechnungsnummer} storniert, Stornorechnung {storno_nummer} erstellt")

        return jsonify({
            'success': True,
            'message': f'Rechnung wurde storniert. Stornorechnung: {storno_nummer}',
            'storno_rechnung_id': stornorechnung.id,
            'storno_nummer': storno_nummer
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Fehler beim Stornieren: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@rechnung_bp.route('/<int:rechnung_id>/archiv/speichern', methods=['POST'])
def rechnung_archiv_speichern(rechnung_id):
    """
    Speichert die Rechnung als PDF im Archiv
    """
    try:
        import os
        from flask import current_app

        rechnung = Rechnung.query.get_or_404(rechnung_id)

        # Archiv-Verzeichnis erstellen
        archiv_dir = os.path.join(current_app.instance_path, 'rechnungen_archiv')
        jahr_dir = os.path.join(archiv_dir, str(rechnung.rechnungsdatum.year))
        monat_dir = os.path.join(jahr_dir, f"{rechnung.rechnungsdatum.month:02d}")

        os.makedirs(monat_dir, exist_ok=True)

        # PDF generieren
        zugpferd_service = ZugpferdService()
        pdf_content = zugpferd_service.create_invoice_from_rechnung(rechnung)

        # Dateiname: Rechnungsnummer_Kunde.pdf
        safe_kunde = "".join(c for c in (rechnung.kunde_name or 'Unbekannt') if c.isalnum() or c in ' _-')[:50]
        filename = f"{rechnung.rechnungsnummer}_{safe_kunde}.pdf"
        filepath = os.path.join(monat_dir, filename)

        # PDF speichern
        with open(filepath, 'wb') as f:
            f.write(pdf_content)

        # Pfad in Datenbank speichern (relativ zum instance-Ordner)
        rel_path = os.path.join('rechnungen_archiv', str(rechnung.rechnungsdatum.year),
                                f"{rechnung.rechnungsdatum.month:02d}", filename)
        rechnung.pdf_datei = rel_path
        rechnung.bearbeitet_am = datetime.utcnow()
        db.session.commit()

        logger.info(f"Rechnung {rechnung.rechnungsnummer} im Archiv gespeichert: {filepath}")

        flash(f"Rechnung wurde im Archiv gespeichert", "success")
        return redirect(url_for('rechnung.rechnung_detail', rechnung_id=rechnung_id))

    except Exception as e:
        logger.error(f"Fehler beim Archivieren: {str(e)}")
        flash(f"Fehler beim Archivieren: {str(e)}", "error")
        return redirect(url_for('rechnung.rechnung_detail', rechnung_id=rechnung_id))


@rechnung_bp.route('/<int:rechnung_id>/archiv/oeffnen')
def rechnung_archiv_oeffnen(rechnung_id):
    """
    Öffnet die archivierte PDF-Datei einer Rechnung
    """
    try:
        import os
        from flask import current_app

        rechnung = Rechnung.query.get_or_404(rechnung_id)

        if not rechnung.pdf_datei:
            flash("Keine archivierte PDF-Datei vorhanden. Bitte zuerst archivieren.", "warning")
            return redirect(url_for('rechnung.rechnung_detail', rechnung_id=rechnung_id))

        # Vollständigen Pfad erstellen
        filepath = os.path.join(current_app.instance_path, rechnung.pdf_datei)

        if not os.path.exists(filepath):
            flash("Archivierte PDF-Datei nicht gefunden. Bitte erneut archivieren.", "error")
            rechnung.pdf_datei = None
            db.session.commit()
            return redirect(url_for('rechnung.rechnung_detail', rechnung_id=rechnung_id))

        # PDF aus Archiv senden
        with open(filepath, 'rb') as f:
            pdf_content = f.read()

        return send_file(
            io.BytesIO(pdf_content),
            mimetype='application/pdf',
            as_attachment=False,
            download_name=f'{rechnung.rechnungsnummer}.pdf'
        )

    except Exception as e:
        logger.error(f"Fehler beim Öffnen der archivierten Rechnung: {str(e)}")
        flash(f"Fehler: {str(e)}", "error")
        return redirect(url_for('rechnung.rechnung_detail', rechnung_id=rechnung_id))


@rechnung_bp.route('/<int:rechnung_id>/archiv/download')
def rechnung_archiv_download(rechnung_id):
    """
    Lädt die archivierte PDF-Datei herunter
    """
    try:
        import os
        from flask import current_app

        rechnung = Rechnung.query.get_or_404(rechnung_id)

        if not rechnung.pdf_datei:
            flash("Keine archivierte PDF-Datei vorhanden.", "warning")
            return redirect(url_for('rechnung.rechnung_detail', rechnung_id=rechnung_id))

        filepath = os.path.join(current_app.instance_path, rechnung.pdf_datei)

        if not os.path.exists(filepath):
            flash("Archivierte PDF-Datei nicht gefunden.", "error")
            return redirect(url_for('rechnung.rechnung_detail', rechnung_id=rechnung_id))

        with open(filepath, 'rb') as f:
            pdf_content = f.read()

        return send_file(
            io.BytesIO(pdf_content),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{rechnung.rechnungsnummer}.pdf'
        )

    except Exception as e:
        logger.error(f"Fehler beim Download: {str(e)}")
        flash(f"Fehler: {str(e)}", "error")
        return redirect(url_for('rechnung.rechnung_detail', rechnung_id=rechnung_id))


@rechnung_bp.route('/archiv')
def rechnungs_archiv():
    """
    Zeigt alle archivierten Rechnungen nach Jahr/Monat
    """
    try:
        import os
        from flask import current_app
        from collections import defaultdict

        # Alle Rechnungen mit PDF-Archiv laden
        rechnungen_mit_archiv = Rechnung.query.filter(
            Rechnung.pdf_datei != None,
            Rechnung.pdf_datei != ''
        ).order_by(Rechnung.rechnungsdatum.desc()).all()

        # Nach Jahr und Monat gruppieren
        archiv_struktur = defaultdict(lambda: defaultdict(list))

        for rechnung in rechnungen_mit_archiv:
            if rechnung.rechnungsdatum:
                jahr = rechnung.rechnungsdatum.year
                monat = rechnung.rechnungsdatum.month
                archiv_struktur[jahr][monat].append(rechnung)

        # Sortieren (neueste zuerst)
        archiv_struktur = dict(sorted(archiv_struktur.items(), reverse=True))
        for jahr in archiv_struktur:
            archiv_struktur[jahr] = dict(sorted(archiv_struktur[jahr].items(), reverse=True))

        # Statistiken
        total_count = len(rechnungen_mit_archiv)
        total_betrag = sum(float(r.brutto_gesamt or 0) for r in rechnungen_mit_archiv)

        return render_template('rechnung/archiv.html',
            archiv_struktur=archiv_struktur,
            total_count=total_count,
            total_betrag=total_betrag,
            page_title="Rechnungsarchiv"
        )

    except Exception as e:
        logger.error(f"Fehler beim Laden des Archivs: {str(e)}")
        flash(f"Fehler beim Laden des Archivs: {str(e)}", "error")
        return redirect(url_for('rechnung.rechnungs_index'))


@rechnung_bp.route('/<int:rechnung_id>/verknuepfen')
def rechnung_verknuepfen(rechnung_id):
    """
    Rechnung mit Auftrag verknüpfen (Rückwärts-Verknüpfung)
    Zeigt alle Aufträge die noch nicht mit einer Rechnung verknüpft sind
    """
    try:
        from src.models.models import Order
        
        rechnung = Rechnung.query.get_or_404(rechnung_id)
        
        # Aufträge ohne Rechnung oder mit dieser Rechnung
        auftraege = Order.query.filter(
            db.or_(
                Order.invoice_id == None,
                Order.invoice_id == rechnung.id
            ),
            Order.status.notin_(['cancelled', 'draft'])
        ).order_by(Order.created_at.desc()).limit(100).all()
        
        # Passende Aufträge hervorheben (gleicher Kunde)
        passende_auftraege = []
        andere_auftraege = []
        
        for auftrag in auftraege:
            if str(auftrag.customer_id) == str(rechnung.kunde_id):
                passende_auftraege.append(auftrag)
            else:
                andere_auftraege.append(auftrag)
        
        return render_template('rechnung/verknuepfen.html',
            rechnung=rechnung,
            passende_auftraege=passende_auftraege,
            andere_auftraege=andere_auftraege,
            aktueller_auftrag=rechnung.auftrag
        )
        
    except Exception as e:
        logger.error(f"Fehler beim Laden der Aufträge: {str(e)}")
        flash(f"Fehler: {str(e)}", "error")
        return redirect(url_for('rechnung.rechnung_detail', rechnung_id=rechnung_id))


@rechnung_bp.route('/<int:rechnung_id>/verknuepfen', methods=['POST'])
def rechnung_verknuepfen_speichern(rechnung_id):
    """
    Speichert die Verknüpfung Rechnung <-> Auftrag
    """
    try:
        from src.models.models import Order
        
        rechnung = Rechnung.query.get_or_404(rechnung_id)
        
        order_id = request.form.get('order_id')
        
        # Alte Verknüpfung lösen (falls vorhanden)
        if rechnung.auftrag_id:
            alter_auftrag = Order.query.get(rechnung.auftrag_id)
            if alter_auftrag:
                alter_auftrag.invoice_id = None
        
        if order_id and order_id != 'none':
            # Neue Verknüpfung setzen
            auftrag = Order.query.get_or_404(order_id)
            
            # Prüfen ob Auftrag bereits andere Rechnung hat
            if auftrag.invoice_id and auftrag.invoice_id != rechnung.id:
                andere_rechnung = Rechnung.query.get(auftrag.invoice_id)
                if andere_rechnung:
                    flash(f"Achtung: Auftrag war bereits mit Rechnung {andere_rechnung.rechnungsnummer} verknüpft. Alte Verknüpfung wurde gelöst.", "warning")
                    andere_rechnung.auftrag_id = None
            
            # Bidirektionale Verknüpfung
            rechnung.auftrag_id = order_id
            auftrag.invoice_id = rechnung.id
            
            # Workflow-Status aktualisieren
            if auftrag.workflow_status in ['delivered', 'picked_up', 'shipped']:
                auftrag.workflow_status = 'invoiced'
            
            flash(f"Rechnung wurde mit Auftrag {auftrag.order_number} verknüpft.", "success")
        else:
            # Verknüpfung entfernen
            rechnung.auftrag_id = None
            flash("Auftragsverknüpfung wurde entfernt.", "info")
        
        rechnung.bearbeitet_am = datetime.utcnow()
        rechnung.bearbeitet_von = current_user.username if current_user.is_authenticated else 'System'
        
        db.session.commit()
        
        return redirect(url_for('rechnung.rechnung_detail', rechnung_id=rechnung_id))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Fehler beim Verknüpfen: {str(e)}")
        flash(f"Fehler: {str(e)}", "error")
        return redirect(url_for('rechnung.rechnung_verknuepfen', rechnung_id=rechnung_id))


@rechnung_bp.route('/api/<int:rechnung_id>/verknuepfen', methods=['POST'])
def api_rechnung_verknuepfen(rechnung_id):
    """
    API: Rechnung mit Auftrag verknüpfen
    """
    try:
        from src.models.models import Order
        
        rechnung = Rechnung.query.get_or_404(rechnung_id)
        data = request.get_json() or {}
        order_id = data.get('order_id')
        
        if not order_id:
            return jsonify({'success': False, 'error': 'Keine Auftrags-ID angegeben'}), 400
        
        auftrag = Order.query.get_or_404(order_id)
        
        # Bidirektionale Verknüpfung
        rechnung.auftrag_id = order_id
        auftrag.invoice_id = rechnung.id
        
        rechnung.bearbeitet_am = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Rechnung mit Auftrag {auftrag.order_number} verknüpft',
            'order_number': auftrag.order_number
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@rechnung_bp.route('/api/order/<order_id>/verknuepfen', methods=['POST'])
def api_auftrag_mit_rechnung_verknuepfen(order_id):
    """
    API: Auftrag mit bestehender Rechnung verknüpfen (aus Auftragsansicht)
    """
    try:
        from src.models.models import Order
        
        auftrag = Order.query.get_or_404(order_id)
        data = request.get_json() or {}
        rechnung_id = data.get('rechnung_id')
        
        if not rechnung_id:
            return jsonify({'success': False, 'error': 'Keine Rechnungs-ID angegeben'}), 400
        
        rechnung = Rechnung.query.get_or_404(rechnung_id)
        
        # Bidirektionale Verknüpfung
        auftrag.invoice_id = rechnung.id
        rechnung.auftrag_id = order_id
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Auftrag mit Rechnung {rechnung.rechnungsnummer} verknüpft',
            'rechnungsnummer': rechnung.rechnungsnummer
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@rechnung_bp.route('/suche/fuer-auftrag/<order_id>')
def suche_rechnungen_fuer_auftrag(order_id):
    """
    Sucht passende Rechnungen für einen Auftrag (für Verknüpfungs-Dialog)
    """
    try:
        from src.models.models import Order
        
        auftrag = Order.query.get_or_404(order_id)
        
        # Suche Rechnungen die:
        # 1. Gleicher Kunde
        # 2. Noch nicht verknüpft oder mit diesem Auftrag verknüpft
        # 3. Nicht storniert
        
        query = Rechnung.query.filter(
            Rechnung.kunde_id == str(auftrag.customer_id),
            Rechnung.status != RechnungsStatus.STORNIERT,
            db.or_(
                Rechnung.auftrag_id == None,
                Rechnung.auftrag_id == order_id
            )
        ).order_by(Rechnung.rechnungsdatum.desc())
        
        rechnungen = query.limit(20).all()
        
        return jsonify({
            'success': True,
            'rechnungen': [{
                'id': r.id,
                'rechnungsnummer': r.rechnungsnummer,
                'datum': r.rechnungsdatum.strftime('%d.%m.%Y') if r.rechnungsdatum else '',
                'betrag': float(r.brutto_gesamt or 0),
                'status': r.status.value if hasattr(r.status, 'value') else r.status,
                'bereits_verknuepft': r.auftrag_id == order_id
            } for r in rechnungen]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rechnung_bp.route('/export')
def export_rechnungen():
    """
    Rechnungen exportieren
    """
    try:
        format_type = request.args.get('format', 'csv')

        # TODO: Export implementieren
        flash(f"Export im Format {format_type} wird noch implementiert", "info")
        return redirect(url_for('rechnung.rechnungs_index'))

    except Exception as e:
        logger.error(f"Fehler beim Export: {str(e)}")
        flash(f"Fehler beim Export: {str(e)}", "error")
        return redirect(url_for('rechnung.rechnungs_index'))


# ═══════════════════════════════════════════════════════════════════════════════
# RECHNUNGS-SCANNER (Handy-Kamera)
# ═══════════════════════════════════════════════════════════════════════════════

@rechnung_bp.route('/scan')
def scan_rechnung():
    """Rechnungs-Scanner Seite (Kamera-Erfassung)"""
    from src.models.models import Supplier
    suppliers = Supplier.query.filter_by(active=True).order_by(Supplier.name).all()
    return render_template('rechnung/scan.html', suppliers=suppliers, today=date.today().isoformat())


@rechnung_bp.route('/scan/upload', methods=['POST'])
def scan_upload():
    """Gescanntes Foto hochladen und Eingangsrechnung erstellen"""
    import os
    from werkzeug.utils import secure_filename
    from src.models.models import Supplier

    try:
        foto = request.files.get('foto')
        if not foto or not foto.filename:
            return jsonify({'success': False, 'error': 'Kein Foto hochgeladen'})

        # Datei validieren
        allowed = {'.jpg', '.jpeg', '.png', '.webp', '.pdf'}
        ext = os.path.splitext(foto.filename)[1].lower()
        if ext not in allowed:
            return jsonify({'success': False, 'error': f'Dateiformat {ext} nicht erlaubt'})

        # Speichern
        upload_dir = os.path.join('instance', 'uploads', 'rechnungs_scans')
        os.makedirs(upload_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = f"scan_{timestamp}{ext}"
        filepath = os.path.join(upload_dir, safe_name)
        foto.save(filepath)

        # Formulardaten
        lieferant_id = request.form.get('lieferant_id', '').strip()
        lieferant_name_input = request.form.get('lieferant_name', '').strip()
        rechnungsnummer_ext = request.form.get('rechnungsnummer', '').strip()
        betrag_str = request.form.get('betrag', '').strip()
        datum_str = request.form.get('datum', '').strip()
        bemerkungen = request.form.get('bemerkungen', '').strip()

        # Lieferant-Name ermitteln
        lieferant_name = lieferant_name_input
        if lieferant_id and not lieferant_name:
            supplier = Supplier.query.get(lieferant_id)
            if supplier:
                lieferant_name = supplier.name

        # Betrag parsen
        betrag = Decimal('0')
        if betrag_str:
            betrag_str = betrag_str.replace(',', '.')
            try:
                betrag = Decimal(betrag_str)
            except Exception:
                pass

        # Datum parsen
        rechnungsdatum = date.today()
        if datum_str:
            try:
                rechnungsdatum = datetime.strptime(datum_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                pass

        # Eingangsrechnung erstellen
        from src.models.rechnungsmodul.models import RechnungsRichtung as RR2
        nummer = f"ER-{datetime.now().strftime('%Y%m')}-{timestamp[-4:]}"

        rechnung = Rechnung(
            rechnungsnummer=nummer,
            richtung=RR2.EINGANG,
            status=RechnungsStatus.ENTWURF,
            rechnungsdatum=rechnungsdatum,
            lieferant_id=lieferant_id or None,
            lieferant_name=lieferant_name or 'Unbekannt',
            brutto_gesamt=betrag,
            netto_gesamt=betrag,
            scan_foto=filepath,
            bemerkungen=bemerkungen,
            interne_notizen=f'Ext. Rechnungsnr: {rechnungsnummer_ext}' if rechnungsnummer_ext else None,
            erstellt_von=current_user.username,
        )

        # Faelligkeit: 30 Tage
        rechnung.faelligkeitsdatum = rechnungsdatum + timedelta(days=30)

        db.session.add(rechnung)
        db.session.commit()

        return jsonify({
            'success': True,
            'rechnung_id': rechnung.id,
            'nummer': nummer,
            'message': f'Eingangsrechnung {nummer} erstellt'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Fehler beim Rechnung-Scan: {e}")
        return jsonify({'success': False, 'error': str(e)})
