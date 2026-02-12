# -*- coding: utf-8 -*-
"""
WORKFLOW-AUTOMATISIERUNGS-SERVICE
=================================
Zentraler Service für automatische Statusübergänge und Workflow-Steuerung

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Tuple, Callable
from flask import current_app
import logging

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Zentrale Workflow-Status Definition"""
    # Angebots-Phase
    OFFER_DRAFT = 'offer_draft'
    OFFER_SENT = 'offer_sent'
    OFFER_EXPIRED = 'offer_expired'
    OFFER_ACCEPTED = 'offer_accepted'
    OFFER_REJECTED = 'offer_rejected'
    
    # Auftrags-Phase
    ORDER_NEW = 'order_new'
    ORDER_CONFIRMED = 'confirmed'
    
    # Design-Phase
    DESIGN_PENDING = 'design_pending'
    DESIGN_ORDERED = 'design_ordered'
    DESIGN_RECEIVED = 'design_received'
    DESIGN_APPROVAL_SENT = 'design_approval_sent'
    DESIGN_APPROVED = 'design_approved'
    DESIGN_REJECTED = 'design_rejected'
    
    # Material-Phase
    MATERIAL_PENDING = 'material_pending'
    MATERIAL_ORDERED = 'material_ordered'
    MATERIAL_RECEIVED = 'material_received'
    
    # Produktions-Phase
    PRODUCTION_SCHEDULED = 'production_scheduled'
    PRODUCTION_IN_PROGRESS = 'in_production'
    PRODUCTION_COMPLETED = 'production_completed'
    
    # QM-Phase
    QC_PENDING = 'qc_pending'
    QC_IN_PROGRESS = 'qc_in_progress'
    QC_PASSED = 'qc_passed'
    QC_FAILED = 'qc_failed'
    
    # Versand-Phase
    PACKING = 'packing'
    READY_TO_SHIP = 'ready_to_ship'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    PICKED_UP = 'picked_up'
    
    # Abschluss-Phase
    INVOICED = 'invoiced'
    PAID = 'paid'
    COMPLETED = 'completed'
    ARCHIVED = 'archived'
    
    # Sonderstatus
    ON_HOLD = 'on_hold'
    CANCELLED = 'cancelled'


class WorkflowTransition:
    """Definiert einen Workflow-Übergang"""
    
    def __init__(self, 
                 from_status: WorkflowStatus,
                 to_status: WorkflowStatus,
                 condition: Optional[Callable] = None,
                 auto_trigger: bool = False,
                 requires_confirmation: bool = False,
                 creates_notification: bool = True,
                 creates_activity: bool = True,
                 next_actions: List[str] = None):
        self.from_status = from_status
        self.to_status = to_status
        self.condition = condition  # Funktion die True/False zurückgibt
        self.auto_trigger = auto_trigger  # Automatisch auslösen wenn Bedingung erfüllt
        self.requires_confirmation = requires_confirmation
        self.creates_notification = creates_notification
        self.creates_activity = creates_activity
        self.next_actions = next_actions or []


