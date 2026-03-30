# -*- coding: utf-8 -*-
"""
STATUS REGISTRY
===============
Zentrale Definition aller Status-Labels, Farben und Icons.
Single Source of Truth - statt Duplikate in Models und Templates.

Nutzung:
    from src.utils.status_registry import StatusRegistry
    label = StatusRegistry.ORDER.label('in_progress')  # 'In Produktion'
    color = StatusRegistry.ORDER.color('in_progress')   # 'warning'
    icon = StatusRegistry.ORDER.icon('in_progress')     # 'bi-gear'

In Templates (via Context Processor):
    {{ order_status_label(order.status) }}
    {{ order_status_badge(order.status) }}

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""


class StatusConfig:
    """Konfigurierbarer Status mit Label, Farbe und Icon"""

    def __init__(self, statuses: dict):
        """
        Args:
            statuses: Dict von status_key -> (label, bootstrap_color, bi_icon)
        """
        self._statuses = statuses

    def label(self, status):
        entry = self._statuses.get(status)
        return entry[0] if entry else status

    def color(self, status):
        entry = self._statuses.get(status)
        return entry[1] if entry else 'secondary'

    def icon(self, status):
        entry = self._statuses.get(status)
        return entry[2] if entry else 'bi-circle'

    def badge_html(self, status):
        return f'<span class="badge bg-{self.color(status)}"><i class="{self.icon(status)} me-1"></i>{self.label(status)}</span>'

    def all(self):
        return {k: {'label': v[0], 'color': v[1], 'icon': v[2]} for k, v in self._statuses.items()}

    def choices(self):
        """Fuer Select-Felder: [(value, label), ...]"""
        return [(k, v[0]) for k, v in self._statuses.items()]


class StatusRegistry:
    """Zentrale Status-Definitionen fuer alle Entities"""

    # Auftraege
    ORDER = StatusConfig({
        'new':          ('Neu',              'primary',   'bi-plus-circle'),
        'accepted':     ('Angenommen',       'info',      'bi-check-circle'),
        'in_progress':  ('In Produktion',    'warning',   'bi-gear'),
        'ready':        ('Fertig',           'success',   'bi-check2-all'),
        'completed':    ('Abgeschlossen',    'success',   'bi-trophy'),
        'shipped':      ('Versendet',        'primary',   'bi-truck'),
        'cancelled':    ('Storniert',        'danger',    'bi-x-circle'),
        'on_hold':      ('Pausiert',         'secondary', 'bi-pause-circle'),
    })

    # Angebote
    ANGEBOT = StatusConfig({
        'entwurf':      ('Entwurf',          'secondary', 'bi-file-earmark'),
        'verschickt':   ('Verschickt',       'info',      'bi-send'),
        'angenommen':   ('Angenommen',       'success',   'bi-check-circle'),
        'abgelehnt':    ('Abgelehnt',        'danger',    'bi-x-circle'),
        'abgelaufen':   ('Abgelaufen',       'secondary', 'bi-clock'),
        'storniert':    ('Storniert',        'dark',      'bi-x-circle'),
    })

    # Rechnungen
    RECHNUNG = StatusConfig({
        'entwurf':      ('Entwurf',          'secondary', 'bi-file-earmark'),
        'versendet':    ('Versendet',        'info',      'bi-send'),
        'ueberfaellig': ('Ueberfaellig',     'danger',    'bi-exclamation-triangle'),
        'teilbezahlt':  ('Teilbezahlt',      'warning',   'bi-cash'),
        'bezahlt':      ('Bezahlt',          'success',   'bi-check-circle'),
        'storniert':    ('Storniert',        'dark',      'bi-x-circle'),
    })

    # Anfragen
    INQUIRY = StatusConfig({
        'neu':              ('Neu',               'primary',   'bi-envelope'),
        'in_bearbeitung':   ('In Bearbeitung',    'warning',   'bi-gear'),
        'angebot_erstellt': ('Angebot erstellt',  'info',      'bi-file-earmark-text'),
        'auftrag_erstellt': ('Auftrag erstellt',  'success',   'bi-check-circle'),
        'storniert':        ('Storniert',         'danger',    'bi-x-circle'),
        'abgeschlossen':    ('Abgeschlossen',     'secondary', 'bi-check2-all'),
    })

    # Bestellungen (Purchasing)
    PURCHASE = StatusConfig({
        'draft':     ('Entwurf',       'secondary', 'bi-file-earmark'),
        'ordered':   ('Bestellt',      'primary',   'bi-send'),
        'confirmed': ('Bestaetigt',    'info',      'bi-check'),
        'shipped':   ('Unterwegs',     'warning',   'bi-truck'),
        'partial':   ('Teillieferung', 'danger',    'bi-box'),
        'delivered': ('Geliefert',     'success',   'bi-check2-all'),
        'cancelled': ('Storniert',     'dark',      'bi-x-circle'),
    })

    # Design-Freigabe
    DESIGN_APPROVAL = StatusConfig({
        'pending':              ('Ausstehend',     'warning',   'bi-clock'),
        'sent':                 ('Gesendet',       'info',      'bi-send'),
        'approved':             ('Freigegeben',    'success',   'bi-check-circle'),
        'rejected':             ('Abgelehnt',      'danger',    'bi-x-circle'),
        'revision_requested':   ('Ueberarbeitung', 'warning',   'bi-arrow-repeat'),
    })

    # Zahlungsstatus
    PAYMENT = StatusConfig({
        'pending':      ('Offen',        'warning',   'bi-clock'),
        'deposit_paid': ('Anzahlung',    'info',      'bi-cash'),
        'paid':         ('Bezahlt',      'success',   'bi-check-circle'),
        'refunded':     ('Erstattet',    'secondary', 'bi-arrow-return-left'),
    })

    # Versand
    SHIPPING = StatusConfig({
        'created':   ('Erstellt',   'secondary', 'bi-box'),
        'shipped':   ('Versendet',  'primary',   'bi-truck'),
        'delivered': ('Zugestellt', 'success',   'bi-check2-all'),
    })

    # Mahnungen
    MAHNUNG = StatusConfig({
        'entwurf':     ('Entwurf',      'secondary', 'bi-file-earmark'),
        'versendet':   ('Versendet',    'warning',   'bi-send'),
        'bezahlt':     ('Bezahlt',      'success',   'bi-check-circle'),
        'storniert':   ('Storniert',    'dark',      'bi-x-circle'),
        'inkasso':     ('Inkasso',      'danger',    'bi-exclamation-octagon'),
        'gerichtlich': ('Gerichtlich',  'danger',    'bi-bank'),
    })


def register_status_helpers(app):
    """Registriert Template-Hilfsfunktionen fuer Status-Anzeige"""

    @app.context_processor
    def status_context():
        return {
            'StatusRegistry': StatusRegistry,
            'order_status_badge': lambda s: StatusRegistry.ORDER.badge_html(s),
            'angebot_status_badge': lambda s: StatusRegistry.ANGEBOT.badge_html(s),
            'rechnung_status_badge': lambda s: StatusRegistry.RECHNUNG.badge_html(s),
            'inquiry_status_badge': lambda s: StatusRegistry.INQUIRY.badge_html(s),
        }
