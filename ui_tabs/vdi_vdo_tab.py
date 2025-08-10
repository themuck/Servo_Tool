from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QGridLayout, QLabel, QCheckBox, QScrollArea, QPushButton)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

class VDIVDOTab(QWidget):
    # Signal für VDI-Toggle-Events
    vdi_toggled = pyqtSignal(int, bool)  # (VDI-Nummer, Zustand)
    
    def __init__(self, parent=None, language_manager=None):
        super().__init__(parent)
        
        # Speichere den language_manager direkt
        self.language_manager = language_manager
        
        layout = QVBoxLayout(self)

        self.polling_checkbox = QCheckBox(self.language_manager.get_text("checkbox_enable_live_updates"))
        self.polling_checkbox.setEnabled(False)
        layout.addWidget(self.polling_checkbox)

        self.io_status_group = QGroupBox(self.language_manager.get_text("group_live_io_status"))
        main_layout = QHBoxLayout()

        # Erstelle IO-Gruppen mit Funktionsanzeigen
        self.vdi_widgets = self._create_io_group(main_layout, self.language_manager.get_text("group_virtual_digital_inputs_vdi"))
        self.vdo_widgets = self._create_io_group(main_layout, self.language_manager.get_text("group_virtual_digital_outputs_vdo"))
             
        self.io_status_group.setLayout(main_layout)
        layout.addWidget(self.io_status_group)
        
        # Erstelle Legendenfelder für zugewiesene Funktionen
        self.legend_group = QGroupBox(self.language_manager.get_text("group_assigned_functions"))
        legend_layout = QHBoxLayout()
        
        # VDI-Legende (links)
        self.vdi_legend_group = QGroupBox(self.language_manager.get_text("group_virtual_digital_inputs_vdi"))
        vdi_legend_layout = QVBoxLayout()
        
        # Erstelle ScrollArea für die VDI-Legende
        self.vdi_legend_scroll = QScrollArea()
        self.vdi_legend_scroll.setWidgetResizable(True)
        self.vdi_legend_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.vdi_legend_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # Setze Size Policy, damit die ScrollArea die gesamte verfügbare Höhe einnimmt
        from PyQt5.QtWidgets import QSizePolicy
        self.vdi_legend_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Erstelle Container-Widget für den Inhalt der VDI-Legende
        self.vdi_legend_content = QWidget()
        self.vdi_legend_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.vdi_legend_content_layout = QVBoxLayout(self.vdi_legend_content)
        
        self.vdi_functions_label = QLabel(self.language_manager.get_text("text_no_functions_assigned"))
        self.vdi_functions_label.setWordWrap(True)
        self.vdi_functions_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.vdi_functions_label.setAlignment(Qt.AlignTop)  # Text oben ausrichten
        self.vdi_legend_content_layout.addWidget(self.vdi_functions_label)
        
        # Entferne den Stretch, damit das Label die gesamte Höhe einnehmen kann
        self.vdi_legend_scroll.setWidget(self.vdi_legend_content)
        vdi_legend_layout.addWidget(self.vdi_legend_scroll)
        self.vdi_legend_group.setLayout(vdi_legend_layout)
        
        # VDO-Legende (rechts)
        self.vdo_legend_group = QGroupBox(self.language_manager.get_text("group_virtual_digital_outputs_vdo"))
        vdo_legend_layout = QVBoxLayout()
        
        # Erstelle ScrollArea für die VDO-Legende
        self.vdo_legend_scroll = QScrollArea()
        self.vdo_legend_scroll.setWidgetResizable(True)
        self.vdo_legend_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.vdo_legend_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # Setze Size Policy, damit die ScrollArea die gesamte verfügbare Höhe einnimmt
        self.vdo_legend_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Erstelle Container-Widget für den Inhalt der VDO-Legende
        self.vdo_legend_content = QWidget()
        self.vdo_legend_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.vdo_legend_content_layout = QVBoxLayout(self.vdo_legend_content)
        
        self.vdo_functions_label = QLabel(self.language_manager.get_text("text_no_functions_assigned"))
        self.vdo_functions_label.setWordWrap(True)
        self.vdo_functions_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.vdo_functions_label.setAlignment(Qt.AlignTop)  # Text oben ausrichten
        self.vdo_legend_content_layout.addWidget(self.vdo_functions_label)
        
        # Entferne den Stretch, damit das Label die gesamte Höhe einnehmen kann
        self.vdo_legend_scroll.setWidget(self.vdo_legend_content)
        vdo_legend_layout.addWidget(self.vdo_legend_scroll)
        self.vdo_legend_group.setLayout(vdo_legend_layout)
        
        # Füge die Legenden zum Hauptlayout hinzu
        legend_layout.addWidget(self.vdi_legend_group)
        legend_layout.addWidget(self.vdo_legend_group)
        self.legend_group.setLayout(legend_layout)
        
        # Entferne die feste Höhe für die Legende, damit sie flexibel ist
        # Die Legende wird jetzt die gesamte verfügbare Höhe einnehmen
        
        layout.addWidget(self.legend_group)
        # Entferne den Stretch, damit die Legende die gesamte verfügbare Höhe einnehmen kann
        
        self.set_enabled(False) # Initially disabled
        self._set_initial_status() # Set initial orange status

    def _create_io_group(self, parent_layout, group_name):
        group = QGroupBox(group_name)
        layout = QGridLayout()
        # Korrigiere die Beschriftung: "Inputs" -> "Input", "Outputs" -> "Output"
        label_text = self.language_manager.get_text("text_input") if "Input" in group_name else self.language_manager.get_text("text_output")
        
        # Erstelle Widgets für jeden IO (Zustands-Label und Funktions-Label)
        widgets = []
        for i in range(16):
            # Container-Widget für jeden IO
            io_container = QWidget()
            io_layout = QVBoxLayout(io_container)
            io_layout.setContentsMargins(2, 2, 2, 2)
            io_layout.setSpacing(2)
            
            # Zustands-Label
            state_label = self._create_io_label(f"{label_text} {i+1}")
            
            # Für VDI: Toggle-Button statt Zustands-Label
            if "VDI" in group_name:
                toggle_button = QPushButton(f"{label_text} {i+1}")
                toggle_button.setCheckable(True)
                toggle_button.clicked.connect(lambda checked, idx=i+1: self.vdi_toggled.emit(idx, checked))
                toggle_button.setEnabled(False)  # Standardmäßig deaktiviert
                
                # Setze die gleiche Größe wie bei den normalen IO-Labels
                screen = QApplication.primaryScreen()
                if screen:
                    # Berechne DPI-Verhältnis (96 DPI = Standard-Referenz)
                    dpi_ratio = screen.logicalDotsPerInch() / 96.0
                    
                    # Begrenze die Skalierung, um zu große Elemente zu vermeiden
                    max_scale = 1.5  # Maximale Skalierung auf 150%
                    effective_scale = min(dpi_ratio, max_scale)
                    
                    # Passe die Größe der Buttons dynamisch an
                    base_size = 30  # Basisgröße in Pixel
                    scaled_size = int(base_size * effective_scale)
                    toggle_button.setMinimumWidth(scaled_size)
                    toggle_button.setMinimumHeight(scaled_size)
                    
                    # Passe die Schriftgröße dynamisch an
                    base_font_size = 8  # Basis-Schriftgröße
                    scaled_font_size = max(int(base_font_size * effective_scale), 7)  # Mindestens 7pt
                    font = QFont()
                    font.setPointSize(scaled_font_size)
                    font.setBold(True)  # Mache den Text fett, damit der Button besser sichtbar ist
                    toggle_button.setFont(font)
                else:
                    # Fallback, wenn keine Bildschirminformationen verfügbar sind
                    toggle_button.setMinimumWidth(40)
                    toggle_button.setMinimumHeight(40)
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
                state_widget = toggle_button
            else:
                state_widget = state_label
            
            # Funktions-Label
            function_label = QLabel(self.language_manager.get_text("text_not_assigned"))
            function_label.setAlignment(Qt.AlignCenter)
            function_label.setWordWrap(True)
            
            # Dynamische Anpassung der Größe basierend auf der DPI-Einstellung
            screen = QApplication.primaryScreen()
            if screen:
                # Berechne DPI-Verhältnis (96 DPI = Standard-Referenz)
                dpi_ratio = screen.logicalDotsPerInch() / 96.0
                
                # Begrenze die Skalierung, um zu große Elemente zu vermeiden
                max_scale = 1.5  # Maximale Skalierung auf 150%
                effective_scale = min(dpi_ratio, max_scale)
                
                # Passe die Größe der Funktions-Labels dynamisch an
                base_height = 20  # Basisgröße in Pixel
                scaled_height = int(base_height * effective_scale)
                function_label.setMinimumHeight(scaled_height)
                
                # Passe die Schriftgröße dynamisch an
                base_font_size = 7  # Basis-Schriftgröße
                scaled_font_size = max(int(base_font_size * effective_scale), 6)  # Mindestens 6pt
                font = QFont()
                font.setPointSize(scaled_font_size)
                function_label.setFont(font)
            else:
                # Fallback, wenn keine Bildschirminformationen verfügbar sind
                function_label.setMinimumHeight(20)
                font = QFont()
                font.setPointSize(7)
                function_label.setFont(font)
            
            function_label.setStyleSheet("border: 1px solid black; background-color: white;")
            
            # Füge Labels zum Container hinzu
            io_layout.addWidget(state_widget)
            io_layout.addWidget(function_label)
            
            # Füge Container zum Grid-Layout hinzu
            layout.addWidget(io_container, i // 8, i % 8)
            
            # Speichere beide Labels im Widget-Dictionary
            widgets.append({
                'state': state_label,
                'state_widget': state_widget,  # Für VDI: Toggle-Button, für VDO: Zustands-Label
                'function': function_label
            })
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
        return widgets
    
    def _create_io_label(self, text):
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setFrameShape(QLabel.Panel)
        label.setFrameShadow(QLabel.Sunken)
        
        # Dynamische Anpassung der Größe basierend auf der DPI-Einstellung
        screen = QApplication.primaryScreen()
        if screen:
            # Berechne DPI-Verhältnis (96 DPI = Standard-Referenz)
            dpi_ratio = screen.logicalDotsPerInch() / 96.0
            
            # Begrenze die Skalierung, um zu große Elemente zu vermeiden
            max_scale = 1.5  # Maximale Skalierung auf 150%
            effective_scale = min(dpi_ratio, max_scale)
            
            # Passe die Größe der Labels dynamisch an
            base_size = 30  # Basisgröße in Pixel
            scaled_size = int(base_size * effective_scale)
            label.setMinimumWidth(scaled_size)
            label.setMinimumHeight(scaled_size)
            
            # Passe die Schriftgröße dynamisch an
            base_font_size = 8  # Basis-Schriftgröße
            scaled_font_size = max(int(base_font_size * effective_scale), 7)  # Mindestens 7pt
            font = QFont()
            font.setPointSize(scaled_font_size)
            label.setFont(font)
        else:
            # Fallback, wenn keine Bildschirminformationen verfügbar sind
            label.setMinimumWidth(40)
            label.setMinimumHeight(40)
            font = QFont()
            font.setPointSize(8)
            label.setFont(font)
        
        label.setStyleSheet("background-color: lightgray; border: 1px solid black;")
        return label
    
    def _set_initial_status(self):
        """Setzt alle Status-Labels auf orange, um anzuzeigen, dass noch kein Wert geladen wurde"""
        for widgets in [self.vdi_widgets, self.vdo_widgets]:
            for widget in widgets:
                # Für VDI: Toggle-Button auf orange setzen
                if 'state_widget' in widget and isinstance(widget['state_widget'], QPushButton):
                    widget['state_widget'].setStyleSheet(
                        "background-color: orange; border: 1px solid black;"
                    )
                else:
                    # Für VDO: Zustands-Label auf orange setzen
                    widget['state'].setStyleSheet("background-color: orange; border: 1px solid black;")

    def set_vdi_labels(self, values_int):
        self._update_labels(self.vdi_widgets, values_int)

    def set_vdo_labels(self, values_int):
        self._update_labels(self.vdo_widgets, values_int)
        
    def _update_labels(self, widgets, values_int):
        for i in range(16):
            is_on = (values_int >> i) & 1
            color = 'lightgreen' if is_on else 'lightgray' # Logik gedreht
            
            # Für VDI: Toggle-Button updaten
            if 'state_widget' in widgets[i] and isinstance(widgets[i]['state_widget'], QPushButton):
                widgets[i]['state_widget'].setChecked(is_on)
                widgets[i]['state_widget'].setStyleSheet(
                    f"background-color: {'lightgreen' if is_on else 'lightgray'}; border: 1px solid black;" # Logik gedreht
                )
            else:
                # Für VDO: Zustands-Label updaten
                widgets[i]['state'].setStyleSheet(f"background-color: {color}; border: 1px solid black;")
    
    def set_vdi_functions(self, functions):
        """Setzt die Funktionsbeschreibungen für die Virtual Digital Inputs"""
        self._update_functions(self.vdi_widgets, functions)
    
    def set_vdo_functions(self, functions):
        """Setzt die Funktionsbeschreibungen für die Virtual Digital Outputs"""
        self._update_functions(self.vdo_widgets, functions)
    
    def _update_functions(self, widgets, functions):
        """Aktualisiert die Funktionsbeschreibungen für die IOs"""
        for i in range(16):
            if i < len(functions) and functions[i]:
                widgets[i]['function'].setText(functions[i])
            else:
                widgets[i]['function'].setText(self.language_manager.get_text("text_not_assigned"))

    def set_enabled(self, enabled):
        self.io_status_group.setEnabled(enabled)
        self.legend_group.setEnabled(enabled)
        self.polling_checkbox.setEnabled(enabled)
        if not enabled:
            self.polling_checkbox.setChecked(False)
            # Setze Status-Labels auf orange zurück, anstatt auf grün/grau
            self._set_initial_status()
            # Setze Funktionsbeschreibungen zurück
            self._update_functions(self.vdi_widgets, [self.language_manager.get_text("text_not_assigned")] * 16)
            self._update_functions(self.vdo_widgets, [self.language_manager.get_text("text_not_assigned")] * 16)
            # Setze Legende zurück
            self.vdi_functions_label.setText(self.language_manager.get_text("text_no_functions_assigned"))
            self.vdo_functions_label.setText(self.language_manager.get_text("text_no_functions_assigned"))
        else:
            # Aktiviere die VDI-Toggle-Buttons, wenn die Verbindung aktiv ist
            for widget in self.vdi_widgets:
                if 'state_widget' in widget and isinstance(widget['state_widget'], QPushButton):
                    widget['state_widget'].setEnabled(True)
    
    def update_vdi_legend(self, functions, function_details=None):
        """Aktualisiert die Legende für Virtual Digital Inputs mit den zugewiesenen Funktionen"""
        self._update_legend(self.vdi_functions_label, functions, function_details)
    
    def update_vdo_legend(self, functions, function_details=None):
        """Aktualisiert die Legende für Virtual Digital Outputs mit den zugewiesenen Funktionen"""
        self._update_legend(self.vdo_functions_label, functions, function_details)
    
    def _update_legend(self, label, functions, function_details=None):
        """Aktualisiert die Legende mit den zugewiesenen Funktionen"""
        if not functions or all(f == self.language_manager.get_text("text_not_assigned") or f == self.language_manager.get_text("text_not_available") or f == self.language_manager.get_text("text_error") for f in functions):
            label.setText(self.language_manager.get_text("text_no_functions_assigned"))
        else:
            # Filtere nur die tatsächlich zugewiesenen Funktionen (nicht die mit Wert 0)
            assigned_functions = []
            for i, func in enumerate(functions):
                # Schließe nicht zugewiesene Funktionen (Wert 0) aus
                if func not in [self.language_manager.get_text("text_not_assigned"), self.language_manager.get_text("text_not_available"), self.language_manager.get_text("text_error"), "0"]:
                    # Bestimme den IO-Typ basierend auf dem Label
                    if label == self.vdi_functions_label:
                        io_type = "VDI"
                    elif label == self.vdo_functions_label:
                        io_type = "VDO"
                    else:
                        io_type = "IO"
                    
                    # Erstelle den Eintrag für die Legende
                    legend_entry = f"{io_type}{i+1}: {func}"
                    
                    # Füge Funktion und Beschreibung hinzu, wenn Details verfügbar sind
                    if function_details and i < len(function_details):
                        details = function_details[i]
                        if details and 'function' in details:
                            legend_entry += f"\n  {self.language_manager.get_text('text_function')}: {details['function']}"
                        if details and 'description' in details:
                            legend_entry += f"\n  {self.language_manager.get_text('text_description')}: {details['description']}"
                    
                    assigned_functions.append(legend_entry)
            
            if assigned_functions:
                label.setText("\n".join(assigned_functions))
            else:
                label.setText(self.language_manager.get_text("text_no_functions_assigned"))
    
    def update_language(self, language_manager):
        """Update all text elements with the selected language"""
        # Update language manager reference
        self.language_manager = language_manager
        
        # Update checkbox
        self.polling_checkbox.setText(language_manager.get_text("checkbox_enable_live_updates"))
        
        # Update group box titles
        self.io_status_group.setTitle(language_manager.get_text("group_live_io_status"))
        self.legend_group.setTitle(language_manager.get_text("group_assigned_functions"))
        self.vdi_legend_group.setTitle(language_manager.get_text("group_virtual_digital_inputs_vdi"))
        self.vdo_legend_group.setTitle(language_manager.get_text("group_virtual_digital_outputs_vdo"))
        
        # Get the current and previous language texts for comparison
        old_not_assigned = "Nicht zugewiesen" if language_manager.get_current_language() == "en" else "Not Assigned"
        new_not_assigned = language_manager.get_text("text_not_assigned")
        
        old_no_functions = "Keine Funktionen zugewiesen" if language_manager.get_current_language() == "en" else "No Functions Assigned"
        new_no_functions = language_manager.get_text("text_no_functions_assigned")
        
        # Update function labels
        for i in range(16):
            if i < len(self.vdi_widgets):
                current_text = self.vdi_widgets[i]['function'].text()
                if current_text == old_not_assigned or current_text == "Nicht zugewiesen" or current_text == "Not Assigned":
                    self.vdi_widgets[i]['function'].setText(new_not_assigned)
            
            if i < len(self.vdo_widgets):
                current_text = self.vdo_widgets[i]['function'].text()
                if current_text == old_not_assigned or current_text == "Nicht zugewiesen" or current_text == "Not Assigned":
                    self.vdo_widgets[i]['function'].setText(new_not_assigned)
        
        # Update legend labels
        vdi_legend_text = self.vdi_functions_label.text()
        if vdi_legend_text == old_no_functions or vdi_legend_text == "Keine Funktionen zugewiesen" or vdi_legend_text == "No Functions Assigned":
            self.vdi_functions_label.setText(new_no_functions)
        
        vdo_legend_text = self.vdo_functions_label.text()
        if vdo_legend_text == old_no_functions or vdo_legend_text == "Keine Funktionen zugewiesen" or vdo_legend_text == "No Functions Assigned":
            self.vdo_functions_label.setText(new_no_functions)
        
        # Update state labels
        for i in range(16):
            if i < len(self.vdi_widgets):
                # Für VDI: Toggle-Button-Text updaten
                if 'state_widget' in self.vdi_widgets[i] and isinstance(self.vdi_widgets[i]['state_widget'], QPushButton):
                    label_text = self.vdi_widgets[i]['state_widget'].text()
                    if label_text.startswith("Input"):
                        self.vdi_widgets[i]['state_widget'].setText(
                            language_manager.get_text("text_input") + " " + str(i+1)
                        )
                else:
                    # Für VDO: Zustands-Label-Text updaten
                    label_text = self.vdi_widgets[i]['state'].text()
                    if label_text.startswith("Input"):
                        self.vdi_widgets[i]['state'].setText(
                            language_manager.get_text("text_input") + " " + str(i+1)
                        )
            
            if i < len(self.vdo_widgets):
                label_text = self.vdo_widgets[i]['state'].text()
                if label_text.startswith("Output"):
                    self.vdo_widgets[i]['state'].setText(
                        language_manager.get_text("text_output") + " " + str(i+1)
                    )