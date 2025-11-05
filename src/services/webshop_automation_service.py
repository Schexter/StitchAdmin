"""
Webshop-Automatisierungs-Service für Lieferanten
Erstellt von Hans Hahn - Alle Rechte vorbehalten

Dieses Modul bietet:
1. Browser-Automatisierung mit Selenium
2. Automatisches Suchen von Artikeln
3. Warenkorb-Management
4. Automatische Bestellabwicklung
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
import re

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebshopAutomationService:
    """Service für automatisierte Webshop-Bestellungen"""
    
    def __init__(self, headless=True, timeout=30):
        self.timeout = timeout
        self.driver = None
        self.wait = None
        self.headless = headless
        
    def setup_driver(self):
        """Chrome-Driver konfigurieren"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        # Performance-Optimierungen
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-plugins")
        
        # User-Agent setzen
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, self.timeout)
            logger.info("Chrome-Driver erfolgreich gestartet")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Starten des Chrome-Drivers: {e}")
            return False
    
    def close_driver(self):
        """Driver beenden"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.wait = None
            logger.info("Chrome-Driver beendet")
    
    def login_to_webshop(self, url: str, username: str, password: str, shop_type: str = 'generic') -> bool:
        """Login in Webshop durchführen"""
        try:
            self.driver.get(url)
            time.sleep(2)
            
            # Verschiedene Login-Strategien je nach Shop-Typ
            if shop_type == 'shopware':
                return self._login_shopware(username, password)
            elif shop_type == 'woocommerce':
                return self._login_woocommerce(username, password)
            elif shop_type == 'magento':
                return self._login_magento(username, password)
            else:
                return self._login_generic(username, password)
                
        except Exception as e:
            logger.error(f"Login-Fehler: {e}")
            return False
    
    def _login_generic(self, username: str, password: str) -> bool:
        """Generischer Login - versucht verschiedene Standard-Selektoren"""
        login_selectors = [
            "input[name='email']", "input[name='username']", "input[type='email']",
            "#email", "#username", "#user", ".email", ".username"
        ]
        
        password_selectors = [
            "input[name='password']", "input[type='password']",
            "#password", "#pass", ".password"
        ]
        
        submit_selectors = [
            "button[type='submit']", "input[type='submit']",
            ".btn-login", ".login-button", "#login", "[value*='login']", "[value*='Login']"
        ]
        
        try:
            # Username eingeben
            username_field = None
            for selector in login_selectors:
                try:
                    username_field = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    break
                except TimeoutException:
                    continue
            
            if not username_field:
                logger.error("Username-Feld nicht gefunden")
                return False
            
            username_field.clear()
            username_field.send_keys(username)
            
            # Passwort eingeben
            password_field = None
            for selector in password_selectors:
                try:
                    password_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if not password_field:
                logger.error("Passwort-Feld nicht gefunden")
                return False
            
            password_field.clear()
            password_field.send_keys(password)
            
            # Login-Button klicken
            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if submit_button:
                submit_button.click()
            else:
                # Fallback: Enter-Taste
                password_field.send_keys(Keys.RETURN)
            
            # Warten auf Redirect nach Login
            time.sleep(3)
            
            # Prüfen ob Login erfolgreich (URL-Änderung oder bestimmte Elemente)
            current_url = self.driver.current_url
            if 'login' not in current_url.lower() or self._check_login_success():
                logger.info("Login erfolgreich")
                return True
            else:
                logger.error("Login fehlgeschlagen")
                return False
                
        except Exception as e:
            logger.error(f"Generic Login Fehler: {e}")
            return False
    
    def _check_login_success(self) -> bool:
        """Prüft ob Login erfolgreich war"""
        success_indicators = [
            ".user-menu", ".account-menu", ".logout", "[href*='logout']",
            ".my-account", ".dashboard", ".profile"
        ]
        
        for selector in success_indicators:
            try:
                self.driver.find_element(By.CSS_SELECTOR, selector)
                return True
            except NoSuchElementException:
                continue
        return False
    
    def search_and_add_articles(self, articles: List[Dict]) -> Dict:
        """Sucht Artikel und fügt sie zum Warenkorb hinzu"""
        results = {
            'success': [],
            'failed': [],
            'total_added': 0,
            'total_value': 0.0
        }
        
        for article in articles:
            article_number = article.get('article_number') or article.get('supplier_article_number')
            quantity = article.get('quantity', 1)
            
            if not article_number:
                results['failed'].append({
                    'article': article,
                    'reason': 'Keine Artikelnummer vorhanden'
                })
                continue
            
            try:
                # Artikel suchen
                if self._search_article(article_number):
                    # Zum Warenkorb hinzufügen
                    if self._add_to_cart(quantity):
                        results['success'].append({
                            'article': article,
                            'article_number': article_number,
                            'quantity': quantity
                        })
                        results['total_added'] += quantity
                        
                        # Preis extrahieren falls möglich
                        price = self._extract_price()
                        if price:
                            results['total_value'] += price * quantity
                        
                        logger.info(f"Artikel {article_number} erfolgreich hinzugefügt (Menge: {quantity})")
                    else:
                        results['failed'].append({
                            'article': article,
                            'reason': 'Konnte nicht zum Warenkorb hinzugefügt werden'
                        })
                else:
                    results['failed'].append({
                        'article': article,
                        'reason': 'Artikel nicht gefunden'
                    })
                    
            except Exception as e:
                results['failed'].append({
                    'article': article,
                    'reason': f'Fehler: {str(e)}'
                })
                logger.error(f"Fehler bei Artikel {article_number}: {e}")
        
        return results
    
    def _search_article(self, article_number: str) -> bool:
        """Sucht einen Artikel im Webshop"""
        search_selectors = [
            "input[name='search']", "#search", ".search-input",
            "input[type='search']", "[placeholder*='suchen']", "[placeholder*='Suchen']",
            "[placeholder*='search']", "[placeholder*='Search']"
        ]
        
        try:
            # Suchfeld finden
            search_field = None
            for selector in search_selectors:
                try:
                    search_field = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    break
                except TimeoutException:
                    continue
            
            if not search_field:
                logger.error("Suchfeld nicht gefunden")
                return False
            
            # Suche durchführen
            search_field.clear()
            search_field.send_keys(article_number)
            search_field.send_keys(Keys.RETURN)
            
            # Warten auf Suchergebnisse
            time.sleep(2)
            
            # Prüfen ob Artikel gefunden wurde
            return self._check_article_found(article_number)
            
        except Exception as e:
            logger.error(f"Suche fehlgeschlagen: {e}")
            return False
    
    def _check_article_found(self, article_number: str) -> bool:
        """Prüft ob Artikel in Suchergebnissen gefunden wurde"""
        # Verschiedene Strategien um zu prüfen ob Artikel gefunden wurde
        
        # 1. Direkte Artikelnummer im Text
        if article_number.lower() in self.driver.page_source.lower():
            return True
        
        # 2. Produktlinks oder -container
        product_selectors = [
            ".product", ".article", ".item", ".product-item",
            "[data-product]", ".search-result", ".product-box"
        ]
        
        for selector in product_selectors:
            try:
                products = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if products:
                    # Prüfe ersten Treffer
                    first_product = products[0]
                    if article_number.lower() in first_product.text.lower():
                        # Klicke auf ersten Treffer
                        first_product.click()
                        time.sleep(2)
                        return True
            except Exception:
                continue
        
        # 3. "Kein Ergebnis" Texte prüfen
        no_result_texts = ["keine ergebnisse", "no results", "not found", "nichts gefunden"]
        page_text = self.driver.page_source.lower()
        
        for text in no_result_texts:
            if text in page_text:
                return False
        
        # 4. Fallback: Annehmen dass etwas gefunden wurde
        return True
    
    def _add_to_cart(self, quantity: int = 1) -> bool:
        """Fügt Artikel zum Warenkorb hinzu"""
        try:
            # Mengenfeld setzen falls vorhanden
            quantity_selectors = [
                "input[name='quantity']", "#quantity", ".quantity",
                "input[type='number']", "[name*='qty']", "[name*='amount']"
            ]
            
            for selector in quantity_selectors:
                try:
                    qty_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    qty_field.clear()
                    qty_field.send_keys(str(quantity))
                    break
                except NoSuchElementException:
                    continue
            
            # "In den Warenkorb" Button finden und klicken
            cart_selectors = [
                ".add-to-cart", "#add-to-cart", "[name='add-to-cart']",
                "button[type='submit']", ".btn-cart", ".add-cart",
                "[value*='warenkorb']", "[value*='cart']", ".buy-now"
            ]
            
            for selector in cart_selectors:
                try:
                    cart_button = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    cart_button.click()
                    time.sleep(2)
                    return True
                except TimeoutException:
                    continue
            
            logger.error("Warenkorb-Button nicht gefunden")
            return False
            
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen zum Warenkorb: {e}")
            return False
    
    def _extract_price(self) -> Optional[float]:
        """Versucht den Preis des aktuellen Artikels zu extrahieren"""
        price_selectors = [
            ".price", ".product-price", "#price", ".cost",
            "[data-price]", ".amount", ".value"
        ]
        
        for selector in price_selectors:
            try:
                price_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                price_text = price_element.text
                
                # Preis aus Text extrahieren (Regex für deutsche und englische Formate)
                price_match = re.search(r'(\d+[,.]?\d*)', price_text.replace('.', '').replace(',', '.'))
                if price_match:
                    return float(price_match.group(1))
            except Exception:
                continue
        
        return None
    
    def open_cart(self) -> bool:
        """Öffnet den Warenkorb"""
        cart_selectors = [
            ".cart", "#cart", ".warenkorb", ".shopping-cart",
            "[href*='cart']", "[href*='warenkorb']", ".cart-icon"
        ]
        
        for selector in cart_selectors:
            try:
                cart_link = self.driver.find_element(By.CSS_SELECTOR, selector)
                cart_link.click()
                time.sleep(2)
                return True
            except NoSuchElementException:
                continue
        
        return False
    
    def get_cart_summary(self) -> Dict:
        """Gibt eine Zusammenfassung des Warenkorbs zurück"""
        try:
            if not self.open_cart():
                return {'error': 'Warenkorb konnte nicht geöffnet werden'}
            
            # Artikel im Warenkorb zählen
            item_selectors = [
                ".cart-item", ".basket-item", ".product-row",
                ".cart-product", ".order-item"
            ]
            
            total_items = 0
            for selector in item_selectors:
                try:
                    items = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    total_items = len(items)
                    break
                except Exception:
                    continue
            
            # Gesamtpreis extrahieren
            total_selectors = [
                ".total", ".cart-total", ".grand-total",
                "#total", ".sum", ".gesamt"
            ]
            
            total_price = None
            for selector in total_selectors:
                try:
                    total_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    total_text = total_element.text
                    price_match = re.search(r'(\d+[,.]?\d*)', total_text.replace('.', '').replace(',', '.'))
                    if price_match:
                        total_price = float(price_match.group(1))
                        break
                except Exception:
                    continue
            
            return {
                'total_items': total_items,
                'total_price': total_price,
                'cart_url': self.driver.current_url
            }
            
        except Exception as e:
            return {'error': f'Fehler beim Abrufen der Warenkorb-Zusammenfassung: {e}'}
    
    def proceed_to_checkout(self) -> Dict:
        """Geht zur Kasse (ohne zu bestellen)"""
        try:
            checkout_selectors = [
                ".checkout", "#checkout", ".zur-kasse",
                "[href*='checkout']", ".proceed-checkout",
                "button[name='checkout']"
            ]
            
            for selector in checkout_selectors:
                try:
                    checkout_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    checkout_button.click()
                    time.sleep(3)
                    
                    return {
                        'success': True,
                        'checkout_url': self.driver.current_url,
                        'message': 'Erfolgreich zur Kasse weitergeleitet'
                    }
                except NoSuchElementException:
                    continue
            
            return {
                'success': False,
                'message': 'Checkout-Button nicht gefunden'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Fehler beim Checkout: {e}'
            }


def create_automation_session(supplier_data: Dict, order_items: List[Dict], headless: bool = True) -> Dict:
    """
    Erstellt eine automatisierte Webshop-Session
    
    Args:
        supplier_data: Dictionary mit Lieferanten-Daten (webshop_url, credentials, etc.)
        order_items: Liste von Artikeln die bestellt werden sollen
        headless: Ob Browser im Hintergrund laufen soll
    
    Returns:
        Dictionary mit Ergebnissen der Automatisierung
    """
    
    automation = WebshopAutomationService(headless=headless)
    
    try:
        # Driver starten
        if not automation.setup_driver():
            return {
                'success': False,
                'error': 'Chrome-Driver konnte nicht gestartet werden',
                'message': 'Stellen Sie sicher, dass Chrome und ChromeDriver installiert sind'
            }
        
        # Login (falls Credentials vorhanden)
        webshop_url = supplier_data.get('webshop_url')
        username = supplier_data.get('webshop_username')
        password = supplier_data.get('webshop_password')  # Bereits entschlüsselt
        shop_type = supplier_data.get('webshop_type', 'generic')
        
        if not webshop_url:
            return {
                'success': False,
                'error': 'Keine Webshop-URL konfiguriert'
            }
        
        login_success = True
        if username and password:
            login_success = automation.login_to_webshop(webshop_url, username, password, shop_type)
            if not login_success:
                logger.warning("Login fehlgeschlagen, fortfahren ohne Login")
        
        # Artikel suchen und hinzufügen
        search_results = automation.search_and_add_articles(order_items)
        
        # Warenkorb-Zusammenfassung
        cart_summary = automation.get_cart_summary()
        
        # Zur Kasse gehen (aber nicht bestellen)
        checkout_result = automation.proceed_to_checkout()
        
        return {
            'success': True,
            'login_success': login_success,
            'search_results': search_results,
            'cart_summary': cart_summary,
            'checkout_result': checkout_result,
            'browser_url': automation.driver.current_url,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Automation-Fehler: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
    
    finally:
        # Browser offen lassen für manuelle Nachbearbeitung
        # automation.close_driver()
        logger.info("Automation abgeschlossen. Browser bleibt für manuelle Bearbeitung geöffnet.")
