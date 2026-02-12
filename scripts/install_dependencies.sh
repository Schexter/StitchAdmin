#!/bin/bash
# -*- coding: utf-8 -*-
#
# StitchAdmin 2.0 - Dependency Installation Script
# =================================================
# Installiert alle System- und Python-Dependencies
#
# Erstellt von: Hans Hahn - Alle Rechte vorbehalten
#

set -e  # Exit on error

echo "======================================================"
echo "StitchAdmin 2.0 - Dependency Installation"
echo "======================================================"
echo ""

# Farben für Output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Prüfe ob als root/sudo ausgeführt
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}[WARNUNG]${NC} Dieses Skript benötigt sudo-Rechte für System-Packages."
    echo "Führe aus: sudo bash scripts/install_dependencies.sh"
    exit 1
fi

# Erkenne Betriebssystem
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
else
    OS=$(uname -s)
fi

echo -e "${GREEN}[INFO]${NC} Erkanntes System: $OS $VERSION"
echo ""

# ==========================================
# 1. SYSTEM-PACKAGES INSTALLIEREN
# ==========================================
echo "======================================================"
echo "1. System-Packages installieren"
echo "======================================================"

if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
    echo -e "${GREEN}[INFO]${NC} Ubuntu/Debian erkannt - verwende apt-get"

    echo "[1/4] Package-Liste aktualisieren..."
    apt-get update -qq

    echo "[2/4] Python 3 und pip installieren..."
    apt-get install -y python3 python3-pip python3-venv

    echo "[3/4] Tesseract OCR installieren..."
    apt-get install -y tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng

    echo "[4/4] Zusätzliche Dependencies installieren..."
    apt-get install -y libpq-dev python3-dev build-essential

    echo -e "${GREEN}[OK]${NC} System-Packages installiert"

elif [[ "$OS" == "fedora" ]] || [[ "$OS" == "rhel" ]] || [[ "$OS" == "centos" ]]; then
    echo -e "${GREEN}[INFO]${NC} Fedora/RHEL/CentOS erkannt - verwende dnf/yum"

    if command -v dnf &> /dev/null; then
        PKG_MANAGER="dnf"
    else
        PKG_MANAGER="yum"
    fi

    echo "[1/3] Python 3 und pip installieren..."
    $PKG_MANAGER install -y python3 python3-pip python3-devel

    echo "[2/3] Tesseract OCR installieren..."
    $PKG_MANAGER install -y tesseract tesseract-langpack-deu tesseract-langpack-eng

    echo "[3/3] Zusätzliche Dependencies installieren..."
    $PKG_MANAGER install -y postgresql-devel gcc

    echo -e "${GREEN}[OK]${NC} System-Packages installiert"

elif [[ "$OS" == "arch" ]] || [[ "$OS" == "manjaro" ]]; then
    echo -e "${GREEN}[INFO]${NC} Arch/Manjaro erkannt - verwende pacman"

    echo "[1/2] Python 3 und pip installieren..."
    pacman -Syu --noconfirm python python-pip

    echo "[2/2] Tesseract OCR installieren..."
    pacman -S --noconfirm tesseract tesseract-data-deu tesseract-data-eng

    echo -e "${GREEN}[OK]${NC} System-Packages installiert"

else
    echo -e "${YELLOW}[WARNUNG]${NC} Unbekanntes Betriebssystem: $OS"
    echo "Bitte installiere manuell:"
    echo "  - Python 3.11+"
    echo "  - pip"
    echo "  - tesseract-ocr mit deutschen Sprachpaketen"
    echo ""
    read -p "Trotzdem fortfahren? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""

# ==========================================
# 2. TESSERACT VERSION PRÜFEN
# ==========================================
echo "======================================================"
echo "2. Tesseract OCR Prüfung"
echo "======================================================"

if command -v tesseract &> /dev/null; then
    TESSERACT_VERSION=$(tesseract --version | head -n 1)
    echo -e "${GREEN}[OK]${NC} $TESSERACT_VERSION"

    # Prüfe verfügbare Sprachen
    echo ""
    echo "Verfügbare Sprachen:"
    tesseract --list-langs | tail -n +2
