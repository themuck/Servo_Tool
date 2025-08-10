import sys, json, csv, math, random, os
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QTabWidget, QAction, QMessageBox, QFileDialog, QComboBox, QHBoxLayout
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from collections import deque
from parameter_manager import ParameterManager
from modbus_client import ServoModbusClient
from ui_tabs.connection_tab import ConnectionTab
from ui_tabs.fault_list_tab import FaultListTab
from ui_tabs.io_status_tab import IOStatusTab
from ui_tabs.register_tab import RegisterTab
from ui_tabs.tuning_tab import TuningTab
from ui_tabs.vdi_vdo_tab import VDIVDOTab
from language_manager import LanguageManager
from workers.export_worker import ExportWorker
from workers.plot_data_worker import PlotDataWorker
from workers.import_worker import ImportWorker
from utils.modbus_helpers import ModbusHelper, UIHelper
from utils.io_helpers import IOHelper
from custom_exceptions import (
    ModbusConnectionException,
    ModbusReadException,
    ModbusWriteException,
    ModbusTimeoutException,
    ParameterValidationException,
    FileOperationException,
    ConfigurationException
)
from logger_config import logger


def resource_path(relative_path):
    """Holt den absoluten Pfad zur Ressource, funktioniert für Entwicklung und PyInstaller"""
    try:
        # PyInstaller erstellt einen temporären Ordner und speichert den Pfad in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)




def setup_high_dpi():
    """Setup High-DPI support - MUST be called before QApplication!"""
    # Enable High DPI display with PyQt5
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # For PyQt 5.14+ - better scaling control
    if hasattr(QApplication, 'setHighDpiScaleFactorRoundingPolicy'):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    
    # Alternative: Set environment variables (can be used instead of attributes)
    # os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    # os.environ["QT_SCALE_FACTOR"] = "1"  # or "1.5", "2" for manual scaling

class AppConfig:
    """Konfigurationsklasse für Anwendungseinstellungen"""
    DEFAULT_WINDOW_SIZE = (1400, 900)
    IO_TIMER_INTERVAL = 1000
    BASE_FONT_SIZE = 9
    MAX_DPI_SCALE = 1.5
    MIN_FONT_SIZE = 8


