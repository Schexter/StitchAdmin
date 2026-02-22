#!/usr/bin/env python3
"""
Screenshot-Generator mit Playwright
"""
import os
import time

OUTPUT_DIR = "/opt/stitchadmin/app/src/static/img/screenshots"
BASE_URL = "https://stitchadmin.hahn-it-wuppertal.de"

SCREENSHOTS = [
    ("dashboard", "/dashboard", 1440, 900),
    ("orders", "/orders", 1440, 900),
    ("machines", "/machines", 1440, 900),
    ("invoices", "/rechnungen", 1440, 900),
    ("crm", "/customers", 1440, 900),
]


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("[INFO] Starte Screenshot-Erstellung...")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = browser.new_context(
            viewport={'width': 1440, 'height': 900},
            ignore_https_errors=True
        )
        page = context.new_page()

        # Login
        print("[INFO] Login...")
        page.goto(f"{BASE_URL}/login", wait_until='networkidle')
        time.sleep(1)
        page.fill('input[name="username"]', 'admin')
        page.fill('input[name="password"]', 'Screenshot2026!')
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')
        time.sleep(2)

        if '/login' in page.url:
            print(f"[FEHLER] Login fehlgeschlagen!")
            browser.close()
            return

        print(f"[OK] Eingeloggt")

        for name, path, w, h in SCREENSHOTS:
            try:
                page.set_viewport_size({'width': w, 'height': h})
                page.goto(f"{BASE_URL}{path}", wait_until='networkidle')
                time.sleep(3)

                # Pruefen ob Seite geladen (kein 500er)
                if 'Internal Server Error' in page.content():
                    print(f"[SKIP] {name} - Server Error, ueberspringe")
                    continue

                outpath = os.path.join(OUTPUT_DIR, f"{name}.png")
                page.screenshot(path=outpath, full_page=False)
                size = os.path.getsize(outpath)
                print(f"[OK] {name}.png ({size:,} bytes)")
            except Exception as e:
                print(f"[FEHLER] {name}: {e}")

        browser.close()

    os.system(f"chown -R stitchadmin:stitchadmin {OUTPUT_DIR}")
    print(f"\n[FERTIG] Screenshots in {OUTPUT_DIR}/")


if __name__ == '__main__':
    main()
