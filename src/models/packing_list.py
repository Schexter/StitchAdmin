# -*- coding: utf-8 -*-
"""
PackingList Model
Packlisten für Versandvorbereitung
Erstellt von: Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime
from src.models import db


class PackingList(db.Model):
    """
    Packliste für Versandvorbereitung
    Wird nach Produktionsabschluss erstellt
    """
    __tablename__ = 'packing_lists'

    # Primärschlüssel
    id = db.Column(db.Integer, primary_key=True)

    # Packlisten-Nummer (z.B. PL-2024-001)
    packing_list_number = db.Column(db.String(50), unique=True, nullable=False)

    # Verknüpfungen
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    production_id = db.Column(db.Integer, nullable=True)  # Hinweis: productions Tabelle existiert nicht
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)

    # Teillieferungen (Cartons)
    carton_number = db.Column(db.Integer, default=1)  # Karton 1 von 3
    total_cartons = db.Column(db.Integer, default=1)  # Gesamt-Anzahl Kartons
    is_partial_delivery = db.Column(db.Boolean, default=False)

    # Status
    # draft = Entwurf
    # ready = Bereit zur Verpackung
    # qc_passed = QK bestanden
    # packed = Verpackt / Versandbereit
    # shipped = Versendet
    status = db.Column(db.String(20), default='ready', nullable=False)

    # Inhalt (JSON Array der Artikel)
    # Format: [{"article_id": 1, "name": "...", "quantity": 10, "ean": "..."}]
    items = db.Column(db.Text)

    # Notizen
    customer_notes = db.Column(db.Text)  # Kundenvorgaben (z.B. "Einzeln verpacken")
    packing_notes = db.Column(db.Text)   # Interne Notizen

    # Gewicht & Maße
    total_weight = db.Column(db.Float)      # kg
    package_length = db.Column(db.Float)    # cm
    package_width = db.Column(db.Float)     # cm
    package_height = db.Column(db.Float)    # cm

    # Qualitätskontrolle
    qc_performed = db.Column(db.Boolean, default=False)
    qc_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    qc_date = db.Column(db.DateTime)
    qc_notes = db.Column(db.Text)
    qc_photos = db.Column(db.Text)  # JSON Array mit Foto-Pfaden

    # Verpackung
    packed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    packed_at = db.Column(db.DateTime)
    packed_confirmed = db.Column(db.Boolean, default=False)

    # Lagerbuchung
    inventory_booked = db.Column(db.Boolean, default=False)
    inventory_booking_date = db.Column(db.DateTime)

    # Verknüpfung zu Lieferschein
    delivery_note_id = db.Column(db.Integer, db.ForeignKey('delivery_notes.id'), nullable=True)

    # Verknüpfung zu PostEntry
    post_entry_id = db.Column(db.Integer, db.ForeignKey('post_entries.id'), nullable=True)

    # PDF
    pdf_path = db.Column(db.String(500))

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    order = db.relationship('Order', backref='packing_lists', foreign_keys=[order_id])
    # production = db.relationship('Production', backref='packing_lists', foreign_keys=[production_id])  # Tabelle existiert nicht
    customer = db.relationship('Customer', backref='packing_lists', foreign_keys=[customer_id])
    qc_user = db.relationship('User', foreign_keys=[qc_by], backref='qc_packing_lists')
    packer = db.relationship('User', foreign_keys=[packed_by], backref='packed_lists')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_packing_lists')

    @property
    def carton_label(self):
        """
        Gibt 'Karton 1 von 3' zurück, wenn Teillieferung
        Sonst None
        """
        if self.total_cartons > 1:
            return f"Karton {self.carton_number} von {self.total_cartons}"
        return None

    @property
    def display_number(self):
        """
        Gibt Packlisten-Nummer mit Carton-Info zurück
        z.B. "PL-2024-001 (Karton 1/3)"
        """
        if self.carton_label:
            return f"{self.packing_list_number} ({self.carton_label})"
        return self.packing_list_number

    @staticmethod
    def generate_packing_list_number():
        """
        Generiert neue Packlisten-Nummer im Format PL-YYYY-NNNN
        z.B. PL-2024-0001
        """
        from datetime import datetime

        year = datetime.now().year
        prefix = f"PL-{year}-"

        # Letzte Packliste in diesem Jahr finden
        last = PackingList.query.filter(
            PackingList.packing_list_number.like(f"{prefix}%")
        ).order_by(PackingList.id.desc()).first()

        if last:
            try:
                last_num = int(last.packing_list_number.split('-')[-1])
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

    def get_qc_photos_list(self):
        """
        Gibt QC-Fotos als Liste zurück
        """
        import json
        if self.qc_photos:
            try:
                return json.loads(self.qc_photos)
            except:
                return []
        return []

    def add_qc_photo(self, photo_path):
        """
        Fügt QC-Foto hinzu
        """
        import json
        photos = self.get_qc_photos_list()
        photos.append(photo_path)
        self.qc_photos = json.dumps(photos)

    def get_status_label(self):
        """
        Gibt deutsche Bezeichnung für Status zurück
        """
        status_labels = {
            'draft': 'Entwurf',
            'ready': 'Bereit zur Verpackung',
            'qc_passed': 'QK bestanden',
            'packed': 'Verpackt / Versandbereit',
            'shipped': 'Versendet'
        }
        return status_labels.get(self.status, self.status)

    def get_status_color(self):
        """
        Gibt Bootstrap-Farbe für Status zurück
        """
        status_colors = {
            'draft': 'secondary',
            'ready': 'warning',
            'qc_passed': 'info',
            'packed': 'success',
            'shipped': 'primary'
        }
        return status_colors.get(self.status, 'secondary')

    def __repr__(self):
        return f'<PackingList {self.packing_list_number} - {self.status}>'


__all__ = ['PackingList']
