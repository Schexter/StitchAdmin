# -*- coding: utf-8 -*-
"""
AUFTRAGSBESTÄTIGUNG CONTROLLER (Document-Workflow Integration)
==============================================================
Verwaltung von Auftragsbestätigungen mit dem BusinessDocument-System:
- Erstellen aus Angebot
- Manuell erstellen
- CRUD-Operationen
- PDF-Generierung
- Status-Workflow
- Lieferschein/Rechnung erstellen

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file, current_app
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, date, timedelta
from decimal import Decimal
import os
import io

from src.models import db
from src.models.models import Customer, Article, Order, OrderItem

# Document-Workflow Models
try:
    from src.models.document_workflow import (
        Nummernkreis, Zahlungsbedingung, BusinessDocument, DocumentPosition, DocumentPayment,
        DokumentTyp, DokumentStatus, PositionsTyp, MwStKennzeichen
    )
    WORKFLOW_AVAILABLE = True
except ImportError:
    WORKFLOW_AVAILABLE = False

import logging
logger = logging.getLogger(__name__)

# Blueprint
auftraege_bp = Blueprint('auftraege', __name__, url_prefix='/auftraege')


def workflow_required(f):
    """Decorator: Prüft ob Document-Workflow verfügbar"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not WORKFLOW_AVAILABLE:
            flash('Document-Workflow nicht verfügbar. Bitte Migration ausführen.', 'warning')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# ÜBERSICHT
# ============================================================================

@auftraege_bp.route('/')
@login_required
@workflow_required
def index():
    """Auftragsbestätigungen-Übersicht"""
    
    # Filter
    status_filter = request.args.get('status', 'alle')
    kunde_filter = request.args.get('kunde', '')
    
    # Query - Auftragsbestätigungen
    query = BusinessDocument.query.filter_by(dokument_typ=DokumentTyp.AUFTRAGSBESTAETIGUNG.value)
    
    # Status filtern
    if status_filter != 'alle':
        query = query.filter_by(status=status_filter)
    
    # Kunde filtern
    if kunde_filter:
        query = query.join(Customer).filter(
            db.or_(
                Customer.company_name.ilike(f'%{kunde_filter}%'),
                Customer.first_name.ilike(f'%{kunde_filter}%'),
                Customer.last_name.ilike(f'%{kunde_filter}%')
            )
        )
    
    auftraege = query.order_by(BusinessDocument.dokument_datum.desc()).all()
    
    # Statistiken
    stats = {
        'gesamt': BusinessDocument.query.filter_by(dokument_typ=DokumentTyp.AUFTRAGSBESTAETIGUNG.value).count(),
        'entwurf': BusinessDocument.query.filter_by(
            dokument_typ=DokumentTyp.AUFTRAGSBESTAETIGUNG.value, 
            status=DokumentStatus.ENTWURF.value
        ).count(),
        'versendet': BusinessDocument.query.filter_by(
            dokument_typ=DokumentTyp.AUFTRAGSBESTAETIGUNG.value, 
            status=DokumentStatus.VERSENDET.value
        ).count(),
        'in_bearbeitung': BusinessDocument.query.filter_by(
            dokument_typ=DokumentTyp.AUFTRAGSBESTAETIGUNG.value, 
            status=DokumentStatus.IN_BEARBEITUNG.value
        ).count(),
        'geliefert': BusinessDocument.query.filter_by(
            dokument_typ=DokumentTyp.AUFTRAGSBESTAETIGUNG.value, 
            status=DokumentStatus.GELIEFERT.value
        ).count(),
    }
    
    return render_template('auftraege/index.html',
                         auftraege=auftraege,
                         stats=stats,
                         status_filter=status_filter,
                         kunde_filter=kunde_filter)


# ============================================================================
# AUFTRAG ANZEIGEN
# ============================================================================

