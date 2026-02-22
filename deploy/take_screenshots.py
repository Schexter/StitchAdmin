#!/usr/bin/env python3
"""
Screenshot-Generator fuer StitchAdmin Landing Page
Nutzt Chromium Headless + Selenium um App-Screenshots zu machen
"""
import subprocess
import time
import os
import sys
import json
import http.cookiejar
import urllib.request
import urllib.parse

BASE_URL = "https://stitchadmin.hahn-it-wuppertal.de"
OUTPUT_DIR = "/opt/stitchadmin/app/src/static/img/screenshots"
CHROMIUM = "/usr/bin/chromium-browser"

# Screenshots: (name, url_path, width, height, wait_seconds)
SCREENSHOTS = [
    ("dashboard", "/dashboard", 1400, 900, 2),
    ("orders", "/orders", 1400, 900, 2),
    ("machines", "/machines/capacity", 1400, 900, 2),
    ("invoices", "/rechnungen", 1400, 900, 2),
    ("crm", "/crm/dashboard", 1400, 900, 2),
]


def take_screenshot_chromium(url, output_path, width=1400, height=900):
    """Screenshot mit Chromium Headless"""
    cmd = [
        CHROMIUM,
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-software-rasterizer",
        "--disable-dev-shm-usage",
        f"--window-size={width},{height}",
        f"--screenshot={output_path}",
        "--hide-scrollbars",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return os.path.exists(output_path)


def login_and_get_cookies():
    """Login via requests und Session-Cookie zurueckgeben"""
    import http.client
    import ssl

    # Zuerst Login-Seite holen fuer CSRF-Token
    ctx = ssl.create_default_context()

    # Login POST
    conn = http.client.HTTPSConnection("stitchadmin.hahn-it-wuppertal.de")

    # GET login page first
    conn.request("GET", "/login")
    resp = conn.getresponse()
    login_html = resp.read().decode()
    cookies_raw = resp.getheader('Set-Cookie', '')
    session_cookie = ''
    for part in cookies_raw.split(','):
        if 'session=' in part:
            session_cookie = part.split(';')[0].strip()
            break

    # Extract CSRF token from HTML
    csrf_token = ''
    if 'csrf_token' in login_html:
        import re
        match = re.search(r'name="csrf_token"[^>]*value="([^"]*)"', login_html)
        if match:
            csrf_token = match.group(1)
    if not csrf_token:
        # Try meta tag
        import re
        match = re.search(r'name="csrf-token"\s+content="([^"]*)"', login_html)
        if match:
            csrf_token = match.group(1)

    # POST login
    body = urllib.parse.urlencode({
        'username': 'admin',
        'password': os.environ.get('ADMIN_PASSWORD', 'admin'),
        'csrf_token': csrf_token,
    })
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': session_cookie,
    }
    conn.request("POST", "/login", body, headers)
    resp = conn.getresponse()
    resp.read()

    # Get session cookie from response
    new_cookies = resp.getheader('Set-Cookie', '')
    for part in new_cookies.split(','):
        if 'session=' in part:
            session_cookie = part.split(';')[0].strip()
            break

    conn.close()
    return session_cookie


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Da Chromium keine Login-Session direkt nutzen kann,
    # erstellen wir die Screenshots ueber einen temporaeren
    # Cookie-basierten Ansatz mit CDP (Chrome DevTools Protocol)

    print("[INFO] Starte Screenshot-Erstellung...")

    # Fuer jeden Screenshot nutzen wir chromium headless
    # Da wir Login brauchen, nutzen wir einen kleinen Trick:
    # Wir starten Chromium mit einer Cookie-Datei

    # Alternative: Screenshots ueber localhost (Flask dev server)
    # oder wir nutzen ein simples Selenium-Script

    # Einfachster Ansatz: Screenshots ohne Login von oeffentlichen Seiten
    # + Screenshots mit Login ueber einen temporaeren lokalen Flask-Server

    # Pragmatischer Ansatz: Nutze Playwright/Puppeteer
    try:
        # Versuche mit playwright
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=CHROMIUM,
                headless=True,
                args=['--no-sandbox']
            )
            page = browser.new_page(viewport={'width': 1400, 'height': 900})

            # Login
            page.goto(f"{BASE_URL}/login")
            page.fill('input[name="username"]', 'admin')
            pw = os.environ.get('ADMIN_PASSWORD', 'admin')
            page.fill('input[name="password"]', pw)
            page.click('button[type="submit"]')
            page.wait_for_load_state('networkidle')
            time.sleep(1)

            # Screenshots
            for name, path, w, h, wait in SCREENSHOTS:
                try:
                    page.set_viewport_size({'width': w, 'height': h})
                    page.goto(f"{BASE_URL}{path}")
                    page.wait_for_load_state('networkidle')
                    time.sleep(wait)
                    outpath = os.path.join(OUTPUT_DIR, f"{name}.png")
                    page.screenshot(path=outpath, full_page=False)
                    print(f"[OK] {name}.png ({w}x{h})")
                except Exception as e:
                    print(f"[FEHLER] {name}: {e}")

            browser.close()
            print("[FERTIG] Alle Screenshots erstellt!")
            return

    except ImportError:
        print("[INFO] Playwright nicht installiert, nutze Fallback...")

    # Fallback: Chromium direkt mit temporaerer HTML-Datei
    # Erstelle eine Login-Redirect-Seite
    for name, path, w, h, wait in SCREENSHOTS:
        outpath = os.path.join(OUTPUT_DIR, f"{name}.png")
        url = f"{BASE_URL}{path}"
        print(f"[...] {name} -> {url}")
        success = take_screenshot_chromium(url, outpath, w, h)
        if success:
            size = os.path.getsize(outpath)
            print(f"[OK] {name}.png ({size} bytes)")
        else:
            print(f"[FEHLER] {name} konnte nicht erstellt werden")

    print("[FERTIG] Screenshots erstellt (ohne Login - zeigen Login-Seite)")
    print("[HINWEIS] Fuer richtige Screenshots: pip install playwright && playwright install chromium")


if __name__ == '__main__':
    main()
