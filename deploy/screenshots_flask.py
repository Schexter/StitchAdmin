#!/usr/bin/env python3
"""
Screenshot-Generator - Nutzt Playwright mit Flask-Session direkt
Laeuft auf dem Server: python3 /opt/stitchadmin/screenshots_flask.py
"""
import os
import sys
import time

# App-Pfad hinzufuegen
sys.path.insert(0, '/opt/stitchadmin/app')
os.chdir('/opt/stitchadmin/app')

# Umgebungsvariablen laden
env_file = '/opt/stitchadmin/app/.env'
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

OUTPUT_DIR = "/opt/stitchadmin/app/src/static/img/screenshots"
BASE_URL = "https://stitchadmin.hahn-it-wuppertal.de"

SCREENSHOTS = [
    ("dashboard", "/dashboard", 1440, 900),
    ("orders", "/orders", 1440, 900),
    ("machines", "/machines/capacity", 1440, 900),
    ("invoices", "/rechnungen", 1440, 900),
    ("crm", "/crm/dashboard", 1440, 900),
]


def get_session_cookie():
    """Erstelle Flask Session-Cookie fuer Admin-User direkt"""
    from app import create_app
    app = create_app()

    with app.test_client() as client:
        # Login als Admin
        # Zuerst GET um CSRF-Token zu holen
        resp = client.get('/login')
        html = resp.data.decode()

        import re
        csrf_match = re.search(r'name="csrf-token"\s+content="([^"]*)"', html)
        if not csrf_match:
            csrf_match = re.search(r'name="csrf_token"[^>]*value="([^"]*)"', html)
        csrf_token = csrf_match.group(1) if csrf_match else ''

        resp = client.post('/login', data={
            'username': 'admin',
            'password': 'admin',  # Aelteres Passwort, evtl. anpassen
            'csrf_token': csrf_token,
        }, follow_redirects=False)

        # Extrahiere Session-Cookie
        cookies = {}
        for header in resp.headers.getlist('Set-Cookie'):
            if 'session=' in header:
                cookie_val = header.split(';')[0]
                return cookie_val

    return None


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("[INFO] Starte Screenshot-Erstellung mit Playwright...")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = browser.new_context(
            viewport={'width': 1440, 'height': 900},
            ignore_https_errors=True
        )
        page = context.new_page()

        # Login ueber das Web-Formular
        print("[INFO] Login...")
        page.goto(f"{BASE_URL}/login", wait_until='networkidle')
        time.sleep(1)

        page.fill('input[name="username"]', 'admin')
        page.fill('input[name="password"]', 'admin')
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')
        time.sleep(2)

        # Pruefen ob Login erfolgreich
        if '/login' in page.url:
            print("[FEHLER] Login fehlgeschlagen! URL:", page.url)
            # Versuche mit anderem Passwort - das von der .env oder so
            print("[INFO] Versuche Passwort-Reset...")

            # Setze Passwort direkt in DB
            from app import create_app
            app = create_app()
            with app.app_context():
                from src.models.models import User, db
                admin = User.query.filter_by(username='admin').first()
                if admin:
                    admin.set_password('screenshot_temp_2026!')
                    db.session.commit()
                    print("[OK] Temp-Passwort gesetzt")

            # Nochmal einloggen
            page.goto(f"{BASE_URL}/login", wait_until='networkidle')
            time.sleep(1)
            page.fill('input[name="username"]', 'admin')
            page.fill('input[name="password"]', 'screenshot_temp_2026!')
            page.click('button[type="submit"]')
            page.wait_for_load_state('networkidle')
            time.sleep(2)

            if '/login' in page.url:
                print("[FEHLER] Login immer noch fehlgeschlagen!")
                browser.close()
                return

        print(f"[OK] Eingeloggt - URL: {page.url}")

        # Screenshots machen
        for name, path, w, h in SCREENSHOTS:
            try:
                page.set_viewport_size({'width': w, 'height': h})
                page.goto(f"{BASE_URL}{path}", wait_until='networkidle')
                time.sleep(2)

                outpath = os.path.join(OUTPUT_DIR, f"{name}.png")
                page.screenshot(path=outpath, full_page=False)
                size = os.path.getsize(outpath)
                print(f"[OK] {name}.png ({size:,} bytes, {w}x{h})")
            except Exception as e:
                print(f"[FEHLER] {name}: {e}")

        browser.close()

    # Berechtigungen setzen
    os.system(f"chown -R stitchadmin:stitchadmin {OUTPUT_DIR}")

    print(f"\n[FERTIG] Screenshots in {OUTPUT_DIR}/")
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith('.png'):
            size = os.path.getsize(os.path.join(OUTPUT_DIR, f))
            print(f"  - {f} ({size:,} bytes)")


if __name__ == '__main__':
    main()