@auftraege_bp.route('/<int:id>')
@login_required
@workflow_required
def show(id):
    """Auftragsbestätigung anzeigen"""
    auftrag = BusinessDocument.query.get_or_404(id)
    
    if auftrag.dokument_typ != DokumentTyp.AUFTRAGSBESTAETIGUNG.value:
        flash('Dokument ist keine Auftragsbestätigung.', 'warning')
        return redirect(url_for('auftraege.index'))
    
    # Vorgänger-Angebot laden (falls vorhanden)
    vorgaenger_angebot = None
    if auftrag.vorgaenger_id:
        vorgaenger_angebot = BusinessDocument.query.get(auftrag.vorgaenger_id)
    
    # Nachfolgende Dokumente (Lieferscheine, Rechnungen)
    lieferscheine = BusinessDocument.query.filter_by(
        vorgaenger_id=auftrag.id,
        dokument_typ=DokumentTyp.LIEFERSCHEIN.value
    ).all()
    
    rechnungen = BusinessDocument.query.filter(
        BusinessDocument.vorgaenger_id == auftrag.id,
        BusinessDocument.dokument_typ.in_([
            DokumentTyp.RECHNUNG.value,
            DokumentTyp.ANZAHLUNG.value,
            DokumentTyp.TEILRECHNUNG.value
        ])
    ).all()
    
    return render_template('auftraege/show.html', 
                         auftrag=auftrag,
                         vorgaenger_angebot=vorgaenger_angebot,
                         lieferscheine=lieferscheine,
                         rechnungen=rechnungen)


# ============================================================================
# NEUER AUFTRAG (manuell)
# ============================================================================

