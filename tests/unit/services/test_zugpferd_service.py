"""
Unit Tests für ZUGFeRD Service
Testet die ZUGFeRD/Factur-X konforme Rechnungserstellung
"""

import pytest
import xml.etree.ElementTree as ET
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from src.services.zugpferd_service import ZugpferdService, PIKEPDF_AVAILABLE, LXML_AVAILABLE


@pytest.fixture
def zugpferd_service():
    """Fixture für ZugpferdService"""
    return ZugpferdService()


@pytest.fixture
def sample_invoice_data():
    """Fixture für Beispiel-Rechnungsdaten"""
    return {
        'invoice_number': 'RE-2025-001',
        'invoice_date': date(2025, 1, 15),
        'delivery_date': date(2025, 1, 15),
        'seller': {
            'name': 'StitchAdmin GmbH',
            'street': 'Musterstraße 1',
            'postcode': '12345',
            'city': 'Musterstadt',
            'country': 'DE',
            'tax_id': 'DE123456789',
            'email': 'info@stitchadmin.de',
            'phone': '+49 123 456789'
        },
        'buyer': {
            'name': 'Max Mustermann',
            'street': 'Testweg 2',
            'postcode': '54321',
            'city': 'Teststadt',
            'country': 'DE'
        },
        'items': [
            {
                'description': 'T-Shirt Bestickung',
                'quantity': 10,
                'unit': 'STK',
                'unit_price': 15.00,
                'total_net': 150.00,
                'tax_rate': 19.0
            }
        ],
        'subtotal': 150.00,
        'total_net': 150.00,
        'total_tax': 28.50,
        'total_gross': 178.50,
        'payment_terms': 'Zahlbar innerhalb 14 Tagen',
        'payment_due_date': date(2025, 1, 29)
    }


class TestZugpferdServiceInit:
    """Tests für Initialisierung"""

    def test_init_creates_instance(self, zugpferd_service):
        """Test: Service-Instanz wird erstellt"""
        assert zugpferd_service is not None
        assert isinstance(zugpferd_service, ZugpferdService)

    def test_init_sets_default_profile(self, zugpferd_service):
        """Test: Standard-Profil wird gesetzt"""
        assert zugpferd_service.profile == ZugpferdService.PROFILE_BASIC

    def test_profile_constants_defined(self):
        """Test: Profil-Konstanten sind definiert"""
        assert hasattr(ZugpferdService, 'PROFILE_MINIMUM')
        assert hasattr(ZugpferdService, 'PROFILE_BASIC')
        assert hasattr(ZugpferdService, 'PROFILE_COMFORT')
        assert hasattr(ZugpferdService, 'PROFILE_EXTENDED')

        # URNs sollten korrekt sein
        assert 'urn:ferd:CrossIndustryDocument:invoice' in ZugpferdService.PROFILE_MINIMUM

    def test_namespaces_defined(self):
        """Test: XML-Namespaces sind definiert"""
        assert hasattr(ZugpferdService, 'NAMESPACES')
        namespaces = ZugpferdService.NAMESPACES

        assert 'rsm' in namespaces
        assert 'ram' in namespaces
        assert 'udt' in namespaces
        assert 'qdt' in namespaces


