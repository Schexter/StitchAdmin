# -*- coding: utf-8 -*-
"""
QR-Code Service für Zahlungs-QR-Codes
======================================

Erstellt von: StitchAdmin
Zweck: Generierung von GiroCode/EPC QR-Codes für SEPA-Überweisungen

Features:
- GiroCode (EPC QR Code) nach EPC069-12 Standard
- SEPA-Überweisungen
- Unterstützung für strukturierte Referenzen
"""

import io
import logging
from typing import Optional, Dict, Any
from decimal import Decimal

# QR Code Library
try:
    import qrcode
    from qrcode.image.pil import PilImage
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False

logger = logging.getLogger(__name__)


class QRCodeService:
    """Service für Zahlungs-QR-Codes"""

    # EPC QR Code Version
    EPC_VERSION = "BCD"  # BCD = Binary Coded Data
    EPC_ENCODING = "1"   # 1 = UTF-8
    EPC_IDENTIFICATION = "SCT"  # SCT = SEPA Credit Transfer

    def __init__(self):
        """Initialisiere QR Code Service"""
        if not QRCODE_AVAILABLE:
            logger.warning("qrcode library nicht installiert. Bitte installieren: pip install qrcode[pil]")

    def create_girocode(
        self,
        beneficiary_name: str,
        iban: str,
        amount: Optional[Decimal] = None,
        purpose: Optional[str] = None,
        reference: Optional[str] = None,
        bic: Optional[str] = None,
        beneficiary_info: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Erstelle GiroCode (EPC QR Code) für SEPA-Überweisung

        Args:
            beneficiary_name: Name des Zahlungsempfängers (max 70 Zeichen)
            iban: IBAN des Empfängers
            amount: Betrag in EUR (optional, max 999999999.99)
            purpose: Verwendungszweck (optional, max 140 Zeichen)
            reference: Strukturierte Referenz (optional)
            bic: BIC des Empfängers (optional, kann leer sein für SEPA)
            beneficiary_info: Zusätzliche Empfänger-Info (optional)

        Returns:
            PNG-Bild als Bytes oder None bei Fehler
        """
        if not QRCODE_AVAILABLE:
            logger.error("qrcode library nicht verfügbar")
            return None

        try:
            # IBAN formatieren (nur Großbuchstaben, keine Leerzeichen)
            iban_clean = iban.replace(' ', '').upper()

            # BIC formatieren (optional)
            bic_clean = bic.replace(' ', '').upper() if bic else ''

            # Betrag formatieren (EUR mit 2 Dezimalstellen)
            amount_str = ''
            if amount is not None:
                amount_str = f"EUR{float(amount):.2f}"

            # GiroCode Datenstruktur nach EPC069-12
            # Format: Zeilen getrennt durch \n
            girocode_data = [
                self.EPC_VERSION,           # Service Tag (BCD)
                self.EPC_ENCODING,          # Version (1 = UTF-8)
                "1",                        # Character Set (1 = UTF-8)
                self.EPC_IDENTIFICATION,    # Identification (SCT)
                bic_clean,                  # BIC (kann leer sein)
                beneficiary_name[:70],      # Beneficiary Name (max 70 Zeichen)
                iban_clean,                 # Beneficiary Account (IBAN)
                amount_str,                 # Amount (EUR123.45 oder leer)
                purpose or '',              # Purpose (optional, max 4 Zeichen Code)
                reference or '',            # Structured Reference (optional)
                beneficiary_info or '',     # Remittance Information (Verwendungszweck, max 140 Zeichen)
                ''                          # Beneficiary to Originator Information (optional)
            ]

            # Zusammenbauen
            girocode_string = '\n'.join(girocode_data)

            # QR Code generieren
            qr = qrcode.QRCode(
                version=None,  # Automatisch
                error_correction=qrcode.constants.ERROR_CORRECT_M,  # Mittlere Fehlerkorrektur
                box_size=10,
                border=4,
            )
            qr.add_data(girocode_string)
            qr.make(fit=True)

            # Als PIL-Bild erstellen
            img = qr.make_image(fill_color="black", back_color="white")

            # In Bytes umwandeln (PNG)
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)

            logger.info(f"GiroCode QR-Code erfolgreich erstellt: {beneficiary_name}, {iban_clean}, {amount_str}")
            return img_buffer.getvalue()

        except Exception as e:
            logger.error(f"Fehler bei GiroCode-Generierung: {str(e)}")
            return None

    def create_payment_qr_for_invoice(self, rechnung, company_settings) -> Optional[bytes]:
        """
        Erstelle Zahlungs-QR-Code für eine Rechnung

        Args:
            rechnung: Rechnung Model-Instanz
            company_settings: CompanySettings Model-Instanz

        Returns:
            PNG-Bild als Bytes oder None bei Fehler
        """
        if not company_settings.iban:
            logger.warning("Keine IBAN in den Firmeneinstellungen hinterlegt")
            return None

        try:
            return self.create_girocode(
                beneficiary_name=company_settings.display_name,
                iban=company_settings.iban,
                amount=rechnung.brutto_gesamt,
                purpose='',  # Kann z.B. 'GDDS' für Waren/Dienstleistungen sein
                reference=rechnung.rechnungsnummer,  # Strukturierte Referenz
                bic=company_settings.bic,
                beneficiary_info=f"Rechnung {rechnung.rechnungsnummer}"
            )
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Zahlungs-QR-Codes: {str(e)}")
            return None

    def validate_iban(self, iban: str) -> bool:
        """
        Validiere IBAN (einfache Prüfung)

        Args:
            iban: IBAN-String

        Returns:
            True wenn gültig, sonst False
        """
        # IBAN bereinigen
        iban_clean = iban.replace(' ', '').upper()

        # Mindestlänge prüfen
        if len(iban_clean) < 15 or len(iban_clean) > 34:
            return False

        # Format prüfen (2 Buchstaben + 2 Ziffern + Rest)
        if not (iban_clean[:2].isalpha() and iban_clean[2:4].isdigit()):
            return False

        # Modulo-97 Prüfsumme (vereinfacht)
        # Für vollständige Validierung würde man alle Buchstaben in Zahlen umwandeln
        # und Modulo 97 rechnen - hier nur Basis-Check

        return True


# Singleton-Instanz
qrcode_service = QRCodeService()