@auftraege_bp.route('/neu', methods=['GET', 'POST'])
@login_required
@workflow_required
def neu():
    """Neue Auftragsbestätigung manuell erstellen"""
    
    if request.method == 'POST':
        try:
            # Kunde laden
            kunde_id = request.form.get('kunde_id')
            kunde = Customer.query.get_or_404(kunde_id)
            
            # Dokumentnummer generieren
            dok_nummer = Nummernkreis.hole_naechste_nummer('auftragsbestaetigung')
            
            # Zahlungsbedingung
            zb_id = request.form.get('zahlungsbedingung_id')
            zahlungsbedingung = Zahlungsbedingung.query.get(zb_id) if zb_id else None
            if not zahlungsbedingung:
                zahlungsbedingung = Zahlungsbedingung.query.filter_by(standard=True, aktiv=True).first()
            
            # Lieferdatum
            lieferdatum_str = request.form.get('lieferdatum')
            lieferdatum = datetime.strptime(lieferdatum_str, '%Y-%m-%d').date() if lieferdatum_str else None
            
            # Auftragsbestätigung erstellen
            auftrag = BusinessDocument(
                dokument_nummer=dok_nummer,
                dokument_typ=DokumentTyp.AUFTRAGSBESTAETIGUNG.value,
                kunde_id=kunde.id,
                
                # Adressen-Snapshot
                rechnungsadresse={
                    'name': kunde.display_name,
                    'company': kunde.company_name,
                    'contact': kunde.contact_person,
                    'street': kunde.street,
                    'house_number': kunde.house_number,
                    'postal_code': kunde.postal_code,
                    'city': kunde.city,
                    'country': kunde.country or 'Deutschland'
                },
                
                # Datum
                dokument_datum=date.today(),
                lieferdatum=lieferdatum,
                
                # Status
                status=DokumentStatus.ENTWURF.value,
                
                # Texte
                betreff=request.form.get('betreff', ''),
                einleitung=request.form.get('einleitung', ''),
                schlussbemerkung=request.form.get('schlussbemerkung', ''),
                interne_notiz=request.form.get('interne_notiz', ''),
                
                # Kundenreferenz
                kunden_referenz=request.form.get('kunden_referenz', ''),
                kunden_bestellnummer=request.form.get('kunden_bestellnummer', ''),
                
                # Zahlungsbedingungen
                zahlungsbedingung_id=zahlungsbedingung.id if zahlungsbedingung else None,
                zahlungsziel_tage=zahlungsbedingung.zahlungsziel_tage if zahlungsbedingung else 14,
                
                # Tracking
                erstellt_von=current_user.username
            )
            
            db.session.add(auftrag)
            db.session.flush()
            
            # Positionen hinzufügen (aus JSON)
            positionen_json = request.form.get('positionen_json')
            if positionen_json:
                import json
                positionen = json.loads(positionen_json)
                
                for idx, pos in enumerate(positionen, start=1):
                    position = DocumentPosition(
                        dokument_id=auftrag.id,
                        position=idx,
                        typ=pos.get('typ', PositionsTyp.ARTIKEL.value),
                        artikel_id=pos.get('artikel_id'),
                        artikelnummer=pos.get('artikelnummer', ''),
                        bezeichnung=pos.get('bezeichnung', ''),
                        beschreibung=pos.get('beschreibung', ''),
                        menge=Decimal(str(pos.get('menge', 1))),
                        einheit=pos.get('einheit', 'Stk.'),
                        einzelpreis_netto=Decimal(str(pos.get('einzelpreis', 0))),
                        mwst_satz=Decimal(str(pos.get('mwst_satz', 19))),
                        rabatt_prozent=Decimal(str(pos.get('rabatt_prozent', 0)))
                    )
                    position.berechne()
                    db.session.add(position)
            
            # Summen berechnen
            auftrag.berechne_summen()
            
            db.session.commit()
            
            flash(f'Auftragsbestätigung {dok_nummer} erfolgreich erstellt!', 'success')
            return redirect(url_for('auftraege.show', id=auftrag.id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler beim Erstellen der AB: {e}")
            flash(f'Fehler: {str(e)}', 'danger')
    
    # GET: Formular anzeigen
    kunden = Customer.query.order_by(Customer.company_name, Customer.last_name).all()
    zahlungsbedingungen = Zahlungsbedingung.query.filter_by(aktiv=True).order_by(Zahlungsbedingung.sortierung).all()
    
    # Standard-Texte
    standard_einleitung = "Vielen Dank für Ihren Auftrag. Hiermit bestätigen wir Ihre Bestellung:"
    standard_schluss = "Bei Fragen stehen wir Ihnen gerne zur Verfügung."
    
    return render_template('auftraege/neu.html',
                         kunden=kunden,
                         zahlungsbedingungen=zahlungsbedingungen,
                         standard_einleitung=standard_einleitung,
                         standard_schluss=standard_schluss)


# ============================================================================
# AUFTRAG AUS ANGEBOT ERSTELLEN
# ============================================================================

@auftraege_bp.route('/aus-angebot/<int:angebot_id>', methods=['POST'])
@login_required
@workflow_required
def aus_angebot(angebot_id):
    """Auftragsbestätigung aus angenommenem Angebot erstellen"""
    angebot = BusinessDocument.query.get_or_404(angebot_id)
    
    if angebot.dokument_typ != DokumentTyp.ANGEBOT.value:
        flash('Quelldokument ist kein Angebot.', 'warning')
        return redirect(url_for('angebote_workflow.index'))
    
    if angebot.status != DokumentStatus.ANGENOMMEN.value:
        flash('Nur angenommene Angebote können in Aufträge umgewandelt werden.', 'warning')
        return redirect(url_for('angebote_workflow.show', id=angebot_id))
    
    try:
        # Neue Dokumentnummer für AB
        ab_nummer = Nummernkreis.hole_naechste_nummer('auftragsbestaetigung')
        
        # Auftragsbestätigung erstellen
        ab = BusinessDocument(
            dokument_nummer=ab_nummer,
            dokument_typ=DokumentTyp.AUFTRAGSBESTAETIGUNG.value,
            vorgaenger_id=angebot.id,
            kunde_id=angebot.kunde_id,
            rechnungsadresse=angebot.rechnungsadresse,
            lieferadresse=angebot.lieferadresse,
            
            dokument_datum=date.today(),
            
            summe_netto=angebot.summe_netto,
            summe_mwst=angebot.summe_mwst,
            summe_brutto=angebot.summe_brutto,
            rabatt_prozent=angebot.rabatt_prozent,
            rabatt_betrag=angebot.rabatt_betrag,
            
            status=DokumentStatus.ENTWURF.value,
            
            betreff=angebot.betreff,
            einleitung="Vielen Dank für Ihren Auftrag. Hiermit bestätigen wir Ihre Bestellung:",
            schlussbemerkung=angebot.schlussbemerkung,
            interne_notiz=f"Erstellt aus Angebot {angebot.dokument_nummer}",
            
            kunden_referenz=angebot.kunden_referenz,
            kunden_bestellnummer=angebot.kunden_bestellnummer,
            
            zahlungsbedingung_id=angebot.zahlungsbedingung_id,
            zahlungsziel_tage=angebot.zahlungsziel_tage,
            
            erstellt_von=current_user.username
        )
        
        db.session.add(ab)
        db.session.flush()
        
        # Positionen kopieren
        for pos in angebot.positionen:
            neue_pos = DocumentPosition(
                dokument_id=ab.id,
                position=pos.position,
                typ=pos.typ,
                artikel_id=pos.artikel_id,
                artikelnummer=pos.artikelnummer,
                bezeichnung=pos.bezeichnung,
                beschreibung=pos.beschreibung,
                menge=pos.menge,
                einheit=pos.einheit,
                einzelpreis_netto=pos.einzelpreis_netto,
                mwst_satz=pos.mwst_satz,
                rabatt_prozent=pos.rabatt_prozent
            )
            neue_pos.berechne()
            db.session.add(neue_pos)
        
        db.session.commit()
        
        flash(f'Auftragsbestätigung {ab_nummer} aus Angebot {angebot.dokument_nummer} erstellt!', 'success')
        return redirect(url_for('auftraege.show', id=ab.id))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Fehler bei Umwandlung: {e}")
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('angebote_workflow.show', id=angebot_id))


# ============================================================================
# AUFTRAG BEARBEITEN
# ============================================================================

@auftraege_bp.route('/<int:id>/bearbeiten', methods=['GET', 'POST'])
@login_required
@workflow_required
def bearbeiten(id):
    """Auftragsbestätigung bearbeiten"""
    auftrag = BusinessDocument.query.get_or_404(id)
    
    if not auftrag.kann_bearbeitet_werden():
        flash('Diese Auftragsbestätigung kann nicht mehr bearbeitet werden.', 'warning')
        return redirect(url_for('auftraege.show', id=id))
    
    if request.method == 'POST':
        try:
            # Felder aktualisieren
            auftrag.betreff = request.form.get('betreff', '')
            auftrag.einleitung = request.form.get('einleitung', '')
            auftrag.schlussbemerkung = request.form.get('schlussbemerkung', '')
            auftrag.interne_notiz = request.form.get('interne_notiz', '')
            auftrag.kunden_referenz = request.form.get('kunden_referenz', '')
            auftrag.kunden_bestellnummer = request.form.get('kunden_bestellnummer', '')
            
            # Lieferdatum
            lieferdatum_str = request.form.get('lieferdatum')
            auftrag.lieferdatum = datetime.strptime(lieferdatum_str, '%Y-%m-%d').date() if lieferdatum_str else None
            
            # Rabatt
            auftrag.rabatt_prozent = Decimal(request.form.get('rabatt_prozent', 0))
            
            # Tracking
            auftrag.geaendert_von = current_user.username
            
            # Positionen aktualisieren (komplett ersetzen)
            positionen_json = request.form.get('positionen_json')
            if positionen_json:
                import json
                
                # Alte Positionen löschen
                DocumentPosition.query.filter_by(dokument_id=auftrag.id).delete()
                
                # Neue Positionen hinzufügen
                positionen = json.loads(positionen_json)
                for idx, pos in enumerate(positionen, start=1):
                    position = DocumentPosition(
                        dokument_id=auftrag.id,
                        position=idx,
                        typ=pos.get('typ', PositionsTyp.ARTIKEL.value),
                        artikel_id=pos.get('artikel_id'),
                        artikelnummer=pos.get('artikelnummer', ''),
                        bezeichnung=pos.get('bezeichnung', ''),
                        beschreibung=pos.get('beschreibung', ''),
                        menge=Decimal(str(pos.get('menge', 1))),
                        einheit=pos.get('einheit', 'Stk.'),
                        einzelpreis_netto=Decimal(str(pos.get('einzelpreis', 0))),
                        mwst_satz=Decimal(str(pos.get('mwst_satz', 19))),
                        rabatt_prozent=Decimal(str(pos.get('rabatt_prozent', 0)))
                    )
                    position.berechne()
                    db.session.add(position)
            
            # Summen neu berechnen
            auftrag.berechne_summen()
            
            db.session.commit()
            
            flash('Auftragsbestätigung erfolgreich aktualisiert!', 'success')
            return redirect(url_for('auftraege.show', id=id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler beim Aktualisieren: {e}")
            flash(f'Fehler: {str(e)}', 'danger')
    
    # GET: Formular anzeigen
    zahlungsbedingungen = Zahlungsbedingung.query.filter_by(aktiv=True).order_by(Zahlungsbedingung.sortierung).all()
    
    return render_template('auftraege/bearbeiten.html',
                         auftrag=auftrag,
                         zahlungsbedingungen=zahlungsbedingungen)


# ============================================================================
# STATUS-AKTIONEN
# ============================================================================

@auftraege_bp.route('/<int:id>/versenden', methods=['POST'])
@login_required
@workflow_required
def versenden(id):
    """Auftragsbestätigung als versendet markieren"""
    auftrag = BusinessDocument.query.get_or_404(id)
    
    if auftrag.status != DokumentStatus.ENTWURF.value:
        flash('Auftragsbestätigung wurde bereits versendet.', 'warning')
        return redirect(url_for('auftraege.show', id=id))
    
    try:
        auftrag.status = DokumentStatus.VERSENDET.value
        auftrag.versendet_am = datetime.utcnow()
        auftrag.versendet_per = request.form.get('versand_art', 'email')
        auftrag.versendet_an = request.form.get('versand_an', auftrag.kunde.email if auftrag.kunde else '')
        auftrag.geaendert_von = current_user.username
        
        db.session.commit()
        
        flash(f'Auftragsbestätigung {auftrag.dokument_nummer} als versendet markiert.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('auftraege.show', id=id))


@auftraege_bp.route('/<int:id>/in-bearbeitung', methods=['POST'])
@login_required
@workflow_required
def in_bearbeitung(id):
    """Auftragsbestätigung in Bearbeitung setzen"""
    auftrag = BusinessDocument.query.get_or_404(id)
    
    if auftrag.status not in [DokumentStatus.VERSENDET.value, DokumentStatus.ENTWURF.value]:
        flash('Auftrag kann nicht in Bearbeitung gesetzt werden.', 'warning')
        return redirect(url_for('auftraege.show', id=id))
    
    try:
        auftrag.status = DokumentStatus.IN_BEARBEITUNG.value
        auftrag.geaendert_von = current_user.username
        
        db.session.commit()
        
        flash(f'Auftrag {auftrag.dokument_nummer} ist jetzt in Bearbeitung.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('auftraege.show', id=id))


@auftraege_bp.route('/<int:id>/stornieren', methods=['POST'])
@login_required
@workflow_required
def stornieren(id):
    """Auftragsbestätigung stornieren"""
    auftrag = BusinessDocument.query.get_or_404(id)
    
    if not auftrag.kann_storniert_werden():
        flash('Diese Auftragsbestätigung kann nicht storniert werden.', 'warning')
        return redirect(url_for('auftraege.show', id=id))
    
    try:
        auftrag.status = DokumentStatus.STORNIERT.value
        auftrag.geaendert_von = current_user.username
        
        db.session.commit()
        
        flash(f'Auftragsbestätigung {auftrag.dokument_nummer} wurde storniert.', 'info')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('auftraege.show', id=id))


# ============================================================================
# LIEFERSCHEIN ERSTELLEN
# ============================================================================

@auftraege_bp.route('/<int:id>/lieferschein', methods=['POST'])
@login_required
@workflow_required
def lieferschein_erstellen(id):
    """Lieferschein aus Auftragsbestätigung erstellen"""
    auftrag = BusinessDocument.query.get_or_404(id)
    
    if auftrag.status not in [DokumentStatus.VERSENDET.value, DokumentStatus.IN_BEARBEITUNG.value]:
        flash('Lieferschein kann nur aus bestätigten Aufträgen erstellt werden.', 'warning')
        return redirect(url_for('auftraege.show', id=id))
    
    try:
        # Neue Dokumentnummer für Lieferschein
        ls_nummer = Nummernkreis.hole_naechste_nummer('lieferschein')
        
        # Lieferschein erstellen
        lieferschein = BusinessDocument(
            dokument_nummer=ls_nummer,
            dokument_typ=DokumentTyp.LIEFERSCHEIN.value,
            vorgaenger_id=auftrag.id,
            kunde_id=auftrag.kunde_id,
            rechnungsadresse=auftrag.rechnungsadresse,
            lieferadresse=auftrag.lieferadresse or auftrag.rechnungsadresse,
            
            dokument_datum=date.today(),
            lieferdatum=date.today(),
            
            status=DokumentStatus.ENTWURF.value,
            
            betreff=f"Lieferung zu Auftrag {auftrag.dokument_nummer}",
            interne_notiz=f"Erstellt aus Auftragsbestätigung {auftrag.dokument_nummer}",
            
            erstellt_von=current_user.username
        )
        
        db.session.add(lieferschein)
        db.session.flush()
        
        # Positionen kopieren (nur Artikel, keine Dienstleistungen)
        for pos in auftrag.positionen:
            if pos.typ not in [PositionsTyp.DIENSTLEISTUNG.value, PositionsTyp.TEXT.value]:
                neue_pos = DocumentPosition(
                    dokument_id=lieferschein.id,
                    position=pos.position,
                    typ=pos.typ,
                    artikel_id=pos.artikel_id,
                    artikelnummer=pos.artikelnummer,
                    bezeichnung=pos.bezeichnung,
                    beschreibung=pos.beschreibung,
                    menge=pos.menge,
                    einheit=pos.einheit,
                    # Keine Preise auf Lieferschein
                    einzelpreis_netto=Decimal('0'),
                    mwst_satz=pos.mwst_satz
                )
                db.session.add(neue_pos)
        
        # Auftrag als teilgeliefert/geliefert markieren
        auftrag.status = DokumentStatus.GELIEFERT.value
        auftrag.geaendert_von = current_user.username
        
        db.session.commit()
        
        flash(f'Lieferschein {ls_nummer} erstellt!', 'success')
        return redirect(url_for('lieferscheine.show', id=lieferschein.id))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Fehler bei Lieferschein-Erstellung: {e}")
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('auftraege.show', id=id))


# ============================================================================
# RECHNUNG ERSTELLEN
# ============================================================================

@auftraege_bp.route('/<int:id>/rechnung', methods=['POST'])
@login_required
@workflow_required
def rechnung_erstellen(id):
    """Rechnung aus Auftragsbestätigung erstellen"""
    auftrag = BusinessDocument.query.get_or_404(id)
    
    if auftrag.status not in [DokumentStatus.VERSENDET.value, DokumentStatus.IN_BEARBEITUNG.value, DokumentStatus.GELIEFERT.value]:
        flash('Rechnung kann nur aus bestätigten Aufträgen erstellt werden.', 'warning')
        return redirect(url_for('auftraege.show', id=id))
    
    rechnungstyp = request.form.get('typ', 'rechnung')  # rechnung, anzahlung, teilrechnung
    
    try:
        # Dokumenttyp bestimmen
        if rechnungstyp == 'anzahlung':
            dok_typ = DokumentTyp.ANZAHLUNG.value
            nk_typ = 'anzahlung'
        elif rechnungstyp == 'teilrechnung':
            dok_typ = DokumentTyp.TEILRECHNUNG.value
            nk_typ = 'rechnung'
        else:
            dok_typ = DokumentTyp.RECHNUNG.value
            nk_typ = 'rechnung'
        
        # Neue Dokumentnummer
        re_nummer = Nummernkreis.hole_naechste_nummer(nk_typ)
        
        # Fälligkeitsdatum berechnen
        zb = auftrag.zahlungsbedingung
        faelligkeit = date.today() + timedelta(days=zb.zahlungsziel_tage if zb else 14)
        
        # Rechnung erstellen
        rechnung = BusinessDocument(
            dokument_nummer=re_nummer,
            dokument_typ=dok_typ,
            vorgaenger_id=auftrag.id,
            kunde_id=auftrag.kunde_id,
            rechnungsadresse=auftrag.rechnungsadresse,
            
            dokument_datum=date.today(),
            leistungsdatum=auftrag.lieferdatum or date.today(),
            faelligkeitsdatum=faelligkeit,
            
            status=DokumentStatus.OFFEN.value,
            
            betreff=f"Rechnung zu Auftrag {auftrag.dokument_nummer}",
            interne_notiz=f"Erstellt aus Auftragsbestätigung {auftrag.dokument_nummer}",
            
            zahlungsbedingung_id=auftrag.zahlungsbedingung_id,
            zahlungsziel_tage=auftrag.zahlungsziel_tage,
            skonto_prozent=zb.skonto_prozent if zb else 0,
            skonto_tage=zb.skonto_tage if zb else 0,
            
            erstellt_von=current_user.username
        )
        
        db.session.add(rechnung)
        db.session.flush()
        
        # Positionen kopieren
        for pos in auftrag.positionen:
            neue_pos = DocumentPosition(
                dokument_id=rechnung.id,
                position=pos.position,
                typ=pos.typ,
                artikel_id=pos.artikel_id,
                artikelnummer=pos.artikelnummer,
                bezeichnung=pos.bezeichnung,
                beschreibung=pos.beschreibung,
                menge=pos.menge,
                einheit=pos.einheit,
                einzelpreis_netto=pos.einzelpreis_netto,
                mwst_satz=pos.mwst_satz,
                rabatt_prozent=pos.rabatt_prozent
            )
            neue_pos.berechne()
            db.session.add(neue_pos)
        
        # Summen berechnen
        rechnung.berechne_summen()
        
        # Zahlungstext generieren
        if zb:
            rechnung.zahlungstext = zb.generiere_zahlungstext()
        
        db.session.commit()
        
        flash(f'Rechnung {re_nummer} erstellt!', 'success')
        return redirect(url_for('rechnungen.show', id=rechnung.id))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Fehler bei Rechnungs-Erstellung: {e}")
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('auftraege.show', id=id))


# ============================================================================
# PDF GENERIERUNG
# ============================================================================

@auftraege_bp.route('/<int:id>/pdf')
@login_required
@workflow_required
def pdf_generieren(id):
    """PDF für Auftragsbestätigung generieren"""
    auftrag = BusinessDocument.query.get_or_404(id)
    
    try:
        pdf_bytes = generiere_ab_pdf(auftrag)
        
        # PDF speichern
        pdf_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'pdfs', 'auftraege')
        os.makedirs(pdf_dir, exist_ok=True)
        
        pdf_filename = f"{auftrag.dokument_nummer.replace('/', '-')}.pdf"
        pdf_path = os.path.join(pdf_dir, pdf_filename)
        
        with open(pdf_path, 'wb') as f:
            f.write(pdf_bytes)
        
        # Pfad im Dokument speichern
        auftrag.pdf_pfad = pdf_path
        auftrag.pdf_erstellt_am = datetime.utcnow()
        db.session.commit()
        
        # Download
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=pdf_filename
        )
        
    except Exception as e:
        logger.error(f"Fehler bei PDF-Generierung: {e}")
        flash(f'Fehler bei PDF-Generierung: {str(e)}', 'danger')
        return redirect(url_for('auftraege.show', id=id))


