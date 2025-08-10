from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
                             QLineEdit, QListWidget, QTreeWidget, QTextEdit,
                             QPushButton, QHeaderView, QTreeWidgetItem, QApplication,
                             QStyledItemDelegate, QComboBox)
from PyQt5.QtCore import Qt, QSignalBlocker
from PyQt5.QtGui import QFont, QColor, QDoubleValidator, QIntValidator

from custom_exceptions import ModbusReadException, ModbusWriteException
from logger_config import logger
from contextlib import contextmanager

@contextmanager
def SignalBlocker(signal, slot):
    """Context manager to temporarily block and unblock a signal-slot connection"""
    try:
        signal.disconnect(slot)
        yield
    except TypeError:
        # Signal was not connected
        yield
    finally:
        signal.connect(slot)

class ParameterDelegate(QStyledItemDelegate):
    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app

    def createEditor(self, parent, option, index):
        if index.column() != 2: # Only for "Wert" column
            return None  # Kein Editor für andere Spalten

        param = index.data(Qt.UserRole)
        if not param or not param.validation:
            return None  # Kein Editor für Parameter ohne Validierung

        v_type = param.validation.get('type')
        editor = None

        # Enums use ComboBox
        if v_type == 'enum':
            editor = QComboBox(parent)
            options = param.validation.get('options', {})
            options_ref = param.validation.get('options_ref')

            # Dynamically load options based on options_ref
            ref_maps = self.main_app.get_reference_maps()
            
            fun_map = ref_maps.get(options_ref)
            if fun_map:
                for key, item in fun_map.items():
                    editor.addItem(f"{key}: {item.get('name', self.main_app.language_manager.get_text('text_not_available'))}", userData=key)
            else: # Fallback to inline options if options_ref is not recognized or not present
                for key, value in options.items():
                    editor.addItem(f"{key}: {value}", userData=key)
        
        # Ranges use validated QLineEdit
        elif v_type == 'range':
            editor = QLineEdit(parent)
            num_type = param.validation.get('number_type', 'integer')
            min_val = param.validation.get('min', None)
            max_val = param.validation.get('max', None)
            
            if num_type == 'float' and min_val is not None and max_val is not None:
                validator = QDoubleValidator(min_val, max_val, 2)
                editor.setValidator(validator)
            elif num_type == 'integer' and min_val is not None and max_val is not None:
                validator = QIntValidator(min_val, max_val)
                editor.setValidator(validator)
        
        if editor:
            editor.setMinimumWidth(250)
            return editor
            
        return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        if isinstance(editor, QComboBox):
            current_value_key = index.data(Qt.EditRole)
            idx = editor.findData(str(current_value_key))
            if idx != -1:
                editor.setCurrentIndex(idx)
        elif isinstance(editor, QLineEdit):
            param = index.data(Qt.UserRole)
            raw_value = index.data(Qt.EditRole)
            
            # Format the value with decimal places for display
            if param and param.validation and param.validation.get('type') == 'range':
                decimal_places = param.validation.get('decimal_places', 0)
                if decimal_places > 0 and raw_value is not None:
                    try:
                        # Check if the raw value is already converted (displayed value)
                        # If it contains a decimal point, it's already converted
                        if isinstance(raw_value, str) and '.' in raw_value:
                            editor.setText(raw_value)
                        else:
                            # Convert raw value to displayed value with decimal places
                            float_value = float(raw_value) / (10 ** decimal_places)
                            editor.setText(f"{float_value:.{decimal_places}f}")
                    except (ValueError, TypeError):
                        editor.setText(str(raw_value))
                else:
                    editor.setText(str(raw_value) if raw_value is not None else "")
            else:
                editor.setText(str(raw_value) if raw_value is not None else "")


    def setModelData(self, editor, model, index):
        if isinstance(editor, QComboBox):
            value = editor.currentData() # This is the key "0", "1" etc
            display_text = editor.currentText()
            model.setData(index, value, Qt.EditRole)
            # We can store the display text in another role if we want to show it when not editing
            # For now, on_item_changed will handle the orange background
        elif isinstance(editor, QLineEdit):
            param = index.data(Qt.UserRole)
            display_value = editor.text()
            
            # Convert display value back to raw value for storage
            if param and param.validation and param.validation.get('type') == 'range':
                decimal_places = param.validation.get('decimal_places', 0)
                if decimal_places > 0 and display_value:
                    try:
                        # Convert displayed value back to raw value
                        float_value = float(display_value)
                        raw_value = int(float_value * (10 ** decimal_places))
                        model.setData(index, raw_value, Qt.EditRole)
                        # Wichtig: Setze den Text direkt, um die Anzeige zu aktualisieren
                        # Dies verhindert, dass on_item_changed den Wert erneut konvertiert
                        model.setData(index, display_value, Qt.DisplayRole)
                    except (ValueError, TypeError):
                        # Fallback to original text if conversion fails
                        model.setData(index, display_value, Qt.EditRole)
                else:
                    model.setData(index, display_value, Qt.EditRole)
            else:
                model.setData(index, display_value, Qt.EditRole)

