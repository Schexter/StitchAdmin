# -*- coding: utf-8 -*-
"""
CRM & Aktivitäten-Tracking
===========================

Erstellt von: StitchAdmin
Zweck: Nachverfolgung von Kundeninteraktionen, Angeboten und Verkaufschancen

Features:
- Aktivitäten-Timeline (Anrufe, E-Mails, Meetings)
- Follow-up-Erinnerungen
- Angebots-Nachverfolgung
- Verkaufschancen-Management
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from src.models import db


class ActivityType:
    """Typen von Aktivitäten"""
    EMAIL = 'email'                  # E-Mail gesendet/empfangen
    PHONE_CALL = 'phone_call'        # Telefonat
    MEETING = 'meeting'              # Persönliches Meeting
    NOTE = 'note'                    # Notiz
    TASK = 'task'                    # Aufgabe/Todo
    ANGEBOT_VERSENDET = 'angebot_versendet'     # Angebot verschickt
    ANGEBOT_NACHFRAGE = 'angebot_nachfrage'     # Nachfrage zum Angebot
    ANGEBOT_ANGENOMMEN = 'angebot_angenommen'   # Angebot angenommen
    ANGEBOT_ABGELEHNT = 'angebot_abgelehnt'     # Angebot abgelehnt
    DOKUMENT = 'dokument'            # Dokument hochgeladen


class ActivityStatus:
    """Status von Aktivitäten"""
    GEPLANT = 'geplant'              # Geplante Aktivität (zukünftig)
    OFFEN = 'offen'                  # Offene Aufgabe
    IN_ARBEIT = 'in_arbeit'          # In Bearbeitung
    ERLEDIGT = 'erledigt'            # Abgeschlossen
    ABGEBROCHEN = 'abgebrochen'      # Abgebrochen


class Activity(db.Model):
    """Aktivitäten und Interaktionen"""
    __tablename__ = 'activities'

    id = db.Column(db.Integer, primary_key=True)

    # Typ und Status
    activity_type = db.Column(db.String(50), nullable=False, index=True)
    status = db.Column(db.String(20), default=ActivityStatus.ERLEDIGT, index=True)

    # Referenzen (mindestens eine muss gesetzt sein)
    kunde_id = db.Column(db.String(50), db.ForeignKey('customers.id'), index=True)
    angebot_id = db.Column(db.Integer, db.ForeignKey('angebote.id'), index=True)
    auftrag_id = db.Column(db.String(50), db.ForeignKey('orders.id'), index=True)
    rechnung_id = db.Column(db.Integer, db.ForeignKey('rechnungen.id'), index=True)

    # Titel und Beschreibung
    titel = db.Column(db.String(200), nullable=False)
    beschreibung = db.Column(db.Text)
    ergebnis = db.Column(db.Text)  # Ergebnis der Aktivität

    # Zeitpunkte
    geplant_am = db.Column(db.DateTime)           # Geplanter Zeitpunkt
    erledigt_am = db.Column(db.DateTime)          # Wann erledigt
    faellig_am = db.Column(db.DateTime, index=True)  # Fälligkeit (für Tasks)

    # Dauer (in Minuten)
    dauer_minuten = db.Column(db.Integer)

    # Priorität
    prioritaet = db.Column(db.String(20), default='normal')  # niedrig, normal, hoch, dringend

    # Follow-up
    follow_up_erforderlich = db.Column(db.Boolean, default=False)
    follow_up_datum = db.Column(db.Date, index=True)
    follow_up_erledigt = db.Column(db.Boolean, default=False)

    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    created_by = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))

    # Anhänge (optional, als JSON)
    anhaenge_json = db.Column(db.Text)  # Liste von Datei-Pfaden

    # Beziehungen
    kunde = db.relationship('Customer', foreign_keys=[kunde_id], backref='aktivitaeten')
    angebot = db.relationship('Angebot', foreign_keys=[angebot_id], backref='aktivitaeten')
    auftrag = db.relationship('Order', foreign_keys=[auftrag_id], backref='aktivitaeten')
    rechnung = db.relationship('Rechnung', foreign_keys=[rechnung_id], backref='aktivitaeten')

    @classmethod
    def create_activity(cls, activity_type, titel, created_by=None,
                       kunde_id=None, angebot_id=None, auftrag_id=None, rechnung_id=None,
                       beschreibung=None, geplant_am=None, faellig_am=None,
                       follow_up_datum=None, prioritaet='normal'):
        """
        Erstellt eine neue Aktivität

        Args:
            activity_type: Typ der Aktivität (ActivityType)
            titel: Titel der Aktivität
            created_by: Benutzer
            kunde_id: Kunden-ID (optional)
            angebot_id: Angebots-ID (optional)
            auftrag_id: Auftrags-ID (optional)
            rechnung_id: Rechnungs-ID (optional)
            beschreibung: Beschreibung (optional)
            geplant_am: Geplanter Zeitpunkt (optional)
            faellig_am: Fälligkeitsdatum (optional)
            follow_up_datum: Follow-up Datum (optional)
            prioritaet: Priorität (optional)

        Returns:
            Activity: Die erstellte Aktivität
        """
        activity = cls(
            activity_type=activity_type,
            titel=titel,
            beschreibung=beschreibung,
            kunde_id=kunde_id,
            angebot_id=angebot_id,
            auftrag_id=auftrag_id,
            rechnung_id=rechnung_id,
            geplant_am=geplant_am,
            faellig_am=faellig_am,
            prioritaet=prioritaet,
            created_by=created_by
        )

        if follow_up_datum:
            activity.follow_up_erforderlich = True
            activity.follow_up_datum = follow_up_datum

        # Für Tasks: Status = offen
        if activity_type == ActivityType.TASK:
            activity.status = ActivityStatus.OFFEN

        db.session.add(activity)
        db.session.commit()

        return activity

    def erledigen(self, ergebnis=None, created_by=None):
        """
        Markiert Aktivität als erledigt

        Args:
            ergebnis: Ergebnis/Notizen (optional)
            created_by: Benutzer (optional)
        """
        self.status = ActivityStatus.ERLEDIGT
        self.erledigt_am = datetime.utcnow()
        if ergebnis:
            self.ergebnis = ergebnis
        if created_by:
            self.updated_by = created_by

        db.session.commit()

    def follow_up_erledigen(self):
        """Markiert Follow-up als erledigt"""
        self.follow_up_erledigt = True
        db.session.commit()

    @property
    def ist_ueberfaellig(self):
        """Prüft ob Aktivität überfällig ist"""
        if not self.faellig_am:
            return False
        return self.status != ActivityStatus.ERLEDIGT and datetime.now() > self.faellig_am

    @property
    def tage_seit_erstellung(self):
        """Tage seit Erstellung"""
        return (datetime.now() - self.created_at).days

    def __repr__(self):
        return f'<Activity {self.activity_type}: {self.titel}>'


class AngebotTracking(db.Model):
    """Erweiterte Nachverfolgung für Angebote (CRM)"""
    __tablename__ = 'angebot_tracking'

    id = db.Column(db.Integer, primary_key=True)
    angebot_id = db.Column(db.Integer, db.ForeignKey('angebote.id'), nullable=False, unique=True)

    # Verkaufschance
    verkaufschance_prozent = db.Column(db.Integer, default=50)  # Wahrscheinlichkeit 0-100%
    erwarteter_abschluss_datum = db.Column(db.Date)

    # Konkurrenz
    hat_konkurrenz = db.Column(db.Boolean, default=False)
    konkurrenz_info = db.Column(db.Text)

    # Entscheidungskriterien
    entscheidungskriterien = db.Column(db.Text)  # Was ist dem Kunden wichtig?
    budget_vorhanden = db.Column(db.Boolean)

    # Nachverfolgung
    letzter_kontakt = db.Column(db.Date, index=True)
    naechster_kontakt_geplant = db.Column(db.Date, index=True)
    anzahl_nachfragen = db.Column(db.Integer, default=0)

    # Status-Details
    grund_fuer_verzoegerung = db.Column(db.Text)
    naechste_schritte = db.Column(db.Text)

    # Verlust-Analyse (wenn abgelehnt)
    verlustgrund = db.Column(db.String(100))  # preis, qualitaet, lieferzeit, konkurrenz, sonstiges
    verlust_details = db.Column(db.Text)
    verlust_an_konkurrent = db.Column(db.String(200))

    # Gewinn-Analyse (wenn angenommen)
    gewinn_faktoren = db.Column(db.Text)  # Was hat den Zuschlag gebracht?

    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(80))

    # Beziehungen
    angebot = db.relationship('Angebot', backref=db.backref('tracking', uselist=False))

    def naechsten_kontakt_planen(self, tage_bis_kontakt=7):
        """
        Plant nächsten Kontakt

        Args:
            tage_bis_kontakt: Tage bis zum nächsten Kontakt
        """
        self.naechster_kontakt_geplant = date.today() + timedelta(days=tage_bis_kontakt)
        db.session.commit()

    def kontakt_durchgefuehrt(self, ergebnis=None, created_by=None):
        """
        Registriert durchgeführten Kontakt

        Args:
            ergebnis: Ergebnis des Kontakts
            created_by: Benutzer
        """
        self.letzter_kontakt = date.today()
        self.anzahl_nachfragen += 1
        self.updated_by = created_by

        # Aktivität erstellen
        Activity.create_activity(
            activity_type=ActivityType.ANGEBOT_NACHFRAGE,
            titel=f"Nachfrage zu Angebot {self.angebot.angebotsnummer}",
            beschreibung=ergebnis,
            angebot_id=self.angebot_id,
            kunde_id=self.angebot.kunde_id,
            created_by=created_by
        )

        db.session.commit()

    def verkaufschance_aktualisieren(self, neue_chance, grund=None):
        """
        Aktualisiert Verkaufschance

        Args:
            neue_chance: Neue Wahrscheinlichkeit (0-100)
            grund: Grund für Änderung
        """
        alte_chance = self.verkaufschance_prozent
        self.verkaufschance_prozent = max(0, min(100, neue_chance))

        # Notiz zur Änderung
        if grund:
            Activity.create_activity(
                activity_type=ActivityType.NOTE,
                titel=f"Verkaufschance geändert: {alte_chance}% → {neue_chance}%",
                beschreibung=grund,
                angebot_id=self.angebot_id,
                kunde_id=self.angebot.kunde_id
            )

        db.session.commit()

    @property
    def tage_seit_versand(self):
        """Tage seit Angebot versendet wurde"""
        if not self.angebot or self.angebot.status != 'verschickt':
            return None
        if not self.letzter_kontakt:
            return (date.today() - self.angebot.angebotsdatum).days
        return (date.today() - self.letzter_kontakt).days

    @property
    def braucht_follow_up(self):
        """Prüft ob Follow-up fällig ist"""
        if self.naechster_kontakt_geplant:
            return date.today() >= self.naechster_kontakt_geplant
        # Standard: Nach 7 Tagen ohne Kontakt
        if self.tage_seit_versand and self.tage_seit_versand >= 7:
            return True
        return False

    def __repr__(self):
        return f'<AngebotTracking {self.angebot.angebotsnummer} ({self.verkaufschance_prozent}%)>'


class SalesStage:
    """Verkaufsphasen"""
    LEAD = 'lead'                    # Erste Anfrage
    QUALIFIZIERT = 'qualifiziert'    # Qualifizierter Lead
    ANGEBOT = 'angebot'              # Angebot erstellt
    VERHANDLUNG = 'verhandlung'      # In Verhandlung
    GEWONNEN = 'gewonnen'            # Auftrag gewonnen
    VERLOREN = 'verloren'            # Verloren


class SalesFunnel(db.Model):
    """Verkaufschancen-Verwaltung (Sales Pipeline)"""
    __tablename__ = 'sales_funnel'

    id = db.Column(db.Integer, primary_key=True)

    # Verkaufschance
    titel = db.Column(db.String(200), nullable=False)
    beschreibung = db.Column(db.Text)

    # Kunde
    kunde_id = db.Column(db.String(50), db.ForeignKey('customers.id'), nullable=False)

    # Referenzen
    angebot_id = db.Column(db.Integer, db.ForeignKey('angebote.id'))
    auftrag_id = db.Column(db.String(50), db.ForeignKey('orders.id'))

    # Phase und Wahrscheinlichkeit
    phase = db.Column(db.String(50), default=SalesStage.LEAD, index=True)
    verkaufschance_prozent = db.Column(db.Integer, default=20)

    # Werte
    erwarteter_wert = db.Column(db.Float)  # Erwarteter Auftragswert
    gewichteter_wert = db.Column(db.Float)  # Erwarteter Wert × Wahrscheinlichkeit

    # Termine
    erwarteter_abschluss = db.Column(db.Date, index=True)
    tatsaechlicher_abschluss = db.Column(db.Date)

    # Verantwortlich
    verantwortlich = db.Column(db.String(80))  # Verkäufer/Bearbeiter

    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Beziehungen
    kunde = db.relationship('Customer', foreign_keys=[kunde_id], backref='sales_opportunities')
    angebot = db.relationship('Angebot', foreign_keys=[angebot_id])
    auftrag = db.relationship('Order', foreign_keys=[auftrag_id])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._berechne_gewichteten_wert()

    def _berechne_gewichteten_wert(self):
        """Berechnet gewichteten Wert (Erwarteter Wert × Wahrscheinlichkeit)"""
        if self.erwarteter_wert and self.verkaufschance_prozent:
            self.gewichteter_wert = self.erwarteter_wert * (self.verkaufschance_prozent / 100.0)

    def phase_aendern(self, neue_phase, created_by=None):
        """
        Ändert Verkaufsphase

        Args:
            neue_phase: Neue Phase (SalesStage)
            created_by: Benutzer
        """
        alte_phase = self.phase
        self.phase = neue_phase

        # Wahrscheinlichkeit anpassen
        wahrscheinlichkeiten = {
            SalesStage.LEAD: 20,
            SalesStage.QUALIFIZIERT: 40,
            SalesStage.ANGEBOT: 60,
            SalesStage.VERHANDLUNG: 80,
            SalesStage.GEWONNEN: 100,
            SalesStage.VERLOREN: 0
        }
        self.verkaufschance_prozent = wahrscheinlichkeiten.get(neue_phase, 50)

        # Gewichteten Wert neu berechnen
        self._berechne_gewichteten_wert()

        # Aktivität erstellen
        Activity.create_activity(
            activity_type=ActivityType.NOTE,
            titel=f"Verkaufsphase geändert: {alte_phase} → {neue_phase}",
            kunde_id=self.kunde_id,
            angebot_id=self.angebot_id,
            created_by=created_by
        )

        db.session.commit()

    def gewinnen(self, auftrag_id, created_by=None):
        """
        Markiert Chance als gewonnen

        Args:
            auftrag_id: ID des gewonnenen Auftrags
            created_by: Benutzer
        """
        self.phase = SalesStage.GEWONNEN
        self.verkaufschance_prozent = 100
        self.auftrag_id = auftrag_id
        self.tatsaechlicher_abschluss = date.today()

        Activity.create_activity(
            activity_type=ActivityType.NOTE,
            titel=f"Verkaufschance gewonnen! Auftrag {auftrag_id}",
            kunde_id=self.kunde_id,
            auftrag_id=auftrag_id,
            created_by=created_by
        )

        db.session.commit()

    def verlieren(self, grund, created_by=None):
        """
        Markiert Chance als verloren

        Args:
            grund: Grund für Verlust
            created_by: Benutzer
        """
        self.phase = SalesStage.VERLOREN
        self.verkaufschance_prozent = 0
        self._berechne_gewichteten_wert()

        Activity.create_activity(
            activity_type=ActivityType.NOTE,
            titel=f"Verkaufschance verloren: {grund}",
            kunde_id=self.kunde_id,
            angebot_id=self.angebot_id,
            created_by=created_by
        )

        db.session.commit()

    def __repr__(self):
        return f'<SalesFunnel {self.titel} ({self.phase}, {self.verkaufschance_prozent}%)>'