@auftraege_bp.route('/<int:id>/pdf/vorschau')
@login_required
@workflow_required
def pdf_vorschau(id):
    """PDF-Vorschau im Browser"""
    auftrag = BusinessDocument.query.get_or_404(id)
    
    try:
        pdf_bytes = generiere_ab_pdf(auftrag)
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=False
        )
        
    except Exception as e:
        logger.error(f"Fehler bei PDF-Vorschau: {e}")
        flash(f'Fehler bei PDF-Vorschau: {str(e)}', 'danger')
        return redirect(url_for('auftraege.show', id=id))


def generiere_ab_pdf(auftrag):
    """
    Generiert PDF für eine Auftragsbestätigung
    
    Args:
        auftrag: BusinessDocument Objekt
        
    Returns:
        bytes: PDF als Bytes
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.enums import TA_RIGHT
    
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )
    
    styles = getSampleStyleSheet()
    
    style_header = ParagraphStyle('Header', parent=styles['Heading1'], fontSize=18, spaceAfter=10)
    style_normal = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=10, leading=14)
    style_small = ParagraphStyle('Small', parent=styles['Normal'], fontSize=8, leading=10)
    
    elements = []
    
    # === KOPFBEREICH ===
    elements.append(Paragraph("<b>StitchAdmin GmbH</b>", style_header))
    elements.append(Paragraph("Musterstraße 123 | 12345 Musterstadt", style_small))
    elements.append(Paragraph("Tel: 0123-456789 | E-Mail: info@stitchadmin.de", style_small))
    elements.append(Spacer(1, 15*mm))
    
    # Empfänger
    adresse = auftrag.rechnungsadresse or {}
    empfaenger = f"""
    {adresse.get('company', '') or adresse.get('name', '')}<br/>
    {adresse.get('contact', '') or ''}<br/>
    {adresse.get('street', '')} {adresse.get('house_number', '')}<br/>
    {adresse.get('postal_code', '')} {adresse.get('city', '')}
    """
    elements.append(Paragraph(empfaenger.strip(), style_normal))
    elements.append(Spacer(1, 10*mm))
    
    # Dokumenttitel
    elements.append(Paragraph("<b>AUFTRAGSBESTÄTIGUNG</b>", style_header))
    elements.append(Spacer(1, 5*mm))
    
    # Dokumentinfo
    info_data = [
        ['Auftrags-Nr.:', auftrag.dokument_nummer],
        ['Datum:', auftrag.dokument_datum.strftime('%d.%m.%Y')],
    ]
    if auftrag.lieferdatum:
        info_data.append(['Lieferdatum:', auftrag.lieferdatum.strftime('%d.%m.%Y')])
    if auftrag.kunden_referenz:
        info_data.append(['Ihre Referenz:', auftrag.kunden_referenz])
    if auftrag.kunden_bestellnummer:
        info_data.append(['Ihre Bestellung:', auftrag.kunden_bestellnummer])
    
    info_table = Table(info_data, colWidths=[40*mm, 50*mm])
    info_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10*mm))
    
    # Betreff
    if auftrag.betreff:
        elements.append(Paragraph(f"<b>Betreff: {auftrag.betreff}</b>", style_normal))
        elements.append(Spacer(1, 5*mm))
    
    # Einleitung
    if auftrag.einleitung:
        elements.append(Paragraph(auftrag.einleitung, style_normal))
        elements.append(Spacer(1, 5*mm))
    
    # === POSITIONEN ===
    pos_data = [['Pos.', 'Bezeichnung', 'Menge', 'Einheit', 'Einzelpreis', 'Gesamt']]
    
    for pos in auftrag.positionen:
        bezeichnung = pos.bezeichnung
        if pos.beschreibung:
            bezeichnung += f"\n{pos.beschreibung}"
        
        pos_data.append([
            str(pos.position),
            Paragraph(bezeichnung, style_small),
            f"{pos.menge:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            pos.einheit,
            f"{pos.einzelpreis_netto:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.'),
            f"{pos.netto_gesamt:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')
        ])
    
    col_widths = [12*mm, 75*mm, 20*mm, 15*mm, 25*mm, 25*mm]
    pos_table = Table(pos_data, colWidths=col_widths, repeatRows=1)
    pos_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('ALIGN', (4, 0), (-1, -1), 'RIGHT'),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
        ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),
    ]))
    elements.append(pos_table)
    elements.append(Spacer(1, 5*mm))
    
    # === SUMMEN ===
    summen_data = [
        ['', 'Zwischensumme (netto):', f"{auftrag.summe_netto:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')],
    ]
    
    if auftrag.rabatt_betrag and auftrag.rabatt_betrag > 0:
        summen_data.append(['', f'Rabatt ({auftrag.rabatt_prozent}%):', 
                           f"- {auftrag.rabatt_betrag:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')])
    
    summen_data.append(['', 'MwSt. (19%):', f"{auftrag.summe_mwst:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')])
    summen_data.append(['', 'Gesamtbetrag:', f"{auftrag.summe_brutto:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')])
    
    summen_table = Table(summen_data, colWidths=[100*mm, 40*mm, 30*mm])
    summen_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('FONTNAME', (1, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (1, -1), (-1, -1), 1, colors.black),
        ('TOPPADDING', (0, -1), (-1, -1), 5),
    ]))
    elements.append(summen_table)
    elements.append(Spacer(1, 10*mm))
    
    # === FUSSBEREICH ===
    if auftrag.schlussbemerkung:
        elements.append(Paragraph(auftrag.schlussbemerkung, style_normal))
        elements.append(Spacer(1, 5*mm))
    
    if auftrag.zahlungsbedingung:
        elements.append(Paragraph(
            f"<b>Zahlungsbedingungen:</b> {auftrag.zahlungsbedingung.generiere_zahlungstext()}", 
            style_small
        ))
    
    doc.build(elements)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes


# ============================================================================
# API ENDPOINTS
# ============================================================================

@auftraege_bp.route('/api/artikel/suche')
@login_required
@workflow_required
def api_artikel_suche():
    """API: Artikelsuche für Positionen"""
    query = request.args.get('q', '').strip()
    
    if len(query) < 2:
        return jsonify([])
    
    artikel = Article.query.filter(
        db.or_(
            Article.name.ilike(f'%{query}%'),
            Article.article_number.ilike(f'%{query}%')
        ),
        Article.active == True
    ).limit(20).all()
    
    return jsonify([{
        'id': a.id,
        'article_number': a.article_number,
        'name': a.name,
        'price': float(a.price or 0),
        'category': a.category
    } for a in artikel])


@auftraege_bp.route('/api/statistiken')
@login_required
@workflow_required
def api_statistiken():
    """API: Auftrags-Statistiken"""
    from sqlalchemy import func
    
    # Aufträge pro Monat (letzte 12 Monate)
    heute = date.today()
    vor_12_monaten = heute - timedelta(days=365)
    
    monatliche_stats = db.session.query(
        func.strftime('%Y-%m', BusinessDocument.dokument_datum).label('monat'),
        func.count(BusinessDocument.id).label('anzahl'),
        func.sum(BusinessDocument.summe_brutto).label('summe')
    ).filter(
        BusinessDocument.dokument_typ == DokumentTyp.AUFTRAGSBESTAETIGUNG.value,
        BusinessDocument.dokument_datum >= vor_12_monaten
    ).group_by(
        func.strftime('%Y-%m', BusinessDocument.dokument_datum)
    ).all()
    
    return jsonify({
        'monatlich': [{
            'monat': m.monat,
            'anzahl': m.anzahl,
            'summe': float(m.summe or 0)
        } for m in monatliche_stats]
    })
