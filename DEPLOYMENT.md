# 🚀 StitchAdmin 2.0 - Deployment Guide

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**

Dieser Guide beschreibt detailliert die Bereitstellung von StitchAdmin 2.0 in verschiedenen Umgebungen.

**Version:** 2.0.0
**Stand:** 13.11.2025

---

## 📋 Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Voraussetzungen](#voraussetzungen)
3. [Entwicklungs-Setup](#entwicklungs-setup)
4. [Produktions-Setup (Linux)](#produktions-setup-linux)
5. [Produktions-Setup (Windows)](#produktions-setup-windows)
6. [Docker-Setup](#docker-setup)
7. [Datenbank-Migration](#datenbank-migration)
8. [Umgebungsvariablen](#umgebungsvariablen)
9. [Backup-Strategie](#backup-strategie)
10. [Monitoring & Logs](#monitoring--logs)
11. [Sicherheit](#sicherheit)
12. [Performance-Tuning](#performance-tuning)
13. [Troubleshooting](#troubleshooting)

---

## 🎯 Übersicht

StitchAdmin 2.0 ist eine Flask-Anwendung mit SQLite/PostgreSQL-Datenbank. Es gibt mehrere Deployment-Optionen:

| Option | Einsatzzweck | Komplexität |
|--------|--------------|-------------|
| **Entwicklung** | Lokales Testing | ⭐ Einfach |
| **Produktion (Linux)** | Server-Deployment | ⭐⭐ Mittel |
| **Produktion (Windows)** | Windows-Server | ⭐⭐ Mittel |
| **Docker** | Container-Deployment | ⭐⭐⭐ Fortgeschritten |

---

## ✅ Voraussetzungen

### Minimale Anforderungen

- **Python:** 3.10 - 3.13
- **RAM:** 2 GB (4 GB empfohlen)
- **Festplatte:** 500 MB (+ Datenbank & Uploads)
- **Betriebssystem:** Windows 10/11, Ubuntu 20.04+, Debian 11+

### Empfohlene Software

- **Git:** Für Code-Updates
- **Nginx/Apache:** Als Reverse Proxy (Produktion)
- **PostgreSQL:** Für größere Datenbanken (optional)
- **Redis:** Für Session-Caching (optional)

---

## 🔧 Entwicklungs-Setup

### 1. Repository klonen

```bash
git clone https://github.com/your-username/StitchAdmin2.0.git
cd StitchAdmin2.0
```

### 2. Virtuelle Umgebung erstellen

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Dependencies installieren

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Python 3.13 Fix (falls nötig):**
```bash
pip install --upgrade "SQLAlchemy>=2.0.36"
```

### 4. Umgebungsvariablen konfigurieren

Erstelle `.env` aus `.env.example`:

```bash
cp .env.example .env  # Linux/Mac
copy .env.example .env  # Windows
```

Bearbeite `.env`:
```env
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production
```

### 5. Datenbank initialisieren

```bash
# Datenbank-Migrations erstellen
python -m flask db init

# Migrations ausführen
python -m flask db migrate -m "Initial migration"
python -m flask db upgrade
```

**Oder direkt:**
```python
python
>>> from app import create_app, db
>>> app = create_app()
>>> with app.app_context():
...     db.create_all()
>>> exit()
```

### 6. Anwendung starten

```bash
python app.py
```

Öffne Browser: `http://localhost:5000`

**Standard-Login:**
- Username: `admin`
- Passwort: `admin123`

---

## 🐧 Produktions-Setup (Linux)

### 1. Server vorbereiten

```bash
# System aktualisieren
sudo apt update && sudo apt upgrade -y

# Abhängigkeiten installieren
sudo apt install -y python3 python3-pip python3-venv git nginx

# PostgreSQL (optional)
sudo apt install -y postgresql postgresql-contrib
```

### 2. Benutzer erstellen

```bash
# Dedizierter Benutzer für die App
sudo useradd -m -s /bin/bash stitchadmin
sudo su - stitchadmin
```

### 3. Anwendung installieren

```bash
cd ~
git clone <your-repository-url> StitchAdmin2.0
cd StitchAdmin2.0

# Virtual Environment
python3 -m venv .venv
source .venv/bin/activate

# Dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn  # WSGI-Server
```

### 4. Produktions-Konfiguration

Erstelle `.env`:

```env
FLASK_APP=app.py
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=<generiere-starken-key>
DATABASE_URL=postgresql://user:password@localhost/stitchadmin
MAX_UPLOAD_SIZE=33554432  # 32MB
```

**Starken SECRET_KEY generieren:**
```bash
python -c 'import secrets; print(secrets.token_hex(32))'
```

### 5. PostgreSQL-Datenbank erstellen (optional)

```bash
# Als postgres-User
sudo -u postgres psql

# In psql:
CREATE DATABASE stitchadmin;
CREATE USER stitchadmin_user WITH PASSWORD 'sicheres-passwort';
GRANT ALL PRIVILEGES ON DATABASE stitchadmin TO stitchadmin_user;
\q
```

### 6. Gunicorn konfigurieren

Erstelle `gunicorn_config.py`:

```python
# /home/stitchadmin/StitchAdmin2.0/gunicorn_config.py
bind = "127.0.0.1:8000"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = "logs/gunicorn-access.log"
errorlog = "logs/gunicorn-error.log"
loglevel = "info"

# Process Naming
proc_name = "stitchadmin"

# Server Mechanics
daemon = False
pidfile = "gunicorn.pid"
```

Erstelle Log-Verzeichnis:
```bash
mkdir -p logs
```

### 7. Systemd Service erstellen

Als root erstellen: `/etc/systemd/system/stitchadmin.service`

```ini
[Unit]
Description=StitchAdmin 2.0 Web Application
After=network.target postgresql.service

[Service]
Type=notify
User=stitchadmin
Group=stitchadmin
WorkingDirectory=/home/stitchadmin/StitchAdmin2.0
Environment="PATH=/home/stitchadmin/StitchAdmin2.0/.venv/bin"
ExecStart=/home/stitchadmin/StitchAdmin2.0/.venv/bin/gunicorn -c gunicorn_config.py app:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

# Restart bei Fehler
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Service aktivieren:
```bash
sudo systemctl daemon-reload
sudo systemctl enable stitchadmin
sudo systemctl start stitchadmin
sudo systemctl status stitchadmin
```

### 8. Nginx als Reverse Proxy

Erstelle `/etc/nginx/sites-available/stitchadmin`:

```nginx
server {
    listen 80;
    server_name ihre-domain.de www.ihre-domain.de;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Client Body Size (für Uploads)
    client_max_body_size 32M;

    # Static Files
    location /static {
        alias /home/stitchadmin/StitchAdmin2.0/src/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Uploads (nur für authentifizierte Benutzer)
    location /uploads {
        alias /home/stitchadmin/StitchAdmin2.0/instance/uploads;
        internal;  # Nur über X-Accel-Redirect
    }

    # Application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health Check
    location /health {
        access_log off;
        return 200 "OK\n";
        add_header Content-Type text/plain;
    }
}
```

Aktivieren:
```bash
sudo ln -s /etc/nginx/sites-available/stitchadmin /etc/nginx/sites-enabled/
sudo nginx -t  # Test
sudo systemctl restart nginx
```

### 9. HTTPS mit Let's Encrypt

```bash
# Certbot installieren
sudo apt install -y certbot python3-certbot-nginx

# Zertifikat erstellen
sudo certbot --nginx -d ihre-domain.de -d www.ihre-domain.de

# Auto-Renewal testen
sudo certbot renew --dry-run
```

### 10. Firewall konfigurieren

```bash
# UFW installieren
sudo apt install -y ufw

# Regeln setzen
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'

# Aktivieren
sudo ufw enable
sudo ufw status
```

---

## 🪟 Produktions-Setup (Windows)

### 1. Python installieren

- Download: https://www.python.org/downloads/
- Bei Installation: "Add Python to PATH" aktivieren

### 2. Repository klonen

```powershell
git clone <repository-url> C:\StitchAdmin2.0
cd C:\StitchAdmin2.0
```

### 3. Virtual Environment

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install waitress  # Windows WSGI-Server
```

### 4. Konfiguration

Erstelle `.env` mit Produktions-Werten.

### 5. Windows Service erstellen

Installiere NSSM (Non-Sucking Service Manager):

```powershell
# Download: https://nssm.cc/download
# Extrahieren nach C:\nssm

# Service erstellen
C:\nssm\win64\nssm.exe install StitchAdmin "C:\StitchAdmin2.0\.venv\Scripts\python.exe" "C:\StitchAdmin2.0\run_production.py"

# Service konfigurieren
C:\nssm\win64\nssm.exe set StitchAdmin AppDirectory "C:\StitchAdmin2.0"
C:\nssm\win64\nssm.exe set StitchAdmin Description "StitchAdmin 2.0 Web Application"

# Service starten
C:\nssm\win64\nssm.exe start StitchAdmin
```

Erstelle `run_production.py`:

```python
from waitress import serve
from app import create_app

app = create_app()

if __name__ == '__main__':
    print("Starting StitchAdmin 2.0 on port 8000...")
    serve(app, host='0.0.0.0', port=8000, threads=4)
```

### 6. IIS als Reverse Proxy (optional)

Installiere IIS + ARR (Application Request Routing) Module.

---

## 🐳 Docker-Setup

### 1. Dockerfile erstellen

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System-Dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Application Code
COPY . .

# Create necessary directories
RUN mkdir -p instance/uploads logs

# Environment
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Expose Port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run Application
CMD ["gunicorn", "-c", "gunicorn_config.py", "app:app"]
```

### 2. docker-compose.yml

```yaml
version: '3.8'

services:
  web:
    build: .
    container_name: stitchadmin
    restart: always
    ports:
      - "8000:8000"
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=postgresql://postgres:password@db:5432/stitchadmin
      - FLASK_ENV=production
    volumes:
      - ./instance:/app/instance
      - ./logs:/app/logs
    depends_on:
      - db
    networks:
      - stitchadmin-network

  db:
    image: postgres:15-alpine
    container_name: stitchadmin-db
    restart: always
    environment:
      - POSTGRES_DB=stitchadmin
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - stitchadmin-network

  nginx:
    image: nginx:alpine
    container_name: stitchadmin-nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./src/static:/usr/share/nginx/html/static:ro
    depends_on:
      - web
    networks:
      - stitchadmin-network

volumes:
  postgres-data:

networks:
  stitchadmin-network:
```

### 3. Starten

```bash
# Build
docker-compose build

# Starten
docker-compose up -d

# Logs
docker-compose logs -f

# Stoppen
docker-compose down
```

---

## 🗄️ Datenbank-Migration

### Von SQLite zu PostgreSQL

**1. Daten exportieren:**

```bash
# SQLite Dump
sqlite3 instance/stitchadmin.db .dump > backup.sql
```

**2. PostgreSQL-Datenbank erstellen:**

```bash
sudo -u postgres createdb stitchadmin
```

**3. Daten importieren (manuell mit pgloader):**

```bash
sudo apt install -y pgloader

# pgloader-Skript
pgloader sqlite://instance/stitchadmin.db \
         postgresql://user:pass@localhost/stitchadmin
```

**4. Konfiguration anpassen:**

```env
DATABASE_URL=postgresql://user:pass@localhost/stitchadmin
```

### Flask-Migrate Workflow

```bash
# Initialisieren (einmalig)
flask db init

# Migration erstellen
flask db migrate -m "Beschreibung der Änderung"

# Migration anwenden
flask db upgrade

# Rollback
flask db downgrade

# Aktuellen Stand zeigen
flask db current

# Historie anzeigen
flask db history
```

---

## 🔧 Umgebungsvariablen

Vollständige Liste aller Umgebungsvariablen:

| Variable | Beschreibung | Standard | Pflicht |
|----------|--------------|----------|---------|
| `FLASK_APP` | Entry Point | `app.py` | Ja |
| `FLASK_ENV` | Umgebung | `development` | Nein |
| `FLASK_DEBUG` | Debug-Modus | `True` | Nein |
| `SECRET_KEY` | Session-Verschlüsselung | - | **Ja** |
| `DATABASE_URL` | Datenbank-URI | SQLite | Nein |
| `MAX_UPLOAD_SIZE` | Upload-Limit (Bytes) | `16777216` | Nein |
| `UPLOAD_FOLDER` | Upload-Verzeichnis | `instance/uploads` | Nein |
| `SESSION_LIFETIME_MINUTES` | Session-Dauer | `30` | Nein |

### .env.example

```env
# Flask Konfiguration
FLASK_APP=app.py
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=<generiere-mit-secrets.token_hex(32)>

# Datenbank
DATABASE_URL=sqlite:///instance/stitchadmin.db
# DATABASE_URL=postgresql://user:password@localhost/stitchadmin

# Upload-Konfiguration
MAX_UPLOAD_SIZE=33554432  # 32MB
UPLOAD_FOLDER=instance/uploads

# Session
SESSION_LIFETIME_MINUTES=30

# Optional: E-Mail (für Benachrichtigungen)
# SMTP_SERVER=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USERNAME=your-email@gmail.com
# SMTP_PASSWORD=your-app-password
# SMTP_FROM_EMAIL=noreply@yourdomain.com
```

---

## 💾 Backup-Strategie

### 1. Automatisches Datenbank-Backup

**Linux Cron-Job:**

```bash
# Backup-Skript: /home/stitchadmin/backup.sh
#!/bin/bash
BACKUP_DIR="/home/stitchadmin/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_PATH="/home/stitchadmin/StitchAdmin2.0/instance/stitchadmin.db"

# SQLite Backup
sqlite3 $DB_PATH ".backup '$BACKUP_DIR/db_backup_$TIMESTAMP.db'"

# Komprimieren
gzip "$BACKUP_DIR/db_backup_$TIMESTAMP.db"

# Alte Backups löschen (älter als 30 Tage)
find $BACKUP_DIR -name "db_backup_*.gz" -mtime +30 -delete

echo "Backup completed: db_backup_$TIMESTAMP.db.gz"
```

Crontab (`crontab -e`):
```cron
# Täglich um 2:00 Uhr
0 2 * * * /home/stitchadmin/backup.sh >> /home/stitchadmin/logs/backup.log 2>&1
```

### 2. PostgreSQL Backup

```bash
# Backup
pg_dump stitchadmin -U stitchadmin_user | gzip > backup_$(date +%Y%m%d).sql.gz

# Restore
gunzip < backup_20251113.sql.gz | psql stitchadmin -U stitchadmin_user
```

### 3. Upload-Dateien sichern

```bash
# Uploads synchronisieren
rsync -av --delete /home/stitchadmin/StitchAdmin2.0/instance/uploads/ \
                   /backup/uploads/
```

### 4. Vollständiges System-Backup

```bash
tar -czf stitchadmin_full_$(date +%Y%m%d).tar.gz \
    --exclude='.venv' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    /home/stitchadmin/StitchAdmin2.0/
```

---

## 📊 Monitoring & Logs

### Log-Dateien

```
logs/
├── error.log           # Anwendungsfehler
├── debug.log           # Debug-Informationen
├── activity_log.json   # Benutzer-Aktivitäten
├── gunicorn-access.log # HTTP-Zugriffe
└── gunicorn-error.log  # Gunicorn-Fehler
```

### Log-Rotation

**logrotate:** `/etc/logrotate.d/stitchadmin`

```
/home/stitchadmin/StitchAdmin2.0/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 stitchadmin stitchadmin
    sharedscripts
    postrotate
        systemctl reload stitchadmin > /dev/null 2>&1 || true
    endscript
}
```

### Health-Check Endpoint

```python
@app.route('/health')
def health():
    """Health Check für Monitoring"""
    try:
        # Datenbank-Check
        db.session.execute('SELECT 1')
        return jsonify({'status': 'healthy', 'database': 'ok'}), 200
    except:
        return jsonify({'status': 'unhealthy', 'database': 'error'}), 503
```

### Monitoring Tools (optional)

- **Uptime Kuma:** Self-hosted Monitoring
- **Prometheus + Grafana:** Metrics & Dashboards
- **Sentry:** Error Tracking

---

## 🔒 Sicherheit

### Sicherheits-Checkliste

- [ ] **Starkes SECRET_KEY** generiert (min. 32 Zeichen)
- [ ] **HTTPS aktiviert** (Let's Encrypt)
- [ ] **Admin-Passwort geändert**
- [ ] **FLASK_DEBUG=False** in Produktion
- [ ] **Firewall konfiguriert** (nur 80, 443, SSH)
- [ ] **SSH Key-Auth** aktiviert (Passwort deaktiviert)
- [ ] **Fail2Ban** installiert (Brute-Force-Schutz)
- [ ] **Regelmäßige Updates** (apt update && apt upgrade)
- [ ] **Backup-Strategie** implementiert
- [ ] **Log-Monitoring** aktiv

### Security Headers (Nginx)

Bereits in Nginx-Config enthalten:
```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

### Rate Limiting (Nginx)

```nginx
# In http-Block
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

# In location /login
location /login {
    limit_req zone=login burst=2 nodelay;
    proxy_pass http://127.0.0.1:8000;
}
```

### Fail2Ban

```bash
# Installieren
sudo apt install -y fail2ban

# Konfiguration: /etc/fail2ban/jail.local
[stitchadmin]
enabled = true
port = http,https
filter = stitchadmin
logpath = /home/stitchadmin/StitchAdmin2.0/logs/gunicorn-access.log
maxretry = 5
bantime = 3600
```

---

## ⚡ Performance-Tuning

### Gunicorn Workers

**Formel:** `(2 x CPU_CORES) + 1`

```python
# gunicorn_config.py
workers = 5  # Für 2 CPU-Kerne
worker_class = "gevent"  # Async Workers (benötigt: pip install gevent)
worker_connections = 1000
```

### PostgreSQL Tuning

```bash
# /etc/postgresql/15/main/postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
max_connections = 100
```

### Nginx Caching

```nginx
# Cache für Static Files
location ~* \.(jpg|jpeg|png|gif|ico|css|js|woff2)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### Redis Session Storage (optional)

```bash
pip install flask-session redis

# .env
REDIS_URL=redis://localhost:6379/0
```

```python
# app.py
from flask_session import Session
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.from_url(os.getenv('REDIS_URL'))
Session(app)
```

---

## 🔧 Troubleshooting

### Problem: Service startet nicht

```bash
# Logs prüfen
sudo journalctl -u stitchadmin -n 50 --no-pager

# Status prüfen
sudo systemctl status stitchadmin

# Manuell starten (für Debugging)
cd /home/stitchadmin/StitchAdmin2.0
source .venv/bin/activate
gunicorn -c gunicorn_config.py app:app
```

### Problem: 502 Bad Gateway

```bash
# Gunicorn läuft?
sudo systemctl status stitchadmin

# Nginx-Logs
sudo tail -f /var/log/nginx/error.log

# Proxy-Einstellungen prüfen
sudo nginx -t
```

### Problem: Datenbank-Fehler

```bash
# SQLite: Berechtigungen prüfen
ls -la instance/stitchadmin.db
sudo chown stitchadmin:stitchadmin instance/stitchadmin.db

# PostgreSQL: Verbindung testen
psql -U stitchadmin_user -d stitchadmin -h localhost
```

### Problem: Upload-Fehler

```bash
# Berechtigungen prüfen
ls -la instance/uploads/
sudo chown -R stitchadmin:stitchadmin instance/uploads/
sudo chmod 755 instance/uploads/

# Upload-Limit erhöhen
# Nginx: client_max_body_size
# Flask: MAX_UPLOAD_SIZE in .env
```

### Problem: Python 3.13 SQLAlchemy-Fehler

```bash
# SQLAlchemy aktualisieren
pip install --upgrade "SQLAlchemy>=2.0.36"
```

### Logs analysieren

```bash
# Error-Log
tail -f logs/error.log

# Gunicorn-Logs
tail -f logs/gunicorn-error.log

# Systemd-Logs
journalctl -u stitchadmin -f
```

---

## 📞 Support & Updates

### Updates einspielen

```bash
cd /home/stitchadmin/StitchAdmin2.0

# Backup erstellen
./backup.sh

# Git Pull
git pull origin main

# Dependencies aktualisieren
source .venv/bin/activate
pip install -r requirements.txt

# Migrations ausführen
flask db upgrade

# Service neu starten
sudo systemctl restart stitchadmin
```

### Rollback

```bash
# Git Rollback
git log  # Commit-ID finden
git checkout <commit-id>

# Datenbank Rollback
flask db downgrade

# Service neu starten
sudo systemctl restart stitchadmin
```

---

## 📝 Changelog

### Version 2.0.0 (13.11.2025)
- Initiales Deployment-Guide
- Linux/Windows/Docker Support
- Backup-Strategie dokumentiert
- Security Best Practices

---

**Erstellt von Hans Hahn - Alle Rechte vorbehalten**
