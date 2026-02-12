# Konzept: Dokument-Workflow & Belegkette
## StitchAdmin 2.0 - Vollständiger Geschäftsprozess

**Version:** 1.0  
**Datum:** 06.01.2025  
**Autor:** Hans Hahn - Alle Rechte vorbehalten

---

## 1. Executive Summary

Dieses Konzept beschreibt die Implementierung einer vollständigen Belegkette für StitchAdmin 2.0:

```
ANGEBOT → AUFTRAGSBESTÄTIGUNG → PRODUKTION → LIEFERSCHEIN → RECHNUNG
                                    ↓
                              ANZAHLUNG (optional)
```

**Kernziele:**
- Durchgängiger Dokumentenfluss ohne Medienbrüche
- GoBD-konforme Nummernkreise
- Flexibles Zahlungsmanagement (Anzahlungen, Teilrechnungen)
- Vereinfachte Auftragserfassung (Wizard statt Mega-Formular)

---

## 2. Nummernkreise-System

### 2.1 Übersicht der Belegarten

| Belegart | Präfix | Format | Beispiel | Beschreibung |
|----------|--------|--------|----------|--------------|
| Angebot | AN | AN-JJJJ-NNNN | AN-2025-0001 | Unverbindliches Angebot |
| Auftragsbestätigung | AB | AB-JJJJ-NNNN | AB-2025-0001 | Verbindliche Bestellung |
| Auftrag (intern) | A | A-JJJJ-NNNN | A-2025-0001 | Produktionsauftrag |
| Lieferschein | LS | LS-JJJJ-NNNN | LS-2025-0001 | Warenausgang |
| Rechnung | RE | RE-JJJJ-NNNN | RE-2025-0001 | Endrechnung |
| Anzahlungsrechnung | AR | AR-JJJJ-NNNN | AR-2025-0001 | Vorauszahlung |
| Gutschrift | GS | GS-JJJJ-NNNN | GS-2025-0001 | Storno/Korrektur |
| Kassenbeleg | K | K-JJJJ-NNNNNN | K-2025-000001 | Barverkauf (6-stellig) |

### 2.2 Nummernkreis-Regeln (GoBD)

- Fortlaufend & lückenlos innerhalb eines Jahres
- Keine Wiederverwendung von Nummern
- Stornos erhalten eigene Nummer (Gutschrift)
- Jahreswechsel: Neue Nummerierung ab 0001
- Unveränderbar nach Erstellung (nur Storno möglich)
- Revisionssicher archiviert

---

## 3. Dokument-Workflow

### 3.1 Kompletter Lebenszyklus

```
PHASE 1: ANGEBOT
━━━━━━━━━━━━━━━━
  Anfrage → Angebot erstellen → Angebot versenden → Status?
                                                      │
                            ┌─────────────────────────┼─────────────────────┐
                            ▼                         ▼                     ▼
                      ANGENOMMEN              ABGELEHNT              VERFALLEN
                            │
                            ▼
PHASE 2: AUFTRAGSBESTÄTIGUNG
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  AB generieren → Anzahlung erforderlich? → AB versenden
                            │
                   ┌────────┴────────┐
                   ▼                 ▼
            Anzahlungs-           NEIN
            rechnung              │
            erstellen             │
                   │              │
                   ▼              │
            Zahlung               │
            erfassen              │
                   │              │
                   └──────────────┘
                            │
                            ▼
PHASE 3: PRODUKTION
━━━━━━━━━━━━━━━━━━━
  Auftrag anlegen → Material bestellen → Produktion → QS → FERTIG
                            │
                            ▼
PHASE 4: LIEFERUNG
━━━━━━━━━━━━━━━━━━
                   ┌────────────────────┐
                   │   LIEFERART?       │
                   └────────┬───────────┘
           ┌────────────────┼────────────────┐
           ▼                ▼                ▼
       ABHOLUNG          VERSAND       TEILLIEFERUNG
           │                │                │
           ▼                ▼                ▼
       Lieferschein     Lieferschein    Mehrere
       + Unterschrift   + Paketlabel    Lieferscheine
                            │
                            ▼
PHASE 5: RECHNUNG
━━━━━━━━━━━━━━━━━
           ┌────────────────────────────────────┐
           │         RECHNUNGSTYP?              │
           └────────────────┬───────────────────┘
           ┌────────────────┼────────────────┐
           ▼                ▼                ▼
      KOMPLETT-        TEIL-           SCHLUSS-
      RECHNUNG        RECHNUNG         RECHNUNG
           │                │                │
           └────────────────┴────────────────┘
                            │
                            ▼
                    Rechnung versenden
                            │
                            ▼
                    Zahlung überwachen
                            │
                            ▼
                        BEZAHLT
```

