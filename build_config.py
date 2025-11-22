"""
StitchAdmin 2.0 - Build Configuration
Konfiguration für PyInstaller und EXE-Erstellung

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
import sys

# Version Information
APP_VERSION = "0.9.0-beta"
APP_NAME = "StitchAdmin 2.0"
APP_AUTHOR = "Hans Hahn"
APP_COPYRIGHT = "© 2025 Hans Hahn - Alle Rechte vorbehalten"

# Build Einstellungen
BUILD_DIR = "build"
DIST_DIR = "dist"
INSTALLER_DIR = "installer"

# Pfade
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(BASE_DIR, "src", "static", "img", "logo.ico")

# PyInstaller Einstellungen
PYINSTALLER_CONFIG = {
    "name": "StitchAdmin",
    "icon": ICON_PATH if os.path.exists(ICON_PATH) else None,
    "onefile": True,  # Einzelne EXE
    "windowed": True,  # Keine Console
    "console": False,  # Kein CMD-Fenster
}

# Zu inkludierende Daten
DATA_FILES = [
    ('src/templates', 'templates'),
    ('src/static', 'static'),
    ('config', 'config'),
]

# Hidden Imports (für PyInstaller)
HIDDEN_IMPORTS = [
    # SQLAlchemy
    'sqlalchemy',
    'sqlalchemy.sql.default_comparator',
    'sqlalchemy.ext.declarative',
    
    # Flask Extensions
    'flask_login',
    'flask_sqlalchemy',
    'werkzeug.security',
    
    # Embroidery
    'pyembroidery',
    
    # Standard Library
    'email.mime.multipart',
    'email.mime.text',
    'email.mime.base',
    
    # Controllers (alle Blueprints)
    'src.controllers.auth',
    'src.controllers.customers',
    'src.controllers.articles',
    'src.controllers.orders',
    'src.controllers.designs',
    'src.controllers.threads',
    'src.controllers.pos',
    'src.controllers.production',
    'src.controllers.dashboard',
]

# Zu excludierende Module (reduziert EXE-Größe)
EXCLUDES = [
    'tkinter',
    'matplotlib',
    'numpy',
    'pandas',
    'scipy',
    'pytest',
    'IPython',
]

def get_version():
    """Gibt die aktuelle Version zurück"""
    return APP_VERSION

def get_build_info():
    """Gibt Build-Informationen zurück"""
    return {
        'version': APP_VERSION,
        'name': APP_NAME,
        'author': APP_AUTHOR,
        'copyright': APP_COPYRIGHT,
    }

if __name__ == '__main__':
    print(f"Build Configuration für {APP_NAME} v{APP_VERSION}")
    print(f"Base Directory: {BASE_DIR}")
    print(f"Icon: {ICON_PATH}")
    print(f"Hidden Imports: {len(HIDDEN_IMPORTS)}")
    print(f"Data Files: {len(DATA_FILES)}")
