# -*- coding: utf-8 -*-
"""
ID GENERATOR SERVICE
====================
Zentrale ID-Erzeugung fuer alle Entities.

Ersetzt:
- order_controller_db.generate_order_id()      -> IdGenerator.order()
- article_controller_db.generate_article_id()   -> IdGenerator.article()
- customer_controller_db.generate_customer_id()  -> IdGenerator.customer()
- supplier_controller_db.generate_supplier_id()  -> IdGenerator.supplier()
- machine_controller_db.generate_machine_id()    -> IdGenerator.machine()
- shipping_controller_db.generate_shipment_id()  -> IdGenerator.shipment()

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import re
from datetime import datetime
from src.models import db


class IdGenerator:
    """Zentrale ID-Generierung mit konfigurierbaren Formaten"""

    @staticmethod
    def _next_sequence(model_class, prefix, separator='-', pad=3):
        """
        Generiert die naechste fortlaufende ID.

        Args:
            model_class: SQLAlchemy Model-Klasse
            prefix: ID-Praefix (z.B. 'A2026', 'KD', 'ART')
            separator: Trennzeichen (z.B. '-')
            pad: Anzahl Stellen (z.B. 3 -> 001)

        Returns:
            Neue ID als String (z.B. 'A2026-042')
        """
        full_prefix = f"{prefix}{separator}"
        pattern = f"{full_prefix}%"

        # Hoechste existierende Nummer finden
        last = model_class.query.filter(
            model_class.id.like(pattern)
        ).order_by(model_class.id.desc()).first()

        if last:
            try:
                num_str = last.id.split(separator)[-1]
                last_num = int(num_str)
                return f"{full_prefix}{last_num + 1:0{pad}d}"
            except (ValueError, IndexError):
                pass

        return f"{full_prefix}{1:0{pad}d}"

    @classmethod
    def order(cls):
        """Auftrags-ID: A2026-001, A2026-002, ..."""
        from src.models.models import Order
        year = datetime.now().year
        return cls._next_sequence(Order, f"A{year}", pad=3)

    @classmethod
    def article(cls):
        """Artikel-ID: ART001, ART002, ..."""
        from src.models.models import Article
        all_art = Article.query.filter(
            Article.id.like('ART%')
        ).with_entities(Article.id).all()

        max_num = 0
        for (aid,) in all_art:
            match = re.match(r'^ART(\d+)$', aid)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num

        return f"ART{max_num + 1:03d}"

    @classmethod
    def customer(cls):
        """Kunden-ID: KD001, KD002, ..."""
        from src.models.models import Customer
        # Alle KD-IDs holen und numerisch die hoechste finden
        # (alphabetische Sortierung versagt bei KD009 vs KD2026-0001)
        all_kd = Customer.query.filter(
            Customer.id.like('KD%')
        ).with_entities(Customer.id).all()

        max_num = 0
        for (cid,) in all_kd:
            match = re.match(r'^KD(\d+)$', cid)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num

        return f"KD{max_num + 1:03d}"

    @classmethod
    def temporary_customer(cls):
        """Temporaerer Kontakt: TMP2026-0001, ..."""
        from src.models.models import Customer
        year = datetime.now().year
        return cls._next_sequence(Customer, f"TMP{year}", pad=4)

    @classmethod
    def supplier(cls):
        """Lieferanten-ID: LF001, LF002, ..."""
        from src.models.models import Supplier
        last = Supplier.query.filter(
            Supplier.id.like('LF%')
        ).order_by(Supplier.id.desc()).first()

        max_num = 0
        if last:
            match = re.match(r'^LF(\d+)$', last.id)
            if match:
                max_num = int(match.group(1))

        return f"LF{max_num + 1:03d}"

    @classmethod
    def machine(cls):
        """Maschinen-ID: M001, M002, ..."""
        from src.models.models import Machine
        last = Machine.query.filter(
            Machine.id.like('M%')
        ).order_by(Machine.id.desc()).first()

        max_num = 0
        if last:
            match = re.match(r'^M(\d+)$', last.id)
            if match:
                max_num = int(match.group(1))

        return f"M{max_num + 1:03d}"

    @classmethod
    def shipment(cls):
        """Versand-ID: SHP-2026-001, ..."""
        from src.models.models import Order
        # Shipment nutzt eigenes Model
        try:
            from src.models.models import Shipment
            year = datetime.now().year
            return cls._next_sequence(Shipment, f"SHP-{year}", pad=3)
        except (ImportError, AttributeError):
            # Fallback
            year = datetime.now().year
            return f"SHP-{year}-001"

    @classmethod
    def invoice(cls, typ='RE'):
        """Rechnungsnummer: RE-202603-0001, PRF-202603-0001, ..."""
        from src.models.rechnungsmodul.models import Rechnung
        now = datetime.now()
        prefix = f"{typ}-{now.year:04d}{now.month:02d}"
        return cls._next_sequence(Rechnung, prefix, pad=4)

    @classmethod
    def angebot(cls):
        """Angebotsnummer: AN-2026-0001, ..."""
        from src.models.angebot import Angebot
        year = datetime.now().year
        return cls._next_sequence(Angebot, f"AN-{year}", pad=4)

    @classmethod
    def inquiry(cls):
        """Anfragenummer: ANF-202603-0001, ..."""
        from src.models.inquiry import Inquiry
        now = datetime.now()
        prefix = f"ANF-{now.year:04d}{now.month:02d}"
        return cls._next_sequence(Inquiry, prefix, pad=4)
