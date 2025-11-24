# -*- coding: utf-8 -*-
"""Test Blueprint-Registrierung"""
import sys
import os

# Füge Projekt-Root zum Path hinzu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

app = create_app()

print("=" * 70)
print("  REGISTRIERTE BLUEPRINTS")
print("=" * 70)
print()

for bp_name in sorted(app.blueprints.keys()):
    bp = app.blueprints[bp_name]
    print(f"Blueprint: {bp_name}")
    print(f"  URL Prefix: {bp.url_prefix}")
    print(f"  Import Name: {bp.import_name}")

    # Zeige Routes
    routes = [rule for rule in app.url_map.iter_rules() if rule.endpoint.startswith(bp_name + '.')]
    if routes:
        print(f"  Routes ({len(routes)}):")
        for route in sorted(routes, key=lambda x: x.rule)[:5]:  # Nur erste 5
            print(f"    - {route.rule} -> {route.endpoint}")
        if len(routes) > 5:
            print(f"    ... und {len(routes) - 5} weitere")
    print()

print("=" * 70)
print(f"Insgesamt {len(app.blueprints)} Blueprints registriert")
print("=" * 70)
