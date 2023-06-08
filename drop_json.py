from PyQt6 import QtWidgets
from PyQt6.QtCore import pyqtSignal
import json
import os

class DropGroupBox(QtWidgets.QGroupBox):
    updated = pyqtSignal() 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.parameters = None  # This will be a dictionary of dictionaries
        self.file_name = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            file_path = event.mimeData().urls()[0].toLocalFile()
            if file_path.lower().endswith('.json'):
                with open(file_path) as f:
                    data = json.load(f)
                self.parameters = data
                self.file_name = os.path.splitext(os.path.basename(file_path))[0]
                self.updated.emit()
        event.accept()
        
