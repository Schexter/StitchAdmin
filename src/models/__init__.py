# StitchAdmin 2.0 - Models Package
# Erstellt von Hans Hahn - Alle Rechte vorbehalten

# Multi-Tenant Foundation
from .tenant import Tenant, UserTenant
from .tenant_mixin import TenantMixin

# Kern-Models aus models.py importieren
from .models import (
    db,
    User,
    Customer,
    Article,
    Order,
    OrderItem,
    OrderStatusHistory,
    Machine,
    ProductionSchedule,
    Thread,
    ThreadStock,
    ThreadUsage,
    Shipment,
    ShipmentItem,
    Supplier,
    SupplierOrder,
    SupplierRating,
    ActivityLog,
    ProductCategory,
    Brand,
    PriceCalculationSettings
)

# Erweiterte Lieferanten-Models
from .article_supplier import ArticleSupplier, ArticleSupplierPriceHistory
from .supplier_contact import SupplierContact, SupplierCommunicationLog

# Artikel-Varianten (L-Shop Integration)
from .article_variant import ArticleVariant

# Workflow: Packlisten & Lieferscheine
from .packing_list import PackingList
from .delivery_note import DeliveryNote

# Auftrags-Workflow: Multi-Position & Personalisierung
from .order_workflow import OrderDesign, OrderItemPersonalization, OrderDesignNameList

# Dokumente & Post
from .document import Document, PostEntry, ArchivedEmail

# Company Settings
from .company_settings import CompanySettings

# Branding Settings
from .branding_settings import BrandingSettings

# Erweiterte Settings
from .settings import (
    TaxRate,
    PriceCalculationRule,
    ImportSettings,
    OperatingCostCategory,
    OperatingCost,
    CalculationMode
)

# Shop (öffentlicher Webshop)
from .shop import ShopCategory, ShopFinishingType, ShopDesignTemplate

# Website CMS
from .website_content import WebsiteContent

# Anfragen (öffentliche Website)
from .inquiry import Inquiry, InquiryStatus

# Design-Management
from .design import (
    Design,
    DesignVersion,
    DesignUsage,
    ThreadBrand,
    ThreadColor,
    DesignOrder
)

# TODO / Aufgaben-System
from .todo import Todo, TodoTemplate

# Produktionsplanung - Zeitblöcke
from .production_block import ProductionBlock

# Produktionszeit-Tracking (Lernende Kalkulation)
from .production_tracking import (
    ProductionTimeLog,
    ProductionStatistics,
    PositionTimeEstimate
)

# Rechnungsmodul (optional)
try:
    from .rechnungsmodul import (
        Receipt,
        ReceiptItem,
        Invoice,
        InvoiceItem,
        TSETransaction
    )
    RECHNUNGSMODUL_AVAILABLE = True
except ImportError:
    RECHNUNGSMODUL_AVAILABLE = False
    Receipt = None
    ReceiptItem = None
    Invoice = None
    InvoiceItem = None
    TSETransaction = None

# POS Models (optional)
try:
    from .pos import (
        POSSession,
        POSTransaction,
        POSPayment
    )
    POS_AVAILABLE = True
except ImportError:
    POS_AVAILABLE = False
    POSSession = None
    POSTransaction = None
    POSPayment = None

# Speicher-Einstellungen
try:
    from .storage_settings import StorageSettings
except ImportError:
    StorageSettings = None

# Dokument-Workflow (Nummernkreise, Geschäftsdokumente, Zahlungen)
try:
    from .document_workflow import (
        # Enums
        DokumentTyp,
        DokumentStatus,
        PositionsTyp,
        MwStKennzeichen,
        # Models
        Nummernkreis,
        Zahlungsbedingung,
        BusinessDocument,
        DocumentPosition,
        DocumentPayment,
        # Helper
        initialisiere_nummernkreise,
        initialisiere_zahlungsbedingungen
    )
    DOCUMENT_WORKFLOW_AVAILABLE = True
except ImportError:
    DOCUMENT_WORKFLOW_AVAILABLE = False
    DokumentTyp = None
    DokumentStatus = None
    PositionsTyp = None
    MwStKennzeichen = None
    Nummernkreis = None
    Zahlungsbedingung = None
    BusinessDocument = None
    DocumentPosition = None
    DocumentPayment = None
    initialisiere_nummernkreise = None
    initialisiere_zahlungsbedingungen = None

