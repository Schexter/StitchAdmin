# -*- coding: utf-8 -*-
"""
DPD CSV-Export Utility für myDPD Business Portal
==================================================
Erzeugt CSV-Dateien im offiziellen DPD 70-Felder-Format.

Format: Semikolon-getrennt, UTF-8 mit BOM, keine Header-Zeile.
Spezifikation: https://business.dpd.de/content/dokumente/myDPD-CSV-Auftragsimport.pdf
"""

import io
import re
from datetime import datetime


# DPD-Feldnamen (70 Felder, 0-basiert)
DPD_FIELD_NAMES = [
    'Anrede',               # 0
    'Firma',                # 1
    'Vorname',              # 2
    'Nachname',             # 3
    'Land',                 # 4
    'PLZ',                  # 5
    'Ort',                  # 6
    'Strasse',              # 7
    'Hausnummer',           # 8
    'Sendungsreferenz1',    # 9
    'Telefon',              # 10
    'Email',                # 11 (für Predict)
    'Gewicht',              # 12 (kg, Dezimal mit Punkt)
    'Inhalt',               # 13
    'Sendungsreferenz2',    # 14
    'Adresszusatz',         # 15
    'Abteilung',            # 16
    'Bundesland',           # 17
    'Kontaktperson',        # 18
    'Telefon2',             # 19
    # Felder 20-69: Dienste, Nachnahme, Versicherung, Retoure, Zoll etc.
]

TOTAL_FIELDS = 70


def build_dpd_row(data: dict) -> list:
    """
    Erzeugt eine 70-Felder-Zeile im DPD-Format.

    Args:
        data: Dict mit Versanddaten. Mögliche Keys:
            - anrede: "Herr", "Frau", "" (optional)
            - firma: Firmenname
            - vorname, nachname: Empfänger-Name
            - land: Ländercode (default: DE)
            - plz: Postleitzahl
            - ort: Stadt
            - strasse: Strassenname (ohne Hausnummer)
            - hausnummer: Hausnummer
            - referenz: Sendungsreferenz (z.B. Auftragsnummer)
            - referenz2: Zweite Referenz
            - telefon: Telefonnummer
            - email: E-Mail (für DPD Predict SMS/Mail)
            - gewicht: Gewicht in kg (Dezimal)
            - inhalt: Paketinhalt-Beschreibung
            - adresszusatz: Adresszusatz (Etage, Hinterhaus etc.)
            - kontaktperson: Kontaktperson bei Firmen

    Returns:
        Liste mit 70 String-Elementen
    """
    row = [''] * TOTAL_FIELDS

    row[0] = _clean(data.get('anrede', ''))
    row[1] = _clean(data.get('firma', ''))
    row[2] = _clean(data.get('vorname', ''))
    row[3] = _clean(data.get('nachname', ''))
    row[4] = _clean(data.get('land', 'DE')).upper()
    row[5] = _clean(data.get('plz', ''))
    row[6] = _clean(data.get('ort', ''))
    row[7] = _clean(data.get('strasse', ''))
    row[8] = _clean(data.get('hausnummer', ''))
    row[9] = _clean(data.get('referenz', ''))
    row[10] = _clean(data.get('telefon', ''))
    row[11] = _clean(data.get('email', ''))
    row[14] = _clean(data.get('referenz2', ''))
    row[15] = _clean(data.get('adresszusatz', ''))
    row[18] = _clean(data.get('kontaktperson', ''))

    # Gewicht: Dezimal mit Punkt, mindestens 0.1 kg
    gewicht = data.get('gewicht', 0)
    try:
        gewicht = float(gewicht)
        if gewicht < 0.1:
            gewicht = 0.1
        row[12] = f'{gewicht:.1f}'
    except (ValueError, TypeError):
        row[12] = '0.1'

    row[13] = _clean(data.get('inhalt', ''))

    return row


def generate_dpd_csv(rows: list, dpd_kundennummer: str = '') -> bytes:
    """
    Erzeugt eine komplette DPD-CSV-Datei.

    Args:
        rows: Liste von Dicts (jeweils an build_dpd_row übergeben)
        dpd_kundennummer: DPD-Kundennummer (wird nicht in CSV geschrieben,
                          aber im Portal beim Upload zugeordnet)

    Returns:
        Bytes der CSV-Datei (UTF-8 mit BOM)
    """
    output = io.StringIO()

    for data in rows:
        row = build_dpd_row(data)
        line = ';'.join(row)
        output.write(line + '\n')

    csv_content = output.getvalue()
    # UTF-8 mit BOM für Excel-Kompatibilität
    return b'\xef\xbb\xbf' + csv_content.encode('utf-8')


