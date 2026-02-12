# -*- coding: utf-8 -*-
"""
AUFTRAGS-WIZARD CONTROLLER
==========================
Step-by-Step Wizard für die vereinfachte Auftragserfassung:

Step 1: Kunde & Grunddaten
Step 2: Textilien auswählen
Step 3: Veredelung definieren
Step 4: Kalkulation & Preise
Step 5: Zusammenfassung & Abschluss

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, date, timedelta
from decimal import Decimal
import json
import os
import uuid

from src.models import db
from src.models.models import Customer, Article, Order, OrderItem, Machine

# Prüfen ob Document-Workflow Models verfügbar
try:
    from src.models.document_workflow import (
        Nummernkreis, Zahlungsbedingung, BusinessDocument, DocumentPosition,
        DokumentTyp, DokumentStatus, PositionsTyp
    )
    DOCUMENT_WORKFLOW_AVAILABLE = True
except ImportError:
    DOCUMENT_WORKFLOW_AVAILABLE = False

# Prüfen ob pyembroidery verfügbar
try:
    import pyembroidery
    PYEMBROIDERY_AVAILABLE = True
except ImportError:
    PYEMBROIDERY_AVAILABLE = False

import logging
logger = logging.getLogger(__name__)

# Blueprint
wizard_bp = Blueprint('wizard', __name__, url_prefix='/wizard')

# Session Key für Wizard-Daten
WIZARD_SESSION_KEY = 'order_wizard_data'


def login_required_json(f):
    """Decorator für JSON-Endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Nicht angemeldet'}), 401
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# WIZARD SESSION MANAGEMENT
# ============================================================================

def get_wizard_data():
    """Holt die aktuellen Wizard-Daten aus der Session"""
    default_data = {
        'current_step': 1,
        'kunde': {},
        'grunddaten': {
            'dokument_typ': 'angebot',  # 'angebot' oder 'auftrag'
            'auftragsart': 'stickerei',  # 'stickerei', 'druck', 'beides'
            'wunschtermin': None,
            'eilauftrag': False,
            'projektname': ''
        },
        'textilien': [],  # Liste von {artikel_id, menge, groessen: {S: 5, M: 10, ...}}
        'veredelungen': [],  # Liste von {position, design_id, typ, details}
        'kalkulation': {
            'summe_netto': 0,
            'summe_mwst': 0,
            'summe_brutto': 0,
            'rabatt_prozent': 0,
            'zahlungsbedingung_id': None
        },
        'notizen': {
            'intern': '',
            'kunde': ''
        }
    }
    return session.get(WIZARD_SESSION_KEY, default_data)


def save_wizard_data(data):
    """Speichert die Wizard-Daten in der Session"""
    session[WIZARD_SESSION_KEY] = data
    session.modified = True


def clear_wizard_data():
    """Löscht die Wizard-Daten aus der Session"""
    if WIZARD_SESSION_KEY in session:
        del session[WIZARD_SESSION_KEY]
        session.modified = True


def get_step_completion(data):
    """Prüft welche Steps abgeschlossen sind"""
    return {
        1: bool(data.get('kunde', {}).get('id')),
        2: len(data.get('textilien', [])) > 0,
        3: len(data.get('veredelungen', [])) > 0,
        4: True,  # Kalkulation ist immer verfügbar
        5: True   # Zusammenfassung
    }


# ============================================================================
# WIZARD HAUPTROUTEN
# ============================================================================

@wizard_bp.route('/')
@wizard_bp.route('/start')
@login_required
def start():
    """Startet einen neuen Wizard oder zeigt den aktuellen Stand"""
    # Optional: Parameter zum Zurücksetzen
    if request.args.get('reset'):
        clear_wizard_data()
    
    # Zu Step 1 weiterleiten
    return redirect(url_for('wizard.step1'))


@wizard_bp.route('/step/<int:step_num>')
@login_required
def step(step_num):
    """Dynamischer Step-Router"""
    if step_num == 1:
        return redirect(url_for('wizard.step1'))
    elif step_num == 2:
        return redirect(url_for('wizard.step2'))
    elif step_num == 3:
        return redirect(url_for('wizard.step3'))
    elif step_num == 4:
        return redirect(url_for('wizard.step4'))
    elif step_num == 5:
        return redirect(url_for('wizard.step5'))
    else:
        return redirect(url_for('wizard.step1'))


# ============================================================================
# STEP 1: KUNDE & GRUNDDATEN
# ============================================================================