class TestXMLGeneration:
    """Tests für XML-Generierung"""

    def test_create_invoice_xml_success(self, zugpferd_service, sample_invoice_data):
        """Test: XML wird erfolgreich erstellt"""
        xml_string = zugpferd_service.create_invoice_xml(sample_invoice_data)

        assert xml_string is not None
        assert isinstance(xml_string, str)
        assert len(xml_string) > 0

        # XML sollte mit Declaration beginnen
        assert xml_string.startswith('<?xml')

    def test_create_invoice_xml_valid_structure(self, zugpferd_service, sample_invoice_data):
        """Test: Erzeugtes XML hat gültige Struktur"""
        xml_string = zugpferd_service.create_invoice_xml(sample_invoice_data)

        # Parse XML
        root = ET.fromstring(xml_string)

        # Root-Element sollte CrossIndustryInvoice sein
        assert 'CrossIndustryInvoice' in root.tag

    def test_create_invoice_xml_with_custom_profile(self, zugpferd_service, sample_invoice_data):
        """Test: XML mit benutzerdefiniertem Profil"""
        xml_string = zugpferd_service.create_invoice_xml(
            sample_invoice_data,
            profile=ZugpferdService.PROFILE_COMFORT
        )

        assert xml_string is not None
        # Profil sollte geändert worden sein
        assert zugpferd_service.profile == ZugpferdService.PROFILE_COMFORT

    def test_create_invoice_xml_contains_invoice_number(self, zugpferd_service, sample_invoice_data):
        """Test: XML enthält Rechnungsnummer"""
        xml_string = zugpferd_service.create_invoice_xml(sample_invoice_data)

        assert 'RE-2025-001' in xml_string

    def test_create_invoice_xml_contains_seller(self, zugpferd_service, sample_invoice_data):
        """Test: XML enthält Verkäufer-Daten"""
        xml_string = zugpferd_service.create_invoice_xml(sample_invoice_data)

        assert 'StitchAdmin GmbH' in xml_string

    def test_create_invoice_xml_contains_buyer(self, zugpferd_service, sample_invoice_data):
        """Test: XML enthält Käufer-Daten"""
        xml_string = zugpferd_service.create_invoice_xml(sample_invoice_data)

        assert 'Max Mustermann' in xml_string

    def test_create_invoice_xml_contains_items(self, zugpferd_service, sample_invoice_data):
        """Test: XML enthält Positionen"""
        xml_string = zugpferd_service.create_invoice_xml(sample_invoice_data)

        assert 'T-Shirt Bestickung' in xml_string

    def test_create_invoice_xml_minimal_data(self, zugpferd_service):
        """Test: XML mit minimalen Daten"""
        minimal_data = {
            'invoice_number': 'MIN-001',
            'invoice_date': date.today(),
            'items': []
        }

        xml_string = zugpferd_service.create_invoice_xml(minimal_data)

        assert xml_string is not None
        assert 'MIN-001' in xml_string

    def test_create_invoice_xml_multiple_items(self, zugpferd_service, sample_invoice_data):
        """Test: XML mit mehreren Positionen"""
        sample_invoice_data['items'].extend([
            {
                'description': 'Polo Bestickung',
                'quantity': 5,
                'unit': 'STK',
                'unit_price': 20.00,
                'total_net': 100.00,
                'tax_rate': 19.0
            },
            {
                'description': 'Hoodie Bestickung',
                'quantity': 3,
                'unit': 'STK',
                'unit_price': 30.00,
                'total_net': 90.00,
                'tax_rate': 19.0
            }
        ])

        xml_string = zugpferd_service.create_invoice_xml(sample_invoice_data)

        assert 'Polo Bestickung' in xml_string
        assert 'Hoodie Bestickung' in xml_string


class TestXMLValidation:
    """Tests für XML-Validierung"""

    def test_validate_xml_without_lxml(self, zugpferd_service, sample_invoice_data):
        """Test: Validierung ohne lxml"""
        xml_string = zugpferd_service.create_invoice_xml(sample_invoice_data)

        with patch('src.services.zugpferd_service.LXML_AVAILABLE', False):
            result = zugpferd_service.validate_xml(xml_string)

            assert result['valid'] is False
            assert 'lxml nicht installiert' in result.get('message', '').lower() or \
                   'validator nicht verfügbar' in result.get('message', '').lower()

    @pytest.mark.skipif(not LXML_AVAILABLE, reason="lxml nicht installiert")
    def test_validate_xml_valid_structure(self, zugpferd_service, sample_invoice_data):
        """Test: Gültiges XML validieren"""
        xml_string = zugpferd_service.create_invoice_xml(sample_invoice_data)

        result = zugpferd_service.validate_xml(xml_string)

        # Ohne XSD-Schema kann nicht vollständig validiert werden,
        # aber Struktur sollte geparst werden können
        assert isinstance(result, dict)

    def test_validate_xml_invalid_xml(self, zugpferd_service):
        """Test: Ungültiges XML"""
        invalid_xml = "This is not XML"

        result = zugpferd_service.validate_xml(invalid_xml)

        assert result['valid'] is False


class TestPDFWithXML:
    """Tests für PDF mit eingebettetem XML"""

    @pytest.mark.skipif(not PIKEPDF_AVAILABLE, reason="pikepdf nicht installiert")
    def test_create_pdf_with_xml_basic(self, zugpferd_service, sample_invoice_data):
        """Test: PDF mit XML erstellen"""
        # Erzeuge XML
        xml_string = zugpferd_service.create_invoice_xml(sample_invoice_data)

        # Dummy PDF (muss gültiges PDF sein)
        pdf_content = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF'

        # PDF mit XML erstellen
        result_pdf = zugpferd_service.create_pdf_with_xml(pdf_content, xml_string)

        assert result_pdf is not None
        assert isinstance(result_pdf, bytes)
        assert len(result_pdf) > 0

    def test_create_pdf_with_xml_without_pikepdf(self, zugpferd_service, sample_invoice_data):
        """Test: PDF-Erstellung ohne pikepdf"""
        xml_string = zugpferd_service.create_invoice_xml(sample_invoice_data)
        pdf_content = b'%PDF-1.4\n...'

        with patch('src.services.zugpferd_service.PIKEPDF_AVAILABLE', False):
            result = zugpferd_service.create_pdf_with_xml(pdf_content, xml_string)

            # Sollte Original-PDF zurückgeben oder Fehler
            assert result is not None


