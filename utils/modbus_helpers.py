import math
from PyQt5.QtWidgets import QApplication, QComboBox
from custom_exceptions import (
    ModbusConnectionException,
    ModbusReadException,
    ModbusTimeoutException,
    ModbusWriteException
)
from logger_config import logger


class ModbusHelper:
    """Hilfsklasse für wiederkehrende Modbus-Operationen"""
    
    @staticmethod
    def _get_parameter_type_info(param):
        """Extrahiert Typinformationen aus einem Parameter"""
        is_32bit = False
        is_signed = False
        
        if param.validation and param.validation.get('number_type'):
            number_type = param.validation.get('number_type')
            is_32bit = '32bit' in number_type
            is_signed = 'signed' in number_type
        
        return is_32bit, is_signed
    
    @staticmethod
    def _validate_number_range(value, param_code, number_type):
        """Validiert einen Zahlenwert basierend auf seinem Typ"""
        bounds = {
            '32bit_unsigned': (0, 4294967295),
            '32bit_signed': (-2147483648, 2147483647),
            '16bit_unsigned': (0, 65535),
            '16bit_signed': (-32768, 32767)
        }
        
        for key, (min_val, max_val) in bounds.items():
            if key in number_type:
                if not (min_val <= value <= max_val):
                    return False, f"Fehler: Wert {value} für {param_code} ist außerhalb des {key}-Bereichs [{min_val}, {max_val}]."
        
        return True, ""
    
    @staticmethod
    def _handle_ui_error(exception, param_code, operation, status_label, disconnect_callback=None):
        """Zentralisierte Fehlerbehandlung für UI-Operationen"""
        error_type = ModbusHelper.handle_modbus_error(exception, param_code, operation)
        error_msg = f"{error_type.replace('_', ' ').title()} beim {operation} von {param_code}"
        
        if status_label:
            status_label.setText(error_msg)
        
        if "connection_error" in error_type and disconnect_callback:
            disconnect_callback()
    
    @staticmethod
    def _validate_modbus_client(modbus_client):
        """Validiert den Modbus-Client"""
        if modbus_client is None:
            raise ModbusConnectionException("Modbus-Client ist nicht initialisiert")
        return True
    
    @staticmethod
    def handle_modbus_error(exception, param_code=None, operation="Lesen"):
        """Standardisierte Fehlerbehandlung für Modbus-Operationen"""
        error_msg = ""
        
        if isinstance(exception, ModbusTimeoutException):
            error_msg = f"Timeout beim {operation} von {param_code if param_code else 'Parameter'}"
            logger.error(f"{error_msg}: {exception}")
            return "timeout"
        elif isinstance(exception, ModbusReadException):
            error_msg = f"Fehler beim {operation} von {param_code if param_code else 'Parameter'}"
            logger.error(f"{error_msg}: {exception}")
            return "read_error"
        elif isinstance(exception, ModbusConnectionException):
            error_msg = f"Verbindungsfehler beim {operation} von {param_code if param_code else 'Parameter'}"
            logger.error(f"{error_msg}: {exception}")
            return "connection_error"
        else:
            error_msg = f"Unerwarteter Fehler beim {operation} von {param_code if param_code else 'Parameter'}"
            logger.error(f"{error_msg}: {exception}")
            return "unknown_error"
    
    @staticmethod
    def validate_parameter(param, value):
        """Validiert einen Parameterwert gegen definierte Regeln"""
        if not param.validation:
            return True, ""  # Keine Validierungsregeln, also gültig
        
        # Prüfe die Bit-Breite mit der neuen Hilfsmethode
        number_type = param.validation.get('number_type')
        if number_type:
            valid, error_msg = ModbusHelper._validate_number_range(value, param.code, number_type)
            if not valid:
                return False, error_msg
        
        v_type = param.validation.get('type')
        if v_type == 'range':
            min_val = param.validation.get('min', -math.inf)
            max_val = param.validation.get('max', math.inf)
            if not (min_val <= value <= max_val):
                error_msg = f"Fehler: Wert {value} für {param.code} ist außerhalb des Bereichs [{min_val}, {max_val}]."
                return False, error_msg
        
        # 'enum' wird durch QComboBox behandelt, keine Laufzeitprüfung hier nötig
        return True, ""
    
    @staticmethod
    def read_parameter_safely(modbus_client, param, status_label=None):
        """Liest einen Parameter sicher mit standardisierter Fehlerbehandlung"""
        try:
            # Validiere den Modbus-Client
            ModbusHelper._validate_modbus_client(modbus_client)
            
            # Prüfe, ob es sich um einen 32-Bit-Parameter handelt
            is_32bit, is_signed = ModbusHelper._get_parameter_type_info(param)
            
            # Debug-Information
            bit_width = "32-Bit" if is_32bit else "16-Bit"
            signed_str = "signed" if is_signed else "unsigned"
            logger.debug(f"DEBUG: Lese Parameter {param.code} als {bit_width} {signed_str}")
            
            if is_32bit:
                val = modbus_client.read_holding_register_32bit(int(param.decimal), is_signed=is_signed)
            else:
                logger.debug(f"DEBUG: Lese Parameter {param.code} als 16-Bit")
                val = modbus_client.read_holding_register(int(param.decimal), count=1)
                if val:
                    val = val[0]
            
            if val is not None:
                logger.debug(f"DEBUG: Parameter {param.code} erfolgreich gelesen: {val}")
                # Wandle den Rohwert in einen anzeigbaren Wert mit Dezimalstellen um
                display_value = ModbusHelper._get_readable_value(val, param)
                return val, display_value, None
            else:
                error_msg = f"Fehler beim Lesen von {param.code}"
                if status_label:
                    status_label.setText(error_msg)
                return None, None, error_msg
        except Exception as e:
            error_type = ModbusHelper.handle_modbus_error(e, param.code, "Lesen")
            error_msg = f"{error_type.replace('_', ' ').title()} beim Lesen von {param.code}"
            if status_label:
                status_label.setText(error_msg)
            return None, None, error_msg
    
    @staticmethod
    def write_parameter_safely(modbus_client, param, value, status_label=None):
        """Schreibt einen Parameter sicher mit standardisierter Fehlerbehandlung"""
        try:
            # Validiere den Modbus-Client
            ModbusHelper._validate_modbus_client(modbus_client)
            
            # Prüfe, ob es sich um einen 32-Bit-Parameter handelt
            is_32bit, is_signed = ModbusHelper._get_parameter_type_info(param)
            
            # Debug-Information
            bit_width = "32-Bit" if is_32bit else "16-Bit"
            signed_str = "signed" if is_signed else "unsigned"
            logger.debug(f"DEBUG: Schreibe Parameter {param.code} als {bit_width} {signed_str}, Wert: {value}")
            
            if is_32bit:
                success = modbus_client.write_holding_register_32bit(int(param.decimal), int(value), is_signed=is_signed)
            else:
                logger.debug(f"DEBUG: Schreibe Parameter {param.code} als 16-Bit, Wert: {value}")
                success = modbus_client.write_holding_register(int(param.decimal), int(value))
            
            if success:
                logger.debug(f"DEBUG: Parameter {param.code} erfolgreich geschrieben: {value}")
                success_msg = f"{param.code} erfolgreich auf {int(value)} geschrieben."
                if status_label:
                    status_label.setText(success_msg)
                return True, None
            else:
                error_msg = f"Fehler beim Schreiben von {param.code}"
                if status_label:
                    status_label.setText(error_msg)
                return False, error_msg
        except Exception as e:
            error_type = ModbusHelper.handle_modbus_error(e, param.code, "Schreiben")
            error_msg = f"{error_type.replace('_', ' ').title()} beim Schreiben von {param.code}"
            if status_label:
                status_label.setText(error_msg)
            return False, error_msg
    
    @staticmethod
    def read_parameter(modbus_client, param, widget, status_label=None, disconnect_callback=None):
        """Liest einen Parameter und aktualisiert das Widget"""
        try:
            # Validiere den Modbus-Client
            ModbusHelper._validate_modbus_client(modbus_client)
            
            # Prüfe, ob es sich um einen 32-Bit-Parameter handelt
            is_32bit, is_signed = ModbusHelper._get_parameter_type_info(param)
            
            # Debug-Information
            bit_width = "32-Bit" if is_32bit else "16-Bit"
            signed_str = "signed" if is_signed else "unsigned"
            logger.debug(f"DEBUG: Lese Parameter {param.code} als {bit_width} {signed_str}")
            
            if is_32bit:
                val = modbus_client.read_holding_register_32bit(int(param.decimal), is_signed=is_signed)
            else:
                logger.debug(f"DEBUG: Lese Parameter {param.code} als 16-Bit")
                val = modbus_client.read_holding_register(int(param.decimal), count=1)
                if val:
                    val = val[0]
            
            if val is not None:
                logger.debug(f"DEBUG: Parameter {param.code} erfolgreich gelesen: {val}")
                
                # Wandle den Rohwert in einen anzeigbaren Wert mit Dezimalstellen um
                display_value = ModbusHelper._get_readable_value(val, param)
                widget.setText(display_value)
                
                if status_label:
                    status_label.setText(f"{param.code} erfolgreich gelesen: {display_value}")
            else:
                error_msg = f"Fehler beim Lesen von {param.code}"
                if status_label:
                    status_label.setText(error_msg)
        except Exception as e:
            ModbusHelper._handle_ui_error(e, param.code, "Lesen", status_label, disconnect_callback)
    
    @staticmethod
    def write_parameter(modbus_client, param, value, status_label=None, disconnect_callback=None, display_text=None):
        """Schreibt einen Parameterwert"""
        try:
            # Validiere den Modbus-Client
            ModbusHelper._validate_modbus_client(modbus_client)
            
            # Prüfe, ob es sich um einen 32-Bit-Parameter handelt
            is_32bit, is_signed = ModbusHelper._get_parameter_type_info(param)
            
            # Debug-Information
            bit_width = "32-Bit" if is_32bit else "16-Bit"
            signed_str = "signed" if is_signed else "unsigned"
            logger.debug(f"DEBUG: Schreibe Parameter {param.code} als {bit_width} {signed_str}, Wert: {value}")
            
            if is_32bit:
                success = modbus_client.write_holding_register_32bit(int(param.decimal), int(value), is_signed=is_signed)
            else:
                logger.debug(f"DEBUG: Schreibe Parameter {param.code} als 16-Bit, Wert: {value}")
                success = modbus_client.write_holding_register(int(param.decimal), int(value))
            
            if success:
                logger.debug(f"DEBUG: Parameter {param.code} erfolgreich geschrieben: {value}")
                success_msg = f"{param.code} erfolgreich auf {display_text or value} geschrieben."
                if status_label:
                    status_label.setText(success_msg)
            else:
                error_msg = f"Fehler beim Schreiben von {param.code}"
                if status_label:
                    status_label.setText(error_msg)
        except Exception as e:
            ModbusHelper._handle_ui_error(e, param.code, "Schreiben", status_label, disconnect_callback)
    
    @staticmethod
    def read_parameter_combobox(modbus_client, param, combobox, status_label=None, disconnect_callback=None):
        """Liest einen Parameter und aktualisiert die Combobox"""
        try:
            # Validiere den Modbus-Client
            ModbusHelper._validate_modbus_client(modbus_client)
            
            # Prüfe, ob es sich um einen 32-Bit-Parameter handelt
            is_32bit, is_signed = ModbusHelper._get_parameter_type_info(param)
            
            # Debug-Information
            bit_width = "32-Bit" if is_32bit else "16-Bit"
            signed_str = "signed" if is_signed else "unsigned"
            logger.debug(f"DEBUG: Lese Parameter {param.code} als {bit_width} {signed_str} für Combobox")
            
            if is_32bit:
                val = modbus_client.read_holding_register_32bit(int(param.decimal), is_signed=is_signed)
            else:
                logger.debug(f"DEBUG: Lese Parameter {param.code} als 16-Bit für Combobox")
                val = modbus_client.read_holding_register(int(param.decimal), count=1)
                if val:
                    val = val[0]
            
            if val is not None:
                logger.debug(f"DEBUG: Parameter {param.code} erfolgreich gelesen: {val}")
                # Finde den Index mit dem passenden Datenwert
                index = combobox.findData(val)
                if index >= 0:
                    combobox.setCurrentIndex(index)
                else:
                    # Fallback: Setze den ersten Eintrag, wenn der Wert nicht gefunden wurde
                    combobox.setCurrentIndex(0)
                
                if status_label:
                    status_label.setText(f"{param.code} erfolgreich gelesen: {combobox.currentText()}")
            else:
                error_msg = f"Fehler beim Lesen von {param.code}"
                if status_label:
                    status_label.setText(error_msg)
        except Exception as e:
            ModbusHelper._handle_ui_error(e, param.code, "Lesen", status_label, disconnect_callback)
    
    @staticmethod
    def _get_readable_value(value, param):
        """Konvertiert einen Rohwert in einen anzeigbaren Wert mit Dezimalstellen"""
        if value is None or value == '':
            return ''
        
        # Handle decimal places for range values
        if param.validation and param.validation.get('type') == 'range':
            decimal_places = param.validation.get('decimal_places', 0)
            if decimal_places > 0:
                try:
                    # Convert raw value to displayed value with decimal places
                    float_value = float(value) / (10 ** decimal_places)
                    return f"{float_value:.{decimal_places}f}"
                except (ValueError, TypeError):
                    # Fallback bei Konvertierungsfehlern
                    return str(value)
        
        return str(value)


