from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                               QListWidget, QPushButton, QMessageBox)
import os

class LoadWorldDialog(QDialog):
    def __init__(self, saves_dir="saves", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Загрузка мира")
        self.setMinimumSize(300, 400)
        self.saves_dir = saves_dir
        self.selected_file = None

        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        btn_load = QPushButton("Загрузить")
        btn_load.clicked.connect(self.accept_load)

        btn_delete = QPushButton("Удалить")
        btn_delete.clicked.connect(self.delete_save)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_load)
        btn_layout.addWidget(btn_delete)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

        self.refresh_list()

    def refresh_list(self):
        self.list_widget.clear()
        if not os.path.exists(self.saves_dir):
            os.makedirs(self.saves_dir)

        for f in os.listdir(self.saves_dir):
            if f.endswith(".db"):
                self.list_widget.addItem(f[:-3]) # Убираем .db

    def accept_load(self):
        item = self.list_widget.currentItem()
        if item:
            self.selected_file = os.path.join(self.saves_dir, item.text() + ".db")
            self.accept()
        else:
            QMessageBox.warning(self, "Внимание", "Выберите файл для загрузки.")

    def delete_save(self):
        item = self.list_widget.currentItem()
        if item:
            reply = QMessageBox.question(self, "Удаление", f"Удалить сохранение '{item.text()}'?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                file_path = os.path.join(self.saves_dir, item.text() + ".db")
                try:
                    os.remove(file_path)
                    self.refresh_list()
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Не удалось удалить файл: {e}")
