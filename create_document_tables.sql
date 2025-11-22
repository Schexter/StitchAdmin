-- ============================================
-- StitchAdmin 2.0 - Dokumentenmanagement Module
-- Datenbank-Tabellen für DMS, Postbuch & E-Mail
-- Erstellt von Hans Hahn - Alle Rechte vorbehalten
-- ============================================

-- Tabelle: documents
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(300) NOT NULL,
    document_number VARCHAR(50) UNIQUE NOT NULL,
    
    -- Klassifizierung
    category VARCHAR(50),
    subcategory VARCHAR(50),
    tags VARCHAR(500),
    
    -- Datei-Info
    filename VARCHAR(255),
    original_filename VARCHAR(255),
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    mime_type VARCHAR(100),
    file_hash VARCHAR(64),
    
    -- OCR & Suche
    ocr_text TEXT,
    searchable_content TEXT,
    
    -- Verknüpfungen
    customer_id INTEGER,
    order_id INTEGER,
    invoice_id INTEGER,
    supplier_id INTEGER,
    
    -- Metadaten
    document_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    uploaded_by INTEGER,
    
    -- Versionierung
    version INTEGER DEFAULT 1,
    parent_document_id INTEGER,
    is_latest_version BOOLEAN DEFAULT 1,
    version_comment TEXT,
    
    -- GoBD / Compliance
    is_archived BOOLEAN DEFAULT 0,
    archive_date DATETIME,
    retention_until DATE,
    is_locked BOOLEAN DEFAULT 0,
    
    -- Zugriffsrechte
    visibility VARCHAR(20) DEFAULT 'private',
    department VARCHAR(50),
    
    -- Zusatzfelder
    description TEXT,
    notes TEXT,
    
    -- Foreign Keys
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    FOREIGN KEY (uploaded_by) REFERENCES users(id),
    FOREIGN KEY (parent_document_id) REFERENCES documents(id)
);

-- Indizes für documents
CREATE INDEX IF NOT EXISTS idx_documents_number ON documents(document_number);
CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category);
CREATE INDEX IF NOT EXISTS idx_documents_customer ON documents(customer_id);
CREATE INDEX IF NOT EXISTS idx_documents_order ON documents(order_id);
CREATE INDEX IF NOT EXISTS idx_documents_created ON documents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(file_hash);


-- Tabelle: document_access_logs
CREATE TABLE IF NOT EXISTS document_access_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    
    action VARCHAR(50) NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    details TEXT,
    
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Indizes für document_access_logs
CREATE INDEX IF NOT EXISTS idx_access_logs_document ON document_access_logs(document_id);
CREATE INDEX IF NOT EXISTS idx_access_logs_user ON document_access_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_access_logs_timestamp ON document_access_logs(timestamp DESC);


-- Tabelle: post_entries (Postbuch)
CREATE TABLE IF NOT EXISTS post_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Basis
    entry_date DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    entry_number VARCHAR(50) UNIQUE,
    direction VARCHAR(10) NOT NULL CHECK(direction IN ('inbound', 'outbound')),
    type VARCHAR(30) NOT NULL,
    
    -- Absender/Empfänger
    sender VARCHAR(200),
    sender_address TEXT,
    recipient VARCHAR(200),
    recipient_address TEXT,
    
    -- Verknüpfungen
    customer_id INTEGER,
    supplier_id INTEGER,
    
    -- Inhalt
    subject VARCHAR(300) NOT NULL,
    reference_number VARCHAR(100),
    description TEXT,
    
    -- Tracking
    tracking_number VARCHAR(100),
    carrier VARCHAR(50),
    shipping_cost DECIMAL(10, 2),
    delivery_status VARCHAR(30),
    delivery_date DATETIME,
    signature_received BOOLEAN DEFAULT 0,
    signature_name VARCHAR(100),
    
    -- Weitere Verknüpfungen
    order_id INTEGER,
    invoice_id INTEGER,
    document_id INTEGER,
    
    -- Bearbeitung
    handled_by INTEGER,
    status VARCHAR(20) DEFAULT 'open',
    priority VARCHAR(20) DEFAULT 'normal',
    
    -- Fristen
    due_date DATE,
    reminder_date DATE,
    
    -- Kosten
    postage_cost DECIMAL(10, 2),
    
    -- Notizen
    notes TEXT,
    internal_notes TEXT,
    
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Keys
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(id),
    FOREIGN KEY (document_id) REFERENCES documents(id),
    FOREIGN KEY (handled_by) REFERENCES users(id)
);

-- Indizes für post_entries
CREATE INDEX IF NOT EXISTS idx_post_entry_number ON post_entries(entry_number);
CREATE INDEX IF NOT EXISTS idx_post_entry_date ON post_entries(entry_date DESC);
CREATE INDEX IF NOT EXISTS idx_post_direction ON post_entries(direction);
CREATE INDEX IF NOT EXISTS idx_post_status ON post_entries(status);
CREATE INDEX IF NOT EXISTS idx_post_customer ON post_entries(customer_id);


