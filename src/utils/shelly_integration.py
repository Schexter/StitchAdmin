"""
Shelly Smart Home Integration
Ermöglicht Energie-Tracking und Steuerung von Maschinen über Shelly-Geräte
"""

import requests
import socket
from typing import List, Dict, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ShellyDevice:
    """Repräsentiert ein Shelly-Gerät"""

    def __init__(self, ip: str, device_type: str = None):
        self.ip = ip
        self.device_type = device_type
        self.base_url = f"http://{ip}"

    def get_status(self) -> Dict:
        """Holt aktuellen Status des Geräts"""
        try:
            response = requests.get(f"{self.base_url}/status", timeout=2)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Fehler beim Abrufen des Status von {self.ip}: {e}")
        return {}

    def get_settings(self) -> Dict:
        """Holt Geräte-Einstellungen"""
        try:
            response = requests.get(f"{self.base_url}/settings", timeout=2)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Einstellungen von {self.ip}: {e}")
        return {}

    def turn_on(self, channel: int = 0) -> bool:
        """Schaltet Gerät ein"""
        try:
            response = requests.get(
                f"{self.base_url}/relay/{channel}",
                params={'turn': 'on'},
                timeout=2
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Fehler beim Einschalten von {self.ip}: {e}")
            return False

    def turn_off(self, channel: int = 0) -> bool:
        """Schaltet Gerät aus"""
        try:
            response = requests.get(
                f"{self.base_url}/relay/{channel}",
                params={'turn': 'off'},
                timeout=2
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Fehler beim Ausschalten von {self.ip}: {e}")
            return False

    def toggle(self, channel: int = 0) -> bool:
        """Schaltet Gerät um (Toggle)"""
        try:
            response = requests.get(
                f"{self.base_url}/relay/{channel}",
                params={'turn': 'toggle'},
                timeout=2
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Fehler beim Toggle von {self.ip}: {e}")
            return False

    def get_power_data(self, channel: int = 0) -> Dict:
        """
        Holt Energie-Daten (Leistung, Spannung, Strom)

        Returns:
            Dict mit:
            - power: Aktuelle Leistung in Watt
            - voltage: Spannung in Volt
            - current: Strom in Ampere
            - pf: Leistungsfaktor
            - energy: Verbrauchte Energie in Wh
            - is_on: Schaltzustand
        """
        try:
            status = self.get_status()

            # Shelly Plus/Pro Geräte (Gen 2)
            if 'switch:0' in status:
                switch_data = status.get(f'switch:{channel}', {})
                return {
                    'power': switch_data.get('apower', 0),  # Aktive Leistung
                    'voltage': switch_data.get('voltage', 0),
                    'current': switch_data.get('current', 0),
                    'pf': switch_data.get('pf', 0),
                    'energy': switch_data.get('aenergy', {}).get('total', 0) / 1000,  # Wh
                    'is_on': switch_data.get('output', False),
                    'temperature': switch_data.get('temperature', {}).get('tC', 0)
                }

            # Shelly Gen 1 Geräte (z.B. Shelly Plug, 1PM)
            elif 'meters' in status:
                meter_data = status.get('meters', [{}])[channel]
                relay_data = status.get('relays', [{}])[channel]
                return {
                    'power': meter_data.get('power', 0),
                    'voltage': meter_data.get('voltage', 0),
                    'current': meter_data.get('current', 0),
                    'pf': meter_data.get('pf', 0),
                    'energy': meter_data.get('total', 0) / 60,  # Watt-Minuten zu Wh
                    'is_on': relay_data.get('ison', False),
                    'temperature': status.get('temperature', 0)
                }

            # Shelly EM (Energie-Monitor ohne Schaltfunktion)
            elif 'emeters' in status:
                emeter_data = status.get('emeters', [{}])[channel]
                return {
                    'power': emeter_data.get('power', 0),
                    'voltage': emeter_data.get('voltage', 0),
                    'current': emeter_data.get('current', 0),
                    'pf': emeter_data.get('pf', 0),
                    'energy': emeter_data.get('total', 0) / 60,
                    'is_on': None,  # Kein Relay
                    'temperature': 0
                }

            return {}

        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Energie-Daten von {self.ip}: {e}")
            return {}

    def get_device_info(self) -> Dict:
        """Holt Geräte-Informationen"""
        try:
            # Shelly API - /shelly Endpoint
            response = requests.get(f"{self.base_url}/shelly", timeout=2)
            if response.status_code == 200:
                data = response.json()
                return {
                    'type': data.get('type', 'Unknown'),
                    'mac': data.get('mac', ''),
                    'auth': data.get('auth', False),
                    'fw': data.get('fw', ''),
                    'name': data.get('name', ''),
                    'discoverable': data.get('discoverable', True)
                }
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Geräte-Info von {self.ip}: {e}")
        return {}


class ShellyScanner:
    """Scannt das Netzwerk nach Shelly-Geräten"""

    @staticmethod
    def scan_network(network_prefix: str = "192.168.1") -> List[ShellyDevice]:
        """
        Scannt Netzwerk nach Shelly-Geräten

        Args:
            network_prefix: Netzwerk-Präfix (z.B. "192.168.1" für 192.168.1.0/24)

        Returns:
            Liste gefundener ShellyDevice-Objekte
        """
        found_devices = []
        logger.info(f"Starte Netzwerk-Scan für Shelly-Geräte im Netzwerk {network_prefix}.0/24")

        # Scanne IP-Bereich
        for i in range(1, 255):
            ip = f"{network_prefix}.{i}"

            try:
                # Versuche HTTP-Verbindung zum Shelly API
                response = requests.get(f"http://{ip}/shelly", timeout=0.5)

                if response.status_code == 200:
                    data = response.json()
                    device_type = data.get('type', 'Unknown')

                    # Prüfe ob es ein Shelly-Gerät ist
                    if 'shelly' in device_type.lower() or data.get('mac', '').startswith(''):
                        device = ShellyDevice(ip, device_type)
                        found_devices.append(device)
                        logger.info(f"Shelly-Gerät gefunden: {ip} - {device_type}")

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                # Keine Antwort, kein Shelly-Gerät
                pass
            except Exception as e:
                logger.debug(f"Fehler beim Scannen von {ip}: {e}")

        logger.info(f"Scan abgeschlossen. {len(found_devices)} Shelly-Geräte gefunden.")
        return found_devices

    @staticmethod
    def scan_mdns() -> List[Dict]:
        """
        Scannt nach Shelly-Geräten via mDNS/Zeroconf
        (Schneller und zuverlässiger als IP-Scan)

        Benötigt: pip install zeroconf
        """
        try:
            from zeroconf import Zeroconf, ServiceBrowser, ServiceListener

            class ShellyListener(ServiceListener):
                def __init__(self):
                    self.devices = []

                def add_service(self, zeroconf, service_type, name):
                    info = zeroconf.get_service_info(service_type, name)
                    if info:
                        # Extrahiere IP-Adresse
                        addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
                        if addresses:
                            self.devices.append({
                                'name': name,
                                'ip': addresses[0],
                                'port': info.port,
                                'type': service_type
                            })

            zeroconf = Zeroconf()
            listener = ShellyListener()

            # Suche nach Shelly HTTP Services
            ServiceBrowser(zeroconf, "_http._tcp.local.", listener)

            # Warte kurz auf Responses
            import time
            time.sleep(3)

            zeroconf.close()

            # Filtere Shelly-Geräte
            shelly_devices = [d for d in listener.devices if 'shelly' in d['name'].lower()]

            return shelly_devices

        except ImportError:
            logger.warning("zeroconf nicht installiert. Verwende IP-Scan.")
            return []
        except Exception as e:
            logger.error(f"mDNS Scan fehlgeschlagen: {e}")
            return []


class ShellyEnergyTracker:
    """Trackt Energie-Verbrauch von Shelly-Geräten"""

    def __init__(self, device: ShellyDevice):
        self.device = device
        self.readings = []

    def record_reading(self) -> Dict:
        """Zeichnet aktuelle Messung auf"""
        power_data = self.device.get_power_data()

        if power_data:
            reading = {
                'timestamp': datetime.now(),
                'power': power_data.get('power', 0),
                'energy': power_data.get('energy', 0),
                'is_on': power_data.get('is_on', False),
                'voltage': power_data.get('voltage', 0),
                'current': power_data.get('current', 0)
            }

            self.readings.append(reading)
            return reading

        return {}

    def calculate_cost(self, electricity_price_per_kwh: float = 0.30) -> Dict:
        """
        Berechnet Kosten basierend auf aufgezeichneten Messwerten

        Args:
            electricity_price_per_kwh: Strompreis in €/kWh (Standard: 30 Cent)

        Returns:
            Dict mit Kosten-Analyse
        """
        if not self.readings:
            return {'total_cost': 0, 'total_kwh': 0}

        # Berechne Gesamtenergie (wenn kontinuierlich getrackt)
        if len(self.readings) > 1:
            # Trapez-Regel für Integration
            total_wh = 0
            for i in range(1, len(self.readings)):
                dt = (self.readings[i]['timestamp'] - self.readings[i-1]['timestamp']).total_seconds() / 3600  # Stunden
                avg_power = (self.readings[i]['power'] + self.readings[i-1]['power']) / 2
                total_wh += avg_power * dt

            total_kwh = total_wh / 1000
        else:
            # Einzelmessung - verwende energy Counter
            total_kwh = self.readings[-1]['energy'] / 1000

        total_cost = total_kwh * electricity_price_per_kwh

        return {
            'total_kwh': round(total_kwh, 3),
            'total_cost': round(total_cost, 2),
            'avg_power': round(sum(r['power'] for r in self.readings) / len(self.readings), 1),
            'max_power': max(r['power'] for r in self.readings),
            'runtime_hours': (self.readings[-1]['timestamp'] - self.readings[0]['timestamp']).total_seconds() / 3600,
            'electricity_price': electricity_price_per_kwh
        }
