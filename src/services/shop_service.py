# -*- coding: utf-8 -*-
"""
Shop-Service für StitchAdmin
Preiskalkulation, Warenkorb und Bestellerstellung

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import uuid
import logging
from datetime import datetime
from flask import session

logger = logging.getLogger(__name__)

CART_SESSION_KEY = 'shop_cart'


# ============================================================
# WARENKORB (Session-basiert)
# ============================================================

def get_cart():
    """Warenkorb aus Session laden"""
    return session.get(CART_SESSION_KEY, [])


def add_to_cart(item):
    """
    Artikel + Veredelung zum Warenkorb hinzufügen.

    item = {
        'article_id': str,
        'article_name': str,
        'variant_id': int or None,
        'variant_info': str (z.B. 'Rot / XL'),
        'quantity': int,
        'unit_price': float,
        'finishings': [{
            'finishing_type_id': int,
            'finishing_name': str,
            'finishing_type': str (stick/druck/...),
            'position': str,
            'design_template_id': int or None,
            'design_name': str,
            'stitch_count': int or None,
            'details': str,
            'setup_price': float,
            'price_per_piece': float,
        }],
        'notes': str
    }
    """
    cart = get_cart()
    cart.append(item)
    session[CART_SESSION_KEY] = cart
    session.modified = True
    return len(cart)


def update_cart_item(index, quantity):
    """Menge eines Warenkorb-Artikels ändern"""
    cart = get_cart()
    if 0 <= index < len(cart):
        if quantity <= 0:
            cart.pop(index)
        else:
            cart[index]['quantity'] = quantity
        session[CART_SESSION_KEY] = cart
        session.modified = True
    return cart


def remove_from_cart(index):
    """Artikel aus Warenkorb entfernen"""
    cart = get_cart()
    if 0 <= index < len(cart):
        cart.pop(index)
        session[CART_SESSION_KEY] = cart
        session.modified = True
    return cart


def clear_cart():
    """Warenkorb leeren"""
    session.pop(CART_SESSION_KEY, None)
    session.modified = True


def get_cart_count():
    """Anzahl der Artikel im Warenkorb"""
    return len(get_cart())


# ============================================================
# PREISKALKULATION
# ============================================================

def calculate_finishing_price(finishing_type, stitch_count=None, quantity=1, width_mm=None, height_mm=None):
    """
    Berechnet den Preis für eine Veredelung.

    Args:
        finishing_type: ShopFinishingType Objekt
        stitch_count: Stichzahl (für Stickerei)
        quantity: Menge
        width_mm: Breite in mm (für Größenzuschlag)
        height_mm: Höhe in mm (für Größenzuschlag)

    Returns:
        dict: {setup: float, per_piece: float, total: float, details: str}
    """
    setup = finishing_type.setup_price or 0
    per_piece = finishing_type.price_per_piece or 0
    details = ''

    if finishing_type.finishing_type == 'stick' and stitch_count:
        # Stickerei: Setup + Stichpreis * Menge
        price_1000 = finishing_type.price_per_1000_stitches or 0
        per_piece = (stitch_count / 1000) * price_1000
        details = f'{stitch_count:,} Stiche × {price_1000:.2f}€/1000'

    elif finishing_type.finishing_type in ('flex', 'flock'):
        # Flex/Flock: Größenzuschlag prüfen
        surcharges = finishing_type.get_size_surcharges()
        if surcharges and width_mm:
            for threshold, surcharge in sorted(surcharges.items()):
                threshold_mm = int(threshold.replace('>', '').replace('mm', ''))
                if width_mm > threshold_mm:
                    per_piece += surcharge
                    details = f'Größenzuschlag +{surcharge:.2f}€'

    total = setup + (per_piece * quantity)

    return {
        'setup': round(setup, 2),
        'per_piece': round(per_piece, 2),
        'total': round(total, 2),
        'details': details
    }


def calculate_item_total(item):
    """Berechnet den Gesamtpreis eines Warenkorb-Artikels"""
    quantity = item.get('quantity', 1)
    unit_price = item.get('unit_price', 0)

    # Textilpreis
    textile_total = unit_price * quantity

    # Veredelungspreise
    finishing_total = 0
    for f in item.get('finishings', []):
        f_setup = f.get('setup_price', 0)
        f_per_piece = f.get('price_per_piece', 0)
        finishing_total += f_setup + (f_per_piece * quantity)

    return round(textile_total + finishing_total, 2)


def calculate_cart_total():
    """Berechnet Gesamtpreis des Warenkorbs inkl. MwSt."""
    cart = get_cart()
    subtotal = 0

    for item in cart:
        subtotal += calculate_item_total(item)

    # MwSt. berechnen
    try:
        from src.models.settings import TaxRate
        tax_rate = TaxRate.get_default_rate()
    except Exception:
        tax_rate = 19.0

    tax_amount = round(subtotal * (tax_rate / 100), 2)
    total = round(subtotal + tax_amount, 2)

    return {
        'subtotal': subtotal,
        'tax_rate': tax_rate,
        'tax_amount': tax_amount,
        'total': total,
        'item_count': len(cart)
    }


# ============================================================
# BESTELLERSTELLUNG
# ============================================================

def create_order_from_cart(customer_data, cart=None):
    """
    Erstellt eine Bestellung aus dem Warenkorb.

    Args:
        customer_data: dict mit Kundendaten
            {first_name, last_name, email, phone, company_name,
             street, house_number, postal_code, city, notes}
        cart: Warenkorb-Items (optional, sonst aus Session)

    Returns:
        Order Objekt mit tracking_token
    """
    from src.models.models import db, Customer, Order, OrderItem
    from src.models.order_workflow import OrderDesign

    if cart is None:
        cart = get_cart()

    if not cart:
        raise ValueError("Warenkorb ist leer")

    # 1. Kunden finden oder anlegen
    customer = _find_or_create_customer(customer_data)

    # 2. Auftrag erstellen
    order_id = str(uuid.uuid4())
    tracking_token = uuid.uuid4().hex

    # Auftragsnummer generieren
    order_number = _generate_order_number()

    # Gesamtpreis berechnen
    totals = calculate_cart_total()

    order = Order(
        id=order_id,
        customer_id=customer.id,
        order_number=order_number,
        order_type='mixed',
        status='new',
        workflow_status='confirmed',
        source='shop',
        tracking_token=tracking_token,
        customer_email_for_tracking=customer_data.get('email'),
        total_price=totals['total'],
        customer_notes=customer_data.get('notes', ''),
        delivery_type='shipping',
        created_at=datetime.utcnow()
    )
    db.session.add(order)

    # 3. Positionen erstellen
    for item in cart:
        order_item = OrderItem(
            order_id=order_id,
            article_id=item.get('article_id'),
            quantity=item.get('quantity', 1),
            unit_price=item.get('unit_price', 0),
            textile_size=item.get('variant_info', ''),
            textile_color=item.get('variant_info', ''),
            position_details=item.get('notes', '')
        )
        db.session.add(order_item)
        db.session.flush()  # ID generieren

        # 4. Veredelungen als OrderDesign erstellen
        for finishing in item.get('finishings', []):
            design_type_map = {
                'stick': 'stick',
                'druck': 'druck',
                'flex': 'flex',
                'flock': 'flock',
                'dtf': 'druck',
                'sublimation': 'druck',
                'tassendruck': 'druck'
            }
            order_design = OrderDesign(
                order_id=order_id,
                position=finishing.get('position', 'brust_links'),
                design_type=design_type_map.get(finishing.get('finishing_type'), 'stick'),
                design_name=finishing.get('design_name', ''),
                stitch_count=finishing.get('stitch_count'),
                setup_price=finishing.get('setup_price', 0),
                price_per_piece=finishing.get('price_per_piece', 0),
                approval_status='pending'
            )
            db.session.add(order_design)

    db.session.commit()

    # 5. Warenkorb leeren
    clear_cart()

    logger.info(f"Shop-Bestellung {order_number} erstellt (Token: {tracking_token})")

    return order


def _find_or_create_customer(data):
    """Kunden anhand E-Mail finden oder neu anlegen"""
    from src.models.models import db, Customer

    email = data.get('email', '').strip().lower()
    if email:
        customer = Customer.query.filter_by(email=email).first()
        if customer:
            return customer

    # Neuen Kunden anlegen - fortlaufende Kundennummer (KD001, KD002, ...)
    from src.controllers.customer_controller_db import generate_customer_id
    customer_id = generate_customer_id()
    customer_type = 'business' if data.get('company_name') else 'private'

    customer = Customer(
        id=customer_id,
        customer_type=customer_type,
        first_name=data.get('first_name', ''),
        last_name=data.get('last_name', ''),
        email=email,
        phone=data.get('phone', ''),
        company_name=data.get('company_name', ''),
        street=data.get('street', ''),
        house_number=data.get('house_number', ''),
        postal_code=data.get('postal_code', ''),
        city=data.get('city', ''),
        country='Deutschland',
        created_at=datetime.utcnow(),
        created_by='shop'
    )
    db.session.add(customer)
    db.session.flush()

    return customer


def _generate_order_number():
    """Generiert eine neue Auftragsnummer"""
    from src.models.models import Order
    from datetime import date

    today = date.today()
    prefix = f"WEB-{today.strftime('%Y%m')}-"

    # Höchste Nummer dieses Monats finden
    last_order = Order.query.filter(
        Order.order_number.like(f'{prefix}%')
    ).order_by(Order.order_number.desc()).first()

    if last_order:
        try:
            last_num = int(last_order.order_number.replace(prefix, ''))
            return f"{prefix}{last_num + 1:04d}"
        except ValueError:
            pass

    return f"{prefix}0001"


def get_order_by_tracking_token(token):
    """Bestellung anhand Tracking-Token finden"""
    from src.models.models import Order
    return Order.query.filter_by(tracking_token=token).first()
