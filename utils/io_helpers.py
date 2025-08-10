import random
from PyQt5.QtWidgets import QApplication
from custom_exceptions import (
    ModbusConnectionException,
    ModbusReadException,
    ModbusTimeoutException
)
from logger_config import logger
from .modbus_helpers import ModbusHelper, UIHelper


class IOHelper:
    """Hilfsklasse für IO-Status-Operationen"""
    
    def __init__(self, parameter_manager, modbus_client, io_tab, vdi_vdo_tab, status_label, tuning_tab=None):
        self.parameter_manager = parameter_manager
        self.modbus_client = modbus_client
        self.io_tab = io_tab
        self.vdi_vdo_tab = vdi_vdo_tab
        self.tuning_tab = tuning_tab
        self.status_label = status_label
        
        # Timeout-Zähler für verschiedene IO-Typen
        self.timeout_counters = {
            'di': 0,
            'do': 0,
            'vdi': 0,
            'vdo': 0
        }
        
        # Lesefehler-Zähler für verschiedene IO-Typen
        self.read_error_counters = {
            'di': 0,
            'do': 0,
            'vdi': 0,
            'vdo': 0
        }
        
        # Flags, um zu überprüfen, ob die Funktionen bereits gelesen wurden
        self.io_functions_read = False
        self.vdi_vdo_functions_read = False
        
        # Speichert die aktuellen VDO-Daten für den Tuning-Tab
        self.current_vdo_data = None
    
    def update_io_status(self, simulation_mode=False):
        """Update I/O status display"""
        UIHelper.keep_ui_responsive()
        
        if simulation_mode:
            self._simulate_io_status()
            return
        
        if self.modbus_client.connected:
            self._read_di_status()
            self._read_do_status()
            self._read_vdi_status()
            self._read_vdo_status(update_vdi_vdo_tab=True)
    
    def read_functions_once(self, simulation_mode=False):
        """Liest die IO- und VDI/VDO-Funktionen einmalig beim Aktivieren des Pollings"""
        UIHelper.keep_ui_responsive()
        
        if simulation_mode:
            self._simulate_io_functions()
            self._simulate_vdi_vdo_functions()
            return
        
        if self.modbus_client.connected:
            # Lese die IO-Funktionen nur einmal aus
            if not self.io_functions_read:
                try:
                    self._read_io_functions()
                    self.io_functions_read = True
                    UIHelper.keep_ui_responsive()
                except Exception as e:
                    logger.error(f"Fehler beim Lesen der IO-Funktionen: {e}")
            
            # Lese die VDI/VDO-Funktionen nur einmal aus
            if not self.vdi_vdo_functions_read:
                try:
                    self._read_vdi_vdo_functions()
                    self.vdi_vdo_functions_read = True
                    UIHelper.keep_ui_responsive()
                except Exception as e:
                    logger.error(f"Fehler beim Lesen der VDI/VDO-Funktionen: {e}")
    
    def _simulate_io_status(self):
        """Simuliert IO-Status für den Simulationsmodus"""
        self.io_tab.set_di_labels(random.randint(0, 65535))
        UIHelper.keep_ui_responsive()
        
        self.io_tab.set_do_labels(random.randint(0, 65535))
        UIHelper.keep_ui_responsive()
        
        # Simuliere auch VDI/VDO
        vdi_value = random.randint(0, 65535)
        self.vdi_vdo_tab.set_vdi_labels(vdi_value)
        
        # Aktualisiere auch die VDI-Buttons im Tuning-Tab, falls vorhanden
        if self.tuning_tab and hasattr(self.tuning_tab, 'update_vdi_buttons'):
            self.tuning_tab.update_vdi_buttons(vdi_value)
        
        UIHelper.keep_ui_responsive()
        
        vdo_sim_value = random.randint(0, 65535)
        # Im Simulationsmodus immer die VDO-Labels im VDI/VDO-Tab aktualisieren
        self.vdi_vdo_tab.set_vdo_labels(vdo_sim_value)
        
        # Speichere die VDO-Daten für den Tuning-Tab auch im Simulationsmodus
        self.current_vdo_data = vdo_sim_value
        
        UIHelper.keep_ui_responsive()
        
        # Simuliere auch IO-Funktionen
        self._simulate_io_functions()
        UIHelper.keep_ui_responsive()
        
        self._simulate_vdi_vdo_functions()
    
    def _read_di_status(self):
        """Liest den DI-Status"""
        di_param = self.parameter_manager.get_parameter("P0B-03")
        if not di_param or not di_param.decimal:
            return
        
        try:
            val_di = self.modbus_client.read_holding_register(int(di_param.decimal), count=1)
            if val_di:
                print(f"DI-Status gelesen: {val_di[0]} (binär: {bin(val_di[0])})")
                self.io_tab.set_di_labels(val_di[0])
                UIHelper.keep_ui_responsive()
                # Zähler zurücksetzen bei erfolgreicher Operation
                self.timeout_counters['di'] = 0
                self.read_error_counters['di'] = 0
        except ModbusTimeoutException as e:
            self._handle_io_error('di', 'DI', e, 'Timeout')
        except ModbusReadException as e:
            self._handle_io_error('di', 'DI', e, 'Lesefehler')
        except ModbusConnectionException as e:
            logger.error(f"Verbindungsfehler beim Lesen von DI: {e}")
            self.status_label.setText(f"Verbindungsfehler bei I/O-Status: {str(e)}")
            return  # Wichtig: Hier zurückkehren, um weitere Abfragen zu vermeiden
        except Exception as e:
            logger.error(f"Unerwarteter Fehler beim Lesen von DI: {e}")
    
    def _read_do_status(self):
        """Liest den DO-Status"""
        do_param = self.parameter_manager.get_parameter("P0B-05")
        if not do_param or not do_param.decimal:
            return
        
        try:
            val_do = self.modbus_client.read_holding_register(int(do_param.decimal), count=1)
            if val_do:
                print(f"DO-Status gelesen: {val_do[0]} (binär: {bin(val_do[0])})")
                self.io_tab.set_do_labels(val_do[0])
                UIHelper.keep_ui_responsive()
                # Zähler zurücksetzen bei erfolgreicher Operation
                self.timeout_counters['do'] = 0
                self.read_error_counters['do'] = 0
        except ModbusTimeoutException as e:
            self._handle_io_error('do', 'DO', e, 'Timeout')
        except ModbusReadException as e:
            self._handle_io_error('do', 'DO', e, 'Lesefehler')
        except ModbusConnectionException as e:
            logger.error(f"Verbindungsfehler beim Lesen von DO: {e}")
            self.status_label.setText(f"Verbindungsfehler bei I/O-Status: {str(e)}")
            return  # Wichtig: Hier zurückkehren, um weitere Abfragen zu vermeiden
        except Exception as e:
            logger.error(f"Unerwarteter Fehler beim Lesen von DO: {e}")
    
    def _read_vdi_status(self):
        """Liest den VDI-Status"""
        vdi_param = self.parameter_manager.get_parameter("P31-00")
        if not vdi_param or not vdi_param.decimal:
            return
        
        try:
            val_vdi = self.modbus_client.read_holding_register(int(vdi_param.decimal), count=1)
            if val_vdi:
                print(f"VDI-Status gelesen: {val_vdi[0]} (binär: {bin(val_vdi[0])})")
                self.vdi_vdo_tab.set_vdi_labels(val_vdi[0])
                
                # Aktualisiere auch die VDI-Buttons im Tuning-Tab, falls vorhanden
                if self.tuning_tab and hasattr(self.tuning_tab, 'update_vdi_buttons'):
                    self.tuning_tab.update_vdi_buttons(val_vdi[0])
                
                UIHelper.keep_ui_responsive()
                # Zähler zurücksetzen bei erfolgreicher Operation
                self.timeout_counters['vdi'] = 0
                self.read_error_counters['vdi'] = 0
        except ModbusTimeoutException as e:
            self._handle_io_error('vdi', 'VDI', e, 'Timeout')
        except ModbusReadException as e:
            self._handle_io_error('vdi', 'VDI', e, 'Lesefehler')
        except ModbusConnectionException as e:
            logger.error(f"Verbindungsfehler beim Lesen von VDI: {e}")
            self.status_label.setText(f"Verbindungsfehler bei I/O-Status: {str(e)}")
            return  # Wichtig: Hier zurückkehren, um weitere Abfragen zu vermeiden
        except Exception as e:
            logger.error(f"Unerwarteter Fehler beim Lesen von VDI: {e}")
    
    def _read_vdo_status(self, update_vdi_vdo_tab=True):
        """Liest den VDO-Status
        
        Args:
            update_vdi_vdo_tab (bool): Wenn True, werden die VDO-Labels im VDI/VDO-Tab aktualisiert.
                                      Wenn False, werden die Daten nur für den Tuning-Tab gespeichert.
        """
        vdo_param = self.parameter_manager.get_parameter("P17-32")
        if not vdo_param or not vdo_param.decimal:
            return
        
        try:
            val_vdo = self.modbus_client.read_holding_register(int(vdo_param.decimal), count=1)
            if val_vdo:
                print(f"VDO-Status gelesen: {val_vdo[0]} (binär: {bin(val_vdo[0])})")
                
                # Aktualisiere die VDO-Labels im VDI/VDO-Tab nur, wenn gewünscht
                if update_vdi_vdo_tab:
                    self.vdi_vdo_tab.set_vdo_labels(val_vdo[0])
                
                # Speichere die VDO-Daten für den Tuning-Tab
                self.current_vdo_data = val_vdo[0]
                
                UIHelper.keep_ui_responsive()
                # Zähler zurücksetzen bei erfolgreicher Operation
                self.timeout_counters['vdo'] = 0
                self.read_error_counters['vdo'] = 0
        except ModbusTimeoutException as e:
            self._handle_io_error('vdo', 'VDO', e, 'Timeout')
        except ModbusReadException as e:
            self._handle_io_error('vdo', 'VDO', e, 'Lesefehler')
        except ModbusConnectionException as e:
            logger.error(f"Verbindungsfehler beim Lesen von VDO: {e}")
            self.status_label.setText(f"Verbindungsfehler bei I/O-Status: {str(e)}")
            return  # Wichtig: Hier zurückkehren, um weitere Abfragen zu vermeiden
        except Exception as e:
            logger.error(f"Unerwarteter Fehler beim Lesen von VDO: {e}")
    
    def _handle_io_error(self, io_type, io_name, exception, error_type):
        """Behandelt IO-Fehler mit Zähler und Deaktivierung bei zu vielen Fehlern"""
        logger.error(f"{error_type} beim Lesen von {io_name}: {exception}")
        
        if error_type == "Timeout":
            self.timeout_counters[io_type] += 1
            if self.timeout_counters[io_type] >= 5:  # Nach 5 aufeinanderfolgenden Timeouts
                self.status_label.setText(f"Zu viele {io_name}-Timeouts - deaktiviere Live-Updates")
                self._disable_io_polling()
                self.timeout_counters[io_type] = 0
        else:  # Lesefehler
            self.read_error_counters[io_type] += 1
            if self.read_error_counters[io_type] >= 5:  # Nach 5 aufeinanderfolgenden Lesefehlern
                self.status_label.setText(f"Zu viele {io_name}-Lesefehler - deaktiviere Live-Updates")
                self._disable_io_polling()
                self.read_error_counters[io_type] = 0
    
    def _disable_io_polling(self):
        """Deaktiviert das IO-Polling in beiden Tabs"""
        self.io_tab.polling_checkbox.setChecked(False)
        self.vdi_vdo_tab.polling_checkbox.setChecked(False)
        # Der Timer wird in der Hauptklasse gestoppt
    
    def reset_function_flags(self):
        """Setzt die Flags für das Lesen der Funktionen zurück"""
        self.io_functions_read = False
        self.vdi_vdo_functions_read = False
        self.current_vdo_data = None
    
    def _simulate_io_functions(self):
        """Simuliert IO-Funktionen für den Simulationsmodus"""
        # Erstelle zufällige Funktionsbeschreibungen für die Simulation
        di_functions = []
        do_functions = []
        
        # Verfügbare Funktionen für DI
        di_fun_options = list(self.parameter_manager.fun_in_map.keys())
        # Verfügbare Funktionen für DO
        do_fun_options = list(self.parameter_manager.fun_out_map.keys())
        
        for i in range(16):
            # Simuliere, dass einige IOs nicht zugewiesen sind (Wert 0)
            if i == 0:  # I1 nicht zugewiesen
                di_functions.append("Nicht zugewiesen")
            elif i < len(di_fun_options):
                fun_key = di_fun_options[i % len(di_fun_options)]
                di_functions.append(self.parameter_manager.fun_in_map[fun_key].get('name', f'DI{i+1}'))
            else:
                di_functions.append(f'DI{i+1}')
                
            if i == 0:  # O1 nicht zugewiesen
                do_functions.append("Nicht zugewiesen")
            elif i < len(do_fun_options):
                fun_key = do_fun_options[i % len(do_fun_options)]
                do_functions.append(self.parameter_manager.fun_out_map[fun_key].get('name', f'DO{i+1}'))
            else:
                do_functions.append(f'DO{i+1}')
        
        self.io_tab.set_di_functions(di_functions)
        self.io_tab.set_do_functions(do_functions)
        
        # Erstelle Funktionsdetails für die Legende
        di_function_details = []
        do_function_details = []
        
        for i in range(16):
            if i < len(di_functions) and di_functions[i] not in ["Nicht zugewiesen", "Nicht verfügbar", "Fehler", "0"]:
                function_details = self._find_function_details(di_functions[i], "fun_in_map")
                di_function_details.append(function_details)
            else:
                di_function_details.append(None)
            
            if i < len(do_functions) and do_functions[i] not in ["Nicht zugewiesen", "Nicht verfügbar", "Fehler", "0"]:
                function_details = self._find_function_details(do_functions[i], "fun_out_map")
                do_function_details.append(function_details)
            else:
                do_function_details.append(None)
        
        # Aktualisiere die Legende mit den zugewiesenen Funktionen und Details
        self.io_tab.update_di_legend(di_functions, di_function_details)
        self.io_tab.update_do_legend(do_functions, do_function_details)
    
    def _simulate_vdi_vdo_functions(self):
        """Simuliert VDI/VDO-Funktionen für den Simulationsmodus"""
        # Erstelle zufällige Funktionsbeschreibungen für die Simulation
        vdi_functions = []
        vdo_functions = []
        
        # Verfügbare Funktionen für VDI
        vdi_fun_options = list(self.parameter_manager.fun_in_map.keys())
        # Verfügbare Funktionen für VDO
        vdo_fun_options = list(self.parameter_manager.fun_out_map.keys())
        
        for i in range(16):
            # Simuliere, dass einige VIOs nicht zugewiesen sind (Wert 0)
            if i == 0:  # VDI1 nicht zugewiesen
                vdi_functions.append("Nicht zugewiesen")
            elif i < len(vdi_fun_options):
                fun_key = vdi_fun_options[i % len(vdi_fun_options)]
                vdi_functions.append(self.parameter_manager.fun_in_map[fun_key].get('name', f'VDI{i+1}'))
            else:
                vdi_functions.append(f'VDI{i+1}')
                
            if i == 0:  # VDO1 nicht zugewiesen
                vdo_functions.append("Nicht zugewiesen")
            elif i < len(vdo_fun_options):
                fun_key = vdo_fun_options[i % len(vdo_fun_options)]
                vdo_functions.append(self.parameter_manager.fun_out_map[fun_key].get('name', f'VDO{i+1}'))
            else:
                vdo_functions.append(f'VDO{i+1}')
        
        self.vdi_vdo_tab.set_vdi_functions(vdi_functions)
        self.vdi_vdo_tab.set_vdo_functions(vdo_functions)
        
        # Erstelle Funktionsdetails für die Legende
        vdi_function_details = []
        vdo_function_details = []
        
        for i in range(16):
            if i < len(vdi_functions) and vdi_functions[i] not in ["Nicht zugewiesen", "Nicht verfügbar", "Fehler", "0"]:
                function_details = self._find_function_details(vdi_functions[i], "fun_in_map")
                vdi_function_details.append(function_details)
            else:
                vdi_function_details.append(None)
            
            if i < len(vdo_functions) and vdo_functions[i] not in ["Nicht zugewiesen", "Nicht verfügbar", "Fehler", "0"]:
                function_details = self._find_function_details(vdo_functions[i], "fun_out_map")
                vdo_function_details.append(function_details)
            else:
                vdo_function_details.append(None)
        
        # Aktualisiere die Legende mit den zugewiesenen Funktionen und Details
        self.vdi_vdo_tab.update_vdi_legend(vdi_functions, vdi_function_details)
        self.vdi_vdo_tab.update_vdo_legend(vdo_functions, vdo_function_details)
    
    def _read_io_functions(self):
        """Liest die IO-Funktionszuweisungen aus dem Servo aus"""
        try:
            # DI-Funktionsparameter (P03-02, P03-04, P03-06, P03-08, P03-10, P03-12, P03-14, P03-16)
            di_function_params = [f"P03-{i:02d}" for i in range(2, 18, 2)]
            di_functions = self._read_function_params(di_function_params, "DI")
            
            # DO-Funktionsparameter (P04-00, P04-02, P04-04, P04-06, P04-08, P04-10)
            do_function_params = [f"P04-{i:02d}" for i in range(0, 12, 2)]
            do_functions = self._read_function_params(do_function_params, "DO")
            
            # Fülle die restlichen IOs mit "Nicht zugewiesen" auf
            while len(di_functions) < 16:
                di_functions.append("Nicht zugewiesen")
            while len(do_functions) < 16:
                do_functions.append("Nicht zugewiesen")
            
            # Aktualisiere die UI mit den Funktionsbeschreibungen
            self.io_tab.set_di_functions(di_functions)
            UIHelper.keep_ui_responsive()
            
            self.io_tab.set_do_functions(do_functions)
            UIHelper.keep_ui_responsive()
            
            # Erstelle Funktionsdetails für die Legende
            di_function_details = []
            do_function_details = []
            
            for i in range(16):
                if i < len(di_functions) and di_functions[i] not in ["Nicht zugewiesen", "Nicht verfügbar", "Fehler", "Timeout", "Lesefehler", "Verbindungsfehler"]:
                    function_details = self._find_function_details(di_functions[i], "fun_in_map")
                    di_function_details.append(function_details)
                else:
                    di_function_details.append(None)
                
                if i < len(do_functions) and do_functions[i] not in ["Nicht zugewiesen", "Nicht verfügbar", "Fehler", "Timeout", "Lesefehler", "Verbindungsfehler"]:
                    function_details = self._find_function_details(do_functions[i], "fun_out_map")
                    do_function_details.append(function_details)
                else:
                    do_function_details.append(None)
            
            # Aktualisiere die Legende mit den zugewiesenen Funktionen und Details
            self.io_tab.update_di_legend(di_functions, di_function_details)
            UIHelper.keep_ui_responsive()
            
            self.io_tab.update_do_legend(do_functions, do_function_details)
            UIHelper.keep_ui_responsive()
            
        except ModbusConnectionException as e:
            logger.error(f"Verbindungsfehler beim Auslesen der IO-Funktionen: {e}")
            self.status_label.setText(f"Verbindungsfehler bei IO-Funktionen: {str(e)}")
            return  # Nicht mehr weitergeben, um Absturz zu vermeiden
        except Exception as e:
            logger.error(f"Fehler beim Auslesen der IO-Funktionen: {e}")
    
    def _read_vdi_vdo_functions(self):
        """Liest die VDI/VDO-Funktionszuweisungen aus dem Servo aus"""
        try:
            # VDI-Funktionsparameter (P17-00, P17-01, P17-03, P17-05, P17-07, P17-09, P17-11, P17-13,
            # P17-15, P17-17, P17-19, P17-21, P17-23, P17-25, P17-27, P17-29)
            vdi_function_params = [f"P17-{i:02d}" for i in range(0, 32, 2)]
            vdi_functions = self._read_function_params(vdi_function_params, "VDI")
            
            # VDO-Funktionsparameter (P17-33, P17-35, P17-37, P17-39, P17-41, P17-43, P17-45, P17-47,
            # P17-49, P17-51, P17-53, P17-55, P17-57, P17-59, P17-61, P17-63)
            vdo_function_params = [f"P17-{i:02d}" for i in range(33, 65, 2)]
            vdo_functions = self._read_function_params(vdo_function_params, "VDO")
            
            # Fülle die restlichen VIOs mit "Nicht zugewiesen" auf
            while len(vdi_functions) < 16:
                vdi_functions.append("Nicht zugewiesen")
            while len(vdo_functions) < 16:
                vdo_functions.append("Nicht zugewiesen")
            
            # Aktualisiere die UI mit den Funktionsbeschreibungen
            self.vdi_vdo_tab.set_vdi_functions(vdi_functions)
            UIHelper.keep_ui_responsive()
            
            self.vdi_vdo_tab.set_vdo_functions(vdo_functions)
            UIHelper.keep_ui_responsive()
            
            # Erstelle Funktionsdetails für die Legende
            vdi_function_details = []
            vdo_function_details = []
            
            for i in range(16):
                if i < len(vdi_functions) and vdi_functions[i] not in ["Nicht zugewiesen", "Nicht verfügbar", "Fehler", "Timeout", "Lesefehler", "Verbindungsfehler"]:
                    function_details = self._find_function_details(vdi_functions[i], "fun_in_map")
                    vdi_function_details.append(function_details)
                else:
                    vdi_function_details.append(None)
                
                if i < len(vdo_functions) and vdo_functions[i] not in ["Nicht zugewiesen", "Nicht verfügbar", "Fehler", "Timeout", "Lesefehler", "Verbindungsfehler"]:
                    function_details = self._find_function_details(vdo_functions[i], "fun_out_map")
                    vdo_function_details.append(function_details)
                else:
                    vdo_function_details.append(None)
            
            # Aktualisiere die Legende mit den zugewiesenen Funktionen und Details
            self.vdi_vdo_tab.update_vdi_legend(vdi_functions, vdi_function_details)
            UIHelper.keep_ui_responsive()
            
            self.vdi_vdo_tab.update_vdo_legend(vdo_functions, vdo_function_details)
            UIHelper.keep_ui_responsive()
            
        except ModbusConnectionException as e:
            logger.error(f"Verbindungsfehler beim Auslesen der VDI/VDO-Funktionen: {e}")
            self.status_label.setText(f"Verbindungsfehler bei VDI/VDO-Funktionen: {str(e)}")
            return  # Nicht mehr weitergeben, um Absturz zu vermeiden
        except Exception as e:
            logger.error(f"Fehler beim Auslesen der VDI/VDO-Funktionen: {e}")
    
    def _read_function_params(self, function_params, io_type):
        """Liest eine Liste von Funktionsparametern"""
        functions = []
        
        for param_code in function_params:
            param = self.parameter_manager.get_parameter(param_code)
            if param and param.decimal:
                try:
                    val = self.modbus_client.read_holding_register(int(param.decimal), count=1)
                    if val:
                        # Hole den Funktionsnamen basierend auf dem Wert
                        function_value = str(val[0])
                        function_name = self._get_function_name(function_value, io_type)
                        functions.append(function_name)
                    else:
                        functions.append("Nicht zugewiesen")
                except ModbusTimeoutException as e:
                    logger.error(f"Timeout beim Lesen von {param_code}: {e}")
                    functions.append("Timeout")
                except ModbusReadException as e:
                    logger.error(f"Fehler beim Lesen von {param_code}: {e}")
                    functions.append("Lesefehler")
                except ModbusConnectionException as e:
                    logger.error(f"Verbindungsfehler beim Lesen von {param_code}: {e}")
                    functions.append("Verbindungsfehler")
                    # Nicht mehr weitergeben, sondern nur im Status anzeigen
                    self.status_label.setText(f"Verbindungsfehler bei {io_type}-Funktionen: {str(e)}")
                    return functions
                except Exception as e:
                    logger.error(f"Unerwarteter Fehler beim Lesen von {param_code}: {e}")
                    functions.append("Fehler")
            else:
                functions.append("Nicht verfügbar")
        
        return functions
    
    def _get_function_name(self, function_value, io_type):
        """Holt den Funktionsnamen basierend auf dem Funktionswert und IO-Typ"""
        try:
            # Wert 0 bedeutet "Nicht zugewiesen"
            if function_value == "0":
                return "Nicht zugewiesen"
                
            if io_type in ["DI", "VDI"]:
                function_map = self.parameter_manager.fun_in_map
            else:  # DO oder VDO
                function_map = self.parameter_manager.fun_out_map
            
            # Suche nach der Funktion mit dem passenden Option-Wert
            if function_value in function_map:
                return function_map[function_value].get('name', f'Funktion {function_value}')
            else:
                return f'Unbekannt ({function_value})'
        except Exception as e:
            print(f"Fehler beim Holen des Funktionsnamens für Wert {function_value}: {e}")
            return f'Fehler ({function_value})'
    
    def _find_function_details(self, function_name, map_name):
        """Findet die Funktionsdetails basierend auf dem Funktionsnamen"""
        function_map = getattr(self.parameter_manager, map_name)
        
        for key, value in function_map.items():
            if value.get('name') == function_name:
                return value
        
        return None
    
    def handle_vdi_toggle(self, vdi_number, state, simulation_mode=False, disconnect_callback=None):
        """Wird aufgerufen, wenn ein VDI-Toggle-Button geklickt wird"""
        if simulation_mode:
            print(f"VDI{vdi_number} Toggle im Simulationsmodus: {state}")
            return
        
        if not self.modbus_client.connected:
            print(f"VDI{vdi_number} Toggle fehlgeschlagen: Keine Verbindung")
            return
        
        try:
            # Bestimme den Parameter für den VDI-Status
            vdi_param = self.parameter_manager.get_parameter("P31-00")
            if not vdi_param or not vdi_param.decimal:
                print(f"VDI{vdi_number} Toggle fehlgeschlagen: Parameter P31-00 nicht gefunden")
                return
            
            # Lese aktuellen VDI-Status
            val_vdi = self.modbus_client.read_holding_register(int(vdi_param.decimal), count=1)
            if not val_vdi:
                print(f"VDI{vdi_number} Toggle fehlgeschlagen: Konnte VDI-Status nicht lesen")
                return
            
            # Berechne neuen Wert basierend auf dem VDI-Status und dem gewünschten Zustand
            current_value = val_vdi[0]
            bit_position = vdi_number - 1  # VDI1 ist Bit 0, VDI2 ist Bit 1, etc.
            
            if state:
                # Setze das Bit
                new_value = current_value | (1 << bit_position)
            else:
                # Lösche das Bit
                new_value = current_value & ~(1 << bit_position)
            
            print(f"VDI{vdi_number} Toggle: {state} (alter Wert: {current_value}, neuer Wert: {new_value})")
            
            # Schreibe neuen Wert
            result = self.modbus_client.write_holding_register(int(vdi_param.decimal), new_value)
            if result:
                print(f"VDI{vdi_number} Toggle erfolgreich: Wert {new_value} geschrieben")
                # Aktualisiere die Anzeige im VDI/VDO-Tab
                self.vdi_vdo_tab.set_vdi_labels(new_value)
                
                # Aktualisiere auch die VDI-Buttons im Tuning-Tab, falls vorhanden
                if self.tuning_tab and hasattr(self.tuning_tab, 'update_vdi_buttons'):
                    self.tuning_tab.update_vdi_buttons(new_value)
            else:
                print(f"VDI{vdi_number} Toggle fehlgeschlagen: Konnte Wert nicht schreiben")
                
        except ModbusTimeoutException as e:
            print(f"VDI{vdi_number} Toggle Timeout: {e}")
            self.status_label.setText(f"Timeout bei VDI{vdi_number}-Toggle: {str(e)}")
        except ModbusReadException as e:
            print(f"VDI{vdi_number} Toggle Lesefehler: {e}")
            self.status_label.setText(f"Lesefehler bei VDI{vdi_number}-Toggle: {str(e)}")
        except ModbusConnectionException as e:
            print(f"VDI{vdi_number} Toggle Verbindungsfehler: {e}")
            self.status_label.setText(f"Verbindungsfehler bei VDI{vdi_number}-Toggle: {str(e)}")
            if disconnect_callback:
                disconnect_callback()
        except Exception as e:
            print(f"VDI{vdi_number} Toggle unerwarteter Fehler: {e}")
            self.status_label.setText(f"Fehler bei VDI{vdi_number}-Toggle: {str(e)}")
    
    def get_vdo_data(self):
        """Gibt die aktuellen VDO-Daten für den Tuning-Tab zurück"""
        return self.current_vdo_data