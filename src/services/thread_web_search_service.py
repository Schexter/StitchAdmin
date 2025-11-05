"""
Garn-Web-Suchsystem für große Garnhersteller
Erstellt von Hans Hahn - Alle Rechte vorbehalten

Dieses Modul bietet:
1. Automatische Suche bei großen Garnherstellern
2. Farb-/Nummer-basierte Produktsuche
3. Preisvergleich zwischen Lieferanten
4. Integration mit Garnlieferanten-Webshops
5. Lagerbestand-Überwachung mit automatischen Suchvorschlägen
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import time
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ThreadWebSearchService:
    """Service für automatische Garn-Web-Suche bei Herstellern"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Große Garnhersteller-Konfiguration
        self.thread_manufacturers = {
            'madeira': {
                'name': 'Madeira',
                'base_url': 'https://www.madeira.de',
                'search_url': 'https://www.madeira.de/search',
                'search_method': 'selenium',
                'color_systems': ['Madeira Rayon', 'Madeira Poly', 'Madeira Metallic'],
                'search_patterns': {
                    'color_number': r'(\d{4})',
                    'color_name': r'([A-Za-z\s]+)',
                    'price': r'(\d+[,.]?\d*)\s*€'
                }
            },
            'gütermann': {
                'name': 'Gütermann',
                'base_url': 'https://www.guetermann.com',
                'search_url': 'https://www.guetermann.com/de/products',
                'search_method': 'requests',
                'color_systems': ['Mara', 'Sulky', 'Toldi'],
                'search_patterns': {
                    'color_number': r'(\d{3,4})',
                    'color_name': r'([A-Za-z\s]+)',
                    'price': r'(\d+[,.]?\d*)\s*€'
                }
            },
            'anchor': {
                'name': 'Anchor',
                'base_url': 'https://www.anchor.com',
                'search_url': 'https://www.anchor.com/products',
                'search_method': 'requests',
                'color_systems': ['Anchor Cotton', 'Anchor Wool'],
                'search_patterns': {
                    'color_number': r'(\d{3,4})',
                    'color_name': r'([A-Za-z\s]+)',
                    'price': r'(\d+[,.]?\d*)\s*€'
                }
            },
            'coats': {
                'name': 'Coats',
                'base_url': 'https://www.coats.com',
                'search_url': 'https://www.coats.com/products',
                'search_method': 'requests',
                'color_systems': ['Epic', 'Gral', 'Nylbond'],
                'search_patterns': {
                    'color_number': r'(\d{3,5})',
                    'color_name': r'([A-Za-z\s]+)',
                    'price': r'(\d+[,.]?\d*)\s*€'
                }
            },
            'hemingworth': {
                'name': 'Hemingworth',
                'base_url': 'https://www.hemingworth.com',
                'search_url': 'https://www.hemingworth.com/thread-colors',
                'search_method': 'requests',
                'color_systems': ['Hemingworth Poly', 'Hemingworth Cotton'],
                'search_patterns': {
                    'color_number': r'(\d{4})',
                    'color_name': r'([A-Za-z\s]+)',
                    'price': r'\$(\d+[,.]?\d*)'
                }
            },
            'brother': {
                'name': 'Brother',
                'base_url': 'https://www.brother.de',
                'search_url': 'https://www.brother.de/stickgarne',
                'search_method': 'selenium',
                'color_systems': ['Brother Embroidery', 'Country'],
                'search_patterns': {
                    'color_number': r'(\d{3})',
                    'color_name': r'([A-Za-z\s]+)',
                    'price': r'(\d+[,.]?\d*)\s*€'
                }
            }
        }
        
        # Deutsche Garnlieferanten/Shops
        self.german_suppliers = {
            'nadelwelt': {
                'name': 'Nadelwelt',
                'base_url': 'https://www.nadelwelt.de',
                'search_url': 'https://www.nadelwelt.de/suche',
                'search_method': 'requests'
            },
            'makerist': {
                'name': 'Makerist',
                'base_url': 'https://www.makerist.de',
                'search_url': 'https://www.makerist.de/search',
                'search_method': 'requests'
            },
            'stoffkontor': {
                'name': 'Stoffkontor',
                'base_url': 'https://www.stoffkontor.eu',
                'search_url': 'https://www.stoffkontor.eu/catalogsearch/result',
                'search_method': 'requests'
            },
            'stoffe_hemmers': {
                'name': 'Stoffe Hemmers',
                'base_url': 'https://www.stoffehemmers.de',
                'search_url': 'https://www.stoffehemmers.de/search',
                'search_method': 'requests'
            }
        }
    
    def search_thread_by_number(self, manufacturer: str, color_number: str, color_name: str = None) -> List[Dict]:
        """
        Sucht Garn nach Hersteller und Farbnummer
        
        Args:
            manufacturer: Hersteller-Name (z.B. 'madeira', 'gütermann')
            color_number: Farbnummer (z.B. '1147', '5005')
            color_name: Optionaler Farbname für bessere Suche
            
        Returns:
            Liste von gefundenen Garnen mit Details
        """
        
        results = []
        manufacturer_key = manufacturer.lower().replace('ü', 'u').replace(' ', '_')
        
        # 1. Beim Original-Hersteller suchen
        if manufacturer_key in self.thread_manufacturers:
            manufacturer_results = self._search_manufacturer_website(
                manufacturer_key, color_number, color_name
            )
            results.extend(manufacturer_results)
        
        # 2. Bei deutschen Lieferanten/Shops suchen
        for supplier_key, supplier_config in self.german_suppliers.items():
            supplier_results = self._search_supplier_website(
                supplier_key, manufacturer, color_number, color_name
            )
            results.extend(supplier_results)
        
        # 3. Allgemeine Google-Suche als Fallback
        if len(results) < 3:
            google_results = self._search_google(manufacturer, color_number, color_name)
            results.extend(google_results)
        
        # Ergebnisse nach Relevanz sortieren
        results = self._sort_results_by_relevance(results, color_number, color_name)
        
        return results[:10]  # Top 10 Ergebnisse
    
    def _search_manufacturer_website(self, manufacturer_key: str, color_number: str, color_name: str = None) -> List[Dict]:
        """Sucht direkt auf der Hersteller-Website"""
        manufacturer_config = self.thread_manufacturers[manufacturer_key]
        results = []
        
        try:
            if manufacturer_config['search_method'] == 'selenium':
                results = self._search_with_selenium(manufacturer_config, color_number, color_name)
            else:
                results = self._search_with_requests(manufacturer_config, color_number, color_name)
                
        except Exception as e:
            logger.error(f"Fehler bei Hersteller-Suche {manufacturer_key}: {e}")
        
        return results
    
    def _search_with_selenium(self, config: Dict, color_number: str, color_name: str = None) -> List[Dict]:
        """Verwendet Selenium für komplexe JavaScript-basierte Webseiten"""
        results = []
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            wait = WebDriverWait(driver, 10)
            
            # Zur Suchseite navigieren
            driver.get(config['search_url'])
            time.sleep(2)
            
            # Suchfeld finden und Farbnummer eingeben
            search_selectors = [
                "input[name='search']", "#search", ".search-input",
                "input[type='search']", "[placeholder*='suchen']"
            ]
            
            search_field = None
            for selector in search_selectors:
                try:
                    search_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    break
                except TimeoutException:
                    continue
            
            if search_field:
                search_query = f"{color_number}"
                if color_name:
                    search_query += f" {color_name}"
                
                search_field.clear()
                search_field.send_keys(search_query)
                search_field.submit()
                
                time.sleep(3)
                
                # Ergebnisse extrahieren
                results = self._extract_selenium_results(driver, config)
            
            driver.quit()
            
        except Exception as e:
            logger.error(f"Selenium-Suche fehlgeschlagen: {e}")
            if 'driver' in locals():
                driver.quit()
        
        return results
    
    def _search_with_requests(self, config: Dict, color_number: str, color_name: str = None) -> List[Dict]:
        """Verwendet requests für einfache HTML-basierte Webseiten"""
        results = []
        
        try:
            # Suchparameter vorbereiten
            search_query = color_number
            if color_name:
                search_query += f" {color_name}"
            
            # GET-Request mit Suchparametern
            params = {
                'q': search_query,
                'search': search_query,
                'query': search_query
            }
            
            response = self.session.get(config['search_url'], params=params, timeout=10)
            response.raise_for_status()
            
            # HTML parsen
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Ergebnisse extrahieren
            results = self._extract_html_results(soup, config, color_number)
            
        except Exception as e:
            logger.error(f"Requests-Suche fehlgeschlagen: {e}")
        
        return results
    
    def _extract_selenium_results(self, driver, config: Dict) -> List[Dict]:
        """Extrahiert Ergebnisse aus Selenium-Browser"""
        results = []
        
        try:
            # Produktcontainer finden
            product_selectors = [
                ".product", ".article", ".item", ".thread-item",
                ".product-item", ".search-result", ".color-item"
            ]
            
            products = []
            for selector in product_selectors:
                try:
                    products = driver.find_elements(By.CSS_SELECTOR, selector)
                    if products:
                        break
                except NoSuchElementException:
                    continue
            
            for product in products[:5]:  # Erste 5 Treffer
                try:
                    result = self._extract_product_data_selenium(product, config)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.warning(f"Fehler beim Extrahieren eines Produkts: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Fehler beim Extrahieren der Selenium-Ergebnisse: {e}")
        
        return results
    
    def _extract_product_data_selenium(self, product_element, config: Dict) -> Optional[Dict]:
        """Extrahiert Produktdaten aus einem Selenium-Element"""
        try:
            # Farbnummer extrahieren
            color_number = self._extract_text_by_pattern(
                product_element.text, 
                config['search_patterns']['color_number']
            )
            
            # Farbname extrahieren
            color_name = self._extract_color_name(product_element.text)
            
            # Preis extrahieren
            price = self._extract_text_by_pattern(
                product_element.text,
                config['search_patterns']['price']
            )
            
            # Link extrahieren
            link_element = product_element.find_element(By.TAG_NAME, "a")
            link = link_element.get_attribute("href") if link_element else None
            
            # Bild extrahieren
            img_element = product_element.find_element(By.TAG_NAME, "img")
            image_url = img_element.get_attribute("src") if img_element else None
            
            return {
                'manufacturer': config['name'],
                'color_number': color_number,
                'color_name': color_name,
                'price': price,
                'currency': 'EUR',
                'link': link,
                'image_url': image_url,
                'source': config['base_url'],
                'availability': 'unknown',
                'search_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.warning(f"Fehler beim Extrahieren von Produktdaten: {e}")
            return None
    
    def _extract_html_results(self, soup: BeautifulSoup, config: Dict, color_number: str) -> List[Dict]:
        """Extrahiert Ergebnisse aus HTML-Soup"""
        results = []
        
        try:
            # Produktcontainer finden
            product_selectors = [
                ".product", ".article", ".item", ".thread-item",
                ".product-item", ".search-result", ".color-item",
                "[data-product]", ".product-card"
            ]
            
            products = []
            for selector in product_selectors:
                products = soup.select(selector)
                if products:
                    break
            
            for product in products[:5]:  # Erste 5 Treffer
                try:
                    result = self._extract_product_data_html(product, config, color_number)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.warning(f"Fehler beim Extrahieren eines Produkts: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Fehler beim Extrahieren der HTML-Ergebnisse: {e}")
        
        return results
    
    def _extract_product_data_html(self, product_soup, config: Dict, search_color_number: str) -> Optional[Dict]:
        """Extrahiert Produktdaten aus einem BeautifulSoup-Element"""
        try:
            product_text = product_soup.get_text()
            
            # Farbnummer extrahieren
            color_number = self._extract_text_by_pattern(
                product_text, 
                config['search_patterns']['color_number']
            )
            
            # Farbname extrahieren
            color_name = self._extract_color_name(product_text)
            
            # Preis extrahieren
            price = self._extract_text_by_pattern(
                product_text,
                config['search_patterns']['price']
            )
            
            # Link extrahieren
            link_element = product_soup.find('a')
            link = link_element.get('href') if link_element else None
            if link and not link.startswith('http'):
                link = config['base_url'] + link
            
            # Bild extrahieren
            img_element = product_soup.find('img')
            image_url = img_element.get('src') if img_element else None
            if image_url and not image_url.startswith('http'):
                image_url = config['base_url'] + image_url
            
            # Verfügbarkeit prüfen
            availability = 'unknown'
            availability_indicators = ['auf lager', 'verfügbar', 'in stock', 'available']
            unavailability_indicators = ['ausverkauft', 'nicht verfügbar', 'out of stock']
            
            product_text_lower = product_text.lower()
            if any(indicator in product_text_lower for indicator in availability_indicators):
                availability = 'available'
            elif any(indicator in product_text_lower for indicator in unavailability_indicators):
                availability = 'out_of_stock'
            
            return {
                'manufacturer': config['name'],
                'color_number': color_number or search_color_number,
                'color_name': color_name,
                'price': price,
                'currency': 'EUR',
                'link': link,
                'image_url': image_url,
                'source': config['base_url'],
                'availability': availability,
                'search_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.warning(f"Fehler beim Extrahieren von HTML-Produktdaten: {e}")
            return None
    
    def _search_supplier_website(self, supplier_key: str, manufacturer: str, color_number: str, color_name: str = None) -> List[Dict]:
        """Sucht bei deutschen Garnlieferanten/Shops"""
        supplier_config = self.german_suppliers[supplier_key]
        results = []
        
        try:
            # Suchquery zusammenstellen
            search_query = f"{manufacturer} {color_number}"
            if color_name:
                search_query += f" {color_name}"
            
            params = {
                'q': search_query,
                'search': search_query,
                'query': search_query
            }
            
            response = self.session.get(supplier_config['search_url'], params=params, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Einfache Produktextraktion für Shops
            results = self._extract_shop_results(soup, supplier_config, manufacturer, color_number)
            
        except Exception as e:
            logger.error(f"Fehler bei Lieferanten-Suche {supplier_key}: {e}")
        
        return results
    
    def _extract_shop_results(self, soup: BeautifulSoup, config: Dict, manufacturer: str, color_number: str) -> List[Dict]:
        """Extrahiert Ergebnisse aus Shop-Websites"""
        results = []
        
        try:
            # Shop-spezifische Selektoren
            product_selectors = [
                ".product", ".article", ".item", ".search-result",
                ".product-item", ".product-card", ".product-tile",
                "[data-product]", ".grid-item"
            ]
            
            products = []
            for selector in product_selectors:
                products = soup.select(selector)
                if products:
                    break
            
            for product in products[:3]:  # Erste 3 Treffer pro Shop
                try:
                    product_text = product.get_text()
                    
                    # Prüfe ob Hersteller und Farbnummer im Text vorkommen
                    if (manufacturer.lower() in product_text.lower() and 
                        color_number in product_text):
                        
                        # Link extrahieren
                        link_element = product.find('a')
                        link = link_element.get('href') if link_element else None
                        if link and not link.startswith('http'):
                            link = config['base_url'] + link
                        
                        # Preis extrahieren (deutscher Shop-Standard)
                        price_match = re.search(r'(\d+[,.]?\d*)\s*€', product_text)
                        price = price_match.group(1) if price_match else None
                        
                        # Titel extrahieren
                        title_element = product.find(['h1', 'h2', 'h3', 'h4', '.title', '.name'])
                        title = title_element.get_text().strip() if title_element else product_text[:50]
                        
                        results.append({
                            'manufacturer': manufacturer,
                            'color_number': color_number,
                            'color_name': self._extract_color_name(title),
                            'price': price,
                            'currency': 'EUR',
                            'link': link,
                            'source': config['name'],
                            'availability': 'unknown',
                            'search_timestamp': datetime.now().isoformat(),
                            'supplier_type': 'shop'
                        })
                        
                except Exception as e:
                    logger.warning(f"Fehler beim Extrahieren eines Shop-Produkts: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Fehler beim Extrahieren der Shop-Ergebnisse: {e}")
        
        return results
    
    def _search_google(self, manufacturer: str, color_number: str, color_name: str = None) -> List[Dict]:
        """Google-Suche als Fallback"""
        results = []
        
        try:
            # Google-Suchquery
            search_query = f"{manufacturer} garn {color_number}"
            if color_name:
                search_query += f" {color_name}"
            search_query += " kaufen"
            
            # Google Custom Search API (falls verfügbar) oder DuckDuckGo
            # Hier vereinfachte Implementation
            
            params = {
                'q': search_query,
                'format': 'json',
                'no_redirect': '1'
            }
            
            # DuckDuckGo Instant Answer API
            response = self.session.get('https://api.duckduckgo.com/', params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # RelatedTopics extrahieren
                for topic in data.get('RelatedTopics', [])[:3]:
                    if isinstance(topic, dict) and 'FirstURL' in topic:
                        results.append({
                            'manufacturer': manufacturer,
                            'color_number': color_number,
                            'color_name': color_name,
                            'price': None,
                            'currency': 'EUR',
                            'link': topic['FirstURL'],
                            'source': 'Web-Suche',
                            'availability': 'unknown',
                            'search_timestamp': datetime.now().isoformat(),
                            'supplier_type': 'web'
                        })
            
        except Exception as e:
            logger.error(f"Google-Suche fehlgeschlagen: {e}")
        
        return results
    
    def _extract_text_by_pattern(self, text: str, pattern: str) -> Optional[str]:
        """Extrahiert Text anhand eines Regex-Patterns"""
        try:
            match = re.search(pattern, text)
            return match.group(1) if match else None
        except Exception:
            return None
    
    def _extract_color_name(self, text: str) -> Optional[str]:
        """Versucht Farbname aus Text zu extrahieren"""
        # Deutsche und englische Farbnamen
        color_names = [
            'rot', 'red', 'blau', 'blue', 'grün', 'green', 'gelb', 'yellow',
            'schwarz', 'black', 'weiß', 'white', 'grau', 'gray', 'grey',
            'rosa', 'pink', 'lila', 'purple', 'violet', 'orange', 'braun', 'brown',
            'beige', 'creme', 'cream', 'gold', 'silber', 'silver', 'türkis', 'turquoise'
        ]
        
        text_lower = text.lower()
        for color in color_names:
            if color in text_lower:
                return color.capitalize()
        
        return None
    
    def _sort_results_by_relevance(self, results: List[Dict], color_number: str, color_name: str = None) -> List[Dict]:
        """Sortiert Ergebnisse nach Relevanz"""
        def relevance_score(result):
            score = 0
            
            # Exakte Farbnummer-Übereinstimmung
            if result.get('color_number') == color_number:
                score += 10
            
            # Preis verfügbar
            if result.get('price'):
                score += 5
            
            # Verfügbarkeit bekannt
            if result.get('availability') == 'available':
                score += 3
            
            # Original-Hersteller
            if result.get('supplier_type') != 'shop':
                score += 2
            
            # Farbname-Übereinstimmung
            if (color_name and result.get('color_name') and 
                color_name.lower() in result.get('color_name', '').lower()):
                score += 2
            
            return score
        
        return sorted(results, key=relevance_score, reverse=True)
    
    def get_price_comparison(self, manufacturer: str, color_number: str) -> Dict:
        """Erstellt einen Preisvergleich für ein Garn"""
        results = self.search_thread_by_number(manufacturer, color_number)
        
        price_comparison = {
            'manufacturer': manufacturer,
            'color_number': color_number,
            'results_count': len(results),
            'sources': [],
            'price_range': None,
            'best_price': None,
            'average_price': None
        }
        
        prices = []
        
        for result in results:
            if result.get('price'):
                try:
                    # Preis normalisieren (Komma zu Punkt)
                    price_str = str(result['price']).replace(',', '.')
                    price = float(re.search(r'(\d+\.?\d*)', price_str).group(1))
                    prices.append(price)
                    
                    price_comparison['sources'].append({
                        'source': result.get('source', 'Unbekannt'),
                        'price': price,
                        'currency': result.get('currency', 'EUR'),
                        'availability': result.get('availability', 'unknown'),
                        'link': result.get('link')
                    })
                except (ValueError, AttributeError):
                    continue
        
        if prices:
            price_comparison['price_range'] = {
                'min': min(prices),
                'max': max(prices)
            }
            price_comparison['best_price'] = min(prices)
            price_comparison['average_price'] = round(sum(prices) / len(prices), 2)
        
        return price_comparison


def search_thread_web(manufacturer: str, color_number: str, color_name: str = None) -> Dict:
    """
    Hauptfunktion für Garn-Web-Suche
    
    Args:
        manufacturer: Hersteller-Name
        color_number: Farbnummer  
        color_name: Optionaler Farbname
        
    Returns:
        Dictionary mit Suchergebnissen und Preisvergleich
    """
    
    search_service = ThreadWebSearchService()
    
    try:
        # Suche durchführen
        search_results = search_service.search_thread_by_number(
            manufacturer, color_number, color_name
        )
        
        # Preisvergleich erstellen
        price_comparison = search_service.get_price_comparison(
            manufacturer, color_number
        )
        
        return {
            'success': True,
            'search_results': search_results,
            'price_comparison': price_comparison,
            'search_timestamp': datetime.now().isoformat(),
            'query': {
                'manufacturer': manufacturer,
                'color_number': color_number,
                'color_name': color_name
            }
        }
        
    except Exception as e:
        logger.error(f"Garn-Web-Suche fehlgeschlagen: {e}")
        return {
            'success': False,
            'error': str(e),
            'search_timestamp': datetime.now().isoformat(),
            'query': {
                'manufacturer': manufacturer,
                'color_number': color_number,
                'color_name': color_name
            }
        }


def search_low_stock_threads() -> List[Dict]:
    """
    Sucht automatisch nach Garnen mit niedrigem Lagerbestand
    
    Returns:
        Liste von Suchvorschlägen für nachzubestellende Garne
    """
    from src.models import Thread, ThreadStock
    
    search_service = ThreadWebSearchService()
    suggestions = []
    
    try:
        # Garne mit niedrigem Lagerbestand finden
        low_stock_threads = ThreadStock.query.join(Thread).filter(
            ThreadStock.quantity <= ThreadStock.min_stock,
            Thread.active == True
        ).all()
        
        for stock in low_stock_threads:
            thread = stock.thread
            
            # Web-Suche für dieses Garn
            search_result = search_thread_web(
                thread.manufacturer,
                thread.color_number,
                thread.color_name_de
            )
            
            if search_result['success'] and search_result['search_results']:
                suggestions.append({
                    'thread': thread,
                    'current_stock': stock.quantity,
                    'min_stock': stock.min_stock,
                    'search_results': search_result['search_results'][:3],  # Top 3
                    'best_price': search_result['price_comparison'].get('best_price'),
                    'average_price': search_result['price_comparison'].get('average_price')
                })
    
    except Exception as e:
        logger.error(f"Fehler bei Low-Stock-Suche: {e}")
    
    return suggestions
