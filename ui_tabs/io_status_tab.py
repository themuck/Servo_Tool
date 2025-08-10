from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QGridLayout, QLabel, QCheckBox, QScrollArea)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

class IOStatusTab(QWidget):
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
        self.di_widgets = self._create_io_group(main_layout, self.language_manager.get_text("group_digital_inputs_di"))
        self.do_widgets = self._create_io_group(main_layout, self.language_manager.get_text("group_digital_outputs_do"))
             
        self.io_status_group.setLayout(main_layout)
        layout.addWidget(self.io_status_group)
        
        # Erstelle Legendenfelder für zugewiesene Funktionen
        self.legend_group = QGroupBox(self.language_manager.get_text("group_assigned_functions"))
        legend_layout = QHBoxLayout()
        
        # DI-Legende (links)
        self.di_legend_group = QGroupBox(self.language_manager.get_text("group_digital_inputs_di"))
        di_legend_layout = QVBoxLayout()
        
        # Erstelle ScrollArea für die DI-Legende
        self.di_legend_scroll = QScrollArea()
        self.di_legend_scroll.setWidgetResizable(True)
        self.di_legend_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.di_legend_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # Setze Size Policy, damit die ScrollArea die gesamte verfügbare Höhe einnimmt
        from PyQt5.QtWidgets import QSizePolicy
        self.di_legend_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Erstelle Container-Widget für den Inhalt der DI-Legende
        self.di_legend_content = QWidget()
        self.di_legend_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.di_legend_content_layout = QVBoxLayout(self.di_legend_content)
        
        self.di_functions_label = QLabel(self.language_manager.get_text("text_no_functions_assigned"))
        self.di_functions_label.setWordWrap(True)
        self.di_functions_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.di_functions_label.setAlignment(Qt.AlignTop)  # Text oben ausrichten
        self.di_legend_content_layout.addWidget(self.di_functions_label)
        
        # Entferne den Stretch, damit das Label die gesamte Höhe einnehmen kann
        self.di_legend_scroll.setWidget(self.di_legend_content)
        di_legend_layout.addWidget(self.di_legend_scroll)
        self.di_legend_group.setLayout(di_legend_layout)
        
        # DO-Legende (rechts)
        self.do_legend_group = QGroupBox(self.language_manager.get_text("group_digital_outputs_do"))
        do_legend_layout = QVBoxLayout()
        
        # Erstelle ScrollArea für die DO-Legende
        self.do_legend_scroll = QScrollArea()
        self.do_legend_scroll.setWidgetResizable(True)
        self.do_legend_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.do_legend_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # Setze Size Policy, damit die ScrollArea die gesamte verfügbare Höhe einnimmt
        self.do_legend_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Erstelle Container-Widget für den Inhalt der DO-Legende
        self.do_legend_content = QWidget()
        self.do_legend_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.do_legend_content_layout = QVBoxLayout(self.do_legend_content)
        
        self.do_functions_label = QLabel(self.language_manager.get_text("text_no_functions_assigned"))
        self.do_functions_label.setWordWrap(True)
        self.do_functions_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.do_functions_label.setAlignment(Qt.AlignTop)  # Text oben ausrichten
        self.do_legend_content_layout.addWidget(self.do_functions_label)
        
        # Entferne den Stretch, damit das Label die gesamte Höhe einnehmen kann
        self.do_legend_scroll.setWidget(self.do_legend_content)
        do_legend_layout.addWidget(self.do_legend_scroll)
        self.do_legend_group.setLayout(do_legend_layout)
        
        # Füge die Legenden zum Hauptlayout hinzu
        legend_layout.addWidget(self.di_legend_group)
        legend_layout.addWidget(self.do_legend_group)
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
            io_layout.addWidget(state_label)
            io_layout.addWidget(function_label)
            
            # Füge Container zum Grid-Layout hinzu
            layout.addWidget(io_container, i // 8, i % 8)
            
            # Speichere beide Labels im Widget-Dictionary
            widgets.append({
                'state': state_label,
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
        for widgets in [self.di_widgets, self.do_widgets]:
            for widget in widgets:
                widget['state'].setStyleSheet("background-color: orange; border: 1px solid black;")

    def set_di_labels(self, values_int):
        self._update_labels(self.di_widgets, values_int)

    def set_do_labels(self, values_int):
        self._update_labels(self.do_widgets, values_int)
        
    def _update_labels(self, widgets, values_int):
        for i in range(16):
            is_on = (values_int >> i) & 1
            color = 'lightgray' if is_on else 'lightgreen'
            widgets[i]['state'].setStyleSheet(f"background-color: {color}; border: 1px solid black;")
    
    def set_di_functions(self, functions):
        """Setzt die Funktionsbeschreibungen für die Digital Inputs"""
        self._update_functions(self.di_widgets, functions)
    
    def set_do_functions(self, functions):
        """Setzt die Funktionsbeschreibungen für die Digital Outputs"""
        self._update_functions(self.do_widgets, functions)
    
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
            self._update_functions(self.di_widgets, [self.language_manager.get_text("text_not_assigned")] * 16)
            self._update_functions(self.do_widgets, [self.language_manager.get_text("text_not_assigned")] * 16)
            # Setze Legende zurück
            self.di_functions_label.setText(self.language_manager.get_text("text_no_functions_assigned"))
            self.do_functions_label.setText(self.language_manager.get_text("text_no_functions_assigned"))
    
    def update_di_legend(self, functions, function_details=None):
        """Aktualisiert die Legende für Digital Inputs mit den zugewiesenen Funktionen"""
        self._update_legend(self.di_functions_label, functions, function_details)
    
    def update_do_legend(self, functions, function_details=None):
        """Aktualisiert die Legende für Digital Outputs mit den zugewiesenen Funktionen"""
        self._update_legend(self.do_functions_label, functions, function_details)
    
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
                    if label == self.di_functions_label:
                        io_type = "DI"
                    elif label == self.do_functions_label:
                        io_type = "DO"
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
        self.di_legend_group.setTitle(language_manager.get_text("group_digital_inputs_di"))
        self.do_legend_group.setTitle(language_manager.get_text("group_digital_outputs_do"))
        
        # Get the current and previous language texts for comparison
        old_not_assigned = "Nicht zugewiesen" if language_manager.get_current_language() == "en" else "Not Assigned"
        new_not_assigned = language_manager.get_text("text_not_assigned")
        
        old_no_functions = "Keine Funktionen zugewiesen" if language_manager.get_current_language() == "en" else "No Functions Assigned"
        new_no_functions = language_manager.get_text("text_no_functions_assigned")
        
        # Update function labels
        for i in range(16):
            if i < len(self.di_widgets):
                current_text = self.di_widgets[i]['function'].text()
                if current_text == old_not_assigned or current_text == "Nicht zugewiesen" or current_text == "Not Assigned":
                    self.di_widgets[i]['function'].setText(new_not_assigned)
            
            if i < len(self.do_widgets):
                current_text = self.do_widgets[i]['function'].text()
                if current_text == old_not_assigned or current_text == "Nicht zugewiesen" or current_text == "Not Assigned":
                    self.do_widgets[i]['function'].setText(new_not_assigned)
        
        # Update legend labels
        di_legend_text = self.di_functions_label.text()
        if di_legend_text == old_no_functions or di_legend_text == "Keine Funktionen zugewiesen" or di_legend_text == "No Functions Assigned":
            self.di_functions_label.setText(new_no_functions)
        
        do_legend_text = self.do_functions_label.text()
        if do_legend_text == old_no_functions or do_legend_text == "Keine Funktionen zugewiesen" or do_legend_text == "No Functions Assigned":
            self.do_functions_label.setText(new_no_functions)
        
        # Update state labels
        for i in range(16):
            if i < len(self.di_widgets):
                label_text = self.di_widgets[i]['state'].text()
                if label_text.startswith("Input"):
                    self.di_widgets[i]['state'].setText(
                        language_manager.get_text("text_input") + " " + str(i+1)
                    )
            
            if i < len(self.do_widgets):
                label_text = self.do_widgets[i]['state'].text()
                if label_text.startswith("Output"):
                    self.do_widgets[i]['state'].setText(
                        language_manager.get_text("text_output") + " " + str(i+1)
                    )
