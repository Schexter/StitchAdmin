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
