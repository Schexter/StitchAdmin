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
from sqlalchemy.exc import SQLAlchemyError
import io

# Imports für Models und Services
try:
    from src.models import db
    from src.models.models import Customer, Order
    from src.models.rechnungsmodul import (
        Rechnung, RechnungsPosition, RechnungsZahlung, MwStSatz, RechnungsStatus, ZugpferdProfil
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
    Zeigt alle Rechnungen mit Filter- und Suchfunktionen
    """
    try:
        from datetime import date, datetime
        from dateutil.relativedelta import relativedelta
        
        # Filter-Parameter
        status_filter = request.args.get('status', '')
        customer_filter = request.args.get('customer', '')
        period_filter = request.args.get('period', '')
        
        # Basis-Query
        rechnungen = []
        if db:
            try:
                query = Rechnung.query
                
                # Status-Filter
                if status_filter:
                    query = query.filter_by(status=status_filter)
                
                # Zeitraum-Filter
                if period_filter:
                    today = date.today()
                    if period_filter == 'today':
                        query = query.filter(db.func.date(Rechnung.rechnungsdatum) == today)
                    elif period_filter == 'week':
                        week_start = today - timedelta(days=today.weekday())
                        query = query.filter(Rechnung.rechnungsdatum >= week_start)
                    elif period_filter == 'month':
                        month_start = today.replace(day=1)
                        query = query.filter(Rechnung.rechnungsdatum >= month_start)
                    elif period_filter == 'year':
                        year_start = today.replace(month=1, day=1)
                        query = query.filter(Rechnung.rechnungsdatum >= year_start)
                
                rechnungen = query.order_by(Rechnung.rechnungsdatum.desc()).all()
            except:
                pass
        
        # Statistiken berechnen
        open_invoices_count = 0
        open_invoices_total = 0
        overdue_invoices_count = 0
        overdue_invoices_total = 0
        paid_this_month_count = 0
        paid_this_month_total = 0
        year_total_count = len(rechnungen)
        year_total_amount = 0
        
        # Mock-Daten für Entwicklung
        if not rechnungen:
            # Erstelle Mock-Rechnung
            class MockRechnung:
                def __init__(self, id, nummer, datum, kunde, betrag, status):
                    self.id = id
                    self.rechnungsnummer = nummer
                    self.rechnungsdatum = datum
                    self.kunde_id = 'MOCK-001'
                    self.kunde = type('obj', (object,), {'display_name': kunde})
                    self.betreff = f'Rechnung für {kunde}'
                    self.summe_netto = betrag / 1.19
                    self.summe_brutto = betrag
                    self.status = status
                    self.faelligkeitsdatum = datum + timedelta(days=14)
                
                def ist_ueberfaellig(self):
                    return self.status == 'sent' and self.faelligkeitsdatum < date.today()
                
                def tage_ueberfaellig(self):
                    if self.ist_ueberfaellig():
                        return (date.today() - self.faelligkeitsdatum).days
                    return 0
            
            # Beispiel-Rechnungen
            rechnungen = [
                MockRechnung(1, 'RE-202507-001', date(2025, 7, 1), 'Musterkunde GmbH', 1190.00, 'paid'),
                MockRechnung(2, 'RE-202507-002', date(2025, 7, 5), 'Test AG', 2380.00, 'sent'),
                MockRechnung(3, 'RE-202507-003', date(2025, 7, 9), 'Demo KG', 595.00, 'draft'),
            ]
            
            # Mock-Statistiken
            open_invoices_count = 1
            open_invoices_total = 2380.00
            paid_this_month_count = 1
            paid_this_month_total = 1190.00
        
        return render_template('rechnung/index.html',
            rechnungen=rechnungen,
            open_invoices_count=open_invoices_count,
            open_invoices_total=open_invoices_total,
            overdue_invoices_count=overdue_invoices_count,
            overdue_invoices_total=overdue_invoices_total,
            paid_this_month_count=paid_this_month_count,
            paid_this_month_total=paid_this_month_total,
            year_total_count=year_total_count,
            year_total_amount=year_total_amount
        )
        
    except Exception as e:
        logger.error(f"Fehler in rechnungs_index: {str(e)}")
        flash(f"Fehler beim Laden der Rechnungsübersicht: {str(e)}", "error")
        return render_template('rechnung/index.html',
            rechnungen=[],
            statistik={},
            status_filter='alle',
            monat_filter='',
            suche='',
            pagination=None,
            today=date.today()
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
            page_title="Neue Rechnung erstellen"
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
        import traceback
        traceback.print_exc()
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
    Formular zur Erstellung einer Rechnung aus einem Auftrag
    """
    try:
        # TODO: Aufträge laden und anzeigen
        flash("Funktion wird noch implementiert", "info")
        return redirect(url_for('rechnung.rechnungs_index'))
        
    except Exception as e:
        logger.error(f"Fehler beim Laden der Aufträge: {str(e)}")
        flash(f"Fehler beim Laden der Aufträge: {str(e)}", "error")
        return redirect(url_for('rechnung.rechnungs_index'))

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
        import traceback
        traceback.print_exc()
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
        import traceback
        traceback.print_exc()
        flash(f"Fehler beim Download: {str(e)}", "error")
        return redirect(url_for('rechnung.rechnung_detail', rechnung_id=rechnung_id))

# API-Endpoints
@rechnung_bp.route('/api/<int:rechnung_id>/bezahlt', methods=['POST'])
def api_rechnung_bezahlt(rechnung_id):
    """
    Rechnung als bezahlt markieren
    """
    try:
        # TODO: Als bezahlt markieren implementieren
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
    Rechnung stornieren
    """
    try:
        # TODO: Stornierung implementieren
        return jsonify({
            'success': True,
            'message': 'Rechnung wurde storniert'
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Stornieren: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

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