@wizard_bp.route('/step1', methods=['GET', 'POST'])
@login_required
def step1():
    """Step 1: Kunde auswählen und Grunddaten eingeben"""
    data = get_wizard_data()
    
    if request.method == 'POST':
        # Daten verarbeiten
        kunde_id = request.form.get('kunde_id')
        
        if not kunde_id:
            flash('Bitte wählen Sie einen Kunden aus.', 'warning')
            return render_template('wizard/step1.html', data=data, step=1)
        
        # Kunde laden und validieren
        kunde = Customer.query.get(kunde_id)
        if not kunde:
            flash('Kunde nicht gefunden.', 'danger')
            return render_template('wizard/step1.html', data=data, step=1)
        
        # Kundendaten speichern
        data['kunde'] = {
            'id': kunde.id,
            'name': kunde.display_name,
            'email': kunde.email,
            'phone': kunde.phone,
            'type': kunde.customer_type
        }
        
        # Grunddaten speichern
        data['grunddaten'] = {
            'dokument_typ': request.form.get('dokument_typ', 'angebot'),
            'auftragsart': request.form.get('auftragsart', 'stickerei'),
            'wunschtermin': request.form.get('wunschtermin'),
            'eilauftrag': request.form.get('eilauftrag') == 'on',
            'projektname': request.form.get('projektname', '')
        }
        
        data['current_step'] = 2
        save_wizard_data(data)
        
        flash('Kunde und Grunddaten gespeichert.', 'success')
        return redirect(url_for('wizard.step2'))
    
    # GET: Formular anzeigen
    # Letzte Kunden für Schnellauswahl
    recent_customers = Customer.query.order_by(Customer.updated_at.desc()).limit(10).all()
    
    # Standard-Zahlungsbedingung
    default_zb = None
    if DOCUMENT_WORKFLOW_AVAILABLE:
        default_zb = Zahlungsbedingung.query.filter_by(standard=True, aktiv=True).first()
    
    return render_template('wizard/step1.html',
                         data=data,
                         step=1,
                         recent_customers=recent_customers,
                         default_zahlungsbedingung=default_zb,
                         completion=get_step_completion(data))


# ============================================================================
# STEP 2: TEXTILIEN AUSWÄHLEN
# ============================================================================

