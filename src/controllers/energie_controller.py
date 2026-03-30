# -*- coding: utf-8 -*-
"""
Energie-Controller: Stromzähler, Ablesungen, Tarifberechnung, Erinnerungen
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import date, datetime
from decimal import Decimal
from src.models import db
from src.models.energie import StromAblesung, StromTarif

energie_bp = Blueprint('energie', __name__, url_prefix='/energie')


def _get_aktiver_tarif(fuer_datum=None):
    """Gibt den zum Datum gültigen Tarif zurück"""
    wenn = fuer_datum or date.today()
    return StromTarif.query.filter(
        StromTarif.gueltig_ab <= wenn
    ).order_by(StromTarif.gueltig_ab.desc()).first()


def _berechne_kosten(kwh, tarif):
    """Berechnet Kosten für kWh-Verbrauch"""
    if not tarif or not kwh:
        return 0.0
    return float(kwh) * tarif.gesamtpreis_kwh


@energie_bp.route('/')
@login_required
def index():
    """Stromzähler-Übersicht mit Verbrauchsanalyse"""
    heute = date.today()

    # Alle Ablesungen sortiert (neueste zuerst)
    ablesungen = StromAblesung.query.order_by(StromAblesung.ablesedatum.desc()).all()

    # Verbrauchsperioden berechnen (Differenz zwischen je zwei Ablesungen)
    perioden = []
    for i in range(len(ablesungen) - 1):
        neu = ablesungen[i]
        alt = ablesungen[i + 1]
        verbrauch_kwh = float(neu.zaehlerstand) - float(alt.zaehlerstand)
        tage = (neu.ablesedatum - alt.ablesedatum).days

        tarif = _get_aktiver_tarif(alt.ablesedatum)
        kosten_arbeit = Decimal(str(_berechne_kosten(verbrauch_kwh, tarif)))

        # Grundgebühr anteilig für die Tage
        grundgebuehr_anteil = Decimal('0')
        if tarif and tarif.grundgebuehr_monat:
            grundgebuehr_anteil = Decimal(str(tarif.grundgebuehr_monat)) * Decimal(str(tage)) / Decimal('30')

        kosten_gesamt = kosten_arbeit + grundgebuehr_anteil

        perioden.append({
            'von': alt.ablesedatum,
            'bis': neu.ablesedatum,
            'tage': tage,
            'verbrauch_kwh': round(verbrauch_kwh, 1),
            'verbrauch_kwh_tag': round(verbrauch_kwh / tage, 2) if tage > 0 else 0,
            'kosten_arbeit': float(kosten_arbeit),
            'grundgebuehr': float(grundgebuehr_anteil),
            'kosten_gesamt': float(kosten_gesamt),
            'tarif': tarif,
        })

    # Erinnerung: Ablesung diesen Monat?
    ablesung_diesen_monat = StromAblesung.query.filter(
        db.extract('year', StromAblesung.ablesedatum) == heute.year,
        db.extract('month', StromAblesung.ablesedatum) == heute.month
    ).first()

    # Aktiver Tarif
    aktiver_tarif = _get_aktiver_tarif()

    # Jahresverbrauch (aktuelles Jahr)
    ablesungen_dieses_jahr = StromAblesung.query.filter(
        db.extract('year', StromAblesung.ablesedatum) == heute.year
    ).order_by(StromAblesung.ablesedatum).all()
    jahresverbrauch = 0
    if len(ablesungen_dieses_jahr) >= 2:
        jahresverbrauch = float(ablesungen_dieses_jahr[-1].zaehlerstand) - float(ablesungen_dieses_jahr[0].zaehlerstand)

    # Chart-Daten: letzte 12 Perioden
    chart_data = {
        'labels': [f"{p['von'].strftime('%b')}-{p['bis'].strftime('%b %y')}" for p in perioden[:12]],
        'kwh': [p['verbrauch_kwh'] for p in perioden[:12]],
        'kosten': [round(p['kosten_gesamt'], 2) for p in perioden[:12]],
    }
    # Zeitreihe umkehren (chronologisch)
    chart_data['labels'].reverse()
    chart_data['kwh'].reverse()
    chart_data['kosten'].reverse()

    return render_template('energie/index.html',
                         ablesungen=ablesungen,
                         perioden=perioden,
                         aktiver_tarif=aktiver_tarif,
                         ablesung_diesen_monat=ablesung_diesen_monat,
                         jahresverbrauch=round(jahresverbrauch, 1),
                         chart_data=chart_data,
                         heute=heute)


@energie_bp.route('/ablesung/neu', methods=['GET', 'POST'])
@login_required
def ablesung_neu():
    """Neue Zählerstand-Ablesung erfassen"""
    if request.method == 'POST':
        try:
            zaehlerstand = Decimal(request.form['zaehlerstand'].replace(',', '.'))
            ablesedatum = date.fromisoformat(request.form.get('ablesedatum', date.today().isoformat()))

            # Plausibilitätsprüfung: Stand muss größer als letzte Ablesung sein
            letzte = StromAblesung.query.order_by(StromAblesung.ablesedatum.desc()).first()
            if letzte and zaehlerstand < letzte.zaehlerstand:
                flash(f'Zählerstand ({zaehlerstand} kWh) ist kleiner als die letzte Ablesung ({letzte.zaehlerstand} kWh). Bitte prüfen.', 'warning')
                return redirect(url_for('energie.ablesung_neu'))

            ablesung = StromAblesung(
                ablesedatum=ablesedatum,
                zaehlerstand=zaehlerstand,
                kommentar=request.form.get('kommentar', '').strip() or None,
                erstellt_von=current_user.username
            )
            db.session.add(ablesung)
            db.session.commit()
            flash(f'Ablesung {zaehlerstand} kWh am {ablesedatum.strftime("%d.%m.%Y")} gespeichert.', 'success')
            return redirect(url_for('energie.index'))
        except (ValueError, TypeError) as e:
            flash(f'Ungültige Eingabe: {e}', 'danger')

    letzte_ablesung = StromAblesung.query.order_by(StromAblesung.ablesedatum.desc()).first()
    return render_template('energie/ablesung_neu.html', letzte_ablesung=letzte_ablesung, heute=date.today())


@energie_bp.route('/ablesung/<int:id>/loeschen', methods=['POST'])
@login_required
def ablesung_loeschen(id):
    """Ablesung löschen"""
    ablesung = StromAblesung.query.get_or_404(id)
    db.session.delete(ablesung)
    db.session.commit()
    flash('Ablesung gelöscht.', 'info')
    return redirect(url_for('energie.index'))


@energie_bp.route('/tarif', methods=['GET', 'POST'])
@login_required
def tarif():
    """Tarif-Konfiguration"""
    if request.method == 'POST':
        try:
            neuer_tarif = StromTarif(
                name=request.form.get('name', 'Tarif').strip(),
                grundgebuehr_monat=Decimal(request.form.get('grundgebuehr', '0').replace(',', '.')),
                arbeitspreis_kwh=Decimal(request.form.get('arbeitspreis', '0').replace(',', '.')),
                netzentgelt_kwh=Decimal(request.form.get('netzentgelt', '0').replace(',', '.')),
                gueltig_ab=date.fromisoformat(request.form.get('gueltig_ab', date.today().isoformat())),
                anbieter=request.form.get('anbieter', '').strip() or None,
                notiz=request.form.get('notiz', '').strip() or None,
            )
            db.session.add(neuer_tarif)
            db.session.commit()
            flash('Tarif gespeichert.', 'success')
            return redirect(url_for('energie.index'))
        except (ValueError, TypeError) as e:
            flash(f'Ungültige Eingabe: {e}', 'danger')

    alle_tarife = StromTarif.query.order_by(StromTarif.gueltig_ab.desc()).all()
    aktiver_tarif = _get_aktiver_tarif()
    return render_template('energie/tarif.html', alle_tarife=alle_tarife, aktiver_tarif=aktiver_tarif, heute=date.today())
