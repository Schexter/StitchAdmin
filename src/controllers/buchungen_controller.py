# -*- coding: utf-8 -*-
"""
Buchungen Controller - Buchungsjournal und Auswertungen
"""

from flask import Blueprint, render_template, request, jsonify, send_file, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import date, datetime, timedelta
from io import BytesIO, StringIO
from decimal import Decimal
import csv
import os
import uuid

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

@buchungen_bp.route('/eingangsrechnung/wizard')
@login_required
def eingangsrechnung_wizard():
    """Eingangsrechnung Wizard - Drag & Drop mit OCR"""
    from src.services.eingangsrechnung_ocr_service import KATEGORIEN, ZAHLUNGSART_KONTEN
    return render_template('buchungen/eingangsrechnung_wizard.html',
                           kategorien=KATEGORIEN,
                           zahlungsarten=ZAHLUNGSART_KONTEN)


@buchungen_bp.route('/eingangsrechnung/upload', methods=['POST'])
@login_required
def eingangsrechnung_upload():
    """PDF oder Bild hochladen und Daten extrahieren"""
    from src.services.eingangsrechnung_ocr_service import extrahiere_rechnungsdaten, extrahiere_aus_bild, berechne_fehlende_werte

    # Datei aus 'pdf' oder 'datei' Feld
    datei = request.files.get('pdf') or request.files.get('datei')
    if not datei:
        return jsonify({'success': False, 'error': 'Keine Datei uebermittelt'}), 400

    erlaubte = {'.pdf', '.jpg', '.jpeg', '.png', '.webp', '.heic'}
    ext = os.path.splitext(datei.filename.lower())[1]
    if ext not in erlaubte:
        return jsonify({'success': False, 'error': f'Erlaubte Formate: PDF, JPG, PNG'}), 400

    # Temporaere Datei speichern
    upload_dir = os.path.join(current_app.root_path, '..', 'instance', 'eingangsrechnungen')
    os.makedirs(upload_dir, exist_ok=True)

    dateiname = f'{uuid.uuid4().hex}_{datei.filename}'
    pfad = os.path.join(upload_dir, dateiname)
    datei.save(pfad)

    # OCR je nach Dateityp
    if ext == '.pdf':
        daten = extrahiere_rechnungsdaten(pfad)
    else:
        daten = extrahiere_aus_bild(pfad)

    daten = berechne_fehlende_werte(
        daten.get('netto', ''), daten.get('mwst_betrag', ''),
        daten.get('brutto', ''), daten.get('mwst_satz', 19)
    ) | daten

    daten['temp_datei'] = dateiname
    daten['original_dateiname'] = datei.filename

    return jsonify({'success': True, 'daten': daten})


# Legacy-Route fuer Abwaertskompatibilitaet
@buchungen_bp.route('/eingangsrechnung/upload-pdf', methods=['POST'])
@login_required
def eingangsrechnung_upload_pdf():
    """Redirect auf neue Upload-Route"""
    return eingangsrechnung_upload()


@buchungen_bp.route('/eingangsrechnung/buchen', methods=['POST'])
@login_required
def eingangsrechnung_buchen():
    """Eingangsrechnung final buchen und PDF archivieren - nutzt RechnungService"""
    from src.services.rechnung_service import RechnungService

    try:
        kategorie_key = request.form.get('kategorie', 'sonstiges')
        lieferant = request.form.get('lieferant', '').strip()
        rechnungsnummer = request.form.get('rechnungsnummer', '').strip()
        rechnungsdatum_str = request.form.get('rechnungsdatum', '')
        netto_str = request.form.get('netto', '0').replace(',', '.')
        mwst_str = request.form.get('mwst_betrag', '0').replace(',', '.')
        mwst_satz = int(request.form.get('mwst_satz', 19))
        temp_datei = request.form.get('temp_datei', '')

        netto = Decimal(netto_str)
        mwst_betrag = Decimal(mwst_str)
        brutto = netto + mwst_betrag
        rechnungsdatum = date.fromisoformat(rechnungsdatum_str) if rechnungsdatum_str else date.today()

        # Zentral ueber RechnungService buchen (eine Quelle der Wahrheit)
        rechnung, fehler = RechnungService.erfasse_eingangsrechnung(
            lieferant_name=lieferant,
            rechnungsnummer=rechnungsnummer,
            rechnungsdatum=rechnungsdatum,
            netto=netto,
            mwst_betrag=mwst_betrag,
            mwst_satz=mwst_satz,
            kategorie=kategorie_key,
            auto_buchen=True
        )

        if not rechnung:
            flash(f'Fehler beim Buchen: {fehler}', 'danger')
            return redirect(url_for('buchungen.eingangsrechnung_wizard'))

        # PDF archivieren
        if temp_datei:
            upload_dir = os.path.join(current_app.root_path, '..', 'instance', 'eingangsrechnungen')
            src_pfad = os.path.join(upload_dir, temp_datei)
            if os.path.exists(src_pfad):
                belegnummer = rechnung.rechnungsnummer
                archiv_name = f'{rechnungsdatum.strftime("%Y%m%d")}_{belegnummer}_{temp_datei}'
                archiv_pfad = os.path.join(upload_dir, archiv_name)
                os.rename(src_pfad, archiv_pfad)

        flash(f'Eingangsrechnung {rechnung.rechnungsnummer} von {lieferant} gebucht ({brutto:.2f} EUR brutto).', 'success')
        return redirect(url_for('buchungen.index'))

    except Exception as e:
        from src.models import db
        db.session.rollback()
        flash(f'Fehler beim Buchen: {e}', 'danger')
        return redirect(url_for('buchungen.eingangsrechnung_wizard'))


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