### 3.2 Dokumenten-Umwandlung

| Von | Nach | Aktion | Automatisch übernommen |
|-----|------|--------|------------------------|
| Angebot | Auftragsbestätigung | "In Auftrag umwandeln" | Alle Positionen, Kunde, Preise |
| Angebot | Angebot (Kopie) | "Kopieren" | Alles außer Nummer/Datum |
| Auftragsbestätigung | Auftrag (intern) | "Produktion starten" | Verknüpfung |
| Auftragsbestätigung | Anzahlungsrechnung | "Anzahlung erstellen" | %-Betrag, Kunde |
| Auftrag | Lieferschein | "Lieferschein erstellen" | Positionen, Kunde |
| Lieferschein | Rechnung | "Rechnung erstellen" | Positionen, Lieferdatum |
| Rechnung | Gutschrift | "Stornieren" | Negative Werte |

---

## 4. Anzahlungen & Teilrechnungen

### 4.1 Anzahlungs-Workflow

```
Gesamtauftrag: 1.000,00 EUR brutto
Anzahlung: 50% = 500,00 EUR

1. ANZAHLUNGSRECHNUNG (AR-2025-0001)
   ┌────────────────────────────────────────────┐
   │ Pos. 1: Anzahlung für Auftrag AB-2025-0001 │
   │         50% gemäß Vereinbarung             │
   │                                            │
   │         Netto:    420,17 EUR               │
   │         MwSt 19%:  79,83 EUR               │
   │         Brutto:   500,00 EUR               │
   └────────────────────────────────────────────┘
   
2. ZAHLUNG ERFASSEN
   → 500,00 EUR eingegangen
   → Status: "bezahlt"
   
3. SCHLUSSRECHNUNG (RE-2025-0001)
   ┌────────────────────────────────────────────┐
   │ Pos. 1: T-Shirt bestickt, 20 Stück         │
   │         Netto:    840,34 EUR               │
   │         MwSt 19%: 159,66 EUR               │
   │         Brutto: 1.000,00 EUR               │
   │                                            │
   │ Abzgl. Anzahlung AR-2025-0001:  -500,00 EUR│
   │                                            │
   │ ════════════════════════════════════════   │
   │ ZU ZAHLEN:                       500,00 EUR│
   └────────────────────────────────────────────┘
```

### 4.2 Teillieferungen

```
Auftrag: 100 T-Shirts bestickt

LIEFERUNG 1 (60 Stück):
├── Lieferschein LS-2025-0001 (60 Stück)
├── Teilrechnung RE-2025-0001 (60 Stück)
└── Status Auftrag: "Teilweise geliefert"

LIEFERUNG 2 (40 Stück):
├── Lieferschein LS-2025-0002 (40 Stück)
├── Schlussrechnung RE-2025-0002 (40 Stück)
└── Status Auftrag: "Vollständig geliefert"
```

---

## 5. Vereinfachter Auftrags-Wizard

### 5.1 Problem: Aktuelles Formular

Das aktuelle Formular ist über 700 Zeilen mit vielen Feldern gleichzeitig sichtbar.
Dies überfordert den Benutzer.

### 5.2 Lösung: Step-by-Step Wizard

```
┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐
│  1  │──│  2  │──│  3  │──│  4  │──│  5  │──│  ✓  │
│Kunde│  │Texti│  │Vered│  │Preis│  │Check│  │Done │
└─────┘  └─────┘  └─────┘  └─────┘  └─────┘  └─────┘
```

#### Step 1: Kunde & Grunddaten
- Kunde wählen oder neu anlegen
- Projektname/Bezeichnung
- Auftragsart (Stickerei/Druck/Beides)
- Wunschtermin, Eilauftrag

#### Step 2: Textilien auswählen
- Artikelsuche mit Filter
- Größenstaffel eingeben (S: 5, M: 10, L: 15...)
- Warenkorb-Ansicht
- Mehrere Artikel möglich

#### Step 3: Veredelung
- Position wählen (Brust links, Rücken...)
- Logo hochladen oder aus Archiv
- Automatische DST-Analyse (Stiche, Größe, Farben)
- Garnfarben zuweisen
- Weitere Positionen hinzufügen

#### Step 4: Kalkulation
- Automatische Preisberechnung
- Aufschlüsselung (Textil + Veredelung + Setup)
- Mengenrabatt-Anzeige
- Manuelle Anpassungen möglich
- Stückpreis-Anzeige

