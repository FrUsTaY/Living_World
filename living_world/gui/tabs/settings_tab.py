import os
import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QCheckBox, QComboBox, QPushButton,
                               QGroupBox, QMessageBox)

CONFIG_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "autosave_enabled": True,
    "autosave_interval_days": 5,
    "autosave_filename": "autosave.db",
    "llm_enabled": False,
    "llm_url": "http://localhost:11434",
    "llm_model": "qwen2.5-coder:7b"
}

def load_settings() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                settings = dict(DEFAULT_SETTINGS)
                settings.update(data)
                return settings
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)

def save_settings(settings: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

class SettingsTab(QWidget):
    """
    Вкладка 'Настройки':
    Управление автосохранением, параметрами симуляции и конфигурацией локальной LLM.
    """
    def __init__(self, simulation, main_window):
        super().__init__()
        self.simulation = simulation
        self.main_window = main_window

        self.layout = QVBoxLayout(self)

        # 1. Секция автосохранения
        self.autosave_group = QGroupBox("Настройки автосохранения мира")
        as_layout = QVBoxLayout(self.autosave_group)

        self.chk_autosave = QCheckBox("Включить периодическое автосохранение")

        as_form = QHBoxLayout()
        as_form.addWidget(QLabel("Интервал сохранения:"))
        self.cb_as_interval = QComboBox()
        self.cb_as_interval.addItems(["Каждый игровой день", "Каждые 5 игровых дней", "Каждые 10 игровых дней", "Каждые 30 игровых дней"])
        as_form.addWidget(self.cb_as_interval)
        as_form.addSpacing(20)
        as_form.addWidget(QLabel("Имя файла:"))
        self.txt_as_file = QLineEdit("autosave.db")
        as_form.addWidget(self.txt_as_file)
        as_form.addStretch()

        as_layout.addWidget(self.chk_autosave)
        as_layout.addLayout(as_form)
        self.layout.addWidget(self.autosave_group)

        # 2. Секция локальной LLM
        self.llm_group = QGroupBox("Интеграция с локальной LLM (Ollama)")
        llm_layout = QVBoxLayout(self.llm_group)

        self.chk_llm = QCheckBox("Включить генерацию решений через LLM")

        llm_url_layout = QHBoxLayout()
        llm_url_layout.addWidget(QLabel("HTTP URL сервера LLM:"))
        self.txt_llm_url = QLineEdit("http://localhost:11434")
        llm_url_layout.addWidget(self.txt_llm_url)

        llm_model_layout = QHBoxLayout()
        llm_model_layout.addWidget(QLabel("Название модели (Ollama):"))
        self.txt_llm_model = QLineEdit("qwen2.5-coder:7b")
        llm_model_layout.addWidget(self.txt_llm_model)

        llm_layout.addWidget(self.chk_llm)
        llm_layout.addLayout(llm_url_layout)
        llm_layout.addLayout(llm_model_layout)
        self.layout.addWidget(self.llm_group)

        # Кнопка сохранения
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Сохранить настройки")
        self.btn_save.setStyleSheet("padding: 8px 16px; font-weight: bold;")
        self.btn_save.clicked.connect(self.save_current_settings)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addStretch()

        self.layout.addLayout(btn_layout)
        self.layout.addStretch()

        self._load_into_ui()

    def _load_into_ui(self):
        settings = load_settings()
        self.chk_autosave.setChecked(settings.get("autosave_enabled", True))

        interval = settings.get("autosave_interval_days", 5)
        interval_map = {1: 0, 5: 1, 10: 2, 30: 3}
        self.cb_as_interval.setCurrentIndex(interval_map.get(interval, 1))

        self.txt_as_file.setText(settings.get("autosave_filename", "autosave.db"))

        self.chk_llm.setChecked(settings.get("llm_enabled", False))
        self.txt_llm_url.setText(settings.get("llm_url", "http://localhost:11434"))
        self.txt_llm_model.setText(settings.get("llm_model", "qwen2.5-coder:7b"))

    def save_current_settings(self):
        interval_days_map = {0: 1, 1: 5, 2: 10, 3: 30}
        days = interval_days_map.get(self.cb_as_interval.currentIndex(), 5)

        settings = {
            "autosave_enabled": self.chk_autosave.isChecked(),
            "autosave_interval_days": days,
            "autosave_filename": self.txt_as_file.text().strip() or "autosave.db",
            "llm_enabled": self.chk_llm.isChecked(),
            "llm_url": self.txt_llm_url.text().strip(),
            "llm_model": self.txt_llm_model.text().strip()
        }

        save_settings(settings)
        QMessageBox.information(self, "Настройки", "Настройки успешно сохранены!")

    def update_data(self):
        pass
