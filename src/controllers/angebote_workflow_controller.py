# -*- coding: utf-8 -*-
"""
ANGEBOTE CONTROLLER (Document-Workflow Integration)
===================================================
Verwaltung von Angeboten mit dem neuen BusinessDocument-System:
- CRUD-Operationen
- PDF-Generierung
- E-Mail-Versand
- Status-Tracking

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
from src.models.models import Customer, Article, Order

# Document-Workflow Models
try:
    from src.models.document_workflow import (
        Nummernkreis, Zahlungsbedingung, BusinessDocument, DocumentPosition, DocumentPayment,
        DokumentTyp, DokumentStatus, PositionsTyp, MwStKennzeichen,
        initialisiere_nummernkreise
    )
    WORKFLOW_AVAILABLE = True
except ImportError:
    WORKFLOW_AVAILABLE = False

import logging
logger = logging.getLogger(__name__)

# Blueprint
angebote_workflow_bp = Blueprint('angebote_workflow', __name__, url_prefix='/angebote-v2')


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

@angebote_workflow_bp.route('/')
@login_required
@workflow_required
def index():
    """Angebots-Übersicht"""
    
    # Filter
    status_filter = request.args.get('status', 'alle')
    kunde_filter = request.args.get('kunde', '')
    
    # Query
    query = BusinessDocument.query.filter_by(dokument_typ=DokumentTyp.ANGEBOT.value)
    
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
    
    angebote = query.order_by(BusinessDocument.dokument_datum.desc()).all()
    
    # Statistiken
    stats = {
        'gesamt': BusinessDocument.query.filter_by(dokument_typ=DokumentTyp.ANGEBOT.value).count(),
        'entwurf': BusinessDocument.query.filter_by(
            dokument_typ=DokumentTyp.ANGEBOT.value, 
            status=DokumentStatus.ENTWURF.value
        ).count(),
        'versendet': BusinessDocument.query.filter_by(
            dokument_typ=DokumentTyp.ANGEBOT.value, 
            status=DokumentStatus.VERSENDET.value
        ).count(),
        'angenommen': BusinessDocument.query.filter_by(
            dokument_typ=DokumentTyp.ANGEBOT.value, 
            status=DokumentStatus.ANGENOMMEN.value
        ).count(),
        'abgelehnt': BusinessDocument.query.filter_by(
            dokument_typ=DokumentTyp.ANGEBOT.value, 
            status=DokumentStatus.ABGELEHNT.value
        ).count(),
    }
    
    # Überfällige Angebote (gueltig_bis < heute und noch versendet)
    heute = date.today()
    stats['ueberfaellig'] = BusinessDocument.query.filter(
        BusinessDocument.dokument_typ == DokumentTyp.ANGEBOT.value,
        BusinessDocument.status == DokumentStatus.VERSENDET.value,
        BusinessDocument.gueltig_bis < heute
    ).count()
    
    return render_template('angebote_v2/index.html',
                         angebote=angebote,
                         stats=stats,
                         status_filter=status_filter,
                         kunde_filter=kunde_filter)


# ============================================================================
# ANGEBOT ANZEIGEN
# ============================================================================

@angebote_workflow_bp.route('/<int:id>')
@login_required
@workflow_required
def show(id):
    """Angebot anzeigen"""
    angebot = BusinessDocument.query.get_or_404(id)
    
    if angebot.dokument_typ != DokumentTyp.ANGEBOT.value:
        flash('Dokument ist kein Angebot.', 'warning')
        return redirect(url_for('angebote_workflow.index'))
    
    return render_template('angebote_v2/show.html', angebot=angebot)


# ============================================================================
# NEUES ANGEBOT
# ============================================================================

@angebote_workflow_bp.route('/neu', methods=['GET', 'POST'])
@login_required
@workflow_required
def neu():
    """Neues Angebot erstellen"""
    
    if request.method == 'POST':
        try:
            # Kunde laden
            kunde_id = request.form.get('kunde_id')
            kunde = Customer.query.get_or_404(kunde_id)
            
            # Dokumentnummer generieren
            dok_nummer = Nummernkreis.hole_naechste_nummer('angebot')
            
            # Zahlungsbedingung
            zb_id = request.form.get('zahlungsbedingung_id')
            zahlungsbedingung = Zahlungsbedingung.query.get(zb_id) if zb_id else None
            if not zahlungsbedingung:
                zahlungsbedingung = Zahlungsbedingung.query.filter_by(standard=True, aktiv=True).first()
            
            # Gültigkeit
            gueltig_tage = int(request.form.get('gueltig_tage', 30))
            
            # Angebot erstellen
            angebot = BusinessDocument(
                dokument_nummer=dok_nummer,
                dokument_typ=DokumentTyp.ANGEBOT.value,
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
                gueltig_bis=date.today() + timedelta(days=gueltig_tage),
                
                # Status
                status=DokumentStatus.ENTWURF.value,
                
                # Texte
                betreff=request.form.get('betreff', ''),
                einleitung=request.form.get('einleitung', ''),
                schlussbemerkung=request.form.get('schlussbemerkung', ''),
                interne_notiz=request.form.get('interne_notiz', ''),
                
                # Zahlungsbedingungen
                zahlungsbedingung_id=zahlungsbedingung.id if zahlungsbedingung else None,
                zahlungsziel_tage=zahlungsbedingung.zahlungsziel_tage if zahlungsbedingung else 14,
                
                # Tracking
                erstellt_von=current_user.username
            )
            
            db.session.add(angebot)
            db.session.flush()
            
            # Positionen hinzufügen (aus JSON)
            positionen_json = request.form.get('positionen_json')
            if positionen_json:
                import json
                positionen = json.loads(positionen_json)
                
                for idx, pos in enumerate(positionen, start=1):
                    position = DocumentPosition(
                        dokument_id=angebot.id,
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
            angebot.berechne_summen()
            
            db.session.commit()
            
            flash(f'Angebot {dok_nummer} erfolgreich erstellt!', 'success')
            return redirect(url_for('angebote_workflow.show', id=angebot.id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler beim Erstellen des Angebots: {e}")
            flash(f'Fehler: {str(e)}', 'danger')
    
    # GET: Formular anzeigen
    kunden = Customer.query.order_by(Customer.company_name, Customer.last_name).all()
    zahlungsbedingungen = Zahlungsbedingung.query.filter_by(aktiv=True).order_by(Zahlungsbedingung.sortierung).all()
    
    # Standard-Texte laden (aus Einstellungen)
    standard_einleitung = "Vielen Dank für Ihre Anfrage. Gerne unterbreiten wir Ihnen folgendes Angebot:"
    standard_schluss = "Bei Fragen stehen wir Ihnen gerne zur Verfügung. Wir freuen uns auf Ihre Bestellung!"
    
    return render_template('angebote_v2/neu.html',
                         kunden=kunden,
                         zahlungsbedingungen=zahlungsbedingungen,
                         standard_einleitung=standard_einleitung,
                         standard_schluss=standard_schluss)


# ============================================================================
# ANGEBOT BEARBEITEN
# ============================================================================

@angebote_workflow_bp.route('/<int:id>/bearbeiten', methods=['GET', 'POST'])
@login_required
@workflow_required
def bearbeiten(id):
    """Angebot bearbeiten"""
    angebot = BusinessDocument.query.get_or_404(id)
    
    if not angebot.kann_bearbeitet_werden():
        flash('Dieses Angebot kann nicht mehr bearbeitet werden.', 'warning')
        return redirect(url_for('angebote_workflow.show', id=id))
    
    if request.method == 'POST':
        try:
            # Felder aktualisieren
            angebot.betreff = request.form.get('betreff', '')
            angebot.einleitung = request.form.get('einleitung', '')
            angebot.schlussbemerkung = request.form.get('schlussbemerkung', '')
            angebot.interne_notiz = request.form.get('interne_notiz', '')
            
            # Gültigkeit
            gueltig_tage = int(request.form.get('gueltig_tage', 30))
            angebot.gueltig_bis = angebot.dokument_datum + timedelta(days=gueltig_tage)
            
            # Rabatt
            angebot.rabatt_prozent = Decimal(request.form.get('rabatt_prozent', 0))
            
            # Tracking
            angebot.geaendert_von = current_user.username
            
            # Positionen aktualisieren (komplett ersetzen)
            positionen_json = request.form.get('positionen_json')
            if positionen_json:
                import json
                
                # Alte Positionen löschen
                DocumentPosition.query.filter_by(dokument_id=angebot.id).delete()
                
                # Neue Positionen hinzufügen
                positionen = json.loads(positionen_json)
                for idx, pos in enumerate(positionen, start=1):
                    position = DocumentPosition(
                        dokument_id=angebot.id,
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
            angebot.berechne_summen()
            
            db.session.commit()
            
            flash('Angebot erfolgreich aktualisiert!', 'success')
            return redirect(url_for('angebote_workflow.show', id=id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler beim Aktualisieren des Angebots: {e}")
            flash(f'Fehler: {str(e)}', 'danger')
    
    # GET: Formular anzeigen
    zahlungsbedingungen = Zahlungsbedingung.query.filter_by(aktiv=True).order_by(Zahlungsbedingung.sortierung).all()
    
    return render_template('angebote_v2/bearbeiten.html',
                         angebot=angebot,
                         zahlungsbedingungen=zahlungsbedingungen)


# ============================================================================
# STATUS-AKTIONEN
# ============================================================================

@angebote_workflow_bp.route('/<int:id>/versenden', methods=['POST'])
@login_required
@workflow_required
def versenden(id):
    """Angebot als versendet markieren"""
    angebot = BusinessDocument.query.get_or_404(id)
    
    if angebot.status != DokumentStatus.ENTWURF.value:
        flash('Angebot wurde bereits versendet.', 'warning')
        return redirect(url_for('angebote_workflow.show', id=id))
    
    try:
        angebot.status = DokumentStatus.VERSENDET.value
        angebot.versendet_am = datetime.utcnow()
        angebot.versendet_per = request.form.get('versand_art', 'email')
        angebot.versendet_an = request.form.get('versand_an', angebot.kunde.email if angebot.kunde else '')
        angebot.geaendert_von = current_user.username
        
        db.session.commit()
        
        flash(f'Angebot {angebot.dokument_nummer} als versendet markiert.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('angebote_workflow.show', id=id))


@angebote_workflow_bp.route('/<int:id>/annehmen', methods=['POST'])
@login_required
@workflow_required
def annehmen(id):
    """Angebot als angenommen markieren"""
    angebot = BusinessDocument.query.get_or_404(id)
    
    if angebot.status != DokumentStatus.VERSENDET.value:
        flash('Nur versendete Angebote können angenommen werden.', 'warning')
        return redirect(url_for('angebote_workflow.show', id=id))
    
    try:
        angebot.status = DokumentStatus.ANGENOMMEN.value
        angebot.angenommen_am = datetime.utcnow()
        angebot.geaendert_von = current_user.username
        
        db.session.commit()
        
        flash(f'Angebot {angebot.dokument_nummer} wurde angenommen! 🎉', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('angebote_workflow.show', id=id))


@angebote_workflow_bp.route('/<int:id>/ablehnen', methods=['POST'])
@login_required
@workflow_required
def ablehnen(id):
    """Angebot als abgelehnt markieren"""
    angebot = BusinessDocument.query.get_or_404(id)
    
    if angebot.status not in [DokumentStatus.VERSENDET.value, DokumentStatus.ENTWURF.value]:
        flash('Dieses Angebot kann nicht abgelehnt werden.', 'warning')
        return redirect(url_for('angebote_workflow.show', id=id))
    
    try:
        angebot.status = DokumentStatus.ABGELEHNT.value
        angebot.abgelehnt_am = datetime.utcnow()
        angebot.ablehnungsgrund = request.form.get('grund', '')
        angebot.geaendert_von = current_user.username
        
        db.session.commit()
        
        flash(f'Angebot {angebot.dokument_nummer} wurde abgelehnt.', 'info')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('angebote_workflow.show', id=id))


@angebote_workflow_bp.route('/<int:id>/stornieren', methods=['POST'])
@login_required
@workflow_required
def stornieren(id):
    """Angebot stornieren"""
    angebot = BusinessDocument.query.get_or_404(id)
    
    if not angebot.kann_storniert_werden():
        flash('Dieses Angebot kann nicht storniert werden.', 'warning')
        return redirect(url_for('angebote_workflow.show', id=id))
    
    try:
        angebot.status = DokumentStatus.STORNIERT.value
        angebot.geaendert_von = current_user.username
        
        db.session.commit()
        
        flash(f'Angebot {angebot.dokument_nummer} wurde storniert.', 'info')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('angebote_workflow.show', id=id))


# ============================================================================
# IN AUFTRAG UMWANDELN
# ============================================================================

@angebote_workflow_bp.route('/<int:id>/in-auftrag', methods=['POST'])
@login_required
@workflow_required
def in_auftrag_umwandeln(id):
    """Angebot in Auftragsbestätigung umwandeln"""
    angebot = BusinessDocument.query.get_or_404(id)
    
    if angebot.status != DokumentStatus.ANGENOMMEN.value:
        flash('Nur angenommene Angebote können in Aufträge umgewandelt werden.', 'warning')
        return redirect(url_for('angebote_workflow.show', id=id))
    
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
            einleitung=f"Vielen Dank für Ihren Auftrag. Hiermit bestätigen wir Ihre Bestellung:",
            schlussbemerkung=angebot.schlussbemerkung,
            interne_notiz=f"Erstellt aus Angebot {angebot.dokument_nummer}",
            
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
        return redirect(url_for('angebote_workflow.show', id=ab.id))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Fehler bei Umwandlung: {e}")
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('angebote_workflow.show', id=id))


# ============================================================================
# PDF GENERIERUNG
# ============================================================================

@angebote_workflow_bp.route('/<int:id>/pdf')
@login_required
@workflow_required
def pdf_generieren(id):
    """PDF für Angebot generieren"""
    angebot = BusinessDocument.query.get_or_404(id)
    
    try:
        pdf_bytes = generiere_angebot_pdf(angebot)
        
        # PDF speichern
        pdf_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'pdfs', 'angebote')
        os.makedirs(pdf_dir, exist_ok=True)
        
        pdf_filename = f"{angebot.dokument_nummer.replace('/', '-')}.pdf"
        pdf_path = os.path.join(pdf_dir, pdf_filename)
        
        with open(pdf_path, 'wb') as f:
            f.write(pdf_bytes)
        
        # Pfad im Dokument speichern
        angebot.pdf_pfad = pdf_path
        angebot.pdf_erstellt_am = datetime.utcnow()
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
        return redirect(url_for('angebote_workflow.show', id=id))


@angebote_workflow_bp.route('/<int:id>/pdf/vorschau')
@login_required
@workflow_required
def pdf_vorschau(id):
    """PDF-Vorschau im Browser"""
    angebot = BusinessDocument.query.get_or_404(id)
    
    try:
        pdf_bytes = generiere_angebot_pdf(angebot)
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=False
        )
        
    except Exception as e:
        logger.error(f"Fehler bei PDF-Vorschau: {e}")
        flash(f'Fehler bei PDF-Vorschau: {str(e)}', 'danger')
        return redirect(url_for('angebote_workflow.show', id=id))


def generiere_angebot_pdf(angebot):
    """
    Generiert PDF für ein Angebot
    
    Args:
        angebot: BusinessDocument Objekt
        
    Returns:
        bytes: PDF als Bytes
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm, cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
    
    buffer = io.BytesIO()
    
    # PDF erstellen
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    style_header = ParagraphStyle(
        'Header',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=10
    )
    
    style_normal = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        leading=14
    )
    
    style_small = ParagraphStyle(
        'Small',
        parent=styles['Normal'],
        fontSize=8,
        leading=10
    )
    
    style_right = ParagraphStyle(
        'Right',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_RIGHT
    )
    
    elements = []
    
    # === KOPFBEREICH ===
    
    # Firmenname (TODO: Aus Einstellungen laden)
    elements.append(Paragraph("<b>StitchAdmin GmbH</b>", style_header))
    elements.append(Paragraph("Musterstraße 123 | 12345 Musterstadt", style_small))
    elements.append(Paragraph("Tel: 0123-456789 | E-Mail: info@stitchadmin.de", style_small))
    elements.append(Spacer(1, 15*mm))
    
    # Empfänger
    adresse = angebot.rechnungsadresse or {}
    empfaenger = f"""
    {adresse.get('company', '') or adresse.get('name', '')}<br/>
    {adresse.get('contact', '') or ''}<br/>
    {adresse.get('street', '')} {adresse.get('house_number', '')}<br/>
    {adresse.get('postal_code', '')} {adresse.get('city', '')}
    """
    elements.append(Paragraph(empfaenger.strip(), style_normal))
    elements.append(Spacer(1, 10*mm))
    
    # Dokumentinfo
    info_data = [
        ['Angebot Nr.:', angebot.dokument_nummer],
        ['Datum:', angebot.dokument_datum.strftime('%d.%m.%Y')],
        ['Gültig bis:', angebot.gueltig_bis.strftime('%d.%m.%Y') if angebot.gueltig_bis else '-'],
    ]
    if angebot.kunden_referenz:
        info_data.append(['Ihre Referenz:', angebot.kunden_referenz])
    
    info_table = Table(info_data, colWidths=[40*mm, 50*mm])
    info_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10*mm))
    
    # Betreff
    if angebot.betreff:
        elements.append(Paragraph(f"<b>Betreff: {angebot.betreff}</b>", style_normal))
        elements.append(Spacer(1, 5*mm))
    
    # Einleitung
    if angebot.einleitung:
        elements.append(Paragraph(angebot.einleitung, style_normal))
        elements.append(Spacer(1, 5*mm))
    
    # === POSITIONEN ===
    
    # Tabellen-Header
    pos_data = [['Pos.', 'Bezeichnung', 'Menge', 'Einheit', 'Einzelpreis', 'Gesamt']]
    
    # Positionen
    for pos in angebot.positionen:
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
    
    # Tabelle erstellen
    col_widths = [12*mm, 75*mm, 20*mm, 15*mm, 25*mm, 25*mm]
    pos_table = Table(pos_data, colWidths=col_widths, repeatRows=1)
    pos_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        
        # Body
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        
        # Alignment
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('ALIGN', (4, 0), (-1, -1), 'RIGHT'),
        
        # Grid
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
        ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),
    ]))
    elements.append(pos_table)
    elements.append(Spacer(1, 5*mm))
    
    # === SUMMEN ===
    
    summen_data = []
    
    summen_data.append(['', 'Zwischensumme (netto):', 
                        f"{angebot.summe_netto:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')])
    
    if angebot.rabatt_betrag and angebot.rabatt_betrag > 0:
        summen_data.append(['', f'Rabatt ({angebot.rabatt_prozent}%):', 
                           f"- {angebot.rabatt_betrag:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')])
    
    summen_data.append(['', 'MwSt. (19%):', 
                        f"{angebot.summe_mwst:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')])
    
    summen_data.append(['', 'Gesamtbetrag:', 
                        f"{angebot.summe_brutto:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')])
    
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
    
    # Schlussbemerkung
    if angebot.schlussbemerkung:
        elements.append(Paragraph(angebot.schlussbemerkung, style_normal))
        elements.append(Spacer(1, 5*mm))
    
    # Zahlungsbedingungen
    if angebot.zahlungsbedingung:
        elements.append(Paragraph(
            f"<b>Zahlungsbedingungen:</b> {angebot.zahlungsbedingung.generiere_zahlungstext()}", 
            style_small
        ))
    
    # PDF generieren
    doc.build(elements)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes


# ============================================================================
# E-MAIL VERSAND
# ============================================================================

@angebote_workflow_bp.route('/<int:id>/email', methods=['GET', 'POST'])
@login_required
@workflow_required
def email_senden(id):
    """Angebot per E-Mail versenden"""
    angebot = BusinessDocument.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            empfaenger = request.form.get('empfaenger')
            betreff = request.form.get('betreff')
            nachricht = request.form.get('nachricht')
            
            # PDF generieren falls nicht vorhanden
            if not angebot.pdf_pfad or not os.path.exists(angebot.pdf_pfad):
                pdf_bytes = generiere_angebot_pdf(angebot)
                
                pdf_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'pdfs', 'angebote')
                os.makedirs(pdf_dir, exist_ok=True)
                
                pdf_filename = f"{angebot.dokument_nummer.replace('/', '-')}.pdf"
                pdf_path = os.path.join(pdf_dir, pdf_filename)
                
                with open(pdf_path, 'wb') as f:
                    f.write(pdf_bytes)
                
                angebot.pdf_pfad = pdf_path
                angebot.pdf_erstellt_am = datetime.utcnow()
            
            # E-Mail senden
            email_gesendet = sende_angebot_email(
                empfaenger=empfaenger,
                betreff=betreff,
                nachricht=nachricht,
                pdf_pfad=angebot.pdf_pfad
            )
            
            if email_gesendet:
                # Status aktualisieren
                if angebot.status == DokumentStatus.ENTWURF.value:
                    angebot.status = DokumentStatus.VERSENDET.value
                
                angebot.versendet_am = datetime.utcnow()
                angebot.versendet_per = 'email'
                angebot.versendet_an = empfaenger
                angebot.geaendert_von = current_user.username
                
                db.session.commit()
                
                flash(f'Angebot erfolgreich an {empfaenger} gesendet!', 'success')
            else:
                flash('E-Mail konnte nicht gesendet werden.', 'danger')
            
            return redirect(url_for('angebote_workflow.show', id=id))
            
        except Exception as e:
            logger.error(f"Fehler beim E-Mail-Versand: {e}")
            flash(f'Fehler: {str(e)}', 'danger')
    
    # GET: E-Mail-Formular
    kunde = angebot.kunde
    
    # Standard-Betreff und Nachricht
    default_betreff = f"Angebot {angebot.dokument_nummer}"
    if angebot.betreff:
        default_betreff += f" - {angebot.betreff}"
    
    default_nachricht = f"""Sehr geehrte Damen und Herren,

anbei erhalten Sie unser Angebot {angebot.dokument_nummer}.

Das Angebot ist gültig bis zum {angebot.gueltig_bis.strftime('%d.%m.%Y') if angebot.gueltig_bis else '-'}.

Bei Fragen stehen wir Ihnen gerne zur Verfügung.

Mit freundlichen Grüßen
{current_user.username}"""
    
    return render_template('angebote_v2/email.html',
                         angebot=angebot,
                         kunde=kunde,
                         default_betreff=default_betreff,
                         default_nachricht=default_nachricht)


def sende_angebot_email(empfaenger, betreff, nachricht, pdf_pfad):
    """
    Sendet Angebot per E-Mail
    
    Args:
        empfaenger: E-Mail-Adresse
        betreff: Betreff
        nachricht: Nachrichtentext
        pdf_pfad: Pfad zur PDF-Datei
        
    Returns:
        bool: True wenn erfolgreich
    """
    try:
        # E-Mail-Konfiguration aus App-Settings
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.application import MIMEApplication
        
        # SMTP-Einstellungen (aus Umgebungsvariablen oder Einstellungen)
        smtp_server = os.environ.get('SMTP_SERVER', 'localhost')
        smtp_port = int(os.environ.get('SMTP_PORT', 25))
        smtp_user = os.environ.get('SMTP_USER', '')
        smtp_password = os.environ.get('SMTP_PASSWORD', '')
        smtp_from = os.environ.get('SMTP_FROM', 'noreply@stitchadmin.de')
        
        # E-Mail erstellen
        msg = MIMEMultipart()
        msg['From'] = smtp_from
        msg['To'] = empfaenger
        msg['Subject'] = betreff
        
        # Nachricht
        msg.attach(MIMEText(nachricht, 'plain', 'utf-8'))
        
        # PDF anhängen
        if pdf_pfad and os.path.exists(pdf_pfad):
            with open(pdf_pfad, 'rb') as f:
                pdf_attachment = MIMEApplication(f.read(), _subtype='pdf')
                pdf_attachment.add_header('Content-Disposition', 'attachment', 
                                         filename=os.path.basename(pdf_pfad))
                msg.attach(pdf_attachment)
        
        # Senden
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            if smtp_user and smtp_password:
                server.starttls()
                server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        logger.info(f"E-Mail an {empfaenger} gesendet: {betreff}")
        return True
        
    except Exception as e:
        logger.error(f"E-Mail-Versand fehlgeschlagen: {e}")
        return False


# ============================================================================
# API ENDPOINTS
# ============================================================================

@angebote_workflow_bp.route('/api/artikel/suche')
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


@angebote_workflow_bp.route('/api/statistiken')
@login_required
@workflow_required
def api_statistiken():
    """API: Angebots-Statistiken"""
    from sqlalchemy import func
    
    # Angebote pro Monat (letzte 12 Monate)
    heute = date.today()
    vor_12_monaten = heute - timedelta(days=365)
    
    monatliche_stats = db.session.query(
        func.strftime('%Y-%m', BusinessDocument.dokument_datum).label('monat'),
        func.count(BusinessDocument.id).label('anzahl'),
        func.sum(BusinessDocument.summe_brutto).label('summe')
    ).filter(
        BusinessDocument.dokument_typ == DokumentTyp.ANGEBOT.value,
        BusinessDocument.dokument_datum >= vor_12_monaten
    ).group_by(
        func.strftime('%Y-%m', BusinessDocument.dokument_datum)
    ).all()
    
    # Umwandlungsrate
    gesamt = BusinessDocument.query.filter_by(dokument_typ=DokumentTyp.ANGEBOT.value).count()
    angenommen = BusinessDocument.query.filter_by(
        dokument_typ=DokumentTyp.ANGEBOT.value,
        status=DokumentStatus.ANGENOMMEN.value
    ).count()
    
    umwandlungsrate = (angenommen / gesamt * 100) if gesamt > 0 else 0
    
    return jsonify({
        'monatlich': [{
            'monat': m.monat,
            'anzahl': m.anzahl,
            'summe': float(m.summe or 0)
        } for m in monatliche_stats],
        'umwandlungsrate': round(umwandlungsrate, 1),
        'gesamt': gesamt,
        'angenommen': angenommen
    })
