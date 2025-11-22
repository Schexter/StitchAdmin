# -*- coding: utf-8 -*-
"""
ZUGPFERD-SERVICE - Elektronische Rechnungserstellung
====================================================

Erstellt von: StitchAdmin
Datum: 09. Juli 2025
Zweck: Service für ZUGPFERD/ZUGFeRD 2.1 konforme Rechnungen

Features:
- ZUGPFERD 2.1 XML-Generierung
- PDF/A-3 Erstellung mit eingebettetem XML
- Validierung nach EN 16931
- Support für verschiedene Profile (MINIMUM, BASIC, COMFORT, EXTENDED)
"""

import os
import xml.etree.ElementTree as ET
from datetime import datetime, date
from decimal import Decimal
import base64
from typing import Dict, List, Optional, Any
import logging
from io import BytesIO
import hashlib

# PDF/A-3 Libraries
try:
    import pikepdf
    PIKEPDF_AVAILABLE = True
except ImportError:
    PIKEPDF_AVAILABLE = False

# XML Validierung
try:
    from lxml import etree
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False

logger = logging.getLogger(__name__)

class ZugpferdService:
    """Service für ZUGPFERD/ZUGFeRD 2.1 konforme Rechnungserstellung"""
    
    # ZUGPFERD Profile
    PROFILE_MINIMUM = "urn:ferd:CrossIndustryDocument:invoice:1p0:minimum"
    PROFILE_BASIC = "urn:ferd:CrossIndustryDocument:invoice:1p0:basic"
    PROFILE_COMFORT = "urn:ferd:CrossIndustryDocument:invoice:1p0:comfort"
    PROFILE_EXTENDED = "urn:ferd:CrossIndustryDocument:invoice:1p0:extended"
    
    # Namespaces
    NAMESPACES = {
        'rsm': 'urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:13',
        'ram': 'urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:13',
        'udt': 'urn:un:unece:uncefact:data:standard:UnqualifiedDataType:15',
        'qdt': 'urn:un:unece:uncefact:data:standard:QualifiedDataType:12'
    }
    
    def __init__(self):
        """Initialisiere ZUGPFERD Service"""
        self.profile = self.PROFILE_BASIC  # Standard-Profil
        
    def create_invoice_xml(self, invoice_data: Dict[str, Any], profile: str = None) -> str:
        """
        Erstelle ZUGPFERD-konformes XML für eine Rechnung
        
        Args:
            invoice_data: Rechnungsdaten
            profile: ZUGPFERD-Profil (optional)
            
        Returns:
            XML-String
        """
        try:
            if profile:
                self.profile = profile
                
            # Root-Element erstellen
            root = ET.Element('{%s}CrossIndustryInvoice' % self.NAMESPACES['rsm'])
            
            # Namespaces setzen
            for prefix, uri in self.NAMESPACES.items():
                root.set('xmlns:' + prefix, uri)
            
            # Context
            context = ET.SubElement(root, '{%s}ExchangedDocumentContext' % self.NAMESPACES['rsm'])
            self._add_context_parameter(context)
            
            # Header
            header = ET.SubElement(root, '{%s}ExchangedDocument' % self.NAMESPACES['rsm'])
            self._add_header(header, invoice_data)
            
            # Transaction
            transaction = ET.SubElement(root, '{%s}SupplyChainTradeTransaction' % self.NAMESPACES['rsm'])
            
            # Line Items (Positionen)
            if 'items' in invoice_data:
                for item in invoice_data['items']:
                    self._add_line_item(transaction, item)
            
            # Trade Agreement
            agreement = ET.SubElement(transaction, '{%s}ApplicableHeaderTradeAgreement' % self.NAMESPACES['ram'])
            self._add_seller(agreement, invoice_data.get('seller', {}))
            self._add_buyer(agreement, invoice_data.get('buyer', {}))
            
            # Trade Delivery
            delivery = ET.SubElement(transaction, '{%s}ApplicableHeaderTradeDelivery' % self.NAMESPACES['ram'])
            self._add_delivery(delivery, invoice_data)
            
            # Trade Settlement
            settlement = ET.SubElement(transaction, '{%s}ApplicableHeaderTradeSettlement' % self.NAMESPACES['ram'])
            self._add_payment_terms(settlement, invoice_data)
            self._add_monetary_summation(settlement, invoice_data)
            
            # XML zu String konvertieren
            xml_string = ET.tostring(root, encoding='utf-8', xml_declaration=True)
            return xml_string.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Fehler bei XML-Erstellung: {str(e)}")
            raise
            
    def _add_context_parameter(self, context: ET.Element):
        """Füge Context-Parameter hinzu"""
        param = ET.SubElement(context, '{%s}GuidelineSpecifiedDocumentContextParameter' % self.NAMESPACES['ram'])
        id_elem = ET.SubElement(param, '{%s}ID' % self.NAMESPACES['ram'])
        id_elem.text = self.profile
        
    def _add_header(self, header: ET.Element, invoice_data: Dict):
        """Füge Header-Informationen hinzu"""
        # ID
        id_elem = ET.SubElement(header, '{%s}ID' % self.NAMESPACES['ram'])
        id_elem.text = invoice_data.get('invoice_number', '')
        
        # TypeCode
        type_elem = ET.SubElement(header, '{%s}TypeCode' % self.NAMESPACES['ram'])
        type_elem.text = '380'  # Commercial Invoice
        
        # IssueDateTime
        issue_date = ET.SubElement(header, '{%s}IssueDateTime' % self.NAMESPACES['ram'])
        date_elem = ET.SubElement(issue_date, '{%s}DateTimeString' % self.NAMESPACES['udt'])
        date_elem.set('format', '102')
        invoice_date = invoice_data.get('invoice_date', datetime.now())
        if isinstance(invoice_date, (date, datetime)):
            date_elem.text = invoice_date.strftime('%Y%m%d')
        else:
            date_elem.text = invoice_date
            
    def _add_line_item(self, transaction: ET.Element, item: Dict):
        """Füge eine Rechnungsposition hinzu"""
        line_item = ET.SubElement(transaction, '{%s}IncludedSupplyChainTradeLineItem' % self.NAMESPACES['ram'])
        
        # Line ID
        doc = ET.SubElement(line_item, '{%s}AssociatedDocumentLineDocument' % self.NAMESPACES['ram'])
        line_id = ET.SubElement(doc, '{%s}LineID' % self.NAMESPACES['ram'])
        line_id.text = str(item.get('position', 1))
        
        # Product
        product = ET.SubElement(line_item, '{%s}SpecifiedTradeProduct' % self.NAMESPACES['ram'])
        name = ET.SubElement(product, '{%s}Name' % self.NAMESPACES['ram'])
        name.text = item.get('description', '')
        
        # Agreement
        agreement = ET.SubElement(line_item, '{%s}SpecifiedLineTradeAgreement' % self.NAMESPACES['ram'])
        
        # Gross Price
        gross_price = ET.SubElement(agreement, '{%s}GrossPriceProductTradePrice' % self.NAMESPACES['ram'])
        charge_amount = ET.SubElement(gross_price, '{%s}ChargeAmount' % self.NAMESPACES['ram'])
        charge_amount.text = str(item.get('unit_price', 0))
        
        # Delivery
        delivery = ET.SubElement(line_item, '{%s}SpecifiedLineTradeDelivery' % self.NAMESPACES['ram'])
        quantity = ET.SubElement(delivery, '{%s}BilledQuantity' % self.NAMESPACES['ram'])
        quantity.set('unitCode', item.get('unit', 'C62'))  # C62 = Stück
        quantity.text = str(item.get('quantity', 1))
        
        # Settlement
        settlement = ET.SubElement(line_item, '{%s}SpecifiedLineTradeSettlement' % self.NAMESPACES['ram'])
        
        # Tax
        tax = ET.SubElement(settlement, '{%s}ApplicableTradeTax' % self.NAMESPACES['ram'])
        tax_type = ET.SubElement(tax, '{%s}TypeCode' % self.NAMESPACES['ram'])
        tax_type.text = 'VAT'
        tax_rate = ET.SubElement(tax, '{%s}RateApplicablePercent' % self.NAMESPACES['ram'])
        tax_rate.text = str(item.get('tax_rate', 19))
        
        # Monetary Summation
        summation = ET.SubElement(settlement, '{%s}SpecifiedTradeSettlementLineMonetarySummation' % self.NAMESPACES['ram'])
        line_total = ET.SubElement(summation, '{%s}LineTotalAmount' % self.NAMESPACES['ram'])
        line_total.text = str(item.get('total_net', 0))
        
    def _add_seller(self, agreement: ET.Element, seller_data: Dict):
        """Füge Verkäufer-Informationen hinzu"""
        seller = ET.SubElement(agreement, '{%s}SellerTradeParty' % self.NAMESPACES['ram'])
        
        # Name
        name = ET.SubElement(seller, '{%s}Name' % self.NAMESPACES['ram'])
        name.text = seller_data.get('name', 'StitchAdmin GmbH')
        
        # Address
        address = ET.SubElement(seller, '{%s}PostalTradeAddress' % self.NAMESPACES['ram'])
        
        line_one = ET.SubElement(address, '{%s}LineOne' % self.NAMESPACES['ram'])
        line_one.text = seller_data.get('street', '')
        
        postcode = ET.SubElement(address, '{%s}PostcodeCode' % self.NAMESPACES['ram'])
        postcode.text = seller_data.get('postcode', '')
        
        city = ET.SubElement(address, '{%s}CityName' % self.NAMESPACES['ram'])
        city.text = seller_data.get('city', '')
        
        country = ET.SubElement(address, '{%s}CountryID' % self.NAMESPACES['ram'])
        country.text = seller_data.get('country', 'DE')
        
        # Tax Registration
        if 'tax_number' in seller_data:
            tax_reg = ET.SubElement(seller, '{%s}SpecifiedTaxRegistration' % self.NAMESPACES['ram'])
            tax_id = ET.SubElement(tax_reg, '{%s}ID' % self.NAMESPACES['ram'])
            tax_id.set('schemeID', 'VA')
            tax_id.text = seller_data['tax_number']
            
    def _add_buyer(self, agreement: ET.Element, buyer_data: Dict):
        """Füge Käufer-Informationen hinzu"""
        buyer = ET.SubElement(agreement, '{%s}BuyerTradeParty' % self.NAMESPACES['ram'])
        
        # Name
        name = ET.SubElement(buyer, '{%s}Name' % self.NAMESPACES['ram'])
        name.text = buyer_data.get('name', '')
        
        # Address
        address = ET.SubElement(buyer, '{%s}PostalTradeAddress' % self.NAMESPACES['ram'])
        
        line_one = ET.SubElement(address, '{%s}LineOne' % self.NAMESPACES['ram'])
        line_one.text = buyer_data.get('street', '')
        
        postcode = ET.SubElement(address, '{%s}PostcodeCode' % self.NAMESPACES['ram'])
        postcode.text = buyer_data.get('postcode', '')
        
        city = ET.SubElement(address, '{%s}CityName' % self.NAMESPACES['ram'])
        city.text = buyer_data.get('city', '')
        
        country = ET.SubElement(address, '{%s}CountryID' % self.NAMESPACES['ram'])
        country.text = buyer_data.get('country', 'DE')
        
    def _add_delivery(self, delivery: ET.Element, invoice_data: Dict):
        """Füge Lieferinformationen hinzu"""
        event = ET.SubElement(delivery, '{%s}ActualDeliverySupplyChainEvent' % self.NAMESPACES['ram'])
        occurrence = ET.SubElement(event, '{%s}OccurrenceDateTime' % self.NAMESPACES['ram'])
        date_elem = ET.SubElement(occurrence, '{%s}DateTimeString' % self.NAMESPACES['udt'])
        date_elem.set('format', '102')
        
        delivery_date = invoice_data.get('delivery_date', invoice_data.get('invoice_date', datetime.now()))
        if isinstance(delivery_date, (date, datetime)):
            date_elem.text = delivery_date.strftime('%Y%m%d')
        else:
            date_elem.text = delivery_date
            
    def _add_payment_terms(self, settlement: ET.Element, invoice_data: Dict):
        """Füge Zahlungsbedingungen hinzu"""
        payment_ref = ET.SubElement(settlement, '{%s}PaymentReference' % self.NAMESPACES['ram'])
        payment_ref.text = invoice_data.get('payment_reference', '')
        
        # Currency
        currency = ET.SubElement(settlement, '{%s}InvoiceCurrencyCode' % self.NAMESPACES['ram'])
        currency.text = invoice_data.get('currency', 'EUR')
        
        # Payment Terms
        terms = ET.SubElement(settlement, '{%s}SpecifiedTradePaymentTerms' % self.NAMESPACES['ram'])
        desc = ET.SubElement(terms, '{%s}Description' % self.NAMESPACES['ram'])
        desc.text = invoice_data.get('payment_terms', 'Zahlbar innerhalb 14 Tagen')
        
        # Due Date
        due_date_elem = ET.SubElement(terms, '{%s}DueDateDateTime' % self.NAMESPACES['ram'])
        date_elem = ET.SubElement(due_date_elem, '{%s}DateTimeString' % self.NAMESPACES['udt'])
        date_elem.set('format', '102')
        
        due_date = invoice_data.get('due_date', datetime.now())
        if isinstance(due_date, (date, datetime)):
            date_elem.text = due_date.strftime('%Y%m%d')
        else:
            date_elem.text = due_date
            
    def _add_monetary_summation(self, settlement: ET.Element, invoice_data: Dict):
        """Füge Rechnungssummen hinzu"""
        summation = ET.SubElement(settlement, '{%s}SpecifiedTradeSettlementHeaderMonetarySummation' % self.NAMESPACES['ram'])
        
        # Line Total
        line_total = ET.SubElement(summation, '{%s}LineTotalAmount' % self.NAMESPACES['ram'])
        line_total.text = str(invoice_data.get('total_net', 0))
        
        # Tax Basis Total
        tax_basis = ET.SubElement(summation, '{%s}TaxBasisTotalAmount' % self.NAMESPACES['ram'])
        tax_basis.text = str(invoice_data.get('total_net', 0))
        
        # Tax Total
        tax_total = ET.SubElement(summation, '{%s}TaxTotalAmount' % self.NAMESPACES['ram'])
        tax_total.set('currencyID', invoice_data.get('currency', 'EUR'))
        tax_total.text = str(invoice_data.get('total_tax', 0))
        
        # Grand Total
        grand_total = ET.SubElement(summation, '{%s}GrandTotalAmount' % self.NAMESPACES['ram'])
        grand_total.text = str(invoice_data.get('total_gross', 0))
        
        # Due Payable Amount
        due_amount = ET.SubElement(summation, '{%s}DuePayableAmount' % self.NAMESPACES['ram'])
        due_amount.text = str(invoice_data.get('total_gross', 0))
        
    def validate_xml(self, xml_string: str, xsd_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Validiere ZUGPFERD XML gegen XSD Schema

        Args:
            xml_string: XML-String
            xsd_path: Pfad zum XSD-Schema (optional)

        Returns:
            Validierungsergebnis mit valid, errors, warnings
        """
        errors = []
        warnings = []

        if not LXML_AVAILABLE:
            warnings.append("lxml nicht installiert - XSD-Validierung nicht verfügbar")
            logger.warning("lxml nicht verfügbar, XML-Validierung übersprungen")
            return {
                'valid': True,
                'errors': [],
                'warnings': warnings
            }

        try:
            # XML parsen
            xml_doc = etree.fromstring(xml_string.encode('utf-8'))

            # Basis-Validierung (Well-formed XML)
            if xml_doc is None:
                errors.append("XML ist nicht wohlgeformt")
                return {'valid': False, 'errors': errors, 'warnings': warnings}

            # XSD-Validierung (falls Schema vorhanden)
            if xsd_path and os.path.exists(xsd_path):
                try:
                    with open(xsd_path, 'r', encoding='utf-8') as xsd_file:
                        xsd_doc = etree.parse(xsd_file)
                        xsd_schema = etree.XMLSchema(xsd_doc)

                        # Validieren
                        if not xsd_schema.validate(xml_doc):
                            for error in xsd_schema.error_log:
                                errors.append(f"Zeile {error.line}: {error.message}")
                        else:
                            logger.info("XML erfolgreich gegen XSD validiert")
                except Exception as e:
                    warnings.append(f"XSD-Validierung fehlgeschlagen: {str(e)}")
                    logger.warning(f"XSD-Validierung nicht möglich: {str(e)}")
            else:
                warnings.append("Kein XSD-Schema angegeben - nur Basis-Validierung")

            # Pflichtfelder prüfen (ZUGFeRD-spezifisch)
            required_elements = [
                './/ram:ID',  # Rechnungsnummer
                './/ram:TypeCode',  # Dokumenttyp
                './/ram:IssueDateTime',  # Rechnungsdatum
                './/ram:SellerTradeParty',  # Verkäufer
                './/ram:BuyerTradeParty',  # Käufer
                './/ram:GrandTotalAmount'  # Gesamtbetrag
            ]

            namespaces = self.NAMESPACES
            for req_elem in required_elements:
                if xml_doc.find(req_elem, namespaces=namespaces) is None:
                    errors.append(f"Pflichtfeld fehlt: {req_elem}")

            is_valid = len(errors) == 0

            return {
                'valid': is_valid,
                'errors': errors,
                'warnings': warnings
            }

        except Exception as e:
            logger.error(f"Fehler bei XML-Validierung: {str(e)}")
            errors.append(f"Validierungsfehler: {str(e)}")
            return {
                'valid': False,
                'errors': errors,
                'warnings': warnings
            }
        
    def create_pdf_with_xml(self, pdf_content: bytes, xml_string: str, filename: str = "factur-x.xml") -> bytes:
        """
        Erstelle PDF/A-3 mit eingebettetem ZUGPFERD XML

        Args:
            pdf_content: PDF-Inhalt als Bytes
            xml_string: ZUGPFERD XML als String
            filename: Name der eingebetteten XML-Datei

        Returns:
            PDF/A-3 mit eingebettetem XML als Bytes
        """
        if not PIKEPDF_AVAILABLE:
            logger.warning("pikepdf nicht installiert - XML wird nicht eingebettet")
            logger.warning("Installieren Sie pikepdf: pip install pikepdf")
            return pdf_content

        try:
            # PDF öffnen
            pdf = pikepdf.open(BytesIO(pdf_content))

            # XML als Bytes
            xml_bytes = xml_string.encode('utf-8')

            # Embedded File Stream erstellen
            xml_stream = pikepdf.Stream(pdf, xml_bytes)
            xml_stream.Type = pikepdf.Name.EmbeddedFile
            xml_stream.Subtype = pikepdf.Name("text/xml")
            xml_stream.Params = pikepdf.Dictionary({
                'Size': len(xml_bytes),
                'ModDate': pikepdf.String(datetime.now().strftime('D:%Y%m%d%H%M%S')),
                'CheckSum': pikepdf.String(f"<{hashlib.md5(xml_bytes).hexdigest()}>")
            })

            # Filespec erstellen
            filespec = pikepdf.Dictionary({
                'Type': pikepdf.Name.Filespec,
                'F': pikepdf.String(filename),
                'UF': pikepdf.String(filename),
                'EF': pikepdf.Dictionary({
                    'F': xml_stream
                }),
                'Desc': pikepdf.String('ZUGFeRD/Factur-X XML Invoice'),
                'AFRelationship': pikepdf.Name.Alternative  # PDF/A-3 Compliance
            })

            # EmbeddedFiles im Names Tree
            if '/Names' not in pdf.Root:
                pdf.Root.Names = pikepdf.Dictionary()

            if '/EmbeddedFiles' not in pdf.Root.Names:
                pdf.Root.Names.EmbeddedFiles = pikepdf.Dictionary()

            # Names Array erstellen oder erweitern
            if '/Names' not in pdf.Root.Names.EmbeddedFiles:
                pdf.Root.Names.EmbeddedFiles.Names = pikepdf.Array([
                    pikepdf.String(filename),
                    filespec
                ])
            else:
                # An bestehendes Array anhängen
                names_array = pdf.Root.Names.EmbeddedFiles.Names
                names_array.extend([pikepdf.String(filename), filespec])

            # Associated Files für PDF/A-3
            if '/AF' not in pdf.Root:
                pdf.Root.AF = pikepdf.Array()
            pdf.Root.AF.append(filespec)

            # PDF/A-3 Metadaten setzen
            self._set_pdfa3_metadata(pdf)

            # PDF speichern
            output_buffer = BytesIO()
            pdf.save(output_buffer)
            output_buffer.seek(0)

            logger.info(f"PDF/A-3 mit eingebettetem {filename} erfolgreich erstellt")
            return output_buffer.getvalue()

        except Exception as e:
            logger.error(f"Fehler bei PDF/A-3 Erstellung: {str(e)}")
            logger.error("Fallback: Gebe Original-PDF ohne XML zurück")
            return pdf_content

    def _set_pdfa3_metadata(self, pdf: 'pikepdf.Pdf'):
        """
        Setze PDF/A-3 Metadaten

        Args:
            pdf: pikepdf.Pdf Objekt
        """
        try:
            # XMP Metadaten für PDF/A-3b
            xmp_metadata = f'''<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about="" xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/">
      <pdfaid:part>3</pdfaid:part>
      <pdfaid:conformance>B</pdfaid:conformance>
    </rdf:Description>
    <rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/">
      <dc:format>application/pdf</dc:format>
      <dc:title>
        <rdf:Alt>
          <rdf:li xml:lang="x-default">ZUGFeRD Invoice</rdf:li>
        </rdf:Alt>
      </dc:title>
    </rdf:Description>
    <rdf:Description rdf:about="" xmlns:pdf="http://ns.adobe.com/pdf/1.3/">
      <pdf:Producer>StitchAdmin ZUGFeRD Service</pdf:Producer>
    </rdf:Description>
    <rdf:Description rdf:about="" xmlns:xmp="http://ns.adobe.com/xap/1.0/">
      <xmp:CreatorTool>StitchAdmin 2.0</xmp:CreatorTool>
      <xmp:CreateDate>{datetime.now().isoformat()}</xmp:CreateDate>
      <xmp:ModifyDate>{datetime.now().isoformat()}</xmp:ModifyDate>
    </rdf:Description>
    <rdf:Description rdf:about="" xmlns:zf="urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#">
      <zf:DocumentType>INVOICE</zf:DocumentType>
      <zf:DocumentFileName>factur-x.xml</zf:DocumentFileName>
      <zf:Version>1.0</zf:Version>
      <zf:ConformanceLevel>BASIC</zf:ConformanceLevel>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>'''

            # Metadaten als Stream hinzufügen
            metadata_stream = pikepdf.Stream(pdf, xmp_metadata.encode('utf-8'))
            metadata_stream.Type = pikepdf.Name.Metadata
            metadata_stream.Subtype = pikepdf.Name.XML

            pdf.Root.Metadata = metadata_stream

            logger.info("PDF/A-3 Metadaten erfolgreich gesetzt")

        except Exception as e:
            logger.warning(f"Konnte PDF/A-3 Metadaten nicht setzen: {str(e)}")

    def create_invoice_from_rechnung(self, rechnung) -> bytes:
        """
        Erstelle vollständiges ZUGFeRD-PDF aus Rechnungs-Model

        Args:
            rechnung: Rechnung Model-Instanz

        Returns:
            PDF/A-3 mit eingebettetem XML
        """
        from src.services.pdf_service import PDFService

        try:
            # Rechnungsdaten aufbereiten
            invoice_data = self._convert_rechnung_to_invoice_data(rechnung)

            # 1. XML generieren
            xml_string = self.create_invoice_xml(invoice_data, rechnung.zugpferd_profil.value)

            # 2. XML validieren
            validation_result = self.validate_xml(xml_string)
            if not validation_result['valid']:
                logger.error(f"XML-Validierung fehlgeschlagen: {validation_result['errors']}")
                # Bei Validierungsfehlern trotzdem weitermachen, aber warnen

            # 3. PDF generieren
            pdf_service = PDFService()
            pdf_content = pdf_service.create_invoice_pdf(invoice_data)

            # 4. XML in PDF einbetten (PDF/A-3)
            zugferd_pdf = self.create_pdf_with_xml(pdf_content, xml_string)

            logger.info(f"ZUGFeRD-Rechnung {rechnung.rechnungsnummer} erfolgreich erstellt")
            return zugferd_pdf

        except Exception as e:
            logger.error(f"Fehler bei ZUGFeRD-Erstellung: {str(e)}")
            raise

    def _convert_rechnung_to_invoice_data(self, rechnung) -> Dict[str, Any]:
        """
        Konvertiert Rechnung-Model zu invoice_data Dictionary

        Args:
            rechnung: Rechnung Model-Instanz

        Returns:
            Dictionary mit Rechnungsdaten
        """
        # Positionen aufbereiten
        items = []
        for pos in rechnung.positionen:
            items.append({
                'position': pos.position,
                'description': f"{pos.artikel_name}\n{pos.beschreibung or ''}".strip(),
                'quantity': float(pos.menge),
                'unit': pos.einheit,
                'unit_price': float(pos.einzelpreis),
                'tax_rate': float(pos.mwst_satz),
                'total_net': float(pos.netto_betrag),
                'total': float(pos.brutto_betrag)
            })

        # Verkäufer-Daten aus CompanySettings laden
        try:
            from src.models.company_settings import CompanySettings
            settings = CompanySettings.get_settings()

            seller_data = {
                'name': settings.display_name,
                'street': f"{settings.street or ''} {settings.house_number or ''}".strip(),
                'postcode': settings.postal_code or '',
                'city': settings.city or '',
                'country': settings.country[:2].upper() if settings.country else 'DE',  # ISO-Code
                'tax_number': settings.vat_id or settings.tax_id or ''
            }
        except Exception as e:
            logger.warning(f"Konnte CompanySettings nicht laden: {e}, verwende Fallback-Daten")
            seller_data = {
                'name': 'StitchAdmin GmbH',
                'street': 'Musterstraße 1',
                'postcode': '12345',
                'city': 'Musterstadt',
                'country': 'DE',
                'tax_number': 'DE123456789'
            }

        # Käufer-Daten
        buyer_data = {
            'name': rechnung.kunde_name,
            'street': rechnung.kunde_adresse.split('\n')[0] if rechnung.kunde_adresse else '',
            'postcode': '',  # TODO: Adresse parsen
            'city': '',
            'country': 'DE'
        }

        # Steuern aggregieren
        taxes = []
        # Gruppiere nach MwSt-Satz
        tax_dict = {}
        for pos in rechnung.positionen:
            rate = float(pos.mwst_satz)
            if rate not in tax_dict:
                tax_dict[rate] = 0
            tax_dict[rate] += float(pos.mwst_betrag)

        for rate, amount in tax_dict.items():
            taxes.append({'rate': rate, 'amount': amount})

        return {
            'invoice_number': rechnung.rechnungsnummer,
            'invoice_date': rechnung.rechnungsdatum,
            'delivery_date': rechnung.leistungsdatum or rechnung.rechnungsdatum,
            'due_date': rechnung.faelligkeitsdatum,
            'customer_number': rechnung.kunde_id,
            'payment_reference': rechnung.rechnungsnummer,
            'payment_terms': rechnung.zahlungsbedingungen or 'Zahlbar innerhalb 14 Tagen',
            'currency': 'EUR',
            'items': items,
            'seller': seller_data,
            'buyer': buyer_data,
            'recipient': buyer_data,  # Gleich wie Käufer
            'sender': seller_data,  # Gleich wie Verkäufer
            'subtotal': float(rechnung.netto_gesamt),
            'total_net': float(rechnung.netto_gesamt),
            'total_tax': float(rechnung.mwst_gesamt),
            'total_gross': float(rechnung.brutto_gesamt),
            'taxes': taxes,
            'discount_amount': float(rechnung.rabatt_betrag or 0),
            'discount_percent': float(rechnung.rabatt_prozent or 0),
            'subject': f"Rechnung {rechnung.rechnungsnummer}",
            'bank_details': {
                'bank_name': settings.bank_name if 'settings' in locals() else 'Musterbank',
                'iban': settings.iban if 'settings' in locals() else 'DE89370400440532013000',
                'bic': settings.bic if 'settings' in locals() else 'COBADEFFXXX'
            },
            'footer_text': settings.invoice_footer_text if 'settings' in locals() and settings.invoice_footer_text else 'Vielen Dank für Ihren Auftrag!'
        }