# -*- coding: utf-8 -*-
"""
BUCHHALTUNG CONTROLLER
======================
Controller für Buchhaltung, Berichte und Exporte

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file, Response
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from decimal import Decimal
from functools import wraps
import io

from src.models import db

import logging
logger = logging.getLogger(__name__)

buchhaltung_bp = Blueprint('buchhaltung', __name__, url_prefix='/buchhaltung')


def admin_required(f):
    """Decorator: Nur Admins"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Nur Administratoren haben Zugriff auf die Buchhaltung.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# DASHBOARD
# ============================================================================

@buchhaltung_bp.route('/')
@login_required
@admin_required
def index():
    """Buchhaltungs-Dashboard"""
    from src.services.buchhaltung_service import BWAService, LiquiditaetsService
    
    heute = date.today()
    jahr = heute.year
    monat = heute.month
    
    try:
        bwa_service = BWAService()
        bwa_monat = bwa_service.berechne_bwa(jahr, monat=monat)
        bwa_jahr = bwa_service.berechne_bwa(jahr)
    except Exception as e:
        logger.error(f"BWA-Fehler: {e}")
        bwa_monat = None
        bwa_jahr = None
    
    try:
        liq_service = LiquiditaetsService()
        liquiditaet = liq_service.berechne_liquiditaet()
    except Exception as e:
        liquiditaet = None
    
    return render_template('buchhaltung/index.html',
                         bwa_monat=bwa_monat,
                         bwa_jahr=bwa_jahr,
                         liquiditaet=liquiditaet,
                         aktueller_monat=monat,
                         aktuelles_jahr=jahr)


# ============================================================================
# BUCHUNGSJOURNAL
# ============================================================================

@buchhaltung_bp.route('/journal')
@login_required
@admin_required
def journal():
    """Buchungsjournal"""
    from src.models.buchhaltung import Buchung, Konto
    
    jahr = request.args.get('jahr', date.today().year, type=int)
    monat = request.args.get('monat', type=int)
    
    query = Buchung.query.filter(Buchung.ist_storniert == False)
    
    if jahr:
        query = query.filter(db.extract('year', Buchung.buchungsdatum) == jahr)
    if monat:
        query = query.filter(db.extract('month', Buchung.buchungsdatum) == monat)
    
    buchungen = query.order_by(Buchung.buchungsdatum.desc()).limit(500).all()
    konten = Konto.query.filter_by(ist_aktiv=True).order_by(Konto.kontonummer).all()
    
    return render_template('buchhaltung/journal.html',
                         buchungen=buchungen,
                         konten=konten,
                         filter_jahr=jahr,
                         filter_monat=monat)


# ============================================================================
# BWA
# ============================================================================

@buchhaltung_bp.route('/bwa')
@login_required
@admin_required
def bwa():
    """BWA-Übersicht"""
    from src.services.buchhaltung_service import BWAService
    
    jahr = request.args.get('jahr', date.today().year, type=int)
    monat = request.args.get('monat', type=int)
    
    bwa_service = BWAService()
    
    try:
        if monat:
            bwa_daten = bwa_service.berechne_bwa(jahr, monat=monat)
        else:
            bwa_daten = bwa_service.berechne_bwa(jahr)
        
        vergleich = bwa_service.berechne_bwa_vergleich(jahr)
    except Exception as e:
        flash(f'Fehler: {e}', 'danger')
        bwa_daten = None
        vergleich = None
    
    return render_template('buchhaltung/bwa.html',
                         bwa=bwa_daten,
                         vergleich=vergleich,
                         filter_jahr=jahr,
                         filter_monat=monat)


