# -*- coding: utf-8 -*-
"""
RECHNUNGEN CONTROLLER (Document-Workflow Integration)
=====================================================
Verwaltung von Rechnungen mit dem BusinessDocument-System:
- Erstellen aus Auftrag/Lieferschein
- Manuell erstellen
- CRUD-Operationen
- PDF-Generierung
- Zahlungsverwaltung
- Fälligkeits-Tracking

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
        Nummernkreis, Zahlungsbedingung, BusinessDocument, DocumentPosition, DocumentPayment,
        DokumentTyp, DokumentStatus, PositionsTyp
    )
    WORKFLOW_AVAILABLE = True
except ImportError:
    WORKFLOW_AVAILABLE = False

import logging
logger = logging.getLogger(__name__)

# Blueprint
rechnungen_bp = Blueprint('rechnungen', __name__, url_prefix='/rechnungen')


def workflow_required(f):
    """Decorator: Prüft ob Document-Workflow verfügbar"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not WORKFLOW_AVAILABLE:
            flash('Document-Workflow nicht verfügbar.', 'warning')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# ÜBERSICHT
# ============================================================================

@rechnungen_bp.route('/')
@login_required
@workflow_required
def index():
    """Rechnungs-Übersicht"""
    
    status_filter = request.args.get('status', 'alle')
    kunde_filter = request.args.get('kunde', '')
    
    # Query - alle Rechnungstypen
    query = BusinessDocument.query.filter(
        BusinessDocument.dokument_typ.in_([
            DokumentTyp.RECHNUNG.value,
            DokumentTyp.ANZAHLUNG.value,
            DokumentTyp.TEILRECHNUNG.value,
            DokumentTyp.SCHLUSSRECHNUNG.value
        ])
    )
    
    if status_filter != 'alle':
        query = query.filter_by(status=status_filter)
    
    if kunde_filter:
        query = query.join(Customer).filter(
            db.or_(
                Customer.company_name.ilike(f'%{kunde_filter}%'),
                Customer.first_name.ilike(f'%{kunde_filter}%'),
                Customer.last_name.ilike(f'%{kunde_filter}%')
            )
        )
    
    rechnungen = query.order_by(BusinessDocument.dokument_datum.desc()).all()
    
    # Statistiken
    alle_rechnungen = BusinessDocument.query.filter(
        BusinessDocument.dokument_typ.in_([
            DokumentTyp.RECHNUNG.value, DokumentTyp.ANZAHLUNG.value,
            DokumentTyp.TEILRECHNUNG.value, DokumentTyp.SCHLUSSRECHNUNG.value
        ])
    )
    
    stats = {
        'gesamt': alle_rechnungen.count(),
        'offen': alle_rechnungen.filter_by(status=DokumentStatus.OFFEN.value).count(),
        'teilbezahlt': alle_rechnungen.filter_by(status=DokumentStatus.TEILBEZAHLT.value).count(),
        'bezahlt': alle_rechnungen.filter_by(status=DokumentStatus.BEZAHLT.value).count(),
        'ueberfaellig': 0,
        'summe_offen': Decimal('0.00')
    }
    
    # Überfällige berechnen
    heute = date.today()
    for r in alle_rechnungen.filter(BusinessDocument.status.in_([DokumentStatus.OFFEN.value, DokumentStatus.TEILBEZAHLT.value])).all():
        if r.faelligkeitsdatum and r.faelligkeitsdatum < heute:
            stats['ueberfaellig'] += 1
        stats['summe_offen'] += r.offener_betrag() if hasattr(r, 'offener_betrag') else (r.summe_brutto or Decimal('0'))
    
    return render_template('rechnungen/index.html',
                         rechnungen=rechnungen,
                         stats=stats,
                         status_filter=status_filter,
                         kunde_filter=kunde_filter)


# ============================================================================
# RECHNUNG ANZEIGEN
# ============================================================================

