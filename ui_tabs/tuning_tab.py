from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QFormLayout, QComboBox, QLineEdit, QPushButton,
                             QCheckBox, QSplitter, QGridLayout, QLabel, QApplication)
import time
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QIntValidator, QFont
import pyqtgraph as pg
import numpy as np
from collections import deque
import math
import os
import sys

# Add parent directory to path to import modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from modbus_client import ModbusClient
from logger_config import logger

class TuningTab(QWidget):
    plot_control_signal = pyqtSignal(str)
    # Signal für VDI-Toggle-Events
    vdi_toggled = pyqtSignal(int, bool)  # (VDI-Nummer, Zustand)
    # Signal für VDO-Polling-Checkbox
    vdo_polling_toggled = pyqtSignal(bool)  # (Polling-Status)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_app = parent
        self.lines = {}
        self.start_time = None  # Startzeit für Realtime-Plot
        
        self.tuning_widgets = {}
        self.direct_cmd_widgets = {}
        self.vdi_buttons = []  # Speichert die VDI-Buttons
        self.vdo_polling_checkbox = None  # Checkbox für VDO-Polling
        
        # Variables for advanced plot features were removed, as PyQtGraph has built-in zoom and pan functionality
        
        # Status-Feedback-Timer für regelmäßige Updates
        self.status_timer = QTimer(self)
        self.status_timer.setInterval(5000)  # Alle 5 Sekunden aktualisieren
        self.status_timer.timeout.connect(self.update_status_feedback)
        self.status_timer.start()
        
        # Zähler für die Status-Updates
        self.update_counter = 0
        self.last_update_time = time.time()
        self.connection_status = "Verbunden"

        layout = QHBoxLayout(self)
        
        # Main splitter for the whole tab
        main_splitter = QSplitter(Qt.Horizontal)

        # Left side: All controls
        left_widget = QWidget()
        # Use a size policy that scales better with different screen resolutions
        # Calculate minimum width based on screen DPI for better 4K display support
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        dpi = screen.logicalDotsPerInch()
        # More conservative scaling for 4K displays - make it wider but still usable
        base_width = 600  # Significantly increased base width for wider field to show labels
        min_width = max(400, int(base_width * (dpi / 96.0) * 0.8))  # 96 DPI is standard, scale with 0.8 factor
        left_widget.setMinimumWidth(min_width)
        left_layout = QVBoxLayout(left_widget)
        self.tuning_group = self._create_tuning_parameters_group()
        self.direct_commands_group = self._create_direct_commands_group()
        self.vdi_group = self._create_vdi_buttons_group()
        self.plot_settings_group = self._create_plot_settings_group()
        left_layout.addWidget(self.tuning_group)
        left_layout.addWidget(self.direct_commands_group)
        left_layout.addWidget(self.vdi_group)
        left_layout.addWidget(self.plot_settings_group)
        left_layout.addStretch(1)
        
        # Right side: The Plot itself
        self.plot_group = self._create_realtime_plot_group()

        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(self.plot_group)
        main_splitter.setStretchFactor(0, 1) # Give more space to the left panel
        main_splitter.setStretchFactor(1, 1) # Give more space to the plot
        # Calculate splitter sizes based on DPI for better 4K display support
        # Significantly increase left panel width for better visibility of labels
        left_size = max(900, int(900 * (dpi / 96.0) * 0.9))  # Significantly increased base width and scaling factor
        right_size = max(950, int(950 * (dpi / 96.0)))  # Keep right panel size
        main_splitter.setSizes([left_size, right_size])

        layout.addWidget(main_splitter)
        self.set_enabled(False)


    def _create_tuning_parameters_group(self):
        group = QGroupBox(self.main_app.language_manager.get_text("group_tuning_parameters"))
        main_layout = QVBoxLayout(group)

        def create_param_row(p_code, attr_name):
            param = self.main_app.parameter_manager.get_parameter(p_code)
            if not param: return None, None
            
            widget = QLineEdit()
            validation_str = self._get_readable_validation_tooltip(param)
            widget.setToolTip(f"{param.name}\n{validation_str} {param.unit}")
            # Set a reasonable maximum width for the text field to leave space for labels
            widget.setMaximumWidth(100)

            read_btn, write_btn = QPushButton(self.main_app.language_manager.get_text("button_read")), QPushButton(self.main_app.language_manager.get_text("button_write"))
            # Set uniform sizes for buttons
            button_width = 80
            button_height = 25
            read_btn.setFixedSize(button_width, button_height)
            write_btn.setFixedSize(button_width, button_height)
            
            h_layout = QHBoxLayout()
            h_layout.addWidget(widget)
            h_layout.addWidget(read_btn)
            h_layout.addWidget(write_btn)
            # Add stretch to push widgets to the right
            h_layout.addStretch(1)
            # Ensure the layout doesn't expand too much
            h_layout.setContentsMargins(0, 0, 0, 0)
            
            self.tuning_widgets[attr_name] = {"param": param, "widget": widget, "read_btn": read_btn, "write_btn": write_btn, "type": "lineedit"}
            return f"{param.code} ({param.name}):", h_layout

        control_layout = QFormLayout()
        # Increase the width of the label column to ensure labels are visible
        control_layout.setLabelAlignment(Qt.AlignLeft)
        control_layout.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
        control_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        control_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        # Set spacing to ensure labels have enough space
        control_layout.setHorizontalSpacing(20)  # Increase horizontal spacing between label and field
        
        p0200_param = self.main_app.parameter_manager.get_parameter("P02-00")
        if p0200_param:
            self.p0200_widget = QComboBox()
            if p0200_param.validation and 'options' in p0200_param.validation:
                for key, value in p0200_param.validation['options'].items():
                    self.p0200_widget.addItem(f"{key}: {value}", userData=key)
            read_btn, write_btn = QPushButton(self.main_app.language_manager.get_text("button_read")), QPushButton(self.main_app.language_manager.get_text("button_write"))
            # Set uniform sizes for buttons
            button_width = 80
            button_height = 25
            read_btn.setFixedSize(button_width, button_height)
            write_btn.setFixedSize(button_width, button_height)
            # Set a reasonable maximum width for the combo box
            self.p0200_widget.setMaximumWidth(150)
            h_layout = QHBoxLayout()
            h_layout.addWidget(self.p0200_widget)
            h_layout.addWidget(read_btn); h_layout.addWidget(write_btn)
            # Add stretch to push widgets to the right
            h_layout.addStretch(1)
            control_layout.addRow(f"{p0200_param.code} ({p0200_param.name}):", h_layout)
            self.tuning_widgets["p0200"] = {"param": p0200_param, "widget": self.p0200_widget, "read_btn": read_btn, "write_btn": write_btn, "type": "combobox"}
        main_layout.addLayout(control_layout)

        self.gain_toggle_button = QPushButton(self.main_app.language_manager.get_text("button_switch_to_gain_set_2"))
        self.gain_toggle_button.clicked.connect(self.toggle_gain_set_view)
        # Make the button span the full width of the group
        self.gain_toggle_button.setMinimumHeight(25)
        main_layout.addWidget(self.gain_toggle_button)

        info_label = QLabel(f"<b>{self.main_app.language_manager.get_text('label_note')}:</b> {self.main_app.language_manager.get_text('text_gain_set_activation')}")
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)

        self.gain_set1_group = QGroupBox(self.main_app.language_manager.get_text("group_gain_parameter_set_1"))
        set1_layout = QFormLayout(self.gain_set1_group)
        # Increase the width of the label column to ensure labels are visible
        set1_layout.setLabelAlignment(Qt.AlignLeft)
        set1_layout.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
        set1_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        set1_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        # Set spacing to ensure labels have enough space
        set1_layout.setHorizontalSpacing(20)  # Increase horizontal spacing between label and field
        
        set1_configs = [("P08-00", "p0800"), ("P08-01", "p0801"), ("P08-02", "p0802")]
        for p_code, attr in set1_configs:
            label, layout = create_param_row(p_code, attr)
            if label: set1_layout.addRow(label, layout)
        main_layout.addWidget(self.gain_set1_group)

        self.gain_set2_group = QGroupBox(self.main_app.language_manager.get_text("group_gain_parameter_set_2"))
        set2_layout = QFormLayout(self.gain_set2_group)
        # Increase the width of the label column to ensure labels are visible
        set2_layout.setLabelAlignment(Qt.AlignLeft)
        set2_layout.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
        set2_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        set2_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        # Set spacing to ensure labels have enough space
        set2_layout.setHorizontalSpacing(20)  # Increase horizontal spacing between label and field
        
        set2_configs = [("P08-03", "p0803"), ("P08-04", "p0804"), ("P08-05", "p0805")]
        for p_code, attr in set2_configs:
            label, layout = create_param_row(p_code, attr)
            if label: set2_layout.addRow(label, layout)
        self.gain_set2_group.setVisible(False)
        main_layout.addWidget(self.gain_set2_group)
        
        # --- Other Parameters Group ---
        self.other_group = QGroupBox(self.main_app.language_manager.get_text("group_other_tuning_parameters"))
        other_layout = QFormLayout(self.other_group)
        # Increase the width of the label column to ensure labels are visible
        other_layout.setLabelAlignment(Qt.AlignLeft)
        other_layout.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
        other_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        other_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        # Set spacing to ensure labels have enough space
        other_layout.setHorizontalSpacing(20)  # Increase horizontal spacing between label and field
        
        other_configs = [("P09-01", "p0901"), ("P08-15", "p0815")]
        for p_code, attr in other_configs:
            label, layout = create_param_row(p_code, attr)
            if label: other_layout.addRow(label, layout)
        main_layout.addWidget(self.other_group)
        
        main_layout.addStretch(1)
        return group

    def _create_direct_commands_group(self):
        group = QGroupBox(self.main_app.language_manager.get_text("group_direct_commands"))
        layout = QFormLayout()
        # Increase the width of the label column to ensure labels are visible
        layout.setLabelAlignment(Qt.AlignLeft)
        layout.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
        layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        # Set spacing to ensure labels have enough space
        layout.setHorizontalSpacing(20)  # Increase horizontal spacing between label and field
        
        params = {"P06-03": "p0603", "P07-03": "p0703", "P05-05": "p0505"}
        for p_code, attr_name in params.items():
            param = self.main_app.parameter_manager.get_parameter(p_code)
            if param:
                le, send_btn = QLineEdit("0"), QPushButton(self.main_app.language_manager.get_text("button_send"))
                # Set uniform size for send button
                send_btn.setFixedSize(80, 25)
                # Set a reasonable maximum width for the text field to leave space for labels
                le.setMaximumWidth(100)
                h_layout = QHBoxLayout(); h_layout.addWidget(le); h_layout.addWidget(send_btn)
                # Add stretch to push widgets to the right
                h_layout.addStretch(1)
                layout.addRow(f"{p_code} ({param.name}):", h_layout)
                self.direct_cmd_widgets[attr_name] = {"param": param, "widget": le, "send_btn": send_btn}
        self.stop_all_btn = QPushButton(self.main_app.language_manager.get_text("button_set_all_commands_to_zero"))
        # Make the button span the full width of the group
        self.stop_all_btn.setMinimumHeight(25)
        layout.addRow(self.stop_all_btn)
        group.setLayout(layout)
        return group

    def _create_plot_settings_group(self):
        group = QGroupBox(self.main_app.language_manager.get_text("group_plot_settings"))
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        
        # Nur noch die Zeitfenster-Breite einstellen
        self.time_window_input = QLineEdit("20")
        self.time_window_input.setValidator(QIntValidator(1, 600, self)) # 1s to 600s (10 minutes)
        form_layout.addRow(self.main_app.language_manager.get_text("label_visible_time") + " (s):", self.time_window_input)
        
        # Watchdog-Timeout für den Plot-Worker
        self.watchdog_timeout_input = QLineEdit("10")
        self.watchdog_timeout_input.setValidator(QIntValidator(1, 60, self)) # 1s to 60s
        form_layout.addRow(self.main_app.language_manager.get_text("label_watchdog_timeout") + " (s):", self.watchdog_timeout_input)
        
        # Button zum Anwenden der Konfiguration
        self.apply_config_btn = QPushButton(self.main_app.language_manager.get_text("button_apply_config"))
        self.apply_config_btn.clicked.connect(self.apply_plot_worker_config)
        form_layout.addRow(self.apply_config_btn)
        
        # Informationstext über Zoom-Funktionen wurde entfernt, da PyQtGraph bereits eingebaute Zoom- und Pan-Funktionen hat
        
        # Der "Anwenden"-Button wurde entfernt, da die Plot-Einstellungen jetzt automatisch übernommen werden
        manual_ctrl_layout = QHBoxLayout()
        start_btn = QPushButton(self.main_app.language_manager.get_text("button_start")); start_btn.clicked.connect(lambda: self.plot_control_signal.emit("start"))
        stop_btn = QPushButton(self.main_app.language_manager.get_text("button_stop")); stop_btn.clicked.connect(lambda: self.plot_control_signal.emit("stop"))
        clear_btn = QPushButton(self.main_app.language_manager.get_text("button_clear")); clear_btn.clicked.connect(lambda: self.plot_control_signal.emit("clear"))
        
        # Set uniform sizes for plot control buttons
        button_width = 80
        button_height = 25
        start_btn.setFixedSize(button_width, button_height)
        stop_btn.setFixedSize(button_width, button_height)
        clear_btn.setFixedSize(button_width, button_height)
        
        manual_ctrl_layout.addWidget(start_btn); manual_ctrl_layout.addWidget(stop_btn); manual_ctrl_layout.addWidget(clear_btn)
        form_layout.addRow(self.main_app.language_manager.get_text("label_manual_control") + ":", manual_ctrl_layout)
        
        # Erweiterte Plot-Funktionen wurden entfernt, da PyQtGraph bereits eingebaute Zoom- und Pan-Funktionen hat
        
        self.legend_group = QGroupBox(self.main_app.language_manager.get_text("group_legend_visibility"))
        self.legend_layout = QGridLayout()
        self.legend_group.setLayout(self.legend_layout)
        layout.addLayout(form_layout)
        layout.addWidget(self.legend_group)
        
        # VDI-Buttons Gruppe unter den Plot-Einstellungen hinzufügen
        # self.vdi_group = self._create_vdi_buttons_group()
        # layout.addWidget(self.vdi_group)

        layout.addStretch(1)
        group.setLayout(layout)
        return group
    
    def _create_vdi_buttons_group(self):
        """Erstellt eine Gruppe mit 3 VDI-Buttons und 2 VDO-Status-Labels unterhalb der Plot-Einstellungen"""
        group = QGroupBox(self.main_app.language_manager.get_text("group_virtual_digital_io_vdi_vdo"))
        layout = QGridLayout()
        
        # Erstelle 3 VDI-Buttons in der ersten Reihe
        for i in range(3):
            toggle_button = QPushButton(f"VDI {i+1}")
            toggle_button.setCheckable(True)
            toggle_button.clicked.connect(lambda checked, idx=i+1: self.vdi_toggled.emit(idx, checked))
            toggle_button.setEnabled(False)  # Standardmäßig deaktiviert
            
            # Setze die gleiche Größe wie bei den VDI-Buttons im VDI-Tab
            screen = QApplication.primaryScreen()
            if screen:
                # Berechne DPI-Verhältnis (96 DPI = Standard-Referenz)
                dpi_ratio = screen.logicalDotsPerInch() / 96.0
                
                # Begrenze die Skalierung, um zu große Elemente zu vermeiden
                max_scale = 1.5  # Maximale Skalierung auf 150%
                effective_scale = min(dpi_ratio, max_scale)
                
                # Passe die Größe der Buttons dynamisch an (einheitlich mit anderen Buttons)
                base_width = 80  # Einheitliche Breite mit anderen Buttons
                base_height = 25  # Einheitliche Höhe mit anderen Buttons
                scaled_width = int(base_width * effective_scale)
                scaled_height = int(base_height * effective_scale)
                toggle_button.setFixedSize(scaled_width, scaled_height)
                
                # Passe die Schriftgröße dynamisch an
                base_font_size = 8  # Basis-Schriftgröße
                scaled_font_size = max(int(base_font_size * effective_scale), 7)  # Mindestens 7pt
                font = QFont()
                font.setPointSize(scaled_font_size)
                font.setBold(True)  # Mache den Text fett, damit der Button besser sichtbar ist
                toggle_button.setFont(font)
            else:
                # Fallback, wenn keine Bildschirminformationen verfügbar sind
                toggle_button.setFixedSize(80, 25)  # Einheitliche Größe mit anderen Buttons
                font = QFont()
                font.setPointSize(8)
                font.setBold(True)  # Mache den Text fett, damit der Button besser sichtbar ist
                toggle_button.setFont(font)
            
            # Mache den Button deutlich sichtbar
            toggle_button.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    border: 2px solid #333333;
                    border-radius: 3px;
                    padding: 2px;
                    font-weight: bold;
                }
                QPushButton:checked {
                    background-color: #90EE90;  /* Hellgrün für aktivierten Zustand */
                    border: 2px solid #008000;
                }
                QPushButton:disabled {
                    background-color: #e0e0e0;
                    border: 2px solid #999999;
                    color: #666666;
                }
            """)
            
            layout.addWidget(toggle_button, 0, i)  # Erste Reihe, Spalte i
            self.vdi_buttons.append(toggle_button)
        
        # Erstelle 3 VDO-Status-Labels in der zweiten Reihe
        self.vdo_labels = []  # Speichert die VDO-Labels
        for i in range(3):
            vdo_label = QLabel(f"VDO {i+1}")
            vdo_label.setAlignment(Qt.AlignCenter)
            vdo_label.setEnabled(False)  # Standardmäßig deaktiviert
            
            # Setze die gleiche Größe wie bei den VDI-Buttons
            screen = QApplication.primaryScreen()
            if screen:
                # Berechne DPI-Verhältnis (96 DPI = Standard-Referenz)
                dpi_ratio = screen.logicalDotsPerInch() / 96.0
                
                # Begrenze die Skalierung, um zu große Elemente zu vermeiden
                max_scale = 1.5  # Maximale Skalierung auf 150%
                effective_scale = min(dpi_ratio, max_scale)
                
                # Passe die Größe der Labels dynamisch an (einheitlich mit anderen Buttons)
                base_width = 80  # Einheitliche Breite mit anderen Buttons
                base_height = 25  # Einheitliche Höhe mit anderen Buttons
                scaled_width = int(base_width * effective_scale)
                scaled_height = int(base_height * effective_scale)
                vdo_label.setFixedSize(scaled_width, scaled_height)
                
                # Passe die Schriftgröße dynamisch an
                base_font_size = 8  # Basis-Schriftgröße
                scaled_font_size = max(int(base_font_size * effective_scale), 7)  # Mindestens 7pt
                font = QFont()
                font.setPointSize(scaled_font_size)
                font.setBold(True)  # Mache den Text fett, damit das Label besser sichtbar ist
                vdo_label.setFont(font)
            else:
                # Fallback, wenn keine Bildschirminformationen verfügbar sind
                vdo_label.setFixedSize(80, 25)  # Einheitliche Größe mit anderen Buttons
                font = QFont()
                font.setPointSize(8)
                font.setBold(True)  # Mache den Text fett, damit das Label besser sichtbar ist
                vdo_label.setFont(font)
            
            # Mache das Label deutlich sichtbar mit einem anderen Stil als die VDI-Buttons
            vdo_label.setStyleSheet("""
                QLabel {
                    background-color: #f0f0f0;
                    border: 2px solid #3333cc;  /* Blaue Umrandung für VDOs zur Unterscheidung */
                    border-radius: 3px;
                    padding: 2px;
                    font-weight: bold;
                }
                QLabel:disabled {
                    background-color: #e0e0e0;
                    border: 2px solid #9999cc;
                    color: #666666;
                }
            """)
            
            layout.addWidget(vdo_label, 1, i)  # Zweite Reihe, Spalte i
            self.vdo_labels.append(vdo_label)
        
        # Füge einen vertikalen Spacer zwischen den Reihen hinzu
        layout.setVerticalSpacing(10)
        
        # Füge eine Checkbox für VDO-Polling hinzu
        self.vdo_polling_checkbox = QCheckBox(self.main_app.language_manager.get_text("checkbox_vdo_polling"))
        self.vdo_polling_checkbox.setChecked(False)  # Standardmäßig deaktiviert
        self.vdo_polling_checkbox.stateChanged.connect(self.on_vdo_polling_toggled)
        layout.addWidget(self.vdo_polling_checkbox, 2, 0, 1, 3)  # Dritte Reihe, über alle drei Spalten
        
        group.setLayout(layout)
        return group
    
    def _create_realtime_plot_group(self):
        group = QGroupBox(self.main_app.language_manager.get_text("group_realtime_data_plot"))
        plot_layout = QVBoxLayout()
        
        # Configure PyQtGraph for better performance
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        
        # Create PlotWidget instead of Matplotlib Figure
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', self.main_app.language_manager.get_text("plot_ylabel_value"))
        self.plot_widget.setLabel('bottom', self.main_app.language_manager.get_text("plot_xlabel_time") + " (s)")
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.addLegend()
        
        # Enable antialiasing for prettier plots
        self.plot_widget.setAntialiasing(True)
        
        plot_layout.addWidget(self.plot_widget)
        
        # Add live values in a single horizontal row below the plot
        self.live_values_group = QGroupBox(self.main_app.language_manager.get_text("group_live_values"))
        live_values_layout = QHBoxLayout()  # Use QHBoxLayout for horizontal arrangement
        
        self.live_value_widgets = {}
        self.plot_codes = ["P0B-00", "P0B-01", "P0B-15", "P0B-02", "P0B-24", "P0B-58"]
        for code in self.plot_codes:
            param = self.main_app.parameter_manager.get_parameter(code)
            if not param:
                continue
            
            # Create a horizontal layout for each live value (label: value)
            value_layout = QHBoxLayout()
            value_layout.setSpacing(2)  # Small spacing between label and value
            value_layout.setContentsMargins(2, 2, 2, 2)  # Small margins
            
            label = QLabel(f"{param.code} ({param.unit}):")  # Use param.code and param.unit
            
            value_edit = QLineEdit(self.main_app.language_manager.get_text("text_not_available"))
            value_edit.setReadOnly(True)
            value_edit.setFixedWidth(50)  # Compact width for the value
            
            value_layout.addWidget(label)
            value_layout.addWidget(value_edit)
            
            live_values_layout.addLayout(value_layout)
            self.live_value_widgets[code] = value_edit
        
        # Add stretch to push items to the left
        live_values_layout.addStretch(1)
        
        # Set minimal spacing and margins
        live_values_layout.setSpacing(8)
        live_values_layout.setContentsMargins(5, 2, 5, 2)  # Minimal top/bottom margins
        
        # Set a fixed, minimal height for the group
        self.live_values_group.setFixedHeight(40)
        
        self.live_values_group.setLayout(live_values_layout)
        plot_layout.addWidget(self.live_values_group)
        
        group.setLayout(plot_layout)
        self.clear_plot(stopped_by_user=False)
        return group

    def get_plot_settings(self):
        return int(self.time_window_input.text())

    def update_plot(self, new_values):
        """Receives new data values from main_app and updates the plot."""
        import time
        
        try:
            # Initialisiere die Startzeit beim ersten Aufruf
            if self.start_time is None:
                self.start_time = time.time()
            
            # Aktuelle Zeit für Realtime-Plot
            current_time = time.time()
            # Berechne die relative Zeit seit dem Start des Plots
            relative_time = current_time - self.start_time

            # Update live value displays
            missing_data_count = 0
            for code, val in new_values.items():
                if code in self.live_value_widgets:
                    self.live_value_widgets[code].setText(str(val))
                else:
                    missing_data_count += 1

            # Hole die aktuellen Plot-Einstellungen
            try:
                # Nur noch die Zeitfenster-Breite verwenden
                visible_time_seconds = int(self.time_window_input.text())
                # Validierung des Zeitfensters
                if visible_time_seconds < 1:
                    visible_time_seconds = 1
                elif visible_time_seconds > 600:  # Max 10 Minuten
                    visible_time_seconds = 600
            except (ValueError, TypeError):
                # Fallback-Werte bei ungültigen Eingaben
                visible_time_seconds = 20.0  # 20 Sekunden Standard

            # Setze die x-Achse auf den sichtbaren Zeitbereich, um die neuesten Daten anzuzeigen
            # Dies sorgt dafür, dass der Plot automatisch mit den neuesten Daten mitverschoben wird
            self.plot_widget.setXRange(relative_time - visible_time_seconds, relative_time)

            # Maximale Anzahl von Datenpunkte - sehr hoch für maximale Datenaufzeichnung
            max_data_points = 1000000

            # Update all visible curves with the new data point
            for code, curve in self.lines.items():
                if curve.isVisible() and code in new_values:
                    # Validiere den Wert vor der Verarbeitung
                    if not self._validate_plot_value(code, new_values[code]):
                        logger.warning(f"Ungültiger Wert für {code}: {new_values[code]}")
                        continue
                    
                    # Hole die aktuellen Daten der Kurve
                    current_data = curve.getData()
                    if current_data[0] is not None and current_data[1] is not None:
                        # Füge den neuen Datenpunkt hinzu
                        time_data = np.append(current_data[0], relative_time)
                        value_data = np.append(current_data[1], new_values[code])
                        
                        # Begrenze die Daten auf das sichtbare Zeitfenster
                        if len(time_data) > 0 and time_data[-1] - time_data[0] > visible_time_seconds:
                            # Finde den Index, ab dem die Daten im sichtbaren Bereich liegen
                            min_time = time_data[-1] - visible_time_seconds
                            visible_indices = np.where(time_data >= min_time)[0]
                            if len(visible_indices) > 0:
                                time_data = time_data[visible_indices[0]:]
                                value_data = value_data[visible_indices[0]:]
                        
                        # Zusätzliche Begrenzung der Datenpunkte auf maximale Anzahl
                        if len(time_data) > max_data_points:
                            time_data = time_data[-max_data_points:]
                            value_data = value_data[-max_data_points:]
                        
                        # Aktualisiere die Kurve
                        curve.setData(time_data, value_data)
                    else:
                        # Erste Datenpunkte für die Kurve
                        curve.setData(np.array([relative_time]), np.array([new_values[code]]))
            
            # Zeige den Status der Datenaktualisierung an
            total_visible_codes = sum(1 for curve in self.lines.values() if curve.isVisible())
            actual_data_count = len(new_values)
            
            if missing_data_count > 0:
                status_text = f"{self.main_app.language_manager.get_text('status_plot_updated')} ({missing_data_count} {self.main_app.language_manager.get_text('status_values_missing')})"
            elif actual_data_count < total_visible_codes:
                status_text = f"{self.main_app.language_manager.get_text('status_plot_updated')} ({total_visible_codes - actual_data_count} {self.main_app.language_manager.get_text('status_channels_without_data')})"
            else:
                status_text = f"{self.main_app.language_manager.get_text('status_plot_updated')} ({self.main_app.language_manager.get_text('status_all_values_present')})"
            
            # Status in der UI anzeigen
            if hasattr(self.main_app, 'status_label'):
                self.main_app.status_label.setText(status_text)
                
        except Exception as e:
            logger.error(f"Fehler bei der Plot-Aktualisierung: {e}", exc_info=True)
            # Zeige Fehlermeldung in der Statusleiste
            if hasattr(self.main_app, 'status_label'):
                self.main_app.status_label.setText(f"{self.main_app.language_manager.get_text('status_plot_error')}: {str(e)}")
            # Optional: Plot neu initialisieren bei schweren Fehlern
            try:
                self.clear_plot(stopped_by_user=False)
            except Exception as clear_error:
                logger.error(f"Fehler bei der Plot-Neuinitialisierung: {clear_error}", exc_info=True)
    
    def update_status_feedback(self):
        """Aktualisiert das Status-Feedback für den Benutzer"""
        try:
            # Update-Zähler erhöhen
            self.update_counter += 1
            
            # Aktuelle Statusinformationen sammeln
            current_time = time.time()
            runtime = current_time - self.last_update_time
            
            # Verbindungszustand prüfen
            if hasattr(self.main_app, 'modbus_client'):
                if self.main_app.modbus_client.connected:
                    self.connection_status = self.main_app.language_manager.get_text("status_connection_success")
                elif hasattr(self.main_app, 'simulation_mode') and self.main_app.simulation_mode:
                    self.connection_status = self.main_app.language_manager.get_text("status_simulation_started")
                else:
                    self.connection_status = self.main_app.language_manager.get_text("status_disconnected")
            
            # Plot-Worker-Status prüfen
            worker_status = self.main_app.language_manager.get_text("status_inactive")
            if hasattr(self.main_app, 'plot_worker'):
                if self.main_app.plot_worker.isRunning():
                    worker_status = self.main_app.language_manager.get_text("status_active")
                    
                    # Prüfe auf Fehler im Worker
                    if hasattr(self.main_app.plot_worker, 'consecutive_failures'):
                        failures = self.main_app.plot_worker.consecutive_failures
                        if failures > 0:
                            worker_status = f"{self.main_app.language_manager.get_text('status_active')} ({failures} {self.main_app.language_manager.get_text('status_errors')})"
            
            # Anzahl der sichtbaren Linien zählen
            visible_lines = sum(1 for line in self.lines.values() if line.isVisible())
            
            # Statusmeldung erstellen
            status_parts = [
                f"{self.main_app.language_manager.get_text('status_plot')}: {worker_status}",
                f"{self.main_app.language_manager.get_text('status_connection')}: {self.connection_status}",
                f"{self.main_app.language_manager.get_text('status_visible_lines')}: {visible_lines}/{len(self.lines)}",
                f"{self.main_app.language_manager.get_text('status_updates')}: {self.update_counter}",
                f"{self.main_app.language_manager.get_text('status_runtime')}: {int(runtime)}s"
            ]
            
            status_text = " | ".join(status_parts)
            
            # Status in der Statusleiste anzeigen, wenn verfügbar
            if hasattr(self.main_app, 'status_label'):
                # Nur aktualisieren, wenn nicht bereits eine wichtige Nachricht angezeigt wird
                current_status = self.main_app.status_label.text()
                if not any(keyword in current_status for keyword in [
                    self.main_app.language_manager.get_text("status_error"),
                    self.main_app.language_manager.get_text("status_connection_error"),
                    self.main_app.language_manager.get_text("status_timeout"),
                    self.main_app.language_manager.get_text("status_export")
                ]):
                    self.main_app.status_label.setText(status_text)
            
            # Spezielle Warnungen bei Problemen
            if self.connection_status == self.main_app.language_manager.get_text("status_disconnected"):
                logger.warning(f"Plot-Status-Feedback: {self.main_app.language_manager.get_text('status_connection_disconnected')}")
            elif self.main_app.language_manager.get_text("status_error") in worker_status:
                logger.warning(f"Plot-Status-Feedback: {self.main_app.language_manager.get_text('status_worker_error')}: {worker_status}")
                
        except Exception as e:
            logger.error(f"Fehler bei der Status-Feedback-Aktualisierung: {e}", exc_info=True)
            # Bei Fehlern im Status-Feedback nicht weiter stören, einfach mit dem nächsten Update fortfahren
    
    def apply_plot_worker_config(self):
        """Wendet die Konfigurationseinstellungen für den Plot-Worker an"""
        try:
            # Werte aus den Eingabefeldern lesen
            watchdog_timeout = int(self.watchdog_timeout_input.text())
            
            # Validierung der Werte
            if not (1 <= watchdog_timeout <= 60):
                raise ValueError(f"Watchdog-Timeout muss zwischen 1 und 60 Sekunden liegen")
            
            # Konfigurations-Dictionary erstellen
            new_config = {
                'min_update_interval': 1,  # Minimales Update-Intervall für maximale Geschwindigkeit
                'max_update_interval': 10,  # Kurzes maximales Intervall
                'watchdog_timeout': watchdog_timeout,
                'max_data_points': 1000000  # Sehr hohe Anzahl für maximale Datenaufzeichnung
            }
            
            # Konfiguration an den Plot-Worker übergeben
            if hasattr(self.main_app, 'plot_worker'):
                self.main_app.plot_worker.update_config(new_config)
                
                # Bestätigung in der Statusleiste anzeigen
                if hasattr(self.main_app, 'status_label'):
                    self.main_app.status_label.setText(self.main_app.language_manager.get_text("status_plot_worker_config_updated"))
                
                logger.info(f"Plot-Worker-Konfiguration aktualisiert: {new_config}")
            else:
                logger.warning("Plot-Worker nicht verfügbar für Konfigurationsaktualisierung")
                
        except ValueError as e:
            # Fehler bei der Validierung der Eingaben
            error_msg = f"{self.main_app.language_manager.get_text('status_invalid_input')}: {str(e)}"
            logger.error(error_msg)
            if hasattr(self.main_app, 'status_label'):
                self.main_app.status_label.setText(error_msg)
        except Exception as e:
            # Unerwarteter Fehler
            error_msg = f"{self.main_app.language_manager.get_text('status_config_update_error')}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            if hasattr(self.main_app, 'status_label'):
                self.main_app.status_label.setText(error_msg)
        
    def clear_plot(self, stopped_by_user=True):
        if stopped_by_user and hasattr(self.main_app, 'plot_worker') and self.main_app.plot_worker.isRunning():
            self.plot_control_signal.emit("stop")
        self.start_time = None  # Startzeit zurücksetzen für neuen Plot
        while self.legend_layout.count():
            child = self.legend_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        
        # Clear the plot widget
        self.plot_widget.clear()
        self.plot_widget.setTitle(self.main_app.language_manager.get_text("plot_title_realtime_servo_data"))
        self.plot_widget.setLabel('left', self.main_app.language_manager.get_text("plot_ylabel_value"))
        self.plot_widget.setLabel('bottom', self.main_app.language_manager.get_text("plot_xlabel_time") + " (s)")
        self.plot_widget.showGrid(x=True, y=True)
        
        # Define colors for each plot line
        colors = ['r', 'g', 'b', 'c', 'm']
        
        # Create plot curves with PyQtGraph
        self.lines = {}
        for i, code in enumerate(self.plot_codes):
            param = self.main_app.parameter_manager.get_parameter(code)
            if not param:
                continue
            color = colors[i % len(colors)]
            curve = self.plot_widget.plot(pen=pg.mkPen(color, width=2), name=f"{param.code} ({param.unit})")
            self.lines[code] = curve
        
        for i, (code, curve) in enumerate(self.lines.items()):
            checkbox = QCheckBox(curve.name()); checkbox.setChecked(True)
            checkbox.stateChanged.connect(lambda state, c=code: self.update_plot_visibility(c, state))
            row, col = divmod(i, 3)
            self.legend_layout.addWidget(checkbox, row, col)
        
        # Zurücksetzen des Flags für den initialen Bereich
        if hasattr(self, 'initial_range_set'):
            delattr(self, 'initial_range_set')
        

    def update_plot_visibility(self, code, state):
        if code in self.lines:
            is_visible = (state == Qt.Checked)
            self.lines[code].setVisible(is_visible)
            
            # Aktualisiere auch die Sichtbarkeit der Live-Werte
            if code in self.live_value_widgets:
                # Finde das übergeordnete Layout des Live-Wert-Widgets
                live_values_layout = self.live_values_group.layout()
                for i in range(live_values_layout.count()):
                    item = live_values_layout.itemAt(i)
                    if item.layout():
                        # Prüfe, ob dieses Layout das Widget für den aktuellen Code enthält
                        for j in range(item.layout().count()):
                            widget = item.layout().itemAt(j).widget()
                            if widget == self.live_value_widgets[code]:
                                # Deaktiviere/aktiviere das gesamte Layout für diesen Live-Wert
                                item.layout().setEnabled(is_visible)
                                break
            
            # Aktualisiere die Liste der sichtbaren Linien im Worker-Thread
            if hasattr(self.main_app, 'plot_worker') and self.main_app.plot_worker.isRunning():
                visible_lines = []
                for c, curve in self.lines.items():
                    if curve.isVisible():
                        visible_lines.append(c)
                self.main_app.plot_worker.update_visible_lines(visible_lines)
            
            # Update the legend in PyQtGraph
            self.plot_widget.getPlotItem().legend.update()

    def set_enabled(self, enabled):
        self.tuning_group.setEnabled(enabled)
        self.direct_commands_group.setEnabled(enabled)
        self.vdi_group.setEnabled(enabled)
        
        # Aktiviere/deaktiviere die VDI-Buttons
        for button in self.vdi_buttons:
            button.setEnabled(enabled)
        
        # Aktiviere/deaktiviere die VDO-Labels
        for label in self.vdo_labels:
            label.setEnabled(enabled)
        
        # Aktiviere/deaktiviere die VDO-Polling-Checkbox
        if self.vdo_polling_checkbox:
            self.vdo_polling_checkbox.setEnabled(enabled)

    def _get_readable_validation_tooltip(self, param):
        if not param or not param.validation:
            return self.main_app.language_manager.get_text("validation_not_available")
        
        v_type = param.validation.get('type')
        if v_type == 'range':
            min_val = param.validation.get('min', 'N/A')
            max_val = param.validation.get('max', 'N/A')
            return f"{self.main_app.language_manager.get_text('validation_range')}: {min_val} ~ {max_val}"
        elif v_type == 'enum':
            return f"{self.main_app.language_manager.get_text('validation_options')}: {', '.join(param.validation.get('options', {}).values())}"
        return self.main_app.language_manager.get_text("validation_see_register_overview")

    def toggle_gain_set_view(self):
        is_set1_visible = self.gain_set1_group.isVisible()
        self.gain_set1_group.setVisible(not is_set1_visible)
        self.gain_set2_group.setVisible(is_set1_visible)
        self.gain_toggle_button.setText(
            self.main_app.language_manager.get_text("button_switch_to_gain_set_1") if is_set1_visible
            else self.main_app.language_manager.get_text("button_switch_to_gain_set_2")
        )
        
    def update_visible_time(self):
        # Diese Methode wird nicht mehr benötigt, da wir nur noch die Zeitfenster-Breite verwenden
        # Sie bleibt aus Kompatibilitätsgründen erhalten, tut aber nichts mehr
        pass
    
    # toggle_advanced_features-Methode wurde entfernt, da PyQtGraph bereits eingebaute Zoom- und Pan-Funktionen hat
    
    def update_language(self, language_manager):
        """Update all text elements with the selected language"""
        # Update group box titles
        self.tuning_group.setTitle(language_manager.get_text("group_tuning_parameters"))
        self.gain_set1_group.setTitle(language_manager.get_text("group_gain_parameter_set_1"))
        self.gain_set2_group.setTitle(language_manager.get_text("group_gain_parameter_set_2"))
        self.other_group.setTitle(language_manager.get_text("group_other_tuning_parameters"))
        self.direct_commands_group.setTitle(language_manager.get_text("group_direct_commands"))
        self.plot_settings_group.setTitle(language_manager.get_text("group_plot_settings"))
        self.plot_group.setTitle(language_manager.get_text("group_realtime_data_plot"))
        self.live_values_group.setTitle(language_manager.get_text("group_live_values"))
        self.legend_group.setTitle(language_manager.get_text("group_legend_visibility"))
        self.vdi_group.setTitle(language_manager.get_text("group_virtual_digital_io_vdi_vdo"))
        
        # Update button text without recreating layouts
        self.gain_toggle_button.setText(
            self.main_app.language_manager.get_text("button_switch_to_gain_set_2") if self.gain_set1_group.isVisible()
            else self.main_app.language_manager.get_text("button_switch_to_gain_set_1")
        )
        
        # Update info label
        info_label = self.tuning_group.findChild(QLabel)
        if info_label and info_label.text().startswith("Hinweis:"):
            info_label.setText(f"<b>{language_manager.get_text('label_note')}:</b> {language_manager.get_text('text_gain_set_activation')}")
        
        # Update button texts in all groups
        for widgets in self.tuning_widgets.values():
            if "read_btn" in widgets:
                widgets["read_btn"].setText(language_manager.get_text("button_read"))
            if "write_btn" in widgets:
                widgets["write_btn"].setText(language_manager.get_text("button_write"))
        
        for widgets in self.direct_cmd_widgets.values():
            if "send_btn" in widgets:
                widgets["send_btn"].setText(language_manager.get_text("button_send"))
        
        self.stop_all_btn.setText(language_manager.get_text("button_set_all_commands_to_zero"))
        
        # Update plot control buttons
        start_btn = self.plot_settings_group.findChild(QPushButton, language_manager.get_text("button_start"))
        if not start_btn:
            start_btn = self.plot_settings_group.findChild(QPushButton, "Start")
        if start_btn:
            start_btn.setText(language_manager.get_text("button_start"))
            
        stop_btn = self.plot_settings_group.findChild(QPushButton, language_manager.get_text("button_stop"))
        if not stop_btn:
            stop_btn = self.plot_settings_group.findChild(QPushButton, "Stop")
        if stop_btn:
            stop_btn.setText(language_manager.get_text("button_stop"))
            
        clear_btn = self.plot_settings_group.findChild(QPushButton, language_manager.get_text("button_clear"))
        if not clear_btn:
            clear_btn = self.plot_settings_group.findChild(QPushButton, "Löschen")
        if clear_btn:
            clear_btn.setText(language_manager.get_text("button_clear"))
        
        # Update plot labels
        self.plot_widget.setTitle(language_manager.get_text("plot_title_realtime_servo_data"))
        self.plot_widget.setLabel('left', language_manager.get_text("plot_ylabel_value"))
        self.plot_widget.setLabel('bottom', language_manager.get_text("plot_xlabel_time") + " (s)")
        
        # Update labels in tuning parameter layouts
        # Update control_layout (P02-00)
        tuning_layout = self.tuning_group.layout()
        if tuning_layout and tuning_layout.count() > 0:
            control_layout = tuning_layout.itemAt(0).layout()
            if control_layout:
                p0200_param = self.main_app.parameter_manager.get_parameter("P02-00")
                if p0200_param:
                    # Update the label in the first row
                    label_item = control_layout.itemAt(0)
                    if label_item and label_item.widget():
                        label_item.widget().setText(f"{p0200_param.code} ({p0200_param.name}):")
        
        # Update gain_set1_group labels
        set1_layout = self.gain_set1_group.layout()
        if set1_layout:
            set1_configs = [("P08-00", "p0800"), ("P08-01", "p0801"), ("P08-02", "p0802")]
            for i, (p_code, attr) in enumerate(set1_configs):
                param = self.main_app.parameter_manager.get_parameter(p_code)
                if param:
                    # Update the label in row i
                    label_item = set1_layout.itemAt(i, QFormLayout.LabelRole)
                    if label_item and label_item.widget():
                        label_item.widget().setText(f"{param.code} ({param.name}):")
                        # Ensure label is visible
                        label_item.widget().setVisible(True)
        
        # Update gain_set2_group labels
        set2_layout = self.gain_set2_group.layout()
        if set2_layout:
            set2_configs = [("P08-03", "p0803"), ("P08-04", "p0804"), ("P08-05", "p0805")]
            for i, (p_code, attr) in enumerate(set2_configs):
                param = self.main_app.parameter_manager.get_parameter(p_code)
                if param:
                    # Update the label in row i
                    label_item = set2_layout.itemAt(i, QFormLayout.LabelRole)
                    if label_item and label_item.widget():
                        label_item.widget().setText(f"{param.code} ({param.name}):")
                        # Ensure label is visible
                        label_item.widget().setVisible(True)
        
        # Update other_group labels
        other_layout = self.other_group.layout()
        if other_layout:
            other_configs = [("P09-01", "p0901"), ("P08-15", "p0815")]
            for i, (p_code, attr) in enumerate(other_configs):
                param = self.main_app.parameter_manager.get_parameter(p_code)
                if param:
                    # Update the label in row i
                    label_item = other_layout.itemAt(i, QFormLayout.LabelRole)
                    if label_item and label_item.widget():
                        label_item.widget().setText(f"{param.code} ({param.name}):")
                        # Ensure label is visible
                        label_item.widget().setVisible(True)
        
        # Update direct_commands_group labels
        direct_cmd_layout = self.direct_commands_group.layout()
        if direct_cmd_layout:
            params = {"P06-03": "p0603", "P07-03": "p0703", "P05-05": "p0505"}
            for i, (p_code, attr_name) in enumerate(params.items()):
                param = self.main_app.parameter_manager.get_parameter(p_code)
                if param:
                    # Update the label in row i
                    label_item = direct_cmd_layout.itemAt(i, QFormLayout.LabelRole)
                    if label_item and label_item.widget():
                        label_item.widget().setText(f"{p_code} ({param.name}):")
        
        # Update live value labels
        live_values_layout = self.live_values_group.layout()
        for i in range(live_values_layout.count()):
            item = live_values_layout.itemAt(i)
            if item.layout():
                label_item = item.layout().itemAt(0)
                if label_item and label_item.widget():
                    # Update label text based on parameter code
                    for code in self.plot_codes:
                        param = self.main_app.parameter_manager.get_parameter(code)
                        if param and param.code in label_item.widget().text():
                            label_item.widget().setText(f"{param.code} ({param.unit}):")
                            break
        
        # Update legend checkboxes
        self._clear_layout(self.legend_layout)
        for i, (code, curve) in enumerate(self.lines.items()):
            param = self.main_app.parameter_manager.get_parameter(code)
            if not param: continue
            checkbox = QCheckBox(f"{param.code} ({param.unit})")
            checkbox.setChecked(curve.isVisible())
            checkbox.stateChanged.connect(lambda state, c=code: self.update_plot_visibility(c, state))
            row, col = divmod(i, 3)
            self.legend_layout.addWidget(checkbox, row, col)

        # Update VDI button texts
        for i, button in enumerate(self.vdi_buttons):
            button.setText(f"VDI {i+1}")
        
        # Update VDO label texts
        for i, label in enumerate(self.vdo_labels):
            label.setText(f"VDO {i+1}")
        
        # Update VDO polling checkbox text
        if self.vdo_polling_checkbox:
            self.vdo_polling_checkbox.setText(language_manager.get_text("checkbox_vdo_polling"))
        
        # Update apply config button text
        if hasattr(self, 'apply_config_btn'):
            self.apply_config_btn.setText(language_manager.get_text("button_apply_config"))

        # Redraw canvas to update plot
        self.plot_widget.update()
    
    def update_vdi_buttons(self, vdi_value):
        """Aktualisiert den Zustand der VDI-Buttons basierend auf dem VDI-Registerwert"""
        for i in range(len(self.vdi_buttons)):
            # Berechne den Zustand des VDI-Bits
            is_on = (vdi_value >> i) & 1
            # Setze den Zustand des entsprechenden Buttons
            self.vdi_buttons[i].setChecked(is_on == 1)
    
    def update_vdo_labels(self, vdo_value):
        """Aktualisiert den Zustand der VDO-Labels basierend auf dem VDO-Registerwert"""
        for i in range(len(self.vdo_labels)):
            # Berechne den Zustand des VDO-Bits
            is_on = (vdo_value >> i) & 1
            # Setze den Zustand des entsprechenden Labels
            if is_on:
                self.vdo_labels[i].setStyleSheet("""
                    QLabel {
                        background-color: #90EE90;  /* Hellgrün für aktivierten Zustand */
                        border: 2px solid #008000;
                        border-radius: 3px;
                        padding: 2px;
                        font-weight: bold;
                    }
                """)
            else:
                self.vdo_labels[i].setStyleSheet("""
                    QLabel {
                        background-color: #f0f0f0;
                        border: 2px solid #3333cc;  /* Blaue Umrandung für VDOs zur Unterscheidung */
                        border-radius: 3px;
                        padding: 2px;
                        font-weight: bold;
                    }
                """)

    def _validate_plot_value(self, code, value):
        """Validiert einen Plot-Wert vor der Verarbeitung"""
        try:
            # Prüfe, ob der Wert numerisch ist
            if not isinstance(value, (int, float)):
                return False
            
            # Prüfe auf NaN oder Infinity
            if math.isnan(value) or math.isinf(value):
                return False
            
            # Codespezifische Validierung
            param = self.main_app.parameter_manager.get_parameter(code)
            if param and param.validation:
                v_type = param.validation.get('type')
                if v_type == 'range':
                    min_val = param.validation.get('min', -math.inf)
                    max_val = param.validation.get('max', math.inf)
                    if not (min_val <= value <= max_val):
                        logger.warning(f"Wert {value} für {code} ist außerhalb des Bereichs [{min_val}, {max_val}]")
                        return False
            
            return True
        except Exception as e:
            logger.error(f"Fehler bei der Validierung von {code}: {e}")
            return False

    def _clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    self._clear_layout(item.layout())
    
    def on_vdo_polling_toggled(self, state):
        """Wird aufgerufen, wenn die VDO-Polling-Checkbox umgeschaltet wird"""
        is_checked = state == Qt.Checked
        self.vdo_polling_toggled.emit(is_checked)
        logger.debug(f"VDO-Polling-Checkbox umgeschaltet: {is_checked}")
    
    def is_vdo_polling_enabled(self):
        """Gibt zurück, ob VDO-Polling aktiviert ist"""
        return self.vdo_polling_checkbox and self.vdo_polling_checkbox.isChecked()
        