@buchhaltung_bp.route('/bwa/export/excel')
@login_required
@admin_required
def bwa_export_excel():
    """BWA als Excel"""
    from src.services.buchhaltung_service import BWAService
    from src.services.buchhaltung_export_service import ExcelExporter
    
    jahr = request.args.get('jahr', date.today().year, type=int)
    
    bwa_service = BWAService()
    bwa_daten = bwa_service.berechne_bwa(jahr)
    
    exporter = ExcelExporter()
    excel_bytes = exporter.export_bwa(bwa_daten)
    
    return send_file(
        io.BytesIO(excel_bytes),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'BWA_{jahr}.xlsx'
    )


# ============================================================================
# UST-VORANMELDUNG
# ============================================================================

@buchhaltung_bp.route('/ust-va')
@login_required
@admin_required
def ust_voranmeldung():
    """USt-Voranmeldung"""
    from src.models.buchhaltung import UStVoranmeldung
    
    jahr = request.args.get('jahr', date.today().year, type=int)
    voranmeldungen = UStVoranmeldung.query.filter_by(jahr=jahr).all()
    
    return render_template('buchhaltung/ust_voranmeldung.html',
                         voranmeldungen=voranmeldungen,
                         filter_jahr=jahr)


@buchhaltung_bp.route('/ust-va/<int:id>/export')
@login_required
@admin_required
def ust_export(id):
    """USt-VA als ELSTER-CSV"""
    from src.models.buchhaltung import UStVoranmeldung
    from src.services.buchhaltung_export_service import ELSTERExporter
    
    va = UStVoranmeldung.query.get_or_404(id)
    exporter = ELSTERExporter()
    csv_content = exporter.export_ust_voranmeldung(va)
    
    return Response(csv_content, mimetype='text/csv',
                   headers={'Content-Disposition': f'attachment; filename=UStVA_{va.jahr}.csv'})


# ============================================================================
# EXPORTE
# ============================================================================

@buchhaltung_bp.route('/export')
@login_required
@admin_required
def export_uebersicht():
    """Export-Übersicht"""
    return render_template('buchhaltung/export.html')


@buchhaltung_bp.route('/export/datev', methods=['POST'])
@login_required
@admin_required
def export_datev():
    """DATEV-Export"""
    from src.models.buchhaltung import Buchung
    from src.services.buchhaltung_export_service import DATEVExporter
    
    datum_von = datetime.strptime(request.form['datum_von'], '%Y-%m-%d').date()
    datum_bis = datetime.strptime(request.form['datum_bis'], '%Y-%m-%d').date()
    
    buchungen = Buchung.query.filter(
        Buchung.buchungsdatum >= datum_von,
        Buchung.buchungsdatum <= datum_bis,
        Buchung.ist_storniert == False
    ).all()
    
    exporter = DATEVExporter()
    csv_content = exporter.export_buchungen(buchungen, datum_von, datum_bis)
    
    return Response(csv_content, mimetype='text/csv',
                   headers={'Content-Disposition': f'attachment; filename=DATEV_Export.csv'})


@buchhaltung_bp.route('/export/gobd', methods=['POST'])
@login_required
@admin_required
def export_gobd():
    """GoBD-Export"""
    from src.models.buchhaltung import Buchung
    from src.models.models import Customer, Supplier
    from src.services.buchhaltung_export_service import GoBDExporter
    import zipfile
    
    jahr = int(request.form.get('jahr', date.today().year))
    
    buchungen = Buchung.query.filter(db.extract('year', Buchung.buchungsdatum) == jahr).all()
    kunden = Customer.query.all()
    lieferanten = Supplier.query.all()
    
    exporter = GoBDExporter()
    paket = exporter.export_gobd_paket(jahr, buchungen, kunden, lieferanten)
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        for filename, content in paket.items():
            zf.writestr(filename, content)
    zip_buffer.seek(0)
    
    return send_file(zip_buffer, mimetype='application/zip',
                    as_attachment=True, download_name=f'GoBD_{jahr}.zip')


# ============================================================================
# KALKULATIONEN
# ============================================================================

@buchhaltung_bp.route('/kalkulation')
@login_required
@admin_required
def kalkulation():
    """Kalkulationen"""
    return render_template('buchhaltung/kalkulation.html')


