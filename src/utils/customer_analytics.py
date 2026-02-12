# -*- coding: utf-8 -*-
"""
Kunden-Analytics & Scoring System
=================================
Berechnet KPIs und Rankings für Kunden

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import func, and_, or_, desc
from src.models import db


class CustomerAnalytics:
    """
    Analysiert Kundendaten und berechnet Scores
    
    Metriken:
    - payment_score: Zahlungsmoral (0-100, höher = besser)
    - revenue_score: Umsatz-Ranking
    - engagement_score: Kontakt-Engagement
    - loyalty_score: Kundentreue
    - overall_score: Gewichteter Gesamtscore
    """
    
    # Gewichtungen für Gesamtscore
    WEIGHTS = {
        'payment': 0.30,      # 30% - Zahlungsmoral ist wichtig
        'revenue': 0.25,      # 25% - Umsatz
        'engagement': 0.20,   # 20% - Aktiver Kontakt
        'loyalty': 0.15,      # 15% - Treue
        'frequency': 0.10     # 10% - Auftragsfrequenz
    }
    
    def __init__(self, customer_id):
        self.customer_id = customer_id
        self._cache = {}
    
    @classmethod
    def get_all_rankings(cls, limit=50):
        """
        Holt Ranking aller Kunden nach verschiedenen Kriterien
        
        Returns: Dict mit verschiedenen Rankings
        """
        from src.models import Customer, Order
        
        today = date.today()
        year_ago = today - timedelta(days=365)
        six_months_ago = today - timedelta(days=180)
        thirty_days_ago = today - timedelta(days=30)
        
        rankings = {
            'top_revenue': [],
            'top_revenue_year': [],
            'best_payers': [],
            'worst_payers': [],
            'most_orders': [],
            'no_contact': [],
            'pending_follow_ups': [],
            'new_customers': [],
            'vip_customers': []
        }
        
        # === TOP UMSATZ (Gesamt) ===
        revenue_query = db.session.query(
            Customer.id,
            Customer.display_name,
            Customer.company_name,
            Customer.customer_type,
            func.sum(Order.total_price).label('total_revenue'),
            func.count(Order.id).label('order_count')
        ).outerjoin(Order, and_(
            Order.customer_id == Customer.id,
            Order.status.notin_(['cancelled'])
        )).filter(
            Customer.is_active == True
        ).group_by(Customer.id).order_by(
            desc('total_revenue')
        ).limit(limit)
        
        for row in revenue_query:
            rankings['top_revenue'].append({
                'customer_id': row.id,
                'name': row.display_name or row.company_name,
                'type': row.customer_type,
                'total_revenue': float(row.total_revenue or 0),
                'order_count': row.order_count
            })
        
        # === TOP UMSATZ (letztes Jahr) ===
        revenue_year_query = db.session.query(
            Customer.id,
            Customer.display_name,
            Customer.company_name,
            func.sum(Order.total_price).label('revenue_year'),
            func.count(Order.id).label('orders_year')
        ).outerjoin(Order, and_(
            Order.customer_id == Customer.id,
            Order.status.notin_(['cancelled']),
            Order.created_at >= year_ago
        )).filter(
            Customer.is_active == True
        ).group_by(Customer.id).having(
            func.sum(Order.total_price) > 0
        ).order_by(
            desc('revenue_year')
        ).limit(limit)
        
        for row in revenue_year_query:
            rankings['top_revenue_year'].append({
                'customer_id': row.id,
                'name': row.display_name or row.company_name,
                'revenue_year': float(row.revenue_year or 0),
                'orders_year': row.orders_year
            })
        
        # === MEISTE AUFTRÄGE ===
        orders_query = db.session.query(
            Customer.id,
            Customer.display_name,
            Customer.company_name,
            func.count(Order.id).label('order_count'),
            func.avg(Order.total_price).label('avg_order_value')
        ).outerjoin(Order, and_(
            Order.customer_id == Customer.id,
            Order.status.notin_(['cancelled'])
        )).filter(
            Customer.is_active == True
        ).group_by(Customer.id).having(
            func.count(Order.id) > 0
        ).order_by(
            desc('order_count')
        ).limit(limit)
        
        for row in orders_query:
            rankings['most_orders'].append({
                'customer_id': row.id,
                'name': row.display_name or row.company_name,
                'order_count': row.order_count,
                'avg_order_value': float(row.avg_order_value or 0)
            })
        
        # === ZAHLUNGSMORAL ===
        try:
            from src.models.rechnungsmodul import Rechnung, RechnungsZahlung, RechnungsStatus
            
            # Beste Zahler (schnellste Zahlung nach Fälligkeit)
            payment_query = db.session.query(
                Customer.id,
                Customer.display_name,
                Customer.company_name,
                func.count(Rechnung.id).label('invoice_count'),
                func.avg(
                    func.julianday(RechnungsZahlung.zahlung_datum) - 
                    func.julianday(Rechnung.faelligkeitsdatum)
                ).label('avg_payment_days')
            ).join(Rechnung, Rechnung.kunde_id == Customer.id
            ).join(RechnungsZahlung, RechnungsZahlung.rechnung_id == Rechnung.id
            ).filter(
                Customer.is_active == True,
                Rechnung.status == RechnungsStatus.BEZAHLT.value,
                RechnungsZahlung.bestaetigt == True
            ).group_by(Customer.id).having(
                func.count(Rechnung.id) >= 2  # Mindestens 2 Rechnungen
            ).order_by('avg_payment_days').limit(limit)
            
            for row in payment_query:
                avg_days = row.avg_payment_days or 0
                rankings['best_payers'].append({
                    'customer_id': row.id,
                    'name': row.display_name or row.company_name,
                    'invoice_count': row.invoice_count,
                    'avg_payment_days': round(avg_days, 1),
                    'rating': cls._payment_rating(avg_days)
                })
            
            # Schlechteste Zahler
            worst_query = db.session.query(
                Customer.id,
                Customer.display_name,
                Customer.company_name,
                func.count(Rechnung.id).label('overdue_count'),
                func.sum(Rechnung.summe_brutto).label('overdue_amount')
            ).join(Rechnung, Rechnung.kunde_id == Customer.id
            ).filter(
                Customer.is_active == True,
                Rechnung.status == RechnungsStatus.UEBERFAELLIG.value
            ).group_by(Customer.id).order_by(
                desc('overdue_amount')
            ).limit(limit)
            
            for row in worst_query:
                rankings['worst_payers'].append({
                    'customer_id': row.id,
                    'name': row.display_name or row.company_name,
                    'overdue_count': row.overdue_count,
                    'overdue_amount': float(row.overdue_amount or 0)
                })
                
        except ImportError:
            pass  # Rechnungsmodul nicht verfügbar
        
        # === KEIN KONTAKT SEIT 30+ TAGEN ===
        try:
            from src.models import ProductionBlock
            
            # Subquery: Letzter Kontakt pro Kunde
            last_contact_subq = db.session.query(
                ProductionBlock.customer_id,
                func.max(ProductionBlock.start_date).label('last_contact')
            ).filter(
                ProductionBlock.is_active == True,
                ProductionBlock.block_type.in_(['call_in', 'call_out', 'customer_visit', 'site_visit', 'email'])
            ).group_by(ProductionBlock.customer_id).subquery()
            
            no_contact_query = db.session.query(
                Customer.id,
                Customer.display_name,
                Customer.company_name,
                Customer.phone,
                Customer.email,
                last_contact_subq.c.last_contact
            ).outerjoin(
                last_contact_subq, last_contact_subq.c.customer_id == Customer.id
            ).filter(
                Customer.is_active == True,
                or_(
                    last_contact_subq.c.last_contact == None,
                    last_contact_subq.c.last_contact < thirty_days_ago
                )
            ).order_by(last_contact_subq.c.last_contact.asc().nullsfirst()).limit(limit)
            
            for row in no_contact_query:
                days_since = None
                if row.last_contact:
                    days_since = (today - row.last_contact).days
                
                rankings['no_contact'].append({
                    'customer_id': row.id,
                    'name': row.display_name or row.company_name,
                    'phone': row.phone,
                    'email': row.email,
                    'last_contact': row.last_contact.strftime('%d.%m.%Y') if row.last_contact else 'Nie',
                    'days_since': days_since
                })
            
            # === FÄLLIGE WIEDERVORLAGEN ===
            follow_ups_query = db.session.query(
                ProductionBlock
            ).join(Customer, Customer.id == ProductionBlock.customer_id
            ).filter(
                ProductionBlock.is_active == True,
                ProductionBlock.follow_up_date <= today,
                ProductionBlock.follow_up_date.isnot(None)
            ).order_by(ProductionBlock.follow_up_date).limit(limit)
            
            for block in follow_ups_query:
                days_overdue = (today - block.follow_up_date).days
                rankings['pending_follow_ups'].append({
                    'customer_id': block.customer_id,
                    'name': block.customer.display_name if block.customer else 'Unbekannt',
                    'activity_type': block.type_label,
                    'title': block.title,
                    'follow_up_date': block.follow_up_date.strftime('%d.%m.%Y'),
                    'days_overdue': days_overdue,
                    'follow_up_notes': block.follow_up_notes
                })
                
        except ImportError:
            pass  # ProductionBlock nicht verfügbar
        
        # === NEUE KUNDEN (letzte 30 Tage) ===
        new_customers_query = Customer.query.filter(
            Customer.is_active == True,
            Customer.created_at >= thirty_days_ago
        ).order_by(Customer.created_at.desc()).limit(limit)
        
        for customer in new_customers_query:
            rankings['new_customers'].append({
                'customer_id': customer.id,
                'name': customer.display_name,
                'type': customer.customer_type,
                'created_at': customer.created_at.strftime('%d.%m.%Y') if customer.created_at else '-',
                'email': customer.email,
                'phone': customer.phone
            })
        
        # === VIP KUNDEN (Score-basiert) ===
        rankings['vip_customers'] = cls.calculate_vip_customers(limit=20)
        
        return rankings
    
    @classmethod
    def calculate_vip_customers(cls, limit=20):
        """
        Berechnet VIP-Kunden basierend auf gewichtetem Score
        """
        from src.models import Customer, Order
        
        today = date.today()
        year_ago = today - timedelta(days=365)
        
        vip_list = []
        
        # Alle aktiven Kunden mit Aufträgen
        customers_query = db.session.query(
            Customer.id,
            Customer.display_name,
            Customer.company_name,
            Customer.customer_type,
            Customer.created_at,
            func.sum(Order.total_price).label('total_revenue'),
            func.count(Order.id).label('order_count')
        ).outerjoin(Order, and_(
            Order.customer_id == Customer.id,
            Order.status.notin_(['cancelled'])
        )).filter(
            Customer.is_active == True
        ).group_by(Customer.id).having(
            func.count(Order.id) > 0
        )
        
        # Maximale Werte für Normalisierung ermitteln
        max_revenue = db.session.query(func.max(Order.total_price)).scalar() or 1
        max_orders = db.session.query(
            func.count(Order.id)
        ).group_by(Order.customer_id).order_by(
            desc(func.count(Order.id))
        ).first()
        max_orders = max_orders[0] if max_orders else 1
        
        for row in customers_query:
            # Scores berechnen (0-100)
            revenue_score = min(100, (float(row.total_revenue or 0) / float(max_revenue)) * 100)
            frequency_score = min(100, (row.order_count / max_orders) * 100)
            
            # Treue-Score (Jahre als Kunde)
            if row.created_at:
                years_customer = (today - row.created_at.date()).days / 365
                loyalty_score = min(100, years_customer * 20)  # 5 Jahre = 100
            else:
                loyalty_score = 0
            
            # Gesamtscore
            overall_score = (
                revenue_score * cls.WEIGHTS['revenue'] +
                frequency_score * cls.WEIGHTS['frequency'] +
                loyalty_score * cls.WEIGHTS['loyalty']
            ) / (cls.WEIGHTS['revenue'] + cls.WEIGHTS['frequency'] + cls.WEIGHTS['loyalty']) * 100
            
            vip_list.append({
                'customer_id': row.id,
                'name': row.display_name or row.company_name,
                'type': row.customer_type,
                'total_revenue': float(row.total_revenue or 0),
                'order_count': row.order_count,
                'years_customer': round((today - row.created_at.date()).days / 365, 1) if row.created_at else 0,
                'revenue_score': round(revenue_score, 1),
                'frequency_score': round(frequency_score, 1),
                'loyalty_score': round(loyalty_score, 1),
                'overall_score': round(overall_score, 1)
            })
        
        # Nach Gesamtscore sortieren
        vip_list.sort(key=lambda x: x['overall_score'], reverse=True)
        
        return vip_list[:limit]
    
    @classmethod
    def _payment_rating(cls, avg_days):
        """
        Bewertet Zahlungsmoral basierend auf Tagen nach Fälligkeit
        
        < 0 (vor Fälligkeit): ⭐⭐⭐⭐⭐
        0-7 Tage: ⭐⭐⭐⭐
        8-14 Tage: ⭐⭐⭐
        15-30 Tage: ⭐⭐
        > 30 Tage: ⭐
        """
        if avg_days < 0:
            return '⭐⭐⭐⭐⭐'
        elif avg_days <= 7:
            return '⭐⭐⭐⭐'
        elif avg_days <= 14:
            return '⭐⭐⭐'
        elif avg_days <= 30:
            return '⭐⭐'
        else:
            return '⭐'
    
    @classmethod
    def get_customer_detail_stats(cls, customer_id):
        """
        Detaillierte Statistiken für einen einzelnen Kunden
        """
        from src.models import Customer, Order
        
        customer = Customer.query.get(customer_id)
        if not customer:
            return None
        
        today = date.today()
        year_ago = today - timedelta(days=365)
        six_months_ago = today - timedelta(days=180)
        
        stats = {
            'customer_id': customer_id,
            'name': customer.display_name,
            'customer_since': customer.created_at,
            'years_customer': 0,
            'revenue': {
                'total': 0,
                'last_year': 0,
                'last_6_months': 0,
                'avg_order_value': 0
            },
            'orders': {
                'total': 0,
                'last_year': 0,
                'completed': 0,
                'cancelled': 0
            },
            'payment': {
                'invoices_total': 0,
                'invoices_paid': 0,
                'invoices_overdue': 0,
                'avg_payment_days': None,
                'rating': None
            },
            'engagement': {
                'last_contact': None,
                'days_since_contact': None,
                'total_activities': 0,
                'calls': 0,
                'visits': 0,
                'emails': 0,
                'complaints': 0,
                'pending_follow_ups': 0
            },
            'scores': {
                'revenue_score': 0,
                'payment_score': 0,
                'engagement_score': 0,
                'loyalty_score': 0,
                'overall_score': 0
            }
        }
        
        # Kunde seit
        if customer.created_at:
            stats['years_customer'] = round((today - customer.created_at.date()).days / 365, 1)
        
        # === AUFTRÄGE & UMSATZ ===
        orders = Order.query.filter_by(customer_id=customer_id).all()
        
        for order in orders:
            if order.status == 'cancelled':
                stats['orders']['cancelled'] += 1
                continue
            
            stats['orders']['total'] += 1
            stats['revenue']['total'] += float(order.total_price or 0)
            
            if order.status == 'completed':
                stats['orders']['completed'] += 1
            
            if order.created_at:
                if order.created_at.date() >= year_ago:
                    stats['orders']['last_year'] += 1
                    stats['revenue']['last_year'] += float(order.total_price or 0)
                
                if order.created_at.date() >= six_months_ago:
                    stats['revenue']['last_6_months'] += float(order.total_price or 0)
        
        if stats['orders']['total'] > 0:
            stats['revenue']['avg_order_value'] = stats['revenue']['total'] / stats['orders']['total']
        
        # === ZAHLUNGEN ===
        try:
            from src.models.rechnungsmodul import Rechnung, RechnungsZahlung, RechnungsStatus
            
            invoices = Rechnung.query.filter_by(kunde_id=customer_id).all()
            payment_days_list = []
            
            for invoice in invoices:
                stats['payment']['invoices_total'] += 1
                
                if invoice.status == RechnungsStatus.BEZAHLT.value:
                    stats['payment']['invoices_paid'] += 1
                    
                    # Zahlungsdauer berechnen
                    for payment in invoice.zahlungen:
                        if payment.bestaetigt and payment.zahlung_datum:
                            days = (payment.zahlung_datum - invoice.faelligkeitsdatum).days
                            payment_days_list.append(days)
                            
                elif invoice.status == RechnungsStatus.UEBERFAELLIG.value:
                    stats['payment']['invoices_overdue'] += 1
            
            if payment_days_list:
                stats['payment']['avg_payment_days'] = round(sum(payment_days_list) / len(payment_days_list), 1)
                stats['payment']['rating'] = cls._payment_rating(stats['payment']['avg_payment_days'])
                
        except ImportError:
            pass
        
        # === CRM AKTIVITÄTEN ===
        try:
            from src.models import ProductionBlock
            
            activities = ProductionBlock.query.filter(
                ProductionBlock.customer_id == customer_id,
                ProductionBlock.is_active == True
            ).all()
            
            for activity in activities:
                stats['engagement']['total_activities'] += 1
                
                if activity.block_type in ['call_in', 'call_out']:
                    stats['engagement']['calls'] += 1
                elif activity.block_type in ['customer_visit', 'site_visit']:
                    stats['engagement']['visits'] += 1
                elif activity.block_type == 'email':
                    stats['engagement']['emails'] += 1
                elif activity.block_type == 'complaint':
                    stats['engagement']['complaints'] += 1
                
                if activity.follow_up_date and activity.follow_up_date <= today:
                    stats['engagement']['pending_follow_ups'] += 1
            
            # Letzter Kontakt
            last_contact = ProductionBlock.query.filter(
                ProductionBlock.customer_id == customer_id,
                ProductionBlock.is_active == True,
                ProductionBlock.block_type.in_(['call_in', 'call_out', 'customer_visit', 'site_visit', 'email'])
            ).order_by(ProductionBlock.start_date.desc()).first()
            
            if last_contact:
                stats['engagement']['last_contact'] = last_contact.start_date
                stats['engagement']['days_since_contact'] = (today - last_contact.start_date).days
                
        except ImportError:
            pass
        
        # === SCORES BERECHNEN ===
        # Revenue Score (0-100)
        # Basierend auf Jahresumsatz, 10.000€ = 100
        stats['scores']['revenue_score'] = min(100, stats['revenue']['last_year'] / 100)
        
        # Payment Score
        if stats['payment']['avg_payment_days'] is not None:
            if stats['payment']['avg_payment_days'] <= 0:
                stats['scores']['payment_score'] = 100
            elif stats['payment']['avg_payment_days'] <= 7:
                stats['scores']['payment_score'] = 80
            elif stats['payment']['avg_payment_days'] <= 14:
                stats['scores']['payment_score'] = 60
            elif stats['payment']['avg_payment_days'] <= 30:
                stats['scores']['payment_score'] = 40
            else:
                stats['scores']['payment_score'] = 20
        else:
            stats['scores']['payment_score'] = 50  # Neutral
        
        # Engagement Score
        if stats['engagement']['days_since_contact'] is not None:
            if stats['engagement']['days_since_contact'] <= 7:
                stats['scores']['engagement_score'] = 100
            elif stats['engagement']['days_since_contact'] <= 30:
                stats['scores']['engagement_score'] = 80
            elif stats['engagement']['days_since_contact'] <= 60:
                stats['scores']['engagement_score'] = 60
            elif stats['engagement']['days_since_contact'] <= 90:
                stats['scores']['engagement_score'] = 40
            else:
                stats['scores']['engagement_score'] = 20
        else:
            stats['scores']['engagement_score'] = 0
        
        # Loyalty Score (Jahre als Kunde)
        stats['scores']['loyalty_score'] = min(100, stats['years_customer'] * 20)
        
        # Overall Score
        stats['scores']['overall_score'] = round(
            stats['scores']['revenue_score'] * cls.WEIGHTS['revenue'] +
            stats['scores']['payment_score'] * cls.WEIGHTS['payment'] +
            stats['scores']['engagement_score'] * cls.WEIGHTS['engagement'] +
            stats['scores']['loyalty_score'] * cls.WEIGHTS['loyalty'],
            1
        )
        
        return stats
    
    @classmethod
    def get_dashboard_summary(cls):
        """
        Zusammenfassung für Dashboard-Widgets
        """
        from src.models import Customer, Order
        
        today = date.today()
        month_ago = today - timedelta(days=30)
        
        summary = {
            'total_customers': Customer.query.filter_by(is_active=True).count(),
            'new_customers_month': Customer.query.filter(
                Customer.is_active == True,
                Customer.created_at >= month_ago
            ).count(),
            'total_revenue_month': 0,
            'total_orders_month': 0,
            'pending_follow_ups': 0,
            'overdue_invoices': 0,
            'customers_no_contact': 0
        }
        
        # Umsatz & Aufträge letzter Monat
        orders_month = Order.query.filter(
            Order.created_at >= month_ago,
            Order.status.notin_(['cancelled'])
        ).all()
        
        summary['total_orders_month'] = len(orders_month)
        summary['total_revenue_month'] = sum(float(o.total_price or 0) for o in orders_month)
        
        # Fällige Wiedervorlagen
        try:
            from src.models import ProductionBlock
            summary['pending_follow_ups'] = ProductionBlock.query.filter(
                ProductionBlock.is_active == True,
                ProductionBlock.follow_up_date <= today,
                ProductionBlock.follow_up_date.isnot(None)
            ).count()
        except:
            pass
        
        # Überfällige Rechnungen
        try:
            from src.models.rechnungsmodul import Rechnung, RechnungsStatus
            summary['overdue_invoices'] = Rechnung.query.filter(
                Rechnung.status == RechnungsStatus.UEBERFAELLIG.value
            ).count()
        except:
            pass
        
        return summary
