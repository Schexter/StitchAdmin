# -*- coding: utf-8 -*-
"""
LAGER- UND BESTANDSMANAGEMENT SERVICE
======================================
Bestandsreservierung, Verfügbarkeitsprüfung und Lageroptimierung

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
import json
import logging

from src.models.models import db, Article, Order, OrderItem

logger = logging.getLogger(__name__)


class ReservationStatus(Enum):
    """Status einer Bestandsreservierung"""
    PENDING = 'pending'           # Reservierung angefragt
    CONFIRMED = 'confirmed'       # Reservierung bestätigt
    PARTIALLY = 'partially'       # Teilweise reserviert
    RELEASED = 'released'         # Reservierung aufgehoben
    CONSUMED = 'consumed'         # Bestand verbraucht (produziert)
    EXPIRED = 'expired'           # Reservierung abgelaufen


class StockReservation(db.Model):
    """
    Bestandsreservierung
    
    Reserviert Artikel für einen Auftrag bis zur Produktion
    """
    __tablename__ = 'stock_reservations'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Verknüpfungen
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), nullable=False)
    order_id = db.Column(db.String(50), db.ForeignKey('orders.id'))
    order_item_id = db.Column(db.Integer, db.ForeignKey('order_items.id'))
    
    # Reservierung
    quantity_requested = db.Column(db.Integer, nullable=False)
    quantity_reserved = db.Column(db.Integer, default=0)
    quantity_consumed = db.Column(db.Integer, default=0)
    
    # Status
    status = db.Column(db.Enum(ReservationStatus), default=ReservationStatus.PENDING)
    
    # Gültigkeit
    valid_until = db.Column(db.DateTime)  # Automatische Freigabe nach Ablauf
    
    # Preisinfo zum Zeitpunkt der Reservierung
    unit_price = db.Column(db.Float)
    
    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    notes = db.Column(db.Text)
    
    # Relationships
    article = db.relationship('Article', backref=db.backref('reservations', lazy='dynamic'))
    order = db.relationship('Order', backref=db.backref('stock_reservations', lazy='dynamic'))
    order_item = db.relationship('OrderItem', backref=db.backref('stock_reservation', uselist=False))
    
    @property
    def is_fulfilled(self) -> bool:
        """Prüft ob Reservierung vollständig erfüllt"""
        return self.quantity_reserved >= self.quantity_requested
    
    @property
    def shortage(self) -> int:
        """Gibt Fehlmenge zurück"""
        return max(0, self.quantity_requested - self.quantity_reserved)
    
    @property
    def is_expired(self) -> bool:
        """Prüft ob Reservierung abgelaufen"""
        if self.valid_until:
            return datetime.utcnow() > self.valid_until
        return False
    
    def confirm(self):
        """Bestätigt Reservierung"""
        if self.quantity_reserved >= self.quantity_requested:
            self.status = ReservationStatus.CONFIRMED
        elif self.quantity_reserved > 0:
            self.status = ReservationStatus.PARTIALLY
        else:
            self.status = ReservationStatus.PENDING
    
    def release(self, quantity: int = None):
        """
        Gibt reservierten Bestand frei
        
        Args:
            quantity: Optional - Teilmenge freigeben
        """
        if quantity is None:
            quantity = self.quantity_reserved
        
        quantity = min(quantity, self.quantity_reserved)
        
        if quantity > 0 and self.article:
            # Bestand wieder erhöhen
            self.article.stock = (self.article.stock or 0) + quantity
            self.quantity_reserved -= quantity
        
        if self.quantity_reserved <= 0:
            self.status = ReservationStatus.RELEASED
    
    def consume(self, quantity: int = None):
        """
        Verbraucht reservierten Bestand (bei Produktion)
        
        Args:
            quantity: Optional - Teilmenge verbrauchen
        """
        if quantity is None:
            quantity = self.quantity_reserved
        
        quantity = min(quantity, self.quantity_reserved)
        
        self.quantity_consumed += quantity
        self.quantity_reserved -= quantity
        
        if self.quantity_reserved <= 0:
            self.status = ReservationStatus.CONSUMED
    
    def __repr__(self):
        return f'<StockReservation {self.id}: Art.{self.article_id} x{self.quantity_requested}>'


class InventoryService:
    """
    Zentraler Lager-Service
    
    Features:
    - Bestandsprüfung
    - Reservierung
    - Verfügbarkeitsberechnung
    - Nachbestellvorschläge
    - Bestandsbewegungen
    """
    
    def __init__(self):
        self.db = db
    
    # ==========================================
    # VERFÜGBARKEIT
    # ==========================================
    
    def get_availability(self, article_id: int) -> Dict:
        """
        Gibt vollständige Verfügbarkeitsinfo für Artikel
        
        Returns:
            Dict mit stock, reserved, available, pending_orders
        """
        article = Article.query.get(article_id)
        
        if not article:
            return {
                'article_id': article_id,
                'error': 'Artikel nicht gefunden'
            }
        
        # Aktuelle Reservierungen
        active_reservations = StockReservation.query.filter(
            StockReservation.article_id == article_id,
            StockReservation.status.in_([
                ReservationStatus.PENDING,
                ReservationStatus.CONFIRMED,
                ReservationStatus.PARTIALLY
            ])
        ).all()
        
        reserved = sum(r.quantity_reserved for r in active_reservations)
        pending_requested = sum(r.shortage for r in active_reservations)
        
        # Offene Bestellungen (Material unterwegs)
        from src.models.models import SupplierOrder
        pending_orders = SupplierOrder.query.filter(
            SupplierOrder.status.in_(['ordered', 'shipped']),
            SupplierOrder.items.any(article_id=article_id)
        ).all() if hasattr(SupplierOrder, 'items') else []
        
        incoming = 0
        for order in pending_orders:
            for item in order.items:
                if item.article_id == article_id:
                    incoming += item.quantity
        
        physical_stock = article.stock or 0
        available = physical_stock - reserved
        
        return {
            'article_id': article_id,
            'article_number': article.article_number,
            'article_name': article.name,
            'physical_stock': physical_stock,
            'reserved': reserved,
            'available': max(0, available),
            'pending_requested': pending_requested,
            'incoming': incoming,
            'projected_stock': physical_stock + incoming,
            'min_stock': article.min_stock or 0,
            'max_stock': article.max_stock or 0,
            'needs_reorder': physical_stock < (article.min_stock or 0),
            'reorder_quantity': self._calculate_reorder_quantity(article)
        }
    
    def check_availability_for_order(self, order_items: List[Dict]) -> Dict:
        """
        Prüft Verfügbarkeit für eine Liste von Auftragspositionen
        
        Args:
            order_items: [{'article_id': int, 'quantity': int}, ...]
        
        Returns:
            Dict mit Gesamtprüfung und Details pro Artikel
        """
        result = {
            'all_available': True,
            'partially_available': False,
            'items': []
        }
        
        for item in order_items:
            article_id = item.get('article_id')
            requested = item.get('quantity', 0)
            
            availability = self.get_availability(article_id)
            available = availability.get('available', 0)
            
            item_result = {
                'article_id': article_id,
                'article_name': availability.get('article_name', 'Unbekannt'),
                'requested': requested,
                'available': available,
                'shortage': max(0, requested - available),
                'is_available': available >= requested
            }
            
            result['items'].append(item_result)
            
            if not item_result['is_available']:
                result['all_available'] = False
                if available > 0:
                    result['partially_available'] = True
        
        return result
    
    # ==========================================
    # RESERVIERUNG
    # ==========================================
    
    def reserve_for_order(self, order, created_by: str = 'system') -> Dict:
        """
        Reserviert Bestand für einen Auftrag
        
        Args:
            order: Order-Objekt
            created_by: Username
        
        Returns:
            Dict mit Erfolg und Details
        """
        result = {
            'success': True,
            'fully_reserved': True,
            'reservations': [],
            'shortages': []
        }
        
        # Gültigkeit: 7 Tage oder bis Lieferdatum
        if order.due_date:
            valid_until = order.due_date
        else:
            valid_until = datetime.utcnow() + timedelta(days=7)
        
        for item in order.items:
            if not item.article_id:
                continue
            
            reservation_result = self.create_reservation(
                article_id=item.article_id,
                quantity=item.quantity,
                order_id=order.id,
                order_item_id=item.id,
                valid_until=valid_until,
                created_by=created_by
            )
            
            result['reservations'].append(reservation_result)
            
            if not reservation_result.get('fully_reserved'):
                result['fully_reserved'] = False
                
                if reservation_result.get('shortage', 0) > 0:
                    result['shortages'].append({
                        'article_id': item.article_id,
                        'article_name': item.article.name if item.article else 'Unbekannt',
                        'shortage': reservation_result['shortage']
                    })
        
        # Order-Status aktualisieren
        if result['shortages']:
            order.material_status = 'shortage'
            result['success'] = False
        else:
            order.material_status = 'reserved'
        
        db.session.commit()
        
        return result
    
    def create_reservation(self,
                           article_id: int,
                           quantity: int,
                           order_id: str = None,
                           order_item_id: int = None,
                           valid_until: datetime = None,
                           created_by: str = 'system') -> Dict:
        """
        Erstellt einzelne Reservierung
        """
        result = {
            'article_id': article_id,
            'requested': quantity,
            'reserved': 0,
            'shortage': quantity,
            'fully_reserved': False,
            'reservation_id': None
        }
        
        try:
            article = Article.query.get(article_id)
            if not article:
                result['error'] = 'Artikel nicht gefunden'
                return result
            
            # Verfügbaren Bestand ermitteln
            available = self.get_availability(article_id)['available']
            
            # Reservierbare Menge
            reservable = min(quantity, available)
            
            # Reservierung erstellen
            reservation = StockReservation(
                article_id=article_id,
                order_id=order_id,
                order_item_id=order_item_id,
                quantity_requested=quantity,
                quantity_reserved=reservable,
                unit_price=article.selling_price or article.purchase_price,
                valid_until=valid_until,
                created_by=created_by
            )
            
            # Status setzen
            if reservable >= quantity:
                reservation.status = ReservationStatus.CONFIRMED
                result['fully_reserved'] = True
            elif reservable > 0:
                reservation.status = ReservationStatus.PARTIALLY
            else:
                reservation.status = ReservationStatus.PENDING
            
            # Bestand reduzieren
            if reservable > 0:
                article.stock = (article.stock or 0) - reservable
            
            db.session.add(reservation)
            db.session.flush()
            
            result['reserved'] = reservable
            result['shortage'] = quantity - reservable
            result['reservation_id'] = reservation.id
            
            logger.info(f"Reservation created: Art.{article_id} x{reservable}/{quantity}")
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Reservation failed: {e}")
        
        return result
    
    def release_reservation(self, reservation_id: int, quantity: int = None) -> Dict:
        """Gibt Reservierung frei"""
        reservation = StockReservation.query.get(reservation_id)
        
        if not reservation:
            return {'success': False, 'error': 'Reservierung nicht gefunden'}
        
        try:
            reservation.release(quantity)
            db.session.commit()
            
            return {
                'success': True,
                'released': quantity or reservation.quantity_reserved
            }
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def release_order_reservations(self, order_id: str) -> Dict:
        """Gibt alle Reservierungen eines Auftrags frei"""
        reservations = StockReservation.query.filter_by(order_id=order_id).all()
        
        released_count = 0
        for res in reservations:
            if res.status not in [ReservationStatus.RELEASED, ReservationStatus.CONSUMED]:
                res.release()
                released_count += 1
        
        db.session.commit()
        
        return {
            'success': True,
            'released_count': released_count
        }
    
    def consume_order_reservations(self, order_id: str) -> Dict:
        """Verbraucht Reservierungen bei Produktionsabschluss"""
        reservations = StockReservation.query.filter_by(order_id=order_id).all()
        
        consumed_count = 0
        for res in reservations:
            if res.status in [ReservationStatus.CONFIRMED, ReservationStatus.PARTIALLY]:
                res.consume()
                consumed_count += 1
        
        db.session.commit()
        
        return {
            'success': True,
            'consumed_count': consumed_count
        }
    
    def cleanup_expired_reservations(self) -> int:
        """Bereinigt abgelaufene Reservierungen"""
        now = datetime.utcnow()
        
        expired = StockReservation.query.filter(
            StockReservation.valid_until < now,
            StockReservation.status.in_([
                ReservationStatus.PENDING,
                ReservationStatus.CONFIRMED,
                ReservationStatus.PARTIALLY
            ])
        ).all()
        
        count = 0
        for res in expired:
            res.status = ReservationStatus.EXPIRED
            res.release()
            count += 1
        
        db.session.commit()
        
        logger.info(f"Cleaned up {count} expired reservations")
        return count
    
    # ==========================================
    # BESTANDSBEWEGUNGEN
    # ==========================================
    
    def book_stock_movement(self,
                            article_id: int,
                            quantity: int,
                            movement_type: str,
                            reference: str = None,
                            notes: str = None,
                            user: str = 'system') -> Dict:
        """
        Bucht Bestandsbewegung
        
        Args:
            article_id: Artikel-ID
            quantity: Menge (positiv = Zugang, negativ = Abgang)
            movement_type: 'incoming', 'outgoing', 'adjustment', 'production', 'return'
            reference: Referenz (Bestellnummer, etc.)
            notes: Notizen
            user: Benutzer
        """
        article = Article.query.get(article_id)
        
        if not article:
            return {'success': False, 'error': 'Artikel nicht gefunden'}
        
        try:
            old_stock = article.stock or 0
            new_stock = old_stock + quantity
            
            # Prüfe auf negativen Bestand
            if new_stock < 0:
                return {
                    'success': False,
                    'error': f'Bestand würde negativ werden ({new_stock})'
                }
            
            # Bestand aktualisieren
            article.stock = new_stock
            
            # Bewegung protokollieren
            from src.models.models import StockMovement
            
            movement = StockMovement(
                article_id=article_id,
                quantity=quantity,
                movement_type=movement_type,
                old_stock=old_stock,
                new_stock=new_stock,
                reference=reference,
                notes=notes,
                created_by=user
            )
            db.session.add(movement)
            db.session.commit()
            
            logger.info(f"Stock movement: Art.{article_id} {movement_type} {quantity:+d} ({old_stock}→{new_stock})")
            
            return {
                'success': True,
                'old_stock': old_stock,
                'new_stock': new_stock,
                'movement_id': movement.id
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Stock movement failed: {e}")
            return {'success': False, 'error': str(e)}
    
    # ==========================================
    # NACHBESTELLUNGEN
    # ==========================================
    
    def get_reorder_suggestions(self) -> List[Dict]:
        """
        Gibt Liste von Artikeln die nachbestellt werden sollten
        """
        suggestions = []
        
        # Artikel unter Mindestbestand
        articles = Article.query.filter(
            Article.min_stock.isnot(None),
            Article.min_stock > 0
        ).all()
        
        for article in articles:
            availability = self.get_availability(article.id)
            
            if availability['available'] < article.min_stock:
                suggestions.append({
                    'article_id': article.id,
                    'article_number': article.article_number,
                    'article_name': article.name,
                    'current_stock': availability['physical_stock'],
                    'available': availability['available'],
                    'reserved': availability['reserved'],
                    'min_stock': article.min_stock,
                    'max_stock': article.max_stock or 0,
                    'incoming': availability['incoming'],
                    'suggested_quantity': self._calculate_reorder_quantity(article),
                    'supplier_id': article.supplier_id,
                    'supplier_name': article.supplier.name if article.supplier else None,
                    'priority': 'high' if availability['available'] <= 0 else 'normal'
                })
        
        # Sortiere nach Priorität
        suggestions.sort(key=lambda x: (0 if x['priority'] == 'high' else 1, x['available']))
        
        return suggestions
    
    def _calculate_reorder_quantity(self, article) -> int:
        """Berechnet optimale Nachbestellmenge"""
        if not article:
            return 0
        
        current_stock = article.stock or 0
        min_stock = article.min_stock or 0
        max_stock = article.max_stock or (min_stock * 3)
        
        if current_stock >= min_stock:
            return 0
        
        # Bestelle bis Max-Bestand
        needed = max_stock - current_stock
        
        # Runde auf Bestelleinheit (falls definiert)
        order_unit = getattr(article, 'order_unit', 1) or 1
        if order_unit > 1:
            needed = ((needed + order_unit - 1) // order_unit) * order_unit
        
        return max(0, needed)
    
    # ==========================================
    # INVENTUR
    # ==========================================
    
    def perform_inventory_count(self,
                                 article_id: int,
                                 counted_quantity: int,
                                 user: str,
                                 location: str = None,
                                 notes: str = None) -> Dict:
        """
        Führt Inventurzählung durch
        
        Args:
            article_id: Artikel-ID
            counted_quantity: Gezählte Menge
            user: Zähler
            location: Optional - Lagerort
            notes: Optional - Bemerkungen
        """
        article = Article.query.get(article_id)
        
        if not article:
            return {'success': False, 'error': 'Artikel nicht gefunden'}
        
        try:
            old_stock = article.stock or 0
            difference = counted_quantity - old_stock
            
            # Bestand anpassen
            article.stock = counted_quantity
            article.last_inventory_date = datetime.utcnow()
            article.last_inventory_by = user
            
            # Bewegung buchen wenn Differenz
            if difference != 0:
                from src.models.models import StockMovement
                
                movement = StockMovement(
                    article_id=article_id,
                    quantity=difference,
                    movement_type='inventory_adjustment',
                    old_stock=old_stock,
                    new_stock=counted_quantity,
                    reference=f'Inventur {datetime.now().strftime("%Y-%m-%d")}',
                    notes=notes or f'Inventurdifferenz: {difference:+d}',
                    created_by=user
                )
                db.session.add(movement)
            
            db.session.commit()
            
            logger.info(f"Inventory count: Art.{article_id} {old_stock}→{counted_quantity} (diff: {difference:+d})")
            
            return {
                'success': True,
                'old_stock': old_stock,
                'new_stock': counted_quantity,
                'difference': difference
            }
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}


# Globale Instanz
inventory_service = InventoryService()