@buchhaltung_bp.route('/kalkulation/stundensatz', methods=['GET', 'POST'])
@login_required
@admin_required
def kalkulation_stundensatz():
    """Stundensatz-Kalkulation"""
    from src.services.buchhaltung_service import KalkulationsService
    
    ergebnis = None
    if request.method == 'POST':
        kalk = KalkulationsService()
        ergebnis = kalk.berechne_stundensatz(
            jahresgehalt=Decimal(request.form.get('jahresgehalt', '50000').replace(',', '.')),
            arbeitsstunden_jahr=int(request.form.get('arbeitsstunden', '1720')),
            gemeinkosten_prozent=Decimal(request.form.get('gemeinkosten', '50')),
            gewinn_prozent=Decimal(request.form.get('gewinn', '20'))
        )
    
    return render_template('buchhaltung/kalkulation_stundensatz.html', ergebnis=ergebnis)


@buchhaltung_bp.route('/kalkulation/stickpreis', methods=['GET', 'POST'])
@login_required
@admin_required
def kalkulation_stickpreis():
    """Stickpreis-Kalkulation"""
    from src.services.buchhaltung_service import KalkulationsService
    
    ergebnis = None
    if request.method == 'POST':
        kalk = KalkulationsService()
        ergebnis = kalk.berechne_stickpreis(
            stichzahl=int(request.form.get('stichzahl', '10000')),
            farbwechsel=int(request.form.get('farbwechsel', '5')),
            preis_pro_1000=Decimal(request.form.get('preis_1000', '0.80').replace(',', '.')),
            preis_farbwechsel=Decimal(request.form.get('preis_farbwechsel', '0.50').replace(',', '.')),
            mindestpreis=Decimal(request.form.get('mindestpreis', '5.00').replace(',', '.')),
            einrichtekosten=Decimal(request.form.get('einrichtekosten', '0').replace(',', '.')),
            menge=int(request.form.get('menge', '100'))
        )
    
    return render_template('buchhaltung/kalkulation_stickpreis.html', ergebnis=ergebnis)


@buchhaltung_bp.route('/kalkulation/deckungsbeitrag', methods=['GET', 'POST'])
@login_required
@admin_required
def kalkulation_deckungsbeitrag():
    """Deckungsbeitrag"""
    from src.services.buchhaltung_service import KalkulationsService
    
    ergebnis = None
    if request.method == 'POST':
        kalk = KalkulationsService()
        ergebnis = kalk.berechne_deckungsbeitrag(
            umsatz=Decimal(request.form.get('umsatz', '0').replace(',', '.')),
            variable_kosten=Decimal(request.form.get('variable_kosten', '0').replace(',', '.')),
            fixkosten=Decimal(request.form.get('fixkosten', '0').replace(',', '.'))
        )
    
    return render_template('buchhaltung/kalkulation_deckungsbeitrag.html', ergebnis=ergebnis)


# ============================================================================
# LIQUIDITÄT & FINANZPLAN
# ============================================================================

@buchhaltung_bp.route('/liquiditaet')
@login_required
@admin_required
def liquiditaet():
    """Liquidität"""
    from src.services.buchhaltung_service import LiquiditaetsService
    
    liq_service = LiquiditaetsService()
    liquiditaet = liq_service.berechne_liquiditaet()
    cashflow = liq_service.berechne_cashflow(date.today().year)
    
    return render_template('buchhaltung/liquiditaet.html',
                         liquiditaet=liquiditaet, cashflow=cashflow)


@buchhaltung_bp.route('/finanzplan')
@login_required
@admin_required
def finanzplan():
    """Finanzplanung"""
    from src.services.buchhaltung_service import FinanzplanService
    
    jahr = request.args.get('jahr', date.today().year, type=int)
    fp_service = FinanzplanService()
    vergleich = fp_service.plan_ist_vergleich(jahr)
    
    return render_template('buchhaltung/finanzplan.html',
                         vergleich=vergleich, filter_jahr=jahr)


