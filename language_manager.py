import json
import os

class LanguageManager:
    """
    Verwaltet die Mehrsprachenunterstützung für die Anwendung.
    Lädt Übersetzungen und stellt Methoden zur Verfügung,
    um Texte in der aktuellen Sprache abzurufen.
    """
    
    def __init__(self, default_language='de'):
        self.current_language = default_language
        self.translations = {}
        self.supported_languages = ['de', 'en']  # Deutsch, Englisch
        self.language_names = {
            'de': 'Deutsch',
            'en': 'English'
        }
        self.load_translations()
    
    def load_translations(self):
        """Lädt die Übersetzungen für alle unterstützten Sprachen."""
        # Übersetzungen direkt im Code definieren
        self.translations = {
            'de': {
                # Hauptfenster
                'app_title': 'Servo Tuning & Diagnostic Tool',
                
                # Menü
                'menu_file': 'Datei',
                'menu_export_registers': 'Alle Register exportieren...',
                'menu_import_registers': 'Alle Register importieren...',
                
                # Tab-Namen
                'tab_tuning_plot': 'Tuning & Plot',
                'tab_io_status': 'I/O Status',
                'tab_vdi_vdo': 'VDI/VDO Status',
                'tab_register_overview': 'Registerübersicht',
                'tab_fault_list': 'Fehlerliste',
                'tab_modbus_connection': 'Modbus-Verbindung',
                
                # Sprachauswahl
                'language_label': 'Sprache',
                
                # Statusmeldungen
                'status_app_started': 'Anwendung gestartet. Bitte verbinden.',
                'status_plot_started': 'Plot gestartet.',
                'status_plot_stopped': 'Plot gestoppt.',
                'status_plot_cleared': 'Plot gelöscht.',
                'status_connection_success': 'Verbindung erfolgreich.',
                'status_simulation_started': 'Simulationsmodus gestartet.',
                'status_connection_failed': 'Verbindung fehlgeschlagen.',
                'status_connection_disconnected': 'Verbindung getrennt.',
                'status_exporting_registers': 'Exportiere alle Register... Bitte warten.',
                'status_plot_updated': 'Plot aktualisiert',
                'status_values_missing': 'Werte fehlen',
                'status_channels_without_data': 'Kanäle ohne Daten',
                'status_all_values_present': 'alle Werte vorhanden',
                'status_plot_error': 'Plot-Fehler',
                'status_plot': 'Plot',
                'status_connection': 'Verbindung',
                'status_visible_lines': 'Sichtbare Linien',
                'status_updates': 'Updates',
                'status_runtime': 'Laufzeit',
                'status_error': 'Fehler',
                'status_connection_error': 'Verbindungsfehler',
                'status_timeout': 'Timeout',
                'status_export': 'Export',
                'status_disconnected': 'Getrennt',
                'status_worker_error': 'Worker-Fehler',
                'status_plot_worker_config_updated': 'Plot-Worker-Konfiguration aktualisiert',
                'status_invalid_input': 'Ungültige Eingabe',
                'status_config_update_error': 'Fehler bei der Konfigurationsaktualisierung',
                'status_inactive': 'Inaktiv',
                'status_active': 'Aktiv',
                'status_errors': 'Fehler',
                
                # Verbindung
                'group_modbus_connection_settings': 'Modbus-Verbindungseinstellungen',
                'button_connect': 'Verbinden',
                'button_disconnect': 'Trennen',
                'label_com_port': 'COM-Port',
                'label_baud_rate': 'Baudrate',
                'label_data_bits': 'Datenbits',
                'label_parity': 'Parität',
                'label_stop_bits': 'Stoppbits',
                'label_modbus_address': 'Modbus-Adresse',
                'checkbox_simulation_mode': 'Simulationsmodus',
                'text_bps': 'bps',
                
                # Register
                'placeholder_search_entire_list': 'Ganze Liste durchsuchen...',
                'button_read_visible_parameters': 'Sichtbare Parameter lesen',
                'button_write_modified_parameters': 'Geänderte Parameter schreiben',
                'header_code': 'Code',
                'header_name': 'Name',
                'header_value': 'Wert',
                'header_modbus_raw_value': 'Modbus-Rohwert',
                'header_unit': 'Einheit',
                'header_default': 'Default',
                'header_hex': 'Hex',
                'header_range_options': 'Bereich/Optionen',
                'header_resettable': 'Zurücksetzbar',
                'placeholder_select_parameter_for_details': 'Wählen Sie einen Parameter aus der Tabelle, um alle Details anzuzeigen.',
                'text_no_description': 'Keine Beschreibung',
                'details_code': 'Code',
                'details_name': 'Name',
                'details_unit': 'Einheit',
                'details_default': 'Default',
                'details_hex': 'Hex',
                'details_decimal': 'Dezimal',
                'details_di_function_details': 'DI Funktion Details',
                'details_do_function_details': 'DO Funktion Details',
                'details_function': 'Funktion',
                'details_description': 'Beschreibung',
                'details_remarks': 'Anmerkungen',
                'details_validation': 'Validierung',
                'details_type': 'Typ',
                'details_range': 'Bereich',
                'details_to': 'bis',
                'details_data_type': 'Datentyp',
                'details_decimal_places': 'Dezimalstellen',
                'details_two_complement': 'Zweierkomplement',
                'details_options': 'Optionen',
                'details_bits': 'Bits',
                'details_info': 'Info',
                'details_handling': 'Details & Handhabung',
                'status_no_modbus_connection': 'Keine Modbus-Verbindung.',
                'status_reading_parameters': 'Lese',
                'status_parameters': 'Parameter...',
                'status_visible_parameters_read': 'sichtbare Parameter gelesen.',
                'status_writing_modified_parameters': 'Schreibe modifizierte Parameter...',
                'status_error_convert_to_number': 'Fehler: Konnte',
                'status_for': 'für',
                'status_modified_parameters_written': 'modifizierte(r) Parameter geschrieben.',
                'status_read_errors': 'Lesefehler',
                'status_write_errors': 'Schreibfehler',
                'text_read_error': 'Lesefehler',
                'text_options': 'Optionen',
                'text_bitmask': 'Bitmaske',
                'text_raw': 'Raw',
                'text_unknown': 'Unbekannt',
                'text_unknown_value': 'Unbekannter Wert',
                'text_not_available': 'N/A',
                
                # Fehlerliste
                'placeholder_select_fault_for_details': 'Wählen Sie einen Fehler aus der Liste für Details.',
                'text_no_details_available': 'Keine Details verfügbar.',
                
                # I/O Status
                'checkbox_enable_live_updates': 'Live-Updates aktivieren',
                'group_live_io_status': 'Live I/O Status',
                'group_virtual_io_status': 'VDI/VDO Status',
                'group_digital_inputs_di': 'Digital Inputs (DI)',
                'group_digital_outputs_do': 'Digital Outputs (DO)',
                'group_virtual_digital_inputs_vdi': 'Virtual Digital Inputs (VDI)',
                'group_virtual_digital_outputs_vdo': 'Virtual Digital Outputs (VDO)',
                'group_assigned_functions': 'Zugewiesene Funktionen',
                'text_no_functions_assigned': 'Keine Funktionen zugewiesen',
                'text_input': 'Input',
                'text_output': 'Output',
                'text_not_assigned': 'Nicht zugewiesen',
                'text_not_available': 'Nicht verfügbar',
                'text_error': 'Fehler',
                'text_function': 'Function',
                'text_description': 'Description',
                'text_number': 'Nr.',
                'text_state': 'Status',
                'text_action': 'Aktion',
                'button_toggle': 'Umschalten',
                
                # Tuning-Tab
                'group_tuning_parameters': 'Tuning-Parameter',
                'group_virtual_digital_io_vdi_vdo': 'VDI/VDO Status',
                'button_read': 'Lesen',
                'button_write': 'Schreiben',
                'button_switch_to_gain_set_2': 'Zu Gain Satz 2 wechseln',
                'button_switch_to_gain_set_1': 'Zu Gain Satz 1 wechseln',
                'label_note': 'Hinweis',
                'text_gain_set_activation': 'Zur Aktivierung von Gain Satz 2 müssen P08-08 und P08-09 konfiguriert werden.',
                'group_gain_parameter_set_1': 'Gain Parameter Set 1',
                'group_gain_parameter_set_2': 'Gain Parameter Set 2',
                'group_other_tuning_parameters': 'Weitere Tuning Parameter',
                'group_direct_commands': 'Direktbefehle',
                'button_send': 'Senden',
                'button_set_all_commands_to_zero': 'Alle Befehle auf 0 setzen',
                'group_plot_settings': 'Plot-Einstellungen',
                'label_sampling_interval': 'Abtastintervall',
                'label_number_of_data_points': 'Anzahl Datenpunkte',
                'label_visible_time': 'Sichtbare Zeit',
                'button_apply': 'Anwenden',
                'button_apply_config': 'Konfiguration anwenden',
                'label_watchdog_timeout': 'Watchdog-Timeout',
                'label_manual_control': 'Manuelle Steuerung',
                'button_start': 'Start',
                'button_stop': 'Stop',
                'button_clear': 'Löschen',
                'checkbox_advanced_plot_features': 'Erweiterte Plot-Funktionen (Zoom/Cursor)',
                'checkbox_vdo_polling': 'VDO-Status aktivieren',
                'group_legend_visibility': 'Legendensichtbarkeit',
                'group_realtime_data_plot': 'Echtzeit-Datenplot',
                'group_live_values': 'Live-Werte',
                'plot_actual_speed': 'Actual Speed',
                'plot_speed_cmd': 'Speed Cmd',
                'plot_pos_dev': 'Pos Dev',
                'plot_torque_cmd': 'Torque Cmd',
                'plot_current': 'Current',
                'text_not_available': 'N/A',
                'plot_title_realtime_servo_data': 'Echtzeit-Servodaten',
                'plot_xlabel_time': 'Zeit',
                'plot_ylabel_value': 'Wert',
                'validation_not_available': 'Validierung: N/A',
                'validation_range': 'Bereich',
                'validation_options': 'Optionen',
                'validation_see_register_overview': 'Validierung: Siehe Registerübersicht',
                'text_cursor_position_default': 'X: --, Y: --',
                'tooltip_sampling_interval': 'Abtastintervall in Millisekunden',
                'tooltip_number_of_data_points': 'Anzahl der Datenpunkte im Plot',
                
                # Allgemeine Begriffe
                'settings': 'Einstellungen',
                'language': 'Sprache',
                'error': 'Fehler',
                'warning': 'Warnung',
                'info': 'Information',
                'success': 'Erfolg',
                'failed': 'Fehlgeschlagen',
                'yes': 'Ja',
                'no': 'Nein',
                'ok': 'OK',
                'cancel': 'Abbrechen'
            },
            'en': {
                # Main window
                'app_title': 'Servo Tuning & Diagnostic Tool',
                
                # Menu
                'menu_file': 'File',
                'menu_export_registers': 'Export All Registers...',
                'menu_import_registers': 'Import All Registers...',
                
                # Tab names
                'tab_tuning_plot': 'Tuning & Plot',
                'tab_io_status': 'I/O Status',
                'tab_vdi_vdo': 'VDI/VDO Status',
                'tab_register_overview': 'Register Overview',
                'tab_fault_list': 'Fault List',
                'tab_modbus_connection': 'Modbus Connection',
                
                # Language selection
                'language_label': 'Language',
                
                # Status messages
                'status_app_started': 'Application started. Please connect.',
                'status_plot_started': 'Plot started.',
                'status_plot_stopped': 'Plot stopped.',
                'status_plot_cleared': 'Plot cleared.',
                'status_connection_success': 'Connection successful.',
                'status_simulation_started': 'Simulation mode started.',
                'status_connection_failed': 'Connection failed.',
                'status_connection_disconnected': 'Connection disconnected.',
                'status_exporting_registers': 'Exporting all registers... Please wait.',
                'status_plot_updated': 'Plot updated',
                'status_values_missing': 'values missing',
                'status_channels_without_data': 'channels without data',
                'status_all_values_present': 'all values present',
                'status_plot_error': 'Plot Error',
                'status_plot': 'Plot',
                'status_connection': 'Connection',
                'status_visible_lines': 'Visible Lines',
                'status_updates': 'Updates',
                'status_runtime': 'Runtime',
                'status_error': 'Error',
                'status_connection_error': 'Connection Error',
                'status_timeout': 'Timeout',
                'status_export': 'Export',
                'status_disconnected': 'Disconnected',
                'status_worker_error': 'Worker Error',
                'status_plot_worker_config_updated': 'Plot Worker Configuration Updated',
                'status_invalid_input': 'Invalid Input',
                'status_config_update_error': 'Configuration Update Error',
                'status_inactive': 'Inactive',
                'status_active': 'Active',
                'status_errors': 'Errors',
                
                # Connection
                'group_modbus_connection_settings': 'Modbus Connection Settings',
                'button_connect': 'Connect',
                'button_disconnect': 'Disconnect',
                'label_com_port': 'COM Port',
                'label_baud_rate': 'Baud Rate',
                'label_data_bits': 'Data Bits',
                'label_parity': 'Parity',
                'label_stop_bits': 'Stop Bits',
                'label_modbus_address': 'Modbus Address',
                'checkbox_simulation_mode': 'Simulation Mode',
                'text_bps': 'bps',
                
                # Register
                'placeholder_search_entire_list': 'Search entire list...',
                'button_read_visible_parameters': 'Read Visible Parameters',
                'button_write_modified_parameters': 'Write Modified Parameters',
                'header_code': 'Code',
                'header_name': 'Name',
                'header_value': 'Value',
                'header_modbus_raw_value': 'Modbus Raw Value',
                'header_unit': 'Unit',
                'header_default': 'Default',
                'header_hex': 'Hex',
                'header_range_options': 'Range/Options',
                'header_resettable': 'Resettable',
                'placeholder_select_parameter_for_details': 'Select a parameter from the table to view all details.',
                'text_no_description': 'No Description',
                'details_code': 'Code',
                'details_name': 'Name',
                'details_unit': 'Unit',
                'details_default': 'Default',
                'details_hex': 'Hex',
                'details_decimal': 'Decimal',
                'details_di_function_details': 'DI Function Details',
                'details_do_function_details': 'DO Function Details',
                'details_function': 'Function',
                'details_description': 'Description',
                'details_remarks': 'Remarks',
                'details_validation': 'Validation',
                'details_type': 'Type',
                'details_range': 'Range',
                'details_to': 'to',
                'details_data_type': 'Data Type',
                'details_decimal_places': 'Decimal Places',
                'details_two_complement': 'Two\'s Complement',
                'details_options': 'Options',
                'details_bits': 'Bits',
                'details_info': 'Info',
                'details_handling': 'Details & Handling',
                'status_no_modbus_connection': 'No Modbus connection.',
                'status_reading_parameters': 'Reading',
                'status_parameters': 'parameters...',
                'status_visible_parameters_read': 'visible parameters read.',
                'status_writing_modified_parameters': 'Writing modified parameters...',
                'status_error_convert_to_number': 'Error: Could not convert',
                'status_for': 'for',
                'status_modified_parameters_written': 'modified parameter(s) written.',
                'status_read_errors': 'read errors',
                'status_write_errors': 'write errors',
                'text_read_error': 'Read Error',
                'text_options': 'Options',
                'text_bitmask': 'Bitmask',
                'text_raw': 'Raw',
                'text_unknown': 'Unknown',
                'text_unknown_value': 'Unknown Value',
                'text_not_available': 'N/A',
                
                # Fault list
                'placeholder_select_fault_for_details': 'Select a fault from the list for details.',
                'text_no_details_available': 'No details available.',
                
                # I/O Status
                'checkbox_enable_live_updates': 'Enable Live Updates',
                'group_live_io_status': 'Live I/O Status',
                'group_virtual_io_status': 'VDI/VDO Status',
                'group_digital_inputs_di': 'Digital Inputs (DI)',
                'group_digital_outputs_do': 'Digital Outputs (DO)',
                'group_virtual_digital_inputs_vdi': 'Virtual Digital Inputs (VDI)',
                'group_virtual_digital_outputs_vdo': 'Virtual Digital Outputs (VDO)',
                'group_assigned_functions': 'Assigned Functions',
                'text_no_functions_assigned': 'No Functions Assigned',
                'text_input': 'Input',
                'text_output': 'Output',
                'text_not_assigned': 'Not Assigned',
                'text_not_available': 'Not Available',
                'text_error': 'Error',
                'text_function': 'Function',
                'text_description': 'Description',
                'text_number': 'No.',
                'text_state': 'State',
                'text_action': 'Action',
                'button_toggle': 'Toggle',
                
                # Tuning Tab
                'group_tuning_parameters': 'Tuning Parameters',
                'group_virtual_digital_io_vdi_vdo': 'VDI/VDO Status',
                'button_read': 'Read',
                'button_write': 'Write',
                'button_switch_to_gain_set_2': 'Switch to Gain Set 2',
                'button_switch_to_gain_set_1': 'Switch to Gain Set 1',
                'label_note': 'Note',
                'text_gain_set_activation': 'To activate Gain Set 2, P08-08 and P08-09 must be configured.',
                'group_gain_parameter_set_1': 'Gain Parameter Set 1',
                'group_gain_parameter_set_2': 'Gain Parameter Set 2',
                'group_other_tuning_parameters': 'Other Tuning Parameters',
                'group_direct_commands': 'Direct Commands',
                'button_send': 'Send',
                'button_set_all_commands_to_zero': 'Set All Commands to Zero',
                'group_plot_settings': 'Plot Settings',
                'label_sampling_interval': 'Sampling Interval',
                'label_number_of_data_points': 'Number of Data Points',
                'label_visible_time': 'Visible Time',
                'button_apply': 'Apply',
                'button_apply_config': 'Apply Configuration',
                'label_watchdog_timeout': 'Watchdog Timeout',
                'label_manual_control': 'Manual Control',
                'button_start': 'Start',
                'button_stop': 'Stop',
                'button_clear': 'Clear',
                'checkbox_advanced_plot_features': 'Advanced Plot Features (Zoom/Cursor)',
                'checkbox_vdo_polling': 'Enable VDO Status',
                'group_legend_visibility': 'Legend Visibility',
                'group_realtime_data_plot': 'Realtime Data Plot',
                'group_live_values': 'Live Values',
                'plot_actual_speed': 'Actual Speed',
                'plot_speed_cmd': 'Speed Cmd',
                'plot_pos_dev': 'Pos Dev',
                'plot_torque_cmd': 'Torque Cmd',
                'plot_current': 'Current',
                'text_not_available': 'N/A',
                'plot_title_realtime_servo_data': 'Realtime Servo Data',
                'plot_xlabel_time': 'Time',
                'plot_ylabel_value': 'Value',
                'validation_not_available': 'Validation: N/A',
                'validation_range': 'Range',
                'validation_options': 'Options',
                'validation_see_register_overview': 'Validation: See Register Overview',
                'text_cursor_position_default': 'X: --, Y: --',
                'tooltip_sampling_interval': 'Sampling interval in milliseconds',
                'tooltip_number_of_data_points': 'Number of data points in the plot',
                
                # General terms
                'settings': 'Settings',
                'language': 'Language',
                'error': 'Error',
                'warning': 'Warning',
                'info': 'Information',
                'success': 'Success',
                'failed': 'Failed',
                'yes': 'Yes',
                'no': 'No',
                'ok': 'OK',
                'cancel': 'Cancel'
            }
        }
    
    def get_text(self, key):
        """
        Gibt den übersetzten Text für den angegebenen Schlüssel zurück.
        
        Args:
            key (str): Der Schlüssel für den zu übersetzenden Text
            
        Returns:
            str: Der übersetzte Text oder der Schlüssel, wenn keine Übersetzung gefunden wurde
        """
        if self.current_language in self.translations:
            if key in self.translations[self.current_language]:
                return self.translations[self.current_language][key]
        
        # Fallback: Schlüssel zurückgeben, wenn keine Übersetzung gefunden wurde
        return key
    
    def set_language(self, language_code):
        """
        Setzt die aktuelle Sprache.
        
        Args:
            language_code (str): Der Sprachcode (z.B. 'de', 'en')
            
        Returns:
            bool: True, wenn die Sprache erfolgreich gesetzt wurde, sonst False
        """
        if language_code in self.supported_languages:
            self.current_language = language_code
            return True
        return False
    
    def get_current_language(self):
        """
        Gibt den Code der aktuellen Sprache zurück.
        
        Returns:
            str: Der Sprachcode der aktuellen Sprache
        """
        return self.current_language
    
    def get_supported_languages(self):
        """
        Gibt eine Liste der unterstützten Sprachcodes zurück.
        
        Returns:
            list: Liste der unterstützten Sprachcodes
        """
        return self.supported_languages
    
    def get_language_names(self):
        """
        Gibt ein Dictionary mit Sprachcodes und Anzeigenamen zurück.
        
        Returns:
            dict: Dictionary mit Sprachcodes und Anzeigenamen
        """
        return self.language_names