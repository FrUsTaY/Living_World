from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QFormLayout

class NPCCardDialog(QDialog):
    def __init__(self, npc, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Карточка жителя: {npc.get_full_name()}")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        data = npc.to_dict()
        for key, value in data.items():
            form.addRow(QLabel(f"<b>{key}:</b>"), QLabel(str(value)))

        layout.addLayout(form)