# ============================================================================
# KONTENPLAN
# ============================================================================

@buchhaltung_bp.route('/kontenplan')
@login_required
@admin_required
def kontenplan():
    """Kontenplan"""
    from src.models.buchhaltung import Konto
    
    konten = Konto.query.filter_by(ist_aktiv=True).order_by(Konto.kontonummer).all()
    return render_template('buchhaltung/kontenplan.html', konten=konten)


@buchhaltung_bp.route('/kontenplan/init', methods=['POST'])
@login_required
@admin_required
def kontenplan_init():
    """SKR03 initialisieren"""
    from src.models.buchhaltung import init_kontenplan
    
    init_kontenplan('SKR03')
    flash('Kontenplan (SKR03) initialisiert.', 'success')
    return redirect(url_for('buchhaltung.kontenplan'))


# ============================================================================
# API
# ============================================================================

@buchhaltung_bp.route('/api/stickpreis')
@login_required
def api_stickpreis():
    """API: Stickpreis berechnen"""
    from src.services.buchhaltung_service import KalkulationsService
    
    kalk = KalkulationsService()
    ergebnis = kalk.berechne_stickpreis(
        stichzahl=request.args.get('stichzahl', 10000, type=int),
        farbwechsel=request.args.get('farbwechsel', 5, type=int),
        menge=request.args.get('menge', 100, type=int)
    )
    
    return jsonify({
        'stueckpreis_netto': float(ergebnis['stueckpreis_netto']),
        'stueckpreis_brutto': float(ergebnis['stueckpreis_brutto']),
        'auftragssumme_brutto': float(ergebnis['auftragssumme_brutto'])
    })


# ============================================================================
# TEXTILDRUCK-KALKULATION
# ============================================================================

@buchhaltung_bp.route('/kalkulation/textildruck', methods=['GET', 'POST'])
@login_required
@admin_required
def kalkulation_textildruck():
    """Textildruck-Kalkulation (Siebdruck, DTG, Flex/Flock)"""
    from src.services.textildruck_kalkulation import TextildruckKalkulator
    from src.services.wettbewerb_preise import WettbewerbsPreisService
    
    ergebnis = None
    wettbewerb = None
    
    if request.method == 'POST':
        verfahren = request.form.get('verfahren', 'siebdruck')
        menge = int(request.form.get('menge', 100))
        textil_ek = Decimal(request.form.get('textil_ek', '0').replace(',', '.'))
        gewinn = float(request.form.get('gewinn', 30))
        
        kalk = TextildruckKalkulator()
        
        try:
            if verfahren == 'siebdruck':
                anzahl_farben = int(request.form.get('anzahl_farben', 2))
                ergebnis = kalk.berechne_siebdruck(
                    menge=menge,
                    anzahl_farben=anzahl_farben,
                    textil_ek=textil_ek,
                    gewinn_prozent=gewinn
                )
            
            elif verfahren == 'dtg':
                druckgroesse = float(request.form.get('druckgroesse', 400))
                dunkles_textil = request.form.get('dunkles_textil') == 'on'
                ergebnis = kalk.berechne_dtg(
                    menge=menge,
                    druckgroesse_cm2=druckgroesse,
                    dunkles_textil=dunkles_textil,
                    textil_ek=textil_ek,
                    gewinn_prozent=gewinn
                )
            
            elif verfahren in ('flex', 'flock'):
                flaeche = float(request.form.get('flaeche', 150))
                ist_flock = request.form.get('ist_flock') == 'on'
                ergebnis = kalk.berechne_flex_flock(
                    menge=menge,
                    flaeche_cm2=flaeche,
                    ist_flock=ist_flock,
                    textil_ek=textil_ek,
                    gewinn_prozent=gewinn
                )
            
            # Wettbewerbsvergleich
            if ergebnis:
                try:
                    wb_service = WettbewerbsPreisService()
                    wettbewerb = wb_service.vergleiche_mit_wettbewerb(
                        eigener_preis=ergebnis['vk_pro_stueck_brutto'],
                        verfahren=verfahren,
                        menge=menge
                    )
                except Exception as e:
                    logger.warning(f"Wettbewerbsvergleich fehlgeschlagen: {e}")
        
        except Exception as e:
            flash(f'Berechnungsfehler: {e}', 'danger')
    
    return render_template('buchhaltung/kalkulation_textildruck.html',
                         ergebnis=ergebnis,
                         wettbewerb=wettbewerb)