@rechnungen_bp.route('/<int:id>')
@login_required
@workflow_required
def show(id):
    """Rechnung anzeigen"""
    rechnung = BusinessDocument.query.get_or_404(id)
    
    if rechnung.dokument_typ not in [DokumentTyp.RECHNUNG.value, DokumentTyp.ANZAHLUNG.value,
                                      DokumentTyp.TEILRECHNUNG.value, DokumentTyp.SCHLUSSRECHNUNG.value]:
        flash('Dokument ist keine Rechnung.', 'warning')
        return redirect(url_for('rechnungen.index'))
    
    # Vorgänger laden
    vorgaenger = None
    if rechnung.vorgaenger_id:
        vorgaenger = BusinessDocument.query.get(rechnung.vorgaenger_id)
    
    # Zahlungen
    zahlungen = rechnung.zahlungen if hasattr(rechnung, 'zahlungen') else []
    
    # Offener Betrag berechnen
    offener_betrag = rechnung.offener_betrag() if hasattr(rechnung, 'offener_betrag') else rechnung.summe_brutto
    
    # Überfällig?
    ist_ueberfaellig = False
    tage_ueberfaellig = 0
    if rechnung.faelligkeitsdatum and rechnung.status in [DokumentStatus.OFFEN.value, DokumentStatus.TEILBEZAHLT.value]:
        if rechnung.faelligkeitsdatum < date.today():
            ist_ueberfaellig = True
            tage_ueberfaellig = (date.today() - rechnung.faelligkeitsdatum).days
    
    return render_template('rechnungen/show.html',
                         rechnung=rechnung,
                         vorgaenger=vorgaenger,
                         zahlungen=zahlungen,
                         offener_betrag=offener_betrag,
                         ist_ueberfaellig=ist_ueberfaellig,
                         tage_ueberfaellig=tage_ueberfaellig)


# ============================================================================
# NEUE RECHNUNG (manuell)
# ============================================================================

