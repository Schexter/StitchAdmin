-- Nummernkreis-Einstellungen
CREATE TABLE IF NOT EXISTS number_sequence_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_type VARCHAR(50) UNIQUE NOT NULL,
    prefix VARCHAR(10) NOT NULL,
    use_year BOOLEAN DEFAULT 1,
    use_month BOOLEAN DEFAULT 0,
    number_length INTEGER DEFAULT 4,
    format_pattern VARCHAR(100),
    current_year INTEGER,
    current_month INTEGER,
    current_number INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

-- Nummernkreis-Protokoll (für Finanzamt)
CREATE TABLE IF NOT EXISTS number_sequence_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_type VARCHAR(50) NOT NULL,
    document_number VARCHAR(100) UNIQUE NOT NULL,
    document_id VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by VARCHAR(80),
    amount_net REAL,
    amount_tax REAL,
    amount_gross REAL,
    is_cancelled BOOLEAN DEFAULT 0,
    cancelled_at DATETIME,
    cancelled_by VARCHAR(80),
    cancellation_reason TEXT,
    tse_transaction_number VARCHAR(100),
    tse_signature TEXT,
    tse_time_format VARCHAR(50),
    metadata_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_number_log_type ON number_sequence_log(document_type);
CREATE INDEX IF NOT EXISTS idx_number_log_number ON number_sequence_log(document_number);
CREATE INDEX IF NOT EXISTS idx_number_log_created ON number_sequence_log(created_at);
-- Angebote
CREATE TABLE IF NOT EXISTS angebote (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    angebotsnummer VARCHAR(50) UNIQUE NOT NULL,
    kunde_id VARCHAR(50) NOT NULL,
    kunde_name VARCHAR(200) NOT NULL,
    kunde_adresse TEXT,
    kunde_email VARCHAR(120),
    status VARCHAR(20) DEFAULT 'entwurf',
    angebotsdatum DATE NOT NULL,
    gueltig_bis DATE,
    gueltig_tage INTEGER DEFAULT 30,
    titel VARCHAR(200),
    beschreibung TEXT,
    bemerkungen TEXT,
    netto_gesamt REAL DEFAULT 0.0,
    mwst_gesamt REAL DEFAULT 0.0,
    brutto_gesamt REAL DEFAULT 0.0,
    rabatt_prozent REAL DEFAULT 0.0,
    rabatt_betrag REAL DEFAULT 0.0,
    zahlungsbedingungen TEXT,
    lieferzeit VARCHAR(100),
    versandkosten REAL DEFAULT 0.0,
    auftrag_id VARCHAR(50),
    in_auftrag_umgewandelt_am DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(80),
    updated_at DATETIME,
    updated_by VARCHAR(80),
    pdf_erstellt_am DATETIME,
    pdf_path VARCHAR(500),
    FOREIGN KEY (kunde_id) REFERENCES customers(id),
    FOREIGN KEY (auftrag_id) REFERENCES orders(id)
);

CREATE INDEX IF NOT EXISTS idx_angebote_nummer ON angebote(angebotsnummer);
CREATE INDEX IF NOT EXISTS idx_angebote_kunde ON angebote(kunde_id);
CREATE INDEX IF NOT EXISTS idx_angebote_status ON angebote(status);

-- Angebots-Positionen
CREATE TABLE IF NOT EXISTS angebots_positionen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    angebot_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    artikel_id VARCHAR(50),
    artikel_name VARCHAR(200) NOT NULL,
    beschreibung TEXT,
    bemerkungen TEXT,
    menge REAL NOT NULL DEFAULT 1,
    einheit VARCHAR(20) DEFAULT 'Stück',
    einzelpreis REAL NOT NULL,
    mwst_satz REAL DEFAULT 19.0,
    rabatt_prozent REAL DEFAULT 0.0,
    rabatt_betrag REAL DEFAULT 0.0,
    netto_betrag REAL,
    mwst_betrag REAL,
    brutto_betrag REAL,
    FOREIGN KEY (angebot_id) REFERENCES angebote(id) ON DELETE CASCADE,
    FOREIGN KEY (artikel_id) REFERENCES articles(id)
);

CREATE INDEX IF NOT EXISTS idx_angebots_pos_angebot ON angebots_positionen(angebot_id);

-- Lieferscheine
CREATE TABLE IF NOT EXISTS lieferscheine (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lieferscheinnummer VARCHAR(50) UNIQUE NOT NULL,
    typ VARCHAR(20) DEFAULT 'lieferschein',
    auftrag_id VARCHAR(50),
    rechnung_id INTEGER,
    kunde_id VARCHAR(50) NOT NULL,
    kunde_name VARCHAR(200) NOT NULL,
    kunde_adresse TEXT,
    lieferadresse_name VARCHAR(200),
    lieferadresse_adresse TEXT,
    status VARCHAR(20) DEFAULT 'entwurf',
    lieferdatum DATE NOT NULL,
    geplantes_versanddatum DATE,
    tatsaechliches_versanddatum DATE,
    versandart VARCHAR(100),
    trackingnummer VARCHAR(100),
    anzahl_pakete INTEGER DEFAULT 1,
    gewicht_kg REAL,
    bemerkungen TEXT,
    interne_notizen TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(80),
    updated_at DATETIME,
    updated_by VARCHAR(80),
    pdf_erstellt_am DATETIME,
    pdf_path VARCHAR(500),
    FOREIGN KEY (kunde_id) REFERENCES customers(id),
    FOREIGN KEY (auftrag_id) REFERENCES orders(id),
    FOREIGN KEY (rechnung_id) REFERENCES rechnungen(id)
);