-- Tabelle: email_accounts
CREATE TABLE IF NOT EXISTS email_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Account-Info
    name VARCHAR(100) NOT NULL,
    email_address VARCHAR(255) UNIQUE NOT NULL,
    
    -- IMAP Settings
    imap_server VARCHAR(255),
    imap_port INTEGER DEFAULT 993,
    imap_use_ssl BOOLEAN DEFAULT 1,
    imap_username VARCHAR(255),
    imap_password_encrypted VARCHAR(500),
    
    -- SMTP Settings
    smtp_server VARCHAR(255),
    smtp_port INTEGER DEFAULT 587,
    smtp_use_tls BOOLEAN DEFAULT 1,
    smtp_username VARCHAR(255),
    smtp_password_encrypted VARCHAR(500),
    
    -- Settings
    auto_archive BOOLEAN DEFAULT 0,
    archive_folder VARCHAR(100) DEFAULT 'INBOX',
    check_interval INTEGER DEFAULT 15,
    
    -- Status
    is_active BOOLEAN DEFAULT 1,
    last_check DATETIME,
    last_error TEXT,
    
    -- Zuordnung
    default_customer_id INTEGER,
    
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (default_customer_id) REFERENCES customers(id)
);


-- Tabelle: archived_emails
CREATE TABLE IF NOT EXISTS archived_emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    email_account_id INTEGER NOT NULL,
    
    -- E-Mail Daten
    message_id VARCHAR(255),
    subject VARCHAR(500),
    from_address VARCHAR(255),
    to_address VARCHAR(500),
    cc_address VARCHAR(500),
    bcc_address VARCHAR(500),
    
    -- Inhalt
    body_text TEXT,
    body_html TEXT,
    
    -- Metadaten
    received_date DATETIME,
    size INTEGER,
    has_attachments BOOLEAN DEFAULT 0,
    attachment_count INTEGER DEFAULT 0,
    
    -- Verknüpfungen
    customer_id INTEGER,
    order_id INTEGER,
    document_id INTEGER,
    
    -- Klassifizierung
    category VARCHAR(50),
    is_read BOOLEAN DEFAULT 0,
    is_important BOOLEAN DEFAULT 0,
    
    -- Timestamps
    archived_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    archived_by INTEGER,
    
    -- Foreign Keys
    FOREIGN KEY (email_account_id) REFERENCES email_accounts(id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (document_id) REFERENCES documents(id),
    FOREIGN KEY (archived_by) REFERENCES users(id)
);

-- Indizes für archived_emails
CREATE INDEX IF NOT EXISTS idx_archived_email_account ON archived_emails(email_account_id);
CREATE INDEX IF NOT EXISTS idx_archived_received ON archived_emails(received_date DESC);
CREATE INDEX IF NOT EXISTS idx_archived_customer ON archived_emails(customer_id);
CREATE INDEX IF NOT EXISTS idx_archived_read ON archived_emails(is_read);


-- Tabelle: email_attachments
CREATE TABLE IF NOT EXISTS email_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    archived_email_id INTEGER NOT NULL,
    
    -- Datei-Info
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),
    file_size INTEGER,
    mime_type VARCHAR(100),
    
    -- Als Dokument gespeichert?
    document_id INTEGER,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (archived_email_id) REFERENCES archived_emails(id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

-- Indizes für email_attachments
CREATE INDEX IF NOT EXISTS idx_email_attachment_email ON email_attachments(archived_email_id);


-- ============================================
-- Initiale Daten
-- ============================================

-- Standard-Kategorien für Dokumente
INSERT OR IGNORE INTO settings (key, value, category) VALUES 
    ('document_categories', 'rechnung,vertrag,angebot,lieferschein,email,post,sonstiges', 'documents'),
    ('post_types', 'brief,einschreiben,einschreiben_rueckschein,paket,fax,email', 'documents'),
    ('post_carriers', 'DHL,DPD,Hermes,Deutsche Post,UPS,FedEx', 'documents');

-- ============================================
-- Views für Reports
-- ============================================

-- View: Dokumente pro Kategorie
CREATE VIEW IF NOT EXISTS v_documents_by_category AS
SELECT 
    category,
    COUNT(*) as count,
    SUM(file_size) / 1024.0 / 1024.0 as total_size_mb,
    MAX(created_at) as latest_upload
FROM documents
WHERE is_archived = 0
GROUP BY category;

-- View: Postbuch Statistiken
CREATE VIEW IF NOT EXISTS v_post_statistics AS
SELECT 
    direction,
    type,
    status,
    COUNT(*) as count,
    SUM(CASE WHEN due_date < DATE('now') AND status != 'completed' THEN 1 ELSE 0 END) as overdue_count
FROM post_entries
GROUP BY direction, type, status;

-- View: E-Mail Statistiken pro Account
CREATE VIEW IF NOT EXISTS v_email_statistics AS
SELECT 
    ea.id,
    ea.name,
    ea.email_address,
    COUNT(ae.id) as total_emails,
    SUM(CASE WHEN ae.is_read = 0 THEN 1 ELSE 0 END) as unread_count,
    SUM(ae.attachment_count) as total_attachments,
    MAX(ae.received_date) as latest_email
FROM email_accounts ea
LEFT JOIN archived_emails ae ON ea.id = ae.email_account_id
GROUP BY ea.id;

-- ============================================
-- Fertig!
-- ============================================

SELECT 'Dokumentenmanagement-Tabellen erfolgreich erstellt!' as status;