# Buchhaltung (optional)
try:
    from .buchhaltung import (
        Konto,
        BuchhaltungBuchung,
        Kostenstelle,
        Geschaeftsjahr,
        UStVoranmeldung,
        Finanzplan,
        Kalkulation,
    )
    BUCHHALTUNG_AVAILABLE = True
except ImportError:
    BUCHHALTUNG_AVAILABLE = False
    Konto = None
    BuchhaltungBuchung = None
    Kostenstelle = None
    Geschaeftsjahr = None
    UStVoranmeldung = None
    Finanzplan = None
    Kalkulation = None

# Kalender (optional)
try:
    from .kalender import (
        KalenderTermin,
        KalenderRessource,
    )
    KALENDER_AVAILABLE = True
except ImportError:
    KALENDER_AVAILABLE = False
    KalenderTermin = None
    KalenderRessource = None

# Exportiere alle Models
__all__ = [
    # Datenbank
    'db',
    
    # Benutzer & Verwaltung
    'User',
    'ActivityLog',
    
    # Kunden
    'Customer',
    
    # Artikel & Kategorien
    'Article',
    'ArticleVariant',
    'ArticleSupplier',
    'ArticleSupplierPriceHistory',
    'ProductCategory',
    'Brand',
    
    # Aufträge
    'Order',
    'OrderItem',
    'OrderStatusHistory',

    # Auftrags-Workflow (Multi-Position & Personalisierung)
    'OrderDesign',
    'OrderItemPersonalization',
    'OrderDesignNameList',
    
    # Produktion
    'Machine',
    'ProductionSchedule',
    
    # Garne
    'Thread',
    'ThreadStock',
    'ThreadUsage',
    
    # Versand
    'Shipment',
    'ShipmentItem',

    # Workflow: Packlisten & Lieferscheine
    'PackingList',
    'DeliveryNote',

    # Dokumente & Post
    'Document',
    'PostEntry',
    'ArchivedEmail',

    # Einstellungen (Company & Branding)
    'CompanySettings',
    'BrandingSettings',

    # Lieferanten
    'Supplier',
    'SupplierOrder',
    'SupplierContact',
    'SupplierCommunicationLog',
    'SupplierRating',
    
    # Einstellungen
    'PriceCalculationSettings',
    'TaxRate',
    'PriceCalculationRule',
    'ImportSettings',
    'OperatingCostCategory',
    'OperatingCost',
    'CalculationMode',
    
    # Design-Management
    'Design',
    'DesignVersion',
    'DesignUsage',
    'ThreadBrand',
    'ThreadColor',
    'DesignOrder',
    
    # TODO / Aufgaben-System
    'Todo',
    'TodoTemplate',
    
    # Produktionsplanung
    'ProductionBlock',

    # Produktionszeit-Tracking
    'ProductionTimeLog',
    'ProductionStatistics',
    'PositionTimeEstimate',

    # Rechnungsmodul (optional)
    'Receipt',
    'ReceiptItem',
    'Invoice',
    'InvoiceItem',
    'TSETransaction',
    'RECHNUNGSMODUL_AVAILABLE',
    
    # POS (optional)
    'POSSession',
    'POSTransaction',
    'POSPayment',
    'POS_AVAILABLE',
    
    # Dokument-Workflow
    'DokumentTyp',
    'DokumentStatus',
    'PositionsTyp',
    'MwStKennzeichen',
    'Nummernkreis',
    'Zahlungsbedingung',
    'BusinessDocument',
    'DocumentPosition',
    'DocumentPayment',
    'initialisiere_nummernkreise',
    'initialisiere_zahlungsbedingungen',
    'DOCUMENT_WORKFLOW_AVAILABLE',

    # Buchhaltung
    'Konto',
    'BuchhaltungBuchung',
    'Kostenstelle',
    'Geschaeftsjahr',
    'UStVoranmeldung',
    'Finanzplan',
    'Kalkulation',
    'BUCHHALTUNG_AVAILABLE',

    # Kalender
    'KalenderTermin',
    'KalenderRessource',
    'KALENDER_AVAILABLE',

    # Shop (öffentlicher Webshop)
    'ShopCategory',
    'ShopFinishingType',
    'ShopDesignTemplate',

    # Website CMS
    'WebsiteContent',

    # Anfragen
    'Inquiry',
    'InquiryStatus',

    # Multi-Tenant
    'Tenant',
    'UserTenant',
    'TenantMixin',
]
