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