@wizard_bp.route('/step2', methods=['GET', 'POST'])
@login_required
def step2():
    """Step 2: Textilien/Artikel auswählen"""
    data = get_wizard_data()
    
    # Prüfen ob Step 1 abgeschlossen
    if not data.get('kunde', {}).get('id'):
        flash('Bitte wählen Sie zuerst einen Kunden aus.', 'warning')
        return redirect(url_for('wizard.step1'))
    
    if request.method == 'POST':
        # Textilien-Daten verarbeiten
        textilien = []
        
        # JSON-Daten vom Frontend
        textilien_json = request.form.get('textilien_json')
        if textilien_json:
            try:
                textilien = json.loads(textilien_json)
            except json.JSONDecodeError:
                flash('Fehler beim Verarbeiten der Textilien-Daten.', 'danger')
                return redirect(url_for('wizard.step2'))
        
        if not textilien:
            flash('Bitte wählen Sie mindestens einen Artikel aus.', 'warning')
            return render_template('wizard/step2.html', data=data, step=2)
        
        # Validierung und Anreicherung
        for item in textilien:
            artikel = Article.query.get(item.get('artikel_id'))
            if artikel:
                item['artikelnummer'] = artikel.article_number
                item['name'] = artikel.name
                item['einzelpreis'] = float(artikel.price or 0)
            
            # Gesamtmenge berechnen aus Größenstaffel
            groessen = item.get('groessen', {})
            item['gesamtmenge'] = sum(int(v) for v in groessen.values() if v)
        
        data['textilien'] = textilien
        data['current_step'] = 3
        save_wizard_data(data)
        
        flash(f'{len(textilien)} Artikel hinzugefügt.', 'success')
        return redirect(url_for('wizard.step3'))
    
    # GET: Artikel-Auswahl anzeigen
    # Kategorien für Filter
    categories = db.session.query(Article.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    
    # Marken für Filter
    brands = db.session.query(Article.brand).distinct().all()
    brands = [b[0] for b in brands if b[0]]
    
    return render_template('wizard/step2.html',
                         data=data,
                         step=2,
                         categories=categories,
                         brands=brands,
                         completion=get_step_completion(data))


# ============================================================================
# STEP 3: VEREDELUNG DEFINIEREN
# ============================================================================

@wizard_bp.route('/step3', methods=['GET', 'POST'])
@login_required
def step3():
    """Step 3: Veredelung (Stickerei/Druck) definieren"""
    data = get_wizard_data()
    
    # Prüfen ob Step 2 abgeschlossen
    if not data.get('textilien'):
        flash('Bitte wählen Sie zuerst Artikel aus.', 'warning')
        return redirect(url_for('wizard.step2'))
    
    if request.method == 'POST':
        # Veredelungs-Daten verarbeiten
        veredelungen = []
        
        # JSON-Daten vom Frontend
        veredelungen_json = request.form.get('veredelungen_json')
        if veredelungen_json:
            try:
                veredelungen = json.loads(veredelungen_json)
            except json.JSONDecodeError:
                flash('Fehler beim Verarbeiten der Veredelungs-Daten.', 'danger')
                return redirect(url_for('wizard.step3'))
        
        # Mindestens eine Veredelung sollte vorhanden sein
        # (kann aber auch leer bleiben für reine Textilbestellungen)
        
        data['veredelungen'] = veredelungen
        data['current_step'] = 4
        save_wizard_data(data)
        
        if veredelungen:
            flash(f'{len(veredelungen)} Veredelung(en) definiert.', 'success')
        else:
            flash('Keine Veredelung hinzugefügt (reine Textilbestellung).', 'info')
        
        return redirect(url_for('wizard.step4'))
    
    # GET: Veredelungs-Formular
    # Standard-Veredelungspositionen
    positionen = [
        {'key': 'brust_links', 'name': 'Brust links', 'max_breite': 100, 'max_hoehe': 100},
        {'key': 'brust_rechts', 'name': 'Brust rechts', 'max_breite': 100, 'max_hoehe': 100},
        {'key': 'brust_mitte', 'name': 'Brust Mitte', 'max_breite': 250, 'max_hoehe': 150},
        {'key': 'ruecken', 'name': 'Rücken', 'max_breite': 300, 'max_hoehe': 400},
        {'key': 'ruecken_oben', 'name': 'Rücken oben/Nacken', 'max_breite': 150, 'max_hoehe': 50},
        {'key': 'aermel_links', 'name': 'Ärmel links', 'max_breite': 100, 'max_hoehe': 100},
        {'key': 'aermel_rechts', 'name': 'Ärmel rechts', 'max_breite': 100, 'max_hoehe': 100},
        {'key': 'cap_vorne', 'name': 'Cap Vorne', 'max_breite': 100, 'max_hoehe': 60},
        {'key': 'cap_seite', 'name': 'Cap Seite', 'max_breite': 60, 'max_hoehe': 40},
        {'key': 'sonstige', 'name': 'Sonstige Position', 'max_breite': 300, 'max_hoehe': 300},
    ]
    
    auftragsart = data.get('grunddaten', {}).get('auftragsart', 'stickerei')
    
    return render_template('wizard/step3.html',
                         data=data,
                         step=3,
                         positionen=positionen,
                         auftragsart=auftragsart,
                         pyembroidery_available=PYEMBROIDERY_AVAILABLE,
                         completion=get_step_completion(data))


# ============================================================================
# STEP 4: KALKULATION & PREISE
# ============================================================================

@wizard_bp.route('/step4', methods=['GET', 'POST'])
@login_required
def step4():
    """Step 4: Automatische Kalkulation und Preisanpassung"""
    data = get_wizard_data()
    
    # Prüfen ob Step 2 abgeschlossen (Step 3 ist optional)
    if not data.get('textilien'):
        flash('Bitte wählen Sie zuerst Artikel aus.', 'warning')
        return redirect(url_for('wizard.step2'))
    
    if request.method == 'POST':
        # Kalkulations-Anpassungen verarbeiten
        kalkulation = {
            'rabatt_prozent': float(request.form.get('rabatt_prozent', 0)),
            'zahlungsbedingung_id': request.form.get('zahlungsbedingung_id'),
            'manuell_angepasst': request.form.get('manuell_angepasst') == 'on',
            'positionen': []  # Wird unten befüllt
        }
        
        # Manuelle Preisanpassungen
        pos_json = request.form.get('positionen_json')
        if pos_json:
            try:
                kalkulation['positionen'] = json.loads(pos_json)
            except json.JSONDecodeError:
                pass
        
        # Summen neu berechnen
        summen = berechne_summen(data, kalkulation)
        kalkulation.update(summen)
        
        data['kalkulation'] = kalkulation
        data['current_step'] = 5
        save_wizard_data(data)
        
        flash('Kalkulation gespeichert.', 'success')
        return redirect(url_for('wizard.step5'))
    
    # GET: Kalkulation berechnen und anzeigen
    kalkulation = berechne_kalkulation(data)
    
    # Zahlungsbedingungen laden
    zahlungsbedingungen = []
    if DOCUMENT_WORKFLOW_AVAILABLE:
        zahlungsbedingungen = Zahlungsbedingung.query.filter_by(aktiv=True)\
            .order_by(Zahlungsbedingung.sortierung).all()
    
    return render_template('wizard/step4.html',
                         data=data,
                         step=4,
                         kalkulation=kalkulation,
                         zahlungsbedingungen=zahlungsbedingungen,
                         completion=get_step_completion(data))


# ============================================================================
# STEP 5: ZUSAMMENFASSUNG & ABSCHLUSS
# ============================================================================

@wizard_bp.route('/step5', methods=['GET', 'POST'])
@login_required
def step5():
    """Step 5: Zusammenfassung prüfen und Auftrag/Angebot erstellen"""
    data = get_wizard_data()
    
    # Prüfen ob Daten vorhanden
    if not data.get('kunde', {}).get('id') or not data.get('textilien'):
        flash('Bitte vervollständigen Sie zunächst alle Schritte.', 'warning')
        return redirect(url_for('wizard.step1'))
    
    if request.method == 'POST':
        # Notizen speichern
        data['notizen'] = {
            'intern': request.form.get('interne_notiz', ''),
            'kunde': request.form.get('kunden_notiz', '')
        }
        save_wizard_data(data)
        
        # Aktion bestimmen
        action = request.form.get('action', 'create')
        
        if action == 'create_angebot':
            return erstelle_dokument(data, 'angebot')
        elif action == 'create_auftrag':
            return erstelle_dokument(data, 'auftrag')
        elif action == 'save_draft':
            flash('Entwurf gespeichert. Sie können später fortfahren.', 'info')
            return redirect(url_for('wizard.step5'))
        else:
            flash('Unbekannte Aktion.', 'warning')
    
    # GET: Zusammenfassung anzeigen
    # Kalkulation aktualisieren
    kalkulation = berechne_kalkulation(data)
    
    # Kunde laden für vollständige Anzeige
    kunde = Customer.query.get(data['kunde']['id']) if data.get('kunde', {}).get('id') else None
    
    return render_template('wizard/step5.html',
                         data=data,
                         step=5,
                         kalkulation=kalkulation,
                         kunde=kunde,
                         completion=get_step_completion(data),
                         workflow_available=DOCUMENT_WORKFLOW_AVAILABLE)


# ============================================================================
# API ENDPOINTS FÜR AJAX
# ============================================================================

@wizard_bp.route('/api/kunden/suche')
@login_required_json
def api_kunden_suche():
    """API: Kundensuche"""
    query = request.args.get('q', '').strip()
    
    if len(query) < 2:
        return jsonify([])
    
    # Suche in verschiedenen Feldern
    kunden = Customer.query.filter(
        db.or_(
            Customer.company_name.ilike(f'%{query}%'),
            Customer.first_name.ilike(f'%{query}%'),
            Customer.last_name.ilike(f'%{query}%'),
            Customer.email.ilike(f'%{query}%'),
            Customer.customer_number.ilike(f'%{query}%')
        )
    ).limit(20).all()
    
    return jsonify([{
        'id': k.id,
        'name': k.display_name,
        'email': k.email,
        'type': k.customer_type,
        'customer_number': k.customer_number
    } for k in kunden])


@wizard_bp.route('/api/artikel/suche')
@login_required_json
def api_artikel_suche():
    """API: Artikelsuche"""
    query = request.args.get('q', '').strip()
    category = request.args.get('category')
    brand = request.args.get('brand')
    
    articles_query = Article.query.filter_by(active=True)
    
    if query:
        articles_query = articles_query.filter(
            db.or_(
                Article.name.ilike(f'%{query}%'),
                Article.article_number.ilike(f'%{query}%'),
                Article.description.ilike(f'%{query}%')
            )
        )
    
    if category:
        articles_query = articles_query.filter_by(category=category)
    
    if brand:
        articles_query = articles_query.filter_by(brand=brand)
    
    articles = articles_query.order_by(Article.name).limit(50).all()
    
    return jsonify([{
        'id': a.id,
        'article_number': a.article_number,
        'name': a.name,
        'category': a.category,
        'brand': a.brand,
        'price': float(a.price or 0),
        'color': a.color,
        'has_variants': a.has_variants
    } for a in articles])


@wizard_bp.route('/api/artikel/<artikel_id>/varianten')
@login_required_json
def api_artikel_varianten(artikel_id):
    """API: Artikel-Varianten (Farben/Größen)"""
    artikel = Article.query.get_or_404(artikel_id)
    
    # Varianten laden
    from src.models.article_variant import ArticleVariant
    varianten = ArticleVariant.query.filter_by(article_id=artikel_id).all()
    
    # Gruppieren nach Farbe
    farben = {}
    groessen = set()
    
    for v in varianten:
        if v.color not in farben:
            farben[v.color] = {
                'hex_color': v.hex_color,
                'groessen': {}
            }
        if v.size:
            farben[v.color]['groessen'][v.size] = {
                'stock': v.stock,
                'price': float(v.price) if v.price else float(artikel.price or 0)
            }
            groessen.add(v.size)
    
    # Standard-Größenreihenfolge
    groessen_order = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL', '4XL', '5XL']
    sorted_groessen = sorted(list(groessen), key=lambda x: groessen_order.index(x) if x in groessen_order else 99)
    
    return jsonify({
        'artikel_id': artikel_id,
        'farben': farben,
        'groessen': sorted_groessen,
        'default_price': float(artikel.price or 0)
    })


@wizard_bp.route('/api/design/analyse', methods=['POST'])
@login_required_json
def api_design_analyse():
    """API: DST/Embroidery-Datei analysieren"""
    if not PYEMBROIDERY_AVAILABLE:
        return jsonify({'error': 'pyembroidery nicht verfügbar'}), 400
    
    if 'file' not in request.files:
        return jsonify({'error': 'Keine Datei hochgeladen'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Keine Datei ausgewählt'}), 400
    
    # Temporär speichern und analysieren
    import tempfile
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            file.save(tmp.name)
            
            # Mit pyembroidery laden
            pattern = pyembroidery.read(tmp.name)
            
            if pattern is None:
                return jsonify({'error': 'Datei konnte nicht gelesen werden'}), 400
            
            # Stiche zählen
            stitch_count = 0
            for stitch in pattern.stitches:
                if stitch[2] == pyembroidery.STITCH:
                    stitch_count += 1
            
            # Dimensionen berechnen (in mm)
            bounds = pattern.bounds()
            width_mm = (bounds[2] - bounds[0]) / 10  # 1/10mm zu mm
            height_mm = (bounds[3] - bounds[1]) / 10
            
            # Farben extrahieren
            colors = []
            for thread in pattern.threadlist:
                colors.append({
                    'color': thread.hex_color() if hasattr(thread, 'hex_color') else '#000000',
                    'name': thread.description if hasattr(thread, 'description') else '',
                    'catalog_number': thread.catalog_number if hasattr(thread, 'catalog_number') else ''
                })
            
            # Temporäre Datei löschen
            os.unlink(tmp.name)
            
            return jsonify({
                'filename': file.filename,
                'stitch_count': stitch_count,
                'width_mm': round(width_mm, 1),
                'height_mm': round(height_mm, 1),
                'color_count': len(colors),
                'colors': colors
            })
            
    except Exception as e:
        logger.error(f"Fehler bei Design-Analyse: {e}")
        return jsonify({'error': str(e)}), 500


@wizard_bp.route('/api/kalkulation/berechnen', methods=['POST'])
@login_required_json
def api_kalkulation_berechnen():
    """API: Kalkulation berechnen/aktualisieren"""
    data = get_wizard_data()
    
    # Optionale Überschreibungen aus Request
    updates = request.get_json() or {}
    if updates.get('rabatt_prozent') is not None:
        data.setdefault('kalkulation', {})['rabatt_prozent'] = float(updates['rabatt_prozent'])
    
    kalkulation = berechne_kalkulation(data)
    
    return jsonify(kalkulation)


# ============================================================================
# HILFSFUNKTIONEN
# ============================================================================

def berechne_kalkulation(data):
    """
    Berechnet die komplette Kalkulation basierend auf den Wizard-Daten
    
    Returns:
        dict mit Positionen, Summen, etc.
    """
    positionen = []
    summe_netto = Decimal('0.00')
    position_nr = 1
    
    # 1. TEXTILIEN
    for textil in data.get('textilien', []):
        artikel = Article.query.get(textil.get('artikel_id'))
        if not artikel:
            continue
        
        # Gesamtmenge aus Größenstaffel
        groessen = textil.get('groessen', {})
        menge = sum(int(v) for v in groessen.values() if v)
        
        if menge <= 0:
            continue
        
        einzelpreis = Decimal(str(artikel.price or 0))
        gesamt = einzelpreis * menge
        
        pos = {
            'nr': position_nr,
            'typ': 'textil',
            'artikel_id': artikel.id,
            'artikelnummer': artikel.article_number,
            'bezeichnung': artikel.name,
            'groessen': groessen,
            'menge': menge,
            'einheit': 'Stk.',
            'einzelpreis': float(einzelpreis),
            'gesamt_netto': float(gesamt)
        }
        positionen.append(pos)
        summe_netto += gesamt
        position_nr += 1
    
    # 2. VEREDELUNGEN
    for veredlung in data.get('veredelungen', []):
        # Stickerei-Preis berechnen
        if veredlung.get('typ') == 'stickerei':
            stiche = veredlung.get('stitch_count', 0)
            preis_pro_1000 = Decimal('1.50')  # Aus Einstellungen laden
            einzelpreis = (Decimal(stiche) / 1000 * preis_pro_1000).quantize(Decimal('0.01'))
            
            # Minimum
            min_preis = Decimal('2.00')
            if einzelpreis < min_preis:
                einzelpreis = min_preis
        else:
            # Druck-Preis
            breite = veredlung.get('breite_cm', 0)
            hoehe = veredlung.get('hoehe_cm', 0)
            flaeche = Decimal(str(breite)) * Decimal(str(hoehe))
            preis_pro_cm2 = Decimal('0.05')
            einzelpreis = (flaeche * preis_pro_cm2).quantize(Decimal('0.01'))
            
            min_preis = Decimal('1.50')
            if einzelpreis < min_preis:
                einzelpreis = min_preis
        
        # Menge = Anzahl Textilien (vereinfacht)
        menge = sum(
            sum(int(v) for v in t.get('groessen', {}).values() if v)
            for t in data.get('textilien', [])
        )
        
        gesamt = einzelpreis * menge
        
        pos = {
            'nr': position_nr,
            'typ': 'veredelung_' + veredlung.get('typ', 'stickerei'),
            'bezeichnung': f"Stickerei {veredlung.get('position', '')}" if veredlung.get('typ') == 'stickerei' 
                          else f"Druck {veredlung.get('position', '')}",
            'beschreibung': f"{veredlung.get('stitch_count', 0):,} Stiche".replace(',', '.') if veredlung.get('typ') == 'stickerei'
                           else f"{veredlung.get('breite_cm', 0)}x{veredlung.get('hoehe_cm', 0)} cm",
            'menge': menge,
            'einheit': 'Stk.',
            'einzelpreis': float(einzelpreis),
            'gesamt_netto': float(gesamt)
        }
        positionen.append(pos)
        summe_netto += gesamt
        position_nr += 1
    
    # 3. EINRICHTUNGSPAUSCHALEN
    if data.get('veredelungen'):
        setup_preis = Decimal('25.00')  # Pro Design-Position
        setup_anzahl = len(data['veredelungen'])
        
        pos = {
            'nr': position_nr,
            'typ': 'einrichtung',
            'bezeichnung': 'Einrichtungspauschale',
            'beschreibung': f'{setup_anzahl} Position(en)',
            'menge': setup_anzahl,
            'einheit': 'pauschal',
            'einzelpreis': float(setup_preis),
            'gesamt_netto': float(setup_preis * setup_anzahl)
        }
        positionen.append(pos)
        summe_netto += setup_preis * setup_anzahl
        position_nr += 1
    
    # 4. RABATT
    rabatt_prozent = Decimal(str(data.get('kalkulation', {}).get('rabatt_prozent', 0)))
    rabatt_betrag = (summe_netto * rabatt_prozent / 100).quantize(Decimal('0.01'))
    
    # MENGENRABATT (automatisch)
    gesamtmenge = sum(p.get('menge', 0) for p in positionen if p.get('typ') == 'textil')
    mengen_rabatt = Decimal('0')
    
    if gesamtmenge >= 500:
        mengen_rabatt = Decimal('20')
    elif gesamtmenge >= 250:
        mengen_rabatt = Decimal('15')
    elif gesamtmenge >= 100:
        mengen_rabatt = Decimal('10')
    elif gesamtmenge >= 50:
        mengen_rabatt = Decimal('5')
    
    # Nur höheren Rabatt anwenden
    effektiver_rabatt = max(rabatt_prozent, mengen_rabatt)
    rabatt_betrag = (summe_netto * effektiver_rabatt / 100).quantize(Decimal('0.01'))
    
    netto_nach_rabatt = summe_netto - rabatt_betrag
    
    # 5. MWST
    mwst_satz = Decimal('19.00')
    mwst_betrag = (netto_nach_rabatt * mwst_satz / 100).quantize(Decimal('0.01'))
    brutto = netto_nach_rabatt + mwst_betrag
    
    return {
        'positionen': positionen,
        'summe_netto': float(summe_netto),
        'rabatt_prozent': float(effektiver_rabatt),
        'rabatt_betrag': float(rabatt_betrag),
        'mengen_rabatt_hinweis': f'Mengenrabatt {mengen_rabatt}%' if mengen_rabatt > 0 else None,
        'netto_nach_rabatt': float(netto_nach_rabatt),
        'mwst_satz': float(mwst_satz),
        'mwst_betrag': float(mwst_betrag),
        'summe_brutto': float(brutto),
        'gesamtmenge': gesamtmenge
    }


def berechne_summen(data, kalkulation_updates):
    """Berechnet nur die Summen mit optionalen Überschreibungen"""
    # Basis-Kalkulation
    kalkulation = berechne_kalkulation(data)
    
    # Überschreibungen anwenden
    rabatt = Decimal(str(kalkulation_updates.get('rabatt_prozent', kalkulation['rabatt_prozent'])))
    summe_netto = Decimal(str(kalkulation['summe_netto']))
    
    rabatt_betrag = (summe_netto * rabatt / 100).quantize(Decimal('0.01'))
    netto_nach_rabatt = summe_netto - rabatt_betrag
    
    mwst_satz = Decimal('19.00')
    mwst_betrag = (netto_nach_rabatt * mwst_satz / 100).quantize(Decimal('0.01'))
    brutto = netto_nach_rabatt + mwst_betrag
    
    return {
        'summe_netto': float(summe_netto),
        'rabatt_betrag': float(rabatt_betrag),
        'netto_nach_rabatt': float(netto_nach_rabatt),
        'mwst_betrag': float(mwst_betrag),
        'summe_brutto': float(brutto)
    }


def erstelle_dokument(data, typ='angebot'):
    """
    Erstellt das finale Dokument (Angebot oder Auftrag)
    
    Args:
        data: Wizard-Daten
        typ: 'angebot' oder 'auftrag'
        
    Returns:
        Redirect zum erstellten Dokument
    """
    try:
        # Kalkulation berechnen
        kalkulation = berechne_kalkulation(data)
        
        if DOCUMENT_WORKFLOW_AVAILABLE:
            # === NEUES SYSTEM: BusinessDocument ===
            
            # Dokumentnummer generieren
            if typ == 'angebot':
                doc_typ = DokumentTyp.ANGEBOT.value
                belegart = 'angebot'
            else:
                doc_typ = DokumentTyp.AUFTRAGSBESTAETIGUNG.value
                belegart = 'auftragsbestaetigung'
            
            try:
                dok_nummer = Nummernkreis.hole_naechste_nummer(belegart)
            except ValueError as e:
                flash(f'Fehler: {e}', 'danger')
                return redirect(url_for('wizard.step5'))
            
            # Kunde laden
            kunde = Customer.query.get(data['kunde']['id'])
            
            # Zahlungsbedingung
            zb_id = data.get('kalkulation', {}).get('zahlungsbedingung_id')
            zahlungsbedingung = Zahlungsbedingung.query.get(zb_id) if zb_id else None
            if not zahlungsbedingung:
                zahlungsbedingung = Zahlungsbedingung.query.filter_by(standard=True, aktiv=True).first()
            
            # Dokument erstellen
            dokument = BusinessDocument(
                dokument_nummer=dok_nummer,
                dokument_typ=doc_typ,
                kunde_id=kunde.id,
                
                # Adressen-Snapshot
                rechnungsadresse={
                    'name': kunde.display_name,
                    'street': kunde.street,
                    'house_number': kunde.house_number,
                    'postal_code': kunde.postal_code,
                    'city': kunde.city,
                    'country': kunde.country
                },
                
                # Datum
                dokument_datum=date.today(),
                gueltig_bis=date.today() + timedelta(days=30) if typ == 'angebot' else None,
                
                # Beträge
                summe_netto=Decimal(str(kalkulation['netto_nach_rabatt'])),
                summe_mwst=Decimal(str(kalkulation['mwst_betrag'])),
                summe_brutto=Decimal(str(kalkulation['summe_brutto'])),
                rabatt_prozent=Decimal(str(kalkulation['rabatt_prozent'])),
                rabatt_betrag=Decimal(str(kalkulation['rabatt_betrag'])),
                
                # Status
                status=DokumentStatus.ENTWURF.value,
                
                # Texte
                betreff=data.get('grunddaten', {}).get('projektname', f'{doc_typ.replace("_", " ").title()}'),
                interne_notiz=data.get('notizen', {}).get('intern', ''),
                
                # Zahlungsbedingungen
                zahlungsbedingung_id=zahlungsbedingung.id if zahlungsbedingung else None,
                zahlungsziel_tage=zahlungsbedingung.zahlungsziel_tage if zahlungsbedingung else 14,
                
                # Tracking
                erstellt_von=current_user.username
            )
            
            db.session.add(dokument)
            db.session.flush()  # ID generieren
            
            # Positionen hinzufügen
            for idx, pos in enumerate(kalkulation['positionen'], start=1):
                position = DocumentPosition(
                    dokument_id=dokument.id,
                    position=idx,
                    typ=pos.get('typ', PositionsTyp.ARTIKEL.value),
                    artikel_id=pos.get('artikel_id'),
                    artikelnummer=pos.get('artikelnummer', ''),
                    bezeichnung=pos.get('bezeichnung', ''),
                    beschreibung=pos.get('beschreibung', ''),
                    menge=pos.get('menge', 1),
                    einheit=pos.get('einheit', 'Stk.'),
                    einzelpreis_netto=Decimal(str(pos.get('einzelpreis', 0))),
                    mwst_satz=Decimal('19.00'),
                    netto_gesamt=Decimal(str(pos.get('gesamt_netto', 0)))
                )
                position.berechne()
                db.session.add(position)
            
            db.session.commit()
            
            # Session leeren
            clear_wizard_data()
            
            flash(f'{typ.title()} {dok_nummer} erfolgreich erstellt!', 'success')
            
            # Zur Dokumentansicht weiterleiten
            # TODO: Route für Dokumentansicht implementieren
            return redirect(url_for('wizard.start'))
            
        else:
            # === LEGACY SYSTEM: Order Model ===
            
            # Auftragsnummer generieren
            from src.controllers.order_controller_db import generate_order_id
            order_id = generate_order_id()
            
            order = Order(
                id=order_id,
                order_number=order_id,
                customer_id=data['kunde']['id'],
                order_type=data['grunddaten'].get('auftragsart', 'embroidery'),
                status='new' if typ == 'auftrag' else 'draft',
                is_offer=(typ == 'angebot'),
                
                description=data.get('grunddaten', {}).get('projektname', ''),
                internal_notes=data.get('notizen', {}).get('intern', ''),
                customer_notes=data.get('notizen', {}).get('kunde', ''),
                
                total_price=kalkulation['summe_brutto'],
                discount_percent=kalkulation['rabatt_prozent'],
                
                rush_order=data.get('grunddaten', {}).get('eilauftrag', False),
                
                created_by=current_user.username,
                created_at=datetime.utcnow()
            )
            
            # Wunschtermin
            wunschtermin = data.get('grunddaten', {}).get('wunschtermin')
            if wunschtermin:
                try:
                    order.due_date = datetime.strptime(wunschtermin, '%Y-%m-%d')
                except ValueError:
                    pass
            
            # Angebots-Felder
            if typ == 'angebot':
                order.offer_valid_until = date.today() + timedelta(days=30)
            
            db.session.add(order)
            
            # Order Items hinzufügen
            for pos in kalkulation['positionen']:
                if pos.get('typ') == 'textil':
                    item = OrderItem(
                        order_id=order.id,
                        article_id=pos.get('artikel_id'),
                        quantity=pos.get('menge', 1),
                        unit_price=pos.get('einzelpreis', 0),
                        position_details=json.dumps(pos.get('groessen', {}))
                    )
                    db.session.add(item)
            
            db.session.commit()
            
            # Session leeren
            clear_wizard_data()
            
            flash(f'{typ.title()} {order_id} erfolgreich erstellt!', 'success')
            return redirect(url_for('orders.show', order_id=order.id))
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Fehler beim Erstellen des Dokuments: {e}")
        flash(f'Fehler beim Erstellen: {str(e)}', 'danger')
        return redirect(url_for('wizard.step5'))


# ============================================================================
# BLUEPRINT REGISTRIERUNG
# ============================================================================

def init_app(app):
    """Registriert den Blueprint"""
    app.register_blueprint(wizard_bp)
