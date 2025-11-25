"""
Unit Tests für PDF Service
Testet die PDF-Generierung für Rechnungen und Belege
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

# Importiere den Service
from src.services.pdf_service import PDFService, REPORTLAB_AVAILABLE


@pytest.fixture
def pdf_service():
    """Fixture für PDFService"""
    return PDFService()


@pytest.fixture
def sample_invoice_data():
    """Fixture für Beispiel-Rechnungsdaten"""
    return {
        'invoice_number': 'RE-2025-001',
        'invoice_date': date(2025, 1, 15),
        'delivery_date': date(2025, 1, 15),
        'customer_number': 'K-001',
        'subject': 'Stickerei-Auftrag',
        'sender': {
            'name': 'StitchAdmin GmbH',
            'street': 'Musterstraße 1',
            'postcode': '12345',
            'city': 'Musterstadt',
            'phone': '+49 123 456789',
            'email': 'info@stitchadmin.de',
            'tax_id': 'DE123456789'
        },
        'recipient': {
            'name': 'Max Mustermann',
            'street': 'Testweg 2',
            'postcode': '54321',
            'city': 'Teststadt'
        },
        'items': [
            {
                'description': 'T-Shirt Bestickung',
                'quantity': 10,
                'unit': 'Stk.',
                'unit_price': 15.00,
                'total': 150.00
            },
            {
                'description': 'Polo-Shirt Bestickung',
                'quantity': 5,
                'unit': 'Stk.',
                'unit_price': 20.00,
                'total': 100.00
            }
        ],
        'subtotal': 250.00,
        'discount_percent': 10,
        'discount_amount': 25.00,
        'total_net': 225.00,
        'taxes': [
            {
                'rate': 19,
                'amount': 42.75
            }
        ],
        'total_gross': 267.75,
        'payment_terms': 'Zahlbar innerhalb 14 Tagen ohne Abzug',
        'bank_details': {
            'bank_name': 'Musterbank',
            'iban': 'DE89 3704 0044 0532 0130 00',
            'bic': 'COBADEFFXXX'
        },
        'payment_reference': 'RE-2025-001',
        'footer_text': 'Vielen Dank für Ihren Auftrag!'
    }


class TestPDFServiceInit:
    """Tests für Initialisierung"""

    def test_init_creates_instance(self, pdf_service):
        """Test: Service-Instanz wird erstellt"""
        assert pdf_service is not None
        assert isinstance(pdf_service, PDFService)

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="ReportLab nicht installiert")
    def test_init_creates_styles(self, pdf_service):
        """Test: Styles werden erstellt wenn ReportLab verfügbar"""
        assert pdf_service.styles is not None

        # Prüfe benutzerdefinierte Styles
        assert 'InvoiceHeader' in pdf_service.styles
        assert 'AddressBlock' in pdf_service.styles
        assert 'TableHeader' in pdf_service.styles
        assert 'Amount' in pdf_service.styles

    def test_init_without_reportlab(self):
        """Test: Initialisierung ohne ReportLab"""
        with patch('src.services.pdf_service.REPORTLAB_AVAILABLE', False):
            service = PDFService()
            assert service.styles is None


class TestFormatHelpers:
    """Tests für Formatierungs-Hilfsmethoden"""

    def test_format_date_with_date_object(self, pdf_service):
        """Test: Datum-Formatierung mit date-Objekt"""
        test_date = date(2025, 1, 15)
        formatted = pdf_service._format_date(test_date)

        assert formatted == '15.01.2025'

    def test_format_date_with_datetime_object(self, pdf_service):
        """Test: Datum-Formatierung mit datetime-Objekt"""
        test_datetime = datetime(2025, 1, 15, 10, 30, 0)
        formatted = pdf_service._format_date(test_datetime)

        assert formatted == '15.01.2025'

    def test_format_date_with_none(self, pdf_service):
        """Test: Datum-Formatierung mit None"""
        formatted = pdf_service._format_date(None)
        assert formatted == ''

    def test_format_date_with_string(self, pdf_service):
        """Test: Datum-Formatierung mit String"""
        formatted = pdf_service._format_date('2025-01-15')
        assert formatted == '2025-01-15'  # String wird unverändert zurückgegeben

    def test_format_currency_with_float(self, pdf_service):
        """Test: Währungs-Formatierung mit Float"""
        formatted = pdf_service._format_currency(1234.56)

        # Deutsches Format: 1.234,56 €
        assert '1.234,56' in formatted
        assert '€' in formatted

    def test_format_currency_with_int(self, pdf_service):
        """Test: Währungs-Formatierung mit Integer"""
        formatted = pdf_service._format_currency(100)

        assert '100,00' in formatted
        assert '€' in formatted

    def test_format_currency_with_decimal(self, pdf_service):
        """Test: Währungs-Formatierung mit Decimal"""
        formatted = pdf_service._format_currency(Decimal('99.99'))

        assert '99,99' in formatted
        assert '€' in formatted

    def test_format_currency_with_zero(self, pdf_service):
        """Test: Währungs-Formatierung mit 0"""
        formatted = pdf_service._format_currency(0)

        assert '0,00' in formatted

    def test_format_currency_large_number(self, pdf_service):
        """Test: Währungs-Formatierung mit großer Zahl"""
        formatted = pdf_service._format_currency(1234567.89)

        # 1.234.567,89 €
        assert '1.234.567,89' in formatted

    def test_format_currency_with_string(self, pdf_service):
        """Test: Währungs-Formatierung mit String"""
        formatted = pdf_service._format_currency('invalid')
        assert formatted == 'invalid'


class TestFallbackPDF:
    """Tests für Fallback-PDF"""

    def test_create_fallback_pdf(self, pdf_service):
        """Test: Fallback-PDF erstellen"""
        pdf_bytes = pdf_service._create_fallback_pdf()

        assert pdf_bytes is not None
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

        # PDF sollte PDF-Header enthalten (strip leading whitespace)
        assert b'%PDF' in pdf_bytes[:100]  # Check first 100 bytes

    def test_fallback_pdf_contains_message(self, pdf_service):
        """Test: Fallback-PDF enthält Nachricht"""
        pdf_bytes = pdf_service._create_fallback_pdf()

        # Sollte Hinweis auf ReportLab enthalten
        assert b'ReportLab' in pdf_bytes


@pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="ReportLab nicht installiert")
class TestInvoicePDFGeneration:
    """Tests für Rechnungs-PDF-Generierung (nur wenn ReportLab verfügbar)"""

    def test_create_invoice_pdf_success(self, pdf_service, sample_invoice_data):
        """Test: Rechnungs-PDF erfolgreich erstellen"""
        pdf_bytes = pdf_service.create_invoice_pdf(sample_invoice_data)

        assert pdf_bytes is not None
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

        # PDF sollte mit PDF-Header beginnen
        assert pdf_bytes.startswith(b'%PDF')

    def test_create_invoice_pdf_minimal_data(self, pdf_service):
        """Test: PDF mit minimalen Daten"""
        minimal_data = {
            'invoice_number': 'RE-001',
            'items': [],
            'total_gross': 0
        }

        pdf_bytes = pdf_service.create_invoice_pdf(minimal_data)

        assert pdf_bytes is not None
        assert isinstance(pdf_bytes, bytes)

    def test_create_invoice_pdf_with_logo(self, pdf_service, sample_invoice_data, tmp_path):
        """Test: PDF mit Logo"""
        # Erstelle dummy Logo-Datei
        logo_path = tmp_path / "logo.png"
        logo_path.write_bytes(b'\x89PNG\r\n\x1a\n')  # PNG Header

        sample_invoice_data['logo_path'] = str(logo_path)

        # Sollte nicht crashen, auch wenn Logo invalide ist
        pdf_bytes = pdf_service.create_invoice_pdf(sample_invoice_data)
        assert pdf_bytes is not None

    def test_create_invoice_pdf_multiple_items(self, pdf_service, sample_invoice_data):
        """Test: PDF mit mehreren Positionen"""
        # Füge mehr Items hinzu
        sample_invoice_data['items'].extend([
            {
                'description': 'Hoodie Bestickung',
                'quantity': 3,
                'unit': 'Stk.',
                'unit_price': 30.00,
                'total': 90.00
            },
            {
                'description': 'Cap Bestickung',
                'quantity': 15,
                'unit': 'Stk.',
                'unit_price': 8.00,
                'total': 120.00
            }
        ])

        pdf_bytes = pdf_service.create_invoice_pdf(sample_invoice_data)
        assert pdf_bytes is not None

    def test_create_invoice_pdf_with_discount(self, pdf_service, sample_invoice_data):
        """Test: PDF mit Rabatt"""
        # Daten enthalten bereits Rabatt
        pdf_bytes = pdf_service.create_invoice_pdf(sample_invoice_data)
        assert pdf_bytes is not None

    def test_create_invoice_pdf_multiple_tax_rates(self, pdf_service, sample_invoice_data):
        """Test: PDF mit mehreren MwSt-Sätzen"""
        sample_invoice_data['taxes'] = [
            {'rate': 19, 'amount': 30.00},
            {'rate': 7, 'amount': 10.00}
        ]

        pdf_bytes = pdf_service.create_invoice_pdf(sample_invoice_data)
        assert pdf_bytes is not None


@pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="ReportLab nicht installiert")
class TestPDFSections:
    """Tests für einzelne PDF-Abschnitte"""

    def test_create_header(self, pdf_service, sample_invoice_data):
        """Test: Header-Erstellung"""
        elements = pdf_service._create_header(sample_invoice_data)

        assert isinstance(elements, list)
        assert len(elements) > 0

    def test_create_address_section(self, pdf_service, sample_invoice_data):
        """Test: Adress-Abschnitt"""
        elements = pdf_service._create_address_section(sample_invoice_data)

        assert isinstance(elements, list)
        assert len(elements) > 0

    def test_create_invoice_info(self, pdf_service, sample_invoice_data):
        """Test: Rechnungsinformationen"""
        elements = pdf_service._create_invoice_info(sample_invoice_data)

        assert isinstance(elements, list)
        assert len(elements) > 0

    def test_create_items_table(self, pdf_service, sample_invoice_data):
        """Test: Positionstabelle"""
        elements = pdf_service._create_items_table(sample_invoice_data)

        assert isinstance(elements, list)
        assert len(elements) > 0

    def test_create_items_table_empty(self, pdf_service):
        """Test: Leere Positionstabelle"""
        data = {'items': []}
        elements = pdf_service._create_items_table(data)

        assert isinstance(elements, list)

    def test_create_totals_section(self, pdf_service, sample_invoice_data):
        """Test: Summen-Abschnitt"""
        elements = pdf_service._create_totals_section(sample_invoice_data)

        assert isinstance(elements, list)
        assert len(elements) > 0

    def test_create_totals_section_minimal(self, pdf_service):
        """Test: Summen mit minimalen Daten"""
        data = {'total_gross': 100.00}
        elements = pdf_service._create_totals_section(data)

        assert isinstance(elements, list)

    def test_create_payment_terms(self, pdf_service, sample_invoice_data):
        """Test: Zahlungsbedingungen"""
        elements = pdf_service._create_payment_terms(sample_invoice_data)

        assert isinstance(elements, list)
        assert len(elements) > 0

    def test_create_payment_terms_without_bank(self, pdf_service):
        """Test: Zahlungsbedingungen ohne Bankdaten"""
        data = {'payment_terms': 'Sofort fällig'}
        elements = pdf_service._create_payment_terms(data)

        assert isinstance(elements, list)

    def test_create_footer(self, pdf_service, sample_invoice_data):
        """Test: Footer-Erstellung"""
        elements = pdf_service._create_footer(sample_invoice_data)

        assert isinstance(elements, list)
        assert len(elements) > 0

    def test_create_footer_custom_text(self, pdf_service):
        """Test: Footer mit benutzerdefiniertem Text"""
        data = {'footer_text': 'Custom Footer Text'}
        elements = pdf_service._create_footer(data)

        assert isinstance(elements, list)


class TestReceiptPDF:
    """Tests für Kassenbeleg-PDF"""

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="ReportLab nicht installiert")
    def test_create_receipt_pdf(self, pdf_service, sample_invoice_data):
        """Test: Kassenbeleg-PDF erstellen"""
        # Konvertiere zu Beleg-Daten
        receipt_data = sample_invoice_data.copy()
        receipt_data['receipt_number'] = receipt_data.pop('invoice_number')

        pdf_bytes = pdf_service.create_receipt_pdf(receipt_data)

        assert pdf_bytes is not None
        assert isinstance(pdf_bytes, bytes)


class TestErrorHandling:
    """Tests für Fehlerbehandlung"""

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="ReportLab nicht installiert")
    def test_create_invoice_pdf_with_exception(self, pdf_service, sample_invoice_data):
        """Test: PDF-Erstellung mit Exception"""
        # Mock ReportLab um Exception zu werfen
        with patch('src.services.pdf_service.SimpleDocTemplate', side_effect=Exception('Test Error')):
            pdf_bytes = pdf_service.create_invoice_pdf(sample_invoice_data)

            # Sollte Fallback-PDF zurückgeben
            assert pdf_bytes is not None
            assert isinstance(pdf_bytes, bytes)

    def test_create_invoice_without_reportlab(self, sample_invoice_data):
        """Test: PDF-Erstellung ohne ReportLab"""
        with patch('src.services.pdf_service.REPORTLAB_AVAILABLE', False):
            service = PDFService()
            pdf_bytes = service.create_invoice_pdf(sample_invoice_data)

            # Sollte Fallback-PDF zurückgeben
            assert pdf_bytes is not None
            assert b'%PDF' in pdf_bytes


class TestEdgeCases:
    """Tests für Edge Cases"""

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="ReportLab nicht installiert")
    def test_pdf_with_very_long_description(self, pdf_service):
        """Test: PDF mit sehr langen Beschreibungen"""
        data = {
            'invoice_number': 'RE-001',
            'items': [{
                'description': 'A' * 500,  # Sehr lange Beschreibung
                'quantity': 1,
                'unit': 'Stk.',
                'unit_price': 10.00,
                'total': 10.00
            }],
            'total_gross': 10.00
        }

        pdf_bytes = pdf_service.create_invoice_pdf(data)
        assert pdf_bytes is not None

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="ReportLab nicht installiert")
    def test_pdf_with_many_items(self, pdf_service):
        """Test: PDF mit vielen Positionen (mehrseitig)"""
        items = [
            {
                'description': f'Item {i}',
                'quantity': 1,
                'unit': 'Stk.',
                'unit_price': 10.00,
                'total': 10.00
            }
            for i in range(50)  # 50 Positionen
        ]

        data = {
            'invoice_number': 'RE-001',
            'items': items,
            'total_gross': 500.00
        }

        pdf_bytes = pdf_service.create_invoice_pdf(data)
        assert pdf_bytes is not None

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="ReportLab nicht installiert")
    def test_pdf_with_special_characters(self, pdf_service):
        """Test: PDF mit Sonderzeichen"""
        data = {
            'invoice_number': 'RE-001',
            'subject': 'Äöü ßẞ € @ & < >',
            'recipient': {
                'name': 'Müller-Lüdenscheid GmbH & Co. KG',
                'street': 'Straße des 17. Juni',
                'city': 'München'
            },
            'items': [{
                'description': 'T-Shirt "Premium" (Größe M)',
                'quantity': 1,
                'unit': 'Stk.',
                'unit_price': 10.00,
                'total': 10.00
            }],
            'total_gross': 10.00
        }

        pdf_bytes = pdf_service.create_invoice_pdf(data)
        assert pdf_bytes is not None

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="ReportLab nicht installiert")
    def test_pdf_with_zero_amounts(self, pdf_service):
        """Test: PDF mit Null-Beträgen"""
        data = {
            'invoice_number': 'RE-001',
            'items': [{
                'description': 'Gratis-Artikel',
                'quantity': 1,
                'unit': 'Stk.',
                'unit_price': 0.00,
                'total': 0.00
            }],
            'total_gross': 0.00
        }

        pdf_bytes = pdf_service.create_invoice_pdf(data)
        assert pdf_bytes is not None


class TestIntegration:
    """Integrationstests für PDF-Service"""

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="ReportLab nicht installiert")
    def test_full_invoice_generation_workflow(self, pdf_service, sample_invoice_data):
        """Test: Vollständiger Workflow für Rechnungs-PDF"""
        # 1. PDF generieren
        pdf_bytes = pdf_service.create_invoice_pdf(sample_invoice_data)

        assert pdf_bytes is not None
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000  # Sollte eine sinnvolle Größe haben

        # 2. PDF sollte gültig sein (Header check)
        assert pdf_bytes.startswith(b'%PDF')

        # 3. PDF sollte Footer haben (EOF marker)
        assert b'%%EOF' in pdf_bytes
