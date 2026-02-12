# -*- coding: utf-8 -*-
"""
OCR Service
===========
Texterkennung und Smart-Extraction für gescannte Dokumente

Features:
- Tesseract OCR für Texterkennung
- Automatische Spracherkennung (Deutsch/Englisch)
- Smart-Extraction: Beträge, Datum, Tracking-Nummern
- Unterstützung für Rechnungen, Briefe, Lieferscheine

Erstellt von: Hans Hahn - Alle Rechte vorbehalten
"""

import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logging.warning("pytesseract oder PIL nicht installiert - OCR-Funktion deaktiviert")

logger = logging.getLogger(__name__)


class OCRService:
    """
    Service für OCR-Texterkennung und Smart-Extraction
    """

    # Tracking-Nummer Patterns (verschiedene Versanddienstleister)
    TRACKING_PATTERNS = {
        'dhl': [
            r'\b\d{12}\b',  # DHL Standard 12 Ziffern
            r'\b\d{20}\b',  # DHL Express 20 Ziffern
            r'\bJJD\d{18}\b',  # DHL Paket Deutschland
        ],
        'dpd': [
            r'\b\d{14}\b',  # DPD 14 Ziffern
            r'\b[0-9]{4}\s?[0-9]{4}\s?[0-9]{4}\s?[0-9]{2}\b'  # DPD mit Leerzeichen
        ],
        'ups': [
            r'\b1Z[A-Z0-9]{16}\b',  # UPS Standard
        ],
        'hermes': [
            r'\b\d{16}\b',  # Hermes 16 Ziffern
        ],
        'gls': [
            r'\b\d{11}\b',  # GLS 11 Ziffern
        ],
        'fedex': [
            r'\b\d{12}\b',  # FedEx 12 Ziffern
            r'\b\d{15}\b',  # FedEx 15 Ziffern
        ]
    }

    # Datum-Patterns (verschiedene Formate)
    DATE_PATTERNS = [
        # DD.MM.YYYY
        r'\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b',
        # DD/MM/YYYY
        r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b',
        # YYYY-MM-DD (ISO)
        r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b',
        # DD. Month YYYY
        r'\b(\d{1,2})\.\s*(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s*(\d{4})\b',
    ]

    # Betrags-Patterns (Euro)
    AMOUNT_PATTERNS = [
        # €123.45 oder € 123.45
        r'€\s*(\d{1,}(?:[.,]\d{2})?)\b',
        # 123,45 € oder 123.45 EUR
        r'\b(\d{1,}[.,]\d{2})\s*(?:€|EUR|Euro)\b',
        # "Summe: 123,45" oder "Gesamt: 123,45"
        r'(?:Summe|Gesamt|Total|Betrag|Rechnungsbetrag)[\s:]*(\d{1,}[.,]\d{2})',
    ]

    # Referenznummer-Patterns
    REFERENCE_PATTERNS = [
        r'(?:Rechnung(?:s)?[-\s]?Nr\.?|Invoice[-\s]?No\.?)[\s:]*([A-Z0-9\-/]+)',
        r'(?:Kunden[-\s]?Nr\.?|Customer[-\s]?No\.?)[\s:]*([A-Z0-9\-/]+)',
        r'(?:Auftrag(?:s)?[-\s]?Nr\.?|Order[-\s]?No\.?)[\s:]*([A-Z0-9\-/]+)',
        r'(?:Liefer[-\s]?Nr\.?|Delivery[-\s]?No\.?)[\s:]*([A-Z0-9\-/]+)',
    ]

    def __init__(self, tesseract_cmd: Optional[str] = None):
        """
        Initialisiert OCR-Service

        Args:
            tesseract_cmd: Pfad zu tesseract binary (optional)
        """
        if not OCR_AVAILABLE:
            raise RuntimeError("pytesseract und PIL müssen installiert sein. Führe aus: pip install pytesseract pillow")

        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def extract_text_from_image(self, image_path: str, lang: str = 'deu') -> str:
        """
        Extrahiert Text aus einem Bild mittels OCR

        Args:
            image_path: Pfad zum Bild
            lang: Sprache für OCR (deu=Deutsch, eng=Englisch)

        Returns:
            Erkannter Text
        """
        try:
            image = Image.open(image_path)

            # Bildvorverarbeitung für bessere OCR-Ergebnisse
            # Convert to grayscale
            image = image.convert('L')

            # OCR durchführen
            text = pytesseract.image_to_string(image, lang=lang)

            return text.strip()

        except Exception as e:
            logger.error(f"OCR-Fehler bei {image_path}: {e}", exc_info=True)
            raise ValueError(f"Fehler bei Texterkennung: {e}")

    def extract_amounts(self, text: str) -> List[Decimal]:
        """
        Extrahiert Geldbeträge aus Text

        Returns:
            Liste von gefundenen Beträgen (sortiert, größter zuerst)
        """
        amounts = []

        for pattern in self.AMOUNT_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                amount_str = match.group(1)
                # Normalisiere: Komma zu Punkt
                amount_str = amount_str.replace(',', '.')
                try:
                    amount = Decimal(amount_str)
                    amounts.append(amount)
                except:
                    continue

        # Sortiere absteigend (größter Betrag zuerst)
        amounts.sort(reverse=True)
        return amounts

    def extract_dates(self, text: str) -> List[datetime]:
        """
        Extrahiert Datumsangaben aus Text

        Returns:
            Liste von gefundenen Daten
        """
        dates = []

        # Monatsnamen-Mapping
        month_map = {
            'Januar': 1, 'Februar': 2, 'März': 3, 'April': 4,
            'Mai': 5, 'Juni': 6, 'Juli': 7, 'August': 8,
            'September': 9, 'Oktober': 10, 'November': 11, 'Dezember': 12
        }

        for pattern in self.DATE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    groups = match.groups()

                    # DD.MM.YYYY oder DD/MM/YYYY
                    if len(groups) == 3 and groups[0].isdigit():
                        if len(groups[0]) <= 2:  # Tag zuerst
                            day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                        else:  # Jahr zuerst (ISO)
                            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])

                        date = datetime(year, month, day)
                        dates.append(date)

                    # DD. Monat YYYY
                    elif len(groups) == 3 and not groups[1].isdigit():
                        day = int(groups[0])
                        month_name = groups[1].capitalize()
                        month = month_map.get(month_name)
                        year = int(groups[2])

                        if month:
                            date = datetime(year, month, day)
                            dates.append(date)

                except (ValueError, TypeError):
                    continue

        return dates

    def extract_tracking_numbers(self, text: str) -> Dict[str, List[str]]:
        """
        Extrahiert Tracking-Nummern aus Text

        Returns:
            Dict mit Carrier als Key und Liste von Tracking-Nummern
        """
        tracking_numbers = {}

        for carrier, patterns in self.TRACKING_PATTERNS.items():
            found = []
            for pattern in patterns:
                matches = re.findall(pattern, text)
                found.extend(matches)

            if found:
                # Duplikate entfernen, Leerzeichen entfernen
                found = list(set([t.replace(' ', '') for t in found]))
                tracking_numbers[carrier] = found

        return tracking_numbers

    def extract_reference_numbers(self, text: str) -> Dict[str, str]:
        """
        Extrahiert Referenznummern (Rechnungs-Nr., Kunden-Nr., etc.)

        Returns:
            Dict mit Typ als Key und Nummer als Value
        """
        references = {}

        for pattern in self.REFERENCE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                ref_type = match.group(0).split(':')[0].strip()
                ref_number = match.group(1).strip()
                references[ref_type] = ref_number

        return references

    def smart_extract(self, text: str) -> Dict[str, any]:
        """
        Intelligente Extraktion aller relevanten Daten

        Args:
            text: OCR-erkannter Text

        Returns:
            Dict mit extrahierten Daten:
            {
                'amounts': [Decimal(...)],
                'dates': [datetime(...)],
                'tracking': {'dhl': [...], ...},
                'references': {'Rechnung-Nr.': '...', ...},
                'primary_amount': Decimal(...),  # Größter Betrag
                'primary_date': datetime(...),    # Neuestes Datum
            }
        """
        result = {
            'amounts': self.extract_amounts(text),
            'dates': self.extract_dates(text),
            'tracking': self.extract_tracking_numbers(text),
            'references': self.extract_reference_numbers(text),
        }

        # Primary-Werte (meistens relevant)
        if result['amounts']:
            result['primary_amount'] = float(result['amounts'][0])

        if result['dates']:
            # Neuestes Datum
            result['primary_date'] = max(result['dates']).isoformat()

        # Tracking-Nummern flach machen
        if result['tracking']:
            all_tracking = []
            for carrier, numbers in result['tracking'].items():
                all_tracking.extend(numbers)
            if all_tracking:
                result['primary_tracking'] = all_tracking[0]

        # Konvertiere datetime zu ISO-String für JSON-Speicherung
        result['dates'] = [d.isoformat() for d in result['dates']]
        result['amounts'] = [float(a) for a in result['amounts']]

        return result

    def process_document(self, image_path: str, lang: str = 'deu') -> Dict[str, any]:
        """
        Vollständige Dokumentenverarbeitung: OCR + Smart-Extraction

        Args:
            image_path: Pfad zum Dokument-Scan
            lang: Sprache für OCR

        Returns:
            Dict mit:
            {
                'text': '...',  # Volltext
                'extracted_data': {...}  # Smart-extrahierte Daten
            }
        """
        # OCR durchführen
        text = self.extract_text_from_image(image_path, lang=lang)

        # Smart-Extraction
        extracted_data = self.smart_extract(text)

        return {
            'text': text,
            'extracted_data': extracted_data
        }


# Helper-Funktion für einfache Verwendung
def process_document_image(image_path: str, lang: str = 'deu') -> Dict[str, any]:
    """
    Convenience-Funktion für Dokumentenverarbeitung

    Args:
        image_path: Pfad zum Bild
        lang: Sprache (deu, eng)

    Returns:
        Dict mit text und extracted_data
    """
    service = OCRService()
    return service.process_document(image_path, lang=lang)


__all__ = ['OCRService', 'process_document_image', 'OCR_AVAILABLE']
