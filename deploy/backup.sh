#!/bin/bash
# StitchAdmin Backup-Script
# Erstellt taeglich PostgreSQL-Dump + Uploads-Backup
# Aufbewahrt 14 Tage

BACKUP_DIR="/opt/stitchadmin/backups"
DATE=$(date +%Y-%m-%d_%H%M)
KEEP_DAYS=14

mkdir -p "$BACKUP_DIR"

# PostgreSQL Dump
echo "[$(date)] Starte PostgreSQL-Backup..."
PGPASSWORD=$(grep DATABASE_URL /opt/stitchadmin/app/.env 2>/dev/null | sed 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/') \
pg_dump -U stitchadmin -h localhost stitchadmin | gzip > "$BACKUP_DIR/db_${DATE}.sql.gz"

if [ $? -eq 0 ]; then
    echo "[OK] DB-Backup: db_${DATE}.sql.gz"
else
    echo "[FEHLER] DB-Backup fehlgeschlagen!"
    # Fallback: pg_dump mit lokaler Authentifizierung
    sudo -u stitchadmin pg_dump stitchadmin | gzip > "$BACKUP_DIR/db_${DATE}.sql.gz"
fi

# Uploads-Backup (nur wenn Aenderungen)
echo "[$(date)] Starte Uploads-Backup..."
tar czf "$BACKUP_DIR/uploads_${DATE}.tar.gz" -C /opt/stitchadmin/data uploads/ 2>/dev/null
echo "[OK] Uploads-Backup: uploads_${DATE}.tar.gz"

# Alte Backups loeschen (aelter als KEEP_DAYS Tage)
echo "[$(date)] Loesche Backups aelter als ${KEEP_DAYS} Tage..."
find "$BACKUP_DIR" -name "*.gz" -mtime +${KEEP_DAYS} -delete
echo "[OK] Aufgeraeumt"

# Backup-Groesse anzeigen
echo "Backup-Verzeichnis: $(du -sh $BACKUP_DIR | cut -f1)"
echo "[$(date)] Backup abgeschlossen."
