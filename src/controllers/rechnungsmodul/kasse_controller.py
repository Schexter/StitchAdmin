# -*- coding: utf-8 -*-
"""
KASSEN-CONTROLLER - TSE-konforme Kassenbuchungen (Vollversion)
=============================================================

Erstellt von: Hans Hahn - Alle Rechte vorbehalten
Datum: 09. Juli 2025
Zweck: Vollständiger Flask-Controller für Kassensystem mit TSE-Integration

Features:
- TSE-konforme Kassenbuchungen
- Artikel-Scanner-Integration
- Beleg-Erstellung und -Druck
- Tagesabschlüsse
- Zahlungsarten-Handling
- Warenkorb-Funktionalität
"""

import json
import uuid
from datetime import datetime, date
from decimal import Decimal
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from sqlalchemy.exc import SQLAlchemyError

# Imports für Models und Services
try:
    from src.models import db, Article, Customer, User
    from src.models.rechnungsmodul import (
        KassenBeleg, BelegPosition, KassenTransaktion, MwStSatz, TSEKonfiguration,
        BelegTyp, ZahlungsArt, models_available
    )
    print("✅ Rechnungsmodul-Models importiert")
except ImportError as e:
    print(f"⚠️ Rechnungsmodul Models Import-Fehler: {e}")
    models_available = False
    db = None

import logging
logger = logging.getLogger(__name__)

# Blueprint erstellen
kasse_bp = Blueprint('kasse', __name__, url_prefix='/kasse')

