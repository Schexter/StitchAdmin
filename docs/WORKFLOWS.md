# Workflows: StitchAdmin 2.0

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Für:** Typische Arbeitsabläufe im System

---

## 📋 Inhaltsverzeichnis

1. [Workflow: Neuen Kunden anlegen](#workflow-neuen-kunden-anlegen)
2. [Workflow: Stickerei-Auftrag erstellen](#workflow-stickerei-auftrag-erstellen)
3. [Workflow: Design bestellen (extern)](#workflow-design-bestellen-extern)
4. [Workflow: Textilien nachbestellen](#workflow-textilien-nachbestellen)
5. [Workflow: Produktion planen](#workflow-produktion-planen)
6. [Workflow: Auftrag abrechnen](#workflow-auftrag-abrechnen)
7. [Workflow: DST-Datei importieren](#workflow-dst-datei-importieren)
8. [Workflow: Garn-Bestand prüfen](#workflow-garn-bestand-prüfen)
9. [Workflow: Versand abwickeln](#workflow-versand-abwickeln)
10. [Workflow: Monatsabschluss](#workflow-monatsabschluss)

---

## 1. Workflow: Neuen Kunden anlegen

**Ziel:** Privat- oder Geschäftskunden im System erfassen

### Schritte

#### 1. Navigation
```
Dashboard → Kunden → "Neuer Kunde"
```

#### 2. Kundentyp wählen
- **Privatkunde:** Einzelperson (Vorname + Nachname)
- **Geschäftskunde:** Firma (Firmenname + Ansprechpartner)

#### 3. Pflichtfelder ausfüllen

**Privatkunde:**
- ✅ Vorname
- ✅ Nachname
- ✅ E-Mail (für Rechnungen/Benachrichtigungen)
- ⚠️ Telefon (empfohlen)
- ⚠️ Adresse (empfohlen)

**Geschäftskunde:**
- ✅ Firmenname
- ✅ Ansprechpartner
- ✅ E-Mail
- ⚠️ Telefon (empfohlen)
- ⚠️ Adresse (empfohlen)
- ⚠️ Steuernummer / USt-ID (für Rechnungen)

#### 4. Optionale Felder
- Newsletter-Anmeldung (Checkbox)
- Geburtsdatum (für Marketing)
- Notizen (interne Infos)

#### 5. Speichern
- Button "Kunde erstellen" klicken
- System generiert automatisch Kunden-ID (z.B. `CUST-20251110-0001`)
- Weiterleitung zur Kunden-Detailseite

#### 6. Ergebnis
✅ Kunde ist jetzt im System  
✅ Kann bei Aufträgen ausgewählt werden  
✅ Erhält Rechnungen per E-Mail

---

## 2. Workflow: Stickerei-Auftrag erstellen

**Ziel:** Kompletten Stickerei-Auftrag von Anfang bis Ende erfassen

### Schritte

#### 1. Auftrag anlegen
```
Dashboard → Aufträge → "Neuer Auftrag"
```

#### 2. Grunddaten
- **Kunde auswählen:** Dropdown-Liste oder Suche
- **Auftragstyp:** "Stickerei" wählen
- **Liefertermin:** Wunschtermin des Kunden
- **Eilauftrag:** Checkbox wenn Express

#### 3. Textilien hinzufügen
Für jede Textil-Position:
- Artikel auswählen (z.B. "T-Shirt Basic schwarz")
- Menge eingeben (z.B. 10 Stück)
- Größen auswählen (z.B. 5× M, 5× L)
- Stickposition festlegen (z.B. "Brust links")

**Beispiel:**
```
Position 1:
- Artikel: T-Shirt Basic (#TSH-001)
- Farbe: Schwarz
- Größen: 5× M, 5× L
- Menge: 10 Stück
- Position: Brust links, 10cm×8cm
```

#### 4. Design-Workflow

**Fall A: Kunde hat Design**
- Design hochladen (DST-Datei)
- System analysiert automatisch:
  - Stichzahl
  - Anzahl Farben
  - Größe (mm)
- Status: "Kunde bereitgestellt" ✅

**Fall B: Design muss erstellt werden**
- Design-Status: "Muss bestellt werden"
- Lieferant auswählen (z.B. "Digitize4Less")
- Vorlage hochladen (Logo/Bild)
- Notizen für Digitalisierer
- Status: "Bei Lieferant bestellt" 🟡

#### 5. Garn auswählen
- Farben aus Design extrahieren
- Für jede Farbe passendes Garn wählen:
  ```
  Farbe 1 (Rot) → Madeira Polyneon 1800 (Karminrot)
  Farbe 2 (Weiß) → Madeira Polyneon 1001 (Schneeweiß)
  Farbe 3 (Schwarz) → Madeira Polyneon 1000 (Tiefschwarz)
  ```

#### 6. Preiskalkulation
System berechnet automatisch:
```
Textilien:      10× 8,50€ = 85,00€
Stickerei:      5.000 Stiche × 0,01€/Stich = 50,00€
Farbwechsel:    3 Farben × 2,50€ = 7,50€
Design-Kosten:  Einmalig 25,00€
─────────────────────────────────────
Netto:          167,50€
MwSt (19%):     31,83€
─────────────────────────────────────
Brutto:         199,33€
```

#### 7. Speichern & Status
- Button "Auftrag erstellen"
- Status automatisch: "Neu" (rot)
- Nächster Schritt: Produktion planen

---

## 3. Workflow: Design bestellen (extern)

**Ziel:** Design von externem Digitalisierer bestellen und verfolgen

### Schritte

#### 1. Auftrag öffnen
```
Aufträge → [Auftrag auswählen] → "Design"-Tab
```

#### 2. Design-Bestellung anlegen
- Button "Design bestellen" klicken
- Lieferant auswählen (z.B. "Digitize4Less")
- Vorlage hochladen:
  - Logo (PNG/JPG)
  - Oder: Skizze/Foto
- Größe angeben (z.B. "10cm × 8cm")
- Farben festlegen (z.B. "3 Farben: Rot, Weiß, Schwarz")

#### 3. Bestellung absenden
- E-Mail an Lieferant wird automatisch generiert:
  ```
  Betreff: Design-Auftrag #D-20251110-001
  
  Sehr geehrte Damen und Herren,
  
  bitte digitalisieren Sie folgendes Design:
  
  - Auftrag: A-20251110-001 (Kunde: Max Mustermann)
  - Größe: 10cm × 8cm
  - Farben: 3 (Rot, Weiß, Schwarz)
  - Dateiformat: DST
  - Gewünschter Liefertermin: 15.11.2025
  
  Vorlage siehe Anhang.
  
  Mit freundlichen Grüßen
  [Ihr Name]
  StitchAdmin
  ```

#### 4. Status-Tracking
- **Bestellt:** Warten auf Lieferant
- **In Bearbeitung:** Lieferant arbeitet daran (manuell setzen)
- **Erhalten:** DST-Datei vom Lieferant erhalten
- **Produktionsbereit:** Freigegeben für Stickerei

#### 5. Design empfangen
- DST-Datei hochladen
- System analysiert automatisch
- Status auf "Erhalten" setzen
- Benachrichtigung an Produktionsplanung

#### 6. Qualitätsprüfung
- DST-Datei in Software öffnen (z.B. Wilcom/Pulse)
- Prüfen:
  - Stichzahl korrekt?
  - Farbreihenfolge OK?
  - Größe stimmt?
- **OK:** Status auf "Produktionsbereit" ✅
- **Probleme:** Zurück an Lieferant

---

## 4. Workflow: Textilien nachbestellen

**Ziel:** Textilien für Auftrag beim Lieferanten bestellen

### Schritte

#### 1. Bestellbedarf ermitteln
```
Aufträge → [Auftrag öffnen] → "Textilien"-Tab
```

Für jede Position prüfen:
- Ist genug Lagerbestand?
- **Ja:** Aus Lager entnehmen ✅
- **Nein:** Nachbestellen 🛒

#### 2. Lieferanten-Bestellung anlegen
```
Button "Textilien bestellen" → Lieferant auswählen
```

**Beispiel:**
```
Lieferant: L-Shop (Bernd Lindemeyer)
Artikel:
- 10× T-Shirt Basic Schwarz, Größe M (Art.-Nr. TSH-001-M-BLK)
- 5× T-Shirt Basic Schwarz, Größe L (Art.-Nr. TSH-001-L-BLK)
- 10× Polo-Shirt Navy, Größe XL (Art.-Nr. POL-002-XL-NVY)

Gesamtpreis: 187,50€ netto
Liefertermin: 3-5 Werktage
```

#### 3. Bestellung absenden
- E-Mail an Lieferant (automatisch generiert)
- Oder: Im L-Shop Webshop bestellen
- Bestellnummer notieren (z.B. `LSH-20251110-042`)

#### 4. Status verfolgen
- **Bestellt:** Warten auf Lieferung
- **Unterwegs:** Versandbenachrichtigung erhalten
- **Geliefert:** Ware ist da

#### 5. Wareneingang
- Lieferung prüfen (Menge, Qualität, Größen korrekt?)
- In Lager einbuchen
- Lagerbestand wird automatisch aktualisiert
- Status der Auftragsposition: "Textilien verfügbar" ✅

#### 6. Produktion freigeben
- Sobald **Design UND Textilien** verfügbar:
- Auftrag kann in Produktion gehen

---

## 5. Workflow: Produktion planen

**Ziel:** Auftrag einer Maschine zuweisen und Produktion starten

### Schritte

#### 1. Aufträge priorisieren
```
Produktion → Produktionsplanung
```

Liste zeigt alle Aufträge mit:
- Liefertermin
- Status (Design + Textilien)
- Stichzahl
- Geschätzte Dauer

#### 2. Maschine auswählen
**Verfügbare Maschinen:**
- ZSK Racer 1 (6 Köpfe, 15 Nadeln)
- ZSK Racer 2 (6 Köpfe, 15 Nadeln)
- Brother PR-1050X (10 Nadeln)

**Kriterien:**
- Ist Maschine frei?
- Passt Design-Größe in Stickfeld?
- Genug Köpfe für Menge?

#### 3. Zeitslot reservieren
**Beispiel:**
```
Auftrag: A-20251110-001
Maschine: ZSK Racer 1
Start: 11.11.2025, 09:00 Uhr
Dauer: ~2 Stunden (5.000 Stiche × 10 Textilien)
Ende: 11.11.2025, 11:00 Uhr
```

#### 4. Produktion vorbereiten
Checkliste:
- [ ] DST-Datei auf USB-Stick kopieren
- [ ] Textilien bereitgelegt (10× T-Shirt M+L)
- [ ] Garne eingefädelt (Rot, Weiß, Schwarz)
- [ ] Vlies/Stabilizer bereit
- [ ] Maschine kalibriert

#### 5. Produktion starten
- Status auf "In Produktion" setzen
- Starttimestamp: Automatisch
- Maschine läuft...

#### 6. Produktion abschließen
- Qualitätskontrolle (alle Textilien OK?)
- Endzeitpunkt erfassen
- Tatsächliche Dauer speichern
- Status auf "Fertig" ✅
- Auftrag geht automatisch in "Versand"

---

## 6. Workflow: Auftrag abrechnen

**Ziel:** Rechnung erstellen und versenden

### Schritte

#### 1. Auftrag öffnen
```
Aufträge → [Auftrag auswählen] → "Rechnung"-Tab
```

#### 2. Rechnung generieren
Button "Rechnung erstellen" klicken

**System füllt automatisch:**
```
Rechnung: R-20251110-001
Datum: 10.11.2025
Fällig: 24.11.2025 (14 Tage)

An:
Max Mustermann
Musterstraße 1
12345 Musterstadt

Positionen:
1. T-Shirt Basic Schwarz (10 Stück)       85,00€
2. Stickerei "Logo" (5.000 Stiche)        50,00€
3. Digitalisierung einmalig               25,00€
────────────────────────────────────────────────
Netto:                                   160,00€
MwSt (19%):                               30,40€
────────────────────────────────────────────────
Brutto:                                  190,40€
```

#### 3. Rechnung prüfen
- Alle Positionen korrekt?
- Preise stimmen?
- Kunde korrekt?
- **Ja:** Weiter zu Schritt 4
- **Nein:** Rechnung bearbeiten

#### 4. Rechnung versenden
**Option A: Per E-Mail**
- Button "Per E-Mail senden"
- PDF wird automatisch generiert
- E-Mail-Vorlage öffnet sich:
  ```
  An: max@mustermann.de
  Betreff: Rechnung R-20251110-001
  
  Sehr geehrter Herr Mustermann,
  
  anbei erhalten Sie die Rechnung für Ihren Auftrag.
  
  Mit freundlichen Grüßen
  [Ihr Name]
  StitchAdmin
  
  Anhang: Rechnung_R-20251110-001.pdf
  ```

**Option B: Ausdrucken**
- Button "PDF herunterladen"
- Rechnung ausdrucken
- Manuell versenden (Post)

#### 5. Zahlung verfolgen
Status-Tracking:
- **Entwurf:** Noch nicht versendet
- **Versendet:** Rechnung ist raus
- **Teilbezahlt:** Anzahlung erhalten
- **Bezahlt:** Vollständig bezahlt ✅
- **Überfällig:** Fälligkeitsdatum überschritten ⚠️

#### 6. Zahlung erfassen
Wenn Zahlung eingeht:
- Rechnung öffnen
- Button "Zahlung erfassen"
- Betrag eingeben (z.B. 190,40€)
- Datum eingeben
- Zahlungsmethode (Bar/Überweisung/PayPal)
- Speichern
- Status wechselt automatisch auf "Bezahlt" ✅

---

## 7. Workflow: DST-Datei importieren

**Ziel:** Design-Datei ins Archiv aufnehmen und analysieren

### Schritte

#### 1. Design-Archiv öffnen
```
Dashboard → Design-Archiv → "Neues Design"
```

#### 2. DST-Datei hochladen
- Button "Datei auswählen"
- DST-Datei vom Computer wählen (z.B. `logo_firma_100x80.dst`)
- Upload startet automatisch

#### 3. Automatische Analyse
System extrahiert:
```
Dateiname: logo_firma_100x80.dst
Dateigröße: 42 KB
─────────────────────────────
Analysiert:
✓ Stichzahl: 4.856
✓ Farbwechsel: 3
✓ Breite: 100,3 mm
✓ Höhe: 79,8 mm
✓ Geschätzte Zeit: 12 Minuten (bei 800 SPM)
```

#### 4. Metadaten ergänzen
**Pflichtfelder:**
- Design-Name (z.B. "Firmenlogo Mustermann GmbH")
- Kategorie (z.B. "Logos" / "Schriftzüge" / "Motive")

**Optional:**
- Design-Nummer (z.B. "D-2025-001")
- Kunde zuordnen (wenn kundenspezifisch)
- Tags (z.B. "Logo, Firma, Schwarz-Weiß")
- Notizen ("Nur für Polo-Shirts verwenden")

#### 5. Thumbnail generieren
- System erstellt automatisch Vorschaubild
- Thumbnail (200×200 px) wird gespeichert
- Anzeige in Liste

#### 6. Design freigeben
- Button "Design speichern"
- Design ist jetzt im Archiv ✅
- Kann bei Aufträgen ausgewählt werden
- Suchbar über Name, Nummer, Tags

#### 7. Design verwenden
Bei neuem Auftrag:
```
Auftrag erstellen → Design → "Aus Archiv wählen"
→ Design "Firmenlogo Mustermann GmbH" auswählen ✅
```

---

## 8. Workflow: Garn-Bestand prüfen

**Ziel:** Garnvorrat überprüfen und Nachbestellungen planen

### Schritte

#### 1. Garn-Übersicht öffnen
```
Dashboard → Garne → "Bestandsliste"
```

#### 2. Bestand filtern
**Ansichten:**
- **Alle Garne:** Komplett-Liste
- **Niedriger Bestand:** Unter Mindestbestand
- **Leer:** Stock = 0
- **Nach Farbe:** Sortiert nach Farbnummer
- **Nach Marke:** Madeira / Gütermann / etc.

#### 3. Kritische Garne identifizieren
**Beispiel:**
```
Garn: Madeira Polyneon 1800 (Karminrot)
Bestand: 3 Spulen
Mindestbestand: 10 Spulen
Status: ⚠️ Nachbestellen!

Garn: Madeira Polyneon 1001 (Schneeweiß)
Bestand: 45 Spulen
Mindestbestand: 20 Spulen
Status: ✅ Ausreichend
```

#### 4. Nachbestellung planen
Für jedes kritische Garn:
- Verbrauch schätzen (z.B. 5 Spulen/Woche)
- Lieferzeit beachten (z.B. 3-5 Tage)
- Sicherheitspuffer einrechnen
- **Beispiel:**
  ```
  Verbrauch: 5 Spulen/Woche
  Aktuell: 3 Spulen
  Lieferzeit: 5 Tage
  → Bestellen: 20 Spulen (= 4 Wochen Vorrat)
  ```

#### 5. Bestellung auslösen
```
Garn → [Garn auswählen] → "Nachbestellen"
```

Formular:
- Lieferant: Madeira Thread GmbH
- Menge: 20 Spulen
- Artikel-Nr.: POLYNEON-1800
- Preis: 2,50€/Spule = 50,00€
- Button "Bestellen"

#### 6. Wareneingang
Wenn Lieferung eintrifft:
- Garn-Detail öffnen
- "Wareneingang erfassen"
- Menge eingeben (z.B. +20 Spulen)
- Bestand wird automatisch aktualisiert
- Status: ✅ Wieder ausreichend

#### 7. Periodische Kontrolle
**Empfehlung:**
- Jeden Montag: Bestandsliste prüfen
- Nachbestellungen auslösen
- Alte/ungenutzte Garne aussortieren

---

## 9. Workflow: Versand abwickeln

**Ziel:** Fertige Aufträge an Kunden versenden

### Schritte

#### 1. Versandbereite Aufträge finden
```
Aufträge → Filter: "Status = Fertig"
```

Liste zeigt:
- Auftrag-Nr.
- Kunde
- Liefertermin
- Anzahl Pakete

#### 2. Verpackung vorbereiten
Checkliste:
- [ ] Textilien gebügelt/gefaltet
- [ ] Rechnung beigelegt (oder bereits versendet?)
- [ ] Karton/Versandtasche bereit
- [ ] Füllmaterial (Luftpolster)

#### 3. Versanddienstleister wählen
**Optionen:**
- **Abholung:** Kunde holt selbst ab
- **DHL:** Standard-Versand
- **DPD:** Express-Versand
- **Hermes:** Günstig für kleine Pakete

#### 4. Versandlabel erstellen
**Beispiel: DHL**
```
Versand → "Neuer Versand"

Empfänger:
Max Mustermann
Musterstraße 1
12345 Musterstadt

Paket:
Gewicht: 1,2 kg
Größe: 30×20×10 cm
Versicherung: 100€
```

System generiert:
- Tracking-Nr.: 00340434243490123456
- Versandkosten: 5,49€
- Label-PDF zum Ausdrucken

#### 5. Versand durchführen
- Label auf Paket kleben
- Paket zu DHL-Stelle bringen (oder Abholung)
- In System "Versandt" markieren
- Datum + Tracking-Nr. werden gespeichert

#### 6. Kunde informieren
Automatische E-Mail:
```
An: max@mustermann.de
Betreff: Ihr Auftrag A-20251110-001 wurde versandt

Sehr geehrter Herr Mustermann,

Ihr Auftrag wurde heute versandt!

Tracking-Link:
https://nolp.dhl.de/nextt-online-public/set_identcodes.do?...

Voraussichtliche Zustellung: 12.11.2025

Mit freundlichen Grüßen
[Ihr Name]
StitchAdmin
```

#### 7. Zustellung verfolgen
System prüft täglich Tracking-Status:
- **Unterwegs:** In Zustellung
- **Zugestellt:** Erfolgreich angekommen ✅
- **Problem:** Empfänger nicht angetroffen ⚠️

#### 8. Auftrag abschließen
Wenn Zustellung bestätigt:
- Status automatisch auf "Abgeschlossen" ✅
- Auftrag wird archiviert
- Statistik wird aktualisiert

---

## 10. Workflow: Monatsabschluss

**Ziel:** Monatliche Auswertung und Buchhaltung

### Schritte

#### 1. Umsatzübersicht
```
Berichte → Monatsübersicht → November 2025
```

**Kennzahlen:**
```
Zeitraum: 01.11.2025 - 30.11.2025
───────────────────────────────────────
Aufträge gesamt:          42
Aufträge abgeschlossen:   38
Aufträge storniert:        2
Aufträge in Bearbeitung:   2
───────────────────────────────────────
Umsatz brutto:         12.450,00€
Umsatz netto:          10.462,18€
MwSt (19%):             1.987,82€
───────────────────────────────────────
Wareneinsatz:           4.280,00€
Rohertrag:              6.182,18€
Marge:                    59,1%
```

#### 2. Offene Rechnungen
Liste:
```
R-20251105-012  Max Mustermann      190,40€  Überfällig seit 3 Tagen
R-20251120-034  Müller GmbH         850,00€  Fällig in 5 Tagen
R-20251125-041  Schmidt KG        1.200,00€  Fällig in 10 Tagen
───────────────────────────────────────────────────────────────
Gesamt offen:                     2.240,40€
```

**Mahnwesen:**
- Überfällige Rechnungen markieren
- Zahlungserinnerung versenden
- Bei >30 Tage: 1. Mahnung

#### 3. Lagerbestand
```
Berichte → Lagerbestand zum 30.11.2025
```

**Wert:**
```
Textilien:        2.450,00€  (85 Artikel)
Garne:              780,00€  (156 Spulen)
Verbrauchsmaterial: 120,00€  (Vlies, Stabilizer)
───────────────────────────────────────
Gesamtwert:       3.350,00€
```

#### 4. Export für DATEV
```
Berichte → DATEV-Export → November 2025
```

System generiert CSV-Dateien:
- Rechnungen (Erlöse)
- Eingangsrechnungen (Ausgaben)
- Zahlungen
- Artikelstamm

**Dateien:**
- `EXTF_Buchungsstapel_2025-11.csv`
- `EXTF_Kontenbeschriftung_2025-11.csv`

#### 5. Statistiken
```
Berichte → Monatsbericht
```

**Auswertungen:**
- Top 5 Kunden (nach Umsatz)
- Top 5 Artikel (nach Stückzahl)
- Produktivität (Stiche/Stunde)
- Auslastung Maschinen
- Liefertreue (%)

#### 6. Sicherung
```
Einstellungen → Datenbank → Backup erstellen
```

**Backup:**
- Dateiname: `stitchadmin_backup_2025-11-30.sql`
- Speicherort: `C:\Backups\StitchAdmin\`
- Automatische Prüfung: Backup OK? ✅

#### 7. Planung nächster Monat
- Kapazität prüfen
- Personalplanung
- Materialbestellungen
- Marketing-Aktionen

---

## 📊 Workflow-Matrix

| Workflow | Häufigkeit | Dauer | Priorität |
|----------|------------|-------|-----------|
| Neuer Kunde | Täglich | 5 Min | Hoch |
| Auftrag erstellen | Täglich | 15 Min | Hoch |
| Design bestellen | Wöchentlich | 10 Min | Mittel |
| Textilien bestellen | Wöchentlich | 15 Min | Hoch |
| Produktion planen | Täglich | 20 Min | Hoch |
| Rechnung erstellen | Täglich | 5 Min | Hoch |
| DST importieren | Bei Bedarf | 5 Min | Niedrig |
| Garn-Bestand | Wöchentlich | 10 Min | Mittel |
| Versand | Täglich | 10 Min | Hoch |
| Monatsabschluss | Monatlich | 60 Min | Hoch |

---

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**  
**Nutze diese Workflows für effiziente Arbeitsabläufe!** 💪🚀
