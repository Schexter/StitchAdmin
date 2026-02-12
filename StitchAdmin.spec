# -*- mode: python ; coding: utf-8 -*-
"""
StitchAdmin 2.0 - PyInstaller Spec File
Erstellt eine ausführbare Windows-Anwendung

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import sys
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

# Import Build Config
sys.path.insert(0, os.path.dirname(os.path.abspath('.')))
try:
    from build_config import *
except ImportError:
    # Fallback-Werte wenn build_config nicht importiert werden kann
    APP_NAME = "StitchAdmin"
    APP_VERSION = "2.0.0"
    HIDDEN_IMPORTS = []
    EXCLUDES = []
    DATA_FILES = []

block_cipher = None

# ============================================================================
# SAMMLE ABHÄNGIGKEITEN
# ============================================================================

# pyembroidery (für DST-Analyse)
pyembroidery_datas, pyembroidery_binaries, pyembroidery_hiddenimports = collect_all('pyembroidery')

# SQLAlchemy
sqlalchemy_hiddenimports = collect_submodules('sqlalchemy')

# Flask und Extensions
flask_hiddenimports = collect_submodules('flask')
flask_login_hiddenimports = collect_submodules('flask_login')
flask_sqlalchemy_hiddenimports = collect_submodules('flask_sqlalchemy')

# Jinja2
jinja2_hiddenimports = collect_submodules('jinja2')

# WTForms
wtforms_hiddenimports = collect_submodules('wtforms')

# Werkzeug
werkzeug_hiddenimports = collect_submodules('werkzeug')

# ReportLab (PDF)
reportlab_datas, reportlab_binaries, reportlab_hiddenimports = collect_all('reportlab')

# OpenPyXL (Excel)
openpyxl_hiddenimports = collect_submodules('openpyxl')

# PIL/Pillow
pillow_hiddenimports = collect_submodules('PIL')

# pikepdf (PDF/A-3 für ZUGFeRD)
try:
    pikepdf_datas, pikepdf_binaries, pikepdf_hiddenimports = collect_all('pikepdf')
except Exception:
    pikepdf_datas, pikepdf_binaries, pikepdf_hiddenimports = [], [], []

# lxml (XML-Validierung)
try:
    lxml_datas, lxml_binaries, lxml_hiddenimports = collect_all('lxml')
except Exception:
    lxml_datas, lxml_binaries, lxml_hiddenimports = [], [], []

# qrcode (QR-Codes für Rechnungen)
try:
    qrcode_hiddenimports = collect_submodules('qrcode')
except Exception:
    qrcode_hiddenimports = []

# cryptography (Verschlüsselung)
try:
    cryptography_datas, cryptography_binaries, cryptography_hiddenimports = collect_all('cryptography')
except Exception:
    cryptography_datas, cryptography_binaries, cryptography_hiddenimports = [], [], []

# ============================================================================
# KOMBINIERE ALLE HIDDEN IMPORTS
# ============================================================================
all_hidden_imports = list(set(
    HIDDEN_IMPORTS +
    pyembroidery_hiddenimports +
    sqlalchemy_hiddenimports +
    flask_hiddenimports +
    flask_login_hiddenimports +
    flask_sqlalchemy_hiddenimports +
    jinja2_hiddenimports +
    wtforms_hiddenimports +
    werkzeug_hiddenimports +
    reportlab_hiddenimports +
    openpyxl_hiddenimports +
    pillow_hiddenimports +
    pikepdf_hiddenimports +
    lxml_hiddenimports +
    qrcode_hiddenimports +
    cryptography_hiddenimports +
    [
        # Zusätzliche Imports die oft fehlen
        'email.mime.multipart',
        'email.mime.text',
        'email.mime.base',
        'email.mime.application',
        'pkg_resources.py2_warn',
        'pkg_resources._vendor',
        # ZUGFeRD/pikepdf spezifisch
        'pikepdf',
        'pikepdf._qpdf',
        'lxml',
        'lxml.etree',
        'lxml._elementpath',
    ]
))

# ============================================================================
# DATEN-DATEIEN
# ============================================================================
datas = [
    # StitchAdmin Dateien
    ('src/templates', 'templates'),
    ('src/static', 'static'),
    ('config', 'config'),
    
    # Dokumentation
    ('README.md', '.'),
    ('LICENSE', '.'),
]

# Füge externe Daten hinzu
datas += pyembroidery_datas
datas += reportlab_datas
datas += pikepdf_datas
datas += lxml_datas
datas += cryptography_datas

# ============================================================================
# BINARIES
# ============================================================================
binaries = (
    pyembroidery_binaries +
    reportlab_binaries +
    pikepdf_binaries +
    lxml_binaries +
    cryptography_binaries
)

# ============================================================================
# ANALYSIS
# ============================================================================
a = Analysis(
    ['app.py'],
    pathex=[os.path.dirname(os.path.abspath('app.py'))],
    binaries=binaries,
    datas=datas,
    hiddenimports=all_hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ============================================================================
# PYZ (Python Bytecode Archiv)
# ============================================================================
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

# ============================================================================
# EXE (Als Ordner-Struktur - schnellerer Start)
# ============================================================================
exe = EXE(
    pyz,
    a.scripts,
    [],  # Nicht in eine Datei packen
    exclude_binaries=True,
    name='StitchAdmin',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Keine Konsole
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src/static/img/logo.ico' if os.path.exists('src/static/img/logo.ico') else None,
    version='version_info.txt' if os.path.exists('version_info.txt') else None,
)

# ============================================================================
# COLLECT (Sammelt alle Dateien)
# ============================================================================
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='StitchAdmin',
)
