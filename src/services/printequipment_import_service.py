# -*- coding: utf-8 -*-
"""
Printequipment Sublimation Import Service
Importiert Sublimationsprodukte von shop.printequipment.de
"""

import re
import json
import logging
import requests
import time
from datetime import datetime

logger = logging.getLogger(__name__)

BASE_URL = 'https://shop.printequipment.de'

# Sublimations-Kategorien mit URLs
SUBLIMATION_CATEGORIES = [
    ('/en/sublimation-products/mug/ceramics/', 'Tassen - Keramik'),
    ('/en/sublimation-products/mug/glass/', 'Tassen - Glas'),
    ('/en/sublimation-products/mug/porcelain/', 'Tassen - Porzellan'),
    ('/en/sublimation-products/mug/plastic/', 'Tassen - Kunststoff'),
    ('/en/sublimation-products/mug/enamel/', 'Tassen - Emaille'),
    ('/en/sublimation-products/mug/stainless-steel/', 'Tassen - Edelstahl'),
    ('/en/sublimation-products/to-go/', 'To-Go Becher'),
    ('/en/sublimation-products/glasses-jugs/', 'Glaeser & Kruege'),
    ('/en/sublimation-products/clothing/', 'Sublimation Bekleidung'),
    ('/en/sublimation-products/pillows-blankets/', 'Kissen & Decken'),
    ('/en/sublimation-products/textile/', 'Textilien'),
    ('/en/sublimation-products/photo-gifts/', 'Fotogeschenke'),
    ('/en/sublimation-products/home-living/', 'Home & Living'),
    ('/en/sublimation-products/aluminium-displays-photos/', 'Aluminium Displays'),
    ('/en/sublimation-products/puzzles-games/', 'Puzzles & Spiele'),
    ('/en/sublimation-products/keyrings/', 'Schluesselanhaenger'),
    ('/en/sublimation-products/floor-mats/', 'Fussmatten'),
    ('/en/sublimation-products/hand-covers/', 'Handschuhe & Huellen'),
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


def scrape_category(category_url, category_name, max_pages=10):
    """Scrapt alle Produkte einer Kategorie (inkl. Pagination)"""
    products = []
    page = 1

    while page <= max_pages:
        url = f'{BASE_URL}{category_url}'
        if page > 1:
            url += f'?p={page}'

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                break

            page_products = parse_products_from_html(resp.text, category_name)
            if not page_products:
                break

            products.extend(page_products)
            logger.info(f"  Seite {page}: {len(page_products)} Produkte ({category_name})")

            # Pruefen ob es eine naechste Seite gibt
            if f'?p={page + 1}' not in resp.text and f'p={page + 1}' not in resp.text:
                break

            page += 1
            time.sleep(1)  # Rate limiting

        except Exception as e:
            logger.warning(f"Fehler beim Scrapen von {url}: {e}")
            break

    return products


def parse_products_from_html(html, category_name):
    """Parst Produkte aus dem HTML (nutzt eingebettete JSON-Daten)"""
    products = []

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        # Methode 1: Google Analytics JSON-Daten
        # Suche nach gtag view_item_list Events
        scripts = soup.find_all('script')
        for script in scripts:
            text = script.string or ''
            if 'view_item_list' in text and 'item_id' in text:
                # JSON-Daten aus dem Script extrahieren
                matches = re.findall(r'\{[^{}]*"item_id"\s*:\s*"[^"]+?"[^{}]*\}', text)
                for match in matches:
                    try:
                        item = json.loads(match)
                        sku = item.get('item_id', '').strip()
                        name = item.get('item_name', '').strip()
                        price = float(item.get('price', 0))

                        if sku and name:
                            products.append({
                                'sku': sku,
                                'name': name,
                                'price': price,
                                'category': category_name,
                            })
                    except (json.JSONDecodeError, ValueError):
                        continue

        # Methode 2: Produktkarten parsen (Fallback)
        if not products:
            product_cards = soup.select('.product-box, .product-card, [data-product-id]')
            for card in product_cards:
                sku_el = card.select_one('[data-product-number], .product-number')
                name_el = card.select_one('.product-name, .product-title, h3, h4')
                price_el = card.select_one('.product-price, .price')

                sku = ''
                if sku_el:
                    sku = sku_el.get('data-product-number', '') or sku_el.get_text(strip=True)
                name = name_el.get_text(strip=True) if name_el else ''
                price_text = price_el.get_text(strip=True) if price_el else '0'
                price = 0
                price_match = re.search(r'[\d.,]+', price_text.replace(',', '.'))
                if price_match:
                    price = float(price_match.group())

                if sku and name:
                    products.append({
                        'sku': sku,
                        'name': name,
                        'price': price,
                        'category': category_name,
                    })

        # Bilder den Produkten zuordnen
        img_map = {}
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or ''
            alt = (img.get('alt') or '').strip()
            if '/media/' in src and alt:
                if src.startswith('/'):
                    src = BASE_URL + src
                img_map[alt.lower()] = src

        for product in products:
            name_lower = product['name'].lower()
            for alt, url in img_map.items():
                if name_lower in alt or alt in name_lower:
                    product['image_url'] = url
                    break
            if 'image_url' not in product:
                # Versuche SKU-basierte Zuordnung
                for alt, url in img_map.items():
                    if product['sku'].lower() in alt:
                        product['image_url'] = url
                        break

    except ImportError:
        logger.error("beautifulsoup4 nicht installiert")
    except Exception as e:
        logger.error(f"Parse-Fehler: {e}")

    return products


def import_products_to_db(products, upload_dir='instance/uploads'):
    """Importiert gescrapte Produkte in die Datenbank"""
    from src.models import db
    from src.models.models import Article

    created = 0
    updated = 0
    skipped = 0

    for product in products:
        try:
            # Pruefen ob Artikel schon existiert (per supplier_article_number)
            existing = Article.query.filter_by(
                supplier_article_number=product['sku']
            ).first()

            if existing:
                # Preis aktualisieren falls geaendert
                if existing.purchase_price_single != product['price']:
                    existing.purchase_price_single = product['price']
                    updated += 1
                else:
                    skipped += 1
                continue

            # Neuen Artikel erstellen
            article = Article(
                id=f"PE-{product['sku']}",
                name=product['name'],
                supplier_article_number=product['sku'],
                article_number=f"PE-{product['sku']}",
                supplier='Printequipment',
                category='Sublimation',
                product_type=product.get('category', 'Sublimation'),
                purchase_price_single=product['price'],
                price=round(product['price'] * 2.5, 2),  # 2.5x Aufschlag als Startpreis
                active=True,
                created_at=datetime.utcnow(),
            )

            # Bild herunterladen falls vorhanden
            if product.get('image_url'):
                try:
                    from src.services.article_image_service import ArticleImageSearchService
                    service = ArticleImageSearchService(upload_base_dir=upload_dir)
                    result = service.download_and_save(
                        f"PE-{product['sku']}",
                        product['image_url']
                    )
                    if result.get('success'):
                        article.image_url = product['image_url']
                        article.image_path = result['image_path']
                        article.image_thumbnail_path = result['thumbnail_path']
                except Exception as e:
                    logger.warning(f"Bild-Download fuer {product['sku']} fehlgeschlagen: {e}")

            db.session.add(article)
            created += 1

            # Batch-Commit alle 50 Artikel
            if created % 50 == 0:
                db.session.commit()
                logger.info(f"Batch-Commit: {created} Artikel erstellt")

        except Exception as e:
            logger.warning(f"Import-Fehler fuer {product.get('sku', '?')}: {e}")
            try:
                db.session.rollback()
            except Exception:
                pass

    # Finaler Commit
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Finaler Commit fehlgeschlagen: {e}")

    return {'created': created, 'updated': updated, 'skipped': skipped}


def run_full_import(app_context, upload_dir='instance/uploads'):
    """Fuehrt den kompletten Import aller Sublimations-Kategorien durch"""
    with app_context:
        all_products = []

        logger.info("=== Printequipment Sublimation Import gestartet ===")

        for cat_url, cat_name in SUBLIMATION_CATEGORIES:
            logger.info(f"Scrape Kategorie: {cat_name}")
            products = scrape_category(cat_url, cat_name)
            all_products.extend(products)
            time.sleep(2)  # Pause zwischen Kategorien

        logger.info(f"Gesamt gescrapt: {len(all_products)} Produkte")

        # Duplikate entfernen (gleiche SKU)
        seen = set()
        unique = []
        for p in all_products:
            if p['sku'] not in seen:
                seen.add(p['sku'])
                unique.append(p)

        logger.info(f"Unique Produkte: {len(unique)}")

        result = import_products_to_db(unique, upload_dir)
        logger.info(f"=== Import abgeschlossen: {result['created']} neu, {result['updated']} aktualisiert, {result['skipped']} uebersprungen ===")

        return result


def assign_druckparameter(pdf_entries):
    """
    Weist Druckparameter aus der PDF den importierten Printequipment-Artikeln zu.

    Args:
        pdf_entries: Liste von Dicts aus parse_druckparameter_pdf()

    Returns:
        Dict mit {matched: int, assigned: int, skipped: int, errors: int}
    """
    from src.models import db
    from src.models.models import Article
    from src.models.veredelung import (
        VeredelungsVerfahren, VeredelungsParameter, ArtikelVeredelung
    )

    # Sublimation-Verfahren laden (oder anlegen)
    sublimation = VeredelungsVerfahren.get_by_code('sublimation')
    if not sublimation:
        logger.info("Sublimation-Verfahren nicht vorhanden, erstelle Defaults...")
        VeredelungsVerfahren.seed_defaults()
        sublimation = VeredelungsVerfahren.get_by_code('sublimation')
        if not sublimation:
            logger.error("Sublimation-Verfahren konnte nicht erstellt werden")
            return {'matched': 0, 'assigned': 0, 'skipped': 0, 'errors': 1}

    # Parameter-Map aufbauen: Name -> VeredelungsParameter
    param_map = {}
    for p in sublimation.parameter:
        param_map[p.name.lower()] = p

    # Mapping PDF-Felder -> Parameter-Name in DB
    field_mapping = {
        'temperatur': 'temperatur',
        'zeit': 'presszeit',
        'druck': 'druck',
        'papier': 'papierposition',
        'bemerkung': 'bemerkung',
    }

    stats = {'matched': 0, 'assigned': 0, 'skipped': 0, 'errors': 0}

    for entry in pdf_entries:
        try:
            # Artikel per SKU-Prefix suchen
            matched_articles = []
            for prefix in entry.get('sku_patterns', []):
                articles = Article.query.filter(
                    Article.supplier_article_number.ilike(prefix + '%'),
                    Article.supplier == 'Printequipment'
                ).all()
                matched_articles.extend(articles)

            if not matched_articles:
                stats['skipped'] += 1
                continue

            # Duplikate entfernen (Artikel koennte ueber mehrere Prefixes gefunden werden)
            seen_ids = set()
            unique_articles = []
            for art in matched_articles:
                if art.id not in seen_ids:
                    seen_ids.add(art.id)
                    unique_articles.append(art)

            stats['matched'] += len(unique_articles)

            for article in unique_articles:
                for pdf_field, param_name in field_mapping.items():
                    wert = entry.get(pdf_field, '').strip()
                    if not wert:
                        continue

                    param = param_map.get(param_name)
                    if not param:
                        continue

                    # Upsert: Existierenden Eintrag updaten oder neuen erstellen
                    existing = ArtikelVeredelung.query.filter_by(
                        article_id=article.id,
                        parameter_id=param.id
                    ).first()

                    if existing:
                        existing.wert = wert
                    else:
                        av = ArtikelVeredelung(
                            article_id=article.id,
                            verfahren_id=sublimation.id,
                            parameter_id=param.id,
                            wert=wert
                        )
                        db.session.add(av)

                    stats['assigned'] += 1

        except Exception as e:
            logger.warning(f"Fehler bei Zuordnung fuer {entry.get('sku_raw', '?')}: {e}")
            stats['errors'] += 1

    try:
        db.session.commit()
        logger.info(f"Druckparameter zugewiesen: {stats}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Commit fehlgeschlagen: {e}")
        stats['errors'] += 1

    return stats
