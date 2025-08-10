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
            return super().createEditor(parent, option, index)

        param = index.data(Qt.UserRole)
        if not param or not param.validation:
            return super().createEditor(parent, option, index)

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
            editor.setText(index.data(Qt.EditRole))


    def setModelData(self, editor, model, index):
        if isinstance(editor, QComboBox):
            value = editor.currentData() # This is the key "0", "1" etc
            display_text = editor.currentText()
            model.setData(index, value, Qt.EditRole)
            # We can store the display text in another role if we want to show it when not editing
            # For now, on_item_changed will handle the orange background
        elif isinstance(editor, QLineEdit):
            model.setData(index, editor.text(), Qt.EditRole)

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
            self.main_app.language_manager.get_text("header_unit"),
            self.main_app.language_manager.get_text("header_default"),
            self.main_app.language_manager.get_text("header_hex"),
            self.main_app.language_manager.get_text("header_range_options")
        ])
        header = self.tree_widget.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Code
        header.setSectionResizeMode(1, QHeaderView.Stretch)           # Name
        header.setSectionResizeMode(2, QHeaderView.Interactive)       # Wert
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Einheit
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Default
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Hex
        header.setSectionResizeMode(6, QHeaderView.Interactive)       # Bereich/Optionen
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
            readable_cached_value = self._get_readable_value(param, cached_value) if cached_value != "" else ""

            item = QTreeWidgetItem(self.tree_widget, [
                param.code or "-", param.name or "-",
                readable_cached_value, # Use cached value here
                param.unit or "-", param.default or "-",
                param.hex or "-", self._get_readable_validation(param)
            ])
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            item.setData(2, Qt.UserRole, param)
            item.setData(0, Qt.UserRole, param)
            # Store the raw cached value in EditRole for the delegate
            if cached_value != "":
                item.setData(2, Qt.EditRole, cached_value)
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
                details_str += f"  {self.main_app.language_manager.get_text('details_range')}: {min_val} {self.main_app.language_manager.get_text('details_to')} {max_val}\n"
                details_str += f"  {self.main_app.language_manager.get_text('details_data_type')}: {num_type}\n"
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

    def on_item_changed(self, item, column):
        if column == 2: # "Wert" column
            # Validate the input before marking as changed
            param = item.data(0, Qt.UserRole)
            new_val = item.data(2, Qt.EditRole)
            
            if new_val is not None and param:
                try:
                    check_val_num = float(new_val)
                    if self.main_app._validate_parameter(param, check_val_num):
                        # This signal now only fires for genuine user edits
                        for j in range(item.columnCount()):
                            item.setBackground(j, QColor("orange"))
                    else:
                        # Revert to previous value if validation fails
                        previous_value = self.parameter_cache.get(param.code, "")
                        readable_value = self._get_readable_value(param, previous_value) if previous_value != "" else ""
                        item.setText(2, readable_value)
                        item.setData(2, Qt.EditRole, previous_value)
                except (ValueError, TypeError):
                    # Revert to previous value if conversion fails
                    previous_value = self.parameter_cache.get(param.code, "")
                    readable_value = self._get_readable_value(param, previous_value) if previous_value != "" else ""
                    item.setText(2, readable_value)
                    item.setData(2, Qt.EditRole, previous_value)

    def read_visible_parameters(self):
        if not self.modbus_client.connected:
            self.main_app.status_label.setText(self.main_app.language_manager.get_text("status_no_modbus_connection"));
            return
        root = self.tree_widget.invisibleRootItem()
        self.main_app.status_label.setText(f"{self.main_app.language_manager.get_text('status_reading_parameters')} {root.childCount()} {self.main_app.language_manager.get_text('status_parameters')}")
        QApplication.processEvents()
        
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
                    # Get parameter properties using helper method
                    is_32bit, is_signed = self._get_parameter_properties(param)
                    
                    # Debug-Information
                    bit_width = "32-Bit" if is_32bit else "16-Bit"
                    signed_str = "signed" if is_signed else "unsigned"
                    logger.debug(f"DEBUG: Lese Parameter {param.code} als {bit_width} {signed_str}")
                    
                    if is_32bit:
                        # 32-Bit-Parameter lesen
                        live_value = self.modbus_client.read_holding_register_32bit(int(param.decimal), is_signed=is_signed)
                    else:
                        # 16-Bit-Parameter lesen
                        logger.debug(f"DEBUG: Lese Parameter {param.code} als 16-Bit")
                        val = self.modbus_client.read_holding_register(int(param.decimal), count=1)
                        live_value = val[0] if val is not None else None
                    
                    if live_value is not None:
                        logger.debug(f"DEBUG: Parameter {param.code} erfolgreich gelesen: {live_value}")
                        readable_value = self._get_readable_value(param, live_value)
                        item.setText(2, readable_value)
                        item.setData(2, Qt.EditRole, live_value)
                        self.parameter_cache[param.code] = live_value # Store in cache
                        self.update_item_color(item, str(live_value))
                    else:
                        logger.debug(f"DEBUG: Parameter {param.code} konnte nicht gelesen werden")
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
                new_val = item.data(2, Qt.EditRole)
                
                if new_val is None: new_val = item.text(2)

                try:
                    check_val_num = float(new_val)
                    if not self.main_app._validate_parameter(param, check_val_num):
                        continue # Validation failed in main_app

                    val_to_write = int(check_val_num)
                    
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
                        written_count += 1
                except (ValueError, TypeError) as e:
                    # More specific error handling for conversion errors
                    error_msg = f"{self.main_app.language_manager.get_text('status_error_convert_to_number')} '{new_val}' {self.main_app.language_manager.get_text('status_for')} {param.code}: {str(e)}"
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
                    readable_val = self._get_readable_value(param, imported_val)
                    item.setText(2, readable_val)
                    item.setData(2, Qt.EditRole, imported_val)
                    self.parameter_cache[param.code] = imported_val # Store imported value in cache
                    for j in range(item.columnCount()):
                        item.setBackground(j, QColor("orange"))

    def update_item_color(self, item, current_value):
        # This function should only be called when signals on the tree are blocked
        default_val_str = item.text(4)
        is_default = False
        try:
            if float(default_val_str) == float(current_value):
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
        if operation == "Lesen":
            logger.log_modbus_operation(operation, int(param.decimal), False, error_msg=str(exception))
            logger.error(f"Modbus-{operation}fehler bei Parameter {param.code} (Register {int(param.decimal)}): {str(exception)}")
        else:  # Schreiben
            logger.log_modbus_operation(operation, int(param.decimal), False, value, error_msg=str(exception))
            print(f"Modbus-{operation}fehler bei Parameter {param.code} (Register {int(param.decimal)}): {str(exception)}")
        
        if operation == "Lesen":
            item.setText(2, self.main_app.language_manager.get_text("text_read_error"))
        else:  # Schreiben
            item.setText(2, self.main_app.language_manager.get_text("text_write_error"))
        # Markiere das Element mit rotem Hintergrund, um auf den Fehler hinzuweisen
        for j in range(item.columnCount()):
            item.setBackground(j, QColor("#ffcccc"))  # Helles Rot
    
    def _handle_general_error(self, item, param, exception, operation):
        """Common error handling method for general exceptions"""
        error_msg = f"Unerwarteter Fehler beim {operation} von Parameter {param.code} (Register {int(param.decimal)}): {str(exception)}"
        logger.log_general_error(error_msg)
        logger.error(error_msg)
        if operation == "Schreiben":
            print(error_msg)
        
        if operation == "Lesen":
            item.setText(2, self.main_app.language_manager.get_text("text_read_error"))
        else:  # Schreiben
            item.setText(2, self.main_app.language_manager.get_text("text_write_error"))
        # Markiere das Element mit rotem Hintergrund, um auf den Fehler hinzuweisen
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
