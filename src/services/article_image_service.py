# -*- coding: utf-8 -*-
"""
Article Image Search Service
Sucht automatisch Produktbilder per Artikelnummer/Bezeichnung.
Quellen: Lieferanten-Webseiten (L-Shop) + Google Custom Search API

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
import re
import uuid
import logging
import requests
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)

# Bildoptimierung
MAX_IMAGE_SIZE = (800, 800)
THUMBNAIL_SIZE = (200, 200)
JPEG_QUALITY = 85


class ArticleImageSearchService:
    """Sucht und speichert Artikelbilder aus verschiedenen Quellen"""

    def __init__(self, upload_base_dir='instance/uploads'):
        self.upload_base_dir = upload_base_dir
        self.articles_dir = os.path.join(upload_base_dir, 'articles')
        self.thumbnails_dir = os.path.join(upload_base_dir, 'articles', 'thumbs')
        os.makedirs(self.articles_dir, exist_ok=True)
        os.makedirs(self.thumbnails_dir, exist_ok=True)

    def search_images(self, article):
        """
        Sucht Bilder fuer einen Artikel. Erst gespeicherte URL, dann Google.

        Args:
            article: Article Model-Objekt

        Returns:
            list: [{url, source, thumbnail_url, width, height}, ...]
        """
        results = []

        # 0. Bereits gespeicherte Bild-URL (aus LShop-Import o.Ä.)
        if getattr(article, 'image_url', None):
            results.append({
                'url': article.image_url,
                'source': 'Lieferant',
                'thumbnail_url': article.image_url,
            })
            return results  # Direkt zurück, kein weiteres Suchen nötig

        # 1. Lieferanten-Suche (L-Shop, etc.) – nur wenn keine URL gespeichert
        supplier = (article.supplier or '').lower()
        supplier_art_nr = article.supplier_article_number or article.article_number or ''

        if supplier_art_nr:
            if 'l-shop' in supplier or 'lshop' in supplier or 'l shop' in supplier:
                results.extend(self._search_lshop(supplier_art_nr, article.name))
            else:
                # Generische Lieferanten-Suche per Artikelnummer
                results.extend(self._search_lshop(supplier_art_nr, article.name))

        # 2. Google Custom Search als Fallback
        if len(results) < 3:
            query_parts = []
            if article.brand:
                query_parts.append(article.brand)
            elif article.brand_id:
                try:
                    from src.models.models import Brand
                    brand = Brand.query.get(article.brand_id)
                    if brand:
                        query_parts.append(brand.name)
                except Exception:
                    pass
            if supplier_art_nr:
                query_parts.append(supplier_art_nr)
            if article.name:
                query_parts.append(article.name)
            query = ' '.join(query_parts)
            if query.strip():
                google_results = self._search_google(query)
                results.extend(google_results)

        return results[:8]

    def _search_lshop(self, article_number, name=''):
        """
        Sucht Produktbilder auf L-Shop Textil.
        Versucht die Produktseite zu finden und Bilder zu extrahieren.
        """
        results = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("beautifulsoup4 nicht installiert - L-Shop Suche deaktiviert")
            return results

        # Suche auf L-Shop
        search_url = f'https://www.l-shop-team.de/suche?q={requests.utils.quote(article_number)}'
        try:
            resp = requests.get(search_url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return results

            soup = BeautifulSoup(resp.text, 'html.parser')

            # Produktbilder aus Suchergebnissen extrahieren
            # L-Shop verwendet verschiedene img-Klassen fuer Produktbilder
            product_images = set()

            # Methode 1: og:image Meta-Tag (wenn direkt auf Produktseite)
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                img_url = og_image['content']
                if img_url and 'logo' not in img_url.lower() and 'icon' not in img_url.lower():
                    product_images.add(img_url)

            # Methode 2: Produktbilder in Suchergebnissen
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src') or ''
                if not src:
                    continue
                # Nur Produktbilder (keine Icons/Logos)
                if any(x in src.lower() for x in ['/product', '/artikel', '/media/image', '/thumbnail']):
                    if not any(x in src.lower() for x in ['logo', 'icon', 'banner', 'sprite', 'pixel']):
                        # Relative URLs ergaenzen
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            src = 'https://www.l-shop-team.de' + src
                        product_images.add(src)

            # Methode 3: Links zu Produktseiten finden und deren Bilder laden
            if not product_images:
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    art_nr_clean = article_number.replace(' ', '').lower()
                    if art_nr_clean in href.replace(' ', '').lower():
                        product_url = href if href.startswith('http') else f'https://www.l-shop-team.de{href}'
                        try:
                            prod_resp = requests.get(product_url, headers=headers, timeout=10)
                            if prod_resp.status_code == 200:
                                prod_soup = BeautifulSoup(prod_resp.text, 'html.parser')
                                og = prod_soup.find('meta', property='og:image')
                                if og and og.get('content'):
                                    product_images.add(og['content'])
                                for img in prod_soup.find_all('img'):
                                    src = img.get('src') or img.get('data-src') or ''
                                    if any(x in src.lower() for x in ['/product', '/media/image']):
                                        if src.startswith('/'):
                                            src = 'https://www.l-shop-team.de' + src
                                        product_images.add(src)
                        except Exception:
                            pass
                        break  # Nur erste passende Produktseite

            for url in list(product_images)[:4]:
                results.append({
                    'url': url,
                    'source': 'L-Shop',
                    'thumbnail_url': url,
                })

        except requests.exceptions.RequestException as e:
            logger.warning(f"L-Shop Suche fehlgeschlagen: {e}")
        except Exception as e:
            logger.error(f"L-Shop Parsing-Fehler: {e}")

        return results

    def _search_google(self, query):
        """
        Sucht Bilder per Google Custom Search API.
        Benoetigt API-Key und CX in CompanySettings.
        """
        results = []

        try:
            from src.models.company_settings import CompanySettings
            settings = CompanySettings.get_settings()
            api_key = settings.google_api_key
            cx = settings.google_search_cx

            if not api_key or not cx:
                logger.debug("Google API nicht konfiguriert - Suche uebersprungen")
                return results

            params = {
                'key': api_key,
                'cx': cx,
                'q': query,
                'searchType': 'image',
                'num': 5,
                'imgSize': 'medium',
                'safe': 'active',
            }

            resp = requests.get(
                'https://www.googleapis.com/customsearch/v1',
                params=params,
                timeout=10
            )

            if resp.status_code == 200:
                data = resp.json()
                for item in data.get('items', []):
                    results.append({
                        'url': item.get('link', ''),
                        'source': 'Google',
                        'thumbnail_url': item.get('image', {}).get('thumbnailLink', item.get('link', '')),
                        'width': item.get('image', {}).get('width', 0),
                        'height': item.get('image', {}).get('height', 0),
                    })
            elif resp.status_code == 403:
                logger.warning("Google API Limit erreicht oder Key ungueltig")
            else:
                logger.warning(f"Google API Fehler: {resp.status_code}")

        except requests.exceptions.RequestException as e:
            logger.warning(f"Google Bildersuche fehlgeschlagen: {e}")
        except Exception as e:
            logger.error(f"Google Bildersuche Fehler: {e}")

        return results

    def download_and_save(self, article_id, image_url):
        """
        Laedt ein Bild herunter, optimiert es und speichert es lokal.

        Args:
            article_id: ID des Artikels
            image_url: URL des Bildes

        Returns:
            dict: {success, image_path, thumbnail_path, error}
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            resp = requests.get(image_url, headers=headers, timeout=15, stream=True)
            resp.raise_for_status()

            # Pruefen ob es ein Bild ist
            content_type = resp.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                return {'success': False, 'error': 'URL ist kein Bild'}

            # Bild oeffnen und optimieren
            img = Image.open(BytesIO(resp.content))

            # RGBA -> RGB konvertieren
            if img.mode in ('RGBA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[3] if len(img.split()) == 4 else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Groesse optimieren
            if img.size[0] > MAX_IMAGE_SIZE[0] or img.size[1] > MAX_IMAGE_SIZE[1]:
                img.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)

            # Sauberen Dateinamen aus article_id generieren
            safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', str(article_id))
            filename = f"{safe_id}.jpg"

            # Speichern
            image_path = os.path.join(self.articles_dir, filename)
            img.save(image_path, 'JPEG', quality=JPEG_QUALITY, optimize=True)

            # Thumbnail erstellen
            thumb_img = img.copy()
            thumb_img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
            thumb_filename = f"thumb_{filename}"
            thumb_path = os.path.join(self.thumbnails_dir, thumb_filename)
            thumb_img.save(thumb_path, 'JPEG', quality=80, optimize=True)

            # Relative Pfade fuer DB
            rel_image = f"articles/{filename}"
            rel_thumb = f"articles/thumbs/{thumb_filename}"

            return {
                'success': True,
                'image_path': rel_image,
                'thumbnail_path': rel_thumb,
            }

        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'Download fehlgeschlagen: {e}'}
        except Exception as e:
            logger.error(f"Bild-Speicherung fehlgeschlagen: {e}")
            return {'success': False, 'error': str(e)}

    def delete_image(self, image_path, thumbnail_path=None):
        """Loescht ein lokal gespeichertes Artikelbild"""
        if image_path:
            full_path = os.path.join(self.upload_base_dir, image_path)
            if os.path.exists(full_path):
                os.remove(full_path)
        if thumbnail_path:
            full_path = os.path.join(self.upload_base_dir, thumbnail_path)
            if os.path.exists(full_path):
                os.remove(full_path)
