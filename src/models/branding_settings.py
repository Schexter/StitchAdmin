# -*- coding: utf-8 -*-
"""
BRANDING SETTINGS MODELL
========================

Erstellt von: Hans Hahn - Alle Rechte vorbehalten
Datum: 10. Juli 2024
Zweck: Datenbankmodell zum Speichern von Branding-Einstellungen (Logo, Farben).
"""

from . import db

class BrandingSettings(db.Model):
    """
    Speichert globale Branding-Einstellungen.
    Dieses Modell wird als Singleton verwendet (es sollte nur eine Zeile geben).
    """
    __tablename__ = 'branding_settings'

    id = db.Column(db.Integer, primary_key=True)
    
    # Relativer Pfad zum Logo im 'static' Ordner
    logo_path = db.Column(db.String(255), nullable=True)
    
    # Primär- und Sekundärfarben für das UI-Theme
    primary_color = db.Column(db.String(7), default='#0d6efd')  # Bootstrap Primary Blue
    secondary_color = db.Column(db.String(7), default='#6c757d') # Bootstrap Secondary Gray

    @staticmethod
    def get_settings():
        """
        Holt die Branding-Einstellungen. Erstellt sie, falls sie nicht existieren.
        """
        settings = BrandingSettings.query.first()
        if not settings:
            settings = BrandingSettings()
            db.session.add(settings)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Fehler beim Erstellen der Standard-Branding-Einstellungen: {e}")
        return settings

    def __repr__(self):
        return f"<BrandingSettings (Logo: {self.logo_path})>"

__all__ = ['BrandingSettings']