#### Step 5: Zusammenfassung
- Komplettübersicht
- Dokumenttyp wählen (Angebot oder direkt Auftrag)
- Anzahlung erforderlich?
- Interne Notizen
- Abschließen

---

## 6. Datenmodell

### 6.1 Nummernkreise

```
Tabelle: nummernkreise
───────────────────────────────────────────────
id              INTEGER PRIMARY KEY
belegart        VARCHAR(20) UNIQUE    -- 'angebot', 'rechnung', etc.
praefix         VARCHAR(10)           -- 'AN', 'RE', etc.
aktuelles_jahr  INTEGER
aktuelle_nummer INTEGER DEFAULT 0
stellen         INTEGER DEFAULT 4     -- Anzahl Ziffern
trennzeichen    VARCHAR(5) DEFAULT '-'
jahr_format     VARCHAR(10) DEFAULT 'YYYY'
jahreswechsel_reset BOOLEAN DEFAULT TRUE
aktiv           BOOLEAN DEFAULT TRUE
```

### 6.2 Geschäftsdokumente

```
Tabelle: business_documents
───────────────────────────────────────────────
id                  INTEGER PRIMARY KEY
dokument_nummer     VARCHAR(50) UNIQUE
dokument_typ        VARCHAR(20)     -- 'angebot', 'ab', 'rechnung', etc.

-- Verkettung
vorgaenger_id       INTEGER FK → business_documents
auftrag_id          VARCHAR(50) FK → orders

-- Kunde
kunde_id            VARCHAR(50) FK → customers
rechnungsadresse    JSON            -- Snapshot
lieferadresse       JSON

-- Datum
dokument_datum      DATE
gueltig_bis         DATE            -- Für Angebote
faelligkeitsdatum   DATE            -- Für Rechnungen

-- Beträge
summe_netto         DECIMAL(12,2)
summe_mwst          DECIMAL(12,2)
summe_brutto        DECIMAL(12,2)
rabatt_prozent      DECIMAL(5,2)
rabatt_betrag       DECIMAL(12,2)
bereits_gezahlt     DECIMAL(12,2)   -- Summe Anzahlungen
restbetrag          DECIMAL(12,2)

-- Status
status              VARCHAR(20)     -- 'entwurf', 'versendet', 'bezahlt', etc.

-- Texte
betreff             VARCHAR(500)
einleitung          TEXT
schlussbemerkung    TEXT
interne_notiz       TEXT

-- Zahlungsbedingungen
zahlungsziel_tage   INTEGER DEFAULT 14
skonto_prozent      DECIMAL(5,2)
skonto_tage         INTEGER

-- PDF
pdf_pfad            VARCHAR(500)

-- Tracking
erstellt_am         TIMESTAMP
erstellt_von        VARCHAR(100)
versendet_am        TIMESTAMP
```

### 6.3 Dokumentpositionen

```
Tabelle: document_positions
───────────────────────────────────────────────
id                  INTEGER PRIMARY KEY
dokument_id         INTEGER FK → business_documents
position            INTEGER         -- Sortierung

-- Typ
typ                 VARCHAR(20)     -- 'artikel', 'veredelung', 'setup', etc.

-- Referenzen
artikel_id          INTEGER FK → articles
order_item_id       INTEGER FK → order_items

-- Beschreibung
artikelnummer       VARCHAR(100)
bezeichnung         VARCHAR(500)
beschreibung        TEXT

-- Mengen & Preise
menge               DECIMAL(10,3)
einheit             VARCHAR(20) DEFAULT 'Stk.'
einzelpreis_netto   DECIMAL(12,4)
rabatt_prozent      DECIMAL(5,2)

-- MwSt
mwst_satz           DECIMAL(5,2)    -- z.B. 19.00
mwst_kennzeichen    VARCHAR(10)     -- 'S', 'E', 'F'

-- Berechnete Werte
netto_gesamt        DECIMAL(12,2)
mwst_betrag         DECIMAL(12,2)
brutto_gesamt       DECIMAL(12,2)
```

### 6.4 Zahlungen

```
Tabelle: document_payments
───────────────────────────────────────────────
id                      INTEGER PRIMARY KEY
dokument_id             INTEGER FK → business_documents

zahlungsart             VARCHAR(30)     -- 'bar', 'ueberweisung', etc.
betrag                  DECIMAL(12,2)
zahlung_datum           DATE

transaktions_id         VARCHAR(100)    -- Bank-Referenz
anzahlungs_rechnung_id  INTEGER FK → business_documents

bestaetigt              BOOLEAN DEFAULT FALSE
bestaetigt_von          VARCHAR(100)
bestaetigt_am           TIMESTAMP

notiz                   TEXT
erstellt_am             TIMESTAMP
```

