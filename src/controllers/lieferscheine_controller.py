# -*- coding: utf-8 -*-
"""
LIEFERSCHEIN CONTROLLER (Document-Workflow Integration)
=======================================================
Verwaltung von Lieferscheinen mit dem BusinessDocument-System:
- Erstellen aus Auftragsbestätigung
- Manuell erstellen
- CRUD-Operationen
- PDF-Generierung
- Teillieferungen
- Status-Workflow

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
from src.models.models import Customer, Article

# Document-Workflow Models
try:
    from src.models.document_workflow import (
        Nummernkreis, Zahlungsbedingung, BusinessDocument, DocumentPosition,
        DokumentTyp, DokumentStatus, PositionsTyp
    )
    WORKFLOW_AVAILABLE = True
except ImportError:
    WORKFLOW_AVAILABLE = False

import logging
logger = logging.getLogger(__name__)

# Blueprint
lieferscheine_bp = Blueprint('lieferscheine', __name__, url_prefix='/lieferscheine')


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

@lieferscheine_bp.route('/')
@login_required
@workflow_required
def index():
    """Lieferschein-Übersicht"""
    
    # Filter
    status_filter = request.args.get('status', 'alle')
    kunde_filter = request.args.get('kunde', '')
    
    # Query
    query = BusinessDocument.query.filter_by(dokument_typ=DokumentTyp.LIEFERSCHEIN.value)
    
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
    
    lieferscheine = query.order_by(BusinessDocument.dokument_datum.desc()).all()
    
    # Statistiken
    stats = {
        'gesamt': BusinessDocument.query.filter_by(dokument_typ=DokumentTyp.LIEFERSCHEIN.value).count(),
        'entwurf': BusinessDocument.query.filter_by(
            dokument_typ=DokumentTyp.LIEFERSCHEIN.value, 
            status=DokumentStatus.ENTWURF.value
        ).count(),
        'geliefert': BusinessDocument.query.filter_by(
            dokument_typ=DokumentTyp.LIEFERSCHEIN.value, 
            status=DokumentStatus.GELIEFERT.value
        ).count(),
        'teilgeliefert': BusinessDocument.query.filter_by(
            dokument_typ=DokumentTyp.LIEFERSCHEIN.value, 
            status=DokumentStatus.TEILGELIEFERT.value
        ).count(),
    }
    
    # Heute zu liefern
    heute = date.today()
    stats['heute'] = BusinessDocument.query.filter(
        BusinessDocument.dokument_typ == DokumentTyp.LIEFERSCHEIN.value,
        BusinessDocument.status == DokumentStatus.ENTWURF.value,
        BusinessDocument.lieferdatum == heute
    ).count()
    
    return render_template('lieferscheine/index.html',
                         lieferscheine=lieferscheine,
                         stats=stats,
                         status_filter=status_filter,
                         kunde_filter=kunde_filter)


# ============================================================================
# LIEFERSCHEIN ANZEIGEN
# ============================================================================

@lieferscheine_bp.route('/<int:id>')
@login_required
@workflow_required
def show(id):
    """Lieferschein anzeigen"""
    lieferschein = BusinessDocument.query.get_or_404(id)
    
    if lieferschein.dokument_typ != DokumentTyp.LIEFERSCHEIN.value:
        flash('Dokument ist kein Lieferschein.', 'warning')
        return redirect(url_for('lieferscheine.index'))
    
    # Vorgänger-Auftrag laden
    vorgaenger_auftrag = None
    if lieferschein.vorgaenger_id:
        vorgaenger_auftrag = BusinessDocument.query.get(lieferschein.vorgaenger_id)
    
    # Nachfolgende Rechnungen
    rechnungen = BusinessDocument.query.filter(
        BusinessDocument.vorgaenger_id == lieferschein.id,
        BusinessDocument.dokument_typ.in_([
            DokumentTyp.RECHNUNG.value,
            DokumentTyp.TEILRECHNUNG.value
        ])
    ).all()
    
    return render_template('lieferscheine/show.html', 
                         lieferschein=lieferschein,
                         vorgaenger_auftrag=vorgaenger_auftrag,
                         rechnungen=rechnungen)


# ============================================================================
# NEUER LIEFERSCHEIN (manuell)
# ============================================================================

@lieferscheine_bp.route('/neu', methods=['GET', 'POST'])
@login_required
@workflow_required
def neu():
    """Neuen Lieferschein manuell erstellen"""
    
    if request.method == 'POST':
        try:
            # Kunde laden
            kunde_id = request.form.get('kunde_id')
            kunde = Customer.query.get_or_404(kunde_id)
            
            # Dokumentnummer generieren
            dok_nummer = Nummernkreis.hole_naechste_nummer('lieferschein')
            
            # Lieferdatum
            lieferdatum_str = request.form.get('lieferdatum')
            lieferdatum = datetime.strptime(lieferdatum_str, '%Y-%m-%d').date() if lieferdatum_str else date.today()
            
            # Lieferschein erstellen
            lieferschein = BusinessDocument(
                dokument_nummer=dok_nummer,
                dokument_typ=DokumentTyp.LIEFERSCHEIN.value,
                kunde_id=kunde.id,
                
                # Adressen-Snapshot
                lieferadresse={
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
                interne_notiz=request.form.get('interne_notiz', ''),
                
                # Versand
                versandart=request.form.get('versandart', 'versand'),
                tracking_nummer=request.form.get('tracking_nummer', ''),
                
                # Tracking
                erstellt_von=current_user.username
            )
            
            db.session.add(lieferschein)
            db.session.flush()
            
            # Positionen hinzufügen (aus JSON)
            positionen_json = request.form.get('positionen_json')
            if positionen_json:
                import json
                positionen = json.loads(positionen_json)
                
                for idx, pos in enumerate(positionen, start=1):
                    position = DocumentPosition(
                        dokument_id=lieferschein.id,
                        position=idx,
                        typ=pos.get('typ', PositionsTyp.ARTIKEL.value),
                        artikel_id=pos.get('artikel_id'),
                        artikelnummer=pos.get('artikelnummer', ''),
                        bezeichnung=pos.get('bezeichnung', ''),
                        beschreibung=pos.get('beschreibung', ''),
                        menge=Decimal(str(pos.get('menge', 1))),
                        einheit=pos.get('einheit', 'Stk.'),
                        # Lieferschein hat keine Preise
                        einzelpreis_netto=Decimal('0'),
                        mwst_satz=Decimal('19')
                    )
                    db.session.add(position)
            
            db.session.commit()
            
            flash(f'Lieferschein {dok_nummer} erfolgreich erstellt!', 'success')
            return redirect(url_for('lieferscheine.show', id=lieferschein.id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler beim Erstellen des Lieferscheins: {e}")
            flash(f'Fehler: {str(e)}', 'danger')
    
    # GET: Formular anzeigen
    kunden = Customer.query.order_by(Customer.company_name, Customer.last_name).all()
    
    # Offene Aufträge für Auswahl
    offene_auftraege = BusinessDocument.query.filter(
        BusinessDocument.dokument_typ == DokumentTyp.AUFTRAGSBESTAETIGUNG.value,
        BusinessDocument.status.in_([DokumentStatus.VERSENDET.value, DokumentStatus.IN_BEARBEITUNG.value])
    ).order_by(BusinessDocument.dokument_datum.desc()).all()
    
    return render_template('lieferscheine/neu.html',
                         kunden=kunden,
                         offene_auftraege=offene_auftraege)


# ============================================================================
# LIEFERSCHEIN AUS AUFTRAG ERSTELLEN
# ============================================================================

@lieferscheine_bp.route('/aus-auftrag/<int:auftrag_id>', methods=['GET', 'POST'])
@login_required
@workflow_required
def aus_auftrag(auftrag_id):
    """Lieferschein aus Auftragsbestätigung erstellen"""
    auftrag = BusinessDocument.query.get_or_404(auftrag_id)
    
    if auftrag.dokument_typ != DokumentTyp.AUFTRAGSBESTAETIGUNG.value:
        flash('Quelldokument ist keine Auftragsbestätigung.', 'warning')
        return redirect(url_for('auftraege.index'))
    
    if auftrag.status not in [DokumentStatus.VERSENDET.value, DokumentStatus.IN_BEARBEITUNG.value, DokumentStatus.TEILGELIEFERT.value]:
        flash('Lieferschein kann nur aus bestätigten Aufträgen erstellt werden.', 'warning')
        return redirect(url_for('auftraege.show', id=auftrag_id))
    
    if request.method == 'POST':
        try:
            # Neue Dokumentnummer
            ls_nummer = Nummernkreis.hole_naechste_nummer('lieferschein')
            
            # Lieferdatum
            lieferdatum_str = request.form.get('lieferdatum')
            lieferdatum = datetime.strptime(lieferdatum_str, '%Y-%m-%d').date() if lieferdatum_str else date.today()
            
            # Lieferschein erstellen
            lieferschein = BusinessDocument(
                dokument_nummer=ls_nummer,
                dokument_typ=DokumentTyp.LIEFERSCHEIN.value,
                vorgaenger_id=auftrag.id,
                kunde_id=auftrag.kunde_id,
                lieferadresse=auftrag.lieferadresse or auftrag.rechnungsadresse,
                
                dokument_datum=date.today(),
                lieferdatum=lieferdatum,
                
                status=DokumentStatus.ENTWURF.value,
                
                betreff=f"Lieferung zu Auftrag {auftrag.dokument_nummer}",
                interne_notiz=f"Erstellt aus Auftragsbestätigung {auftrag.dokument_nummer}",
                
                versandart=request.form.get('versandart', 'versand'),
                tracking_nummer=request.form.get('tracking_nummer', ''),
                
                erstellt_von=current_user.username
            )
            
            db.session.add(lieferschein)
            db.session.flush()
            
            # Positionen aus Form (mit Liefermengen)
            positionen_json = request.form.get('positionen_json')
            if positionen_json:
                import json
                positionen = json.loads(positionen_json)
                
                pos_nr = 1
                for pos in positionen:
                    liefermenge = Decimal(str(pos.get('liefermenge', 0)))
                    if liefermenge > 0:
                        position = DocumentPosition(
                            dokument_id=lieferschein.id,
                            position=pos_nr,
                            typ=pos.get('typ', PositionsTyp.ARTIKEL.value),
                            artikel_id=pos.get('artikel_id'),
                            artikelnummer=pos.get('artikelnummer', ''),
                            bezeichnung=pos.get('bezeichnung', ''),
                            beschreibung=pos.get('beschreibung', ''),
                            menge=liefermenge,
                            einheit=pos.get('einheit', 'Stk.'),
                            einzelpreis_netto=Decimal('0'),
                            mwst_satz=Decimal('19')
                        )
                        db.session.add(position)
                        pos_nr += 1
            
            # Prüfen ob Teillieferung
            ist_volllieferung = request.form.get('volllieferung') == '1'
            
            if ist_volllieferung:
                auftrag.status = DokumentStatus.GELIEFERT.value
            else:
                auftrag.status = DokumentStatus.TEILGELIEFERT.value
            
            auftrag.geaendert_von = current_user.username
            
            db.session.commit()
            
            flash(f'Lieferschein {ls_nummer} erstellt!', 'success')
            return redirect(url_for('lieferscheine.show', id=lieferschein.id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler bei Lieferschein-Erstellung: {e}")
            flash(f'Fehler: {str(e)}', 'danger')
    
    # GET: Formular mit Auftrags-Positionen
    return render_template('lieferscheine/aus_auftrag.html', auftrag=auftrag)


# ============================================================================
# LIEFERSCHEIN BEARBEITEN
# ============================================================================

@lieferscheine_bp.route('/<int:id>/bearbeiten', methods=['GET', 'POST'])
@login_required
@workflow_required
def bearbeiten(id):
    """Lieferschein bearbeiten"""
    lieferschein = BusinessDocument.query.get_or_404(id)
    
    if lieferschein.status != DokumentStatus.ENTWURF.value:
        flash('Nur Entwürfe können bearbeitet werden.', 'warning')
        return redirect(url_for('lieferscheine.show', id=id))
    
    if request.method == 'POST':
        try:
            # Felder aktualisieren
            lieferschein.betreff = request.form.get('betreff', '')
            lieferschein.interne_notiz = request.form.get('interne_notiz', '')
            lieferschein.versandart = request.form.get('versandart', 'versand')
            lieferschein.tracking_nummer = request.form.get('tracking_nummer', '')
            
            # Lieferdatum
            lieferdatum_str = request.form.get('lieferdatum')
            lieferschein.lieferdatum = datetime.strptime(lieferdatum_str, '%Y-%m-%d').date() if lieferdatum_str else None
            
            lieferschein.geaendert_von = current_user.username
            
            # Positionen aktualisieren
            positionen_json = request.form.get('positionen_json')
            if positionen_json:
                import json
                
                DocumentPosition.query.filter_by(dokument_id=lieferschein.id).delete()
                
                positionen = json.loads(positionen_json)
                for idx, pos in enumerate(positionen, start=1):
                    position = DocumentPosition(
                        dokument_id=lieferschein.id,
                        position=idx,
                        typ=pos.get('typ', PositionsTyp.ARTIKEL.value),
                        artikelnummer=pos.get('artikelnummer', ''),
                        bezeichnung=pos.get('bezeichnung', ''),
                        beschreibung=pos.get('beschreibung', ''),
                        menge=Decimal(str(pos.get('menge', 1))),
                        einheit=pos.get('einheit', 'Stk.'),
                        einzelpreis_netto=Decimal('0'),
                        mwst_satz=Decimal('19')
                    )
                    db.session.add(position)
            
            db.session.commit()
            
            flash('Lieferschein aktualisiert!', 'success')
            return redirect(url_for('lieferscheine.show', id=id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler beim Aktualisieren: {e}")
            flash(f'Fehler: {str(e)}', 'danger')
    
    return render_template('lieferscheine/bearbeiten.html', lieferschein=lieferschein)


# ============================================================================
# STATUS-AKTIONEN
# ============================================================================

@lieferscheine_bp.route('/<int:id>/ausliefern', methods=['POST'])
@login_required
@workflow_required
def ausliefern(id):
    """Lieferschein als ausgeliefert markieren"""
    lieferschein = BusinessDocument.query.get_or_404(id)
    
    if lieferschein.status != DokumentStatus.ENTWURF.value:
        flash('Lieferschein wurde bereits ausgeliefert.', 'warning')
        return redirect(url_for('lieferscheine.show', id=id))
    
    try:
        lieferschein.status = DokumentStatus.GELIEFERT.value
        lieferschein.lieferdatum = date.today()
        lieferschein.geaendert_von = current_user.username
        
        db.session.commit()
        
        flash(f'Lieferschein {lieferschein.dokument_nummer} als ausgeliefert markiert.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('lieferscheine.show', id=id))


@lieferscheine_bp.route('/<int:id>/stornieren', methods=['POST'])
@login_required
@workflow_required
def stornieren(id):
    """Lieferschein stornieren"""
    lieferschein = BusinessDocument.query.get_or_404(id)
    
    if lieferschein.status == DokumentStatus.STORNIERT.value:
        flash('Lieferschein ist bereits storniert.', 'warning')
        return redirect(url_for('lieferscheine.show', id=id))
    
    try:
        lieferschein.status = DokumentStatus.STORNIERT.value
        lieferschein.geaendert_von = current_user.username
        
        db.session.commit()
        
        flash(f'Lieferschein {lieferschein.dokument_nummer} wurde storniert.', 'info')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('lieferscheine.show', id=id))


# ============================================================================
# RECHNUNG AUS LIEFERSCHEIN
# ============================================================================

@lieferscheine_bp.route('/<int:id>/rechnung', methods=['POST'])
@login_required
@workflow_required
def rechnung_erstellen(id):
    """Rechnung aus Lieferschein erstellen"""
    lieferschein = BusinessDocument.query.get_or_404(id)
    
    if lieferschein.status != DokumentStatus.GELIEFERT.value:
        flash('Rechnung kann nur aus ausgelieferten Lieferscheinen erstellt werden.', 'warning')
        return redirect(url_for('lieferscheine.show', id=id))
    
    try:
        # Preise aus Vorgänger-Auftrag holen
        auftrag = None
        if lieferschein.vorgaenger_id:
            auftrag = BusinessDocument.query.get(lieferschein.vorgaenger_id)
        
        # Neue Dokumentnummer
        re_nummer = Nummernkreis.hole_naechste_nummer('rechnung')
        
        # Zahlungsbedingung
        zb = None
        if auftrag and auftrag.zahlungsbedingung_id:
            zb = Zahlungsbedingung.query.get(auftrag.zahlungsbedingung_id)
        if not zb:
            zb = Zahlungsbedingung.query.filter_by(standard=True, aktiv=True).first()
        
        faelligkeit = date.today() + timedelta(days=zb.zahlungsziel_tage if zb else 14)
        
        # Rechnung erstellen
        rechnung = BusinessDocument(
            dokument_nummer=re_nummer,
            dokument_typ=DokumentTyp.RECHNUNG.value,
            vorgaenger_id=lieferschein.id,
            kunde_id=lieferschein.kunde_id,
            rechnungsadresse=auftrag.rechnungsadresse if auftrag else lieferschein.lieferadresse,
            
            dokument_datum=date.today(),
            lieferdatum=lieferschein.lieferdatum,
            leistungsdatum=lieferschein.lieferdatum,
            faelligkeitsdatum=faelligkeit,
            
            status=DokumentStatus.OFFEN.value,
            
            betreff=f"Rechnung zu Lieferschein {lieferschein.dokument_nummer}",
            interne_notiz=f"Erstellt aus Lieferschein {lieferschein.dokument_nummer}",
            
            zahlungsbedingung_id=zb.id if zb else None,
            zahlungsziel_tage=zb.zahlungsziel_tage if zb else 14,
            skonto_prozent=zb.skonto_prozent if zb else 0,
            skonto_tage=zb.skonto_tage if zb else 0,
            zahlungstext=zb.generiere_zahlungstext() if zb else '',
            
            erstellt_von=current_user.username
        )
        
        db.session.add(rechnung)
        db.session.flush()
        
        # Positionen mit Preisen aus Auftrag kopieren
        auftrag_positionen = {}
        if auftrag:
            for pos in auftrag.positionen:
                key = (pos.artikelnummer, pos.bezeichnung)
                auftrag_positionen[key] = pos
        
        for ls_pos in lieferschein.positionen:
            key = (ls_pos.artikelnummer, ls_pos.bezeichnung)
            auftrag_pos = auftrag_positionen.get(key)
            
            einzelpreis = auftrag_pos.einzelpreis_netto if auftrag_pos else Decimal('0')
            
            neue_pos = DocumentPosition(
                dokument_id=rechnung.id,
                position=ls_pos.position,
                typ=ls_pos.typ,
                artikel_id=ls_pos.artikel_id,
                artikelnummer=ls_pos.artikelnummer,
                bezeichnung=ls_pos.bezeichnung,
                beschreibung=ls_pos.beschreibung,
                menge=ls_pos.menge,
                einheit=ls_pos.einheit,
                einzelpreis_netto=einzelpreis,
                mwst_satz=Decimal('19'),
                rabatt_prozent=auftrag_pos.rabatt_prozent if auftrag_pos else Decimal('0')
            )
            neue_pos.berechne()
            db.session.add(neue_pos)
        
        rechnung.berechne_summen()
        
        db.session.commit()
        
        flash(f'Rechnung {re_nummer} erstellt!', 'success')
        return redirect(url_for('rechnungen.show', id=rechnung.id))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Fehler bei Rechnungs-Erstellung: {e}")
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('lieferscheine.show', id=id))


# ============================================================================
# PDF GENERIERUNG
# ============================================================================

@lieferscheine_bp.route('/<int:id>/pdf')
@login_required
@workflow_required
def pdf_generieren(id):
    """PDF für Lieferschein generieren"""
    lieferschein = BusinessDocument.query.get_or_404(id)
    
    try:
        pdf_bytes = generiere_lieferschein_pdf(lieferschein)
        
        # PDF speichern
        pdf_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'pdfs', 'lieferscheine')
        os.makedirs(pdf_dir, exist_ok=True)
        
        pdf_filename = f"{lieferschein.dokument_nummer.replace('/', '-')}.pdf"
        pdf_path = os.path.join(pdf_dir, pdf_filename)
        
        with open(pdf_path, 'wb') as f:
            f.write(pdf_bytes)
        
        lieferschein.pdf_pfad = pdf_path
        lieferschein.pdf_erstellt_am = datetime.utcnow()
        db.session.commit()
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=pdf_filename
        )
        
    except Exception as e:
        logger.error(f"Fehler bei PDF-Generierung: {e}")
        flash(f'Fehler bei PDF-Generierung: {str(e)}', 'danger')
        return redirect(url_for('lieferscheine.show', id=id))


@lieferscheine_bp.route('/<int:id>/pdf/vorschau')
@login_required
@workflow_required
def pdf_vorschau(id):
    """PDF-Vorschau im Browser"""
    lieferschein = BusinessDocument.query.get_or_404(id)
    
    try:
        pdf_bytes = generiere_lieferschein_pdf(lieferschein)
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=False
        )
        
    except Exception as e:
        logger.error(f"Fehler bei PDF-Vorschau: {e}")
        flash(f'Fehler: {str(e)}', 'danger')
        return redirect(url_for('lieferscheine.show', id=id))


def generiere_lieferschein_pdf(lieferschein):
    """
    Generiert PDF für einen Lieferschein
    
    WICHTIG: Lieferschein enthält KEINE Preise!
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    
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
    
    # Lieferadresse
    adresse = lieferschein.lieferadresse or {}
    empfaenger = f"""
    <b>Lieferadresse:</b><br/>
    {adresse.get('company', '') or adresse.get('name', '')}<br/>
    {adresse.get('contact', '') or ''}<br/>
    {adresse.get('street', '')} {adresse.get('house_number', '')}<br/>
    {adresse.get('postal_code', '')} {adresse.get('city', '')}
    """
    elements.append(Paragraph(empfaenger.strip(), style_normal))
    elements.append(Spacer(1, 10*mm))
    
    # Dokumenttitel
    elements.append(Paragraph("<b>LIEFERSCHEIN</b>", style_header))
    elements.append(Spacer(1, 5*mm))
    
    # Dokumentinfo
    info_data = [
        ['Lieferschein-Nr.:', lieferschein.dokument_nummer],
        ['Datum:', lieferschein.dokument_datum.strftime('%d.%m.%Y')],
        ['Lieferdatum:', lieferschein.lieferdatum.strftime('%d.%m.%Y') if lieferschein.lieferdatum else '-'],
    ]
    if lieferschein.versandart:
        versandart_text = {
            'versand': 'Versand',
            'abholung': 'Abholung',
            'spedition': 'Spedition'
        }.get(lieferschein.versandart, lieferschein.versandart)
        info_data.append(['Versandart:', versandart_text])
    if lieferschein.tracking_nummer:
        info_data.append(['Sendungsnr.:', lieferschein.tracking_nummer])
    if lieferschein.vorgaenger:
        info_data.append(['Zu Auftrag:', lieferschein.vorgaenger.dokument_nummer])
    
    info_table = Table(info_data, colWidths=[40*mm, 60*mm])
    info_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10*mm))
    
    # Betreff
    if lieferschein.betreff:
        elements.append(Paragraph(f"<b>Betreff: {lieferschein.betreff}</b>", style_normal))
        elements.append(Spacer(1, 5*mm))
    
    # === POSITIONEN (ohne Preise!) ===
    pos_data = [['Pos.', 'Artikelnr.', 'Bezeichnung', 'Menge', 'Einheit']]
    
    for pos in lieferschein.positionen:
        bezeichnung = pos.bezeichnung
        if pos.beschreibung:
            bezeichnung += f"\n{pos.beschreibung}"
        
        pos_data.append([
            str(pos.position),
            pos.artikelnummer or '-',
            Paragraph(bezeichnung, style_small),
            f"{pos.menge:,.0f}".replace(',', '.'),
            pos.einheit
        ])
    
    col_widths = [12*mm, 30*mm, 85*mm, 20*mm, 20*mm]
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
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
        ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),
    ]))
    elements.append(pos_table)
    elements.append(Spacer(1, 15*mm))
    
    # === FUSSBEREICH ===
    elements.append(Paragraph("Bitte prüfen Sie die Lieferung auf Vollständigkeit und eventuelle Transportschäden.", style_normal))
    elements.append(Spacer(1, 10*mm))
    
    # Unterschriftsfeld
    elements.append(Paragraph("_" * 50, style_normal))
    elements.append(Paragraph("Empfangsbestätigung (Datum, Unterschrift)", style_small))
    
    doc.build(elements)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes


# ============================================================================
# API ENDPOINTS
# ============================================================================

@lieferscheine_bp.route('/api/offene-auftraege')
@login_required
@workflow_required
def api_offene_auftraege():
    """API: Offene Aufträge für Lieferschein-Erstellung"""
    auftraege = BusinessDocument.query.filter(
        BusinessDocument.dokument_typ == DokumentTyp.AUFTRAGSBESTAETIGUNG.value,
        BusinessDocument.status.in_([DokumentStatus.VERSENDET.value, DokumentStatus.IN_BEARBEITUNG.value])
    ).order_by(BusinessDocument.dokument_datum.desc()).all()
    
    return jsonify([{
        'id': a.id,
        'nummer': a.dokument_nummer,
        'kunde': a.kunde.display_name if a.kunde else '-',
        'datum': a.dokument_datum.strftime('%d.%m.%Y'),
        'betrag': float(a.summe_brutto or 0)
    } for a in auftraege])
