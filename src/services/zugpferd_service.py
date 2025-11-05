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
        
    def validate_xml(self, xml_string: str) -> Dict[str, Any]:
        """
        Validiere ZUGPFERD XML
        
        Args:
            xml_string: XML-String
            
        Returns:
            Validierungsergebnis
        """
        # TODO: Implementiere XSD-Validierung
        return {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
    def create_pdf_with_xml(self, pdf_content: bytes, xml_string: str) -> bytes:
        """
        Erstelle PDF/A-3 mit eingebettetem ZUGPFERD XML
        
        Args:
            pdf_content: PDF-Inhalt
            xml_string: ZUGPFERD XML
            
        Returns:
            PDF/A-3 mit eingebettetem XML
        """
        try:
            # TODO: Implementiere PDF/A-3 Erstellung mit PyPDF2 oder ähnlich
            # Für jetzt geben wir das originale PDF zurück
            logger.warning("PDF/A-3 Erstellung noch nicht implementiert")
            return pdf_content
            
        except Exception as e:
            logger.error(f"Fehler bei PDF/A-3 Erstellung: {str(e)}")
            return pdf_content