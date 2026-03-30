# -*- coding: utf-8 -*-
"""
ORDER SERVICE
=============
Zentrale Geschaeftslogik fuer alle Auftrags-Operationen.

Regeln:
- Preisberechnung: Eine Quelle der Wahrheit
- Status-Transitionen: Zentral validiert
- Ein Commit pro Operation (atomar)
- Controller rufen nur diesen Service auf

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from src.models import db
from src.models.models import Order, OrderItem, Article
from flask_login import current_user
import logging

logger = logging.getLogger(__name__)


# =========================================================================
# ERLAUBTE STATUS-TRANSITIONEN
# =========================================================================

# status (Produktionsstatus)
VALID_STATUS_TRANSITIONS = {
    'new':         ['accepted', 'cancelled'],
    'accepted':    ['in_progress', 'cancelled'],
    'in_progress': ['ready', 'cancelled'],
    'ready':       ['completed', 'in_progress'],  # Zurueck moeglich
    'completed':   ['ready'],  # Korrektur moeglich
    'cancelled':   ['new'],    # Reaktivierung
}

# workflow_status (Gesamtablauf)
VALID_WORKFLOW_TRANSITIONS = {
    'offer':            ['confirmed', 'cancelled'],
    'confirmed':        ['design_pending', 'in_production', 'cancelled'],
    'design_pending':   ['design_approved', 'confirmed', 'cancelled'],
    'design_approved':  ['in_production', 'cancelled'],
    'in_production':    ['packing', 'ready_to_ship', 'cancelled'],
    'packing':          ['ready_to_ship', 'in_production'],
    'ready_to_ship':    ['shipped', 'packing'],
    'shipped':          ['invoiced', 'completed'],
    'invoiced':         ['completed', 'shipped'],
    'completed':        ['shipped'],  # Korrektur
    'cancelled':        ['confirmed'],
}


class OrderService:
    """Zentrale Geschaeftslogik fuer Auftraege"""

    # =====================================================================
    # PREISBERECHNUNG (Eine Quelle der Wahrheit)
    # =====================================================================

    @staticmethod
    def berechne_gesamtpreis(order_id: str, speichern: bool = True) -> Tuple[float, Dict]:
        """
        Berechnet den Gesamtpreis eines Auftrags aus allen Komponenten.

        Formel:
          Artikelsumme + Design-Positionen + Design-Kosten + Anpassungskosten
          - Rabatt (%)

        Args:
            order_id: Auftrags-ID
            speichern: True = in DB speichern, False = nur berechnen

        Returns:
            Tuple (Gesamtpreis, Detail-Dict)
        """
        order = Order.query.get(order_id)
        if not order:
            return 0.0, {'error': 'Auftrag nicht gefunden'}

        details = {
            'artikel_summe': 0.0,
            'design_positionen_summe': 0.0,
            'design_kosten': 0.0,
            'anpassungskosten': 0.0,
            'zwischensumme': 0.0,
            'rabatt_prozent': float(order.discount_percent or 0),
            'rabatt_betrag': 0.0,
            'gesamt': 0.0,
            'positionen': []
        }

        # 1. Artikelsumme
        items = OrderItem.query.filter_by(order_id=order_id).all()
        total_qty = 0
        for item in items:
            preis = float(item.unit_price or 0)
            if not preis and item.article_id:
                article = Article.query.get(item.article_id)
                if article and article.price:
                    preis = float(article.price)
                    # Preis auf Item setzen fuer Konsistenz
                    if speichern:
                        item.unit_price = preis

            menge = int(item.quantity or 0)
            total_qty += menge
            pos_summe = menge * preis

            details['artikel_summe'] += pos_summe
            details['positionen'].append({
                'artikel': item.article_id,
                'menge': menge,
                'einzelpreis': preis,
                'summe': pos_summe
            })

        if total_qty == 0:
            total_qty = 1

        # 2. Design-Positionen (Multi-Design / OrderDesign)
        try:
            from src.models.order_workflow import OrderDesign
            designs = OrderDesign.query.filter_by(order_id=order_id).all()
            for design in designs:
                setup = float(design.setup_price or 0)
                per_piece = float(design.price_per_piece or 0) * total_qty
                supplier = float(design.supplier_cost or 0)
                details['design_positionen_summe'] += setup + per_piece + supplier
        except ImportError:
            pass

        # 3. Design-Kosten (Order-Level)
        details['design_kosten'] = float(order.design_cost or 0)
        details['anpassungskosten'] = float(order.adaptation_cost or 0)

        # 4. Zwischensumme
        details['zwischensumme'] = (
            details['artikel_summe'] +
            details['design_positionen_summe'] +
            details['design_kosten'] +
            details['anpassungskosten']
        )

        # 5. Rabatt
        if details['rabatt_prozent'] > 0:
            details['rabatt_betrag'] = round(
                details['zwischensumme'] * details['rabatt_prozent'] / 100, 2
            )

        # 6. Gesamtpreis
        details['gesamt'] = round(
            details['zwischensumme'] - details['rabatt_betrag'], 2
        )

        # In DB speichern
        if speichern and details['gesamt'] > 0:
            order.total_price = details['gesamt']

        return details['gesamt'], details

    @staticmethod
    def aktualisiere_preis_wenn_noetig(order: Order):
        """
        Aktualisiert den Preis nur wenn er 0 oder nicht gesetzt ist.
        Wird nach Item-Aenderungen aufgerufen.
        """
        if not order.total_price or order.total_price <= 0:
            preis, _ = OrderService.berechne_gesamtpreis(order.id, speichern=True)
            return preis
        return order.total_price

    # =====================================================================
    # STATUS-TRANSITIONEN
    # =====================================================================

    @staticmethod
    def update_status(order_id: str, neuer_status: str,
                      kommentar: str = '') -> Tuple[bool, str]:
        """
        Aendert den Produktions-Status eines Auftrags mit Validierung.

        Returns:
            Tuple (Erfolg, Nachricht)
        """
        order = Order.query.get(order_id)
        if not order:
            return False, 'Auftrag nicht gefunden'

        alter_status = order.status

        # Validierung: Ist die Transition erlaubt?
        erlaubte = VALID_STATUS_TRANSITIONS.get(alter_status, [])
        if neuer_status not in erlaubte:
            return False, f'Status-Wechsel von "{alter_status}" nach "{neuer_status}" nicht erlaubt. Erlaubt: {", ".join(erlaubte)}'

        # Design-Validierung fuer Produktionsstart
        if neuer_status == 'in_progress':
            ok, msg = OrderService._validate_production_start(order)
            if not ok:
                return False, msg

        username = current_user.username if current_user.is_authenticated else 'System'

        try:
            order.status = neuer_status
            order.updated_at = datetime.utcnow()
            order.updated_by = username

            # Spezielle Felder je nach Status
            if neuer_status == 'in_progress':
                order.production_start = datetime.utcnow()
            elif neuer_status == 'ready':
                order.production_end = datetime.utcnow()
            elif neuer_status == 'completed':
                order.completed_at = datetime.utcnow()
                order.completed_by = username

            # Status-Historie
            OrderService._add_status_history(
                order_id, alter_status, neuer_status, kommentar, username
            )

            db.session.commit()

            # E-Mail Automation (nicht-blockierend)
            OrderService._trigger_email_automation(order, neuer_status, alter_status)

            logger.info(f"Auftrag {order_id}: {alter_status} -> {neuer_status}")
            return True, f'Status auf "{neuer_status}" geaendert'

        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler bei Status-Update {order_id}: {e}")
            return False, str(e)

    @staticmethod
    def update_workflow_status(order_id: str, neuer_status: str,
                               kommentar: str = '') -> Tuple[bool, str]:
        """
        Aendert den Workflow-Status eines Auftrags mit Validierung.

        Returns:
            Tuple (Erfolg, Nachricht)
        """
        order = Order.query.get(order_id)
        if not order:
            return False, 'Auftrag nicht gefunden'

        alter_status = order.workflow_status or 'confirmed'
        username = current_user.username if current_user.is_authenticated else 'System'

        # Validierung
        erlaubte = VALID_WORKFLOW_TRANSITIONS.get(alter_status, [])
        if neuer_status not in erlaubte:
            return False, f'Workflow-Wechsel von "{alter_status}" nach "{neuer_status}" nicht erlaubt'

        try:
            order.workflow_status = neuer_status
            order.updated_at = datetime.utcnow()
            order.updated_by = username

            # Spezielle Felder je nach Workflow-Status
            if neuer_status == 'in_production' and not order.production_start:
                order.production_start = datetime.utcnow()
            elif neuer_status == 'completed':
                order.completed_at = datetime.utcnow()
                order.completed_by = username
            elif neuer_status == 'shipped':
                if not order.production_end:
                    order.production_end = datetime.utcnow()

            # Status-Historie
            OrderService._add_status_history(
                order_id, f'wf:{alter_status}', f'wf:{neuer_status}', kommentar, username
            )

            db.session.commit()
            logger.info(f"Auftrag {order_id} Workflow: {alter_status} -> {neuer_status}")
            return True, f'Workflow-Status auf "{neuer_status}" geaendert'

        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler bei Workflow-Update {order_id}: {e}")
            return False, str(e)

    # =====================================================================
    # ARTIKEL-VERWALTUNG
    # =====================================================================

    @staticmethod
    def add_items(order_id: str, items_data: List[Dict]) -> Tuple[bool, str]:
        """
        Fuegt Artikel zu einem Auftrag hinzu und aktualisiert den Preis.

        Args:
            order_id: Auftrags-ID
            items_data: Liste von Dicts mit article_id, quantity, size, color, unit_price

        Returns:
            Tuple (Erfolg, Nachricht)
        """
        order = Order.query.get(order_id)
        if not order:
            return False, 'Auftrag nicht gefunden'

        try:
            for item_data in items_data:
                article_id = item_data.get('article_id')
                if not article_id:
                    continue

                preis = float(item_data.get('unit_price', 0) or 0)
                if not preis:
                    article = Article.query.get(article_id)
                    if article and article.price:
                        preis = float(article.price)

                item = OrderItem(
                    order_id=order_id,
                    article_id=article_id,
                    quantity=int(item_data.get('quantity', 1)),
                    textile_size=item_data.get('size', ''),
                    textile_color=item_data.get('color', ''),
                    unit_price=preis
                )
                db.session.add(item)

            db.session.flush()

            # Preis aktualisieren
            OrderService.aktualisiere_preis_wenn_noetig(order)

            db.session.commit()
            return True, f'{len(items_data)} Artikel hinzugefuegt'

        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler beim Hinzufuegen von Artikeln: {e}")
            return False, str(e)

    @staticmethod
    def update_items(order_id: str, existing_items: Dict, new_items: List[Dict]) -> Tuple[bool, str]:
        """
        Aktualisiert bestehende Items und fuegt neue hinzu.

        Args:
            existing_items: Dict von item_id -> {quantity, unit_price, size, color}
            new_items: Liste neuer Items

        Returns:
            Tuple (Erfolg, Nachricht)
        """
        order = Order.query.get(order_id)
        if not order:
            return False, 'Auftrag nicht gefunden'

        try:
            # Bestehende Items aktualisieren
            for item_id_str, data in existing_items.items():
                item = OrderItem.query.get(int(item_id_str))
                if item and item.order_id == order_id:
                    item.quantity = int(data.get('quantity', item.quantity))
                    if 'unit_price' in data and data['unit_price']:
                        item.unit_price = float(data['unit_price'])
                    if 'size' in data:
                        item.textile_size = data['size']
                    if 'color' in data:
                        item.textile_color = data['color']

            # Neue Items hinzufuegen
            if new_items:
                for item_data in new_items:
                    article_id = item_data.get('article_id')
                    if not article_id:
                        continue
                    preis = float(item_data.get('unit_price', 0) or 0)
                    if not preis:
                        article = Article.query.get(article_id)
                        if article and article.price:
                            preis = float(article.price)

                    db.session.add(OrderItem(
                        order_id=order_id,
                        article_id=article_id,
                        quantity=int(item_data.get('quantity', 1)),
                        textile_size=item_data.get('size', ''),
                        textile_color=item_data.get('color', ''),
                        unit_price=preis
                    ))

            db.session.flush()
            OrderService.aktualisiere_preis_wenn_noetig(order)
            db.session.commit()
            return True, 'Artikel aktualisiert'

        except Exception as e:
            db.session.rollback()
            logger.error(f"Fehler beim Aktualisieren der Artikel: {e}")
            return False, str(e)

    # =====================================================================
    # HILFSMETHODEN (privat)
    # =====================================================================

    @staticmethod
    def _validate_production_start(order: Order) -> Tuple[bool, str]:
        """Prueft ob die Produktion gestartet werden kann"""
        # Methode am Model nutzen wenn vorhanden
        if hasattr(order, 'can_start_production'):
            return order.can_start_production()

        # Fallback: Design muss vorhanden sein
        if not order.design_file and not order.design_file_path:
            return False, 'Design fehlt - Produktion kann nicht gestartet werden'

        return True, ''

    @staticmethod
    def _add_status_history(order_id: str, von: str, nach: str,
                             kommentar: str, username: str):
        """Fuegt einen Eintrag in die Status-Historie hinzu"""
        try:
            from src.models import OrderStatusHistory
            db.session.add(OrderStatusHistory(
                order_id=order_id,
                from_status=von,
                to_status=nach,
                comment=kommentar,
                changed_by=username
            ))
        except (ImportError, Exception) as e:
            logger.warning(f"Status-Historie konnte nicht gespeichert werden: {e}")

    @staticmethod
    def _trigger_email_automation(order: Order, neuer_status: str, alter_status: str):
        """Loest E-Mail-Automations aus (nicht-blockierend)"""
        try:
            from src.services.email_automation_service import EmailAutomationService
            automation = EmailAutomationService()
            automation.check_and_send(order, 'order_status', neuer_status, alter_status)
        except Exception as e:
            logger.warning(f"Email-Automation Fehler: {e}")