def parse_address_for_dpd(full_name: str, street_line: str) -> dict:
    """
    Parst einen Namen und eine Strassenzeile in DPD-kompatible Felder.

    Args:
        full_name: "Max Mustermann" oder "Firma GmbH / Max Mustermann"
        street_line: "Musterstr. 12a" oder "Musterstrasse 12"

    Returns:
        Dict mit vorname, nachname, firma, strasse, hausnummer
    """
    result = {
        'vorname': '',
        'nachname': '',
        'firma': '',
        'strasse': '',
        'hausnummer': '',
    }

    # Name parsen
    if full_name:
        full_name = full_name.strip()
        # Firma / Kontaktperson
        if '/' in full_name:
            parts = full_name.split('/', 1)
            result['firma'] = parts[0].strip()
            name_part = parts[1].strip()
        elif any(kw in full_name.lower() for kw in ['gmbh', 'ag', 'kg', 'ohg', 'e.k.', 'ug', 'gbr', 'mbh']):
            result['firma'] = full_name
            name_part = ''
        else:
            name_part = full_name

        if name_part:
            name_parts = name_part.split()
            if len(name_parts) >= 2:
                result['vorname'] = name_parts[0]
                result['nachname'] = ' '.join(name_parts[1:])
            elif len(name_parts) == 1:
                result['nachname'] = name_parts[0]

    # Strasse + Hausnummer trennen
    if street_line:
        street_line = street_line.strip()
        # Pattern: "Musterstr. 12a" oder "Musterstrasse 12"
        match = re.match(r'^(.+?)\s+(\d+\s*\w?)$', street_line)
        if match:
            result['strasse'] = match.group(1).strip()
            result['hausnummer'] = match.group(2).strip()
        else:
            result['strasse'] = street_line

    return result


def _clean(value) -> str:
    """Bereinigt einen Wert für CSV-Export (kein Semikolon, kein Zeilenumbruch)."""
    if value is None:
        return ''
    s = str(value).strip()
    s = s.replace(';', ',').replace('\n', ' ').replace('\r', '')
    return s


# ─── DHL Business CSV ────────────────────────────────────────────────────────

DHL_HEADERS = [
    'Auftrags-Nr.',
    'Empfaenger Firma',
    'Empfaenger Vorname',
    'Empfaenger Nachname',
    'Empfaenger Strasse',
    'Empfaenger Hausnummer',
    'Empfaenger PLZ',
    'Empfaenger Ort',
    'Empfaenger Land',
    'Empfaenger Telefon',
    'Empfaenger Email',
    'Gewicht (kg)',
    'Inhalt',
    'Referenz',
]


def build_dhl_row(data: dict) -> list:
    """Erzeugt eine DHL-CSV-Zeile."""
    addr = parse_address_for_dpd(
        data.get('name', ''),
        data.get('strasse_komplett', '')
    )
    return [
        _clean(data.get('referenz', '')),
        _clean(data.get('firma', addr['firma'])),
        _clean(data.get('vorname', addr['vorname'])),
        _clean(data.get('nachname', addr['nachname'])),
        _clean(data.get('strasse', addr['strasse'])),
        _clean(data.get('hausnummer', addr['hausnummer'])),
        _clean(data.get('plz', '')),
        _clean(data.get('ort', '')),
        _clean(data.get('land', 'DE')).upper(),
        _clean(data.get('telefon', '')),
        _clean(data.get('email', '')),
        f"{float(data.get('gewicht', 0.5)):.2f}",
        _clean(data.get('inhalt', 'Textilien/Stickerei')),
        _clean(data.get('referenz2', '')),
    ]


def generate_dhl_csv(rows: list) -> bytes:
    """Erzeugt eine DHL Business CSV-Datei mit Header-Zeile."""
    output = io.StringIO()
    # Header
    output.write(';'.join(DHL_HEADERS) + '\n')
    for data in rows:
        row = build_dhl_row(data)
        output.write(';'.join(row) + '\n')
    return b'\xef\xbb\xbf' + output.getvalue().encode('utf-8')