class WorkflowService:
    """
    Zentraler Workflow-Service
    
    Verwaltet:
    - Automatische Statusübergänge
    - Workflow-Regeln
    - Benachrichtigungen
    - Aktivitäts-Logging
    """
    
    # Definiere alle erlaubten Übergänge
    TRANSITIONS = {
        # === ANGEBOT → AUFTRAG ===
        (WorkflowStatus.OFFER_DRAFT, WorkflowStatus.OFFER_SENT): WorkflowTransition(
            WorkflowStatus.OFFER_DRAFT, WorkflowStatus.OFFER_SENT,
            creates_notification=True,
            next_actions=['email_send_offer']
        ),
        (WorkflowStatus.OFFER_SENT, WorkflowStatus.OFFER_ACCEPTED): WorkflowTransition(
            WorkflowStatus.OFFER_SENT, WorkflowStatus.OFFER_ACCEPTED,
            creates_notification=True,
            next_actions=['create_order_from_offer']
        ),
        (WorkflowStatus.OFFER_SENT, WorkflowStatus.OFFER_REJECTED): WorkflowTransition(
            WorkflowStatus.OFFER_SENT, WorkflowStatus.OFFER_REJECTED,
            creates_notification=True,
            next_actions=['log_rejection_reason']
        ),
        (WorkflowStatus.OFFER_SENT, WorkflowStatus.OFFER_EXPIRED): WorkflowTransition(
            WorkflowStatus.OFFER_SENT, WorkflowStatus.OFFER_EXPIRED,
            auto_trigger=True,  # Automatisch wenn Gültigkeitsdatum überschritten
            creates_notification=True
        ),
        
        # === AUFTRAG → DESIGN ===
        (WorkflowStatus.ORDER_CONFIRMED, WorkflowStatus.DESIGN_PENDING): WorkflowTransition(
            WorkflowStatus.ORDER_CONFIRMED, WorkflowStatus.DESIGN_PENDING,
            next_actions=['check_design_availability']
        ),
        (WorkflowStatus.DESIGN_PENDING, WorkflowStatus.DESIGN_ORDERED): WorkflowTransition(
            WorkflowStatus.DESIGN_PENDING, WorkflowStatus.DESIGN_ORDERED,
            creates_notification=True,
            next_actions=['create_design_order']
        ),
        (WorkflowStatus.DESIGN_ORDERED, WorkflowStatus.DESIGN_RECEIVED): WorkflowTransition(
            WorkflowStatus.DESIGN_ORDERED, WorkflowStatus.DESIGN_RECEIVED,
            creates_notification=True
        ),
        (WorkflowStatus.DESIGN_RECEIVED, WorkflowStatus.DESIGN_APPROVAL_SENT): WorkflowTransition(
            WorkflowStatus.DESIGN_RECEIVED, WorkflowStatus.DESIGN_APPROVAL_SENT,
            creates_notification=True,
            next_actions=['send_design_approval_email']
        ),
        (WorkflowStatus.DESIGN_APPROVAL_SENT, WorkflowStatus.DESIGN_APPROVED): WorkflowTransition(
            WorkflowStatus.DESIGN_APPROVAL_SENT, WorkflowStatus.DESIGN_APPROVED,
            creates_notification=True,
            next_actions=['check_material_availability']
        ),
        (WorkflowStatus.DESIGN_APPROVAL_SENT, WorkflowStatus.DESIGN_REJECTED): WorkflowTransition(
            WorkflowStatus.DESIGN_APPROVAL_SENT, WorkflowStatus.DESIGN_REJECTED,
            creates_notification=True,
            next_actions=['request_design_revision']
        ),
        
        # === MATERIAL ===
        (WorkflowStatus.DESIGN_APPROVED, WorkflowStatus.MATERIAL_PENDING): WorkflowTransition(
            WorkflowStatus.DESIGN_APPROVED, WorkflowStatus.MATERIAL_PENDING,
            auto_trigger=True
        ),
        (WorkflowStatus.MATERIAL_PENDING, WorkflowStatus.MATERIAL_ORDERED): WorkflowTransition(
            WorkflowStatus.MATERIAL_PENDING, WorkflowStatus.MATERIAL_ORDERED,
            creates_notification=True
        ),
        (WorkflowStatus.MATERIAL_ORDERED, WorkflowStatus.MATERIAL_RECEIVED): WorkflowTransition(
            WorkflowStatus.MATERIAL_ORDERED, WorkflowStatus.MATERIAL_RECEIVED,
            creates_notification=True,
            next_actions=['update_inventory', 'check_production_readiness']
        ),
        
        # === PRODUKTION ===
        (WorkflowStatus.MATERIAL_RECEIVED, WorkflowStatus.PRODUCTION_SCHEDULED): WorkflowTransition(
            WorkflowStatus.MATERIAL_RECEIVED, WorkflowStatus.PRODUCTION_SCHEDULED,
            auto_trigger=True
        ),
        (WorkflowStatus.DESIGN_APPROVED, WorkflowStatus.PRODUCTION_SCHEDULED): WorkflowTransition(
            WorkflowStatus.DESIGN_APPROVED, WorkflowStatus.PRODUCTION_SCHEDULED,
            # Wenn Material bereits vorhanden
        ),
        (WorkflowStatus.PRODUCTION_SCHEDULED, WorkflowStatus.PRODUCTION_IN_PROGRESS): WorkflowTransition(
            WorkflowStatus.PRODUCTION_SCHEDULED, WorkflowStatus.PRODUCTION_IN_PROGRESS,
            creates_notification=True
        ),
        (WorkflowStatus.PRODUCTION_IN_PROGRESS, WorkflowStatus.PRODUCTION_COMPLETED): WorkflowTransition(
            WorkflowStatus.PRODUCTION_IN_PROGRESS, WorkflowStatus.PRODUCTION_COMPLETED,
            creates_notification=True,
            next_actions=['record_thread_usage', 'create_packing_list']
        ),
        
        # === QM ===
        (WorkflowStatus.PRODUCTION_COMPLETED, WorkflowStatus.QC_PENDING): WorkflowTransition(
            WorkflowStatus.PRODUCTION_COMPLETED, WorkflowStatus.QC_PENDING,
            auto_trigger=True
        ),
        (WorkflowStatus.QC_PENDING, WorkflowStatus.QC_IN_PROGRESS): WorkflowTransition(
            WorkflowStatus.QC_PENDING, WorkflowStatus.QC_IN_PROGRESS
        ),
        (WorkflowStatus.QC_IN_PROGRESS, WorkflowStatus.QC_PASSED): WorkflowTransition(
            WorkflowStatus.QC_IN_PROGRESS, WorkflowStatus.QC_PASSED,
            creates_notification=True,
            next_actions=['proceed_to_packing']
        ),
        (WorkflowStatus.QC_IN_PROGRESS, WorkflowStatus.QC_FAILED): WorkflowTransition(
            WorkflowStatus.QC_IN_PROGRESS, WorkflowStatus.QC_FAILED,
            creates_notification=True,
            next_actions=['create_rework_order', 'notify_production']
        ),
        
        # === VERSAND ===
        (WorkflowStatus.QC_PASSED, WorkflowStatus.PACKING): WorkflowTransition(
            WorkflowStatus.QC_PASSED, WorkflowStatus.PACKING,
            auto_trigger=True
        ),
        (WorkflowStatus.PACKING, WorkflowStatus.READY_TO_SHIP): WorkflowTransition(
            WorkflowStatus.PACKING, WorkflowStatus.READY_TO_SHIP,
            creates_notification=True,
            next_actions=['create_delivery_note', 'notify_customer_ready']
        ),
        (WorkflowStatus.READY_TO_SHIP, WorkflowStatus.SHIPPED): WorkflowTransition(
            WorkflowStatus.READY_TO_SHIP, WorkflowStatus.SHIPPED,
            creates_notification=True,
            next_actions=['send_tracking_email', 'create_post_entry']
        ),
        (WorkflowStatus.READY_TO_SHIP, WorkflowStatus.PICKED_UP): WorkflowTransition(
            WorkflowStatus.READY_TO_SHIP, WorkflowStatus.PICKED_UP,
            creates_notification=True,
            next_actions=['record_pickup_signature']
        ),
        (WorkflowStatus.SHIPPED, WorkflowStatus.DELIVERED): WorkflowTransition(
            WorkflowStatus.SHIPPED, WorkflowStatus.DELIVERED,
            creates_notification=True
        ),
        
        # === ABSCHLUSS ===
        (WorkflowStatus.DELIVERED, WorkflowStatus.INVOICED): WorkflowTransition(
            WorkflowStatus.DELIVERED, WorkflowStatus.INVOICED,
            auto_trigger=True,
            next_actions=['create_invoice']
        ),
        (WorkflowStatus.PICKED_UP, WorkflowStatus.INVOICED): WorkflowTransition(
            WorkflowStatus.PICKED_UP, WorkflowStatus.INVOICED,
            auto_trigger=True,
            next_actions=['create_invoice']
        ),
        (WorkflowStatus.INVOICED, WorkflowStatus.PAID): WorkflowTransition(
            WorkflowStatus.INVOICED, WorkflowStatus.PAID,
            creates_notification=True
        ),
        (WorkflowStatus.PAID, WorkflowStatus.COMPLETED): WorkflowTransition(
            WorkflowStatus.PAID, WorkflowStatus.COMPLETED,
            auto_trigger=True
        ),
        (WorkflowStatus.COMPLETED, WorkflowStatus.ARCHIVED): WorkflowTransition(
            WorkflowStatus.COMPLETED, WorkflowStatus.ARCHIVED,
            # Nach 30 Tagen automatisch
        ),
    }
    
    def __init__(self):
        self.db = None
        self.notification_service = None
        
    def init_app(self, app, db):
        """Initialisiert den Service mit Flask-App"""
        self.db = db
        app.workflow_service = self
        
    def can_transition(self, order, to_status: WorkflowStatus) -> Tuple[bool, str]:
        """
        Prüft ob ein Übergang möglich ist
        
        Returns:
            (bool, str): (Möglich, Grund falls nicht)
        """
        from src.models.models import Order
        
        current_status = self._get_workflow_status(order)
        transition_key = (current_status, to_status)
        
        if transition_key not in self.TRANSITIONS:
            return False, f"Übergang von {current_status.value} zu {to_status.value} nicht erlaubt"
        
        transition = self.TRANSITIONS[transition_key]
        
        # Prüfe Bedingung falls vorhanden
        if transition.condition:
            if not transition.condition(order):
                return False, "Bedingungen für Übergang nicht erfüllt"
        
        # Spezielle Prüfungen
        if to_status == WorkflowStatus.PRODUCTION_IN_PROGRESS:
            can_start, reason = order.can_start_production()
            if not can_start:
                return False, reason
        
        return True, "OK"
    
    def transition(self, order, to_status: WorkflowStatus, 
                   user: str = 'system', 
                   comment: str = '',
                   skip_actions: bool = False) -> Dict:
        """
        Führt einen Workflow-Übergang durch
        
        Returns:
            Dict mit Ergebnis und ausgeführten Aktionen
        """
        from src.models.models import Order, OrderStatusHistory, ActivityLog
        
        result = {
            'success': False,
            'from_status': None,
            'to_status': to_status.value,
            'actions_executed': [],
            'notifications_sent': [],
            'errors': []
        }
        
        # Prüfe ob Übergang möglich
        can_do, reason = self.can_transition(order, to_status)
        if not can_do:
            result['errors'].append(reason)
            return result
        
        current_status = self._get_workflow_status(order)
        result['from_status'] = current_status.value
        
        transition = self.TRANSITIONS[(current_status, to_status)]
        
        try:
            # Status aktualisieren
            old_status = order.status
            order.workflow_status = to_status.value
            order.status = self._map_to_legacy_status(to_status)
            order.updated_at = datetime.utcnow()
            order.updated_by = user
            
            # Spezielle Felder je nach Status
            self._update_status_fields(order, to_status, user)
            
            # Status-Historie erstellen
            if transition.creates_activity:
                history = OrderStatusHistory(
                    order_id=order.id,
                    from_status=old_status,
                    to_status=order.status,
                    comment=comment or f"Workflow: {current_status.value} → {to_status.value}",
                    changed_by=user
                )
                self.db.session.add(history)
                
                # Activity Log
                activity = ActivityLog(
                    username=user,
                    action='workflow_transition',
                    details=f"Auftrag {order.id}: {current_status.value} → {to_status.value}"
                )
                self.db.session.add(activity)
            
            # Commit vor Aktionen
            self.db.session.commit()
            
            # Folgeaktionen ausführen
            if not skip_actions and transition.next_actions:
                for action in transition.next_actions:
                    try:
                        action_result = self._execute_action(action, order, user)
                        result['actions_executed'].append({
                            'action': action,
                            'success': action_result.get('success', True),
                            'details': action_result
                        })
                    except Exception as e:
                        result['errors'].append(f"Aktion {action} fehlgeschlagen: {str(e)}")
                        logger.error(f"Workflow action {action} failed: {e}")
            
            # Benachrichtigungen
            if transition.creates_notification:
                try:
                    notif_result = self._send_notification(order, current_status, to_status, user)
                    result['notifications_sent'].append(notif_result)
                except Exception as e:
                    result['errors'].append(f"Benachrichtigung fehlgeschlagen: {str(e)}")
            
            result['success'] = True
            logger.info(f"Workflow transition: Order {order.id} from {current_status.value} to {to_status.value}")
            
        except Exception as e:
            self.db.session.rollback()
            result['errors'].append(str(e))
            logger.error(f"Workflow transition failed: {e}")
        
        return result
    
    def get_available_transitions(self, order) -> List[Dict]:
        """
        Gibt alle möglichen nächsten Status zurück
        """
        current_status = self._get_workflow_status(order)
        available = []
        
        for (from_status, to_status), transition in self.TRANSITIONS.items():
            if from_status == current_status:
                can_do, reason = self.can_transition(order, to_status)
                available.append({
                    'status': to_status.value,
                    'label': self._get_status_label(to_status),
                    'available': can_do,
                    'reason': reason if not can_do else None,
                    'requires_confirmation': transition.requires_confirmation,
                    'auto_trigger': transition.auto_trigger
                })
        
        return available
    
    def check_auto_transitions(self, order) -> List[Dict]:
        """
        Prüft und führt automatische Übergänge durch
        """
        results = []
        current_status = self._get_workflow_status(order)
        
        for (from_status, to_status), transition in self.TRANSITIONS.items():
            if from_status == current_status and transition.auto_trigger:
                can_do, reason = self.can_transition(order, to_status)
                if can_do:
                    # Zusätzliche Bedingungsprüfung für Auto-Trigger
                    if self._check_auto_condition(order, to_status):
                        result = self.transition(order, to_status, user='system')
                        results.append(result)
                        
                        # Nach erfolgreichem Übergang rekursiv prüfen
                        if result['success']:
                            results.extend(self.check_auto_transitions(order))
                        break
        
        return results
    
    def get_workflow_progress(self, order) -> Dict:
        """
        Gibt den Workflow-Fortschritt als Prozent und Phase zurück
        """
        current_status = self._get_workflow_status(order)
        
        # Definiere Phasen und deren Gewichtung
        phases = [
            ('offer', [WorkflowStatus.OFFER_DRAFT, WorkflowStatus.OFFER_SENT], 5),
            ('order', [WorkflowStatus.ORDER_NEW, WorkflowStatus.ORDER_CONFIRMED], 10),
            ('design', [WorkflowStatus.DESIGN_PENDING, WorkflowStatus.DESIGN_ORDERED, 
                       WorkflowStatus.DESIGN_RECEIVED, WorkflowStatus.DESIGN_APPROVAL_SENT,
                       WorkflowStatus.DESIGN_APPROVED], 20),
            ('material', [WorkflowStatus.MATERIAL_PENDING, WorkflowStatus.MATERIAL_ORDERED,
                         WorkflowStatus.MATERIAL_RECEIVED], 15),
            ('production', [WorkflowStatus.PRODUCTION_SCHEDULED, WorkflowStatus.PRODUCTION_IN_PROGRESS,
                           WorkflowStatus.PRODUCTION_COMPLETED], 25),
            ('qc', [WorkflowStatus.QC_PENDING, WorkflowStatus.QC_IN_PROGRESS, 
                   WorkflowStatus.QC_PASSED], 10),
            ('shipping', [WorkflowStatus.PACKING, WorkflowStatus.READY_TO_SHIP,
                         WorkflowStatus.SHIPPED, WorkflowStatus.DELIVERED, WorkflowStatus.PICKED_UP], 10),
            ('completion', [WorkflowStatus.INVOICED, WorkflowStatus.PAID, 
                           WorkflowStatus.COMPLETED, WorkflowStatus.ARCHIVED], 5)
        ]
        
        total_progress = 0
        current_phase = 'unknown'
        current_phase_progress = 0
        
        found_current = False
        for phase_name, statuses, weight in phases:
            if current_status in statuses:
                current_phase = phase_name
                idx = statuses.index(current_status)
                current_phase_progress = ((idx + 1) / len(statuses)) * 100
                phase_progress = (idx / len(statuses)) * weight
                total_progress += phase_progress
                found_current = True
                break
            elif not found_current:
                total_progress += weight
        
        return {
            'total_progress': min(100, round(total_progress)),
            'current_phase': current_phase,
            'current_phase_label': self._get_phase_label(current_phase),
            'phase_progress': round(current_phase_progress),
            'current_status': current_status.value,
            'current_status_label': self._get_status_label(current_status)
        }
    
    # === Private Hilfsmethoden ===
    
    def _get_workflow_status(self, order) -> WorkflowStatus:
        """Ermittelt den aktuellen Workflow-Status"""
        if order.workflow_status:
            try:
                return WorkflowStatus(order.workflow_status)
            except ValueError:
                pass
        
        # Fallback: Mapping von altem Status
        status_map = {
            'new': WorkflowStatus.ORDER_NEW,
            'accepted': WorkflowStatus.ORDER_CONFIRMED,
            'in_progress': WorkflowStatus.PRODUCTION_IN_PROGRESS,
            'ready': WorkflowStatus.READY_TO_SHIP,
            'completed': WorkflowStatus.COMPLETED,
            'cancelled': WorkflowStatus.CANCELLED
        }
        return status_map.get(order.status, WorkflowStatus.ORDER_NEW)
    
    def _map_to_legacy_status(self, workflow_status: WorkflowStatus) -> str:
        """Mappt Workflow-Status auf Legacy-Status für Kompatibilität"""
        legacy_map = {
            WorkflowStatus.OFFER_DRAFT: 'draft',
            WorkflowStatus.OFFER_SENT: 'offer_sent',
            WorkflowStatus.ORDER_NEW: 'new',
            WorkflowStatus.ORDER_CONFIRMED: 'accepted',
            WorkflowStatus.DESIGN_PENDING: 'design_pending',
            WorkflowStatus.DESIGN_APPROVED: 'design_approved',
            WorkflowStatus.PRODUCTION_IN_PROGRESS: 'in_progress',
            WorkflowStatus.PRODUCTION_COMPLETED: 'production_done',
            WorkflowStatus.QC_PASSED: 'qc_passed',
            WorkflowStatus.PACKING: 'packing',
            WorkflowStatus.READY_TO_SHIP: 'ready',
            WorkflowStatus.SHIPPED: 'shipped',
            WorkflowStatus.DELIVERED: 'delivered',
            WorkflowStatus.PICKED_UP: 'picked_up',
            WorkflowStatus.INVOICED: 'invoiced',
            WorkflowStatus.PAID: 'paid',
            WorkflowStatus.COMPLETED: 'completed',
            WorkflowStatus.ARCHIVED: 'archived',
            WorkflowStatus.CANCELLED: 'cancelled'
        }
        return legacy_map.get(workflow_status, 'new')
    
    def _update_status_fields(self, order, status: WorkflowStatus, user: str):
        """Aktualisiert spezielle Felder je nach Status"""
        now = datetime.utcnow()
        
        if status == WorkflowStatus.PRODUCTION_IN_PROGRESS:
            order.production_start = now
        elif status == WorkflowStatus.PRODUCTION_COMPLETED:
            order.production_end = now
            if order.production_start:
                duration = now - order.production_start
                order.production_minutes = int(duration.total_seconds() / 60)
        elif status == WorkflowStatus.COMPLETED:
            order.completed_at = now
            order.completed_by = user
        elif status == WorkflowStatus.ARCHIVED:
            order.archived_at = now
            order.archived_by = user
        elif status == WorkflowStatus.DESIGN_APPROVAL_SENT:
            order.design_approval_status = 'sent'
            order.design_approval_sent_at = now
        elif status == WorkflowStatus.DESIGN_APPROVED:
            order.design_approval_status = 'approved'
            order.design_approval_date = now
    
    def _check_auto_condition(self, order, to_status: WorkflowStatus) -> bool:
        """Prüft zusätzliche Bedingungen für Auto-Trigger"""
        if to_status == WorkflowStatus.OFFER_EXPIRED:
            # Prüfe ob Angebot abgelaufen
            if order.offer_valid_until:
                from datetime import date
                return date.today() > order.offer_valid_until
            return False
        
        if to_status == WorkflowStatus.QC_PENDING:
            # Nur wenn QC in Settings aktiviert
            from src.models import CompanySettings
            settings = CompanySettings.get_settings()
            return settings.require_qc_before_packing
        
        if to_status == WorkflowStatus.INVOICED:
            # Nur wenn Auto-Rechnung aktiviert
            from src.models import CompanySettings
            settings = CompanySettings.get_settings()
            return getattr(settings, 'auto_create_invoice', False)
        
        return True
    
    def _execute_action(self, action: str, order, user: str) -> Dict:
        """Führt eine Workflow-Aktion aus"""
        action_handlers = {
            'create_packing_list': self._action_create_packing_list,
            'create_delivery_note': self._action_create_delivery_note,
            'create_invoice': self._action_create_invoice,
            'record_thread_usage': self._action_record_thread_usage,
            'send_design_approval_email': self._action_send_design_approval,
            'send_tracking_email': self._action_send_tracking_email,
            'notify_customer_ready': self._action_notify_customer_ready,
            'update_inventory': self._action_update_inventory,
            'create_post_entry': self._action_create_post_entry,
        }
        
        handler = action_handlers.get(action)
        if handler:
            return handler(order, user)
        else:
            logger.warning(f"Unknown workflow action: {action}")
            return {'success': False, 'error': f'Unbekannte Aktion: {action}'}
    
    def _action_create_packing_list(self, order, user: str) -> Dict:
        """Erstellt automatisch eine Packliste"""
        try:
            from src.models import PackingList
            
            # Prüfe ob bereits vorhanden
            existing = PackingList.query.filter_by(order_id=order.id).first()
            if existing:
                return {'success': True, 'skipped': True, 'reason': 'Packliste existiert bereits'}
            
            packing_list = PackingList(
                packing_list_number=PackingList.generate_packing_list_number(),
                order_id=order.id,
                customer_id=order.customer_id,
                status='ready',
                customer_notes=order.customer_notes or '',
                created_by=user
            )
            
            # Items aus Auftrag übernehmen
            items = []
            if order.items:
                for item in order.items:
                    items.append({
                        'article_id': item.article_id,
                        'name': item.article.name if item.article else 'Unbekannt',
                        'quantity': item.quantity,
                        'ean': item.article.ean if item.article else ''
                    })
            packing_list.set_items_list(items)
            
            self.db.session.add(packing_list)
            self.db.session.commit()
            
            order.packing_list_id = packing_list.id
            self.db.session.commit()
            
            return {'success': True, 'packing_list_id': packing_list.id}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _action_create_delivery_note(self, order, user: str) -> Dict:
        """Erstellt automatisch einen Lieferschein"""
        try:
            from src.models import DeliveryNote, PackingList
            
            # Hole Packliste
            packing_list = PackingList.query.filter_by(order_id=order.id).first()
            if not packing_list:
                return {'success': False, 'error': 'Keine Packliste vorhanden'}
            
            # Prüfe ob bereits vorhanden
            if packing_list.delivery_note_id:
                return {'success': True, 'skipped': True, 'reason': 'Lieferschein existiert bereits'}
            
            delivery_note = DeliveryNote(
                delivery_note_number=DeliveryNote.generate_delivery_note_number(),
                order_id=order.id,
                customer_id=order.customer_id,
                packing_list_id=packing_list.id,
                status='draft',
                created_by=user
            )
            
            self.db.session.add(delivery_note)
            self.db.session.commit()
            
            packing_list.delivery_note_id = delivery_note.id
            order.delivery_note_id = delivery_note.id
            self.db.session.commit()
            
            return {'success': True, 'delivery_note_id': delivery_note.id}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _action_create_invoice(self, order, user: str) -> Dict:
        """Erstellt automatisch eine Rechnung"""
        try:
            from src.models.rechnungsmodul import Rechnung, RechnungsStatus
            
            # Prüfe ob bereits vorhanden
            if order.invoice_id:
                return {'success': True, 'skipped': True, 'reason': 'Rechnung existiert bereits'}
            
            # Erstelle Rechnung
            rechnung = Rechnung.from_order(order, created_by=user)
            self.db.session.add(rechnung)
            self.db.session.commit()
            
            order.invoice_id = rechnung.id
            self.db.session.commit()
            
            return {'success': True, 'invoice_id': rechnung.id}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _action_record_thread_usage(self, order, user: str) -> Dict:
        """Erfasst Garnverbrauch"""
        try:
            from src.controllers.production_controller_db import _record_automatic_thread_usage
            _record_automatic_thread_usage(order)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _action_send_design_approval(self, order, user: str) -> Dict:
        """Sendet Design-Freigabe-E-Mail"""
        try:
            if not order.customer or not order.customer.email:
                return {'success': False, 'error': 'Keine Kunden-E-Mail'}
            
            # Generiere Token falls nicht vorhanden
            if not order.design_approval_token:
                order.generate_approval_token()
                self.db.session.commit()
            
            # E-Mail senden
            from src.services.email_service import EmailService
            email_service = EmailService()
            
            approval_url = f"/design-approval/{order.design_approval_token}"
            
            result = email_service.send_design_approval_request(
                to=order.customer.email,
                customer_name=order.customer.display_name,
                order_number=order.order_number,
                approval_url=approval_url
            )
            
            return result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _action_send_tracking_email(self, order, user: str) -> Dict:
        """Sendet Tracking-E-Mail"""
        try:
            if not order.customer or not order.customer.email:
                return {'success': False, 'error': 'Keine Kunden-E-Mail'}
            
            # Hole Tracking-Info
            shipment = order.shipments.first() if order.shipments else None
            if not shipment or not shipment.tracking_number:
                return {'success': True, 'skipped': True, 'reason': 'Keine Tracking-Nummer'}
            
            from src.services.email_service import EmailService
            email_service = EmailService()
            
            result = email_service.send_shipping_notification(
                to=order.customer.email,
                customer_name=order.customer.display_name,
                order_number=order.order_number,
                carrier=shipment.carrier,
                tracking_number=shipment.tracking_number
            )
            
            return result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _action_notify_customer_ready(self, order, user: str) -> Dict:
        """Benachrichtigt Kunden dass Auftrag abholbereit ist"""
        try:
            if order.delivery_type != 'pickup':
                return {'success': True, 'skipped': True, 'reason': 'Kein Abholauftrag'}
            
            if not order.customer or not order.customer.email:
                return {'success': False, 'error': 'Keine Kunden-E-Mail'}
            
            from src.services.email_service import EmailService
            email_service = EmailService()
            
            result = email_service.send_pickup_ready_notification(
                to=order.customer.email,
                customer_name=order.customer.display_name,
                order_number=order.order_number
            )
            
            return result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _action_update_inventory(self, order, user: str) -> Dict:
        """Aktualisiert Lagerbestand"""
        try:
            from src.models.models import Article
            
            updated = []
            for item in order.items:
                if item.article:
                    item.article.stock = (item.article.stock or 0) + item.quantity
                    updated.append(item.article_id)
            
            self.db.session.commit()
            return {'success': True, 'updated_articles': updated}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _action_create_post_entry(self, order, user: str) -> Dict:
        """Erstellt Postbuch-Eintrag"""
        try:
            from src.models import PostEntry
            
            # Prüfe ob bereits vorhanden
            existing = PostEntry.query.filter_by(order_id=order.id, type='outgoing').first()
            if existing:
                return {'success': True, 'skipped': True}
            
            post_entry = PostEntry(
                type='outgoing',
                customer_id=order.customer_id,
                order_id=order.id,
                status='sent',
                is_auto_created=True,
                created_by=user
            )
            
            self.db.session.add(post_entry)
            self.db.session.commit()
            
            return {'success': True, 'post_entry_id': post_entry.id}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _send_notification(self, order, from_status: WorkflowStatus, 
                          to_status: WorkflowStatus, user: str) -> Dict:
        """Sendet interne Benachrichtigung"""
        try:
            # TODO: Implementiere Notification-System
            # Für jetzt: Nur Log
            logger.info(f"NOTIFICATION: Order {order.id} changed from {from_status.value} to {to_status.value}")
            return {'success': True, 'type': 'log'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _get_status_label(self, status: WorkflowStatus) -> str:
        """Gibt deutschen Label für Status zurück"""
        labels = {
            WorkflowStatus.OFFER_DRAFT: 'Angebot (Entwurf)',
            WorkflowStatus.OFFER_SENT: 'Angebot versendet',
            WorkflowStatus.OFFER_ACCEPTED: 'Angebot angenommen',
            WorkflowStatus.OFFER_REJECTED: 'Angebot abgelehnt',
            WorkflowStatus.OFFER_EXPIRED: 'Angebot abgelaufen',
            WorkflowStatus.ORDER_NEW: 'Neuer Auftrag',
            WorkflowStatus.ORDER_CONFIRMED: 'Auftrag bestätigt',
            WorkflowStatus.DESIGN_PENDING: 'Design ausstehend',
            WorkflowStatus.DESIGN_ORDERED: 'Design bestellt',
            WorkflowStatus.DESIGN_RECEIVED: 'Design erhalten',
            WorkflowStatus.DESIGN_APPROVAL_SENT: 'Freigabe gesendet',
            WorkflowStatus.DESIGN_APPROVED: 'Design freigegeben',
            WorkflowStatus.DESIGN_REJECTED: 'Design abgelehnt',
            WorkflowStatus.MATERIAL_PENDING: 'Material ausstehend',
            WorkflowStatus.MATERIAL_ORDERED: 'Material bestellt',
            WorkflowStatus.MATERIAL_RECEIVED: 'Material eingetroffen',
            WorkflowStatus.PRODUCTION_SCHEDULED: 'Produktion geplant',
            WorkflowStatus.PRODUCTION_IN_PROGRESS: 'In Produktion',
            WorkflowStatus.PRODUCTION_COMPLETED: 'Produktion abgeschlossen',
            WorkflowStatus.QC_PENDING: 'QM ausstehend',
            WorkflowStatus.QC_IN_PROGRESS: 'QM läuft',
            WorkflowStatus.QC_PASSED: 'QM bestanden',
            WorkflowStatus.QC_FAILED: 'QM nicht bestanden',
            WorkflowStatus.PACKING: 'Wird verpackt',
            WorkflowStatus.READY_TO_SHIP: 'Versandbereit',
            WorkflowStatus.SHIPPED: 'Versendet',
            WorkflowStatus.DELIVERED: 'Zugestellt',
            WorkflowStatus.PICKED_UP: 'Abgeholt',
            WorkflowStatus.INVOICED: 'Rechnung erstellt',
            WorkflowStatus.PAID: 'Bezahlt',
            WorkflowStatus.COMPLETED: 'Abgeschlossen',
            WorkflowStatus.ARCHIVED: 'Archiviert',
            WorkflowStatus.ON_HOLD: 'Pausiert',
            WorkflowStatus.CANCELLED: 'Storniert'
        }
        return labels.get(status, status.value)
    
    def _get_phase_label(self, phase: str) -> str:
        """Gibt deutschen Label für Phase zurück"""
        labels = {
            'offer': 'Angebot',
            'order': 'Auftragserfassung',
            'design': 'Design',
            'material': 'Material',
            'production': 'Produktion',
            'qc': 'Qualitätskontrolle',
            'shipping': 'Versand',
            'completion': 'Abschluss'
        }
        return labels.get(phase, phase)


# Singleton-Instanz
workflow_service = WorkflowService()
