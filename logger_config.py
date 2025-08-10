"""
Zentrale Konfiguration für das Logging-System der Servo-Steuerungsanwendung.
Stellt konsistente Fehlermeldungen und Logging-Funktionalität bereit.
"""

import logging
import os
from datetime import datetime
from typing import Optional

class ServoLogger:
    """Zentrale Logging-Klasse für die Servo-Steuerungsanwendung."""
    
    def __init__(self, log_level: str = "DEBUG", log_to_file: bool = True, log_dir: str = "logs"):
        """
        Initialisiert das Logging-System.
        
        Args:
            log_level: Logging-Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_to_file: Wenn True, wird auch in eine Datei geloggt
            log_dir: Verzeichnis für Log-Dateien
        """
        self.log_level = log_level
        self.log_to_file = log_to_file
        self.log_dir = log_dir
        
        # Logger erstellen
        self.logger = logging.getLogger("ServoTool")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Verhindern, dass mehrere Handler hinzugefügt werden
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Richtet die Handler für das Logging ein."""
        # Formatter für konsistente Ausgabe
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)  # Ändere zu DEBUG, um alle Debug-Meldungen anzuzeigen
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File Handler, wenn gewünscht
        if self.log_to_file:
            # Log-Verzeichnis erstellen, falls nicht vorhanden
            os.makedirs(self.log_dir, exist_ok=True)
            
            # Log-Datei mit aktuellem Datum
            log_filename = os.path.join(
                self.log_dir, 
                f"servo_tool_{datetime.now().strftime('%Y%m%d')}.log"
            )
            
            file_handler = logging.FileHandler(log_filename, encoding='utf-8')
            file_handler.setLevel(getattr(logging, self.log_level.upper()))
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def debug(self, message: str, **kwargs):
        """Loggt eine Debug-Nachricht."""
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Loggt eine Info-Nachricht."""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Loggt eine Warnung."""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Loggt eine Fehlermeldung."""
        self.logger.error(message, exc_info=True, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Loggt eine kritische Fehlermeldung."""
        self.logger.critical(message, **kwargs)
    
    def log_modbus_connection(self, port: str, success: bool, error_msg: Optional[str] = None):
        """Loggt Modbus-Verbindungsversuche."""
        if success:
            self.info(f"Modbus-Verbindung erfolgreich hergestellt zu {port}")
        else:
            self.error(f"Modbus-Verbindung fehlgeschlagen zu {port}: {error_msg}")
    
    def log_modbus_operation(self, operation: str, address: int, success: bool, 
                            value=None, error_msg: Optional[str] = None):
        """Loggt Modbus-Lese-/Schreiboperationen."""
        if success:
            if value is not None:
                self.info(f"Modbus-{operation} erfolgreich: Adresse {address}, Wert {value}")
            else:
                self.info(f"Modbus-{operation} erfolgreich: Adresse {address}")
        else:
            self.error(f"Modbus-{operation} fehlgeschlagen: Adresse {address}, Fehler: {error_msg}")
    
    def log_timeout(self, operation: str, address: int, timeout_duration: float):
        """Loggt Timeout-Fehler."""
        self.warning(f"Timeout bei {operation}: Adresse {address} nach {timeout_duration}s")
    
    def log_parameter_validation(self, parameter: str, value: float, valid: bool, 
                                 min_val=None, max_val=None):
        """Loggt Parameter-Validierungen."""
        if valid:
            self.debug(f"Parameter-Validierung erfolgreich: {parameter}={value}")
        else:
            self.error(f"Parameter-Validierung fehlgeschlagen: {parameter}={value} "
                      f"(Bereich: [{min_val}, {max_val}])")
    
    def log_file_operation(self, operation: str, filename: str, success: bool, 
                          error_msg: Optional[str] = None):
        """Loggt Dateioperationen."""
        if success:
            self.info(f"Datei-{operation} erfolgreich: {filename}")
        else:
            self.error(f"Datei-{operation} fehlgeschlagen: {filename}, Fehler: {error_msg}")
    
    def log_general_error(self, message: str):
        """Loggt allgemeine Fehlermeldungen."""
        self.error(message)


# Globale Logger-Instanz
logger = ServoLogger()