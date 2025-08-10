from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QFormLayout, 
                             QComboBox, QLineEdit, QPushButton, QCheckBox)

class ConnectionTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_app = parent

        layout = QVBoxLayout(self)
        self.connection_group = QGroupBox(self.main_app.language_manager.get_text("group_modbus_connection_settings"))
        form_layout = self.create_form_layout()
        self.connection_group.setLayout(form_layout)
        
        self.connect_button = QPushButton(self.main_app.language_manager.get_text("button_connect"))

        layout.addWidget(self.connection_group)
        layout.addWidget(self.connect_button)
        layout.addStretch(1)

    def create_form_layout(self):
        form_layout = QFormLayout()

        self.com_port_input = QComboBox()
        self.com_port_input.addItems([f"COM{i}" for i in range(1, 10)])
        self.com_port_input.setEditable(True)
        form_layout.addRow(self.main_app.language_manager.get_text("label_com_port") + ":", self.com_port_input)

        self.baud_rate_input = QComboBox()
        baud_rates = {
            f"2400 {self.main_app.language_manager.get_text('text_bps')}": 2400,
            f"4800 {self.main_app.language_manager.get_text('text_bps')}": 4800,
            f"9600 {self.main_app.language_manager.get_text('text_bps')}": 9600,
            f"19200 {self.main_app.language_manager.get_text('text_bps')}": 19200,
            f"38400 {self.main_app.language_manager.get_text('text_bps')}": 38400,
            f"57600 {self.main_app.language_manager.get_text('text_bps')}": 57600
        }
        for text, rate in baud_rates.items():
            self.baud_rate_input.addItem(text, rate)
        self.baud_rate_input.setCurrentText(f"19200 {self.main_app.language_manager.get_text('text_bps')}")
        form_layout.addRow(self.main_app.language_manager.get_text("label_baud_rate") + ":", self.baud_rate_input)

        self.data_bits_input = QComboBox()
        self.data_bits_input.addItems(["8", "7"])
        form_layout.addRow(self.main_app.language_manager.get_text("label_data_bits") + ":", self.data_bits_input)

        self.parity_input = QComboBox()
        self.parity_input.addItems(["N", "E", "O"])
        self.parity_input.setCurrentText("E")
        form_layout.addRow(self.main_app.language_manager.get_text("label_parity") + ":", self.parity_input)

        self.stop_bits_input = QComboBox()
        self.stop_bits_input.addItems(["1", "2"])
        self.stop_bits_input.setCurrentText("2")
        form_layout.addRow(self.main_app.language_manager.get_text("label_stop_bits") + ":", self.stop_bits_input)

        self.modbus_address_input = QLineEdit("1")
        form_layout.addRow(self.main_app.language_manager.get_text("label_modbus_address") + ":", self.modbus_address_input)

        self.simulation_checkbox = QCheckBox(self.main_app.language_manager.get_text("checkbox_simulation_mode"))
        form_layout.addRow(self.simulation_checkbox)

        
        return form_layout

    def get_connection_parameters(self):
        return {
            "port": self.com_port_input.currentText(),
            "baudrate": self.baud_rate_input.currentData(),
            "bytesize": int(self.data_bits_input.currentText()),
            "parity": self.parity_input.currentText(),
            "stopbits": int(self.stop_bits_input.currentText()),
            "slave_id": int(self.modbus_address_input.text())
        }

    def set_connected_state(self, connected):
        # The button is always enabled, its text changes
        self.connect_button.setText(
            self.main_app.language_manager.get_text("button_disconnect") if connected
            else self.main_app.language_manager.get_text("button_connect")
        )
        
        # Only the settings group gets disabled
        self.connection_group.setEnabled(not connected)
    
    def update_language(self, language_manager):
        """Update all text elements with the selected language"""
        # Update group box title
        self.connection_group.setTitle(language_manager.get_text("group_modbus_connection_settings"))
        
        # Update connect button
        self.connect_button.setText(
            language_manager.get_text("button_disconnect") if self.connect_button.text() == language_manager.get_text("button_disconnect")
            else language_manager.get_text("button_connect")
        )
        
        # Update simulation checkbox
        self.simulation_checkbox.setText(language_manager.get_text("checkbox_simulation_mode"))
        
        # Update form labels
        form_layout = self.connection_group.layout()
        
        # Update baud rate items
        baud_rates = {
            f"2400 {language_manager.get_text('text_bps')}": 2400,
            f"4800 {language_manager.get_text('text_bps')}": 4800,
            f"9600 {language_manager.get_text('text_bps')}": 9600,
            f"19200 {language_manager.get_text('text_bps')}": 19200,
            f"38400 {language_manager.get_text('text_bps')}": 38400,
            f"57600 {language_manager.get_text('text_bps')}": 57600
        }
        
        # Save current selection
        current_baud = self.baud_rate_input.currentData()
        
        # Clear and repopulate
        self.baud_rate_input.clear()
        for text, rate in baud_rates.items():
            self.baud_rate_input.addItem(text, rate)
        
        # Restore selection
        index = self.baud_rate_input.findData(current_baud)
        if index >= 0:
            self.baud_rate_input.setCurrentIndex(index)
        else:
            self.baud_rate_input.setCurrentText(f"19200 {language_manager.get_text('text_bps')}")