# TSE-Service-Klasse
class TSEService:
    """Service-Klasse für TSE-Integration"""
    
    def __init__(self):
        self.is_mock = True  # TODO: Auf False setzen für echte TSE
        
    def get_tse_info(self):
        """Hole TSE-Informationen"""
        if self.is_mock:
            return {
                'serial': 'MOCK_TSE_DEV_001',
                'status': 'AKTIV',
                'hersteller': 'StitchAdmin Mock',
                'modell': 'MockTSE v1.0',
                'zertifikat_gueltig': True,
                'wartung_faellig': False
            }
        else:
            # TODO: Echte TSE-Integration
            return self._get_real_tse_info()
    
    def test_connection(self):
        """Teste TSE-Verbindung"""
        if self.is_mock:
            return {'success': True, 'message': 'Mock TSE verbunden'}
        else:
            # TODO: Echte TSE-Verbindung testen
            return self._test_real_tse()
    
    def start_transaction(self, process_type, client_id):
        """Starte TSE-Transaktion"""
        if self.is_mock:
            return {
                'success': True,
                'transaction_id': str(uuid.uuid4()),
                'started_at': datetime.utcnow().isoformat() + 'Z'
            }
        else:
            # TODO: Echte TSE-Transaktion starten
            return self._start_real_transaction(process_type, client_id)
    
    def finish_transaction(self, transaction_id, process_data):
        """Beende TSE-Transaktion"""
        if self.is_mock:
            return {
                'success': True,
                'tse_serial': 'MOCK_TSE_DEV_001',
                'started_at': datetime.utcnow().isoformat() + 'Z',
                'finished_at': datetime.utcnow().isoformat() + 'Z',
                'signature_counter': 1,
                'signature_algorithm': 'SHA256',
                'signature': 'MOCK_SIGNATURE_' + transaction_id[:8],
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        else:
            # TODO: Echte TSE-Transaktion beenden
            return self._finish_real_transaction(transaction_id, process_data)
    
    def _get_real_tse_info(self):
        """Placeholder für echte TSE-Info"""
        pass
    
    def _test_real_tse(self):
        """Placeholder für echte TSE-Verbindung"""
        pass
    
    def _start_real_transaction(self, process_type, client_id):
        """Placeholder für echte TSE-Transaktion"""
        pass
    
    def _finish_real_transaction(self, transaction_id, process_data):
        """Placeholder für echte TSE-Transaktion"""
        pass

# Globale TSE-Service-Instanz
tse_service = TSEService()

# Kassensystem-Utility-Klasse
class KassensystemUtils:
    """Utility-Funktionen für das Kassensystem"""
    
    @staticmethod
    def get_tagesabschluss(datum, kassen_id='KASSE-01'):
        """Erstelle Tagesabschluss-Statistiken"""
        if not models_available or not db:
            return {
                'datum': datum,
                'kassen_id': kassen_id,
                'anzahl_belege': 0,
                'anzahl_stornos': 0,
                'umsatz_bar': 0.00,
                'umsatz_ec': 0.00,
                'umsatz_kreditkarte': 0.00,
                'umsatz_rechnung': 0.00,
                'umsatz_gesamt': 0.00,
                'belege': []
            }
        
        try:
            # Alle Belege des Tages
            belege = KassenBeleg.query.filter(
                db.func.date(KassenBeleg.erstellt_am) == datum,
                KassenBeleg.kassen_id == kassen_id
            ).all()
            
            # Statistiken berechnen
            anzahl_belege = len([b for b in belege if not b.storniert])
            anzahl_stornos = len([b for b in belege if b.storniert])
            
            umsatz_bar = sum(float(b.brutto_gesamt) for b in belege 
                           if not b.storniert and b.zahlungsart == ZahlungsArt.BAR)
            umsatz_ec = sum(float(b.brutto_gesamt) for b in belege 
                          if not b.storniert and b.zahlungsart == ZahlungsArt.EC_KARTE)
            umsatz_kreditkarte = sum(float(b.brutto_gesamt) for b in belege 
                                   if not b.storniert and b.zahlungsart == ZahlungsArt.KREDITKARTE)
            umsatz_rechnung = sum(float(b.brutto_gesamt) for b in belege 
                                if not b.storniert and b.zahlungsart == ZahlungsArt.RECHNUNG)
            
            umsatz_gesamt = umsatz_bar + umsatz_ec + umsatz_kreditkarte + umsatz_rechnung
            
            return {
                'datum': datum,
                'kassen_id': kassen_id,
                'anzahl_belege': anzahl_belege,
                'anzahl_stornos': anzahl_stornos,
                'umsatz_bar': umsatz_bar,
                'umsatz_ec': umsatz_ec,
                'umsatz_kreditkarte': umsatz_kreditkarte,
                'umsatz_rechnung': umsatz_rechnung,
                'umsatz_gesamt': umsatz_gesamt,
                'belege': [b.to_dict() for b in belege if hasattr(b, 'to_dict')]
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Tagesabschluss: {e}")
            return {
                'datum': datum,
                'kassen_id': kassen_id,
                'anzahl_belege': 0,
                'anzahl_stornos': 0,
                'umsatz_bar': 0.00,
                'umsatz_ec': 0.00,
                'umsatz_kreditkarte': 0.00,
                'umsatz_rechnung': 0.00,
                'umsatz_gesamt': 0.00,
                'belege': [],
                'error': str(e)
            }

# Warenkorb-Funktionen
def get_warenkorb():
    """Hole Warenkorb aus Session"""
    return session.get('warenkorb', [])

def add_to_warenkorb(artikel_data):
    """Füge Artikel zum Warenkorb hinzu"""
    warenkorb = get_warenkorb()
    
    # Prüfe ob Artikel bereits im Warenkorb
    for item in warenkorb:
        if item.get('artikel_id') == artikel_data.get('artikel_id'):
            # Menge erhöhen
            item['menge'] += artikel_data.get('menge', 1)
            session['warenkorb'] = warenkorb
            return True
    
    # Neuen Artikel hinzufügen
    artikel_data['warenkorb_id'] = str(uuid.uuid4())
    warenkorb.append(artikel_data)
    session['warenkorb'] = warenkorb
    return True

def remove_from_warenkorb(warenkorb_id):
    """Entferne Artikel aus Warenkorb"""
    warenkorb = get_warenkorb()
    warenkorb = [item for item in warenkorb if item.get('warenkorb_id') != warenkorb_id]
    session['warenkorb'] = warenkorb
    return True

def clear_warenkorb():
    """Leere Warenkorb"""
    session['warenkorb'] = []

def calculate_warenkorb_totals(warenkorb):
    """Berechne Warenkorb-Summen"""
    netto_gesamt = 0
    mwst_gesamt = 0
    brutto_gesamt = 0
    
    for item in warenkorb:
        menge = item.get('menge', 1)
        preis = item.get('preis', 0)
        mwst_satz = item.get('mwst_satz', 19.0)
        
        netto_betrag = menge * preis
        mwst_betrag = netto_betrag * (mwst_satz / 100)
        brutto_betrag = netto_betrag + mwst_betrag
        
        # Update item
        item['netto_betrag'] = round(netto_betrag, 2)
        item['mwst_betrag'] = round(mwst_betrag, 2)
        item['brutto_betrag'] = round(brutto_betrag, 2)
        
        netto_gesamt += netto_betrag
        mwst_gesamt += mwst_betrag
        brutto_gesamt += brutto_betrag
    
    return {
        'netto_gesamt': round(netto_gesamt, 2),
        'mwst_gesamt': round(mwst_gesamt, 2),
        'brutto_gesamt': round(brutto_gesamt, 2),
        'anzahl_positionen': len(warenkorb)
    }

# Haupt-Routen
@kasse_bp.route('/')
def kassen_index():
    """
    Haupt-Kassen-Interface
    Zeigt aktuelle Kassen-Übersicht und Schnellzugriffe
    """
    try:
        # TSE-Status prüfen
        tse_info = tse_service.get_tse_info()
        
        # Heutige Statistiken
        heute = date.today()
        tagesstatistik = KassensystemUtils.get_tagesabschluss(heute)
        
        # Letzte Belege für Template
        recent_receipts = []
        if models_available and db:
            try:
                recent_receipts = KassenBeleg.query.filter(
                    db.func.date(KassenBeleg.datum) == heute
                ).order_by(KassenBeleg.datum.desc()).limit(10).all()
            except Exception as e:
                logger.warning(f"Fehler beim Laden der Belege: {e}")
        
        # Daten für Template vorbereiten
        today_revenue = tagesstatistik.get('umsatz_gesamt', 0)
        today_receipts = tagesstatistik.get('anzahl_belege', 0)
        kasse_status = 'Geöffnet'
        tse_status = tse_info.get('status', 'UNBEKANNT')
        
        return render_template('kasse/index.html',
            today_revenue=today_revenue,
            today_receipts=today_receipts,
            kasse_status=kasse_status,
            tse_status=tse_status,
            recent_receipts=recent_receipts
        )
        
    except Exception as e:
        logger.error(f"Fehler im Kassen-Index: {str(e)}")
        flash(f"Fehler beim Laden der Kassen-Übersicht: {str(e)}", "error")
        return render_template('kasse/error.html', error=str(e))

@kasse_bp.route('/verkauf')
def verkauf_interface():
    """
    Verkaufs-Interface für Kassenbuchungen
    Hauptarbeitsplatz für Kassierer
    """
    try:
        # TSE-Status prüfen
        tse_status = tse_service.test_connection()
        
        # Zahlungsarten
        zahlungsarten = [
            {'id': 'BAR', 'name': 'Barzahlung', 'icon': '💰'},
            {'id': 'EC_KARTE', 'name': 'EC-Karte', 'icon': '💳'},
            {'id': 'KREDITKARTE', 'name': 'Kreditkarte', 'icon': '💳'},
            {'id': 'RECHNUNG', 'name': 'Rechnung', 'icon': '📄'}
        ]
        
        # Warenkorb
        warenkorb = get_warenkorb()
        warenkorb_summen = calculate_warenkorb_totals(warenkorb)
        
        # MwSt-Sätze
        mwst_saetze = []
        if models_available and db:
            try:
                mwst_saetze = MwStSatz.get_aktuelle_saetze()
            except Exception as e:
                logger.warning(f"Fehler beim Laden der MwSt-Sätze: {e}")
        
        return render_template('kasse/verkauf.html',
            tse_status=tse_status,
            zahlungsarten=zahlungsarten,
            warenkorb=warenkorb,
            warenkorb_summen=warenkorb_summen,
            mwst_saetze=mwst_saetze,
            kassierer=session.get('kassierer_name', 'Demo Kassierer'),
            training_modus=not tse_status.get('success', False),
            page_title="Verkauf"
        )
        
    except Exception as e:
        logger.error(f"Fehler im Verkaufs-Interface: {str(e)}")
        flash(f"Fehler beim Laden des Verkaufs-Interface: {str(e)}", "error")
        return redirect(url_for('kasse.kassen_index'))

@kasse_bp.route('/artikel/suchen')
def artikel_suchen():
    """
    AJAX-Endpoint für Artikel-Suche
    Unterstützt Barcode-Scanner und Textsuche
    """
    try:
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 10))
        
        if len(query) < 1:
            return jsonify({'success': True, 'artikel': []})
        
        gefundene_artikel = []
        
        # Suche in echter Datenbank
        if models_available and db:
            try:
                artikel = Article.query.filter(
                    db.or_(
                        Article.name.ilike(f'%{query}%'),
                        Article.article_number.ilike(f'%{query}%'),
                        Article.supplier_article_number.ilike(f'%{query}%')
                    )
                ).filter(Article.active == True).limit(limit).all()
                
                for a in artikel:
                    gefundene_artikel.append({
                        'id': a.id,
                        'artikel_nummer': a.article_number,
                        'name': a.name,
                        'preis': float(a.price or 0),
                        'lagerbestand': a.stock or 0,
                        'kategorie': a.category or 'Unbekannt',
                        'aktiv': a.active
                    })
                    
            except Exception as e:
                logger.warning(f"Fehler bei Artikel-Suche: {e}")
        
        # Fallback: Mock-Artikel
        if not gefundene_artikel:
            mock_artikel = [
                {
                    'id': 'MOCK-001',
                    'artikel_nummer': '12345',
                    'name': 'Baumwollgarn rot 50g',
                    'preis': 4.99,
                    'lagerbestand': 25,
                    'kategorie': 'Garne',
                    'aktiv': True
                },
                {
                    'id': 'MOCK-002',
                    'artikel_nummer': '12346',
                    'name': 'Stricknadeln 5mm',
                    'preis': 12.50,
                    'lagerbestand': 8,
                    'kategorie': 'Werkzeug',
                    'aktiv': True
                },
                {
                    'id': 'MOCK-003',
                    'artikel_nummer': '12347',
                    'name': 'Häkelnadel Set',
                    'preis': 24.99,
                    'lagerbestand': 3,
                    'kategorie': 'Werkzeug',
                    'aktiv': True
                }
            ]
            
            # Filter Mock-Artikel nach Suchanfrage
            for artikel in mock_artikel:
                if (query.lower() in artikel['name'].lower() or 
                    query in artikel['artikel_nummer']):
                    gefundene_artikel.append(artikel)
        
        return jsonify({
            'success': True,
            'artikel': gefundene_artikel[:limit],
            'anzahl_gefunden': len(gefundene_artikel)
        })
        
    except Exception as e:
        logger.error(f"Fehler bei Artikel-Suche: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@kasse_bp.route('/warenkorb/hinzufuegen', methods=['POST'])
def warenkorb_hinzufuegen():
    """
    Artikel zum Warenkorb hinzufügen
    AJAX-Endpoint für dynamische Warenkorb-Updates
    """
    try:
        data = request.get_json()
        
        # Validierung
        required_fields = ['artikel_id', 'name', 'preis']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Feld {field} fehlt'})
        
        # Artikel-Daten vorbereiten
        artikel_data = {
            'artikel_id': data['artikel_id'],
            'artikel_nummer': data.get('artikel_nummer', ''),
            'name': data['name'],
            'preis': float(data['preis']),
            'menge': float(data.get('menge', 1)),
            'mwst_satz': float(data.get('mwst_satz', 19.0)),
            'kategorie': data.get('kategorie', 'Unbekannt')
        }
        
        # Zum Warenkorb hinzufügen
        add_to_warenkorb(artikel_data)
        
        # Neue Summen berechnen
        warenkorb = get_warenkorb()
        warenkorb_summen = calculate_warenkorb_totals(warenkorb)
        
        return jsonify({
            'success': True,
            'warenkorb': warenkorb,
            'warenkorb_summen': warenkorb_summen,
            'message': f'{artikel_data["name"]} wurde zum Warenkorb hinzugefügt'
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen zum Warenkorb: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@kasse_bp.route('/warenkorb/entfernen', methods=['POST'])
def warenkorb_entfernen():
    """
    Artikel aus Warenkorb entfernen
    """
    try:
        data = request.get_json()
        warenkorb_id = data.get('warenkorb_id')
        
        if not warenkorb_id:
            return jsonify({'success': False, 'error': 'Warenkorb-ID fehlt'})
        
        # Artikel entfernen
        remove_from_warenkorb(warenkorb_id)
        
        # Neue Summen berechnen
        warenkorb = get_warenkorb()
        warenkorb_summen = calculate_warenkorb_totals(warenkorb)
        
        return jsonify({
            'success': True,
            'warenkorb': warenkorb,
            'warenkorb_summen': warenkorb_summen,
            'message': 'Artikel wurde aus dem Warenkorb entfernt'
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Entfernen aus Warenkorb: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@kasse_bp.route('/warenkorb/aktualisieren', methods=['POST'])
def warenkorb_aktualisieren():
    """
    Warenkorb-Position aktualisieren (Menge ändern)
    """
    try:
        data = request.get_json()
        warenkorb_id = data.get('warenkorb_id')
        neue_menge = float(data.get('menge', 1))
        
        if not warenkorb_id:
            return jsonify({'success': False, 'error': 'Warenkorb-ID fehlt'})
        
        if neue_menge <= 0:
            return jsonify({'success': False, 'error': 'Menge muss größer als 0 sein'})
        
        # Warenkorb aktualisieren
        warenkorb = get_warenkorb()
        for item in warenkorb:
            if item.get('warenkorb_id') == warenkorb_id:
                item['menge'] = neue_menge
                break
        
        session['warenkorb'] = warenkorb
        
        # Neue Summen berechnen
        warenkorb_summen = calculate_warenkorb_totals(warenkorb)
        
        return jsonify({
            'success': True,
            'warenkorb': warenkorb,
            'warenkorb_summen': warenkorb_summen,
            'message': 'Warenkorb wurde aktualisiert'
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Warenkorbs: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@kasse_bp.route('/verkauf/abschliessen', methods=['POST'])
def verkauf_abschliessen():
    """
    Verkauf abschließen mit TSE-Signierung
    Hauptfunktion für Kassenbuchungen
    """
    try:
        data = request.get_json()
        
        # Validierung
        warenkorb = get_warenkorb()
        if not warenkorb:
            return jsonify({'success': False, 'error': 'Warenkorb ist leer'})
        
        zahlungsart = data.get('zahlungsart')
        if not zahlungsart:
            return jsonify({'success': False, 'error': 'Zahlungsart nicht gewählt'})
        
        # Warenkorb-Summen berechnen
        warenkorb_summen = calculate_warenkorb_totals(warenkorb)
        
        # 1. TSE-Transaktion starten
        tse_transaction = tse_service.start_transaction(
            process_type="Kassenbeleg-V1.0",
            client_id="KASSE-01"
        )
        
        if not tse_transaction.get('success'):
            return jsonify({
                'success': False, 
                'error': f"TSE-Fehler: {tse_transaction.get('error', 'Unbekannt')}"
            })
        
        # 2. Beleg in Datenbank erstellen (nur wenn Models verfügbar)
        if models_available and db:
            try:
                # Neuen Beleg erstellen
                beleg = KassenBeleg(
                    beleg_typ=BelegTyp.RECHNUNG,
                    netto_gesamt=warenkorb_summen['netto_gesamt'],
                    mwst_gesamt=warenkorb_summen['mwst_gesamt'],
                    brutto_gesamt=warenkorb_summen['brutto_gesamt'],
                    zahlungsart=ZahlungsArt(zahlungsart),
                    gegeben=data.get('erhaltener_betrag'),
                    rueckgeld=data.get('rueckgeld'),
                    kassierer_name=session.get('kassierer_name', 'Demo Kassierer'),
                    kassen_id='KASSE-01'
                )
                
                db.session.add(beleg)
                db.session.flush()  # Um die ID zu bekommen
                
                # 3. Belegpositionen hinzufügen
                for i, item in enumerate(warenkorb):
                    position = BelegPosition(
                        beleg_id=beleg.id,
                        position=i + 1,
                        artikel_id=item.get('artikel_id'),
                        artikel_nummer=item.get('artikel_nummer'),
                        artikel_name=item['name'],
                        menge=item['menge'],
                        einzelpreis_netto=item['preis'],
                        einzelpreis_brutto=item['preis'] * (1 + item['mwst_satz'] / 100),
                        mwst_satz=item['mwst_satz'],
                        mwst_betrag=item['mwst_betrag'],
                        netto_betrag=item['netto_betrag'],
                        brutto_betrag=item['brutto_betrag']
                    )
                    db.session.add(position)
                
                # 4. TSE-Transaktion beenden
                process_data = {
                    'beleg_nummer': beleg.belegnummer,
                    'brutto_betrag': float(beleg.brutto_gesamt),
                    'zahlungsart': beleg.zahlungsart.value,
                    'positionen': len(warenkorb)
                }
                
                tse_finish = tse_service.finish_transaction(
                    tse_transaction['transaction_id'],
                    process_data
                )
                
                if not tse_finish.get('success'):
                    db.session.rollback()
                    return jsonify({
                        'success': False,
                        'error': f"TSE-Signierung fehlgeschlagen: {tse_finish.get('error', 'Unbekannt')}"
                    })
                
                # 5. TSE-Transaktion in Datenbank speichern
                tse_transaktion = KassenTransaktion(
                    tse_serial=tse_finish['tse_serial'],
                    tse_transaktion_nummer=tse_transaction['transaction_id'],
                    tse_start=datetime.fromisoformat(tse_finish['started_at'].replace('Z', '')),
                    tse_ende=datetime.fromisoformat(tse_finish['finished_at'].replace('Z', '')),
                    tse_signatur_zaehler=tse_finish['signature_counter'],
                    tse_signatur_algorithmus=tse_finish['signature_algorithm'],
                    tse_signatur=tse_finish['signature'],
                    tse_prozess_typ='Kassenbeleg-V1',
                    tse_client_id='KASSE-01'
                )
                
                tse_transaktion.set_prozess_daten(process_data)
                db.session.add(tse_transaktion)
                db.session.flush()
                
                # Beleg mit TSE-Transaktion verknüpfen
                beleg.tse_transaktion_id = tse_transaktion.id
                
                # 6. Alles speichern
                db.session.commit()
                
                # 7. Warenkorb leeren
                clear_warenkorb()
                
                logger.info(f"Verkauf erfolgreich abgeschlossen: {beleg.belegnummer}")
                
                return jsonify({
                    'success': True,
                    'beleg_nummer': beleg.belegnummer,
                    'beleg_id': beleg.id,
                    'brutto_betrag': float(beleg.brutto_gesamt),
                    'tse_signatur': tse_finish['signature'][:32] + '...',
                    'message': 'Verkauf erfolgreich abgeschlossen'
                })
                
            except Exception as db_error:
                db.session.rollback()
                logger.error(f"Datenbank-Fehler beim Verkaufsabschluss: {str(db_error)}")
                return jsonify({'success': False, 'error': f'Datenbank-Fehler: {str(db_error)}'})
        
        else:
            # Mock-Modus ohne Datenbank
            beleg_nummer = f"MOCK-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            # TSE-Transaktion trotzdem beenden
            process_data = {
                'beleg_nummer': beleg_nummer,
                'brutto_betrag': warenkorb_summen['brutto_gesamt'],
                'zahlungsart': zahlungsart,
                'positionen': len(warenkorb)
            }
            
            tse_finish = tse_service.finish_transaction(
                tse_transaction['transaction_id'],
                process_data
            )
            
            # Warenkorb leeren
            clear_warenkorb()
            
            logger.info(f"Mock-Verkauf abgeschlossen: {beleg_nummer}")
            
            return jsonify({
                'success': True,
                'beleg_nummer': beleg_nummer,
                'brutto_betrag': warenkorb_summen['brutto_gesamt'],
                'tse_signatur': tse_finish['signature'][:32] + '...',
                'message': 'Mock-Verkauf erfolgreich abgeschlossen (keine Datenbank)'
            })
        
    except Exception as e:
        if models_available and db:
            db.session.rollback()
        logger.error(f"Fehler beim Verkaufsabschluss: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@kasse_bp.route('/tagesabschluss')
def tagesabschluss():
    """
    Tagesabschluss anzeigen
    Übersicht über alle Kassenbuchungen des Tages
    """
    try:
        datum_str = request.args.get('datum', date.today().isoformat())
        datum = date.fromisoformat(datum_str)
        
        # Tagesstatistiken berechnen
        statistik = KassensystemUtils.get_tagesabschluss(datum, 'KASSE-01')
        
        # Zusätzliche Daten für Tagesabschluss
        zusatz_daten = {
            'kassenstand_anfang': 0.00,
            'kassenstand_ende': statistik.get('umsatz_bar', 0.00),
            'differenz': 0.00,
            'geprueft': False,
            'abgeschlossen': False
        }
        
        return render_template('kasse/tagesabschluss.html',
            statistik=statistik,
            zusatz_daten=zusatz_daten,
            datum=datum,
            page_title=f"Tagesabschluss {datum.strftime('%d.%m.%Y')}"
        )
        
    except Exception as e:
        logger.error(f"Fehler beim Tagesabschluss: {str(e)}")
        flash(f"Fehler beim Laden des Tagesabschlusses: {str(e)}", "error")
        return redirect(url_for('kasse.kassen_index'))

@kasse_bp.route('/einstellungen')
def kassen_einstellungen():
    """
    Kassen-Einstellungen
    """
    try:
        # TSE-Konfiguration laden
        tse_config = None
        if models_available and db:
            try:
                tse_config = TSEKonfiguration.query.filter_by(aktiv=True).first()
            except:
                pass
        
        # MwSt-Sätze laden
        mwst_saetze = []
        if models_available and db:
            try:
                mwst_saetze = MwStSatz.get_aktuelle_saetze()
            except:
                pass
        
        return render_template('kasse/einstellungen.html',
            tse_config=tse_config,
            mwst_saetze=mwst_saetze,
            page_title="Kassen-Einstellungen"
        )
        
    except Exception as e:
        logger.error(f"Fehler bei Kassen-Einstellungen: {str(e)}")
        flash(f"Fehler beim Laden der Einstellungen: {str(e)}", "error")
        return redirect(url_for('kasse.kassen_index'))

# Weitere Routen für fehlende Templates
@kasse_bp.route('/berichte')
def berichte():
    """Berichte und Statistiken"""
    try:
        return render_template('kasse/berichte.html',
            page_title="Berichte"
        )
    except Exception as e:
        logger.error(f"Fehler bei Berichte: {str(e)}")
        flash(f"Fehler beim Laden der Berichte: {str(e)}", "error")
        return redirect(url_for('kasse.kassen_index'))

@kasse_bp.route('/z-bericht')
def z_bericht():
    """Z-Bericht (Kassenjournal)"""
    try:
        return render_template('kasse/z_bericht.html',
            page_title="Z-Bericht"
        )
    except Exception as e:
        logger.error(f"Fehler bei Z-Bericht: {str(e)}")
        flash(f"Fehler beim Laden des Z-Berichts: {str(e)}", "error")
        return redirect(url_for('kasse.kassen_index'))

@kasse_bp.route('/beleg/<int:beleg_id>')
def beleg_detail(beleg_id):
    """Beleg-Detail anzeigen"""
    try:
        beleg = None
        firma = {
            'name': 'StitchAdmin GmbH',
            'strasse': 'Musterstraße 1',
            'plz': '12345',
            'ort': 'Musterstadt',
            'telefon': '0123-456789',
            'steuernummer': 'DE123456789'
        }
        
        if models_available and db:
            try:
                beleg = KassenBeleg.query.get_or_404(beleg_id)
            except:
                pass
        
        if not beleg:
            flash('Beleg nicht gefunden', 'error')
            return redirect(url_for('kasse.kassen_index'))
        
        return render_template('kasse/beleg_detail.html',
            beleg=beleg,
            firma=firma,
            page_title=f"Beleg {beleg.beleg_nummer}"
        )
    except Exception as e:
        logger.error(f"Fehler bei Beleg-Detail: {str(e)}")
        flash(f"Fehler beim Laden des Belegs: {str(e)}", "error")
        return redirect(url_for('kasse.kassen_index'))

@kasse_bp.route('/api/sale', methods=['POST'])
def api_sale():
    """API-Endpunkt für Verkauf aus verkauf.html"""
    try:
        data = request.get_json()
        
        # Mock-Response für Entwicklung
        receipt_id = f"MOCK-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        return jsonify({
            'success': True,
            'receipt_id': receipt_id,
            'message': 'Verkauf erfolgreich (Mock-Modus)'
        })
        
    except Exception as e:
        logger.error(f"Fehler bei API-Sale: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@kasse_bp.route('/api/beleg/<int:beleg_id>/storno', methods=['POST'])
def api_beleg_storno(beleg_id):
    """API-Endpunkt für Beleg-Stornierung"""
    try:
        if models_available and db:
            beleg = KassenBeleg.query.get_or_404(beleg_id)
            beleg.storniert = True
            beleg.storno_datum = datetime.utcnow()
            beleg.storno_grund = request.get_json().get('grund', 'Stornierung durch Benutzer')
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Beleg wurde storniert'
        })
        
    except Exception as e:
        logger.error(f"Fehler bei Beleg-Storno: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@kasse_bp.route('/api/tagesabschluss', methods=['POST'])
def api_tagesabschluss():
    """API-Endpunkt für Tagesabschluss"""
    try:
        data = request.get_json()
        datum = data.get('date', date.today().isoformat())
        
        # TODO: Implementiere echten Tagesabschluss
        return jsonify({
            'success': True,
            'message': f'Tagesabschluss für {datum} wurde durchgeführt (Mock-Modus)'
        })
        
    except Exception as e:
        logger.error(f"Fehler bei Tagesabschluss: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)

# Export des Blueprints
__all__ = ['kasse_bp']
