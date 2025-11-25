"""
StitchAdmin 2.0 - Build Configuration
Konfiguration für PyInstaller und EXE-Erstellung

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
import sys

# ============================================================================
# VERSION INFORMATION
# ============================================================================
APP_VERSION = "2.0.0"
APP_VERSION_TUPLE = (2, 0, 0, 0)  # Für Windows Version Info
APP_NAME = "StitchAdmin 2.0"
APP_AUTHOR = "Hans Hahn"
APP_COPYRIGHT = "© 2025 Hans Hahn - Alle Rechte vorbehalten"
APP_DESCRIPTION = "ERP-System für Stickerei & Textilveredelung"
APP_URL = "https://stitchadmin.de"

# ============================================================================
# BUILD EINSTELLUNGEN
# ============================================================================
BUILD_DIR = "build"
DIST_DIR = "dist"
INSTALLER_DIR = "installer_output"

# Pfade
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(BASE_DIR, "src", "static", "img", "logo.ico")

# ============================================================================
# PYINSTALLER EINSTELLUNGEN
# ============================================================================
PYINSTALLER_CONFIG = {
    "name": "StitchAdmin",
    "icon": ICON_PATH if os.path.exists(ICON_PATH) else None,
    "onefile": False,  # Ordner-Struktur (schnellerer Start)
    "windowed": True,  # Keine Console
    "console": False,  # Kein CMD-Fenster
    "uac_admin": False,  # Keine Admin-Rechte für die App selbst
}

# ============================================================================
# ZU INKLUDIERENDE DATEN
# ============================================================================
DATA_FILES = [
    # Templates
    ('src/templates', 'templates'),
    
    # Statische Dateien (CSS, JS, Bilder)
    ('src/static', 'static'),
    
    # Konfigurationsvorlagen
    ('config', 'config'),
    
    # Dokumentation
    ('README.md', '.'),
    ('CHANGELOG.md', '.'),
    ('QUICKSTART.md', '.'),
    ('LICENSE', '.'),
]

# ============================================================================
# HIDDEN IMPORTS (für PyInstaller)
# ============================================================================
HIDDEN_IMPORTS = [
    # === Flask & Extensions ===
    'flask',
    'flask.json',
    'flask_login',
    'flask_sqlalchemy',
    'flask_wtf',
    'wtforms',
    'werkzeug',
    'werkzeug.security',
    'werkzeug.utils',
    'jinja2',
    'jinja2.ext',
    
    # === SQLAlchemy ===
    'sqlalchemy',
    'sqlalchemy.sql.default_comparator',
    'sqlalchemy.ext.declarative',
    'sqlalchemy.orm',
    'sqlalchemy.pool',
    'sqlalchemy.dialects.sqlite',
    
    # === Embroidery ===
    'pyembroidery',
    'pyembroidery.DstReader',
    'pyembroidery.PesReader',
    'pyembroidery.EmbPattern',
    
    # === Image Processing ===
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    
    # === PDF & Documents ===
    'reportlab',
    'reportlab.lib',
    'reportlab.lib.pagesizes',
    'reportlab.pdfgen',
    'reportlab.platypus',
    'openpyxl',
    
    # === Data Processing ===
    'pandas',
    'numpy',
    
    # === Email ===
    'email',
    'email.mime',
    'email.mime.multipart',
    'email.mime.text',
    'email.mime.base',
    'email.mime.application',
    'smtplib',
    'imaplib',
    
    # === Cryptography ===
    'cryptography',
    'cryptography.fernet',
    
    # === Standard Library ===
    'json',
    'uuid',
    'hashlib',
    'secrets',
    'datetime',
    'decimal',
    'logging',
    'logging.handlers',
    
    # === StitchAdmin Models ===
    'src.models',
    'src.models.models',
    'src.models.settings',
    'src.models.nummernkreis',
    'src.models.company_settings',
    'src.models.packing_list',
    'src.models.delivery_note',
    'src.models.document',
    'src.models.rechnungsmodul',
    'src.models.crm_activities',
    
    # === StitchAdmin Controllers ===
    'src.controllers',
    'src.controllers.auth_controller',
    'src.controllers.dashboard_controller',
    'src.controllers.customer_controller_db',
    'src.controllers.article_controller_db',
    'src.controllers.order_controller_db',
    'src.controllers.production_controller_db',
    'src.controllers.shipping_controller_db',
    'src.controllers.packing_list_controller',
    'src.controllers.email_controller',
    'src.controllers.settings_controller',
    
    # === StitchAdmin Services ===
    'src.services',
    'src.services.email_service',
    
    # === StitchAdmin Utils ===
    'src.utils',
    'src.utils.dst_analyzer',
    
    # === StitchAdmin Updates ===
    'src.updates',
    'src.updates.backup_manager',
    'src.updates.update_manager',
    
    # === StitchAdmin Update Controller ===
    'src.controllers.update_controller',
]

# ============================================================================
# ZU EXCLUDIERENDE MODULE (reduziert EXE-Größe)
# ============================================================================
EXCLUDES = [
    # Testing
    'pytest',
    'unittest',
    'test',
    'tests',
    
    # Development
    'IPython',
    'ipython',
    'jupyter',
    'notebook',
    
    # GUI Frameworks (wir nutzen Web-Interface)
    'tkinter',
    'tk',
    'tcl',
    'PyQt5',
    'PyQt6',
    'wx',
    
    # Wissenschaftliche Pakete (falls nicht benötigt)
    'scipy',
    'matplotlib',
    'matplotlib.pyplot',
    
    # Datenbank-Treiber die nicht benötigt werden
    'psycopg2',
    'pymysql',
    'cx_Oracle',
]

# ============================================================================
# RUNTIME HOOKS
# ============================================================================
RUNTIME_HOOKS = []

# ============================================================================
# BINARIES
# ============================================================================
BINARIES = []

# ============================================================================
# HILFSFUNKTIONEN
# ============================================================================

def get_version():
    """Gibt die aktuelle Version zurück"""
    return APP_VERSION

def get_version_tuple():
    """Gibt die Version als Tuple zurück (für Windows)"""
    return APP_VERSION_TUPLE

def get_build_info():
    """Gibt Build-Informationen zurück"""
    return {
        'version': APP_VERSION,
        'name': APP_NAME,
        'author': APP_AUTHOR,
        'copyright': APP_COPYRIGHT,
        'description': APP_DESCRIPTION,
        'url': APP_URL,
    }

def create_version_file():
    """Erstellt eine Windows Version-Info Datei für PyInstaller"""
    version_info = f'''
# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={APP_VERSION_TUPLE},
    prodvers={APP_VERSION_TUPLE},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [
            StringStruct(u'CompanyName', u'{APP_AUTHOR}'),
            StringStruct(u'FileDescription', u'{APP_DESCRIPTION}'),
            StringStruct(u'FileVersion', u'{APP_VERSION}'),
            StringStruct(u'InternalName', u'StitchAdmin'),
            StringStruct(u'LegalCopyright', u'{APP_COPYRIGHT}'),
            StringStruct(u'OriginalFilename', u'StitchAdmin.exe'),
            StringStruct(u'ProductName', u'{APP_NAME}'),
            StringStruct(u'ProductVersion', u'{APP_VERSION}'),
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''
    
    version_file = os.path.join(BASE_DIR, 'version_info.txt')
    with open(version_file, 'w', encoding='utf-8') as f:
        f.write(version_info)
    
    return version_file

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print(f"Build Configuration für {APP_NAME} v{APP_VERSION}")
    print(f"=" * 60)
    print(f"Base Directory:  {BASE_DIR}")
    print(f"Icon:            {ICON_PATH}")
    print(f"Hidden Imports:  {len(HIDDEN_IMPORTS)}")
    print(f"Excludes:        {len(EXCLUDES)}")
    print(f"Data Files:      {len(DATA_FILES)}")
    print(f"=" * 60)
    
    # Test ob Icon existiert
    if os.path.exists(ICON_PATH):
        print(f"✓ Icon gefunden: {ICON_PATH}")
    else:
        print(f"✗ Icon NICHT gefunden: {ICON_PATH}")
        print("  Bitte erstellen Sie eine logo.ico Datei in src/static/img/")
