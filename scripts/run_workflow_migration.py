# -*- coding: utf-8 -*-
"""
Automatische Ausführung der Workflow-Migration
"""

import sys
import os

# Füge Projekt-Root zum Path hinzu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import migrate-Funktion
from add_workflow_tables import migrate

if __name__ == '__main__':
    print()
    print("Starte automatische Migration...")
    print()

    if migrate():
        print("\n[SUCCESS] Migration erfolgreich!")
        sys.exit(0)
    else:
        print("\n[ERROR] Migration fehlgeschlagen!")
        sys.exit(1)