class UIHelper:
    """Hilfsklasse für wiederkehrende UI-Operationen"""
    
    @staticmethod
    def keep_ui_responsive():
        """Hält die GUI responsive durch Aufruf von processEvents"""
        QApplication.processEvents()
    
    @staticmethod
    def update_status_with_translation(status_label, current_status, language_manager):
        """Aktualisiert das Status-Label basierend auf dem aktuellen Text und der Sprache"""
        status_mapping = {
            "Anwendung gestartet": "status_app_started",
            "Plot gestartet": "status_plot_started",
            "Plot gestoppt": "status_plot_stopped",
            "Plot gelöscht": "status_plot_cleared",
            "Verbindung erfolgreich": "status_connection_success",
            "Simulationsmodus gestartet": "status_simulation_started",
            "Verbindung fehlgeschlagen": "status_connection_failed",
            "Verbindung getrennt": "status_connection_disconnected",
            "Exportiere alle Register": "status_exporting_registers",
            "Application started": "status_app_started",
            "Plot started": "status_plot_started",
            "Plot stopped": "status_plot_stopped",
            "Plot cleared": "status_plot_cleared",
            "Connection successful": "status_connection_success",
            "Simulation mode started": "status_simulation_started",
            "Connection failed": "status_connection_failed",
            "Connection disconnected": "status_connection_disconnected",
            "Exporting all registers": "status_exporting_registers"
        }
        
        for status_key, translation_key in status_mapping.items():
            if status_key in current_status:
                status_label.setText(language_manager.get_text(translation_key))
                break
    
    @staticmethod
    def update_ui_language(app, language_manager):
        """Aktualisiert alle UI-Elemente mit der neuen Sprache"""
        # Update window title
        app.update_window_title()
        
        # Update menu bar
        app.menuBar().clear()
        app.create_menu_bar()
        
        # Update tab names
        for i in range(app.tabs.count()):
            tab = app.tabs.widget(i)
            tab_name = ""
            if tab == app.tuning_tab:
                tab_name = language_manager.get_text("tab_tuning_plot")
            elif tab == app.io_tab:
                tab_name = language_manager.get_text("tab_io_status")
            elif tab == app.vdi_vdo_tab:
                tab_name = language_manager.get_text("tab_vdi_vdo")
            elif tab == app.register_tab:
                tab_name = language_manager.get_text("tab_register_overview")
            elif tab == app.fault_tab:
                tab_name = language_manager.get_text("tab_fault_list")
            elif tab == app.connection_tab:
                tab_name = language_manager.get_text("tab_modbus_connection")
            
            if tab_name:
                app.tabs.setTabText(i, tab_name)
        
        # Update tab content
        app.tuning_tab.update_language(language_manager)
        app.io_tab.update_language(language_manager)
        app.vdi_vdo_tab.update_language(language_manager)
        app.register_tab.update_language(language_manager)
        app.fault_tab.update_language(language_manager)
        app.connection_tab.update_language(language_manager)
        
        # Update status label if it contains translatable text
        current_status = app.status_label.text()
        UIHelper.update_status_with_translation(app.status_label, current_status, language_manager)