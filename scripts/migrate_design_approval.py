# -*- coding: utf-8 -*-
"""
Migration: Design-Freigabe-Tabellen erstellen
==============================================
Erstellt die neuen Tabellen für den verbesserten Design-Freigabe-Workflow

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
import sys

# Pfad zum src-Verzeichnis hinzufügen
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

def run_migration():
    """Führt die Migration aus"""
    
    from src.app import create_app
    from src.models import db
    
    app = create_app()
    
    with app.app_context():
        # Neue Tabellen aus design_approval.py erstellen
        
        sql_statements = [
            # DesignApprovalRequest
            """
            CREATE TABLE IF NOT EXISTS design_approval_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id VARCHAR(50) NOT NULL,
                design_id INTEGER,
                token VARCHAR(100) UNIQUE NOT NULL,
                status VARCHAR(30) DEFAULT 'draft',
                pdf_file_path VARCHAR(500),
                pdf_file_hash VARCHAR(64),
                signed_pdf_path VARCHAR(500),
                signature_type VARCHAR(30),
                signature_data TEXT,
                signature_certificate TEXT,
                signer_name VARCHAR(200),
                signer_email VARCHAR(200),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                sent_at DATETIME,
                viewed_at DATETIME,
                approved_at DATETIME,
                expires_at DATETIME,
                ip_address VARCHAR(50),
                user_agent VARCHAR(500),
                customer_notes TEXT,
                internal_notes TEXT,
                revision_details TEXT,
                created_by VARCHAR(100),
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (design_id) REFERENCES order_designs(id)
            )
            """,
            
            # Index für Token-Suche
            """
            CREATE INDEX IF NOT EXISTS idx_design_approval_token 
            ON design_approval_requests(token)
            """,
            
            # Index für Status-Filterung
            """
            CREATE INDEX IF NOT EXISTS idx_design_approval_status 
            ON design_approval_requests(status)
            """,
            
            # DesignApprovalHistory
            """
            CREATE TABLE IF NOT EXISTS design_approval_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL,
                action VARCHAR(50) NOT NULL,
                details TEXT,
                performed_by VARCHAR(100),
                ip_address VARCHAR(50),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                attachment_path VARCHAR(500),
                attachment_name VARCHAR(200),
                FOREIGN KEY (request_id) REFERENCES design_approval_requests(id) ON DELETE CASCADE
            )
            """,
            
            # DesignApprovalEmailTracking
            """
            CREATE TABLE IF NOT EXISTS design_approval_email_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL,
                message_id VARCHAR(200),
                recipient_email VARCHAR(200),
                subject VARCHAR(500),
                sent_at DATETIME,
                delivered_at DATETIME,
                opened_at DATETIME,
                clicked_at DATETIME,
                bounced BOOLEAN DEFAULT 0,
                bounce_reason TEXT,
                has_pdf_attachment BOOLEAN DEFAULT 0,
                pdf_attachment_hash VARCHAR(64),
                FOREIGN KEY (request_id) REFERENCES design_approval_requests(id) ON DELETE CASCADE
            )
            """
        ]
        
        print("=" * 60)
        print("Migration: Design-Freigabe-Tabellen")
        print("=" * 60)
        
        from sqlalchemy import text
        
        for i, sql in enumerate(sql_statements, 1):
            try:
                db.session.execute(text(sql))
                print(f"✓ Statement {i} erfolgreich ausgeführt")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"⊘ Statement {i} übersprungen (existiert bereits)")
                else:
                    print(f"✗ Statement {i} fehlgeschlagen: {e}")
        
        db.session.commit()
        
        print("=" * 60)
        print("Migration abgeschlossen!")
        print("=" * 60)
        
        # Verzeichnisse erstellen
        instance_path = app.instance_path
        dirs_to_create = [
            os.path.join(instance_path, 'design_approvals'),
            os.path.join(instance_path, 'design_approvals', 'sent'),
            os.path.join(instance_path, 'design_approvals', 'signed'),
        ]
        
        for dir_path in dirs_to_create:
            os.makedirs(dir_path, exist_ok=True)
            print(f"✓ Verzeichnis erstellt: {dir_path}")


if __name__ == '__main__':
    run_migration()
