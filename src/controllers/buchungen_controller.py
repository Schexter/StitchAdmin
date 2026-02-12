# -*- coding: utf-8 -*-
"""
Buchungen Controller - Buchungsjournal und Auswertungen
"""

from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required
from datetime import date, datetime, timedelta
from io import BytesIO, StringIO
import csv

from src.services.buchungs_service import BuchungsService
from src.models.buchungsmodul import Kontenrahmen

buchungen_bp = Blueprint('buchungen', __name__, url_prefix='/buchungen')

@buchungen_bp.route('/')
@login_required
def index():
    """Buchungsjournal - Hauptseite"""
    # Standard: Aktueller Monat
    heute = date.today()
    monat_start = heute.replace(day=1)
    
    # Lade Konten für Filter
    konten = Kontenrahmen.query.filter_by(aktiv=True).order_by(Kontenrahmen.konto_nummer).all()
    
    # Statistiken
    stats = BuchungsService.get_statistiken(monat_start, heute)
    
    return render_template('buchungen/index.html',
        konten=konten,
        stats=stats,
        datum_von=monat_start,
        datum_bis=heute
    )

@buchungen_bp.route('/api/buchungen')
@login_required
def api_buchungen():
    """API: Lädt Buchungen mit Filtern"""
    # Filter-Parameter
    konto = request.args.get('konto')
    datum_von = request.args.get('datum_von')
    datum_bis = request.args.get('datum_bis')
    beleg_typ = request.args.get('beleg_typ')
    limit = request.args.get('limit', type=int, default=100)
    
    # Parse Datum
    if datum_von:
        datum_von = datetime.strptime(datum_von, '%Y-%m-%d').date()
    if datum_bis:
        datum_bis = datetime.strptime(datum_bis, '%Y-%m-%d').date()
    
    # Lade Buchungen
    buchungen = BuchungsService.get_buchungen(
        konto_nummer=konto,
        datum_von=datum_von,
        datum_bis=datum_bis,
        beleg_typ=beleg_typ,
        limit=limit
    )
    
    # Konvertiere zu JSON
    result = [{
        'id': b.id,
        'datum': b.buchungsdatum.isoformat(),
        'beleg': b.belegnummer,
        'konto_soll': b.konto_soll,
        'konto_haben': b.konto_haben,
        'betrag': float(b.betrag),
        'text': b.buchungstext,
        'typ': b.beleg_typ
    } for b in buchungen]
    
    return jsonify({'success': True, 'buchungen': result})

@buchungen_bp.route('/export/datev')
@login_required
def export_datev():
    """DATEV-Export"""
    datum_von = request.args.get('datum_von')
    datum_bis = request.args.get('datum_bis')
    
    if not datum_von or not datum_bis:
        return "Bitte Datum angeben", 400
    
    datum_von = datetime.strptime(datum_von, '%Y-%m-%d').date()
    datum_bis = datetime.strptime(datum_bis, '%Y-%m-%d').date()
    
    content, filename = BuchungsService.export_datev(datum_von, datum_bis)
    
    # Als Download zurückgeben
    output = BytesIO(content.encode('utf-8'))
    output.seek(0)
    
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

@buchungen_bp.route('/eingangsrechnung/neu', methods=['GET', 'POST'])
@login_required
def eingangsrechnung_neu():
    """Neue Eingangsrechnung buchen"""
    from decimal import Decimal
    from flask import flash, redirect, url_for

    if request.method == 'POST':
        try:
            # Hole Formulardaten
            lieferant = request.form.get('lieferant')
            rechnungsnummer = request.form.get('rechnungsnummer')
            rechnungsdatum_str = request.form.get('rechnungsdatum')
            netto_betrag = Decimal(request.form.get('netto_betrag'))
            mwst_satz = int(request.form.get('mwst_satz', 19))
            beschreibung = request.form.get('beschreibung')

            # Parse Datum
            rechnungsdatum = datetime.strptime(rechnungsdatum_str, '%Y-%m-%d').date()

            # Berechne MwSt
            mwst_betrag = netto_betrag * Decimal(mwst_satz) / Decimal(100)

            # Buche
            erfolg = BuchungsService.buche_eingangsrechnung(
                lieferant=lieferant,
                rechnungsnummer=rechnungsnummer,
                rechnungsdatum=rechnungsdatum,
                netto_betrag=netto_betrag,
                mwst_satz=mwst_satz,
                mwst_betrag=mwst_betrag,
                beschreibung=beschreibung
            )

            if erfolg:
                flash(f'Eingangsrechnung {rechnungsnummer} erfolgreich gebucht!', 'success')
                return redirect(url_for('buchungen.index'))
            else:
                flash('Fehler beim Buchen der Eingangsrechnung', 'danger')

        except Exception as e:
            flash(f'Fehler: {str(e)}', 'danger')

    return render_template('buchungen/eingangsrechnung_neu.html')

@buchungen_bp.route('/konten')
@login_required
def konten():
    """Konten-Übersicht"""
    konten = Kontenrahmen.query.filter_by(aktiv=True).order_by(Kontenrahmen.konto_art, Kontenrahmen.konto_nummer).all()

    # Gruppiere nach Konto-Art
    konten_grouped = {}
    for konto in konten:
        if konto.konto_art not in konten_grouped:
            konten_grouped[konto.konto_art] = []
        konten_grouped[konto.konto_art].append(konto)

    return render_template('buchungen/konten.html', konten_grouped=konten_grouped)
