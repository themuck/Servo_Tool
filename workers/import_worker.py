import json
from PyQt5.QtCore import QThread, pyqtSignal
from logger_config import logger


class ImportWorker(QThread):
    """Worker-Klasse für asynchronen Import von Registern"""
    finished = pyqtSignal(dict, str)  # import_data, file_path
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.file_path = None
    
    def run(self):
        """Führt den Import in einem separaten Thread durch"""
        try:
            with open(self.file_path, 'r') as f:
                import_data = json.load(f)
            
            self.finished.emit(import_data, self.file_path)
            
        except FileNotFoundError:
            error_msg = f"Fehler: Datei nicht gefunden: {self.file_path}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
        except json.JSONDecodeError as e:
            error_msg = f"Fehler: Ungültiges JSON-Format: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
        except Exception as e:
            error_msg = f"Fehler beim Lesen der Datei: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)