from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QFormLayout
from PySide6.QtCore import QTimer

class NPCCardDialog(QDialog):
    def __init__(self, npc, city=None, parent=None):
        super().__init__(parent)
        self.npc = npc
        self.city = city
        self.setWindowTitle(f"Карточка жителя: {npc.get_full_name()}")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)
        self.form = QFormLayout()
        self.labels = {}

        data = npc.to_dict(self.city)
        for key, value in data.items():
            val_label = QLabel(str(value))
            self.labels[key] = val_label
            self.form.addRow(QLabel(f"<b>{key}:</b>"), val_label)

        layout.addLayout(self.form)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_data)
        self.update_timer.start(500) # Обновление каждые 500мс

    def update_data(self):
        data = self.npc.to_dict(self.city)
        for key, value in data.items():
            if key in self.labels:
                self.labels[key].setText(str(value))
