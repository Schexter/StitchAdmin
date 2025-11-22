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