### 6.5 Zahlungsbedingungen (Vorlagen)

```
Tabelle: zahlungsbedingungen
───────────────────────────────────────────────
id                      INTEGER PRIMARY KEY
bezeichnung             VARCHAR(100)    -- z.B. "14 Tage netto"

zahlungsziel_tage       INTEGER DEFAULT 14
skonto_prozent          DECIMAL(5,2)
skonto_tage             INTEGER

anzahlung_erforderlich  BOOLEAN DEFAULT FALSE
anzahlung_prozent       DECIMAL(5,2)    -- z.B. 50%
anzahlung_text          VARCHAR(200)

text_rechnung           TEXT            -- Text für Dokumente
aktiv                   BOOLEAN DEFAULT TRUE
standard                BOOLEAN DEFAULT FALSE
```

---

## 7. Preiskalkulation

### 7.1 Kalkulationsschema

```
    MATERIAL          PRODUKTION         SERVICE
    ────────          ──────────         ───────
    • Textil          • Stickerei        • Express
    • Garn            • Druck            • Versand
    • Folie           • Nachbearb.       • Design
        │                 │                  │
        └─────────────────┴──────────────────┘
                          │
                          ▼
                  HERSTELLKOSTEN
                          │
                          ▼
                + Gewinnaufschlag (z.B. 40%)
                          │
                          ▼
                - Mengenrabatt
                          │
                          ▼
                + MwSt
                          │
                          ▼
                = VERKAUFSPREIS
```

### 7.2 Konfigurierbare Parameter

| Parameter | Beispielwert | Beschreibung |
|-----------|--------------|--------------|
| AUFSCHLAG_PROZENT | 40 | Gewinnaufschlag |
| SETUP_STICKEREI | 25,00 EUR | Einrichtung pro Design |
| SETUP_DRUCK | 15,00 EUR | Einrichtung Druck |
| STICKPREIS_PRO_1000 | 1,50 EUR | Pro 1000 Stiche |
| MIN_STICKPREIS | 2,00 EUR | Minimum pro Stück |
| DRUCKPREIS_PRO_CM2 | 0,05 EUR | Pro cm² |
| MIN_DRUCKPREIS | 1,50 EUR | Minimum pro Stück |

### 7.3 Mengenrabatt-Staffel

| Ab Menge | Rabatt |
|----------|--------|
| 25 | 0% |
| 50 | 5% |
| 100 | 10% |
| 250 | 15% |
| 500 | 20% |

---

## 8. Implementierungsplan

### Phase 1: Grundlagen (1-2 Wochen)
- [ ] Nummernkreis-Model & Migration
- [ ] Zahlungsbedingungen-Model
- [ ] BusinessDocument-Model
- [ ] DocumentPosition-Model
- [ ] Admin-UI für Nummernkreise

### Phase 2: Wizard (1-2 Wochen)
- [ ] Wizard-Controller
- [ ] Step 1-5 Templates
- [ ] Artikelsuche (AJAX)
- [ ] DST-Analyse Integration
- [ ] Kalkulations-Engine

### Phase 3: Angebote (1 Woche)
- [ ] Angebot CRUD
- [ ] PDF-Generierung
- [ ] E-Mail-Versand
- [ ] Status-Tracking

### Phase 4: Auftrag & Produktion (1 Woche)
- [ ] Angebot → AB Konvertierung
- [ ] AB-PDF
- [ ] Verknüpfung mit internem Auftrag

### Phase 5: Lieferung & Rechnung (1-2 Wochen)
- [ ] Lieferschein aus Auftrag
- [ ] Rechnung aus Lieferschein
- [ ] Anzahlungsrechnungen
- [ ] Schlussrechnung mit Anzahlungsabzug
- [ ] Teillieferungen

### Phase 6: Zahlungen & Mahnwesen (1 Woche)
- [ ] Zahlungserfassung
- [ ] Offene Posten Liste
- [ ] Mahnungsgenerierung

---

## 9. Zusammenfassung

| Vorher | Nachher |
|--------|---------|
| Einzelne Aufträge | Durchgängige Belegkette |
| Manuelle IDs | GoBD-konforme Nummernkreise |
| Komplexes Formular | Step-by-Step Wizard |
| Keine Angebote | Angebot → AB → Rechnung |
| Keine Anzahlungen | Flexible Zahlungsmodelle |
| Keine Lieferscheine | Vollständige Logistik |

**Geschätzter Aufwand:** 6-10 Wochen für komplette Implementierung

---

*Erstellt von Hans Hahn - Alle Rechte vorbehalten*
