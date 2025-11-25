# -*- coding: utf-8 -*-
"""
Rechnungsmodul - Models
Erstellt von: Hans Hahn - Alle Rechte vorbehalten
Datum: 09. Juli 2025

Dieses Modul importiert alle Rechnungsmodul-Models und stellt sie zur Verfügung.
"""

# Importiere echte SQLAlchemy-Models
from .models import (
    KassenBeleg, BelegPosition, KassenTransaktion, MwStSatz, TSEKonfiguration,
    Rechnung, RechnungsPosition, RechnungsZahlung, TagesAbschluss, ZugpferdKonfiguration,
    BelegTyp, ZahlungsArt, RechnungsStatus, TSEStatus, ZugpferdProfil, RechnungsRichtung
)

models_available = True

# Alle verfügbaren Klassen exportieren
__all__ = [
    'KassenBeleg', 'BelegPosition', 'KassenTransaktion', 'MwStSatz', 'TSEKonfiguration',
    'Rechnung', 'RechnungsPosition', 'RechnungsZahlung', 'TagesAbschluss', 'ZugpferdKonfiguration',
    'BelegTyp', 'ZahlungsArt', 'RechnungsStatus', 'TSEStatus', 'ZugpferdProfil', 'RechnungsRichtung',
    'models_available'
]
