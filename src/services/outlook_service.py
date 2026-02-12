# -*- coding: utf-8 -*-
"""
Outlook Integration Service
StitchAdmin 2.0
Erstellt von Hans Hahn - Alle Rechte vorbehalten

Nutzt das lokale Outlook für E-Mail-Versand.
Vorteile:
- Keine SMTP-Konfiguration nötig
- Nutzt bereits eingerichtete E-Mail-Signatur
- E-Mails erscheinen im "Gesendet"-Ordner
- Funktioniert mit Exchange/Microsoft 365
"""

import os
import logging
import tempfile
from typing import Optional, List

logger = logging.getLogger(__name__)

# Windows COM nur auf Windows verfügbar
try:
    import win32com.client
    import pythoncom
    OUTLOOK_AVAILABLE = True
except ImportError:
    OUTLOOK_AVAILABLE = False
    pythoncom = None
    logger.warning("win32com nicht verfügbar - Outlook-Integration deaktiviert")


class OutlookService:
    """
    Service für E-Mail-Versand über lokales Outlook
    """

    def __init__(self):
        self.outlook = None
        self._connected = False

    @staticmethod
    def is_available() -> bool:
        """Prüft ob Outlook-Integration verfügbar ist"""
        if not OUTLOOK_AVAILABLE:
            print("[OUTLOOK] win32com nicht verfuegbar")
            return False

        try:
            # COM initialisieren (wichtig fuer Threads!)
            pythoncom.CoInitialize()
            print("[OUTLOOK] Versuche Outlook.Application zu erstellen...")
            outlook = win32com.client.Dispatch("Outlook.Application")
            result = outlook is not None
            print(f"[OUTLOOK] Outlook.Application erstellt: {result}")
            return result
        except Exception as e:
            print(f"[OUTLOOK] Fehler beim Erstellen von Outlook.Application: {e}")
            logger.debug(f"Outlook nicht verfügbar: {e}")
            return False

    def connect(self) -> bool:
        """Verbindet mit Outlook"""
        if not OUTLOOK_AVAILABLE:
            logger.error("win32com nicht installiert")
            return False

        try:
            # COM initialisieren (wichtig fuer Threads!)
            pythoncom.CoInitialize()
            self.outlook = win32com.client.Dispatch("Outlook.Application")
            self._connected = True
            logger.info("Outlook-Verbindung hergestellt")
            return True
        except Exception as e:
            logger.error(f"Outlook-Verbindung fehlgeschlagen: {e}")
            self._connected = False
            return False

    def create_email(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: Optional[List[str]] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        html_body: bool = False,
        display_first: bool = True
    ) -> bool:
        """
        Erstellt eine neue E-Mail in Outlook

        Args:
            to: Empfänger E-Mail-Adresse(n), mehrere mit ; getrennt
            subject: Betreff
            body: Nachrichtentext (Plain Text oder HTML)
            attachments: Liste von Dateipfaden für Anhänge
            cc: CC-Empfänger
            bcc: BCC-Empfänger
            html_body: Ob body HTML ist
            display_first: True = E-Mail anzeigen, False = direkt senden

        Returns:
            True bei Erfolg
        """
        if not self._connected:
            if not self.connect():
                return False

        try:
            # Neue E-Mail erstellen (olMailItem = 0)
            mail = self.outlook.CreateItem(0)

            # Empfänger
            mail.To = to
            if cc:
                mail.CC = cc
            if bcc:
                mail.BCC = bcc

            # Betreff
            mail.Subject = subject

            # Body (mit Signatur)
            if html_body:
                # Bei HTML: Signatur wird automatisch angehängt
                mail.HTMLBody = body + mail.HTMLBody  # Signatur ist bereits in HTMLBody
            else:
                # Bei Plain Text
                mail.Body = body

            # Anhänge hinzufügen
            if attachments:
                for attachment_path in attachments:
                    if os.path.exists(attachment_path):
                        mail.Attachments.Add(attachment_path)
                        logger.debug(f"Anhang hinzugefügt: {attachment_path}")
                    else:
                        logger.warning(f"Anhang nicht gefunden: {attachment_path}")

            # E-Mail anzeigen oder direkt senden
            if display_first:
                mail.Display()  # Öffnet Outlook-Fenster
                logger.info(f"E-Mail-Entwurf erstellt: {subject}")
            else:
                mail.Send()
                logger.info(f"E-Mail gesendet an: {to}")

            return True

        except Exception as e:
            logger.error(f"Fehler beim Erstellen der E-Mail: {e}")
            return False

    def send_invoice_email(
        self,
        to: str,
        invoice_number: str,
        customer_name: str,
        amount: float,
        pdf_path: str,
        due_date: Optional[str] = None,
        display_first: bool = True
    ) -> bool:
        """
        Versendet eine Rechnung per E-Mail

        Args:
            to: Empfänger E-Mail
            invoice_number: Rechnungsnummer
            customer_name: Kundenname
            amount: Rechnungsbetrag
            pdf_path: Pfad zur PDF-Datei
            due_date: Fälligkeitsdatum (optional)
            display_first: True = Anzeigen, False = Direkt senden

        Returns:
            True bei Erfolg
        """
        subject = f"Rechnung {invoice_number}"

        # HTML-Body für professionelles Aussehen
        body = f"""
<html>
<body style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
<p>Sehr geehrte Damen und Herren,</p>

<p>anbei erhalten Sie unsere Rechnung <strong>{invoice_number}</strong> über <strong>{amount:,.2f} €</strong>.</p>

{"<p>Fälligkeitsdatum: <strong>" + due_date + "</strong></p>" if due_date else ""}

<p>Bei Fragen stehen wir Ihnen gerne zur Verfügung.</p>

<p>Mit freundlichen Grüßen</p>
</body>
</html>
"""

        return self.create_email(
            to=to,
            subject=subject,
            body=body,
            attachments=[pdf_path] if pdf_path else None,
            html_body=True,
            display_first=display_first
        )

    def send_reminder_email(
        self,
        to: str,
        invoice_number: str,
        customer_name: str,
        amount: float,
        original_due_date: str,
        days_overdue: int,
        reminder_level: int = 1,
        display_first: bool = True
    ) -> bool:
        """
        Versendet eine Zahlungserinnerung

        Args:
            to: Empfänger E-Mail
            invoice_number: Rechnungsnummer
            customer_name: Kundenname
            amount: Offener Betrag
            original_due_date: Ursprüngliches Fälligkeitsdatum
            days_overdue: Tage überfällig
            reminder_level: 1 = Erinnerung, 2 = Mahnung, 3 = Letzte Mahnung
            display_first: True = Anzeigen, False = Direkt senden

        Returns:
            True bei Erfolg
        """
        # Betreff je nach Mahnstufe
        if reminder_level == 1:
            subject = f"Zahlungserinnerung - Rechnung {invoice_number}"
            intro = "wir möchten Sie freundlich daran erinnern, dass die folgende Rechnung noch offen ist:"
        elif reminder_level == 2:
            subject = f"Mahnung - Rechnung {invoice_number}"
            intro = "leider ist die folgende Rechnung trotz Fälligkeit noch nicht beglichen worden:"
        else:
            subject = f"Letzte Mahnung - Rechnung {invoice_number}"
            intro = "trotz unserer bisherigen Erinnerungen steht die folgende Rechnung noch aus:"

        body = f"""
<html>
<body style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
<p>Sehr geehrte Damen und Herren,</p>

<p>{intro}</p>

<table style="border-collapse: collapse; margin: 20px 0;">
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Rechnungsnummer:</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{invoice_number}</td>
    </tr>
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Offener Betrag:</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>{amount:,.2f} €</strong></td>
    </tr>
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Fällig seit:</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{original_due_date} ({days_overdue} Tage)</td>
    </tr>
</table>

<p>Wir bitten Sie, den offenen Betrag zeitnah zu überweisen.</p>

<p>Sollte sich diese E-Mail mit Ihrer Zahlung überschneiden, bitten wir Sie, diese Nachricht als gegenstandslos zu betrachten.</p>

<p>Mit freundlichen Grüßen</p>
</body>
</html>
"""

        return self.create_email(
            to=to,
            subject=subject,
            body=body,
            html_body=True,
            display_first=display_first
        )

    def get_default_account_email(self) -> Optional[str]:
        """
        Gibt die E-Mail-Adresse des Standard-Outlook-Kontos zurück

        Returns:
            E-Mail-Adresse oder None
        """
        if not self._connected:
            if not self.connect():
                return None

        try:
            namespace = self.outlook.GetNamespace("MAPI")
            accounts = namespace.Accounts

            if accounts.Count > 0:
                # Erstes Konto (Standard)
                return accounts.Item(1).SmtpAddress

            return None

        except Exception as e:
            logger.error(f"Fehler beim Abrufen des E-Mail-Kontos: {e}")
            return None

    def list_accounts(self) -> List[dict]:
        """
        Listet alle verfügbaren Outlook-Konten

        Returns:
            Liste von {name, email} Dictionaries
        """
        if not self._connected:
            if not self.connect():
                return []

        try:
            namespace = self.outlook.GetNamespace("MAPI")
            accounts = namespace.Accounts

            result = []
            for i in range(1, accounts.Count + 1):
                account = accounts.Item(i)
                result.append({
                    'name': account.DisplayName,
                    'email': account.SmtpAddress
                })

            return result

        except Exception as e:
            logger.error(f"Fehler beim Auflisten der Konten: {e}")
            return []


# Singleton-Instanz
_outlook_service = None

def get_outlook_service() -> OutlookService:
    """Gibt Singleton-Instanz des OutlookService zurück"""
    global _outlook_service
    if _outlook_service is None:
        _outlook_service = OutlookService()
    return _outlook_service
