# -*- coding: utf-8 -*-
"""
Website Content Model - CMS für die öffentliche Website
StitchAdmin 2.0
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime
from src.models.models import db


class WebsiteContent(db.Model):
    """
    Key-Value-Store für editierbare Website-Inhalte.
    Gruppiert nach Sektionen (hero, services, gallery, about, process, meta, footer).
    """
    __tablename__ = 'website_content'

    id = db.Column(db.Integer, primary_key=True)
    section = db.Column(db.String(50), nullable=False, index=True)
    key = db.Column(db.String(100), nullable=False)
    content_type = db.Column(db.String(20), nullable=False, default='text')
    value = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))

    __table_args__ = (
        db.UniqueConstraint('section', 'key', name='uq_website_content_section_key'),
    )

    @classmethod
    def get(cls, section, key, default=''):
        """Einzelnen Content-Wert laden"""
        item = cls.query.filter_by(section=section, key=key).first()
        return item.value if item and item.value else default

    @classmethod
    def get_section(cls, section):
        """Alle Inhalte einer Sektion als Dict laden"""
        items = cls.query.filter_by(section=section).order_by(cls.sort_order).all()
        return {item.key: item.value for item in items if item.value}

    @classmethod
    def set(cls, section, key, value, content_type='text', sort_order=0, updated_by=None):
        """Content-Wert setzen (Upsert)"""
        item = cls.query.filter_by(section=section, key=key).first()
        if not item:
            item = cls(section=section, key=key, content_type=content_type, sort_order=sort_order)
            db.session.add(item)
        item.value = value
        item.updated_at = datetime.utcnow()
        item.updated_by = updated_by
        return item

    @classmethod
    def delete_key(cls, section, key):
        """Content-Wert löschen"""
        item = cls.query.filter_by(section=section, key=key).first()
        if item:
            db.session.delete(item)

    @classmethod
    def seed_defaults(cls):
        """Standard-Inhalte setzen (aktuelle Hardcoded-Werte)"""
        defaults = {
            'hero': [
                ('badge_text', 'Professionelle Stickerei', 'text', 0),
                ('title', 'Ihr Partner für hochwertige Stickerei', 'text', 1),
                ('subtitle', 'Von Firmenlogos über Vereinsausstattung bis hin zu individuellen Designs – wir veredeln Ihre Textilien mit modernster Sticktechnik und höchster Präzision.', 'textarea', 2),
                ('bg_image', 'https://images.unsplash.com/photo-1558171813-4c088753af8f?w=1920&q=80', 'image', 3),
                ('cta_text', 'Anfrage stellen', 'text', 4),
                ('cta_link', '#kontakt', 'text', 5),
            ],
            'services': [
                ('section_title', 'Unsere Leistungen', 'text', 0),
                ('section_subtitle', 'Professionelle Textilveredelung für jeden Bedarf', 'text', 1),
                ('card_1_title', 'Maschinenstickerei', 'text', 10),
                ('card_1_description', 'Hochwertige Stickereien auf allen Textilien – langlebig, waschbeständig und in brillanten Farben.', 'textarea', 11),
                ('card_1_image', 'https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=600&q=80', 'image', 12),
                ('card_2_title', 'Firmenlogos', 'text', 20),
                ('card_2_description', 'Corporate Identity auf Arbeitskleidung, Poloshirts und Hemden – für einen professionellen Auftritt.', 'textarea', 21),
                ('card_2_image', 'https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?w=600&q=80', 'image', 22),
                ('card_3_title', 'Vereinsausstattung', 'text', 30),
                ('card_3_description', 'Trikots, Trainingsanzüge und Fanartikel mit Ihrem Vereinslogo und individueller Beflockung.', 'textarea', 31),
                ('card_3_image', 'https://images.unsplash.com/photo-1517466787929-bc90951d0974?w=600&q=80', 'image', 32),
                ('card_4_title', 'Design-Service', 'text', 40),
                ('card_4_description', 'Wir digitalisieren Ihr Logo und erstellen stickfertige Dateien – perfekt abgestimmt auf Ihr Textil.', 'textarea', 41),
                ('card_4_image', 'https://images.unsplash.com/photo-1626785774573-4b799315345d?w=600&q=80', 'image', 42),
                ('card_5_title', 'Personalisierung', 'text', 50),
                ('card_5_description', 'Namen, Initialen oder individuelle Texte – perfekt als Geschenk oder für besondere Anlässe.', 'textarea', 51),
                ('card_5_image', 'https://images.unsplash.com/photo-1513364776144-60967b0f800f?w=600&q=80', 'image', 52),
                ('card_6_title', 'Textilbeschaffung', 'text', 60),
                ('card_6_description', 'Wir liefern auch die passenden Textilien – von Arbeitskleidung bis hin zu Premium-Poloshirts.', 'textarea', 61),
                ('card_6_image', 'https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=600&q=80', 'image', 62),
            ],
            'gallery': [
                ('section_title', 'Unsere Arbeiten', 'text', 0),
                ('section_subtitle', 'Einblicke in aktuelle Projekte und fertige Stickereien', 'text', 1),
                ('image_1', 'https://images.unsplash.com/photo-1503342217505-b0a15ec515c7?w=400&q=80', 'image', 10),
                ('image_1_alt', 'Poloshirt bestickt', 'text', 11),
                ('image_2', 'https://images.unsplash.com/photo-1562157873-818bc0726f68?w=400&q=80', 'image', 20),
                ('image_2_alt', 'Arbeitskleidung', 'text', 21),
                ('image_3', 'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=400&q=80', 'image', 30),
                ('image_3_alt', 'Textilveredelung', 'text', 31),
                ('image_4', 'https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=400&q=80', 'image', 40),
                ('image_4_alt', 'Stickerei Detail', 'text', 41),
                ('image_5', 'https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=400&q=80', 'image', 50),
                ('image_5_alt', 'Kollektion', 'text', 51),
                ('image_6', 'https://images.unsplash.com/photo-1558171813-4c088753af8f?w=400&q=80', 'image', 60),
                ('image_6_alt', 'Nähmaschine', 'text', 61),
                ('image_7', 'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&q=80', 'image', 70),
                ('image_7_alt', 'Hemden bestickt', 'text', 71),
                ('image_8', 'https://images.unsplash.com/photo-1578587018452-892bacefd3f2?w=400&q=80', 'image', 80),
                ('image_8_alt', 'Garnrollen', 'text', 81),
            ],
            'about': [
                ('title', 'Qualität aus Leidenschaft', 'text', 0),
                ('text', 'Mit modernsten Maschinen und jahrelanger Erfahrung setzen wir Ihre Ideen präzise um.', 'textarea', 1),
                ('image', 'https://images.unsplash.com/photo-1581783898377-1c85bf937427?w=800&q=80', 'image', 2),
                ('checklist_1', 'Modernste Multi-Head Stickmaschinen', 'text', 10),
                ('checklist_2', 'Schnelle Lieferzeiten ab 3 Werktagen', 'text', 11),
                ('checklist_3', 'Persönliche Beratung & individuelle Lösungen', 'text', 12),
                ('checklist_4', 'Faire Preise – auch bei Kleinauflagen', 'text', 13),
            ],
            'process': [
                ('section_title', 'In 4 Schritten zum fertigen Produkt', 'text', 0),
                ('step_1_title', 'Beratung', 'text', 10),
                ('step_1_description', 'Wir besprechen Ihr Projekt und beraten Sie zu Materialien und Möglichkeiten.', 'textarea', 11),
                ('step_1_icon', 'bi-chat-text-fill', 'icon', 12),
                ('step_2_title', 'Design', 'text', 20),
                ('step_2_description', 'Wir erstellen oder digitalisieren Ihr Motiv für die perfekte Stickumsetzung.', 'textarea', 21),
                ('step_2_icon', 'bi-palette-fill', 'icon', 22),
                ('step_3_title', 'Produktion', 'text', 30),
                ('step_3_description', 'Ihre Textilien werden auf unseren Maschinen präzise und hochwertig bestickt.', 'textarea', 31),
                ('step_3_icon', 'bi-gear-wide-connected', 'icon', 32),
                ('step_4_title', 'Lieferung', 'text', 40),
                ('step_4_description', 'Qualitätskontrolle, sorgfältige Verpackung und schneller Versand zu Ihnen.', 'textarea', 41),
                ('step_4_icon', 'bi-box-seam-fill', 'icon', 42),
            ],
        }

        for section, items in defaults.items():
            for key, value, content_type, sort_order in items:
                existing = cls.query.filter_by(section=section, key=key).first()
                if not existing:
                    cls.set(section, key, value, content_type, sort_order)

        db.session.commit()

    def __repr__(self):
        return f'<WebsiteContent {self.section}.{self.key}>'