@rechnungen_bp.route('/neu', methods=['GET', 'POST'])
@login_required
@workflow_required
def neu():
    """Neue Rechnung manuell erstellen"""
    
    if request.method == 'POST':
        try:
            kunde_id = request.form.get('kunde_id')
            kunde = Customer.query.get_or_404(kunde_id)
            
            # Rechnungstyp
            rechnungstyp = request.form.get('rechnungstyp', 'rechnung')
            if rechnungstyp == 'anzahlung':
                dok_typ = DokumentTyp.ANZAHLUNG.value
            elif rechnungstyp == 'teilrechnung':
                dok_typ = DokumentTyp.TEILRECHNUNG.value
            else:
                dok_typ = DokumentTyp.RECHNUNG.value
            
            dok_nummer = Nummernkreis.hole_naechste_nummer('rechnung')
            
            # Zahlungsbedingung
            zb_id = request.form.get('zahlungsbedingung_id')
            zb = Zahlungsbedingung.query.get(zb_id) if zb_id else None
            if not zb:
                zb = Zahlungsbedingung.query.filter_by(standard=True, aktiv=True).first()
            
            # Fälligkeit berechnen
            faelligkeit = date.today() + timedelta(days=zb.zahlungsziel_tage if zb else 14)
            
            # Leistungsdatum
            leistungsdatum_str = request.form.get('leistungsdatum')
            leistungsdatum = datetime.strptime(leistungsdatum_str, '%Y-%m-%d').date() if leistungsdatum_str else date.today()
            
            rechnung = BusinessDocument(
                dokument_nummer=dok_nummer,
                dokument_typ=dok_typ,
                kunde_id=kunde.id,
                
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
                
                dokument_datum=date.today(),
                leistungsdatum=leistungsdatum,
                faelligkeitsdatum=faelligkeit,
                
                status=DokumentStatus.OFFEN.value,
                
                betreff=request.form.get('betreff', ''),
                einleitung=request.form.get('einleitung', ''),
                schlussbemerkung=request.form.get('schlussbemerkung', ''),
                interne_notiz=request.form.get('interne_notiz', ''),
                
                zahlungsbedingung_id=zb.id if zb else None,
                zahlungsziel_tage=zb.zahlungsziel_tage if zb else 14,
                skonto_prozent=zb.skonto_prozent if zb else 0,
                skonto_tage=zb.skonto_tage if zb else 0,
                zahlungstext=zb.generiere_zahlungstext() if zb else '',
                
                erstellt_von=current_user.username
            )
            
            db.session.add(rechnung)
            db.session.flush()
            
            # Positionen
            positionen_json = request.form.get('positionen_json')
            if positionen_json:
                import json
                positionen = json.loads(positionen_json)
                
                for idx, pos in enumerate(positionen, start=1):
                    position = DocumentPosition(
                        dokument_id=rechnung.id,
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
            
            rechnung.berechne_summen()
            db.session.commit()
            
            flash(f'Rechnung {dok_nummer} erstellt!', 'success')
            return redirect(url_for('rechnungen.show', id=rechnung.id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler: {e}")
            flash(f'Fehler: {str(e)}', 'danger')
    
    kunden = Customer.query.order_by(Customer.company_name, Customer.last_name).all()
    zahlungsbedingungen = Zahlungsbedingung.query.filter_by(aktiv=True).order_by(Zahlungsbedingung.sortierung).all()
    
    return render_template('rechnungen/neu.html',
                         kunden=kunden,
                         zahlungsbedingungen=zahlungsbedingungen)


# ============================================================================
# RECHNUNG BEARBEITEN
# ============================================================================

@rechnungen_bp.route('/<int:id>/bearbeiten', methods=['GET', 'POST'])
@login_required
@workflow_required
def bearbeiten(id):
    """Rechnung bearbeiten (nur wenn noch offen und keine Zahlungen)"""
    rechnung = BusinessDocument.query.get_or_404(id)
    
    # Prüfen ob bearbeitbar
    if rechnung.status not in [DokumentStatus.OFFEN.value]:
        flash('Diese Rechnung kann nicht mehr bearbeitet werden.', 'warning')
        return redirect(url_for('rechnungen.show', id=id))
    
    if rechnung.zahlungen and len(list(rechnung.zahlungen)) > 0:
        flash('Rechnungen mit Zahlungen können nicht bearbeitet werden.', 'warning')
        return redirect(url_for('rechnungen.show', id=id))
    
    if request.method == 'POST':
        try:
            rechnung.betreff = request.form.get('betreff', '')
            rechnung.einleitung = request.form.get('einleitung', '')
            rechnung.schlussbemerkung = request.form.get('schlussbemerkung', '')
            rechnung.interne_notiz = request.form.get('interne_notiz', '')
            
            leistungsdatum_str = request.form.get('leistungsdatum')
            if leistungsdatum_str:
                rechnung.leistungsdatum = datetime.strptime(leistungsdatum_str, '%Y-%m-%d').date()
            
            rechnung.geaendert_von = current_user.username
            
            # Positionen aktualisieren
            positionen_json = request.form.get('positionen_json')
            if positionen_json:
                import json
                DocumentPosition.query.filter_by(dokument_id=rechnung.id).delete()
                
                positionen = json.loads(positionen_json)
                for idx, pos in enumerate(positionen, start=1):
                    position = DocumentPosition(
                        dokument_id=rechnung.id,
                        position=idx,
                        typ=pos.get('typ', PositionsTyp.ARTIKEL.value),
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
            
            rechnung.berechne_summen()
            db.session.commit()
            
            flash('Rechnung aktualisiert!', 'success')
            return redirect(url_for('rechnungen.show', id=id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {str(e)}', 'danger')
    
    zahlungsbedingungen = Zahlungsbedingung.query.filter_by(aktiv=True).order_by(Zahlungsbedingung.sortierung).all()
    
    return render_template('rechnungen/bearbeiten.html',
                         rechnung=rechnung,
                         zahlungsbedingungen=zahlungsbedingungen)


# ============================================================================
# ZAHLUNGEN
# ============================================================================

@rechnungen_bp.route('/<int:id>/zahlung', methods=['GET', 'POST'])
@login_required
@workflow_required
def zahlung_erfassen(id):
    """Zahlung für Rechnung erfassen"""
    rechnung = BusinessDocument.query.get_or_404(id)
    
    if rechnung.status in [DokumentStatus.BEZAHLT.value, DokumentStatus.STORNIERT.value]:
        flash('Für diese Rechnung können keine Zahlungen mehr erfasst werden.', 'warning')
        return redirect(url_for('rechnungen.show', id=id))
    
    if request.method == 'POST':
        try:
            betrag = Decimal(request.form.get('betrag', '0').replace(',', '.'))
            zahlungsart = request.form.get('zahlungsart', 'ueberweisung')
            zahlung_datum_str = request.form.get('zahlung_datum')
            zahlung_datum = datetime.strptime(zahlung_datum_str, '%Y-%m-%d').date() if zahlung_datum_str else date.today()
            
            if betrag <= 0:
                flash('Bitte gültigen Betrag eingeben.', 'warning')
                return redirect(url_for('rechnungen.zahlung_erfassen', id=id))
            
            zahlung = DocumentPayment(
                dokument_id=rechnung.id,
                zahlungsart=zahlungsart,
                betrag=betrag,
                zahlung_datum=zahlung_datum,
                transaktions_id=request.form.get('transaktions_id', ''),
                bank_referenz=request.form.get('bank_referenz', ''),
                notiz=request.form.get('notiz', ''),
                bestaetigt=True,
                bestaetigt_von=current_user.username,
                bestaetigt_am=datetime.utcnow(),
                erstellt_von=current_user.username
            )
            
            db.session.add(zahlung)
            
            # Status aktualisieren
            offener_betrag = rechnung.offener_betrag() - betrag
            
            if offener_betrag <= Decimal('0.01'):
                rechnung.status = DokumentStatus.BEZAHLT.value
                rechnung.bezahlt_am = zahlung_datum
            else:
                rechnung.status = DokumentStatus.TEILBEZAHLT.value
            
            rechnung.geaendert_von = current_user.username
            
            db.session.commit()
            
            flash(f'Zahlung von {betrag:.2f} € erfasst!', 'success')
            return redirect(url_for('rechnungen.show', id=id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler bei Zahlung: {e}")
            flash(f'Fehler: {str(e)}', 'danger')
    
    offener_betrag = rechnung.offener_betrag() if hasattr(rechnung, 'offener_betrag') else rechnung.summe_brutto
    
    return render_template('rechnungen/zahlung.html',
                         rechnung=rechnung,
                         offener_betrag=offener_betrag)


@rechnungen_bp.route('/<int:id>/zahlung/<int:zahlung_id>/loeschen', methods=['POST'])
@login_required
@workflow_required
def zahlung_loeschen(id, zahlung_id):
    """Zahlung löschen"""
    rechnung = BusinessDocument.query.get_or_404(id)
    zahlung = DocumentPayment.query.get_or_404(zahlung_id)
    
    if zahlung.dokument_id != rechnung.id:
        flash('Zahlung gehört nicht zu dieser Rechnung.', 'danger')
        return redirect(url_for('rechnungen.show', id=id))
    
    try:
        db.session.delete(zahlung)
        
        # Status neu berechnen
        verbleibende_zahlungen = [z for z in rechnung.zahlungen if z.id != zahlung_id]
        summe_gezahlt = sum(z.betrag for z in verbleibende_zahlungen if z.bestaetigt)
        
        if summe_gezahlt <= 0:
            rechnung.status = DokumentStatus.OFFEN.value
            rechnung.bezahlt_am = None
        elif summe_gezahlt < rechnung.summe_brutto:
            rechnung.status = DokumentStatus.TEILBEZAHLT.value
            rechnung.bezahlt_am = None
        else:
            rechnung.status = DokumentStatus.BEZAHLT.value
        
        db.session.commit()
        
        flash('Zahlung gelöscht.', 'info')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('rechnungen.show', id=id))


# ============================================================================
# STATUS-AKTIONEN
# ============================================================================

@rechnungen_bp.route('/<int:id>/stornieren', methods=['POST'])
@login_required
@workflow_required
def stornieren(id):
    """Rechnung stornieren"""
    rechnung = BusinessDocument.query.get_or_404(id)
    
    if rechnung.status == DokumentStatus.BEZAHLT.value:
        flash('Bezahlte Rechnungen können nicht storniert werden. Erstellen Sie eine Gutschrift.', 'warning')
        return redirect(url_for('rechnungen.show', id=id))
    
    try:
        rechnung.status = DokumentStatus.STORNIERT.value
        rechnung.geaendert_von = current_user.username
        db.session.commit()
        
        flash(f'Rechnung {rechnung.dokument_nummer} storniert.', 'info')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('rechnungen.show', id=id))


@rechnungen_bp.route('/<int:id>/mahnen', methods=['POST'])
@login_required
@workflow_required
def mahnen(id):
    """Mahnstufe erhöhen"""
    rechnung = BusinessDocument.query.get_or_404(id)
    
    if rechnung.status not in [DokumentStatus.OFFEN.value, DokumentStatus.TEILBEZAHLT.value, DokumentStatus.UEBERFAELLIG.value, DokumentStatus.GEMAHNT.value]:
        flash('Diese Rechnung kann nicht gemahnt werden.', 'warning')
        return redirect(url_for('rechnungen.show', id=id))
    
    try:
        rechnung.mahnstufe = (rechnung.mahnstufe or 0) + 1
        rechnung.letzte_mahnung_am = date.today()
        rechnung.status = DokumentStatus.GEMAHNT.value
        rechnung.geaendert_von = current_user.username
        
        db.session.commit()
        
        flash(f'Mahnstufe auf {rechnung.mahnstufe} erhöht.', 'info')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('rechnungen.show', id=id))


# ============================================================================
# GUTSCHRIFT ERSTELLEN
# ============================================================================

@rechnungen_bp.route('/<int:id>/gutschrift', methods=['POST'])
@login_required
@workflow_required
def gutschrift_erstellen(id):
    """Gutschrift zu einer Rechnung erstellen"""
    rechnung = BusinessDocument.query.get_or_404(id)
    
    try:
        gs_nummer = Nummernkreis.hole_naechste_nummer('gutschrift')
        
        gutschrift = BusinessDocument(
            dokument_nummer=gs_nummer,
            dokument_typ=DokumentTyp.GUTSCHRIFT.value,
            vorgaenger_id=rechnung.id,
            kunde_id=rechnung.kunde_id,
            rechnungsadresse=rechnung.rechnungsadresse,
            
            dokument_datum=date.today(),
            
            summe_netto=-rechnung.summe_netto,
            summe_mwst=-rechnung.summe_mwst,
            summe_brutto=-rechnung.summe_brutto,
            
            status=DokumentStatus.OFFEN.value,
            
            betreff=f"Gutschrift zu Rechnung {rechnung.dokument_nummer}",
            interne_notiz=f"Gutschrift erstellt aus Rechnung {rechnung.dokument_nummer}",
            
            erstellt_von=current_user.username
        )
        
        db.session.add(gutschrift)
        db.session.flush()
        
        # Positionen mit negativen Beträgen kopieren
        for pos in rechnung.positionen:
            neue_pos = DocumentPosition(
                dokument_id=gutschrift.id,
                position=pos.position,
                typ=pos.typ,
                artikelnummer=pos.artikelnummer,
                bezeichnung=pos.bezeichnung,
                beschreibung=pos.beschreibung,
                menge=-pos.menge,  # Negativ!
                einheit=pos.einheit,
                einzelpreis_netto=pos.einzelpreis_netto,
                mwst_satz=pos.mwst_satz
            )
            neue_pos.berechne()
            db.session.add(neue_pos)
        
        db.session.commit()
        
        flash(f'Gutschrift {gs_nummer} erstellt!', 'success')
        return redirect(url_for('rechnungen.show', id=gutschrift.id))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Fehler bei Gutschrift: {e}")
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('rechnungen.show', id=id))


# ============================================================================
# PDF GENERIERUNG (mit StorageSettings & ZugPferd)
# ============================================================================

@rechnungen_bp.route('/<int:id>/pdf')
@login_required
@workflow_required
def pdf_generieren(id):
    """PDF für Rechnung generieren (mit ZugPferd-Integration)"""
    rechnung = BusinessDocument.query.get_or_404(id)
    
    try:
        # Neuen PDF-Service nutzen
        from src.services.document_pdf_service import get_pdf_service
        pdf_service = get_pdf_service()
        
        # PDF mit ZugPferd generieren
        pdf_bytes = pdf_service.generate_rechnung_pdf(rechnung, with_zugpferd=True)
        
        # Kundenname für Dateinamen
        kunde_name = rechnung.kunde.display_name if rechnung.kunde else None
        
        # PDF speichern (mit konfigurierten Pfaden)
        pdf_path = pdf_service.save_pdf(
            pdf_bytes,
            doc_type='rechnung',
            doc_nummer=rechnung.dokument_nummer,
            kunde_name=kunde_name,
            datum=rechnung.dokument_datum
        )
        
        # Pfad in DB speichern
        rechnung.pdf_pfad = pdf_path
        rechnung.pdf_erstellt_am = datetime.utcnow()
        db.session.commit()
        
        # Dateiname aus Pfad extrahieren
        pdf_filename = os.path.basename(pdf_path)
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=pdf_filename
        )
        
    except Exception as e:
        logger.error(f"Fehler bei PDF: {e}")
        flash(f'Fehler: {str(e)}', 'danger')
        return redirect(url_for('rechnungen.show', id=id))


@rechnungen_bp.route('/<int:id>/pdf/vorschau')
@login_required
@workflow_required
def pdf_vorschau(id):
    """PDF-Vorschau (ohne Speichern)"""
    rechnung = BusinessDocument.query.get_or_404(id)
    
    try:
        from src.services.document_pdf_service import get_pdf_service
        pdf_service = get_pdf_service()
        
        # PDF generieren (ohne ZugPferd für schnellere Vorschau)
        pdf_bytes = pdf_service.generate_rechnung_pdf(rechnung, with_zugpferd=False)
        
        return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf', as_attachment=False)
    except Exception as e:
        flash(f'Fehler: {str(e)}', 'danger')
        return redirect(url_for('rechnungen.show', id=id))


@rechnungen_bp.route('/<int:id>/pdf/zugpferd')
@login_required
@workflow_required
def pdf_zugpferd(id):
    """PDF mit ZugPferd-XML generieren (explizit)"""
    rechnung = BusinessDocument.query.get_or_404(id)
    
    try:
        from src.services.document_pdf_service import get_pdf_service
        pdf_service = get_pdf_service()
        
        # PDF MIT ZugPferd generieren
        pdf_bytes = pdf_service.generate_rechnung_pdf(rechnung, with_zugpferd=True)
        
        # Kundenname für Dateinamen
        kunde_name = rechnung.kunde.display_name if rechnung.kunde else None
        
        # PDF speichern
        pdf_path = pdf_service.save_pdf(
            pdf_bytes,
            doc_type='rechnung',
            doc_nummer=rechnung.dokument_nummer,
            kunde_name=kunde_name,
            datum=rechnung.dokument_datum
        )
        
        rechnung.pdf_pfad = pdf_path
        rechnung.pdf_erstellt_am = datetime.utcnow()
        rechnung.zugpferd_profil = 'BASIC'  # Profil speichern
        db.session.commit()
        
        pdf_filename = os.path.basename(pdf_path).replace('.pdf', '_ZugPferd.pdf')
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=pdf_filename
        )
        
    except Exception as e:
        logger.error(f"Fehler bei ZugPferd-PDF: {e}")
        flash(f'Fehler: {str(e)}', 'danger')
        return redirect(url_for('rechnungen.show', id=id))


def generiere_rechnung_pdf(rechnung):
    """Generiert PDF für eine Rechnung"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=20*mm, leftMargin=20*mm,
                           topMargin=20*mm, bottomMargin=20*mm)
    
    styles = getSampleStyleSheet()
    style_header = ParagraphStyle('Header', parent=styles['Heading1'], fontSize=18)
    style_normal = ParagraphStyle('Normal2', parent=styles['Normal'], fontSize=10, leading=14)
    style_small = ParagraphStyle('Small', parent=styles['Normal'], fontSize=8, leading=10)
    
    elements = []
    
    # Kopf
    elements.append(Paragraph("<b>StitchAdmin GmbH</b>", style_header))
    elements.append(Paragraph("Musterstraße 123 | 12345 Musterstadt | Tel: 0123-456789", style_small))
    elements.append(Spacer(1, 15*mm))
    
    # Empfänger
    adresse = rechnung.rechnungsadresse or {}
    elements.append(Paragraph(f"""
        {adresse.get('company', '') or adresse.get('name', '')}<br/>
        {adresse.get('contact', '')}<br/>
        {adresse.get('street', '')} {adresse.get('house_number', '')}<br/>
        {adresse.get('postal_code', '')} {adresse.get('city', '')}
    """.strip(), style_normal))
    elements.append(Spacer(1, 10*mm))
    
    # Titel
    titel = "RECHNUNG"
    if rechnung.dokument_typ == DokumentTyp.ANZAHLUNG.value:
        titel = "ANZAHLUNGSRECHNUNG"
    elif rechnung.dokument_typ == DokumentTyp.GUTSCHRIFT.value:
        titel = "GUTSCHRIFT"
    
    elements.append(Paragraph(f"<b>{titel}</b>", style_header))
    elements.append(Spacer(1, 5*mm))
    
    # Infos
    info_data = [
        ['Rechnungs-Nr.:', rechnung.dokument_nummer],
        ['Rechnungsdatum:', rechnung.dokument_datum.strftime('%d.%m.%Y')],
        ['Leistungsdatum:', rechnung.leistungsdatum.strftime('%d.%m.%Y') if rechnung.leistungsdatum else '-'],
        ['Fällig bis:', rechnung.faelligkeitsdatum.strftime('%d.%m.%Y') if rechnung.faelligkeitsdatum else '-'],
    ]
    
    info_table = Table(info_data, colWidths=[40*mm, 50*mm])
    info_table.setStyle(TableStyle([('FONTSIZE', (0, 0), (-1, -1), 9)]))
    elements.append(info_table)
    elements.append(Spacer(1, 10*mm))
    
    # Betreff
    if rechnung.betreff:
        elements.append(Paragraph(f"<b>Betreff: {rechnung.betreff}</b>", style_normal))
        elements.append(Spacer(1, 5*mm))
    
    # Einleitung
    if rechnung.einleitung:
        elements.append(Paragraph(rechnung.einleitung, style_normal))
        elements.append(Spacer(1, 5*mm))
    
    # Positionen
    pos_data = [['Pos.', 'Bezeichnung', 'Menge', 'Einheit', 'Einzelpreis', 'Gesamt']]
    
    for pos in rechnung.positionen:
        pos_data.append([
            str(pos.position),
            Paragraph(pos.bezeichnung, style_small),
            f"{pos.menge:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            pos.einheit,
            f"{pos.einzelpreis_netto:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.'),
            f"{pos.netto_gesamt:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')
        ])
    
    col_widths = [12*mm, 75*mm, 18*mm, 15*mm, 25*mm, 25*mm]
    pos_table = Table(pos_data, colWidths=col_widths, repeatRows=1)
    pos_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
    ]))
    elements.append(pos_table)
    elements.append(Spacer(1, 5*mm))
    
    # Summen
    def fmt(val):
        return f"{val:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    summen_data = [
        ['', 'Nettobetrag:', fmt(rechnung.summe_netto or 0)],
        ['', 'MwSt. 19%:', fmt(rechnung.summe_mwst or 0)],
        ['', 'Gesamtbetrag:', fmt(rechnung.summe_brutto or 0)],
    ]
    
    summen_table = Table(summen_data, colWidths=[100*mm, 40*mm, 30*mm])
    summen_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (1, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (1, -1), (-1, -1), 1, colors.black),
    ]))
    elements.append(summen_table)
    elements.append(Spacer(1, 10*mm))
    
    # Zahlungstext
    if rechnung.zahlungstext:
        elements.append(Paragraph(f"<b>Zahlungsbedingungen:</b> {rechnung.zahlungstext}", style_small))
        elements.append(Spacer(1, 5*mm))
    
    # Bankverbindung aus Firmeneinstellungen
    try:
        from src.models.company_settings import CompanySettings
        cs = CompanySettings.get_settings()
        bank_text = f"{cs.display_name or ''} | IBAN: {cs.iban or ''} | BIC: {cs.bic or ''}"
    except Exception:
        bank_text = "Bankverbindung: Bitte in Einstellungen konfigurieren"
    elements.append(Paragraph(f"<b>Bankverbindung:</b><br/>{bank_text}", style_small))
    
    doc.build(elements)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ============================================================================
# API ENDPOINTS
# ============================================================================

@rechnungen_bp.route('/api/offene')
@login_required
@workflow_required
def api_offene_rechnungen():
    """API: Offene Rechnungen"""
    rechnungen = BusinessDocument.query.filter(
        BusinessDocument.dokument_typ.in_([DokumentTyp.RECHNUNG.value, DokumentTyp.ANZAHLUNG.value]),
        BusinessDocument.status.in_([DokumentStatus.OFFEN.value, DokumentStatus.TEILBEZAHLT.value])
    ).order_by(BusinessDocument.faelligkeitsdatum).all()
    
    return jsonify([{
        'id': r.id,
        'nummer': r.dokument_nummer,
        'kunde': r.kunde.display_name if r.kunde else '-',
        'betrag': float(r.summe_brutto or 0),
        'offen': float(r.offener_betrag() if hasattr(r, 'offener_betrag') else r.summe_brutto),
        'faellig': r.faelligkeitsdatum.strftime('%d.%m.%Y') if r.faelligkeitsdatum else '-',
        'ueberfaellig': r.faelligkeitsdatum < date.today() if r.faelligkeitsdatum else False
    } for r in rechnungen])


@rechnungen_bp.route('/api/statistiken')
@login_required
@workflow_required
def api_statistiken():
    """API: Rechnungs-Statistiken"""
    from sqlalchemy import func
    
    # Umsatz pro Monat
    umsatz = db.session.query(
        func.strftime('%Y-%m', BusinessDocument.dokument_datum).label('monat'),
        func.sum(BusinessDocument.summe_brutto).label('summe')
    ).filter(
        BusinessDocument.dokument_typ == DokumentTyp.RECHNUNG.value,
        BusinessDocument.status != DokumentStatus.STORNIERT.value
    ).group_by(
        func.strftime('%Y-%m', BusinessDocument.dokument_datum)
    ).order_by(
        func.strftime('%Y-%m', BusinessDocument.dokument_datum).desc()
    ).limit(12).all()
    
    return jsonify({
        'monatlich': [{'monat': u.monat, 'summe': float(u.summe or 0)} for u in reversed(umsatz)]
    })
