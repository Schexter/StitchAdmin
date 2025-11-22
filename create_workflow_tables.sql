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