class RegisterTab(QWidget):
    def __init__(self, parameter_manager, modbus_client, parent=None):
        super().__init__(parent)
        self.main_app = parent
        self.parameter_manager = parameter_manager
        self.modbus_client = modbus_client
        self.grouped_params = self._group_params_by_pxx()
        self.pxx_mapping = self.main_app.pxx_mapping
        self.parameter_cache = {} # Cache for loaded parameter values
        
        # Reference maps for options - defined once to avoid duplication
        self.ref_maps = {
            "servo_FunIN.json": self.main_app.parameter_manager.fun_in_map,
            "servo_FunOUT.json": self.main_app.parameter_manager.fun_out_map
        }
        
        main_layout = QHBoxLayout(self)
        main_splitter = QSplitter(Qt.Horizontal)

        left_widget = self.create_left_widget()
        right_widget = self.create_right_widget()

        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([250, 750])
        main_layout.addWidget(main_splitter)

        self.update_pxx_list()
        self.set_enabled(False)

    def create_left_widget(self):
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.main_app.language_manager.get_text("placeholder_search_entire_list"))
        self.search_input.textChanged.connect(self.update_view)
        left_layout.addWidget(self.search_input)
        
        self.pxx_list_widget = QListWidget()
        self.pxx_list_widget.currentRowChanged.connect(self.update_view)
        left_layout.addWidget(self.pxx_list_widget)
        return left_widget

    def create_right_widget(self):
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        self.right_splitter = QSplitter(Qt.Vertical)
        
        right_top_widget = QWidget()
        right_top_layout = QVBoxLayout(right_top_widget)
        right_top_layout.setContentsMargins(0,0,0,0)

        self.actions_layout = QHBoxLayout()
        read_btn = QPushButton(self.main_app.language_manager.get_text("button_read_visible_parameters"))
        read_btn.clicked.connect(self.read_visible_parameters)
        write_btn = QPushButton(self.main_app.language_manager.get_text("button_write_modified_parameters"))
        write_btn.clicked.connect(self.write_modified_parameters)
        self.actions_layout.addWidget(read_btn)
        self.actions_layout.addWidget(write_btn)
        
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels([
            self.main_app.language_manager.get_text("header_code"),
            self.main_app.language_manager.get_text("header_name"),
            self.main_app.language_manager.get_text("header_value"),
            self.main_app.language_manager.get_text("header_modbus_raw_value"),
            self.main_app.language_manager.get_text("header_unit"),
            self.main_app.language_manager.get_text("header_default"),
            self.main_app.language_manager.get_text("header_hex"),
            self.main_app.language_manager.get_text("header_range_options")
        ])
        header = self.tree_widget.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Code
        header.setSectionResizeMode(1, QHeaderView.Stretch)           # Name
        header.setSectionResizeMode(2, QHeaderView.Interactive)       # Wert
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Modbus-Rohwert
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Einheit
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Default
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Hex
        header.setSectionResizeMode(7, QHeaderView.Interactive)       # Bereich/Optionen
        self.tree_widget.setColumnWidth(2, 150) # Give "Wert" a decent initial width
        self.tree_widget.itemSelectionChanged.connect(self.show_details)
        self.tree_widget.itemChanged.connect(self.on_item_changed)
        
        # Set the custom delegate for the "Wert" column
        delegate = ParameterDelegate(self.main_app, self.tree_widget)
        self.tree_widget.setItemDelegateForColumn(2, delegate)
        
        right_top_layout.addLayout(self.actions_layout)
        right_top_layout.addWidget(self.tree_widget)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setFont(QFont("Courier New", 10))
        self.details_text.setPlaceholderText(self.main_app.language_manager.get_text("placeholder_select_parameter_for_details"))

        self.right_splitter.addWidget(right_top_widget)
        self.right_splitter.addWidget(self.details_text)
        self.right_splitter.setSizes([500, 200])
        right_layout.addWidget(self.right_splitter)
        return right_widget

    def _group_params_by_pxx(self):
        grouped = {}
        if self.parameter_manager.parameters:
            for param in self.parameter_manager.parameters.values():
                pxx = param.code.split('-')[0]
                if pxx not in grouped: grouped[pxx] = []
                grouped[pxx].append(param)
        return grouped

    def update_pxx_list(self):
        self.pxx_list_widget.clear()
        sorted_keys = sorted(self.grouped_params.keys())
        for key in sorted_keys:
            desc = self.pxx_mapping.get(key, self.main_app.language_manager.get_text("text_no_description"))
            self.pxx_list_widget.addItem(f"{key} - {desc}")

    def update_view(self):
        self.tree_widget.clear()
        self.details_text.clear()
        search_term = self.search_input.text().lower()

        params_to_display = []
        if search_term:
            self.pxx_list_widget.blockSignals(True)
            self.pxx_list_widget.setCurrentRow(-1)
            self.pxx_list_widget.blockSignals(False)
            for param in self.parameter_manager.parameters.values():
                if search_term in param.code.lower() or search_term in param.name.lower():
                    params_to_display.append(param)
        else:
            selected_item = self.pxx_list_widget.currentItem()
            if selected_item:
                pxx_key = selected_item.text().split(' ')[0]
                params_to_display = self.grouped_params.get(pxx_key, [])
            else: # Show all if nothing is selected or searched
                params_to_display = list(self.parameter_manager.parameters.values())

        try:
            # Use a more robust way to disconnect
            self.tree_widget.itemChanged.disconnect(self.on_item_changed)
        except TypeError:
            pass # Ignore if not connected

        for param in params_to_display:
            # Retrieve cached value if available
            cached_value = self.parameter_cache.get(param.code, "")
            
            # Default-Wert mit Berücksichtigung der Dezimalstellen für die Tabelle
            default_display = param.default
            if param.validation and param.validation.get('type') == 'range':
                decimal_places = param.validation.get('decimal_places', 0)
                if decimal_places > 0 and param.default is not None:
                    try:
                        default_display = float(param.default) / (10 ** decimal_places)
                        default_display = f"{default_display:.{decimal_places}f}"
                    except (ValueError, TypeError):
                        default_display = str(param.default)
                else:
                    default_display = str(param.default)
            else:
                default_display = str(param.default) if param.default is not None else "-"
            
            item = QTreeWidgetItem(self.tree_widget, [
                param.code or "-", param.name or "-",
                "", # Wertefeld - wird aus Rohwert konvertiert
                str(cached_value), # Modbus-Rohwert
                param.unit or "-", default_display,
                param.hex or "-", self._get_readable_validation(param)
            ])
            # Nur die Werte-Spalte (Spalte 2) editierbar machen
            self._set_value_column_editable(item)
            item.setData(2, Qt.UserRole, param)
            item.setData(0, Qt.UserRole, param)
            # Store the raw cached value in EditRole for the delegate
            if cached_value != "":
                item.setData(2, Qt.EditRole, cached_value)
                # Konvertiere Rohwert in formatierten Wert für die Anzeige
                readable_value = self._get_readable_value(param, cached_value)
                # Wichtig: Setze den Text, nicht nur das EditRole, um den formatierten Wert anzuzeigen
                item.setText(2, readable_value)
                # Apply color based on default value, but only if not already orange (modified/imported)
                if item.background(0).color() != QColor("orange"):
                    self.update_item_color(item, str(cached_value))
        
        self.tree_widget.itemChanged.connect(self.on_item_changed)
    def show_details(self):
        selected_items = self.tree_widget.selectedItems()
        if not selected_items: self.details_text.clear(); return
        param = selected_items[0].data(0, Qt.UserRole)
        if not param: return
        
        details_str = (f"{self.main_app.language_manager.get_text('details_code')}: {param.code}\n"
                       f"{self.main_app.language_manager.get_text('details_name')}: {param.name}\n"
                       f"{self.main_app.language_manager.get_text('details_unit')}: {param.unit}\n"
                       f"{self.main_app.language_manager.get_text('details_default')}: {param.default}\n"
                       f"{self.main_app.language_manager.get_text('details_hex')}: {param.hex}\n"
                       f"{self.main_app.language_manager.get_text('details_decimal')}: {param.decimal}\n\n")

        # --- Detailed I/O Function Description ---
        current_value = selected_items[0].text(2).split(':')[0] # Get the option number
        io_desc = self._get_io_function_description(param, current_value)
        details_str += io_desc

        if param.validation:
            details_str += f"--- {self.main_app.language_manager.get_text('details_validation')} ---\n"
            v_type = param.validation.get('type')
            details_str += f"{self.main_app.language_manager.get_text('details_type')}: {v_type}\n"

            if v_type == 'range':
                min_val = param.validation.get('min', 'N/A')
                max_val = param.validation.get('max', 'N/A')
                num_type = param.validation.get('number_type', '')
                decimal_places = param.validation.get('decimal_places', 0)
                
                # Zeige den Bereich mit korrekten Dezimalstellen an
                if decimal_places > 0 and min_val != 'N/A' and max_val != 'N/A':
                    try:
                        min_display = float(min_val) / (10 ** decimal_places)
                        max_display = float(max_val) / (10 ** decimal_places)
                        details_str += f"  {self.main_app.language_manager.get_text('details_range')}: {min_display:.{decimal_places}f} {self.main_app.language_manager.get_text('details_to')} {max_display:.{decimal_places}f}\n"
                    except (ValueError, TypeError):
                        details_str += f"  {self.main_app.language_manager.get_text('details_range')}: {min_val} {self.main_app.language_manager.get_text('details_to')} {max_val}\n"
                else:
                    details_str += f"  {self.main_app.language_manager.get_text('details_range')}: {min_val} {self.main_app.language_manager.get_text('details_to')} {max_val}\n"
                    
                details_str += f"  {self.main_app.language_manager.get_text('details_data_type')}: {num_type}\n"
                
                # Zusätzliche Informationen für Range-Validierung anzeigen, falls vorhanden
                if decimal_places > 0:
                    details_str += f"  {self.main_app.language_manager.get_text('details_decimal_places')}: {decimal_places}\n"
                
                two_complement = param.validation.get('two_complement')
                if two_complement is not None:
                    details_str += f"  {self.main_app.language_manager.get_text('details_two_complement')}: {two_complement}\n"
                
                # Weitere optionale Felder
                if param.validation.get('description'):
                    details_str += f"  {self.main_app.language_manager.get_text('details_description')}: {param.validation.get('description')}\n"
                if param.validation.get('remarks'):
                    details_str += f"  {self.main_app.language_manager.get_text('details_remarks')}: {param.validation.get('remarks')}\n"
            elif v_type == 'enum':
                options_ref = param.validation.get('options_ref')
                display_options = {}
                if options_ref:
                    fun_map = self.ref_maps.get(options_ref)
                    if fun_map:
                        display_options = {key: item.get('name', self.main_app.language_manager.get_text('text_not_available')) for key, item in fun_map.items()}
                else:
                    display_options = param.validation.get('options', {})
                
                details_str += f"  {self.main_app.language_manager.get_text('details_options')}:\n"
                for key, value in display_options.items():
                    details_str += f"    {key}: {value}\n"
                
                # Zusätzliche Informationen für Enums anzeigen, falls vorhanden
                if param.validation.get('description'):
                    details_str += f"  {self.main_app.language_manager.get_text('details_description')}: {param.validation.get('description')}\n"
                if param.validation.get('remarks'):
                    details_str += f"  {self.main_app.language_manager.get_text('details_remarks')}: {param.validation.get('remarks')}\n"
            elif v_type == 'bitmask':
                bits = param.validation.get('bits', {})
                details_str += f"  {self.main_app.language_manager.get_text('details_bits')}:\n"
                for key, value in bits.items():
                    details_str += f"    {key}: {value}\n"
            elif v_type == 'raw':
                details_str += f"  {self.main_app.language_manager.get_text('details_info')}: {param.validation.get('value', 'N/A')}\n"
        else:
            details_str += f"\n{self.main_app.language_manager.get_text('details_validation')}: {self.main_app.language_manager.get_text('text_not_available')}"
            
        self.details_text.setText(details_str)

    def _convert_value_for_validation(self, param, new_val):
        """Convert the value for validation considering decimal places"""
        if param.validation and param.validation.get('type') == 'range':
            decimal_places = param.validation.get('decimal_places', 0)
            if decimal_places > 0:
                # Check if the new_val is already a converted display value (contains decimal point)
                if isinstance(new_val, str) and '.' in new_val:
                    return float(new_val) * (10 ** decimal_places)
                else:
                    # It's already a raw value, use it directly
                    return float(new_val)
            else:
                return float(new_val)
        else:
            return float(new_val)
    
    def _update_item_after_validation(self, item, param, raw_value):
        """Update item after successful validation"""
        # Mark as changed
        for j in range(item.columnCount()):
            item.setBackground(j, QColor("orange"))
        
        # Update the raw value column
        item.setText(3, str(raw_value))
        item.setData(2, Qt.EditRole, raw_value)
        
        # Convert the raw value back to formatted value for display
        readable_value = self._get_readable_value(param, raw_value)
        item.setText(2, readable_value)
        
        # Ensure only the value column is editable
        self._set_value_column_editable(item)
    
    def _revert_to_previous_value(self, item, param):
        """Revert item to previous cached value"""
        previous_value = self.parameter_cache.get(param.code, "")
        readable_value = self._get_readable_value(param, previous_value) if previous_value != "" else ""
        item.setText(2, readable_value)
        item.setText(3, str(previous_value))  # Modbus-Rohwert in Spalte 3
        item.setData(2, Qt.EditRole, previous_value)
        
        # Ensure only the value column is editable
        self._set_value_column_editable(item)
    
    def _set_value_column_editable(self, item):
        """Ensure only the value column (column 2) is editable"""
        # First set all columns to non-editable
        for col in range(item.columnCount()):
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        # Then set only the value column to editable
        item.setFlags(item.flags() | Qt.ItemIsEditable)

    def on_item_changed(self, item, column):
        if column == 2: # "Wert" column
            # Use context manager to prevent recursion
            with SignalBlocker(self.tree_widget.itemChanged, self.on_item_changed):
                # Validate the input before marking as changed
                param = item.data(0, Qt.UserRole)
                new_val = item.data(2, Qt.EditRole)
                
                if new_val is not None and param:
                    try:
                        # Convert value for validation
                        check_val_num = self._convert_value_for_validation(param, new_val)
                            
                        if self.main_app._validate_parameter(param, check_val_num):
                            # Update item after successful validation
                            raw_value = int(check_val_num)
                            self._update_item_after_validation(item, param, raw_value)
                        else:
                            # Revert to previous value if validation fails
                            self._revert_to_previous_value(item, param)
                    except (ValueError, TypeError):
                        # Revert to previous value if conversion fails
                        self._revert_to_previous_value(item, param)

    def read_visible_parameters(self):
        if not self.modbus_client.connected:
            self.main_app.status_label.setText(self.main_app.language_manager.get_text("status_no_modbus_connection"));
            return
        root = self.tree_widget.invisibleRootItem()
        self.main_app.status_label.setText(f"{self.main_app.language_manager.get_text('status_reading_parameters')} {root.childCount()} {self.main_app.language_manager.get_text('status_parameters')}")
        QApplication.processEvents()
        
        # Import ModbusHelper
        from utils.modbus_helpers import ModbusHelper
        
        # Use context manager for signal handling
        with SignalBlocker(self.tree_widget.itemChanged, self.on_item_changed):
            error_count = 0
            for i in range(root.childCount()):
                item = root.child(i)
                param = item.data(0, Qt.UserRole)
                if not param or not param.decimal: continue
                
                for j in range(item.columnCount()):
                    item.setBackground(j, QColor("white"))

                try:
                    # Use ModbusHelper to read parameter with proper decimal formatting
                    result = ModbusHelper.read_parameter_safely(self.modbus_client, param, self.main_app.status_label)
                    
                    if result and len(result) == 3:
                        raw_value, display_value, error = result
                        
                        if error:
                            logger.debug(f"DEBUG: Parameter {param.code} konnte nicht gelesen werden: {error}")
                            item.setText(2, self.main_app.language_manager.get_text("text_read_error"))
                            error_count += 1
                        else:
                            logger.debug(f"DEBUG: Parameter {param.code} erfolgreich gelesen: {raw_value}, angezeigt als: {display_value}")
                            # Setze den Rohwert in die Modbus-Rohwert-Spalte
                            item.setText(3, str(raw_value))
                            item.setData(2, Qt.EditRole, raw_value)
                            # Konvertiere den Rohwert in das Wertefeld
                            readable_value = self._get_readable_value(param, raw_value)
                            # Wichtig: Setze den Text, nicht nur das EditRole, um den formatierten Wert anzuzeigen
                            item.setText(2, readable_value)
                            # Aktualisiere auch die Spalte "Bereich/Optionen"
                            item.setText(7, self._get_readable_validation(param))
                            self.parameter_cache[param.code] = raw_value # Store in cache
                            self.update_item_color(item, str(raw_value))
                            
                            # Stelle sicher, dass nur die Werte-Spalte editierbar ist
                            self._set_value_column_editable(item)
                    else:
                        logger.debug(f"DEBUG: Parameter {param.code} konnte nicht gelesen werden, ungültiges Ergebnis")
                        item.setText(2, self.main_app.language_manager.get_text("text_read_error"))
                        error_count += 1
                except ModbusReadException as e:
                    # Use common error handling method
                    self._handle_modbus_error(item, param, e, "Lesen")
                    error_count += 1
                except Exception as e:
                    # Use common error handling method
                    self._handle_general_error(item, param, e, "Lesen")
                    error_count += 1
        
        if error_count > 0:
            self.main_app.status_label.setText(f"{root.childCount() - error_count}/{root.childCount()} {self.main_app.language_manager.get_text('status_visible_parameters_read')}, {error_count} {self.main_app.language_manager.get_text('status_read_errors')}")
        else:
            self.main_app.status_label.setText(f"{root.childCount()} {self.main_app.language_manager.get_text('status_visible_parameters_read')}")

    def write_modified_parameters(self):
        if not self.modbus_client.connected:
            self.main_app.status_label.setText(self.main_app.language_manager.get_text("status_no_modbus_connection"));
            return
        written_count = 0
        error_count = 0
        root = self.tree_widget.invisibleRootItem()
        self.main_app.status_label.setText(self.main_app.language_manager.get_text("status_writing_modified_parameters"))
        for i in range(root.childCount()):
            item = root.child(i)
            if item.background(0).color() == QColor("orange"):
                param = item.data(0, Qt.UserRole)
                
                # Get the raw value from the Modbus raw value column (column 3)
                raw_value_str = item.text(3)
                if not raw_value_str or raw_value_str == self.main_app.language_manager.get_text("text_read_error"):
                    # Fallback to EditRole if raw value column is empty
                    new_val = item.data(2, Qt.EditRole)
                    if new_val is None:
                        new_val = item.text(2)
                    
                    # Convert display value back to raw value if needed
                    if param.validation and param.validation.get('type') == 'range':
                        decimal_places = param.validation.get('decimal_places', 0)
                        if decimal_places > 0:
                            try:
                                # Convert displayed value back to raw value
                                float_value = float(new_val)
                                val_to_write = int(float_value * (10 ** decimal_places))
                            except (ValueError, TypeError):
                                # Fallback to original value if conversion fails
                                val_to_write = int(float(new_val))
                        else:
                            val_to_write = int(float(new_val))
                    else:
                        val_to_write = int(float(new_val))
                else:
                    # Use the raw value directly from the Modbus raw value column
                    try:
                        val_to_write = int(raw_value_str)
                    except (ValueError, TypeError):
                        # Fallback to EditRole if raw value conversion fails
                        new_val = item.data(2, Qt.EditRole)
                        if new_val is None:
                            new_val = item.text(2)
                        val_to_write = int(float(new_val))

                try:
                    # Validate the parameter
                    if not self.main_app._validate_parameter(param, val_to_write):
                        continue # Validation failed in main_app
                    
                    # Get parameter properties using helper method
                    is_32bit, is_signed = self._get_parameter_properties(param)
                    
                    write_successful = False
                    if is_32bit:
                        write_successful = self.modbus_client.write_holding_register_32bit(int(param.decimal), val_to_write, is_signed=is_signed)
                    else:
                        write_successful = self.modbus_client.write_holding_register(int(param.decimal), val_to_write)

                    if write_successful:
                        # After successful write, reset color to white/yellow
                        for j in range(item.columnCount()): item.setBackground(j, QColor("white"))
                        self.update_item_color(item, str(val_to_write))
                        self.parameter_cache[param.code] = val_to_write # Update cache on write
                        
                        # Update the raw value column
                        item.setText(3, str(val_to_write))
                        item.setData(2, Qt.EditRole, val_to_write)
                        # Convert the raw value to the display value field
                        readable_value = self._get_readable_value(param, val_to_write)
                        # Wichtig: Setze den Text, nicht nur das EditRole, um den formatierten Wert anzuzeigen
                        item.setText(2, readable_value)
                        
                        # Stelle sicher, dass nur die Werte-Spalte editierbar ist
                        self._set_value_column_editable(item)
                        
                        written_count += 1
                except (ValueError, TypeError) as e:
                    # More specific error handling for conversion errors
                    error_msg = f"{self.main_app.language_manager.get_text('status_error_convert_to_number')} '{val_to_write}' {self.main_app.language_manager.get_text('status_for')} {param.code}: {str(e)}"
                    self.main_app.status_label.setText(error_msg)
                    logger.error(error_msg)
                    continue
                except ModbusWriteException as e:
                    # Use common error handling method
                    self._handle_modbus_error(item, param, e, "Schreiben", val_to_write)
                    error_count += 1
                except Exception as e:
                    # Use common error handling method
                    self._handle_general_error(item, param, e, "Schreiben")
                    error_count += 1
        
        if error_count > 0:
            self.main_app.status_label.setText(f"{written_count} {self.main_app.language_manager.get_text('status_modified_parameters_written')}, {error_count} {self.main_app.language_manager.get_text('status_write_errors')}")
        else:
            self.main_app.status_label.setText(f"{written_count} {self.main_app.language_manager.get_text('status_modified_parameters_written')}")

    def display_imported_data(self, import_data):
        self.search_input.clear(); self.pxx_list_widget.setCurrentRow(-1); self.update_view()
        QApplication.processEvents()
        root = self.tree_widget.invisibleRootItem()
        
        # Use context manager for signal handling
        with SignalBlocker(self.tree_widget.itemChanged, self.on_item_changed):
            for i in range(root.childCount()):
                item = root.child(i)
                param = item.data(0, Qt.UserRole)
                if param and param.code in import_data:
                    imported_val = import_data[param.code]
                    # Setze den Rohwert in die Modbus-Rohwert-Spalte
                    item.setText(3, str(imported_val))
                    item.setData(2, Qt.EditRole, imported_val)
                    # Konvertiere den Rohwert in das Wertefeld
                    readable_val = self._get_readable_value(param, imported_val)
                    # Wichtig: Setze den Text, nicht nur das EditRole, um den formatierten Wert anzuzeigen
                    item.setText(2, readable_val)
                    self.parameter_cache[param.code] = imported_val # Store imported value in cache
                    for j in range(item.columnCount()):
                        item.setBackground(j, QColor("orange"))
                    
                    # Stelle sicher, dass nur die Werte-Spalte editierbar ist
                    self._set_value_column_editable(item)

    def update_item_color(self, item, current_value):
        # This function should only be called when signals on the tree are blocked
        default_val_str = item.text(4)
        is_default = False
        
        # Get parameter for decimal places handling
        param = item.data(0, Qt.UserRole)
        
        try:
            # Handle decimal places for range values when comparing
            if param and param.validation and param.validation.get('type') == 'range':
                decimal_places = param.validation.get('decimal_places', 0)
                if decimal_places > 0:
                    try:
                        # Convert raw value to displayed value with decimal places
                        current_value_display = float(current_value) / (10 ** decimal_places)
                        
                        # Get the actual default value from the parameter object
                        # This is more reliable than using the displayed text
                        if param.default is not None:
                            # The default value is stored as a raw value in the parameter object
                            default_value_display = float(param.default) / (10 ** decimal_places)
                            
                            # Compare with tolerance for floating point precision
                            if abs(default_value_display - current_value_display) < 0.0001:
                                is_default = True
                        else:
                            # Fallback to displayed default value if param.default is not available
                            if '.' in default_val_str:
                                default_value_display = float(default_val_str)
                                if abs(default_value_display - current_value_display) < 0.0001:
                                    is_default = True
                            else:
                                # Default value in display is also a raw value
                                default_value_display = float(default_val_str) / (10 ** decimal_places)
                                if abs(default_value_display - current_value_display) < 0.0001:
                                    is_default = True
                    except (ValueError, TypeError):
                        pass
                else:
                    # No decimal places, compare directly
                    try:
                        if param.default is not None:
                            if float(param.default) == float(current_value):
                                is_default = True
                        else:
                            if float(default_val_str) == float(current_value):
                                is_default = True
                    except (ValueError, TypeError):
                        if default_val_str == str(current_value):
                            is_default = True
            
            # Fallback to direct comparison if decimal places handling didn't work or isn't applicable
            if not is_default:
                try:
                    if float(default_val_str) == float(current_value):
                        is_default = True
                except (ValueError, TypeError):
                    if default_val_str == str(current_value):
                        is_default = True
        except (ValueError, TypeError):
            if default_val_str == str(current_value):
                is_default = True
        
        # Only color yellow if it's not the default AND not already orange (modified/imported)
        # This prevents overwriting the orange color set by on_item_changed or display_imported_data
        if not is_default and item.background(0).color() != QColor("orange"):
            for j in range(item.columnCount()):
                item.setBackground(j, QColor("yellow"))
        elif is_default and item.background(0).color() != QColor("white"):
            # If it's default and not white, set to white (e.g., after a write operation)
            for j in range(item.columnCount()):
                item.setBackground(j, QColor("white"))

    def _get_readable_validation(self, param):
        if not param or not param.validation:
            return self.main_app.language_manager.get_text("text_not_available")
        
        v_type = param.validation.get('type')
        if v_type == 'range':
            min_val = param.validation.get('min', 'N/A')
            max_val = param.validation.get('max', 'N/A')
            decimal_places = param.validation.get('decimal_places', 0)
            
            # Zeige den Bereich mit korrekten Dezimalstellen an
            if decimal_places > 0 and min_val != 'N/A' and max_val != 'N/A':
                try:
                    min_display = float(min_val) / (10 ** decimal_places)
                    max_display = float(max_val) / (10 ** decimal_places)
                    return f"{min_display:.{decimal_places}f} ~ {max_display:.{decimal_places}f}"
                except (ValueError, TypeError):
                    return f"{min_val} ~ {max_val}"
            else:
                return f"{min_val} ~ {max_val}"
        elif v_type == 'enum':
            options_ref = param.validation.get('options_ref')
            if options_ref:
                fun_map = self.ref_maps.get(options_ref)
                if fun_map:
                    return f"{len(fun_map)} {self.main_app.language_manager.get_text('text_options')}"
            # Fallback to inline options if options_ref is not present or not recognized
            return f"{len(param.validation.get('options', {}))} {self.main_app.language_manager.get_text('text_options')}"
        elif v_type == 'bitmask':
            return self.main_app.language_manager.get_text("text_bitmask")
        elif v_type == 'raw':
            return self.main_app.language_manager.get_text("text_raw")
        return self.main_app.language_manager.get_text("text_unknown")

    def _get_readable_value(self, param, value):
        if not param: return str(value)

        # DI/DO Function mapping
        if "P03-02" <= param.code <= "P03-17":
            fun_map = self.main_app.parameter_manager.fun_in_map
            func_details = fun_map.get(str(value))
            if func_details: return f"{value}: {func_details.get('name', self.main_app.language_manager.get_text('text_not_available'))}"
        elif "P04-00" <= param.code <= "P04-11":
            fun_map = self.main_app.parameter_manager.fun_out_map
            func_details = fun_map.get(str(value))
            if func_details: return f"{value}: {func_details.get('name', self.main_app.language_manager.get_text('text_not_available'))}"

        # Standard Enum mapping
        if param.validation and param.validation.get('type') == 'enum':
            options = param.validation.get('options', {})
            desc = options.get(str(value), self.main_app.language_manager.get_text("text_unknown_value"))
            return f"{value}: {desc}"
        
        # Handle decimal places for all validation types (not just range)
        if param.validation:
            decimal_places = param.validation.get('decimal_places', 0)
            if decimal_places > 0:
                try:
                    # Convert raw value to displayed value with decimal places
                    float_value = float(value) / (10 ** decimal_places)
                    return f"{float_value:.{decimal_places}f}"
                except (ValueError, TypeError):
                    return str(value)
            
        return str(value)
    
    def _get_io_function_description(self, param, current_value):
        """Helper method to get I/O function description to avoid code duplication"""
        io_desc = ""
        if "P03-02" <= param.code <= "P03-17":
            fun_map = self.main_app.parameter_manager.fun_in_map
            func_details = fun_map.get(current_value)
            if func_details:
                io_desc = (f"--- {self.main_app.language_manager.get_text('details_di_function_details')} ---\n"
                           f"{self.main_app.language_manager.get_text('details_function')}: {func_details.get('function', self.main_app.language_manager.get_text('text_not_available'))}\n"
                           f"{self.main_app.language_manager.get_text('details_description')}: {func_details.get('description', self.main_app.language_manager.get_text('text_not_available'))}\n"
                           f"{self.main_app.language_manager.get_text('details_remarks')}: {func_details.get('remarks', self.main_app.language_manager.get_text('text_not_available'))}\n\n")
        elif "P04-00" <= param.code <= "P04-11":
            fun_map = self.main_app.parameter_manager.fun_out_map
            func_details = fun_map.get(current_value)
            if func_details:
                io_desc = (f"--- {self.main_app.language_manager.get_text('details_do_function_details')} ---\n"
                           f"{self.main_app.language_manager.get_text('details_function')}: {func_details.get('function', self.main_app.language_manager.get_text('text_not_available'))}\n"
                           f"{self.main_app.language_manager.get_text('details_description')}: {func_details.get('description', self.main_app.language_manager.get_text('text_not_available'))}\n"
                           f"{self.main_app.language_manager.get_text('details_remarks')}: {func_details.get('remarks', self.main_app.language_manager.get_text('text_not_available'))}\n\n")
        return io_desc
    
    def _get_parameter_properties(self, param):
        """Helper method to determine parameter properties (bit width, signed)"""
        is_32bit = False
        is_signed = False
        if param.validation and param.validation.get('number_type'):
            number_type = param.validation.get('number_type')
            is_32bit = '32bit' in number_type
            is_signed = 'signed' in number_type
        return is_32bit, is_signed
    
    def _handle_modbus_error(self, item, param, exception, operation, value=None):
        """Common error handling method for Modbus exceptions"""
        # Log the error with consistent format
        error_msg = f"Modbus-{operation}fehler bei Parameter {param.code} (Register {int(param.decimal)}): {str(exception)}"
        logger.error(error_msg)
        
        if operation == "Lesen":
            logger.log_modbus_operation(operation, int(param.decimal), False, error_msg=str(exception))
        else:  # Schreiben
            logger.log_modbus_operation(operation, int(param.decimal), False, value, error_msg=str(exception))
            print(error_msg)  # Only print for write operations
        
        # Update UI with consistent error display
        self._display_error_on_item(item, operation)
    
    def _handle_general_error(self, item, param, exception, operation):
        """Common error handling method for general exceptions"""
        # Create consistent error message format
        error_msg = f"Unerwarteter Fehler beim {operation} von Parameter {param.code} (Register {int(param.decimal)}): {str(exception)}"
        
        # Log the error
        logger.log_general_error(error_msg)
        logger.error(error_msg)
        
        if operation == "Schreiben":
            print(error_msg)  # Only print for write operations
        
        # Update UI with consistent error display
        self._display_error_on_item(item, operation)
    
    def _display_error_on_item(self, item, operation):
        """Helper method to display error on item with consistent formatting"""
        # Set error text based on operation type
        error_text_key = "text_read_error" if operation == "Lesen" else "text_write_error"
        item.setText(2, self.main_app.language_manager.get_text(error_text_key))
        
        # Mark the item with red background to indicate error
        for j in range(item.columnCount()):
            item.setBackground(j, QColor("#ffcccc"))  # Helles Rot
    
    def update_language(self, language_manager):
        """Update all text elements with the selected language"""
        # Update search input placeholder
        self.search_input.setPlaceholderText(language_manager.get_text("placeholder_search_entire_list"))
        
        # Update buttons
        for i in range(self.actions_layout.count()):
            widget = self.actions_layout.itemAt(i).widget()
            if isinstance(widget, QPushButton):
                if i == 0:  # Read button
                    widget.setText(language_manager.get_text("button_read_visible_parameters"))
                elif i == 1:  # Write button
                    widget.setText(language_manager.get_text("button_write_modified_parameters"))
        
        # Update tree widget headers
        self.tree_widget.setHeaderLabels([
            language_manager.get_text("header_code"),
            language_manager.get_text("header_name"),
            language_manager.get_text("header_value"),
            language_manager.get_text("header_modbus_raw_value"),
            language_manager.get_text("header_unit"),
            language_manager.get_text("header_default"),
            language_manager.get_text("header_hex"),
            language_manager.get_text("header_range_options")
        ])
        
        # Update details text placeholder
        self.details_text.setPlaceholderText(language_manager.get_text("placeholder_select_parameter_for_details"))
        
        # Update pxx list items
        for i in range(self.pxx_list_widget.count()):
            item = self.pxx_list_widget.item(i)
            text = item.text()
            if " - " in text:
                key, desc = text.split(" - ", 1)
                if desc == language_manager.get_text("text_no_description"):
                    item.setText(f"{key} - {language_manager.get_text('text_no_description')}")
        
        # Refresh the current view to update parameter details
        self.update_view()
        
        # If there's a selected item, update its details
        selected_items = self.tree_widget.selectedItems()
        if selected_items:
            self.show_details()

    def set_enabled(self, enabled):
        for i in range(self.actions_layout.count()):
            widget = self.actions_layout.itemAt(i).widget()
            if isinstance(widget, QPushButton): widget.setEnabled(enabled)