CREATE INDEX IF NOT EXISTS idx_lieferscheine_nummer ON lieferscheine(lieferscheinnummer);
CREATE INDEX IF NOT EXISTS idx_lieferscheine_kunde ON lieferscheine(kunde_id);
CREATE INDEX IF NOT EXISTS idx_lieferscheine_auftrag ON lieferscheine(auftrag_id);

-- Lieferschein-Positionen
CREATE TABLE IF NOT EXISTS lieferschein_positionen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lieferschein_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    artikel_id VARCHAR(50),
    artikel_name VARCHAR(200) NOT NULL,
    artikelnummer VARCHAR(100),
    menge REAL NOT NULL DEFAULT 1,
    einheit VARCHAR(20) DEFAULT 'Stück',
    seriennummern TEXT,
    bemerkungen TEXT,
    FOREIGN KEY (lieferschein_id) REFERENCES lieferscheine(id) ON DELETE CASCADE,
    FOREIGN KEY (artikel_id) REFERENCES articles(id)
);

CREATE INDEX IF NOT EXISTS idx_lieferschein_pos_ls ON lieferschein_positionen(lieferschein_id);
-- Mahnungen
CREATE TABLE IF NOT EXISTS mahnungen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mahnungsnummer VARCHAR(50) UNIQUE NOT NULL,
    rechnung_id INTEGER NOT NULL,
    kunde_id VARCHAR(50) NOT NULL,
    mahnstufe INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'entwurf',
    mahndatum DATE NOT NULL,
    versanddatum DATE,
    zahlungsfrist DATE NOT NULL,
    zahlungsfrist_tage INTEGER DEFAULT 7,
    forderungsbetrag REAL NOT NULL,
    offener_betrag REAL NOT NULL,
    mahngebuehr REAL DEFAULT 0.0,
    verzugszinsen REAL DEFAULT 0.0,
    gesamtbetrag REAL NOT NULL,
    zinssatz_prozent REAL,
    zinsen_von_datum DATE,
    zinsen_bis_datum DATE,
    verzugstage INTEGER,
    mahntext TEXT,
    bemerkungen TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(80),
    updated_at DATETIME,
    updated_by VARCHAR(80),
    pdf_erstellt_am DATETIME,
    pdf_path VARCHAR(500),
    FOREIGN KEY (rechnung_id) REFERENCES rechnungen(id),
    FOREIGN KEY (kunde_id) REFERENCES customers(id)
);

CREATE INDEX IF NOT EXISTS idx_mahnungen_nummer ON mahnungen(mahnungsnummer);
CREATE INDEX IF NOT EXISTS idx_mahnungen_rechnung ON mahnungen(rechnung_id);
CREATE INDEX IF NOT EXISTS idx_mahnungen_kunde ON mahnungen(kunde_id);
CREATE INDEX IF NOT EXISTS idx_mahnungen_status ON mahnungen(status);

-- Ratenzahlungen
CREATE TABLE IF NOT EXISTS ratenzahlungen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vereinbarungsnummer VARCHAR(50) UNIQUE NOT NULL,
    rechnung_id INTEGER NOT NULL,
    kunde_id VARCHAR(50) NOT NULL,
    vereinbarungsdatum DATE NOT NULL,
    gesamtbetrag REAL NOT NULL,
    anzahl_raten INTEGER NOT NULL,
    ratenbetrag REAL NOT NULL,
    erste_rate_datum DATE NOT NULL,
    raten_intervall_tage INTEGER DEFAULT 30,
    zinssatz_prozent REAL DEFAULT 0.0,
    status VARCHAR(20) DEFAULT 'aktiv',
    bezahlt_betrag REAL DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(80),
    updated_at DATETIME,
    updated_by VARCHAR(80),
    FOREIGN KEY (rechnung_id) REFERENCES rechnungen(id),
    FOREIGN KEY (kunde_id) REFERENCES customers(id)
);

CREATE INDEX IF NOT EXISTS idx_ratenzahlungen_nummer ON ratenzahlungen(vereinbarungsnummer);
CREATE INDEX IF NOT EXISTS idx_ratenzahlungen_rechnung ON ratenzahlungen(rechnung_id);
CREATE INDEX IF NOT EXISTS idx_ratenzahlungen_kunde ON ratenzahlungen(kunde_id);

