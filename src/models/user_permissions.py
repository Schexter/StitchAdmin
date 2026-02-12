"""
User Permissions & Dashboard Layout Models
Erstellt von Hans Hahn - Alle Rechte vorbehalten

Verwaltung von:
- Modulen im System
- Benutzer-Berechtigungen pro Modul
- Persönlichen Dashboard-Layouts
"""

from datetime import datetime
from src.models.models import db


class Module(db.Model):
    """
    Definiert alle verfügbaren Module im System
    
    Beispiel-Module:
    - CRM (Kundenverwaltung)
    - Production (Produktion & Aufträge)
    - POS (Kasse)
    - Accounting (Buchhaltung)
    - Documents (Dokumente & Post)
    - Administration (Verwaltung)
    - Warehouse (Lager)
    - Design Archive (Design-Archiv)
    """
    __tablename__ = 'modules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)  # z.B. "crm"
    display_name = db.Column(db.String(100), nullable=False)  # "CRM - Kundenverwaltung"
    description = db.Column(db.String(255))  # "Verwaltung von Kunden und Kontakten"
    icon = db.Column(db.String(50), default="bi-grid-fill")  # Bootstrap Icon Klasse
    color = db.Column(db.String(50), default="primary")  # Bootstrap-Farbe
    route = db.Column(db.String(200))  # "customers.index" (Blueprint.route)
    category = db.Column(db.String(50), default="core")  # "core", "finance", "production", "admin"
    
    # Status & Einstellungen
    is_active = db.Column(db.Boolean, default=True, index=True)
    requires_admin = db.Column(db.Boolean, default=False)  # Nur für Admins sichtbar
    default_enabled = db.Column(db.Boolean, default=True)  # Standard-sichtbar für neue User
    sort_order = db.Column(db.Integer, default=0)  # Standard-Reihenfolge im Dashboard
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    permissions = db.relationship('ModulePermission', back_populates='module', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Module {self.name}: {self.display_name}>'
    
    def to_dict(self):
        """Konvertiert Modul zu Dictionary für API"""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'icon': self.icon,
            'color': self.color,
            'route': self.route,
            'category': self.category,
            'is_active': self.is_active,
            'requires_admin': self.requires_admin,
            'sort_order': self.sort_order
        }


class ModulePermission(db.Model):
    """
    Berechtigungen: Welcher User darf welches Modul nutzen
    
    Rechte-Stufen:
    - can_view: Modul sehen und Daten anzeigen
    - can_create: Neue Einträge erstellen
    - can_edit: Bestehende Einträge bearbeiten
    - can_delete: Einträge löschen
    """
    __tablename__ = 'module_permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'), nullable=False, index=True)
    
    # Berechtigungen (CRUD)
    can_view = db.Column(db.Boolean, default=True)
    can_create = db.Column(db.Boolean, default=False)
    can_edit = db.Column(db.Boolean, default=False)
    can_delete = db.Column(db.Boolean, default=False)
    
    # Audit-Trail
    granted_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # Welcher Admin hat Recht vergeben
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)
    revoked_at = db.Column(db.DateTime, nullable=True)  # Wann wurde Recht entzogen
    
    # Unique Constraint: Ein User kann nur eine Berechtigung pro Modul haben
    __table_args__ = (
        db.UniqueConstraint('user_id', 'module_id', name='unique_user_module_permission'),
    )
    
    # Relationships
    module = db.relationship('Module', back_populates='permissions')
    user = db.relationship('User', foreign_keys=[user_id], backref='module_permissions')
    granter = db.relationship('User', foreign_keys=[granted_by])
    
    def __repr__(self):
        return f'<ModulePermission user={self.user_id} module={self.module_id} view={self.can_view}>'
    
    def to_dict(self):
        """Konvertiert Berechtigung zu Dictionary für API"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'module_id': self.module_id,
            'can_view': self.can_view,
            'can_create': self.can_create,
            'can_edit': self.can_edit,
            'can_delete': self.can_delete,
            'granted_at': self.granted_at.isoformat() if self.granted_at else None
        }


class DashboardLayout(db.Model):
    """
    Persönliche Dashboard-Konfiguration pro User
    
    Speichert:
    - Reihenfolge der Module
    - Sichtbarkeit (ein-/ausgeblendet)
    - Kachelgröße (optional)
    """
    __tablename__ = 'dashboard_layouts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True, index=True)
    
    # JSON-Feld mit Dashboard-Konfiguration
    # Beispiel:
    # {
    #   "modules": [
    #       {"module_id": 1, "order": 1, "visible": true, "size": "normal"},
    #       {"module_id": 2, "order": 2, "visible": false, "size": "normal"}
    #   ],
    #   "theme": "light",
    #   "compact_mode": false
    # }
    layout_config = db.Column(db.JSON, default=dict)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('dashboard_layout', uselist=False))
    
    def __repr__(self):
        return f'<DashboardLayout user={self.user_id}>'
    
    def get_module_order(self):
        """Gibt die Modul-Reihenfolge als Liste zurück"""
        if not self.layout_config or 'modules' not in self.layout_config:
            return []
        return sorted(
            self.layout_config['modules'],
            key=lambda x: x.get('order', 999)
        )
    
    def is_module_visible(self, module_id):
        """Prüft ob ein Modul sichtbar ist"""
        if not self.layout_config or 'modules' not in self.layout_config:
            return True  # Default: sichtbar
        
        for module in self.layout_config['modules']:
            if module.get('module_id') == module_id:
                return module.get('visible', True)
        
        return True  # Wenn nicht konfiguriert, dann sichtbar
    
    def to_dict(self):
        """Konvertiert Layout zu Dictionary für API"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'layout_config': self.layout_config,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def create_default_layout(user_id):
        """Erstellt ein Standard-Layout für einen neuen User"""
        from src.models.user_permissions import Module
        
        # Hole alle aktiven Module
        modules = Module.query.filter_by(is_active=True).order_by(Module.sort_order).all()
        
        layout_config = {
            'modules': [
                {
                    'module_id': module.id,
                    'order': idx + 1,
                    'visible': module.default_enabled,
                    'size': 'normal'
                }
                for idx, module in enumerate(modules)
            ],
            'theme': 'light',
            'compact_mode': False
        }
        
        layout = DashboardLayout(
            user_id=user_id,
            layout_config=layout_config
        )
        
        return layout