else
    echo -e "${RED}[ERROR]${NC} Tesseract nicht gefunden!"
    exit 1
fi

echo ""

# ==========================================
# 3. PYTHON-PACKAGES INSTALLIEREN
# ==========================================
echo "======================================================"
echo "3. Python-Packages installieren"
echo "======================================================"

# Wechsel zum Projekt-Verzeichnis
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo -e "${GREEN}[INFO]${NC} Projekt-Verzeichnis: $PROJECT_DIR"

# Prüfe ob requirements.txt existiert
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}[ERROR]${NC} requirements.txt nicht gefunden!"
    exit 1
fi

# Installiere mit pip (als ursprünglicher User, nicht root)
if [ -n "$SUDO_USER" ]; then
    echo -e "${GREEN}[INFO]${NC} Installiere als User: $SUDO_USER"
    su - $SUDO_USER -c "cd $PROJECT_DIR && python3 -m pip install --user -r requirements.txt"
else
    echo -e "${GREEN}[INFO]${NC} Installiere Python-Packages..."
    python3 -m pip install -r requirements.txt
fi

echo -e "${GREEN}[OK]${NC} Python-Packages installiert"

echo ""

# ==========================================
# 4. INSTALLATION VERIFIZIEREN
# ==========================================
echo "======================================================"
echo "4. Installation verifizieren"
echo "======================================================"

# Python-Version
PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}[CHECK]${NC} Python: $PYTHON_VERSION"

# Kritische Packages prüfen
PACKAGES=("flask" "pytesseract" "Pillow" "reportlab" "sqlalchemy")

for package in "${PACKAGES[@]}"; do
    if python3 -c "import ${package,,}" 2>/dev/null; then
        VERSION=$(python3 -c "import ${package,,}; print(${package,,}.__version__)" 2>/dev/null || echo "OK")
        echo -e "${GREEN}[CHECK]${NC} $package: $VERSION"
    else
        echo -e "${RED}[ERROR]${NC} $package: Nicht installiert!"
    fi
done

echo ""

# ==========================================
# 5. DATENBANK MIGRATIONEN
# ==========================================
echo "======================================================"
echo "5. Datenbank-Migrationen (optional)"
echo "======================================================"

echo "Möchten Sie die Datenbank-Migrationen jetzt ausführen?"
echo "  - add_order_photos_field.py (Fotos für Aufträge)"
echo "  - add_post_entry_photos_fields.py (Fotos & OCR für PostEntry)"
echo ""
read -p "Migrationen ausführen? [y/N] " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -f "scripts/add_order_photos_field.py" ]; then
        echo "Führe Order-Migration aus..."
        python3 scripts/add_order_photos_field.py || echo -e "${YELLOW}[WARNUNG]${NC} Migration fehlgeschlagen oder bereits ausgeführt"
    fi

    if [ -f "scripts/add_post_entry_photos_fields.py" ]; then
        echo "Führe PostEntry-Migration aus..."
        python3 scripts/add_post_entry_photos_fields.py || echo -e "${YELLOW}[WARNUNG]${NC} Migration fehlgeschlagen oder bereits ausgeführt"
    fi
fi

echo ""

# ==========================================
# FERTIG!
# ==========================================
echo "======================================================"
echo -e "${GREEN}Installation erfolgreich abgeschlossen!${NC}"
echo "======================================================"
echo ""
echo "Nächste Schritte:"
echo "  1. Konfiguration anpassen: cp .env.example .env"
echo "  2. Server starten: python3 app.py"
echo "  3. Im Browser öffnen: http://localhost:5000"
echo ""
echo "Für OCR-Funktionen:"
echo "  - Dokumente scannen: /documents/post/<ID>/scan"
echo "  - Auftrag-Fotos: /orders/<ID>/photos"
echo ""
echo "Dokumentation:"
echo "  - docs/MOBILE_WORKFLOW_FEATURES.md"
echo "  - docs/POSTENTRY_OCR_FEATURES.md"
echo ""
echo "======================================================"
