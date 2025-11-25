"""
StitchAdmin 2.0 - Hardware ID Generator
Erstellt von Hans Hahn - Alle Rechte vorbehalten

Generiert eine eindeutige Hardware-ID basierend auf:
- CPU Information
- Motherboard/System UUID
- MAC-Adresse der primären Netzwerkkarte

Die Hardware-ID ist plattformübergreifend (Windows, Mac, Linux) und
sollte bei gleicher Hardware konsistent bleiben.
"""

import hashlib
import logging
import platform
import subprocess
import uuid
from typing import Optional

logger = logging.getLogger(__name__)


class HardwareIDGenerator:
    """
    Generiert eine eindeutige Hardware-ID für Lizenz-Binding.

    Die ID basiert auf mehreren Hardware-Komponenten und wird als
    SHA-256 Hash zurückgegeben.
    """

    @staticmethod
    def get_hardware_id() -> str:
        """
        Generiert die Hardware-ID für das aktuelle System.

        Returns:
            str: 64-Zeichen SHA-256 Hash der Hardware-Komponenten

        Raises:
            RuntimeError: Wenn Hardware-ID nicht generiert werden kann
        """
        try:
            system = platform.system()
            logger.info(f"Generiere Hardware-ID für Plattform: {system}")

            # Collect hardware components
            components = []

            # 1. Get CPU info
            cpu_info = HardwareIDGenerator._get_cpu_info()
            if cpu_info:
                components.append(cpu_info)
                logger.debug(f"CPU Info: {cpu_info[:20]}...")

            # 2. Get system/motherboard UUID
            system_uuid = HardwareIDGenerator._get_system_uuid()
            if system_uuid:
                components.append(system_uuid)
                logger.debug(f"System UUID: {system_uuid}")

            # 3. Get primary MAC address
            mac_address = HardwareIDGenerator._get_mac_address()
            if mac_address:
                components.append(mac_address)
                logger.debug(f"MAC Address: {mac_address}")

            # Ensure we have at least one component
            if not components:
                raise RuntimeError("Keine Hardware-Komponenten gefunden")

            # Combine all components and create hash
            combined = "|".join(components)
            hardware_hash = hashlib.sha256(combined.encode()).hexdigest()

            logger.info(f"Hardware-ID erfolgreich generiert: {hardware_hash[:16]}...")
            return hardware_hash

        except Exception as e:
            logger.error(f"Fehler bei Hardware-ID Generierung: {e}", exc_info=True)
            raise RuntimeError(f"Hardware-ID konnte nicht generiert werden: {e}")

    @staticmethod
    def _get_cpu_info() -> Optional[str]:
        """
        Ermittelt CPU-Informationen plattformabhängig.

        Returns:
            Optional[str]: CPU Identifier oder None bei Fehler
        """
        try:
            system = platform.system()

            if system == "Windows":
                # Windows: Use WMIC to get CPU ProcessorId
                result = subprocess.run(
                    ["wmic", "cpu", "get", "ProcessorId"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        return lines[1].strip()

            elif system == "Darwin":  # macOS
                # macOS: Use sysctl to get CPU brand
                result = subprocess.run(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return result.stdout.strip()

            elif system == "Linux":
                # Linux: Read from /proc/cpuinfo
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if "processor" in line.lower() or "serial" in line.lower():
                            return line.strip()
                        # Also try model name
                        if "model name" in line.lower():
                            return line.split(":")[1].strip()

            # Fallback: Use platform.processor()
            processor = platform.processor()
            if processor:
                return processor

        except Exception as e:
            logger.warning(f"CPU-Info konnte nicht ermittelt werden: {e}")

        return None

    @staticmethod
    def _get_system_uuid() -> Optional[str]:
        """
        Ermittelt System/Motherboard UUID plattformabhängig.

        Returns:
            Optional[str]: System UUID oder None bei Fehler
        """
        try:
            system = platform.system()

            if system == "Windows":
                # Windows: Use WMIC to get UUID
                result = subprocess.run(
                    ["wmic", "csproduct", "get", "UUID"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        return lines[1].strip()

            elif system == "Darwin":  # macOS
                # macOS: Use system_profiler
                result = subprocess.run(
                    ["system_profiler", "SPHardwareDataType"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if "UUID" in line or "Serial" in line:
                            return line.split(":")[1].strip()

            elif system == "Linux":
                # Linux: Try to read machine-id or product_uuid
                try:
                    with open("/etc/machine-id", "r") as f:
                        return f.read().strip()
                except:
                    try:
                        with open("/sys/class/dmi/id/product_uuid", "r") as f:
                            return f.read().strip()
                    except:
                        pass

        except Exception as e:
            logger.warning(f"System-UUID konnte nicht ermittelt werden: {e}")

        return None

    @staticmethod
    def _get_mac_address() -> Optional[str]:
        """
        Ermittelt die MAC-Adresse der primären Netzwerkkarte.

        Returns:
            Optional[str]: MAC-Adresse oder None bei Fehler
        """
        try:
            # Get MAC address using uuid.getnode()
            # This returns the MAC address as an integer
            mac = uuid.getnode()

            # Convert to MAC address format (XX:XX:XX:XX:XX:XX)
            mac_address = ':'.join(('%012X' % mac)[i:i+2] for i in range(0, 12, 2))

            # Validate that it's not a random MAC (getnode() can return random if no real MAC found)
            # Random MACs have the multicast bit set (second char is odd: 2, 6, A, E)
            if mac_address and mac_address[1] not in ['2', '6', 'A', 'E', 'a', 'e']:
                return mac_address

            logger.warning("Keine gültige MAC-Adresse gefunden (möglicherweise zufällig generiert)")
            return None

        except Exception as e:
            logger.warning(f"MAC-Adresse konnte nicht ermittelt werden: {e}")
            return None

    @staticmethod
    def get_hardware_info_display() -> dict:
        """
        Gibt lesbare Hardware-Informationen für Debug/Support zurück.

        Returns:
            dict: Dictionary mit lesbaren Hardware-Informationen
        """
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "processor": platform.processor(),
            "machine": platform.machine(),
            "cpu_info": HardwareIDGenerator._get_cpu_info() or "N/A",
            "system_uuid": HardwareIDGenerator._get_system_uuid() or "N/A",
            "mac_address": HardwareIDGenerator._get_mac_address() or "N/A",
            "hardware_id": HardwareIDGenerator.get_hardware_id()[:16] + "..." if HardwareIDGenerator.get_hardware_id() else "N/A"
        }


# Convenience function for direct usage
def get_hardware_id() -> str:
    """
    Convenience-Funktion zum direkten Abrufen der Hardware-ID.

    Returns:
        str: Hardware-ID als SHA-256 Hash
    """
    return HardwareIDGenerator.get_hardware_id()


if __name__ == "__main__":
    # Test/Debug-Modus
    logging.basicConfig(level=logging.DEBUG)

    print("=" * 60)
    print("StitchAdmin 2.0 - Hardware ID Generator")
    print("=" * 60)

    try:
        hw_id = get_hardware_id()
        print(f"\n✅ Hardware-ID: {hw_id}\n")

        print("Hardware-Informationen:")
        print("-" * 60)
        info = HardwareIDGenerator.get_hardware_info_display()
        for key, value in info.items():
            print(f"{key:20}: {value}")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Fehler: {e}\n")
