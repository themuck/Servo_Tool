import sys
import os
import json
from PyQt5.QtCore import QThread, pyqtSignal
from custom_exceptions import (
    ModbusConnectionException,
    ModbusReadException,
    ModbusTimeoutException
)
from logger_config import logger


class ExportWorker(QThread):
    """Worker-Klasse für asynchronen Export von Registern"""
    progress_updated = pyqtSignal(int, int, str)  # current, total, parameter_name
    finished = pyqtSignal(dict, str)  # export_data, file_path
    error_occurred = pyqtSignal(str)
    
    def __init__(self, modbus_client, parameter_manager):
        super().__init__()
        self.modbus_client = modbus_client
        self.parameter_manager = parameter_manager
        self.file_path = None
        self.is_running = True
    
    def run(self):
        """Führt den Export in einem separaten Thread durch"""
        try:
            if not self.modbus_client.connected:
                self.error_occurred.emit("Export fehlgeschlagen: Keine Verbindung.")
                return
                
            all_params = self.parameter_manager.get_all_parameters_raw()
            export_data = {}
            total_params = len(all_params)
            
            for i, param_info in enumerate(all_params):
                if not self.is_running:
                    self.error_occurred.emit("Export abgebrochen.")
                    return
                    
                self.progress_updated.emit(i + 1, total_params, param_info.get('code', ''))
                
                try:
                    addr = int(param_info.get('decimal')) - 1
                    val = self.modbus_client.read_holding_register(addr, count=1)
                    if val is not None:
                        export_data[param_info.get('code')] = val[0]
                except (ValueError, TypeError):
                    continue  # Skip if address is invalid
                except ModbusTimeoutException as e:
                    logger.warning(f"Timeout beim Lesen von {param_info.get('code', 'unbekannt')}: {e}")
                    continue  # Skip this parameter and continue with next
                except ModbusReadException as e:
                    logger.warning(f"Fehler beim Lesen von {param_info.get('code', 'unbekannt')}: {e}")
                    continue  # Skip this parameter and continue with next
                except ModbusConnectionException as e:
                    logger.error(f"Verbindungsfehler beim Lesen von {param_info.get('code', 'unbekannt')}: {e}")
                    self.error_occurred.emit("Verbindungsfehler beim Export - Export abgebrochen")
                    return
            
            self.finished.emit(export_data, self.file_path)
            
        except Exception as e:
            logger.error(f"Unerwarteter Fehler beim Export: {e}")
            self.error_occurred.emit(f"Unerwarteter Fehler beim Export: {e}")
    
    def stop(self):
        """Stoppt den Export-Vorgang"""
        self.is_running = False