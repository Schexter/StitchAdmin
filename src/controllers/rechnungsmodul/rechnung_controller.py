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
        def get_next_invoice_number():
            # Generiere eindeutige Rechnungsnummer
            prefix = "RE"
            jahr = datetime.now().year
            monat = datetime.now().month

            # Hole die nächste Nummer für diesen Monat
            count = Rechnung.query.filter(
                Rechnung.rechnungsnummer.like(f"{prefix}-{jahr:04d}{monat:02d}-%")
            ).count()

            return f"{prefix}-{jahr:04d}{monat:02d}-{count + 1:04d}"

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

                # Status-Filter anwenden
                if status_filter:
                    ausgang_query = ausgang_query.filter_by(status=status_filter)
                    eingang_query = eingang_query.filter_by(status=status_filter)

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
        
        return render_template('rechnung/neue_rechnung.html',
            naechste_nummer=naechste_nummer,
            zugpferd_profile=zugpferd_profile,
            mwst_saetze=mwst_saetze,
            page_title="Neue Rechnung erstellen",
            today=date.today().isoformat()
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

        # Positionen verarbeiten
        positionen_data = json.loads(request.form.get('positionen', '[]'))
        for idx, pos_data in enumerate(positionen_data, 1):
            position = RechnungsPosition(
                position=idx,
                artikel_name=pos_data.get('artikel_name', ''),
                beschreibung=pos_data.get('beschreibung', ''),
                menge=Decimal(str(pos_data.get('menge', 1))),
                einheit=pos_data.get('einheit', 'Stück'),
                einzelpreis=Decimal(str(pos_data.get('einzelpreis', 0))),
                mwst_satz=Decimal(str(pos_data.get('mwst_satz', 19))),
                rabatt_prozent=Decimal(str(pos_data.get('rabatt_prozent', 0)))
            )
            position.calculate_amounts()
            rechnung.positionen.append(position)

        # Gesamtsummen berechnen
        rechnung.calculate_totals()

        # In DB speichern
        db.session.add(rechnung)
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

        return render_template('rechnung/detail.html',
            rechnung=rechnung,
            page_title=f"Rechnung {rechnung.rechnungsnummer}"
        )

    except Exception as e:
        logger.error(f"Fehler beim Anzeigen der Rechnung: {str(e)}")
        flash(f"Fehler beim Laden der Rechnung: {str(e)}", "error")
        return redirect(url_for('rechnung.rechnungs_index'))

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
    """
    Rechnung aus einem spezifischen Auftrag erstellen
    """
    try:
        from src.models.models import Order, Customer

        # Lade Auftrag mit Positionen
        order = Order.query.get_or_404(order_id)
        kunde = Customer.query.get(order.customer_id) if order.customer_id else None

        # Berechne Summen aus Auftragspositionen
        positionen = []
        netto_gesamt = Decimal('0')
        mwst_gesamt = Decimal('0')

        if hasattr(order, 'items') and order.items:
            for idx, item in enumerate(order.items, 1):
                einzelpreis = Decimal(str(item.unit_price or 0))
                menge = Decimal(str(item.quantity or 1))
                mwst_satz = Decimal('19')  # Standard-MwSt

                netto = einzelpreis * menge
                mwst = netto * (mwst_satz / 100)
                brutto = netto + mwst

                netto_gesamt += netto
                mwst_gesamt += mwst

                positionen.append({
                    'position': idx,
                    'artikel_id': item.article_id,
                    'artikel_name': item.article.name if item.article else f'Position {idx}',
                    'beschreibung': item.position_details or '',
                    'menge': float(menge),
                    'einheit': 'Stück',
                    'einzelpreis_netto': float(einzelpreis),
                    'mwst_satz': float(mwst_satz),
                    'netto_betrag': float(netto),
                    'mwst_betrag': float(mwst),
                    'brutto_betrag': float(brutto)
                })

        brutto_gesamt = netto_gesamt + mwst_gesamt

        # Nächste Rechnungsnummer generieren
        naechste_nummer = RechnungsUtils.get_next_invoice_number()

        # ZugPFeRD-Profile laden
        zugpferd_profile = [
            {'value': 'MINIMUM', 'label': 'Minimum (einfachste Stufe)'},
            {'value': 'BASIC', 'label': 'Basic (Standard)'},
            {'value': 'COMFORT', 'label': 'Comfort (erweitert)'},
            {'value': 'EXTENDED', 'label': 'Extended (vollständig)'},
        ]

        return render_template('rechnung/aus_auftrag_erstellen.html',
            order=order,
            kunde=kunde,
            positionen=positionen,
            netto_gesamt=float(netto_gesamt),
            mwst_gesamt=float(mwst_gesamt),
            brutto_gesamt=float(brutto_gesamt),
            naechste_nummer=naechste_nummer,
            zugpferd_profile=zugpferd_profile,
            today=date.today().isoformat()
        )

    except Exception as e:
        logger.error(f"Fehler beim Erstellen der Rechnung aus Auftrag: {str(e)}")
        flash(f"Fehler: {str(e)}", "error")
        return redirect(url_for('rechnung.neue_rechnung_aus_auftrag'))

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
    """
    Neue Eingangsrechnung erfassen
    """
    try:
        from src.models.models import Supplier

        # Formulardaten
        lieferant_id = request.form.get('lieferant_id')
        rechnungsnummer = request.form.get('rechnungsnummer', '')
        rechnungsdatum = datetime.strptime(request.form.get('rechnungsdatum'), '%Y-%m-%d').date() if request.form.get('rechnungsdatum') else date.today()
        faelligkeitsdatum = datetime.strptime(request.form.get('faelligkeitsdatum'), '%Y-%m-%d').date() if request.form.get('faelligkeitsdatum') else None
        netto_gesamt = Decimal(request.form.get('netto_gesamt', '0').replace(',', '.'))
        mwst_gesamt = Decimal(request.form.get('mwst_gesamt', '0').replace(',', '.'))
        brutto_gesamt = Decimal(request.form.get('brutto_gesamt', '0').replace(',', '.'))
        bemerkungen = request.form.get('bemerkungen', '')

        # Lieferant laden
        lieferant = Supplier.query.get(lieferant_id) if lieferant_id else None
        lieferant_name = lieferant.name if lieferant else request.form.get('lieferant_name', 'Unbekannt')

        # Eingangsrechnung erstellen
        rechnung = Rechnung(
            rechnungsnummer=rechnungsnummer or f"ER-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            richtung=RechnungsRichtung.EINGANG,
            lieferant_id=lieferant_id,
            lieferant_name=lieferant_name,
            kunde_id=None,  # Keine Kunden-ID bei Eingangsrechnungen
            kunde_name=lieferant_name,  # Für Kompatibilität
            rechnungsdatum=rechnungsdatum,
            faelligkeitsdatum=faelligkeitsdatum,
            netto_gesamt=netto_gesamt,
            mwst_gesamt=mwst_gesamt,
            brutto_gesamt=brutto_gesamt,
            bemerkungen=bemerkungen,
            status=RechnungsStatus.OFFEN,
            erstellt_von=current_user.username if current_user.is_authenticated else 'System'
        )

        db.session.add(rechnung)
        db.session.commit()

        flash(f"Eingangsrechnung {rechnung.rechnungsnummer} wurde erfasst!", "success")
        return redirect(url_for('rechnung.rechnungs_index', tab='eingang'))

    except Exception as e:
        db.session.rollback()
        logger.error(f"Fehler beim Erfassen der Eingangsrechnung: {str(e)}")
        flash(f"Fehler beim Erfassen: {str(e)}", "error")
        return redirect(url_for('rechnung.neue_eingangsrechnung'))

@rechnung_bp.route('/<int:rechnung_id>/bearbeiten')
def rechnung_bearbeiten(rechnung_id):
    """
    Rechnung bearbeiten
    """
    try:
        # TODO: Rechnung bearbeiten implementieren
        flash(f"Bearbeitung von Rechnung {rechnung_id} wird noch implementiert", "info")
        return redirect(url_for('rechnung.rechnungs_index'))
        
    except Exception as e:
        logger.error(f"Fehler beim Bearbeiten der Rechnung: {str(e)}")
        flash(f"Fehler beim Bearbeiten der Rechnung: {str(e)}", "error")
        return redirect(url_for('rechnung.rechnungs_index'))

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
    """
    Rechnung als bezahlt markieren
    """
    try:
        rechnung = Rechnung.query.get_or_404(rechnung_id)

        rechnung.status = RechnungsStatus.BEZAHLT
        rechnung.bezahlt_am = date.today()
        rechnung.bezahlt_betrag = rechnung.brutto_gesamt
        rechnung.bearbeitet_am = datetime.utcnow()
        rechnung.bearbeitet_von = current_user.username if current_user.is_authenticated else 'System'

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Rechnung wurde als bezahlt markiert'
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Markieren als bezahlt: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

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
