# -*- coding: utf-8 -*-
"""
Printequipment Druckparameter PDF-Parser
Extrahiert Sublimations-Parameter aus der Artikeldruckparameter-PDF.
"""

import re
import logging
import pdfplumber

logger = logging.getLogger(__name__)


def parse_druckparameter_pdf(pdf_path):
    """
    Parst die Printequipment Artikeldruckparameter-PDF.

    Returns:
        Liste von Dicts mit:
        - artikelname: str
        - sku_patterns: list[str]  (z.B. ['AL-', 'ALSS-'])
        - temperatur: str          (z.B. '190')
        - zeit: str                (z.B. '60-70 Sek.')
        - druck: str               (z.B. 'Mittel')
        - papier: str              (z.B. 'Oben')
        - bemerkung: str           (Produktionshinweise)
    """
    entries = []
    seen_skus = set()

    try:
        pdf = pdfplumber.open(pdf_path)
    except Exception as e:
        logger.error(f"PDF konnte nicht geoeffnet werden: {e}")
        return entries

    for page_num, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        for table in tables:
            if not table:
                continue

            for row_idx, row in enumerate(table):
                # Header-Zeile ueberspringen
                if row_idx == 0 and row and row[0] and 'Artikelname' in str(row[0]):
                    continue

                # Zeilen ohne genug Spalten ueberspringen
                if not row or len(row) < 6:
                    continue

                entry = _parse_row(row)
                if entry and entry['sku_raw'] not in seen_skus:
                    seen_skus.add(entry['sku_raw'])
                    entries.append(entry)

    pdf.close()
    logger.info(f"PDF geparst: {len(entries)} Eintraege aus {page_num + 1} Seiten")
    return entries


def _parse_row(row):
    """Parst eine einzelne Tabellenzeile."""
    try:
        artikelname = _clean(row[0])
        sku_raw = _clean(row[1])

        if not artikelname or not sku_raw:
            return None

        # Temperatur: "190°" oder "190" -> "190"
        temp_raw = _clean(row[2])
        temperatur = _extract_temperature(temp_raw)

        # Zeit: "60-70 Sek." -> als Text belassen
        zeit = _clean(row[3])

        # Druck: "Mittel", "Stark", "Leicht", "Leicht/Mittel"
        druck = _clean(row[4])

        # Papier: "Oben" oder "Unten"
        papier = _clean(row[5])

        # Bemerkung/Tipp (letzte Spalte)
        bemerkung = _clean(row[6]) if len(row) > 6 else ''

        # SKU-Patterns extrahieren (z.B. "AL-/ALSS-" -> ["AL-", "ALSS-"])
        sku_patterns = _extract_sku_patterns(sku_raw)

        if not sku_patterns:
            return None

        return {
            'artikelname': artikelname,
            'sku_raw': sku_raw,
            'sku_patterns': sku_patterns,
            'temperatur': temperatur,
            'zeit': zeit,
            'druck': druck,
            'papier': papier,
            'bemerkung': bemerkung,
        }

    except Exception as e:
        logger.debug(f"Zeile konnte nicht geparst werden: {e}")
        return None


def _clean(val):
    """Bereinigt einen Zellenwert."""
    if val is None:
        return ''
    text = str(val).strip()
    # Mehrzeilige Zellen zusammenfuegen
    text = ' '.join(text.split('\n'))
    # Doppelte Leerzeichen entfernen
    text = re.sub(r'\s+', ' ', text)
    return text


def _extract_temperature(raw):
    """Extrahiert Temperatur-Wert aus Text wie '190°' oder '190'."""
    if not raw:
        return ''
    match = re.search(r'(\d{2,3})', raw)
    return match.group(1) if match else raw


def _extract_sku_patterns(sku_raw):
    """
    Extrahiert SKU-Prefixes aus dem Artikelnummer-Feld.

    Beispiele:
      "AL-/ALSS-"         -> ["AL-", "ALSS-"]
      "BAA -/VML-/BAL-"   -> ["BAA", "VML-", "BAL-"]
      "ALHERZ-57"         -> ["ALHERZ-57"]
      "CHIP-KR"           -> ["CHIP-KR"]
    """
    if not sku_raw:
        return []

    # Splitten bei "/"
    parts = re.split(r'\s*/\s*', sku_raw)
    patterns = []

    for part in parts:
        p = part.strip()
        if p:
            # Leerzeichen innerhalb entfernen (z.B. "BAA -" -> "BAA-")
            p = re.sub(r'\s+', '', p)
            patterns.append(p)

    return patterns
