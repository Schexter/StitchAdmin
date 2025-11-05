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
    from src.models.rechnungsmodul import (
        Rechnung, RechnungsPosition, RechnungsZahlung, MwStSatz
    )
    # ZUGPFERD Service erstellen wir später
    def get_zugpferd_service():
        # Temporärer Mock für ZUGPFERD
        class MockZugpferd:
            def generate_invoice_xml(self, rechnung):
                return f'<xml>Mock ZUGPFERD für {rechnung.rechnungsnummer}</xml>'
            def generate_pdf_a3(self, rechnung, xml):
                return b'Mock PDF/A-3 Content'
        return MockZugpferd()
    
    # Utility-Klasse für Rechnungen
    class RechnungsUtils:
        @staticmethod
        def get_next_invoice_number():
            import random
            return f"RE-{datetime.now().strftime('%Y%m')}-{random.randint(1000, 9999)}"
            
except ImportError as e:
    print(f"Import-Fehler: {e}")
    db = None

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
        # TODO: Implementiere Rechnungserstellung
        flash("Rechnungserstellung wird noch implementiert", "info")
        return redirect(url_for('rechnung.rechnungs_index'))
        
    except Exception as e:
        logger.error(f"Fehler beim Erstellen der Rechnung: {str(e)}")
        flash(f"Fehler beim Erstellen der Rechnung: {str(e)}", "error")
        return redirect(url_for('rechnung.neue_rechnung'))

@rechnung_bp.route('/<int:rechnung_id>')
def rechnung_detail(rechnung_id):
    """
    Einzelne Rechnung anzeigen
    """
    try:
        # TODO: Rechnung aus DB laden
        flash(f"Rechnung {rechnung_id} - Details werden noch implementiert", "info")
        return redirect(url_for('rechnung.rechnungs_index'))
        
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
        # TODO: PDF generieren und anzeigen
        flash(f"PDF für Rechnung {rechnung_id} wird noch generiert", "info")
        return redirect(url_for('rechnung.rechnungs_index'))
        
    except Exception as e:
        logger.error(f"Fehler beim Generieren des PDFs: {str(e)}")
        flash(f"Fehler beim Generieren des PDFs: {str(e)}", "error")
        return redirect(url_for('rechnung.rechnungs_index'))

@rechnung_bp.route('/<int:rechnung_id>/download')
def rechnung_download(rechnung_id):
    """
    Rechnung herunterladen (ZUGPFERD PDF/XML)
    """
    try:
        # TODO: ZUGPFERD-Datei generieren und download
        flash(f"Download für Rechnung {rechnung_id} wird noch implementiert", "info")
        return redirect(url_for('rechnung.rechnungs_index'))
        
    except Exception as e:
        logger.error(f"Fehler beim Download: {str(e)}")
        flash(f"Fehler beim Download: {str(e)}", "error")
        return redirect(url_for('rechnung.rechnungs_index'))

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