class ServoTuningApp(QMainWindow):
    
    def __init__(self):
        super().__init__()
        
        # Initialize language manager
        self.language_manager = LanguageManager()
        
        # Setup High-DPI scaling for this window
        self.setup_for_high_dpi()
        
        # Initialize components
        self.parameter_manager = ParameterManager()
        self.parameter_manager.load_parameters()
        self.modbus_client = ServoModbusClient()
        
        # Load configuration data
        self.fault_data = self._load_json_data("servo_faults.json")
        self.pxx_mapping = self._load_json_data("servo_parameters_mapping.json")
        
        # Initialize state
        self.simulation_mode = False
        self.simulation_time = 0
        
        # Setup IO timer (bleibt unverändert)
        self.io_timer = QTimer(self)
        self.io_timer.setInterval(AppConfig.IO_TIMER_INTERVAL)
        self.io_timer.timeout.connect(self.update_io_status)
        
        # Setup separaten Timer für VDO-Polling auf der Tuning-Seite
        self.vdo_polling_timer = QTimer(self)
        self.vdo_polling_timer.setInterval(AppConfig.IO_TIMER_INTERVAL)
        self.vdo_polling_timer.timeout.connect(self.update_vdo_polling)
        
        # Setup plot worker thread (ersetzt den Timer)
        self.plot_worker = PlotDataWorker(self.modbus_client, self.parameter_manager, self)
        self.plot_worker.data_updated.connect(self.update_plot_with_data)
        self.plot_worker.watchdog_triggered.connect(self.handle_plot_worker_watchdog)
        
        # Initialize worker threads
        self.export_worker = None
        self.import_worker = None
        
        # Initialize UI
        self.init_ui()
        
        # Set window title using language manager
        self.update_window_title()

    def is_connected(self):
        """Prüft, ob eine Verbindung besteht oder der Simulationsmodus aktiv ist"""
        return self.modbus_client.connected or self.simulation_mode

    def _handle_io_function(self, function_type, operation="read"):
        """Allgemeine Methode für IO-Funktionsoperationen"""
        if not self.io_helper:
            logger.warning(f"IO-Helper nicht verfügbar für {function_type}-{operation}")
            return
        
        method_name = f"{operation}_{function_type}_functions"
        if hasattr(self.io_helper, method_name):
            getattr(self.io_helper, method_name)()
            logger.debug(f"{operation}_{function_type}_functions erfolgreich ausgeführt")
        else:
            logger.error(f"Methode {method_name} nicht im IO-Helper gefunden")

    def _save_checkbox_states(self):
        """Speichert den aktuellen Zustand der Checkboxen"""
        checkbox_states = {}
        for code, line in self.tuning_tab.lines.items():
            checkbox_states[code] = line.isVisible()
        logger.debug(f"Checkbox-Zustände gespeichert: {len(checkbox_states)} Einträge")
        return checkbox_states

    def _restore_checkbox_states(self, checkbox_states):
        """Stellt die Checkbox-Zustände wieder her"""
        for code, is_visible in checkbox_states.items():
            if code in self.tuning_tab.lines:
                self.tuning_tab.lines[code].setVisible(is_visible)
                # Aktualisiere auch die Checkbox in der UI
                for i in range(self.tuning_tab.legend_layout.count()):
                    item = self.tuning_tab.legend_layout.itemAt(i)
                    if item.widget():
                        checkbox = item.widget()
                        if checkbox.text() == self.tuning_tab.lines[code].name():
                            checkbox.setChecked(is_visible)
                            break
        logger.debug("Checkbox-Zustände wiederhergestellt")

    def _update_visible_lines_in_worker(self):
        """Aktualisiert die Liste der sichtbaren Linien im Worker"""
        if self.plot_worker.isRunning():
            visible_lines = []
            for code, line in self.tuning_tab.lines.items():
                if line.isVisible():
                    visible_lines.append(code)
            self.plot_worker.update_visible_lines(visible_lines)
            logger.debug(f"Sichtbare Linien im Worker aktualisiert: {len(visible_lines)} Linien")

    def setup_for_high_dpi(self):
        """Configure window and fonts for high-DPI displays"""
        screen = QApplication.primaryScreen()
        if screen:
            # Calculate DPI ratio (96 DPI = standard reference)
            dpi_ratio = screen.logicalDotsPerInch() / 96.0
            
            # Scale window size (but limit maximum scaling to prevent huge windows)
            effective_scale = min(dpi_ratio, AppConfig.MAX_DPI_SCALE)
            
            scaled_width = int(AppConfig.DEFAULT_WINDOW_SIZE[0] * effective_scale)
            scaled_height = int(AppConfig.DEFAULT_WINDOW_SIZE[1] * effective_scale)
            
            self.setGeometry(100, 100, scaled_width, scaled_height)
            
            # Scale font size
            scaled_font_size = max(int(AppConfig.BASE_FONT_SIZE * dpi_ratio), AppConfig.MIN_FONT_SIZE)
            font = QFont()
            font.setPointSize(scaled_font_size)
            self.setFont(font)
            
            logger.info(f"High-DPI Setup: DPI ratio = {dpi_ratio:.2f}, Window size = {scaled_width}x{scaled_height}, Font size = {scaled_font_size}pt")

    def _load_json_data(self, filename):
        """Load JSON data with proper error handling"""
        try:
            file_path = resource_path(filename)
            with open(file_path, mode='r', encoding='utf-8') as file:
                data = json.load(file)
                logger.info(f"{filename.replace('.json', '')} loaded successfully from {filename}")
                return data
        except FileNotFoundError:
            logger.error(f"Error: {filename} not found.")
            return {} if 'mapping' in filename else []
        except json.JSONDecodeError as e:
            logger.error(f"Error: {filename} could not be decoded: {e}")
            return {} if 'mapping' in filename else []

    def init_ui(self):
        """Initialize the user interface"""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Status label
        self.status_label = QLabel(self.language_manager.get_text("status_app_started"))
        
        # Create menu and tabs
        self.create_menu_bar()
        self.tabs = QTabWidget()
        self.create_tabs()
        
        # Add widgets to layout
        self.main_layout.addWidget(self.tabs)
        self.main_layout.addWidget(self.status_label)
        
        # Initialize IO helper after tabs are created
        try:
            self.io_helper = IOHelper(self.parameter_manager, self.modbus_client, self.io_tab, self.vdi_vdo_tab, self.status_label, self.tuning_tab)
            logger.info(f"io_helper initialisiert: {self.io_helper is not None}")
            logger.debug(f"io_helper ID nach Initialisierung: {id(self.io_helper)}")
        except Exception as e:
            logger.error(f"Fehler bei der Initialisierung des IO-Helpers: {e}")
            self.io_helper = None
            QMessageBox.critical(self, "Fehler", f"IO-Helper konnte nicht initialisiert werden: {e}")

    def create_menu_bar(self):
        """Create the application menu bar"""
        menubar = self.menuBar()
        file_menu = menubar.addMenu(self.language_manager.get_text("menu_file"))
        
        # Export action
        self.export_action = QAction(self.language_manager.get_text("menu_export_registers"), self)
        self.export_action.triggered.connect(self.export_all_registers)
        self.export_action.setEnabled(False)
        file_menu.addAction(self.export_action)

        # Import action
        self.import_action = QAction(self.language_manager.get_text("menu_import_registers"), self)
        self.import_action.triggered.connect(self.import_all_registers)
        self.import_action.setEnabled(True)  # Import should always be enabled
        file_menu.addAction(self.import_action)
        
        # Add language selection to menu bar
        language_label = QLabel(self.language_manager.get_text("language_label") + ":")
        self.language_combo = QComboBox()
        
        # Add supported languages
        supported_languages = self.language_manager.get_language_names()
        for lang_code, lang_name in supported_languages.items():
            self.language_combo.addItem(lang_name, lang_code)
        
        # Set current language
        current_lang = self.language_manager.current_language
        index = self.language_combo.findData(current_lang)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)
        
        # Connect signal
        self.language_combo.currentIndexChanged.connect(self.change_language)
        
        # Add language selection to menu bar (right aligned)
        language_widget = QWidget()
        language_layout = QHBoxLayout(language_widget)
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.language_combo)
        language_layout.setContentsMargins(0, 0, 10, 0)  # Add some padding on the right
        menubar.setCornerWidget(language_widget)

    def create_tabs(self):
        """Create and setup all tabs"""
        # Initialize tab objects
        self.tuning_tab = TuningTab(self)
        self.io_tab = IOStatusTab(self, self.language_manager)
        self.vdi_vdo_tab = VDIVDOTab(self, self.language_manager)
        self.register_tab = RegisterTab(self.parameter_manager, self.modbus_client, self)
        self.fault_tab = FaultListTab(self.fault_data, self)
        self.connection_tab = ConnectionTab(self)
        
        # Add tabs to widget
        tabs_config = {
            self.language_manager.get_text("tab_tuning_plot"): self.tuning_tab,
            self.language_manager.get_text("tab_io_status"): self.io_tab,
            self.language_manager.get_text("tab_vdi_vdo"): self.vdi_vdo_tab,
            self.language_manager.get_text("tab_register_overview"): self.register_tab,
            self.language_manager.get_text("tab_fault_list"): self.fault_tab,
            self.language_manager.get_text("tab_modbus_connection"): self.connection_tab
        }
        
        for name, tab in tabs_config.items():
            self.tabs.addTab(tab, name)

        # Connect signals
        self.tuning_tab.plot_control_signal.connect(self.handle_plot_control)
        self.io_tab.polling_checkbox.stateChanged.connect(self.toggle_io_polling)
        self.vdi_vdo_tab.polling_checkbox.stateChanged.connect(self.toggle_io_polling)
        self.vdi_vdo_tab.vdi_toggled.connect(self.handle_vdi_toggle)
        self.tuning_tab.vdi_toggled.connect(self.handle_vdi_toggle)
        self.tuning_tab.vdo_polling_toggled.connect(self.handle_vdo_polling_toggle)
        self.connection_tab.connect_button.clicked.connect(self.toggle_connection)
        self._connect_tuning_signals()
        
        # Synchronisiere die Polling-Checkboxen
        self.io_tab.polling_checkbox.stateChanged.connect(self.sync_polling_checkboxes)
        self.vdi_vdo_tab.polling_checkbox.stateChanged.connect(self.sync_polling_checkboxes)
        
        # Verbinde das Tab-Wechsel-Signal
        self.tabs.currentChanged.connect(self.on_tab_changed)

    def _connect_tuning_signals(self):
        """Connect all tuning-related signals"""
        # Connect parameter widgets
        for widgets in self.tuning_tab.tuning_widgets.values():
            p, w, r, w_btn, t = widgets.values()
            if t == "combobox":
                r.clicked.connect(lambda _, p=p, w=w: self.read_parameter_combobox(p, w))
                w_btn.clicked.connect(lambda _, p=p, w=w: self.write_parameter_combobox(p, w))
            else:
                r.clicked.connect(lambda _, p=p, w=w: self.read_parameter(p, w))
                w_btn.clicked.connect(lambda _, p=p, w=w: self.write_parameter(p, w))
        
        # Connect direct command widgets
        for widgets in self.tuning_tab.direct_cmd_widgets.values():
            widgets["send_btn"].clicked.connect(
                lambda _, p=widgets["param"], w=widgets["widget"]: 
                self.write_parameter_and_start_plot(p, w)
            )
        
        # Connect stop button
        self.tuning_tab.stop_all_btn.clicked.connect(self.send_zero_commands_and_start_plot)
    
    def handle_plot_control(self, action):
        """Handle plot control actions"""
        if action == "start":
            if self.is_connected() and not self.plot_worker.isRunning():
                # Aktualisiere die Liste der sichtbaren Linien
                visible_lines = []
                for code, line in self.tuning_tab.lines.items():
                    if line.isVisible():
                        visible_lines.append(code)
                self.plot_worker.update_visible_lines(visible_lines)
                
                self.plot_worker.start()
                self.status_label.setText("Plot gestartet.")
        elif action == "stop":
            if self.plot_worker.isRunning():
                self.plot_worker.stop()
                self.status_label.setText("Plot gestoppt.")
        elif action == "clear":
            if self.plot_worker.isRunning():
                self.plot_worker.stop()
            self.tuning_tab.clear_plot(stopped_by_user=True)
            self.status_label.setText("Plot gelöscht.")
        # "apply_settings" wurde entfernt, da die Plot-Einstellungen jetzt automatisch übernommen werden

    def toggle_connection(self):
        """Toggle connection state"""
        if self.is_connected():
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        """Establish connection (real or simulation)"""
        self.simulation_mode = self.connection_tab.simulation_checkbox.isChecked()
        
        # Setze den Simulationsmodus im Plot-Worker
        self.plot_worker.set_simulation_mode(self.simulation_mode)
        
        if self.simulation_mode:
            is_connected = True
            logger.info("Simulationsmodus aktiviert")
        else:
            try:
                connection_params = self.connection_tab.get_connection_parameters()
                # Timeouts konfigurieren, falls in den Verbindungseinstellungen angegeben
                if 'timeout' in connection_params:
                    self.modbus_client.set_timeouts(default_timeout=connection_params['timeout'])
                
                is_connected = self.modbus_client.connect(**connection_params)
                if is_connected:
                    logger.log_modbus_connection(connection_params.get('host', 'unbekannt'), True)
                else:
                    logger.log_modbus_connection(connection_params.get('host', 'unbekannt'), False, "Unbekannter Fehler")
            except ModbusConnectionException as e:
                logger.log_modbus_connection(connection_params.get('host', 'unbekannt'), False, str(e))
                self.status_label.setText(f"Verbindungsfehler: {str(e)}")
                self._disconnect()
                return
            except ModbusTimeoutException as e:
                logger.log_timeout("Verbindung", connection_params.get('host', 'unbekannt'), connection_params.get('timeout', 0))
                self.status_label.setText(f"Timeout bei Verbindung: {str(e)}")
                self._disconnect()
                return
            except Exception as e:
                logger.error(f"Unerwarteter Fehler bei Verbindung: {e}")
                self.status_label.setText(f"Unerwarteter Fehler bei Verbindung: {str(e)}")
                self._disconnect()
                return
        
        if is_connected:
            status_msg = "Simulationsmodus gestartet." if self.simulation_mode else "Verbindung erfolgreich."
            self.status_label.setText(status_msg)
            self.set_ui_connected_state(True)
        else:
            self.status_label.setText("Verbindung fehlgeschlagen.")
            self._disconnect()
            
    def _disconnect(self):
        """Disconnect and cleanup"""
        # Stop plot worker and IO timer
        if self.plot_worker.isRunning():
            self.plot_worker.stop()
        if self.io_timer.isActive():
            self.io_timer.stop()
        if self.vdo_polling_timer.isActive():
            self.vdo_polling_timer.stop()
        
        # Always attempt to disconnect the client if it exists,
        # as a port might be open even if our logical connection failed.
        if self.modbus_client.client:
            self.modbus_client.disconnect()
             
        # Reset state
        self.simulation_mode = False
        self.simulation_time = 0
        
        # Setze den Simulationsmodus im Plot-Worker zurück
        self.plot_worker.set_simulation_mode(False)
        
        # Setze die Flags für das Lesen der Funktionen zurück
        if self.io_helper:
            self.io_helper.reset_function_flags()
        
        self.set_ui_connected_state(False)
        self.status_label.setText("Verbindung getrennt.")

    def set_ui_connected_state(self, connected):
        """Update UI elements based on connection state"""
        self.tuning_tab.set_enabled(connected)
        self.io_tab.set_enabled(connected)
        self.vdi_vdo_tab.set_enabled(connected)
        self.register_tab.set_enabled(connected)
        self.connection_tab.set_connected_state(connected)
        
        # Export is only possible with a real connection
        self.export_action.setEnabled(connected and not self.simulation_mode)
        
        # Stop worker and timer if disconnecting
        if not connected:
            if self.plot_worker.isRunning():
                self.plot_worker.stop()
            if self.io_timer.isActive():
                self.io_timer.stop()
            if self.vdo_polling_timer.isActive():
                self.vdo_polling_timer.stop()

    def apply_plot_settings(self):
        """Apply new plot settings"""
        try:
            time_window = self.tuning_tab.get_plot_settings()
            logger.debug(f"Eingelesener Wert - Zeitfenster: {time_window}s")
            
            # Speichere Checkbox-Zustände
            checkbox_states = self._save_checkbox_states()
            
            # Plot neu zeichnen
            self.tuning_tab.clear_plot(stopped_by_user=False)
            
            # Stelle Checkbox-Zustände wieder her
            self._restore_checkbox_states(checkbox_states)
            
            # Aktualisiere die Legende
            self.tuning_tab.plot_widget.getPlotItem().legend.update()
            
            # Aktualisiere sichtbare Linien im Worker
            self._update_visible_lines_in_worker()
            
            self.status_label.setText(f"Plot-Einstellungen aktualisiert: Zeitfenster {time_window} Sekunden.")
        except (ValueError, TypeError) as e:
            logger.error(f"Fehler beim Anwenden der Plot-Einstellungen: {e}")
            self.status_label.setText("Fehler: Zeitfenster ungültig.")

    def update_io_status(self):
        """Update I/O status display using IO helper"""
        logger.debug("update_io_status aufgerufen")
        logger.debug(f"io_helper ist: {self.io_helper}")
        
        if self.io_helper and self.is_io_tab_active():
            logger.debug("io_helper existiert und IO-Tab ist aktiv, rufe update_io_status auf")
            logger.debug(f"io_helper ID in update_io_status: {id(self.io_helper)}")
            self.io_helper.update_io_status(self.simulation_mode)
        else:
            logger.warning("io_helper existiert nicht oder IO-Tab ist nicht aktiv")
    
    def _simulate_io_functions(self):
        """Simuliert IO-Funktionen für den Simulationsmodus"""
        self._handle_io_function("io", "simulate")
    
    def _simulate_vdi_vdo_functions(self):
        """Simuliert VDI/VDO-Funktionen für den Simulationsmodus"""
        self._handle_io_function("vdi_vdo", "simulate")
    
    def _read_io_functions(self):
        """Liest die IO-Funktionszuweisungen aus dem Servo aus"""
        self._handle_io_function("io", "read")
    
    def _read_vdi_vdo_functions(self):
        """Liest die VDI/VDO-Funktionszuweisungen aus dem Servo aus"""
        self._handle_io_function("vdi_vdo", "read")
    
    def _get_function_name(self, function_value, io_type):
        """Holt den Funktionsnamen basierend auf dem Funktionswert und IO-Typ"""
        if self.io_helper:
            return self.io_helper.get_function_name(function_value, io_type)
        return "Nicht zugewiesen"
    
    def handle_vdi_toggle(self, vdi_number, state):
        """Wird aufgerufen, wenn ein VDI-Toggle-Button geklickt wird"""
        if self.io_helper:
            self.io_helper.handle_vdi_toggle(vdi_number, state, self.simulation_mode, self._disconnect)
    
    def handle_vdo_polling_toggle(self, enabled):
        """Wird aufgerufen, wenn die VDO-Polling-Checkbox umgeschaltet wird"""
        logger.debug(f"VDO-Polling umgeschaltet: {enabled}")
        
        # Starte oder stoppe den VDO-Polling-Timer basierend auf dem Checkbox-Zustand
        if enabled and self.is_connected():
            logger.debug("VDO-Polling aktiviert, starte VDO-Polling-Timer")
            # Aktualisiere die VDOs sofort
            if self.io_helper:
                try:
                    # Lese VDO-Daten direkt, aber aktualisiere nicht den VDI/VDO-Tab
                    self.io_helper._read_vdo_status(update_vdi_vdo_tab=False)
                    # Hole die VDO-Daten und aktualisiere die Labels
                    vdo_data = self.io_helper.get_vdo_data()
                    if vdo_data is not None:
                        self.tuning_tab.update_vdo_labels(vdo_data)
                        logger.debug("VDO-Labels sofort aktualisiert")
                except Exception as e:
                    logger.error(f"Fehler beim sofortigen Aktualisieren der VDOs: {e}")
            # Starte den VDO-Polling-Timer
            self.vdo_polling_timer.start()
        else:
            logger.debug("VDO-Polling deaktiviert, stoppe VDO-Polling-Timer")
            self.vdo_polling_timer.stop()

    def update_vdo_polling(self):
        """Aktualisiert VDO-Daten für das VDO-Polling auf der Tuning-Seite"""
        logger.debug("update_vdo_polling aufgerufen")
        
        if self.io_helper and hasattr(self.tuning_tab, 'is_vdo_polling_enabled') and self.tuning_tab.is_vdo_polling_enabled():
            logger.debug("VDO-Polling ist aktiv, lese VDO-Daten")
            try:
                # Lese nur VDO-Daten, um Modbus-Traffic zu minimieren, aber aktualisiere nicht den VDI/VDO-Tab
                self.io_helper._read_vdo_status(update_vdi_vdo_tab=False)
                
                # Aktualisiere die VDO-Labels im Tuning-Tab
                vdo_data = self.io_helper.get_vdo_data()
                if vdo_data is not None:
                    self.tuning_tab.update_vdo_labels(vdo_data)
                    logger.debug("VDO-Labels im Tuning-Tab aktualisiert")
            except Exception as e:
                logger.error(f"Fehler beim Lesen der VDO-Daten: {e}")
    
    def update_plot_with_data(self, values):
        """Aktualisiert den Plot mit den vom Worker-Thread erhaltenen Daten"""
        # Die Simulationsdaten werden jetzt direkt im PlotDataWorker generiert
        # und hier nur noch an den Plot weitergegeben
        try:
            self.tuning_tab.update_plot(values)
            QApplication.processEvents()  # Halte die GUI responsive
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Plots: {e}")
            # Nicht kritisch, fahre mit der nächsten Aktualisierung fort
    
    def handle_plot_worker_watchdog(self, message):
        """Handles watchdog events from the plot worker."""
        logger.warning(f"Plot Worker Watchdog: {message}")
        
        # Zeige die Nachricht in der Statusleiste an
        if hasattr(self, 'status_label'):
            self.status_label.setText(f"Plot Worker: {message}")
        
        # Bei schweren Fehlern, versuche den Worker neu zu starten
        if "Neustart erforderlich" in message or "zu viele Fehler" in message.lower():
            logger.info("Versuche Plot Worker neu zu starten...")
            try:
                # Stoppe den aktuellen Worker
                if hasattr(self, 'plot_worker') and self.plot_worker.isRunning():
                    self.plot_worker.stop()
                    self.plot_worker.wait(1000)  # Warte bis zu 1 Sekunde
                
                # Erstelle einen neuen Worker
                self.plot_worker = PlotDataWorker(self.modbus_client, self.parameter_manager, self)
                self.plot_worker.data_updated.connect(self.update_plot_with_data)
                self.plot_worker.watchdog_triggered.connect(self.handle_plot_worker_watchdog)
                
                # Starte den neuen Worker
                self.plot_worker.start()
                
                logger.info("Plot Worker erfolgreich neu gestartet")
                if hasattr(self, 'status_label'):
                    self.status_label.setText("Plot Worker neu gestartet")
            except Exception as e:
                logger.error(f"Fehler beim Neustart des Plot Workers: {e}", exc_info=True)
                if hasattr(self, 'status_label'):
                    self.status_label.setText(f"Fehler beim Neustart: {str(e)}")

    def sync_polling_checkboxes(self, state):
        """Synchronisiert die Polling-Checkboxen zwischen IO-Status-Tab und VDI/VDO-Tab"""
        # Verhindere Rekursion durch Blockieren der Signale während der Synchronisation
        self.io_tab.polling_checkbox.blockSignals(True)
        self.vdi_vdo_tab.polling_checkbox.blockSignals(True)
        
        try:
            # Setze beide Checkboxen auf den gleichen Zustand
            self.io_tab.polling_checkbox.setChecked(state == Qt.Checked)
            self.vdi_vdo_tab.polling_checkbox.setChecked(state == Qt.Checked)
        finally:
            # Reaktiviere die Signale
            self.io_tab.polling_checkbox.blockSignals(False)
            self.vdi_vdo_tab.polling_checkbox.blockSignals(False)

    def toggle_io_polling(self, state):
        """Toggle I/O polling based on checkbox state"""
        logger.debug(f"toggle_io_polling aufgerufen mit state={state}, Qt.Checked={Qt.Checked}")
        logger.debug(f"Verbunden: {self.modbus_client.connected}, Simulationsmodus: {self.simulation_mode}")
        
        if state == Qt.Checked and self.is_connected() and self.is_io_tab_active():
            logger.debug("Starte IO-Timer und IO-Tab ist aktiv")
            # Lese die Funktionen einmal beim Aktivieren des Pollings
            if self.io_helper:
                self.io_helper.read_functions_once(self.simulation_mode)
            self.io_timer.start()
        else:
            logger.debug("Stoppe IO-Timer oder IO-Tab ist nicht aktiv")
            self.io_timer.stop()
            # Setze die Flags für das Lesen der Funktionen zurück, wenn das Polling deaktiviert wird
            if self.io_helper:
                self.io_helper.reset_function_flags()
    
    def is_io_tab_active(self):
        """Prüft, ob einer der IO-Status-Tabs aktiv ist"""
        current_tab = self.tabs.currentWidget()
        return current_tab == self.io_tab or current_tab == self.vdi_vdo_tab
    
    def on_tab_changed(self, index):
        """Wird aufgerufen, wenn der Tab gewechselt wird"""
        current_tab = self.tabs.widget(index)
        is_io_tab = current_tab == self.io_tab or current_tab == self.vdi_vdo_tab
        
        # Wenn zu einem IO-Tab gewechselt wird und die Polling-Checkbox aktiv ist, starte das Polling
        if is_io_tab and (self.io_tab.polling_checkbox.isChecked() or self.vdi_vdo_tab.polling_checkbox.isChecked()):
            if not self.io_timer.isActive() and self.is_connected():
                logger.debug("Tab zu IO-Status gewechselt, starte IO-Timer")
                self.io_timer.start()
        # Wenn von einem IO-Tab weg gewechselt wird, stoppe das Polling
        elif not is_io_tab and self.io_timer.isActive():
            logger.debug("Tab von IO-Status weg gewechselt, stoppe IO-Timer")
            self.io_timer.stop()
    
    def read_parameter(self, p, w):
        """Read a parameter and update widget"""
        ModbusHelper.read_parameter(self.modbus_client, p, w, self.status_label, self._disconnect)

    def write_parameter(self, p, w):
        """Write a parameter from widget value"""
        try:
            value_to_write = float(w.text())
            if not self._validate_parameter(p, value_to_write):
                return  # Stop if validation fails
            ModbusHelper.write_parameter(self.modbus_client, p, int(value_to_write), self.status_label, self._disconnect)
        except ValueError:
            self.status_label.setText("Fehler: Ungültiger Wert für Eingabe.")

    def read_parameter_combobox(self, p, w):
        """Read parameter for combobox widget"""
        ModbusHelper.read_parameter_combobox(self.modbus_client, p, w, self.status_label, self._disconnect)

    def write_parameter_combobox(self, p, w):
        """Write parameter from combobox widget"""
        value_to_write = w.currentData()
        display_text = w.currentText()
        ModbusHelper.write_parameter(self.modbus_client, p, int(value_to_write), self.status_label, self._disconnect, display_text)
    
    def write_parameter_and_start_plot(self, p, w):
        """Write parameter and start plot if successful"""
        self.write_parameter(p, w)
        # Check if write was successful before starting plot by checking status
        if "erfolgreich" in self.status_label.text():
            self.handle_plot_control("start")

    def send_zero_commands(self):
        """Send zero to all direct command widgets"""
        for w in self.tuning_tab.direct_cmd_widgets.values():
            w["widget"].setText("0")
            self.write_parameter(w["param"], w["widget"])

    def send_zero_commands_and_start_plot(self):
        """Send zero commands and start plot"""
        self.send_zero_commands()
        self.handle_plot_control("start")

    def export_all_registers(self):
        """Export all registers to JSON file using worker thread"""
        if not self.modbus_client.connected:
            self.status_label.setText("Export fehlgeschlagen: Keine Verbindung.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Register exportieren", "", "JSON-Dateien (*.json)")
        if not path:
            return

        # Create and start worker thread
        self.export_worker = ExportWorker(self.modbus_client, self.parameter_manager)
        self.export_worker.file_path = path
        
        # Connect signals
        self.export_worker.progress_updated.connect(self._on_export_progress)
        self.export_worker.finished.connect(self._on_export_finished)
        self.export_worker.error_occurred.connect(self._on_export_error)
        
        # Start the worker thread
        self.export_worker.start()
        self.status_label.setText("Exportiere alle Register... Bitte warten.")
    
    def _on_export_progress(self, current, total, parameter_name):
        """Handler for export progress updates"""
        self.status_label.setText(f"Lese Parameter {current}/{total}: {parameter_name}")
        QApplication.processEvents()  # Keep UI responsive
    
    def _on_export_finished(self, export_data, file_path):
        """Handler for export completion"""
        try:
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=4)
            logger.log_file_operation("Export", file_path, True)
            self.status_label.setText(f"Alle {len(export_data)} Register erfolgreich exportiert nach {file_path}")
        except Exception as e:
            logger.log_file_operation("Export", file_path, False, str(e))
            self.status_label.setText(f"Fehler beim Speichern der Datei: {e}")
        finally:
            self.export_worker = None
    
    def _on_export_error(self, error_message):
        """Handler for export errors"""
        self.status_label.setText(error_message)
        if "Verbindungsfehler" in error_message:
            self._disconnect()
        self.export_worker = None

    def import_all_registers(self):
        """Import registers from JSON file using worker thread"""
        path, _ = QFileDialog.getOpenFileName(self, "Register importieren", "", "JSON-Dateien (*.json)")
        if not path:
            return

        # Create and start worker thread
        self.import_worker = ImportWorker()
        self.import_worker.file_path = path
        
        # Connect signals
        self.import_worker.finished.connect(self._on_import_finished)
        self.import_worker.error_occurred.connect(self._on_import_error)
        
        # Start the worker thread
        self.import_worker.start()
        self.status_label.setText("Lese Importdatei... Bitte warten.")
    
    def _on_import_finished(self, import_data, file_path):
        """Handler for import completion"""
        # Switch to the register tab and display the data
        self.tabs.setCurrentWidget(self.register_tab)
        self.register_tab.display_imported_data(import_data)
        self.status_label.setText(f"{len(import_data)} Register aus Datei geladen. Zum Schreiben auf 'Geänderte Parameter schreiben' klicken.")
        self.import_worker = None
    
    def _on_import_error(self, error_message):
        """Handler for import errors"""
        self.status_label.setText(error_message)
        self.import_worker = None

    def _validate_parameter(self, param, value):
        """Validate parameter value against defined rules"""
        if not param.validation:
            return True  # No validation rules, so it's valid

        v_type = param.validation.get('type')
        if v_type == 'range':
            min_val = param.validation.get('min', -math.inf)
            max_val = param.validation.get('max', math.inf)
            if not (min_val <= value <= max_val):
                error_msg = f"Wert {value} für {param.code} ist außerhalb des Bereichs [{min_val}, {max_val}]."
                logger.log_parameter_validation(param.code, value, False, min_val, max_val)
                self.status_label.setText(f"Fehler: {error_msg}")
                return False
        
        # 'enum' is handled by QComboBox, no runtime check needed here for now
        # but could be added if direct text entry were possible.
        
        return True
    
    def change_language(self, index):
        """Change the application language"""
        lang_code = self.language_combo.itemData(index)
        if lang_code and lang_code != self.language_manager.current_language:
            self.language_manager.set_language(lang_code)
            self.update_ui_language()
    
    def update_ui_language(self):
        """Update all UI elements with the new language"""
        UIHelper.update_ui_language(self, self.language_manager)
    
    def update_window_title(self):
        """Update the window title based on current language"""
        self.setWindowTitle(self.language_manager.get_text("app_title"))
    
    def get_reference_maps(self):
        """Get reference maps for options - used by ParameterDelegate"""
        return {
            "servo_FunIN.json": self.parameter_manager.fun_in_map,
            "servo_FunOUT.json": self.parameter_manager.fun_out_map
        }


if __name__ == "__main__":
    # CRITICAL: Setup High-DPI support BEFORE creating QApplication
    setup_high_dpi()
    
    app = QApplication(sys.argv)
    
    # Optional: Print DPI information for debugging
    screen = app.primaryScreen()
    if screen:
        logger.info(f"Screen DPI: {screen.logicalDotsPerInch()}")
        logger.info(f"Device Pixel Ratio: {screen.devicePixelRatio()}")
        logger.info(f"Screen Size: {screen.size().width()}x{screen.size().height()}")
    
    window = ServoTuningApp()
    window.show()
    sys.exit(app.exec_())