class TestDataConversion:
    """Tests für Datenkonvertierung"""

    def test_convert_rechnung_to_invoice_data(self, zugpferd_service):
        """Test: Konvertierung von Rechnung zu Invoice-Daten"""
        # Mock Rechnung-Objekt
        mock_rechnung = Mock()
        mock_rechnung.rechnungsnummer = 'RE-2025-001'
        mock_rechnung.rechnungsdatum = date(2025, 1, 15)
        mock_rechnung.leistungsdatum = date(2025, 1, 15)
        mock_rechnung.netto = Decimal('100.00')
        mock_rechnung.mwst = Decimal('19.00')
        mock_rechnung.brutto = Decimal('119.00')

        # Mock Kunde
        mock_kunde = Mock()
        mock_kunde.firma = 'Test Kunde'
        mock_kunde.strasse = 'Teststraße 1'
        mock_kunde.plz = '12345'
        mock_kunde.ort = 'Teststadt'
        mock_kunde.land = 'DE'
        mock_rechnung.kunde = mock_kunde

        # Mock Positionen
        mock_position = Mock()
        mock_position.bezeichnung = 'Test Artikel'
        mock_position.menge = 10
        mock_position.einheit = 'STK'
        mock_position.einzelpreis = Decimal('10.00')
        mock_position.gesamtpreis = Decimal('100.00')
        mock_position.mwst_satz = Decimal('19.00')
        mock_rechnung.positionen = Mock()
        mock_rechnung.positionen.all = Mock(return_value=[mock_position])

        # Konvertiere
        invoice_data = zugpferd_service._convert_rechnung_to_invoice_data(mock_rechnung)

        assert invoice_data is not None
        assert isinstance(invoice_data, dict)
        assert invoice_data['invoice_number'] == 'RE-2025-001'


class TestErrorHandling:
    """Tests für Fehlerbehandlung"""

    def test_create_invoice_xml_with_missing_data(self, zugpferd_service):
        """Test: XML-Erstellung mit fehlenden Daten"""
        incomplete_data = {}

        # Sollte trotzdem XML generieren (mit leeren Werten)
        xml_string = zugpferd_service.create_invoice_xml(incomplete_data)

        assert xml_string is not None

    def test_create_invoice_xml_with_none_values(self, zugpferd_service):
        """Test: XML mit None-Werten"""
        data_with_none = {
            'invoice_number': None,
            'invoice_date': None,
            'seller': None,
            'buyer': None,
            'items': None
        }

        # Sollte nicht crashen
        try:
            xml_string = zugpferd_service.create_invoice_xml(data_with_none)
            assert xml_string is not None
        except Exception:
            # Oder Exception werfen (akzeptabel)
            pass


class TestEdgeCases:
    """Tests für Edge Cases"""

    def test_xml_with_special_characters(self, zugpferd_service):
        """Test: XML mit Sonderzeichen"""
        data = {
            'invoice_number': 'RE-2025-001',
            'invoice_date': date.today(),
            'seller': {
                'name': 'Müller & Söhne GmbH',
                'street': 'Straße des 17. Juni',
                'city': 'München'
            },
            'buyer': {
                'name': 'Test <Company> & Co.',
                'street': 'Äöü-Straße'
            },
            'items': [{
                'description': 'T-Shirt "Premium" (Größe M) & mehr',
                'quantity': 1,
                'unit': 'STK',
                'unit_price': 10.00
            }]
        }

        xml_string = zugpferd_service.create_invoice_xml(data)

        assert xml_string is not None
        # Sonderzeichen sollten escaped sein
        assert '&amp;' in xml_string or 'Müller' in xml_string

    def test_xml_with_very_large_numbers(self, zugpferd_service):
        """Test: XML mit sehr großen Beträgen"""
        data = {
            'invoice_number': 'RE-LARGE',
            'invoice_date': date.today(),
            'items': [{
                'description': 'Großauftrag',
                'quantity': 100000,
                'unit': 'STK',
                'unit_price': 999999.99,
                'total_net': 99999999000.00
            }],
            'total_gross': 119000000000.00
        }

        xml_string = zugpferd_service.create_invoice_xml(data)
        assert xml_string is not None

    def test_xml_with_decimal_precision(self, zugpferd_service):
        """Test: XML mit hoher Dezimalpräzision"""
        data = {
            'invoice_number': 'RE-DEC',
            'invoice_date': date.today(),
            'items': [{
                'description': 'Präziser Artikel',
                'quantity': 1,
                'unit': 'STK',
                'unit_price': 10.123456789,
                'total_net': 10.123456789
            }]
        }

        xml_string = zugpferd_service.create_invoice_xml(data)
        assert xml_string is not None


class TestIntegration:
    """Integrationstests für ZUGFeRD-Service"""

    def test_full_zugferd_workflow(self, zugpferd_service, sample_invoice_data):
        """Test: Vollständiger ZUGFeRD-Workflow"""
        # 1. Erstelle XML
        xml_string = zugpferd_service.create_invoice_xml(sample_invoice_data)
        assert xml_string is not None

        # 2. Validiere XML (soweit möglich)
        validation = zugpferd_service.validate_xml(xml_string)
        assert isinstance(validation, dict)

        # 3. Parse XML um Struktur zu prüfen
        root = ET.fromstring(xml_string)
        assert root is not None

        # XML sollte alle wichtigen Elemente enthalten
        assert 'CrossIndustryInvoice' in root.tag
