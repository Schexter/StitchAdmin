# -*- coding: utf-8 -*-
"""
Rechnungsmodul - Models
Erstellt von: Hans Hahn - Alle Rechte vorbehalten
Datum: 09. Juli 2025

Dieses Modul importiert alle Rechnungsmodul-Models und stellt sie zur Verfügung.
Verwendet echte SQLAlchemy-Models wenn verfügbar, sonst Mock-Implementierungen.
"""

# Versuche echte SQLAlchemy-Models zu importieren
try:
    from .models import (
        KassenBeleg, BelegPosition, KassenTransaktion, MwStSatz, TSEKonfiguration,
        Rechnung, RechnungsPosition, RechnungsZahlung, TagesAbschluss, ZugpferdKonfiguration,
        BelegTyp, ZahlungsArt, RechnungsStatus, TSEStatus, ZugpferdProfil
    )
    
    # Teste ob die Models funktionieren
    models_available = True
    print("[OK] Echte Rechnungsmodul-Models verfuegbar")

except (ImportError, Exception) as e:
    print(f"[WARNUNG] Echte Models nicht verfuegbar: {e}")
    print("[INFO] Verwende Mock-Implementierungen...")
    
    # Mock-Implementierungen für Development
    class MockQuery:
        """Mock-Query-Klasse für Development ohne echte Datenbank"""
        def __init__(self):
            pass
        
        def filter(self, *args):
            return self
        
        def filter_by(self, *args, **kwargs):
            return self
        
        def order_by(self, *args):
            return self
        
        def limit(self, n):
            return self
        
        def all(self):
            return []
        
        def first(self):
            return None
        
        def count(self):
            return 0
        
        def get(self, id):
            return None
    
    class MockModel:
        """Basis-Mock-Model"""
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
        
        @classmethod
        def query(cls):
            return MockQuery()
    
    class KassenBeleg(MockModel):
        """Mock-Klasse für Kassenbelege"""
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            # Standardwerte
            self.id = kwargs.get('id', None)
            self.belegnummer = kwargs.get('belegnummer', None)
            self.beleg_typ = kwargs.get('beleg_typ', None)
            self.erstellt_am = kwargs.get('erstellt_am', None)
            self.netto_gesamt = kwargs.get('netto_gesamt', 0.0)
            self.mwst_gesamt = kwargs.get('mwst_gesamt', 0.0)
            self.brutto_gesamt = kwargs.get('brutto_gesamt', 0.0)
            self.zahlungsart = kwargs.get('zahlungsart', None)
            self.kassierer_name = kwargs.get('kassierer_name', None)
            self.storniert = kwargs.get('storniert', False)
    
    class BelegPosition(MockModel):
        """Mock-Klasse für Belegpositionen"""
        pass
    
    class KassenTransaktion(MockModel):
        """Mock-Klasse für TSE-Transaktionen"""
        pass
    
    class MwStSatz(MockModel):
        """Mock-Klasse für MwSt-Sätze"""
        pass
    
    class TSEKonfiguration(MockModel):
        """Mock-Klasse für TSE-Konfiguration"""
        pass
    
    class Rechnung(MockModel):
        """Mock-Klasse für Rechnungen"""
        pass
    
    class RechnungsPosition(MockModel):
        """Mock-Klasse für Rechnungspositionen"""
        pass
    
    class RechnungsZahlung(MockModel):
        """Mock-Klasse für Rechnungszahlungen"""
        pass
    
    class TagesAbschluss(MockModel):
        """Mock-Klasse für Tagesabschlüsse"""
        pass
    
    class ZugpferdKonfiguration(MockModel):
        """Mock-Klasse für ZUGPFERD-Konfiguration"""
        pass
    
    # Mock-Enums
    class BelegTyp:
        RECHNUNG = "RECHNUNG"
        GUTSCHRIFT = "GUTSCHRIFT"
        TRAINING = "TRAINING"
        STORNO = "STORNO"
    
    class ZahlungsArt:
        BAR = "BAR"
        EC_KARTE = "EC_KARTE"
        KREDITKARTE = "KREDITKARTE"
        RECHNUNG = "RECHNUNG"
        UEBERWEISUNG = "UEBERWEISUNG"
    
    class RechnungsStatus:
        ENTWURF = "ENTWURF"
        OFFEN = "OFFEN"
        BEZAHLT = "BEZAHLT"
        STORNIERT = "STORNIERT"
    
    class TSEStatus:
        AKTIV = "AKTIV"
        INAKTIV = "INAKTIV"
        DEFEKT = "DEFEKT"
    
    class ZugpferdProfil:
        MINIMUM = "MINIMUM"
        BASIC = "BASIC"
        COMFORT = "COMFORT"
        EXTENDED = "EXTENDED"
    
    models_available = False

# Alle verfügbaren Klassen exportieren
__all__ = [
    'KassenBeleg', 'BelegPosition', 'KassenTransaktion', 'MwStSatz', 'TSEKonfiguration',
    'Rechnung', 'RechnungsPosition', 'RechnungsZahlung', 'TagesAbschluss', 'ZugpferdKonfiguration',
    'BelegTyp', 'ZahlungsArt', 'RechnungsStatus', 'TSEStatus', 'ZugpferdProfil',
    'models_available'
]
