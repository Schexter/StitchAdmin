# StitchAdmin 2.0 - Models Package
# Erstellt von Hans Hahn - Alle Rechte vorbehalten

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
]