-- Einzelne Raten
CREATE TABLE IF NOT EXISTS raten (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ratenzahlung_id INTEGER NOT NULL,
    ratennummer INTEGER NOT NULL,
    betrag REAL NOT NULL,
    faelligkeitsdatum DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'offen',
    bezahlt_datum DATE,
    bezahlt_betrag REAL DEFAULT 0.0,
    FOREIGN KEY (ratenzahlung_id) REFERENCES ratenzahlungen(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_raten_ratenzahlung ON raten(ratenzahlung_id);
CREATE INDEX IF NOT EXISTS idx_raten_faelligkeit ON raten(faelligkeitsdatum);
CREATE INDEX IF NOT EXISTS idx_raten_status ON raten(status);
-- Aktivitäten (CRM)
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'erledigt',
    kunde_id VARCHAR(50),
    angebot_id INTEGER,
    auftrag_id VARCHAR(50),
    rechnung_id INTEGER,
    titel VARCHAR(200) NOT NULL,
    beschreibung TEXT,
    ergebnis TEXT,
    geplant_am DATETIME,
    erledigt_am DATETIME,
    faellig_am DATETIME,
    dauer_minuten INTEGER,
    prioritaet VARCHAR(20) DEFAULT 'normal',
    follow_up_erforderlich BOOLEAN DEFAULT 0,
    follow_up_datum DATE,
    follow_up_erledigt BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(80),
    updated_at DATETIME,
    updated_by VARCHAR(80),
    anhaenge_json TEXT,
    FOREIGN KEY (kunde_id) REFERENCES customers(id),
    FOREIGN KEY (angebot_id) REFERENCES angebote(id),
    FOREIGN KEY (auftrag_id) REFERENCES orders(id),
    FOREIGN KEY (rechnung_id) REFERENCES rechnungen(id)
);

CREATE INDEX IF NOT EXISTS idx_activities_type ON activities(activity_type);
CREATE INDEX IF NOT EXISTS idx_activities_status ON activities(status);
CREATE INDEX IF NOT EXISTS idx_activities_kunde ON activities(kunde_id);
CREATE INDEX IF NOT EXISTS idx_activities_angebot ON activities(angebot_id);
CREATE INDEX IF NOT EXISTS idx_activities_auftrag ON activities(auftrag_id);
CREATE INDEX IF NOT EXISTS idx_activities_faellig ON activities(faellig_am);
CREATE INDEX IF NOT EXISTS idx_activities_follow_up ON activities(follow_up_datum);
CREATE INDEX IF NOT EXISTS idx_activities_created ON activities(created_at);

-- Angebots-Tracking (erweiterte CRM-Features)
CREATE TABLE IF NOT EXISTS angebot_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    angebot_id INTEGER UNIQUE NOT NULL,
    verkaufschance_prozent INTEGER DEFAULT 50,
    erwarteter_abschluss_datum DATE,
    hat_konkurrenz BOOLEAN DEFAULT 0,
    konkurrenz_info TEXT,
    entscheidungskriterien TEXT,
    budget_vorhanden BOOLEAN,
    letzter_kontakt DATE,
    naechster_kontakt_geplant DATE,
    anzahl_nachfragen INTEGER DEFAULT 0,
    grund_fuer_verzoegerung TEXT,
    naechste_schritte TEXT,
    verlustgrund VARCHAR(100),
    verlust_details TEXT,
    verlust_an_konkurrent VARCHAR(200),
    gewinn_faktoren TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    updated_by VARCHAR(80),
    FOREIGN KEY (angebot_id) REFERENCES angebote(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_angebot_tracking_angebot ON angebot_tracking(angebot_id);
CREATE INDEX IF NOT EXISTS idx_angebot_tracking_letzter_kontakt ON angebot_tracking(letzter_kontakt);
CREATE INDEX IF NOT EXISTS idx_angebot_tracking_naechster_kontakt ON angebot_tracking(naechster_kontakt_geplant);

-- Sales Funnel (Verkaufschancen-Pipeline)
CREATE TABLE IF NOT EXISTS sales_funnel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titel VARCHAR(200) NOT NULL,
    beschreibung TEXT,
    kunde_id VARCHAR(50) NOT NULL,
    angebot_id INTEGER,
    auftrag_id VARCHAR(50),
    phase VARCHAR(50) DEFAULT 'lead',
    verkaufschance_prozent INTEGER DEFAULT 20,
    erwarteter_wert REAL,
    gewichteter_wert REAL,
    erwarteter_abschluss DATE,
    tatsaechlicher_abschluss DATE,
    verantwortlich VARCHAR(80),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    FOREIGN KEY (kunde_id) REFERENCES customers(id),
    FOREIGN KEY (angebot_id) REFERENCES angebote(id),
    FOREIGN KEY (auftrag_id) REFERENCES orders(id)
);

CREATE INDEX IF NOT EXISTS idx_sales_funnel_kunde ON sales_funnel(kunde_id);
CREATE INDEX IF NOT EXISTS idx_sales_funnel_phase ON sales_funnel(phase);
CREATE INDEX IF NOT EXISTS idx_sales_funnel_abschluss ON sales_funnel(erwarteter_abschluss);

-- Angebote erweitern (neue Spalten)
-- Hinweis: Diese Spalte muss zur bestehenden angebote-Tabelle hinzugefügt werden
ALTER TABLE angebote ADD COLUMN erstellt_aus_auftrag_id VARCHAR(50);
