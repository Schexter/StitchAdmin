# -*- coding: utf-8 -*-
"""
DeliveryNote Model
Lieferscheine für Versand/Abholung
Erstellt von: Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime, date
from src.models import db


class DeliveryNote(db.Model):
    """
    Lieferschein für Versand oder Abholung
    Wird nach Verpackung erstellt
    """
    __tablename__ = 'delivery_notes'

    # Primärschlüssel
    id = db.Column(db.Integer, primary_key=True)

    # Lieferschein-Nummer (z.B. LS-2024-001)
    delivery_note_number = db.Column(db.String(50), unique=True, nullable=False)

    # Verknüpfungen
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    packing_list_id = db.Column(db.Integer, db.ForeignKey('packing_lists.id'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    post_entry_id = db.Column(db.Integer, db.ForeignKey('post_entries.id'), nullable=True)

    # Datum
    delivery_date = db.Column(db.Date, default=date.today, nullable=False)

    # Inhalt (JSON Array)
    # Format: [{"article_id": 1, "name": "...", "quantity": 10, "unit": "Stk"}]
    items = db.Column(db.Text)

    # Notizen
    notes = db.Column(db.Text)

    # Lieferart
    # 'pickup' = Abholung durch Kunde
    # 'shipping' = Versand per Dienstleister
    delivery_method = db.Column(db.String(20), default='shipping')

    # Unterschrift (digital + gedruckt)
    # 'digital' = Digital auf Tablet erfasst
    # 'printed' = Auf gedrucktem Lieferschein
    signature_type = db.Column(db.String(20))

    # Digitale Unterschrift
    signature_image = db.Column(db.String(500))       # Pfad zur PNG-Datei
    signature_name = db.Column(db.String(200))        # Name des Unterzeichners
    signature_date = db.Column(db.DateTime)
    signature_device = db.Column(db.String(100))      # z.B. "iPad Pro", "Desktop"

    # Fotos (z.B. von verpacktem Paket)
    # JSON Array: ["uploads/photos/photo1.jpg", "uploads/photos/photo2.jpg"]
    photos = db.Column(db.Text)

    # Status
    # draft = Entwurf
    # ready = Bereit
    # sent = Versendet / Übergeben
    # delivered = Zugestellt / Abgeholt
    # signed = Unterschrieben
    status = db.Column(db.String(20), default='ready', nullable=False)

    # PDFs
    pdf_path = db.Column(db.String(500))                    # Basis-PDF
    pdf_with_signature_path = db.Column(db.String(500))     # PDF mit Unterschrift

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    order = db.relationship('Order', backref='delivery_notes', foreign_keys=[order_id])
    packing_list = db.relationship('PackingList', backref='delivery_note',
                                   foreign_keys=[packing_list_id], uselist=False)
    customer = db.relationship('Customer', backref='delivery_notes', foreign_keys=[customer_id])
    post_entry = db.relationship('PostEntry', backref='delivery_note',
                                 foreign_keys=[post_entry_id], uselist=False)
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_delivery_notes')

    @property
    def is_signed(self):
        """
        Prüft ob Lieferschein unterschrieben wurde
        """
        return self.signature_image is not None or self.signature_name is not None

    @property
    def is_pickup(self):
        """
        Prüft ob Abholung
        """
        return self.delivery_method == 'pickup'

    @property
    def is_shipping(self):
        """
        Prüft ob Versand
        """
        return self.delivery_method == 'shipping'

    @staticmethod
    def generate_delivery_note_number():
        """
        Generiert neue Lieferschein-Nummer im Format LS-YYYY-NNNN
        z.B. LS-2024-0001
        """
        from datetime import datetime

        year = datetime.now().year
        prefix = f"LS-{year}-"

        # Letzten Lieferschein in diesem Jahr finden
        last = DeliveryNote.query.filter(
            DeliveryNote.delivery_note_number.like(f"{prefix}%")
        ).order_by(DeliveryNote.id.desc()).first()

        if last:
            try:
                last_num = int(last.delivery_note_number.split('-')[-1])
                new_num = last_num + 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1

        return f"{prefix}{new_num:04d}"

    def get_items_list(self):
        """
        Gibt items als Python-Liste zurück (aus JSON)
        """
        import json
        if self.items:
            try:
                return json.loads(self.items)
            except:
                return []
        return []

    def set_items_list(self, items_list):
        """
        Setzt items aus Python-Liste (zu JSON)
        """
        import json
        self.items = json.dumps(items_list, ensure_ascii=False)

    def get_photos_list(self):
        """
        Gibt Fotos als Liste zurück
        """
        import json
        if self.photos:
            try:
                return json.loads(self.photos)
            except:
                return []
        return []

    def add_photo(self, photo_path):
        """
        Fügt Foto hinzu
        """
        import json
        photos = self.get_photos_list()
        photos.append(photo_path)
        self.photos = json.dumps(photos)

    def get_status_label(self):
        """
        Gibt deutsche Bezeichnung für Status zurück
        """
        status_labels = {
            'draft': 'Entwurf',
            'ready': 'Bereit',
            'sent': 'Versendet',
            'delivered': 'Zugestellt',
            'signed': 'Unterschrieben'
        }
        return status_labels.get(self.status, self.status)

    def get_status_color(self):
        """
        Gibt Bootstrap-Farbe für Status zurück
        """
        status_colors = {
            'draft': 'secondary',
            'ready': 'info',
            'sent': 'primary',
            'delivered': 'success',
            'signed': 'success'
        }
        return status_colors.get(self.status, 'secondary')

    def get_delivery_method_label(self):
        """
        Gibt deutsche Bezeichnung für Lieferart zurück
        """
        if self.delivery_method == 'pickup':
            return 'Abholung'
        elif self.delivery_method == 'shipping':
            return 'Versand'
        return self.delivery_method

    def __repr__(self):
        return f'<DeliveryNote {self.delivery_note_number} - {self.status}>'


__all__ = ['DeliveryNote']