@buchhaltung_bp.route('/wettbewerb')
@login_required
@admin_required
def wettbewerb_preise():
    """Wettbewerbs-Preise verwalten"""
    from src.services.wettbewerb_preise import WettbewerbsPreisService, WettbewerbsPreisDB
    
    verfahren = request.args.get('verfahren', 'siebdruck')
    
    # Alle Preise laden
    preise = WettbewerbsPreisDB.query.filter_by(verfahren=verfahren).order_by(
        WettbewerbsPreisDB.menge, WettbewerbsPreisDB.stueckpreis_brutto
    ).all()
    
    # Marktüberblick
    wb_service = WettbewerbsPreisService()
    ueberblick = wb_service.get_marktueberblick(verfahren)
    
    return render_template('buchhaltung/wettbewerb.html',
                         preise=preise,
                         ueberblick=ueberblick,
                         filter_verfahren=verfahren)


@buchhaltung_bp.route('/wettbewerb/neu', methods=['POST'])
@login_required
@admin_required
def wettbewerb_preis_neu():
    """Neuen Wettbewerbspreis manuell erfassen"""
    from src.services.wettbewerb_preise import WettbewerbsPreisService
    
    wb_service = WettbewerbsPreisService()
    
    erfolg = wb_service.speichere_preis(
        anbieter=request.form.get('anbieter', ''),
        verfahren=request.form.get('verfahren', 'siebdruck'),
        menge=int(request.form.get('menge', 100)),
        stueckpreis_brutto=Decimal(request.form.get('preis', '0').replace(',', '.')),
        produkt=request.form.get('produkt', ''),
        lieferzeit_tage=int(request.form.get('lieferzeit', 0)),
        quelle_url=request.form.get('url', ''),
        ist_manuell=True
    )
    
    if erfolg:
        flash('Wettbewerbspreis gespeichert.', 'success')
    else:
        flash('Fehler beim Speichern.', 'danger')
    
    return redirect(url_for('buchhaltung.wettbewerb_preise', verfahren=request.form.get('verfahren')))


# ============================================================================
# KONTENRAHMEN
# ============================================================================

@buchhaltung_bp.route('/kontenplan/setup', methods=['GET', 'POST'])
@login_required
@admin_required
def kontenplan_setup():
    """Kontenrahmen-Auswahl und Initialisierung"""
    from src.services.kontenrahmen_service import KontenrahmenService
    from src.models.buchhaltung import Konto
    
    kr_service = KontenrahmenService()
    branchen = kr_service.get_branchen()
    
    # Aktueller Stand
    anzahl_konten = Konto.query.count()
    
    if request.method == 'POST':
        rahmen = request.form.get('kontenrahmen', 'SKR03')
        branche = request.form.get('branche')
        
        ergebnis = kr_service.initialisiere_kontenrahmen(rahmen, branche)
        
        flash(f'Kontenrahmen {rahmen} initialisiert: {ergebnis["angelegt"]} Konten angelegt, '
              f'{ergebnis["uebersprungen"]} übersprungen.', 'success')
        
        return redirect(url_for('buchhaltung.kontenplan'))
    
    return render_template('buchhaltung/kontenplan_setup.html',
                         branchen=branchen,
                         anzahl_konten=anzahl_konten)
