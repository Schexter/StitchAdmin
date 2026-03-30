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
    # XRechnung (EN 16931 CIUS für Deutschland)
    PROFILE_XRECHNUNG = "urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0"

    # Mapping von Kurzname zu Profil-URN
    PROFILE_MAP = {
        'MINIMUM': PROFILE_MINIMUM,
        'BASIC': PROFILE_BASIC,
        'COMFORT': PROFILE_COMFORT,
        'EXTENDED': PROFILE_EXTENDED,
        'XRECHNUNG': PROFILE_XRECHNUNG,
    }
    
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

    def _get_creator_name(self, username: str) -> str:
        """Vollständigen Namen des Erstellers aus User-Tabelle holen"""
        if not username:
            return ''
        try:
            from src.models.models import User
            user = User.query.filter_by(username=username).first()
            if user:
                name = f"{user.first_name or ''} {user.last_name or ''}".strip()
                return name or username
        except Exception:
            pass
        return username

    def _safe_str(self, value, default: str = '') -> str:
        """Konvertiert einen Wert sicher zu String, ersetzt None durch default"""
        if value is None:
            return default
        return str(value)

    def _safe_get(self, data: Dict, key: str, default: Any = '') -> Any:
        """Holt einen Wert aus Dict, ersetzt None durch default"""
        value = data.get(key, default)
        return default if value is None else value

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
        line_id.text = self._safe_str(self._safe_get(item, 'position', 1))

        # Product
        product = ET.SubElement(line_item, '{%s}SpecifiedTradeProduct' % self.NAMESPACES['ram'])
        name = ET.SubElement(product, '{%s}Name' % self.NAMESPACES['ram'])
        name.text = self._safe_str(self._safe_get(item, 'description', 'Artikel'))

        # Agreement
        agreement = ET.SubElement(line_item, '{%s}SpecifiedLineTradeAgreement' % self.NAMESPACES['ram'])

        # Gross Price
        gross_price = ET.SubElement(agreement, '{%s}GrossPriceProductTradePrice' % self.NAMESPACES['ram'])
        charge_amount = ET.SubElement(gross_price, '{%s}ChargeAmount' % self.NAMESPACES['ram'])
        charge_amount.text = self._safe_str(self._safe_get(item, 'unit_price', 0))

        # Delivery
        delivery = ET.SubElement(line_item, '{%s}SpecifiedLineTradeDelivery' % self.NAMESPACES['ram'])
        quantity = ET.SubElement(delivery, '{%s}BilledQuantity' % self.NAMESPACES['ram'])
        # Unit-Code mapping: Stück -> C62, etc.
        unit = self._safe_get(item, 'unit', 'Stück')
        unit_code_map = {'Stück': 'C62', 'Stk': 'C62', 'Std': 'HUR', 'Stunde': 'HUR', 'm': 'MTR', 'kg': 'KGM'}
        unit_code = unit_code_map.get(unit, 'C62')
        quantity.set('unitCode', unit_code)
        quantity.text = self._safe_str(self._safe_get(item, 'quantity', 1))

        # Settlement
        settlement = ET.SubElement(line_item, '{%s}SpecifiedLineTradeSettlement' % self.NAMESPACES['ram'])

        # Tax
        tax = ET.SubElement(settlement, '{%s}ApplicableTradeTax' % self.NAMESPACES['ram'])
        tax_type = ET.SubElement(tax, '{%s}TypeCode' % self.NAMESPACES['ram'])
        tax_type.text = 'VAT'
        tax_rate = ET.SubElement(tax, '{%s}RateApplicablePercent' % self.NAMESPACES['ram'])
        tax_rate.text = self._safe_str(self._safe_get(item, 'tax_rate', 19))

        # Monetary Summation
        summation = ET.SubElement(settlement, '{%s}SpecifiedTradeSettlementLineMonetarySummation' % self.NAMESPACES['ram'])
        line_total = ET.SubElement(summation, '{%s}LineTotalAmount' % self.NAMESPACES['ram'])
        line_total.text = self._safe_str(self._safe_get(item, 'total_net', 0))
        
    def _add_seller(self, agreement: ET.Element, seller_data: Dict):
        """Füge Verkäufer-Informationen hinzu"""
        seller = ET.SubElement(agreement, '{%s}SellerTradeParty' % self.NAMESPACES['ram'])

        # Name
        name = ET.SubElement(seller, '{%s}Name' % self.NAMESPACES['ram'])
        name.text = self._safe_str(self._safe_get(seller_data, 'name', 'StitchAdmin'))

        # Address
        address = ET.SubElement(seller, '{%s}PostalTradeAddress' % self.NAMESPACES['ram'])

        line_one = ET.SubElement(address, '{%s}LineOne' % self.NAMESPACES['ram'])
        line_one.text = self._safe_str(self._safe_get(seller_data, 'street', ''))

        postcode = ET.SubElement(address, '{%s}PostcodeCode' % self.NAMESPACES['ram'])
        postcode.text = self._safe_str(self._safe_get(seller_data, 'postcode', ''))

        city = ET.SubElement(address, '{%s}CityName' % self.NAMESPACES['ram'])
        city.text = self._safe_str(self._safe_get(seller_data, 'city', ''))

        country = ET.SubElement(address, '{%s}CountryID' % self.NAMESPACES['ram'])
        country.text = self._safe_str(self._safe_get(seller_data, 'country', 'DE'))

        # E-Mail und Telefon (für XRechnung relevant)
        email = self._safe_get(seller_data, 'email', '')
        if email:
            contact = ET.SubElement(seller, '{%s}DefinedTradeContact' % self.NAMESPACES['ram'])
            email_comm = ET.SubElement(contact, '{%s}EmailURIUniversalCommunication' % self.NAMESPACES['ram'])
            email_uri = ET.SubElement(email_comm, '{%s}URIID' % self.NAMESPACES['ram'])
            email_uri.text = self._safe_str(email)
            phone = self._safe_get(seller_data, 'phone', '')
            if phone:
                phone_comm = ET.SubElement(contact, '{%s}TelephoneUniversalCommunication' % self.NAMESPACES['ram'])
                phone_num = ET.SubElement(phone_comm, '{%s}CompleteNumber' % self.NAMESPACES['ram'])
                phone_num.text = self._safe_str(phone)

        # Tax Registration - USt-ID (VA) und/oder Steuernummer (FC)
        vat_id = self._safe_get(seller_data, 'vat_id', '')
        if vat_id:
            tax_reg = ET.SubElement(seller, '{%s}SpecifiedTaxRegistration' % self.NAMESPACES['ram'])
            tax_id_elem = ET.SubElement(tax_reg, '{%s}ID' % self.NAMESPACES['ram'])
            tax_id_elem.set('schemeID', 'VA')
            tax_id_elem.text = self._safe_str(vat_id)

        tax_number = self._safe_get(seller_data, 'tax_number', '')
        if tax_number and tax_number != vat_id:
            tax_reg2 = ET.SubElement(seller, '{%s}SpecifiedTaxRegistration' % self.NAMESPACES['ram'])
            tax_id_elem2 = ET.SubElement(tax_reg2, '{%s}ID' % self.NAMESPACES['ram'])
            tax_id_elem2.set('schemeID', 'FC')
            tax_id_elem2.text = self._safe_str(tax_number)
            
    def _add_buyer(self, agreement: ET.Element, buyer_data: Dict):
        """Füge Käufer-Informationen hinzu"""
        buyer = ET.SubElement(agreement, '{%s}BuyerTradeParty' % self.NAMESPACES['ram'])

        # Name
        name = ET.SubElement(buyer, '{%s}Name' % self.NAMESPACES['ram'])
        name.text = self._safe_str(self._safe_get(buyer_data, 'name', 'Kunde'))

        # Address
        address = ET.SubElement(buyer, '{%s}PostalTradeAddress' % self.NAMESPACES['ram'])

        line_one = ET.SubElement(address, '{%s}LineOne' % self.NAMESPACES['ram'])
        line_one.text = self._safe_str(self._safe_get(buyer_data, 'street', ''))

        postcode = ET.SubElement(address, '{%s}PostcodeCode' % self.NAMESPACES['ram'])
        postcode.text = self._safe_str(self._safe_get(buyer_data, 'postcode', ''))

        city = ET.SubElement(address, '{%s}CityName' % self.NAMESPACES['ram'])
        city.text = self._safe_str(self._safe_get(buyer_data, 'city', ''))

        country = ET.SubElement(address, '{%s}CountryID' % self.NAMESPACES['ram'])
        country.text = self._safe_str(self._safe_get(buyer_data, 'country', 'DE'))

        # Käufer USt-ID (falls Firmenkunde)
        buyer_vat = self._safe_get(buyer_data, 'vat_id', '')
        if buyer_vat:
            tax_reg = ET.SubElement(buyer, '{%s}SpecifiedTaxRegistration' % self.NAMESPACES['ram'])
            tax_id_elem = ET.SubElement(tax_reg, '{%s}ID' % self.NAMESPACES['ram'])
            tax_id_elem.set('schemeID', 'VA')
            tax_id_elem.text = self._safe_str(buyer_vat)
        
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
        """Füge Zahlungsbedingungen und Bankdaten hinzu"""
        payment_ref = ET.SubElement(settlement, '{%s}PaymentReference' % self.NAMESPACES['ram'])
        payment_ref.text = self._safe_str(self._safe_get(invoice_data, 'payment_reference', ''))

        # Currency
        currency = ET.SubElement(settlement, '{%s}InvoiceCurrencyCode' % self.NAMESPACES['ram'])
        currency.text = self._safe_str(self._safe_get(invoice_data, 'currency', 'EUR'))

        # Bankdaten als Zahlungsmittel (SpecifiedTradeSettlementPaymentMeans)
        bank_details = invoice_data.get('bank_details', {})
        iban = self._safe_get(bank_details, 'iban', '')
        if iban:
            payment_means = ET.SubElement(settlement, '{%s}SpecifiedTradeSettlementPaymentMeans' % self.NAMESPACES['ram'])
            # TypeCode 58 = SEPA Überweisung
            type_code = ET.SubElement(payment_means, '{%s}TypeCode' % self.NAMESPACES['ram'])
            type_code.text = '58'
            # Empfänger-Konto (Verkäufer)
            payee_account = ET.SubElement(payment_means, '{%s}PayeePartyCreditorFinancialAccount' % self.NAMESPACES['ram'])
            iban_elem = ET.SubElement(payee_account, '{%s}IBANID' % self.NAMESPACES['ram'])
            iban_elem.text = self._safe_str(iban).replace(' ', '')
            # BIC
            bic = self._safe_get(bank_details, 'bic', '')
            if bic:
                institution = ET.SubElement(payment_means, '{%s}PayeeSpecifiedCreditorFinancialInstitution' % self.NAMESPACES['ram'])
                bic_elem = ET.SubElement(institution, '{%s}BICID' % self.NAMESPACES['ram'])
                bic_elem.text = self._safe_str(bic)

        # MwSt-Aufschlüsselung (ApplicableTradeTax)
        taxes = invoice_data.get('taxes', [])
        for tax_info in taxes:
            trade_tax = ET.SubElement(settlement, '{%s}ApplicableTradeTax' % self.NAMESPACES['ram'])
            calc_amount = ET.SubElement(trade_tax, '{%s}CalculatedAmount' % self.NAMESPACES['ram'])
            calc_amount.text = self._safe_str(tax_info.get('amount', 0))
            tax_type = ET.SubElement(trade_tax, '{%s}TypeCode' % self.NAMESPACES['ram'])
            tax_type.text = 'VAT'
            # Bemessungsgrundlage
            basis_amount = ET.SubElement(trade_tax, '{%s}BasisAmount' % self.NAMESPACES['ram'])
            basis_amount.text = self._safe_str(tax_info.get('basis', tax_info.get('amount', 0)))
            # Steuersatz
            rate_percent = ET.SubElement(trade_tax, '{%s}RateApplicablePercent' % self.NAMESPACES['ram'])
            rate_percent.text = self._safe_str(tax_info.get('rate', 19))

        # Payment Terms
        terms = ET.SubElement(settlement, '{%s}SpecifiedTradePaymentTerms' % self.NAMESPACES['ram'])
        desc = ET.SubElement(terms, '{%s}Description' % self.NAMESPACES['ram'])
        desc.text = self._safe_str(self._safe_get(invoice_data, 'payment_terms', 'Zahlbar innerhalb 14 Tagen'))

        # Due Date
        due_date_elem = ET.SubElement(terms, '{%s}DueDateDateTime' % self.NAMESPACES['ram'])
        date_elem = ET.SubElement(due_date_elem, '{%s}DateTimeString' % self.NAMESPACES['udt'])
        date_elem.set('format', '102')

        due_date = self._safe_get(invoice_data, 'due_date', datetime.now())
        if isinstance(due_date, (date, datetime)):
            date_elem.text = due_date.strftime('%Y%m%d')
        else:
            date_elem.text = self._safe_str(due_date)
            
    def _add_monetary_summation(self, settlement: ET.Element, invoice_data: Dict):
        """Füge Rechnungssummen hinzu"""
        summation = ET.SubElement(settlement, '{%s}SpecifiedTradeSettlementHeaderMonetarySummation' % self.NAMESPACES['ram'])

        # Line Total
        line_total = ET.SubElement(summation, '{%s}LineTotalAmount' % self.NAMESPACES['ram'])
        line_total.text = self._safe_str(self._safe_get(invoice_data, 'total_net', 0))

        # Tax Basis Total
        tax_basis = ET.SubElement(summation, '{%s}TaxBasisTotalAmount' % self.NAMESPACES['ram'])
        tax_basis.text = self._safe_str(self._safe_get(invoice_data, 'total_net', 0))

        # Tax Total
        tax_total = ET.SubElement(summation, '{%s}TaxTotalAmount' % self.NAMESPACES['ram'])
        tax_total.set('currencyID', self._safe_str(self._safe_get(invoice_data, 'currency', 'EUR')))
        tax_total.text = self._safe_str(self._safe_get(invoice_data, 'total_tax', 0))

        # Grand Total
        grand_total = ET.SubElement(summation, '{%s}GrandTotalAmount' % self.NAMESPACES['ram'])
        grand_total.text = self._safe_str(self._safe_get(invoice_data, 'total_gross', 0))

        # Due Payable Amount
        due_amount = ET.SubElement(summation, '{%s}DuePayableAmount' % self.NAMESPACES['ram'])
        due_amount.text = self._safe_str(self._safe_get(invoice_data, 'total_gross', 0))
        
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

    def _get_conformance_level(self) -> str:
        """Gibt ConformanceLevel passend zum aktiven Profil zurück"""
        if self.profile == self.PROFILE_XRECHNUNG:
            return 'XRECHNUNG'
        elif self.profile == self.PROFILE_EXTENDED:
            return 'EXTENDED'
        elif self.profile == self.PROFILE_COMFORT:
            return 'COMFORT'
        elif self.profile == self.PROFILE_MINIMUM:
            return 'MINIMUM'
        return 'BASIC'

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
      <zf:ConformanceLevel>{self._get_conformance_level()}</zf:ConformanceLevel>
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

            # 1. XML generieren - Profil aus String- oder Enum-Feld auflösen
            profil_raw = rechnung.zugpferd_profil or 'BASIC'
            profil_name = profil_raw.value if hasattr(profil_raw, 'value') else str(profil_raw)
            profil_urn = self.PROFILE_MAP.get(profil_name.upper(), self.PROFILE_BASIC)
            xml_string = self.create_invoice_xml(invoice_data, profil_urn)

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
            # MwSt-Satz: Kann Numeric-Feld oder FK zu MwStSatz sein
            if hasattr(pos, 'mwst_satz') and pos.mwst_satz is not None:
                if hasattr(pos.mwst_satz, 'satz'):
                    # Altes Model: FK zu MwStSatz-Objekt
                    mwst_rate = float(pos.mwst_satz.satz)
                else:
                    # Neues Model: Numeric-Feld direkt
                    mwst_rate = float(pos.mwst_satz)
            else:
                mwst_rate = 19.0

            # Bezeichnung: neues Model nutzt artikel_name
            bezeichnung = getattr(pos, 'bezeichnung', None) or getattr(pos, 'artikel_name', '') or ''
            # Netto-Gesamt: neues Model nutzt netto_betrag
            netto = getattr(pos, 'netto_gesamt', None) or getattr(pos, 'netto_betrag', 0) or 0
            # Brutto-Gesamt: neues Model nutzt brutto_betrag
            brutto = getattr(pos, 'brutto_gesamt', None) or getattr(pos, 'brutto_betrag', 0) or 0
            # MwSt-Betrag
            mwst_betrag = getattr(pos, 'mwst_betrag', 0) or 0

            rabatt_pct = float(getattr(pos, 'rabatt_prozent', 0) or 0)
            rabatt_betrag = float(getattr(pos, 'rabatt_betrag', 0) or 0)
            items.append({
                'position': pos.position,
                'description': bezeichnung,
                'quantity': float(pos.menge),
                'unit': pos.einheit or 'Stk.',
                'unit_price': float(pos.einzelpreis),
                'tax_rate': mwst_rate,
                'total_net': float(netto),
                'total': float(brutto),
                'rabatt_prozent': rabatt_pct,
                'rabatt_betrag': rabatt_betrag,
            })

        # Verkäufer-Daten aus CompanySettings laden
        settings = None
        try:
            from src.models.company_settings import CompanySettings
            settings = CompanySettings.get_settings()

            # Land-Code: "Deutschland" -> "DE", "Österreich" -> "AT", etc.
            country_code = 'DE'
            if settings.country:
                country_map = {
                    'deutschland': 'DE', 'österreich': 'AT', 'schweiz': 'CH',
                    'austria': 'AT', 'germany': 'DE', 'switzerland': 'CH'
                }
                country_code = country_map.get(settings.country.lower(), settings.country[:2].upper())

            seller_data = {
                'name': settings.display_name,
                'owner_name': settings.owner_name or '',
                'street': f"{settings.street or ''} {settings.house_number or ''}".strip(),
                'postcode': settings.postal_code or '',
                'city': settings.city or '',
                'country': country_code,
                'vat_id': settings.vat_id or '',
                'tax_number': settings.tax_id or '',
                'email': settings.email or '',
                'phone': settings.phone or '',
            }
        except Exception as e:
            logger.warning(f"Konnte CompanySettings nicht laden: {e}, verwende Fallback-Daten")
            seller_data = {
                'name': 'StitchAdmin GmbH',
                'street': 'Musterstrasse 1',
                'postcode': '12345',
                'city': 'Musterstadt',
                'country': 'DE',
                'vat_id': '',
                'tax_number': '',
                'email': '',
                'phone': '',
            }

        # Käufer-Daten direkt aus dem Customer-Objekt
        kunde = rechnung.kunde
        if kunde:
            buyer_street = f"{kunde.street or ''} {kunde.house_number or ''}".strip()
            buyer_country = 'DE'
            if kunde.country:
                country_map = {
                    'deutschland': 'DE', 'österreich': 'AT', 'schweiz': 'CH',
                    'austria': 'AT', 'germany': 'DE', 'switzerland': 'CH'
                }
                buyer_country = country_map.get(kunde.country.lower(), kunde.country[:2].upper())

            buyer_data = {
                'name': kunde.display_name,
                'street': buyer_street,
                'postcode': kunde.postal_code or '',
                'city': kunde.city or '',
                'country': buyer_country,
                'vat_id': kunde.vat_id or '',
                'email': kunde.email or '',
            }
        else:
            buyer_data = {
                'name': 'Unbekannter Kunde',
                'street': '',
                'postcode': '',
                'city': '',
                'country': 'DE',
                'vat_id': '',
                'email': '',
            }

        # Steuern aggregieren - gruppiere nach MwSt-Satz
        tax_dict = {}  # rate -> {'amount': X, 'basis': Y}
        for pos in rechnung.positionen:
            if hasattr(pos, 'mwst_satz') and pos.mwst_satz is not None:
                if hasattr(pos.mwst_satz, 'satz'):
                    rate = float(pos.mwst_satz.satz)
                else:
                    rate = float(pos.mwst_satz)
            else:
                rate = 19.0
            if rate not in tax_dict:
                tax_dict[rate] = {'amount': 0, 'basis': 0}
            mwst_betrag = getattr(pos, 'mwst_betrag', 0) or 0
            netto = getattr(pos, 'netto_gesamt', None) or getattr(pos, 'netto_betrag', 0) or 0
            tax_dict[rate]['amount'] += float(mwst_betrag)
            tax_dict[rate]['basis'] += float(netto)

        taxes = []
        for rate, data in tax_dict.items():
            taxes.append({'rate': rate, 'amount': round(data['amount'], 2), 'basis': round(data['basis'], 2)})

        # Bankdaten
        bank_details = {}
        if settings:
            bank_details = {
                'bank_name': settings.bank_name or '',
                'iban': settings.iban or '',
                'bic': settings.bic or '',
            }

        # Betraege: neues Model nutzt netto_gesamt/mwst_gesamt/brutto_gesamt
        summe_netto = getattr(rechnung, 'summe_netto', None) or getattr(rechnung, 'netto_gesamt', 0) or 0
        summe_mwst = getattr(rechnung, 'summe_mwst', None) or getattr(rechnung, 'mwst_gesamt', 0) or 0
        summe_brutto = getattr(rechnung, 'summe_brutto', None) or getattr(rechnung, 'brutto_gesamt', 0) or 0

        # Logo aus CompanySettings
        logo_path = None
        if settings and settings.logo_path:
            try:
                from flask import current_app
                logo_full = os.path.join(current_app.static_folder, settings.logo_path)
                if os.path.exists(logo_full):
                    logo_path = logo_full
            except Exception:
                pass

        return {
            'logo_path': logo_path,
            'invoice_number': rechnung.rechnungsnummer,
            'invoice_date': rechnung.rechnungsdatum,
            'delivery_date': getattr(rechnung, 'leistungsdatum', None) or rechnung.rechnungsdatum,
            'due_date': rechnung.faelligkeitsdatum,
            'customer_number': rechnung.kunde_id,
            'payment_reference': rechnung.rechnungsnummer,
            'payment_terms': getattr(rechnung, 'zahlungsbedingungen', None) or 'Zahlbar innerhalb 14 Tagen',
            'currency': 'EUR',
            'items': items,
            'seller': seller_data,
            'buyer': buyer_data,
            'recipient': buyer_data,
            'sender': seller_data,
            'subtotal': float(summe_netto),
            'total_net': float(summe_netto),
            'total_tax': float(summe_mwst),
            'total_gross': float(summe_brutto),
            'taxes': taxes,
            'discount_amount': float(getattr(rechnung, 'rabatt_betrag', 0) or 0),
            'discount_percent': float(getattr(rechnung, 'rabatt_prozent', 0) or 0),
            'subject': f"Rechnung {rechnung.rechnungsnummer}",
            'bank_details': bank_details,
            'created_by': self._get_creator_name(getattr(rechnung, 'erstellt_von', None)),
            'footer_text': settings.invoice_footer_text if settings and settings.invoice_footer_text else 'Vielen Dank fuer Ihren Auftrag!'
        }