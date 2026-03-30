# -*- coding: utf-8 -*-
"""
Eingangsrechnung OCR-Service
Extrahiert Rechnungsdaten automatisch aus PDF-Dateien.
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""
import re
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime

logger = logging.getLogger(__name__)

# Kategorie → SKR03-Konto-Mapping (für Wareneinkauf/Aufwand)
KATEGORIEN = {
    'textilien': {
        'label': 'Textilien / Material',
        'icon': 'bi-box-seam',
        'konto_aufwand': '3200',
        'konto_label': 'Wareneinkauf Textilien (3200)',
        'beispiele': 'T-Shirts, Hoodies, Polos, Caps',
    },
    'druckbedarf': {
        'label': 'Druckfarben / Verbrauch',
        'icon': 'bi-droplet-fill',
        'konto_aufwand': '3980',
        'konto_label': 'Sonstiger Wareneinkauf (3980)',
        'beispiele': 'Tinte, Folien, Transferpapier, Chemikalien',
    },
    'maschinen': {
        'label': 'Maschinen / Werkzeug',
        'icon': 'bi-gear-wide-connected',
        'konto_aufwand': '4830',
        'konto_label': 'Werkzeuge/Maschinen (4830)',
        'beispiele': 'Stickmaschine, Drucker, Schneideplotter',
    },
    'buero': {
        'label': 'Bürobedarf / IT',
        'icon': 'bi-clipboard2',
        'konto_aufwand': '4910',
        'konto_label': 'Bürobedarf (4910)',
        'beispiele': 'Papier, Toner, Software, PC-Zubehör',
    },
    'dienstleistung': {
        'label': 'Dienstleistung / Fremdleistung',
        'icon': 'bi-person-workspace',
        'konto_aufwand': '4980',
        'konto_label': 'Sonstige Kosten (4980)',
        'beispiele': 'Lohnstickerei, Grafik, Beratung, Reparatur',
    },
    'energie': {
        'label': 'Energie / Wasser',
        'icon': 'bi-lightning-charge',
        'konto_aufwand': '4240',
        'konto_label': 'Energiekosten (4240)',
        'beispiele': 'Strom, Gas, Wasser, Heizung',
    },
    'versicherung': {
        'label': 'Versicherungen / Beiträge',
        'icon': 'bi-shield-check',
        'konto_aufwand': '4360',
        'konto_label': 'Versicherungen (4360)',
        'beispiele': 'Betriebshaftpflicht, Inhaltsversicherung',
    },
    'porto': {
        'label': 'Porto / Versandkosten',
        'icon': 'bi-truck',
        'konto_aufwand': '4220',
        'konto_label': 'Porto/Versand (4220)',
        'beispiele': 'DHL, DPD, UPS, Briefporto',
    },
    'miete': {
        'label': 'Miete / Raumkosten',
        'icon': 'bi-building',
        'konto_aufwand': '4210',
        'konto_label': 'Miete (4210)',
        'beispiele': 'Miete, Nebenkosten, Reinigung',
    },
    'kfz': {
        'label': 'Fahrzeug / Tanken',
        'icon': 'bi-fuel-pump',
        'konto_aufwand': '4500',
        'konto_label': 'Kfz-Kosten (4500)',
        'beispiele': 'Benzin, Diesel, Werkstatt, TÜV',
    },
    'telefon': {
        'label': 'Telefon / Internet',
        'icon': 'bi-phone',
        'konto_aufwand': '4920',
        'konto_label': 'Telefon/Internet (4920)',
        'beispiele': 'Mobilfunk, Festnetz, DSL, Hosting',
    },
    'sonstiges': {
        'label': 'Sonstiges',
        'icon': 'bi-three-dots',
        'konto_aufwand': '4980',
        'konto_label': 'Sonstige Kosten (4980)',
        'beispiele': 'Alles andere',
    },
}

# Gegenkonto je nach Zahlungsart
ZAHLUNGSART_KONTEN = {
    'offen': ('1600', 'Verbindlichkeiten (noch offen)'),
    'bar': ('1000', 'Barkasse (sofort bezahlt)'),
    'bank': ('1200', 'Bank (bereits überwiesen)'),
}


def extrahiere_rechnungsdaten(pdf_path: str) -> dict:
    """
    Liest PDF und extrahiert Rechnungsdaten per Regex.
    Returns dict mit: lieferant, rechnungsnummer, datum, netto, mwst_satz,
                      mwst_betrag, brutto, rohtext
    """
    try:
        import pdfplumber
    except ImportError:
        logger.error('pdfplumber nicht installiert')
        return _leere_daten()

    rohtext = ''
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    rohtext += text + '\n'
    except Exception as e:
        logger.error(f'PDF-Lesefehler: {e}')
        return _leere_daten()

    if not rohtext.strip():
        return _leere_daten()

    return {
        'lieferant': _extrahiere_lieferant(rohtext),
        'rechnungsnummer': _extrahiere_rechnungsnummer(rohtext),
        'datum': _extrahiere_datum(rohtext),
        'netto': _extrahiere_netto(rohtext),
        'mwst_satz': _extrahiere_mwst_satz(rohtext),
        'mwst_betrag': _extrahiere_mwst_betrag(rohtext),
        'brutto': _extrahiere_brutto(rohtext),
        'rohtext': rohtext[:2000],  # Vorschau
        'gefunden': True,
    }


def _leere_daten():
    return {
        'lieferant': '', 'rechnungsnummer': '', 'datum': '',
        'netto': '', 'mwst_satz': 19, 'mwst_betrag': '', 'brutto': '',
        'rohtext': '', 'gefunden': False,
    }


def _extrahiere_lieferant(text: str) -> str:
    """Nimmt die ersten nicht-leeren Zeilen als Lieferant"""
    zeilen = [z.strip() for z in text.split('\n') if z.strip()]
    # Erste Zeile die kein Schlüsselwort ist
    skip = {'rechnung', 'invoice', 'lieferschein', 'gutschrift', 'rechnungsnummer',
            'datum', 'seite', 'page', 'www.', 'http'}
    for zeile in zeilen[:8]:
        if not any(s in zeile.lower() for s in skip) and len(zeile) > 3:
            return zeile[:80]
    return zeilen[0][:80] if zeilen else ''


def _extrahiere_rechnungsnummer(text: str) -> str:
    patterns = [
        r'Rechnungs(?:nummer|nr\.?)\s*[:\-]?\s*([A-Z0-9\-/]+)',
        r'Invoice\s*(?:No\.?|Number|Nr\.?)\s*[:\-]?\s*([A-Z0-9\-/]+)',
        r'RE[\-\s]?(\d{4,}[\-/]?\d*)',
        r'Beleg[\-\s]?Nr\.?\s*[:\-]?\s*([A-Z0-9\-/]+)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ''


def _extrahiere_datum(text: str) -> str:
    patterns = [
        r'Rechnungs(?:datum|datum)\s*[:\-]?\s*(\d{1,2}[.\-]\d{1,2}[.\-]\d{2,4})',
        r'Datum\s*[:\-]?\s*(\d{1,2}[.\-]\d{1,2}[.\-]\d{2,4})',
        r'Date\s*[:\-]?\s*(\d{1,2}[.\-]\d{1,2}[.\-]\d{2,4})',
        r'(\d{1,2})\.\s*(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s*(\d{4})',
        # Letzter Fallback: erstes Datum im Dokument
        r'(\d{1,2}[.\-]\d{1,2}[.\-]\d{2,4})',
    ]
    monate = {
        'januar': '01', 'februar': '02', 'märz': '03', 'april': '04',
        'mai': '05', 'juni': '06', 'juli': '07', 'august': '08',
        'september': '09', 'oktober': '10', 'november': '11', 'dezember': '12',
    }
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            if 'Januar' in p or 'januar' in p.lower():
                tag, monat_str, jahr = m.group(1), m.group(2).lower(), m.group(3)
                monat = monate.get(monat_str, '01')
                return f'{jahr}-{monat}-{tag.zfill(2)}'
            datum_str = m.group(1).replace('-', '.')
            teile = datum_str.split('.')
            if len(teile) == 3:
                tag, monat, jahr = teile
                if len(jahr) == 2:
                    jahr = '20' + jahr
                return f'{jahr}-{monat.zfill(2)}-{tag.zfill(2)}'
    return ''


def _parse_betrag(betrag_str: str) -> str:
    """Normalisiert deutschen Betrag zu float-String"""
    if not betrag_str:
        return ''
    betrag_str = betrag_str.strip().replace(' ', '').replace('€', '').replace('EUR', '')
    # 1.234,56 → 1234.56
    if ',' in betrag_str and '.' in betrag_str:
        betrag_str = betrag_str.replace('.', '').replace(',', '.')
    elif ',' in betrag_str:
        betrag_str = betrag_str.replace(',', '.')
    try:
        val = float(betrag_str)
        return f'{val:.2f}'
    except ValueError:
        return ''


def _extrahiere_brutto(text: str) -> str:
    patterns = [
        r'Gesamt(?:betrag)?\s*(?:brutto|inkl\.?\s*MwSt\.?)?\s*[:\-]?\s*([\d.,]+)\s*(?:€|EUR)?',
        r'Rechnungs(?:betrag|summe)\s*[:\-]?\s*([\d.,]+)\s*(?:€|EUR)?',
        r'Total\s*[:\-]?\s*([\d.,]+)\s*(?:€|EUR)?',
        r'Brutto\s*[:\-]?\s*([\d.,]+)\s*(?:€|EUR)?',
        r'Zu\s*zahlen\s*[:\-]?\s*([\d.,]+)\s*(?:€|EUR)?',
        r'Zahlbetrag\s*[:\-]?\s*([\d.,]+)\s*(?:€|EUR)?',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            val = _parse_betrag(m.group(1))
            if val:
                return val
    return ''


def _extrahiere_mwst_satz(text: str) -> int:
    """Gibt 19 oder 7 zurück"""
    if re.search(r'7\s*%', text):
        return 7
    return 19


def _extrahiere_mwst_betrag(text: str) -> str:
    patterns = [
        r'(?:MwSt|Mehrwertsteuer|USt\.?|VAT)\s*(?:\d+\s*%)?\s*[:\-]?\s*([\d.,]+)\s*(?:€|EUR)?',
        r'(?:19|7)\s*%\s*(?:MwSt|USt)\s*[:\-]?\s*([\d.,]+)\s*(?:€|EUR)?',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            val = _parse_betrag(m.group(1))
            if val:
                return val
    return ''


def _extrahiere_netto(text: str) -> str:
    patterns = [
        r'Netto(?:betrag|summe)?\s*[:\-]?\s*([\d.,]+)\s*(?:€|EUR)?',
        r'(?:Zwischen|Sub)summe\s*[:\-]?\s*([\d.,]+)\s*(?:€|EUR)?',
        r'Summe\s+(?:netto|ohne\s+MwSt\.?)\s*[:\-]?\s*([\d.,]+)\s*(?:€|EUR)?',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            val = _parse_betrag(m.group(1))
            if val:
                return val
    # Fallback: Brutto - MwSt
    brutto = _extrahiere_brutto(text)
    mwst = _extrahiere_mwst_betrag(text)
    if brutto and mwst:
        try:
            netto = float(brutto) - float(mwst)
            return f'{netto:.2f}'
        except ValueError:
            pass
    return ''


def extrahiere_aus_bild(bild_path: str) -> dict:
    """
    Extrahiert Rechnungsdaten aus Foto/Bild (JPG, PNG).
    Nutzt pytesseract falls verfuegbar, sonst leere Daten.
    """
    rohtext = ''
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(bild_path)
        # Bild optimieren fuer OCR
        if img.mode != 'RGB':
            img = img.convert('RGB')
        # Versuche Deutsch + Englisch
        try:
            rohtext = pytesseract.image_to_string(img, lang='deu+eng')
        except Exception:
            rohtext = pytesseract.image_to_string(img)
    except ImportError:
        logger.warning('pytesseract nicht installiert - Bild-OCR nicht verfuegbar')
        return _leere_daten()
    except Exception as e:
        logger.error(f'Bild-OCR-Fehler: {e}')
        return _leere_daten()

    if not rohtext.strip():
        logger.info('Bild-OCR: Kein Text erkannt')
        return _leere_daten()

    logger.info(f'Bild-OCR: {len(rohtext)} Zeichen erkannt')
    return {
        'lieferant': _extrahiere_lieferant(rohtext),
        'rechnungsnummer': _extrahiere_rechnungsnummer(rohtext),
        'datum': _extrahiere_datum(rohtext),
        'netto': _extrahiere_netto(rohtext),
        'mwst_satz': _extrahiere_mwst_satz(rohtext),
        'mwst_betrag': _extrahiere_mwst_betrag(rohtext),
        'brutto': _extrahiere_brutto(rohtext),
        'rohtext': rohtext[:2000],
        'gefunden': True,
        'quelle': 'bild_ocr',
    }


def berechne_fehlende_werte(netto: str, mwst_betrag: str, brutto: str, mwst_satz: int) -> dict:
    """Ergänzt fehlende Werte rechnerisch"""
    result = {'netto': netto, 'mwst_betrag': mwst_betrag, 'brutto': brutto}
    try:
        if brutto and mwst_betrag and not netto:
            result['netto'] = f'{float(brutto) - float(mwst_betrag):.2f}'
        elif netto and not mwst_betrag and not brutto:
            mwst = float(netto) * mwst_satz / 100
            result['mwst_betrag'] = f'{mwst:.2f}'
            result['brutto'] = f'{float(netto) + mwst:.2f}'
        elif netto and mwst_betrag and not brutto:
            result['brutto'] = f'{float(netto) + float(mwst_betrag):.2f}'
        elif brutto and not mwst_betrag and not netto:
            netto_val = float(brutto) / (1 + mwst_satz / 100)
            result['netto'] = f'{netto_val:.2f}'
            result['mwst_betrag'] = f'{float(brutto) - netto_val:.2f}'
    except (ValueError, TypeError):
        pass
    return result
