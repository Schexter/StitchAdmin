"""
StitchAdmin Logger-System
Zentrales Logging für alle Module
"""
import logging
from datetime import datetime
import os
from typing import Optional

class StitchLogger:
    """Zentraler Logger für StitchAdmin"""
    
    def __init__(self, log_dir: str = "logs"):
        """
        Initialisiert das Logger-System
        
        Args:
            log_dir: Verzeichnis für Log-Dateien
        """
        self.log_dir = log_dir
        self._ensure_log_dir()
        
        # Verschiedene Logger für unterschiedliche Bereiche
        self.error_logger = self._setup_logger(
            'error', 
            os.path.join(self.log_dir, 'error.log'),
            logging.ERROR
        )
        
        self.activity_logger = self._setup_logger(
            'activity',
            os.path.join(self.log_dir, 'activity.log'),
            logging.INFO
        )
        
        self.production_logger = self._setup_logger(
            'production',
            os.path.join(self.log_dir, 'production.log'),
            logging.INFO
        )
        
        self.import_logger = self._setup_logger(
            'import',
            os.path.join(self.log_dir, 'import.log'),
            logging.INFO
        )
        
        self.debug_logger = self._setup_logger(
            'debug',
            os.path.join(self.log_dir, 'debug.log'),
            logging.DEBUG
        )
    
    def _ensure_log_dir(self):
        """Stellt sicher, dass das Log-Verzeichnis existiert"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def _setup_logger(self, name: str, log_file: str, level: int) -> logging.Logger:
        """
        Erstellt und konfiguriert einen Logger
        
        Args:
            name: Name des Loggers
            log_file: Pfad zur Log-Datei
            level: Logging-Level
            
        Returns:
            Konfigurierter Logger
        """
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        handler = logging.FileHandler(log_file, encoding='utf-8')
        handler.setFormatter(formatter)
        
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.addHandler(handler)
        
        # Auch auf Konsole ausgeben für Entwicklung
        if os.environ.get('DEBUG', 'False').lower() == 'true':
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        return logger
    
    def log_error(self, message: str, exception: Optional[Exception] = None, 
                  module: str = "general"):
        """
        Protokolliert einen Fehler
        
        Args:
            message: Fehlerbeschreibung
            exception: Optional - Die aufgetretene Exception
            module: Modul, in dem der Fehler auftrat
        """
        error_msg = f"[{module}] {message}"
        if exception:
            error_msg += f" | Exception: {type(exception).__name__}: {str(exception)}"
        self.error_logger.error(error_msg)
    
    def log_activity(self, user: str, action: str, details: str = "", 
                     result: str = "success"):
        """
        Protokolliert eine Benutzeraktivität
        
        Args:
            user: Benutzername
            action: Durchgeführte Aktion
            details: Zusätzliche Details
            result: Ergebnis der Aktion (success/failure)
        """
        activity_msg = f"User: {user} | Action: {action} | Result: {result}"
        if details:
            activity_msg += f" | Details: {details}"
        self.activity_logger.info(activity_msg)
    
    def log_production(self, order_id: str, status: str, 
                       machine: str = "", details: str = ""):
        """
        Protokolliert Produktionsaktivitäten
        
        Args:
            order_id: Auftragsnummer
            status: Produktionsstatus
            machine: Maschinenbezeichnung
            details: Zusätzliche Details
        """
        production_msg = f"Order: {order_id} | Status: {status}"
        if machine:
            production_msg += f" | Machine: {machine}"
        if details:
            production_msg += f" | Details: {details}"
        self.production_logger.info(production_msg)
    
    def log_import(self, source: str, record_count: int, 
                   success_count: int, error_count: int, 
                   details: str = ""):
        """
        Protokolliert Import-Vorgänge
        
        Args:
            source: Importquelle (z.B. "Excel", "L-Shop")
            record_count: Anzahl der Datensätze
            success_count: Erfolgreich importierte Datensätze
            error_count: Fehlgeschlagene Datensätze
            details: Zusätzliche Details
        """
        import_msg = (f"Source: {source} | Total: {record_count} | "
                     f"Success: {success_count} | Errors: {error_count}")
        if details:
            import_msg += f" | Details: {details}"
        self.import_logger.info(import_msg)
    
    def log_debug(self, message: str, module: str = "general"):
        """
        Protokolliert Debug-Informationen
        
        Args:
            message: Debug-Nachricht
            module: Modul, aus dem die Nachricht stammt
        """
        debug_msg = f"[{module}] {message}"
        self.debug_logger.debug(debug_msg)
    
    def get_recent_errors(self, count: int = 10) -> list:
        """
        Gibt die letzten Fehler zurück
        
        Args:
            count: Anzahl der zurückzugebenden Fehler
            
        Returns:
            Liste der letzten Fehlereinträge
        """
        error_file = os.path.join(self.log_dir, 'error.log')
        if not os.path.exists(error_file):
            return []
        
        with open(error_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            return lines[-count:] if len(lines) >= count else lines
    
    def clear_old_logs(self, days: int = 30):
        """
        Löscht alte Log-Einträge
        
        Args:
            days: Logs älter als diese Anzahl von Tagen werden gelöscht
        """
        # TODO: Implementierung für das Löschen alter Logs
        pass

# Globale Logger-Instanz
logger = StitchLogger()

# Convenience-Funktionen für einfachen Zugriff
log_error = logger.log_error
log_activity = logger.log_activity
log_production = logger.log_production
log_import = logger.log_import
log_debug = logger.log_debug
