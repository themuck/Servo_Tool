from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QSplitter, QTreeWidget, 
                             QTextEdit, QHeaderView, QTreeWidgetItem)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class FaultListTab(QWidget):
    def __init__(self, fault_data, parent=None):
        super().__init__(parent)
        self.main_app = parent
        self.fault_data = fault_data
        
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Vertical)

        self.fault_tree = QTreeWidget()
        if self.fault_data:
            headers = [
                self.main_app.language_manager.get_text("header_code"),
                self.main_app.language_manager.get_text("header_name"),
                self.main_app.language_manager.get_text("header_resettable")
            ]
            self.fault_tree.setHeaderLabels(headers)

            for fault_entry in self.fault_data:
                items = [
                    fault_entry.get('code', ''),
                    fault_entry.get('name', ''),
                    fault_entry.get('resettable', '')
                ]
                tree_item = QTreeWidgetItem(self.fault_tree, items)
                tree_item.setData(0, Qt.UserRole, fault_entry)

        self.fault_tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.fault_tree.itemSelectionChanged.connect(self.show_fault_details)

        self.fault_details_text = QTextEdit()
        self.fault_details_text.setReadOnly(True)
        self.fault_details_text.setFont(QFont("Courier New", 10))
        self.fault_details_text.setPlaceholderText(self.main_app.language_manager.get_text("placeholder_select_fault_for_details"))

        splitter.addWidget(self.fault_tree)
        splitter.addWidget(self.fault_details_text)
        splitter.setSizes([500, 200])

        layout.addWidget(splitter)

    def show_fault_details(self):
        selected_items = self.fault_tree.selectedItems()
        if not selected_items:
            self.fault_details_text.clear()
            return
        
        full_row_data = selected_items[0].data(0, Qt.UserRole)
        if full_row_data:
            details_str = (f"{self.main_app.language_manager.get_text('details_code')}: {full_row_data.get('code', 'N/A')}\n"
                           f"{self.main_app.language_manager.get_text('details_name')}: {full_row_data.get('name', 'N/A')}\n"
                           f"{self.main_app.language_manager.get_text('details_resettable')}: {full_row_data.get('resettable', 'N/A')}\n\n"
                           f"--- {self.main_app.language_manager.get_text('details_handling')} ---\n"
                           f"{full_row_data.get('description', self.main_app.language_manager.get_text('text_no_details_available'))}")
            self.fault_details_text.setText(details_str)
        else:
            self.fault_details_text.clear()
    
    def update_language(self, language_manager):
        """Update all text elements with the selected language"""
        # Update tree widget headers
        self.fault_tree.setHeaderLabels([
            language_manager.get_text("header_code"),
            language_manager.get_text("header_name"),
            language_manager.get_text("header_resettable")
        ])
        
        # Update details text placeholder
        self.fault_details_text.setPlaceholderText(language_manager.get_text("placeholder_select_fault_for_details"))
        
        # Refresh the current view to update fault details
        selected_items = self.fault_tree.selectedItems()
        if selected_items:
            self.show_fault_details()